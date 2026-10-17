# -*- coding: utf-8 -*-
"""把离线临额分析追加到 临额效果分析_重点结论.xlsx"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
import pandas as pd

prev = r"E:\岳松个人文件\嘉银工作内容的整理\code\临额效果分析_重点结论.xlsx"
offline = r"E:\岳松个人文件\嘉银工作内容的整理\code\离线临额效果分析_重点结论.xlsx"

xls = pd.ExcelFile(prev)
existing = {s: pd.read_excel(prev, sheet_name=s) for s in xls.sheet_names}

d1 = pd.read_excel(offline, sheet_name='D1_各批次放款率')
d2 = pd.read_excel(offline, sheet_name='D2_对照组放款率')
d3 = pd.read_excel(offline, sheet_name='D3_额度使用率')
d4 = pd.read_excel(offline, sheet_name='D4_临额金额分桶放款率')

with pd.ExcelWriter(prev, engine='openpyxl') as w:
    for s, df in existing.items():
        df.to_excel(w, sheet_name=s, index=False)
    d1.to_excel(w, sheet_name='C1_离线临额_各批次放款率', index=False)
    d2.to_excel(w, sheet_name='C2_离线临额_对照组', index=False)
    d3.to_excel(w, sheet_name='C3_离线临额_额度使用率', index=False)
    d4.to_excel(w, sheet_name='C4_离线临额_金额分桶放款率', index=False)

print(f"已合并到: {prev}")
print("Sheet数:", len(existing) + 4)
