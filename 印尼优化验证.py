# -*- coding: utf-8 -*-
"""
印尼拍拍指标 - 优化后代码验证脚本
对比原始SQL和优化后SQL的结果是否一致
"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from indonesia_presto import PrestoQuery
import pandas as pd
import os
import time
import base64
import json

OUTPUT_DIR = r"E:\岳松个人文件\嘉银工作内容的整理\code"

# 读取基准结果
baseline_path = os.path.join(OUTPUT_DIR, "印尼拍拍_基准结果_第一段.csv")
if os.path.exists(baseline_path):
    baseline_df = pd.read_csv(baseline_path)
    print(f"基准结果已加载: {len(baseline_df)} 行, {len(baseline_df.columns)} 列")
else:
    print("❌ 基准结果文件不存在，请先运行印尼基准测试.py")
    sys.exit(1)

# 优化后的SQL（保持与原始完全一致的逻辑）
OPTIMIZED_SQL = """
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
    SUM(contract_amount) AS loan_amt_total_idr,
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
SELECT issue_month 
,if(sum(contract_amount)>0,sum(loan_cycle_amount)/sum(contract_amount),0) as avg_loan_cycle
,if(sum(case when grant_strategy = 'NEW' then contract_amount else 0 end)>0,sum(case when grant_strategy = 'NEW' then loan_cycle_amount else 0 end)/sum(case when grant_strategy = 'NEW' then contract_amount else 0 end),0) as new_avg_loan_cycle
,if(sum(case when grant_strategy = 'OLD' then contract_amount else 0 end)>0,sum(case when grant_strategy = 'OLD' then loan_cycle_amount else 0 end)/sum(case when grant_strategy = 'OLD' then contract_amount else 0 end),0) as old_avg_loan_cycle
,if(sum(should_capital)>0,sum(day_diff*should_capital)/sum(should_capital),0) as all_duration 
,if(sum(case when grant_strategy = 'NEW' then should_capital else 0 end)>0,sum(case when grant_strategy = 'NEW' then day_diff*should_capital else 0 end)/sum(case when grant_strategy = 'NEW' then should_capital else 0 end),0) as new_duration 
,if(sum(case when grant_strategy = 'OLD' then should_capital else 0 end)>0,sum(case when grant_strategy = 'OLD' then day_diff*should_capital else 0 end)/sum(case when grant_strategy = 'OLD' then should_capital else 0 end),0) as old_duration 
from (
  SELECT camera_id,date_format(create_time,'%Y-%m-01') as issue_month
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
 from ind.ba_asset_base_info
where if_app = 1 AND grant_strategy = 'NEW' and is_reloan2='NEW_PURE'
group by 1 
),
reg_cnt as (select 
    date_format(reg_dt,'%Y-%m-01') as reg_month, 
    count(distinct t.mid) reg_cnt,    
    COUNT(DISTINCT CASE WHEN DATE(mad.first_issue_time) = t.reg_dt THEN t.mid ELSE NULL END) AS t0_issue_cnt,
    COUNT(DISTINCT CASE 
            WHEN mad.first_issue_time <= current_date - interval '1' day
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
    from ind.tyn_reg_install_new t
    LEFT JOIN mid_app_date mad ON mad.mid = t.mid
    WHERE t.reg_dt >= DATE'2025-01-01'
    GROUP BY 1 
),
new_pure_app_month as (
SELECT 
        app_month, 
        count(distinct case when if_app= 1 then mid else 0 end) app_user_cnt,
        count(distinct case when if_in_confirm_temp = 1 then mid else 0 end) in_confirm_user_cnt,
        count(distinct case when if_confirm_passed_final= 1 and app_month = date_format(confirm_date_final,'%Y-%m-01') then mid else 0 end) confirm_user_cnt,
        count(distinct case when if_confirm_passed_final= 1 and date_format(confirm_date_final,'%Y-%m-01')<= date_format(current_date- interval '1' day,'%Y-%m-01') then mid else 0 end) confirm_user_cnt_all,
        count(distinct case when if_confirm_passed_num_24h= 1 and app_month = date_format(confirm_date_final,'%Y-%m-01') then mid else 0 end) confirm_user_cnt_24h,
        count(distinct case when if_confirm_passed_num_t30= 1 and app_month = date_format(confirm_date_final,'%Y-%m-01') then mid else 0 end) confirm_user_cnt_t30,
        count(distinct case when if_issue= 1 and app_month = issue_month then mid else 0 end) issue_user_cnt,  
        SUM(case when if_in_confirm_temp = 1 then grantcredit_amount else NULL end) AS new_pure_in_confirm_grantcredit_amount,   
        count(distinct case when app_month=issue_month then mid else null end) AS issue_user_from_app_m,  
        count(distinct case when app_month=date_format(confirm_date_final,'%Y-%m-01') then mid else null end) AS confirm_user_from_app_m,
        count(distinct case when issue_month<=date_format(current_date- interval '1' day,'%Y-%m-01') then mid else null end) AS issue_user_from_app_all,
        count(distinct case when date_format(confirm_date_final,'%Y-%m-01')<= date_format(current_date- interval '1' day,'%Y-%m-01') then mid else null end) AS confirm_user_from_app_all,
        count(distinct case when app_month=issue_month then biz_id else null end) AS issue_cnt_from_app_m,
        count(distinct case when app_month=date_format(confirm_date_final,'%Y-%m-01') then biz_id else null end) AS confirm_cnt_from_app_m,
        sum(case when app_month=issue_month then contract_amount_usd else null end) AS issue_amt_from_app_m,
        sum(case when app_month=date_format(confirm_date_final,'%Y-%m-01') then contract_amount_usd else null end) AS confirm_amt_from_app_m
      FROM ind.ba_asset_base_info 
      WHERE grant_strategy='NEW' 
      and if_app=1 
      and is_reloan2='NEW_PURE'
      and date(app_date) >= date'2025-01-01'
      GROUP BY 1
),
new_confirm_month as (
SELECT  
        date_format(confirm_date_final,'%Y-%m-01') as confirm_month,
        count(distinct mid) confirm_new_user_cnt,  
        SUM(apply_grantcredit_amount) AS confirm_grantcredit_amount,  
        sum(contract_amount_usd) as contract_amount_usd,   
        count(distinct case when if_issue= 1 then mid else 0 end) issue_user_cnt,  
        count(distinct case when issue_month=date_format(confirm_date_final,'%Y-%m-01') and if_issue=1 then biz_id else null end) AS issue_cnt_from_confirm,  
        count(distinct biz_id) AS confirm_new_cnt, 
        sum(case when issue_month=date_format(confirm_date_final,'%Y-%m-01') and if_issue=1 then contract_amount_usd else 0 end) AS issue_amt_from_confirm 
      FROM ind.ba_asset_base_info 
      WHERE grant_strategy='NEW' 
      and if_app=1  
      and if_confirm_passed_final= 1
      and date(app_date) >= date'2025-01-01'
      GROUP BY 1 
),
total_confirm_month as ( 
SELECT  
        date_format(confirm_date_final,'%Y-%m-01') as confirm_month,
        count(distinct case when issue_month=date_format(confirm_date_final,'%Y-%m-01') and if_issue=1 then biz_id else null end) AS issue_cnt_from_confirm_all,  
        count(distinct biz_id) AS confirm_all_cnt, 
        count(distinct case when grant_strategy='OLD' then mid else null end) AS confirm_old_user_cnt,   
        sum(case when issue_month=date_format(confirm_date_final,'%Y-%m-01') and if_issue=1 then contract_amount_usd else 0 end) AS issue_amt_from_confirm_all,  
        SUM(apply_grantcredit_amount) AS confirm_grantcredit_amount_all,  
        count(distinct case when issue_month=date_format(confirm_date_final,'%Y-%m-01') and if_issue=1 then mid else null end) AS issue_user_from_confirm_all,  
        count(distinct mid) confirm_all_user_cnt
      FROM ind.ba_asset_base_info 
      WHERE if_app=1  
      and if_confirm_passed_final= 1
      and date(app_date) >= date'2025-01-01'
      GROUP BY 1
),
application_metrics AS ( 
    SELECT  
        app_month, 
        sum(case when if_recall=0 then if_app end) if_app,
        sum(case when grant_strategy='NEW' and if_recall=0 then if_app end) new_if_app,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_app end) old_if_app,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed 
                 when grant_strategy='NEW' then if_in_confirm_temp end) if_external_3_passed,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed end) old_if_external_3_passed,
        sum(case when grant_strategy='NEW' then if_in_confirm_temp end) new_if_external_3_passed,  
        sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 
                 when grant_strategy='NEW' then if_confirm_passed_final end) if_in_external_data_4,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 end) old_if_in_external_data_4,
        sum(case when grant_strategy='NEW' then if_confirm_passed_final end) new_if_in_external_data_4,
        sum(if_external_data_4_passed) as if_external_data_4_passed,
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
),
old_managed_month as (
SELECT 
date_format(date(SLICE_date),'%Y-%m-01') as stat_month,
count(distinct case when if_overdue<>1 and if_reject_recent_7_days<>1 then mid end) old_managed_cnt
FROM ind.ys_operable_reloan_cnt_251119
group by 1 
),
onloan_balance as (
select DATE_FORMAT(a1.data_date1, '%Y-%m-01') AS balance_month 
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
            (select date_trunc('month', to_date(if(length(data_date)=6,concat(data_date,'01'),data_date),'yyyymmdd') + interval '1' month)- interval '1' day as data_date1,
            lid,should_time,fact_time,
            date_diff('day',date(should_time),if(fact_time is null,to_date(data_date,'yyyymmdd'),date(fact_time))) due_days  
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
),
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
            (select date_trunc('month', to_date(if(length(data_date)=6,concat(data_date,'01'),data_date),'yyyymmdd') + interval '1' month)- interval '1' day as data_date1,data_date,
            lid,should_time,fact_time,camera_id,
            date_diff('day',date(should_time),if(fact_time is null,to_date(data_date,'yyyymmdd'),date(fact_time))) due_days  
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
select issue_month
,sum(owing_principal)owing_principal
,count(distinct biz_id)biz_num
from
  (select a.*,(should_capital-fact_capital+contract_amount) as owing_principal
  from
    (select biz_id,mid,release_time,app_date,issue_date,contract_amount,app_time,issue_month,baseinfo_onloan_amount,
    sum(should_capital)should_capital,
    sum(fact_capital)fact_capital
    from
        (select a.*,b.should_capital,
        case when coalesce(b.fact_time,current_date)>a.app_time then 0 else b.fact_capital end as fact_capital
        from
                (select biz_id,mid,release_time,app_date,issue_date,contract_amount,app_time,issue_month,baseinfo_onloan_amount from ind.xly_application_funnel
                where if_issue=1 and if_app=1
                and issue_date>='2025-01-01'
                and grant_strategy='OLD'
                )a 
                left join
                (select * from ods.s02_loan_repayment)b
                on cast(a.mid as bigint)=cast(b.customer_id as bigint)
                where a.app_time>b.create_time
        )a 
    group by 1,2,3,4,5,6,7,8,9
    )a
)a
group by 1
),
cohort as (
SELECT a.first_loan_issue_month
,sum(amt_old_6m)*1.000000 /sum(cnt_new) as cohort_6m_cnt_rate
,sum(amt_old_12m)*1.000000 /sum(cnt_new) as cohort_12m_cnt_rate
,sum(amt_old_6m)*1.000000 /sum(amt_new) as cohort_6m_amt_rate
,sum(amt_old_12m)*1.000000 /sum(amt_new) as cohort_12m_amt_rate
from
(SELECT first_loan_issue_month
,sum(case when month_num_issue<=6 then contract_amount_usd1 end) as amt_old_6m
,sum(case when month_num_issue<=12 then contract_amount_usd1 end) as amt_old_12m
from ind.ba_asset_base_info
where grant_strategy='OLD' and if_issue=1
group by 1) a
left join
(SELECT issue_month,count(mid) as cnt_new,sum(contract_amount_usd1) as amt_new
from ind.ba_asset_base_info
where grant_strategy='NEW' and if_issue=1
group by 1) b
on a.first_loan_issue_month=b.issue_month
group by 1
)
SELECT 
    im.issue_month as month,
    daa.daily_cnt,
    maa.monthly_cnt,
    ob.owing_principal*1.00000/f.exchange_rate_to_dollar as onloan_amount_30_m,
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
    ob.old_repay_user_num as old_onloan_amount_30_m,
    opd.owing_principal*1.000000 /(opd.biz_num*f.exchange_rate_to_dollar) as old_onloan_amount_30_m_user_avg,
    ob.owing_principal*1.000000 /(ob.repay_user_num*f.exchange_rate_to_dollar) as onloan_amount_30_m_user_avg, 
    gamd.grant_amount_max*1.000000 /ob.repay_user_num as grant_amount_30_m_user_avg,
    npam.new_pure_in_confirm_grantcredit_amount*1.000000 /npam.in_confirm_user_cnt as new_pure_confirm_app_avg_amt,
    c.cohort_6m_cnt_rate,
    c.cohort_12m_cnt_rate,
    c.cohort_6m_amt_rate,
    c.cohort_12m_amt_rate,
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
ORDER BY month
"""

def submit_sql(pq, sql, desc="SQL", max_retries=3):
    """提交SQL并获取结果"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for attempt in range(max_retries):
        try:
            print(f"  {desc} (第{attempt+1}/{max_retries}次)...")
            
            query_url = 'https://data.samir.co.id/dataworks-development/adhoc/querySql'
            data_sql = {
                "sql": base64.b64encode(sql.encode()).decode(),
                "windowId": 16,
                "headRowNum": 54,
                "engine": "PRESTO",
                "queryType": "Data",
                "varList": [],
                "dependStatus": 1
            }
            
            check_res = pq.sess.post(query_url, headers=headers, data=json.dumps(data_sql), timeout=(10, 30))
            check_data = check_res.json()
            
            if check_data['data']['checkError'] == 'True':
                error_msg = check_data['data']['checkResultList'][0]['errorMsg']
                print(f"    ❌ SQL错误: {error_msg[:200]}")
                return None
            
            job_query_id = check_data['data']['jobQueryId']
            
            job_url = 'https://data.samir.co.id/dataworks-development/adhoc/queryPrestoJobLog'
            job_payload = {"jobQueryId": job_query_id}
            
            for _ in range(60):
                time.sleep(3)
                job_res = pq.sess.get(job_url, headers=headers, params=job_payload, timeout=(10, 30))
                job_data = job_res.json()
                
                state = job_data['data']['taskState']
                if state == 'FINISHED':
                    break
                elif state in ('FAILED', 'KILLED', 'CANCELED'):
                    print(f"    ❌ 执行失败: {state}")
                    return None
            
            query_id = job_data['data']['queryId']
            result_url = 'https://data.samir.co.id/dataworks-development/adhoc/getQueryResult'
            result_payload = {'current': 1, 'size': 5000, 'queryId': query_id}
            result_res = pq.sess.post(result_url, headers=headers, data=json.dumps(result_payload), timeout=(10, 120))
            result_data = result_res.json()
            
            total_records = result_data['data'].get('totalRecords', 0)
            records = result_data['data'].get('records', [])
            columns = result_data['data'].get('columns', [])
            
            if total_records == 0:
                print(f"    ⚠️ 结果为空")
                return pd.DataFrame(columns=columns)
            
            all_records = list(records)
            pages = (total_records // 5000) + 1
            for page in range(2, pages + 1):
                result_payload = {'current': page, 'size': 5000, 'queryId': query_id}
                result_res = pq.sess.post(result_url, headers=headers, data=json.dumps(result_payload), timeout=(10, 120))
                page_data = result_res.json()
                if page_data['data'] and page_data['data'].get('records'):
                    all_records.extend(page_data['data']['records'])
            
            df = pd.DataFrame(all_records, columns=columns)
            print(f"    ✅ 成功，返回 {len(df)} 行")
            return df
            
        except Exception as e:
            print(f"    异常: {str(e)[:100]}")
            if attempt < max_retries - 1:
                print("    重新登录重试...")
                pq.login_process()
                time.sleep(2)
                continue
            return None
    
    return None

def compare_results(baseline_df, optimized_df):
    """对比两个DataFrame的结果"""
    print("\n" + "=" * 60)
    print("结果对比验证")
    print("=" * 60)
    
    # 检查行数
    if len(baseline_df) != len(optimized_df):
        print(f"❌ 行数不一致: 基准={len(baseline_df)}, 优化={len(optimized_df)}")
        return False
    else:
        print(f"✅ 行数一致: {len(baseline_df)} 行")
    
    # 检查列数
    if len(baseline_df.columns) != len(optimized_df.columns):
        print(f"❌ 列数不一致: 基准={len(baseline_df.columns)}, 优化={len(optimized_df.columns)}")
        return False
    else:
        print(f"✅ 列数一致: {len(baseline_df.columns)} 列")
    
    # 检查列名
    if list(baseline_df.columns) != list(optimized_df.columns):
        print(f"❌ 列名不一致!")
        baseline_cols = set(baseline_df.columns)
        optimized_cols = set(optimized_df.columns)
        only_in_baseline = baseline_cols - optimized_cols
        only_in_optimized = optimized_cols - baseline_cols
        if only_in_baseline:
            print(f"   仅在基准中: {only_in_baseline}")
        if only_in_optimized:
            print(f"   仅在优化中: {only_in_optimized}")
        return False
    else:
        print(f"✅ 列名一致")
    
    # 检查数据内容
    print("\n开始逐列对比数据...")
    diff_count = 0
    total_comparisons = 0
    
    for col in baseline_df.columns:
        baseline_vals = baseline_df[col].fillna('NULL').astype(str)
        optimized_vals = optimized_df[col].fillna('NULL').astype(str)
        
        if baseline_vals.equals(optimized_vals):
            continue
        
        # 找出差异行
        mismatches = baseline_vals != optimized_vals
        mismatch_count = mismatches.sum()
        total_comparisons += len(baseline_df)
        
        if mismatch_count > 0:
            diff_count += mismatch_count
            if diff_count <= 5:  # 只显示前5个差异
                print(f"\n⚠️ 列 '{col}' 有 {mismatch_count} 处差异:")
                diff_indices = baseline_df[mismatches].index[:3]
                for idx in diff_indices:
                    print(f"   行{idx}: 基准={baseline_df.loc[idx, col]}, 优化={optimized_df.loc[idx, col]}")
    
    if diff_count == 0:
        print("\n✅✅✅ 所有数据完全一致！优化验证通过！")
        return True
    else:
        print(f"\n❌ 共有 {diff_count} 处数据差异")
        print(f"   差异率: {diff_count/total_comparisons*100:.2f}%" if total_comparisons > 0 else "")
        return False

def main():
    print("=" * 60)
    print("印尼拍拍指标 - 优化后代码验证")
    print("=" * 60)
    
    # 连接数据库
    print("\n[1/3] 连接印尼 Presto...")
    pq = PrestoQuery()
    pq.login_process()
    print("  连接成功")
    
    # 执行优化后的SQL
    print("\n[2/3] 执行优化后的SQL...")
    print("  SQL较长，预计执行时间：60-120秒")
    
    optimized_df = submit_sql(pq, OPTIMIZED_SQL, "优化后SQL")
    
    if optimized_df is None or not isinstance(optimized_df, pd.DataFrame):
        print("❌ 优化后SQL执行失败")
        return
    
    # 对比结果
    print("\n[3/3] 对比结果...")
    is_match = compare_results(baseline_df, optimized_df)
    
    # 保存优化后结果
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    optimized_path = os.path.join(OUTPUT_DIR, f"印尼拍拍_优化结果_{timestamp}.csv")
    optimized_df.to_csv(optimized_path, index=False, encoding='utf-8-sig')
    print(f"\n优化后结果已保存: {optimized_path}")
    
    if is_match:
        print("\n🎉 优化验证完成！代码可安全使用！")
    else:
        print("\n⚠️ 验证失败，请检查差异！")

if __name__ == "__main__":
    main()