-- ================================================
-- KPI Metrics Summary Report
-- Purpose: Monthly summary of loan business metrics
-- Date Range: From 2025-01-01 onwards
-- ================================================

WITH 

-- ================================================
-- 1. Issue Month Metrics (Core Loan Data)
-- ================================================
issue_month AS (
    SELECT 
        issue_month,
        
        -- Customer counts (distinct)
        COUNT(DISTINCT mid) AS loan_customer_cnt_total,
        COUNT(DISTINCT CASE WHEN grant_strategy = 'NEW' THEN mid END) AS loan_customer_cnt_new,
        COUNT(DISTINCT CASE WHEN grant_strategy = 'OLD' THEN mid END) AS loan_customer_cnt_old,
        
        -- Loan counts
        SUM(if_issue) AS loan_cnt_total,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN if_issue ELSE 0 END) AS loan_cnt_new,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN if_issue ELSE 0 END) AS loan_cnt_old,
        
        -- Loan amounts (USD)
        SUM(contract_amount_usd1) AS loan_amt_total,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN contract_amount_usd1 ELSE 0 END) AS loan_amt_new,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN contract_amount_usd1 ELSE 0 END) AS loan_amt_old,
        
        -- Average loan amounts
        CASE WHEN SUM(if_issue) > 0 THEN SUM(contract_amount_usd1) / SUM(if_issue) ELSE 0 END AS avg_loan_amt_total,
        CASE WHEN SUM(CASE WHEN grant_strategy = 'NEW' THEN if_issue ELSE 0 END) > 0 
             THEN SUM(CASE WHEN grant_strategy = 'NEW' THEN contract_amount_usd1 ELSE 0 END) / 
                  SUM(CASE WHEN grant_strategy = 'NEW' THEN if_issue ELSE 0 END) 
             ELSE 0 END AS avg_loan_amt_new,
        CASE WHEN SUM(CASE WHEN grant_strategy = 'OLD' THEN if_issue ELSE 0 END) > 0 
             THEN SUM(CASE WHEN grant_strategy = 'OLD' THEN contract_amount_usd1 ELSE 0 END) / 
                  SUM(CASE WHEN grant_strategy = 'OLD' THEN if_issue ELSE 0 END) 
             ELSE 0 END AS avg_loan_amt_old,
        
        -- Revenue metrics
        SUM(revenue) AS revenue_total,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN revenue ELSE 0 END) AS revenue_new,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN revenue ELSE 0 END) AS revenue_old,
        
        -- IDR amounts
        SUM(contract_amount) AS loan_amt_total_idr,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN contract_amount ELSE 0 END) AS loan_amt_new_idr,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN contract_amount ELSE 0 END) AS loan_amt_old_idr,
        SUM(amount) AS loan1_amt_total_idr,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN amount ELSE 0 END) AS loan1_amt_new_idr,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN amount ELSE 0 END) AS loan1_amt_old_idr,
        SUM(loan_cycle_amount) AS loan_cycle_amount_idr,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN loan_cycle_amount ELSE 0 END) AS loan_cycle_amt_new_idr,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN loan_cycle_amount ELSE 0 END) AS loan_cycle_amt_old_idr

    FROM ind.ba_asset_base_info
    WHERE issue_month >= '2025-01-01'
      AND if_issue = 1
    GROUP BY issue_month
    ORDER BY issue_month
),

