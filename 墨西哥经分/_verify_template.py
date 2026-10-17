# -*- coding: utf-8 -*-
import openpyxl

f = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\墨西哥周报达成跟进_9月模板.xlsx"
wb = openpyxl.load_workbook(f, data_only=False)
ws1 = wb["Sheet1"]

print("=== 模板 R20-R39 各列原始值 ===")
for row in range(20, 40):
    vals = {}
    for c in range(4, 14):
        v = ws1.cell(row, c).value
        if v is not None:
            vals[openpyxl.utils.get_column_letter(c)] = v
    if vals:
        print(f"  R{row}: {vals}")
