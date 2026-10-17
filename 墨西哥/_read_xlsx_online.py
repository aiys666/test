# -*- coding: utf-8 -*-
import pandas as pd

path = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\20260928\满额动支发放临额测试_在线临额20261006.xlsx"

df = pd.read_excel(path, sheet_name="问题1", header=None)
print("=== row2 完整文本 ===")
print(repr(df.iloc[2, 0]))
print()
print("=== row0 ===")
print(repr(df.iloc[0, 0]))
print()
print("=== 数值块 4-13行（7.1-8.27区间） col0..col19 ===")
for r in range(3, 14):
    vals = []
    for c in range(0, 20):
        v = df.iloc[r, c]
        vals.append(v)
    print(r, vals)
print()
print("=== 数值块 17-25行（9.5-无限区间） col0..col19 ===")
for r in range(17, 26):
    vals = []
    for c in range(0, 20):
        v = df.iloc[r, c]
        vals.append(v)
    print(r, vals)

print()
df2 = pd.read_excel(path, sheet_name="问题2", header=None)
print("=== 问题2 完整 ===")
print(df2.to_string(max_cols=20, max_colwidth=80))
