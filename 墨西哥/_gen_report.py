# -*- coding: utf-8 -*-
"""生成 8/3→8/10 逾期率上涨归因分析报告（美化 Excel）· 修正版

数据源：_decomp_result_0803_0810.csv（逐维度 Kitagawa 分解，122维度×2口径，共1918行group）
全市场锚定：「是否转产线」维度完整覆盖全市场，两期合计与源表一致，作为全市场基准分解。
"""
import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import CellIsRule

# ── 样式常量 ──────────────────────────────────────────
TITLE_FONT = Font(name='微软雅黑', size=16, bold=True, color='1F3864')
H1_FONT = Font(name='微软雅黑', size=13, bold=True, color='FFFFFF')
H2_FONT = Font(name='微软雅黑', size=11, bold=True, color='1F3864')
BODY_FONT = Font(name='微软雅黑', size=10)
BOLD_FONT = Font(name='微软雅黑', size=10, bold=True)
NOTE_FONT = Font(name='微软雅黑', size=9, italic=True, color='7F7F7F')

H1_FILL = PatternFill('solid', fgColor='1F3864')
H2_FILL = PatternFill('solid', fgColor='D6E4F0')
HEAD_FILL = PatternFill('solid', fgColor='2E5B9F')
GREEN_FILL = PatternFill('solid', fgColor='C6EFCE')
RED_FILL = PatternFill('solid', fgColor='FFC7CE')
AMBER_FILL = PatternFill('solid', fgColor='FFE699')
LIGHT_FILL = PatternFill('solid', fgColor='F2F2F2')

THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
RIGHT = Alignment(horizontal='right', vertical='center')


def style_header_row(ws, row, cols):
    for c in range(1, cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEAD_FILL
        cell.font = Font(name='微软雅黑', size=10, bold=True, color='FFFFFF')
        cell.alignment = CENTER
        cell.border = BORDER


def write_title(ws, text, span):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=span)
    c = ws.cell(row=1, column=1, value=text)
    c.font = TITLE_FONT
    c.alignment = Alignment(horizontal='left', vertical='center')
    ws.row_dimensions[1].height = 30


def write_note(ws, row, text, span):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    c = ws.cell(row=row, column=1, value=text)
    c.font = NOTE_FONT
    c.alignment = LEFT


def write_h1(ws, r, text, span):
    ws.cell(row=r, column=1, value=text).font = H1_FONT
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=span)
    for c in range(1, span + 1):
        ws.cell(row=r, column=c).fill = H1_FILL
    ws.row_dimensions[r].height = 22
    return r + 1


# ── 读取分解结果 ──────────────────────────────────────
full = pd.read_csv(r'e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_decomp_result_0803_0810.csv')
full['rate_diff'] = full['comp_rate'] - full['base_rate']
full['share_diff'] = full['comp_share'] - full['base_share']
N_DIMS = full['dim_name'].nunique()

# 全市场锚定：取「是否转产线」维度（完整覆盖全市场）
anchor = full[full['dim_name'] == '是否转产线']

def _agg(df, ncol, ocol):
    return float(df[ncol].sum()), float(df[ocol].sum())

market = {}
for basis in ['笔数', '金额']:
    s = anchor[anchor['basis'] == basis]
    if basis == '笔数':
        b_n, b_o = _agg(s, 'base_n', 'base_o')
        c_n, c_o = _agg(s, 'comp_n', 'comp_o')
    else:
        b_n, b_o = _agg(s, 'base_n', 'base_o')
        c_n, c_o = _agg(s, 'comp_n', 'comp_o')
    market[basis] = dict(b_n=b_n, c_n=c_n, b_o=b_o, c_o=c_o,
                         b_r=b_o / b_n, c_r=c_o / c_n,
                         change=(c_o / c_n) - (b_o / b_n))


def decomp_summary(basis):
    """用「是否转产线」维度（完整覆盖）做基准分解汇总。"""
    s = anchor[anchor['basis'] == basis]
    tot = s['dim_total_change'].iloc[0]
    ind = s['individual'].sum()
    stru = s['structural'].sum()
    inter = s['interaction'].sum()
    return tot, ind, stru, inter


