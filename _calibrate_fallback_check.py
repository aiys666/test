# -*- coding: utf-8 -*-
"""找出9月目标产品中8月无参考的, 并为其找fallback(期限相同+总收息最接近)。"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'e:\岳松个人文件\嘉银工作内容的整理\code')
import pandas as pd
import numpy as np
from _calibrate import load_mine, load_ref, RATE_COLS

mwk, mmo = load_mine()
rwk, rmo = load_ref()
mwk = mwk[mwk['issue_week'].str[:7].isin(['2026-08','2026-09'])].copy()
mmo = mmo[mmo['放款月份'].str[:7].isin(['2026-08','2026-09'])].copy()

MIN_AUG_CNT = 3
aug_m = mmo[(mmo['放款月份'].str[:7]=='2026-08') & (mmo['放款笔数']>MIN_AUG_CNT)].copy()
sep_weeks = mwk[mwk['issue_week'].str[:7]=='2026-09'].copy()

aug_products = set(aug_m['产品'])
sep_products = set(sep_weeks['产品'])
print(f'8月参考产品(>{MIN_AUG_CNT}笔): {len(aug_products)}')
print(f'9月目标产品: {len(sep_products)}')
missing = sep_products - aug_products
print(f'\n9月有但8月无参考的产品: {len(missing)}')
for p in sorted(missing):
    sub = sep_weeks[sep_weeks['产品']==p]
    term = sub['平均期限'].iloc[0]
    rev = sub['总收息_含税'].iloc[0]
    cnt = sub['放款笔数'].sum()
    print(f'  {p}: 期限={term}天, 总收息={rev:.4f}, 9月总笔数={cnt}')

# 为每个missing找fallback: 期限相同且总收息最接近
print('\n===== fallback候选 =====')
for p in sorted(missing):
    sub = sep_weeks[sep_weeks['产品']==p]
    term = sub['平均期限'].iloc[0]
    rev = sub['总收息_含税'].iloc[0]
    cand = aug_m[aug_m['平均期限']==term].copy()
    if len(cand)==0:
        print(f'  {p}({term}天): 无期限相同的8月产品!')
        # 放宽: 全部8月产品按总收息距离
        cand = aug_m.copy()
    cand = cand.copy()
    cand['rev_dist'] = (cand['总收息_含税']-rev).abs()
    cand = cand.sort_values('rev_dist')
    best = cand.iloc[0]
    print(f'  {p}: 期限={term}天, 总收息={rev:.4f} -> 参考[{best["产品"]}] 期限={best["平均期限"]}天, 总收息={best["总收息_含税"]:.4f}, 距离={best["rev_dist"]:.4f}, 8月笔数={best["放款笔数"]}')
    # 显示前3候选
    top3 = cand.head(3)[['产品','平均期限','总收息_含税','放款笔数','rev_dist']]
    print(top3.to_string(index=False))