-- ================================================
-- 2. Duration Metrics (Loan Cycle and Payment Duration)
-- ================================================
duration AS (
    SELECT  
        issue_month,
        
        -- Average loan cycle (total / NEW / OLD)
        CASE WHEN SUM(contract_amount) > 0 THEN SUM(loan_cycle_amount) / SUM(contract_amount) ELSE 0 END AS avg_loan_cycle,
        CASE WHEN SUM(CASE WHEN grant_strategy = 'NEW' THEN contract_amount ELSE 0 END) > 0 
             THEN SUM(CASE WHEN grant_strategy = 'NEW' THEN loan_cycle_amount ELSE 0 END) / 
                  SUM(CASE WHEN grant_strategy = 'NEW' THEN contract_amount ELSE 0 END) 
             ELSE 0 END AS new_avg_loan_cycle,
        CASE WHEN SUM(CASE WHEN grant_strategy = 'OLD' THEN contract_amount ELSE 0 END) > 0 
             THEN SUM(CASE WHEN grant_strategy = 'OLD' THEN loan_cycle_amount ELSE 0 END) / 
                  SUM(CASE WHEN grant_strategy = 'OLD' THEN contract_amount ELSE 0 END) 
             ELSE 0 END AS old_avg_loan_cycle,
        
        -- Average payment duration (weighted by should_capital)
        CASE WHEN SUM(should_capital) > 0 THEN SUM(day_diff * should_capital) / SUM(should_capital) ELSE 0 END AS all_duration,
        CASE WHEN SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital ELSE 0 END) > 0 
             THEN SUM(CASE WHEN grant_strategy = 'NEW' THEN day_diff * should_capital ELSE 0 END) / 
                  SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital ELSE 0 END) 
             ELSE 0 END AS new_duration,
        CASE WHEN SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital ELSE 0 END) > 0 
             THEN SUM(CASE WHEN grant_strategy = 'OLD' THEN day_diff * should_capital ELSE 0 END) / 
                  SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital ELSE 0 END) 
             ELSE 0 END AS old_duration

    FROM (
        -- Repayment data with day difference
        SELECT 
            camera_id,
            DATE_FORMAT(create_time, '%Y-%m-01') AS issue_month,
            DATE_DIFF('day', DATE(create_time), COALESCE(DATE(fact_time), DATE(should_time))) AS day_diff,
            DATE(create_time) AS issue_date,
            should_capital  
        FROM ods.s02_loan_repayment 
    ) a  
    JOIN (
        -- Loan base info
        SELECT 
            biz_id,
            grant_strategy,
            loan_cycle,
            loan_cycle_amount,
            contract_amount,
            haircut_amount / contract_amount AS haircut_rate 
        FROM ind.ba_asset_base_info 
        WHERE if_issue = 1
    ) b ON a.camera_id = TRY_CAST(b.biz_id AS BIGINT)
    GROUP BY issue_month
),

-- ================================================
-- 3. First Issue Time (NEW_PURE users)
-- ================================================
mid_app_date AS (
    SELECT 
        mid,
        MIN(release_time) AS first_issue_time,   
        MIN(app_date) AS first_app_date
    FROM ind.ba_asset_base_info
    WHERE if_app = 1 
      AND grant_strategy = 'NEW' 
      AND is_reloan2 = 'NEW_PURE'
    GROUP BY mid
),

-- ================================================
-- 4. Registration to Issue Conversion
-- ================================================
reg_cnt AS (
    SELECT 
        DATE_FORMAT(reg_dt, '%Y-%m-01') AS reg_month, 
        COUNT(DISTINCT t.mid) AS reg_cnt,    
        COUNT(DISTINCT CASE WHEN DATE(mad.first_issue_time) = t.reg_dt THEN t.mid END) AS t0_issue_cnt,
        COUNT(DISTINCT CASE WHEN mad.first_issue_time <= CURRENT_DATE - INTERVAL '1' DAY THEN t.mid END) AS all_issue_cnt,  
        COUNT(DISTINCT CASE WHEN mad.first_issue_time <= t.reg_time + INTERVAL '24' HOUR THEN t.mid END) AS t24h_issue_cnt, 
        COUNT(DISTINCT CASE WHEN mad.first_issue_time <= t.reg_time + INTERVAL '30' DAY THEN t.mid END) AS t30d_issue_cnt   

    FROM ind.tyn_reg_install_new t
    LEFT JOIN mid_app_date mad ON mad.mid = t.mid
    WHERE t.reg_dt >= DATE '2025-01-01'
    GROUP BY reg_month
),

