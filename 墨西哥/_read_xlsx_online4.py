# -*- coding: utf-8 -*-
"""读取Excel问题1 sheet完整数据, 用于与yj表放款口径对比"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd

f = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\20260928\满额动支发放临额测试_在线临额20261006.xlsx"
xl = pd.ExcelFile(f)
print("sheets:", xl.sheet_names)
for s in xl.sheet_names:
    df = xl.parse(s, header=None, nrows=50)
    print("="*100)
    print("SHEET:", s, "shape_preview:", df.shape)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 500)
pd.set_option('display.max_colwidth', 30)

# 问题1 sheet 完整
df1 = xl.parse("问题1", header=None)
print("="*100)
print("问题1 完整:")
print(df1.to_string())
