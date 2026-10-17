# -*- coding: utf-8 -*-
"""逐格dump 问题1 sheet"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import openpyxl

f = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\20260928\满额动支发放临额测试_在线临额20261006.xlsx"
wb = openpyxl.load_workbook(f, data_only=True)
ws = wb['问题1']

# 先打印前4行(表头)每列内容
for r in range(1, 5):
    print(f"--- ROW {r} ---")
    for c in range(1, 39):
        v = ws.cell(row=r, column=c).value
        if v is not None:
            print(f"  {openpyxl.utils.get_column_letter(c)}{r}: {repr(v)}")

print()
print("="*150)
# 打印所有数据行(5-26)
for r in range(5, 27):
    print(f"--- ROW {r} ---")
    for c in range(1, 39):
        v = ws.cell(row=r, column=c).value
        if v is not None:
            # 数字保留原值
            print(f"  {openpyxl.utils.get_column_letter(c)}{r}: {repr(v)}")
