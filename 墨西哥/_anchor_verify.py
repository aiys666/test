# -*- coding: utf-8 -*-
"""重新锚定源表全市场真实总量，并交叉校验结果表某维度合计。"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功\n")

sql = """
SELECT app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt
FROM mx.yj_test_table_250225
WHERE app_time >= date'2026-08-03'
  AND app_week IN (date'2026-08-03', date'2026-08-10')
GROUP BY 1 ORDER BY 1
"""
tot = pq.query(sql)
print("源表全市场总量:")
print(tot.to_string(index=False))
tot['week'] = pd.to_datetime(tot['week']).dt.date
tb = tot.set_index('week').astype(float)
d03 = pd.Timestamp('2026-08-03').date(); d10 = pd.Timestamp('2026-08-10').date()
br = tb.loc[d03, 'overdue_cnt'] / tb.loc[d03, 'billed_cnt']
cr = tb.loc[d10, 'overdue_cnt'] / tb.loc[d10, 'billed_cnt']
print(f"\n笔数口径: {br*100:.4f}% -> {cr*100:.4f}%, 变化 {(cr-br)*100:+.4f}pp")
bra = tb.loc[d03, 'overdue_amt'] / tb.loc[d03, 'billed_amt']
cra = tb.loc[d10, 'overdue_amt'] / tb.loc[d10, 'billed_amt']
print(f"金额口径: {bra*100:.4f}% -> {cra*100:.4f}%, 变化 {(cra-bra)*100:+.4f}pp")

# 交叉校验：结果表中"是否转产线"维度两期合计 = 源表全市场
chk = """
SELECT week, SUM(billed_cnt) AS billed_cnt, SUM(overdue_cnt) AS overdue_cnt,
       SUM(billed_amt) AS billed_amt, SUM(overdue_amt) AS overdue_amt
FROM mx.tmp_effect_decomp_all_dims
WHERE dim_name = '是否转产线'
  AND week IN (date'2026-08-03', date'2026-08-10')
GROUP BY 1 ORDER BY 1
"""
c = pq.query(chk)
print("\n结果表[是否转产线]维度合计（应≈源表全市场）:")
print(c.to_string(index=False))
