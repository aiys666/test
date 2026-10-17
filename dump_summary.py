import sys
sys.stdout.reconfigure(encoding='utf-8')
import openpyxl

wb = openpyxl.load_workbook(r"D:\Documents\Downloads\9月每周4t7预估(覆盖率100%法).xlsx", data_only=False)
ws = wb.active

lines = []
lines.append(f"最大行={ws.max_row}, 最大列={ws.max_column}")
lines.append("=== 标题区(1-5行) ===")
for row in range(1, 6):
    cells = []
    for col in range(1, ws.max_column+1):
        v = ws.cell(row, col).value
        if v is not None:
            s = str(v)
            if len(s) > 120: s = s[:120]+'...'
            cells.append(f"{openpyxl.utils.get_column_letter(col)}{row}={s}")
    if cells:
        lines.append(f"  r{row}: " + " | ".join(cells))

lines.append("")
lines.append("=== 每周汇总行 + 月聚合区 ===")
for row in range(6, ws.max_row+1):
    a = ws.cell(row,1).value
    b = ws.cell(row,2).value
    # only summary/section rows
    if a is not None and ('汇总' in str(a) or '聚合' in str(a) or '月度' in str(a) or '差额' in str(a) or '对比' in str(a) or '---' in str(a)):
        cells = []
        for col in range(1, ws.max_column+1):
            v = ws.cell(row, col).value
            if v is not None:
                s = str(v)
                if len(s) > 150: s = s[:150]+'...'
                cells.append(f"{openpyxl.utils.get_column_letter(col)}{row}={s}")
        lines.append(f"  r{row}: " + " | ".join(cells))

# Write to file
with open(r"e:\岳松个人文件\嘉银工作内容的整理\code\sheet_dump.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("已写入 sheet_dump.txt")
print("\n".join(lines))
