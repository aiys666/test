import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)

pq = PrestoQuery()
pq.login()

sql = """
SELECT dim_name, dim_group, week, billed_cnt, overdue_cnt, billed_amt, overdue_amt
FROM mx.tmp_effect_decomp_all_dims
WHERE week IN (date'2026-08-03', date'2026-08-10')
"""
raw = pq.query(sql)
raw['week'] = pd.to_datetime(raw['week']).dt.date
print('raw 行数:', raw.shape[0])
print('raw 维度数:', raw['dim_name'].nunique())

B08 = pd.Timestamp('2026-08-03').date()
B10 = pd.Timestamp('2026-08-10').date()

w = raw.pivot_table(
    index=['dim_name', 'dim_group'],
    columns='week',
    values=['billed_cnt', 'overdue_cnt', 'billed_amt', 'overdue_amt'],
    aggfunc='sum'
).reset_index()
w.columns = ['_'.join(map(str, c)).strip('_') for c in w.columns]
w = w.rename(columns={
    f'billed_cnt_{B08}': 'b_n', f'billed_cnt_{B10}': 'c_n',
    f'overdue_cnt_{B08}': 'b_o', f'overdue_cnt_{B10}': 'c_o',
    f'billed_amt_{B08}': 'b_amt', f'billed_amt_{B10}': 'c_amt',
    f'overdue_amt_{B08}': 'b_oamt', f'overdue_amt_{B10}': 'c_oamt',
})
print('pivot 后维度数:', w['dim_name'].nunique())
print('pivot 后行数:', len(w))

# 检查是否转产线/是否复贷 是否在 pivot 里
for d in ['是否转产线','是否复贷','产品等级']:
    print(d, '在 pivot:', d in set(w['dim_name']))

# 找出在 raw 但不在 pivot 的维度
raw_dims = set(raw['dim_name'].unique())
pivot_dims = set(w['dim_name'].unique())
print('raw有但pivot无的维度数:', len(raw_dims - pivot_dims))
print(sorted(raw_dims - pivot_dims)[:50])
