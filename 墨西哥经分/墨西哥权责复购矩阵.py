# -*- coding: utf-8 -*-
"""墨西哥复购矩阵查询与导出（公式驱动版）。

只有 vintage底表 是直连 Presto 跑出的原始数据（double_cnt / double_mid / frs_cnt）。
其他所有 Sheet 全部用 Excel 公式引用 vintage底表，方便逐格校验。

口径：
- 整体复购矩阵 = 复购标数 / 首贷用户数
- 复购用户占比 = 复购用户数 / 首贷用户数
- 单户成交标数 = 复购标数 / 复购用户数

Sheet 结构：
1. 复购矩阵            — 引用各 vintage 表的"最新表现比例"对角线
2. vintage底表         — Presto 原始数据 + 公式列
3. 整体复购vintage      — SUMIFS 引用 vintage底表 + 最新表现比例对角线
4. 复购用户占比vintage   — SUMIFS 引用 vintage底表 + 最新表现比例对角线
5. 单户成交标数vintage   — SUMIFS 引用 vintage底表 + 最新表现比例对角线
"""

import sys
import os
import argparse
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery


# ---------------------------------------------------------------------------
# SQL 构建
# ---------------------------------------------------------------------------

def build_vintage_sql(start_month, end_month):
    """按首贷月份 x MOB0-12 的 vintage 明细（只有有数据的行）。"""
    return f"""
WITH double_loan AS (
    SELECT 
        d.ltv_month, 
        date_diff('month', d.ltv_month, date_trunc('month', date(r.release_time))) AS mob,  
        r.camera_id AS biz_id,
        cast(r.cust_id AS bigint) AS mid
    FROM mx.wxs_application_funnel r
    LEFT JOIN mx.ys_dl_ltv_first_loan_0511 d
        ON cast(r.cust_id AS bigint) = d.mid  
    WHERE r.is_reloan = 'old'
      AND r.if_issue = 1
      AND d.mid IS NOT NULL
      AND d.ltv_month >= DATE '{start_month}'
      AND d.ltv_month <= DATE '{end_month}'
),
double_agg AS (
    SELECT 
        ltv_month,
        mob,
        COUNT(DISTINCT biz_id) AS double_cnt,
        COUNT(DISTINCT mid) AS double_mid 
    FROM double_loan
    WHERE mob BETWEEN 0 AND 12
    GROUP BY 1, 2
),
first_loan AS (
    SELECT 
        ltv_month, 
        COUNT(DISTINCT mid) AS frs_cnt 
    FROM mx.ys_dl_ltv_first_loan_0511
    WHERE ltv_month >= DATE '{start_month}'
      AND ltv_month <= DATE '{end_month}'
    GROUP BY 1 
)
SELECT
    d.ltv_month,
    d.mob,
    d.double_cnt,
    d.double_mid,
    f.frs_cnt
FROM double_agg d
LEFT JOIN first_loan f ON d.ltv_month = f.ltv_month
ORDER BY d.ltv_month, d.mob
"""


def build_first_loan_sql(start_month, end_month):
    """查询首贷月份和首贷用户数。"""
    return f"""
SELECT 
    ltv_month, 
    COUNT(DISTINCT mid) AS frs_cnt 
FROM mx.ys_dl_ltv_first_loan_0511
WHERE ltv_month >= DATE '{start_month}'
  AND ltv_month <= DATE '{end_month}'
GROUP BY 1 
ORDER BY 1
"""


