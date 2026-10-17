# -*- coding: utf-8 -*-
"""墨西哥复购矩阵 —— 复贷月锚点动态分组分析（含总量对账）。

逻辑（以复贷月为锚点）：
- 对每个复贷月（2026-08、2026-09），首贷客户分两组：
  - 历史首贷：首贷月 < 该复贷月（从 2024 起截至复贷月前一月）
  - 当月新首贷：首贷月 = 该复贷月
- 总量 = 历史首贷 + 当月新首贷（8月复贷全部来源）
- 绝对数指标：总量 = 历史 + 当月（严格对账）
- 比例指标：总量按分子分母总量重算（等价加权），不是简单相加
- 进件类按进件月(app_time)，放款类按放款月(release_time)
"""

import sys
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side

sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

# ---- 关键日期参数 ----
FIRST_LOAN_MIN = "2024-01-01"     # 历史首贷最早月
REP_MONTHS = ("2026-08-01", "2026-09-01")  # 两个复贷月


def build_app_pool_sql():
    """进件池：进件数 / 整体通过率 分子分母。

    复贷月 = 进件月；分组 = 首贷月是否等于该复贷月。
    """
    months = ",".join(f"DATE '{m}'" for m in REP_MONTHS)
    return f"""
WITH pool AS (
    SELECT
        date_trunc('month', date(r.app_time)) AS rep_month,
        CASE WHEN d.ltv_month = date_trunc('month', date(r.app_time))
             THEN '当月新首贷' ELSE '历史首贷' END AS grp,
        r.if_app,
        r.if_in_sx,
        r.if_issue,
        r.if_SX_passed
    FROM mx.wxs_application_funnel r
    LEFT JOIN mx.ys_dl_ltv_first_loan_0511 d
        ON cast(r.cust_id AS bigint) = d.mid
    WHERE r.is_reloan = 'old'
      AND d.mid IS NOT NULL
      AND d.ltv_month >= DATE '{FIRST_LOAN_MIN}'
      AND d.ltv_month <= date_trunc('month', date(r.app_time))
      AND date_trunc('month', date(r.app_time)) IN ({months})
)
SELECT
    rep_month,
    grp,
    sum(if_app)       AS app_cnt,
    sum(if_in_sx)     AS in_sx_cnt,
    sum(if_issue)     AS app_issue_cnt,
    sum(if_SX_passed) AS sx_passed_cnt
FROM pool
GROUP BY 1, 2
ORDER BY 1, 2
"""


def build_loan_pool_sql():
    """放款池：复购标数/用户数、放款、前砍后收、1T0-4t7、出账数。

    复贷月 = 放款月；分组 = 首贷月是否等于该放款月。
    """
    months = ",".join(f"DATE '{m}'" for m in REP_MONTHS)
    return f"""
WITH pool AS (
    SELECT
        date_trunc('month', date(r.release_time)) AS rep_month,
        CASE WHEN d.ltv_month = date_trunc('month', date(r.release_time))
             THEN '当月新首贷' ELSE '历史首贷' END AS grp,
        r.camera_id,
        r.cust_id,
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
      AND d.ltv_month >= DATE '{FIRST_LOAN_MIN}'
      AND d.ltv_month <= date_trunc('month', date(r.release_time))
      AND date_trunc('month', date(r.release_time)) IN ({months})
)
SELECT
    rep_month,
    grp,
    count(distinct camera_id) AS double_cnt,
    count(distinct cust_id)   AS double_mid,
    sum(if_issue)             AS issue_cnt,
    sum(contract_amount)      AS contract_amt,
    sum(haircut_amount)       AS haircut_amt,
    sum(should_interest)      AS should_interest_amt,
    sum(if(is_t0_window_1 = 1, coalesce(t0_overdue_capit_1, 0) + coalesce(t0_overdue_interest_1, 0), 0)) AS t0_bad_amt,
    sum(if(is_t0_window_1 = 1, coalesce(t0_should_capit_1, 0), 0)) AS t0_should_capit,
    sum(if(is_t7_window_4 = 1, coalesce(t7_overdue_capit_4, 0) + coalesce(t7_overdue_interest_4, 0), 0)) AS t7_bad_amt,
    sum(if(is_t7_window_4 = 1, coalesce(t7_should_capit_4, 0), 0)) AS t7_should_capit,
    sum(if(is_t0_window_1 = 1, 1, 0)) AS t0_billed_cnt,
    sum(if(is_t7_window_4 = 1, 1, 0)) AS t7_billed_cnt
FROM pool
GROUP BY 1, 2
ORDER BY 1, 2
"""


