
--:{author=tudalun, department=墨西哥风险策略, dagName=yj_reloan_prof_create, taskName=yj_reloan_prof}
-- 删除目标分区中前一天及之后的数据（保证幂等性）
delete from mx.tmp_advance_table
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
;
--:{author=tudalun, department=墨西哥风险策略, dagName=yj_reloan_prof_create, taskName=yj_reloan_prof}
-- 插入当天符合条件的数据（从源表提取 advance 多头指标）
insert into mx.tmp_advance_table
select externalid,
  max(cast(json_extract_scalar(inputdata, '$.advance_gd_x_19') as double)) as gd_x_19,
  max(cast(json_extract_scalar(inputdata, '$.advance_gd_x_21') as double)) as gd_x_21,
  etl_date
from (
  select biz_id,externalid, inputdata, etl_date
  from ods.s21_risk_model_record
  where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
    and modelid = 2025     
    and strategytype = 'CHAMPION'
) t0
group by 1, 4
;
--:{author=tudalun, department=墨西哥风险策略, dagName=yj_reloan_prof_create, taskName=yj_reloan_prof}
-- 按 externalid 和 etl_date 分组



drop table if EXISTS mx.yj_reloan_prof
;
--:{author=tudalun, department=墨西哥风险策略, dagName=yj_reloan_prof_create, taskName=yj_reloan_prof}
CREATE table  mx.yj_reloan_prof as
 select
 a.biz_id-- 申请量
 -- by month
 ,substr(cast(current_timestamp as varchar),1,24) as update_time 
,
a.credit_no
,
a.app_time
,
a.tenant
,
a.source
,
 date_trunc('month',date(a.create_time)) as monthh
 --- 基础信息
 ,
 case when degree<0 then null else degree end as degree
 ,
 case when income<0 then null else income end as income
 ,
 case when age<0 then null else age end as age
 ,
  case when degree>=5 then '3_[5,inf]' when degree>=3 then '2_[3,4)' else '1_[inf,3)' end as degree_flag
  ,
  case when income>=8 then '3_[8,inf]' when income>=5 then '2_[5,8)' when income>=0 then '1_[0,5)' else '0_-1' end as income_flag
  ,
  case when age>=54 then '3_[54,inf]' when age>=38 then '2_[38,54)'  else '1_[inf,38)' end as age_flag
,-- advance近30天多头
case when c.externalid is not null and GD_X_19 is null then null else GD_X_19 end as GD_X_19
,-- advance近730天多头
case when c.externalid is not null and GD_X_21 is null then null else GD_X_21 end as GD_X_21
,-- 提取白户
case when c.externalid is not null then case when GD_X_19 is null and GD_X_21 is null then 1 when GD_X_21=1 or (GD_X_21=2 and GD_X_19 !=1) then 1 else 0 end end as adv_fenzu
-- 通过率
,a.if_in_sx
,a.if_sx_passed
,a.if_in_fu_anti_fraud
,a.if_fu_external_data_passed
-- 授信额度
,a.grantcredit_7d_amount
--24小时用信率
,a.if_in_sx_24h
,a.if_sx_passed_24h
-- 逾期出账
,a.t0_overdue_amount_1
,a.t3_overdue_amount_1
,a.t0_should_amt_1
,a.t3_should_amt_1
,a.is_t0_window_1
,a.is_t3_window_1
 --- 新媒体来源
,
case when new_media_source='Google' then '1_Google' when new_media_source='tiktok' then '2_tiktok' when new_media_source='探知' then '3_探知' when new_media_source='organic' then '4_organic' else '5_其它' end as new_media_source
,
 --- advance多头
  case when c.externalid is null then -1 
  when GD_X_19 is null and GD_X_21 is null then 1 
  when GD_X_21=1 or (GD_X_21=2 and GD_X_19 !=1) then 2 
  else 3 
  end as adv_fenzu_flag
,
 case when c.externalid is null then '0_-1' 
 when GD_X_19>=5 then '3_[5,inf]' 
 when GD_X_19>=3 then '2_[3,5)' 
 when GD_X_19>=1 then '1_[1,3)' 
 else '-1_-999' 
 end as adv_30d 
,
 case when c.externalid is null then '0_-1' 
 when GD_X_21>=10 then '3_[10,inf]' 
 when GD_X_21>=3 then '2_[3,10)' 
 when GD_X_21>=1 then '1_[1,3)' 
 else '-1_-999' 
 end as adv_730d 
 -- 行为准则
