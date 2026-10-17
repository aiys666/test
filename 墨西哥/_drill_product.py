# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)
pd.set_option('display.max_rows', 300)

full = pd.read_csv(r'e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_decomp_result_0803_0810.csv')
full['rate_diff'] = full['comp_rate'] - full['base_rate']
full['share_diff'] = full['comp_share'] - full['base_share']

# 相关维度清单
target_dims = ['是否转产线','产品等级','上期产品等级','产品等级变化','转产测试260701','转产测试260722','转产标记1','产品测试0722','产品随机分组0722']

for dim in target_dims:
    sub = full[full['dim_name'] == dim]
    if sub.empty:
        print(f"\n===== 维度[{dim}] 在分解结果中不存在 =====")
        continue
    for basis in ['笔数','金额']:
        s = sub[sub['basis'] == basis].copy()
        s = s.sort_values('base_share', ascending=False)
        print(f"\n===== 维度[{dim}] 【{basis}口径】 按基期占比排序 =====")
        cols = ['dim_group','base_n','comp_n','base_rate','comp_rate','rate_diff',
                'base_share','comp_share','share_diff','individual','structural','interaction']
        print(s[cols].round(6).to_string(index=False))
