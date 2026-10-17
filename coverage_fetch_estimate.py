# -*- coding: utf-8 -*-
"""
覆盖率100%选优法 — 全自动取数 + 预估（首贷/复贷两个sheet）

流程:
    1. 用 SQL 从 mx.wxs_application_funnel 取出 Excel 中"需要手动输入"的数据
       (周度按 issue_week、月度按 issue_month, 首贷 is_reloan='new' / 复贷 'old')
    2. 在 Python 中计算各逾期率指标(比率), 其中:
       总收息_含税 = (SUM(haircut_amount) + SUM(should_interest)) / SUM(contract_amount)
    3. 复用 create_weekly_excel.build_sheet 跑覆盖率100%选优预估,
       分"首贷""复贷"两个 sheet 输出最终 Excel

用法:
    python coverage_fetch_estimate.py
"""
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'e:\岳松个人文件\嘉银工作内容的整理\code')

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from mexico_presto import PrestoQuery
from create_weekly_excel import build_sheet, DEFAULT_TARGET_WEEKS, DEFAULT_WEEK_WEIGHTS

REF_MONTH = '2026-08'
TARGET_MONTH = '2026-09'
REVENUE_FIELD = '总收息_含税'

OUT_XLSX = r'e:\岳松个人文件\嘉银工作内容的整理\code\9月每周4t7预估_自动取数_首贷复贷_v2.xlsx'
CACHE_CSV = r'e:\岳松个人文件\嘉银工作内容的整理\code\_coverage_raw_cache.csv'

# 取数 SQL: 一条查询同时含周度/月度两个时间维度, 后续在 Python 中再分组
SQL = """
SELECT
    f.is_reloan,
    COALESCE(NULLIF(TRIM(y.product_name_new), ''), f.product_name) AS product_name,
    f.loan_cycle,
    CAST(f.issue_week  AS VARCHAR) AS issue_week,
    CAST(f.issue_month AS VARCHAR) AS issue_month,
    SUM(f.contract_amount)       AS contract_amount,
    SUM(f.haircut_amount)        AS haircut_amount,
    SUM(f.should_interest)       AS should_interest,
    SUM(f.if_issue)              AS issue_cnt,
    SUM(f.t0_should_capit_1)     AS t0_should_capit_1,
    SUM(f.t0_overdue_capit_1)    AS t0_overdue_capit_1,
    SUM(f.t3_should_capit_1)     AS t3_should_capit_1,
    SUM(f.t3_overdue_capit_1)    AS t3_overdue_capit_1,
    SUM(f.t0_should_capit_2)     AS t0_should_capit_2,
    SUM(f.t0_overdue_capit_2)    AS t0_overdue_capit_2,
    SUM(f.t0_should_capit_3)     AS t0_should_capit_3,
    SUM(f.t0_overdue_capit_3)    AS t0_overdue_capit_3,
    SUM(f.t0_should_capit_4)     AS t0_should_capit_4,
    SUM(f.t0_overdue_capit_4)    AS t0_overdue_capit_4,
    SUM(f.t7_should_capit_1)     AS t7_should_capit_1,
    SUM(f.t7_overdue_capit_1)    AS t7_overdue_capit_1,
    SUM(f.t7_should_capit_2)     AS t7_should_capit_2,
    SUM(f.t7_overdue_capit_2)    AS t7_overdue_capit_2,
    SUM(f.t7_should_capit_3)     AS t7_should_capit_3,
    SUM(f.t7_overdue_capit_3)    AS t7_overdue_capit_3,
    SUM(f.t7_should_capit_4)     AS t7_should_capit_4,
    SUM(f.t7_overdue_capit_4)    AS t7_overdue_capit_4,
    SUM(f.t7_overdue_interest_4) AS t7_overdue_interest_4,
    SUM(f.is_t0_window_1)        AS is_t0_window_1,
    SUM(f.is_t3_window_1)        AS is_t3_window_1,
    SUM(f.is_t0_window_2)        AS is_t0_window_2,
    SUM(f.is_t0_window_3)        AS is_t0_window_3,
    SUM(f.is_t0_window_4)        AS is_t0_window_4,
    SUM(f.is_t7_window_4)        AS is_t7_window_4
FROM mx.wxs_application_funnel f
LEFT JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
WHERE f.if_issue = 1
  AND f.is_reloan IN ('new', 'old')
  AND f.app_time >= CAST('2026-01-01 00:00:00.000' AS TIMESTAMP)
GROUP BY 1, 2, 3, 4, 5
"""

