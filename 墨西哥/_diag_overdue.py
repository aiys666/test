# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 250)

pq = PrestoQuery()
pq.login()
print("登录成功\n")

# 1. 周维度总览：各周出账/逾期
sql1 = """
SELECT app_week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM mx.yj_test_table_250225
WHERE app_time >= date'2026-08-03'
  AND mid = 1040160066607324
  AND is_t0_window_1 IS NOT NULL
GROUP BY 1
ORDER BY 1
"""
print("=== 周维度总量 ===")
df1 = pq.query(sql1)
print(df1 if isinstance(df1, pd.DataFrame) else df1)
print()

# 2. 逾期字段整体分布（是否存在逾期记录）
sql2 = """
SELECT is_t0_overdue_1, COUNT(*) AS cnt
FROM mx.yj_test_table_250225
WHERE app_time >= date'2026-08-03'
  AND mid = 1040160066607324
  AND is_t0_window_1 IS NOT NULL
GROUP BY 1
"""
print("=== is_t0_overdue_1 取值分布 ===")
df2 = pq.query(sql2)
print(df2 if isinstance(df2, pd.DataFrame) else df2)
print()

# 3. 时间字段范围（判断观察窗）
sql3 = """
SELECT MIN(app_time) AS min_app_time, MAX(app_time) AS max_app_time,
       MIN(app_week) AS min_week, MAX(app_week) AS max_week
FROM mx.yj_test_table_250225
WHERE mid = 1040160066607324
"""
print("=== 时间范围 ===")
df3 = pq.query(sql3)
print(df3 if isinstance(df3, pd.DataFrame) else df3)
