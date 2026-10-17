import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()

# 两期子集实际行数
r = pq.query("""
SELECT COUNT(*) AS c, COUNT(DISTINCT dim_name) AS d
FROM mx.tmp_effect_decomp_all_dims
WHERE week IN (date'2026-08-03', date'2026-08-10')
""")
print('两期子集:', r.to_string(index=False) if isinstance(r, pd.DataFrame) else r)

# 直接拉原始行，看返回多少
raw = pq.query("""
SELECT dim_name, dim_group, week, billed_cnt, overdue_cnt, billed_amt, overdue_amt
FROM mx.tmp_effect_decomp_all_dims
WHERE week IN (date'2026-08-03', date'2026-08-10')
""")
if isinstance(raw, pd.DataFrame):
    print('fetch 返回行数:', raw.shape[0], '维度数:', raw['dim_name'].nunique())
else:
    print('fetch 返回:', raw)