-- ================================================
-- 5. NEW_PURE Application Metrics
-- ================================================
new_pure_app_month AS (
    SELECT 
        app_month, 
        COUNT(DISTINCT CASE WHEN if_app = 1 THEN mid END) AS app_user_cnt,
        COUNT(DISTINCT CASE WHEN if_in_confirm_temp = 1 THEN mid END) AS in_confirm_user_cnt,
        COUNT(DISTINCT CASE WHEN if_confirm_passed_final = 1 AND app_month = DATE_FORMAT(confirm_date_final, '%Y-%m-01') THEN mid END) AS confirm_user_cnt,
        COUNT(DISTINCT CASE WHEN if_confirm_passed_final = 1 AND DATE_FORMAT(confirm_date_final, '%Y-%m-01') <= DATE_FORMAT(CURRENT_DATE - INTERVAL '1' DAY, '%Y-%m-01') THEN mid END) AS confirm_user_cnt_all,
        COUNT(DISTINCT CASE WHEN if_confirm_passed_num_24h = 1 AND app_month = DATE_FORMAT(confirm_date_final, '%Y-%m-01') THEN mid END) AS confirm_user_cnt_24h,
        COUNT(DISTINCT CASE WHEN if_confirm_passed_num_t30 = 1 AND app_month = DATE_FORMAT(confirm_date_final, '%Y-%m-01') THEN mid END) AS confirm_user_cnt_t30,
        COUNT(DISTINCT CASE WHEN if_issue = 1 AND app_month = issue_month THEN mid END) AS issue_user_cnt,  
        SUM(CASE WHEN if_in_confirm_temp = 1 THEN grantcredit_amount END) AS new_pure_in_confirm_grantcredit_amount,   
        COUNT(DISTINCT CASE WHEN app_month = issue_month THEN mid END) AS issue_user_from_app_m,  
        COUNT(DISTINCT CASE WHEN app_month = DATE_FORMAT(confirm_date_final, '%Y-%m-01') THEN mid END) AS confirm_user_from_app_m,
        COUNT(DISTINCT CASE WHEN issue_month <= DATE_FORMAT(CURRENT_DATE - INTERVAL '1' DAY, '%Y-%m-01') THEN mid END) AS issue_user_from_app_all,
        COUNT(DISTINCT CASE WHEN DATE_FORMAT(confirm_date_final, '%Y-%m-01') <= DATE_FORMAT(CURRENT_DATE - INTERVAL '1' DAY, '%Y-%m-01') THEN mid END) AS confirm_user_from_app_all,
        COUNT(DISTINCT CASE WHEN app_month = issue_month THEN biz_id END) AS issue_cnt_from_app_m,
        COUNT(DISTINCT CASE WHEN app_month = DATE_FORMAT(confirm_date_final, '%Y-%m-01') THEN biz_id END) AS confirm_cnt_from_app_m,
        SUM(CASE WHEN app_month = issue_month THEN contract_amount_usd END) AS issue_amt_from_app_m,
        SUM(CASE WHEN app_month = DATE_FORMAT(confirm_date_final, '%Y-%m-01') THEN contract_amount_usd END) AS confirm_amt_from_app_m

    FROM ind.ba_asset_base_info 
    WHERE grant_strategy = 'NEW' 
      AND if_app = 1 
      AND is_reloan2 = 'NEW_PURE'
      AND DATE(app_date) >= DATE '2025-01-01'
    GROUP BY app_month
),

-- ================================================
-- 6. NEW Confirmation Metrics
-- ================================================
new_confirm_month AS (
    SELECT  
        DATE_FORMAT(confirm_date_final, '%Y-%m-01') AS confirm_month,
        COUNT(DISTINCT mid) AS confirm_new_user_cnt,  
        SUM(apply_grantcredit_amount) AS confirm_grantcredit_amount,  
        SUM(contract_amount_usd) AS contract_amount_usd,   
        COUNT(DISTINCT CASE WHEN if_issue = 1 THEN mid END) AS issue_user_cnt,  
        COUNT(DISTINCT CASE WHEN issue_month = DATE_FORMAT(confirm_date_final, '%Y-%m-01') AND if_issue = 1 THEN biz_id END) AS issue_cnt_from_confirm,  
        COUNT(DISTINCT biz_id) AS confirm_new_cnt, 
        SUM(CASE WHEN issue_month = DATE_FORMAT(confirm_date_final, '%Y-%m-01') AND if_issue = 1 THEN contract_amount_usd ELSE 0 END) AS issue_amt_from_confirm 

    FROM ind.ba_asset_base_info 
    WHERE grant_strategy = 'NEW' 
      AND if_app = 1  
      AND if_confirm_passed_final = 1
      AND DATE(app_date) >= DATE '2025-01-01'
    GROUP BY confirm_month
),

-- ================================================
-- 7. Total Confirmation Metrics (NEW + OLD)
-- ================================================
total_confirm_month AS ( 
    SELECT  
        DATE_FORMAT(confirm_date_final, '%Y-%m-01') AS confirm_month,
        COUNT(DISTINCT CASE WHEN issue_month = DATE_FORMAT(confirm_date_final, '%Y-%m-01') AND if_issue = 1 THEN biz_id END) AS issue_cnt_from_confirm_all,  
        COUNT(DISTINCT biz_id) AS confirm_all_cnt, 
        COUNT(DISTINCT CASE WHEN grant_strategy = 'OLD' THEN mid END) AS confirm_old_user_cnt,   
        SUM(CASE WHEN issue_month = DATE_FORMAT(confirm_date_final, '%Y-%m-01') AND if_issue = 1 THEN contract_amount_usd ELSE 0 END) AS issue_amt_from_confirm_all,  
        SUM(apply_grantcredit_amount) AS confirm_grantcredit_amount_all,  
        COUNT(DISTINCT CASE WHEN issue_month = DATE_FORMAT(confirm_date_final, '%Y-%m-01') AND if_issue = 1 THEN mid END) AS issue_user_from_confirm_all,  
        COUNT(DISTINCT mid) AS confirm_all_user_cnt

    FROM ind.ba_asset_base_info 
    WHERE if_app = 1  
      AND if_confirm_passed_final = 1
      AND DATE(app_date) >= DATE '2025-01-01'
    GROUP BY confirm_month
),

