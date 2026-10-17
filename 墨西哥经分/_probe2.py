# -*- coding: utf-8 -*-
import openpyxl
path = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\老客拒尾测试考虑逾期天数 - 副本.xlsx"
wb = openpyxl.load_workbook(path, data_only=True)

ws = wb["V6-1它包在逾"]
print("==== V6-1它包在逾 dims ====", ws.max_row, ws.max_column)
for ri, r in enumerate(ws.iter_rows()):
    vals = [c.value for c in r]
    if any(v is not None for v in vals):
        print(ri, "|", vals)
