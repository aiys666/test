# -*- coding: utf-8 -*-
"""
墨西哥 1T0 逾期率导出
====================
单独提取 1T0（第一期T0窗口）的本金逾期率、本息逾期率
一个Excel含3个Sheet：月度/周度/日度
月度从2025-01-01起，日/周从2026-01-01起
"""

import sys, os, calendar, time
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime

# ═══════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════
OUTPUT_DIR = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析"

START_DATE = {
    'monthly': "date'2025-01-01'",
    'weekly':  "date'2026-01-01'",
    'daily':   "date'2026-01-01'",
}

MODE_LABEL = {
    'monthly': '月度',
    'weekly':  '周度',
    'daily':   '日度',
}

DATE_FMT = {
    'monthly': 'yyyy"年"m"月";@',
    'weekly':  'yyyy-mm-dd',
    'daily':   'yyyy-mm-dd',
}

# ═══════════════════════════════════════════════════════
# SQL
# ═══════════════════════════════════════════════════════

def build_sql(mode):
    """1T0 本金逾期率 + 本息逾期率"""
    start = START_DATE[mode]
    if mode == 'monthly':
        trunc = "date_trunc('month', date(r.release_time))"
    elif mode == 'weekly':
        trunc = "date_trunc('week', date(r.release_time))"
    else:
        trunc = "date(r.release_time)"
    return f"""
select
    {trunc} as qz_period,
    r.is_reloan,
    case when sum(r.t0_should_capit_1) = 0 then 0
         else sum(r.t0_overdue_capit_1) * 1.0000 / sum(r.t0_should_capit_1)
    end as t0_capit_overdue_rate,
    case when sum(r.t0_should_amt_1) = 0 then 0
         else sum(r.t0_overdue_amount_1) * 1.0000 / sum(r.t0_should_amt_1)
    end as t0_amt_overdue_rate
from mx.wxs_application_funnel r
where r.if_issue = 1
  and r.release_time >= {start}
group by 1, 2
order by 1 desc, 2
"""

# ═══════════════════════════════════════════════════════
# 行配置
# ═══════════════════════════════════════════════════════

# Sheet1行配置: (row, 首贷/复贷, 指标名, 字段, 格式)
ROWS = [
    # 首贷
    (4,  '首贷', '1T0本金逾期率', 't0_capit_overdue_rate', 'pct'),
    (5,  '首贷', '1T0本息逾期率', 't0_amt_overdue_rate',  'pct'),
    # 复贷
    (7,  '复贷', '1T0本金逾期率', 't0_capit_overdue_rate', 'pct'),
    (8,  '复贷', '1T0本息逾期率', 't0_amt_overdue_rate',  'pct'),
]

FMT_MAP = {
    'pct': '0.0%',
}

# 样式
FONT_HDR   = Font(name='微软雅黑', size=10, bold=True, color='FFFFFFFF')
FONT_DATA  = Font(name='微软雅黑', size=10, color='FF000000')
FONT_LABEL = Font(name='微软雅黑', size=10, color='FF000000')
HDR_FILL   = PatternFill('solid', fgColor='4472C4')
THIN       = Side(style='thin')
BORDER     = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
ALIGN_CENTER = Alignment(horizontal='center', vertical='center')

# ═══════════════════════════════════════════════════════
# 主逻辑
# ═══════════════════════════════════════════════════════

