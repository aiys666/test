 
 with 
 base as (
 select 
 sum(spend)/31 as daily_avg_volume,
 sum(spend)/sum(install_cnt) as cps,
 sum(if_app) as if_app,
 sum(issue_cnt) as issue_cnt
 from ind.ys_daily_install_app
 where ad_date_month >= DATE_FORMAT(date_add('month',-1,CURRENT_DATE), '%Y-%m-01')
 and ad_date_month < DATE_FORMAT(date_add('month',0,CURRENT_DATE), '%Y-%m-01')
 ),

 base_app_new as (
 select  
 sum(issue_contract_amount_usd)/sum(issue_cnt_from_issue) as first_loan_avg_amount,
 sum(in_confirm_cnt)/sum(if_app) as first_f_confirm_rate,
 sum(pass_cnt)/sum(confirm_passed_cnt) as first_s_confirm_rate,
  sum(in_confirm_cnt)/sum(if_app)*sum(pass_cnt)/sum(confirm_passed_cnt) as pass_rate,
  sum(issue_contract_amount_usd) as first_loan_amt,

 from ind.ys_daily_app_should
 where issue_month >= DATE_FORMAT(date_add('month',-1,CURRENT_DATE), '%Y-%m-01')
 and issue_month < DATE_FORMAT(date_add('month',0,CURRENT_DATE), '%Y-%m-01')
 and grant_strategy='NEW'

 )





 select  '1_daily_avg_volume' as type, 
 daily_avg_volume 
 from base
 union all
 select  '2_cps' as type, 
 cps 
 from base
 union all
 select  '3_if_app' as type, 
 if_app 
 from base
 union all
 select  '4_issue_cnt' as type, 
 issue_cnt 
 from base


 


    COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date) AS ad_date,
    to_char(date_trunc('month', COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date)), 'yyyy-mm-dd') AS ad_date_month,
    to_char(date_trunc('week', COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date)), 'yyyy-mm-dd') AS ad_date_week,
    COALESCE(a.media_source, b.media_source, c.media_source, d.media_source2, e.media_source2) AS media_source,
    COALESCE(a.spend, 0) AS spend,
    COALESCE(b.install_cnt, 0) AS install_cnt,
    COALESCE(c.reg_cnt, 0) AS reg_cnt,
    COALESCE(d.if_app, 0) AS if_app,
    COALESCE(e.issue_cnt, 0) AS issue_cnt,
    COALESCE(e.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(e.issue_cnt_1_4, 0) AS issue_cnt_1_4




    WITH overall_data AS (
    SELECT app_month,
           sum(issue_contract_amount_usd) as contract_amount_usd, 
           sum(case when grant_strategy='OLD' then issue_contract_amount else 0 end )/sum(issue_contract_amount) as contract_amount_old_rate,
           sum(issue_haircut_amount)*1.0000/SUM(issue_contract_amount)+(SUM(issue_interest)*1.0000/SUM(issue_contract_amount))*(1-SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount)) as ov_coll_fee_rate,
           SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount) as ov_bad_debt_rate
    FROM ind.ba_apply_should_result
    GROUP BY 1
),
fl_data AS (
    SELECT app_month,
           sum(in_confirm_cnt_1_2)*1.0000/sum(in_confirm_cnt) as fl_in_confirm_cnt_1_2_rate,
           sum(issue_contract_amount_usd)*1.0000/sum(issue_cnt_from_issue) as fl_issue_per_usd,
           sum(issue_cnt_from_issue) as fl_issue_cnt,
           (sum(in_confirm_cnt)*1.0000/sum(if_app))*(sum(pass_cnt)*1.0000/sum(confirm_passed_cnt)) as fl_pass_rate,
           sum(issue_contract_amount_usd) as fl_contract_amt_usd,
           sum(loan_cycle_amount)*1.0000/sum(issue_contract_amount) as fl_loan_cycle, 
           sum(issue_haircut_amount)*1.0000/SUM(issue_contract_amount)+(SUM(issue_interest)*1.0000/SUM(issue_contract_amount))*(1-SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount)) as fl_fee_rate,
           SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount) as fl_bad_debt_rate 
    FROM ind.ba_apply_should_result
    WHERE grant_strategy='NEW' 
    GROUP BY 1
),
rl_data AS (
    SELECT app_month,
           sum(issue_contract_amount_usd)*1.0000/sum(issue_cnt_from_issue) as rl_issue_per_usd,
           sum(issue_cnt_from_issue) as rl_issue_cnt,
           (sum(in_confirm_cnt)*1.0000/sum(if_app))*(sum(pass_cnt)*1.0000/sum(confirm_passed_cnt)) as rl_pass_rate,
           sum(issue_contract_amount_usd) as rl_contract_amt_usd,
           sum(loan_cycle_amount)*1.0000/sum(issue_contract_amount) as rl_loan_cycle, 
           sum(issue_haircut_amount)*1.0000/SUM(issue_contract_amount)+(SUM(issue_interest)*1.0000/SUM(issue_contract_amount))*(1-SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount)) as rl_fee_rate,
           SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount) as rl_bad_debt_rate 
    FROM ind.ba_apply_should_result
    WHERE grant_strategy='OLD' 
    GROUP BY 1
),
weshare_data AS (
    SELECT issue_month,
           SUM(CASE WHEN account_name IN ('Weshare','Weshare2') THEN contract_amount_usd1 ELSE 0 END) AS Weshare_amt
    FROM ind.ba_asset_base_info
    WHERE issue_month>='2025-01-01'
    GROUP BY 1
),
install_data AS (
    SELECT ad_date_month, 
           sum(spend)/count(distinct ad_date) as daily_avg_volume,
           sum(spend)/sum(issue_cnt) as cps,
           sum(issue_cnt_1_2) as issue_cnt_1_2,
           sum(spend)/sum(issue_cnt_1_4) as cps1_4,
           sum(issue_cnt) as issue_cnt,
           sum(spend) as spend,
           sum(contract_amount_usd) as contract_amount_usd,
           sum(spend)/sum(contract_amount_usd) as cust_cost
    FROM ind.ba_install_apply_result
    WHERE ad_date < CURRENT_DATE
    GROUP BY 1 
)

SELECT o.app_month,
       i.daily_avg_volume,
       i.cps,
       f.fl_in_confirm_cnt_1_2_rate,
       i.issue_cnt_1_2,
       f.fl_issue_per_usd,
       f.fl_issue_cnt,
       f.fl_pass_rate,
       f.fl_contract_amt_usd,
       f.fl_loan_cycle,
       f.fl_fee_rate,
       f.fl_bad_debt_rate,
       i.cust_cost,
       r.rl_issue_per_usd,
       r.rl_issue_cnt,
       r.rl_pass_rate,
       r.rl_contract_amt_usd,
       r.rl_loan_cycle,
       r.rl_fee_rate,
       r.rl_bad_debt_rate,
       o.contract_amount_usd,
       o.contract_amount_old_rate,
       w.Weshare_amt*1.0000/o.contract_amount_usd as Weshare_rate,
       w.Weshare_amt,
       o.ov_coll_fee_rate,
       o.ov_bad_debt_rate,
       i.spend/o.contract_amount_usd as ov_cust_cost
       
FROM overall_data o
LEFT JOIN fl_data f ON o.app_month = f.app_month
LEFT JOIN rl_data r ON o.app_month = r.app_month
LEFT JOIN weshare_data w ON o.app_month = w.issue_month
LEFT JOIN install_data i ON o.app_month = i.ad_date_month
ORDER BY o.app_month;