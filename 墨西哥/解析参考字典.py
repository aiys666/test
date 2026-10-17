# -*- coding: utf-8 -*-
"""解析 数据库表字典202608.xlsx -> reference_dict.json
格式A: 字段名称/字段中文释义/数值类型/字段逻辑或说明 [/key关联说明]
格式B: Column/Type/[Extra/]/Comment
"""
import json
from openpyxl import load_workbook

SRC = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\01了解文档\数据库表字典202608.xlsx"
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\field_dict_data\reference_dict.json"

wb = load_workbook(SRC, data_only=True)
result = {}

def norm(v):
    return (str(v).strip() if v is not None else "")


for sn in wb.sheetnames:
    ws = wb[sn]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        result[sn] = []
        continue

    # 找表头行
    hdr_idx = None
    fmt = None
    name_col = cn_col = logic_col = None
    for i, row in enumerate(rows[:8]):
        cells = [norm(c) for c in row]
        if any(c.startswith("字段名称") for c in cells):
            hdr_idx = i
            fmt = "A"
            name_col = next(j for j, c in enumerate(cells) if c.startswith("字段名称"))
            cn_col = next((j for j, c in enumerate(cells) if "释义" in c or "中文" in c), name_col + 1)
            logic_col = next((j for j, c in enumerate(cells) if "逻辑" in c or "说明" in c), name_col + 3)
            break
        if any(c.lower() == "column" for c in cells):
            hdr_idx = i
            fmt = "B"
            name_col = next(j for j, c in enumerate(cells) if c.lower() == "column")
            cn_col = next((j for j, c in enumerate(cells) if c in ("Comment", "中文", "注释")), name_col + 3)
            # 有些表用 Extra 存中文
            if cn_col >= len(cells) or norm(cells[cn_col]) == "":
                cn_col = next((j for j, c in enumerate(cells) if c == "Extra"), cn_col)
            break

    if hdr_idx is None:
        result[sn] = []
        continue

    fields = []
    cur_table = sn
    for row in rows[hdr_idx + 1:]:
        cells = [norm(c) for c in row]
        # 格式A下可能出现 "表N：xxx" 分段
        if fmt == "A" and len(cells) > 0 and cells[0].startswith("表"):
            cur_table = cells[0].split("：")[-1].strip()
            continue
        if name_col >= len(cells):
            continue
        name = cells[name_col]
        if not name or name.lower() == "column":
            continue
        cn = cells[cn_col] if cn_col is not None and cn_col < len(cells) else ""
        logic = cells[logic_col] if logic_col is not None and logic_col < len(cells) else ""
        fields.append({"name": name, "cn": cn, "logic": logic, "table": cur_table})

    result[sn] = fields

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)

# 打印概览
total = 0
for sn, fields in result.items():
    if fields:
        total += len(fields)
        print(f"{sn:32s} {len(fields):4d} 字段  例:{fields[0]['name']} | {fields[0]['cn'][:18]}")
print("总字段(非空sheet):", total)
