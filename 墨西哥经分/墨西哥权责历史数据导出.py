# -*- coding: utf-8 -*-
"""
墨西哥权责历史数据 — 进件端 + 权责端合并导出
=============================================
SQL1: mx.daily_order_base_final  → 进件/放款/CPS/通过率等
SQL2: mx.wxs_application_funnel   → 期限/息费率/坏账率等
两表按 (qz_month, is_reloan) Join，增加日均花费金额，导出Excel
"""

import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime
import calendar

# ═══════════════════════════════════════════════════════
# SQL1: 进件端（花费/进件/放款/CPS/通过率）
# ═══════════════════════════════════════════════════════
SQL1 = """
select 
DATE_PARSE(date_mon || '-01', '%Y-%m-%d') AS qz_month
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
where data_date>=date'2025-01-01'
group by 1,2
order by 1 desc ,2
"""

# ═══════════════════════════════════════════════════════
# SQL2: 权责端（期限/息费率/坏账率）
# ═══════════════════════════════════════════════════════
SQL2 = """
select
    date_trunc('month', date(r.release_time)) as qz_month, 
    r.is_reloan, 
    sum(loan_cycle*contract_amount)*1.0/sum(contract_amount) as avg_loan_cycle,
    sum(r.should_interest)*1.0000/sum(r.contract_amount)   as interest_rate,
    sum(r.haircut_amount)*1.0000/sum(r.contract_amount)   as haircut_rate,
    case when sum(r.t7_should_capit_4)=0 then 0 else sum(r.t7_overdue_capit_4)*1.0000/sum(r.t7_should_capit_4) end  as capit_bad_rate,
    case when sum(r.t7_should_amt_4)=0 then 0 else sum(r.t7_overdue_amount_4)*1.0000/sum(r.t7_should_amt_4) end as amt_bad_rate,
    case when sum(r.t7_should_interest_4)=0 then 0 else sum(r.t7_overdue_interest_4)*1.0000/sum(r.t7_should_interest_4) end as interest_bad_rate
from mx.wxs_application_funnel r 
where  r.if_issue=1 
and date(r.release_time) >= date'2025-01-01'
 GROUP BY 1,2
 order by 1 desc, 2
"""

# ═══════════════════════════════════════════════════════
# 输出路径
# ═══════════════════════════════════════════════════════
OUTPUT_DIR = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"墨西哥权责历史数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")


def run():
    print("=" * 60)
    print("墨西哥权责历史数据 — 进件+权责合并导出")
    print("=" * 60)

    # ── 1. 连接数据库 ────────────────────────────────
    print("\n[1/4] 连接墨西哥 Presto...")
    pq = PrestoQuery()
    pq.login()
    print("  连接成功")

    # ── 2. 执行SQL1（进件端）────────────────────────
    print("\n[2/4] 查询进件端数据 (mx.daily_order_base_final)...")
    df1 = pq.query(SQL1, wait_sec=5)
    if isinstance(df1, str):
        print(f"  查询失败: {df1[:300]}")
        return
    print(f"  返回 {len(df1)} 行 × {len(df1.columns)} 列")
    print(f"  列: {list(df1.columns)}")

    # ── 3. 执行SQL2（权责端）────────────────────────
    print("\n[3/4] 查询权责端数据 (mx.wxs_application_funnel)...")
    df2 = pq.query(SQL2, wait_sec=5)
    if isinstance(df2, str):
        print(f"  查询失败: {df2[:300]}")
        return
    print(f"  返回 {len(df2)} 行 × {len(df2.columns)} 列")
    print(f"  列: {list(df2.columns)}")

    # ── 4. 合并 + 计算 + 导出 ────────────────────────
    print("\n[4/4] 合并数据 + 计算日均花费 + 导出Excel...")

    # 数值转换
    for col in df1.columns:
        if col not in ("qz_month", "is_reloan"):
            df1[col] = pd.to_numeric(df1[col], errors="coerce")
    for col in df2.columns:
        if col not in ("qz_month", "is_reloan"):
            df2[col] = pd.to_numeric(df2[col], errors="coerce")

    # 统一 qz_month 格式为 date
    df1["qz_month"] = pd.to_datetime(df1["qz_month"]).dt.date
    df2["qz_month"] = pd.to_datetime(df2["qz_month"]).dt.date

    # Merge
    df = pd.merge(df1, df2, on=["qz_month", "is_reloan"], how="outer")

    # 计算日均花费金额 = ad_cost / 当月天数
    def get_month_days(d):
        if pd.isna(d):
            return 30
        if isinstance(d, str):
            d = pd.to_datetime(d).date()
        return calendar.monthrange(d.year, d.month)[1]

    df["month_days"] = df["qz_month"].apply(get_month_days)
    df["daily_ad_cost"] = (df["ad_cost"] / df["month_days"]).round(2)

    # 排序: 月份降序, is_reloan (new在前)
    df["is_reloan_sort"] = df["is_reloan"].apply(lambda x: 0 if x == "new" else 1)
    df = df.sort_values(["qz_month", "is_reloan_sort"], ascending=[False, True]).drop(columns=["is_reloan_sort"])

    # 列顺序
    col_order = [
        "qz_month", "is_reloan",
        "ad_cost", "daily_ad_cost", "apply_cnt", "loan_cnt",
        "loan_contract_amt_usd", "loan_amt_avg", "cps",
        "confirm_rate", "pass_rate",
        "avg_loan_cycle", "interest_rate", "haircut_rate",
        "capit_bad_rate", "amt_bad_rate", "interest_bad_rate",
        "month_days"
    ]
    # 只保留存在的列
    col_order = [c for c in col_order if c in df.columns]
    df = df[col_order]

    # 列名中文映射
    col_rename = {
        "qz_month": "权责月份",
        "is_reloan": "首复贷",
        "ad_cost": "花费金额(USD)",
        "daily_ad_cost": "日均花费(USD)",
        "apply_cnt": "进件数",
        "loan_cnt": "放款数",
        "loan_contract_amt_usd": "放款金额(USD)",
        "loan_amt_avg": "放款件均(USD)",
        "cps": "CPS(USD)",
        "confirm_rate": "用信率",
        "pass_rate": "通过率",
        "avg_loan_cycle": "平均期限",
        "interest_rate": "实收息费率",
        "haircut_rate": "砍头比例",
        "capit_bad_rate": "本金坏账率",
        "amt_bad_rate": "本金息费坏账率",
        "interest_bad_rate": "息费坏账率",
        "month_days": "当月天数",
    }
    df = df.rename(columns=col_rename)

    # 首复贷标签: new→首贷, old→复贷
    df["首复贷"] = df["首复贷"].apply(lambda x: "首贷" if x == "new" else ("复贷" if x == "old" else x))

    print(f"  合并后: {len(df)} 行 × {len(df.columns)} 列")
    print(df.head(10).to_string(index=False))

    # ── 导出Excel ──
    write_excel(df)
    print(f"\n  已保存: {OUTPUT_FILE}")
    print("=" * 60)
    print("完成!")


