
-- select * from ind.ba_apply_should_result_week_old_ys where app_month>='2026-01-01' limit 100000
-- select * from ind.ba_apply_should_result_week_new_ys where app_month>='2026-01-01' limit 100000
-- select * from ind.ba_install_apply_result_ys where ad_date>=date'2026-01-01' limit 100000

drop table if exists ind.ba_apply_should_result_week_old_ys;
create table if not exists ind.ba_apply_should_result_week_old_ys as
WITH
application_metrics AS (
    SELECT
        app_week,app_month,grant_strategy,product_tag,is_reloan2,new_grade_level,first_loan_grade_level,loan_type2,
        SUM(CASE WHEN if_recall = 0 THEN if_app END) if_app,
        SUM(CASE WHEN grant_strategy = 'OLD' AND if_recall = 0 THEN if_external_data_3_passed WHEN grant_strategy = 'NEW' THEN if_in_confirm_final END) if_external_3_passed,
        SUM(CASE WHEN if_in_confirm_final = 1 THEN grant_amount_max END) in_confirm_grantcredit_amount_total,
        SUM(CASE WHEN if_in_confirm_final = 1 THEN grantcredit_amount END) in_confirm_grantcredit_amount,
        SUM(CASE WHEN if_confirm_passed_final = 1 THEN apply_grantcredit_amount END) confirm_grantcredit_amount,
        SUM(CASE WHEN if_confirm_passed_final = 1 THEN apply_amount END) confirm_apply_amount,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND if_issue = 1 THEN apply_grantcredit_amount END) issue_confirm_grantcredit_amount,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND if_issue = 1 THEN apply_amount END) issue_confirm_apply_amount,
        SUM(CASE WHEN grant_strategy = 'OLD' AND if_recall = 0 THEN if_in_external_data_4 WHEN grant_strategy = 'NEW' THEN if_confirm_passed_final END) if_in_external_data_4,
        SUM(if_external_data_4_passed) pass_cnt,
        SUM(if_issue) issue_cnt_from_app,
        SUM(is_released_within_24h) is_released_within_24h
    FROM ind.ba_asset_base_info
    WHERE date(app_date) >= DATE '2025-01-01' AND date(app_date) < CURRENT_DATE AND grant_strategy = 'OLD'
    GROUP BY 1,2,3,4,5,6,7,8
),
confirm_metrics AS (
    SELECT
        create_week,date_format(create_date,'%Y-%m-01') create_month,grant_strategy,product_tag,is_reloan2,new_grade_level,first_loan_grade_level,loan_type2,
        COUNT(DISTINCT CASE WHEN if_recall = 0 THEN id END) create_app_cnt,
        SUM(if_in_confirm_final) in_confirm_cnt_final,
        SUM(if_in_confirm_temp) in_confirm_cnt,
        SUM(CASE WHEN new_grade_level IN ('1','2') THEN if_in_confirm_temp ELSE 0 END) in_confirm_cnt_1_2,
        SUM(CASE WHEN new_grade_level IN ('1','2','3') THEN if_in_confirm_temp ELSE 0 END) in_confirm_cnt_1_3,
        SUM(CASE WHEN new_grade_level IN ('1','2','3','4') THEN if_in_confirm_temp ELSE 0 END) in_confirm_cnt_1_4,
        SUM(if_confirm_passed_final) confirm_passed_cnt,
        SUM(if_confirm_passed_num_24h) if_confirm_passed_num_24h,
        SUM(if_confirm_passed_num_t0) if_confirm_passed_num_t0,
        SUM(if_confirm_passed_num_t7) if_confirm_passed_num_t7
    FROM ind.ba_asset_base_info
    WHERE date(create_date) >= DATE '2025-01-01' AND date(create_date) < CURRENT_DATE AND grant_strategy = 'OLD'
    GROUP BY 1,2,3,4,5,6,7,8
),
issue_metrics AS (
    SELECT
        issue_week,issue_month,grant_strategy,product_tag,is_reloan2,loan_type2,new_grade_level,first_loan_grade_level,
        SUM(if_issue) issue_cnt_from_issue,
        SUM(CASE WHEN new_grade_level IN ('1','2') THEN if_issue ELSE 0 END) issue_cnt_1_2,
        SUM(CASE WHEN new_grade_level IN ('1','2','3') THEN if_issue ELSE 0 END) issue_cnt_1_3,
        SUM(CASE WHEN new_grade_level IN ('1','2','3','4') THEN if_issue ELSE 0 END) issue_cnt_1_4, 
        SUM(haircut_amount) issue_haircut_amount,
        SUM(interest) issue_interest,
        SUM(revenue) issue_revenue,
        SUM(contract_amount) issue_contract_amount,
        SUM(contract_amount_usd1) issue_contract_amount_usd, 
        SUM(apply_grantcredit_amount * app_exchange_rate_to_dollar) issue_in_confirm_grantcredit_amount,
        SUM(overdue_amount_1_0) overdue_amount_1_0,SUM(should_capital_1_0) should_capital_1_0,
        SUM(overdue_amount_1_7) overdue_amount_1_7,SUM(should_capital_1_7) should_capital_1_7,
        SUM(overdue_amount_1_14) overdue_amount_1_14,SUM(should_capital_1_14) should_capital_1_14,
        SUM(overdue_amount_1_30) overdue_amount_1_30,SUM(should_capital_1_30) should_capital_1_30,
        SUM(overdue_amount_2_0) overdue_amount_2_0,SUM(should_capital_2_0) should_capital_2_0,
        SUM(overdue_amount_2_7) overdue_amount_2_7,SUM(should_capital_2_7) should_capital_2_7,
        SUM(overdue_amount_2_14) overdue_amount_2_14,SUM(should_capital_2_14) should_capital_2_14,
        SUM(overdue_amount_2_30) overdue_amount_2_30,SUM(should_capital_2_30) should_capital_2_30,
        SUM(loan_cycle_amount) loan_cycle_amount
    FROM ind.ba_asset_base_info
    WHERE if_issue = 1 AND grant_strategy = 'OLD' AND date(issue_date) >= DATE '2025-01-01' AND date(issue_date) < CURRENT_DATE
    GROUP BY 1,2,3,4,5,6,7,8
),
data_date AS (
    SELECT DISTINCT
        date_mon,
        date_format(DATE_PARSE(data_date,'%Y%m%d'),'%Y-%m-01') data_month,
        month_days,
        DAY(DATE_ADD('day',-1,CURRENT_DATE)) current_date_day,
        CASE WHEN DATE_PARSE(month_end,'%Y%m%d') < DATE_TRUNC('month',CURRENT_DATE) THEN DAY(DATE_PARSE(month_end,'%Y%m%d')) ELSE DAY(DATE_ADD('day',-1,CURRENT_DATE)) END date_month_end_actual
    FROM dim.dim_data_info
)
SELECT
    COALESCE(a.grant_strategy,i.grant_strategy,c.grant_strategy,y.grant_strategy) grant_strategy,
    COALESCE(a.product_tag,i.product_tag,c.product_tag,y.product_tag) product_tag,
    COALESCE(a.is_reloan2,i.is_reloan2,c.is_reloan2,y.is_reloan2) is_reloan2,
    COALESCE(a.new_grade_level,i.new_grade_level,c.new_grade_level,y.new_grade_level) new_grade_level,
    COALESCE(a.first_loan_grade_level,i.first_loan_grade_level,c.first_loan_grade_level,y.first_loan_grade_level) first_loan_grade_level,
    COALESCE(DATE(a.app_week),DATE(i.issue_week),c.create_week,date(y.create_week)) app_week,
    COALESCE(a.app_month,i.issue_month,c.create_month,y.create_month) app_month, 
    COALESCE(a.if_app,0) if_app,
    COALESCE(a.if_external_3_passed,0) if_external_3_passed,
    COALESCE(c.create_app_cnt,0) create_app_cnt,
    COALESCE(c.in_confirm_cnt_final,0) in_confirm_cnt_final,
    COALESCE(c.in_confirm_cnt,0) in_confirm_cnt,
    COALESCE(c.in_confirm_cnt_1_2,0) in_confirm_cnt_1_2,
    COALESCE(c.in_confirm_cnt_1_3,0) in_confirm_cnt_1_3,
    COALESCE(c.in_confirm_cnt_1_4,0) in_confirm_cnt_1_4,
    COALESCE(c.confirm_passed_cnt,0) confirm_passed_cnt,
    COALESCE(c.if_confirm_passed_num_24h,0) if_confirm_passed_num_24h,
    COALESCE(c.if_confirm_passed_num_t0,0) if_confirm_passed_num_t0,
    COALESCE(c.if_confirm_passed_num_t7,0) if_confirm_passed_num_t7,
    COALESCE(a.in_confirm_grantcredit_amount_total,0) in_confirm_grantcredit_amount_total,
    COALESCE(a.in_confirm_grantcredit_amount,0) in_confirm_grantcredit_amount,
    COALESCE(a.confirm_grantcredit_amount,0) confirm_grantcredit_amount,
    COALESCE(a.confirm_apply_amount,0) confirm_apply_amount,
    COALESCE(a.if_in_external_data_4,0) if_in_external_data_4,
    COALESCE(a.pass_cnt,0) pass_cnt,
    COALESCE(a.is_released_within_24h,0) is_released_within_24h,
    COALESCE(i.issue_cnt_from_issue,0) issue_cnt_from_issue,
    COALESCE(i.issue_cnt_1_2,0) issue_cnt_1_2,
    COALESCE(i.issue_cnt_1_3,0) issue_cnt_1_3,
    COALESCE(i.issue_cnt_1_4,0) issue_cnt_1_4,
    
    COALESCE(i.issue_contract_amount,0) issue_contract_amount,
    COALESCE(i.issue_contract_amount_usd,0) issue_contract_amount_usd,
    COALESCE(i.issue_in_confirm_grantcredit_amount,0) issue_in_confirm_grantcredit_amount,
    COALESCE(i.overdue_amount_1_0,0) overdue_amount_1_0,
    COALESCE(i.should_capital_1_0,0) should_capital_1_0,
    COALESCE(i.overdue_amount_1_7,0) overdue_amount_1_7,
    COALESCE(i.should_capital_1_7,0) should_capital_1_7,
    COALESCE(i.overdue_amount_2_7,0) overdue_amount_2_7,
    COALESCE(i.should_capital_2_7,0) should_capital_2_7,
    COALESCE(i.loan_cycle_amount,0) loan_cycle_amount,
    COALESCE(i.issue_haircut_amount,0) issue_haircut_amount,
    COALESCE(i.issue_interest,0) issue_interest,
    COALESCE(i.issue_revenue,0) issue_revenue,  
    COALESCE(a.loan_type2,i.loan_type2,c.loan_type2) loan_type2,
    COALESCE(y.one_credit_cnt, 0) AS one_credit_cnt,
    COALESCE(y.one_click_T1, 0) AS one_click_T1,
    COALESCE(y.one_click_T3, 0) AS one_click_T3,
    COALESCE(y.one_click_T5, 0) AS one_click_T5,
    COALESCE(y.one_click_T7, 0) AS one_click_T7,
    COALESCE(y.one_click_T15, 0) AS one_click_T15,
    COALESCE(y.one_click_T30, 0) AS one_click_T30,
    COALESCE(y.one_confirm_T1, 0) AS one_confirm_T1,
    COALESCE(y.one_confirm_T3, 0) AS one_confirm_T3,
    COALESCE(y.one_confirm_T5, 0) AS one_confirm_T5,
    COALESCE(y.one_confirm_T7, 0) AS one_confirm_T7,
    COALESCE(y.one_confirm_T15, 0) AS one_confirm_T15,
    COALESCE(y.one_confirm_T30, 0) AS one_confirm_T30,

    COALESCE(y.all_credit_cnt, 0) AS all_credit_cnt,
    COALESCE(y.all_click_T1, 0) AS all_click_T1,
    COALESCE(y.all_click_T3, 0) AS all_click_T3,
    COALESCE(y.all_click_T5, 0) AS all_click_T5,
    COALESCE(y.all_click_T7, 0) AS all_click_T7,
    COALESCE(y.all_click_T15, 0) AS all_click_T15,
    COALESCE(y.all_click_T30, 0) AS all_click_T30,
    COALESCE(y.all_confirm_T1, 0) AS all_confirm_T1,
    COALESCE(y.all_confirm_T3, 0) AS all_confirm_T3,
    COALESCE(y.all_confirm_T5, 0) AS all_confirm_T5,
    COALESCE(y.all_confirm_T7, 0) AS all_confirm_T7,
    COALESCE(y.all_confirm_T15, 0) AS all_confirm_T15,
    COALESCE(y.all_confirm_T30, 0) AS all_confirm_T30
