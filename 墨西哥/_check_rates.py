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

# 1. 周维度总览（结果表全量）
sql1 = """
SELECT week,
       SUM(billed_cnt) AS billed_cnt,
       SUM(overdue_cnt) AS overdue_cnt,
       ROUND(SUM(overdue_cnt)*1.0/SUM(billed_cnt), 4) AS overdue_rate,
       SUM(billed_amt) AS billed_amt,
       SUM(overdue_amt) AS overdue_amt,
       ROUND(SUM(overdue_amt)*1.0/SUM(billed_amt), 4) AS overdue_rate_amt
FROM mx.tmp_effect_decomp_all_dims
GROUP BY 1
ORDER BY 1
"""
print("=== 周维度总量（结果表） ===")
df1 = pq.query(sql1)
print(df1 if isinstance(df1, pd.DataFrame) else df1)
print()

# 2. 8/3 vs 8/10 逾期率变化确认
sql2 = """
SELECT dim_name,
       SUM(CASE WHEN week = date'2026-08-03' THEN billed_cnt ELSE 0 END) AS b_billed,
       SUM(CASE WHEN week = date'2026-08-03' THEN overdue_cnt ELSE 0 END) AS b_overdue,
       SUM(CASE WHEN week = date'2026-08-10' THEN billed_cnt ELSE 0 END) AS c_billed,
       SUM(CASE WHEN week = date'2026-08-10' THEN overdue_cnt ELSE 0 END) AS c_overdue
FROM mx.tmp_effect_decomp_all_dims
WHERE week IN (date'2026-08-03', date'2026-08-10')
GROUP BY 1
ORDER BY 1
"""
print("=== 各维度 8/3 vs 8/10 笔数(笔数口径) ===")
df2 = pq.query(sql2)
print(df2 if isinstance(df2, pd.DataFrame) else df2)
