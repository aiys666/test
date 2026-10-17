# -*- coding: utf-8 -*-
"""完整dump Excel所有sheet, 逐格读取含合并单元格的多级表头"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import openpyxl

f = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\20260928\满额动支发放临额测试_在线临额20261006.xlsx"
wb = openpyxl.load_workbook(f, data_only=True)
print("sheets:", wb.sheetnames)

for sn in wb.sheetnames:
    ws = wb[sn]
    print("="*150)
    print(f"SHEET: {sn}  dims={ws.dimensions}  max_row={ws.max_row} max_col={ws.max_column}")
    # 打印合并单元格区域
    print("merged:", [str(m) for m in ws.merged_cells.ranges][:30])
