# -*- coding: utf-8 -*-
import openpyxl

path = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\老客拒尾分析.xlsx"
wb = openpyxl.load_workbook(path, data_only=True, read_only=True)

def dump(name):
    ws = wb[name]
    print(f"\n########## {name} ##########")
    for ri, row in enumerate(ws.iter_rows(values_only=True)):
        cells = ["" if v is None else v for v in row]
        # 去掉尾部空
        while cells and cells[-1] == "":
            cells.pop()
        if cells:
            print(f"R{ri}: {cells}")

dump("整体数据")
dump("BY评级 ")
wb.close()
