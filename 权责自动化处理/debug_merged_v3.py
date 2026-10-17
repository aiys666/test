# 调试: 查看非循环贷区域 (5月) 的原始数据
import openpyxl
from openpyxl.utils import get_column_letter
from datetime import datetime

SRC = r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\01周一周报整理\权责近两个月的数据预估.xlsx'
wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb['Sheet1']

# 收集合并单元格
merged_filled = {}
for mr in ws.merged_cells.ranges:
    top_val = ws.cell(mr.min_row, mr.min_col).value
    for r in range(mr.min_row, mr.max_row + 1):
        for c in range(mr.min_col, mr.max_col + 1):
            merged_filled[(r, c)] = top_val

def gv(row, col):
    if (row, col) in merged_filled:
        return merged_filled[(row, col)]
    return ws.cell(row, col).value

print('=== 5月区域 非循环贷 原始数据 (行104-130) ===')
for r in range(104, 130):
    row_data = {}
    for c in range(1, 30):
        v = gv(r, c)
        if v is not None:
            row_data[get_column_letter(c)] = v
    if row_data:
        items = [f'{k}={repr(v)[:20]}' for k, v in sorted(row_data.items())]
        print(f'行{r}: {" | ".join(items)}')
    else:
        print(f'行{r}: [空行]')
