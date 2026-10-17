-- 一、2026.4开始 每周三发一次临额   初期设置10%灰度不发 
-- 1、跑新表：mx.darren_temp_limit_base_table_26*    不能动老表darren_temp_limit_base_table_260310/260401/260408/260409/260415/260416  temp_limit_0310_tag改成对应日期
-- 2、跑给技术的数据导出表格给技术刷新表(需要验证)  此时用户只要到首页就会知道有临额
-- 3、给运营提供代码  运营营销告知用户临额 
-- 4、离线跑批流程:  上传名单(设置定时)+到时触发决策流(入参mid 出参临额+临额有效期)+更新额度表+通知运营
drop table if exists mx.darren_temp_limit_base_table_260826_3;
create table mx.darren_temp_limit_base_table_260826_3 as 
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
   case when from_base(substr(to_hex(sha256(to_utf8('20260422'||identity_number||app_group))),1,4),16)/65536.0000000000000000 >=0 then '0826临额测试组_有在贷' else '0826临额对照组_有在贷' end as temp_limit_tag, 
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
and (id_30days_max_overdue_days <= 2 or id_30days_max_overdue_days is null)--- 近30天无逾期
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
where (android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 or  
android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and repayment_score+duotou_score>=-1)-- 30%
-- where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and  repayment_score+duotou_score<-1
-- or android_oldcust_maincreditlevel_charge_v5_3>=8 and android_oldcust_maincreditlevel_charge_v5_3<=10 and  repayment_score+duotou_score>=-1)-- 15%

-- where temp_limit_issue_amount >= 200 -- 发放临额要大于等于200
;


select temp_limit_tag,
-- data_date,
sum(temp_limit_issue_amount)/count(distinct mid)temp_amount_avg
,sum(curr_main_credit_limit)/count(distinct mid)main_amount_avg
,sum(total_available_limit)/count(distinct mid)total_amt_avg
,count(mid),count(distinct mid)
from mx.darren_temp_limit_base_table_260701_2
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
from mx.darren_temp_limit_base_table_260826_3)
group by 1,2,3) t0 
left join (select mid,
  temp_limit_issue_amount,
  temp_limit_tag,phone_number
  from mx.darren_temp_limit_base_table_260826_3) t1 
on cast(t0.mid as bigint) = t1.mid
group by 1,2,3,4,5


-- 验证数据
select test.*
,credit.temp_credit_amount_expired_day 
,credit.total_grantamount
,credit.temp_credit_amount
,credit.total_grantamount-credit.temp_credit_amount as delt_check
from 
(
select 
mid
,cast(json_extract(grantcredit_info, '$.temp_credit_amount_expired_day') as double)temp_credit_amount_expired_day
,cast(json_extract(grantcredit_info, '$.temp_credit_amount') as double)temp_credit_amount
 from mx.temp_test_0401
 where mid='1040160059308691'
 limit 10 )test
 left join 
 (
select mid,limit_type,total_grantamount,used_grantamount,update_time
,cast(mid as varchar)
,cast(json_extract(grantcredit_info, '$.temp_credit_amount_expired_day') as double)temp_credit_amount_expired_day
,cast(json_extract(grantcredit_info, '$.temp_credit_amount') as double)temp_credit_amount
from ods_view_presto.s05_user_credit_limit
where create_time>=cast('2026-03-30' as TIMESTAMP)
and limit_type='TEMP'
-- limit 10
-- and grantcredit_info like '%temp_credit_amount%'
)credit
on test.mid=cast(credit.mid as varchar)


SELECT temp_limit_tag
,sum(temp_limit_issue_amount)/count(mid)
,sum(curr_main_credit_limit)/count(mid)
,count(distinct mid)
from mx.yuhan_temp_disc_base_table_260618_2
group by 1







