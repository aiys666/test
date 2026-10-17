# -*- coding: utf-8 -*-
"""读取 V6-1分析0923 - 副本 (2).xlsx 各sheet完整内容，含值字段设置"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import openpyxl

XLSX = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\V6-1分析0923 - 副本 (2).xlsx"
wb = openpyxl.load_workbook(XLSX, data_only=True)
print("sheets:", wb.sheetnames)

# 复贷1t0定位分析的xlsx
X2 = r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\复贷8月10周1t0定位分析\复贷1t0上升定位_全维度拆解.xlsx"
wb2 = openpyxl.load_workbook(X2, data_only=True)
print("\n复贷1t0定位分析 sheets:", wb2.sheetnames)
for ws in wb2.worksheets:
    print(f"  [{ws.title}] {ws.max_row}行 x {ws.max_column}列")
    # 打印表头
    if ws.max_row >= 1:
        hdr = [c.value for c in ws[1]]
        print("    表头:", hdr[:20])
