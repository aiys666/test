
drop table if exists ind.ys_operable_reloan_cnt_251119;
create table if not exists ind.ys_operable_reloan_cnt_251119 as
SELECT
a.*
,b.*
,case when c.mid is not null then 1 else 0 end as if_reject_recent_7_days
,case when max_overdue_days>7 then 1 else 0 end as if_overdue
from
(
SELECT 
last_day_of_month(date_add('day', x, date('2025-01-01'))) AS slice_date
FROM 
UNNEST(sequence(0, date_diff('day', date('2025-01-01'), current_date))) AS t(x)
WHERE 
date_trunc('month', date_add('day', x, date('2025-01-01'))) = date_add('day', x, date('2025-01-01'))
AND 
last_day_of_month(date_add('day', x, date('2025-01-01'))) <> last_day_of_month(current_date)
) a 
left join 
(SELECT 
biz_id first_bizid
,mid
,release_time first_release_time
,IDENTITY
from
ind.xly_application_funnel 
where if_issue=1
and grant_strategy='NEW'
) b
on date(b.first_release_time)<=a.slice_date
left join
(select cast(a.mid as bigint) as mid,create_time
from ods.s05_creditx_order a
where a.status =425  and to_char(apply_time,'yyyymmdd')>='20250101'
) c 
on b.mid=c.mid and a.slice_date <= date(c.create_time) +  interval '7' day and a.slice_date > date(c.create_time)
left join
(select
data_date,
cast(customer_id as bigint) as mid,
max(date_diff('day', date(r.should_time), if(r.fact_time is null, date(date_parse(data_date, '%Y%m%d')), date(r.fact_time)))) as max_overdue_days,
sum(should_capital-fact_capital) as onloan_balance 
from ods.s02_loan_repayment_his r
where data_date in (
SELECT 
to_char(last_day_of_month(date_add('day', x, date('2025-01-01'))),'yyyymmdd') AS slice_date
FROM 
UNNEST(sequence(0, date_diff('day', date('2025-01-01'), current_date))) AS t(x)
WHERE date_trunc('month', date_add('day', x, date('2025-01-01'))) = date_add('day', x, date('2025-01-01'))
)
group by 1,2) d
on b.mid=d.mid
and to_char(a.slice_date,'yyyymmdd')= d.data_date
;














drop table if exists ind.ba_paipai_basic_performance_monthly;


