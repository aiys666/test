# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)

pq = PrestoQuery()
pq.login()
print("登录成功\n")

# 1. 各 mid 数据量分布（找出 1040160066607324 是什么）
sql1 = """
SELECT mid, COUNT(*) AS total_rows,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt
FROM mx.yj_test_table_250225
WHERE app_time >= date'2026-08-03'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 30
"""
print("=== 各 mid 数据量(8/3以来) ===")
df1 = pq.query(sql1)
print(df1 if isinstance(df1, pd.DataFrame) else df1)
print()

# 2. 全表(不限制 mid/窗口)逾期字段分布
sql2 = """
SELECT is_t0_overdue_1, COUNT(*) AS cnt
FROM mx.yj_test_table_250225
WHERE app_time >= date'2026-06-01'
GROUP BY 1
"""
print("=== 全表 is_t0_overdue_1 分布(6月以来) ===")
df2 = pq.query(sql2)
print(df2 if isinstance(df2, pd.DataFrame) else df2)
print()

# 3. 全表出账/逾期周趋势（不限制 mid）
sql3 = """
SELECT app_week,
       COUNT(*) AS rows_cnt,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt
FROM mx.yj_test_table_250225
WHERE app_week >= date'2026-07-01'
GROUP BY 1
ORDER BY 1
"""
print("=== 全表周趋势(7月以来,不限mid) ===")
df3 = pq.query(sql3)
print(df3 if isinstance(df3, pd.DataFrame) else df3)
print()
