import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ============================================================
# Load data
# ============================================================
print("加载数据...")
df = pd.read_excel(r"D:\Documents\Downloads\评级产品表现-放款月 (14).xlsx", sheet_name='评级产品表现-放款月')
df['放款月份'] = df['放款月份'].ffill()
df['月份'] = df['放款月份'].astype(str).str[:7]

aug = df[df['月份'] == '2026-08'].copy()
aug = aug[aug['产品'].notna()].copy()
aug = aug[aug['放款笔数'] > 3].copy()

sep = df[df['月份'] == '2026-09'].copy()
sep = sep[sep['产品'].notna()].copy()

# Global average ratios (fallback for products not in Aug)
avg_r_本金_1t0 = (aug['4t7本金逾期率'] / aug['1t0本金逾期率'].replace(0, np.nan)).mean()
avg_r_本金_1t3 = (aug['4t7本金逾期率'] / aug['1t3本金逾期率'].replace(0, np.nan)).mean()
avg_r_本金_2t0 = (aug['4t7本金逾期率'] / aug['2t0本金逾期率'].replace(0, np.nan)).mean()
avg_r_本金_3t0 = (aug['4t7本金逾期率'] / aug['3t0本金逾期率'].replace(0, np.nan)).mean()
avg_r_本金_4t0 = (aug['4t7本金逾期率'] / aug['4t0本金逾期率'].replace(0, np.nan)).mean()
avg_r_息费_1t0 = (aug['4t7息费逾期率_本金分母'] / aug['1t0本金逾期率'].replace(0, np.nan)).mean()
avg_r_息费_1t3 = (aug['4t7息费逾期率_本金分母'] / aug['1t3本金逾期率'].replace(0, np.nan)).mean()
avg_r_息费_2t0 = (aug['4t7息费逾期率_本金分母'] / aug['2t0本金逾期率'].replace(0, np.nan)).mean()
avg_r_息费_3t0 = (aug['4t7息费逾期率_本金分母'] / aug['3t0本金逾期率'].replace(0, np.nan)).mean()
avg_r_息费_4t0 = (aug['4t7息费逾期率_本金分母'] / aug['4t0本金逾期率'].replace(0, np.nan)).mean()

print(f"全局比率: 本金/2t0={avg_r_本金_2t0:.4f}, 本金/4t0={avg_r_本金_4t0:.4f}")

# ============================================================
# Styles
# ============================================================
thin_border = Border(left=Side('thin'), right=Side('thin'), top=Side('thin'), bottom=Side('thin'))
header_fill = PatternFill('solid', fgColor='4472C4')
header_font = Font(name='微软雅黑', size=10, bold=True, color='FFFFFF')
section_fill = PatternFill('solid', fgColor='D9E2F3')
section_font = Font(name='微软雅黑', size=10, bold=True, color='1F4E79')
input_fill = PatternFill('solid', fgColor='FFF2CC')
ratio_fill = PatternFill('solid', fgColor='E2EFDA')
est1_fill = PatternFill('solid', fgColor='FCE4D6')
est2_fill = PatternFill('solid', fgColor='DDEBF7')
est3_fill = PatternFill('solid', fgColor='F2DCDB')
est4_fill = PatternFill('solid', fgColor='E4DFEC')
est5_fill = PatternFill('solid', fgColor='DCE6F1')
final_fill = PatternFill('solid', fgColor='FFF2CC')
actual_fill = PatternFill('solid', fgColor='F2F2F2')
normal_font = Font(name='微软雅黑', size=10)
title_font = Font(name='微软雅黑', size=14, bold=True, color='1F4E79')
note_font = Font(name='微软雅黑', size=9, color='808080', italic=True)
center = Alignment('center', 'center', wrap_text=True)
left_a = Alignment('left', 'center', wrap_text=True)

PCT = '0.0%'
PCT2 = '0.00%'
RATIO = '0.00'
NUM = '#,##0'

# ============================================================
# Workbook
# ============================================================
wb = Workbook()
ws = wb.active
ws.title = '9月4t7预估(公式版)'
ws.sheet_view.showGridLines = False