create table if not exists ind.ba_paipai_basic_performance_monthly as
with issue_month as (
SELECT 
    issue_month, 
    COUNT(DISTINCT mid) AS loan_customer_cnt_total,
    COUNT(DISTINCT CASE WHEN grant_strategy = 'NEW' THEN mid END) AS loan_customer_cnt_new,
    COUNT(DISTINCT CASE WHEN grant_strategy = 'OLD' THEN mid END) AS loan_customer_cnt_old,
    SUM(if_issue) AS loan_cnt_total,
    SUM(CASE WHEN grant_strategy = 'NEW' THEN if_issue ELSE 0 END) AS loan_cnt_new,
    SUM(CASE WHEN grant_strategy = 'OLD' THEN if_issue ELSE 0 END) AS loan_cnt_old,
    SUM(contract_amount_usd1) AS loan_amt_total,
    SUM(CASE WHEN grant_strategy = 'NEW' THEN contract_amount_usd1 ELSE 0 END) AS loan_amt_new,
    SUM(CASE WHEN grant_strategy = 'OLD' THEN contract_amount_usd1 ELSE 0 END) AS loan_amt_old,
     
    CASE WHEN SUM(if_issue) > 0 THEN SUM(contract_amount_usd1) *1.000000 / SUM(if_issue) ELSE 0 END AS avg_loan_amt_total,
    CASE WHEN SUM(CASE WHEN grant_strategy = 'NEW' THEN if_issue ELSE 0 END) > 0 
         THEN SUM(CASE WHEN grant_strategy = 'NEW' THEN contract_amount_usd1 ELSE 0 END) *1.000000 / 
              SUM(CASE WHEN grant_strategy = 'NEW' THEN if_issue ELSE 0 END) 
         ELSE 0 END AS avg_loan_amt_new,
    CASE WHEN SUM(CASE WHEN grant_strategy = 'OLD' THEN if_issue ELSE 0 END) > 0 
         THEN SUM(CASE WHEN grant_strategy = 'OLD' THEN contract_amount_usd1 ELSE 0 END) *1.000000 / 
              SUM(CASE WHEN grant_strategy = 'OLD' THEN if_issue ELSE 0 END) 
         ELSE 0 END AS avg_loan_amt_old,
    sum(revenue) AS revenue_total,
    SUM(CASE WHEN grant_strategy = 'NEW' THEN revenue ELSE 0 END) AS revenue_new,
    SUM(CASE WHEN grant_strategy = 'OLD' THEN revenue ELSE 0 END) AS revenue_old,
    SUM(contract_amount ) AS loan_amt_total_idr,
    SUM(CASE WHEN grant_strategy = 'NEW' THEN contract_amount ELSE 0 END) AS loan_amt_new_idr,
    SUM(CASE WHEN grant_strategy = 'OLD' THEN contract_amount ELSE 0 END) AS loan_amt_old_idr,
    SUM(amount) AS loan1_amt_total_idr,
    SUM(CASE WHEN grant_strategy = 'NEW' THEN amount ELSE 0 END) AS loan1_amt_new_idr,
    SUM(CASE WHEN grant_strategy = 'OLD' THEN amount ELSE 0 END) AS loan1_amt_old_idr,
    sum(loan_cycle_amount) AS loan_cycle_amount_idr,
    SUM(CASE WHEN grant_strategy = 'NEW' THEN loan_cycle_amount ELSE 0 END) AS loan_cycle_amt_new_idr,
    SUM(CASE WHEN grant_strategy = 'OLD' THEN loan_cycle_amount ELSE 0 END) AS loan_cycle_amt_old_idr


FROM ind.ba_asset_base_info
WHERE issue_month >= '2025-01-01'
and if_issue = 1
GROUP BY 1
ORDER BY 1) ,
 
 duration as (
    
SELECT  issue_month 
,if(sum(contract_amount)>0,sum(loan_cycle_amount)/sum(contract_amount)  ,0)  as avg_loan_cycle
,if(sum( case when grant_strategy = 'NEW' then contract_amount else 0 end)>0,sum(case when grant_strategy = 'NEW' then loan_cycle_amount else 0 end)/sum( case when grant_strategy = 'NEW' then contract_amount else 0 end)  ,0) as new_avg_loan_cycle
,if(sum( case when grant_strategy = 'OLD' then contract_amount else 0 end)>0,sum(case when grant_strategy = 'OLD' then loan_cycle_amount else 0 end)/sum( case when grant_strategy = 'OLD' then contract_amount else 0 end)  ,0) as old_avg_loan_cycle
,if(sum(should_capital)>0,sum(day_diff*should_capital)/sum(should_capital)  ,0) as all_duration 
,if(sum( case when grant_strategy = 'NEW' then should_capital else 0 end)>0,sum(case when grant_strategy = 'NEW' then day_diff*should_capital else 0 end)/sum( case when grant_strategy = 'NEW' then should_capital else 0 end)  ,0) as new_duration 
,if(sum( case when grant_strategy = 'OLD' then should_capital else 0 end)>0,sum(case when grant_strategy = 'OLD' then day_diff*should_capital else 0 end)/sum( case when grant_strategy = 'OLD' then should_capital else 0 end)  ,0) as old_duration 


from (
  SELECT camera_id ,date_format(create_time,'%Y-%m-01') as issue_month
  ,date_diff('day',date(create_time),coalesce(date(fact_time),date(should_time))) as day_diff 
  ,date(create_time) as issue_date 
  ,should_capital  
from ods.s02_loan_repayment 
) a  
join (
  SELECT biz_id,grant_strategy,loan_cycle,loan_cycle_amount,contract_amount,haircut_amount*1.00/contract_amount as haircut_rate 
  from ind.ba_asset_base_info 
  where if_issue=1
  ) b 
  on a.camera_id=try_cast(b.biz_id as bigint) 
group by 1 
),

mid_app_date as (
 select mid,
        MIN(release_time) AS first_issue_time,   
        MIN(app_date) AS first_app_date
 from
ind.ba_asset_base_info
where if_app = 1 AND grant_strategy = 'NEW' and is_reloan2='NEW_PURE'
group by 1 
),
 
reg_cnt as (select 
    date_format(reg_dt,'%Y-%m-01') as reg_month, 
    count(distinct t.mid) reg_cnt,    
    COUNT(DISTINCT CASE WHEN DATE(mad.first_issue_time) = t.reg_dt THEN t.mid ELSE NULL END) AS t0_issue_cnt,
    COUNT(DISTINCT CASE 
            WHEN mad.first_issue_time <=  current_date- interval '1' day
            THEN t.mid ELSE NULL 
        END) AS all_issue_cnt,  
    COUNT(DISTINCT CASE 
            WHEN mad.first_issue_time <= t.reg_time + INTERVAL '24' HOUR 
            THEN t.mid ELSE NULL 
        END) AS t24h_issue_cnt, 
    COUNT(DISTINCT CASE 
            WHEN mad.first_issue_time <= t.reg_time + INTERVAL '30' DAY 
            THEN t.mid ELSE NULL 
        END) AS t30d_issue_cnt   

    from dws.dws_acq_reg_install t
    LEFT JOIN mid_app_date mad ON mad.mid = t.mid
    WHERE t.reg_dt >= DATE'2025-01-01'
    
    GROUP BY 1 
    ),

