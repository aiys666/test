# -*- coding: utf-8 -*-
"""生成「月度偏差归因」填好数据的示例（印尼6月）"""
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
result_fill = PatternFill('solid', fgColor='FCE4D6')  # 橙色=结论
thin = Border(*[Side(style='thin', color='BFBFBF')] * 4)
center = Alignment(horizontal='center', vertical='center')
note_font = Font(name='微软雅黑', size=9, color='808080')
pos_font = Font(name='微软雅黑', size=10, color='008000')
neg_font = Font(name='微软雅黑', size=10, color='FF0000')


def style(cell, font=None, fill=None, align=None):
    if font: cell.font = font
    if fill: cell.fill = fill
    if align: cell.alignment = align
    cell.border = thin


# ============ Sheet 1: 偏差归因概览（填好数据）============
ws1 = wb.active
ws1.title = '偏差归因概览'

ws1['A1'] = '印尼 6月 偏差归因概览（示例）'
ws1['A1'].font = title_font
ws1['A1'].fill = header_fill
ws1.merge_cells('A1:F1')

headers = ['指标', '目标值', '实际值', '偏差额', '偏差%', '方向']
for i, h in enumerate(headers, 1):
    style(ws1.cell(row=3, column=i, value=h), header_font, header_fill, center)

# (label, 目标, 实际) 金额单位=万美元, 比率=小数, 笔数=笔
data = [
    ('首贷', None, None),
    ('  首贷笔数', 30857.14, 25241),
    ('  首贷件均(美元)', 70.0, 105.69),
    ('  首贷成交金额(万)', 216.0, 266.77),
    ('  首贷息费率', 0.2881, 0.2918),
    ('  首贷坏账率', 0.2861, 0.3044),
    ('复贷', None, None),
    ('  复贷笔数', 151690.46, 117697),
    ('  复贷件均(美元)', 137.0, 160.70),
    ('  复贷成交金额(万)', 2078.16, 1891.39),
    ('  复贷息费率', 0.3715, 0.3720),
    ('  复贷坏账率', 0.2146, 0.2234),
    ('整体', None, None),
    ('  整体成交金额(万)', 2294.16, 2158.16),
    ('  获客成本率', 0.25, 0.1338),
    ('  整体经营利润率', 0.0416, 0.0354),
    ('  整体经营利润(万)', 94.67, 76.49),
]

r = 4
for label, target, actual in data:
    if target is None:  # 区块标题
        style(ws1.cell(row=r, column=1, value=label), bold, sec_fill)
        for col in range(2, 7):
            style(ws1.cell(row=r, column=col), None, sec_fill)
    else:
        style(ws1.cell(row=r, column=1, value=label))
        # B=目标, C=实际
        style(ws1.cell(row=r, column=2, value=target), None, input_fill, center)
        style(ws1.cell(row=r, column=3, value=actual), None, input_fill, center)
        # D=偏差额 = B-C
        style(ws1.cell(row=r, column=4, value=f'=B{r}-C{r}'), None, calc_fill, center)
        # E=偏差% = D/B
        c5 = ws1.cell(row=r, column=5, value=f'=IF(B{r}=0,0,D{r}/B{r})')
        style(c5, None, calc_fill, center)
        c5.number_format = '0.0%'
        # F=方向
        style(ws1.cell(row=r, column=6, value=f'=IF(D{r}>0,"↑超",IF(D{r}<0,"↓差","平"))'), None, calc_fill, center)
    r += 1

ws1.cell(row=r+1, column=1, value='说明：偏差额=目标-实际；正=实际优于目标(金额/利润)，负=差于目标；坏账率正偏差=坏账减少(好)').font = note_font

ws1.column_dimensions['A'].width = 22
for col in ['B','C','D']:
    ws1.column_dimensions[col].width = 16
ws1.column_dimensions['E'].width = 10
ws1.column_dimensions['F'].width = 8

# ============ Sheet 2: 量价拆解（填好数据）============
ws2 = wb.create_sheet('量价拆解')
ws2['A1'] = '成交金额偏差 = 量效应 + 价效应（示例）'
ws2['A1'].font = title_font
ws2['A1'].fill = header_fill
ws2.merge_cells('A1:H1')

headers2 = ['业务', '目标笔数', '实际笔数', '目标件均', '实际件均', '量效应(万)', '价效应(万)', '总偏差(万)']
for i, h in enumerate(headers2, 1):
    style(ws2.cell(row=5, column=i, value=h), header_font, header_fill, center)