def build_first_loan_sql():
    """首贷用户数（分母），按复贷月动态分组。

    对每个复贷月：当月新首贷 = 首贷月=复贷月；历史首贷 = 首贷月<复贷月。
    """
    months = ",".join(f"DATE '{m}'" for m in REP_MONTHS)
    return f"""
WITH months AS (
    SELECT month FROM (VALUES {months}) AS t(month)
),
frs AS (
    SELECT
        m.month AS rep_month,
        CASE WHEN d.ltv_month = m.month THEN '当月新首贷' ELSE '历史首贷' END AS grp,
        d.mid
    FROM months m
    JOIN mx.ys_dl_ltv_first_loan_0511 d
        ON d.ltv_month >= DATE '{FIRST_LOAN_MIN}'
       AND d.ltv_month <= m.month
)
SELECT
    rep_month,
    grp,
    count(distinct mid) AS frs_cnt
FROM frs
GROUP BY 1, 2
ORDER BY 1, 2
"""


def build_product_dist_sql(rep_month="2026-08-01"):
    """产品分布：8月复贷放款，按 历史首贷/当月新首贷 x 产品名 聚合放款笔数、放款金额。"""
    return f"""
SELECT
    CASE WHEN d.ltv_month = DATE '{rep_month}' THEN '当月新首贷' ELSE '历史首贷' END AS grp,
    coalesce(r.product_name, '未知') AS product_name,
    count(*) AS issue_cnt,
    sum(r.contract_amount) AS contract_amt
FROM mx.wxs_application_funnel r
LEFT JOIN mx.ys_dl_ltv_first_loan_0511 d
    ON cast(r.cust_id AS bigint) = d.mid
WHERE r.is_reloan = 'old'
  AND r.if_issue = 1
  AND d.mid IS NOT NULL
  AND d.ltv_month >= DATE '{FIRST_LOAN_MIN}'
  AND d.ltv_month <= DATE '{rep_month}'
  AND date_trunc('month', date(r.release_time)) = DATE '{rep_month}'
GROUP BY 1, 2
ORDER BY 2, 1
"""


