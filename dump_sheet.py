import sys
sys.stdout.reconfigure(encoding='utf-8')
import openpyxl

wb = openpyxl.load_workbook(r"D:\Documents\Downloads\9月每周4t7预估(覆盖率100%法).xlsx", data_only=False)
ws = wb.active

print(f"最大行={ws.max_row}, 最大列={ws.max_column}")
print("\n=== 完整结构(非空单元格) ===")
for row in range(1, ws.max_row+1):
    # collect non-empty
    cells = []
    for col in range(1, ws.max_column+1):
        v = ws.cell(row, col).value
        if v is not None:
            s = str(v)
            if len(s) > 80:
                s = s[:80] + '...'
            cells.append(f"{openpyxl.utils.get_column_letter(col)}{row}={s}")
    if cells:
        print(f"  r{row}: " + " | ".join(cells))
