# -*- coding: utf-8 -*-
"""
评级产品每周 4t7 预估（覆盖率 100% 选优法）— 方式 B：手动上传 Excel

用法:
    # 你自己从 Presto 导出周度文件 + 月度文件后：
    python create_weekly_excel.py \
        --weekly  "D:/xx/评级产品表现-放款月2.xlsx" \
        --monthly "D:/xx/评级产品表现-放款月21.xlsx" \
        --out "D:/xx/9月每周4t7预估.xlsx" \
        --ref-month 2026-08 --target-month 2026-09

    # 目标周/权重默认由 --target-month 自动推导，也可手动指定：
    #   --target-weeks 08-31,09-07,09-14,09-21,09-28
    #   --week-weights 6/7,1,1,1,3/7

    # 被自动取数脚本复用（多 sheet）：
    from create_weekly_excel import build_sheet, derive_target_weeks, derive_week_weights
    build_sheet(wb, '首贷', df_w, df_m, '2026-08', '2026-09', weeks, weights, '总收息_含税')

规则:
    对每个"周×产品"，找覆盖率(出账笔数/放款笔数)=100% 的最晚指标:
        4T7 > 4T0 > 3T0 > 2T0 > 1T3 > 1T0
    4T7 覆盖率=100% -> 直接用实际 4t7 值;
    否则 -> 该指标 × 参考月比率(参考月4t7 / 参考月该指标);
    推荐"无" -> 回退用 1t0 × 比率。
    TR = 总收息 - 4t7本金逾期率 - 4t7息费逾期率(本金分母)

月度聚合(时间加权): 权重 = 该周落在目标月内的天数 / 7
    例: 目标月 9 月 -> 08-31 周仅 6 天(6/7)、09-28 周仅 3 天(3/7)、中间整周权重 1
"""
import os
import sys
import calendar
import argparse
from datetime import date, datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ============================================================
# 默认配置
# ============================================================
DEFAULT_REF_MONTH = '2026-08'     # 参考月(算比率用)
DEFAULT_TARGET_MONTH = '2026-09'  # 目标月(要预估的月)
REVENUE_FIELD = '总收息_含税'      # 总收息口径(含税/不含税)
MIN_AUG_CNT = 3                   # 参考月产品过滤: 放款笔数须 > 该值


def derive_target_weeks(target_month):
    """由目标月 'YYYY-MM' 推导覆盖该月的所有放款周(周一为周起始)，返回 ['MM-DD', ...]。"""
    y, m = int(target_month[:4]), int(target_month[5:7])
    first = date(y, m, 1)
    last = date(y, m, calendar.monthrange(y, m)[1])
    wk = first - timedelta(days=first.weekday())  # 该月第一天所在周的周一
    weeks = []
    while wk <= last:
        weeks.append(wk.strftime('%m-%d'))
        wk += timedelta(days=7)
    return weeks


def derive_week_weights(target_month, target_weeks):
    """周在目标月内的天数 / 7，返回 {'MM-DD': '6/7'|'1'|...}（权重=1 时返回 '1'）。"""
    y, m = int(target_month[:4]), int(target_month[5:7])
    first = date(y, m, 1)
    last = date(y, m, calendar.monthrange(y, m)[1])
    out = {}
    for w in target_weeks:
        ws = datetime.strptime(f'{y}-{w}', '%Y-%m-%d').date()
        if ws.month > m:  # 目标月为 1 月时首周可能落在上一年 12 月
            ws = ws.replace(year=y - 1)
        end = min(last, ws + timedelta(days=6))
        start = max(first, ws)
        d = (end - start).days + 1
        d = max(1, min(7, d))
        out[w] = '1' if d == 7 else f'{d}/7'
    return out