new_pure_app_month as (
SELECT 
        app_month, 
        count(distinct case when if_app= 1  then mid else 0 end) app_user_cnt,
        count(distinct case when if_in_confirm_temp = 1  then mid else 0 end) in_confirm_user_cnt,
        count(distinct case when if_confirm_passed_final= 1 and app_month = date_format(confirm_date_final,'%Y-%m-01') then mid else 0 end) confirm_user_cnt,
        count(distinct case when if_confirm_passed_final= 1 and date_format(confirm_date_final,'%Y-%m-01')<= date_format(current_date- interval '1' day,'%Y-%m-01') then mid else 0 end) confirm_user_cnt_all,
        count(distinct case when if_confirm_passed_num_24h= 1 and app_month = date_format(confirm_date_final,'%Y-%m-01') then mid else 0 end) confirm_user_cnt_24h,
        count(distinct case when if_confirm_passed_num_t30= 1 and app_month = date_format(confirm_date_final,'%Y-%m-01') then mid else 0 end) confirm_user_cnt_t30,
        count(distinct case when if_issue= 1 and app_month = issue_month then mid else 0 end) issue_user_cnt,  
        SUM(case when if_in_confirm_temp = 1 then grantcredit_amount else NULL end) AS new_pure_in_confirm_grantcredit_amount,   
        count(distinct case when app_month=issue_month then mid else null end) AS issue_user_from_app_m,  
        count(distinct case when app_month=date_format(confirm_date_final,'%Y-%m-01')  then mid else null end) AS confirm_user_from_app_m,
        count(distinct case when issue_month<=date_format(current_date- interval '1' day,'%Y-%m-01') then mid else null end) AS issue_user_from_app_all,
        count(distinct case when date_format(confirm_date_final,'%Y-%m-01')<= date_format(current_date- interval '1' day,'%Y-%m-01')  then mid else null end) AS confirm_user_from_app_all,
        count(distinct case when app_month=issue_month then biz_id else null end) AS issue_cnt_from_app_m,
        count(distinct case when app_month=date_format(confirm_date_final,'%Y-%m-01')  then biz_id else null end) AS confirm_cnt_from_app_m,
        sum(case when app_month=issue_month then contract_amount_usd else null end) AS issue_amt_from_app_m,
        sum(case when app_month=date_format(confirm_date_final,'%Y-%m-01')  then contract_amount_usd else null end) AS confirm_amt_from_app_m
         
      FROM ind.ba_asset_base_info 
      WHERE grant_strategy='NEW' 
      and if_app=1 
      and is_reloan2='NEW_PURE'
      and date(app_date) >= date'2025-01-01'
      GROUP BY 1
      ) ,



new_confirm_month as (
SELECT  
        date_format(confirm_date_final,'%Y-%m-01') as confirm_month,
        count(distinct mid) confirm_new_user_cnt,  
        SUM(apply_grantcredit_amount) AS confirm_grantcredit_amount,  
        sum(contract_amount_usd) as contract_amount_usd ,   
        count(distinct case when if_issue= 1 then mid else 0 end) issue_user_cnt,  
        count(distinct case when issue_month=date_format(confirm_date_final,'%Y-%m-01') and if_issue=1 then biz_id else null end) AS issue_cnt_from_confirm,  
        count(distinct biz_id ) AS confirm_new_cnt, 
        sum( case when issue_month=date_format(confirm_date_final,'%Y-%m-01') and if_issue=1 then contract_amount_usd else 0 end) AS issue_amt_from_confirm 

      FROM ind.ba_asset_base_info 
      WHERE grant_strategy='NEW' 
      and if_app=1  
      and if_confirm_passed_final= 1
      and date(app_date) >= date'2025-01-01'
      GROUP BY 1 
      ) ,


total_confirm_month as ( 
SELECT  
        date_format(confirm_date_final,'%Y-%m-01') as confirm_month,
        count(distinct case when issue_month=date_format(confirm_date_final,'%Y-%m-01') and if_issue=1 then biz_id else null end) AS issue_cnt_from_confirm_all,  
        count(distinct biz_id ) AS confirm_all_cnt, 
        count(distinct case when grant_strategy='OLD' then mid else null end ) AS confirm_old_user_cnt,   
        sum( case when issue_month=date_format(confirm_date_final,'%Y-%m-01') and if_issue=1 then contract_amount_usd else 0 end) AS issue_amt_from_confirm_all,  
        SUM(apply_grantcredit_amount) AS confirm_grantcredit_amount_all,  
        count(distinct case when issue_month=date_format(confirm_date_final,'%Y-%m-01') and if_issue=1 then mid else null end) AS issue_user_from_confirm_all,  
        count(distinct mid) confirm_all_user_cnt
      FROM ind.ba_asset_base_info 
      WHERE  if_app=1  
      and if_confirm_passed_final= 1
      and date(app_date) >= date'2025-01-01'
      GROUP BY 1
) ,



