# -*- coding: utf-8 -*-
"""
合并 field_dict_data/*.json -> 墨西哥老客核心字段字典.xlsx
列：来源文件 | 表名 | 字段名 | 业务含义 | 数据来源表 | 更新频率 | 口径定义
"""
import json, glob, os, re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

DATA_DIR = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\field_dict_data"
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\墨西哥老客核心字段字典.xlsx"

# 表级默认更新频率（无则每日；07为手动）
DEFAULT_FREQ = {
    "mx.yj_clear_reloan": "手动",
}

# 从口径文本里尝试提取来源表（s0x_/s2x_/mx./ods./tmp_ 等）
_SRC_RE = re.compile(
    r"(?:ods\.|mx\.)?(s0[0-9]_[a-zA-Z0-9_]+|s2[0-9]_[a-zA-Z0-9_]+|mx\.[a-zA-Z0-9_]+|ods\.[a-zA-Z0-9_]+|tmp_[a-zA-Z0-9_]+|wxs_[a-zA-Z0-9_]+|darren_[a-zA-Z0-9_]+|android_[a-zA-Z0-9_]+)"
)


def guess_source(field, table):
    logic = field.get("logic", "") or ""
    desc = field.get("desc", "") or ""
    if field.get("source_table"):
        return field["source_table"]
    m = _SRC_RE.search(logic)
    if m:
        return m.group(1)
    m = _SRC_RE.search(desc)
    if m:
        return m.group(1)
    if logic.startswith("派生") or logic.startswith("case") or logic.startswith("sum") or "sum(" in logic.lower() or "case when" in logic.lower():
        return "派生计算（见口径）"
    return "待补"


def load_all():
    records = []
    for fp in sorted(glob.glob(os.path.join(DATA_DIR, "*.json"))):
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        for t in data:
            table = t.get("table", "?")
            src_file = t.get("source_file", os.path.basename(fp))
            freq = DEFAULT_FREQ.get(table, "每日")
            for fld in t.get("fields", []):
                records.append({
                    "src_file": src_file,
                    "table": table,
                    "name": fld.get("name", "?"),
                    "desc": fld.get("desc", ""),
                    "source": guess_source(fld, table),
                    "freq": fld.get("update_freq", freq),
                    "logic": fld.get("logic", ""),
                })
    return records


HEADERS = ["来源文件", "表名", "字段名", "业务含义", "数据来源表", "更新频率", "口径定义"]

wb = Workbook()
ws = wb.active
ws.title = "字段字典"

thin = Side(style="thin", color="BFBFBF")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
title_font = Font(name="微软雅黑", size=14, bold=True, color="1F4E78")
header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
header_fill = PatternFill("solid", fgColor="1F4E78")
body_font = Font(name="微软雅黑", size=10)
wrap_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
wrap_left = Alignment(horizontal="left", vertical="top", wrap_text=True)

NCOL = len(HEADERS)
last_col = get_column_letter(NCOL)

ws.merge_cells(f"A1:{last_col}1")
ws["A1"] = "墨西哥老客核心字段字典（段清单+口径说明）"
ws["A1"].font = title_font
ws["A1"].alignment = wrap_center
ws.row_dimensions[1].height = 28

HROW = 2
for c, h in enumerate(HEADERS, start=1):
    cell = ws.cell(row=HROW, column=c, value=h)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = wrap_center
    cell.border = border
ws.row_dimensions[HROW].height = 22

records = load_all()
r = HROW + 1
for rec in records:
    vals = [rec["src_file"], rec["table"], rec["name"], rec["desc"], rec["source"], rec["freq"], rec["logic"]]
    for c, v in enumerate(vals, start=1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font = body_font
        cell.border = border
        cell.alignment = wrap_center if c in (3, 6) else wrap_left
    r += 1

widths = [22, 30, 30, 40, 28, 10, 70]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w

ws.freeze_panes = f"A{HROW + 1}"
ws.auto_filter.ref = f"A{HROW}:{last_col}{r - 1}"

# 汇总sheet
ws2 = wb.create_sheet("汇总")
ws2.merge_cells("A1:C1")
ws2["A1"] = "各表字段数汇总"
ws2["A1"].font = title_font
ws2.cell(row=2, column=1, value="表名").font = header_font
ws2.cell(row=2, column=2, value="来源文件").font = header_font
ws2.cell(row=2, column=3, value="字段数").font = header_font
for c in range(1, 4):
    ws2.cell(row=2, column=c).fill = header_fill
    ws2.cell(row=2, column=c).alignment = wrap_center
    ws2.cell(row=2, column=c).border = border

from collections import Counter
cnt = Counter((rec["table"], rec["src_file"]) for rec in records)
rr = 3
for (tbl, sf), n in sorted(cnt.items()):
    ws2.cell(row=rr, column=1, value=tbl).font = body_font
    ws2.cell(row=rr, column=2, value=sf).font = body_font
    ws2.cell(row=rr, column=3, value=n).font = body_font
    for c in range(1, 4):
        ws2.cell(row=rr, column=c).border = border
    rr += 1
ws2.cell(row=rr, column=1, value="合计").font = Font(name="微软雅黑", size=11, bold=True)
ws2.cell(row=rr, column=3, value=len(records)).font = Font(name="微软雅黑", size=11, bold=True)
for c in range(1, 4):
    ws2.column_dimensions[get_column_letter(c)].width = 40 if c == 2 else 18

wb.save(OUT)
print(f"OK -> {OUT}")
print(f"总字段数: {len(records)}")
for (tbl, sf), n in sorted(cnt.items()):
    print(f"  {tbl}: {n}（{sf}）")