-- ================================================
-- 8. Application Funnel Metrics
-- ================================================
application_metrics AS ( 
    SELECT  
        app_month, 
        
        -- Application counts
        SUM(CASE WHEN if_recall = 0 THEN if_app END) AS if_app,
        SUM(CASE WHEN grant_strategy = 'NEW' AND if_recall = 0 THEN if_app END) AS new_if_app,
        SUM(CASE WHEN grant_strategy = 'OLD' AND if_recall = 0 THEN if_app END) AS old_if_app,

        -- External data 3 passed (NEW: in_confirm_temp, OLD: external_data_3_passed)
        SUM(CASE WHEN grant_strategy = 'OLD' AND if_recall = 0 THEN if_external_data_3_passed
                 WHEN grant_strategy = 'NEW' THEN if_in_confirm_temp END) AS if_external_3_passed,
        SUM(CASE WHEN grant_strategy = 'OLD' AND if_recall = 0 THEN if_external_data_3_passed END) AS old_if_external_3_passed,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN if_in_confirm_temp END) AS new_if_external_3_passed,  

        -- External data 4 passed (NEW: confirm_passed_final, OLD: in_external_data_4)
        SUM(CASE WHEN grant_strategy = 'OLD' AND if_recall = 0 THEN if_in_external_data_4
                 WHEN grant_strategy = 'NEW' THEN if_confirm_passed_final END) AS if_in_external_data_4,
        SUM(CASE WHEN grant_strategy = 'OLD' AND if_recall = 0 THEN if_in_external_data_4 END) AS old_if_in_external_data_4,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN if_confirm_passed_final END) AS new_if_in_external_data_4,

        -- External data 4 passed
        SUM(if_external_data_4_passed) AS if_external_data_4_passed,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN if_external_data_4_passed END) AS old_if_external_data_4_passed,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN if_external_data_4_passed END) AS new_if_external_data_4_passed,

        -- Confirm apply amounts
        SUM(CASE WHEN if_confirm_passed_final = 1 THEN apply_amount END) AS confirm_apply_amount,
        SUM(CASE WHEN grant_strategy = 'OLD' AND if_confirm_passed_final = 1 THEN apply_amount END) AS old_confirm_apply_amount,
        SUM(CASE WHEN grant_strategy = 'NEW' AND if_confirm_passed_final = 1 THEN apply_amount END) AS new_confirm_apply_amount,

        -- Contract amounts (USD)
        SUM(contract_amount_usd1) AS total_contract_amount_usd,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN contract_amount_usd1 END) AS old_contract_amount_usd,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN contract_amount_usd1 END) AS new_contract_amount_usd,

        -- Confirmation metrics
        SUM(if_in_confirm_temp) AS in_confirm_cnt, 
        SUM(CASE WHEN grant_strategy = 'OLD' THEN if_in_confirm_temp END) AS old_in_confirm_cnt,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN if_in_confirm_temp END) AS new_in_confirm_cnt,
        SUM(if_confirm_passed_final) AS confirm_passed_cnt, 
        SUM(CASE WHEN grant_strategy = 'OLD' THEN if_confirm_passed_final END) AS old_confirm_passed_cnt,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN if_confirm_passed_final END) AS new_confirm_passed_cnt 

    FROM ind.ba_asset_base_info
    WHERE DATE(app_date) >= DATE('2025-01-01')  
      AND DATE(app_date) < CURRENT_DATE
      AND if_app = 1
    GROUP BY app_month
),

