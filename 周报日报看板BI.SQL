
drop table if exists ind.ba_apply_should_result;
create table
if not exists ind.ba_apply_should_result as

WITH application_metrics AS ( 
    SELECT
        date(app_date) AS app_date,
        app_week,
        app_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
        media_source2,
        source_channel2,   


        sum(case when if_recall=0 then if_app end) if_app, 
        sum(if_in_confirm_final) AS in_confirm_cnt_final,
        sum(if_in_confirm_temp) AS in_confirm_cnt,

        sum(case when new_grade_level IN ('1','2') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_4,
        sum(case when user_level IN ('1','2') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_2,
        sum(case when user_level IN ('1','2','3') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_3,
        sum(if_confirm_passed_final) AS confirm_passed_cnt,
        sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
        sum(if_confirm_passed_num_t7) AS if_confirm_passed_num_t7,
        SUM(case when if_in_confirm_final = 1 then grant_amount_max else NULL end) AS in_confirm_grantcredit_amount_total,
        SUM(case when if_in_confirm_final = 1 then grantcredit_amount else NULL end) AS in_confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_grantcredit_amount else NULL end) AS confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_amount else NULL end) AS confirm_apply_amount,
        sum(if_pass) AS pass_cnt,
        count(distinct case when sign_date is not null then biz_id end) AS sign_cnt,
		sum(if_in_anti_fraud) AS if_in_anti_fraud,
        sum(if_anti_fraud_passed) AS if_anti_fraud_passed,
        sum(if_in_anti_fraud_weak) AS if_in_anti_fraud_weak,
        sum(if_anti_fraud_weak_passed) AS if_anti_fraud_weak_passed,
        sum(if_in_external_data_1) AS if_in_external_data_1,
        sum(if_external_data_1_passed) AS if_external_data_1_passed,
        sum(if_in_model) AS if_in_model, 
        sum(if_model_passed) AS if_model_passed, 
        sum(if_in_ai) AS if_in_ai,
        sum(if_ai_passed) AS if_ai_passed,
        sum(if_in_manual_check) AS if_in_manual_check,
        sum(if_in_manual_check_1) AS if_in_manual_check_1,
        sum(if_manual_check_1_passed) AS if_manual_check_1_passed,
        sum(if_in_manual_check_2) AS if_in_manual_check_2,
        sum(if_manual_check_2_passed) AS if_manual_check_2_passed,
        sum(if_in_external_data_pre2) AS if_in_external_data_pre2,
        sum(if_external_data_pre2_passed) AS if_external_data_pre2_passed,
        sum(if_in_external_data_2) AS if_in_external_data_2, 
        sum(if_external_data_2_passed) AS if_external_data_2_passed,
        sum(if_in_external_data_3) AS if_in_external_data_3, 
        sum(if_external_data_3_passed) AS if_external_data_3_passed1, 
        sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed 
                 when grant_strategy='NEW' then if_in_confirm_temp end) if_external_data_3_passed,
         sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 
                 when grant_strategy='NEW' then if_confirm_passed_final end) if_in_external_data_4,
        sum(if_external_data_4_passed ) as if_external_data_4_passed,
        sum(if_issue) AS issue_cnt_from_app,
        sum(is_released_within_24h) AS is_released_within_24h
    FROM ind.ba_asset_base_info
    WHERE date(app_date) >= DATE('2025-01-01')  
    AND date(app_date) < CURRENT_DATE
    -- AND if_app = 1
    GROUP BY 1,2,3,4,5,6,7,8,9,10



),
issue_metrics AS ( 
    SELECT
        date(issue_date) AS issue_date,
        issue_week,
        issue_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
        media_source2,
        source_channel2,
        sum(if_issue) AS issue_cnt_from_issue,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(case when user_level IN ('1','2') then if_issue else 0 end) AS rl_issue_cnt_1_2,
        sum(case when user_level IN ('1','2','3') then if_issue else 0 end) AS rl_issue_cnt_1_3,

        sum(haircut_amount) as issue_haircut_amount,
        sum(interest) as issue_interest,
        sum(revenue) as issue_revenue,
        sum(contract_amount) AS issue_contract_amount,
        sum(contract_amount_usd1) AS issue_contract_amount_usd,
     
        sum(case when grant_strategy = 'NEW' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_new,
        sum(case when grant_strategy = 'OLD' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_old,
        sum(overdue_amount_1_0) AS overdue_amount_1_0,
        sum(should_capital_1_0) AS should_capital_1_0,
        sum(overdue_amount_1_7) AS overdue_amount_1_7,
        sum(should_capital_1_7) AS should_capital_1_7,
        sum(overdue_amount_1_14) AS overdue_amount_1_14,
        sum(should_capital_1_14) AS should_capital_1_14,
        sum(overdue_amount_1_30) AS overdue_amount_1_30,
        sum(should_capital_1_30) AS should_capital_1_30,
        sum(overdue_amount_2_0) AS overdue_amount_2_0,
        sum(should_capital_2_0) AS should_capital_2_0,
        sum(overdue_amount_2_7) AS overdue_amount_2_7,
        sum(should_capital_2_7) AS should_capital_2_7,
        sum(overdue_amount_2_14) AS overdue_amount_2_14,
        sum(should_capital_2_14) AS should_capital_2_14,
        sum(overdue_amount_2_30) AS overdue_amount_2_30,
        sum(should_capital_2_30) AS should_capital_2_30,
        sum(overdue_amount_3_0) AS overdue_amount_3_0,
        sum(should_capital_3_0) AS should_capital_3_0,
        sum(overdue_amount_3_7) AS overdue_amount_3_7,
        sum(should_capital_3_7) AS should_capital_3_7,
        sum(overdue_amount_3_14) AS overdue_amount_3_14,
        sum(should_capital_3_14) AS should_capital_3_14,
        sum(overdue_amount_3_30) AS overdue_amount_3_30,
        sum(should_capital_3_30) AS should_capital_3_30,
        sum(overdue_amount_total_30) AS overdue_amount_total_30,
        sum(should_capital_total_30) AS should_capital_total_30,


        sum(loan_cycle_amount) AS loan_cycle_amount,
        sum(act_bad_debt_ratio*contract_amount) AS act_bad_debt_amt


    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    AND date(issue_date) >= DATE('2025-01-01') 
    AND date(issue_date) < CURRENT_DATE 
    GROUP BY 1,2,3,4,5,6,7,8,9,10


),



should_metrics AS (


    SELECT
    to_char(date_trunc('month',a.should_date),'yyyy-mm-dd') as should_month,
	to_char(date_trunc('week', a.should_date),'yyyy-mm-dd') as should_week,
    date(a.should_date) AS should_date,
    c.grant_strategy,
    c.product_tag,
    c.is_reloan2,
    c.new_grade_level,
    c.user_level,
    c.media_source2,
    c.source_channel2, 

    SUM(a.should_capital) AS should_capital, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.should_capital ELSE null END) AS should_capital_d0, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.should_capital ELSE null END) AS should_capital_d1,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.should_capital ELSE null END) AS should_capital_d7,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.should_capital ELSE null END) AS should_capital_d15,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.should_capital ELSE null END) AS should_capital_d30,
 
 
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d0, 
    SUM(CASE WHEN due_day <= 1  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.fact_capital ELSE 0 END) AS t1_capital_paid_d1,
    SUM(CASE WHEN due_day <= 7  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.fact_capital ELSE 0 END) AS t7_capital_paid_d7,
    SUM(CASE WHEN due_day <= 15 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t15_capital_paid_d15,
    SUM(CASE WHEN due_day <= 30 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t30_capital_paid_d30,

    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8  THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d7,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d15,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d30


 
FROM (
    SELECT  
        customer_id,
        camera_id AS biz_id, 
        should_date, 
        due_day, 
        SUM(should_amount) AS should_amount,
        SUM(should_capital) AS should_capital,
        SUM(should_interest) AS should_interest,
        SUM(should_fine) AS should_fine,
        SUM(fact_amount) AS fact_amount,
        SUM(fact_capital) AS fact_capital,
        SUM(fact_interest) AS fact_interest,
        SUM(fact_fine) AS fact_fine
    FROM ind.gqy_case_info_f
    WHERE is_due = 0
        AND should_date >= DATE('2025-01-01') 
        AND should_date < CURRENT_DATE
    GROUP BY 
        1,2,3,4

) a 
LEFT JOIN (
    SELECT 
        data_date,
        customer_id,
        MAX(max_due_day) AS cus_ovd_day
    FROM ind.gqy_daliy_case
    GROUP BY 1,2
    HAVING MAX(max_due_day) >= 1
) b ON a.customer_id = b.customer_id AND should_date = b.data_date
left join ind.ba_asset_base_info c 
on  TRY_CAST (a.biz_id AS BIGINT) = TRY_CAST (c.biz_id AS BIGINT)
WHERE b.customer_id IS NULL 
GROUP BY 1,2,3,4,5,6,7,8,9,10


),
data_date as (
    select distinct 
    date_mon,
    date_format(DATE_PARSE(data_date, '%Y%m%d'), '%Y-%m-01') AS data_month, 
    month_days,  
    day(DATE_ADD('day', -1, CURRENT_DATE)) as current_date_day,
    case when DATE_PARSE(month_end, '%Y%m%d')<DATE_TRUNC('month', CURRENT_DATE) 
    then day(DATE_PARSE(month_end, '%Y%m%d'))
    else day(DATE_ADD('day', -1, CURRENT_DATE))
    end as date_month_end_actual 
    from dim.dim_data_info
)

 


        SELECT 
    COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy) AS grant_strategy,
    COALESCE(a.product_tag, i.product_tag, s.product_tag) AS product_tag,
    COALESCE(a.is_reloan2, i.is_reloan2, s.is_reloan2) AS is_reloan2,
    COALESCE(a.new_grade_level, i.new_grade_level, s.new_grade_level) AS new_grade_level,
    COALESCE(a.user_level, i.user_level, s.user_level) AS user_level,
    COALESCE(a.media_source2, i.media_source2, s.media_source2) AS media_source,
    COALESCE(a.source_channel2, i.source_channel2, s.source_channel2) AS source_channel2,
    COALESCE(a.app_date, i.issue_date, s.should_date) AS app_date,
    COALESCE(a.app_week, i.issue_week, s.should_week) AS app_week,
    COALESCE(a.app_month, i.issue_month, s.should_month) AS app_month,  
    COALESCE(a.if_app, 0) AS if_app,
    COALESCE(a.in_confirm_cnt_final, 0) AS in_confirm_cnt_final,
    COALESCE(a.in_confirm_cnt, 0) AS in_confirm_cnt,
    COALESCE(a.in_confirm_cnt_1_2, 0) AS in_confirm_cnt_1_2,
    COALESCE(a.in_confirm_cnt_1_4, 0) AS in_confirm_cnt_1_4,
    COALESCE(a.rl_in_confirm_cnt_1_2, 0) AS rl_in_confirm_cnt_1_2,
    COALESCE(a.rl_in_confirm_cnt_1_3, 0) AS rl_in_confirm_cnt_1_3,

    COALESCE(a.confirm_passed_cnt, 0) AS confirm_passed_cnt,
    COALESCE(a.if_confirm_passed_num_t0, 0) AS if_confirm_passed_num_t0,
    COALESCE(a.if_confirm_passed_num_t7, 0) AS if_confirm_passed_num_t7,

    COALESCE(a.in_confirm_grantcredit_amount_total, 0) AS in_confirm_grantcredit_amount_total,
    COALESCE(a.in_confirm_grantcredit_amount, 0) AS in_confirm_grantcredit_amount,
    COALESCE(a.confirm_grantcredit_amount, 0) AS confirm_grantcredit_amount,
    COALESCE(a.confirm_apply_amount, 0) AS confirm_apply_amount,
    COALESCE(a.pass_cnt, 0) AS pass_cnt,
    COALESCE(a.sign_cnt, 0) AS sign_cnt,
	
    COALESCE(if_in_anti_fraud, 0) AS if_in_anti_fraud,
    COALESCE(if_anti_fraud_passed, 0) AS if_anti_fraud_passed,
    COALESCE(if_in_anti_fraud_weak, 0) AS if_in_anti_fraud_weak,
    COALESCE(if_anti_fraud_weak_passed, 0) AS if_anti_fraud_weak_passed,
    COALESCE(if_in_external_data_1, 0) AS if_in_external_data_1,
    COALESCE(if_external_data_1_passed, 0) AS if_external_data_1_passed,
    COALESCE(if_in_model, 0) AS if_in_model, 
    COALESCE(if_model_passed, 0) AS if_model_passed, 
    COALESCE(if_in_ai, 0) AS if_in_ai,
    COALESCE(if_ai_passed, 0) AS if_ai_passed,
    COALESCE(if_in_manual_check, 0) AS if_in_manual_check,
    COALESCE(if_in_manual_check_1, 0) AS if_in_manual_check_1,
    COALESCE(if_manual_check_1_passed, 0) AS if_manual_check_1_passed,
    COALESCE(if_in_manual_check_2, 0) AS if_in_manual_check_2,
    COALESCE(if_manual_check_2_passed, 0) AS if_manual_check_2_passed,
    COALESCE(if_in_external_data_pre2, 0) AS if_in_external_data_pre2,
    COALESCE(if_external_data_pre2_passed, 0) AS if_external_data_pre2_passed,
    COALESCE(if_in_external_data_2, 0) AS if_in_external_data_2, 
    COALESCE(if_external_data_2_passed, 0) AS if_external_data_2_passed,
    COALESCE(if_in_external_data_3, 0) AS if_in_external_data_3, 
    COALESCE(if_external_data_3_passed, 0) AS if_external_data_3_passed,
    COALESCE(if_in_external_data_4, 0) AS if_in_external_data_4, 
    COALESCE(if_external_data_4_passed, 0) AS if_external_data_4_passed,
 
    COALESCE(a.issue_cnt_from_app, 0) AS issue_cnt_from_app,
    COALESCE(a.is_released_within_24h, 0) AS is_released_within_24h, 
    COALESCE(i.issue_cnt_from_issue, 0) AS issue_cnt_from_issue,
    COALESCE(i.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(i.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(i.rl_issue_cnt_1_2, 0) AS rl_issue_cnt_1_2,
    COALESCE(i.rl_issue_cnt_1_3, 0) AS rl_issue_cnt_1_3,
    COALESCE(i.issue_contract_amount, 0) AS issue_contract_amount,
    COALESCE(i.issue_contract_amount_usd, 0) AS issue_contract_amount_usd,
    SUM(COALESCE(i.issue_contract_amount_usd, 0)) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='NEW'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_new_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='OLD'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_old_group,
    
    COALESCE(i.overdue_amount_1_0, 0) AS overdue_amount_1_0,
    COALESCE(i.should_capital_1_0, 0) AS should_capital_1_0,
    COALESCE(i.overdue_amount_1_7, 0) AS overdue_amount_1_7,
    COALESCE(i.should_capital_1_7, 0) AS should_capital_1_7,
    COALESCE(i.overdue_amount_1_14, 0) AS overdue_amount_1_14,
    COALESCE(i.should_capital_1_14, 0) AS should_capital_1_14,
    COALESCE(i.overdue_amount_1_30, 0) AS overdue_amount_1_30,
    COALESCE(i.should_capital_1_30, 0) AS should_capital_1_30, 
    COALESCE(i.overdue_amount_2_0, 0) AS overdue_amount_2_0,
    COALESCE(i.should_capital_2_0, 0) AS should_capital_2_0,
    COALESCE(i.overdue_amount_2_7, 0) AS overdue_amount_2_7,
    COALESCE(i.should_capital_2_7, 0) AS should_capital_2_7, 
    COALESCE(i.overdue_amount_2_30, 0) AS overdue_amount_2_30,
    COALESCE(i.should_capital_2_30, 0) AS should_capital_2_30, 
    COALESCE(s.should_capital_d0, 0) AS should_capital_d0, 
    COALESCE(s.should_capital_d1, 0) AS should_capital_d1,
    COALESCE(s.should_capital_d7, 0) AS should_capital_d7,
    COALESCE(s.should_capital_d15, 0) AS should_capital_d15,
    COALESCE(s.should_capital_d30, 0) AS should_capital_d30, 
    COALESCE(s.should_capital_d0 - s.t0_capital_paid_d0, 0) AS t0_capital_due_d0,
    COALESCE(s.should_capital_d1 - s.t1_capital_paid_d1, 0) AS t1_capital_due_d1,
    COALESCE(s.should_capital_d7 - s.t7_capital_paid_d7, 0) AS t7_capital_due_d7,
    COALESCE(s.should_capital_d15 - s.t15_capital_paid_d15, 0) AS t15_capital_due_d15,
    COALESCE(s.should_capital_d30 - s.t30_capital_paid_d30, 0) AS t30_capital_due_d30,
    COALESCE(s.t0_capital_paid_d7, 0) AS t0_capital_paid_d7,
    COALESCE(s.t0_capital_paid_d15, 0) AS t0_capital_paid_d15,
    COALESCE(s.t0_capital_paid_d30, 0) AS t0_capital_paid_d30,
    COALESCE(s.t7_capital_paid_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_d7,
    COALESCE(s.t15_capital_paid_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_d15,
    COALESCE(s.t30_capital_paid_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_d30,

    COALESCE(s.should_capital_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_due_d7,
    COALESCE(s.should_capital_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_due_d15,
    COALESCE(s.should_capital_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_due_d30,
    COALESCE(loan_cycle_amount, 0) AS loan_cycle_amount,
    COALESCE(issue_haircut_amount, 0) AS issue_haircut_amount,
    COALESCE(issue_interest, 0) AS issue_interest,
    COALESCE(issue_revenue, 0) AS issue_revenue,
    COALESCE(act_bad_debt_amt, 0) AS act_bad_debt_amt,
    total_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar  AS ov_total_amt_usd,
    fl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS fl_total_amt_usd,
    rl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS rl_total_amt_usd,
    month_days, 
    date_month_end_actual ,
    COALESCE(issue_contract_amount_usd_new, 0) AS issue_contract_amount_usd_new,
    COALESCE(issue_contract_amount_usd_old, 0) AS issue_contract_amount_usd_old
    

FROM application_metrics a
FULL JOIN issue_metrics i 
    ON a.grant_strategy = i.grant_strategy
    AND a.product_tag = i.product_tag
    AND a.is_reloan2 = i.is_reloan2
    AND a.new_grade_level = i.new_grade_level
    AND a.media_source2 = i.media_source2
    AND a.source_channel2 = i.source_channel2
    AND a.app_date = i.issue_date
    AND a.app_week = i.issue_week
    AND a.app_month = i.issue_month
    AND a.user_level = i.user_level

FULL JOIN should_metrics s
    ON COALESCE(a.grant_strategy, i.grant_strategy) = s.grant_strategy
    AND COALESCE(a.product_tag, i.product_tag) = s.product_tag
    AND COALESCE(a.is_reloan2, i.is_reloan2) = s.is_reloan2
    AND COALESCE(a.new_grade_level, i.new_grade_level) = s.new_grade_level
    AND COALESCE(a.media_source2, i.media_source2) = s.media_source2
    AND COALESCE(a.source_channel2, i.source_channel2) = s.source_channel2
    AND COALESCE(a.app_date, i.issue_date) = s.should_date
    AND COALESCE(a.app_week, i.issue_week) = s.should_week
    AND COALESCE(a.app_month, i.issue_month) = s.should_month
    AND COALESCE(a.user_level, i.user_level) = s.user_level
LEFT JOIN ind.ba_kpi_targets_m b
    ON COALESCE(a.app_month, i.issue_month, s.should_month) = b.month 
left join data_date c
    ON b.month = c.data_month 
LEFT JOIN dim.dim_exchange_rate_cost f1 ON c.date_mon = f1.month_id AND f1.account_currency = 'IDR'
;

 
 

drop table if exists ind.ba_install_apply_result;
create table
if not exists ind.ba_install_apply_result as

with spend AS (
    select 
        date(ad_date) as ad_date
        ,case when lower(campaign_name) like  '%ios%' or media_source='ASA' or lower(media_source) like '%ios%' then 'IOS'
                when media_source like '%oogle%' and lower(campaign_name) not like '%ios%' then 'Google'
                when media_source like '%acebook%' and lower(campaign_name) not like '%ios%' then 'Facebook'
                when media_source='organic' then 'Organic'  
                when media_source='Tiktok' then 'Tiktok'
                when media_source='Kwai' then 'Kwai'
                else 'other'
            end as media_source
        ,sum(spend_usd_discount) as spend
        from ind.tyn_ads_cost_discount a
        where ad_date >= date'2025-01-01'
        group by 1,2  
    union all
    select
        distinct
        ad_date,
        'Organic' as media_source,
        0 as spend
        from ind.tyn_ads_cost_discount  
        where ad_date >= date'2025-01-01'
    ),
install_cnt as (
    SELECT install_date,   
    case when media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source else 'other' end as media_source,

    sum(install_cnt) as install_cnt 
    FROM (
    SELECT 
    DATE(event_time + INTERVAL '7' HOUR) AS install_date,
    case 	   		
			when platform = 'ios'  then 'IOS'	
			when media_source='googleadwords_int' then 'Google'
             when media_source='Facebook Ads' or media_source='restricted' then 'Facebook'
             when media_source='organic' then 'Organic'
             when media_source = 'shareit_int' then 'Shareit'
             when  media_source = 'kreditlist_int' or (media_source = 'vfine_int' and partner like '%redi%'  ) 
             or 
             (media_source is null and partner = 'kreditlist')
             then 'kreditlist_int'
			 when media_source = 'vfine_int' or media_source = 'adecentptuo_int' then 'Vfine'
             when media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when media_source = 'kwaiforbusiness_int' then 'Kwai'
             when media_source = 'cashcashpro' then 'cashcashpro'
			 when media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when media_source = 'kredit pintal' then 'kp'
			 when media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(campaign, '^pp') then 'Novabeyond'
			 when media_source = 'pyxis_int' then 'pyxis'
			 when media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when media_source = 'Twitter' then 'twitter'
			 when media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' or partner ='appscuckoobd650' then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(partner) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when campaign like '%CookeAds_CPI%' then 'CookeAds_CPI'
			when campaign ='CookeAds_CPS' or lower(campaign) like '%cookeads%' then 'CookeAds_CPS'
			when partner = '19mobicn' then '19mobi'
			when campaign = 'Samire_Jan2025youmi' then 'youmi'
			when media_source ='yupaamj_int' then 'yup'
			--when regexp_like(campaign, '^pp') then 'Novabeyond'
			when media_source = 'mintegral_int' then 'mintegral_int'
			when lower(media_source) like '%grab%' then 'Grab'
			when media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(campaign) like '%runto%' then 'RUNTOA'
			when lower(campaign) like '%mejoy%'  then 'mejoy'
			when lower(campaign) like '%yolo%'  then 'yolo'
			when media_source ='LinkAja_ads' then 'LinkAja_ads'
			when media_source ='easycash01' then 'easycash01'
			when media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when media_source ='tangads' then 'tangads'
			when media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when media_source ='oppoglobal_int' then 'oppoglobal_int'
            when media_source like '%_int%' then 'other'
			 else 'Organic'
        end as media_source,
    COUNT(DISTINCT appsflyer_id) AS install_cnt
    FROM ods.s08_appsflyer_push_data
    WHERE  etl_date>='20250101' and event_name='install' 
    and date(event_time + INTERVAL '7' HOUR) >= date'2025-01-01'
    GROUP BY 1,2 
    )t
    GROUP BY 1,2 
     ),

 
reg_cnt as (
    select 
    reg_dt,
    case 
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source 
    when media_source='ASA' or lower(media_source) like '%ios%' then 'IOS' 
    else 'other'
    end as media_source, 
    count(distinct mid) reg_cnt
    from ind.tyn_reg_install_new
    where reg_dt >= date'2025-01-01'
    group by 1,2 
     ),
apply_cnt AS ( 
    SELECT
        date(app_date) as app_date,  
        media_source2, 
        sum(if_app) AS if_app  
    FROM ind.ba_asset_base_info 
    WHERE grant_strategy='NEW' 
    and if_app=1
    and if_recall=0
    and date(app_date) >= date'2025-01-01'
    GROUP BY 1,2 

),
issue_cnt AS ( 

    SELECT
        date(issue_date) as issue_date, 
        media_source2, 
        sum(if_issue) AS issue_cnt,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(contract_amount_usd) as contract_amount_usd
    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    and grant_strategy='NEW' 
    and date(issue_date) >= date'2025-01-01'
    GROUP BY 1,2
)
 
SELECT
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
    COALESCE(e.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(e.contract_amount_usd, 0) AS contract_amount_usd

FROM spend a
FULL OUTER JOIN install_cnt b ON a.ad_date = b.install_date AND a.media_source = b.media_source
FULL OUTER JOIN reg_cnt c ON a.ad_date = c.reg_dt AND a.media_source = c.media_source
FULL OUTER JOIN apply_cnt d ON a.ad_date = d.app_date AND a.media_source = d.media_source2
FULL OUTER JOIN issue_cnt e ON a.ad_date = e.issue_date AND a.media_source = e.media_source2;


  























  
drop table if exists ind.ba_apply_should_result;
create table
if not exists ind.ba_apply_should_result as

WITH application_metrics AS ( 
    SELECT
        date(app_date) AS app_date,
        app_week,
        app_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
        media_source2,
        source_channel2,  



        sum(case when if_recall=0 then if_app end) if_app, 
        sum(if_in_confirm_final) AS in_confirm_cnt_final,
        sum(if_in_confirm_temp) AS in_confirm_cnt,

        sum(case when new_grade_level IN ('1','2') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_4,
        sum(case when user_level IN ('1','2') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_2,
        sum(case when user_level IN ('1','2','3') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_3,
        sum(if_confirm_passed_final) AS confirm_passed_cnt,
        sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
        sum(if_confirm_passed_num_t7) AS if_confirm_passed_num_t7,
        SUM(case when if_in_confirm_final = 1 then grant_amount_max else NULL end) AS in_confirm_grantcredit_amount_total,
        SUM(case when if_in_confirm_final = 1 then grantcredit_amount else NULL end) AS in_confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_grantcredit_amount else NULL end) AS confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_amount else NULL end) AS confirm_apply_amount,
        sum(if_pass) AS pass_cnt,
        count(distinct case when sign_date is not null then biz_id end) AS sign_cnt,
		sum(if_in_anti_fraud) AS if_in_anti_fraud,
        sum(if_anti_fraud_passed) AS if_anti_fraud_passed,
        sum(if_in_anti_fraud_weak) AS if_in_anti_fraud_weak,
        sum(if_anti_fraud_weak_passed) AS if_anti_fraud_weak_passed,
        sum(if_in_external_data_1) AS if_in_external_data_1,
        sum(if_external_data_1_passed) AS if_external_data_1_passed,
        sum(if_in_model) AS if_in_model, 
        sum(if_model_passed) AS if_model_passed, 
        sum(if_in_ai) AS if_in_ai,
        sum(if_ai_passed) AS if_ai_passed,
        sum(if_in_manual_check) AS if_in_manual_check,
        sum(if_in_manual_check_1) AS if_in_manual_check_1,
        sum(if_manual_check_1_passed) AS if_manual_check_1_passed,
        sum(if_in_manual_check_2) AS if_in_manual_check_2,
        sum(if_manual_check_2_passed) AS if_manual_check_2_passed,
        sum(if_in_external_data_pre2) AS if_in_external_data_pre2,
        sum(if_external_data_pre2_passed) AS if_external_data_pre2_passed,
        sum(if_in_external_data_2) AS if_in_external_data_2, 
        sum(if_external_data_2_passed) AS if_external_data_2_passed,
        sum(if_in_external_data_3) AS if_in_external_data_3, 
        sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed 
                 when grant_strategy='NEW' then if_in_confirm_temp end) if_external_data_3_passed,
         sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 
                 when grant_strategy='NEW' then if_confirm_passed_final end) if_in_external_data_4,
        sum(if_external_data_4_passed ) as if_external_data_4_passed,
        sum(if_issue) AS issue_cnt_from_app,
        sum(is_released_within_24h) AS is_released_within_24h
    FROM ind.ba_asset_base_info
    WHERE date(app_date) >= DATE('2025-01-01')  
    AND date(app_date) < CURRENT_DATE
    -- AND if_app = 1
    GROUP BY 1,2,3,4,5,6,7,8,9,10




),
issue_metrics AS ( 
    SELECT
        date(issue_date) AS issue_date,
        issue_week,
        issue_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
        media_source2,
        source_channel2,

        sum(if_issue) AS issue_cnt_from_issue,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(case when user_level IN ('1','2') then if_issue else 0 end) AS rl_issue_cnt_1_2,
        sum(case when user_level IN ('1','2','3') then if_issue else 0 end) AS rl_issue_cnt_1_3,

        sum(haircut_amount) as issue_haircut_amount,
        sum(interest) as issue_interest,
        sum(revenue) as issue_revenue,
        sum(contract_amount) AS issue_contract_amount,
        sum(contract_amount_usd1) AS issue_contract_amount_usd,
     
        sum(case when grant_strategy = 'NEW' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_new,
        sum(case when grant_strategy = 'OLD' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_old,
        sum(overdue_amount_1_0) AS overdue_amount_1_0,
        sum(should_capital_1_0) AS should_capital_1_0,
        sum(overdue_amount_1_7) AS overdue_amount_1_7,
        sum(should_capital_1_7) AS should_capital_1_7,
        sum(overdue_amount_1_14) AS overdue_amount_1_14,
        sum(should_capital_1_14) AS should_capital_1_14,
        sum(overdue_amount_1_30) AS overdue_amount_1_30,
        sum(should_capital_1_30) AS should_capital_1_30,
        sum(overdue_amount_2_0) AS overdue_amount_2_0,
        sum(should_capital_2_0) AS should_capital_2_0,
        sum(overdue_amount_2_7) AS overdue_amount_2_7,
        sum(should_capital_2_7) AS should_capital_2_7,
        sum(overdue_amount_2_14) AS overdue_amount_2_14,
        sum(should_capital_2_14) AS should_capital_2_14,
        sum(overdue_amount_2_30) AS overdue_amount_2_30,
        sum(should_capital_2_30) AS should_capital_2_30,
        sum(overdue_amount_3_0) AS overdue_amount_3_0,
        sum(should_capital_3_0) AS should_capital_3_0,
        sum(overdue_amount_3_7) AS overdue_amount_3_7,
        sum(should_capital_3_7) AS should_capital_3_7,
        sum(overdue_amount_3_14) AS overdue_amount_3_14,
        sum(should_capital_3_14) AS should_capital_3_14,
        sum(overdue_amount_3_30) AS overdue_amount_3_30,
        sum(should_capital_3_30) AS should_capital_3_30,
        sum(overdue_amount_total_30) AS overdue_amount_total_30,
        sum(should_capital_total_30) AS should_capital_total_30,

        sum(loan_cycle_amount) AS loan_cycle_amount,
        sum(act_bad_debt_ratio*contract_amount) AS act_bad_debt_amt


    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    AND date(issue_date) >= DATE('2025-01-01') 
    AND date(issue_date) < CURRENT_DATE 
    GROUP BY 1,2,3,4,5,6,7,8,9,10



),



should_metrics AS (


    SELECT
    to_char(date_trunc('month',a.should_date),'yyyy-mm-dd') as should_month,
	to_char(date_trunc('week', a.should_date),'yyyy-mm-dd') as should_week,
    date(a.should_date) AS should_date,
    c.grant_strategy,
    c.product_tag,
    c.is_reloan2,
    c.new_grade_level,
    c.user_level,
    c.media_source2,
    c.source_channel2, 


    SUM(a.should_capital) AS should_capital, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.should_capital ELSE null END) AS should_capital_d0, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.should_capital ELSE null END) AS should_capital_d1,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.should_capital ELSE null END) AS should_capital_d7,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.should_capital ELSE null END) AS should_capital_d15,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.should_capital ELSE null END) AS should_capital_d30,
 
 
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d0, 
    SUM(CASE WHEN due_day <= 1  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.fact_capital ELSE 0 END) AS t1_capital_paid_d1,
    SUM(CASE WHEN due_day <= 7  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.fact_capital ELSE 0 END) AS t7_capital_paid_d7,
    SUM(CASE WHEN due_day <= 15 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t15_capital_paid_d15,
    SUM(CASE WHEN due_day <= 30 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t30_capital_paid_d30,

    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8  THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d7,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d15,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d30


 
FROM (
    SELECT  
        customer_id,
        camera_id AS biz_id, 
        should_date, 
        due_day, 
        SUM(should_amount) AS should_amount,
        SUM(should_capital) AS should_capital,
        SUM(should_interest) AS should_interest,
        SUM(should_fine) AS should_fine,
        SUM(fact_amount) AS fact_amount,
        SUM(fact_capital) AS fact_capital,
        SUM(fact_interest) AS fact_interest,
        SUM(fact_fine) AS fact_fine
    FROM ind.gqy_case_info_f
    WHERE is_due = 0
        AND should_date >= DATE('2025-01-01') 
        AND should_date < CURRENT_DATE
    GROUP BY 
        1,2,3,4

) a 
LEFT JOIN (
    SELECT 
        data_date,
        customer_id,
        MAX(max_due_day) AS cus_ovd_day
    FROM ind.gqy_daliy_case
    GROUP BY 1,2
    HAVING MAX(max_due_day) >= 1
) b ON a.customer_id = b.customer_id AND should_date = b.data_date
left join ind.ba_asset_base_info c 
on  TRY_CAST (a.biz_id AS BIGINT) = TRY_CAST (c.biz_id AS BIGINT)
WHERE b.customer_id IS NULL 
GROUP BY 1,2,3,4,5,6,7,8,9,10



),
data_date as (
    select distinct 
    date_mon,
    date_format(DATE_PARSE(data_date, '%Y%m%d'), '%Y-%m-01') AS data_month, 
    month_days,  
    day(DATE_ADD('day', -1, CURRENT_DATE)) as current_date_day,
    case when DATE_PARSE(month_end, '%Y%m%d')<DATE_TRUNC('month', CURRENT_DATE) 
    then day(DATE_PARSE(month_end, '%Y%m%d'))
    else day(DATE_ADD('day', -1, CURRENT_DATE))
    end as date_month_end_actual 
    from dim.dim_data_info
)

 


        SELECT 
    COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy) AS grant_strategy,
    COALESCE(a.product_tag, i.product_tag, s.product_tag) AS product_tag,
    COALESCE(a.is_reloan2, i.is_reloan2, s.is_reloan2) AS is_reloan2,
    COALESCE(a.new_grade_level, i.new_grade_level, s.new_grade_level) AS new_grade_level,
    COALESCE(a.user_level, i.user_level, s.user_level) AS user_level,
    COALESCE(a.media_source2, i.media_source2, s.media_source2) AS media_source,
    COALESCE(a.source_channel2, i.source_channel2, s.source_channel2) AS source_channel2, 


    COALESCE(a.app_date, i.issue_date, s.should_date) AS app_date,
    COALESCE(a.app_week, i.issue_week, s.should_week) AS app_week,
    COALESCE(a.app_month, i.issue_month, s.should_month) AS app_month,  
    COALESCE(a.if_app, 0) AS if_app,
    COALESCE(a.in_confirm_cnt_final, 0) AS in_confirm_cnt_final,
    COALESCE(a.in_confirm_cnt, 0) AS in_confirm_cnt,
    COALESCE(a.in_confirm_cnt_1_2, 0) AS in_confirm_cnt_1_2,
    COALESCE(a.in_confirm_cnt_1_4, 0) AS in_confirm_cnt_1_4,
    COALESCE(a.rl_in_confirm_cnt_1_2, 0) AS rl_in_confirm_cnt_1_2,
    COALESCE(a.rl_in_confirm_cnt_1_3, 0) AS rl_in_confirm_cnt_1_3,

    COALESCE(a.confirm_passed_cnt, 0) AS confirm_passed_cnt,
    COALESCE(a.if_confirm_passed_num_t0, 0) AS if_confirm_passed_num_t0,
    COALESCE(a.if_confirm_passed_num_t7, 0) AS if_confirm_passed_num_t7,

    COALESCE(a.in_confirm_grantcredit_amount_total, 0) AS in_confirm_grantcredit_amount_total,
    COALESCE(a.in_confirm_grantcredit_amount, 0) AS in_confirm_grantcredit_amount,
    COALESCE(a.confirm_grantcredit_amount, 0) AS confirm_grantcredit_amount,
    COALESCE(a.confirm_apply_amount, 0) AS confirm_apply_amount,
    COALESCE(a.pass_cnt, 0) AS pass_cnt,
    COALESCE(a.sign_cnt, 0) AS sign_cnt,
	
    COALESCE(if_in_anti_fraud, 0) AS if_in_anti_fraud,
    COALESCE(if_anti_fraud_passed, 0) AS if_anti_fraud_passed,
    COALESCE(if_in_anti_fraud_weak, 0) AS if_in_anti_fraud_weak,
    COALESCE(if_anti_fraud_weak_passed, 0) AS if_anti_fraud_weak_passed,
    COALESCE(if_in_external_data_1, 0) AS if_in_external_data_1,
    COALESCE(if_external_data_1_passed, 0) AS if_external_data_1_passed,
    COALESCE(if_in_model, 0) AS if_in_model, 
    COALESCE(if_model_passed, 0) AS if_model_passed, 
    COALESCE(if_in_ai, 0) AS if_in_ai,
    COALESCE(if_ai_passed, 0) AS if_ai_passed,
    COALESCE(if_in_manual_check, 0) AS if_in_manual_check,
    COALESCE(if_in_manual_check_1, 0) AS if_in_manual_check_1,
    COALESCE(if_manual_check_1_passed, 0) AS if_manual_check_1_passed,
    COALESCE(if_in_manual_check_2, 0) AS if_in_manual_check_2,
    COALESCE(if_manual_check_2_passed, 0) AS if_manual_check_2_passed,
    COALESCE(if_in_external_data_pre2, 0) AS if_in_external_data_pre2,
    COALESCE(if_external_data_pre2_passed, 0) AS if_external_data_pre2_passed,
    COALESCE(if_in_external_data_2, 0) AS if_in_external_data_2, 
    COALESCE(if_external_data_2_passed, 0) AS if_external_data_2_passed,
    COALESCE(if_in_external_data_3, 0) AS if_in_external_data_3, 
    COALESCE(if_external_data_3_passed, 0) AS if_external_data_3_passed,
    COALESCE(if_in_external_data_4, 0) AS if_in_external_data_4, 
    COALESCE(if_external_data_4_passed, 0) AS if_external_data_4_passed,
 
    COALESCE(a.issue_cnt_from_app, 0) AS issue_cnt_from_app,
    COALESCE(a.is_released_within_24h, 0) AS is_released_within_24h, 
    COALESCE(i.issue_cnt_from_issue, 0) AS issue_cnt_from_issue,
    COALESCE(i.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(i.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(i.rl_issue_cnt_1_2, 0) AS rl_issue_cnt_1_2,
    COALESCE(i.rl_issue_cnt_1_3, 0) AS rl_issue_cnt_1_3,
    COALESCE(i.issue_contract_amount, 0) AS issue_contract_amount,
    COALESCE(i.issue_contract_amount_usd, 0) AS issue_contract_amount_usd,
    SUM(COALESCE(i.issue_contract_amount_usd, 0)) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='NEW'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_new_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='OLD'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_old_group,
    
    COALESCE(i.overdue_amount_1_0, 0) AS overdue_amount_1_0,
    COALESCE(i.should_capital_1_0, 0) AS should_capital_1_0,
    COALESCE(i.overdue_amount_1_7, 0) AS overdue_amount_1_7,
    COALESCE(i.should_capital_1_7, 0) AS should_capital_1_7,
    COALESCE(i.overdue_amount_1_14, 0) AS overdue_amount_1_14,
    COALESCE(i.should_capital_1_14, 0) AS should_capital_1_14,
    COALESCE(i.overdue_amount_1_30, 0) AS overdue_amount_1_30,
    COALESCE(i.should_capital_1_30, 0) AS should_capital_1_30, 
    COALESCE(i.overdue_amount_2_0, 0) AS overdue_amount_2_0,
    COALESCE(i.should_capital_2_0, 0) AS should_capital_2_0,
    COALESCE(i.overdue_amount_2_7, 0) AS overdue_amount_2_7,
    COALESCE(i.should_capital_2_7, 0) AS should_capital_2_7, 
    COALESCE(i.overdue_amount_2_30, 0) AS overdue_amount_2_30,
    COALESCE(i.should_capital_2_30, 0) AS should_capital_2_30,
    COALESCE(i.overdue_amount_3_0, 0) AS overdue_amount_3_0,
    COALESCE(i.should_capital_3_0, 0) AS should_capital_3_0,
    COALESCE(i.overdue_amount_3_30, 0) AS overdue_amount_3_30,
    COALESCE(i.should_capital_3_30, 0) AS should_capital_3_30,

    COALESCE(overdue_amount_total_30, 0) AS overdue_amount_total_30,
    COALESCE(should_capital_total_30, 0) AS should_capital_total_30,



    COALESCE(s.should_capital_d0, 0) AS should_capital_d0, 
    COALESCE(s.should_capital_d1, 0) AS should_capital_d1,
    COALESCE(s.should_capital_d7, 0) AS should_capital_d7,
    COALESCE(s.should_capital_d15, 0) AS should_capital_d15,
    COALESCE(s.should_capital_d30, 0) AS should_capital_d30,




    COALESCE(s.should_capital_d0 - s.t0_capital_paid_d0, 0) AS t0_capital_due_d0,
    COALESCE(s.should_capital_d1 - s.t1_capital_paid_d1, 0) AS t1_capital_due_d1,
    COALESCE(s.should_capital_d7 - s.t7_capital_paid_d7, 0) AS t7_capital_due_d7,
    COALESCE(s.should_capital_d15 - s.t15_capital_paid_d15, 0) AS t15_capital_due_d15,
    COALESCE(s.should_capital_d30 - s.t30_capital_paid_d30, 0) AS t30_capital_due_d30,
    COALESCE(s.t0_capital_paid_d7, 0) AS t0_capital_paid_d7,
    COALESCE(s.t0_capital_paid_d15, 0) AS t0_capital_paid_d15,
    COALESCE(s.t0_capital_paid_d30, 0) AS t0_capital_paid_d30,
    COALESCE(s.t7_capital_paid_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_d7,
    COALESCE(s.t15_capital_paid_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_d15,
    COALESCE(s.t30_capital_paid_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_d30,

    COALESCE(s.should_capital_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_due_d7,
    COALESCE(s.should_capital_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_due_d15,
    COALESCE(s.should_capital_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_due_d30,
    COALESCE(loan_cycle_amount, 0) AS loan_cycle_amount,
    COALESCE(issue_haircut_amount, 0) AS issue_haircut_amount,
    COALESCE(issue_interest, 0) AS issue_interest,
    COALESCE(issue_revenue, 0) AS issue_revenue,
    COALESCE(act_bad_debt_amt, 0) AS act_bad_debt_amt,
    total_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar  AS ov_total_amt_usd,
    fl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS fl_total_amt_usd,
    rl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS rl_total_amt_usd,
    month_days, 
    date_month_end_actual ,
    COALESCE(issue_contract_amount_usd_new, 0) AS issue_contract_amount_usd_new,
    COALESCE(issue_contract_amount_usd_old, 0) AS issue_contract_amount_usd_old
    

FROM application_metrics a
FULL JOIN issue_metrics i 
    ON a.grant_strategy = i.grant_strategy
    AND a.product_tag = i.product_tag
    AND a.is_reloan2 = i.is_reloan2
    AND a.new_grade_level = i.new_grade_level
    AND a.media_source2 = i.media_source2
    AND a.source_channel2 = i.source_channel2
    AND a.app_date = i.issue_date
    AND a.app_week = i.issue_week
    AND a.app_month = i.issue_month
    AND a.user_level = i.user_level 


FULL JOIN should_metrics s
    ON COALESCE(a.grant_strategy, i.grant_strategy) = s.grant_strategy
    AND COALESCE(a.product_tag, i.product_tag) = s.product_tag
    AND COALESCE(a.is_reloan2, i.is_reloan2) = s.is_reloan2
    AND COALESCE(a.new_grade_level, i.new_grade_level) = s.new_grade_level
    AND COALESCE(a.media_source2, i.media_source2) = s.media_source2
    AND COALESCE(a.source_channel2, i.source_channel2) = s.source_channel2
    AND COALESCE(a.app_date, i.issue_date) = s.should_date
    AND COALESCE(a.app_week, i.issue_week) = s.should_week
    AND COALESCE(a.app_month, i.issue_month) = s.should_month
    AND COALESCE(a.user_level, i.user_level) = s.user_level 


LEFT JOIN ind.ba_kpi_targets_m b
    ON COALESCE(a.app_month, i.issue_month, s.should_month) = b.month 
left join data_date c
    ON b.month = c.data_month 
LEFT JOIN dim.dim_exchange_rate_cost f1 ON c.date_mon = f1.month_id AND f1.account_currency = 'IDR'
;

 
 

drop table if exists ind.ba_install_apply_result;
create table
if not exists ind.ba_install_apply_result as

with spend AS (
    select 
        date(ad_date) as ad_date
        ,case when lower(campaign_name) like  '%ios%' or media_source='ASA' or lower(media_source) like '%ios%' then 'IOS'
                when media_source like '%oogle%' and lower(campaign_name) not like '%ios%' then 'Google'
                when media_source like '%acebook%' and lower(campaign_name) not like '%ios%' then 'Facebook'
                when media_source='organic' then 'Organic'  
                when media_source='Tiktok' then 'Tiktok'
                when media_source='Kwai' then 'Kwai'
                else 'other'
            end as media_source
        ,sum(spend_usd_discount) as spend
        from ind.tyn_ads_cost_discount a
        where ad_date >= date'2025-01-01'
        group by 1,2  
    union all
    select
        distinct
        ad_date,
        'Organic' as media_source,
        0 as spend
        from ind.tyn_ads_cost_discount  
        where ad_date >= date'2025-01-01'
    ),
install_cnt as (
    SELECT install_date,   
    case when media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source else 'other' end as media_source,

    sum(install_cnt) as install_cnt 
    FROM (
    SELECT 
    DATE(event_time + INTERVAL '7' HOUR) AS install_date,
    case 	   		
			when platform = 'ios'  then 'IOS'	
			when media_source='googleadwords_int' then 'Google'
             when media_source='Facebook Ads' or media_source='restricted' then 'Facebook'
             when media_source='organic' then 'Organic'
             when media_source = 'shareit_int' then 'Shareit'
             when  media_source = 'kreditlist_int' or (media_source = 'vfine_int' and partner like '%redi%'  ) 
             or 
             (media_source is null and partner = 'kreditlist')
             then 'kreditlist_int'
			 when media_source = 'vfine_int' or media_source = 'adecentptuo_int' then 'Vfine'
             when media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when media_source = 'kwaiforbusiness_int' then 'Kwai'
             when media_source = 'cashcashpro' then 'cashcashpro'
			 when media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when media_source = 'kredit pintal' then 'kp'
			 when media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(campaign, '^pp') then 'Novabeyond'
			 when media_source = 'pyxis_int' then 'pyxis'
			 when media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when media_source = 'Twitter' then 'twitter'
			 when media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' or partner ='appscuckoobd650' then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(partner) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when campaign like '%CookeAds_CPI%' then 'CookeAds_CPI'
			when campaign ='CookeAds_CPS' or lower(campaign) like '%cookeads%' then 'CookeAds_CPS'
			when partner = '19mobicn' then '19mobi'
			when campaign = 'Samire_Jan2025youmi' then 'youmi'
			when media_source ='yupaamj_int' then 'yup'
			--when regexp_like(campaign, '^pp') then 'Novabeyond'
			when media_source = 'mintegral_int' then 'mintegral_int'
			when lower(media_source) like '%grab%' then 'Grab'
			when media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(campaign) like '%runto%' then 'RUNTOA'
			when lower(campaign) like '%mejoy%'  then 'mejoy'
			when lower(campaign) like '%yolo%'  then 'yolo'
			when media_source ='LinkAja_ads' then 'LinkAja_ads'
			when media_source ='easycash01' then 'easycash01'
			when media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when media_source ='tangads' then 'tangads'
			when media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when media_source ='oppoglobal_int' then 'oppoglobal_int'
            when media_source like '%_int%' then 'other'
			 else 'Organic'
        end as media_source,
    COUNT(DISTINCT appsflyer_id) AS install_cnt
    FROM ods.s08_appsflyer_push_data
    WHERE  etl_date>='20250101' and event_name='install' 
    and date(event_time + INTERVAL '7' HOUR) >= date'2025-01-01'
    GROUP BY 1,2 
    )t
    GROUP BY 1,2 
     ),

 
reg_cnt as (
    select 
    reg_dt,
    case 
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source 
    when media_source='ASA' or lower(media_source) like '%ios%' then 'IOS' 
    else 'other'
    end as media_source, 
    count(distinct mid) reg_cnt
    from ind.tyn_reg_install_new
    where reg_dt >= date'2025-01-01'
    group by 1,2 
     ),
apply_cnt AS ( 
    SELECT
        date(app_date) as app_date,  
        media_source2, 
        sum(if_app) AS if_app  
    FROM ind.ba_asset_base_info 
    WHERE grant_strategy='NEW' 
    and if_app=1
    and if_recall=0
    and date(app_date) >= date'2025-01-01'
    GROUP BY 1,2 

),
issue_cnt AS ( 

    SELECT
        date(issue_date) as issue_date, 
        media_source2, 
        sum(if_issue) AS issue_cnt,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(contract_amount_usd) as contract_amount_usd
    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    and grant_strategy='NEW' 
    and date(issue_date) >= date'2025-01-01'
    GROUP BY 1,2
)
 
SELECT
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
    COALESCE(e.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(e.contract_amount_usd, 0) AS contract_amount_usd

FROM spend a
FULL OUTER JOIN install_cnt b ON a.ad_date = b.install_date AND a.media_source = b.media_source
FULL OUTER JOIN reg_cnt c ON a.ad_date = c.reg_dt AND a.media_source = c.media_source
FULL OUTER JOIN apply_cnt d ON a.ad_date = d.app_date AND a.media_source = d.media_source2
FULL OUTER JOIN issue_cnt e ON a.ad_date = e.issue_date AND a.media_source = e.media_source2;


  






  



  -------- 2025-11-28 









drop table if exists ind.ba_apply_should_result;
create table
if not exists ind.ba_apply_should_result as

WITH application_metrics AS ( 
    SELECT
        date(app_date) AS app_date,
        app_week,
        app_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
        media_source2,
        source_channel2,  
        case when if_regular_backup='1' then 1 else 0 end as if_regular_backup,
        case when if_backup_switch=1 then 1 else 0 end as if_backup_switch,



        sum(case when if_recall=0 then if_app end) if_app, 
        sum(if_in_confirm_final) AS in_confirm_cnt_final,
        sum(if_in_confirm_temp) AS in_confirm_cnt,

        sum(case when new_grade_level IN ('1','2') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_4,
        sum(case when user_level IN ('1','2') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_2,
        sum(case when user_level IN ('1','2','3') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_3,
        sum(if_confirm_passed_final) AS confirm_passed_cnt,
        sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
        sum(if_confirm_passed_num_t7) AS if_confirm_passed_num_t7,
        SUM(case when if_in_confirm_final = 1 then grant_amount_max else NULL end) AS in_confirm_grantcredit_amount_total,
        SUM(case when if_in_confirm_final = 1 then grantcredit_amount else NULL end) AS in_confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_grantcredit_amount else NULL end) AS confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_amount else NULL end) AS confirm_apply_amount, 
        SUM(case when if_confirm_passed_final= 1 and if_issue=1 then apply_grantcredit_amount else NULL end) AS issue_confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 and if_issue=1 then apply_amount else NULL end) AS issue_confirm_apply_amount, 
        sum(if_pass) AS pass_cnt,
        -- count(distinct case when sign_date is not null then biz_id end) AS sign_cnt,
		sum(if_in_anti_fraud) AS if_in_anti_fraud,
        sum(if_anti_fraud_passed) AS if_anti_fraud_passed,
        sum(if_in_anti_fraud_weak) AS if_in_anti_fraud_weak,
        sum(if_anti_fraud_weak_passed) AS if_anti_fraud_weak_passed,
        sum(if_in_external_data_1) AS if_in_external_data_1,
        sum(if_external_data_1_passed) AS if_external_data_1_passed,
        sum(if_in_model) AS if_in_model, 
        sum(if_model_passed) AS if_model_passed, 
        sum(if_in_ai) AS if_in_ai,
        sum(if_ai_passed) AS if_ai_passed,
        sum(if_in_manual_check) AS if_in_manual_check,
        sum(if_in_manual_check_1) AS if_in_manual_check_1,
        sum(if_manual_check_1_passed) AS if_manual_check_1_passed,
        sum(if_in_manual_check_2) AS if_in_manual_check_2,
        sum(if_manual_check_2_passed) AS if_manual_check_2_passed,
        sum(if_in_external_data_pre2) AS if_in_external_data_pre2,
        sum(if_external_data_pre2_passed) AS if_external_data_pre2_passed,
        sum(if_in_external_data_2) AS if_in_external_data_2, 
        sum(if_external_data_2_passed) AS if_external_data_2_passed,
        sum(if_in_external_data_3) AS if_in_external_data_3, 
        sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed 
                 when grant_strategy='NEW' then if_in_confirm_temp end) if_external_data_3_passed,
         sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 
                 when grant_strategy='NEW' then if_confirm_passed_final end) if_in_external_data_4,
        sum(if_external_data_4_passed ) as if_external_data_4_passed,
        sum(if_issue) AS issue_cnt_from_app,
        sum(is_released_within_24h) AS is_released_within_24h
    FROM ind.ba_asset_base_info
    WHERE date(app_date) >= DATE('2025-01-01')  
    AND date(app_date) < CURRENT_DATE
    -- AND if_app = 1
    GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12



),
issue_metrics AS ( 
    SELECT
        date(issue_date) AS issue_date,
        issue_week,
        issue_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
        media_source2,
        source_channel2,
        case when if_regular_backup='1' then 1 else 0 end as if_regular_backup,
        case when if_backup_switch=1 then 1 else 0 end as if_backup_switch,

        sum(if_issue) AS issue_cnt_from_issue,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(case when user_level IN ('1','2') then if_issue else 0 end) AS rl_issue_cnt_1_2,
        sum(case when user_level IN ('1','2','3') then if_issue else 0 end) AS rl_issue_cnt_1_3,

        sum(haircut_amount) as issue_haircut_amount,
        sum(interest) as issue_interest,
        sum(revenue) as issue_revenue,
        sum(contract_amount) AS issue_contract_amount,
        sum(contract_amount_usd1) AS issue_contract_amount_usd,
     
        sum(case when grant_strategy = 'NEW' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_new,
        sum(case when grant_strategy = 'OLD' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_old,
        sum(overdue_amount_1_0) AS overdue_amount_1_0,
        sum(should_capital_1_0) AS should_capital_1_0,
        sum(overdue_amount_1_7) AS overdue_amount_1_7,
        sum(should_capital_1_7) AS should_capital_1_7,
        sum(overdue_amount_1_14) AS overdue_amount_1_14,
        sum(should_capital_1_14) AS should_capital_1_14,
        sum(overdue_amount_1_30) AS overdue_amount_1_30,
        sum(should_capital_1_30) AS should_capital_1_30,
        sum(overdue_amount_2_0) AS overdue_amount_2_0,
        sum(should_capital_2_0) AS should_capital_2_0,
        sum(overdue_amount_2_7) AS overdue_amount_2_7,
        sum(should_capital_2_7) AS should_capital_2_7,
        sum(overdue_amount_2_14) AS overdue_amount_2_14,
        sum(should_capital_2_14) AS should_capital_2_14,
        sum(overdue_amount_2_30) AS overdue_amount_2_30,
        sum(should_capital_2_30) AS should_capital_2_30,
        sum(overdue_amount_3_0) AS overdue_amount_3_0,
        sum(should_capital_3_0) AS should_capital_3_0,
        sum(overdue_amount_3_7) AS overdue_amount_3_7,
        sum(should_capital_3_7) AS should_capital_3_7,
        sum(overdue_amount_3_14) AS overdue_amount_3_14,
        sum(should_capital_3_14) AS should_capital_3_14,
        sum(overdue_amount_3_30) AS overdue_amount_3_30,
        sum(should_capital_3_30) AS should_capital_3_30,
        sum(overdue_amount_total_30) AS overdue_amount_total_30,
        sum(should_capital_total_30) AS should_capital_total_30,

        sum(loan_cycle_amount) AS loan_cycle_amount
        -- ,
        -- sum(act_bad_debt_ratio*contract_amount) AS act_bad_debt_amt


    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    AND date(issue_date) >= DATE('2025-01-01') 
    AND date(issue_date) < CURRENT_DATE 
    GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12




),



should_metrics AS (


    SELECT
    to_char(date_trunc('month',a.should_date),'yyyy-mm-dd') as should_month,
	to_char(date_trunc('week', a.should_date),'yyyy-mm-dd') as should_week,
    date(a.should_date) AS should_date,
    c.grant_strategy,
    c.product_tag,
    c.is_reloan2,
    c.new_grade_level,
    c.user_level,
    c.media_source2,
    c.source_channel2, 
    case when c.if_regular_backup='1' then 1 else 0 end as if_regular_backup,
    case when c.if_backup_switch=1 then 1 else 0 end as if_backup_switch,


    SUM(a.should_capital) AS should_capital, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.should_capital ELSE null END) AS should_capital_d0, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.should_capital ELSE null END) AS should_capital_d1,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.should_capital ELSE null END) AS should_capital_d7,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.should_capital ELSE null END) AS should_capital_d15,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.should_capital ELSE null END) AS should_capital_d30,
 
 
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d0, 
    SUM(CASE WHEN due_day <= 1  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.fact_capital ELSE 0 END) AS t1_capital_paid_d1,
    SUM(CASE WHEN due_day <= 7  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.fact_capital ELSE 0 END) AS t7_capital_paid_d7,
    SUM(CASE WHEN due_day <= 15 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t15_capital_paid_d15,
    SUM(CASE WHEN due_day <= 30 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t30_capital_paid_d30,

    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8  THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d7,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d15,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d30


 
FROM (
    SELECT  
        customer_id,
        camera_id AS biz_id, 
        should_date, 
        due_day, 
        SUM(should_amount) AS should_amount,
        SUM(should_capital) AS should_capital,
        SUM(should_interest) AS should_interest,
        SUM(should_fine) AS should_fine,
        SUM(fact_amount) AS fact_amount,
        SUM(fact_capital) AS fact_capital,
        SUM(fact_interest) AS fact_interest,
        SUM(fact_fine) AS fact_fine
    FROM ind.gqy_case_info_f
    WHERE is_due = 0
        AND should_date >= DATE('2025-01-01') 
        AND should_date < CURRENT_DATE
    GROUP BY 
        1,2,3,4

) a 
LEFT JOIN (
    SELECT 
        data_date,
        customer_id,
        MAX(max_due_day) AS cus_ovd_day
    FROM ind.gqy_daliy_case
    GROUP BY 1,2
    HAVING MAX(max_due_day) >= 1
) b ON a.customer_id = b.customer_id AND should_date = b.data_date
left join ind.ba_asset_base_info c 
on  TRY_CAST (a.biz_id AS BIGINT) = TRY_CAST (c.biz_id AS BIGINT)
WHERE b.customer_id IS NULL 
GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12




),
data_date as (
    select distinct 
    date_mon,
    date_format(DATE_PARSE(data_date, '%Y%m%d'), '%Y-%m-01') AS data_month, 
    month_days,  
    day(DATE_ADD('day', -1, CURRENT_DATE)) as current_date_day,
    case when DATE_PARSE(month_end, '%Y%m%d')<DATE_TRUNC('month', CURRENT_DATE) 
    then day(DATE_PARSE(month_end, '%Y%m%d'))
    else day(DATE_ADD('day', -1, CURRENT_DATE))
    end as date_month_end_actual 
    from dim.dim_data_info
)

 


        SELECT 
    COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy) AS grant_strategy,
    COALESCE(a.product_tag, i.product_tag, s.product_tag) AS product_tag,
    COALESCE(a.is_reloan2, i.is_reloan2, s.is_reloan2) AS is_reloan2,
    COALESCE(a.new_grade_level, i.new_grade_level, s.new_grade_level) AS new_grade_level,
    COALESCE(a.user_level, i.user_level, s.user_level) AS user_level,
    COALESCE(a.media_source2, i.media_source2, s.media_source2) AS media_source,
    COALESCE(a.source_channel2, i.source_channel2, s.source_channel2) AS source_channel2, 
    COALESCE(a.if_regular_backup, 0) AS if_regular_backup,
    COALESCE(a.if_backup_switch, 0) AS if_backup_switch,



    COALESCE(a.app_date, i.issue_date, s.should_date) AS app_date,
    COALESCE(a.app_week, i.issue_week, s.should_week) AS app_week,
    COALESCE(a.app_month, i.issue_month, s.should_month) AS app_month,  
    COALESCE(a.if_app, 0) AS if_app,
    COALESCE(a.in_confirm_cnt_final, 0) AS in_confirm_cnt_final,
    COALESCE(a.in_confirm_cnt, 0) AS in_confirm_cnt,
    COALESCE(a.in_confirm_cnt_1_2, 0) AS in_confirm_cnt_1_2,
    COALESCE(a.in_confirm_cnt_1_4, 0) AS in_confirm_cnt_1_4,
    COALESCE(a.rl_in_confirm_cnt_1_2, 0) AS rl_in_confirm_cnt_1_2,
    COALESCE(a.rl_in_confirm_cnt_1_3, 0) AS rl_in_confirm_cnt_1_3,

    COALESCE(a.confirm_passed_cnt, 0) AS confirm_passed_cnt,
    COALESCE(a.if_confirm_passed_num_t0, 0) AS if_confirm_passed_num_t0,
    COALESCE(a.if_confirm_passed_num_t7, 0) AS if_confirm_passed_num_t7,

    COALESCE(a.in_confirm_grantcredit_amount_total, 0) AS in_confirm_grantcredit_amount_total,
    COALESCE(a.in_confirm_grantcredit_amount, 0) AS in_confirm_grantcredit_amount,
    COALESCE(a.confirm_grantcredit_amount, 0) AS confirm_grantcredit_amount,
    COALESCE(a.confirm_apply_amount, 0) AS confirm_apply_amount, 
    COALESCE(a.issue_confirm_grantcredit_amount, 0) AS issue_confirm_grantcredit_amount,
    COALESCE(a.issue_confirm_apply_amount, 0) AS issue_confirm_apply_amount,


    COALESCE(a.pass_cnt, 0) AS pass_cnt,
    COALESCE(a.sign_cnt, 0) AS sign_cnt,
	
    COALESCE(if_in_anti_fraud, 0) AS if_in_anti_fraud,
    COALESCE(if_anti_fraud_passed, 0) AS if_anti_fraud_passed,
    COALESCE(if_in_anti_fraud_weak, 0) AS if_in_anti_fraud_weak,
    COALESCE(if_anti_fraud_weak_passed, 0) AS if_anti_fraud_weak_passed,
    COALESCE(if_in_external_data_1, 0) AS if_in_external_data_1,
    COALESCE(if_external_data_1_passed, 0) AS if_external_data_1_passed,
    COALESCE(if_in_model, 0) AS if_in_model, 
    COALESCE(if_model_passed, 0) AS if_model_passed, 
    COALESCE(if_in_ai, 0) AS if_in_ai,
    COALESCE(if_ai_passed, 0) AS if_ai_passed,
    COALESCE(if_in_manual_check, 0) AS if_in_manual_check,
    COALESCE(if_in_manual_check_1, 0) AS if_in_manual_check_1,
    COALESCE(if_manual_check_1_passed, 0) AS if_manual_check_1_passed,
    COALESCE(if_in_manual_check_2, 0) AS if_in_manual_check_2,
    COALESCE(if_manual_check_2_passed, 0) AS if_manual_check_2_passed,
    COALESCE(if_in_external_data_pre2, 0) AS if_in_external_data_pre2,
    COALESCE(if_external_data_pre2_passed, 0) AS if_external_data_pre2_passed,
    COALESCE(if_in_external_data_2, 0) AS if_in_external_data_2, 
    COALESCE(if_external_data_2_passed, 0) AS if_external_data_2_passed,
    COALESCE(if_in_external_data_3, 0) AS if_in_external_data_3, 
    COALESCE(if_external_data_3_passed, 0) AS if_external_data_3_passed,
    COALESCE(if_in_external_data_4, 0) AS if_in_external_data_4, 
    COALESCE(if_external_data_4_passed, 0) AS if_external_data_4_passed,
 
    COALESCE(a.issue_cnt_from_app, 0) AS issue_cnt_from_app,
    COALESCE(a.is_released_within_24h, 0) AS is_released_within_24h, 
    COALESCE(i.issue_cnt_from_issue, 0) AS issue_cnt_from_issue,
    COALESCE(i.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(i.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(i.rl_issue_cnt_1_2, 0) AS rl_issue_cnt_1_2,
    COALESCE(i.rl_issue_cnt_1_3, 0) AS rl_issue_cnt_1_3,
    COALESCE(i.issue_contract_amount, 0) AS issue_contract_amount,
    COALESCE(i.issue_contract_amount_usd, 0) AS issue_contract_amount_usd,
    SUM(COALESCE(i.issue_contract_amount_usd, 0)) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='NEW'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_new_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='OLD'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_old_group,
    
    COALESCE(i.overdue_amount_1_0, 0) AS overdue_amount_1_0,
    COALESCE(i.should_capital_1_0, 0) AS should_capital_1_0,
    COALESCE(i.overdue_amount_1_7, 0) AS overdue_amount_1_7,
    COALESCE(i.should_capital_1_7, 0) AS should_capital_1_7,
    COALESCE(i.overdue_amount_1_14, 0) AS overdue_amount_1_14,
    COALESCE(i.should_capital_1_14, 0) AS should_capital_1_14,
    COALESCE(i.overdue_amount_1_30, 0) AS overdue_amount_1_30,
    COALESCE(i.should_capital_1_30, 0) AS should_capital_1_30, 
    COALESCE(i.overdue_amount_2_0, 0) AS overdue_amount_2_0,
    COALESCE(i.should_capital_2_0, 0) AS should_capital_2_0,
    COALESCE(i.overdue_amount_2_7, 0) AS overdue_amount_2_7,
    COALESCE(i.should_capital_2_7, 0) AS should_capital_2_7, 
    COALESCE(i.overdue_amount_2_30, 0) AS overdue_amount_2_30,
    COALESCE(i.should_capital_2_30, 0) AS should_capital_2_30,
    COALESCE(i.overdue_amount_3_0, 0) AS overdue_amount_3_0,
    COALESCE(i.should_capital_3_0, 0) AS should_capital_3_0,
    COALESCE(i.overdue_amount_3_30, 0) AS overdue_amount_3_30,
    COALESCE(i.should_capital_3_30, 0) AS should_capital_3_30,

    COALESCE(overdue_amount_total_30, 0) AS overdue_amount_total_30,
    COALESCE(should_capital_total_30, 0) AS should_capital_total_30,



    COALESCE(s.should_capital_d0, 0) AS should_capital_d0, 
    COALESCE(s.should_capital_d1, 0) AS should_capital_d1,
    COALESCE(s.should_capital_d7, 0) AS should_capital_d7,
    COALESCE(s.should_capital_d15, 0) AS should_capital_d15,
    COALESCE(s.should_capital_d30, 0) AS should_capital_d30,




    COALESCE(s.should_capital_d0 - s.t0_capital_paid_d0, 0) AS t0_capital_due_d0,
    COALESCE(s.should_capital_d1 - s.t1_capital_paid_d1, 0) AS t1_capital_due_d1,
    COALESCE(s.should_capital_d7 - s.t7_capital_paid_d7, 0) AS t7_capital_due_d7,
    COALESCE(s.should_capital_d15 - s.t15_capital_paid_d15, 0) AS t15_capital_due_d15,
    COALESCE(s.should_capital_d30 - s.t30_capital_paid_d30, 0) AS t30_capital_due_d30,
    COALESCE(s.t0_capital_paid_d7, 0) AS t0_capital_paid_d7,
    COALESCE(s.t0_capital_paid_d15, 0) AS t0_capital_paid_d15,
    COALESCE(s.t0_capital_paid_d30, 0) AS t0_capital_paid_d30,
    COALESCE(s.t7_capital_paid_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_d7,
    COALESCE(s.t15_capital_paid_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_d15,
    COALESCE(s.t30_capital_paid_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_d30,

    COALESCE(s.should_capital_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_due_d7,
    COALESCE(s.should_capital_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_due_d15,
    COALESCE(s.should_capital_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_due_d30,
    COALESCE(loan_cycle_amount, 0) AS loan_cycle_amount,
    COALESCE(issue_haircut_amount, 0) AS issue_haircut_amount,
    COALESCE(issue_interest, 0) AS issue_interest,
    COALESCE(issue_revenue, 0) AS issue_revenue,
    -- COALESCE(act_bad_debt_amt, 0) AS act_bad_debt_amt,
    total_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar  AS ov_total_amt_usd,
    fl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS fl_total_amt_usd,
    rl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS rl_total_amt_usd,
    month_days, 
    date_month_end_actual ,
    COALESCE(issue_contract_amount_usd_new, 0) AS issue_contract_amount_usd_new,
    COALESCE(issue_contract_amount_usd_old, 0) AS issue_contract_amount_usd_old
    

FROM application_metrics a
FULL JOIN issue_metrics i 
    ON a.grant_strategy = i.grant_strategy
    AND a.product_tag = i.product_tag
    AND a.is_reloan2 = i.is_reloan2
    AND a.new_grade_level = i.new_grade_level
    AND a.media_source2 = i.media_source2
    AND a.source_channel2 = i.source_channel2
    AND a.app_date = i.issue_date
    AND a.app_week = i.issue_week
    AND a.app_month = i.issue_month
    AND a.user_level = i.user_level 
    AND a.if_regular_backup = i.if_regular_backup
    AND a.if_backup_switch = i.if_backup_switch



FULL JOIN should_metrics s
    ON COALESCE(a.grant_strategy, i.grant_strategy) = s.grant_strategy
    AND COALESCE(a.product_tag, i.product_tag) = s.product_tag
    AND COALESCE(a.is_reloan2, i.is_reloan2) = s.is_reloan2
    AND COALESCE(a.new_grade_level, i.new_grade_level) = s.new_grade_level
    AND COALESCE(a.media_source2, i.media_source2) = s.media_source2
    AND COALESCE(a.source_channel2, i.source_channel2) = s.source_channel2
    AND COALESCE(a.app_date, i.issue_date) = s.should_date
    AND COALESCE(a.app_week, i.issue_week) = s.should_week
    AND COALESCE(a.app_month, i.issue_month) = s.should_month
    AND COALESCE(a.user_level, i.user_level) = s.user_level 
    AND COALESCE(a.if_regular_backup, 0) = s.if_regular_backup
    AND COALESCE(a.if_backup_switch, 0) = s.if_backup_switch



LEFT JOIN ind.ba_kpi_targets_m b
    ON COALESCE(a.app_month, i.issue_month, s.should_month) = b.month 
left join data_date c
    ON b.month = c.data_month 
LEFT JOIN dim.dim_exchange_rate_cost f1 ON c.date_mon = f1.month_id AND f1.account_currency = 'IDR'
;

 
 

drop table if exists ind.ba_install_apply_result;
create table
if not exists ind.ba_install_apply_result as

with spend AS (
    select 
        date(ad_date) as ad_date
        ,case when lower(campaign_name) like  '%ios%' or media_source='ASA' or lower(media_source) like '%ios%' then 'IOS'
                when media_source like '%oogle%' and lower(campaign_name) not like '%ios%' then 'Google'
                when media_source like '%acebook%' and lower(campaign_name) not like '%ios%' then 'Facebook'
                when media_source='organic' then 'Organic'  
                when media_source='Tiktok' then 'Tiktok'
                when media_source='Kwai' then 'Kwai'
                else 'other'
            end as media_source
        ,sum(spend_usd_discount) as spend
        from ind.tyn_ads_cost_discount a
        where ad_date >= date'2025-01-01'
        group by 1,2  
    union all
    select
        distinct
        ad_date,
        'Organic' as media_source,
        0 as spend
        from ind.tyn_ads_cost_discount  
        where ad_date >= date'2025-01-01'
    ),
install_cnt as (
    SELECT install_date,   
    case when media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source else 'other' end as media_source,

    sum(install_cnt) as install_cnt 
    FROM (
    SELECT 
    DATE(event_time + INTERVAL '7' HOUR) AS install_date,
    case 	   		
			when platform = 'ios'  then 'IOS'	
			when media_source='googleadwords_int' then 'Google'
             when media_source='Facebook Ads' or media_source='restricted' then 'Facebook'
             when media_source='organic' then 'Organic'
             when media_source = 'shareit_int' then 'Shareit'
             when  media_source = 'kreditlist_int' or (media_source = 'vfine_int' and partner like '%redi%'  ) 
             or 
             (media_source is null and partner = 'kreditlist')
             then 'kreditlist_int'
			 when media_source = 'vfine_int' or media_source = 'adecentptuo_int' then 'Vfine'
             when media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when media_source = 'kwaiforbusiness_int' then 'Kwai'
             when media_source = 'cashcashpro' then 'cashcashpro'
			 when media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when media_source = 'kredit pintal' then 'kp'
			 when media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(campaign, '^pp') then 'Novabeyond'
			 when media_source = 'pyxis_int' then 'pyxis'
			 when media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when media_source = 'Twitter' then 'twitter'
			 when media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' or partner ='appscuckoobd650' then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(partner) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when campaign like '%CookeAds_CPI%' then 'CookeAds_CPI'
			when campaign ='CookeAds_CPS' or lower(campaign) like '%cookeads%' then 'CookeAds_CPS'
			when partner = '19mobicn' then '19mobi'
			when campaign = 'Samire_Jan2025youmi' then 'youmi'
			when media_source ='yupaamj_int' then 'yup'
			--when regexp_like(campaign, '^pp') then 'Novabeyond'
			when media_source = 'mintegral_int' then 'mintegral_int'
			when lower(media_source) like '%grab%' then 'Grab'
			when media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(campaign) like '%runto%' then 'RUNTOA'
			when lower(campaign) like '%mejoy%'  then 'mejoy'
			when lower(campaign) like '%yolo%'  then 'yolo'
			when media_source ='LinkAja_ads' then 'LinkAja_ads'
			when media_source ='easycash01' then 'easycash01'
			when media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when media_source ='tangads' then 'tangads'
			when media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when media_source ='oppoglobal_int' then 'oppoglobal_int'
            when media_source like '%_int%' then 'other'
			 else 'Organic'
        end as media_source,
    COUNT(DISTINCT appsflyer_id) AS install_cnt
    FROM ods.s08_appsflyer_push_data
    WHERE  etl_date>='20250101' and event_name='install' 
    and date(event_time + INTERVAL '7' HOUR) >= date'2025-01-01'
    GROUP BY 1,2 
    )t
    GROUP BY 1,2 
     ),

 
reg_cnt as (
    select 
    reg_dt,
    case 
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source 
    when media_source='ASA' or lower(media_source) like '%ios%' then 'IOS' 
    else 'other'
    end as media_source, 
    count(distinct mid) reg_cnt
    from ind.tyn_reg_install_new
    where reg_dt >= date'2025-01-01'
    group by 1,2 
     ),
apply_cnt AS ( 
    SELECT
        date(app_date) as app_date,  
        media_source2, 
        sum(if_app) AS if_app  
    FROM ind.ba_asset_base_info 
    WHERE grant_strategy='NEW' 
    and if_app=1
    and if_recall=0
    and date(app_date) >= date'2025-01-01'
    GROUP BY 1,2 

),
issue_cnt AS ( 

    SELECT
        date(issue_date) as issue_date, 
        media_source2, 
        sum(if_issue) AS issue_cnt,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(contract_amount_usd) as contract_amount_usd
    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    and grant_strategy='NEW' 
    and date(issue_date) >= date'2025-01-01'
    GROUP BY 1,2
)
 
SELECT
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
    COALESCE(e.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(e.contract_amount_usd, 0) AS contract_amount_usd

FROM spend a
FULL OUTER JOIN install_cnt b ON a.ad_date = b.install_date AND a.media_source = b.media_source
FULL OUTER JOIN reg_cnt c ON a.ad_date = c.reg_dt AND a.media_source = c.media_source
FULL OUTER JOIN apply_cnt d ON a.ad_date = d.app_date AND a.media_source = d.media_source2
FULL OUTER JOIN issue_cnt e ON a.ad_date = e.issue_date AND a.media_source = e.media_source2;


  