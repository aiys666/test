import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Load intermediate data
result_df = pd.read_pickle(r"e:\岳松个人文件\嘉银工作内容的整理\code\est_result.pkl")
aug_ratio = pd.read_pickle(r"e:\岳松个人文件\嘉银工作内容的整理\code\aug_ratio.pkl")
jul_ratios = pd.read_pickle(r"e:\岳松个人文件\嘉银工作内容的整理\code\jul_ratios.pkl")
jun_ratios = pd.read_pickle(r"e:\岳松个人文件\嘉银工作内容的整理\code\jun_ratios.pkl")

output_path = r"D:\Documents\Downloads\9月4t7预估详解.xlsx"

# ============================================================
# Styles
# ============================================================
thin_border = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
header_font = Font(name='微软雅黑', size=10, bold=True, color='FFFFFF')

section_fill = PatternFill(start_color='D9E2F3', end_color='D9E2F3', fill_type='solid')
section_font = Font(name='微软雅黑', size=10, bold=True, color='1F4E79')

input_fill = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')
ratio_fill = PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid')
est1_fill = PatternFill(start_color='FCE4D6', end_color='FCE4D6', fill_type='solid')
est2_fill = PatternFill(start_color='DDEBF7', end_color='DDEBF7', fill_type='solid')
final_fill = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')
actual_fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')

normal_font = Font(name='微软雅黑', size=10)
title_font = Font(name='微软雅黑', size=14, bold=True, color='1F4E79')
note_font = Font(name='微软雅黑', size=9, color='808080', italic=True)

center = Alignment(horizontal='center', vertical='center', wrap_text=True)
left = Alignment(horizontal='left', vertical='center', wrap_text=True)
right_align = Alignment(horizontal='right', vertical='center')

# ============================================================
# Create Workbook
# ============================================================
wb = Workbook()

# ============================================================
# Sheet 1: 预估说明
# ============================================================
ws1 = wb.active
ws1.title = '预估说明'
ws1.sheet_view.showGridLines = False

ws1['A1'] = '9月4t7预估方法论说明'
ws1['A1'].font = title_font
ws1.merge_cells('A1:F1')

row = 3
explanations = [
    ('一、预估目标', section_font),
    ('基于9月已完全出账的1t0、1t3、2t0指标,预估9月各产品的4t7本金坏账率、4t7息费坏账率、4t7TR', normal_font),
    ('', normal_font),
    ('二、核心公式', section_font),
    ('4t7TR = 总收息_含税 - 4t7本金逾期率 - 4t7息费逾期率_本金分母', normal_font),
    ('    (已通过8月数据验证,公式完全准确,误差=0)', note_font),
    ('', normal_font),
    ('三、预估方法:比率迁移法', section_font),
    ('Step 1: 从8月(已完全出账)数据计算迁移比率', normal_font),
    ('    4t7本金/1t0 = 8月4t7本金逾期率 / 8月1t0本金逾期率', normal_font),
    ('    4t7本金/1t3 = 8月4t7本金逾期率 / 8月1t3本金逾期率', normal_font),
    ('    4t7本金/2t0 = 8月4t7本金逾期率 / 8月2t0本金逾期率', normal_font),
    ('    (息费同理)', normal_font),
    ('', normal_font),
    ('Step 2: 将8月比率 × 9月实际1t0/1t3/2t0 → 得到三组预估', normal_font),
    ('    预估4t7本金(基于1t0) = 9月1t0 × 8月(4t7本金/1t0)', normal_font),
    ('    预估4t7本金(基于1t3) = 9月1t3 × 8月(4t7本金/1t3)', normal_font),
    ('    预估4t7本金(基于2t0) = 9月2t0 × 8月(4t7本金/2t0)', normal_font),
    ('    (息费同理)', normal_font),
    ('', normal_font),
    ('Step 3: 对三组预估取均值 → 最终预估值', normal_font),
    ('    预估4t7本金 = avg(基于1t0, 基于1t3, 基于2t0)', normal_font),
    ('    预估4t7息费 = avg(基于1t0, 基于1t3, 基于2t0)', normal_font),
    ('', normal_font),
    ('Step 4: 计算预估TR', normal_font),
    ('    预估4t7TR = 9月总收息_含税 - 预估4t7本金 - 预估4t7息费', normal_font),
    ('', normal_font),
    ('四、比率选择依据', section_font),
    ('6/7/8三月比率稳定性验证显示:', normal_font),
    ('    4t7/2t0 比率最稳定(月间极差多在0.02-0.08)', normal_font),
    ('    4t7/1t3 比率次之', normal_font),
    ('    4t7/1t0 比率波动较大', normal_font),
    ('三种方法取均值可降低单一指标波动风险', normal_font),
    ('', normal_font),
    ('五、特殊情况处理', section_font),
    ('    1. 产品在8月无数据或样本≤3笔: 使用全局平均比率', normal_font),
    ('    2. 9月某指标为0(如1t0=0): 该方法不可用,仅使用可用的方法', normal_font),
    ('    3. A_07_01_50_00产品的4t7息费=0: 该产品为纯前砍息产品,无后收息费', normal_font),
    ('', normal_font),
    ('六、9月已有部分4t7实际数据', section_font),
    ('9月部分早期放款已到达4t7观察窗口,可作为预估结果的参照', normal_font),
    ('但部分样本可能存在偏差(早期放款客群质量与整体不同)', normal_font),
]