def build_product_pivot(product_df):
    """产品分布透视：行=产品名，列=[历史笔数,历史金额,当月笔数,当月金额]，加占比与总计。"""
    products = sorted(product_df["product_name"].unique())

    def get(grp, col):
        m = {(r.product_name, r.grp): r for r in product_df.itertuples()}
        return [float(getattr(m[(p, grp)], col)) if (p, grp) in m else 0.0 for p in products]

    hist_cnt = get("历史首贷", "issue_cnt")
    hist_amt = get("历史首贷", "contract_amt")
    cur_cnt = get("当月新首贷", "issue_cnt")
    cur_amt = get("当月新首贷", "contract_amt")

    df = pd.DataFrame({
        "产品名": products,
        "历史首贷笔数": hist_cnt,
        "历史首贷金额": hist_amt,
        "当月新首贷笔数": cur_cnt,
        "当月新首贷金额": cur_amt,
    })
    df["总笔数"] = df["历史首贷笔数"] + df["当月新首贷笔数"]
    df["总金额"] = df["历史首贷金额"] + df["当月新首贷金额"]
    df["笔数占比"] = df["总笔数"] / df["总笔数"].sum()
    df["金额占比"] = df["总金额"] / df["总金额"].sum()
    # 当月贡献占比（当月笔数占该产品总笔数）
    df["当月笔数占比"] = df["当月新首贷笔数"] / df["总笔数"]
    df["当月金额占比"] = df["当月新首贷金额"] / df["总金额"]
    df = df.sort_values("总金额", ascending=False).reset_index(drop=True)

    # 总计行
    total = df[["历史首贷笔数", "历史首贷金额", "当月新首贷笔数", "当月新首贷金额", "总笔数", "总金额"]].sum()
    total["产品名"] = "总计"
    total["笔数占比"] = 1.0
    total["金额占比"] = 1.0
    total["当月笔数占比"] = total["当月新首贷笔数"] / total["总笔数"]
    total["当月金额占比"] = total["当月新首贷金额"] / total["总金额"]
    df = pd.concat([df, total.to_frame().T], ignore_index=True)
    return df


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def merge_pools(app_df, loan_df, frs_df):
    """合并三份数据，补全 历史/当月 两组的 2 复贷月组合，再生成总量组。"""
    app_cols = ["app_cnt", "in_sx_cnt", "app_issue_cnt", "sx_passed_cnt"]
    loan_cols = ["double_cnt", "double_mid", "issue_cnt", "contract_amt", "haircut_amt",
                 "should_interest_amt", "t0_bad_amt", "t0_should_capit", "t7_bad_amt",
                 "t7_should_capit", "t0_billed_cnt", "t7_billed_cnt"]
    all_cols = app_cols + loan_cols

    def norm_month(df):
        df = df.copy()
        df["rep_month"] = pd.to_datetime(df["rep_month"]).dt.strftime("%Y-%m")
        df["grp"] = df["grp"].astype(str)
        return df

    app_df = norm_month(app_df)
    loan_df = norm_month(loan_df)
    frs_df = norm_month(frs_df)

    frs_map = {(row.grp, row.rep_month): _num(row.frs_cnt) for row in frs_df.itertuples()}

    grps = ["历史首贷", "当月新首贷"]
    months = ["2026-08", "2026-09"]

    rows = []
    for g in grps:
        for m in months:
            rec = {"grp": g, "rep_month": m, "frs_cnt": frs_map.get((g, m), 0.0)}
            am = app_df[(app_df["grp"] == g) & (app_df["rep_month"] == m)]
            lm = loan_df[(loan_df["grp"] == g) & (loan_df["rep_month"] == m)]
            for c in app_cols:
                rec[c] = _num(am[c].values[0]) if len(am) else 0.0
            for c in loan_cols:
                rec[c] = _num(lm[c].values[0]) if len(lm) else 0.0
            rows.append(rec)

    cols = ["grp", "rep_month", "frs_cnt"] + all_cols
    wide = pd.DataFrame(rows, columns=cols)

    # 生成总量组：历史 + 当月（按复贷月），绝对数相加
    total_rows = []
    for m in months:
        h = wide[(wide["grp"] == "历史首贷") & (wide["rep_month"] == m)]
        n = wide[(wide["grp"] == "当月新首贷") & (wide["rep_month"] == m)]
        rec = {"grp": "总量", "rep_month": m}
        for c in ["frs_cnt"] + all_cols:
            hv = _num(h[c].values[0]) if len(h) else 0.0
            nv = _num(n[c].values[0]) if len(n) else 0.0
            rec[c] = hv + nv
        total_rows.append(rec)

    total_df = pd.DataFrame(total_rows, columns=cols)
    wide = pd.concat([wide, total_df], ignore_index=True)

    grp_order = {"总量": 0, "历史首贷": 1, "当月新首贷": 2}
    wide["_gorder"] = wide["grp"].map(grp_order)
    wide = wide.sort_values(["rep_month", "_gorder"]).drop(columns="_gorder").reset_index(drop=True)
    return wide


def compute_metrics(wide):
    """计算 15 个指标（含总量组）。"""
    def div(a, b):
        return a / b if b else float("nan")

    out = []
    for _, r in wide.iterrows():
        label = f"{r['grp']}-{r['rep_month']}"
        out.append({
            "组合": label,
            "首贷用户数": r["frs_cnt"],
            "整体复购矩阵": div(r["double_cnt"], r["frs_cnt"]),
            "复购用户占比": div(r["double_mid"], r["frs_cnt"]),
            "单户成交标数": div(r["double_cnt"], r["double_mid"]),
            "进件数": r["app_cnt"],
            "整体通过率": div(r["in_sx_cnt"], r["app_cnt"]) * div(r["app_issue_cnt"], r["sx_passed_cnt"]),
            "放款笔数": r["issue_cnt"],
            "放款金额": r["contract_amt"],
            "放款件均": div(r["contract_amt"], r["issue_cnt"]),
            "1T0逾期率": div(r["t0_bad_amt"], r["t0_should_capit"]),
            "4t7逾期率": div(r["t7_bad_amt"], r["t7_should_capit"]),
            "前砍比例": div(r["haircut_amt"], r["contract_amt"]),
            "后收息费比例": div(r["should_interest_amt"], r["contract_amt"]),
            "1t0出账数": r["t0_billed_cnt"],
            "4t7出账数": r["t7_billed_cnt"],
        })
    return pd.DataFrame(out)


