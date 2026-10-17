# -*- coding: utf-8 -*-
import openpyxl

path = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\老客拒尾分析.xlsx"
wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
print("SHEETS:", wb.sheetnames, flush=True)
for name in wb.sheetnames:
    ws = wb[name]
    cnt = 0
    first_row = None
    for row in ws.iter_rows(values_only=True):
        if cnt == 0:
            first_row = row
        cnt += 1
    print(f"\n### {name}  rows={cnt}", flush=True)
    print("HEADER:", first_row, flush=True)
wb.close()
print("DONE", flush=True)
