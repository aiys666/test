import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()

# 结果表全部维度
all_dims = pq.query("SELECT DISTINCT dim_name FROM mx.tmp_effect_decomp_all_dims ORDER BY dim_name")
all_set = set(all_dims['dim_name'].tolist())

# 两周有数据的维度
two_week = pq.query("""
SELECT DISTINCT dim_name FROM mx.tmp_effect_decomp_all_dims
WHERE week IN (date'2026-08-03', date'2026-08-10')
ORDER BY dim_name
""")
two_set = set(two_week['dim_name'].tolist())

print('结果表维度数:', len(all_set))
print('8/3或8/10有数据的维度数:', len(two_set))
print('差异(结果表有但两周无数据):', sorted(all_set - two_set))
print()
print('关键维度在两期是否有数据:')
for d in ['是否复贷','是否转产线','产品等级','上期产品等级','产品等级变化','贷款类型','V3版本标识','是否继承标签']:
    r = pq.query(f"""
    SELECT week, SUM(billed_cnt) AS n FROM mx.tmp_effect_decomp_all_dims
    WHERE dim_name = '{d}' AND week IN (date'2026-08-03', date'2026-08-10')
    GROUP BY week ORDER BY week
    """)
    print(f'  {d}:')
    if isinstance(r, pd.DataFrame) and len(r):
        print(r.to_string(index=False))
    else:
        print('    (无数据)')
