# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)
pd.set_option('display.max_rows', 300)

full = pd.read_csv(r'e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_decomp_result_0803_0810.csv')
full['rate_diff'] = full['comp_rate'] - full['base_rate']
full['share_diff'] = full['comp_share'] - full['base_share']

# 全市场锚定：取「是否转产线」维度（完整覆盖全市场）
anchor = full[full['dim_name'] == '是否转产线']


def market_summary(basis):
    s = anchor[anchor['basis'] == basis]
    b_n = s['base_n'].sum(); c_n = s['comp_n'].sum()
    b_o = s['base_o'].sum(); c_o = s['comp_o'].sum()
    b_r = b_o / b_n; c_r = c_o / c_n
    return b_n, c_n, b_r, c_r, (c_r - b_r)


def decomp_summary(basis):
    s = anchor[anchor['basis'] == basis]
    tot = s['dim_total_change'].iloc[0]
    ind = s['individual'].sum()
    stru = s['structural'].sum()
    inter = s['interaction'].sum()
    return tot, ind, stru, inter


print("=" * 90)
print("一、全市场锚定与三类效应汇总（占总变化比重）—— 判断普涨还是结构转移")
print("=" * 90)
for basis in ['笔数', '金额']:
    b_n, c_n, b_r, c_r, chg = market_summary(basis)
    tot, ind, stru, inter = decomp_summary(basis)
    print(f"\n[{basis}口径] 出账 {b_n:,.0f} -> {c_n:,.0f}")
    print(f"  逾期率 {b_r*100:.2f}% -> {c_r*100:.2f}%  总变化={chg*100:+.4f}pp (维度合计 {tot*100:+.4f}pp)")
    print(f"  个体效应(率普涨) 合计={ind*100:+.4f}pp  占比={ind/tot*100:+.1f}%")
    print(f"  结构效应(占比转移) 合计={stru*100:+.4f}pp  占比={stru/tot*100:+.1f}%")
    print(f"  交互效应 合计={inter*100:+.4f}pp  占比={inter/tot*100:+.1f}%")

print("\n" + "=" * 90)
print("二、转产线相关维度完整分解")
print("=" * 90)
for basis in ['笔数', '金额']:
    s = full[full['basis'] == basis]
    for dn in ['是否转产线', '转产标记1']:
        sub = s[s['dim_name'] == dn]
        if sub.empty:
            continue
        print(f"\n--- [{basis}口径] {dn} ---")
        print(sub[['dim_group', 'base_n', 'comp_n', 'base_rate', 'comp_rate', 'rate_diff',
                   'base_share', 'comp_share', 'individual', 'structural', 'interaction']].round(6).to_string(index=False))

print("\n" + "=" * 90)
print("三、有实质规模(base_n>2000 且 comp_n>2000)的分组中，逾期率恶化最大的 Top20")
print("=" * 90)
for basis in ['笔数', '金额']:
    s = full[full['basis'] == basis]
    print(f"\n--- [{basis}口径] ---")
    sub = s[(s['base_n'] > 2000) & (s['comp_n'] > 2000)]
    sub = sub.reindex(sub['rate_diff'].sort_values(ascending=False).index).head(20)
    print(sub[['dim_name', 'dim_group', 'base_n', 'comp_n', 'base_rate', 'comp_rate', 'rate_diff',
               'base_share', 'comp_share', 'individual', 'structural', 'interaction']].round(6).to_string(index=False))