# 122维度的稳健性佐证：统计「个体效应≥自身总变化90%」的维度占比与结构效应占比中位数
def median_pct(basis):
    s = full[full['basis'] == basis]
    grp = s.groupby('dim_name').agg(
        ind=('individual', 'sum'), stru=('structural', 'sum'),
        inter=('interaction', 'sum'), dtc=('dim_total_change', 'first'))
    valid = grp[grp['dtc'].abs() > 0.01]
    dom = (valid['ind'] >= 0.9 * valid['dtc']).mean() * 100
    med_stru = (valid['stru'] / valid['dtc'] * 100).median()
    return dom, med_stru


wb = Workbook()

# ============ Sheet1 概览与结论 ============
ws = wb.active
ws.title = '概览与结论'
write_title(ws, '墨西哥逾期率上涨归因分析 · 2026-08-03 → 2026-08-10（修正版）', 8)
write_note(ws, 2, '分析对象：T0逾期率（放款后首个还款日逾期）。口径：逐维度 Kitagawa 效应分解（个体效应 + 结构效应 + 交互效应）。数据源：全量重建结果表，无测试过滤。', 8)

r = write_h1(ws, 4, '一、核心结论', 8)

conclusions = [
    ('1', '逾期率上升是“全面系统性普涨”，个体效应绝对主导',
     '以完整覆盖全市场的「是否转产线」维度做基准分解：个体效应占笔数 +2.885pp / 金额 +3.856pp（≈100%~104%），说明几乎每个分组、每个维度切片的逾期率都在同步上升，没有出现“个别高风险客群集中爆雷”。122 个有效维度中，93% 的维度个体效应超过其自身总变化，结构效应中位数≈0，进一步佐证普涨性质。'),
    ('2', '客群结构没有向高风险偏移，反而轻微改善',
     '结构效应为负（笔数 -0.151pp / 金额 -0.194pp），即放款客群的占比结构在往有利方向微调，并未推高整体逾期率；交互效应仅为 +0.03pp / +0.21pp。'),
    ('3', '最重要的结构性风险：转产线客群快速扩张且自身恶化快于全市场',
     '「转产线」组占比：笔数 28.0%→32.1%（+4.1pp）、金额 33.0%→39.2%（+6.2pp）；逾期率：笔数 26.9%→30.3%（+3.41pp）、金额 22.2%→28.3%（+6.09pp），金额口径恶化速度远超全市场（+3.87pp）。因其绝对率仍低于未转产线客群，对整体率的结构效应为负——但该客群扩张+恶化双重叠加，是唯一清晰的结构性风险源，需重点盯防。'),
    ('4', '产品等级升级路径存在小样本超额恶化',
     '金额口径下部分升级路径逾期率跳升显著：C_07_04_00_75→B_07_03_00_60 为 +23.7pp、C_07_04_00_75→B_07_04_00_75 为 +23.4pp、上期产品等级 C_07_04_00_75 为 +21.4pp；但单路径绝对规模有限（约 10~20 万金额，占全市场 <1%），对总变化贡献有限，属策略层面的警示信号。'),
]
for no, head, body in conclusions:
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
    c = ws.cell(row=r, column=1, value=f'结论{no}：{head}')
    c.font = BOLD_FONT
    c.fill = H2_FILL
    ws.merge_cells(start_row=r + 1, start_column=1, end_row=r + 1, end_column=8)
    b = ws.cell(row=r + 1, column=1, value=body)
    b.font = BODY_FONT
    b.alignment = LEFT
    ws.row_dimensions[r + 1].height = 40
    r += 3

# 关键数字表
r += 1
r = write_h1(ws, r, '二、关键数字（全市场锚定）', 8)

kpi_headers = ['口径', '基期出账', '对比期出账', '基期逾期率', '对比期逾期率', '总变化(pp)', '定性判断', '注']
for j, h in enumerate(kpi_headers, 1):
    ws.cell(row=r, column=j, value=h)
style_header_row(ws, r, 8)
r += 1

kpi_rows = [
    ('笔数', f"{market['笔数']['b_n']:,.0f}", f"{market['笔数']['c_n']:,.0f}",
     f"{market['笔数']['b_r']*100:.2f}%", f"{market['笔数']['c_r']*100:.2f}%",
     f"{market['笔数']['change']*100:+.2f}", '全面普涨', '个体效应主导'),
    ('金额', f"{market['金额']['b_n']:,.0f}", f"{market['金额']['c_n']:,.0f}",
     f"{market['金额']['b_r']*100:.2f}%", f"{market['金额']['c_r']*100:.2f}%",
     f"{market['金额']['change']*100:+.2f}", '全面普涨', '个体效应主导'),
]
for row in kpi_rows:
    for j, v in enumerate(row, 1):
        cell = ws.cell(row=r, column=j, value=v)
        cell.font = BOLD_FONT if j in (4, 5, 6) else BODY_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1

