WITH
base_loan AS (
    SELECT
        DATE_TRUNC('month', date(r.release_time)) AS month,
        CASE WHEN r.is_reloan = 'new' THEN 0 ELSE 1 END AS double_loan,
        r.contract_amount,
        r.loan_cycle,
        r.should_interest,        -- 后收利息
        r.haircut_amount          -- 前砍息(砍头息)
    FROM mx.wxs_application_funnel r
    WHERE r.if_issue = 1
      AND r.release_time >= DATE '2026-01-01'
      AND date(r.release_time) < CURRENT_DATE
),
loan_agg AS (
    SELECT month, double_loan,
        SUM(contract_amount) AS sum_contract, COUNT(1) AS cnt_loan,
        SUM(loan_cycle * contract_amount) AS sum_weighted_term,
        SUM(coalesce(should_interest,0) + coalesce(haircut_amount,0)) AS sum_fee  -- 息费=利息+砍头息
    FROM base_loan GROUP BY 1,2
    UNION ALL
    SELECT month, NULL AS double_loan,
        SUM(contract_amount), COUNT(1),
        SUM(loan_cycle * contract_amount),
        SUM(coalesce(should_interest,0) + coalesce(haircut_amount,0))
    FROM base_loan GROUP BY 1
),
loan_metrics AS (
    SELECT '成交金额 (USD)***' AS metric,
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END AS loan_type,
        month, ROUND(sum_contract, 0) AS value FROM loan_agg
    UNION ALL
    SELECT '成交标数',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(cnt_loan, 0) FROM loan_agg
    UNION ALL
    SELECT '笔均 (USD)***',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_contract / cnt_loan, 1) FROM loan_agg
    UNION ALL
    SELECT '期限',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_weighted_term / sum_contract, 1) FROM loan_agg
    UNION ALL
    SELECT '息费',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_fee / sum_contract, 4) FROM loan_agg
),
cost_spend AS (
    SELECT DATE_TRUNC('month', ad_date) AS month, SUM(spend_usd) AS spend
    FROM dwd.dwd_ads_cost
    WHERE ad_date >= DATE '2026-01-01'
    AND ad_date < CURRENT_DATE - INTERVAL '0' DAY
    GROUP BY 1
),
daily_spend AS (
    SELECT
        month,
        spend,
        CASE
            WHEN DATE_FORMAT(DATE(month), '%Y-%m') = DATE_FORMAT(CURRENT_DATE - INTERVAL '1' DAY, '%Y-%m')
            THEN DAY_OF_MONTH(CURRENT_DATE - INTERVAL '1' DAY)
            ELSE DAY_OF_MONTH(DATE_TRUNC('month', DATE(month)) + INTERVAL '1' MONTH - INTERVAL '1' DAY)
        END AS days
    FROM cost_spend
),
first_loan_cnt AS (
    SELECT month, cnt_loan FROM loan_agg WHERE double_loan = 0
),
cps_rows AS (
    SELECT '静态CPS (USD)***' AS metric, '首贷' AS loan_type, c.month,
        ROUND(c.spend / fl.cnt_loan, 2) AS value
    FROM cost_spend c LEFT JOIN first_loan_cnt fl ON c.month = fl.month
),
daily_spend_rows AS (
    SELECT '日投放金额(USD)***' AS metric, '整体' AS loan_type, month,
        ROUND(spend / days, 2) AS value
    FROM daily_spend
),
overdue_base AS (
    -- 口径: wxs_application_funnel vintage 1T0/1T7 本金逾期率 + 1T7息费坏账
    -- 首贷/复贷
    SELECT DATE_TRUNC('month', date(r.release_time)) AS month,
        CASE WHEN r.is_reloan = 'new' THEN 0 ELSE 1 END AS double_loan,
        SUM(r.t0_overdue_capit_1) AS sum_t0_overdue,
        SUM(r.t0_should_capit_1)  AS sum_t0_should,
        SUM(r.t7_overdue_capit_1) AS sum_t7_overdue,
        SUM(r.t7_should_capit_1)  AS sum_t7_should,
        SUM(coalesce(r.t7_overdue_interest_4,0)) AS sum_t7_overdue_interest,   -- 1T7息费坏账分子
        SUM(coalesce(r.t7_should_amt_4,0))       AS sum_t7_should_amt            -- 1T7息费坏账分母(本息)
    FROM mx.wxs_application_funnel r
    WHERE r.if_issue = 1
      AND r.release_time >= DATE '2026-01-01'
      AND date(r.release_time) < CURRENT_DATE
    GROUP BY 1, 2
    UNION ALL
    -- 整体
    SELECT DATE_TRUNC('month', date(r.release_time)) AS month,
        NULL AS double_loan,
        SUM(r.t0_overdue_capit_1), SUM(r.t0_should_capit_1),
        SUM(r.t7_overdue_capit_1), SUM(r.t7_should_capit_1),
        SUM(coalesce(r.t7_overdue_interest_4,0)),
        SUM(coalesce(r.t7_should_amt_4,0))
    FROM mx.wxs_application_funnel r
    WHERE r.if_issue = 1
      AND r.release_time >= DATE '2026-01-01'
      AND date(r.release_time) < CURRENT_DATE
    GROUP BY 1
),
overdue_rows AS (
    SELECT '1T0' AS metric,
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END AS loan_type,
        month, ROUND(sum_t0_overdue / NULLIF(sum_t0_should, 0), 4) AS value
    FROM overdue_base
    UNION ALL
    SELECT '1T7',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_t7_overdue / NULLIF(sum_t7_should, 0), 4)
    FROM overdue_base
    UNION ALL
    -- 1T7息费坏账口径: t7_overdue_interest_4 / t7_should_amt_4 (用于TR计算)
    SELECT '1T7息费坏账' AS metric,
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_t7_overdue_interest / NULLIF(sum_t7_should_amt, 0), 4)
    FROM overdue_base
),
all_rows AS (
    SELECT * FROM loan_metrics UNION ALL
    SELECT * FROM cps_rows UNION ALL
    SELECT * FROM daily_spend_rows UNION ALL
    SELECT * FROM overdue_rows
)
SELECT metric, loan_type,
    MAX(CASE WHEN month = DATE '2026-01-01' THEN value END) AS "1月",
    MAX(CASE WHEN month = DATE '2026-02-01' THEN value END) AS "2月",
    MAX(CASE WHEN month = DATE '2026-03-01' THEN value END) AS "3月",
    MAX(CASE WHEN month = DATE '2026-04-01' THEN value END) AS "4月",
    MAX(CASE WHEN month = DATE '2026-05-01' THEN value END) AS "5月",
    MAX(CASE WHEN month = DATE '2026-06-01' THEN value END) AS "6月",
    MAX(CASE WHEN month = DATE '2026-07-01' THEN value END) AS "7月",
    MAX(CASE WHEN month = DATE '2026-08-01' THEN value END) AS "8月",
    MAX(CASE WHEN month = DATE '2026-09-01' THEN value END) AS "9月"
FROM all_rows
GROUP BY metric, loan_type
ORDER BY
    CASE metric
        WHEN '成交金额 (USD)***' THEN 1 WHEN '成交标数' THEN 2
        WHEN '笔均 (USD)***' THEN 3 WHEN '期限' THEN 4
        WHEN '息费' THEN 5 WHEN '日投放金额(USD)***' THEN 6
        WHEN '静态CPS (USD)***' THEN 7 WHEN '1T0' THEN 8
        WHEN '1T7' THEN 9 WHEN '1T7息费坏账' THEN 10
    END,
    CASE loan_type WHEN '首贷' THEN 1 WHEN '复贷' THEN 2 WHEN '整体' THEN 3 END
"""