# ============================================================
# Column layout (46 cols: A-AT)
# A: 产品, B: 9月笔数, C: 9月金额, D: loan_cycle
# E-J: 9月输入(1t0,1t3,2t0,3t0,4t0,总收息)
# K-Q: 8月原始(1t0,1t3,2t0,3t0,4t0,4t7本金,4t7息费)
# R-AA: 8月比率(本金/1t0~4t0, 息费/1t0~4t0)
# AB-AC: 预估①1t0(本金,息费)
# AD-AE: 预估②1t3
# AF-AG: 预估③2t0
# AH-AI: 预估④3t0
# AJ-AK: 预估⑤4t0
# AL: 推荐方法, AM: 最终本金, AN: 最终息费, AO: 最终TR
# AP: 出账笔数, AQ: 覆盖率, AR: 实际本金, AS: 实际息费, AT: 实际TR
# ============================================================
col_defs = [
    ('A', 1, '产品信息', '产品', 18, 'info', input_fill),
    ('B', 2, '产品信息', '9月笔数', 8, 'info', input_fill),
    ('C', 3, '产品信息', '9月金额', 12, 'info', input_fill),
    ('D', 4, '产品信息', 'loan_cycle', 8, 'info', input_fill),

    ('E', 5, '9月输入(原始)', '9月1t0', 8, 'sep_input', input_fill),
    ('F', 6, '9月输入(原始)', '9月1t3', 8, 'sep_input', input_fill),
    ('G', 7, '9月输入(原始)', '9月2t0', 8, 'sep_input', input_fill),
    ('H', 8, '9月输入(原始)', '9月3t0', 8, 'sep_input', input_fill),
    ('I', 9, '9月输入(原始)', '9月4t0', 8, 'sep_input', input_fill),
    ('J', 10, '9月输入(原始)', '9月总收息', 8, 'sep_input', input_fill),

    ('K', 11, '8月原始数据', '8月1t0', 8, 'aug_raw', input_fill),
    ('L', 12, '8月原始数据', '8月1t3', 8, 'aug_raw', input_fill),
    ('M', 13, '8月原始数据', '8月2t0', 8, 'aug_raw', input_fill),
    ('N', 14, '8月原始数据', '8月3t0', 8, 'aug_raw', input_fill),
    ('O', 15, '8月原始数据', '8月4t0', 8, 'aug_raw', input_fill),
    ('P', 16, '8月原始数据', '8月4t7本金', 8, 'aug_raw', input_fill),
    ('Q', 17, '8月原始数据', '8月4t7息费', 8, 'aug_raw', input_fill),

    ('R', 18, '8月比率(公式)', '本金/1t0', 7, 'aug_ratio', ratio_fill),
    ('S', 19, '8月比率(公式)', '本金/1t3', 7, 'aug_ratio', ratio_fill),
    ('T', 20, '8月比率(公式)', '本金/2t0', 7, 'aug_ratio', ratio_fill),
    ('U', 21, '8月比率(公式)', '本金/3t0', 7, 'aug_ratio', ratio_fill),
    ('V', 22, '8月比率(公式)', '本金/4t0', 7, 'aug_ratio', ratio_fill),
    ('W', 23, '8月比率(公式)', '息费/1t0', 7, 'aug_ratio', ratio_fill),
    ('X', 24, '8月比率(公式)', '息费/1t3', 7, 'aug_ratio', ratio_fill),
    ('Y', 25, '8月比率(公式)', '息费/2t0', 7, 'aug_ratio', ratio_fill),
    ('Z', 26, '8月比率(公式)', '息费/3t0', 7, 'aug_ratio', ratio_fill),
    ('AA', 27, '8月比率(公式)', '息费/4t0', 7, 'aug_ratio', ratio_fill),

    ('AB', 28, '预估①基于1t0', '本金', 8, 'est1', est1_fill),
    ('AC', 29, '预估①基于1t0', '息费', 8, 'est1', est1_fill),

    ('AD', 30, '预估②基于1t3', '本金', 8, 'est2', est2_fill),
    ('AE', 31, '预估②基于1t3', '息费', 8, 'est2', est2_fill),

    ('AF', 32, '预估③基于2t0', '本金', 8, 'est3', est3_fill),
    ('AG', 33, '预估③基于2t0', '息费', 8, 'est3', est3_fill),

    ('AH', 34, '预估④基于3t0', '本金', 8, 'est4', est4_fill),
    ('AI', 35, '预估④基于3t0', '息费', 8, 'est4', est4_fill),

    ('AJ', 36, '预估⑤基于4t0', '本金', 8, 'est5', est5_fill),
    ('AK', 37, '预估⑤基于4t0', '息费', 8, 'est5', est5_fill),

    ('AL', 38, '最终(按期限选优)', '推荐方法', 14, 'final', final_fill),
    ('AM', 39, '最终(按期限选优)', '本金', 8, 'final', final_fill),
    ('AN', 40, '最终(按期限选优)', '息费', 8, 'final', final_fill),
    ('AO', 41, '最终(按期限选优)', 'TR', 8, 'final', final_fill),

    ('AP', 42, '9月实际(参照)', '出账笔数', 8, 'actual', actual_fill),
    ('AQ', 43, '9月实际(参照)', '覆盖率', 8, 'actual', actual_fill),
    ('AR', 44, '9月实际(参照)', '实际本金', 8, 'actual', actual_fill),
    ('AS', 45, '9月实际(参照)', '实际息费', 8, 'actual', actual_fill),
    ('AT', 46, '9月实际(参照)', '实际TR', 8, 'actual', actual_fill),
]
NCOLS = len(col_defs)