# 分析过程
r += 1
r = write_h1(ws, r, '三、分析过程', 8)

steps = [
    '① 数据源：22.sql 全量重建结果表 mx.tmp_effect_decomp_all_dims（122 维度 × 7周），取 08-03 与 08-10 两周，共 1918 行 group。',
    '② 结果表是「同一批客群 × 122 个字段」的展开，每个字段的覆盖率不同；其中「是否转产线」字段无空值、完整覆盖全市场（两期合计与源表一致），作为全市场基准分解。',
    '③ 对每个维度（dim_name）分别做分组，计算两期各组出账笔数/金额、逾期笔数/金额、逾期率、占比（组内占比=组出账/该维度总出账）。',
    '④ Kitagawa 分解：个体效应=基期占比×(对比期率-基期率)；结构效应=基期率×(对比期占比-基期占比)；交互效应=率差×占比差；三类效应之和恒等于维度总率变化。',
    '⑤ 过滤小样本（base_n、comp_n 均 > 2000 或对应金额规模），定位超额恶化的具体分组；专项下钻「转产线客群」与「产品等级升级路径」。',
]
for s in steps:
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
    c = ws.cell(row=r, column=1, value=s)
    c.font = BODY_FONT
    c.alignment = LEFT
    ws.row_dimensions[r].height = 18
    r += 1

for col, w in zip('ABCDEFGH', [22, 16, 16, 14, 14, 14, 14, 14]):
    ws.column_dimensions[col].width = w
ws.sheet_view.showGridLines = False

# ============ Sheet2 效应分解汇总 ============
ws2 = wb.create_sheet('效应分解汇总')
write_title(ws2, '三类效应分解汇总（判断上涨性质）', 10)
write_note(ws2, 2, '以完整覆盖全市场的「是否转产线」维度做基准分解；另给出 122 维度中「个体效应主导」的维度占比与结构效应占比中位数作为稳健性佐证。', 10)
r = 3
headers = ['口径', '总变化(pp)', '个体效应合计(pp)', '个体效应占比', '结构效应合计(pp)', '结构效应占比', '交互效应合计(pp)', '交互效应占比', '性质判断', '解读']
for j, h in enumerate(headers, 1):
    ws2.cell(row=r, column=j, value=h)
style_header_row(ws2, r, 10)
r += 1

for basis in ['笔数', '金额']:
    tot, ind, stru, inter = decomp_summary(basis)
    dom, med_stru = median_pct(basis)
    nature = '全面普涨'
    note = f'个体效应主导；122 维度中个体效应≥自身总变化90%的维度占 {dom:.0f}%（结构效应占比中位数 {med_stru:+.1f}%）'
    vals = [basis, f'{tot*100:+.4f}', f'{ind*100:+.4f}', f'{ind/tot*100:+.1f}%',
            f'{stru*100:+.4f}', f'{stru/tot*100:+.1f}%', f'{inter*100:+.4f}', f'{inter/tot*100:+.1f}%', nature, note]
    for j, v in enumerate(vals, 1):
        cell = ws2.cell(row=r, column=j, value=v)
        cell.font = BOLD_FONT if j in (2, 9) else BODY_FONT
        cell.alignment = CENTER if j < 9 else LEFT
        cell.border = BORDER
    r += 1

r += 1
ws2.cell(row=r, column=1, value='解读：').font = H2_FONT
r += 1
ws2.merge_cells(start_row=r, start_column=1, end_row=r, end_column=10)
ws2.cell(row=r, column=1, value='个体效应≈100%（结构效应为负、交互效应接近 0）→ 逾期率上升是普遍现象（各分组同步恶化），不是高风险客群占比扩张导致。应关注系统性因素（宏观/资金成本/放款策略整体收紧/账期错配等），而非单一客群。').font = BODY_FONT
ws2.cell(row=r, column=1).alignment = LEFT

