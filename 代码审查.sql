
DROP TABLE if exists ind.ys_mor_tmp_loop_credit_result;
create table ind.ys_mor_tmp_loop_credit_result as 
/* ========================= 
   ========================= */
WITH ind_data AS (
    SELECT
        date_format(createtime, '%Y-%m-01')                            AS create_month,
        to_char(date_trunc('week', createtime), 'yyyy-mm-dd')          AS create_week,
        cast(new_grade_level as VARCHAR) new_grade_level,
        new_grade_level_fl,
        CONCAT('OLD_', strategyname)                                   AS strategy_name,
        CASE
            WHEN a.product_level LIKE 'M%' THEN 'M'
            WHEN a.product_level IN (
                'A14','B10','B12','C8','A15','B13','B14','C9',
                'A16','B15','B16','C10','G1','G2','H1','H2','H3','H4',
                'I1','I2','I3','I4','I5','I6'
            ) THEN 'F-NofeeNew'
            WHEN a.product_level IN ('B7','C7','A9','B8') THEN 'F-NofeeOld'
            WHEN a.product_level LIKE 'J%' OR a.product_level LIKE 'K%' OR a.product_level LIKE 'L%' THEN 'NR'
            WHEN a.product_level LIKE 'R%' OR a.product_level LIKE 'S%' THEN 'NF'
            WHEN a.product_level LIKE 'Q%' THEN 'NW'
            WHEN substring(a.product_level,1,1) IN ('D','E','F') THEN 'R-30'
            WHEN a.product_level IS NOT NULL THEN 'R-15'
            ELSE 'Unknown'
        END                                                             AS product_tag,

        /* ---- sums ---- */
        COUNT(1)                                                        AS one_credit_cnt,

        SUM(if_click_T1)                                                AS one_click_T1,
        SUM(if_click_T3)                                                AS one_click_T3,
        SUM(if_click_T5)                                                AS one_click_T5,
        SUM(if_click_T7)                                                AS one_click_T7,
        SUM(if_click_T15)                                               AS one_click_T15,
        SUM(if_click_T30)                                               AS one_click_T30,

        SUM(if_confirm_T1)                                              AS one_confirm_T1,
        SUM(if_confirm_T3)                                              AS one_confirm_T3,
        SUM(if_confirm_T5)                                              AS one_confirm_T5,
        SUM(if_confirm_T7)                                              AS one_confirm_T7,
        SUM(if_confirm_T15)                                             AS one_confirm_T15,
        SUM(if_confirm_T30)                                             AS one_confirm_T30

    FROM ind.ctj_mor_tmp_loop_credit_trans a
    WHERE createtime >= DATE '2026-01-01'
    GROUP BY 1,2,3,4,5,6
),

/* ========================= 
   ========================= */
ys_data AS (
    SELECT
        date_format(createtime, '%Y-%m-01')                            AS create_month,
        to_char(date_trunc('week', createtime), 'yyyy-mm-dd')          AS create_week,
        cast(new_grade_level as VARCHAR) new_grade_level,
        new_grade_level_fl,
        CONCAT('OLD_', strategyname)                                   AS strategy_name,
        CASE
            WHEN a.product_level LIKE 'M%' THEN 'M'
            WHEN a.product_level IN (
                'A14','B10','B12','C8','A15','B13','B14','C9',
                'A16','B15','B16','C10','G1','G2','H1','H2','H3','H4',
                'I1','I2','I3','I4','I5','I6'
            ) THEN 'F-NofeeNew'
            WHEN a.product_level IN ('B7','C7','A9','B8') THEN 'F-NofeeOld'
            WHEN a.product_level LIKE 'J%' OR a.product_level LIKE 'K%' OR a.product_level LIKE 'L%' THEN 'NR'
            WHEN a.product_level LIKE 'R%' OR a.product_level LIKE 'S%' THEN 'NF'
            WHEN a.product_level LIKE 'Q%' THEN 'NW'
            WHEN substring(a.product_level,1,1) IN ('D','E','F') THEN 'R-30'
            WHEN a.product_level IS NOT NULL THEN 'R-15'
            ELSE 'Unknown'
        END                                                             AS product_tag,

        COUNT(1)                                                        AS all_credit_cnt,

        SUM(if_click_T1)                                                AS all_click_T1,
        SUM(if_click_T3)                                                AS all_click_T3,
        SUM(if_click_T5)                                                AS all_click_T5,
        SUM(if_click_T7)                                                AS all_click_T7,
        SUM(if_click_T15)                                               AS all_click_T15,
        SUM(if_click_T30)                                               AS all_click_T30,

        SUM(if_confirm_T1)                                              AS all_confirm_T1,
        SUM(if_confirm_T3)                                              AS all_confirm_T3,
        SUM(if_confirm_T5)                                              AS all_confirm_T5,
        SUM(if_confirm_T7)                                              AS all_confirm_T7,
        SUM(if_confirm_T15)                                             AS all_confirm_T15,
        SUM(if_confirm_T30)                                             AS all_confirm_T30

    FROM ind.ys_mor_tmp_loop_credit_trans a
    WHERE createtime >= DATE '2026-01-01'
    GROUP BY 1,2,3,4,5,6
)

 
/* ========================= 
   ========================= */