# 数值求和列(分组后累加), 比率列后续在 Python 中计算
SUM_COLS = [
    'contract_amount', 'haircut_amount', 'should_interest', 'issue_cnt',
    't0_should_capit_1', 't0_overdue_capit_1',
    't3_should_capit_1', 't3_overdue_capit_1',
    't0_should_capit_2', 't0_overdue_capit_2',
    't0_should_capit_3', 't0_overdue_capit_3',
    't0_should_capit_4', 't0_overdue_capit_4',
    't7_should_capit_1', 't7_overdue_capit_1',
    't7_should_capit_2', 't7_overdue_capit_2',
    't7_should_capit_3', 't7_overdue_capit_3',
    't7_should_capit_4', 't7_overdue_capit_4', 't7_overdue_interest_4',
    'is_t0_window_1', 'is_t3_window_1', 'is_t0_window_2',
    'is_t0_window_3', 'is_t0_window_4', 'is_t7_window_4',
]

# Excel 指标列名 -> 分子/分母(sum列) 映射
RATE_DEFS = {
    '总收息_含税': ('haircut_amount__should_interest', 'contract_amount'),
    '1t0本金逾期率': ('t0_overdue_capit_1', 't0_should_capit_1'),
    '1t3本金逾期率': ('t3_overdue_capit_1', 't3_should_capit_1'),
    '2t0本金逾期率': ('t0_overdue_capit_2', 't0_should_capit_2'),
    '3t0本金逾期率': ('t0_overdue_capit_3', 't0_should_capit_3'),
    '4t0本金逾期率': ('t0_overdue_capit_4', 't0_should_capit_4'),
    '4t7本金逾期率': ('t7_overdue_capit_4', 't7_should_capit_4'),
    '4t7息费逾期率_本金分母': ('t7_overdue_interest_4', 't7_should_capit_4'),
    '1t7本金逾期率': ('t7_overdue_capit_1', 't7_should_capit_1'),
    '2t7本金逾期率': ('t7_overdue_capit_2', 't7_should_capit_2'),
    '3t7本金逾期率': ('t7_overdue_capit_3', 't7_should_capit_3'),
}


def safe_div(num, den):
    return num / den.where(den != 0)


def add_rates(df):
    """在分组求和后的 df 上计算各比率指标列"""
    df = df.copy()
    for col, (num_expr, den_col) in RATE_DEFS.items():
        num = df['haircut_amount'] + df['should_interest'] if num_expr == 'haircut_amount__should_interest' else df[num_expr]
        den = df[den_col]
        df[col] = safe_div(num, den)
    return df


def to_sheet_df(raw, time_col, time_out_col):
    """把取数原始行聚合为 build_sheet 需要的周度/月度 DataFrame。

    raw: 含 is_reloan, product_name, loan_cycle, issue_week, issue_month + SUM_COLS
    time_col: 'issue_week' 或 'issue_month'
    time_out_col: 'issue_week' 或 '放款月份'
    """
    out = raw.groupby(['is_reloan', 'product_name', time_col], as_index=False).agg(
        {**{c: 'sum' for c in SUM_COLS}, 'loan_cycle': 'max'}
    )
    out = add_rates(out)
    out = out.rename(columns={
        'product_name': '产品',
        'issue_cnt': '放款笔数',
        'contract_amount': '放款金额',
        'loan_cycle': '平均期限',
        time_col: time_out_col,
    })
    keep = ['is_reloan', '产品', '放款笔数', '放款金额', '平均期限', time_out_col,
            'is_t0_window_1', 'is_t3_window_1', 'is_t0_window_2',
            'is_t0_window_3', 'is_t0_window_4', 'is_t7_window_4',
            '总收息_含税', '1t0本金逾期率', '1t3本金逾期率', '2t0本金逾期率',
            '3t0本金逾期率', '4t0本金逾期率', '4t7本金逾期率', '4t7息费逾期率_本金分母']
    return out[keep]


