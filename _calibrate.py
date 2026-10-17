# -*- coding: utf-8 -*-
"""校准脚本: 自动取数的复贷(old)数据 vs 用户之前给的参考Excel(纯复贷)。"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'e:\岳松个人文件\嘉银工作内容的整理\code')
import pandas as pd
import numpy as np

from coverage_fetch_estimate import add_rates, to_sheet_df, SUM_COLS

REF_WEEKLY = r'd:\Documents\Downloads\评级产品表现-放款月2 (1).xlsx'
REF_MONTHLY = r'd:\Documents\Downloads\评级产品表现-放款月21.xlsx'
CACHE = r'e:\岳松个人文件\嘉银工作内容的整理\code\_coverage_raw_cache.csv'

# 比对的指标(参考Excel列名 == 我方sheet列名)
RATE_COLS = ['总收息_含税', '1t0本金逾期率', '1t3本金逾期率', '2t0本金逾期率',
             '3t0本金逾期率', '4t0本金逾期率', '4t7本金逾期率', '4t7息费逾期率_本金分母']
CNT_COLS = ['is_t0_window_1', 'is_t3_window_1', 'is_t0_window_2',
            'is_t0_window_3', 'is_t0_window_4', 'is_t7_window_4']


def load_mine():
    raw = pd.read_csv(CACHE, dtype={'issue_week': str, 'issue_month': str})
    for c in SUM_COLS:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)
    raw = raw[raw['is_reloan'] == 'old'].copy()
    wk = to_sheet_df(raw, 'issue_week', 'issue_week').drop(columns='is_reloan')
    mo = to_sheet_df(raw, 'issue_month', '放款月份').drop(columns='is_reloan')
    return wk, mo


def load_ref():
    wk = pd.read_excel(REF_WEEKLY)
    mo = pd.read_excel(REF_MONTHLY)
    # 去掉合计行
    wk = wk[wk['issue_week'].astype(str) != '合计'].copy()
    mo = mo[mo['放款月份'].astype(str) != '合计'].copy()
    # 参考Excel是合并单元格: 周/月只在每组首行出现, 需ffill
    wk['issue_week'] = wk['issue_week'].ffill()
    mo['放款月份'] = mo['放款月份'].ffill()
    wk['issue_week'] = pd.to_datetime(wk['issue_week'], errors='coerce').dt.strftime('%Y-%m-%d')
    mo['放款月份'] = pd.to_datetime(mo['放款月份'], errors='coerce').dt.strftime('%Y-%m-%d')
    return wk, mo


def cmp(label, mine, ref, key):
    m = mine.rename(columns={key: '_k'})
    r = ref.rename(columns={key: '_k'})
    m = m[['_k', '产品', '放款笔数', '放款金额', '平均期限'] + RATE_COLS + CNT_COLS].copy()
    r = r[['_k', '产品', '放款笔数', '放款金额', '平均期限'] + RATE_COLS + CNT_COLS].copy()
    m['_k'] = m['_k'].astype(str).str.strip()
    r['_k'] = r['_k'].astype(str).str.strip()
    m['产品'] = m['产品'].astype(str).str.strip()
    r['产品'] = r['产品'].astype(str).str.strip()

    mg = m.groupby('_k')['产品'].nunique().rename('mine_产品数')
    rg = r.groupby('_k')['产品'].nunique().rename('ref_产品数')
    keycmp = pd.concat([mg, rg], axis=1).fillna(0).astype(int)
    print(f'\n===== {label} 各时间片产品数对比 =====')
    print(keycmp.to_string())

    joined = pd.merge(m, r, on=['_k', '产品'], how='outer', indicator=True, suffixes=('_mine', '_ref'))
    only_mine = joined[joined['_merge'] == 'left_only']
    only_ref = joined[joined['_merge'] == 'right_only']
    print(f'\n--- {label} 仅我方有({len(only_mine)}) ---')
    if len(only_mine):
        print(only_mine[['_k', '产品', '放款笔数_mine']].head(50).to_string())
    print(f'--- {label} 仅参考有({len(only_ref)}) ---')
    if len(only_ref):
        print(only_ref[['_k', '产品', '放款笔数_ref']].head(50).to_string())

    both = joined[joined['_merge'] == 'both'].copy()
    print(f'\n--- {label} 两边都有: {len(both)} 条, 指标差异 ---')
    for col in ['放款笔数', '放款金额']:
        a = both[col + '_mine'].astype(float)
        b = both[col + '_ref'].astype(float)
        diff = (a - b).abs()
        rel = (diff / b.replace(0, np.nan)).abs()
        print(f'  {col}: 绝对差 max={diff.max():.2f}, mean={diff.mean():.2f}; '
              f'相对差>1%的条数={(rel>0.01).sum()}/{len(both)}')
        bad = both.loc[(rel > 0.01) & b.notna(), ['_k', '产品', col + '_mine', col + '_ref']]
        if len(bad):
            print(bad.head(20).to_string())
    for col in RATE_COLS + CNT_COLS:
        a = pd.to_numeric(both[col + '_mine'], errors='coerce')
        b = pd.to_numeric(both[col + '_ref'], errors='coerce')
        diff = (a - b).abs()
        print(f'  {col}: 绝对差 max={diff.max():.6f}, mean={diff.mean():.6f}')
    return joined


def main():
    mwk, mmo = load_mine()
    rwk, rmo = load_ref()
    # 只比对重叠期间: 参考Excel仅覆盖8月/9月
    mwk = mwk[mwk['issue_week'].astype(str).str[:7].isin(['2026-08', '2026-09'])].copy()
    mmo = mmo[mmo['放款月份'].astype(str).str[:7].isin(['2026-08', '2026-09'])].copy()
    cmp('周度', mwk, rwk, 'issue_week')
    cmp('月度', mmo, rmo, '放款月份')


if __name__ == '__main__':
    main()
