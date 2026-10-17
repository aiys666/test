# -*- coding: utf-8 -*-
import openpyxl

f = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\墨西哥周报达成跟进_9月模板_更新_20260914_134729.xlsx"
wb = openpyxl.load_workbook(f, data_only=False)
ws1 = wb["Sheet1"]

print("=== R1/R2 表头 ===")
for c in range(1, 15):
    v = ws1.cell(2, c).value
    print(f"  col{c}({openpyxl.utils.get_column_letter(c)}): {repr(v)}")

print("\n=== R20 第二段表头 ===")
for c in range(5, 14):
    v = ws1.cell(20, c).value
    print(f"  col{c}({openpyxl.utils.get_column_letter(c)}): {repr(v)}")

print("\n=== 关键数据行 E/F/G/H/J/K/L/M ===")
for row in [3, 4, 5, 6, 9, 15, 16, 17, 21, 22, 23, 24, 25, 30, 31, 33, 36]:
    vals = {}
    for c in [5, 6, 7, 8, 10, 11, 12, 13]:
        vals[openpyxl.utils.get_column_letter(c)] = ws1.cell(row, c).value
    print(f"  R{row}: {vals}")

print("\n=== 息费 R15-R17 是否空白 ===")
for row in [15, 16, 17]:
    nonempty = [openpyxl.utils.get_column_letter(c) for c in [5,6,7,8,10,11,12,13] if ws1.cell(row, c).value not in (None, "")]
    print(f"  R{row}: 非空列={nonempty}")

print("\n=== 辅助列 O/P/Q (R2-R7) ===")
for row in range(2, 8):
    vals = [ws1.cell(row, c).value for c in [15, 16, 17]]
    print(f"  R{row}: {vals}")

print("\n=== Sheet3 数据源表头 + 前3行 ===")
ws3 = wb["数据源"]
for c in range(1, 13):
    print(f"  col{c}({openpyxl.utils.get_column_letter(c)}): {repr(ws3.cell(1, c).value)}")
for r in range(2, 5):
    print(f"  R{r}: {[ws3.cell(r, c).value for c in range(1, 13)]}")