def parse_args():
    ap = argparse.ArgumentParser(description='评级产品每周4t7预估(覆盖率100%法)生成器 — 手动上传Excel')
    ap.add_argument('--weekly', required=True, help='周度文件路径')
    ap.add_argument('--monthly', required=True, help='月度文件路径')
    ap.add_argument('--out', default=None, help='输出Excel路径(默认: 当前目录/{目标月}每周4t7预估.xlsx)')
    ap.add_argument('--ref-month', default=DEFAULT_REF_MONTH, help='参考月 (YYYY-MM)')
    ap.add_argument('--target-month', default=DEFAULT_TARGET_MONTH, help='目标月 (YYYY-MM)')
    ap.add_argument('--revenue-field', default=REVENUE_FIELD, help='总收息字段(含税/不含税)')
    ap.add_argument('--target-weeks', default=None, help='目标周,逗号分隔(默认按目标月自动推导)')
    ap.add_argument('--week-weights', default=None, help='周权重,逗号分隔(默认按目标月自动推导)')
    return ap.parse_args()


def build_sheet(wb, sheet_name, df_w, df_m, ref_month, target_month,
                target_weeks, week_weights, revenue_field='总收息_含税',
                min_aug_cnt=3):
    """从周度/月度原始 DataFrame 构建一个预估 sheet(写入 wb, 返回 sheet 对象)。

    df_w: 周度原始 DataFrame, 须含列 issue_week, 产品, 放款笔数, 放款金额, 平均期限,
          is_t0_window_1, is_t3_window_1, is_t0_window_2, is_t0_window_3,
          is_t0_window_4, is_t7_window_4, 总收息_含税, 1t0本金逾期率, 1t3本金逾期率,
          2t0本金逾期率, 3t0本金逾期率, 4t0本金逾期率, 4t7本金逾期率, 4t7息费逾期率_本金分母
    df_m: 月度原始 DataFrame, 须含列 放款月份, 产品, 放款笔数, 放款金额, 平均期限 + 同上指标列
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

    print(f"[{sheet_name}] 目标周数: {len(target_weeks)}, {ref_month} 参考产品(>{min_aug_cnt}笔): {len(aug_m)}, "
          f"{target_month} 产品: {len(sep_m)}")
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
        # 目标月输入
        ('S', 19, 'sep', '总收息', 8, input_f),
        ('T', 20, 'sep', '1t0', 8, input_f), ('U', 21, 'sep', '1t3', 8, input_f),
        ('V', 22, 'sep', '2t0', 8, input_f), ('W', 23, 'sep', '3t0', 8, input_f),
        ('X', 24, 'sep', '4t0', 8, input_f),
        ('Y', 25, 'sep', '4t7本', 8, input_f), ('Z', 26, 'sep', '4t7息', 8, input_f),
        # 参考月原始(输入)
        ('AA', 27, 'aug', f'参考月1t0', 9, input_f), ('AB', 28, 'aug', f'参考月1t3', 9, input_f),
        ('AC', 29, 'aug', f'参考月2t0', 9, input_f), ('AD', 30, 'aug', f'参考月3t0', 9, input_f),
        ('AE', 31, 'aug', f'参考月4t0', 9, input_f),
        ('AF', 32, 'aug', f'参考月4t7本', 11, input_f), ('AG', 33, 'aug', f'参考月4t7息', 11, input_f),
        # 参考月比率-本金(公式)
        ('AH', 34, 'rb', '本/1t0', 7, ratio_f), ('AI', 35, 'rb', '本/1t3', 7, ratio_f),
        ('AJ', 36, 'rb', '本/2t0', 7, ratio_f), ('AK', 37, 'rb', '本/3t0', 7, ratio_f),
        ('AL', 38, 'rb', '本/4t0', 7, ratio_f),
        # 参考月比率-息费(公式)
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
        'sep': '目标月输入(原始)', 'aug': '参考月原始(参考)', 'rb': '参考月比率-本金(公式)',
        'rx': '参考月比率-息费(公式)', 'est': '最终预估(公式)', 'flag': '标记'
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
    ws['A1'] = f'{target_month} 每周4t7预估(覆盖率100%选优法) — 共{len(target_weeks)}周'
    ws['A1'].font = tfont
    ws.merge_cells('A1:AU1')
    ws.row_dimensions[1].height = 25
    ws['A2'] = ('规则: 找覆盖率=100%的最晚指标(4T7>4T0>3T0>2T0>1T3>1T0)→该指标×'
                f'{ref_month}比率(4t7/该指标); 4T7=100%则直接用实际值; 推荐"无"时回退用1t0×比率; '
                f'TR=总收息-4t7本金-4t7息费')
    ws['A2'].font = nfont2
    ws.merge_cells('A2:AU2')
    ws['A3'] = (f'月度聚合为时间加权: 首周仅{week_weights[target_weeks[0]]}、'
                f'末周仅{week_weights[target_weeks[-1]]}、中间整周权重1')
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

            # 参考月行: 直接命中, 否则 fallback 到"期限相同 + 总收息最接近"的参考月产品
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

            # 推荐指标 R(嵌套 IF: 4T7>4T0>3T0>2T0>1T3>1T0)
            ws.cell(row=r, column=18,
                    value=(f'=IF(Q{r}=1,"4T7",IF(P{r}=1,"4T0",IF(O{r}=1,"3T0",'
                           f'IF(N{r}=1,"2T0",IF(M{r}=1,"1T3",IF(L{r}=1,"1T0","无"))))))')
                    ).alignment = ctr

            # 目标月输入 S-Z
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

            # 参考月原始 AA-AG
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
                    ws.cell(row=r, column=c, value='无参考月').font = nfont2

            # 参考月比率-本金 AH-AL(公式 = AF/AA ~ AF/AE)
            if aug_row is not None:
                for ci in range(5):
                    aug_col = get_column_letter(27 + ci)
                    ws.cell(row=r, column=34 + ci,
                            value=f'=IF({aug_col}{r}=0,"-",AF{r}/{aug_col}{r})').number_format = RATIO
                # 参考月比率-息费 AM-AQ(公式 = AG/AA ~ AG/AE)
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

            # 无历史表现参考产品标记 AU
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
    # 月度聚合(时间加权, 从各周汇总行)
    # ============================================================
    r += 1
    ws.cell(row=r, column=1, value=f'{target_month} 月度聚合(时间加权)').font = Font(
        name='微软雅黑', size=12, bold=True, color='1F4E79')
    for c in range(1, NCOLS + 1):
        ws.cell(row=r, column=c).fill = sfill
        ws.cell(row=r, column=c).border = thin
    r += 1

    month_row = r

    def wt(week_str):
        """返回周权重字符串; 权重=1 时返回 '1'"""
        return week_weights.get(week_str, '1')

    def num(cell, week_str, wr):
        """生成分子项: D*指标*权重; 权重=1 时省略"""
        w = wt(week_str)
        if w == '1':
            return f'D{wr}*{cell}{wr}'
        return f'D{wr}*{cell}{wr}*{w}'

    def den(week_str, wr):
        """生成分母项: D*权重; 权重=1 时省略"""
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

    # 目标周 / 权重: 默认按目标月自动推导, 也可命令行覆盖
    if args.target_weeks:
        target_weeks = [x.strip() for x in args.target_weeks.split(',') if x.strip()]
    else:
        target_weeks = derive_target_weeks(args.target_month)
    if args.week_weights:
        ws_list = [x.strip() for x in args.week_weights.split(',') if x.strip()]
        week_weights = dict(zip(target_weeks, ws_list))
    else:
        week_weights = derive_week_weights(args.target_month, target_weeks)

    out_path = args.out or os.path.join(os.getcwd(), f'{args.target_month}每周4t7预估.xlsx')

    df_w = pd.read_excel(args.weekly, sheet_name=0)
    df_m = pd.read_excel(args.monthly, sheet_name=0)

    wb = Workbook()
    build_sheet(wb, f'{args.target_month}每周4t7预估', df_w, df_m,
                args.ref_month, args.target_month,
                target_weeks, week_weights, args.revenue_field)
    wb.save(out_path)
    print(f"\n目标周: {target_weeks}")
    print(f"周权重: {week_weights}")
    print(f"已保存: {out_path}")


if __name__ == '__main__':
    main()