application_metrics AS ( 
    SELECT  
        app_month, 
        sum(case when if_recall=0 then if_app end) if_app,
        sum(case when grant_strategy='NEW' and if_recall=0 then if_app end) new_if_app,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_app end) old_if_app,

        sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed 
                 when grant_strategy='NEW' then if_in_confirm_final end) if_external_3_passed,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed end) old_if_external_3_passed,
        sum(case when grant_strategy='NEW' then if_in_confirm_final end) new_if_external_3_passed,  

        sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 
                 when grant_strategy='NEW' then if_confirm_passed_final end) if_in_external_data_4,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 end) old_if_in_external_data_4,
        sum(case when grant_strategy='NEW' then if_confirm_passed_final end) new_if_in_external_data_4,

        sum(if_external_data_4_passed ) as if_external_data_4_passed,
        sum(case when grant_strategy='OLD' then if_external_data_4_passed end) old_if_external_data_4_passed,
        sum(case when grant_strategy='NEW' then if_external_data_4_passed end) new_if_external_data_4_passed,

        SUM(case when if_confirm_passed_final= 1 then apply_amount else NULL end) AS confirm_apply_amount,
        SUM(case when grant_strategy='OLD' and if_confirm_passed_final= 1 then apply_amount else NULL end) AS old_confirm_apply_amount,
        SUM(case when grant_strategy='NEW' and if_confirm_passed_final= 1 then apply_amount else NULL end) AS new_confirm_apply_amount,

        sum(contract_amount_usd1) AS total_contract_amount_usd,
        SUM(case when grant_strategy='OLD' then contract_amount_usd1 else NULL end) AS old_contract_amount_usd,
        SUM(case when grant_strategy='NEW' then contract_amount_usd1 else NULL end) AS new_contract_amount_usd,
          
         
        sum(if_in_confirm_temp) AS in_confirm_cnt, 
        SUM(case when grant_strategy='OLD' then if_in_confirm_temp else NULL end) AS old_in_confirm_cnt,
        SUM(case when grant_strategy='NEW' then if_in_confirm_temp else NULL end) AS new_in_confirm_cnt,
        sum(if_confirm_passed_final) AS confirm_passed_cnt, 
        SUM(case when grant_strategy='OLD' then if_confirm_passed_final else NULL end) AS old_confirm_passed_cnt,
        SUM(case when grant_strategy='NEW' then if_confirm_passed_final else NULL end) AS new_confirm_passed_cnt 
        

        
         
    FROM ind.ba_asset_base_info
    WHERE date(app_date) >= DATE('2025-01-01')  
    AND date(app_date) < CURRENT_DATE
    AND if_app = 1
    GROUP BY 1 



),
 



due_amt as (

SELECT 
    app_month, 
    SUM(overdue_amount_1_0) *1.000000 / NULLIF(SUM(should_capital_1_0), 0) AS total_overdue_amount_1_0_ratio,
    SUM(overdue_amount_1_30) *1.000000 / NULLIF(SUM(should_capital_1_30), 0) AS total_overdue_amount_1_30_ratio,
    SUM(overdue_amount_3_30) *1.000000 / NULLIF(SUM(should_capital_3_30), 0) AS total_overdue_amount_3_30_ratio,
    SUM(overdue_amount_total_30) *1.000000 / NULLIF(SUM(should_capital_total_30), 0) AS total_overdue_amount_total_30_ratio,

    SUM(t1_capital_due_d1) *1.000000 / NULLIF(SUM(should_capital_d1), 0) AS total_t1_capital_due_d1_ratio,
    SUM(t30_capital_due_d30) *1.000000 / NULLIF(SUM(should_capital_d30), 0) AS total_t30_capital_due_d30_ratio,
     
    SUM(CASE WHEN grant_strategy = 'NEW' THEN overdue_amount_1_0 ELSE 0 END) *1.000000 / 
    NULLIF(SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital_1_0 ELSE 0 END), 0) AS new_overdue_amount_1_0_ratio,
    SUM(CASE WHEN grant_strategy = 'NEW' THEN overdue_amount_1_30 ELSE 0 END) *1.000000 / 
    NULLIF(SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital_1_30 ELSE 0 END), 0) AS new_overdue_amount_1_30_ratio,
    SUM(CASE WHEN grant_strategy = 'NEW' THEN overdue_amount_3_30 ELSE 0 END) *1.000000 / 
    NULLIF(SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital_3_30 ELSE 0 END), 0) AS new_overdue_amount_3_30_ratio,
    SUM(CASE WHEN grant_strategy = 'NEW' THEN overdue_amount_total_30 ELSE 0 END) *1.000000 / 
    NULLIF(SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital_total_30 ELSE 0 END), 0) AS new_overdue_amount_total_30_ratio,


    SUM(CASE WHEN grant_strategy = 'NEW' THEN t1_capital_due_d1 ELSE 0 END) *1.000000 / 
    NULLIF(SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital_d1 ELSE 0 END), 0) AS new_t1_capital_due_d1_ratio,
    SUM(CASE WHEN grant_strategy = 'NEW' THEN t30_capital_due_d30 ELSE 0 END) *1.000000 / 
    NULLIF(SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital_d30 ELSE 0 END), 0) AS new_t30_capital_due_d30_ratio,
     
    SUM(CASE WHEN grant_strategy = 'OLD' THEN overdue_amount_1_0 ELSE 0 END) *1.000000 / 
    NULLIF(SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital_1_0 ELSE 0 END), 0) AS old_overdue_amount_1_0_ratio,
    SUM(CASE WHEN grant_strategy = 'OLD' THEN overdue_amount_1_30 ELSE 0 END) *1.000000 / 
    NULLIF(SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital_1_30 ELSE 0 END), 0) AS old_overdue_amount_1_30_ratio,
    SUM(CASE WHEN grant_strategy = 'OLD' THEN overdue_amount_3_30 ELSE 0 END) *1.000000 / 
    NULLIF(SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital_3_30 ELSE 0 END), 0) AS old_overdue_amount_3_30_ratio,
    SUM(CASE WHEN grant_strategy = 'OLD' THEN overdue_amount_total_30 ELSE 0 END) *1.000000 / 
    NULLIF(SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital_total_30 ELSE 0 END), 0) AS old_overdue_amount_total_30_ratio,


    SUM(CASE WHEN grant_strategy = 'OLD' THEN t1_capital_due_d1 ELSE 0 END) *1.000000 / 
    NULLIF(SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital_d1 ELSE 0 END), 0) AS old_t1_capital_due_d1_ratio,
    SUM(CASE WHEN grant_strategy = 'OLD' THEN t30_capital_due_d30 ELSE 0 END) *1.000000 / 
    NULLIF(SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital_d30 ELSE 0 END), 0) AS old_t30_capital_due_d30_ratio

