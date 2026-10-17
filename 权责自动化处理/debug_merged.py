# 深度分析 Excel 合并单元格结构
import openpyxl
from openpyxl.utils import get_column_letter

SRC = r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\01周一周报整理\权责近两个月的数据预估.xlsx'
wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb['Sheet1']

print('=== 合并单元格范围（按行列排序）===')
merged_ranges = sorted(ws.merged_cells.ranges, key=lambda x: (x.min_row, x.min_col))
for mr in merged_ranges:
    top_val = ws.cell(mr.min_row, mr.min_col).value
    print(f'  {mr}  =>  起始值: {repr(top_val)}')

print()
print(f'=== Sheet1 数据维度: {ws.max_row}行 x {ws.max_column}列 ===')

print()
print('=== 前25行原始数据 (B-L列) ===')
print(f'{"行":<4} {"B(日期)":<12} {"C":<8} {"D":<8} {"E":<8} {"F(产品)":<10} {"G":<8} {"H":<8} {"I":<8} {"J(进件)":<10} {"K":<8} {"L":<8}')
for r in range(1, 26):
    vals = {c: ws.cell(r, c).value for c in range(2, 13)}
    def f(v):
        if v is None: return '-'
        if isinstance(v, float): return f'{v:.4f}'
        return str(v)[:12]
    print(f'{r:<4} {f(vals[2]):<12} {f(vals[3]):<8} {f(vals[4]):<8} {f(vals[5]):<8} {f(vals[6]):<10} {f(vals[7]):<8} {f(vals[8]):<8} {f(vals[9]):<8} {f(vals[10]):<10} {f(vals[11]):<8} {f(vals[12]):<8}')

print()
print('=== 5月区域（搜索5月行）===')
for r in range(1, ws.max_row + 1):
    v = ws.cell(r, 6).value
    if v and ('5' in str(v) or '05' in str(v) or '2026-05' in str(v)):
        print(f'  行{r}: F={repr(v)}, B={repr(ws.cell(r,2).value)}, C={repr(ws.cell(r,3).value)}')
        for c2 in range(1, 30):
            cv = ws.cell(r, c2).value
            if cv is not None:
                print(f'    {get_column_letter(c2)}({c2}): {repr(cv)}')
        print()
        if r > 100:
            break
