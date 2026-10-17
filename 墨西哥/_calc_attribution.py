# -*- coding: utf-8 -*-
"""计算逐维度 Kitagawa 分解的准确汇总数字，用于更新报告。"""
import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)
pd.set_option('display.max_rows', 300)

full = pd.read_csv(r'e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_decomp_result_0803_0810.csv')
full['rate_diff'] = full['comp_rate'] - full['base_rate']
full['share_diff'] = full['comp_share'] - full['base_share']

print("总行数:", len(full), " 维度数:", full['dim_name'].nunique(), " 口径:", full['basis'].unique())

# 全市场真实总量（源表锚定，从 CSV 无法得到，但可用每维度合计来校验 dim_total_change）
print("\n=== 每个维度的 dim_total_change 是否一致（应≈全市场真实总变化） ===")
for basis in ['笔数', '金额']:
    s = full[full['basis'] == basis]
    dtc = s.groupby('dim_name')['dim_total_change'].first()
    print(f"[{basis}] dim_total_change: min={dtc.min()*100:+.4f}pp  max={dtc.max()*100:+.4f}pp  mean={dtc.mean()*100:+.4f}pp  median={dtc.median()*100:+.4f}pp  n_dim={len(dtc)}")

print("\n=== 每维度三类效应之和 与 dim_total_change 的校验 ===")
for basis in ['笔数', '金额']:
    s = full[full['basis'] == basis]
    chk = s.groupby('dim_name').agg(
        ind=('individual', 'sum'),
        stru=('structural', 'sum'),
        inter=('interaction', 'sum'),
        tot_eff=('total_effect', 'sum'),
        dtc=('dim_total_change', 'first'),
    )
    chk['sum3'] = chk['ind'] + chk['stru'] + chk['inter']
    chk['diff'] = (chk['sum3'] - chk['dtc']).abs()
    print(f"[{basis}] sum3 vs dim_total_change: max_abs_diff={chk['diff'].max():.2e}")

print("\n=== 个体效应占比的分布（每维度 individual_sum / dim_total_change） ===")
for basis in ['笔数', '金额']:
    s = full[full['basis'] == basis]
    grp = s.groupby('dim_name').agg(
        ind=('individual', 'sum'),
        stru=('structural', 'sum'),
        inter=('interaction', 'sum'),
        dtc=('dim_total_change', 'first'),
    )
    grp['ind_pct'] = grp['ind'] / grp['dtc'] * 100
    grp['stru_pct'] = grp['stru'] / grp['dtc'] * 100
    grp['inter_pct'] = grp['inter'] / grp['dtc'] * 100
    print(f"\n[{basis}] 个体效应占比: 中位数={grp['ind_pct'].median():+.1f}%  均值={grp['ind_pct'].mean():+.1f}%")
    print(f"[{basis}] 结构效应占比: 中位数={grp['stru_pct'].median():+.1f}%  均值={grp['stru_pct'].mean():+.1f}%")
    print(f"[{basis}] 交互效应占比: 中位数={grp['inter_pct'].median():+.1f}%  均值={grp['inter_pct'].mean():+.1f}%")
    # 结构效应为正的维度（占比转移向高风险倾斜）
    pos = grp[grp['stru'] > 0]
    neg = grp[grp['stru'] < 0]
    print(f"[{basis}] 结构效应>0 的维度数: {len(pos)}/{len(grp)}, <0 维度数: {len(neg)}")

print("\n=== 转产线相关维度 ===")
for basis in ['笔数', '金额']:
    s = full[full['basis'] == basis]
    for dn in ['是否转产线', '转产标记1']:
        sub = s[s['dim_name'] == dn]
        if len(sub) == 0:
            continue
        dtc = sub['dim_total_change'].iloc[0]
        ind = sub['individual'].sum(); stru = sub['structural'].sum(); inter = sub['interaction'].sum()
        print(f"\n[{basis}][{dn}] total_change={dtc*100:+.4f}pp  ind={ind*100:+.4f}  stru={stru*100:+.4f}  inter={inter*100:+.4f}")
        print(sub[['dim_group','base_n','comp_n','base_rate','comp_rate','rate_diff','base_share','comp_share']].round(6).to_string(index=False))

print("\n=== 规模可观且率差最大 Top15（笔数/金额） ===")
for basis in ['笔数', '金额']:
    s = full[full['basis'] == basis].copy()
    thr = 2000 if basis == '笔数' else 100000
    sub = s[(s['base_n'] > thr) & (s['comp_n'] > thr)]
    sub = sub.reindex(sub['rate_diff'].sort_values(ascending=False).index).head(15)
    print(f"\n[{basis}]")
    print(sub[['dim_name','dim_group','base_n','comp_n','base_rate','comp_rate','rate_diff','base_share','comp_share']].round(6).to_string(index=False))
