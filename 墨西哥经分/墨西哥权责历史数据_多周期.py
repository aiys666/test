# -*- coding: utf-8 -*-
"""
墨西哥权责历史数据 — 日/周/月 多周期导出
==========================================
功能:
  1. 连接墨西哥 Presto
  2. 支持 daily / weekly / monthly 三种时间粒度
  3. 每种粒度生成独立 Excel（Sheet1指标 + Sheet2期限占比）
  4. 月度从2025-01-01起，日/周从2026-01-01起
"""

import sys, os, calendar, time
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════
OUTPUT_DIR = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析"

# 各模式起始日期
START_DATE = {
    'monthly': "date'2025-01-01'",
    'weekly':  "date'2026-01-01'",
    'daily':   "date'2026-01-01'",
}

# 模式中文名
MODE_LABEL = {
    'monthly': '月度',
    'weekly':  '周度',
    'daily':   '日度',
}

# ═══════════════════════════════════════════════════════
# SQL 生成器
# ═══════════════════════════════════════════════════════

def build_sql1(mode):
    """SQL1: 投放 + 进件 + 放款漏斗数据"""
    start = START_DATE[mode]
    if mode == 'monthly':
        date_expr = "DATE_PARSE(date_mon || '-01', '%Y-%m-%d')"
    elif mode == 'weekly':
        date_expr = "date_trunc('week', data_date)"
    else:  # daily
        date_expr = "data_date"
    return f"""
select
{date_expr} AS qz_period
,case when order_type_new ='首贷' then 'new' else 'old' end  is_reloan
,sum(ad_cost) as ad_cost
,sum(apply_cnt) as apply_cnt
,sum(loan_cnt) as loan_cnt
,sum(loan_contract_amt_usd) as loan_contract_amt_usd
,sum(loan_contract_amt_usd)*1.0000/sum(loan_cnt) as loan_amt_avg
,sum(ad_cost)/sum(loan_cnt) as cps
,sum(if_in_ruledetermine_data)*1.0000/sum(if_in_confirm)  as confirm_rate
,(sum(if_model_passed)*1.0000/sum(apply_cnt))*(sum(pass_cnt)*1.0000/sum(if_in_ruledetermine_data)) as pass_rate
from  mx.daily_order_base_final a
where data_date>={start}
group by 1,2
order by 1 desc ,2
"""

def build_sql2(mode):
    """SQL2: 权责风险数据"""
    start = START_DATE[mode]
    if mode == 'monthly':
        trunc = "date_trunc('month', date(r.release_time))"
    elif mode == 'weekly':
        trunc = "date_trunc('week', date(r.release_time))"
    else:  # daily
        trunc = "date(r.release_time)"
    return f"""
select
    {trunc} as qz_period,
    r.is_reloan,
    sum(loan_cycle*contract_amount)*1.0/sum(contract_amount) as avg_loan_cycle,
    max(case when r.loan_cycle <120 then r.loan_cycle else null end) as max_loan_cycle,
    sum(r.should_interest)*1.0000/sum(r.contract_amount)   as interest_rate,
    sum(r.haircut_amount)*1.0000/sum(r.contract_amount)   as haircut_rate,
    case when sum(r.t7_should_capit_4)=0 then 0 else sum(r.t7_overdue_capit_4)*1.0000/sum(r.t7_should_capit_4) end  as capit_bad_rate,
    case when sum(r.t7_should_amt_4)=0 then 0 else sum(r.t7_overdue_amount_4)*1.0000/sum(r.t7_should_amt_4) end as amt_bad_rate,
    case when sum(r.t7_should_interest_4)=0 then 0 else sum(r.t7_overdue_interest_4)*1.0000/sum(r.t7_should_interest_4) end as interest_bad_rate,
    sum(r.fact_fine) as fact_fine
from mx.wxs_application_funnel r
where  r.if_issue=1
and r.release_time>={start}
 GROUP BY 1,2
"""