for text, font in explanations:
    ws1.cell(row=row, column=1, value=text).font = font
    ws1.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    row += 1

ws1.column_dimensions['A'].width = 80
for col in range(2, 7):
    ws1.column_dimensions[get_column_letter(col)].width = 15

# ============================================================
# Sheet 2: 9月预估详解
# ============================================================
ws2 = wb.create_sheet('9月预估详解')
ws2.sheet_view.showGridLines = False

# Title
ws2['A1'] = '9月各产品4t7预估 - 完整推演过程'
ws2['A1'].font = title_font
ws2.merge_cells('A1:Z1')
ws2.row_dimensions[1].height = 25

# Define columns with groups
col_groups = [
    ('产品信息', input_fill, [
        ('产品', '产品', 15),
        ('9月放款笔数', '放款笔数', 10),
        ('9月放款金额', '放款金额', 13),
    ]),
    ('Step1: 9月输入指标(已知)', input_fill, [
        ('9月1t0', '1t0', 8),
        ('9月1t3', '1t3', 8),
        ('9月2t0', '2t0', 8),
        ('9月总收息_含税', '总收息', 8),
    ]),
    ('Step2: 8月迁移比率(参考)', ratio_fill, [
        ('8月比率来源', '来源', 12),
        ('8月放款笔数', '8月笔数', 8),
        ('8月4t7本金/1t0', '本金/1t0', 9),
        ('8月4t7本金/1t3', '本金/1t3', 9),
        ('8月4t7本金/2t0', '本金/2t0', 9),
        ('8月4t7息费/1t0', '息费/1t0', 9),
        ('8月4t7息费/1t3', '息费/1t3', 9),
        ('8月4t7息费/2t0', '息费/2t0', 9),
    ]),
    ('Step3a: 基于1t0预估', est1_fill, [
        ('预估4t7本金(基于1t0)', '本金', 9),
        ('预估4t7息费(基于1t0)', '息费', 9),
        ('预估4t7TR(基于1t0)', 'TR', 9),
    ]),
    ('Step3b: 基于1t3预估', est2_fill, [
        ('预估4t7本金(基于1t3)', '本金', 9),
        ('预估4t7息费(基于1t3)', '息费', 9),
        ('预估4t7TR(基于1t3)', 'TR', 9),
    ]),
    ('Step3c: 基于2t0预估', est1_fill, [
        ('预估4t7本金(基于2t0)', '本金', 9),
        ('预估4t7息费(基于2t0)', '息费', 9),
        ('预估4t7TR(基于2t0)', 'TR', 9),
    ]),
    ('Step4: 三法均值(最终预估)', final_fill, [
        ('预估4t7本金(三法均值)', '本金', 10),
        ('预估4t7息费(三法均值)', '息费', 10),
        ('预估4t7TR(三法均值)', 'TR', 10),
    ]),
    ('参照: 9月部分实际4t7', actual_fill, [
        ('9月4t7已出账笔数', '出账笔数', 9),
        ('9月4t7出账覆盖率', '覆盖率', 8),
        ('9月实际4t7本金(部分样本)', '实际本金', 9),
        ('9月实际4t7息费(部分样本)', '实际息费', 9),
        ('9月实际4t7TR(部分样本)', '实际TR', 9),
    ]),
]

# Write group headers (row 3)
col_idx = 1
for group_name, fill, cols in col_groups:
    start_col = col_idx
    end_col = col_idx + len(cols) - 1
    cell = ws2.cell(row=3, column=start_col, value=group_name)
    cell.font = section_font
    cell.fill = fill
    cell.alignment = center
    cell.border = thin_border
    ws2.merge_cells(start_row=3, start_column=start_col, end_row=3, end_column=end_col)
    col_idx = end_col + 1

