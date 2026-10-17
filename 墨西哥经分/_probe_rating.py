# -*- coding: utf-8 -*-
import openpyxl

path = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\老客拒尾分析.xlsx"
wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
ws = wb["BY评级 "]
for ri, row in enumerate(ws.iter_rows(values_only=True)):
    cells = ["" if v is None else v for v in row]
    while cells and cells[-1] == "":
        cells.pop()
    if cells:
        print(f"R{ri}: {cells}")
wb.close()
print("DONE")
