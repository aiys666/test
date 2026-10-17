# 全面扫描 Excel 行列结构
import openpyxl
from openpyxl.utils import get_column_letter

SRC = r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\01周一周报整理\权责近两个月的数据预估.xlsx'
wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb['Sheet1']

# 扫描整个sheet，找所有非空单元格
print('=== 所有非空单元格 (前120行) ===')
for r in range(1, 130):
    row_data = {}
    for c in range(1, ws.max_column + 1):
        v = ws.cell(r, c).value
        if v is not None:
            row_data[c] = v
    if row_data:
        parts = []
        for c, v in sorted(row_data.items()):
            letter = get_column_letter(c)
            if isinstance(v, float):
                parts.append(f'{letter}={v:.5f}')
            else:
                parts.append(f'{letter}={repr(v)[:20]}')
        print(f'行{r:3d}: {" | ".join(parts)}')

print()
print('=== 5月区域：行73-130 完整扫描 ===')
for r in range(73, 130):
    row_data = {}
    for c in range(1, 49):
        v = ws.cell(r, c).value
        if v is not None:
            row_data[get_column_letter(c)] = v
    if row_data:
        items = [f'{k}={repr(v)[:18]}' for k, v in sorted(row_data.items())]
        print(f'行{r}: {" | ".join(items)}')