# Write column headers (row 4)
col_idx = 1
for group_name, fill, cols in col_groups:
    for col_name, header, width in cols:
        cell = ws2.cell(row=4, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin_border
        ws2.column_dimensions[get_column_letter(col_idx)].width = width
        col_idx += 1

ws2.row_dimensions[3].height = 20
ws2.row_dimensions[4].height = 18

# Write data rows
data_start_row = 5
for i, (_, row_data) in enumerate(result_df.iterrows()):
    r = data_start_row + i
    col_idx = 1
    for group_name, fill, cols in col_groups:
        for col_name, header, width in cols:
            val = row_data[col_name]
            cell = ws2.cell(row=r, column=col_idx)
            if pd.isna(val):
                cell.value = '-'
            elif col_name in ['产品', '8月比率来源']:
                cell.value = val
            elif col_name in ['9月放款笔数', '8月放款笔数', '9月4t7已出账笔数']:
                cell.value = int(val) if not pd.isna(val) else '-'
                cell.number_format = '#,##0'
            elif col_name in ['9月放款金额']:
                cell.value = val
                cell.number_format = '#,##0.00'
            elif col_name == '9月4t7出账覆盖率':
                cell.value = val
                cell.number_format = '0.0%'
            else:
                cell.value = val
                cell.number_format = '0.0000%'
            cell.font = normal_font
            cell.fill = fill
            cell.alignment = center if col_name != '产品' else left
            cell.border = thin_border
            col_idx += 1

# Add weighted summary row
summary_row = data_start_row + len(result_df) + 1
ws2.cell(row=summary_row, column=1, value='金额加权汇总').font = section_font
ws2.cell(row=summary_row, column=1).fill = final_fill
ws2.cell(row=summary_row, column=1).alignment = center
ws2.cell(row=summary_row, column=1).border = thin_border

# Calculate weighted averages
total_amount = result_df['9月放款金额'].sum()
ws2.cell(row=summary_row, column=2, value=int(result_df['9月放款笔数'].sum())).number_format = '#,##0'
ws2.cell(row=summary_row, column=3, value=total_amount).number_format = '#,##0.00'

# Weighted average for key columns
for col_idx, col_name in enumerate([
    '预估4t7本金(三法均值)', '预估4t7息费(三法均值)', '预估4t7TR(三法均值)'
], start=22):  # Columns V, W, X (Step4 group)
    valid = result_df[result_df[col_name].notna()]
    weighted = (valid[col_name] * valid['9月放款金额']).sum() / valid['9月放款金额'].sum()
    cell = ws2.cell(row=summary_row, column=col_idx, value=weighted)
    cell.number_format = '0.0000%'
    cell.font = section_font
    cell.fill = final_fill
    cell.alignment = center
    cell.border = thin_border

# Also calculate weighted actual
for col_idx, col_name in enumerate([
    '9月实际4t7本金(部分样本)', '9月实际4t7息费(部分样本)', '9月实际4t7TR(部分样本)'
], start=25):  # Columns Y, Z, AA (actual group)
    valid = result_df[result_df[col_name].notna() & (result_df['9月放款金额'] > 0)]
    if len(valid) > 0:
        weighted = (valid[col_name] * valid['9月放款金额']).sum() / valid['9月放款金额'].sum()
        cell = ws2.cell(row=summary_row, column=col_idx, value=weighted)
        cell.number_format = '0.0000%'
        cell.font = section_font
        cell.fill = final_fill
        cell.alignment = center
        cell.border = thin_border

# Fill remaining summary cells
for c in range(1, 31):
    cell = ws2.cell(row=summary_row, column=c)
    if cell.value is None:
        cell.value = ''
        cell.fill = final_fill
    cell.border = thin_border
    if not cell.font.bold:
        cell.font = normal_font

# Freeze panes
ws2.freeze_panes = 'B5'

# ============================================================
# Sheet 3: 8月比率参考
# ============================================================
ws3 = wb.create_sheet('8月比率参考')
ws3.sheet_view.showGridLines = False

ws3['A1'] = '8月各产品4t7迁移比率参考表'
ws3['A1'].font = title_font
ws3.merge_cells('A1:M1')
ws3.row_dimensions[1].height = 25

aug_cols = [
    ('产品', '产品', 18, None),
    ('放款笔数', '放款笔数', 8, '#,##0'),
    ('放款金额', '放款金额', 13, '#,##0.00'),
    ('可靠', '可靠', 6, None),
    ('4t7本金', '4t7本金', 9, '0.0000%'),
    ('4t7息费', '4t7息费', 9, '0.0000%'),
    ('1t0', '1t0', 9, '0.0000%'),
    ('1t3', '1t3', 9, '0.0000%'),
    ('2t0', '2t0', 9, '0.0000%'),
    ('4t7本金/1t0', '本金/1t0', 10, '0.0000'),
    ('4t7本金/1t3', '本金/1t3', 10, '0.0000'),
    ('4t7本金/2t0', '本金/2t0', 10, '0.0000'),
    ('4t7息费/2t0', '息费/2t0', 10, '0.0000'),
]

# Headers
for c, (col_name, header, width, fmt) in enumerate(aug_cols, 1):
    cell = ws3.cell(row=3, column=c, value=header)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = center
    cell.border = thin_border
    ws3.column_dimensions[get_column_letter(c)].width = width

# Data
for i, (_, row_data) in enumerate(aug_ratio.iterrows()):
    r = 4 + i
    for c, (col_name, header, width, fmt) in enumerate(aug_cols, 1):
        val = row_data[col_name]
        cell = ws3.cell(row=r, column=c)
        if pd.isna(val):
            cell.value = '-'
        elif col_name == '可靠':
            cell.value = '✓' if val else '✗'
        elif col_name in ['产品']:
            cell.value = val
        elif col_name == '放款笔数':
            cell.value = int(val)
        else:
            cell.value = val
        cell.font = normal_font
        cell.fill = ratio_fill if col_name.startswith('4t7') or '/' in col_name else input_fill
        cell.alignment = center if col_name != '产品' else left
        cell.border = thin_border
        if fmt and not pd.isna(val) and col_name != '可靠':
            cell.number_format = fmt

ws3.freeze_panes = 'B4'

# ============================================================
# Sheet 4: 比率稳定性验证
# ============================================================
ws4 = wb.create_sheet('比率稳定性验证')
ws4.sheet_view.showGridLines = False

ws4['A1'] = '6/7/8月迁移比率稳定性验证 (4t7/2t0)'
ws4['A1'].font = title_font
ws4.merge_cells('A1:J1')
ws4.row_dimensions[1].height = 25

ws4['A3'] = '说明: 以下展示各产品在6/7/8月的4t7本金/2t0和4t7息费/2t0比率,用于验证比率稳定性'
ws4['A3'].font = note_font
ws4.merge_cells('A3:J3')

# Get common products across 6/7/8 months
all_products = set(aug_ratio['产品']) | set(jul_ratios['产品']) | set(jun_ratios['产品'])
# Only include products that exist in August (our reference month)
common_products = sorted([p for p in all_products if p in aug_ratio['产品'].values])

# Headers
headers = ['产品', '6月本金/2t0', '7月本金/2t0', '8月本金/2t0', '均值', '极差', '6月息费/2t0', '7月息费/2t0', '8月息费/2t0', '息费极差']
for c, h in enumerate(headers, 1):
    cell = ws4.cell(row=5, column=c, value=h)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = center
    cell.border = thin_border
    ws4.column_dimensions[get_column_letter(c)].width = 14
ws4.column_dimensions['A'].width = 20

# Data
r = 6
for product in common_products:
    # 本金/2t0
    u_val = jun_ratios.loc[jun_ratios['产品'] == product, '4t7本金/2t0'].values[0] if product in jun_ratios['产品'].values else np.nan
    j_val = jul_ratios.loc[jul_ratios['产品'] == product, '4t7本金/2t0'].values[0] if product in jul_ratios['产品'].values else np.nan
    a_val = aug_ratio.loc[aug_ratio['产品'] == product, '4t7本金/2t0'].values[0] if product in aug_ratio['产品'].values else np.nan

    # 息费/2t0
    u_xf = jun_ratios.loc[jun_ratios['产品'] == product, '4t7息费/2t0'].values[0] if product in jun_ratios['产品'].values else np.nan
    j_xf = jul_ratios.loc[jul_ratios['产品'] == product, '4t7息费/2t0'].values[0] if product in jul_ratios['产品'].values else np.nan
    a_xf = aug_ratio.loc[aug_ratio['产品'] == product, '4t7息费/2t0'].values[0] if product in aug_ratio['产品'].values else np.nan

    vals = [v for v in [u_val, j_val, a_val] if not np.isnan(v)]
    mean_val = np.mean(vals) if vals else np.nan
    range_val = (max(vals) - min(vals)) if len(vals) > 1 else 0

    xf_vals = [v for v in [u_xf, j_xf, a_xf] if not np.isnan(v)]
    xf_range = (max(xf_vals) - min(xf_vals)) if len(xf_vals) > 1 else 0

    row_data = [product, u_val, j_val, a_val, mean_val, range_val, u_xf, j_xf, a_xf, xf_range]
    for c, val in enumerate(row_data, 1):
        cell = ws4.cell(row=r, column=c)
        if pd.isna(val):
            cell.value = '-'
        elif c == 1:
            cell.value = val
        else:
            cell.value = val
            cell.number_format = '0.0000'
        cell.font = normal_font
        cell.alignment = center if c != 1 else left
        cell.border = thin_border
        # Color code: green for stable, yellow for moderate, red for unstable
        if c == 6 or c == 10:
            if not pd.isna(val):
                if val < 0.05:
                    cell.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
                elif val < 0.10:
                    cell.fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
                else:
                    cell.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
    r += 1

ws4.freeze_panes = 'B6'

# ============================================================
# Sheet 5: 9月实际vs预估对比
# ============================================================
ws5 = wb.create_sheet('9月实际vs预估对比')
ws5.sheet_view.showGridLines = False

ws5['A1'] = '9月4t7预估 vs 部分实际4t7对比'
ws5['A1'].font = title_font
ws5.merge_cells('A1:K1')
ws5.row_dimensions[1].height = 25

ws5['A3'] = '说明: 9月部分早期放款已到达4t7窗口,有实际数据可对比。覆盖率=已出账笔数/总笔数'
ws5['A3'].font = note_font
ws5.merge_cells('A3:K3')

compare_cols = [
    ('产品', '产品', 18),
    ('9月放款笔数', '笔数', 8),
    ('9月放款金额', '金额', 13),
    ('9月4t7出账覆盖率', '覆盖率', 8),
    ('预估4t7本金(三法均值)', '预估本金', 10),
    ('9月实际4t7本金(部分样本)', '实际本金', 10),
    ('本金差异', '本金差异', 10),
    ('预估4t7TR(三法均值)', '预估TR', 10),
    ('9月实际4t7TR(部分样本)', '实际TR', 10),
    ('TR差异', 'TR差异', 10),
]

# Headers
for c, (col_name, header, width) in enumerate(compare_cols, 1):
    cell = ws5.cell(row=5, column=c, value=header)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = center
    cell.border = thin_border
    ws5.column_dimensions[get_column_letter(c)].width = width

# Data
r = 6
for _, row_data in result_df.iterrows():
    est_ben = row_data['预估4t7本金(三法均值)']
    act_ben = row_data['9月实际4t7本金(部分样本)']
    est_tr = row_data['预估4t7TR(三法均值)']
    act_tr = row_data['9月实际4t7TR(部分样本)']

    ben_diff = est_ben - act_ben if not pd.isna(est_ben) and not pd.isna(act_ben) else np.nan
    tr_diff = est_tr - act_tr if not pd.isna(est_tr) and not pd.isna(act_tr) else np.nan

    row_vals = [
        row_data['产品'],
        int(row_data['9月放款笔数']),
        row_data['9月放款金额'],
        row_data['9月4t7出账覆盖率'],
        est_ben, act_ben, ben_diff,
        est_tr, act_tr, tr_diff
    ]

    for c, val in enumerate(row_vals, 1):
        cell = ws5.cell(row=r, column=c)
        if pd.isna(val):
            cell.value = '-'
        elif c == 1:
            cell.value = val
        elif c == 2:
            cell.value = int(val)
            cell.number_format = '#,##0'
        elif c == 3:
            cell.value = val
            cell.number_format = '#,##0.00'
        elif c == 4:
            cell.value = val
            cell.number_format = '0.0%'
        else:
            cell.value = val
            cell.number_format = '0.0000%'
        cell.font = normal_font
        cell.alignment = center if c != 1 else left
        cell.border = thin_border
        # Color difference cells
        if c in [7, 10] and not pd.isna(val):
            if abs(val) < 0.02:
                cell.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
            elif abs(val) < 0.05:
                cell.fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
            else:
                cell.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
    r += 1

ws5.freeze_panes = 'B6'

# Save
wb.save(output_path)
print(f"Excel已保存: {output_path}")