def build_loan_pool_sql(start_month, end_month):
    """放款池指标：按首贷月份 x MOB放款月 聚合。

    池子：is_reloan='old' AND if_issue=1（复贷已放款）。
    MOB  = date_diff('month', 首贷月, 放款月)。
    """
    return f"""
WITH pool AS (
    SELECT
        d.ltv_month,
        date_diff('month', d.ltv_month, date_trunc('month', date(r.release_time))) AS mob,
        r.if_issue,
        r.contract_amount,
        r.haircut_amount,
        r.should_interest,
        r.is_t0_window_1,
        r.t0_overdue_capit_1,
        r.t0_overdue_interest_1,
        r.t0_should_capit_1,
        r.is_t7_window_4,
        r.t7_overdue_capit_4,
        r.t7_overdue_interest_4,
        r.t7_should_capit_4
    FROM mx.wxs_application_funnel r
    LEFT JOIN mx.ys_dl_ltv_first_loan_0511 d
        ON cast(r.cust_id AS bigint) = d.mid
    WHERE r.is_reloan = 'old'
      AND r.if_issue = 1
      AND d.mid IS NOT NULL
      AND d.ltv_month >= DATE '{start_month}'
      AND d.ltv_month <= DATE '{end_month}'
)
SELECT
    ltv_month,
    mob,
    sum(if_issue)        AS issue_cnt,           -- 放款笔数
    sum(contract_amount) AS contract_amt,        -- 放款金额
    sum(haircut_amount)  AS haircut_amt,         -- 前砍金额
    sum(should_interest) AS should_interest_amt, -- 后收息费
    sum(if(is_t0_window_1 = 1, coalesce(t0_overdue_capit_1, 0) + coalesce(t0_overdue_interest_1, 0), 0)) AS t0_bad_amt,  -- 1T0分子(本金+利息坏账)
    sum(if(is_t0_window_1 = 1, coalesce(t0_should_capit_1, 0), 0))  AS t0_should_capit, -- 1T0分母(应还本金)
    sum(if(is_t7_window_4 = 1, coalesce(t7_overdue_capit_4, 0) + coalesce(t7_overdue_interest_4, 0), 0)) AS t7_bad_amt,  -- 4t7分子(本金+利息坏账)
    sum(if(is_t7_window_4 = 1, coalesce(t7_should_capit_4, 0), 0))  AS t7_should_capit, -- 4t7分母(应还本金)
    sum(if(is_t0_window_1 = 1, 1, 0)) AS t0_billed_cnt,  -- 1t0出账数
    sum(if(is_t7_window_4 = 1, 1, 0)) AS t7_billed_cnt   -- 4t7出账数
FROM pool
WHERE mob BETWEEN 0 AND 12
GROUP BY 1, 2
ORDER BY 1, 2
"""


def build_app_pool_sql(start_month, end_month):
    """进件池指标：按首贷月份 x MOB进件月 聚合。

    池子：is_reloan='old'（全量复贷进件，不限定放款）。
    MOB  = date_diff('month', 首贷月, 进件月)。
    """
    return f"""
WITH pool AS (
    SELECT
        d.ltv_month,
        date_diff('month', d.ltv_month, date_trunc('month', date(r.app_time))) AS mob,
        r.if_app,
        r.if_in_sx,
        r.if_issue,
        r.if_SX_passed
    FROM mx.wxs_application_funnel r
    LEFT JOIN mx.ys_dl_ltv_first_loan_0511 d
        ON cast(r.cust_id AS bigint) = d.mid
    WHERE r.is_reloan = 'old'
      AND d.mid IS NOT NULL
      AND d.ltv_month >= DATE '{start_month}'
      AND d.ltv_month <= DATE '{end_month}'
)
SELECT
    ltv_month,
    mob,
    sum(if_app)       AS app_cnt,        -- 进件数
    sum(if_in_sx)     AS in_sx_cnt,      -- 进入授信数
    sum(if_issue)     AS app_issue_cnt,  -- 进件池放款数
    sum(if_SX_passed) AS sx_passed_cnt   -- 授信通过数
FROM pool
WHERE mob BETWEEN 0 AND 12
GROUP BY 1, 2
ORDER BY 1, 2
"""


