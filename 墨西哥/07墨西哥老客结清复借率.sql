select * 
from mx.yj_clear_reloan





drop table if EXISTS mx.yj_clear_reloan;
CREATE table mx.yj_clear_reloan as
select a.app_group
,case when finish_num>=10 then '10+' else cast(finish_num as varchar) end as finish_num --结清次数分组
,a.finish_time
,a.first_finish_time
,a.is_reloan
,max(substr(cast(current_timestamp as varchar),1,24)) as update_tim
,count(distinct a.biz_id) as finish_user_num --结清人数
,count(distinct case when date_diff('day',date(a.finish_time),now()) >=5 then a.biz_id end) as finish_user_num_5d --满足5天表现期的结清人数
,avg( case when date_diff('day',date(a.finish_time),now()) >=5 then finish_global_limit end) as avg_finish_global_limit_5d --满足5天表现期的结清订单的平均全局额度
,count(distinct case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <=5 then a.biz_id end) as reloan_apply_user_num_5d --结清后5天内复借的人数
,count(distinct case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <=5 then b.biz_id end) as reloan_apply_num_5d --结清后5天内复借的次数
-- 通过率
,sum(case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 then b.if_in_sx end) as if_in_sx
,sum(case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 then b.if_in_fu_anti_fraud end ) as if_in_fu_anti_fraud
,sum(case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 then b.if_fu_external_data_passed end) as if_fu_external_data_passed
,sum(case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 then b.if_sx_passed end) as if_sx_passed
,avg(case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 then coalesce(cast(b.global_limit as integer), cast(b.grantcredit_7d_amount as integer)) end) as reloan_global_limit
--24h用信率
,sum(case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 then b.if_sx_passed_24h end ) as if_sx_passed_24h
,sum(case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5  then b.if_in_sx_24h end) as if_in_sx_24h
,sum(case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 and b.if_issue=1 then b.contract_amount end) as reloan_amt_5d --结清后5天内放款金额
,sum(case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 and b.if_issue=1 and b.is_t0_window_1=1 then b.t0_overdue_amount_1 end) as t0_overdue_amount_1
,sum(case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 and b.if_issue=1 and b.is_t3_window_1=1 then b.t3_overdue_amount_1 end) as t3_overdue_amount_1
,sum(case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 and b.if_issue=1 and b.is_t0_window_1=1 then b.t0_should_amt_1 end) as t0_should_amt_1
,sum(case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 and b.if_issue=1 and b.is_t3_window_1=1 then b.t3_should_amt_1 end) as t3_should_amt_1
,count(distinct case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 and b.if_issue=1 and b.is_t0_window_1=1  then b.biz_id end) as T0
,count(distinct case when date_diff('day',date(a.finish_time),now()) >=5 and date_diff('day',date(a.finish_time),date(b.app_time)) <5 and b.if_issue=1 and b.is_t3_window_1=1 then b.biz_id end) as T3
from
(select t1.biz_id,t1.credit_no,t1.finish_time,t1.app_group,t1.is_reloan,first_finish_time
,count(distinct t2.biz_id) as finish_num  --算出本笔结清订单的历史结清次数：也就是每一个人在相同app上基于当前结清订单 计算的结清次数（包括本笔）--每个人在该时间点只有一个唯一的结清次数
,avg(coalesce(cast(t1.global_limit as integer),cast(t1.grantcredit_7d_amount as integer))) as finish_global_limit
from 
(select tt1.* ,first_finish_time 
from mx.wxs_application_funnel tt1 --分析起点：本笔必须是结清订单
left join
(select 
credit_no
,app_group
,biz_id as first_bizid
,row_number() over(partition by credit_no,app_group order by app_time) as rn
-- ,date(create_time)  as first_loan_date
,date(finish_time) as first_finish_time
from
mx.wxs_application_funnel
where is_reloan='new'
and if_issue=1 
and finish_time is not null 
) tt3 on tt1.credit_no=tt3.credit_no and tt1.app_group=tt3.app_group and rn=1
where finish_time is not null and tt1.app_group is not null 
) t1
left join 
(select * from mx.wxs_application_funnel --历史结清
where finish_time is not null and app_group is not null) t2 on t1.credit_no=t2.credit_no and t1.app_group=t2.app_group and t1.finish_time>=t2.finish_time
group by 1,2,3,4,5,6) a --分析的目标人群，即结清行为人群
left join 
(select t1.*
from
mx.wxs_application_funnel t1 -- 结清后复借情况
) b 
on a.credit_no=b.credit_no and a.app_group=b.app_group and a.finish_time<b.app_time --left join 结清后复借情况
where a.finish_time>=cast('2025-03-15 05:00:00.000' as timestamp)
group by 1,2,3,4,5