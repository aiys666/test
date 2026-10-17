-- 墨西哥60/90天复借率 & 留存率

-- ========== 复借率（60天+90天）==========
-- 分母：首贷人数/金额（double_loan=0）
-- 分子：60/90天内复借人数/金额（double_loan=1）
WITH first_loans_r AS (
    SELECT 
        DATE_TRUNC('month', t.release_time) AS issue_month,
        t.customer_id AS mid,
        t.release_time,
        t.contract_amount
    FROM ods.s02_loan t
    INNER JOIN mx.risk_double_loan_tag rt
        ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
    WHERE rt.double_loan = 0
      AND t.release_time >= DATE '2026-01-01'
      AND t.state IN (1, 2, 3)
),
reloans_r AS (
    SELECT 
        t.customer_id AS mid,
        CAST(t.camera_id AS VARCHAR) AS biz_id,
        t.release_time,
        t.contract_amount
    FROM ods.s02_loan t
    INNER JOIN mx.risk_double_loan_tag rt
        ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
    WHERE rt.double_loan = 1
      AND t.release_time >= DATE '2026-01-01'
      AND t.state IN (1, 2, 3)
)
SELECT 
    a.issue_month,
    d.exchange_rate_to_dollar,
    COUNT(DISTINCT a.mid) AS first_loan_cnt,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 60 THEN b.biz_id END) AS reloan_bizid_cnt_60d,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 60 THEN b.mid END) AS reloan_mid_cnt_60d,
    SUM(CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 60 THEN b.contract_amount ELSE 0 END) AS reloan_amount_60d_mxn,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 90 THEN b.biz_id END) AS reloan_bizid_cnt_90d,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 90 THEN b.mid END) AS reloan_mid_cnt_90d,
    SUM(CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 90 THEN b.contract_amount ELSE 0 END) AS reloan_amount_90d_mxn,
    ROUND(CAST(COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 60 THEN b.mid END) AS DOUBLE) / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_mid_60d,
    ROUND(CAST(COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 90 THEN b.mid END) AS DOUBLE) / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_mid_90d,
    ROUND(CAST(COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 60 THEN b.biz_id END) AS DOUBLE) / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_biz_60d,
    ROUND(CAST(COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 90 THEN b.biz_id END) AS DOUBLE) / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_biz_90d
FROM first_loans_r a
LEFT JOIN reloans_r b
    ON a.mid = b.mid
   AND b.release_time > a.release_time
LEFT JOIN dim.dim_exchange_rate_cost d 
    ON d.account_currency = 'MXN' 
   AND DATE_PARSE(d.month_id, '%Y%m') = a.issue_month
GROUP BY 1, 2
ORDER BY 1, 2;

-- ========== 90天留存率（需表权限）==========
-- 90d人头留存率 = 新客成交后90天后仍有在贷且未逾期的用户数/新客用户数
-- 注意：dws.dws_risk_stgy_apply_mid_tags_his 和 ods.s02_loan_repayment_his 需要相应权限
-- WITH first_loans AS (
--     SELECT 
--         DATE_TRUNC('month', t.release_time) AS issue_month,
--         t.customer_id AS mid,
--         t.release_time,
--         DATE_ADD('day', 90, DATE(t.release_time)) AS first_loan_date_90plus
--     FROM ods.s02_loan t
--     INNER JOIN mx.risk_double_loan_tag rt
--         ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
--     WHERE rt.double_loan = 0
--       AND t.release_time >= DATE '2026-01-01'
--       AND t.state IN (1, 2, 3)
-- ),
-- no_overdue_90d AS (
--     SELECT 
--         DATE(DATE_PARSE(data_date, '%Y%m%d')) AS data_date,
--         mid AS customer_id
--     FROM dws.dws_risk_stgy_apply_mid_tags_his
--     GROUP BY 1, 2
--     HAVING MAX(curr_overdue_days) < 1
-- ),
-- onloan_90d AS (
--     SELECT  
--         DATE(DATE_PARSE(data_date, '%Y%m%d')) AS slice_date,
--         customer_id
--     FROM ods.s02_loan_repayment_his a1
--     WHERE a1.state IN (0, 2, 4)
--       AND DATE_DIFF('day', DATE(should_time), DATE_PARSE(data_date, '%Y%m%d')) <= 90
-- )
-- SELECT 
--     a.issue_month,
--     COUNT(DISTINCT a.mid) AS new_cnt,
--     COUNT(DISTINCT CASE WHEN b.customer_id IS NOT NULL AND c.customer_id IS NOT NULL THEN a.mid END) AS onloan_no_ovd_cnt_90d,
--     ROUND(CAST(COUNT(DISTINCT CASE WHEN b.customer_id IS NOT NULL AND c.customer_id IS NOT NULL THEN a.mid END) AS DOUBLE) 
--         / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS retention_90d_rate
-- FROM first_loans a
-- LEFT JOIN no_overdue_90d b
--     ON a.mid = b.customer_id
--    AND a.first_loan_date_90plus = b.data_date
-- LEFT JOIN onloan_90d c
--     ON a.mid = c.customer_id
--    AND a.first_loan_date_90plus = c.slice_date
-- GROUP BY 1
-- ORDER BY 1;