def fill_full_grid(vintage_df, loan_pool_df, app_pool_df, first_loan_df):
    """合并四份数据，补全所有 ltv_month x MOB0-12 组合，缺数据补0。"""
    loan_cols = ["issue_cnt", "contract_amt", "haircut_amt", "should_interest_amt",
                 "t0_bad_amt", "t0_should_capit", "t7_bad_amt", "t7_should_capit",
                 "t0_billed_cnt", "t7_billed_cnt"]
    app_cols = ["app_cnt", "in_sx_cnt", "app_issue_cnt", "sx_passed_cnt"]
    vintage_cols = ["double_cnt", "double_mid"]

    def prep(df, keep_cols):
        df = df.copy()
        if df.empty:
            return pd.DataFrame(columns=["ltv_month", "mob"] + keep_cols)
        df["ltv_month"] = pd.to_datetime(df["ltv_month"]).dt.strftime("%Y/%m/%d")
        df["mob"] = df["mob"].astype(int)
        for c in keep_cols:
            if c not in df.columns:
                df[c] = 0
        return df[["ltv_month", "mob"] + keep_cols]

    vintage_df = prep(vintage_df, vintage_cols)
    loan_pool_df = prep(loan_pool_df, loan_cols)
    app_pool_df = prep(app_pool_df, app_cols)

    merged = vintage_df.merge(loan_pool_df, on=["ltv_month", "mob"], how="outer") \
                       .merge(app_pool_df, on=["ltv_month", "mob"], how="outer")
    merged = merged.fillna(0)

    first_loan_df = first_loan_df.copy()
    first_loan_df["ltv_month"] = pd.to_datetime(first_loan_df["ltv_month"]).dt.strftime("%Y/%m/%d")
    all_months = sorted(first_loan_df["ltv_month"].unique())
    frs_map = {row.ltv_month: int(float(row.frs_cnt)) for row in first_loan_df.itertuples()}

    int_cols = set(vintage_cols + app_cols + ["issue_cnt", "t0_billed_cnt", "t7_billed_cnt"])

    def to_num(v, as_int):
        try:
            f = float(v)
        except (TypeError, ValueError):
            f = 0.0
        return int(f) if as_int else f

    full_rows = []
    for month in all_months:
        frs_cnt = frs_map[month]
        for mob in range(13):
            rec = {"ltv_month": month, "mob": mob, "frs_cnt": frs_cnt}
            match = merged[(merged["ltv_month"] == month) & (merged["mob"] == mob)]
            for c in vintage_cols + app_cols + loan_cols:
                val = match[c].values[0] if len(match) > 0 else 0
                rec[c] = to_num(val, c in int_cols)
            full_rows.append(rec)

    cols = ["ltv_month", "mob", "frs_cnt"] + vintage_cols + app_cols + loan_cols
    return pd.DataFrame(full_rows, columns=cols).sort_values(["ltv_month", "mob"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Excel 样式工具
# ---------------------------------------------------------------------------

def _thin_border():
    thin = Side(style="thin")
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def _header_style(cell):
    cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFFFF")
    cell.fill = PatternFill("solid", fgColor="4472C4")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = _thin_border()


def _data_style(cell, fmt=None):
    cell.font = Font(name="微软雅黑", size=10)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = _thin_border()
    if fmt:
        cell.number_format = fmt


def _title_style(cell):
    cell.font = Font(name="微软雅黑", size=12, bold=True)
    cell.alignment = Alignment(horizontal="left", vertical="center")


# ---------------------------------------------------------------------------
# Excel 构建（公式驱动）
# ---------------------------------------------------------------------------

def build_excel(vintage_df, output_path, start_month, end_month):
    """生成公式驱动的完整 Excel。

    数据流：
      vintage底表 (Presto原始数据 + 公式列)
        -> 各指标 vintage 透视矩阵 (SUMIFS按月份xMOB + 最新表现比例对角线)
        -> 复购矩阵 (引用各 vintage 表的"最新表现比例"对角线)
    """
    # 首贷月份列表（降序，用于 vintage 矩阵列头）
    ltv_months_desc = sorted(vintage_df["ltv_month"].unique(), reverse=True)

    wb = Workbook()
    wb.calculation.fullCalcOnLoad = True

    # ---- 底表列字母映射（固定，供透视矩阵引用）----
    col = {
        "app_cnt": "F", "in_sx_cnt": "G", "app_issue_cnt": "H", "sx_passed_cnt": "I",
        "issue_cnt": "J", "contract_amt": "K", "haircut_amt": "L", "should_interest_amt": "M",
        "t0_bad_amt": "N", "t0_should_capit": "O", "t7_bad_amt": "P", "t7_should_capit": "Q",
        "t0_billed_cnt": "R", "t7_billed_cnt": "S",
    }

    # ==================== Sheet 1: 复购矩阵 ====================
    ws1 = wb.active
    ws1.title = "复购矩阵"
    ws1.cell(1, 2).value = f"复购矩阵 ({start_month} ~ {end_month}) -- 引用各vintage表最新表现比例对角线"
    ws1.merge_cells(start_row=1, start_column=2, end_row=1, end_column=15)
    _title_style(ws1.cell(1, 2))

    ws1.cell(2, 2).value = "指标"
    _header_style(ws1.cell(2, 2))
    for i in range(13):
        ws1.cell(2, 3 + i).value = f"MOB{i}"
        _header_style(ws1.cell(2, 3 + i))

    # 指标行：标签、对应vintage透视表、格式
    labels = [
        ("整体复购矩阵", "整体复购vintage", '0%'),
        ("复购用户占比", "复购用户占比vintage", '0%'),
        ("单户成交标数", "单户成交标数vintage", '0.00'),
        ("进件数", "进件数vintage", '#,##0'),
        ("整体通过率", "整体通过率vintage", '0.00%'),
        ("放款笔数", "放款笔数vintage", '#,##0'),
        ("放款金额", "放款金额vintage", '#,##0'),
        ("放款件均", "放款件均vintage", '#,##0.00'),
        ("1T0逾期率", "1T0逾期率vintage", '0.00%'),
        ("4t7逾期率", "4t7逾期率vintage", '0.00%'),
        ("前砍比例", "前砍比例vintage", '0.00%'),
        ("后收息费比例", "后收息费比例vintage", '0.00%'),
        ("1t0出账数", "1t0出账数vintage", '#,##0'),
        ("4t7出账数", "4t7出账数vintage", '#,##0'),
    ]
    for row_idx, (label, vintage_sheet, fmt) in enumerate(labels, 3):
        ws1.cell(row_idx, 2).value = label
        ws1.cell(row_idx, 2).font = Font(name="微软雅黑", size=10)
        for mob in range(13):
            col_idx = 3 + mob
            detail_row = 3 + mob
            ws1.cell(row_idx, col_idx).value = f"='{vintage_sheet}'!A{detail_row}"
            _data_style(ws1.cell(row_idx, col_idx), fmt=fmt)

    ws1.column_dimensions['A'].width = 3
    ws1.column_dimensions['B'].width = 20
    for cidx in range(3, 16):
        ws1.column_dimensions[get_column_letter(cidx)].width = 12
    ws1.sheet_view.showGridLines = False

    # ==================== Sheet 2: vintage底表 ====================
    ws3 = wb.create_sheet("vintage底表")
    ws3.cell(1, 1).value = f"vintage 底表 ({start_month} ~ {end_month}) -- Presto原始数据(F~S), T~AB=公式"
    ws3.merge_cells(start_row=1, start_column=1, end_row=1, end_column=28)
    _title_style(ws3.cell(1, 1))

    headers3 = ["首贷月份(ltv_month)", "MOB", "复购标数(double_cnt)", "复购用户数(double_mid)",
                "首贷用户数(frs_cnt)",
                "进件数(app_cnt)", "进入授信数(in_sx_cnt)", "进件池放款数(app_issue_cnt)",
                "授信通过数(sx_passed_cnt)", "放款笔数(issue_cnt)", "放款金额(contract_amt)",
                "前砍金额(haircut_amt)", "后收息费(should_interest_amt)", "1T0坏账(t0_bad_amt)",
                "1T0应还本金(t0_should_capit)", "4t7坏账(t7_bad_amt)", "4t7应还本金(t7_should_capit)",
                "1t0出账数(t0_billed_cnt)", "4t7出账数(t7_billed_cnt)",
                "整体复购矩阵", "复购用户占比", "单户成交标数",
                "整体通过率", "放款件均", "前砍比例", "后收息费比例", "1T0逾期率", "4t7逾期率"]
    for ci, h in enumerate(headers3, 1):
        ws3.cell(2, ci).value = h
        _header_style(ws3.cell(2, ci))

    for ri, row in enumerate(vintage_df.itertuples(index=False), 3):
        ws3.cell(ri, 1).value = row.ltv_month
        ws3.cell(ri, 1).number_format = '@'
        ws3.cell(ri, 2).value = int(row.mob)
        ws3.cell(ri, 3).value = int(row.double_cnt)
        ws3.cell(ri, 4).value = int(row.double_mid)
        ws3.cell(ri, 5).value = int(row.frs_cnt)
        ws3.cell(ri, 6).value = int(row.app_cnt)
        ws3.cell(ri, 7).value = int(row.in_sx_cnt)
        ws3.cell(ri, 8).value = int(row.app_issue_cnt)
        ws3.cell(ri, 9).value = int(row.sx_passed_cnt)
        ws3.cell(ri, 10).value = int(row.issue_cnt)
        ws3.cell(ri, 11).value = float(row.contract_amt)
        ws3.cell(ri, 12).value = float(row.haircut_amt)
        ws3.cell(ri, 13).value = float(row.should_interest_amt)
        ws3.cell(ri, 14).value = float(row.t0_bad_amt)
        ws3.cell(ri, 15).value = float(row.t0_should_capit)
        ws3.cell(ri, 16).value = float(row.t7_bad_amt)
        ws3.cell(ri, 17).value = float(row.t7_should_capit)
        ws3.cell(ri, 18).value = int(row.t0_billed_cnt)
        ws3.cell(ri, 19).value = int(row.t7_billed_cnt)
        # 原有比例公式
        ws3.cell(ri, 20).value = f"=IF($E{ri}=0,\"\",$C{ri}/$E{ri})"   # 整体复购矩阵
        ws3.cell(ri, 21).value = f"=IF($E{ri}=0,\"\",$D{ri}/$E{ri})"   # 复购用户占比
        ws3.cell(ri, 22).value = f"=IF($D{ri}=0,\"\",$C{ri}/$D{ri})"   # 单户成交标数
        # 新增指标公式
        ws3.cell(ri, 23).value = f"=IF(OR($F{ri}=0,$H{ri}=0),\"\",($G{ri}/$F{ri})*($H{ri}/$I{ri}))"  # 整体通过率
        ws3.cell(ri, 24).value = f"=IF($J{ri}=0,\"\",$K{ri}/$J{ri})"   # 放款件均
        ws3.cell(ri, 25).value = f"=IF($K{ri}=0,\"\",$L{ri}/$K{ri})"   # 前砍比例
        ws3.cell(ri, 26).value = f"=IF($K{ri}=0,\"\",$M{ri}/$K{ri})"   # 后收息费比例
        ws3.cell(ri, 27).value = f"=IF($O{ri}=0,\"\",$N{ri}/$O{ri})"   # 1T0逾期率
        ws3.cell(ri, 28).value = f"=IF($Q{ri}=0,\"\",$P{ri}/$Q{ri})"   # 4t7逾期率

        _data_style(ws3.cell(ri, 1), fmt='@')
        _data_style(ws3.cell(ri, 2), fmt='0')
        for c in range(3, 6):
            _data_style(ws3.cell(ri, c), fmt='#,##0')
        for c in (6, 7, 8, 9, 10, 18, 19):
            _data_style(ws3.cell(ri, c), fmt='#,##0')
        for c in range(11, 18):
            _data_style(ws3.cell(ri, c), fmt='#,##0.00')
        _data_style(ws3.cell(ri, 20), fmt='0%')
        _data_style(ws3.cell(ri, 21), fmt='0%')
        _data_style(ws3.cell(ri, 22), fmt='0.00')
        _data_style(ws3.cell(ri, 23), fmt='0.00%')
        _data_style(ws3.cell(ri, 24), fmt='#,##0.00')
        _data_style(ws3.cell(ri, 25), fmt='0.00%')
        _data_style(ws3.cell(ri, 26), fmt='0.00%')
        _data_style(ws3.cell(ri, 27), fmt='0.00%')
        _data_style(ws3.cell(ri, 28), fmt='0.00%')

    widths3 = {'A': 18, 'B': 8, 'C': 16, 'D': 16, 'E': 16,
               'F': 14, 'G': 14, 'H': 16, 'I': 16, 'J': 14, 'K': 16,
               'L': 14, 'M': 16, 'N': 14, 'O': 16, 'P': 14, 'Q': 16,
               'R': 14, 'S': 14, 'T': 12, 'U': 12, 'V': 12,
               'W': 12, 'X': 12, 'Y': 12, 'Z': 12, 'AA': 12, 'AB': 12}
    for letter, w in widths3.items():
        ws3.column_dimensions[letter].width = w
    ws3.sheet_view.showGridLines = False

    # ==================== vintage 透视矩阵 Sheets ====================
    # 原有三个（保留 C/D/E 列不变）
    _add_vintage_matrix_sheet(
        wb, "整体复购vintage",
        f"整体复购矩阵 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='0%', mode='ratio', num_col='C', den_col='E')

    _add_vintage_matrix_sheet(
        wb, "复购用户占比vintage",
        f"复购用户占比 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='0%', mode='ratio', num_col='D', den_col='E')

    _add_vintage_matrix_sheet(
        wb, "单户成交标数vintage",
        f"单户成交标数 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='0.00', mode='ratio', num_col='C', den_col='D')

    # 新增指标透视矩阵
    _add_vintage_matrix_sheet(
        wb, "进件数vintage",
        f"进件数 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='#,##0', mode='sum', num_col=col["app_cnt"])

    _add_vintage_matrix_sheet(
        wb, "整体通过率vintage",
        f"整体通过率 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='0.00%', mode='pass_rate',
        num_col=col["in_sx_cnt"], den_col=col["app_cnt"],
        num2_col=col["app_issue_cnt"], den2_col=col["sx_passed_cnt"])

    _add_vintage_matrix_sheet(
        wb, "放款笔数vintage",
        f"放款笔数 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='#,##0', mode='sum', num_col=col["issue_cnt"])

    _add_vintage_matrix_sheet(
        wb, "放款金额vintage",
        f"放款金额 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='#,##0', mode='sum', num_col=col["contract_amt"])

    _add_vintage_matrix_sheet(
        wb, "放款件均vintage",
        f"放款件均 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='#,##0.00', mode='ratio',
        num_col=col["contract_amt"], den_col=col["issue_cnt"])

    _add_vintage_matrix_sheet(
        wb, "1T0逾期率vintage",
        f"1T0逾期率 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='0.00%', mode='ratio',
        num_col=col["t0_bad_amt"], den_col=col["t0_should_capit"])

    _add_vintage_matrix_sheet(
        wb, "4t7逾期率vintage",
        f"4t7逾期率 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='0.00%', mode='ratio',
        num_col=col["t7_bad_amt"], den_col=col["t7_should_capit"])

    _add_vintage_matrix_sheet(
        wb, "前砍比例vintage",
        f"前砍比例 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='0.00%', mode='ratio',
        num_col=col["haircut_amt"], den_col=col["contract_amt"])

    _add_vintage_matrix_sheet(
        wb, "后收息费比例vintage",
        f"后收息费比例 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='0.00%', mode='ratio',
        num_col=col["should_interest_amt"], den_col=col["contract_amt"])

    _add_vintage_matrix_sheet(
        wb, "1t0出账数vintage",
        f"1t0出账数 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='#,##0', mode='sum', num_col=col["t0_billed_cnt"])

    _add_vintage_matrix_sheet(
        wb, "4t7出账数vintage",
        f"4t7出账数 vintage ({start_month} ~ {end_month}) -- SUMIFS引用vintage底表",
        ltv_months_desc, fmt='#,##0', mode='sum', num_col=col["t7_billed_cnt"])

    wb.save(output_path)
    print(f"  Excel 已保存: {output_path}")


def _add_vintage_matrix_sheet(wb, sheet_name, title, ltv_months_desc, fmt,
                               mode='ratio', num_col=None, den_col=None,
                               num2_col=None, den2_col=None):
    """添加一个 vintage 透视矩阵 Sheet（公式驱动 + 最新表现比例对角线）。

    结构：A=最新表现比例(对角线), B=MOB, C+=首贷月份(降序)
    三种模式：
      mode='sum'       : SUMIFS(num_col)
      mode='ratio'     : SUMIFS(num_col) / SUMIFS(den_col)
      mode='pass_rate' : (SUMIFS(num_col)/SUMIFS(den_col)) * (SUMIFS(num2_col)/SUMIFS(den2_col))

    对角线（最新表现比例）：MOB_n 取第 n+1 列月份的数据（即最新可表现月份）
    """
    ws = wb.create_sheet(sheet_name)
    n_months = len(ltv_months_desc)

    # 黄色高亮（对角线）
    yellow_fill = PatternFill("solid", fgColor="FFFF00")

    # 标题
    ws.cell(1, 1).value = title
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n_months + 2)
    _title_style(ws.cell(1, 1))

    # 表头：A=最新表现比例, B=MOB, C+=首贷月份（降序）
    ws.cell(2, 1).value = "最新表现比例"
    _header_style(ws.cell(2, 1))
    ws.cell(2, 2).value = "MOB"
    _header_style(ws.cell(2, 2))
    for ci, month_str in enumerate(ltv_months_desc, 3):
        ws.cell(2, ci).value = month_str
        ws.cell(2, ci).number_format = '@'
        _header_style(ws.cell(2, ci))

    # 数据行 MOB 0-12
    for mob in range(13):
        r = 3 + mob
        # B列: MOB
        ws.cell(r, 2).value = mob
        _data_style(ws.cell(r, 2), fmt='0')

        # A列: 最新表现比例（对角线）— MOB_n 取第 (3+n) 列即 C+n 列
        if mob < n_months:
            diag_col = get_column_letter(3 + mob)
            ws.cell(r, 1).value = f"={diag_col}{r}"
            _data_style(ws.cell(r, 1), fmt=fmt)
            ws.cell(r, 1).fill = yellow_fill
        else:
            ws.cell(r, 1).value = ""
            _data_style(ws.cell(r, 1), fmt=fmt)
            ws.cell(r, 1).fill = yellow_fill

        # C+列: 各月份 SUMIFS 数据
        for ci in range(3, n_months + 3):
            col_letter = get_column_letter(ci)
            if mode == 'sum':
                numerator = (
                    f"SUMIFS('vintage底表'!${num_col}:${num_col},"
                    f"'vintage底表'!$A:$A,{col_letter}$2,"
                    f"'vintage底表'!$B:$B,$B{r})"
                )
            elif mode == 'pass_rate':
                numerator = (
                    f"("
                    f"SUMIFS('vintage底表'!${num_col}:${num_col},"
                    f"'vintage底表'!$A:$A,{col_letter}$2,"
                    f"'vintage底表'!$B:$B,$B{r})"
                    f"/"
                    f"SUMIFS('vintage底表'!${den_col}:${den_col},"
                    f"'vintage底表'!$A:$A,{col_letter}$2,"
                    f"'vintage底表'!$B:$B,$B{r})"
                    f")*("
                    f"SUMIFS('vintage底表'!${num2_col}:${num2_col},"
                    f"'vintage底表'!$A:$A,{col_letter}$2,"
                    f"'vintage底表'!$B:$B,$B{r})"
                    f"/"
                    f"SUMIFS('vintage底表'!${den2_col}:${den2_col},"
                    f"'vintage底表'!$A:$A,{col_letter}$2,"
                    f"'vintage底表'!$B:$B,$B{r})"
                    f")"
                )
            else:  # ratio
                numerator = (
                    f"SUMIFS('vintage底表'!${num_col}:${num_col},"
                    f"'vintage底表'!$A:$A,{col_letter}$2,"
                    f"'vintage底表'!$B:$B,$B{r})"
                    f"/"
                    f"SUMIFS('vintage底表'!${den_col}:${den_col},"
                    f"'vintage底表'!$A:$A,{col_letter}$2,"
                    f"'vintage底表'!$B:$B,$B{r})"
                )

            formula = f"=IFERROR({numerator},\"\")"
            ws.cell(r, ci).value = formula
            _data_style(ws.cell(r, ci), fmt=fmt)

    # 列宽
    ws.column_dimensions['A'].width = 16
    ws.column_dimensions['B'].width = 10
    for col in range(3, n_months + 3):
        ws.column_dimensions[get_column_letter(col)].width = 14
    ws.sheet_view.showGridLines = False


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="墨西哥复购矩阵 vintage 查询（公式驱动版）")
    parser.add_argument("--start", default="2024-07-01", help="首贷月份起始，默认 2024-07-01")
    parser.add_argument("--end", default=None, help="首贷月份截止，默认当前月")
    args = parser.parse_args()

    start_month = args.start
    end_month = args.end or pd.Timestamp.now().strftime("%Y-%m-01")

    print("=" * 60)
    print("墨西哥复购矩阵 vintage 查询（公式驱动版）")
    print(f"  首贷月份范围: {start_month} ~ {end_month}")
    print("=" * 60)

    print("\n[1/5] 连接墨西哥 Presto...")
    pq = PrestoQuery()
    pq.login()
    print("  连接成功")

    print("\n[2/5] 执行 vintage 底表 SQL...")
    vintage_df = pq.query(build_vintage_sql(start_month, end_month), wait_sec=5)
    if isinstance(vintage_df, str):
        print(f"  查询失败: {vintage_df[:500]}")
        return
    print(f"  返回 {len(vintage_df)} 行 x {len(vintage_df.columns)} 列")

    print("\n[3/5] 执行首贷用户数 SQL...")
    first_loan_df = pq.query(build_first_loan_sql(start_month, end_month), wait_sec=5)
    if isinstance(first_loan_df, str):
        print(f"  查询失败: {first_loan_df[:500]}")
        return
    print(f"  返回 {len(first_loan_df)} 行")

    print("\n[4/5] 执行放款池 / 进件池 SQL...")
    loan_pool_df = pq.query(build_loan_pool_sql(start_month, end_month), wait_sec=5)
    if isinstance(loan_pool_df, str):
        print(f"  放款池查询失败: {loan_pool_df[:500]}")
        return
    print(f"  放款池返回 {len(loan_pool_df)} 行")

    app_pool_df = pq.query(build_app_pool_sql(start_month, end_month), wait_sec=5)
    if isinstance(app_pool_df, str):
        print(f"  进件池查询失败: {app_pool_df[:500]}")
        return
    print(f"  进件池返回 {len(app_pool_df)} 行")

    print("\n  补全全组合网格...")
    full_df = fill_full_grid(vintage_df, loan_pool_df, app_pool_df, first_loan_df)
    n_months = full_df["ltv_month"].nunique()
    print(f"  全组合: {len(full_df)} 行（{n_months} 个月 x 13 MOB）")
    print(full_df.head(15).to_string(index=False))
    print("  ...")

    print("\n[5/5] 导出 Excel（公式驱动）...")
    out_dir = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(
        out_dir,
        f"墨西哥复购矩阵_vintage_{start_month.replace('-', '')}_{end_month.replace('-', '')}_{pd.Timestamp.now().strftime('%H%M%S')}.xlsx"
    )
    build_excel(full_df, out_path, start_month, end_month)
    print("\n完成！")
    print(f"  文件: {out_path}")
    print("  结构: vintage底表=Presto原始数据, vintage表=SUMIFS+对角线, 复购矩阵=引用对角线")
    print("  对角线: 每个MOB取最新可表现月份的数据(黄色高亮), 复购矩阵直接引用")


if __name__ == "__main__":
    main()
