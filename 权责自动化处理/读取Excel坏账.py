# -*- coding: utf-8 -*-
"""读取Excel中的坏账数字，对照ba_asset_base_info的逾期字段"""
import openpyxl

SRC = r'E:/岳松个人文件/嘉银工作内容的整理/01工作内容/权责分析/202605月预估/权责近两个月的数据预估.xlsx'
wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb['Sheet1']

merged = {}
for mr in ws.merged_cells.ranges:
    v = ws.cell(mr.min_row, mr.min_col).value
    for r in range(mr.min_row, mr.max_row+1):
        for c in range(mr.min_col, mr.max_col+1):
            merged[(r, c)] = v

def gv(r, c):
    return merged.get((r, c), ws.cell(r, c).value)

print('=== Excel 列头（第9-10行）===')
for c in range(1, 30):
    h1 = gv(9, c) or ''
    h2 = gv(10, c) or ''
    if h1 or h2:
        print(f'  列{c}({chr(64+c)}): [{h1}] | [{h2}]')

print()
print('=== Excel 坏账数据（X列=24）===')
for r in range(10, ws.max_row + 1):
    f_val = gv(r, 6)
    if not hasattr(f_val, 'strftime'):
        continue
    a = gv(r, 1)
    b = gv(r, 2)
    e = gv(r, 5)
    w_val = gv(r, 23)  # W列 = 放款金额
    x_val = gv(r, 24)  # X列 = 坏账
    if x_val is not None and x_val != 0:
        print(f'  月份={f_val.strftime("%Y-%m")} 类型={a} 策略={b} 产品={e} '
              f'放款={w_val} 坏账={x_val}')
