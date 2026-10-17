# -*- coding: utf-8 -*-
"""
9月每周4t7预估（覆盖率100%选优法）— 生成器

用法示例:
    # 全部用默认路径(周度文件 + 月度文件在 Downloads)
    python create_weekly_excel.py

    # 指定文件
    python create_weekly_excel.py --weekly "D:/xx/评级产品表现-放款月2.xlsx" \
                                  --monthly "D:/xx/评级产品表现-放款月21.xlsx" \
                                  --out "D:/xx/9月每周4t7预估.xlsx"

    # 被自动化取数脚本复用(多个sheet)
    from create_weekly_excel import build_sheet
    build_sheet(wb, '首贷', df_w_new, df_m_new, '2026-08', '2026-09', ...)

规则:
    对每个"周×产品", 找覆盖率(出账笔数/放款笔数)=100%的最晚指标:
        4T7 > 4T0 > 3T0 > 2T0 > 1T3 > 1T0
    4T7覆盖率=100% -> 直接用实际4t7值;
    否则 -> 该指标 × 8月比率(8月4t7 / 8月该指标);
    推荐"无" -> 回退用 1t0 × 8月比率。
    TR = 总收息 - 4t7本金逾期率 - 4t7息费逾期率(本金分母)

月度聚合(时间加权):
    首个周(08-31)在目标月仅6天 -> 权重 6/7
    中间整周 -> 权重 1
    末个周(09-28)在目标月仅3天 -> 权重 3/7
"""
import sys
import argparse

sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ============================================================
# 默认配置（用户每次只需替换这4个路径/参数）
# ============================================================
DEFAULT_WEEKLY = r"d:\Documents\Downloads\评级产品表现-放款月2 (1).xlsx"
DEFAULT_MONTHLY = r"d:\Documents\Downloads\评级产品表现-放款月21.xlsx"
DEFAULT_OUT = r"D:\Documents\Downloads\9月每周4t7预估(覆盖率100%法).xlsx"
DEFAULT_REF_MONTH = '2026-08'   # 参考月(用于算比率)
DEFAULT_TARGET_MONTH = '2026-09'  # 目标月(要预估的月)
DEFAULT_TARGET_WEEKS = ['08-31', '09-07', '09-14', '09-21', '09-28']
# 各周在目标月内的天数权重(分子=落在目标月的天数)
DEFAULT_WEEK_WEIGHTS = {
    '08-31': '6/7',
    '09-07': '1',
    '09-14': '1',
    '09-21': '1',
    '09-28': '3/7',
}
# 总收息口径: 含税 或 不含税
REVENUE_FIELD = '总收息_含税'
# 参考月产品过滤: 放款笔数须大于该值
MIN_AUG_CNT = 3


def parse_args():
    ap = argparse.ArgumentParser(description='9月每周4t7预估(覆盖率100%法)生成器')
    ap.add_argument('--weekly', default=DEFAULT_WEEKLY, help='周度文件路径')
    ap.add_argument('--monthly', default=DEFAULT_MONTHLY, help='月度文件路径')
    ap.add_argument('--out', default=DEFAULT_OUT, help='输出Excel路径')
    ap.add_argument('--ref-month', default=DEFAULT_REF_MONTH, help='参考月(比率)')
    ap.add_argument('--target-month', default=DEFAULT_TARGET_MONTH, help='目标月(预估)')
    ap.add_argument('--revenue-field', default=REVENUE_FIELD, help='总收息字段(含税/不含税)')
    return ap.parse_args()


