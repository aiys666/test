
 -- 20261021
  drop table if exists mx.darren_temp_limit_base_table_261021_3;
create table mx.darren_temp_limit_base_table_261021_3 as 
with t0 as (
--- 留10%灰度不发 本次有效期5天 
select t0.*,
  t1.*,
  t2.*,
  t4.*,
  case when repayment_clearing_count<=2 then -2 else 2 end as repayment_score,
  case when (advance_duotou_cnt_x_19<=1  or advance_duotou_cnt_x_19>=5) then -1 else 1 end as duotou_score,
  -- t5.*,
  t3.random_no as random_num, --随机数
  -- t4.repayment_clearing_count,-- 结清次数
  -- t4.daily_max_available_limit, -- 最新的单日最大可借(固定额度)
   case when from_base(substr(to_hex(sha256(to_utf8('20260422'||identity_number||app_group))),1,4),16)/65536.0000000000000000 >=0.2 then '1021临额测试组_有在贷' else '1021临额对照组_有在贷' end as temp_limit_tag, 
  case when curr_main_available_limit + coalesce(curr_temp_credit_limit,0) - coalesce(curr_temp_used_credit_limit,0) < 200 then '可用额度不足'
    when curr_main_available_limit + coalesce(curr_temp_credit_limit,0) - coalesce(curr_temp_used_credit_limit,0) >= 200 then '可用额度充足且有在贷' end as tagg,     -- 剩余主额+剩余临额      在贷是where做了限制
    -- 主额的20%和在贷临额的最大值是此次临额最大值
  -- round(greatest(curr_main_credit_limit*0.2,coalesce(curr_temp_used_credit_limit,0))/50)*50 as temp_limit_issue_amount
  round(greatest(greatest(curr_main_credit_limit*0.3,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50 as temp_limit_issue_amount-- 如果这个值小于200 仍给200 30%
  -- round(greatest(greatest(curr_main_credit_limit*0.2,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50 as temp_limit_issue_amount-- 如果这个值小于200 仍给200  20%
-- round(greatest(greatest(curr_main_credit_limit*0.1,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50 as temp_limit_issue_amount-- 如果这个值小于200 仍给200 10%
-- round(greatest(greatest(curr_main_credit_limit*0.15,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50 as temp_limit_issue_amount-- 如果这个值小于200 仍给200 15%
  -- ,curr_credit_level
  -- ,curr_credit_level_version
from (
select *
from dws.dws_risk_stgy_apply_mid_tags 
) t0  --  存最新一天的切片数据(但也是T-1的数据   比如今天是5.14  这个数据是5.13下午6点左右更新的)
left join 
-- 取最新的用信临额发放日期
-- 用信确认临额调整临额(C010) :当用户用信时，触发用信临额决策流，用户确认使用临额后触发变更; ('C013','C015')  离线发临额
-- (select *
-- from (
-- select mid as mid1,
--   create_time as temp_limit_issue_date,
--   row_number() over(partition by mid order by create_time desc) as rn1
-- from ods_view_presto.s05_user_creditlimit_change_record
-- where limit_type = 'TEMP'
-- and change_event_type in ('C010','C013','C015')) tt0   
-- where rn1 = 1) t1 
-- on t0.mid = t1.mid1
-- 取最新的临额使用日期
(select *
from (
select  mid as mid1,create_time as temp_limit_issue_date,  -- 实际是使用时间这里为了保持表格一致性没改
row_number() over(partition by mid order by create_time desc) as rn1
from ods_view_presto.s05_user_creditlimit_used_detail
where change_action = 'FREEZE_LIMIT' and limit_type = 'TEMP'
) tt0   
where rn1 = 1) t1 
on t0.mid = t1.mid1
left join (
--- mid维度的结清期次数及结清订单数
select t0.mid as mid4
 ,count(distinct case when t1.state in (1,3,5) and fact_time < load_time then rid end) as repayment_clearing_count_index
 ,count(distinct case when t2.state in (1,2) and finish_time < load_time then camera_id end) as repayment_clearing_count
from dws.dws_risk_stgy_apply_mid_tags t0
left join (select customer_id,fact_time,rid,state
 from ods_view_presto.s02_loan_repayment) t1--根据历史订单biz_id取所有放款订单(期数维度)
on cast(t0.mid as bigint) = cast(t1.customer_id as bigint)
and t0.load_time > t1.fact_time -- 切片表加载时间时间 以防穿越
left join (select customer_id,finish_time,camera_id,state
from ods_view_presto.s02_loan) t2 --根据历史订单biz_id取所有放款订单(订单维度)
on cast(t0.mid as bigint) = cast(t2.customer_id as bigint)
and t0.load_time > t2.finish_time -- 切片表加载时间时间 以防穿越
group by 1) t4
on cast(t0.mid as varchar) = cast(t4.mid4 as varchar)
-- 取最新的老客V5_2主评级   切片表的数据有空值不太准确
left join 
(select mid as mid2,android_oldcust_maincreditlevel_charge_v5_3,
advance_duotou_cnt_x_19,
row_number() over (partition by mid order by createtime desc) as rn2 
from mx.android_oldcust_maincreditlevel_charge_v5_3_table) t2  -- T0 早上11点更新的数据
on t0.mid = t2.mid2 and t2.rn2 = 1
-- 为了取随机数
left join dwd.dwd_mem_info t3 
on t0.mid = t3.mid
-- 取最新的单日最大可借(固定额度)
-- left join (
--   select mid,daily_max_available_limit
--   from ods_view_presto.s05_user_credit_limit
--   where limit_type = 'MAIN') t4 
-- on t0.mid = t4.mid
-- 以下即发放人群  之前的版本
-- where id_curr_overdue_days <= 0 -- 当前未逾期
-- and t0.age <= 65 -- 年龄<=65
-- and id_30days_max_overdue_days <= 0 -- 近30天最大逾期天数<=0(即近30天无逾期记录)
-- -- and curr_main_available_limit < 200 --- 可用额度不足     (没做这个限制  限制了不利于追业绩)
where curr_ovd_cnt_this_app_group <= 0 -- 本包当前无逾期
and curr_ovd_cnt_other_app_group_90d <= 0 --- 他包近90天无逾期
and t0.age <= 65 --- 年龄<=65
and (id_30days_max_overdue_days <= 0 or id_30days_max_overdue_days is null)--- 近30天无逾期
and if_prohibit_apply = 0 --- 不在禁申期中
and curr_main_limit_expire_date > to_date(cast(current_date as varchar), 'yyyy-mm-dd') --- 主额度未过期
and app_group in ('Balam Plata','Tuna Cash','Mexcredo')
-- ,'Mikredi'
and onloan_cnt > 0 --- 有在贷 
and is_reloan_stgy = 1 --- 复贷客户
and (date_diff('day',temp_limit_issue_date,date(current_date)) >= 10 or temp_limit_issue_date is null) 
-- --- 距离上次临额使用时间>=10天 或者暂时未使用过临额   
 )

select *,
-- 用户今天总共能用的额度 = min(剩余主额, 每日限额) + 剩余临额(运营发营销话术需要用到)
  round(least(greatest(coalesce(curr_main_available_limit,0),0),daily_max_available_limit) + greatest(temp_limit_issue_amount - coalesce(curr_temp_used_credit_limit,0),0)) as total_available_limit
from t0 
-- 8月-9月初版本，提额比例加大（30%）；
-- where (android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 or  
-- android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and repayment_score+duotou_score>=-1)-- 30%
-- 8月-9月初版本，提额比例加大（15%）；
-- where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and  repayment_score+duotou_score<-1
-- or android_oldcust_maincreditlevel_charge_v5_3>=8 and android_oldcust_maincreditlevel_charge_v5_3<=10 and  repayment_score+duotou_score>=-1)-- 15%

-- 回滚至7月版本（9月9号开始复用）
where android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 and  repayment_score+duotou_score>=-1-- 30%
-- where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and repayment_score+duotou_score>=-1
-- or android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 and repayment_score+duotou_score<-1
-- ) -- 20%
-- where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and  repayment_score+duotou_score<-1
-- or android_oldcust_maincreditlevel_charge_v5_3>=8 and android_oldcust_maincreditlevel_charge_v5_3<=10 and  repayment_score+duotou_score>-1)-- 10%

-- where temp_limit_issue_amount >= 200 -- 发放临额要大于等于200
;



 drop table if exists mx.darren_temp_limit_base_table_261021_2;
create table mx.darren_temp_limit_base_table_261021_2 as 
with t0 as (
--- 留10%灰度不发 本次有效期5天 
select t0.*,
  t1.*,
  t2.*,
  t4.*,
  case when repayment_clearing_count<=2 then -2 else 2 end as repayment_score,
  case when (advance_duotou_cnt_x_19<=1  or advance_duotou_cnt_x_19>=5) then -1 else 1 end as duotou_score,
  -- t5.*,
  t3.random_no as random_num, --随机数
  -- t4.repayment_clearing_count,-- 结清次数
  -- t4.daily_max_available_limit, -- 最新的单日最大可借(固定额度)
   case when from_base(substr(to_hex(sha256(to_utf8('20260422'||identity_number||app_group))),1,4),16)/65536.0000000000000000 >=0.2 then '1021临额测试组_有在贷' else '1021临额对照组_有在贷' end as temp_limit_tag, 
  case when curr_main_available_limit + coalesce(curr_temp_credit_limit,0) - coalesce(curr_temp_used_credit_limit,0) < 200 then '可用额度不足'
    when curr_main_available_limit + coalesce(curr_temp_credit_limit,0) - coalesce(curr_temp_used_credit_limit,0) >= 200 then '可用额度充足且有在贷' end as tagg,     -- 剩余主额+剩余临额      在贷是where做了限制
    -- 主额的20%和在贷临额的最大值是此次临额最大值
  -- round(greatest(curr_main_credit_limit*0.2,coalesce(curr_temp_used_credit_limit,0))/50)*50 as temp_limit_issue_amount
  -- round(greatest(greatest(curr_main_credit_limit*0.3,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50 as temp_limit_issue_amount-- 如果这个值小于200 仍给200 30%
  round(greatest(greatest(curr_main_credit_limit*0.2,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50 as temp_limit_issue_amount-- 如果这个值小于200 仍给200  20%
-- round(greatest(greatest(curr_main_credit_limit*0.1,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50 as temp_limit_issue_amount-- 如果这个值小于200 仍给200 10%
-- round(greatest(greatest(curr_main_credit_limit*0.15,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50 as temp_limit_issue_amount-- 如果这个值小于200 仍给200 15%
  -- ,curr_credit_level
  -- ,curr_credit_level_version
from (
select *
from dws.dws_risk_stgy_apply_mid_tags 
) t0  --  存最新一天的切片数据(但也是T-1的数据   比如今天是5.14  这个数据是5.13下午6点左右更新的)
left join 
-- 取最新的用信临额发放日期
-- 用信确认临额调整临额(C010) :当用户用信时，触发用信临额决策流，用户确认使用临额后触发变更; ('C013','C015')  离线发临额
-- (select *
-- from (
-- select mid as mid1,
--   create_time as temp_limit_issue_date,
--   row_number() over(partition by mid order by create_time desc) as rn1
-- from ods_view_presto.s05_user_creditlimit_change_record
-- where limit_type = 'TEMP'
-- and change_event_type in ('C010','C013','C015')) tt0   
-- where rn1 = 1) t1 
-- on t0.mid = t1.mid1
-- 取最新的临额使用日期
(select *
from (
select  mid as mid1,create_time as temp_limit_issue_date,  -- 实际是使用时间这里为了保持表格一致性没改
row_number() over(partition by mid order by create_time desc) as rn1
from ods_view_presto.s05_user_creditlimit_used_detail
where change_action = 'FREEZE_LIMIT' and limit_type = 'TEMP'
) tt0   
where rn1 = 1) t1 
on t0.mid = t1.mid1
left join (
--- mid维度的结清期次数及结清订单数
select t0.mid as mid4
 ,count(distinct case when t1.state in (1,3,5) and fact_time < load_time then rid end) as repayment_clearing_count_index
 ,count(distinct case when t2.state in (1,2) and finish_time < load_time then camera_id end) as repayment_clearing_count
from dws.dws_risk_stgy_apply_mid_tags t0
left join (select customer_id,fact_time,rid,state
 from ods_view_presto.s02_loan_repayment) t1--根据历史订单biz_id取所有放款订单(期数维度)
on cast(t0.mid as bigint) = cast(t1.customer_id as bigint)
and t0.load_time > t1.fact_time -- 切片表加载时间时间 以防穿越
left join (select customer_id,finish_time,camera_id,state
from ods_view_presto.s02_loan) t2 --根据历史订单biz_id取所有放款订单(订单维度)
on cast(t0.mid as bigint) = cast(t2.customer_id as bigint)
and t0.load_time > t2.finish_time -- 切片表加载时间时间 以防穿越
group by 1) t4
on cast(t0.mid as varchar) = cast(t4.mid4 as varchar)
-- 取最新的老客V5_2主评级   切片表的数据有空值不太准确
left join 
(select mid as mid2,android_oldcust_maincreditlevel_charge_v5_3,
advance_duotou_cnt_x_19,
row_number() over (partition by mid order by createtime desc) as rn2 
from mx.android_oldcust_maincreditlevel_charge_v5_3_table) t2  -- T0 早上11点更新的数据
on t0.mid = t2.mid2 and t2.rn2 = 1
-- 为了取随机数
left join dwd.dwd_mem_info t3 
on t0.mid = t3.mid
-- 取最新的单日最大可借(固定额度)
-- left join (
--   select mid,daily_max_available_limit
--   from ods_view_presto.s05_user_credit_limit
--   where limit_type = 'MAIN') t4 
-- on t0.mid = t4.mid
-- 以下即发放人群  之前的版本
-- where id_curr_overdue_days <= 0 -- 当前未逾期
-- and t0.age <= 65 -- 年龄<=65
-- and id_30days_max_overdue_days <= 0 -- 近30天最大逾期天数<=0(即近30天无逾期记录)
-- -- and curr_main_available_limit < 200 --- 可用额度不足     (没做这个限制  限制了不利于追业绩)
where curr_ovd_cnt_this_app_group <= 0 -- 本包当前无逾期
and curr_ovd_cnt_other_app_group_90d <= 0 --- 他包近90天无逾期
and t0.age <= 65 --- 年龄<=65
and (id_30days_max_overdue_days <= 0 or id_30days_max_overdue_days is null)--- 近30天无逾期
and if_prohibit_apply = 0 --- 不在禁申期中
and curr_main_limit_expire_date > to_date(cast(current_date as varchar), 'yyyy-mm-dd') --- 主额度未过期
and app_group in ('Balam Plata','Tuna Cash','Mexcredo')
-- ,'Mikredi'
and onloan_cnt > 0 --- 有在贷 
and is_reloan_stgy = 1 --- 复贷客户
and (date_diff('day',temp_limit_issue_date,date(current_date)) >= 10 or temp_limit_issue_date is null) 
-- --- 距离上次临额使用时间>=10天 或者暂时未使用过临额   
 )

select *,
-- 用户今天总共能用的额度 = min(剩余主额, 每日限额) + 剩余临额(运营发营销话术需要用到)
  round(least(greatest(coalesce(curr_main_available_limit,0),0),daily_max_available_limit) + greatest(temp_limit_issue_amount - coalesce(curr_temp_used_credit_limit,0),0)) as total_available_limit
from t0 
-- 8月-9月初版本，提额比例加大（30%）；
-- where (android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 or  
-- android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and repayment_score+duotou_score>=-1)-- 30%
-- 8月-9月初版本，提额比例加大（15%）；
-- where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and  repayment_score+duotou_score<-1
-- or android_oldcust_maincreditlevel_charge_v5_3>=8 and android_oldcust_maincreditlevel_charge_v5_3<=10 and  repayment_score+duotou_score>=-1)-- 15%

-- 回滚至7月版本（9月9号开始复用）
-- where android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 and  repayment_score+duotou_score>=-1-- 30%
where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and repayment_score+duotou_score>=-1
or android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 and repayment_score+duotou_score<-1
) -- 20%
-- where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and  repayment_score+duotou_score<-1
-- or android_oldcust_maincreditlevel_charge_v5_3>=8 and android_oldcust_maincreditlevel_charge_v5_3<=10 and  repayment_score+duotou_score>-1)-- 10%

-- where temp_limit_issue_amount >= 200 -- 发放临额要大于等于200
;




 drop table if exists mx.darren_temp_limit_base_table_261021_1;
create table mx.darren_temp_limit_base_table_261021_1 as 
with t0 as (
--- 留10%灰度不发 本次有效期5天 
select t0.*,
  t1.*,
  t2.*,
  t4.*,
  case when repayment_clearing_count<=2 then -2 else 2 end as repayment_score,
  case when (advance_duotou_cnt_x_19<=1  or advance_duotou_cnt_x_19>=5) then -1 else 1 end as duotou_score,
  -- t5.*,
  t3.random_no as random_num, --随机数
  -- t4.repayment_clearing_count,-- 结清次数
  -- t4.daily_max_available_limit, -- 最新的单日最大可借(固定额度)
   case when from_base(substr(to_hex(sha256(to_utf8('20260422'||identity_number||app_group))),1,4),16)/65536.0000000000000000 >=0.2 then '1021临额测试组_有在贷' else '1021临额对照组_有在贷' end as temp_limit_tag, 
  case when curr_main_available_limit + coalesce(curr_temp_credit_limit,0) - coalesce(curr_temp_used_credit_limit,0) < 200 then '可用额度不足'
    when curr_main_available_limit + coalesce(curr_temp_credit_limit,0) - coalesce(curr_temp_used_credit_limit,0) >= 200 then '可用额度充足且有在贷' end as tagg,     -- 剩余主额+剩余临额      在贷是where做了限制
    -- 主额的20%和在贷临额的最大值是此次临额最大值
  -- round(greatest(curr_main_credit_limit*0.2,coalesce(curr_temp_used_credit_limit,0))/50)*50 as temp_limit_issue_amount
  -- round(greatest(greatest(curr_main_credit_limit*0.3,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50 as temp_limit_issue_amount-- 如果这个值小于200 仍给200 30%
  -- round(greatest(greatest(curr_main_credit_limit*0.2,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50 as temp_limit_issue_amount-- 如果这个值小于200 仍给200  20%
round(greatest(greatest(curr_main_credit_limit*0.1,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50 as temp_limit_issue_amount-- 如果这个值小于200 仍给200 10%
-- round(greatest(greatest(curr_main_credit_limit*0.15,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50 as temp_limit_issue_amount-- 如果这个值小于200 仍给200 15%
  -- ,curr_credit_level
  -- ,curr_credit_level_version
from (
select *
from dws.dws_risk_stgy_apply_mid_tags 
) t0  --  存最新一天的切片数据(但也是T-1的数据   比如今天是5.14  这个数据是5.13下午6点左右更新的)
left join 
-- 取最新的用信临额发放日期
-- 用信确认临额调整临额(C010) :当用户用信时，触发用信临额决策流，用户确认使用临额后触发变更; ('C013','C015')  离线发临额
-- (select *
-- from (
-- select mid as mid1,
--   create_time as temp_limit_issue_date,
--   row_number() over(partition by mid order by create_time desc) as rn1
-- from ods_view_presto.s05_user_creditlimit_change_record
-- where limit_type = 'TEMP'
-- and change_event_type in ('C010','C013','C015')) tt0   
-- where rn1 = 1) t1 
-- on t0.mid = t1.mid1
-- 取最新的临额使用日期
(select *
from (
select  mid as mid1,create_time as temp_limit_issue_date,  -- 实际是使用时间这里为了保持表格一致性没改
row_number() over(partition by mid order by create_time desc) as rn1
from ods_view_presto.s05_user_creditlimit_used_detail
where change_action = 'FREEZE_LIMIT' and limit_type = 'TEMP'
) tt0   
where rn1 = 1) t1 
on t0.mid = t1.mid1
left join (
--- mid维度的结清期次数及结清订单数
select t0.mid as mid4
 ,count(distinct case when t1.state in (1,3,5) and fact_time < load_time then rid end) as repayment_clearing_count_index
 ,count(distinct case when t2.state in (1,2) and finish_time < load_time then camera_id end) as repayment_clearing_count
from dws.dws_risk_stgy_apply_mid_tags t0
left join (select customer_id,fact_time,rid,state
 from ods_view_presto.s02_loan_repayment) t1--根据历史订单biz_id取所有放款订单(期数维度)
on cast(t0.mid as bigint) = cast(t1.customer_id as bigint)
and t0.load_time > t1.fact_time -- 切片表加载时间时间 以防穿越
left join (select customer_id,finish_time,camera_id,state
from ods_view_presto.s02_loan) t2 --根据历史订单biz_id取所有放款订单(订单维度)
on cast(t0.mid as bigint) = cast(t2.customer_id as bigint)
and t0.load_time > t2.finish_time -- 切片表加载时间时间 以防穿越
group by 1) t4
on cast(t0.mid as varchar) = cast(t4.mid4 as varchar)
-- 取最新的老客V5_2主评级   切片表的数据有空值不太准确
left join 
(select mid as mid2,android_oldcust_maincreditlevel_charge_v5_3,
advance_duotou_cnt_x_19,
row_number() over (partition by mid order by createtime desc) as rn2 
from mx.android_oldcust_maincreditlevel_charge_v5_3_table) t2  -- T0 早上11点更新的数据
on t0.mid = t2.mid2 and t2.rn2 = 1
-- 为了取随机数
left join dwd.dwd_mem_info t3 
on t0.mid = t3.mid
-- 取最新的单日最大可借(固定额度)
-- left join (
--   select mid,daily_max_available_limit
--   from ods_view_presto.s05_user_credit_limit
--   where limit_type = 'MAIN') t4 
-- on t0.mid = t4.mid
-- 以下即发放人群  之前的版本
-- where id_curr_overdue_days <= 0 -- 当前未逾期
-- and t0.age <= 65 -- 年龄<=65
-- and id_30days_max_overdue_days <= 0 -- 近30天最大逾期天数<=0(即近30天无逾期记录)
-- -- and curr_main_available_limit < 200 --- 可用额度不足     (没做这个限制  限制了不利于追业绩)
where curr_ovd_cnt_this_app_group <= 0 -- 本包当前无逾期
and curr_ovd_cnt_other_app_group_90d <= 0 --- 他包近90天无逾期
and t0.age <= 65 --- 年龄<=65
and (id_30days_max_overdue_days <= 0 or id_30days_max_overdue_days is null)--- 近30天无逾期
and if_prohibit_apply = 0 --- 不在禁申期中
and curr_main_limit_expire_date > to_date(cast(current_date as varchar), 'yyyy-mm-dd') --- 主额度未过期
and app_group in ('Balam Plata','Tuna Cash','Mexcredo')
-- ,'Mikredi'
and onloan_cnt > 0 --- 有在贷 
and is_reloan_stgy = 1 --- 复贷客户
and (date_diff('day',temp_limit_issue_date,date(current_date)) >= 10 or temp_limit_issue_date is null) 
-- --- 距离上次临额使用时间>=10天 或者暂时未使用过临额   
 )

select *,
-- 用户今天总共能用的额度 = min(剩余主额, 每日限额) + 剩余临额(运营发营销话术需要用到)
  round(least(greatest(coalesce(curr_main_available_limit,0),0),daily_max_available_limit) + greatest(temp_limit_issue_amount - coalesce(curr_temp_used_credit_limit,0),0)) as total_available_limit
from t0 
-- 8月-9月初版本，提额比例加大（30%）；
-- where (android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 or  
-- android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and repayment_score+duotou_score>=-1)-- 30%
-- 8月-9月初版本，提额比例加大（15%）；
-- where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and  repayment_score+duotou_score<-1
-- or android_oldcust_maincreditlevel_charge_v5_3>=8 and android_oldcust_maincreditlevel_charge_v5_3<=10 and  repayment_score+duotou_score>=-1)-- 15%

-- 回滚至7月版本（9月9号开始复用）
-- where android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 and  repayment_score+duotou_score>=-1-- 30%
-- where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and repayment_score+duotou_score>=-1
-- or android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 and repayment_score+duotou_score<-1
-- ) -- 20%
where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and  repayment_score+duotou_score<-1
or android_oldcust_maincreditlevel_charge_v5_3>=8 and android_oldcust_maincreditlevel_charge_v5_3<=10 and  repayment_score+duotou_score>-1)-- 10%

-- where temp_limit_issue_amount >= 200 -- 发放临额要大于等于200
;

select temp_limit_tag,
-- data_date,
sum(temp_limit_issue_amount)/count(distinct mid)temp_amount_avg
,sum(curr_main_credit_limit)/count(distinct mid)main_amount_avg
,sum(total_available_limit)/count(distinct mid)total_amt_avg
,count(mid),count(distinct mid)
from mx.darren_temp_limit_base_table_261021_3
group by 1
order by 1


--- 给技术提供的代码   跑出数据导出csv给技术
select 
t0.mid,cust_id,tenant_id,double_loan
-- t0.*
,phone_number
  -- concat('{"temp_credit_amount_expired_day":"5","temp_credit_amount":',cast(t1.temp_limit_issue_amount as varchar),'}') as grantcredit_info
from (
select mid,
  cust_id,
  tenant_id,
  1 as double_loan
from ods.s05_creditx_order
where cast(mid as bigint) in (select mid 
from mx.darren_temp_limit_base_table_261021_1)
group by 1,2,3) t0 
left join (select mid,
  temp_limit_issue_amount,
  temp_limit_tag,phone_number
  from mx.darren_temp_limit_base_table_261021_1) t1 
on cast(t0.mid as bigint) = t1.mid
where temp_limit_tag in ('1021临额测试组_有在贷') ;
group by 1,2,3,4,5

 

SELECT temp_limit_tag
,sum(temp_limit_issue_amount)/count(mid)
,sum(curr_main_credit_limit)/count(mid)
,count(distinct mid)
from mx.darren_temp_limit_base_table_261021_1
group by 1




select temp_limit_tag,
data_date,
sum(temp_limit_issue_amount)/count(distinct mid)temp_amount_avg
,sum(curr_main_credit_limit)/count(distinct mid)main_amount_avg
,sum(total_available_limit)/count(distinct mid)total_amt_avg
,count(mid),count(distinct mid)
from mx.yuhan_temp_limit_base_table_his_20260924
where data_date>='20260920'
group by 1,2
order by 1,2


 

-- 确认离线临额是否落库
select count(distinct mid)
-- mid as mid11,change_total_grantamount as temp_limit_issue_amount_new,
--   row_number() over(partition by mid order by  desc) as rn11
from ods_view_presto.s05_user_creditlimit_change_record
where 
create_time>=cast('2026-10-13 20:00:00' as TIMESTAMP) 
-- and create_time<cast('2026-06-10 21:35:00' as TIMESTAMP) 
-- mid=1040160064242694
and limit_type = 'TEMP' and change_event_type in ('C015')

 


drop table if exists mx.yuhan_temp_limit_base_table;
CREATE TABLE mx.yuhan_temp_limit_base_table
WITH (
    format = 'ORC',
    partitioned_by = ARRAY['data_date']  
) 
AS
-- INSERT INTO mx.yuhan_temp_limit_base_table
SELECT 
 mid,
 identity_number,
 phone_number,
 app_group,
 new_media_source,
 first_apply_date,
 last_apply_date,
 first_loan_date,
 last_loan_date,
 last_repay_date,
 last_login_date,
 onloan_cnt,
 onloan_bal,
 curr_overdue_days,
 id_curr_overdue_days,
 max_overdue_days,
 id_30days_max_overdue_days,
 if_prohibit_apply,
 is_reloan_stgy,
 newcust_credit_limit,
 newcust_credit_level,
 newcust_credit_level_version,
--  以上数据从dws_risk_stgy_apply_mid_tags取的  dws_risk_stgy_apply_mid_tags是T-1的数据  不是实时数据
-- 将固额相关数据更新成盘古最新的数据
 m.total_grantamount as curr_main_credit_limit,
 m.used_grantamount as curr_main_used_credit_limit,
 m.total_grantamount - m.used_grantamount as curr_main_available_limit,
 m.expiring_time as curr_main_limit_expire_date,
 curr_credit_level,
 curr_credit_level_version,
 curr_temp_credit_limit,
 -- 将固额相关数据更新成盘古最新的数据
 t.used_grantamount as curr_temp_used_credit_limit,
--  指的是前一次临额的过期日(不是此次的)
 curr_temp_limit_expired_date,
 load_time,
 realname,
 sex,
 age,
 push_token,
 random_number,
 tenant_id,
 mid1,
 --  指的是前一次临额的发放日(不是此次的)   为了控制10天发放频率
 temp_limit_issue_date,
 rn1,
 mid2,
 android_oldcust_maincreditlevel_charge_v5_3,
 rn2,
--  mid as mid2,
--  curr_credit_level as android_oldcust_maincreditlevel_charge_v5_1,
--  rn1 as rn2,
 random_num,
  -- 将单日可借上限更新成盘古最新的数据
 m.daily_max_available_limit as daily_max_available_limit,
 case when temp_limit_tag='1021临额测试组_有在贷' then '1021临额测试组_有在贷_3' else null end as temp_limit_tag,  --  0513临额分了10% 20% 30%发放
-- case when temp_limit_tag='0701临额测试组_有在贷' then '0701临额测试组_有在贷_1' else null end as temp_limit_tag,  --  0513临额分了10% 20% 30%发放
-- temp_limit_tag,
 tagg,
-- 将临额发放金额更新成离线临额决策流跑出来的数据
 temp_limit_issue_amount_new as temp_limit_issue_amount,
--  total_available_limit
 round(least(greatest(coalesce(m.total_grantamount - m.used_grantamount,0),0),m.daily_max_available_limit) + greatest(temp_limit_issue_amount_new - coalesce(t.used_grantamount,0),0)) as total_available_limit
--  因为触发了决策流 实时的生产数据会更新所以不能直接用圈客群时的值 需要重新计算
, date_format(date_add('day', +0, DATE(now())), '%Y%m%d')AS data_date -- 0513/0514 是当天下午两点以后发的临额
-- select date_format(date_add('day',+1,DATE(now())), '%Y%m%d')
from mx.darren_temp_limit_base_table_261021_3 base 
left join  
(select *
from (
select mid as mid11,change_total_grantamount as temp_limit_issue_amount_new,
  row_number() over(partition by mid order by create_time desc) as rn11
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type = 'TEMP'
and change_event_type in ('C015')) tt0    -- C015是离线临额，C013是让系统帮忙刷数时使用
where rn11 = 1) t1 
on base.mid=t1.mid11
left JOIN
(select mid as mid22,
               total_grantamount,
               used_grantamount,
               date(expiring_time) as expiring_time,
               daily_max_available_limit
          from ods_view_presto.s05_user_credit_limit
         where limit_type = 'MAIN') m
on base.mid=m.mid22
left join (select mid as mid3,
                    total_grantamount,
                    used_grantamount,
                    date(expiring_time) as expiring_time
               from ods_view_presto.s05_user_credit_limit
              where limit_type = 'TEMP') t
on base.mid = t.mid3
-- where temp_limit_issue_amount_new>=200;




-- 看一下临额分布
select temp_limit_tag,
data_date,
sum(temp_limit_issue_amount)/count(distinct mid)temp_amount_avg
,sum(curr_main_credit_limit)/count(distinct mid)main_amount_avg
,sum(total_available_limit)/count(distinct mid)total_amt_avg
,count(mid),count(distinct mid)
from mx.yuhan_temp_limit_base_table 
-- where temp_limit_issue_amount>=200
group by 1,2
order by 1,2


-- 看一下临额分布
select temp_limit_tag,
data_date,
sum(temp_limit_issue_amount)/count(distinct mid)temp_amount_avg
,sum(curr_main_credit_limit)/count(distinct mid)main_amount_avg
,sum(total_available_limit)/count(distinct mid)total_amt_avg
,count(mid),count(distinct mid)
from mx.yuhan_temp_limit_base_table_his
where data_date>='20261021'
-- where temp_limit_issue_amount>=200
group by 1,2
order by 1,2
 


 
-- 看一下临额分布
select temp_limit_tag,
data_date,
sum(temp_limit_issue_amount)/count(distinct mid)temp_amount_avg
,sum(curr_main_credit_limit)/count(distinct mid)main_amount_avg
,sum(total_available_limit)/count(distinct mid)total_amt_avg
,count(mid),count(distinct mid)
from mx.yuhan_temp_limit_base_table_his_20260924
where data_date>='20261021'
-- where temp_limit_issue_amount>=200
group by 1,2
order by 1,2
 