# Group headers (row 4)
group_names = {
    'info': '产品信息',
    'sep_input': 'Step1: 9月输入(原始数据)',
    'aug_raw': 'Step2: 8月原始数据(参考)',
    'aug_ratio': 'Step3: 8月比率(=8月4t7/8月指标)',
    'est1': 'Step4①: 预估(=9月1t0×比率)',
    'est2': 'Step4②: 预估(=9月1t3×比率)',
    'est3': 'Step4③: 预估(=9月2t0×比率)',
    'est4': 'Step4④: 预估(=9月3t0×比率)',
    'est5': 'Step4⑤: 预估(=9月4t0×比率)',
    'final': 'Step5: 最终(按loan_cycle选优)',
    'actual': '参照: 9月实际(部分)',
}

groups_order = []
seen = set()
for cd in col_defs:
    if cd[5] not in seen:
        groups_order.append(cd[5])
        seen.add(cd[5])

group_cols = {}
for cd in col_defs:
    g = cd[5]
    if g not in group_cols:
        group_cols[g] = [cd[1], cd[1]]
    else:
        group_cols[g][1] = cd[1]

for g in groups_order:
    start, end = group_cols[g]
    cell = ws.cell(row=4, column=start, value=group_names[g])
    cell.font = section_font
    cell.fill = section_fill
    cell.alignment = center
    cell.border = thin_border
    if start != end:
        ws.merge_cells(start_row=4, start_column=start, end_row=4, end_column=end)

# Sub-headers (row 5)
for cd in col_defs:
    col_letter, col_idx, header, sub_header, width, group, fill = cd
    cell = ws.cell(row=5, column=col_idx, value=sub_header)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = center
    cell.border = thin_border
    ws.column_dimensions[col_letter].width = width

ws.row_dimensions[4].height = 20
ws.row_dimensions[5].height = 18

# Title
ws['A1'] = '9月各产品4t7预估 - 公式版(按loan_cycle选优早期指标)'
ws['A1'].font = title_font
ws.merge_cells('A1:AT1')
ws.row_dimensions[1].height = 25

ws['A2'] = ('选优逻辑: 7天→④⑤(3t0,4t0) | 14天→②③(1t3,2t0) | 21天→①②(1t0,1t3) | 28天→①(1t0) — '
            '出账越多指标越精准 | 黄=原始输入 绿=比率 橙/蓝/粉/紫/浅蓝=五组预估 黄=最终 灰=实际')
ws['A2'].font = note_font
ws.merge_cells('A2:AT2')

