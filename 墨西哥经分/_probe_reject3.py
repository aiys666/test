# -*- coding: utf-8 -*-
import openpyxl, io, sys

path = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\老客拒尾分析.xlsx"
wb = openpyxl.load_workbook(path, data_only=True, read_only=True)

out = io.StringIO()

def dump(name, out):
    ws = wb[name]
    print(f"\n########## {name} ##########", file=out)
    for ri, row in enumerate(ws.iter_rows(values_only=True)):
        cells = ["" if v is None else v for v in row]
        while cells and cells[-1] == "":
            cells.pop()
        if cells:
            print(f"R{ri}: {cells}", file=out)

for name in ["整体数据", "BY评级&历史逾期天数", "BY评级&他包在逾"]:
    dump(name, out)

wb.close()
open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥经分\_dump_reject.txt", "w", encoding="utf-8").write(out.getvalue())
print("written")
