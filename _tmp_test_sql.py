# -*- coding: utf-8 -*-
"""调试 SQL 查询，验证字段是否正确"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from indonesia_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login_process()

# 测试1: 简单查询 ba_asset_base_info 表，验证 loan_cycle 字段是否存在
sql1 = """
SELECT
    DATE_TRUNC('month', release_time) AS month,
    CASE WHEN grant_strategy='NEW' THEN 0 WHEN grant_strategy='OLD' THEN 1 END AS double_loan,
    contract_amount_usd1 AS contract_amount,
    loan_cycle
FROM ind.ba_asset_base_info
WHERE release_time >= DATE '2026-08-01'
  AND if_issue = 1
  AND release_time < CURRENT_DATE
LIMIT 5
"""
print("\n=== 测试1: loan_cycle 字段 ===")
df1 = pq.submit_query(sql1, wait_sec=5)
print(f"返回类型: {type(df1)}")
print(f"返回: {df1}")

# 测试2: 验证字段
sql2 = """
SELECT column_name FROM information_schema.columns 
WHERE table_schema = 'ind' AND table_name = 'ba_asset_base_info'
ORDER BY ordinal_position
"""
print("\n=== 测试2: ba_asset_base_info 字段 ===")
df2 = pq.submit_query(sql2, wait_sec=5)
if isinstance(df2, pd.DataFrame):
    print(df2.to_string())
else:
    print(f"返回: {df2}")
