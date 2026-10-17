# -*- coding: utf-8 -*-
import openpyxl

path = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\老客拒尾测试考虑逾期天数 - 副本.xlsx"
wb = openpyxl.load_workbook(path, data_only=True)

ws = wb["整体它包有在逾"]
print("===== 整体它包有在逾 max_row=", ws.max_row, " max_col=", ws.max_column)
for i, row in enumerate(ws.iter_rows()):
    vals = ["" if c.value is None else str(c.value) for c in row]
    print(i, "||".join(vals))