def write_excel(df):
    """格式化导出Excel"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "墨西哥权责历史数据"

    # 样式
    FONT_HDR = Font(name="微软雅黑", size=10, bold=True, color="FFFFFFFF")
    FONT_DATA = Font(name="微软雅黑", size=10, color="FF000000")
    HDR_FILL = PatternFill("solid", fgColor="4472C4")
    THIN = Side(style="thin")
    BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
    ALIGN_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")

    # 写表头
    for ci, col_name in enumerate(df.columns, 1):
        c = ws.cell(1, ci)
        c.value = col_name
        c.font = FONT_HDR
        c.fill = HDR_FILL
        c.border = BORDER
        c.alignment = ALIGN_CENTER

    # 写数据
    for ri, (_, row) in enumerate(df.iterrows(), 2):
        for ci, col_name in enumerate(df.columns, 1):
            val = row[col_name]
            c = ws.cell(ri, ci)
            if pd.isna(val):
                c.value = None
            elif isinstance(val, (int, float)):
                c.value = float(val) if float(val) != int(val) else int(val)
            else:
                c.value = val
            c.font = FONT_DATA
            c.border = BORDER

            # 数值格式
            if col_name in ("花费金额(USD)", "日均花费(USD)", "放款金额(USD)"):
                c.number_format = '#,##0.00'
                c.alignment = ALIGN_RIGHT
            elif col_name in ("进件数", "放款数", "当月天数"):
                c.number_format = '#,##0'
                c.alignment = ALIGN_RIGHT
            elif col_name in ("放款件均(USD)", "CPS(USD)", "平均期限"):
                c.number_format = '0.00'
                c.alignment = ALIGN_RIGHT
            elif col_name in ("用信率", "通过率", "实收息费率", "砍头比例",
                              "本金坏账率", "本金息费坏账率", "息费坏账率"):
                c.number_format = '0.00%'
                c.alignment = ALIGN_RIGHT
            elif col_name == "权责月份":
                c.number_format = 'yyyy-mm'
                c.alignment = ALIGN_CENTER
            else:
                c.alignment = ALIGN_CENTER

    # 列宽
    col_widths = {
        "权责月份": 12, "首复贷": 8,
        "花费金额(USD)": 14, "日均花费(USD)": 14,
        "进件数": 10, "放款数": 10,
        "放款金额(USD)": 14, "放款件均(USD)": 12,
        "CPS(USD)": 10, "用信率": 10, "通过率": 10,
        "平均期限": 10, "实收息费率": 10, "砍头比例": 10,
        "本金坏账率": 12, "本金息费坏账率": 14, "息费坏账率": 12,
        "当月天数": 8,
    }
    for ci, col_name in enumerate(df.columns, 1):
        letter = get_column_letter(ci)
        width = col_widths.get(col_name, 12)
        ws.column_dimensions[letter].width = width

    # 行高
    ws.row_dimensions[1].height = 30

    # 无网格线
    ws.sheet_view.showGridLines = False

    # 冻结首行+前两列
    ws.freeze_panes = "C2"

    wb.save(OUTPUT_FILE)


if __name__ == "__main__":
    run()