def build_sql3(mode):
    """SQL3: 期限分布数据"""
    start = START_DATE[mode]
    if mode == 'monthly':
        trunc = "date_trunc('month', date(r.release_time))"
    elif mode == 'weekly':
        trunc = "date_trunc('week', date(r.release_time))"
    else:  # daily
        trunc = "date(r.release_time)"
    return f"""
select
    {trunc} as qz_period,
    r.is_reloan,
    count(*) as total_cnt,
    sum(case when r.loan_cycle <= 7 then 1 else 0 end) * 1.0000 / count(*) as term_7_pct,
    sum(case when r.loan_cycle > 7 and r.loan_cycle <= 14 then 1 else 0 end) * 1.0000 / count(*) as term_14_pct,
    sum(case when r.loan_cycle > 14 and r.loan_cycle <= 21 then 1 else 0 end) * 1.0000 / count(*) as term_21_pct,
    sum(case when r.loan_cycle > 21 and r.loan_cycle <= 28 then 1 else 0 end) * 1.0000 / count(*) as term_28_pct,
    sum(case when r.loan_cycle > 28 and r.loan_cycle <= 45 then 1 else 0 end) * 1.0000 / count(*) as term_45_pct
from mx.wxs_application_funnel r
where r.if_issue = 1
  and r.release_time >= {start}
group by 1, 2
"""

# ═══════════════════════════════════════════════════════
# Sheet1 模板配置
# ═══════════════════════════════════════════════════════

FIRST_LOAN_ROWS = [
    (4,  '成交金额',       'loan_contract_amt_usd', 'amount'),
    (5,  '成交标数',       'loan_cnt',              'cnt'),
    (6,  '笔均',           'loan_amt_avg',          'avg'),
    (7,  '通过率',         'pass_rate',             'pct'),
    (8,  '平均期限',       'avg_loan_cycle',        'avg'),
    (9,  '最大期限',       'max_loan_cycle',        'avg'),
    (10, '预计实收息费%',   'interest_rate',         'pct'),
    (11, '砍头占比%',      'haircut_rate',          'pct'),
    (12, '本金Vintage%',   'capit_bad_rate',        'pct'),
    (13, '本金息费坏账率',  'amt_bad_rate',          'pct'),
    (14, '息费Vintage%',   'interest_bad_rate',     'pct'),
    (15, '罚息收入',       'fact_fine',             'amount'),
    (16, '投放预算',       'ad_cost',               'amount'),
    (17, '日均投放预算',    'daily_ad_cost',         'amount'),
    (18, '进件订单数',     'apply_cnt',             'cnt'),
    (19, '用信率',         'confirm_rate',          'pct'),
    (20, 'CPS(USD)',      'cps',                   'cps'),
]

RELOAN_ROWS = [
    (22, '成交金额',       'loan_contract_amt_usd', 'amount'),
    (23, '成交标数',       'loan_cnt',              'cnt'),
    (24, '笔均',           'loan_amt_avg',          'avg'),
    (25, '进件订单数',     'apply_cnt',             'cnt'),
    (26, '用信率',         'confirm_rate',          'pct'),
    (27, '通过率',         'pass_rate',             'pct'),
    (28, '平均期限',       'avg_loan_cycle',        'avg'),
    (29, '最大期限',       'max_loan_cycle',        'avg'),
    (30, '预计实收息费%',   'interest_rate',         'pct'),
    (31, '砍头占比%',      'haircut_rate',          'pct'),
    (32, '本金Vintage%',   'capit_bad_rate',        'pct'),
    (33, '本金息费坏账率',  'amt_bad_rate',          'pct'),
    (34, '息费Vintage%',   'interest_bad_rate',     'pct'),
    (35, '罚息收入',       'fact_fine',             'amount'),
]

FMT_MAP = {
    'amount': '#,##0',
    'cnt':    '#,##0',
    'avg':    '0.0',
    'pct':    '0.0%',
    'cps':    '0.00',
}

# 样式
FONT_HDR   = Font(name='微软雅黑', size=10, bold=True, color='FFFFFFFF')
FONT_DATA  = Font(name='微软雅黑', size=10, color='FF000000')
FONT_LABEL = Font(name='微软雅黑', size=10, color='FF000000')
HDR_FILL   = PatternFill('solid', fgColor='4472C4')
THIN       = Side(style='thin')
BORDER     = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
ALIGN_CENTER = Alignment(horizontal='center', vertical='center')