-- ================================================
-- 9. Overdue Amount Ratios
-- ================================================
due_amt AS (
    SELECT 
        app_month, 
        
        -- Total overdue ratios
        SUM(overdue_amount_1_0) / NULLIF(SUM(should_capital_1_0), 0) AS total_overdue_amount_1_0_ratio,
        SUM(overdue_amount_1_30) / NULLIF(SUM(should_capital_1_30), 0) AS total_overdue_amount_1_30_ratio,
        SUM(overdue_amount_3_30) / NULLIF(SUM(should_capital_3_30), 0) AS total_overdue_amount_3_30_ratio,
        SUM(overdue_amount_total_30) / NULLIF(SUM(should_capital_total_30), 0) AS total_overdue_amount_total_30_ratio,
        
        -- T1/T30 due ratios
        SUM(t1_capital_due_d1) / NULLIF(SUM(should_capital_d1), 0) AS total_t1_capital_due_d1_ratio,
        SUM(t30_capital_due_d30) / NULLIF(SUM(should_capital_d30), 0) AS total_t30_capital_due_d30_ratio,
        
        -- NEW overdue ratios
        SUM(CASE WHEN grant_strategy = 'NEW' THEN overdue_amount_1_0 ELSE 0 END) / NULLIF(SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital_1_0 ELSE 0 END), 0) AS new_overdue_amount_1_0_ratio,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN overdue_amount_1_30 ELSE 0 END) / NULLIF(SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital_1_30 ELSE 0 END), 0) AS new_overdue_amount_1_30_ratio,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN overdue_amount_3_30 ELSE 0 END) / NULLIF(SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital_3_30 ELSE 0 END), 0) AS new_overdue_amount_3_30_ratio,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN overdue_amount_total_30 ELSE 0 END) / NULLIF(SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital_total_30 ELSE 0 END), 0) AS new_overdue_amount_total_30_ratio,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN t1_capital_due_d1 ELSE 0 END) / NULLIF(SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital_d1 ELSE 0 END), 0) AS new_t1_capital_due_d1_ratio,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN t30_capital_due_d30 ELSE 0 END) / NULLIF(SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital_d30 ELSE 0 END), 0) AS new_t30_capital_due_d30_ratio,
        
        -- OLD overdue ratios
        SUM(CASE WHEN grant_strategy = 'OLD' THEN overdue_amount_1_0 ELSE 0 END) / NULLIF(SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital_1_0 ELSE 0 END), 0) AS old_overdue_amount_1_0_ratio,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN overdue_amount_1_30 ELSE 0 END) / NULLIF(SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital_1_30 ELSE 0 END), 0) AS old_overdue_amount_1_30_ratio,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN overdue_amount_3_30 ELSE 0 END) / NULLIF(SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital_3_30 ELSE 0 END), 0) AS old_overdue_amount_3_30_ratio,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN overdue_amount_total_30 ELSE 0 END) / NULLIF(SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital_total_30 ELSE 0 END), 0) AS old_overdue_amount_total_30_ratio,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN t1_capital_due_d1 ELSE 0 END) / NULLIF(SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital_d1 ELSE 0 END), 0) AS old_t1_capital_due_d1_ratio,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN t30_capital_due_d30 ELSE 0 END) / NULLIF(SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital_d30 ELSE 0 END), 0) AS old_t30_capital_due_d30_ratio

    FROM ind.ba_apply_should_result 
    GROUP BY app_month
),

-- ================================================
-- 10. OLD Managed Users
-- ================================================
old_managed_month AS (
    SELECT 
        DATE_FORMAT(DATE(SLICE_date), '%Y-%m-01') AS stat_month,
        COUNT(DISTINCT CASE WHEN if_overdue <> 1 AND if_reject_recent_7_days <> 1 THEN mid END) AS old_managed_cnt
    FROM ind.ys_operable_reloan_cnt_251119
    GROUP BY stat_month
),