FROM ind.ba_apply_should_result 
GROUP BY 1
) ,

old_managed_month as (
SELECT 
date_format(date(SLICE_date),'%Y-%m-01') as stat_month,
count(distinct case when if_overdue<>1 and if_reject_recent_7_days<>1 then mid end) old_managed_cnt
FROM ind.ys_operable_reloan_cnt_251119
group by 1 
) ,


onloan_balance as (
select  DATE_FORMAT(a1.data_date1, '%Y-%m-01') AS balance_month 
    ,sum(a1.should_capital) principal
    ,count(distinct case when due_days<=30 and grant_strategy='OLD' then c1.mid end)old_repay_user_num
    ,sum(case when due_days<=30 then a1.should_capital- a1.fact_capital end) as owing_principal 
    ,count(distinct case when due_days<=30 then c1.mid end)repay_user_num
    from
        (select a.indexs,should_capital,fact_capital,date_trunc('month', to_date(if(length(data_date)=6,concat(data_date,'01'),data_date),'yyyymmdd') + interval '1' month) as dt,
        camera_id,lid,date_trunc('month', to_date(if(length(data_date)=6,concat(data_date,'01'),data_date),'yyyymmdd') + interval '1' month)- interval '1' day as data_date1,data_date
        from ods.s02_loan_repayment_his a
        where ((date_trunc('month', to_date(if(length(data_date)=6,concat(data_date,'01'),data_date),'yyyymmdd') + interval '1' month)- interval '1' day=to_date(if(length(data_date)=6,concat(data_date,'01'),data_date),'yyyymmdd'))
        or(data_date<'202409') or (to_date(data_date,'yyyymmdd')=current_date- interval '1' day))
        and length(data_date)=8
        )a1
        left join
        (select camera_id,date(trade_start_time)trade_start_time,date(trade_end_time)trade_end_time,date(trade_end_time) + interval '60' day as due_date_60,loan_indexs,loan_cycle
        from ods.s02_loan
        )b1
        on cast(a1.camera_id as bigint)=cast(b1.camera_id as bigint)
        left join
        ind.xly_application_funnel c1
        on cast(a1.camera_id as bigint)=cast(c1.biz_id as bigint)
        left join
        (select data_date1,lid,max(due_days) due_days
        from
            (
            select date_trunc('month', to_date(if(length(data_date)=6,concat(data_date,'01'),data_date),'yyyymmdd') + interval '1' month)- interval '1' day as data_date1,
            lid,should_time,fact_time,
            date_diff ('day',date (should_time),if (fact_time is null,to_date(data_date,'yyyymmdd'),date (fact_time))) due_days  
            from ods.s02_loan_repayment_his
            where ((date_trunc('month', to_date(if(length(data_date)=6,concat(data_date,'01'),data_date),'yyyymmdd') + interval '1' month)- interval '1' day=to_date(if(length(data_date)=6,concat(data_date,'01'),data_date),'yyyymmdd'))
            or(data_date<'202409') or (to_date(data_date,'yyyymmdd')=current_date- interval '1' day))
            and length(data_date)=8
            )
        group by 1,2
        )d1
        on cast(a1.lid as bigint)=cast(d1.lid as bigint)
        and a1.data_date1=d1.data_date1
        where
        to_char(date(a1.data_date1),'yyyy-mm')<=to_char(date(due_date_60),'yyyy-mm')
 
        group by 1 
) ,

 
grant_amount_max_data as (
select 
DATE_FORMAT(data_date1, '%Y-%m-01') AS grant_month
,sum(grant_amount_max)grant_amount_max
from
    (select
    a.data_date1,a.data_date,a.camera_id,b.grant_amount_max,
    row_number() over(PARTITION by b.mid,a.data_date order by b.release_time desc) rn
    from
        (select data_date1,data_date,camera_id,max(due_days) due_days
        from
            (
            select date_trunc('month', to_date(if(length(data_date)=6,concat(data_date,'01'),data_date),'yyyymmdd') + interval '1' month)- interval '1' day as data_date1,data_date,
            lid,should_time,fact_time,camera_id,
            date_diff ('day',date (should_time),if (fact_time is null,to_date(data_date,'yyyymmdd'),date (fact_time))) due_days  
            from ods.s02_loan_repayment_his
            where ((date_trunc('month', to_date(if(length(data_date)=6,concat(data_date,'01'),data_date),'yyyymmdd') + interval '1' month)- interval '1' day=to_date(if(length(data_date)=6,concat(data_date,'01'),data_date),'yyyymmdd'))
            or(data_date<'202409') or (to_date(data_date,'yyyymmdd')=current_date- interval '1' day))
            and length(data_date)=8
            )
        group by 1,2,3
        )a
        left join
        (select biz_id,grant_amount_max,mid,release_time from ind.ba_asset_base_info
        where if_issue=1 and if_app=1
        )b
        on cast(a.camera_id as bigint)=cast(b.biz_id as bigint)
        where a.due_days<=30
    )c
    where rn=1
    group by 1
),


