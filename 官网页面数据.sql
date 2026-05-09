 
WITH date_ranges AS (
    SELECT 
        1 as period_id,
        'Begin' as period_name,
        NULL as start_date,
        CURRENT_DATE - INTERVAL '1' DAY as end_date
    UNION ALL
    SELECT 
        2 as period_id,
        'Year' as period_name,
        CURRENT_DATE - INTERVAL '1' YEAR as start_date,
        CURRENT_DATE - INTERVAL '1' DAY as end_date
    UNION ALL
    SELECT 
        3 as period_id,
        'Today' as period_name,
        CURRENT_DATE - INTERVAL '1' DAY as start_date,
        CURRENT_DATE - INTERVAL '1' DAY as end_date
),
loan_data AS ( 
    SELECT 
        d.period_id,
        d.period_name,
        SUM(a.contract_amount) AS loan_amt_total_idr,
        COUNT(DISTINCT a.mid) AS loan_customer_cnt_total,
        SUM(a.if_issue) AS loan_cnt_total,
        COUNT(DISTINCT a.account_name) AS account_cnt 
    FROM date_ranges d
    LEFT JOIN ind.ba_asset_base_info a 
        ON a.if_issue = 1 
        AND a.release_time < d.end_date + INTERVAL '1' DAY   
        AND (d.start_date IS NULL OR a.release_time >= d.start_date)
    GROUP BY 1,2
),
repayment_data AS (
     SELECT 
        dr.period_id,
        dr.period_name,
         SUM(CASE 
            WHEN d.state IN (0,2,4) 
            THEN COALESCE(d.should_capital, 0) - COALESCE(d.fact_capital, 0)
            ELSE 0 
        END) AS outstanding_balance,
         SUM(COALESCE(d.fact_capital, 0)) AS total_repayment_amount
    FROM date_ranges dr
    LEFT JOIN ind.ba_asset_base_info a 
        ON a.if_issue = 1 
        AND a.release_time < dr.end_date + INTERVAL '1' DAY
        AND (dr.start_date IS NULL OR a.release_time >= dr.start_date)
    LEFT JOIN ods.s02_loan_repayment d 
        ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(d.camera_id AS BIGINT)
    GROUP BY 1,2
)

 SELECT 
    l.period_name ,
    COALESCE(l.loan_amt_total_idr, 0) as issue_amount,
    COALESCE(r.outstanding_balance, 0) as outstanding_balance,
    COALESCE(r.total_repayment_amount, 0) as total_repayment_amount,
    COALESCE(l.loan_customer_cnt_total, 0) as loan_customer_cnt_total,
    COALESCE(l.loan_cnt_total, 0) as loan_cnt_total,
    COALESCE(l.account_cnt, 0) as account_cnt
FROM loan_data l
LEFT JOIN repayment_data r ON l.period_id = r.period_id
ORDER BY l.period_id;