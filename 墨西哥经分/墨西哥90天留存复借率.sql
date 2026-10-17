

WITH first_loans AS (
    SELECT
        DATE_TRUNC('month', t.release_time) AS issue_month,
        t.customer_id AS mid,
        t.release_time,
        t.contract_amount
    FROM ods.s02_loan t
    INNER JOIN mx.risk_double_loan_tag rt
        ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
    WHERE rt.double_loan = 0
      AND t.release_time >= DATE '2025-12-01'
      AND t.state IN (1, 2, 3)
),
reloans AS (
    SELECT
        t.customer_id AS mid,
        CAST(t.camera_id AS VARCHAR) AS biz_id,
        t.release_time,
        t.contract_amount
    FROM ods.s02_loan t
    INNER JOIN mx.risk_double_loan_tag rt
        ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
    WHERE rt.double_loan = 1
      AND t.release_time >= DATE '2025-12-01'
      AND t.state IN (1, 2, 3)
)
SELECT
    a.issue_month, -- 首贷月份
    d.exchange_rate_to_dollar,
    COUNT(DISTINCT a.mid) AS first_loan_cnt,   -- 首贷人数
    COUNT(DISTINCT b.biz_id) AS reloan_bizid_cnt_90d,  -- 首贷90天内复贷笔数
    COUNT(DISTINCT b.mid) AS reloan_mid_cnt_90d, -- 首贷90天内复贷人数
    SUM(b.contract_amount) AS reloan_amount_90d_mxn, -- 首贷90天内复贷金额本币
    ROUND(SUM(b.contract_amount) / d.exchange_rate_to_dollar, 2) AS reloan_amount_90d_usd,
    ROUND(COUNT(DISTINCT b.biz_id) * 1.0 / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_biz,
    ROUND(COUNT(DISTINCT b.mid) * 1.0 / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_mid
FROM first_loans a
LEFT JOIN reloans b
    ON a.mid = b.mid
   AND b.release_time > a.release_time
   AND date_diff('day', a.release_time, b.release_time) <= 90
left join dim.dim_exchange_rate_cost  d on account_currency = 'MXN' and  date_parse(d.month_id, '%Y%m')=a.issue_month
GROUP BY 1,2
ORDER BY 1,2


WITH first_loans AS (
    SELECT
        DATE_TRUNC('month', t.release_time) AS issue_month,
        t.customer_id AS mid,
        t.release_time,
        t.contract_amount
    FROM ods.s02_loan t
    INNER JOIN mx.risk_double_loan_tag rt
        ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
    WHERE rt.double_loan = 0
      AND t.release_time >= DATE '2025-12-01'
      AND t.state IN (1, 2, 3)
),
reloans AS (
    SELECT
        t.customer_id AS mid,
        CAST(t.camera_id AS VARCHAR) AS biz_id,
        t.release_time,
        t.contract_amount
    FROM ods.s02_loan t
    INNER JOIN mx.risk_double_loan_tag rt
        ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
    WHERE rt.double_loan = 1
      AND t.release_time >= DATE '2025-12-01'
      AND t.state IN (1, 2, 3)
)
SELECT
    a.issue_month, -- 首贷月份
    d.exchange_rate_to_dollar,
    COUNT(DISTINCT a.mid) AS first_loan_cnt,   -- 首贷人数
    COUNT(DISTINCT b.biz_id) AS reloan_bizid_cnt_90d,  -- 首贷90天内复贷笔数
    COUNT(DISTINCT b.mid) AS reloan_mid_cnt_90d, -- 首贷90天内复贷人数
    SUM(b.contract_amount) AS reloan_amount_90d_mxn, -- 首贷90天内复贷金额本币
    ROUND(SUM(b.contract_amount) / d.exchange_rate_to_dollar, 2) AS reloan_amount_90d_usd,
    ROUND(COUNT(DISTINCT b.biz_id) * 1.0 / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_biz,
    ROUND(COUNT(DISTINCT b.mid) * 1.0 / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_mid
FROM first_loans a
LEFT JOIN reloans b
    ON a.mid = b.mid
   AND b.release_time > a.release_time
   AND date_diff('day', a.release_time, b.release_time) <= 60
left join dim.dim_exchange_rate_cost  d on account_currency = 'MXN' and  date_parse(d.month_id, '%Y%m')=a.issue_month
GROUP BY 1,2
ORDER BY 1,2


-- 60天留存率
SELECT
    issue_month,
    COUNT(a.customer_id) AS new_cnt,
    COUNT(CASE WHEN COALESCE(b.overdue_days, 0) <= 0 THEN a.customer_id END) AS no_ovd_cnt,
    COUNT(CASE WHEN COALESCE(b.overdue_days, 0) <= 0 AND b.onloan_rid_cnt > 0 THEN a.customer_id END) AS onloan_cnt
FROM
(
    SELECT
        DATE_TRUNC('month', t.release_time) AS issue_month,
        t.customer_id,
        CAST(DATE_ADD('day', 60, t.release_time) AS DATE) AS obs_date   -- 强制转为 date
    FROM ods.s02_loan t
    INNER JOIN mx.risk_double_loan_tag rt
        ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
    WHERE rt.double_loan = 0
        AND t.release_time >= DATE '2025-12-01'
        AND t.state IN (1, 2, 3)
) a
LEFT JOIN
(
    SELECT
        customer_id,
        CAST(date_parse(data_date, '%Y%m%d') AS DATE) AS date_date,
        MAX(CASE WHEN state IN (2)
                 THEN DATE_DIFF('day', DATE(should_time), CAST(date_parse(data_date, '%Y%m%d') AS DATE))
                 ELSE 0 END) AS overdue_days,
        COUNT(CASE WHEN state IN (0, 2, 4)
                    AND DATE_DIFF('day', DATE(should_time), CAST(date_parse(data_date, '%Y%m%d') AS DATE)) <= 60
                   THEN rid END) AS onloan_rid_cnt
    FROM ods.s02_loan_repayment_his
    WHERE data_date >= '20251201'
    GROUP BY customer_id, CAST(date_parse(data_date, '%Y%m%d') AS DATE)
) b
ON a.customer_id = b.customer_id AND a.obs_date = b.date_date
GROUP BY issue_month
ORDER BY issue_month;








-- 90天
SELECT
    issue_month,
    COUNT(a.customer_id) AS new_cnt,
    COUNT(CASE WHEN COALESCE(b.overdue_days, 0) <= 0 THEN a.customer_id END) AS no_ovd_cnt,
    COUNT(CASE WHEN COALESCE(b.overdue_days, 0) <= 0 AND b.onloan_rid_cnt > 0 THEN a.customer_id END) AS onloan_cnt
FROM
(
    SELECT
        DATE_TRUNC('month', t.release_time) AS issue_month,
        t.customer_id,
        CAST(DATE_ADD('day', 90, t.release_time) AS DATE) AS obs_date   -- 强制转为 date
    FROM ods.s02_loan t
    INNER JOIN mx.risk_double_loan_tag rt
        ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
    WHERE rt.double_loan = 0
        AND t.release_time >= DATE '2025-12-01'
        AND t.state IN (1, 2, 3)
) a
LEFT JOIN
(
    SELECT
        customer_id,
        CAST(date_parse(data_date, '%Y%m%d') AS DATE) AS date_date,
        MAX(CASE WHEN state IN (2)
                 THEN DATE_DIFF('day', DATE(should_time), CAST(date_parse(data_date, '%Y%m%d') AS DATE))
                 ELSE 0 END) AS overdue_days,
        COUNT(CASE WHEN state IN (0, 2, 4)
                    AND DATE_DIFF('day', DATE(should_time), CAST(date_parse(data_date, '%Y%m%d') AS DATE)) <= 90
                   THEN rid END) AS onloan_rid_cnt
    FROM ods.s02_loan_repayment_his
    WHERE data_date >= '20251201'
    GROUP BY customer_id, CAST(date_parse(data_date, '%Y%m%d') AS DATE)
) b
ON a.customer_id = b.customer_id AND a.obs_date = b.date_date
GROUP BY issue_month
ORDER BY issue_month;
