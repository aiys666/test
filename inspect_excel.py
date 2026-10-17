# -*- coding: utf-8 -*-
"""
读取 Excel 结构脚本（只读模式，不修改原文件）
目标文件: 墨西哥周报达成跟进_8月模板.xlsx
"""
import os
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

FILE = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\墨西哥周报达成跟进_8月模板.xlsx"

print("=" * 80)
print("【0】文件信息")
print("=" * 80)
print("文件路径:", FILE)
print("文件存在:", os.path.exists(FILE))
print("文件大小(bytes):", os.path.getsize(FILE) if os.path.exists(FILE) else "N/A")

# 只读模式打开，避免修改
wb = load_workbook(FILE, data_only=True, read_only=False)
# data_only=True -> 取公式计算后的值；如果原文件没有缓存值，公式可能返回 None

print()
print("=" * 80)
print("【1】所有 Sheet 名")
print("=" * 80)
for i, name in enumerate(wb.sheetnames, 1):
    print(f"  Sheet{i}: {name}")

ws = wb["Sheet1"] if "Sheet1" in wb.sheetnames else wb[wb.sheetnames[0]]
print()
print("当前分析 Sheet:", ws.title)

print()
print("=" * 80)
print("【2】Sheet1 基本属性")
print("=" * 80)
print("max_row(总行数):", ws.max_row)
print("max_column(总列数):", ws.max_column)
print("dimensions:", ws.dimensions)

# 列宽
print()
print("=" * 80)
print("【3】每列宽度 (A-K)")
print("=" * 80)
for col_idx in range(1, 12):  # A..K
    letter = get_column_letter(col_idx)
    dim = ws.column_dimensions.get(letter)
    width = dim.width if dim is not None else None
    print(f"  列 {letter}: width={width}")

# 合并单元格
print()
print("=" * 80)
print("【4】合并单元格 (merged_cells)")
print("=" * 80)
merged = sorted(ws.merged_cells.ranges, key=lambda r: (r.min_row, r.min_col))
print(f"合并区域数量: {len(merged)}")
for mr in merged:
    print(f"  {mr}")

# 构建“属于哪个合并区域”的快速查找表
def find_merged(row, col):
    for mr in ws.merged_cells.ranges:
        if mr.min_row <= row <= mr.max_row and mr.min_col <= col <= mr.max_col:
            return str(mr)
    return None

# 打印 A1:K40 所有单元格
print()
print("=" * 80)
print("【5】R1-R40 × A-K 单元格内容（含合并标记）")
print("=" * 80)
header_letters = [get_column_letter(c) for c in range(1, 12)]
print("行号 | " + " | ".join(f"{h:>10}" for h in header_letters))
print("-" * 130)
for r in range(1, 41):
    cells = []
    for c in range(1, 12):
        val = ws.cell(row=r, column=c).value
        if val is None:
            val = ""
        sval = str(val).replace("\n", "\\n")
        if len(sval) > 10:
            sval = sval[:9] + "…"
        cells.append(sval)
    print(f" R{r:<3}| " + " | ".join(f"{v:>10}" for v in cells))

# 详细逐单元格（完整值）
print()
print("=" * 80)
print("【6】逐单元格详细内容（R1-R40 × A-K，完整值 + 合并标记）")
print("=" * 80)
for r in range(1, 41):
    for c in range(1, 12):
        letter = get_column_letter(c)
        val = ws.cell(row=r, column=c).value
        merged_tag = find_merged(r, c)
        tag = f"  [合并:{merged_tag}]" if merged_tag else ""
        if val is None and not merged_tag:
            continue
        if val is None:
            val_text = "<空>"
        else:
            val_text = str(val).replace("\n", "\\n")
        print(f"  {letter}{r}: {val_text}{tag}")
    print()

# 分段打印：方便核对
def print_section(title, row_range):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)
    for r in row_range:
        row_vals = []
        for c in range(1, 12):
            letter = get_column_letter(c)
            val = ws.cell(row=r, column=c).value
            merged_tag = find_merged(r, c)
            if val is None and not merged_tag:
                row_vals.append(f"{letter}{r}=空")
                continue
            val_text = "<空>" if val is None else str(val).replace("\n", "\\n")
            tag = f"[合并:{merged_tag}]" if merged_tag else ""
            row_vals.append(f"{letter}{r}={val_text}{tag}")
        print(f"  R{r}: " + " | ".join(row_vals))

print_section("【7】R2 表头行（指标列名）", [2])
print_section("【8】R3-R17 第一段（规模&收入）", range(3, 18))
print_section("【9】R20 第二段表头", [20])
print_section("【10】R21-R36 第二段（成本）", range(21, 37))
print_section("【11】R37-R39 脚注", range(37, 40))

# 按列打印：D、E、F、G、H、I、J、K
print()
print("=" * 80)
print("【12】按列打印所有行数据 (D,E,F,G,H,I,J,K) R1-R40")
print("=" * 80)
target_cols = {
    "D": 4, "E(8月目标)": 5, "F(8月实际)": 6, "G(8月预估)": 7,
    "H": 8, "I(空白)": 9, "J(7月实际)": 10, "K": 11,
}
for label, c in target_cols.items():
    letter = get_column_letter(c)
    print(f"\n--- 列 {letter} ({label}) ---")
    for r in range(1, 41):
        val = ws.cell(row=r, column=c).value
        merged_tag = find_merged(r, c)
        if val is None and not merged_tag:
            print(f"  R{r}: <空>")
            continue
        val_text = "<空>" if val is None else str(val).replace("\n", "\\n")
        tag = f"  [合并:{merged_tag}]" if merged_tag else ""
        print(f"  R{r}: {val_text}{tag}")

print()
print("=" * 80)
print("分析完成")
print("=" * 80)
wb.close()
