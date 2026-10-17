# -*- coding: utf-8 -*-
import openpyxl
import os

PATH = r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\8月预估\【7月】印尼经营计划测算_20260730.xlsx'

print('文件存在:', os.path.exists(PATH))
print('加载工作簿(只读, 无公式计算)...')
wb = openpyxl.load_workbook(PATH, data_only=True, read_only=True)

print('=' * 80)
print('一、所有 Sheet 名:')
for i, name in enumerate(wb.sheetnames, 1):
    print(f'  {i}. {name}')

# 目标关键字
TR_KEYS = ['TR', 'TR%', '首贷-TR', '复贷-TR', '整体-TR']
PROFIT_KEYS = ['经营利润率', '首贷-经营利润率', '复贷-经营利润率', '整体-经营利润率']
BAD_KEYS = ['本金坏账', '首贷-本金坏账', '复贷-本金坏账']
CAPITAL_KEYS = ['资金成本']
ALL_KEYS = TR_KEYS + PROFIT_KEYS + BAD_KEYS + CAPITAL_KEYS

found = []  # (sheet, row, col, value)

print('=' * 80)
print('二、每个 Sheet 概览(行数/列数/前3行前5列):')
for ws in wb.worksheets:
    print('-' * 70)
    print(f'Sheet: {ws.title}')
    # read_only 模式下 ws.max_row/max_column 可能为 None 或不准，迭代获取
    rows = list(ws.iter_rows(values_only=True))
    max_row = len(rows)
    max_col = max((len(r) for r in rows), default=0)
    print(f'  行数: {max_row}, 列数: {max_col}')
    for ri in range(min(3, max_row)):
        vals = rows[ri]
        snippet = [str(vals[ci]) if ci < len(vals) and vals[ci] is not None else '' for ci in range(min(5, len(vals)))]
        print(f'  行{ri+1}: {snippet}')

print('=' * 80)
print('三、字段定位:')
for ws in wb.worksheets:
    for ri, row in enumerate(ws.iter_rows(values_only=True), start=1):
        for ci, val in enumerate(row, start=1):
            if val is None:
                continue
            s = str(val).strip()
            for k in ALL_KEYS:
                if s == k or k in s:
                    found.append((ws.title, ri, ci, s))

if not found:
    print('  未找到精确/包含匹配，开始宽松搜索(包含关键字)...')
    for ws in wb.worksheets:
        for ri, row in enumerate(ws.iter_rows(values_only=True), start=1):
            for ci, val in enumerate(row, start=1):
                if val is None:
                    continue
                s = str(val).strip()
                for k in ALL_KEYS:
                    if k in s:
                        found.append((ws.title, ri, ci, s))
                        break

for item in found:
    print(f'  Sheet={item[0]} | 行={item[1]} | 列={item[2]} | 内容={item[3]}')

print('=' * 80)
print('四、查找 8 月(2026-08) 列号:')
aug_cols = []  # (sheet, row, col, value)
for ws in wb.worksheets:
    for ri, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if ri > 20:  # 日期一般在表头
            break
        for ci, val in enumerate(row, start=1):
            if val is None:
                continue
            s = str(val).strip()
            if '2026-08' in s or '2026/08' in s or '2026.08' in s or s == '8月' or '8月' in s:
                aug_cols.append((ws.title, ri, ci, s))

for item in aug_cols:
    print(f'  Sheet={item[0]} | 行={item[1]} | 列={item[2]} | 内容={item[3]}')

print('=' * 80)
print('五、各字段行附近(前后3行)的8月列数值:')
# 重新加载非 read_only 以便随机访问
wb.close()
wb = openpyxl.load_workbook(PATH, data_only=True)

def col_letter(n):
    try:
        from openpyxl.utils import get_column_letter
        return get_column_letter(n)
    except Exception:
        return str(n)

# 按sheet分组8月列
from collections import defaultdict
aug_by_sheet = defaultdict(list)
for item in aug_cols:
    aug_by_sheet[item[0]].append(item)

# 按sheet分组字段
field_by_sheet = defaultdict(list)
for item in found:
    field_by_sheet[item[0]].append(item)

for sh, fields in field_by_sheet.items():
    if sh not in aug_by_sheet:
        print(f'  [Sheet {sh}] 未找到8月列，跳过')
        continue
    ws = wb[sh]
    max_r = ws.max_row
    aug = aug_by_sheet[sh]
    for f in fields:
        f_sheet, f_row, f_col, f_val = f
        print(f'  [Sheet {sh}] 字段="{f_val}" @ 行{f_row}列{f_col}')
        for ac in aug:
            a_sheet, a_row, a_col, a_val = ac
            print(f'    8月列: 列{a_col} (表头值={a_val})')
            for dr in range(-3, 4):
                r = f_row + dr
                if r < 1 or r > max_r:
                    continue
                cell = ws.cell(row=r, column=a_col)
                label = ws.cell(row=r, column=f_col).value if r != f_row else f_val
                print(f'      行{r} (偏移{dr:+d}): 标签={label!r} | 8月列值={cell.value!r}')

wb.close()
print('=' * 80)
print('分析完成。')