owing_principal_data as (
select
issue_month
,sum(owing_principal)owing_principal
,count(distinct biz_id)biz_num
from
  (select
  a.*,(should_capital-fact_capital+contract_amount) as owing_principal
  from
    (select
    biz_id,mid,release_time,app_date,issue_date,contract_amount,app_time,issue_month,baseinfo_onloan_amount,
    sum(should_capital)should_capital,
    sum(fact_capital)fact_capital
    from
        (select
        a.*,
        b.should_capital,
        case when coalesce(b.fact_time,current_date)>a.app_time then 0 else b.fact_capital end as fact_capital
        from
                (select biz_id,mid,release_time,app_date,issue_date,contract_amount,app_time,issue_month,baseinfo_onloan_amount from ind.xly_application_funnel
                where if_issue=1 and if_app=1
                and issue_date>='2025-01-01'
                and grant_strategy='OLD'
                )a 
                left join
                (select *  
                from ods.s02_loan_repayment
                )b
                on cast(a.mid as bigint)=cast(b.customer_id as bigint)
                where a.app_time>b.create_time
        )a 
    group by 1,2,3,4,5,6,7,8,9
    )a
)a
group by 1
),

cohort as (

    SELECT
a.first_loan_issue_month
,sum(amt_old_6m)*1.000000 /sum(cnt_new) as cohort_6m_cnt_rate
,sum(amt_old_12m)*1.000000 /sum(cnt_new) as cohort_12m_cnt_rate
,sum(amt_old_6m)*1.000000 /sum(amt_new) as cohort_6m_amt_rate
,sum(amt_old_12m)*1.000000 /sum(amt_new) as cohort_12m_amt_rate
from
(SELECT
first_loan_issue_month
,sum(case when month_num_issue<=6 then contract_amount_usd1 end) as amt_old_6m
,sum(case when month_num_issue<=12 then contract_amount_usd1 end) as amt_old_12m
from
ind.ba_asset_base_info
where grant_strategy='OLD'
and if_issue=1
group by 1
) a
left join
(SELECT 
issue_month
,count(mid) as cnt_new
,sum(contract_amount_usd1) as amt_new
from
ind.ba_asset_base_info
where grant_strategy='NEW'
and if_issue=1
group by 1
) b
on a.first_loan_issue_month=b.issue_month
group by 1
)



