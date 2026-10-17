# -*- coding: utf-8 -*-
"""把修正后的全量离线临额分析合并到主Excel"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
import pandas as pd

prev = r"E:\岳松个人文件\嘉银工作内容的整理\code\临额效果分析_重点结论.xlsx"
offline = r"E:\岳松个人文件\嘉银工作内容的整理\code\离线临额效果分析_全量.xlsx"

xls = pd.ExcelFile(prev)
existing = {s: pd.read_excel(prev, sheet_name=s) for s in xls.sheet_names}

d1 = pd.read_excel(offline, sheet_name='D1_全部52批次明细')
d2 = pd.read_excel(offline, sheet_name='D2_人群x实验组汇总')
d3 = pd.read_excel(offline, sheet_name='D3_有在贷按月趋势')
d4 = pd.read_excel(offline, sheet_name='D4_对照组')

with pd.ExcelWriter(prev, engine='openpyxl') as w:
    for s, df in existing.items():
        df.to_excel(w, sheet_name=s, index=False)
    d1.to_excel(w, sheet_name='C1_离线临额_全部52批次', index=False)
    d2.to_excel(w, sheet_name='C2_离线临额_人群x实验组', index=False)
    d3.to_excel(w, sheet_name='C3_离线临额_按月趋势', index=False)
    d4.to_excel(w, sheet_name='C4_离线临额_对照组', index=False)

print(f"已合并到: {prev}")
print("Sheet数:", len(existing) + 4)
