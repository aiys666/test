# -*- coding: utf-8 -*-
import pandas as pd

path = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\20260928\满额动支发放临额测试_在线临额20261006.xlsx"

df = pd.read_excel(path, sheet_name="问题1", header=None)
print("=== 问题1 row3-9（7.1-8.27 区间上半部分） col0..col25 ===")
for r in range(3, 10):
    vals = [df.iloc[r, c] for c in range(26)]
    print(r, vals)
