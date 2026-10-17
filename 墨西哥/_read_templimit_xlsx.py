# -*- coding: utf-8 -*-
"""读取用户离线临额分析Excel 临额策略数据检查.xlsx 全部内容"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import openpyxl

XLSX = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\临额策略数据检查.xlsx"
wb = openpyxl.load_workbook(XLSX, data_only=True)
print("sheets:", wb.sheetnames)

for ws in wb.worksheets:
    print("\n" + "="*100)
    print(f"### Sheet: {ws.title}  rows={ws.max_row} cols={ws.max_column}")
    # 打印前 60 行
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        # 去掉全空行
        vals = [("" if v is None else v) for v in row]
        if not any(str(v).strip() for v in vals):
            continue
        # 每个单元格截断显示
        short = [str(v)[:120] for v in vals]
        print(f"[{i}] " + " | ".join(short))
        if i >= 80:
            print("...(截断, 更多行见后续)")
            break