for col, w in zip('ABCDEFGHIJ', [12, 14, 18, 16, 18, 16, 18, 16, 12, 40]):
    ws2.column_dimensions[col].width = w
ws2.sheet_view.showGridLines = False

# ============ Sheet3 转产线专项 ============
ws3 = wb.create_sheet('转产线专项')
write_title(ws3, '转产线客群：快速扩张 + 自身恶化快于全市场（重点盯防）', 13)
write_note(ws3, 2, '「是否转产线」维度完整覆盖全市场。转产线客群占比显著上升，且金额口径恶化速度远超全市场；但因绝对率仍低于未转产线客群，对整体率的结构效应为负。', 13)
r = 4
for basis in ['笔数', '金额']:
    s = anchor[anchor['basis'] == basis]
    tot, ind, stru, inter = decomp_summary(basis)
    ws3.cell(row=r, column=1, value=f'【{basis}口径】总变化 {tot*100:+.2f}pp（个体 {ind*100:+.2f} / 结构 {stru*100:+.2f} / 交互 {inter*100:+.2f}）').font = H2_FONT
    r += 1
    headers = ['分组', '基期出账', '对比期出账', '基期逾期率', '对比期逾期率', '率差(pp)', '基期占比', '对比期占比', '占比差(pp)', '个体效应(pp)', '结构效应(pp)', '交互效应(pp)']
    for j, h in enumerate(headers, 1):
        ws3.cell(row=r, column=j, value=h)
    style_header_row(ws3, r, 12)
    r += 1
    for _, row in s.iterrows():
        vals = [row['dim_group'], row['base_n'], row['comp_n'],
                f"{row['base_rate']*100:.2f}%", f"{row['comp_rate']*100:.2f}%", f"{row['rate_diff']*100:+.2f}",
                f"{row['base_share']*100:.2f}%", f"{row['comp_share']*100:.2f}%", f"{row['share_diff']*100:+.2f}",
                f"{row['individual']*100:+.4f}", f"{row['structural']*100:+.4f}", f"{row['interaction']*100:+.4f}"]
        for j, v in enumerate(vals, 1):
            cell = ws3.cell(row=r, column=j, value=v)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = CENTER if j == 1 else RIGHT
            if j in (2, 3):
                cell.number_format = '#,##0'
        r += 1
    r += 1

for col, w in zip('ABCDEFGHIJKLM', [18, 16, 16, 14, 14, 12, 12, 12, 12, 16, 16, 16]):
    ws3.column_dimensions[col].width = w
ws3.sheet_view.showGridLines = False

# ============ Sheet4 产品等级升级路径专项 ============
ws4 = wb.create_sheet('产品等级升级路径')
write_title(ws4, '产品等级升级路径：小样本超额恶化（策略警示）', 13)
write_note(ws4, 2, '金额口径，按率差降序取 Top20，且两组规模均 > 10 万（金额）。绝对占比极小，对总变化贡献有限，但升级后率跳升明显，需策略层确认。', 13)
r = 4
prod_dims = ['产品等级', '上期产品等级', '产品等级变化']
s = full[(full['basis'] == '金额') & (full['dim_name'].isin(prod_dims))]
s = s[(s['base_n'] > 100000) & (s['comp_n'] > 100000)]
s = s.reindex(s['rate_diff'].sort_values(ascending=False).index).head(20)
headers = ['维度', '分组', '基期金额', '对比期金额', '基期逾期率', '对比期逾期率', '率差(pp)', '基期占比', '对比期占比', '占比差(pp)', '个体效应(pp)', '结构效应(pp)', '交互效应(pp)']
for j, h in enumerate(headers, 1):
    ws4.cell(row=r, column=j, value=h)
style_header_row(ws4, r, 13)
r += 1
for _, row in s.iterrows():
    vals = [row['dim_name'], row['dim_group'], row['base_n'], row['comp_n'],
            f"{row['base_rate']*100:.2f}%", f"{row['comp_rate']*100:.2f}%", f"{row['rate_diff']*100:+.2f}",
            f"{row['base_share']*100:.2f}%", f"{row['comp_share']*100:.2f}%", f"{row['share_diff']*100:+.2f}",
            f"{row['individual']*100:+.4f}", f"{row['structural']*100:+.4f}", f"{row['interaction']*100:+.4f}"]
    for j, v in enumerate(vals, 1):
        cell = ws4.cell(row=r, column=j, value=v)
        cell.font = BODY_FONT
        cell.border = BORDER
        cell.alignment = LEFT if j == 2 else (RIGHT if j >= 3 else CENTER)
        if j in (3, 4):
            cell.number_format = '#,##0'
    r += 1