# ============================================================
# Write data rows with FORMULAS
# ============================================================
print("写入数据行(带公式)...")
data_start = 6
sep_products = sep['产品'].tolist()
aug_by_product = aug.set_index('产品')

for i, sep_row in sep.iterrows():
    r = data_start + sep_products.index(sep_row['产品'])
    product = sep_row['产品']
    has_aug = product in aug_by_product.index

    # --- 产品信息 ---
    ws.cell(row=r, column=1, value=product).font = normal_font
    ws.cell(row=r, column=2, value=int(sep_row['放款笔数'])).number_format = NUM
    ws.cell(row=r, column=3, value=float(sep_row['放款金额'])).number_format = NUM
    # loan_cycle from 平均期限
    term = sep_row['平均期限']
    cycle_str = f'{int(term)}天' if pd.notna(term) else '-'
    ws.cell(row=r, column=4, value=cycle_str)

    # --- 9月输入 ---
    ws.cell(row=r, column=5, value=float(sep_row['1t0本金逾期率'])).number_format = PCT
    ws.cell(row=r, column=6, value=float(sep_row['1t3本金逾期率'])).number_format = PCT
    ws.cell(row=r, column=7, value=float(sep_row['2t0本金逾期率'])).number_format = PCT
    # 3t0, 4t0 may be NaN
    v3t0 = sep_row['3t0本金逾期率']
    v4t0 = sep_row['4t0本金逾期率']
    ws.cell(row=r, column=8, value=float(v3t0) if pd.notna(v3t0) else '-').number_format = PCT
    ws.cell(row=r, column=9, value=float(v4t0) if pd.notna(v4t0) else '-').number_format = PCT
    ws.cell(row=r, column=10, value=float(sep_row['总收息_含税'])).number_format = PCT

    # --- 8月原始数据 ---
    if has_aug:
        a = aug_by_product.loc[product]
        ws.cell(row=r, column=11, value=float(a['1t0本金逾期率'])).number_format = PCT
        ws.cell(row=r, column=12, value=float(a['1t3本金逾期率'])).number_format = PCT
        ws.cell(row=r, column=13, value=float(a['2t0本金逾期率'])).number_format = PCT
        ws.cell(row=r, column=14, value=float(a['3t0本金逾期率'])).number_format = PCT
        ws.cell(row=r, column=15, value=float(a['4t0本金逾期率'])).number_format = PCT
        ws.cell(row=r, column=16, value=float(a['4t7本金逾期率'])).number_format = PCT
        ws.cell(row=r, column=17, value=float(a['4t7息费逾期率_本金分母'])).number_format = PCT
    else:
        for c in range(11, 18):
            ws.cell(row=r, column=c, value='无8月数据').font = note_font

    # --- 8月比率 (公式) ---
    if has_aug:
        ws.cell(row=r, column=18, value=f'=IF(K{r}=0,"-",P{r}/K{r})').number_format = RATIO    # 本金/1t0
        ws.cell(row=r, column=19, value=f'=IF(L{r}=0,"-",P{r}/L{r})').number_format = RATIO    # 本金/1t3
        ws.cell(row=r, column=20, value=f'=IF(M{r}=0,"-",P{r}/M{r})').number_format = RATIO    # 本金/2t0
        ws.cell(row=r, column=21, value=f'=IF(N{r}=0,"-",P{r}/N{r})').number_format = RATIO    # 本金/3t0
        ws.cell(row=r, column=22, value=f'=IF(O{r}=0,"-",P{r}/O{r})').number_format = RATIO    # 本金/4t0
        ws.cell(row=r, column=23, value=f'=IF(K{r}=0,"-",Q{r}/K{r})').number_format = RATIO    # 息费/1t0
        ws.cell(row=r, column=24, value=f'=IF(L{r}=0,"-",Q{r}/L{r})').number_format = RATIO    # 息费/1t3
        ws.cell(row=r, column=25, value=f'=IF(M{r}=0,"-",Q{r}/M{r})').number_format = RATIO    # 息费/2t0
        ws.cell(row=r, column=26, value=f'=IF(N{r}=0,"-",Q{r}/N{r})').number_format = RATIO    # 息费/3t0
        ws.cell(row=r, column=27, value=f'=IF(O{r}=0,"-",Q{r}/O{r})').number_format = RATIO    # 息费/4t0
    else:
        ws.cell(row=r, column=18, value=float(avg_r_本金_1t0)).number_format = RATIO
        ws.cell(row=r, column=19, value=float(avg_r_本金_1t3)).number_format = RATIO
        ws.cell(row=r, column=20, value=float(avg_r_本金_2t0)).number_format = RATIO
        ws.cell(row=r, column=21, value=float(avg_r_本金_3t0)).number_format = RATIO
        ws.cell(row=r, column=22, value=float(avg_r_本金_4t0)).number_format = RATIO
        ws.cell(row=r, column=23, value=float(avg_r_息费_1t0)).number_format = RATIO
        ws.cell(row=r, column=24, value=float(avg_r_息费_1t3)).number_format = RATIO
        ws.cell(row=r, column=25, value=float(avg_r_息费_2t0)).number_format = RATIO
        ws.cell(row=r, column=26, value=float(avg_r_息费_3t0)).number_format = RATIO
        ws.cell(row=r, column=27, value=float(avg_r_息费_4t0)).number_format = RATIO
        ws.cell(row=r, column=18).font = note_font

    # --- 预估①基于1t0: 本金=E*R, 息费=E*W ---
    ws.cell(row=r, column=28, value=f'=IFERROR(E{r}*R{r},"-")').number_format = PCT
    ws.cell(row=r, column=29, value=f'=IFERROR(E{r}*W{r},"-")').number_format = PCT

    # --- 预估②基于1t3: 本金=F*S, 息费=F*X ---
    ws.cell(row=r, column=30, value=f'=IFERROR(F{r}*S{r},"-")').number_format = PCT
    ws.cell(row=r, column=31, value=f'=IFERROR(F{r}*X{r},"-")').number_format = PCT

    # --- 预估③基于2t0: 本金=G*T, 息费=G*Y ---
    ws.cell(row=r, column=32, value=f'=IFERROR(G{r}*T{r},"-")').number_format = PCT
    ws.cell(row=r, column=33, value=f'=IFERROR(G{r}*Y{r},"-")').number_format = PCT

    # --- 预估④基于3t0: 本金=H*U, 息费=H*Z ---
    ws.cell(row=r, column=34, value=f'=IFERROR(H{r}*U{r},"-")').number_format = PCT
    ws.cell(row=r, column=35, value=f'=IFERROR(H{r}*Z{r},"-")').number_format = PCT

    # --- 预估⑤基于4t0: 本金=I*V, 息费=I*AA ---
    ws.cell(row=r, column=36, value=f'=IFERROR(I{r}*V{r},"-")').number_format = PCT
    ws.cell(row=r, column=37, value=f'=IFERROR(I{r}*AA{r},"-")').number_format = PCT

    # --- 最终(按loan_cycle选优) ---
    # AL: 推荐方法
    ws.cell(row=r, column=38, value=(
        f'=IF(D{r}="7天","④⑤(3t0,4t0)",'
        f'IF(D{r}="14天","②③(1t3,2t0)",'
        f'IF(D{r}="21天","①②(1t0,1t3)",'
        f'IF(D{r}="28天","①(1t0)","全部均值"))))'
    ))
    # AM: 最终本金 — 7天:AVERAGE(AH,AJ) 14天:AVERAGE(AD,AF) 21天:AVERAGE(AB,AD) 28天:AB
    ws.cell(row=r, column=39, value=(
        f'=IFERROR(IF(D{r}="7天",IFERROR(AVERAGE(AH{r},AJ{r}),IFERROR(AJ{r},AH{r})),'
        f'IF(D{r}="14天",IFERROR(AVERAGE(AD{r},AF{r}),IFERROR(AF{r},AD{r})),'
        f'IF(D{r}="21天",IFERROR(AVERAGE(AB{r},AD{r}),IFERROR(AD{r},AB{r})),'
        f'IF(D{r}="28天",AB{r},'
        f'IFERROR(AVERAGE(AB{r},AD{r},AF{r},AH{r},AJ{r}),"-"))))),"-")'
    )).number_format = PCT
    # AN: 最终息费 — 同理
    ws.cell(row=r, column=40, value=(
        f'=IFERROR(IF(D{r}="7天",IFERROR(AVERAGE(AI{r},AK{r}),IFERROR(AK{r},AI{r})),'
        f'IF(D{r}="14天",IFERROR(AVERAGE(AE{r},AG{r}),IFERROR(AG{r},AE{r})),'
        f'IF(D{r}="21天",IFERROR(AVERAGE(AC{r},AE{r}),IFERROR(AE{r},AC{r})),'
        f'IF(D{r}="28天",AC{r},'
        f'IFERROR(AVERAGE(AC{r},AE{r},AG{r},AI{r},AK{r}),"-"))))),"-")'
    )).number_format = PCT
    # AO: 最终TR = J - AM - AN
    ws.cell(row=r, column=41, value=f'=IFERROR(J{r}-AM{r}-AN{r},"-")').number_format = PCT

    # --- 9月实际(参照) ---
    ws.cell(row=r, column=42, value=int(sep_row['is_t7_window_4'])).number_format = NUM
    ws.cell(row=r, column=43, value=f'=IF(B{r}=0,0,AP{r}/B{r})').number_format = PCT
    val_ben = sep_row['4t7本金逾期率']
    val_xf = sep_row['4t7息费逾期率_本金分母']
    val_tr = sep_row['4t7TR']
    ws.cell(row=r, column=44, value=float(val_ben) if pd.notna(val_ben) else '-').number_format = PCT
    ws.cell(row=r, column=45, value=float(val_xf) if pd.notna(val_xf) else '-').number_format = PCT
    ws.cell(row=r, column=46, value=float(val_tr) if pd.notna(val_tr) else '-').number_format = PCT

    # Formatting
    for c in range(1, NCOLS + 1):
        cell = ws.cell(row=r, column=c)
        cell.border = thin_border
        if not cell.font or not cell.font.name:
            cell.font = normal_font
        if not cell.alignment or cell.alignment.horizontal != 'left':
            cell.alignment = center if c != 1 else left_a
        for cd in col_defs:
            if cd[1] == c:
                cell.fill = cd[6]
                break

