# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)

# ---- 1. xlsx 完整清单 ----
path = r'D:\Documents\Downloads\效应分解_2026-08-03_vs_2026-08-10 (1).xlsx'
xl = pd.ExcelFile(path)
print("=== xlsx 完整 sheet 列表 (%d 个) ===" % len(xl.sheet_names))
for i, s in enumerate(xl.sheet_names):
    df = pd.read_excel(path, sheet_name=s)
    print(f"{i+1:2d}. {s}  (rows={df.shape[0]})")

print("\n")

# ---- 2. 结果表真实数据 ----
pq = PrestoQuery()
pq.login()
print("登录成功\n")

sql1 = """
SELECT COUNT(*) AS row_cnt,
       COUNT(DISTINCT dim_name) AS dim_cnt,
       COUNT(DISTINCT week) AS week_cnt
FROM mx.tmp_effect_decomp_all_dims
"""
print("=== 结果表行数/维度数/周数 ===")
print(pq.query(sql1))
print()

sql2 = """
SELECT week,
       SUM(billed_cnt) AS billed_cnt,
       SUM(overdue_cnt) AS overdue_cnt,
       ROUND(SUM(overdue_cnt)*1.0/SUM(billed_cnt), 4) AS rate,
       SUM(billed_amt) AS billed_amt,
       SUM(overdue_amt) AS overdue_amt,
       ROUND(SUM(overdue_amt)*1.0/SUM(billed_amt), 4) AS rate_amt
FROM mx.tmp_effect_decomp_all_dims
GROUP BY 1
ORDER BY 1
"""
print("=== 结果表各周总量 ===")
df = pq.query(sql2)
print(df if isinstance(df, pd.DataFrame) else df)
print()

# 8/3 vs 8/10 逾期率变化
sql3 = """
SELECT
  SUM(CASE WHEN week = date'2026-08-03' THEN billed_cnt ELSE 0 END) AS b_cnt,
  SUM(CASE WHEN week = date'2026-08-03' THEN overdue_cnt ELSE 0 END) AS b_overdue,
  SUM(CASE WHEN week = date'2026-08-10' THEN billed_cnt ELSE 0 END) AS c_cnt,
  SUM(CASE WHEN week = date'2026-08-10' THEN overdue_cnt ELSE 0 END) AS c_overdue,
  SUM(CASE WHEN week = date'2026-08-03' THEN billed_amt ELSE 0 END) AS b_amt,
  SUM(CASE WHEN week = date'2026-08-03' THEN overdue_amt ELSE 0 END) AS b_overdue_amt,
  SUM(CASE WHEN week = date'2026-08-10' THEN billed_amt ELSE 0 END) AS c_amt,
  SUM(CASE WHEN week = date'2026-08-10' THEN overdue_amt ELSE 0 END) AS c_overdue_amt
FROM mx.tmp_effect_decomp_all_dims
WHERE week IN (date'2026-08-03', date'2026-08-10')
"""
print("=== 8/3 vs 8/10 总量(笔数/金额) ===")
df3 = pq.query(sql3)
print(df3 if isinstance(df3, pd.DataFrame) else df3)