rows2 = [
    ('首贷', 30857.14, 25241, 70.0, 105.69),
    ('复贷', 151690.46, 117697, 137.0, 160.70),
]
for r, (label, b, c, d, e) in enumerate(rows2, 6):
    style(ws2.cell(row=r, column=1, value=label), bold)
    style(ws2.cell(row=r, column=2, value=b), None, input_fill, center)
    style(ws2.cell(row=r, column=3, value=c), None, input_fill, center)
    style(ws2.cell(row=r, column=4, value=d), None, input_fill, center)
    style(ws2.cell(row=r, column=5, value=e), None, input_fill, center)
    style(ws2.cell(row=r, column=6, value=f'=(C{r}-B{r})*D{r}/10000'), None, calc_fill, center)
    style(ws2.cell(row=r, column=7, value=f'=(E{r}-D{r})*C{r}/10000'), None, calc_fill, center)
    style(ws2.cell(row=r, column=8, value=f'=C{r}*E{r}/10000-B{r}*D{r}/10000'), None, calc_fill, center)

ws2.cell(row=8, column=1, value='洞察：首贷「量跌价涨」金额反超；复贷「量跌价涨」金额仍跌 → 缩量提质').font = bold

for col in ['A','B','C','D','E','F','G','H']:
    ws2.column_dimensions[col].width = 13

# ============ Sheet 3: 利润偏差桥（填好数据）============
ws3 = wb.create_sheet('利润偏差桥')
ws3['A1'] = '整体利润偏差桥（印尼6月示例，单位万美元）'
ws3['A1'].font = title_font
ws3['A1'].fill = header_fill
ws3.merge_cells('A1:C1')

headers3 = ['驱动因素', '偏差贡献(万)', '说明']
for i, h in enumerate(headers3, 1):
    style(ws3.cell(row=5, column=i, value=h), header_font, header_fill, center)

# 利润桥：目标 → 首贷变化 → 复贷变化 → 催收 → 实际
bridge = [
    ('起点：目标整体利润', 94.67, '目标值'),
    ('首贷利润变化', 7.5, '获客成本改善+31 被 坏账恶化-4.9 部分抵消'),
    ('复贷利润变化', -29.8, '坏账恶化-16.7 + 规模-14.8 + 资金-5.7，运营+6.4对冲'),
    ('催收M30+收入变化', 4.1, '催收回款增加'),
    ('终点：实际整体利润', 76.49, '= 上面各项累加'),
]

r = 6
for label, val, note in bridge:
    style(ws3.cell(row=r, column=1, value=label), bold)
    c = ws3.cell(row=r, column=2, value=val)
    if r == 10:  # 终点
        style(c, Font(bold=True, color='FF0000', size=11), result_fill, center)
    elif val < 0:
        style(c, neg_font, calc_fill, center)
    else:
        style(c, pos_font, calc_fill, center)
    ws3.cell(row=r, column=3, value=note).font = note_font
    r += 1

ws3.column_dimensions['A'].width = 24
ws3.column_dimensions['B'].width = 14
ws3.column_dimensions['C'].width = 52

# ============ Sheet 4: 经营结论 ============
ws4 = wb.create_sheet('经营结论')
ws4['A1'] = '印尼 6月 经营结论（示例）'
ws4['A1'].font = title_font
ws4['A1'].fill = header_fill
ws4.merge_cells('A1:B1')

conclusions = [
    ('一句话结论', '利润低于目标18万，实质是「复贷坏账恶化-16.7万 + 成交收缩-14.8万」，被「获客成本改善+31万」部分对冲'),
    ('判断1：风险是最大痛点', '复贷坏账率21.5%→22.3%恶化，贡献一半以上利润缺口 → 优先找风控看复贷客群质量'),
    ('判断2：投放效率在提升', '日投放-34%、获客成本率25%→13.4% → 「缩量」是主动的、健康的，不是被动下滑'),
    ('判断3：资金成本要关注', '资金成本率2.7%→3.0%随利率上行 → 融资端成本在传导到业务端'),
    ('下一步行动', '① 复贷坏账专项分析 ② 保持当前投放效率 ③ 融资成本压降'),
]
r = 3
for title, content in conclusions:
    style(ws4.cell(row=r, column=1, value=title), bold, sec_fill)
    style(ws4.cell(row=r, column=2, value=content))
    ws4.merge_cells(start_row=r, start_column=2, end_row=r, end_column=2)
    r += 1

ws4.column_dimensions['A'].width = 24
ws4.column_dimensions['B'].width = 80

out = r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\8月预估\月度偏差归因示例_印尼6月.xlsx'
wb.save(out)
print(f'已生成: {out}')
