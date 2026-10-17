# -*- coding: utf-8 -*-
"""只看8月(参考月)的差异: 8月是比率的分子分母, 必须稳定。"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'e:\岳松个人文件\嘉银工作内容的整理\code')
import pandas as pd
import numpy as np
from _calibrate import load_mine, load_ref, RATE_COLS, CNT_COLS

mwk, mmo = load_mine()
rwk, rmo = load_ref()
mwk = mwk[mwk['issue_week'].str[:7] == '2026-08'].copy()
mmo = mmo[mmo['放款月份'].str[:7] == '2026-08'].copy()

def show(label, m, r, key):
    m = m.rename(columns={key:'_k'}).copy()
    r = r.rename(columns={key:'_k'}).copy()
    m['_k'] = m['_k'].astype(str); r['_k'] = r['_k'].astype(str)
    m['产品'] = m['产品'].astype(str); r['产品'] = r['产品'].astype(str)
    j = pd.merge(m, r, on=['_k','产品'], suffixes=('_mine','_ref'))
    print(f'\n########## {label} 8月 (共{len(j)}条) ##########')
    for col in ['放款笔数','放款金额']:
        d = (j[col+'_mine']-j[col+'_ref']).abs()
        print(f'  {col}: max={d.max():.2f}, mean={d.mean():.2f}')
    for col in CNT_COLS:
        d = (j[col+'_mine']-j[col+'_ref']).abs()
        print(f'  {col}: max={d.max():.0f}, mean={d.mean():.2f}')
    for col in RATE_COLS:
        d = (j[col+'_mine']-j[col+'_ref']).abs()
        print(f'  {col}: max={d.max():.6f}, mean={d.mean():.6f}')
    # 8月月度放款笔数差异top
    if key == '放款月份':
        j['_d'] = (j['放款笔数_mine']-j['放款笔数_ref']).abs()
        print('--- 放款笔数差异最大5行 ---')
        print(j.nlargest(5,'_d')[['_k','产品','放款笔数_mine','放款笔数_ref']].to_string(index=False))

show('周度', mwk, rwk, 'issue_week')
show('月度', mmo, rmo, '放款月份')

# 8月月度我方 vs 参考: 是否周度求和能对上参考月度
print('\n===== 我方周度按8月求和 vs 参考月度(8月) 放款笔数 =====')
mine_m = mwk.groupby('产品')['放款笔数'].sum().rename('周度求和')
ref_m = rmo[rmo['放款月份'].str[:7]=='2026-08'].set_index('产品')['放款笔数'].rename('参考月度')
cmp = pd.concat([mine_m, ref_m], axis=1)
cmp['差'] = cmp['周度求和'] - cmp['参考月度']
print(cmp.to_string())
