# -*- coding: utf-8 -*-
"""逐步测试 SQL 复杂度，找出问题所在"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from indonesia_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login_process()

# 测试4: 包含 loan_metrics CTE 的 SQL
sql4 = """
WITH
base_loan AS (
    SELECT
        DATE_TRUNC('month', release_time) AS month,
        CASE WHEN grant_strategy='NEW' THEN 0 WHEN grant_strategy='OLD' THEN 1 END AS double_loan,
        contract_amount_usd1 AS contract_amount,
        loan_cycle
    FROM ind.ba_asset_base_info
    WHERE release_time >= DATE '2026-08-01'
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
)
SELECT * FROM loan_metrics
"""
print("\n=== 测试4: loan_metrics CTE ===")
df4 = pq.submit_query(sql4, wait_sec=3)
print(f"返回: {type(df4)}")
if isinstance(df4, pd.DataFrame):
    print(df4)

# 测试5: 增加 overdue_base CTE
sql5 = """
WITH
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
)
SELECT * FROM overdue_base LIMIT 5
"""
print("\n=== 测试5: overdue_base CTE ===")
df5 = pq.submit_query(sql5, wait_sec=3)
print(f"返回: {type(df5)}")
if isinstance(df5, pd.DataFrame):
    print(df5)

# 测试6: 增加 cost_spend CTE
sql6 = """
WITH
cost_spend AS (
    SELECT DATE_TRUNC('month', ad_date) AS month, SUM(spend_usd_discount) AS spend
    FROM ind.tyn_ads_cost_discount
    WHERE ad_date >= DATE '2026-01-01'
    AND ad_date < CURRENT_DATE
    GROUP BY 1
)
SELECT * FROM cost_spend
"""
print("\n=== 测试6: cost_spend CTE ===")
df6 = pq.submit_query(sql6, wait_sec=3)
print(f"返回: {type(df6)}")
if isinstance(df6, pd.DataFrame):
    print(df6)