--------------------------------------------------------------------------
-- 四、周四对无在贷发临额   40%临额+40%减息(后收5%)+20%对照
drop table if exists mx.yuhan_temp_disc_base_table_260903_1;
create table mx.yuhan_temp_disc_base_table_260903_1 as 
with t0 as (
--- 留20%灰度不发 本次有效期3天 从0423开始有效期改为5天
select t0.*,
  t1.*,    
  t2.*,
  t3.random_no as random_num, --随机数
  t4.*,
  case when repayment_clearing_count<=2 then -2 else 2 end as repayment_score,
  case when (advance_duotou_cnt_x_19<=1  or advance_duotou_cnt_x_19>=5) then -1 else 1 end as duotou_score,
  -- t4.daily_max_available_limit, -- 最新的单日最大可借(固定额度)
  -- case when random() < 0.4 then '临额测试组' when random() < 0.8 then '减息测试组' else '对照组' end as temp_limit_0416_tag_, 
    -- case when from_base(substr(to_hex(sha256(to_utf8('20260423'||identity_number||app_group))),1,4),16)/65536.0000000000000000 < 0.4 then '0423临额测试组_无在贷'
    --    when from_base(substr(to_hex(sha256(to_utf8('20260423'||identity_number||app_group))),1,4),16)/65536.0000000000000000 < 0.8 then '0423减息测试组_无在贷'
    --    else '0423临额减息对照组_无在贷' end as temp_limit_tag,     
    case when from_base(substr(to_hex(sha256(to_utf8('20260430'||identity_number||app_group))),1,4),16)/65536.0000000000000000 < 0.4 then '0903临额测试组_无在贷'
       when from_base(substr(to_hex(sha256(to_utf8('20260430'||identity_number||app_group))),1,4),16)/65536.0000000000000000 < 0.8 then '0903减息测试组_无在贷'
       else '0903临额减息测试组_无在贷' end as temp_limit_tag,  
  case when curr_main_available_limit + coalesce(curr_temp_credit_limit,0) - coalesce(curr_temp_used_credit_limit,0) < 200 then '可用额度不足'
    when curr_main_available_limit + coalesce(curr_temp_credit_limit,0) - coalesce(curr_temp_used_credit_limit,0) >= 200 then '可用额度充足' end as tagg,     -- 剩余主额+剩余临额   
      -- round(greatest(greatest(curr_main_credit_limit*0.3,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50   as temp_limit_issue_amount
       round(greatest(greatest(curr_main_credit_limit*0.15,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50   as temp_limit_issue_amount
  -- round(greatest(greatest(curr_main_credit_limit*0.2,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50   as temp_limit_issue_amount
  -- round(greatest(greatest(curr_main_credit_limit*0.1,coalesce(curr_temp_used_credit_limit,0)),200)/50)*50   as temp_limit_issue_amount
  -- round(greatest(greatest(curr_main_credit_limit*0.1,coalesce(curr_temp_used_credit_limit,0)))/50)*50 as temp_limit_issue_amount
from (
select *
from dws.dws_risk_stgy_apply_mid_tags) t0  --  存最新一天的切片数据
left join 
-- 取最新的用信临额发放日期
-- 用信确认临额调整临额  当用户用信时，触发用信临额决策流，用户确认使用临额后触发变更
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
(select *
from (
select  mid as mid1,create_time as temp_limit_issue_date,  -- 实际是使用时间这里为了保持表格一致性没改
row_number() over(partition by mid order by create_time desc) as rn1
from ods_view_presto.s05_user_creditlimit_used_detail
where change_action = 'FREEZE_LIMIT' and limit_type = 'TEMP'
) tt0   
where rn1 = 1) t1 
on t0.mid = t1.mid1
-- left join 
-- -- 取最新的老客V5_2主评级
-- (select mid as mid2,android_oldcust_maincreditlevel_charge_v5_2,
-- advance_duotou_cnt_x_19,
-- row_number() over (partition by mid order by createtime desc) as rn2 
-- from mx.android_oldcust_main_creditlevel_charge_v5_2_param_table) t2 
-- on t0.mid = t2.mid2 and t2.rn2 = 1
left join 
(select mid as mid2,android_oldcust_maincreditlevel_charge_v5_3,
advance_duotou_cnt_x_19,
row_number() over (partition by mid order by createtime desc) as rn2 
from mx.android_oldcust_maincreditlevel_charge_v5_3_table) t2  -- T0 早上11点更新的数据
on t0.mid = t2.mid2 and t2.rn2 = 1
-- 为了取随机数
left join dwd.dwd_mem_info t3 
on t0.mid = t3.mid
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
-- 取最新的单日最大可借(固定额度)
-- left join (
--   select mid,daily_max_available_limit
--   from ods_view_presto.s05_user_credit_limit
--   where limit_type = 'MAIN') t4 
-- on t0.mid = t4.mid
-- 以下即发放人群
-- where id_curr_overdue_days <= 0 -- 当前未逾期
-- and id_30days_max_overdue_days <= 0 -- 近30天最大逾期天数<=0(即近30天无逾期记录)
-- -- and curr_main_available_limit < 200 --- 可用额度不足     (没做这个限制  限制了不利于追业绩)
-- -- and (date_diff('day',temp_limit_issue_date,date(current_date)) >= 8 or temp_limit_issue_date is null) 
-- --- 距离上次发放临额间隔>=10天 或者暂时未发过临额
-- -- and curr_credit_level<=11
where curr_ovd_cnt_this_app_group <= 0 -- 本包当前无逾期
and curr_ovd_cnt_other_app_group_90d <= 0 --- 他包近90天无逾期
-- and curr_ovd_cnt_other_app_group > 0 --- 他包有在逾
and t0.age <= 65 --- 年龄<=65
and (id_30days_max_overdue_days <= 2 or id_30days_max_overdue_days is null)--- 近30天无逾期
and if_prohibit_apply = 0 -- 不处于禁言期内 
and curr_main_limit_expire_date > to_date(cast(current_date as varchar), 'yyyy-mm-dd') --- 主额度未过期
and app_group in ('Balam Plata','Tuna Cash','Mexcredo')
and onloan_cnt = 0 --- 无在贷 
and is_reloan_stgy = 1 --- 复贷客户
-- and (date_diff('day',temp_limit_issue_date,date(current_date)) >= 10 or temp_limit_issue_date is null) 
) -- 10%

select *,
-- 用户今天总共能用的额度 = min(剩余主额, 每日限额) + 剩余临额(运营发营销话术需要用到)
  round(least(greatest(coalesce(curr_main_available_limit,0),0),daily_max_available_limit) + greatest(temp_limit_issue_amount - coalesce(curr_temp_used_credit_limit,0),0)) as total_available_limit
from t0 
-- where (android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 or  
-- android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and repayment_score+duotou_score>=-1)-- 30%
where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and  repayment_score+duotou_score<-1
or android_oldcust_maincreditlevel_charge_v5_3>=8 and android_oldcust_maincreditlevel_charge_v5_3<=10 and  repayment_score+duotou_score>=-1)-- 15%

-- where android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 and  repayment_score+duotou_score>=-1-- 30%
-- where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and repayment_score+duotou_score>=-1
-- or android_oldcust_maincreditlevel_charge_v5_3>=1 and android_oldcust_maincreditlevel_charge_v5_3<=2 and repayment_score+duotou_score<-1
-- ) -- 20%
-- where (android_oldcust_maincreditlevel_charge_v5_3>=3 and android_oldcust_maincreditlevel_charge_v5_3<=7 and  repayment_score+duotou_score<-1
-- or android_oldcust_maincreditlevel_charge_v5_3>=8 and android_oldcust_maincreditlevel_charge_v5_3<=10 and  repayment_score+duotou_score>-1)-- 10%
-- where temp_limit_issue_amount >= 200 -- 发放临额要大于等于200
;

--- 给技术提供的代码   跑出数据导出csv给技术
select t0.*,phone_number
  -- concat('{"temp_credit_amount_expired_day":"3","temp_credit_amount":',cast(t1.temp_limit_issue_amount as varchar),'}') as grantcredit_info
from (
select mid,
  cust_id,
  tenant_id,
  1 as double_loan
from ods.s05_creditx_order
where cast(mid as bigint) in (select mid 
from mx.yuhan_temp_disc_base_table_260903_1)
group by 1,2,3) t0 
left join (select mid,
  temp_limit_issue_amount,
  temp_limit_tag,phone_number
  from mx.yuhan_temp_disc_base_table_260903_1) t1 
on cast(t0.mid as bigint) = t1.mid
where temp_limit_tag in ('0903临额测试组_无在贷','0903临额减息测试组_无在贷') ;

-- 临额只有这两个圈选；另一个减息不需要


-- 运营代码
select mid,
  phone_number,
  realname,
  case when sex = '男' then 'male' else 'female' end as gender,
  random_num,
  temp_limit_tag,
  total_available_limit,  -- 用户今天总共能用的额度
  tagg,-- 客群标签
  temp_limit_issue_amount,-- 临额金额
  app_group,
  push_token -- 运营加的要用
from mx.yuhan_temp_limit_base_table
where total_available_limit>=200 
and  temp_limit_tag is not null;
-- 临额有效期5天   减息券有效期5天
select temp_limit_tag,count(mid),count(distinct mid)
,sum(temp_limit_issue_amount)/count(distinct mid)temp_amount_avg
,sum(curr_main_credit_limit)/count(distinct mid)main_amount_avg
,sum(total_available_limit)/count(distinct mid)total_amt_avg from mx.yuhan_temp_limit_base_table group by 1
-- mx.darren_temp_limit_base_table_26*圈选客群 导出数据到excel表格去营销系统触发临额决策流发临额落库  大概等两个小时 可以刷新这个表的数据


-- 临额切片表 只有最新数据    
-- 一、针对有在贷客群的代码


drop table if exists mx.yuhan_temp_limit_base_table;
CREATE TABLE mx.yuhan_temp_limit_base_table
WITH (
    format = 'ORC',
    partitioned_by = ARRAY['data_date']  
) 
AS
INSERT INTO mx.yuhan_temp_limit_base_table
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
 case when temp_limit_tag='0909临额测试组_有在贷' then '0909临额测试组_有在贷_3' else null end as temp_limit_tag,  --  0513临额分了10% 20% 30%发放
-- case when temp_limit_tag='0701临额测试组_有在贷' then '0701临额测试组_有在贷_1' else null end as temp_limit_tag,  --  0513临额分了10% 20% 30%发放
-- temp_limit_tag,
 tagg,
-- 将临额发放金额更新成离线临额决策流跑出来的数据
 temp_limit_issue_amount_new as temp_limit_issue_amount,
--  total_available_limit
 round(least(greatest(coalesce(m.total_grantamount - m.used_grantamount,0),0),m.daily_max_available_limit) + greatest(temp_limit_issue_amount_new - coalesce(t.used_grantamount,0),0)) as total_available_limit
--  因为触发了决策流 实时的生产数据会更新所以不能直接用圈客群时的值 需要重新计算
, date_format(date_add('day',+0,DATE(now())), '%Y%m%d')AS data_date -- 0513/0514 是当天下午两点以后发的临额
-- select date_format(date_add('day',+1,DATE(now())), '%Y%m%d')
from mx.darren_temp_limit_base_table_260909_3 base 
left join  
(select *
from (
select mid as mid11,change_total_grantamount as temp_limit_issue_amount_new,
  row_number() over(partition by mid order by create_time desc) as rn11
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type = 'TEMP'
and change_event_type in ('C015')) tt0   -- 10%和20%发放的临额是C013需要改；30%不用改就是C015%
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



-- 二、0423对无在贷人群的临额：
-- 1、需要先插入没发临额的部分（不用更新数据）  
drop table if exists mx.yuhan_temp_limit_base_table;
CREATE TABLE mx.yuhan_temp_limit_base_table 
WITH (
    format = 'ORC',
    partitioned_by = ARRAY['data_date']  
) 
AS
INSERT INTO mx.yuhan_temp_limit_base_table
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
 curr_main_credit_limit,
 curr_main_used_credit_limit,
 curr_main_available_limit,
 curr_main_limit_expire_date,
 curr_credit_level,
 curr_credit_level_version,
 curr_temp_credit_limit,
 curr_temp_used_credit_limit,
 curr_temp_limit_expired_date,
 load_time,
 realname,
 sex,
 age,
 push_token,
 random_number,
 tenant_id,
 mid1,
 temp_limit_issue_date,
 rn1,
 mid2,
 android_oldcust_maincreditlevel_charge_v5_3,
 rn2,
 random_num,
 daily_max_available_limit,
 temp_limit_tag,
--  case when temp_limit_tag='0604减息测试组_无在贷' then '0604减息测试组_无在贷_1' else null end as temp_limit_tag, 
 tagg,
 temp_limit_issue_amount,
 total_available_limit,
-- , date_format(date_add('day',+1,DATE(now())), '%Y%m%d')AS data_date 
 date_format(date_add('day',+1,DATE(now())), '%Y%m%d')AS data_date 
from mx.yuhan_temp_disc_base_table_260903_1
where temp_limit_tag in ('0903减息测试组_无在贷');
-- and temp_limit_issue_amount >= 200;


-- 2、再插入发临额的测试组数据（需要更新数据）
drop table if exists mx.yuhan_temp_limit_base_table;
CREATE TABLE mx.yuhan_temp_limit_base_table 
WITH (
    format = 'ORC',
    partitioned_by = ARRAY['data_date']  
) 
as
INSERT INTO mx.yuhan_temp_limit_base_table
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
 m.total_grantamount as curr_main_credit_limit,
 m.used_grantamount as curr_main_used_credit_limit,
 m.total_grantamount - m.used_grantamount as curr_main_available_limit,
 m.expiring_time as curr_main_limit_expire_date,
 curr_credit_level,
 curr_credit_level_version,
 curr_temp_credit_limit,
 t.used_grantamount as curr_temp_used_credit_limit,
 curr_temp_limit_expired_date,
 load_time,
 realname,
 sex,
 age,
 push_token,
 random_number,
 tenant_id,
 mid1,
 temp_limit_issue_date,
 rn1,
 mid2,
 android_oldcust_maincreditlevel_charge_v5_3,
 rn2,
 random_num,
 m.daily_max_available_limit as daily_max_available_limit,
 temp_limit_tag,
--  case when temp_limit_tag='0528临额测试组_无在贷'   then '0528临额测试组_无在贷_2' 
--       when temp_limit_tag='0528临额减息测试组_无在贷'  then '0528临额减息测试组_无在贷_2' else null end as temp_limit_tag, 
 tagg,
 temp_limit_issue_amount_new as temp_limit_issue_amount,
--  total_available_limit
 round(least(greatest(coalesce(m.total_grantamount - m.used_grantamount,0),0),m.daily_max_available_limit) + greatest(temp_limit_issue_amount_new - coalesce(t.used_grantamount,0),0)) as total_available_limit
, date_format(date_add('day',+1,DATE(now())), '%Y%m%d') AS data_date 
from mx.yuhan_temp_disc_base_table_260903_1 base 
left join  
(select *
from (
select mid as mid11,change_total_grantamount as temp_limit_issue_amount_new,
  row_number() over(partition by mid order by create_time desc) as rn11
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type = 'TEMP'
and change_event_type in ('C015')) tt0   
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
-- where temp_limit_issue_amount_new>=200
where temp_limit_tag in ('0903临额测试组_无在贷','0903临额减息测试组_无在贷');



-- 看一下临额分布
select temp_limit_tag,
data_date,
sum(temp_limit_issue_amount)/count(distinct mid)temp_amount_avg
,sum(curr_main_credit_limit)/count(distinct mid)main_amount_avg
,sum(total_available_limit)/count(distinct mid)total_amt_avg
,count(mid),count(distinct mid)
from mx.yuhan_temp_limit_base_table_his
-- where temp_limit_issue_amount>=200
group by 1,2
order by 1,2

select data_date,
sum(temp_limit_issue_amount)/count(distinct mid)temp_amount_avg
,sum(curr_main_credit_limit)/count(distinct mid)main_amount_avg
,sum(total_available_limit)/count(distinct mid)total_amt_avg
,count(mid),count(distinct mid)
from mx.yuhan_temp_limit_base_table_his
group by 1 order by 1


delete from mx.yuhan_temp_limit_base_table_his where data_date='20260624';
ALTER TABLE mx.report_application_funnel DROP PARTITION (dt='2026-05-27');

-- 临额历史切片表
DROP TABLE IF EXISTS mx.yuhan_temp_limit_base_table_his;
CREATE TABLE mx.yuhan_temp_limit_base_table_his (
  mid bigint,
  identity_number varchar,           -- string → varchar
  phone_number varchar,              -- string → varchar
  app_group varchar,                 -- string → varchar
  new_media_source varchar,          -- string → varchar
  first_apply_date date,
  last_apply_date date,
  first_loan_date date,
  last_loan_date date,
  last_repay_date date,
  last_login_date date,
  onloan_cnt bigint,
  onloan_bal decimal(38,6),
  curr_overdue_days bigint,
  id_curr_overdue_days bigint,
  max_overdue_days bigint,
  id_30days_max_overdue_days bigint,
  if_prohibit_apply int,
  is_reloan_stgy int,
  newcust_credit_limit decimal(38,6),
  newcust_credit_level double,
  newcust_credit_level_version varchar,   -- string → varchar
  curr_main_credit_limit decimal(38,6),
  curr_main_used_credit_limit decimal(38,6),
  curr_main_available_limit decimal(38,6),
  curr_main_limit_expire_date date,
  curr_credit_level double,
  curr_credit_level_version varchar,      -- string → varchar
  curr_temp_credit_limit decimal(38,6),
  curr_temp_used_credit_limit decimal(38,6),
  curr_temp_limit_expired_date date,
  load_time timestamp,
  realname varchar,                       -- string → varchar
  sex varchar,                            -- string → varchar
  age bigint,
  push_token varchar,                     -- string → varchar
  random_number varchar,                  -- string → varchar
  tenant_id decimal(38,6),
  mid1 bigint,
  temp_limit_issue_date timestamp,
  rn1 bigint,
  mid2 bigint,
  -- android_oldcust_maincreditlevel_charge_v5_1 double,
  android_oldcust_maincreditlevel_charge_v5_1 double,
  rn2 bigint,
  random_num varchar,                     -- string → varchar
  daily_max_available_limit decimal(38,6),
  temp_limit_tag varchar(50),
  tagg varchar(50),
  temp_limit_issue_amount decimal(38,6),
  total_available_limit decimal(38,6),
  data_date varchar
)
WITH (
  format = 'ORC',
  partitioned_by = ARRAY['data_date']
);


-- 0422发放临额因为切片表被删了所以需要重新回溯
INSERT INTO mx.yuhan_temp_limit_base_table_his
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
 m.total_grantamount as curr_main_credit_limit,
 m.used_grantamount as curr_main_used_credit_limit,
 m.total_grantamount - m.used_grantamount as curr_main_available_limit,
 m.expiring_time as curr_main_limit_expire_date,
 curr_credit_level,
 curr_credit_level_version,
 curr_temp_credit_limit,
 t.used_grantamount as curr_temp_used_credit_limit,
 curr_temp_limit_expired_date,
 load_time,
 realname,
 sex,
 age,
 push_token,
 random_number,
 tenant_id,
 mid1,
 temp_limit_issue_date,
 rn1,
 mid2,
 android_oldcust_maincreditlevel_charge_v5_1,
 rn2,
 random_num,
 m1.daily_max_available_limit as daily_max_available_limit,
 case when temp_limit_tag='0422临额测试组' then '0422临额测试组_有在贷' else null end as temp_limit_tag,
 tagg,
 temp_limit_issue_amount_new as temp_limit_issue_amount,
 base1.total_available_limit as total_available_limit
--  round(least(greatest(coalesce(m.total_grantamount - m.used_grantamount,0),0),m1.daily_max_available_limit) + greatest(temp_limit_issue_amount_new - coalesce(t.used_grantamount,0))) as total_available_limit
, '20260422' AS data_date 
from mx.darren_temp_limit_base_table_260422 base 
join (select mid as mid_223,total_available_limit from mx.old_on_loan_user_mkt_semi_monthly)  base1
on base.mid=base1.mid_223
left join  
-- 取刷额后的最新临额
(select *
from (
select mid as mid11,change_total_grantamount as temp_limit_issue_amount_new,
  row_number() over(partition by mid order by create_time desc) as rn11
from ods.s05_user_creditlimit_change_record
where limit_type = 'TEMP'
and change_event_type in ('C015')) tt0   
where rn11 = 1) t1 
on base.mid=t1.mid11
left JOIN
-- 取刷额前的固定额度剩余额度
(select *
from 
(
 select mid as mid22,
               change_total_grantamount as total_grantamount,
               change_used_grantamount as used_grantamount,
               date(expiring_time) as expiring_time,
               row_number() over(partition by mid order by create_time desc) as rn111
          from ods.s05_user_creditlimit_change_record
         where limit_type = 'MAIN' and update_time<cast('2026-04-22 00:03:05.658' as TIMESTAMP)  
         
)bb
where rn111=1
) m
on base.mid=m.mid22
-- 取刷额前的占用临额
left join (
select *
from 
(
select mid as mid3,
                    change_total_grantamount as total_grantamount,
                    change_used_grantamount as used_grantamount,
                    date(expiring_time) as expiring_time,
                    row_number() over(partition by mid order by create_time desc) as rn112
               from ods.s05_user_creditlimit_change_record
              --  ods_view_presto
              where limit_type = 'TEMP' and update_time<cast('2026-04-21 21:00:00.670' as TIMESTAMP) 
)
where rn112=1
) t
on base.mid = t.mid3
left JOIN
-- 取刷额前的固定额度单日可借最大上限
(select *
from 
(
 select mid as mid223,
               change_daily_max_available_limit as daily_max_available_limit,
               row_number() over(partition by mid order by create_time desc) as rn1113
          from ods.s05_user_creditlimit_change_record
         where limit_type = 'MAIN' and update_time<cast('2026-04-22 00:03:05.658' as TIMESTAMP)  
         and change_event_type in ('C009','C002','C005','C001','C010')
)bb
where rn1113=1
) m1
on base.mid=m1.mid223
where temp_limit_issue_amount_new>=200;

-- 直接插入0423无在贷临额
INSERT INTO mx.yuhan_temp_limit_base_table_his
SELECT * from mx.yuhan_temp_limit_base_table
 where temp_limit_tag is not null;
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
 curr_main_credit_limit,
 curr_main_used_credit_limit,
 curr_main_available_limit,
 curr_main_limit_expire_date,
 curr_credit_level,
 curr_credit_level_version,
 curr_temp_credit_limit,
 curr_temp_used_credit_limit,
 curr_temp_limit_expired_date,
 load_time,
 realname,
 sex,
 age,
 push_token,
 random_number,
 tenant_id,
 mid1,
 temp_limit_issue_date,
 rn1,
 cast(mid2 as bigint) mid2,
 cast(android_oldcust_maincreditlevel_charge_v5_1 as double)android_oldcust_maincreditlevel_charge_v5_1,
 cast(rn2 as bigint)rn2,
 random_num,
 daily_max_available_limit,
 cast(temp_limit_tag as varchar(50))temp_limit_tag,
 cast(tagg as varchar(50) )tagg,
 temp_limit_issue_amount,
 cast(total_available_limit as decimal(38,6))total_available_limit,
 data_date
from mx.yuhan_temp_limit_base_table;



-- 其他参数尝试
-- select '$etl_date'
-- set $base_date=date_add('day',+2,${yyMMdd})
-- SET base_date=${yyMMdd};
-- SET hivevar:new_date=date_format(date_add(date_parse(${hivevar:base_date}, '%y%m%d'), 2), '%y%m%d');
-- drop table if exists mx.darren_temp_limit_base_table_${yyMMdd};
-- create table mx.darren_temp_limit_base_table_${yyMMdd} as

select 
last_credit_amount,count(1)
from 
(
select biz_id,
  mid,
  date_add('hour',-6,createtime) dt,
  max(try_cast(json_extract_scalar(inputdata,'$.last_used_temp_credit_amount') as double)) last_used_temp_credit_amount,
  max(try_cast(json_extract_scalar(inputdata,'$.last_credit_amount') as double)) last_credit_amount,
  etl_date
from ods.s21_risk_model_record
where modelid in (4719)
and productid in (509) and etl_date >= '20260428' and strategytype = 'CHAMPION' and createtime >= cast('2026-04-22 00:00:00.000' as timestamp)
-- and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
-- and strategytype = 'CHAMPION'
group by 1,2,3,etl_date
)base 
group by 1;

-- 离线临额决策流调用记录
select
-- a.mid
count(distinct a.mid),
count(distinct base.mid),
count(distinct case when temp_credit_amount>=200 then base.mid else null end)
from mx.darren_temp_limit_base_table_260520_4 a
left join
(
select 
        externalid,
        mid, 
        biz_id,
        cast(json_extract_scalar(outputdata, '$.temp_credit_amount') as double) as temp_credit_amount,
        cast(json_extract_scalar(outputdata, '$.temp_credit_amount_expired_day') as varchar) as temp_credit_amount_expired_day
      from ods.s21_risk_strategy_record
      where productid in (509) and etl_date >= '20260519' and strategytype = 'CHAMPION' and createtime >= cast('2026-05-19 00:00:00' as timestamp)
)base 
on a.mid= base.mid
-- where temp_limit_tag in ('0521临额测试组_无在贷','0521临额减息测试组_无在贷')
-- where (base.temp_credit_amount is null or base.temp_credit_amount<200)  and temp_limit_tag in ('0521临额测试组_无在贷','0521临额减息测试组_无在贷')
group by 1

select count(distinct mid)
-- mid as mid11,change_total_grantamount as temp_limit_issue_amount_new,
--   row_number() over(partition by mid order by  desc) as rn11
from ods_view_presto.s05_user_creditlimit_change_record
where 
create_time>=cast('2026-08-26 20:00:00' as TIMESTAMP) 
-- and create_time<cast('2026-06-10 21:35:00' as TIMESTAMP) 
-- mid=1040160064242694
and limit_type = 'TEMP' and change_event_type in ('C015')
order by create_time desc

select now()
select *
from ods_view_presto.s05_user_creditlimit_change_record
where mid=1040160067955969
order by create_time desc

select * 
from mx.darren_temp_limit_base_table_260624_2
where mid=1040160067955969



-- 决策流输出total_available_limit验证
select 
case when base.total_available_limit=flow.total_available_limit then 1 else 0 end as flag
-- base.total_available_limit,flow.total_available_limit as "决策流输出"
,count(1)
from 
(
select mid,cast(total_available_limit as double) total_available_limit, curr_main_credit_limit,curr_main_used_credit_limit,
curr_main_available_limit,daily_max_available_limit,temp_limit_issue_amount,curr_temp_used_credit_limit
from mx.yuhan_temp_disc_base_table_260514
where temp_limit_tag in ('0514临额测试组_无在贷','0514临额减息测试组_无在贷')
)base 
left join 
(
select externalid,
  mid as mid_t2,
  cast(json_extract_scalar(outputdata, '$.total_available_limit') as double) as total_available_limit,
  createtime,
  etl_date
from ods.s21_risk_model_record
where modelid =4761 
  and strategytype = 'SHADOW'
  and etl_date >= to_char(date_add('day', -2, current_date), 'yyyymmdd')
  and createtime >= cast('2026-05-13 22:00:00' as timestamp)
)flow 
on base.mid=flow.mid_t2
group by 1

-- 额度变更记录表离线临额记录
select count(distinct mid) 
from ods_view_presto.s05_user_creditlimit_change_record
where change_event_type='C015'  and create_time >= cast('2026-05-06 20:00:00.434' as timestamp)
where mid=1040160062705405
order by create_time desc






-- 临额检查相关
select biz_id,temp_grant_amount
-- temp_limit_0401_tag,if_fu_sx_refuse_passed,sum(curr_main_credit_limit_0401)/count(biz_id),sum(global_limit)/count(biz_id)
from mx.yj_test_table_250225 a 
where app_date>=date'2026-04-01'  and if_fu_sx_refuse_passed=1
and temp_limit_0401_tag='0401临额对照组'  and temp_grant_amount>0
group by 1,2
order by 1,2

and if_fu_sx_refuse_passed is null
and temp_limit_0401_tag='0401临额测试组'  

select temp_limit_0401_tag,temp_limit_0408_tag,
case when app_date>=date'2026-04-07' then 1 else 0 end as flag
,count(distinct mid)
,sum(case when if_issue=1 then contract_amount else null end) as amount
-- temp_limit_0401_tag,if_fu_sx_refuse_passed,sum(curr_main_credit_limit_0401)/count(biz_id),sum(global_limit)/count(biz_id)
from mx.yj_test_table_250225 a 
where app_date>=date'2026-03-31' 
--  and if_fu_sx_refuse_passed=1
-- and temp_limit_0401_tag='0401临额对照组'  and temp_grant_amount>0
group by 1,2,3
order by 1,2,3


select 
list_peo_0408
,count(distinct mid)
from mx.yj_test_table_250225 a 
where temp_limit_0408_tag ='0408临额对照组'
group by 1
order by 1


select a.temp_limit_0408_tag,a.tagg_0408
,count(distinct b.mid) cnt_peo
,count(distinct a.mid)
from mx.yj_test_table_250225 a 
left join 
(
select temp_limit_0408_tag,tagg,mid
-- ,count(mid) as cnt_peo
from mx.darren_temp_limit_base_table_260408
-- group by 1
)b 
on a.temp_limit_0408_tag=b.temp_limit_0408_tag and  a.tagg_0408=b.tagg
group by 1,2
order by 1,2


SELECT * FROM ods_view_presto.s05_creditx_order 
-- WHERE DATE(CREATE_TIME) >= date_add('day',-10,DATE(now()))
where biz_id='1620000407231219' 
-- 临额为0  对照组审核失败没放款1620000404242594 
limit 10

  select *
  -- mid,change_total_grantamount,change_used_grantamount,create_time as settle_time,limit_type,change_event_type
  -- ,row_number() over (partition by mid order by create_time) as rn
from ods_view_presto.s05_user_creditlimit_change_record
where
-- change_event_type in ('C010','C013','C002')
mid=1040160060624213
order by create_time
where create_time>=cast('2026-03-30' as TIMESTAMP)

SELECT * , '20260401' AS data_date from mx.darren_temp_limit_base_table_260401
where mid=1040160060624213;

SELECT * , '20260408' AS data_date from mx.darren_temp_limit_base_table_260408
where mid=1040160060624213;

select  date_add('day', +5, date'2026-04-07') 

select *
-- mid,change_total_grantamount,change_used_grantamount,create_time as settle_time,limit_type
--   row_number() over (partition by mid order by create_time) as rn
-- from ods_view_presto.s05_user_creditlimit_change_record
from ods_view_presto.s05_user_credit_limit
where
-- change_event_type in ('C010','C013','C002')
mid=1040160062598706
-- mid=1040160060642311
order by create_time desc
where create_time>=cast('2026-03-30' as TIMESTAMP)

select *
from ods_view_presto.s09_os_credit_snapshot

select *
from ods_view_presto.s05_creditx_order
-- where status = 372  -- 代表放款成功 
where mid='1040160048975370'

select * 
from ods_view_presto.s02_loan limit 1