SELECT 
    
    COALESCE(i.create_month, y.create_month) AS create_month,
    COALESCE(i.create_week, y.create_week)   AS create_week,
    'loop' as loan_type2,
    'OLD' as grant_strategy,
    COALESCE(i.new_grade_level, y.new_grade_level) AS new_grade_level,
    COALESCE(i.new_grade_level_fl, y.new_grade_level_fl) AS first_loan_grade_level,
    COALESCE(i.strategy_name, y.strategy_name) AS is_reloan2,
    COALESCE(i.product_tag, y.product_tag)     AS product_tag,

    i.one_credit_cnt, i.one_click_T1, i.one_click_T3, i.one_click_T5, i.one_click_T7, i.one_click_T15, i.one_click_T30,
    i.one_confirm_T1, i.one_confirm_T3, i.one_confirm_T5, i.one_confirm_T7, i.one_confirm_T15, i.one_confirm_T30,

    y.all_credit_cnt, y.all_click_T1, y.all_click_T3, y.all_click_T5, y.all_click_T7, y.all_click_T15, y.all_click_T30,
    y.all_confirm_T1, y.all_confirm_T3, y.all_confirm_T5, y.all_confirm_T7, y.all_confirm_T15, y.all_confirm_T30

FROM ind_data i
FULL OUTER JOIN ys_data y
  ON i.create_month = y.create_month
 AND i.create_week  = y.create_week
 AND i.new_grade_level = y.new_grade_level
 AND i.new_grade_level_fl = y.new_grade_level_fl
 AND i.strategy_name = y.strategy_name
 AND i.product_tag = y.product_tag
ORDER BY create_month, create_week;














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
    COALESCE(a.grant_strategy,i.grant_strategy,c.grant_strategy) grant_strategy,
    COALESCE(a.product_tag,i.product_tag,c.product_tag) product_tag,
    COALESCE(a.is_reloan2,i.is_reloan2,c.is_reloan2) is_reloan2,
    COALESCE(a.new_grade_level,i.new_grade_level,c.new_grade_level) new_grade_level,
    COALESCE(a.first_loan_grade_level,i.first_loan_grade_level,c.first_loan_grade_level) first_loan_grade_level,
    COALESCE(DATE(a.app_week),DATE(i.issue_week),c.create_week) app_week,
    COALESCE(a.app_month,i.issue_month,c.create_month) app_month,
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
left join ind.ys_mor_tmp_loop_credit_result y 
 ON COALESCE(a.grant_strategy,i.grant_strategy) = y.grant_strategy
    AND COALESCE(a.product_tag,i.product_tag) = y.product_tag
    AND COALESCE(a.is_reloan2,i.is_reloan2) = y.is_reloan2
    AND COALESCE(a.loan_type2,i.loan_type2) = y.loan_type2
    AND COALESCE(a.new_grade_level,i.new_grade_level) = y.new_grade_level
    AND COALESCE(a.app_week,i.issue_week) = y.create_week
    AND COALESCE(a.app_month,i.issue_month) = y.create_month
    AND COALESCE(a.first_loan_grade_level,i.first_loan_grade_level) = y.first_loan_grade_level
LEFT JOIN ind.ba_kpi_targets_m b ON COALESCE(a.app_month,i.issue_month) = b.month
LEFT JOIN data_date cc ON b.month = cc.data_month
LEFT JOIN dim.dim_exchange_rate_cost f1 ON cc.date_mon = f1.month_id AND f1.account_currency = 'IDR';
-- where 
-- limit 100000;

select * from ind.ba_apply_should_result_week_old_ys where app_month>='2026-01-01' limit 100000






