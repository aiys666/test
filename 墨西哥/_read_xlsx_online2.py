# -*- coding: utf-8 -*-
import pandas as pd

path = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\20260928\满额动支发放临额测试_在线临额20261006.xlsx"

df = pd.read_excel(path, sheet_name="问题1", header=None)
# 打印所有行完整内容
print("=== 问题1 全部行（每行 col0..col37） ===")
for r in range(len(df)):
    vals = [df.iloc[r, c] for c in range(38)]
    print(r, vals)

print()
for sn in ["取授信时资产等级", "取大流时资产等级"]:
    d = pd.read_excel(path, sheet_name=sn, header=None)
    print(f"=== {sn} shape={d.shape} ===")
    print(d.to_string(max_cols=40, max_colwidth=60))
    print()