# ============================================================
# Summary row (weighted by 金额)
# ============================================================
summary_row = data_start + len(sep) + 1
last_data_row = data_start + len(sep) - 1

ws.cell(row=summary_row, column=1, value='金额加权汇总').font = section_font
ws.cell(row=summary_row, column=2, value=f'=SUM(B{data_start}:B{last_data_row})').number_format = NUM
ws.cell(row=summary_row, column=3, value=f'=SUM(C{data_start}:C{last_data_row})').number_format = NUM

# Weighted averages
for col, letter in [(28,'AB'),(29,'AC'),(30,'AD'),(31,'AE'),(32,'AF'),(33,'AG'),
                     (34,'AH'),(35,'AI'),(36,'AJ'),(37,'AK'),
                     (39,'AM'),(40,'AN'),(41,'AO'),
                     (44,'AR'),(45,'AS'),(46,'AT')]:
    ws.cell(row=summary_row, column=col,
            value=f'=IFERROR(SUMPRODUCT({letter}{data_start}:{letter}{last_data_row},$C${data_start}:$C${last_data_row})/SUM($C${data_start}:$C${last_data_row}),"-")').number_format = PCT

for c in range(1, NCOLS + 1):
    cell = ws.cell(row=summary_row, column=c)
    cell.border = thin_border
    cell.fill = final_fill
    if not cell.font or not cell.font.bold:
        cell.font = normal_font
    cell.alignment = center

