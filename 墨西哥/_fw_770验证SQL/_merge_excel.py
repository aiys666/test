# -*- coding: utf-8 -*-
"""把逾期率重点结论追加到 临额效果分析_重点结论.xlsx"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
import pandas as pd

prev = r"E:\岳松个人文件\嘉银工作内容的整理\code\临额效果分析_重点结论.xlsx"
overdue = r"E:\岳松个人文件\嘉银工作内容的整理\code\临额逾期率分析_重点结论.xlsx"

# 读取已有sheet
xls = pd.ExcelFile(prev)
existing = {s: pd.read_excel(prev, sheet_name=s) for s in xls.sheet_names}

# 读取逾期率分析的核心sheet
d1 = pd.read_excel(overdue, sheet_name='D1_总体逾期率_分账龄')
d2 = pd.read_excel(overdue, sheet_name='D2_有临额vs无临额')
d3 = pd.read_excel(overdue, sheet_name='D3_逾期件均拆临额')
d5 = pd.read_excel(overdue, sheet_name='D5_临额金额分桶逾期率')

# 合并写入
with pd.ExcelWriter(prev, engine='openpyxl') as w:
    for s, df in existing.items():
        df.to_excel(w, sheet_name=s, index=False)
    # 追加逾期率重点sheet (重命名为B系列)
    d1.to_excel(w, sheet_name='B1_总体逾期率_分账龄', index=False)
    d2.to_excel(w, sheet_name='B2_有临额vs无临额_逾期率', index=False)
    d3.to_excel(w, sheet_name='B3_逾期件均拆临额影响', index=False)
    d5.to_excel(w, sheet_name='B4_临额金额分桶_逾期率', index=False)

print(f"已合并到: {prev}")
print(f"Sheet列表: {list(existing.keys()) + ['B1_总体逾期率_分账龄','B2_有临额vs无临额_逾期率','B3_逾期件均拆临额影响','B4_临额金额分桶_逾期率']}")
