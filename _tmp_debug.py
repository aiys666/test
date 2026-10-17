# -*- coding: utf-8 -*-
"""调试 SQL 提交 - 直接调用底层 API 查看 job 返回"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from indonesia_presto import PrestoQuery
import requests
import json
import base64
import time

pq = PrestoQuery()
pq.login_process()

# 测试简化的 SQL（只有 loan_metrics，不含中文）
sql_simple = """
SELECT
    DATE_TRUNC('month', release_time) AS month,
    CASE WHEN grant_strategy='NEW' THEN 0 WHEN grant_strategy='OLD' THEN 1 END AS double_loan,
    SUM(contract_amount_usd1) AS sum_contract,
    COUNT(1) AS cnt_loan
FROM ind.ba_asset_base_info
WHERE release_time >= DATE '2026-01-01'
  AND if_issue = 1
  AND release_time < CURRENT_DATE
GROUP BY 1, 2
"""
print("\n=== 测试1: 简化 SQL ===")
df1 = pq.submit_query(sql_simple, wait_sec=3)
print(f"返回: {type(df1)}, len={len(df1) if isinstance(df1, type(None)) is False else 'N/A'}")
print(df1)

# 测试2: 带中文 metric 的 SQL
sql_cn = """
SELECT '成交金额 (USD)***' AS metric, '首贷' AS loan_type, 100 AS value
UNION ALL
SELECT '成交标数', '首贷', 200
"""
print("\n=== 测试2: 中文 SQL ===")
df2 = pq.submit_query(sql_cn, wait_sec=3)
print(f"返回: {type(df2)}")
print(df2)

# 测试3: 完整的 CTE SQL 但只到 loan_metrics
sql_cte = """
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
)
SELECT * FROM loan_agg
"""
print("\n=== 测试3: CTE SQL ===")
df3 = pq.submit_query(sql_cte, wait_sec=3)
print(f"返回: {type(df3)}")
print(df3)