ws.freeze_panes = 'B6'

# ============================================================
# Sheet 2: 公式说明
# ============================================================
ws2 = wb.create_sheet('公式说明')
ws2.sheet_view.showGridLines = False
ws2['A1'] = '公式说明 - 每列的计算逻辑'
ws2['A1'].font = title_font
ws2.merge_cells('A1:D1')

formula_explanations = [
    ('列', '公式', '说明', '示例'),
    ('D (loan_cycle)', '来自平均期限', '7天/14天/21天/28天', '平均期限=7→7天'),
    ('E-J (9月输入)', '原始数据', '1t0,1t3,2t0,3t0,4t0,总收息', ''),
    ('K-Q (8月原始)', '原始数据', '8月各指标+4t7', ''),
    ('R (本金/1t0)', '=P/K', '8月4t7本金÷8月1t0', ''),
    ('S (本金/1t3)', '=P/L', '8月4t7本金÷8月1t3', ''),
    ('T (本金/2t0)', '=P/M', '8月4t7本金÷8月2t0', ''),
    ('U (本金/3t0)', '=P/N', '8月4t7本金÷8月3t0', ''),
    ('V (本金/4t0)', '=P/O', '8月4t7本金÷8月4t0', ''),
    ('W-AA (息费比率)', '=Q/对应指标', '8月4t7息费÷8月各指标', ''),
    ('AB (预估①本金)', '=E*R', '9月1t0×8月(本金/1t0)', ''),
    ('AC (预估①息费)', '=E*W', '9月1t0×8月(息费/1t0)', ''),
    ('AD-AE (预估②)', '=F*S, =F*X', '9月1t3×比率', ''),
    ('AF-AG (预估③)', '=G*T, =G*Y', '9月2t0×比率', ''),
    ('AH-AI (预估④)', '=H*U, =H*Z', '9月3t0×比率', ''),
    ('AJ-AK (预估⑤)', '=I*V, =I*AA', '9月4t0×比率', ''),
    ('AL (推荐方法)', '按loan_cycle自动选择', '7天→④⑤ 14天→②③ 21天→①② 28天→①', ''),
    ('AM (最终本金)', 'IF按D选优', '7天:AVERAGE(④,⑤) 14天:AVERAGE(②,③) 21天:AVERAGE(①,②) 28天:①', ''),
    ('AN (最终息费)', 'IF按D选优', '同上逻辑', ''),
    ('AO (最终TR)', '=J-AM-AN', '总收息-本金-息费', ''),
    ('AQ (覆盖率)', '=AP/B', '已出账笔数÷总笔数', ''),
    ('加权汇总', '=SUMPRODUCT/SUM', '按放款金额加权平均', ''),
]