SELECT 
    im.issue_month as month ,
    daa.daily_cnt,
    maa.monthly_cnt,
    ob.owing_principal*1.00000/f.exchange_rate_to_dollar as onloan_amount_30_m,
    ob.repay_user_num as onloan_user_cnt_30_m,
    im.loan_customer_cnt_total,
    im.loan_customer_cnt_new,
    im.loan_customer_cnt_old,
    im.loan_cnt_total,
    im.loan_cnt_new,
    im.loan_cnt_old,
    im.loan_amt_total,
    im.loan_amt_new,
    im.loan_amt_old,
    im.avg_loan_amt_total,
    im.avg_loan_amt_new,
    im.avg_loan_amt_old,
    rc.reg_cnt,
    npam.app_user_cnt,
    npam.in_confirm_user_cnt,
    npam.confirm_user_cnt,
    npam.issue_user_cnt,
    ncm.confirm_new_user_cnt,
    npam.new_pure_in_confirm_grantcredit_amount*1.000000 /npam.in_confirm_user_cnt as new_pure_in_confirm_avg_amt,
    ncm.confirm_grantcredit_amount*1.000000 /ncm.confirm_new_user_cnt as new_confirm_avg_amt,
    --  ncm.contract_amount_usd*1.000000 /ncm.issue_user_cnt as new_avg_amt,
    rc.all_issue_cnt*1.000000 /rc.reg_cnt as new_reg_issue_rate,
    rc.t24h_issue_cnt*1.000000 /rc.reg_cnt as new_t24h_reg_issue_rate,
    rc.t30d_issue_cnt*1.000000 /rc.reg_cnt as new_t30d_reg_issue_rate,
    
    npam.in_confirm_user_cnt*1.000000 /npam.app_user_cnt as new_pure_in_confirm_rate,
    npam.confirm_user_cnt_all*1.000000 /npam.in_confirm_user_cnt as new_pure_confirm_rate,
    npam.confirm_user_cnt_24h*1.000000 /npam.in_confirm_user_cnt as new_pure_confirm_rate_24h,
    npam.confirm_user_cnt_t30*1.000000 /npam.in_confirm_user_cnt as new_pure_confirm_rate_t30,
 

    am.confirm_passed_cnt*1.000000 /am.in_confirm_cnt as total_confirm_rate,
    am.new_confirm_passed_cnt*1.000000 /am.new_in_confirm_cnt as new_confirm_rate,
    am.old_confirm_passed_cnt*1.000000 /am.old_in_confirm_cnt as old_confirm_rate,

    am.new_if_external_3_passed*1.000000 /am.new_if_app as new_before_pass_rate,
    am.new_if_external_data_4_passed*1.000000 /am.new_if_in_external_data_4 as new_after_pass_rate,
    am.new_contract_amount_usd*1.000000 /am.new_confirm_apply_amount as new_after_pass_amt_rate,

 

    am.old_if_external_3_passed*1.000000 /am.old_if_app as old_before_pass_rate,
    am.old_if_external_data_4_passed*1.000000 /am.old_if_in_external_data_4 as old_after_pass_rate,
    am.old_contract_amount_usd*1.000000 /am.old_confirm_apply_amount as old_after_pass_amt_rate,



    omm.old_managed_cnt,
    tcm.confirm_old_user_cnt,
    ob.old_repay_user_num as old_onloan_user_cnt_30_m,
    opd.owing_principal*1.000000 /(opd.biz_num*f.exchange_rate_to_dollar) as old_onloan_amount_30_m_user_avg, 


    ob.owing_principal*1.000000 /(ob.repay_user_num*f.exchange_rate_to_dollar) as onloan_amount_30_m_user_avg, 
    gamd.grant_amount_max*1.000000 /ob.repay_user_num  as grant_amount_30_m_user_avg,
    npam.new_pure_in_confirm_grantcredit_amount*1.000000 /npam.in_confirm_user_cnt as new_pure_confirm_app_avg_amt,
 
    c.cohort_6m_cnt_rate,
    c.cohort_12m_cnt_rate,
    c.cohort_6m_amt_rate,
    c.cohort_12m_amt_rate,

    -- (revenue_total*1.000000 / loan1_amt_total_idr)/(loan_cycle_amount_idr/loan_amt_total_idr)*365 as apr_loan1_amt_ratio,

    -- (revenue_new*1.000000 / loan1_amt_new_idr)/(loan_cycle_amt_new_idr/loan_amt_new_idr)*365 as new_apr_loan1_amt_ratio,
    -- (revenue_old*1.000000 / loan1_amt_old_idr)/(loan_cycle_amt_old_idr/loan_amt_old_idr)*365 as old_apr_loan1_amt_ratio,
    -- (revenue_total*1.000000 / loan_amt_total_idr)/(loan_cycle_amount_idr/loan_amt_total_idr)*365 as apr_loan_amt_ratio,
    -- (revenue_new*1.000000 / loan_amt_new_idr)/(loan_cycle_amt_new_idr/loan_amt_new_idr)*365 as new_apr_loan_amt_ratio,
    -- (revenue_old*1.000000 / loan_amt_old_idr)/(loan_cycle_amt_old_idr/loan_amt_old_idr)*365 as old_apr_loan_amt_ratio,
    d.avg_loan_cycle,
    d.new_avg_loan_cycle,
    d.old_avg_loan_cycle,
    d.all_duration,
    d.new_duration,
    d.old_duration,



    da.total_overdue_amount_1_0_ratio,
    da.new_overdue_amount_1_0_ratio,
    da.old_overdue_amount_1_0_ratio,
    da.total_overdue_amount_1_30_ratio,
    da.new_overdue_amount_1_30_ratio,
    da.old_overdue_amount_1_30_ratio,
    da.total_overdue_amount_3_30_ratio,
    da.new_overdue_amount_3_30_ratio,
    da.old_overdue_amount_3_30_ratio,
    total_overdue_amount_total_30_ratio,
    new_overdue_amount_total_30_ratio,
    old_overdue_amount_total_30_ratio,




    da.total_t1_capital_due_d1_ratio,
    da.new_t1_capital_due_d1_ratio,
    da.old_t1_capital_due_d1_ratio,
    da.total_t30_capital_due_d30_ratio, 
    da.new_t30_capital_due_d30_ratio, 
    da.old_t30_capital_due_d30_ratio,
    f.exchange_rate_to_dollar

    