FROM application_metrics a
FULL JOIN issue_metrics i 
    ON a.grant_strategy = i.grant_strategy AND a.product_tag = i.product_tag AND a.is_reloan2 = i.is_reloan2 
    AND a.loan_type2 = i.loan_type2 AND a.new_grade_level = i.new_grade_level AND a.app_week = i.issue_week
    AND a.app_month = i.issue_month AND a.first_loan_grade_level = i.first_loan_grade_level
FULL JOIN confirm_metrics c 
    ON COALESCE(a.grant_strategy,i.grant_strategy) = c.grant_strategy
    AND COALESCE(a.product_tag,i.product_tag) = c.product_tag
    AND COALESCE(a.is_reloan2,i.is_reloan2) = c.is_reloan2
    AND COALESCE(a.loan_type2,i.loan_type2) = c.loan_type2
    AND COALESCE(a.new_grade_level,i.new_grade_level) = c.new_grade_level
    AND COALESCE(DATE(a.app_week),DATE(i.issue_week)) = c.create_week
    AND COALESCE(a.app_month,i.issue_month) = c.create_month
    AND COALESCE(a.first_loan_grade_level,i.first_loan_grade_level) = c.first_loan_grade_level
full join ind.ys_mor_tmp_loop_credit_result y 
 ON COALESCE(a.grant_strategy,i.grant_strategy,c.grant_strategy) = y.grant_strategy
    AND COALESCE(a.product_tag,i.product_tag,c.product_tag) = y.product_tag
    AND COALESCE(a.is_reloan2,i.is_reloan2,c.is_reloan2) = y.is_reloan2
    AND COALESCE(a.loan_type2,i.loan_type2,c.loan_type2)  = y.loan_type2
    AND COALESCE(a.new_grade_level,i.new_grade_level,c.new_grade_level) = y.new_grade_level
    AND COALESCE(DATE(a.app_week),DATE(i.issue_week),c.create_week) = date(y.create_week)
    AND COALESCE(a.app_month,i.issue_month,c.create_month) =y.create_month
    AND COALESCE(a.first_loan_grade_level,i.first_loan_grade_level) = y.first_loan_grade_level