for i, row_data in enumerate(formula_explanations):
    r = 3 + i
    for c, val in enumerate(row_data, 1):
        cell = ws2.cell(row=r, column=c, value=val)
        cell.font = header_font if i == 0 else normal_font
        cell.fill = header_fill if i == 0 else (ratio_fill if c == 2 else PatternFill())
        cell.alignment = left_a if c > 1 else center
        cell.border = thin_border

ws2.column_dimensions['A'].width = 22
ws2.column_dimensions['B'].width = 35
ws2.column_dimensions['C'].width = 35
ws2.column_dimensions['D'].width = 25

# ============================================================
# Sheet 3: TR公式验证
# ============================================================
ws3 = wb.create_sheet('TR公式验证')
ws3.sheet_view.showGridLines = False
ws3['A1'] = 'TR公式验证: 4t7TR = 总收息_含税 - 4t7本金 - 4t7息费 (8月数据验证)'
ws3['A1'].font = title_font
ws3.merge_cells('A1:G1')

headers = ['产品', '总收息', '4t7本金', '4t7息费', '4t7TR(原)', 'TR(公式)', '差异']
for c, h in enumerate(headers, 1):
    cell = ws3.cell(row=3, column=c, value=h)
    cell.font = header_font; cell.fill = header_fill; cell.alignment = center; cell.border = thin_border
    ws3.column_dimensions[get_column_letter(c)].width = 14

