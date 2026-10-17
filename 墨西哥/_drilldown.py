# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)
pd.set_option('display.max_rows', 200)

full = pd.read_csv(r'e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_decomp_result_0803_0810.csv')

# 补充率变化和占比变化列
full['rate_diff'] = full['comp_rate'] - full['base_rate']
full['share_diff'] = full['comp_share'] - full['base_share']

print("总行数:", len(full), "| 维度数:", full['dim_name'].nunique())

for basis in ['笔数', '金额']:
    sub = full[full['basis'] == basis].copy()
    print(f"\n{'='*80}")
    print(f"【{basis}口径】")

    # 1. 个体效应 Top（率变化贡献最大的分组）
    ind = sub.reindex(sub['individual'].abs().sort_values(ascending=False).index).head(12)
    print(f"\n--- 个体效应(率驱动) Top12 分组 ---")
    print(ind[['dim_name','dim_group','base_n','comp_n','base_rate','comp_rate',
               'rate_diff','base_share','comp_share','individual','structural','interaction']]
          .round(6).to_string(index=False))

    # 2. 结构效应 Top（占比变化贡献最大的分组）
    stru = sub.reindex(sub['structural'].abs().sort_values(ascending=False).index).head(12)
    print(f"\n--- 结构效应(占比驱动) Top12 分组 ---")
    print(stru[['dim_name','dim_group','base_n','comp_n','base_rate','comp_rate',
                'rate_diff','base_share','comp_share','individual','structural','interaction']]
          .round(6).to_string(index=False))

    # 3. 交互效应 Top
    inter = sub.reindex(sub['interaction'].abs().sort_values(ascending=False).index).head(8)
    print(f"\n--- 交互效应 Top8 分组 ---")
    print(inter[['dim_name','dim_group','base_n','comp_n','base_rate','comp_rate',
                 'rate_diff','base_share','comp_share','individual','structural','interaction']]
          .round(6).to_string(index=False))

    # 4. 率变化绝对值最大的分组（真正恶化的群体）
    rated = sub.reindex(sub['rate_diff'].abs().sort_values(ascending=False).index).head(15)
    print(f"\n--- 逾期率变化(绝对值) Top15 分组 ---")
    print(rated[['dim_name','dim_group','base_n','comp_n','base_rate','comp_rate',
                 'rate_diff','base_share','comp_share']].round(6).to_string(index=False))