,apply_num_total
, apply_num_30d
, issue_num_total
,issue_num_30d
,issue_amount_total
,issue_amount_30d
--历史结清订单数 bytenant 
,finish_num_total
,finish_num_30d
,to_newissue_days
,to_lastfinish_days
,to_lastfinish_hours
,no_apply_num_total
, no_apply_num_30d
,max_overdue_days
,max_overdue_days_30d
-- 最大历史逾期天数等标签
,a.app
,case when max_overdue_days=0 then '1.[0]' 
 when max_overdue_days>=1 and max_overdue_days<=30 then '2.[1-30]'
 when max_overdue_days>30 then '3.[31,inf]' 
 end as max_overduedays_flag
,case when finish_num_total BETWEEN 0 and 1 then '1_[0,1]' 
 when finish_num_total BETWEEN 2 and 3 then '2_[2,3]' 
when finish_num_total BETWEEN 4 and 5 then '3_[4,5]'
when finish_num_total>=6 then '4_[6,inf]'  
end as finish_num_total_flag
,case when finish_num_total_byapp BETWEEN 0 and 1 then '1_[0,1]' 
 when finish_num_total_byapp BETWEEN 2 and 3 then '2_[2,3]' 
when finish_num_total_byapp BETWEEN 4 and 5 then '3_[4,5]'
when finish_num_total_byapp>=6 then '4_[6,inf]'  
end as finish_num_total_byapp_flag
,case when to_lastfinish_days=0 then '1_[0]' 
when to_lastfinish_days BETWEEN 1 and 10  then '2_[1,10]' 
when to_lastfinish_days BETWEEN 11 and 30  then '3_[11,30]' 
when to_lastfinish_days>30 then '4_[31,inf]' 
end as to_lastfinish_days_flag
,case when to_lastfinish_days_byapp=0 then '1_[0]' 
when to_lastfinish_days_byapp BETWEEN 1 and 10  then '2_[1,10]' 
when to_lastfinish_days_byapp BETWEEN 11 and 30  then '3_[11,30]' 
when to_lastfinish_days_byapp>30 then '4_[31,inf]' 
end as to_lastfinish_days_byapp_flag
,case when to_newissue_days=0 then '1_[0]'
when to_newissue_days BETWEEN 1 and 15  then '2_[1,15]'
when to_newissue_days BETWEEN 16 and 30  then '3_[16,30]'
when to_newissue_days BETWEEN 31 and 60  then '4_[31,60]'
when to_newissue_days >60  then '5_[61,inf]'
end as to_newissue_days_flag
,case when to_newissue_days_byapp=0 then '1_[0]'
when to_newissue_days_byapp BETWEEN 1 and 15  then '2_[1,15]'
when to_newissue_days_byapp BETWEEN 16 and 30  then '3_[16,30]'
when to_newissue_days_byapp BETWEEN 31 and 60  then '4_[31,60]'
when to_newissue_days_byapp >60  then '5_[61,inf]'
end as to_newissue_days_byapp_flag
,case when to_lastfinish_days>30 then 1 else 0 end as if_to_lastfinish_days_over_30
 --历史结清订单数 距离上次结清间隔天数 距离新客放款平均间隔天数(app维度）
 ,finish_num_total_byapp
 , to_lastfinish_days_byapp
 ,to_newissue_days_byapp
from
mx.wxs_application_funnel a
left join
(
 select * from
 ( select 
 identity 
 ,app_group
  ,age 
  ,degree
  ,income
  ,row_number() over(PARTITION by identity,app_group order by t1.create_time desc ) as rn
from ods.s01_mem_base_info t1
left join ods.s08_app_category_mapping t2
on t1.app_channel=t2.app_channel)
where rn=1
) b
on a.credit_no=b.identity
and a.app_group=b.app_group
-- 从返回结果中提取三方多头信息
left join mx.tmp_advance_table c 
on cast(a.biz_id as varchar)= c.externalid 
-- 提取新媒体来源字段
left JOIN
(SELECT
mid
,new_media_source
from mx.gm_attribution_detail
) e
on e.mid=a.mid
-- 行为变量
left JOIN
(
select t1.biz_id
,count(t2.biz_id) as apply_num_total
,count(case when date_diff('day',date(t2.app_time),date(t1.app_time)) <=30 then t2.biz_id end) as apply_num_30d
,count(case when t2.if_issue=1 then t2.biz_id end) as issue_num_total
,count(case when t2.if_issue=1 and date_diff('day',date(t2.app_time),date(t1.app_time)) <=30 then t2.biz_id end) as issue_num_30d
,sum(case when t2.if_issue=1 then t2.contract_amount end) as issue_amount_total
,sum(case when t2.if_issue=1 and date_diff('day',date(t2.app_time),date(t1.app_time)) <=30 then t2.contract_amount end) as issue_amount_30d
,count(case when t2.finish_time is not null and t1.app_time > t2.finish_time then t2.biz_id end) as finish_num_total
,count(case when t2.finish_time is not null and date_diff('day',date(t2.app_time),date(t1.app_time)) <=30 then t2.biz_id end) as finish_num_30d
,max(case when t2.is_reloan='new' and t2.if_issue=1 and t2.finish_time is not null then date_diff('day',date(t2.release_time),date(t1.app_time)) end) as to_newissue_days
,min(case when t2.finish_time is not null and t1.app_time > t2.finish_time then date_diff('day',date(t2.finish_time),date(t1.app_time)) end) as to_lastfinish_days
,min(case when t2.finish_time is not null and t1.app_time > t2.finish_time then date_diff('hour',t2.finish_time,t1.app_time) end) as to_lastfinish_hours
,count(case when t2.if_in_sx=1 and t2.if_sx_passed !=1 then t2.biz_id end) as no_apply_num_total
,count(case when t2.if_in_sx=1 and t2.if_sx_passed !=1 and date_diff('day',date(t2.app_time),date(t1.app_time)) <=30 then t2.biz_id end) as no_apply_num_30d
,max(case 
when t2.finish_time is not null and t2.should_time<t2.finish_time 
then date_diff('day',date(t2.should_time),date(t2.finish_time))
when t2.finish_time is null and  t2.should_time<t1.app_time
then date_diff('day',date(t2.should_time),date(t1.app_time)) else null 
end) as max_overdue_days
,max(case when date_diff('day',date(t2.app_time),date(t1.app_time)) <=30 
then case when t2.finish_time is not null and t2.should_time<t2.finish_time 
    then date_diff('day',date(t2.should_time),date(t2.finish_time))
    when t2.finish_time is null and  t2.should_time<t1.app_time 
    then date_diff('day',date(t2.should_time),date(t1.app_time)) else null
    end 
end) as max_overdue_days_30d
-- byapp_group 维度
,max(case 
    when t1.app_group='YW' then  -- 包含: yawey, yawey_ultra, yawey_max, yawey_plus
        case when t2.is_reloan='new' and t2.if_issue=1 and t2.finish_time is not null 
             then date_diff('day',date(t2.release_time),date(t1.app_time)) 
        end
    when t1.app_group='HL' then  -- 包含: hola max, hola se, hola, hola pro
        case when t2.is_reloan='new' and t2.if_issue=1 and t2.finish_time is not null 
             then date_diff('day',date(t2.release_time),date(t1.app_time)) 
        end
    when t1.app_group='TG' then  -- 包含: tengo_plus, tengo, tengo_max, tengo_ultra
        case when t2.is_reloan='new' and t2.if_issue=1 and t2.finish_time is not null 
             then date_diff('day',date(t2.release_time),date(t1.app_time)) 
        end
    when t1.app_group='Mexcredo' then
        case when t2.is_reloan='new' and t2.if_issue=1 and t2.finish_time is not null 
             then date_diff('day',date(t2.release_time),date(t1.app_time)) 
        end
    when t1.app_group='Cash Vivas' then
        case when t2.is_reloan='new' and t2.if_issue=1 and t2.finish_time is not null 
             then date_diff('day',date(t2.release_time),date(t1.app_time)) 
        end
    when t1.app_group='PF' then  -- 原pf
        case when t2.is_reloan='new' and t2.if_issue=1 and t2.finish_time is not null 
             then date_diff('day',date(t2.release_time),date(t1.app_time)) 
        end
    when t1.app_group='LS' then
        case when t2.is_reloan='new' and t2.if_issue=1 and t2.finish_time is not null 
             then date_diff('day',date(t2.release_time),date(t1.app_time)) 
        end
    when t1.app_group='Balam Plata' then
        case when t2.is_reloan='new' and t2.if_issue=1 and t2.finish_time is not null 
             then date_diff('day',date(t2.release_time),date(t1.app_time)) 
        end
    when t1.app_group='Toca Lana' then
        case when t2.is_reloan='new' and t2.if_issue=1 and t2.finish_time is not null 
             then date_diff('day',date(t2.release_time),date(t1.app_time)) 
        end
    when t1.app_group='Tuna Cash' then
        case when t2.is_reloan='new' and t2.if_issue=1 and t2.finish_time is not null 
             then date_diff('day',date(t2.release_time),date(t1.app_time)) 
        end
end) as to_newissue_days_byapp
,count(case 
    when t1.app_group='YW' then  -- 包含: yawey, yawey_ultra, yawey_max, yawey_plus
        case when t2.finish_time is not null then t2.biz_id end
    when t1.app_group='HL' then  -- 包含: hola max, hola se, hola, hola pro
        case when t2.finish_time is not null then t2.biz_id end
    when t1.app_group='TG' then  -- 包含: tengo_plus, tengo, tengo_max, tengo_ultra
        case when t2.finish_time is not null then t2.biz_id end
    when t1.app_group='Mexcredo' then
        case when t2.finish_time is not null then t2.biz_id end
    when t1.app_group='Cash Vivas' then
        case when t2.finish_time is not null then t2.biz_id end
    when t1.app_group='PF' then  -- 原pf
        case when t2.finish_time is not null then t2.biz_id end
    when t1.app_group='LS' then
        case when t2.finish_time is not null then t2.biz_id end
    when t1.app_group='Balam Plata' then
        case when t2.finish_time is not null then t2.biz_id end
    when t1.app_group='Toca Lana' then
        case when t2.finish_time is not null then t2.biz_id end
    when t1.app_group='Tuna Cash' then
        case when t2.finish_time is not null then t2.biz_id end
end) as finish_num_total_byapp
,min(case 
    when t1.app_group='YW' then  -- 包含: yawey, yawey_ultra, yawey_max, yawey_plus
        case when t2.finish_time is not null and t1.app_time > t2.finish_time 
             then date_diff('day', date(t2.finish_time), date(t1.app_time)) 
        end
    when t1.app_group='HL' then  -- 包含: hola max, hola se, hola, hola pro
        case when t2.finish_time is not null and t1.app_time > t2.finish_time 
             then date_diff('day', date(t2.finish_time), date(t1.app_time)) 
        end
    when t1.app_group='TG' then  -- 包含: tengo_plus, tengo, tengo_max, tengo_ultra
        case when t2.finish_time is not null and t1.app_time > t2.finish_time 
             then date_diff('day', date(t2.finish_time), date(t1.app_time)) 
        end
    when t1.app_group='Mexcredo' then
        case when t2.finish_time is not null and t1.app_time > t2.finish_time 
             then date_diff('day', date(t2.finish_time), date(t1.app_time)) 
        end
    when t1.app_group='Cash Vivas' then
        case when t2.finish_time is not null and t1.app_time > t2.finish_time 
             then date_diff('day', date(t2.finish_time), date(t1.app_time)) 
        end
    when t1.app_group='PF' then  -- 原pf
        case when t2.finish_time is not null and t1.app_time > t2.finish_time 
             then date_diff('day', date(t2.finish_time), date(t1.app_time)) 
        end
    when t1.app_group='LS' then
        case when t2.finish_time is not null and t1.app_time > t2.finish_time 
             then date_diff('day', date(t2.finish_time), date(t1.app_time)) 
        end
    when t1.app_group='Balam Plata' then
        case when t2.finish_time is not null and t1.app_time > t2.finish_time 
             then date_diff('day', date(t2.finish_time), date(t1.app_time)) 
        end
    when t1.app_group='Toca Lana' then
        case when t2.finish_time is not null and t1.app_time > t2.finish_time 
             then date_diff('day', date(t2.finish_time), date(t1.app_time)) 
        end
    when t1.app_group='Tuna Cash' then
        case when t2.finish_time is not null and t1.app_time > t2.finish_time 
             then date_diff('day', date(t2.finish_time), date(t1.app_time)) 
        end
end) as to_lastfinish_days_byapp
from mx.wxs_application_funnel t1 --当笔
left join mx.wxs_application_funnel t2 --历史笔
 on t1.credit_no=t2.credit_no  and t1.app_time>t2.app_time
group by 1
)f 
on cast(a.biz_id as bigint)=cast(f.biz_id as bigint) 
-- 看三个月以内情况
where is_reloan='old'  and date_diff('month',date_trunc('month',date(a.create_time)),current_date)<=12
;