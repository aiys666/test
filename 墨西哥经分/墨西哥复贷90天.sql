-- 墨西哥复贷90天分析
-- 首贷放款后90天内复贷笔数/人数/金额
-- 与印尼 ind.ba_asset_base_info 的 reloan_num 逻辑等价
-- 墨西哥用 double_loan=0(首贷) / double_loan=1(复贷) 区分

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
      AND t.release_time >= DATE '2025-07-01'
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
      AND t.release_time >= DATE '2025-07-01'
      AND t.state IN (1, 2, 3)
)
SELECT
    a.issue_month,
    COUNT(DISTINCT a.mid) AS first_loan_cnt,
    COUNT(DISTINCT b.biz_id) AS reloan_bizid_cnt_90d,
    COUNT(DISTINCT b.mid) AS reloan_mid_cnt_90d,
    SUM(b.contract_amount) AS reloan_amount_90d_mxn,
    ROUND(SUM(b.contract_amount) / 17.3594, 2) AS reloan_amount_90d_usd,
    ROUND(COUNT(DISTINCT b.biz_id) * 1.0 / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_biz,
    ROUND(COUNT(DISTINCT b.mid) * 1.0 / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_mid
FROM first_loans a
LEFT JOIN reloans b
    ON a.mid = b.mid
   AND b.release_time > a.release_time
   AND date_diff('day', a.release_time, b.release_time) <= 90
GROUP BY 1
ORDER BY 1