-- ================================================
-- 11. On-loan Balance
-- ================================================
onloan_balance AS (
    SELECT  
        DATE_FORMAT(a1.data_date1, '%Y-%m-01') AS balance_month,
        SUM(a1.should_capital) AS principal,
        COUNT(DISTINCT CASE WHEN due_days <= 30 AND grant_strategy = 'OLD' THEN c1.mid END) AS old_repay_user_num,
        SUM(CASE WHEN due_days <= 30 THEN a1.should_capital - a1.fact_capital END) AS owing_principal,
        COUNT(DISTINCT CASE WHEN due_days <= 30 THEN c1.mid END) AS repay_user_num

    FROM (
        -- Repayment history with month-end date
        SELECT 
            a.indexs,
            should_capital,
            fact_capital,
            DATE_TRUNC('month', TO_DATE(CASE WHEN LENGTH(data_date) = 6 THEN CONCAT(data_date, '01') ELSE data_date END, 'yyyymmdd') + INTERVAL '1' MONTH) AS dt,
            camera_id,
            lid,
            DATE_TRUNC('month', TO_DATE(CASE WHEN LENGTH(data_date) = 6 THEN CONCAT(data_date, '01') ELSE data_date END, 'yyyymmdd') + INTERVAL '1' MONTH) - INTERVAL '1' DAY AS data_date1,
            data_date
        FROM ods.s02_loan_repayment_his a
        WHERE (
            (DATE_TRUNC('month', TO_DATE(CASE WHEN LENGTH(data_date) = 6 THEN CONCAT(data_date, '01') ELSE data_date END, 'yyyymmdd') + INTERVAL '1' MONTH) - INTERVAL '1' DAY = TO_DATE(CASE WHEN LENGTH(data_date) = 6 THEN CONCAT(data_date, '01') ELSE data_date END, 'yyyymmdd')
            OR data_date < '202409' 
            OR TO_DATE(data_date, 'yyyymmdd') = CURRENT_DATE - INTERVAL '1' DAY
        ) AND LENGTH(data_date) = 8
    ) a1
    LEFT JOIN (
        -- Loan info
        SELECT 
            camera_id,
            DATE(trade_start_time) AS trade_start_time,
            DATE(trade_end_time) AS trade_end_time,
            DATE(trade_end_time) + INTERVAL '60' DAY AS due_date_60,
            loan_indexs,
            loan_cycle
        FROM ods.s02_loan
    ) b1 ON CAST(a1.camera_id AS BIGINT) = CAST(b1.camera_id AS BIGINT)
    LEFT JOIN ind.xly_application_funnel c1 ON CAST(a1.camera_id AS BIGINT) = CAST(c1.biz_id AS BIGINT)
    LEFT JOIN (
        -- Max due days per loan per month
        SELECT 
            data_date1,
            lid,
            MAX(due_days) AS due_days
        FROM (
            SELECT 
                DATE_TRUNC('month', TO_DATE(CASE WHEN LENGTH(data_date) = 6 THEN CONCAT(data_date, '01') ELSE data_date END, 'yyyymmdd') + INTERVAL '1' MONTH) - INTERVAL '1' DAY AS data_date1,
                lid,
                should_time,
                fact_time,
                DATE_DIFF('day', DATE(should_time), CASE WHEN fact_time IS NULL THEN TO_DATE(data_date, 'yyyymmdd') ELSE DATE(fact_time) END) AS due_days  
            FROM ods.s02_loan_repayment_his
            WHERE (
                (DATE_TRUNC('month', TO_DATE(CASE WHEN LENGTH(data_date) = 6 THEN CONCAT(data_date, '01') ELSE data_date END, 'yyyymmdd') + INTERVAL '1' MONTH) - INTERVAL '1' DAY = TO_DATE(CASE WHEN LENGTH(data_date) = 6 THEN CONCAT(data_date, '01') ELSE data_date END, 'yyyymmdd')
                OR data_date < '202409' 
                OR TO_DATE(data_date, 'yyyymmdd') = CURRENT_DATE - INTERVAL '1' DAY
            ) AND LENGTH(data_date) = 8
        ) GROUP BY data_date1, lid
    ) d1 ON CAST(a1.lid AS BIGINT) = CAST(d1.lid AS BIGINT) AND a1.data_date1 = d1.data_date1
    
    WHERE TO_CHAR(DATE(a1.data_date1), 'yyyy-mm') <= TO_CHAR(DATE(due_date_60), 'yyyy-mm')
    GROUP BY balance_month
),

-- ================================================
-- 12. Max Grant Amount
-- ================================================
grant_amount_max_data AS (
    SELECT 
        DATE_FORMAT(data_date1, '%Y-%m-01') AS grant_month,
        SUM(grant_amount_max) AS grant_amount_max
    
    FROM (
        SELECT
            a.data_date1,
            a.data_date,
            a.camera_id,
            b.grant_amount_max,
            ROW_NUMBER() OVER (PARTITION BY b.mid, a.data_date ORDER BY b.release_time DESC) AS rn
        
        FROM (
            -- Due days per camera_id per date
            SELECT 
                data_date1,
                data_date,
                camera_id,
                MAX(due_days) AS due_days
            FROM (
                SELECT 
                    DATE_TRUNC('month', TO_DATE(CASE WHEN LENGTH(data_date) = 6 THEN CONCAT(data_date, '01') ELSE data_date END, 'yyyymmdd') + INTERVAL '1' MONTH) - INTERVAL '1' DAY AS data_date1,
                    data_date,
                    lid,
                    should_time,
                    fact_time,
                    camera_id,
                    DATE_DIFF('day', DATE(should_time), CASE WHEN fact_time IS NULL THEN TO_DATE(data_date, 'yyyymmdd') ELSE DATE(fact_time) END) AS due_days  
                FROM ods.s02_loan_repayment_his
                WHERE (
                    (DATE_TRUNC('month', TO_DATE(CASE WHEN LENGTH(data_date) = 6 THEN CONCAT(data_date, '01') ELSE data_date END, 'yyyymmdd') + INTERVAL '1' MONTH) - INTERVAL '1' DAY = TO_DATE(CASE WHEN LENGTH(data_date) = 6 THEN CONCAT(data_date, '01') ELSE data_date END, 'yyyymmdd')
                    OR data_date < '202409' 
                    OR TO_DATE(data_date, 'yyyymmdd') = CURRENT_DATE - INTERVAL '1' DAY
                ) AND LENGTH(data_date) = 8
            ) GROUP BY data_date1, data_date, camera_id
        ) a
        LEFT JOIN (
            SELECT biz_id, grant_amount_max, mid, release_time 
            FROM ind.ba_asset_base_info
            WHERE if_issue = 1 AND if_app = 1
        ) b ON CAST(a.camera_id AS BIGINT) = CAST(b.biz_id AS BIGINT)
        WHERE a.due_days <= 30
    ) c
    WHERE rn = 1
    GROUP BY grant_month
),

-- ================================================
-- 13. Owing Principal (OLD users)
-- ================================================
owing_principal_data AS (
    SELECT
        issue_month,
        SUM(owing_principal) AS owing_principal,
        COUNT(DISTINCT biz_id) AS biz_num
    
    FROM (
        SELECT
            a.*,
            (should_capital - fact_capital + contract_amount) AS owing_principal
        
        FROM (
            SELECT
                biz_id,
                mid,
                release_time,
                app_date,
                issue_date,
                contract_amount,
                app_time,
                issue_month,
                baseinfo_onloan_amount,
                SUM(should_capital) AS should_capital,
                SUM(fact_capital) AS fact_capital
            
            FROM (
                SELECT
                    a.*,
                    b.should_capital,
                    CASE WHEN COALESCE(b.fact_time, CURRENT_DATE) > a.app_time THEN 0 ELSE b.fact_capital END AS fact_capital
                
                FROM (
                    SELECT biz_id, mid, release_time, app_date, issue_date, contract_amount, app_time, issue_month, baseinfo_onloan_amount 
                    FROM ind.xly_application_funnel
                    WHERE if_issue = 1 AND if_app = 1
                      AND issue_date >= '2025-01-01'
                      AND grant_strategy = 'OLD'
                ) a 
                LEFT JOIN ods.s02_loan_repayment b ON CAST(a.mid AS BIGINT) = CAST(b.customer_id AS BIGINT)
                WHERE a.app_time > b.create_time
            ) a 
            GROUP BY biz_id, mid, release_time, app_date, issue_date, contract_amount, app_time, issue_month, baseinfo_onloan_amount
        ) a
    ) a
    GROUP BY issue_month
),

-- ================================================
-- 14. Cohort Analysis (NEW to OLD conversion)
-- ================================================
cohort AS (
    SELECT
        a.first_loan_issue_month,
        SUM(amt_old_6m) / SUM(cnt_new) AS cohort_6m_cnt_rate,
        SUM(amt_old_12m) / SUM(cnt_new) AS cohort_12m_cnt_rate,
        SUM(amt_old_6m) / SUM(amt_new) AS cohort_6m_amt_rate,
        SUM(amt_old_12m) / SUM(amt_new) AS cohort_12m_amt_rate
    
    FROM (
        -- OLD users with contract amounts by first loan month
        SELECT
            first_loan_issue_month,
            SUM(CASE WHEN month_num_issue <= 6 THEN contract_amount_usd1 END) AS amt_old_6m,
            SUM(CASE WHEN month_num_issue <= 12 THEN contract_amount_usd1 END) AS amt_old_12m
        FROM ind.ba_asset_base_info
        WHERE grant_strategy = 'OLD'
          AND if_issue = 1
        GROUP BY first_loan_issue_month
    ) a
    LEFT JOIN (
        -- NEW users count and amount
        SELECT 
            issue_month,
            COUNT(mid) AS cnt_new,
            SUM(contract_amount_usd1) AS amt_new
        FROM ind.ba_asset_base_info
        WHERE grant_strategy = 'NEW'
          AND if_issue = 1
        GROUP BY issue_month
    ) b ON a.first_loan_issue_month = b.issue_month
    GROUP BY a.first_loan_issue_month
)

-- ================================================
-- Final Report - Combine All Metrics
-- ================================================
SELECT 
    im.issue_month AS month,
    
    -- Active users
    daa.daily_cnt,
    maa.monthly_cnt,
    
    -- On-loan balance
    ob.owing_principal / f.exchange_rate_to_dollar AS onloan_amount_30_m,
    
    -- Issue metrics
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
    
    -- Registration metrics
    rc.reg_cnt,
    npam.app_user_cnt,
    npam.in_confirm_user_cnt,
    npam.confirm_user_cnt,
    npam.issue_user_cnt,
    ncm.confirm_new_user_cnt,
    
    -- Average amounts
    npam.new_pure_in_confirm_grantcredit_amount / NULLIF(npam.in_confirm_user_cnt, 0) AS new_pure_in_confirm_avg_amt,
    ncm.confirm_grantcredit_amount / NULLIF(ncm.confirm_new_user_cnt, 0) AS new_confirm_avg_amt,
    
    -- Conversion rates
    rc.all_issue_cnt / NULLIF(rc.reg_cnt, 0) AS new_reg_issue_rate,
    rc.t24h_issue_cnt / NULLIF(rc.reg_cnt, 0) AS new_t24h_reg_issue_rate,
    rc.t30d_issue_cnt / NULLIF(rc.reg_cnt, 0) AS new_t30d_reg_issue_rate,
    
    -- NEW_PURE confirmation rates
    npam.in_confirm_user_cnt / NULLIF(npam.app_user_cnt, 0) AS new_pure_in_confirm_rate,
    npam.confirm_user_cnt_all / NULLIF(npam.in_confirm_user_cnt, 0) AS new_pure_confirm_rate,
    npam.confirm_user_cnt_24h / NULLIF(npam.in_confirm_user_cnt, 0) AS new_pure_confirm_rate_24h,
    npam.confirm_user_cnt_t30 / NULLIF(npam.in_confirm_user_cnt, 0) AS new_pure_confirm_rate_t30,
    
    -- Overall confirmation rates
    am.confirm_passed_cnt / NULLIF(am.in_confirm_cnt, 0) AS total_confirm_rate,
    am.new_confirm_passed_cnt / NULLIF(am.new_in_confirm_cnt, 0) AS new_confirm_rate,
    am.old_confirm_passed_cnt / NULLIF(am.old_in_confirm_cnt, 0) AS old_confirm_rate,
    
    -- NEW funnel metrics
    am.new_if_external_3_passed / NULLIF(am.new_if_app, 0) AS new_before_pass_rate,
    am.new_if_external_data_4_passed / NULLIF(am.new_if_in_external_data_4, 0) AS new_after_pass_rate,
    am.new_contract_amount_usd / NULLIF(am.new_confirm_apply_amount, 0) AS new_after_pass_amt_rate,
    
    -- OLD funnel metrics
    am.old_if_external_3_passed / NULLIF(am.old_if_app, 0) AS old_before_pass_rate,
    am.old_if_external_data_4_passed / NULLIF(am.old_if_in_external_data_4, 0) AS old_after_pass_rate,
    am.old_contract_amount_usd / NULLIF(am.old_confirm_apply_amount, 0) AS old_after_pass_amt_rate,
    
    -- OLD managed metrics
    omm.old_managed_cnt,
    tcm.confirm_old_user_cnt,
    ob.old_repay_user_num AS old_onloan_amount_30_m,
    opd.owing_principal / (opd.biz_num * f.exchange_rate_to_dollar) AS old_onloan_amount_30_m_user_avg,
    
    -- User average metrics
    ob.owing_principal / (ob.repay_user_num * f.exchange_rate_to_dollar) AS onloan_amount_30_m_user_avg,
    gamd.grant_amount_max / NULLIF(ob.repay_user_num, 0) AS grant_amount_30_m_user_avg,
    npam.new_pure_in_confirm_grantcredit_amount / NULLIF(npam.in_confirm_user_cnt, 0) AS new_pure_confirm_app_avg_amt,
    
    -- Cohort metrics
    c.cohort_6m_cnt_rate,
    c.cohort_12m_cnt_rate,
    c.cohort_6m_amt_rate,
    c.cohort_12m_amt_rate,
    
    -- Duration metrics
    d.avg_loan_cycle,
    d.new_avg_loan_cycle,
    d.old_avg_loan_cycle,
    d.all_duration,
    d.new_duration,
    d.old_duration,
    
    -- Overdue ratios
    da.total_overdue_amount_1_0_ratio,
    da.new_overdue_amount_1_0_ratio,
    da.old_overdue_amount_1_0_ratio,
    da.total_overdue_amount_1_30_ratio,
    da.new_overdue_amount_1_30_ratio,
    da.old_overdue_amount_1_30_ratio,
    da.total_overdue_amount_3_30_ratio,
    da.new_overdue_amount_3_30_ratio,
    da.old_overdue_amount_3_30_ratio,
    da.total_overdue_amount_total_30_ratio,
    da.new_overdue_amount_total_30_ratio,
    da.old_overdue_amount_total_30_ratio,
    
    -- T1/T30 due ratios
    da.total_t1_capital_due_d1_ratio,
    da.new_t1_capital_due_d1_ratio,
    da.old_t1_capital_due_d1_ratio,
    da.total_t30_capital_due_d30_ratio,
    da.new_t30_capital_due_d30_ratio,
    da.old_t30_capital_due_d30_ratio,
    
    -- Exchange rate
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
LEFT JOIN ind.ys_daily_activate daa ON im.issue_month = DATE_FORMAT(DATE_PARSE(daa.month, '%Y/%m/%d'), '%Y-%m-01')
LEFT JOIN ind.ys_monthly_activate maa ON im.issue_month = DATE_FORMAT(DATE_PARSE(maa.month, '%Y/%m/%d'), '%Y-%m-01')
LEFT JOIN cohort c ON im.issue_month = c.first_loan_issue_month
LEFT JOIN dim.dim_exchange_rate_cost f ON TO_CHAR(DATE(im.issue_month), 'yyyymm') = f.month_id AND f.account_currency = 'IDR'

ORDER BY month;