FROM issue_month im
LEFT JOIN duration d ON im.issue_month = d.issue_month
LEFT JOIN reg_cnt rc ON im.issue_month = rc.reg_month
LEFT JOIN new_pure_app_month npam ON im.issue_month = npam.app_month
LEFT JOIN new_confirm_month ncm ON im.issue_month = ncm.confirm_month
LEFT JOIN total_confirm_month tcm ON im.issue_month = tcm.confirm_month
LEFT JOIN application_metrics am ON im.issue_month = am.app_month
LEFT JOIN due_amt da ON im.issue_month = da.app_month
LEFT JOIN old_managed_month omm ON im.issue_month = omm.stat_month
LEFT JOIN onloan_balance ob ON im.issue_month = ob.balance_month
LEFT JOIN grant_amount_max_data gamd ON im.issue_month = gamd.grant_month
LEFT JOIN owing_principal_data opd ON im.issue_month = opd.issue_month
left join ind.ys_daily_activate daa on im.issue_month = DATE_FORMAT(date_parse(daa.month, '%Y/%m/%d'), '%Y-%m-01')
left join ind.ys_monthly_activate maa on im.issue_month = DATE_FORMAT(date_parse(maa.month, '%Y/%m/%d'), '%Y-%m-01')
left join cohort as c on im.issue_month=c.first_loan_issue_month
LEFT JOIN dim.dim_exchange_rate_cost f ON TO_CHAR(DATE(im.issue_month), 'yyyymm') = f.month_id AND f.account_currency = 'IDR'
 
ORDER BY month;





留存率的指标：

WITH mid_max_ovd_days as (
  SELECT 
  lb.customer_id,
  date(date_parse(data_date, '%Y%m%d')) as date_date, 
  max(case when (lb.should_capital+lb.should_interest) <= (lb.fact_capital+lb.fact_interest+lb.subtract_capital+lb.subtract_interest+lb.coupon_amount) 
      THEN 0
      ELSE date_diff('day',date(lb.should_time),date(date_parse(data_date, '%Y%m%d'))) end) overdue_days,
  max(case when state in (2,3) then date_diff('day',date(lb.should_time),date(date_parse(data_date, '%Y%m%d'))) else 0 end) as overdue_days1,
  max(case 
        when state in (2) then date_diff('day',date(lb.should_time),date(date_parse(data_date, '%Y%m%d'))) 
        else 0 
        end) as overdue_days2,
  count(case when lb.state IN (0, 2, 4) and date_diff('day', date(should_time), date_parse(data_date, '%Y%m%d')) <= 90 then rid end) as onloan_rid_cnt 
  from ods.s02_loan_repayment_his lb  
  where lb.data_date>='20260301' 
  group by 1,2
)
SELECT
issue_month
,count(a.customer_id) as new_cnt
-- ,count(case when b.overdue_days<=0 or b.overdue_days is null then a.customer_id end) as no_ovd_cnt
,count(case when (b.overdue_days<=0 or b.overdue_days is null) and b.onloan_rid_cnt>0 then a.customer_id end) as onloan_cnt 
from
(SELECT
mid as customer_id
,to_char(date_trunc('month',release_time),'yyyy-mm-dd') as issue_month
,release_time
,date(date_add('day',60,release_time)) first_loan_date_90plus
from
ind.ba_asset_base_info
where release_time is not null
and if_issue=1
and reloan_num=1
and release_time>=date'2026-03-01'
and release_time<=date'2026-07-31'
) a
left join
mid_max_ovd_days b
on a.customer_id=b.customer_id
and a.first_loan_date_90plus=b.date_date
group by 1
order by 1
;


-- 日活、月活数据；

WITH combined_events AS ( 
  SELECT
    TO_DATE(etl_date, 'yyyymmdd') AS event_date,
    customer_user_id AS user_id
  FROM ods.s08_appsflyer_push_data
  WHERE etl_date >= '20250101'
    AND (event_name LIKE '%Home%' OR event_name LIKE '%home%' OR event_name LIKE '%addloan%')
    AND event_source != 'S2S'
  
  UNION ALL
   
  SELECT
    TO_DATE(etl_date, 'yyyymmdd') AS event_date,
    cast(mid as varchar) AS user_id
  FROM ods.s29_behavior_record
  WHERE etl_date >= '20250101'    
    AND (event_name LIKE '%Home%' OR event_name LIKE '%home%' OR event_name LIKE '%addloan%')
),
 
daily_uv AS (
  SELECT
    event_date,
    COUNT(DISTINCT user_id) AS daily_uv
  FROM combined_events
  GROUP BY event_date
),
 
monthly_uv AS (
  SELECT
    DATE_FORMAT(event_date, '%Y-%m-01') AS data_month,
    COUNT(DISTINCT user_id) AS monthly_uv
  FROM combined_events
  GROUP BY DATE_FORMAT(event_date, '%Y-%m-01')
)
 
SELECT
  DATE_FORMAT(d.event_date, '%Y-%m-01') AS data_month,
  AVG(d.daily_uv) AS avg_daily_active_users,
  m.monthly_uv AS monthly_active_users
FROM daily_uv d
JOIN monthly_uv m 
  ON DATE_FORMAT(d.event_date, '%Y-%m-01') = m.data_month
GROUP BY DATE_FORMAT(d.event_date, '%Y-%m-01'), m.monthly_uv
ORDER BY data_month;