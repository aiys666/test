# -*- coding: utf-8 -*-
"""分析周报Sheet引用数据源的公式，确定需要的聚合维度"""
import openpyxl
import warnings
warnings.filterwarnings('ignore')

path = r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\墨西哥\印尼经分周报_20260629_v1.xlsx'
wb = openpyxl.load_workbook(path, read_only=True)

# 扫描周报Sheet的公式
ws = wb['周报']
refs = []
for row in ws.iter_rows(min_row=1, max_row=122, max_col=78, values_only=False):
    for cell in row:
        if cell.value and str(cell.value).startswith('='):
            val = str(cell.value)
            if any(k in val for k in ['数据源', '进件', '复贷', '投放']):
                refs.append(f"R{cell.row}C{cell.column}: {val[:100]}")

# 扫描首贷分析Sheet的公式
ws2 = wb['首贷分析']
refs2 = []
for row in ws2.iter_rows(min_row=1, max_row=140, max_col=27, values_only=False):
    for cell in row:
        if cell.value and str(cell.value).startswith('='):
            val = str(cell.value)
            if any(k in val for k in ['数据源', '进件', '复贷', '投放']):
                refs2.append(f"R{cell.row}C{cell.column}: {val[:100]}")

wb.close()

print("=== 周报 Sheet 引用数据源的公式 ===")
for r in refs:
    print(r)
print(f"  共 {len(refs)} 条引用")

print("\n=== 首贷分析 Sheet 引用数据源的公式 ===")
for r in refs2:
    print(r)
print(f"  共 {len(refs2)} 条引用")

# 扫描是否有透视表引用数据源
print("\n=== 各Sheet是否有透视表 ===")
wb2 = openpyxl.load_workbook(path, read_only=False)
for name in wb2.sheetnames:
    ws = wb2[name]
    pivots = ws._pivots if hasattr(ws, '_pivots') else []
    print(f"  {name}: pivots={len(pivots) if pivots else 0}")
wb2.close()
