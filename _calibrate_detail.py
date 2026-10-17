# -*- coding: utf-8 -*-
"""深挖: 周度/月度 出账笔数与逾期率差异最大的行。"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'e:\岳松个人文件\嘉银工作内容的整理\code')
import pandas as pd
import numpy as np
from _calibrate import load_mine, load_ref, RATE_COLS, CNT_COLS

mwk, mmo = load_mine()
rwk, rmo = load_ref()
mwk = mwk[mwk['issue_week'].str[:7].isin(['2026-08','2026-09'])].copy()

def show(label, m, r, key):
    m = m.rename(columns={key:'_k'}).copy()
    r = r.rename(columns={key:'_k'}).copy()
    m['_k'] = m['_k'].astype(str); r['_k'] = r['_k'].astype(str)
    m['产品'] = m['产品'].astype(str); r['产品'] = r['产品'].astype(str)
    j = pd.merge(m, r, on=['_k','产品'], suffixes=('_mine','_ref'))
    print(f'\n########## {label} ##########')
    # 出账笔数差异top
    for col in CNT_COLS:
        j[f'd_{col}'] = (j[col+'_mine'] - j[col+'_ref']).abs()
        j[f'pct_{col}'] = j[f'd_{col}'] / j[col+'_ref'].replace(0,np.nan)
    print('--- 出账笔数: 差异最大的5行 (is_t0_window_1) ---')
    top = j.nlargest(5, 'd_is_t0_window_1')[['_k','产品','is_t0_window_1_mine','is_t0_window_1_ref','d_is_t0_window_1']]
    print(top.to_string(index=False))
    print('--- 出账笔数: is_t3_window_1 差异最大5行 ---')
    top = j.nlargest(5, 'd_is_t3_window_1')[['_k','产品','is_t3_window_1_mine','is_t3_window_1_ref','d_is_t3_window_1']]
    print(top.to_string(index=False))
    print('--- 出账笔数: is_t7_window_4 差异最大5行 ---')
    top = j.nlargest(5, 'd_is_t7_window_4')[['_k','产品','is_t7_window_4_mine','is_t7_window_4_ref','d_is_t7_window_4']]
    print(top.to_string(index=False))
    # 逾期率差异top
    for col in RATE_COLS:
        j[f'dr_{col}'] = (j[col+'_mine'] - j[col+'_ref']).abs()
    print('--- 逾期率: 4t7本金 差异最大5行 ---')
    top = j.nlargest(5, 'dr_4t7本金逾期率')[['_k','产品','放款笔数_mine','4t7本金逾期率_mine','4t7本金逾期率_ref','is_t7_window_4_mine','is_t7_window_4_ref']]
    print(top.to_string(index=False))
    print('--- 逾期率: 1t0 差异最大5行 ---')
    top = j.nlargest(5, 'dr_1t0本金逾期率')[['_k','产品','放款笔数_mine','1t0本金逾期率_mine','1t0本金逾期率_ref','is_t0_window_1_mine','is_t0_window_1_ref']]
    print(top.to_string(index=False))

show('周度', mwk, rwk, 'issue_week')
