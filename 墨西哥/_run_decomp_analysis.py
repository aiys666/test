# -*- coding: utf-8 -*-
"""8/3→8/10 逾期率 Kitagawa 分解（正确口径：逐维度分解）。

每个维度的分组是对同一批客群的切分，因此：
  - 维度内 share = 组出账 / 该维度全部出账
  - 维度内 total_change = sum(individual+structural+interaction) ≈ 全市场真实总变化
这样 individual/structural/interaction 的量级才是真实的（pp），可用于跨维度比较。
"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)
pd.set_option('display.max_rows', 200)

pq = PrestoQuery()
pq.login()
print("登录成功\n")

# ── 1. 拉取两周全维度数据 ──────────────────────────────
sql = """
SELECT dim_name, dim_group, week, billed_cnt, overdue_cnt, billed_amt, overdue_amt
FROM mx.tmp_effect_decomp_all_dims
WHERE week IN (date'2026-08-03', date'2026-08-10')
"""
raw = pq.query(sql)
assert isinstance(raw, pd.DataFrame), f"查询失败: {raw}"
raw['week'] = pd.to_datetime(raw['week']).dt.date
print(f"拉取 {raw.shape[0]} 行")

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
for col in ['b_n','c_n','b_o','c_o','b_amt','c_amt','b_oamt','c_oamt']:
    if col not in w.columns:
        w[col] = 0
    w[col] = pd.to_numeric(w[col].replace('', 0), errors='coerce').fillna(0).astype(float)

w.to_csv(r'e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_decomp_wide_0803_0810.csv', index=False, encoding='utf-8-sig')

# ── 2. 源表真实全市场总量（锚定总变化）────────────────────
tot_sql = """
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
tot = pq.query(tot_sql)
assert isinstance(tot, pd.DataFrame), f"总量查询失败: {tot}"
tot['week'] = pd.to_datetime(tot['week']).dt.date
tb = tot.set_index('week')

def rate(df, n, o):
    return np.where(df[n] > 0, df[o]/df[n], 0.0)

totals = {
    '笔数': {
        'b_n': float(tb.loc[B08, 'billed_cnt']), 'c_n': float(tb.loc[B10, 'billed_cnt']),
        'b_o': float(tb.loc[B08, 'overdue_cnt']), 'c_o': float(tb.loc[B10, 'overdue_cnt']),
    },
    '金额': {
        'b_n': float(tb.loc[B08, 'billed_amt']), 'c_n': float(tb.loc[B10, 'billed_amt']),
        'b_o': float(tb.loc[B08, 'overdue_amt']), 'c_o': float(tb.loc[B10, 'overdue_amt']),
    },
}

# ── 3. 逐维度 Kitagawa 分解 ────────────────────────────
def decomp_dim(sub, basis):
    """对单个维度（单口径）做 Kitagawa 分解。"""
    n = sub[['b_n','c_n']].sum(axis=0)
    o = sub[['b_o','c_o']].sum(axis=0)
    base_rate = o['b_o']/n['b_n'] if n['b_n'] else 0.0
    comp_rate = o['c_o']/n['c_n'] if n['c_n'] else 0.0
    out = sub[['dim_name','dim_group']].copy()
    out['base_n'] = sub['b_n']; out['comp_n'] = sub['c_n']
    out['base_o'] = sub['b_o']; out['comp_o'] = sub['c_o']
    out['base_rate'] = rate(sub, 'b_n','b_o')
    out['comp_rate'] = rate(sub, 'c_n','c_o')
    out['base_share'] = sub['b_n']/n['b_n'] if n['b_n'] else 0.0
    out['comp_share'] = sub['c_n']/n['c_n'] if n['c_n'] else 0.0
    out['individual'] = out['base_share'] * (out['comp_rate'] - out['base_rate'])
    out['structural'] = out['base_rate'] * (out['comp_share'] - out['base_share'])
    out['interaction'] = (out['comp_rate'] - out['base_rate']) * (out['comp_share'] - out['base_share'])
    out['total_effect'] = out['individual'] + out['structural'] + out['interaction']
    out['basis'] = basis
    out['dim_total_change'] = comp_rate - base_rate
    return out