def build_pivot(metrics):
    """转成 指标 x 列 的横向表：列 = [总量-8月, 历史-8月, 当月-8月, 总量-9月, 历史-9月, 当月-9月]"""
    metric_names = [
        "首贷用户数", "整体复购矩阵", "复购用户占比", "单户成交标数", "进件数",
        "整体通过率", "放款笔数", "放款金额", "放款件均", "1T0逾期率", "4t7逾期率",
        "前砍比例", "后收息费比例", "1t0出账数", "4t7出账数",
    ]
    cols = ["总量-2026-08", "历史首贷-2026-08", "当月新首贷-2026-08",
            "总量-2026-09", "历史首贷-2026-09", "当月新首贷-2026-09"]
    data = {}
    for mname in metric_names:
        data[mname] = []
    for c in cols:
        grp, month = c.rsplit("-", 1)
        row = metrics[(metrics["组合"] == f"{grp}-{month}")]
        for mname in metric_names:
            data[mname].append(row.iloc[0][mname] if len(row) else float("nan"))
    piv = pd.DataFrame(data, index=cols).T.reset_index()
    piv.columns = ["指标"] + cols
    return piv


def export_excel(wide, metrics, pivot, product_pivot, out_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "指标对比"

    title = "墨西哥复购矩阵 —— 复贷月锚点动态分组（总量 = 历史首贷 + 当月新首贷）"
    ws.cell(1, 1).value = title
    ws.cell(1, 1).font = Font(name="微软雅黑", size=12, bold=True)

    header_fill = PatternFill("solid", fgColor="4472C4")
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    cols = ["总量-2026-08", "历史首贷-2026-08", "当月新首贷-2026-08",
            "总量-2026-09", "历史首贷-2026-09", "当月新首贷-2026-09"]
    pct_metrics = {"整体复购矩阵", "复购用户占比", "整体通过率", "1T0逾期率", "4t7逾期率", "前砍比例", "后收息费比例"}
    dec_metrics = {"单户成交标数", "放款件均"}

    ws.cell(3, 1).value = "指标"
    ws.cell(3, 1).font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFFFF")
    ws.cell(3, 1).fill = header_fill
    ws.cell(3, 1).border = border
    for ci, c in enumerate(cols, 2):
        cell = ws.cell(3, ci)
        cell.value = c
        cell.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFFFF")
        cell.fill = header_fill
        cell.border = border

    for ri, row in enumerate(pivot.itertuples(index=False), 4):
        mname = row[0]
        ws.cell(ri, 1).value = mname
        ws.cell(ri, 1).font = Font(name="微软雅黑", size=10)
        ws.cell(ri, 1).border = border
        for ci, val in enumerate(row[1:], 2):
            cell = ws.cell(ri, ci)
            cell.value = val
            cell.border = border
            cell.font = Font(name="微软雅黑", size=10)
            if pd.notna(val):
                if mname in pct_metrics:
                    cell.number_format = "0.00%"
                elif mname in dec_metrics:
                    cell.number_format = "#,##0.00"
                else:
                    cell.number_format = "#,##0"

    ws.column_dimensions["A"].width = 16
    for c in range(2, 8):
        ws.column_dimensions[chr(64 + c)].width = 16
    ws.sheet_view.showGridLines = False

    # 底表 Sheet
    ws2 = wb.create_sheet("底表")
    for ci, col_name in enumerate(wide.columns, 1):
        c = ws2.cell(1, ci)
        c.value = col_name
        c.font = Font(name="微软雅黑", size=10, bold=True)
        c.fill = header_fill
    for ri, row in enumerate(wide.itertuples(index=False), 2):
        for ci, val in enumerate(row, 1):
            ws2.cell(ri, ci).value = val
    ws2.sheet_view.showGridLines = False

    if product_pivot is not None:
        export_product_sheet(wb, product_pivot, header_fill, border)

    wb.save(out_path)
    print(f"  Excel 已保存: {out_path}")


def export_product_sheet(wb, product_pivot, header_fill, border):
    ws = wb.create_sheet("产品分布-8月")
    ws.cell(1, 1).value = "8月复贷放款 —— 产品分布（历史首贷 vs 当月新首贷）"
    ws.cell(1, 1).font = Font(name="微软雅黑", size=12, bold=True)

    headers = ["产品名", "历史首贷笔数", "历史首贷金额", "当月新首贷笔数", "当月新首贷金额",
               "总笔数", "总金额", "笔数占比", "金额占比", "当月笔数占比", "当月金额占比"]
    for ci, h in enumerate(headers, 1):
        c = ws.cell(2, ci)
        c.value = h
        c.font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFFFF")
        c.fill = header_fill
        c.border = border

    for ri, row in enumerate(product_pivot.itertuples(index=False), 3):
        is_total = row[0] == "总计"
        for ci, val in enumerate(row, 1):
            c = ws.cell(ri, ci)
            c.value = val
            c.border = border
            c.font = Font(name="微软雅黑", size=10, bold=is_total)
            if is_total:
                c.fill = PatternFill("solid", fgColor="D9E1F2")
            if ci == 1:
                c.number_format = "General"
            elif ci in (2, 4, 6):
                c.number_format = "#,##0"
            elif ci in (3, 5, 7):
                c.number_format = "#,##0.00"
            else:
                c.number_format = "0.00%"

    widths = [24, 12, 14, 12, 14, 10, 14, 9, 9, 11, 11]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i) if i <= 26 else "A"].width = w
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A3"
    return ws