for col, w in zip('ABCDEFGHIJKLM', [14, 30, 16, 16, 14, 14, 12, 12, 12, 12, 16, 16, 16]):
    ws4.column_dimensions[col].width = w
ws4.sheet_view.showGridLines = False

# ============ Sheet5 规模可观且率差最大分组 ============
ws5 = wb.create_sheet('率高风险分组')
write_title(ws5, '规模可观且率差最大的分组（超额恶化定位）', 12)
write_note(ws5, 2, '笔数口径：两组均 > 2000 笔；金额口径：两组均 > 10 万。按率差降序 Top15。', 12)
r = 4
for basis, thr in [('笔数', 2000), ('金额', 100000)]:
    s = full[full['basis'] == basis]
    s = s[(s['base_n'] > thr) & (s['comp_n'] > thr)]
    s = s.reindex(s['rate_diff'].sort_values(ascending=False).index).head(15)
    ws5.cell(row=r, column=1, value=f'【{basis}口径】').font = H2_FONT
    r += 1
    headers = ['维度', '分组', '基期出账', '对比期出账', '基期逾期率', '对比期逾期率', '率差(pp)', '基期占比', '对比期占比', '个体效应(pp)', '结构效应(pp)', '交互效应(pp)']
    for j, h in enumerate(headers, 1):
        ws5.cell(row=r, column=j, value=h)
    style_header_row(ws5, r, 12)
    r += 1
    for _, row in s.iterrows():
        vals = [row['dim_name'], row['dim_group'], row['base_n'], row['comp_n'],
                f"{row['base_rate']*100:.2f}%", f"{row['comp_rate']*100:.2f}%", f"{row['rate_diff']*100:+.2f}",
                f"{row['base_share']*100:.2f}%", f"{row['comp_share']*100:.2f}%",
                f"{row['individual']*100:+.4f}", f"{row['structural']*100:+.4f}", f"{row['interaction']*100:+.4f}"]
        for j, v in enumerate(vals, 1):
            cell = ws5.cell(row=r, column=j, value=v)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = LEFT if j == 2 else (RIGHT if j >= 3 else CENTER)
            if j in (3, 4):
                cell.number_format = '#,##0'
        r += 1
    r += 1

for col, w in zip('ABCDEFGHIJKL', [16, 26, 14, 14, 12, 12, 12, 12, 12, 14, 14, 14]):
    ws5.column_dimensions[col].width = w
ws5.sheet_view.showGridLines = False

# ============ Sheet6 全量明细 ============
ws6 = wb.create_sheet('全量明细')
nrows = len(full)
write_title(ws6, f'全部维度分组 Kitagawa 分解明细（{nrows} 行 = {N_DIMS} 维度 × 2 口径展开）', 18)
r = 3
headers = ['口径', '维度', '分组', '基期出账', '对比期出账', '基期逾期率', '对比期逾期率', '率差(pp)', '基期占比', '对比期占比', '占比差(pp)', '个体效应(pp)', '结构效应(pp)', '交互效应(pp)', '总效应(pp)', '维度总变化(pp)']
for j, h in enumerate(headers, 1):
    ws6.cell(row=r, column=j, value=h)
style_header_row(ws6, r, len(headers))
r += 1

for _, row in full.sort_values(['basis', 'dim_name', 'individual'], ascending=[True, True, False]).iterrows():
    vals = [row['basis'], row['dim_name'], row['dim_group'], row['base_n'], row['comp_n'],
            f"{row['base_rate']*100:.2f}%", f"{row['comp_rate']*100:.2f}%", f"{row['rate_diff']*100:+.2f}",
            f"{row['base_share']*100:.2f}%", f"{row['comp_share']*100:.2f}%", f"{row['share_diff']*100:+.2f}",
            f"{row['individual']*100:+.4f}", f"{row['structural']*100:+.4f}", f"{row['interaction']*100:+.4f}",
            f"{row['total_effect']*100:+.4f}", f"{row['dim_total_change']*100:+.4f}"]
    for j, v in enumerate(vals, 1):
        cell = ws6.cell(row=r, column=j, value=v)
        cell.font = BODY_FONT
        cell.border = BORDER
        if j == 1:
            cell.alignment = CENTER
        elif j in (2, 3):
            cell.alignment = LEFT
        elif j in (4, 5):
            cell.alignment = RIGHT
            cell.number_format = '#,##0'
        else:
            cell.alignment = RIGHT
    r += 1