# 历史表现 sheet 的列定义: (表头, 数据列, 数字格式)  后收占比=含税(should_interest/contract_amount)
HISTORY_COLUMNS = [
    ('放款笔数', '放款笔数', '#,##0'),
    ('放款金额', '放款金额', '#,##0'),
    ('放款件均', '放款件均', '#,##0'),
    ('后收占比(含税)', '后收占比(含税)', '0.0%'),
    ('前砍占比', '前砍占比', '0.0%'),
    ('4T7本金坏账', '4T7本金坏账', '0.0%'),
    ('4T7息费坏账', '4T7息费坏账', '0.0%'),
    ('4T7TR', '4T7TR', '0.0%'),
    ('1T7本金坏账', '1T7本金坏账', '0.0%'),
    ('2T7本金坏账', '2T7本金坏账', '0.0%'),
    ('3T7本金坏账', '3T7本金坏账', '0.0%'),
]


def build_history_sheet(wb, sheet_name, gdf, time_col, time_col_label):
    """写一个全量汇总(不分产品)的历史表现 sheet。

    gdf: 按 [issue_month/issue_week] 分组求和后的 DataFrame(单首贷/复贷, 已含 SUM_COLS)
    time_col: 'issue_month' 或 'issue_week'
    time_col_label: '放款月' 或 '放款周'
    """
    g = gdf.copy()
    g['放款笔数'] = g['issue_cnt']
    g['放款金额'] = g['contract_amount']
    g[time_col_label] = g[time_col]
    g['放款件均'] = safe_div(g['contract_amount'], g['issue_cnt'])
    g['后收占比(含税)'] = safe_div(g['should_interest'], g['contract_amount'])
    g['前砍占比'] = safe_div(g['haircut_amount'], g['contract_amount'])
    g['4T7本金坏账'] = safe_div(g['t7_overdue_capit_4'], g['t7_should_capit_4'])
    g['4T7息费坏账'] = safe_div(g['t7_overdue_interest_4'], g['t7_should_capit_4'])
    g['4T7TR'] = g['后收占比(含税)'] + g['前砍占比'] - g['4T7本金坏账'] - g['4T7息费坏账']
    g['1T7本金坏账'] = safe_div(g['t7_overdue_capit_1'], g['t7_should_capit_1'])
    g['2T7本金坏账'] = safe_div(g['t7_overdue_capit_2'], g['t7_should_capit_2'])
    g['3T7本金坏账'] = safe_div(g['t7_overdue_capit_3'], g['t7_should_capit_3'])

    ws = wb.create_sheet(title=sheet_name)
    ws.sheet_view.showGridLines = False

    thin = Border(left=Side('thin'), right=Side('thin'), top=Side('thin'), bottom=Side('thin'))
    hfill = PatternFill('solid', fgColor='4472C4')
    hfont = Font(name='微软雅黑', size=10, bold=True, color='FFFFFF')
    nfont = Font(name='微软雅黑', size=10)
    tfont = Font(name='微软雅黑', size=13, bold=True, color='1F4E79')
    ctr = Alignment('center', 'center', wrap_text=True)

    ncols = 1 + len(HISTORY_COLUMNS)
    ws.cell(row=1, column=1, value=f'{sheet_name}历史表现(2026-01-01起)')
    ws.cell(row=1, column=1).font = tfont
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)

    # 表头
    headers = [time_col_label] + [h for h, _, _ in HISTORY_COLUMNS]
    for ci, h in enumerate(headers, start=1):
        c = ws.cell(row=2, column=ci, value=h)
        c.font = hfont
        c.fill = hfill
        c.alignment = ctr
        c.border = thin
    ws.row_dimensions[2].height = 16

    # 数据行
    for ri, (_, srow) in enumerate(g.iterrows(), start=3):
        ws.cell(row=ri, column=1, value=srow[time_col_label]).alignment = ctr
        ws.cell(row=ri, column=1).font = nfont
        for ci, (_, col, fmt) in enumerate(HISTORY_COLUMNS, start=2):
            v = srow[col]
            cell = ws.cell(row=ri, column=ci, value=float(v) if pd.notna(v) else 0)
            cell.number_format = fmt
            cell.alignment = ctr
            cell.font = nfont
            cell.border = thin
        ws.cell(row=ri, column=1).border = thin

    for ci in range(1, ncols + 1):
        ws.column_dimensions[get_column_letter(ci)].width = 18 if ci == 1 else 14
    ws.freeze_panes = 'A3'
    return ws


