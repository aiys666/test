# -*- coding: utf-8 -*-
"""测试完整的宽表 SQL"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from indonesia_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login_process()

# 测试完整的宽表 SQL
SQL_WIDE_TABLE = """
WITH
base_loan AS (
    SELECT
        DATE_TRUNC('month', release_time) AS month,
        CASE WHEN grant_strategy='NEW' THEN 0 WHEN grant_strategy='OLD' THEN 1 END AS double_loan,
        contract_amount_usd1 AS contract_amount,
        loan_cycle
    FROM ind.ba_asset_base_info
    WHERE release_time >= DATE '2026-01-01'
      AND if_issue = 1
      AND release_time < CURRENT_DATE
),
loan_agg AS (
    SELECT month, double_loan,
        SUM(contract_amount) AS sum_contract, COUNT(1) AS cnt_loan,
        SUM(loan_cycle * contract_amount) AS sum_weighted_term
    FROM base_loan GROUP BY 1,2
    UNION ALL
    SELECT month, NULL AS double_loan,
        SUM(contract_amount), COUNT(1),
        SUM(loan_cycle * contract_amount)
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
        month, ROUND(sum_contract / NULLIF(cnt_loan, 0), 1) FROM loan_agg
    UNION ALL
    SELECT '期限',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_weighted_term / NULLIF(sum_contract, 0), 1) FROM loan_agg
),
cost_spend AS (
    SELECT DATE_TRUNC('month', ad_date) AS month, SUM(spend_usd_discount) AS spend
    FROM ind.tyn_ads_cost_discount
    WHERE ad_date >= DATE '2026-01-01'
    AND ad_date < CURRENT_DATE
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
        ROUND(c.spend / NULLIF(fl.cnt_loan, 0), 2) AS value
    FROM cost_spend c LEFT JOIN first_loan_cnt fl ON c.month = fl.month
),
daily_spend_rows AS (
    SELECT '日投放金额(USD)***' AS metric, '整体' AS loan_type, month,
        ROUND(spend / NULLIF(days, 0), 2) AS value
    FROM daily_spend
),
overdue_base AS (
    SELECT
        DATE_TRUNC('month', issue_date) AS month,
        CASE WHEN grant_strategy='NEW' THEN 0 WHEN grant_strategy='OLD' THEN 1 END AS double_loan,
        SUM(overdue_amount_1_0) AS sum_overdue_t0,
        SUM(overdue_amount_1_7) AS sum_overdue_t7,
        SUM(should_capital_1_0) AS sum_should_t0,
        SUM(should_capital_1_7) AS sum_should_t7
    FROM ind.ba_asset_base_info
    WHERE should_cnt_1_0 = 1
      AND DATE(issue_date) >= DATE '2026-01-01'
      AND DATE(issue_date) < CURRENT_DATE
    GROUP BY 1, 2
    UNION ALL
    SELECT
        DATE_TRUNC('month', issue_date) AS month,
        NULL AS double_loan,
        SUM(overdue_amount_1_0),
        SUM(overdue_amount_1_7),
        SUM(should_capital_1_0),
        SUM(should_capital_1_7)
    FROM ind.ba_asset_base_info
    WHERE should_cnt_1_0 = 1
      AND DATE(issue_date) >= DATE '2026-01-01'
      AND DATE(issue_date) < CURRENT_DATE
    GROUP BY 1
),
overdue_rows AS (
    SELECT '1T0' AS metric,
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END AS loan_type,
        month, ROUND(sum_overdue_t0 / NULLIF(sum_should_t0, 0), 4) AS value
    FROM overdue_base
    UNION ALL
    SELECT '1T7',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_overdue_t7 / NULLIF(sum_should_t7, 0), 4)
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
    MAX(CASE WHEN month = DATE '2026-08-01' THEN value END) AS "8月"
FROM all_rows
GROUP BY metric, loan_type
ORDER BY
    CASE metric
        WHEN '成交金额 (USD)***' THEN 1 WHEN '成交标数' THEN 2
        WHEN '笔均 (USD)***' THEN 3 WHEN '期限' THEN 4
        WHEN '日投放金额(USD)***' THEN 5
        WHEN '静态CPS (USD)***' THEN 6 WHEN '1T0' THEN 7
        WHEN '1T7' THEN 8
    END,
    CASE loan_type WHEN '首贷' THEN 1 WHEN '复贷' THEN 2 WHEN '整体' THEN 3 END
"""

print("\n=== 测试宽表 SQL ===")
df = pq.submit_query(SQL_WIDE_TABLE, wait_sec=5)
print(f"返回类型: {type(df)}")
if isinstance(df, pd.DataFrame):
    print(f"返回 {len(df)} 行 × {len(df.columns)} 列")
    print(df.to_string())
else:
    print(f"返回: {df}")
