# -*- coding: utf-8 -*-
"""测试 issue_date 字段"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from indonesia_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login_process()

# 测试1: 直接查 issue_date 字段是否存在
sql1 = """
SELECT issue_date, should_cnt_1_0, overdue_amount_1_0, should_capital_1_0
FROM ind.ba_asset_base_info
WHERE should_cnt_1_0 = 1
  AND DATE(issue_date) >= DATE '2026-08-01'
LIMIT 5
"""
print("\n=== 测试1: issue_date 字段 ===")
df1 = pq.submit_query(sql1, wait_sec=5)
print(f"返回: {type(df1)}")
print(df1)

# 测试2: 直接用 release_time 代替 issue_date
sql2 = """
SELECT
    DATE_TRUNC('month', release_time) AS month,
    CASE WHEN grant_strategy='NEW' THEN 0 WHEN grant_strategy='OLD' THEN 1 END AS double_loan,
    SUM(overdue_amount_1_0) AS sum_overdue_t0,
    SUM(should_capital_1_0) AS sum_should_t0
FROM ind.ba_asset_base_info
WHERE should_cnt_1_0 = 1
  AND DATE(release_time) >= DATE '2026-08-01'
  AND DATE(release_time) < CURRENT_DATE
GROUP BY 1, 2
"""
print("\n=== 测试2: 用 release_time 代替 issue_date ===")
df2 = pq.submit_query(sql2, wait_sec=5)
print(f"返回: {type(df2)}")
print(df2)

# 测试3: 直接查 ba_asset_base_info 表的所有字段
sql3 = """
SELECT * FROM ind.ba_asset_base_info LIMIT 1
"""
print("\n=== 测试3: ba_asset_base_info 表所有字段 ===")
df3 = pq.submit_query(sql3, wait_sec=5)
print(f"返回: {type(df3)}")
if isinstance(df3, pd.DataFrame):
    print("字段列表:")
    for c in df3.columns:
        print(f"  - {c}: {df3[c].iloc[0]}")