for i, (_, row) in enumerate(aug.iterrows()):
    r = 4 + i
    ws3.cell(row=r, column=1, value=row['产品']).font = normal_font
    ws3.cell(row=r, column=2, value=float(row['总收息_含税'])).number_format = PCT
    ws3.cell(row=r, column=3, value=float(row['4t7本金逾期率'])).number_format = PCT
    ws3.cell(row=r, column=4, value=float(row['4t7息费逾期率_本金分母'])).number_format = PCT
    ws3.cell(row=r, column=5, value=float(row['4t7TR'])).number_format = PCT
    ws3.cell(row=r, column=6, value=f'=B{r}-C{r}-D{r}').number_format = PCT
    ws3.cell(row=r, column=7, value=f'=E{r}-F{r}').number_format = PCT2
    for c in range(1, 8):
        cell = ws3.cell(row=r, column=c)
        cell.border = thin_border; cell.font = normal_font
        cell.alignment = center if c != 1 else left_a
        cell.fill = input_fill if c <= 5 else (ratio_fill if c == 6 else actual_fill)

ws3.freeze_panes = 'B4'

# ============================================================
# Sheet 4: 比率稳定性(6-7-8月, 5指标)
# ============================================================
ws4 = wb.create_sheet('比率稳定性(6-7-8月)')
ws4.sheet_view.showGridLines = False
ws4['A1'] = '6/7/8月 4t7/各指标 比率稳定性验证(按loan_cycle分组)'
ws4['A1'].font = title_font
ws4.merge_cells('A1:N1')
ws4['A2'] = '每个产品展示5个指标(1t0,1t3,2t0,3t0,4t0)的4t7比率在6/7/8月间的极差,极差越小越稳定'
ws4['A2'].font = note_font
ws4.merge_cells('A2:N2')

jun_df = df[(df['月份']=='2026-06') & df['产品'].notna() & df['4t7本金逾期率'].notna()].copy()
jul_df = df[(df['月份']=='2026-07') & df['产品'].notna() & df['4t7本金逾期率'].notna()].copy()
aug_df = df[(df['月份']=='2026-08') & df['产品'].notna() & df['4t7本金逾期率'].notna()].copy()

# Headers
headers4 = ['产品','loan_cycle','月','1t0','1t3','2t0','3t0','4t0']
for c, h in enumerate(headers4, 1):
    cell = ws4.cell(row=4, column=c, value=h)
    cell.font = header_font; cell.fill = header_fill; cell.alignment = center; cell.border = thin_border
    ws4.column_dimensions[get_column_letter(c)].width = 10
ws4.column_dimensions['A'].width = 20
ws4.column_dimensions['B'].width = 8

common = set(aug_df['产品']) & set(jul_df['产品']) & set(jun_df['产品'])
common = sorted(common)
aug_d = aug_df.set_index('产品').to_dict('index')
jul_d = jul_df.set_index('产品').to_dict('index')
jun_d = jun_df.set_index('产品').to_dict('index')

indicators = ['1t0本金逾期率','1t3本金逾期率','2t0本金逾期率','3t0本金逾期率','4t0本金逾期率']
r = 5
for product in common:
    for mname, mdict in [('6月',jun_d),('7月',jul_d),('8月',aug_d)]:
        row = mdict[product]
        ws4.cell(row=r, column=1, value=product)
        ws4.cell(row=r, column=2, value=f'{int(row["平均期限"])}天')
        ws4.cell(row=r, column=3, value=mname)
        for ci, ind in enumerate(indicators):
            v = row[ind]
            ratio = row['4t7本金逾期率']/v if v > 0 else '-'
            cell = ws4.cell(row=r, column=4+ci, value=ratio if isinstance(ratio, str) else float(ratio))
            cell.number_format = RATIO if isinstance(ratio, float) else 'General'
        for c in range(1, 9):
            cell = ws4.cell(row=r, column=c)
            cell.border = thin_border; cell.font = normal_font
            cell.alignment = center if c != 1 else left_a
            if c >= 4:
                cell.fill = ratio_fill
            else:
                cell.fill = input_fill
        r += 1

ws4.freeze_panes = 'B5'

# ============================================================
# Save
# ============================================================
output_path = r"D:\Documents\Downloads\9月4t7预估详解(公式版v3).xlsx"
wb.calculation.calcMode = 'auto'
wb.calculation.fullCalcOnLoad = True
wb.save(output_path)
print(f"\nExcel已保存: {output_path}")
print(f"共 {len(sep)} 个9月产品, {len(aug)} 个8月参考产品")
print(f"列数: {NCOLS} (A-{get_column_letter(NCOLS)})")