def main():
    print("=" * 60)
    print("墨西哥复购矩阵 —— 复贷月锚点动态分组（含总量对账）")
    print(f"  复贷月: {REP_MONTHS}")
    print(f"  分组: 历史首贷(首贷月<复贷月) + 当月新首贷(首贷月=复贷月) = 总量")
    print("=" * 60)

    pq = PrestoQuery()
    pq.login()
    print("  连接成功")

    print("\n[1/3] 进件池...")
    app_df = pq.query(build_app_pool_sql(), wait_sec=5)
    if isinstance(app_df, str):
        print(f"  失败: {app_df[:500]}")
        return
    print(f"  {len(app_df)} 行")

    print("[2/3] 放款池...")
    loan_df = pq.query(build_loan_pool_sql(), wait_sec=5)
    if isinstance(loan_df, str):
        print(f"  失败: {loan_df[:500]}")
        return
    print(f"  {len(loan_df)} 行")

    print("[3/3] 首贷用户数...")
    frs_df = pq.query(build_first_loan_sql(), wait_sec=5)
    if isinstance(frs_df, str):
        print(f"  失败: {frs_df[:500]}")
        return
    print(f"  {len(frs_df)} 行")

    print("[4/4] 产品分布（8月复贷放款 x 产品名）...")
    product_df = pq.query(build_product_dist_sql("2026-08-01"), wait_sec=5)
    if isinstance(product_df, str):
        print(f"  失败: {product_df[:500]}")
        product_pivot = None
    else:
        print(f"  {len(product_df)} 行")
        product_pivot = build_product_pivot(product_df)

    wide = merge_pools(app_df, loan_df, frs_df)
    metrics = compute_metrics(wide)
    pivot = build_pivot(metrics)

    print("\n========== 底表 ==========")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 250)
    print(wide.to_string(index=False))

    print("\n========== 指标对比（横向） ==========")
    pct_metrics = {"整体复购矩阵", "复购用户占比", "整体通过率", "1T0逾期率", "4t7逾期率", "前砍比例", "后收息费比例"}
    dec_metrics = {"单户成交标数", "放款件均"}
    show = pivot.copy()
    for col in show.columns[1:]:
        show[col] = show[col].map(
            lambda x: f"{x:.2%}" if pd.notna(x) else "—")
    for ri, mname in enumerate(show["指标"]):
        if mname in pct_metrics:
            continue
        for col in show.columns[1:]:
            raw = pivot[pivot["指标"] == mname][col].values[0]
            if pd.notna(raw):
                show.loc[ri, col] = f"{raw:,.2f}" if mname in dec_metrics else f"{raw:,.0f}"
    print(show.to_string(index=False))

    # 对账校验：绝对数指标 总量 == 历史 + 当月
    print("\n========== 对账校验（8月，总量 = 历史 + 当月） ==========")
    ok = True
    for mname in ["首贷用户数", "进件数", "放款笔数", "放款金额", "1t0出账数", "4t7出账数"]:
        total = metrics[(metrics["组合"] == "总量-2026-08")].iloc[0][mname]
        hist = metrics[(metrics["组合"] == "历史首贷-2026-08")].iloc[0][mname]
        cur = metrics[(metrics["组合"] == "当月新首贷-2026-08")].iloc[0][mname]
        diff = abs(total - (hist + cur))
        flag = "OK" if diff < 1 else "!! 不对"
        if diff >= 1:
            ok = False
        print(f"  {mname:12s} 总量={total:,.0f}  历史={hist:,.0f} + 当月={cur:,.0f} = {hist+cur:,.0f}  {flag}")
    print(f"  对账结果: {'全部通过' if ok else '存在不一致，请检查'}")
    print("\n  (比例指标如复购率/逾期率的分母不同，不能直接相加，总量已按分子分母总量重算=加权)")

    out_dir = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"墨西哥复购矩阵_当月影响_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

    if product_pivot is not None:
        print("\n========== 产品分布（8月复贷放款） ==========")
        pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
        print(product_pivot.to_string(index=False))

    export_excel(wide, metrics, pivot, product_pivot, out_path)
    print("\n完成！")


if __name__ == "__main__":
    main()