frames = []
colmap = {
    '笔数': ('b_n','c_n','b_o','c_o'),
    '金额': ('b_amt','c_amt','b_oamt','c_oamt'),
}
for basis, (bn, cn, bo, co) in colmap.items():
    sub = w[['dim_name','dim_group', bn, cn, bo, co]].rename(
        columns={bn:'b_n', cn:'c_n', bo:'b_o', co:'c_o'})
    for dim, g in sub.groupby('dim_name'):
        frames.append(decomp_dim(g, basis))

full = pd.concat(frames, ignore_index=True)
full.to_csv(r'e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_decomp_result_0803_0810.csv', index=False, encoding='utf-8-sig')

# ── 4. 全市场总变化 ──────────────────────────────────
print("\n" + "="*90)
print("全市场真实总变化")
print("="*90)
for basis in ['笔数','金额']:
    t = totals[basis]
    br = t['b_o']/t['b_n']; cr = t['c_o']/t['c_n']
    print(f"[{basis}] 基期 {t['b_n']:.0f}->对比期 {t['c_n']:.0f}, 逾期率 {br*100:.2f}% -> {cr*100:.2f}%, 变化 {(cr-br)*100:+.2f}pp")

# ── 5. 每个维度的三类效应结构 ──────────────────────────
print("\n" + "="*90)
print("各维度 Kitagawa 三类效应（看是否普遍为 individual 主导 = 全面普涨）")
print("="*90)
for basis in ['笔数','金额']:
    s = full[full['basis']==basis]
    dim_sum = s.groupby('dim_name').agg(
        individual=('individual','sum'),
        structural=('structural','sum'),
        interaction=('interaction','sum'),
        total_effect=('total_effect','sum'),
    ).reset_index()
    print(f"\n--- [{basis}] 结构效应最大的 Top10 维度（结构效应>0 说明该维度分组占比在向高风险倾斜） ---")
    dim_sum['abs_struct'] = dim_sum['structural'].abs()
    print(dim_sum.reindex(dim_sum['structural'].sort_values(ascending=False).index).head(10)
          [['dim_name','individual','structural','interaction','total_effect']].round(6).to_string(index=False))

# ── 6. 具体分组贡献（individual 效应 = 占比×率差，真实 pp）────────
print("\n" + "="*90)
print("个体效应（占比×率差）最大的分组 = 真正推高整体逾期率的组")
print("="*90)
for basis in ['笔数','金额']:
    s = full[full['basis']==basis]
    print(f"\n--- [{basis}] individual Top15 ---")
    top = s.reindex(s['individual'].sort_values(ascending=False).index).head(15)
    print(top[['dim_name','dim_group','base_n','comp_n','base_rate','comp_rate',
               'base_share','comp_share','individual','structural','interaction']].round(6).to_string(index=False))

# ── 7. 规模可观且率差最大的分组 ──────────────────────────
print("\n" + "="*90)
print("规模可观(base_n>2000 或 金额>10万)且率差最大的分组")
print("="*90)
for basis in ['笔数','金额']:
    s = full[full['basis']==basis].copy()
    s['rate_diff'] = s['comp_rate'] - s['base_rate']
    thr = 2000 if basis=='笔数' else 100000
    sub = s[(s['base_n']>thr) & (s['comp_n']>thr)]
    sub = sub.reindex(sub['rate_diff'].sort_values(ascending=False).index).head(15)
    print(f"\n--- [{basis}] ---")
    print(sub[['dim_name','dim_group','base_n','comp_n','base_rate','comp_rate','rate_diff',
               'base_share','comp_share','individual','structural','interaction']].round(6).to_string(index=False))