LEFT JOIN ind.ba_kpi_targets_m b ON COALESCE(a.app_month,i.issue_month) = b.month
LEFT JOIN data_date cc ON b.month = cc.data_month
LEFT JOIN dim.dim_exchange_rate_cost f1 ON cc.date_mon = f1.month_id AND f1.account_currency = 'IDR';
-- where 
-- limit 100000;
 












 

drop table if exists ind.ba_apply_should_result_week_new_ys;
create table
if not exists ind.ba_apply_should_result_week_new_ys as

WITH application_metrics AS ( 
    SELECT 
        app_week,
        app_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
          loan_type2,
        media_source2,
        source_channel2, 

        sum(case when if_recall=0 then if_app end) if_app,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed 
                 when grant_strategy='NEW' then if_in_confirm_temp end) if_external_3_passed,
        sum(if_in_confirm_final ) AS in_confirm_cnt_final,
        sum(if_in_confirm_temp) AS in_confirm_cnt,
        sum(case when new_grade_level IN ('1','2') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_4,
          sum(if_confirm_passed_final) AS confirm_passed_cnt, 
        sum(if_confirm_passed_num_24h) AS if_confirm_passed_num_24h,
        sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
        sum(if_confirm_passed_num_t7) AS if_confirm_passed_num_t7,
        SUM(case when if_in_confirm_final = 1 then grant_amount_max else NULL end) AS in_confirm_grantcredit_amount_total,
        SUM(case when if_in_confirm_final = 1 then grantcredit_amount else NULL end) AS in_confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_grantcredit_amount else NULL end) AS confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_amount else NULL end) AS confirm_apply_amount,
 
        SUM(case when if_confirm_passed_final= 1 and if_issue=1 then apply_grantcredit_amount else NULL end) AS issue_confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 and if_issue=1 then apply_amount else NULL end) AS issue_confirm_apply_amount,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 
                 when grant_strategy='NEW' then if_confirm_passed_final end) if_in_external_data_4,

        sum(if_external_data_4_passed ) as pass_cnt,
        sum(if_issue) AS issue_cnt_from_app,
        sum(is_released_within_24h) AS is_released_within_24h
    FROM ind.ba_asset_base_info
    WHERE date(app_date) >= DATE('2025-01-01')  
    AND date(app_date) < CURRENT_DATE
    -- AND if_app = 1
    GROUP BY 1,2,3,4,5,6,7,8,9 




),

 
issue_metrics AS ( 
    SELECT 
        issue_week,
        issue_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        loan_type2,
        new_grade_level, 
 
        media_source2,
        source_channel2, 
        sum(if_issue) AS issue_cnt_from_issue,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        
        sum(haircut_amount) as issue_haircut_amount,
        sum(interest) as issue_interest,
        sum(revenue) as issue_revenue,
        sum(contract_amount) AS issue_contract_amount,
        sum(contract_amount_usd1) AS issue_contract_amount_usd,
      
        SUM(apply_grantcredit_amount*app_exchange_rate_to_dollar) AS issue_in_confirm_grantcredit_amount,
 

        
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

        sum(loan_cycle_amount) AS loan_cycle_amount
 

    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    AND date(issue_date) >= DATE('2025-01-01') 
    AND date(issue_date) < CURRENT_DATE 
    GROUP BY 1,2,3,4,5,6,7,8,9  

) 
 
        SELECT 
    COALESCE(a.grant_strategy, i.grant_strategy) AS grant_strategy,
    COALESCE(a.product_tag, i.product_tag ) AS product_tag,
    COALESCE(a.is_reloan2, i.is_reloan2) AS is_reloan2,
    COALESCE(a.new_grade_level, i.new_grade_level) AS new_grade_level,
  
    COALESCE(a.media_source2, i.media_source2) AS media_source,
    COALESCE(a.source_channel2, i.source_channel2) AS source_channel2,  
    COALESCE(a.app_week, i.issue_week) AS app_week,
    COALESCE(a.app_month, i.issue_month) AS app_month,  
    COALESCE(a.if_app, 0) AS if_app,
    COALESCE(a.if_external_3_passed, 0) AS if_external_3_passed,
    COALESCE(a.in_confirm_cnt_final, 0) AS in_confirm_cnt_final,
    COALESCE(a.in_confirm_cnt, 0) AS in_confirm_cnt,
    COALESCE(a.in_confirm_cnt_1_2, 0) AS in_confirm_cnt_1_2,
    COALESCE(a.in_confirm_cnt_1_4, 0) AS in_confirm_cnt_1_4, 

    COALESCE(a.confirm_passed_cnt, 0) AS confirm_passed_cnt,
    COALESCE(a.if_confirm_passed_num_24h, 0) AS if_confirm_passed_num_24h,

    COALESCE(a.if_confirm_passed_num_t0, 0) AS if_confirm_passed_num_t0,
    COALESCE(a.if_confirm_passed_num_t7, 0) AS if_confirm_passed_num_t7,

    COALESCE(a.in_confirm_grantcredit_amount_total, 0) AS in_confirm_grantcredit_amount_total,
    COALESCE(a.in_confirm_grantcredit_amount, 0) AS in_confirm_grantcredit_amount,
    COALESCE(a.confirm_grantcredit_amount, 0) AS confirm_grantcredit_amount,
    COALESCE(a.confirm_apply_amount, 0) AS confirm_apply_amount,
    COALESCE(a.if_in_external_data_4, 0) AS if_in_external_data_4,
    COALESCE(a.pass_cnt, 0) AS pass_cnt, 
    COALESCE(a.issue_cnt_from_app, 0) AS issue_cnt_from_app,
    COALESCE(a.is_released_within_24h, 0) AS is_released_within_24h, 
    COALESCE(i.issue_cnt_from_issue, 0) AS issue_cnt_from_issue,
    COALESCE(i.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(i.issue_cnt_1_4, 0) AS issue_cnt_1_4, 
    COALESCE(i.issue_contract_amount, 0) AS issue_contract_amount,
    COALESCE(i.issue_contract_amount_usd, 0) AS issue_contract_amount_usd,
    COALESCE(i.issue_in_confirm_grantcredit_amount, 0) AS issue_in_confirm_grantcredit_amount, 
    
    COALESCE(i.overdue_amount_1_0, 0) AS overdue_amount_1_0,
    COALESCE(i.should_capital_1_0, 0) AS should_capital_1_0,
    COALESCE(i.overdue_amount_1_7, 0) AS overdue_amount_1_7,
    COALESCE(i.should_capital_1_7, 0) AS should_capital_1_7, 
    COALESCE(i.overdue_amount_2_7, 0) AS overdue_amount_2_7,
    COALESCE(i.should_capital_2_7, 0) AS should_capital_2_7,  
    COALESCE(loan_cycle_amount, 0) AS loan_cycle_amount,
    COALESCE(issue_haircut_amount, 0) AS issue_haircut_amount,
    COALESCE(issue_interest, 0) AS issue_interest,
    COALESCE(issue_revenue, 0) AS issue_revenue,  
        COALESCE(a.loan_type2, i.loan_type2) AS loan_type2  
FROM application_metrics a
FULL JOIN issue_metrics i 
    ON a.grant_strategy = i.grant_strategy
    AND a.product_tag = i.product_tag
    AND a.is_reloan2 = i.is_reloan2
    AND a.loan_type2 = i.loan_type2
    AND a.new_grade_level = i.new_grade_level
    AND a.media_source2 = i.media_source2
    AND a.source_channel2 = i.source_channel2 
    AND a.app_week = i.issue_week
    AND a.app_month = i.issue_month 
  
LEFT JOIN dim.dim_exchange_rate_cost f1  
ON TO_CHAR(DATE(i.issue_month), 'yyyymm') = f1.month_id 
                                     AND f1.account_currency = 'IDR'
;

  


   
drop table if exists ind.ba_install_apply_result_ys;
create table
if not exists ind.ba_install_apply_result_ys as

with spend AS (
    select 
        date(ad_date) as ad_date
        ,case when media_source='ASA' then 'IOS_ASA'
                when lower(campaign_name) like  '%ios%'  or lower(media_source) like '%ios%' then 'IOS_OTHER'
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
     case 
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai') then media_source 
    when media_source='ASA' then 'IOS_ASA'
    when lower(media_source) like '%ios%' then 'IOS_OTHER' 
    else 'other'
    end as media_source,  
    sum(install_cnt) as install_cnt 
    FROM (
    SELECT 
    DATE(event_time + INTERVAL '7' HOUR) AS install_date,
    case 	   		
		when platform = 'ios' and  media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  media_source in ('restricted','Facebook Ads') then 'IOS-fb'
			when platform = 'ios' and  media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  media_source = 'tangads' then 'IOS-tangads'
			when platform = 'ios' and  media_source = 'Pinjamyuk_ads' then 'IOS-Pinjamyuk'
		  --when platform = 'ios' and  media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when media_source='googleadwords_int' then 'Google'
             when media_source='Facebook Ads' or media_source='restricted' then 'Facebook'
             when media_source='organic' then 'Organic'
             when media_source = 'shareit_int' then 'Shareit'
             when media_source = 'kreditlist_int' or (media_source = 'vfine_int' and partner like '%redi%'  ) 
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
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' or partner ='appscuckoobd650'then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(campaign) like '%rainbow%' then 'rainbow'
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
			when media_source in ('easycash01','easycashid_int') then 'easycash01'
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
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai') then media_source 
    when media_source='ASA' then 'IOS_ASA'
    when lower(media_source) like '%ios%' then 'IOS_OTHER' 
    else 'other'
    end as media_source, 
    count(distinct mid) reg_cnt
    from dws.dws_acq_reg_install
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
        sum(case when reloan_num=1 then if_issue else 0 end ) AS issue_cnt_1,
       --  sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
       --  sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(contract_amount_usd) as contract_amount_usd,
        sum(case when reloan_num=1 then contract_amount_usd else 0 end ) as contract_amount_usd_1
    FROM  ind.ba_asset_base_info
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
    COALESCE(e.issue_cnt_1, 0) AS issue_cnt_1, 
    COALESCE(e.contract_amount_usd, 0) AS contract_amount_usd, 
    COALESCE(e.contract_amount_usd_1, 0) AS contract_amount_usd_1

FROM spend a
FULL OUTER JOIN install_cnt b ON a.ad_date = b.install_date AND a.media_source = b.media_source
FULL OUTER JOIN reg_cnt c ON a.ad_date = c.reg_dt AND a.media_source = c.media_source
FULL OUTER JOIN apply_cnt d ON a.ad_date = d.app_date AND a.media_source = d.media_source2
FULL OUTER JOIN issue_cnt e ON a.ad_date = e.issue_date AND a.media_source = e.media_source2;









 