# Excel 日期格式
DATE_FMT = {
    'monthly': 'yyyy"年"m"月";@',
    'weekly':  'yyyy-mm-dd',
    'daily':   'yyyy-mm-dd',
}

# 区间天数计算
def period_days(d, mode):
    """计算每个区间的天数"""
    if mode == 'monthly':
        return calendar.monthrange(d.year, d.month)[1]
    elif mode == 'weekly':
        return 7
    else:  # daily
        return 1


# ═══════════════════════════════════════════════════════
# 主逻辑
# ═══════════════════════════════════════════════════════

def run_mode(mode, pq):
    """运行单个模式（daily/weekly/monthly）"""
    label = MODE_LABEL[mode]
    print(f"\n{'='*60}")
    print(f"  {label}数据导出")
    print(f"{'='*60}")

    # ── 查询 ────────────────────────────────
    def exec_with_retry(sql, desc, max_retries=3):
        for attempt in range(max_retries):
            try:
                print(f"  {desc} (第{attempt+1}/{max_retries}次)...")
                df = pq.query(sql, wait_sec=5)
                if isinstance(df, str):
                    print(f"    查询失败: {df[:200]}")
                    if attempt < max_retries - 1:
                        print("    重新登录重试...")
                        pq.login()
                        time.sleep(2)
                        continue
                    return df
                print(f"    返回 {len(df)} 行")
                return df
            except Exception as e:
                print(f"    异常: {str(e)[:200]}")
                if attempt < max_retries - 1:
                    print("    重新登录重试...")
                    pq.login()
                    time.sleep(2)
                    continue
                return str(e)

    sql1, sql2, sql3 = build_sql1(mode), build_sql2(mode), build_sql3(mode)

    print(f"\n  [1/5] 查询投放漏斗数据(SQL1)...")
    df1 = exec_with_retry(sql1, "SQL1")
    if isinstance(df1, str):
        print(f"  SQL1 查询失败，跳过{label}")
        return

    print(f"  [2/5] 查询权责风险数据(SQL2)...")
    df2 = exec_with_retry(sql2, "SQL2")
    if isinstance(df2, str):
        print(f"  SQL2 查询失败，跳过{label}")
        return

    print(f"  [3/5] 查询期限分布数据(SQL3)...")
    df3 = exec_with_retry(sql3, "SQL3")
    if isinstance(df3, str):
        print(f"  SQL3 查询失败，Sheet2将为空")
        df3 = pd.DataFrame()

    # ── 合并数据 ──────────────────────────────
    print(f"  [4/5] 合并数据...")

    for col in ['qz_period']:
        df1[col] = pd.to_datetime(df1[col])
        df2[col] = pd.to_datetime(df2[col])
        if len(df3) > 0:
            df3[col] = pd.to_datetime(df3[col])

    df2['is_reloan'] = df2['is_reloan'].astype(str).str.strip()
    df2['is_reloan'] = df2['is_reloan'].apply(lambda x: 'new' if x in ('new', 'True', 'true', '1') else 'old')

    df = pd.merge(df1, df2, on=['qz_period', 'is_reloan'], how='outer')

    num_cols = ['ad_cost', 'apply_cnt', 'loan_cnt', 'loan_contract_amt_usd',
                'loan_amt_avg', 'cps', 'confirm_rate', 'pass_rate',
                'avg_loan_cycle', 'max_loan_cycle', 'interest_rate', 'haircut_rate',
                'capit_bad_rate', 'amt_bad_rate', 'interest_bad_rate', 'fact_fine']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 日均投放 = ad_cost / 区间天数
    df['period_days'] = df['qz_period'].apply(lambda d: period_days(d, mode))
    df['daily_ad_cost'] = df.apply(
        lambda r: r['ad_cost'] / r['period_days'] if pd.notna(r['ad_cost']) and r['period_days'] > 0 else 0,
        axis=1
    )

    df = df.sort_values(['qz_period', 'is_reloan'], ascending=[True, True]).reset_index(drop=True)
    print(f"    合并后 {len(df)} 行，范围: {df['qz_period'].min()} ~ {df['qz_period'].max()}")

    # ── 生成 Excel ──────────────────────────
    print(f"  [5/5] 生成 Excel...")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    all_periods = sorted(df['qz_period'].unique())
    month_col_start = 3
    date_fmt = DATE_FMT[mode]

    # Row 2: 时间表头
    for i, p in enumerate(all_periods):
        col = month_col_start + i
        cell = ws.cell(2, col)
        cell.value = p
        cell.number_format = date_fmt
        cell.font = FONT_HDR
        cell.fill = HDR_FILL
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER

    # 指标行
    all_rows = FIRST_LOAN_ROWS + RELOAN_ROWS

    for row, lbl, field, fmt_key in all_rows:
        is_first = row <= 20
        ws.cell(row, 1).value = '首贷' if is_first else '复贷'
        ws.cell(row, 1).font = FONT_LABEL
        ws.cell(row, 1).alignment = ALIGN_CENTER
        ws.cell(row, 1).border = BORDER

        b_cell = ws.cell(row, 2)
        b_cell.value = lbl
        b_cell.font = FONT_HDR
        b_cell.fill = HDR_FILL
        b_cell.alignment = ALIGN_CENTER
        b_cell.border = BORDER

        loan_type = 'new' if is_first else 'old'
        sub = df[df['is_reloan'] == loan_type]

        for i, p in enumerate(all_periods):
            col = month_col_start + i
            cell = ws.cell(row, col)
            cell.font = FONT_DATA
            cell.alignment = ALIGN_CENTER
            cell.border = BORDER
            cell.number_format = FMT_MAP.get(fmt_key, 'General')

            row_data = sub[sub['qz_period'] == p]
            if len(row_data) > 0:
                val = row_data.iloc[0][field]
                if pd.notna(val):
                    cell.value = float(val)

    # Row 36: 区间天数
    days_label = '当月天数' if mode == 'monthly' else '区间天数'
    ws.cell(36, 1).value = ''
    ws.cell(36, 1).border = BORDER
    ws.cell(36, 2).value = days_label
    ws.cell(36, 2).font = FONT_HDR
    ws.cell(36, 2).fill = HDR_FILL
    ws.cell(36, 2).alignment = ALIGN_CENTER
    ws.cell(36, 2).border = BORDER

    for i, p in enumerate(all_periods):
        col = month_col_start + i
        cell = ws.cell(36, col)
        cell.value = period_days(p, mode)
        cell.font = FONT_DATA
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER
        cell.number_format = '0'

    # 列宽
    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 14
    for i in range(len(all_periods)):
        col_letter = get_column_letter(month_col_start + i)
        ws.column_dimensions[col_letter].width = 12 if mode == 'daily' else 11

    # 行高
    for r in range(2, 37):
        ws.row_dimensions[r].height = 14.5

    ws.sheet_view.showGridLines = False

    for title_row, title_text in [(3, '首贷'), (21, '复贷')]:
        ws.merge_cells(start_row=title_row, start_column=1, end_row=title_row, end_column=2)
        cell = ws.cell(title_row, 1)
        cell.value = title_text
        cell.font = Font(name='微软雅黑', size=12, bold=True, color='FFFFFFFF')
        cell.fill = PatternFill('solid', fgColor='1F4E79')
        cell.alignment = Alignment(horizontal='center', vertical='center')

    ws.freeze_panes = 'C3'

    # ── Sheet2 期限占比 ──────────────────────
    ws2 = wb.create_sheet("Sheet2")

    TERM_ROWS = [
        (4,  '首贷', '7天',  'term_7_pct',  'pct'),
        (5,  '首贷', '14天', 'term_14_pct', 'pct'),
        (6,  '首贷', '21天', 'term_21_pct', 'pct'),
        (7,  '首贷', '28天', 'term_28_pct', 'pct'),
        (8,  '首贷', '45天', 'term_45_pct', 'pct'),
        (10, '复贷', '7天',  'term_7_pct',  'pct'),
        (11, '复贷', '14天', 'term_14_pct', 'pct'),
        (12, '复贷', '21天', 'term_21_pct', 'pct'),
        (13, '复贷', '28天', 'term_28_pct', 'pct'),
        (14, '复贷', '45天', 'term_45_pct', 'pct'),
    ]

    for i, p in enumerate(all_periods):
        col = month_col_start + i
        cell = ws2.cell(2, col)
        cell.value = p
        cell.number_format = date_fmt
        cell.font = FONT_HDR
        cell.fill = HDR_FILL
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER

    for row, loan_type_label, term_label, field, fmt_key in TERM_ROWS:
        ws2.cell(row, 1).value = loan_type_label
        ws2.cell(row, 1).font = FONT_LABEL
        ws2.cell(row, 1).alignment = ALIGN_CENTER
        ws2.cell(row, 1).border = BORDER

        b_cell = ws2.cell(row, 2)
        b_cell.value = term_label
        b_cell.font = FONT_HDR
        b_cell.fill = HDR_FILL
        b_cell.alignment = ALIGN_CENTER
        b_cell.border = BORDER

        loan_type = 'new' if loan_type_label == '首贷' else 'old'
        if len(df3) > 0:
            df3['is_reloan'] = df3['is_reloan'].astype(str).str.strip()
            df3['is_reloan'] = df3['is_reloan'].apply(lambda x: 'new' if x in ('new', 'True', 'true', '1') else 'old')
            sub3 = df3[df3['is_reloan'] == loan_type]
        else:
            sub3 = pd.DataFrame()

        for i, p in enumerate(all_periods):
            col = month_col_start + i
            cell = ws2.cell(row, col)
            cell.font = FONT_DATA
            cell.alignment = ALIGN_CENTER
            cell.border = BORDER
            cell.number_format = FMT_MAP.get(fmt_key, 'General')

            if len(sub3) > 0:
                row_data = sub3[sub3['qz_period'] == p]
                if len(row_data) > 0:
                    val = row_data.iloc[0][field]
                    if pd.notna(val):
                        cell.value = float(val)

    for title_row, title_text in [(3, '首贷'), (9, '复贷')]:
        ws2.merge_cells(start_row=title_row, start_column=1, end_row=title_row, end_column=2)
        cell = ws2.cell(title_row, 1)
        cell.value = title_text
        cell.font = Font(name='微软雅黑', size=12, bold=True, color='FFFFFFFF')
        cell.fill = PatternFill('solid', fgColor='1F4E79')
        cell.alignment = Alignment(horizontal='center', vertical='center')

    ws2.column_dimensions['A'].width = 6
    ws2.column_dimensions['B'].width = 14
    for i in range(len(all_periods)):
        col_letter = get_column_letter(month_col_start + i)
        ws2.column_dimensions[col_letter].width = 12 if mode == 'daily' else 11

    for r in range(2, 15):
        ws2.row_dimensions[r].height = 14.5

    ws2.sheet_view.showGridLines = False
    ws2.freeze_panes = 'C3'

    # ── 保存 ────────────────────────────────
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(OUTPUT_DIR, f"墨西哥权责历史数据_{label}_{timestamp}.xlsx")
    wb.save(out_path)
    print(f"  已保存: {out_path}")
    return out_path


def main():
    print("=" * 60)
    print("墨西哥权责历史数据 — 日/周/月 多周期导出")
    print("=" * 60)

    # ── 1. 连接数据库 ────────────────────────
    print("\n[1/3] 连接墨西哥 Presto...")
    pq = PrestoQuery()
    pq.login()
    print("  连接成功")

    # ── 2. 依次运行三种粒度 ──────────────────
    results = []
    for mode in ['monthly', 'weekly', 'daily']:
        print(f"\n[2/3] 开始 {MODE_LABEL[mode]} 数据...")
        path = run_mode(mode, pq)
        if path:
            results.append((MODE_LABEL[mode], path))

    # ── 3. 汇总 ──────────────────────────────
    print(f"\n{'='*60}")
    print("全部完成! 生成文件:")
    for label, path in results:
        print(f"  {label}: {path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
