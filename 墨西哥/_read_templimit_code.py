# -*- coding: utf-8 -*-
"""完整读取 临额策略数据检查.xlsx 的 代码 sheet SQL 文本"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import openpyxl

XLSX = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\临额策略数据检查.xlsx"
wb = openpyxl.load_workbook(XLSX, data_only=True)

ws = wb["代码"]
for row in ws.iter_rows(values_only=True):
    for v in row:
        if v is not None and str(v).strip():
            print(str(v))