def build_sheet(wb, sheet_name, df_w, df_m, ref_month, target_month,
                target_weeks, week_weights, revenue_field='总收息_含税',
                min_aug_cnt=3):
    """从周度/月度原始DataFrame构建一个预估sheet(写入wb, 返回sheet对象)。

    df_w: 周度原始DataFrame, 须含列 issue_week, 产品, 放款笔数, 放款金额, 平均期限,
          is_t0_window_1, is_t3_window_1, is_t0_window_2, is_t0_window_3,
          is_t0_window_4, is_t7_window_4, 总收息_含税, 1t0本金逾期率, 1t3本金逾期率,
          2t0本金逾期率, 3t0本金逾期率, 4t0本金逾期率, 4t7本金逾期率, 4t7息费逾期率_本金分母
    df_m: 月度原始DataFrame, 须含列 放款月份, 产品, 放款笔数, 放款金额, 平均期限 + 同上指标列
    """
    # ---- 周度处理 ----
    df_w = df_w.copy()
    df_w['issue_week'] = df_w['issue_week'].ffill()
    df_w = df_w[df_w['产品'].notna()].copy()
    df_w['week'] = df_w['issue_week'].apply(lambda x: pd.to_datetime(x, errors='coerce'))
    df_w = df_w[df_w['week'].notna()].copy()
    df_w['week_str'] = df_w['week'].dt.strftime('%m-%d')
    sep_weeks = df_w[df_w['week_str'].isin(target_weeks)].copy()

    # ---- 月度处理 ----
    df_m = df_m.copy()
    df_m['放款月份'] = df_m['放款月份'].ffill()
    df_m['月份'] = df_m['放款月份'].astype(str).str[:7]
    aug_m = df_m[(df_m['月份'] == ref_month) & df_m['产品'].notna() & (df_m['放款笔数'] > min_aug_cnt)].copy()
    sep_m = df_m[(df_m['月份'] == target_month) & df_m['产品'].notna()].copy()
    aug_by_product = aug_m.set_index('产品')

    print(f"[{sheet_name}] 目标周数: {len(target_weeks)}, {ref_month}参考产品(>{min_aug_cnt}笔): {len(aug_m)}, "
          f"{target_month}产品: {len(sep_m)}")
    print(f"[{sheet_name}] 总收息字段: {revenue_field}")

    # ============================================================
    # 样式
    # ============================================================
    thin = Border(left=Side('thin'), right=Side('thin'), top=Side('thin'), bottom=Side('thin'))
    hfill = PatternFill('solid', fgColor='4472C4')
    hfont = Font(name='微软雅黑', size=10, bold=True, color='FFFFFF')
    sfill = PatternFill('solid', fgColor='D9E2F3')
    sfont = Font(name='微软雅黑', size=10, bold=True, color='1F4E79')
    input_f = PatternFill('solid', fgColor='FFF2CC')
    cov_f = PatternFill('solid', fgColor='F2F2F2')
    rec_f = PatternFill('solid', fgColor='BDD7EE')
    ratio_f = PatternFill('solid', fgColor='E2EFDA')
    est_f = PatternFill('solid', fgColor='FCE4D6')
    sum_f = PatternFill('solid', fgColor='C6E0B4')
    month_f = PatternFill('solid', fgColor='FFD966')
    nfont = Font(name='微软雅黑', size=10)
    tfont = Font(name='微软雅黑', size=14, bold=True, color='1F4E79')
    nfont2 = Font(name='微软雅黑', size=9, color='808080', italic=True)
    ctr = Alignment('center', 'center', wrap_text=True)
    PCT = '0.0%'
    RATIO = '0.00'
    NUM = '#,##0'

    # ============================================================
    # Sheet
    # ============================================================
    ws = wb.create_sheet(title=sheet_name)
    ws.sheet_view.showGridLines = False

    # 列定义: (字母, 序号, 分组, 子表头, 宽度, 填充)
    col_defs = [
        ('A', 1, 'info', '周次', 8, input_f), ('B', 2, 'info', '产品', 22, input_f),
        ('C', 3, 'info', '笔数', 8, input_f), ('D', 4, 'info', '金额', 12, input_f),
        ('E', 5, 'info', '期限', 6, input_f),
        # 出账笔数(输入)
        ('F', 6, 'cnt', '1T0出账', 8, input_f), ('G', 7, 'cnt', '1T3出账', 8, input_f),
        ('H', 8, 'cnt', '2T0出账', 8, input_f), ('I', 9, 'cnt', '3T0出账', 8, input_f),
        ('J', 10, 'cnt', '4T0出账', 8, input_f), ('K', 11, 'cnt', '4T7出账', 8, input_f),
        # 覆盖率(公式)
        ('L', 12, 'cov', '1T0%', 7, cov_f), ('M', 13, 'cov', '1T3%', 7, cov_f),
        ('N', 14, 'cov', '2T0%', 7, cov_f), ('O', 15, 'cov', '3T0%', 7, cov_f),
        ('P', 16, 'cov', '4T0%', 7, cov_f), ('Q', 17, 'cov', '4T7%', 7, cov_f),
        # 推荐指标(公式)
        ('R', 18, 'rec', '推荐', 7, rec_f),
        # 9月输入
        ('S', 19, 'sep', '总收息', 8, input_f),
        ('T', 20, 'sep', '9月1t0', 8, input_f), ('U', 21, 'sep', '9月1t3', 8, input_f),
        ('V', 22, 'sep', '9月2t0', 8, input_f), ('W', 23, 'sep', '9月3t0', 8, input_f),
        ('X', 24, 'sep', '9月4t0', 8, input_f),
        ('Y', 25, 'sep', '9月4t7本', 8, input_f), ('Z', 26, 'sep', '9月4t7息', 8, input_f),
        # 8月原始(输入)
        ('AA', 27, 'aug', '8月1t0', 7, input_f), ('AB', 28, 'aug', '8月1t3', 7, input_f),
        ('AC', 29, 'aug', '8月2t0', 7, input_f), ('AD', 30, 'aug', '8月3t0', 7, input_f),
        ('AE', 31, 'aug', '8月4t0', 7, input_f),
        ('AF', 32, 'aug', '8月4t7本', 7, input_f), ('AG', 33, 'aug', '8月4t7息', 7, input_f),
        # 8月比率-本金(公式)
        ('AH', 34, 'rb', '本/1t0', 7, ratio_f), ('AI', 35, 'rb', '本/1t3', 7, ratio_f),
        ('AJ', 36, 'rb', '本/2t0', 7, ratio_f), ('AK', 37, 'rb', '本/3t0', 7, ratio_f),
        ('AL', 38, 'rb', '本/4t0', 7, ratio_f),
        # 8月比率-息费(公式)
        ('AM', 39, 'rx', '息/1t0', 7, ratio_f), ('AN', 40, 'rx', '息/1t3', 7, ratio_f),
        ('AO', 41, 'rx', '息/2t0', 7, ratio_f), ('AP', 42, 'rx', '息/3t0', 7, ratio_f),
        ('AQ', 43, 'rx', '息/4t0', 7, ratio_f),
        # 预估(公式)
        ('AR', 44, 'est', '预估4t7本', 9, est_f), ('AS', 45, 'est', '预估4t7息', 9, est_f),
        ('AT', 46, 'est', '预估4t7TR', 9, est_f),
        ('AU', 47, 'flag', '无历史表现参考产品', 13, input_f),
    ]
    NCOLS = len(col_defs)

    # 分组表头(第4行)
    gmap = {}
    for cd in col_defs:
        g = cd[2]
        if g not in gmap:
            gmap[g] = [cd[1], cd[1]]
        else:
            gmap[g][1] = cd[1]

    gnames = {
        'info': '产品信息', 'cnt': '出账笔数(输入)', 'cov': '覆盖率(公式)', 'rec': '推荐指标',
        'sep': '9月输入(原始)', 'aug': '8月原始(参考)', 'rb': '8月比率-本金(公式)',
        'rx': '8月比率-息费(公式)', 'est': '最终预估(公式)', 'flag': '标记'
    }
    for g, (s, e) in gmap.items():
        c = ws.cell(row=4, column=s, value=gnames[g])
        c.font = sfont
        c.fill = sfill
        c.alignment = ctr
        c.border = thin
        if s != e:
            ws.merge_cells(start_row=4, start_column=s, end_row=4, end_column=e)

    # 子表头(第5行)
    for cd in col_defs:
        L, idx, _, sh, w, f = cd
        c = ws.cell(row=5, column=idx, value=sh)
        c.font = hfont
        c.fill = hfill
        c.alignment = ctr
        c.border = thin
        ws.column_dimensions[L].width = w
    ws.row_dimensions[4].height = 20
    ws.row_dimensions[5].height = 16

    # 标题
    ws['A1'] = f'{target_month}每周4t7预估(覆盖率100%选优法) — 共{len(target_weeks)}周'
    ws['A1'].font = tfont
    ws.merge_cells('A1:AU1')
    ws.row_dimensions[1].height = 25
    ws['A2'] = ('规则: 找覆盖率=100%的最晚指标(4T7>4T0>3T0>2T0>1T3>1T0)→该指标×'
                f'{ref_month}比率(4t7/该指标); 4T7=100%则直接用实际值; 推荐"无"时回退用1t0×比率; '
                f'TR=总收息-4t7本金-4t7息费')
    ws['A2'].font = nfont2
    ws.merge_cells('A2:AU2')
    ws['A3'] = f'月度聚合为时间加权: 首周仅{week_weights[target_weeks[0]]}、末周仅{week_weights[target_weeks[-1]]}、中间整周权重1'
    ws['A3'].font = nfont2
    ws.merge_cells('A3:AU3')

    # ============================================================
    # 写数据行
    # ============================================================
    r = 6
    weekly_summaries = []  # (week_str, summary_row, week_start, week_end)

    for w in target_weeks:
        wdata = sep_weeks[sep_weeks['week_str'] == w].copy()
        wdata = wdata.sort_values('产品').reset_index(drop=True)
        if len(wdata) == 0:
            print(f"  [警告] 周 {w} 无数据, 跳过")
            continue

        # 周分隔行
        ws.cell(row=r, column=1, value=f'--- {w} ---').font = sfont
        for c in range(1, NCOLS + 1):
            ws.cell(row=r, column=c).fill = sfill
            ws.cell(row=r, column=c).border = thin
        r += 1

        week_start = r
        for _, srow in wdata.iterrows():
            product = srow['产品']
            has_aug = product in aug_by_product.index
            term = srow['平均期限']
            cycle = f'{int(term)}天' if pd.notna(term) else '-'

            # 8月参考行: 直接命中, 否则fallback到"期限相同+总收息最接近"的8月产品
            aug_row = aug_by_product.loc[product] if has_aug else None
            fb_label = None
            if aug_row is None and len(aug_m) > 0:
                cand = aug_m[aug_m['平均期限'] == term].copy()
                if len(cand) == 0:
                    cand = aug_m.copy()
                cand = cand[cand[revenue_field].notna()].copy()
                if len(cand) > 0:
                    rev_target = srow[revenue_field] if pd.notna(srow[revenue_field]) else 0
                    cand = cand.copy()
                    cand['_dist'] = (cand[revenue_field] - rev_target).abs()
                    aug_row = cand.sort_values('_dist').iloc[0]
                    fb_label = aug_row['产品']

            # 产品信息 A-E
            ws.cell(row=r, column=1, value=w)
            ws.cell(row=r, column=2, value=product)
            ws.cell(row=r, column=3, value=int(srow['放款笔数'])).number_format = NUM
            ws.cell(row=r, column=4, value=float(srow['放款金额'])).number_format = NUM
            ws.cell(row=r, column=5, value=cycle).alignment = ctr

            # 出账笔数 F-K(输入)
            cnt_cols = ['is_t0_window_1', 'is_t3_window_1', 'is_t0_window_2',
                        'is_t0_window_3', 'is_t0_window_4', 'is_t7_window_4']
            for ci, col in enumerate(cnt_cols):
                v = srow[col] if col in srow.index and pd.notna(srow[col]) else 0
                ws.cell(row=r, column=6 + ci, value=int(v)).number_format = NUM

            # 覆盖率 L-Q(公式 = 出账笔数/放款笔数)
            for ci in range(6):
                cnt_col = get_column_letter(6 + ci)  # F-K
                ws.cell(row=r, column=12 + ci,
                        value=f'=IF(C{r}=0,0,{cnt_col}{r}/C{r})').number_format = PCT

            # 推荐指标 R(嵌套IF: 4T7>4T0>3T0>2T0>1T3>1T0)
            ws.cell(row=r, column=18,
                    value=(f'=IF(Q{r}=1,"4T7",IF(P{r}=1,"4T0",IF(O{r}=1,"3T0",'
                           f'IF(N{r}=1,"2T0",IF(M{r}=1,"1T3",IF(L{r}=1,"1T0","无"))))))')
                    ).alignment = ctr

            # 9月输入 S-Z
            ws.cell(row=r, column=19,
                    value=float(srow[revenue_field]) if pd.notna(srow[revenue_field]) else 0
                    ).number_format = PCT
            ind_cols = ['1t0本金逾期率', '1t3本金逾期率', '2t0本金逾期率',
                        '3t0本金逾期率', '4t0本金逾期率']
            for ci, col in enumerate(ind_cols):
                v = srow[col] if col in srow.index and pd.notna(srow[col]) else 0
                ws.cell(row=r, column=20 + ci, value=float(v)).number_format = PCT
            ws.cell(row=r, column=25,
                    value=float(srow['4t7本金逾期率']) if pd.notna(srow['4t7本金逾期率']) else 0
                    ).number_format = PCT
            ws.cell(row=r, column=26,
                    value=float(srow['4t7息费逾期率_本金分母']) if pd.notna(srow['4t7息费逾期率_本金分母']) else 0
                    ).number_format = PCT

            # 8月原始 AA-AG
            if aug_row is not None:
                a = aug_row
                for ci, col in enumerate(ind_cols):
                    ws.cell(row=r, column=27 + ci,
                            value=float(a[col]) if pd.notna(a[col]) else 0).number_format = PCT
                ws.cell(row=r, column=32,
                        value=float(a['4t7本金逾期率']) if pd.notna(a['4t7本金逾期率']) else 0
                        ).number_format = PCT
                ws.cell(row=r, column=33,
                        value=float(a['4t7息费逾期率_本金分母']) if pd.notna(a['4t7息费逾期率_本金分母']) else 0
                        ).number_format = PCT
            else:
                for c in range(27, 34):
                    ws.cell(row=r, column=c, value='无8月').font = nfont2

            # 8月比率-本金 AH-AL(公式 = AF/AA ~ AF/AE)
            if aug_row is not None:
                for ci in range(5):
                    aug_col = get_column_letter(27 + ci)
                    ws.cell(row=r, column=34 + ci,
                            value=f'=IF({aug_col}{r}=0,"-",AF{r}/{aug_col}{r})').number_format = RATIO
                # 8月比率-息费 AM-AQ(公式 = AG/AA ~ AG/AE)
                for ci in range(5):
                    aug_col = get_column_letter(27 + ci)
                    ws.cell(row=r, column=39 + ci,
                            value=f'=IF({aug_col}{r}=0,"-",AG{r}/{aug_col}{r})').number_format = RATIO
            else:
                for c in range(34, 44):
                    ws.cell(row=r, column=c, value='-').font = nfont2

            # 预估4t7本金 AR(公式)
            ar_f = (f'=IFERROR(IF(R{r}="4T7",Y{r},'
                    f'IF(R{r}="4T0",X{r}*AL{r},'
                    f'IF(R{r}="3T0",W{r}*AK{r},'
                    f'IF(R{r}="2T0",V{r}*AJ{r},'
                    f'IF(R{r}="1T3",U{r}*AI{r},'
                    f'IF(R{r}="1T0",T{r}*AH{r},'
                    f'T{r}*AH{r})))))),0)')
            ws.cell(row=r, column=44, value=ar_f).number_format = PCT

            # 预估4t7息费 AS(公式)
            as_f = (f'=IFERROR(IF(R{r}="4T7",Z{r},'
                    f'IF(R{r}="4T0",X{r}*AQ{r},'
                    f'IF(R{r}="3T0",W{r}*AP{r},'
                    f'IF(R{r}="2T0",V{r}*AO{r},'
                    f'IF(R{r}="1T3",U{r}*AN{r},'
                    f'IF(R{r}="1T0",T{r}*AM{r},'
                    f'T{r}*AM{r})))))),0)')
            ws.cell(row=r, column=45, value=as_f).number_format = PCT

            # 预估4t7TR AT = 总收息 - 本金 - 息费
            ws.cell(row=r, column=46, value=f'=S{r}-AR{r}-AS{r}').number_format = PCT

            # 无历史表现参考产品标记 AU: 8月无参考且无期限相同的fallback
            if has_aug:
                flag = ''
            elif fb_label is None:
                flag = '无历史表现参考产品'
            else:
                flag = f'无直接参考,采用:{fb_label}'
            ws.cell(row=r, column=47, value=flag)

            # 填充/边框/字体
            for ci, cd in enumerate(col_defs):
                cell = ws.cell(row=r, column=ci + 1)
                cell.fill = cd[5]
                cell.border = thin
                if cell.font is None or not cell.font.bold:
                    cell.font = nfont

            r += 1

        week_end = r - 1
        # 周加权汇总行(按放款金额加权)
        ws.cell(row=r, column=1, value=f'{w} 加权汇总').font = sfont
        ws.cell(row=r, column=2, value='').font = sfont
        ws.cell(row=r, column=3, value=f'=SUM(C{week_start}:C{week_end})').number_format = NUM
        ws.cell(row=r, column=4, value=f'=SUM(D{week_start}:D{week_end})').number_format = NUM
        ws.cell(row=r, column=44,
                value=f'=IFERROR(SUMPRODUCT(D{week_start}:D{week_end},AR{week_start}:AR{week_end})/SUM(D{week_start}:D{week_end}),0)'
                ).number_format = PCT
        ws.cell(row=r, column=45,
                value=f'=IFERROR(SUMPRODUCT(D{week_start}:D{week_end},AS{week_start}:AS{week_end})/SUM(D{week_start}:D{week_end}),0)'
                ).number_format = PCT
        ws.cell(row=r, column=46,
                value=f'=IFERROR(SUMPRODUCT(D{week_start}:D{week_end},AT{week_start}:AT{week_end})/SUM(D{week_start}:D{week_end}),0)'
                ).number_format = PCT
        for c in range(1, NCOLS + 1):
            ws.cell(row=r, column=c).fill = sum_f
            ws.cell(row=r, column=c).border = thin
            ws.cell(row=r, column=c).font = sfont
        weekly_summaries.append((w, r, week_start, week_end))
        r += 1

    # ============================================================
    # 月度聚合(时间加权, 从5个周汇总行)
    # ============================================================
    r += 1
    ws.cell(row=r, column=1, value='9月月度聚合(时间加权)').font = Font(name='微软雅黑', size=12, bold=True, color='1F4E79')
    for c in range(1, NCOLS + 1):
        ws.cell(row=r, column=c).fill = sfill
        ws.cell(row=r, column=c).border = thin
    r += 1

    month_row = r

    def wt(week_str):
        """返回周权重字符串; 权重=1时返回'1'"""
        return week_weights.get(week_str, '1')

    def num(cell, week_str, wr):
        """生成分子项: D*指标*权重; 权重=1时省略"""
        w = wt(week_str)
        if w == '1':
            return f'D{wr}*{cell}{wr}'
        return f'D{wr}*{cell}{wr}*{w}'

    def den(week_str, wr):
        """生成分母项: D*权重; 权重=1时省略"""
        w = wt(week_str)
        if w == '1':
            return f'D{wr}'
        return f'D{wr}*{w}'

    num_ar = [num('AR', w, wr) for w, wr, _, _ in weekly_summaries]
    num_as = [num('AS', w, wr) for w, wr, _, _ in weekly_summaries]
    num_at = [num('AT', w, wr) for w, wr, _, _ in weekly_summaries]
    den_all = [den(w, wr) for w, wr, _, _ in weekly_summaries]

    ws.cell(row=r, column=1, value='月聚合').font = sfont
    ws.cell(row=r, column=3,
            value=f'=SUM({",".join([f"C{wr}" for _, wr, _, _ in weekly_summaries])})').number_format = NUM
    ws.cell(row=r, column=4,
            value=f'=SUM({",".join([f"D{wr}" for _, wr, _, _ in weekly_summaries])})').number_format = NUM
    ws.cell(row=r, column=44,
            value=f'=IFERROR(({"+".join(num_ar)})/({"+".join(den_all)}),0)').number_format = PCT
    ws.cell(row=r, column=45,
            value=f'=IFERROR(({"+".join(num_as)})/({"+".join(den_all)}),0)').number_format = PCT
    ws.cell(row=r, column=46,
            value=f'=IFERROR(({"+".join(num_at)})/({"+".join(den_all)}),0)').number_format = PCT
    for c in range(1, NCOLS + 1):
        ws.cell(row=r, column=c).fill = month_f
        ws.cell(row=r, column=c).border = thin
        ws.cell(row=r, column=c).font = sfont
    r += 1

    # 冻结窗格(冻结前5行 + 前2列)
    ws.freeze_panes = 'C6'

    return ws


def main():
    args = parse_args()
    df_w = pd.read_excel(args.weekly, sheet_name=0)
    df_m = pd.read_excel(args.monthly, sheet_name=0)

    wb = Workbook()
    build_sheet(wb, '9月每周4t7预估', df_w, df_m,
                args.ref_month, args.target_month,
                DEFAULT_TARGET_WEEKS, DEFAULT_WEEK_WEIGHTS,
                args.revenue_field)
    wb.save(args.out)
    print(f"\n已保存: {args.out}")


if __name__ == '__main__':
    main()
