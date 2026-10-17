import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

wb = openpyxl.load_workbook(r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\墨西哥周报达成跟进.xlsx', data_only=False)
ws = wb['Sheet1']

print('=== 冻结窗格 ===')
print(ws.freeze_panes)

print('\n=== 合并单元格 (前30个) ===')
for i, mc in enumerate(ws.merged_cells.ranges):
    if i >= 30:
        break
    print(mc)

print('\n=== 列宽 ===')
for col in 'ABCDEFGHIJKLMNOPQRST':
    cd = ws.column_dimensions.get(col)
    if cd:
        print(f'{col}: width={cd.width}')

print('\n=== 行高 ===')
for r in range(1, 50):
    rd = ws.row_dimensions.get(r)
    if rd:
        print(f'R{r}: height={rd.height}')

print('\n=== R1:R5 内容 ===')
for r in range(1, 6):
    vals = [ws.cell(r, c).value for c in range(1, 12)]
    print(f'R{r}: {vals}')

print('\n=== R2 表头样式 ===')
for c in range(1, 15):
    cell = ws.cell(2, c)
    fg = cell.fill.start_color
    fg_rgb = fg.rgb if fg and hasattr(fg, 'rgb') else None
    print(f'C{c}({cell.column_letter}): value={cell.value} | font={cell.font.name},{cell.font.size},bold={cell.font.bold} | fill={fg_rgb} | align={cell.alignment.horizontal},{cell.alignment.vertical}')

print('\n=== R3 数据行样式 ===')
for c in range(1, 10):
    cell = ws.cell(3, c)
    fg = cell.fill.start_color
    fg_rgb = fg.rgb if fg and hasattr(fg, 'rgb') else None
    print(f'C{c}({cell.column_letter}): value={cell.value} | font={cell.font.name},{cell.font.size},bold={cell.font.bold} | fill={fg_rgb} | align={cell.alignment.horizontal},{cell.alignment.vertical}')

print('\n=== 日实际区块 (R40起) ===')
for r in range(40, 50):
    vals = [ws.cell(r, c).value for c in range(1, 8)]
    print(f'R{r}: {vals}')

print('\n=== Sheet2 格式 ===')
ws2 = wb['Sheet2']
print(f'列宽: {[(col, ws2.column_dimensions.get(col).width) for col in "ABCDEFGHIJKLMNOPQRST" if ws2.column_dimensions.get(col)]}')
print(f'R1 样式: font={ws2.cell(1,1).font.bold}, fill={ws2.cell(1,1).fill.start_color.rgb if ws2.cell(1,1).fill.start_color else None}')
print(f'冻结: {ws2.freeze_panes}')
