# -*- coding: utf-8 -*-
"""生成「月度偏差归因」Excel 模板"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

wb = openpyxl.Workbook()

bold = Font(bold=True, name='微软雅黑', size=11)
title_font = Font(bold=True, name='微软雅黑', size=13, color='FFFFFF')
header_fill = PatternFill('solid', fgColor='4472C4')
header_font = Font(bold=True, name='微软雅黑', size=10, color='FFFFFF')
input_fill = PatternFill('solid', fgColor='FFF2CC')
calc_fill = PatternFill('solid', fgColor='E2EFDA')
sec_fill = PatternFill('solid', fgColor='D6E4F0')
thin = Border(*[Side(style='thin', color='BFBFBF')] * 4)
center = Alignment(horizontal='center', vertical='center')
note_font = Font(name='微软雅黑', size=9, color='808080')


def style_cell(cell, font=None, fill=None, align=None):
    if font:
        cell.font = font
    if fill:
        cell.fill = fill
    if align:
        cell.alignment = align
    cell.border = thin


# ============ Sheet 1: 偏差归因概览 ============
ws1 = wb.active
ws1.title = '偏差归因概览'

ws1['A1'] = '月度偏差归因概览（黄色=填目标/实际，绿色=自动算）'
ws1['A1'].font = title_font
ws1['A1'].fill = header_fill
ws1.merge_cells('A1:G1')

headers = ['指标', '目标值', '实际值', '偏差额', '偏差%', '偏差方向', '归因提示']
for i, h in enumerate(headers, 1):
    c = ws1.cell(row=3, column=i, value=h)
    style_cell(c, header_font, header_fill, center)

# 每个指标：label, 是否输入, D列公式, E列公式, F列公式, G列提示
indicators = [
    ('首贷', 'section'),
    ('  首贷笔数', 'input'),
    ('  首贷件均', 'input'),
    ('  首贷成交金额', 'input'),
    ('  首贷息费率', 'input'),
    ('  首贷坏账率', 'input'),
    ('复贷', 'section'),
    ('  复贷笔数', 'input'),
    ('  复贷件均', 'input'),
    ('  复贷成交金额', 'input'),
    ('  复贷息费率', 'input'),
    ('  复贷坏账率', 'input'),
    ('整体', 'section'),
    ('  整体成交金额', 'input'),
    ('  获客成本', 'input'),
    ('  整体经营利润率', 'input'),
    ('  整体经营利润', 'input'),
]

r = 4
for label, typ in indicators:
    if typ == 'section':
        c = ws1.cell(row=r, column=1, value=label)
        style_cell(c, bold, sec_fill)
        for col in range(2, 8):
            style_cell(ws1.cell(row=r, column=col), None, sec_fill)
    else:
        ws1.cell(row=r, column=1, value=label)
        # B=目标, C=实际 填黄色
        style_cell(ws1.cell(row=r, column=2), None, input_fill, center)
        style_cell(ws1.cell(row=r, column=3), None, input_fill, center)
        # D=偏差额 = B-C
        style_cell(ws1.cell(row=r, column=4, value=f'=B{r}-C{r}'), None, calc_fill, center)
        # E=偏差% = D/B
        style_cell(ws1.cell(row=r, column=5, value=f'=IF(B{r}=0,0,D{r}/B{r})'), None, calc_fill, center)
        # F=偏差方向
        style_cell(ws1.cell(row=r, column=6,
                    value=f'=IF(D{r}>0,"↑超",IF(D{r}<0,"↓差","平"))'), None, calc_fill, center)
    r += 1

# 底部说明
ws1.cell(row=r + 1, column=1, value='说明：偏差额=目标-实际；正值=实际优于目标，负值=实际差于目标').font = note_font

ws1.column_dimensions['A'].width = 20
for col in ['B', 'C', 'D', 'E']:
    ws1.column_dimensions[col].width = 14
ws1.column_dimensions['F'].width = 10
ws1.column_dimensions['G'].width = 30

# ============ Sheet 2: 量价拆解 ============
ws2 = wb.create_sheet('量价拆解')

ws2['A1'] = '成交金额偏差 = 量效应（笔数）+ 价效应（件均）'
ws2['A1'].font = title_font
ws2['A1'].fill = header_fill
ws2.merge_cells('A1:H1')

ws2['A3'] = '原理：成交金额 = 笔数 × 件均，偏差拆成「量」和「价」两部分'
ws2['A3'].font = Font(italic=True, name='微软雅黑', size=9)

headers2 = ['业务', '目标笔数', '实际笔数', '目标件均', '实际件均', '量效应', '价效应', '总偏差']
for i, h in enumerate(headers2, 1):
    style_cell(ws2.cell(row=5, column=i, value=h), header_font, header_fill, center)

for r, label in [(6, '首贷'), (7, '复贷')]:
    ws2.cell(row=r, column=1, value=label).font = bold
    for col in range(2, 6):
        style_cell(ws2.cell(row=r, column=col), None, input_fill, center)
    # 量效应 = (实际笔数-目标笔数) × 目标件均
    style_cell(ws2.cell(row=r, column=6, value=f'=(C{r}-B{r})*D{r}'), None, calc_fill, center)
    # 价效应 = (实际件均-目标件均) × 实际笔数
    style_cell(ws2.cell(row=r, column=7, value=f'=(E{r}-D{r})*C{r}'), None, calc_fill, center)
    # 总偏差 = 实际成交 - 目标成交
    style_cell(ws2.cell(row=r, column=8, value=f'=C{r}*E{r}-B{r}*D{r}'), None, calc_fill, center)

ws2.cell(row=9, column=1, value='判断：|量效应| > |价效应| → 问题在笔数；反之在件均').font = note_font

for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
    ws2.column_dimensions[col].width = 13

# ============ Sheet 3: 利润偏差桥 ============
ws3 = wb.create_sheet('利润偏差桥')

ws3['A1'] = '利润偏差桥（从目标利润走到实际利润）'
ws3['A1'].font = title_font
ws3['A1'].fill = header_fill
ws3.merge_cells('A1:C1')

ws3['A3'] = '逻辑：目标利润 + 各驱动因素偏差 = 实际利润'
ws3['A3'].font = Font(italic=True, name='微软雅黑', size=9)

headers3 = ['驱动因素', '偏差贡献', '说明']
for i, h in enumerate(headers3, 1):
    style_cell(ws3.cell(row=5, column=i, value=h), header_font, header_fill, center)

bridge = [
    ('起点：目标利润', 'input', '填目标整体经营利润（万美元）'),
    ('放款额偏差贡献', 'input', '=Δ成交金额 × 目标利润率'),
    ('息费率偏差贡献', 'input', '=Δ息费率 × 实际成交金额'),
    ('坏账率偏差贡献', 'input', '=Δ坏账率 × 实际成交金额（符号取负）'),
    ('获客成本偏差', 'input', '=实际获客成本 - 目标获客成本'),
    ('运营成本偏差', 'input', '=实际运营成本 - 目标运营成本'),
    ('终点：实际利润', 'calc', '= 上面 6 项累加'),
]

r = 6
for label, typ, note in bridge:
    ws3.cell(row=r, column=1, value=label).font = bold
    if typ == 'input':
        style_cell(ws3.cell(row=r, column=2), None, input_fill, center)
    else:
        style_cell(ws3.cell(row=r, column=2, value=f'=SUM(B6:B{r-1})'), None, calc_fill, center)
    ws3.cell(row=r, column=3, value=note).font = note_font
    r += 1

ws3.column_dimensions['A'].width = 22
ws3.column_dimensions['B'].width = 14
ws3.column_dimensions['C'].width = 42

out = r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\8月预估\月度偏差归因模板.xlsx'
wb.save(out)
print(f'已生成: {out}')