ws6.freeze_panes = 'A4'
ws6.auto_filter.ref = f'A3:P{r-1}'
last = r - 1
ws6.conditional_formatting.add(f'H4:H{last}', CellIsRule(operator='greaterThan', formula=['5'], fill=RED_FILL, font=Font(color='9C0006')))
for col, w in zip('ABCDEFGHIJKLMNOP', [8, 16, 20, 12, 12, 11, 11, 11, 11, 11, 11, 12, 12, 12, 12, 13]):
    ws6.column_dimensions[col].width = w
ws6.sheet_view.showGridLines = False

# ============ Sheet7 与旧结果对比 ============
ws7 = wb.create_sheet('与旧结果对比')
write_title(ws7, '本次结果 vs 旧 xlsx 差异说明', 6)
r = 3
headers = ['对比项', '旧 xlsx（效应分解_2026-08-03_vs_2026-08-10）', '本次（全量重建）', '差异根因']
for j, h in enumerate(headers, 1):
    ws7.cell(row=r, column=j, value=h)
style_header_row(ws7, r, 4)
r += 1

diff_rows = [
    ('数据范围', '带 mid=1040160066607324 测试过滤，每个维度仅 1~2 条测试记录', '全量数据，122 维度 × 7 周，分解结果 1918 行 group', '22.sql 原 SQL 第2批 INSERT 残留测试过滤 AND mid=1040160066607324 与 AND is_t0_window_1 IS NOT NULL'),
    ('基期/对比期出账笔数', '每 sheet 仅 1 笔', '全市场 8081 → 8303 笔', '旧数据被 mid 过滤压缩成极少量测试样本'),
    ('逾期率', '全部为 0（0/1=0）', '笔数 29.51%→32.28%；金额 24.33%→28.19%', '旧样本中无逾期记录，率恒为 0'),
    ('占比', '全部为 100%（1/1）', '真实占比（如转产线组 28.0%→32.1%）', '旧数据每组仅 1 条，分母=分子'),
    ('分解结果', '个体/结构/交互全为 0，无区分度', '个体效应≈100% 主导，结构效应为负，可定位具体恶化分组', '旧数据逾期率与占比无变化，分解失效'),
    ('结论可用性', '不可用（无法归因）', '可用（定性：全面普涨；结构风险：转产线客群扩张+快速恶化）', '—'),
]
for row in diff_rows:
    for j, v in enumerate(row, 1):
        cell = ws7.cell(row=r, column=j, value=v)
        cell.font = BODY_FONT
        cell.alignment = LEFT
        cell.border = BORDER
    ws7.row_dimensions[r].height = 44
    r += 1

r += 1
ws7.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
ws7.cell(row=r, column=1, value="关键动作：本次分析前已删除 22.sql 中第2批 INSERT 块的测试过滤条件 AND mid=1040160066607324 与 AND is_t0_window_1 IS NOT NULL，改为全量 WHERE app_time >= date'2026-08-03'。").font = Font(name='微软雅黑', size=10, bold=True, color='9C0006')
ws7.cell(row=r, column=1).alignment = LEFT

for col, w in zip('ABCD', [16, 46, 46, 46]):
    ws7.column_dimensions[col].width = w
ws7.sheet_view.showGridLines = False

# ── 保存 ──────────────────────────────────────────────
out = r'E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\墨西哥逾期率上涨归因分析_0803_0810_修正版_v2.xlsx'
wb.save(out)
print('报告已生成:', out)
print(f'全市场 笔数: {market["笔数"]["b_r"]*100:.2f}% -> {market["笔数"]["c_r"]*100:.2f}%  (+{market["笔数"]["change"]*100:.2f}pp)')
print(f'全市场 金额: {market["金额"]["b_r"]*100:.2f}% -> {market["金额"]["c_r"]*100:.2f}%  (+{market["金额"]["change"]*100:.2f}pp)')
print(f'分解明细行数: {nrows}')
