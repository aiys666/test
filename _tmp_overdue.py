# -*- coding: utf-8 -*-
"""测试 overdue_base CTE 各字段"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from indonesia_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login_process()

# 测试1: 简化 overdue_base, 只查 1T0
sql1 = """
SELECT
    DATE_TRUNC('month', issue_date) AS month,
    CASE WHEN grant_strategy='NEW' THEN 0 WHEN grant_strategy='OLD' THEN 1 END AS double_loan,
    SUM(overdue_amount_1_0) AS sum_overdue_t0,
    SUM(should_capital_1_0) AS sum_should_t0
FROM ind.ba_asset_base_info
WHERE should_cnt_1_0 = 1
  AND DATE(issue_date) >= DATE '2026-08-01'
  AND DATE(issue_date) < CURRENT_DATE
GROUP BY 1, 2
"""
print("\n=== 测试1: 简化 overdue_base (只 8月) ===")
df1 = pq.submit_query(sql1, wait_sec=5)
print(f"返回: {type(df1)}")
if isinstance(df1, pd.DataFrame):
    print(df1)

# 测试2: 加 date_diff 过滤条件
sql2 = """
SELECT
    DATE_TRUNC('month', issue_date) AS month,
    CASE WHEN grant_strategy='NEW' THEN 0 WHEN grant_strategy='OLD' THEN 1 END AS double_loan,
    SUM(overdue_amount_1_0) AS sum_overdue_t0,
    SUM(should_capital_1_0) AS sum_should_t0
FROM ind.ba_asset_base_info
WHERE should_cnt_1_0 = 1
  AND DATE(issue_date) >= DATE '2026-01-01'
  AND DATE(issue_date) < CURRENT_DATE
  AND (
    (product_tag_detail<>'R_30D' AND date_diff('day', date(issue_date), current_date) >= 16)
    OR
    (product_tag_detail='R_30D' AND date_diff('day', date(issue_date), current_date) >= 31)
  )
GROUP BY 1, 2
"""
print("\n=== 测试2: 加 date_diff 过滤 ===")
df2 = pq.submit_query(sql2, wait_sec=5)
print(f"返回: {type(df2)}")
if isinstance(df2, pd.DataFrame):
    print(df2)

# 测试3: 用日报代码原版写法 + 按月聚合
sql3 = """
SELECT
    DATE_TRUNC('month', issue_date) AS month,
    CASE WHEN grant_strategy='NEW' THEN 'NEW' WHEN grant_strategy='OLD' THEN 'OLD' END AS double_loan_str,
    SUM(overdue_amount_1_0)*100.0/NULLIF(SUM(should_capital_1_0), 0) AS t0_rate
FROM ind.ba_asset_base_info
WHERE should_cnt_1_0=1
  AND DATE(issue_date) >= DATE '2026-08-01'
  AND DATE(issue_date) < CURRENT_DATE
  AND (
    (product_tag_detail<>'R_30D' and date_diff('day',date(issue_date),current_date) between 16 and 22)
    or 
    (product_tag_detail='R_30D' and date_diff('day',date(issue_date),current_date) between 31 and 37)
  )
GROUP BY 1, 2
"""
print("\n=== 测试3: 日报代码写法 ===")
df3 = pq.submit_query(sql3, wait_sec=5)
print(f"返回: {type(df3)}")
if isinstance(df3, pd.DataFrame):
    print(df3)