def login_with_retry(pq, retries=5):
    for a in range(retries):
        try:
            pq.login()
            return True
        except Exception as e:
            print(f'  [登录重试 {a + 1}] {e}')
            time.sleep(5 * (a + 1))
    return False


def query_with_retry(pq, sql, retries=5):
    for a in range(retries):
        try:
            df = pq.query(sql)
            if isinstance(df, str):
                raise RuntimeError(df)
            return df
        except Exception as e:
            print(f'  [取数重试 {a + 1}] {e}')
            time.sleep(8 * (a + 1))
    raise RuntimeError('取数多次失败')


def main():
    pq = PrestoQuery()
    print('登录 Presto ...')
    if not login_with_retry(pq):
        raise ConnectionError('登录失败')

    raw = None
    if __import__('os').path.exists(CACHE_CSV):
        print('发现缓存文件, 直接读取(如需重新取数请删除该文件)')
        raw = pd.read_csv(CACHE_CSV, dtype={'issue_week': str, 'issue_month': str})
    else:
        print('执行取数 SQL ...')
        raw = query_with_retry(pq, SQL)
        print(f'取数完成, 共 {len(raw)} 行')
        raw.to_csv(CACHE_CSV, index=False, encoding='utf-8-sig')
        print(f'已缓存: {CACHE_CSV}')

    # 数值列转 float(部分可能返回字符串)
    for c in SUM_COLS:
        raw[c] = pd.to_numeric(raw[c], errors='coerce').fillna(0)

    # 周度 / 月度
    weekly = to_sheet_df(raw, 'issue_week', 'issue_week')
    monthly = to_sheet_df(raw, 'issue_month', '放款月份')

    # 历史表现(全量汇总, 不分产品): 2026-01-01 起
    hist_month = raw[raw['issue_month'] >= '2026-01-01'].groupby(
        ['is_reloan', 'issue_month'], as_index=False).agg(
        {**{c: 'sum' for c in SUM_COLS}}
    )
    hist_week = raw[raw['issue_week'] >= '2026-01-01'].groupby(
        ['is_reloan', 'issue_week'], as_index=False).agg(
        {**{c: 'sum' for c in SUM_COLS}}
    )

    wb = Workbook()

    for reloan, label in [('new', '首贷'), ('old', '复贷')]:
        df_w = weekly[weekly['is_reloan'] == reloan].drop(columns='is_reloan').reset_index(drop=True)
        df_m = monthly[monthly['is_reloan'] == reloan].drop(columns='is_reloan').reset_index(drop=True)
        print(f'\n===== {label}(is_reloan={reloan}) =====')
        print(f'  周度行数: {len(df_w)}, 月度行数: {len(df_m)}')
        build_sheet(wb, label, df_w, df_m,
                    REF_MONTH, TARGET_MONTH,
                    DEFAULT_TARGET_WEEKS, DEFAULT_WEEK_WEIGHTS,
                    REVENUE_FIELD)

        # 历史月 sheet
        hm = hist_month[hist_month['is_reloan'] == reloan].drop(columns='is_reloan').sort_values('issue_month')
        build_history_sheet(wb, f'{label}月', hm, 'issue_month', '放款月')
        # 历史周 sheet
        hw = hist_week[hist_week['is_reloan'] == reloan].drop(columns='is_reloan').sort_values('issue_week')
        build_history_sheet(wb, f'{label}周', hw, 'issue_week', '放款周')

    # 删除默认空 sheet
    if 'Sheet' in wb.sheetnames:
        del wb['Sheet']

    wb.save(OUT_XLSX)
    print(f'\n已保存: {OUT_XLSX}')


if __name__ == '__main__':
    main()