def write_sheet(ws, df, mode):
    """向一个Sheet写入1T0数据"""
    label = MODE_LABEL[mode]
    date_fmt = DATE_FMT[mode]
    col_start = 3

    all_periods = sorted(df['qz_period'].unique())

    # Row 1: 标题
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=col_start + len(all_periods) - 1)
    title_cell = ws.cell(1, 1)
    title_cell.value = f'墨西哥 1T0 逾期率（{label}）'
    title_cell.font = Font(name='微软雅黑', size=12, bold=True, color='FFFFFFFF')
    title_cell.fill = PatternFill('solid', fgColor='1F4E79')
    title_cell.alignment = ALIGN_CENTER

    # Row 2: 时间表头
    for i, p in enumerate(all_periods):
        col = col_start + i
        cell = ws.cell(2, col)
        cell.value = p
        cell.number_format = date_fmt
        cell.font = FONT_HDR
        cell.fill = HDR_FILL
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER

    # 数据行
    for row, loan_label, metric_label, field, fmt_key in ROWS:
        ws.cell(row, 1).value = loan_label
        ws.cell(row, 1).font = FONT_LABEL
        ws.cell(row, 1).alignment = ALIGN_CENTER
        ws.cell(row, 1).border = BORDER

        b_cell = ws.cell(row, 2)
        b_cell.value = metric_label
        b_cell.font = FONT_HDR
        b_cell.fill = HDR_FILL
        b_cell.alignment = ALIGN_CENTER
        b_cell.border = BORDER

        loan_type = 'new' if loan_label == '首贷' else 'old'
        sub = df[df['is_reloan'] == loan_type]

        for i, p in enumerate(all_periods):
            col = col_start + i
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

    # 首贷/复贷分组标题
    for title_row, title_text in [(3, '首贷'), (6, '复贷')]:
        ws.merge_cells(start_row=title_row, start_column=1, end_row=title_row, end_column=2)
        cell = ws.cell(title_row, 1)
        cell.value = title_text
        cell.font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFFFF')
        cell.fill = PatternFill('solid', fgColor='1F4E79')
        cell.alignment = ALIGN_CENTER

    # 列宽
    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 16
    for i in range(len(all_periods)):
        col_letter = get_column_letter(col_start + i)
        ws.column_dimensions[col_letter].width = 12

    # 行高
    for r in range(1, 9):
        ws.row_dimensions[r].height = 14.5

    ws.sheet_view.showGridLines = False
    ws.freeze_panes = 'C3'


def run_mode(mode, pq, wb, sheet_name):
    """查询并写入一个Sheet"""
    label = MODE_LABEL[mode]
    print(f"\n  [{label}] 查询数据...")

    sql = build_sql(mode)
    for attempt in range(3):
        try:
            print(f"    SQL (第{attempt+1}/3次)...")
            df = pq.query(sql, wait_sec=5)
            if isinstance(df, str):
                print(f"    查询失败: {df[:200]}")
                if attempt < 2:
                    pq.login()
                    time.sleep(2)
                    continue
                return False
            print(f"    返回 {len(df)} 行")
            break
        except Exception as e:
            print(f"    异常: {str(e)[:200]}")
            if attempt < 2:
                pq.login()
                time.sleep(2)
                continue
            return False

    # 处理数据
    df['qz_period'] = pd.to_datetime(df['qz_period'])
    df['is_reloan'] = df['is_reloan'].astype(str).str.strip()
    df['is_reloan'] = df['is_reloan'].apply(lambda x: 'new' if x in ('new', 'True', 'true', '1') else 'old')
    for col in ['t0_capit_overdue_rate', 't0_amt_overdue_rate']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.sort_values(['qz_period', 'is_reloan']).reset_index(drop=True)
    print(f"    范围: {df['qz_period'].min()} ~ {df['qz_period'].max()}")

    # 写入Sheet
    ws = wb.create_sheet(sheet_name)
    write_sheet(ws, df, mode)
    return True


def main():
    print("=" * 60)
    print("墨西哥 1T0 逾期率导出（月度/周度/日度）")
    print("=" * 60)

    # ── 1. 连接 ────────────────────────
    print("\n[1/2] 连接墨西哥 Presto...")
    pq = PrestoQuery()
    pq.login()
    print("  连接成功")

    # ── 2. 生成Excel ──────────────────
    print("\n[2/2] 生成 Excel...")
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # 删除默认Sheet

    for mode in ['monthly', 'weekly', 'daily']:
        run_mode(mode, pq, wb, MODE_LABEL[mode])

    # ── 3. 保存 ───────────────────────
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(OUTPUT_DIR, f"墨西哥1T0逾期率_{timestamp}.xlsx")
    wb.save(out_path)
    print(f"\n  已保存: {out_path}")
    print("=" * 60)
    print("完成!")


if __name__ == "__main__":
    main()
