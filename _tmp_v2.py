# -*- coding: utf-8 -*-
"""测试 overdue_base 不同写法"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from indonesia_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login_process()

# 测试1: 日报代码原版（只用 date_diff 范围，不用月份过滤）
sql1 = """
SELECT
    DATE_TRUNC('month', issue_date) AS month,
    CASE WHEN grant_strategy='NEW' THEN 0 WHEN grant_strategy='OLD' THEN 1 END AS double_loan,
    SUM(CASE WHEN grant_strategy='NEW' THEN overdue_amount_1_0 END)*100.0/
        NULLIF(SUM(CASE WHEN grant_strategy='NEW' THEN should_capital_1_0 END), 0) AS t0_rate
FROM ind.ba_asset_base_info
WHERE should_cnt_1_0=1
  AND (
    (product_tag_detail<>'R_30D' AND date_diff('day',date(issue_date),current_date) between 16 and 22)
    OR
    (product_tag_detail='R_30D' AND date_diff('day',date(issue_date),current_date) between 31 and 37)
  )
GROUP BY 1, 2
"""
print("\n=== 测试1: 日报代码原版 + 按月聚合 ===")
df1 = pq.submit_query(sql1, wait_sec=10)
print(f"返回: {type(df1)}")
if isinstance(df1, pd.DataFrame):
    print(df1)

# 测试2: 直接查 should_cnt_1_0 字段类型
sql2 = """
SELECT DISTINCT should_cnt_1_0, count(1) as cnt
FROM ind.ba_asset_base_info
WHERE DATE(issue_date) >= DATE '2026-08-01'
GROUP BY 1
LIMIT 10
"""
print("\n=== 测试2: should_cnt_1_0 字段类型 ===")
df2 = pq.submit_query(sql2, wait_sec=10)
print(f"返回: {type(df2)}")
if isinstance(df2, pd.DataFrame):
    print(df2)
