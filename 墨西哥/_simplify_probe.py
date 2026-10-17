# -*- coding: utf-8 -*-
"""读取双评级 xlsx 全期_产品×档, 看 B/C/E 等产品既有口径数值, 辅助简化重构决策."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd

X = r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\墨西哥_产品评级收益测算_双评级.xlsx"
df = pd.read_excel(X, sheet_name="全期_产品×档")
print("cols:", len(df.columns))
for c in df.columns:
    print(repr(c))
