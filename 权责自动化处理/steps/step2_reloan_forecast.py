# -*- coding: utf-8 -*-
"""
Step 2: 首贷 + 复贷进件量预估
从数据库查询历史数据 → 计算MOB转化率 → MA平滑 → 生成预估Excel

从 reloan_forecast_v11.py 提取核心算法
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import calendar
import openpyxl
from datetime import datetime
from dateutil.relativedelta import relativedelta

from core.db import PrestoQuery
from core.config import load_config
from core.excel_styles import (
    HDR_FILL, SUB_FILL, YLW_FILL, GRN_FILL, ORG_FILL, BLU_FILL, RED_FILL,
    WHT_FONT, BLD_FONT, PCT_FMT, NUM_FMT, USD_FMT, USD_FMT_INT,
    header_style, set_col_width, thin_border,
)


# ═══════════════════════════════════════════════════════════════
# SQL
# ═══════════════════════════════════════════════════════════════

SQL_FIRST_LOAN = """
WITH raw AS (
    SELECT
        SUBSTR(CAST(issue_month AS VARCHAR), 1, 7) AS month,
        COUNT(DISTINCT biz_id) AS loan_cnt
    FROM ind.ba_asset_base_info
    WHERE release_time IS NOT NULL
      AND release_time >= DATE '2022-01-01'
      AND grant_strategy = 'NEW'
    GROUP BY 1
)
SELECT
    month,
    CASE
        WHEN month = SUBSTR(CAST(CURRENT_DATE AS VARCHAR), 1, 7) AND DAY(CURRENT_DATE) > 1
        THEN CAST(ROUND(
              loan_cnt * 1.0 / (DAY(CURRENT_DATE) - 1)
            * EXTRACT(DAY FROM (
                DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1' month - INTERVAL '1' day
              ))
        , 0) AS BIGINT)
        ELSE loan_cnt
    END AS loan_cnt
FROM raw
ORDER BY 1 DESC
"""

SQL_RELOAN = """
SELECT
     tag,
     month,
     loan_type2,
     month_num,
     CASE
         WHEN rl_month = SUBSTR(CAST(CURRENT_DATE AS VARCHAR), 1, 7)
              AND DAY(CURRENT_DATE) > 1
         THEN CAST(ROUND(
             loan_cnt * 1.0 / (DAY(CURRENT_DATE) - 1)
             * EXTRACT(DAY FROM (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1' MONTH - INTERVAL '1' DAY))
         , 0) AS BIGINT)
         ELSE loan_cnt
     END AS loan_cnt,
     rl_month
 FROM
 (
     SELECT
         'application' AS tag,
         TO_CHAR(a.release_time, 'yyyy-mm') AS month,
         (YEAR(DATE(b.app_date)) - YEAR(a.release_time)) * 12
         + (MONTH(DATE(b.app_date)) - MONTH(a.release_time)) AS month_num,
         TO_CHAR(DATE(b.app_date), 'yyyy-mm') AS rl_month,
         b.loan_type2,
         COUNT(DISTINCT b.biz_id) AS loan_cnt
     FROM
     (
         SELECT
             a.release_time,
             a.mid
         FROM dwd.dwd_loan_info a
         LEFT JOIN ind.xly_application_funnel c
             ON TRY_CAST(a.order_no AS BIGINT) = TRY_CAST(c.biz_id AS BIGINT)
         WHERE
             c.grant_strategy = 'NEW'
             AND a.release_time IS NOT NULL
             AND DATE(a.release_time) <= CURRENT_DATE
     ) a
     INNER JOIN
     (
         SELECT
             app_date,
             loan_type2,
             biz_id,
             mid
         FROM ind.ba_asset_base_info
         WHERE
             grant_strategy = 'OLD'
             AND if_app = 1
             AND if_recall = 0
             AND loan_type2 IN ('loop', 'normal')
             AND DATE(create_date) <= CURRENT_DATE
     ) b ON CAST(a.mid AS BIGINT) = CAST(b.mid AS BIGINT)
     WHERE
         (YEAR(DATE(b.app_date)) - YEAR(a.release_time)) * 12
         + (MONTH(DATE(b.app_date)) - MONTH(a.release_time)) BETWEEN 0 AND 45
     GROUP BY 1,2,3,4,5
 ) t
 WHERE month >= '2022-01'
 ORDER BY month DESC, month_num, loan_type2
 LIMIT 100000;
"""


# ═══════════════════════════════════════════════════════════════
# MOB 转化率计算
# ═══════════════════════════════════════════════════════════════

def calc_mob_rates(reloan_df: pd.DataFrame, fl_dict: dict,
                   loan_type: str, mob_list: list, debug=False) -> tuple:
    """
    计算每个 MOB 的转化率
    返回: (mob_rates, mob_rates_detail)
      mob_rates:       {mob: [rate_newest, rate_2nd_newest, ...]}
      mob_rates_detail: {mob: [(cohort, rate), ...]}
    """
    sub = reloan_df[reloan_df['loan_type2'] == loan_type].copy()
    mob_rates = {}
    mob_rates_detail = {}

    for mob in sorted(mob_list):
        mob_data = sub[sub['month_num'] == mob].sort_values('month', ascending=False)
        rates = []
        details = []
        for _, row in mob_data.iterrows():
            cohort = str(row['month'])[:7]
            fc = fl_dict.get(cohort, 0)
            if fc > 0:
                rate = round(row['loan_cnt'] / fc, 6)
                rates.append(rate)
                details.append((cohort, rate))
        if rates:
            mob_rates[mob] = rates
            mob_rates_detail[mob] = details

    return mob_rates, mob_rates_detail


def calc_ma_rate(mob_rates: dict, mob: int, window: int = 2) -> float:
    """
    MA平滑计算
    - MOB0: 跳过当月未完成数据，取后 window 期平均
    - MOB1+: 直接取最新1期数据
    - 无数据MOB: 沿用前一个MOB的MA
    """
    rates = mob_rates.get(mob, [])
    if rates:
        if mob == 0:
            recent = rates[1:1 + window]
            if recent:
                return round(sum(recent) / len(recent), 6)
            return round(sum(rates) / len(rates), 6)
        else:
            return round(rates[0], 6)

    # 无数据：沿用前一个MOB的MA
    for step in range(1, mob + 1):
        prev_mob = mob - step
        prev_rates = mob_rates.get(prev_mob, [])
        if prev_rates:
            if prev_mob == 0:
                prev_recent = prev_rates[1:1 + window]
                if prev_recent:
                    return round(sum(prev_recent) / len(prev_recent), 6)
                return round(sum(prev_rates) / len(prev_rates), 6)
            else:
                return round(prev_rates[0], 6)

    return 0.0


def get_adj_factor(loan_type: str, mob: int, cfg: dict) -> float:
    """获取调整系数"""
    lt_cfg = cfg.get("reloan_forecast", {}).get(loan_type, {})
    if mob == 0:
        return lt_cfg.get("adj_current", 1.0)
    elif mob <= 3:
        return lt_cfg.get("adj_short", 1.0)
    elif mob <= 13:
        return lt_cfg.get("adj_long", 1.0)
    else:
        return lt_cfg.get("adj_mob14_plus", 1.0)


def build_first_loan_forecast(months: list, cfg: dict) -> dict:
    """计算首贷预估量"""
    fl_cfg = cfg.get("first_loan", {})
    result = {}
    for month in months:
        y, m = int(month[:4]), int(month[5:7])
        days = calendar.monthrange(y, m)[1]
        installs = fl_cfg["daily_spend"] / fl_cfg["cpi"] * days
        apps = installs * fl_cfg["install_register_rate"]
        fl_cnt = int(apps * fl_cfg["pass_rate"] * fl_cfg["sign_loan_rate"])
        result[month] = fl_cnt
    return result


# ═══════════════════════════════════════════════════════════════
# Excel 输出
# ═══════════════════════════════════════════════════════════════

def create_params_sheet(ws, cfg: dict):
    """参数配置 Sheet"""
    ws.title = "参数配置"
    fl = cfg.get("first_loan", {})
    rf = cfg.get("reloan_forecast", {})
    loop = rf.get("loop", {})
    normal = rf.get("normal", {})

    rows = [
        ("参数名", "值", "说明"),
        ("首贷 | 日均投放消耗($美金)", fl.get("daily_spend", 0), "月预算÷天数"),
        ("首贷 | CPI($美金/安装)", fl.get("cpi", 0), "每获取一次App安装的成本"),
        ("首贷 | 安装注册率", fl.get("install_register_rate", 0), "安装→注册转化率"),
        ("首贷 | 综合通过率", fl.get("pass_rate", 0), "=机审×用信×后置"),
        ("首贷 | 签名放款率", fl.get("sign_loan_rate", 0), "签约→实际放款"),
        ("首贷 | 件均($美金)", fl.get("avg_amount", 0), "首贷平均放款金额"),
        ("", "", ""),
        ("复贷 | MA窗口(月)", rf.get("ma_window", 2), "移动平均取最近N期"),
        ("复贷 | 循环贷MOB0调整系数", loop.get("adj_current", 1), "1.0=不调"),
        ("复贷 | 循环贷MOB1-3调整系数", loop.get("adj_short", 1), "1.0=不调"),
        ("复贷 | 循环贷MOB4-13调整系数", loop.get("adj_long", 1), "1.0=不调"),
        ("复贷 | 循环贷MOB14+调整系数", loop.get("adj_mob14_plus", 1), "1.0=不调"),
        ("复贷 | 非循环贷MOB0调整系数", normal.get("adj_current", 1), "1.0=不调"),
        ("复贷 | 非循环贷MOB1-3调整系数", normal.get("adj_short", 1), "1.0=不调"),
        ("复贷 | 非循环贷MOB4-13调整系数", normal.get("adj_long", 1), "1.0=不调"),
        ("复贷 | 非循环贷MOB14+调整系数", normal.get("adj_mob14_plus", 1), "1.0=不调"),
    ]
    for r, (a, b, c) in enumerate(rows, 1):
        ws.cell(r, 1, a)
        ws.cell(r, 2, b)
        ws.cell(r, 3, c)
    header_style(ws, 1)
    set_col_width(ws, {"A": 45, "B": 18, "C": 55})


def create_reloan_sheet(ws, forecast_results: list, loan_type: str):
    """复贷预估 Sheet"""
    sheet_name = f"复贷预估_{loan_type}"
    ws.title = sheet_name

    headers = ["预估月份", "MOB周期", "对应首贷月",
               "首贷放款量", "MA转化率", "调整系数", "调整后转化率", "预估进件量"]
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    header_style(ws, 1)

    month_rows = {}
    for row, rec in enumerate(forecast_results, 2):
        ws.cell(row, 1, rec["预估月份"])
        ws.cell(row, 2, rec["MOB周期"])
        ws.cell(row, 3, rec["对应首贷月份"])
        ws.cell(row, 4, rec["首贷放款量"])
        ws.cell(row, 5, rec["MA转化率"])
        ws.cell(row, 6, rec["调整系数"])
        ws.cell(row, 7, rec["调整后转化率"])
        ws.cell(row, 8, rec["预估进件量"])

        for c, fmt in [(4, NUM_FMT), (5, PCT_FMT), (6, PCT_FMT),
                       (7, PCT_FMT), (8, NUM_FMT)]:
            ws.cell(row, c).number_format = fmt

        fill = ORG_FILL if loan_type == "loop" else BLU_FILL
        ws.cell(row, 1).fill = fill
        month_rows.setdefault(rec["预估月份"], []).append(row)

    # 小计行
    total_map = {}
    next_row = len(forecast_results) + 2
    for month, rows in month_rows.items():
        r0, r1 = rows[0], rows[-1]
        ws.cell(next_row, 1, month)
        ws.cell(next_row, 2, "小计")
        ws.cell(next_row, 4, f"=SUM(D{r0}:D{r1})")
        ws.cell(next_row, 8, f"=SUM(H{r0}:H{r1})")
        for c in range(1, 9):
            ws.cell(next_row, c).fill = SUB_FILL
            ws.cell(next_row, c).font = BLD_FONT
        ws.cell(next_row, 4).number_format = NUM_FMT
        ws.cell(next_row, 8).number_format = NUM_FMT
        total_map[month] = next_row
        next_row += 1

    set_col_width(ws, {"A": 14, "B": 10, "C": 14, "D": 18,
                       "E": 16, "F": 12, "G": 14, "H": 16})
    return total_map


def create_cohort_sheet(ws, mob_rates_detail: dict, fl_dict: dict,
                        reloan_df: pd.DataFrame, loan_type: str,
                        window: int, ma_matrix: dict):
    """Cohort 矩阵 Sheet"""
    ws.title = f"cohort矩阵_{loan_type}"

    all_cohorts = set()
    for details in mob_rates_detail.values():
        for cohort, _ in details:
            all_cohorts.add(cohort)
    sorted_cohorts = sorted(all_cohorts)
    if not sorted_cohorts:
        ws.cell(1, 1, "无数据")
        return

    ws.cell(1, 1, "MOB")
    for c, cohort in enumerate(sorted_cohorts, 2):
        ws.cell(1, c, cohort)
    ma_col = len(sorted_cohorts) + 2
    ws.cell(1, ma_col, f"MA({window}期)")
    header_style(ws, 1)

    cohort_col = {cohort: c for c, cohort in enumerate(sorted_cohorts, 2)}
    max_mob = max(ma_matrix.keys()) if ma_matrix else 45

    for row_idx, mob in enumerate(range(0, max_mob + 1), 2):
        ws.cell(row_idx, 1, f"MOB{mob}")
        fill = ORG_FILL if loan_type == "loop" else BLU_FILL
        ws.cell(row_idx, 1).fill = fill

        details = mob_rates_detail.get(mob, [])
        detail_dict = {cohort: rate for cohort, rate in details}
        for cohort, col in cohort_col.items():
            rate = detail_dict.get(cohort)
            if rate is not None:
                ws.cell(row_idx, col, rate).number_format = PCT_FMT

        ma_val = ma_matrix.get(mob, 0)
        ws.cell(row_idx, ma_col, ma_val)
        ws.cell(row_idx, ma_col).number_format = PCT_FMT
        ws.cell(row_idx, ma_col).fill = YLW_FILL
        ws.cell(row_idx, ma_col).font = BLD_FONT

    ws.column_dimensions["A"].width = 8
    ws.freeze_panes = "B2"


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def run(cfg: dict, db: PrestoQuery = None, verbose: bool = True) -> dict:
    """
    执行 Step 2: 首贷 + 复贷进件量预估
    """
    if db is None:
        return {"status": "error", "message": "此步骤需要数据库连接"}

    months_cfg = cfg.get("months", {})
    months = [months_cfg.get("current", ""), months_cfg.get("next", "")]
    months = [m for m in months if m]

    if verbose:
        print(f"  预估月份: {', '.join(months)}")

    # 1. 查询数据
    if verbose:
        print("  查询首贷历史...")
    first_loan_df = db.query_df(SQL_FIRST_LOAN, verbose=False)
    if first_loan_df.empty:
        return {"status": "error", "message": "首贷查询返回空数据"}

    first_loan_df["loan_cnt"] = first_loan_df["loan_cnt"].astype(int)
    fl_dict = dict(zip(
        first_loan_df["month"].astype(str).str[:7],
        first_loan_df["loan_cnt"]
    ))
    if verbose:
        print(f"    首贷月份: {len(fl_dict)} 个, {min(fl_dict.keys())} ~ {max(fl_dict.keys())}")

    if verbose:
        print("  查询复贷矩阵...")
    reloan_df = db.query_df(SQL_RELOAN, verbose=False)
    if reloan_df.empty:
        return {"status": "error", "message": "复贷查询返回空数据"}

    reloan_df["month_num"] = reloan_df["month_num"].astype(int)
    reloan_df["loan_cnt"] = reloan_df["loan_cnt"].astype(int)
    reloan_df["month"] = reloan_df["month"].astype(str).str[:7]
    reloan_df["rl_month"] = reloan_df["rl_month"].astype(str).str[:7]
    if verbose:
        print(f"    复贷记录: {len(reloan_df)} 条")

    # 2. 首贷预估
    fl_forecast_dict = build_first_loan_forecast(months, cfg)

    # 3. MOB 转化率计算
    window = cfg.get("reloan_forecast", {}).get("ma_window", 2)
    mob_list = cfg.get("reloan_forecast", {}).get("mob_list", list(range(0, 46)))

    loop_mob_rates, loop_detail = calc_mob_rates(reloan_df, fl_dict, "loop", mob_list)
    normal_mob_rates, normal_detail = calc_mob_rates(reloan_df, fl_dict, "normal", mob_list)

    loop_ma = {mob: calc_ma_rate(loop_mob_rates, mob, window) for mob in mob_list}
    normal_ma = {mob: calc_ma_rate(normal_mob_rates, mob, window) for mob in mob_list}

    if verbose:
        print(f"  [loop] 有数据MOB: {len(loop_mob_rates)}, MOB0 MA={loop_ma.get(0,0):.4f}")
        print(f"  [normal] 有数据MOB: {len(normal_mob_rates)}, MOB0 MA={normal_ma.get(0,0):.4f}")

    # 4. 生成预估
    def build_forecast(ma_matrix: dict, lt: str) -> list:
        results = []
        for target in months:
            tdate = datetime.strptime(target + "-01", "%Y-%m-%d")
            for mob in mob_list:
                ma_val = ma_matrix.get(mob, 0)
                y, m = tdate.year, tdate.month
                cm = datetime(y, m, 1) - relativedelta(months=mob)
                cohort_month = cm.strftime("%Y-%m")
                fl_cnt = fl_dict.get(cohort_month, fl_forecast_dict.get(cohort_month, 0))
                adj = get_adj_factor(lt, mob, cfg)
                results.append({
                    "预估月份": target,
                    "MOB周期": f"MOB{mob}",
                    "对应首贷月份": cohort_month,
                    "首贷放款量": fl_cnt,
                    "MA转化率": round(ma_val, 6),
                    "调整系数": adj,
                    "调整后转化率": round(ma_val * adj, 6),
                    "预估进件量": int(fl_cnt * ma_val * adj) if fl_cnt > 0 and ma_val > 0 else 0,
                })
        return results

    loop_forecast = build_forecast(loop_ma, "loop")
    normal_forecast = build_forecast(normal_ma, "normal")

    # 汇总
    summary = {}
    for m in months:
        lp = sum(r["预估进件量"] for r in loop_forecast if r["预估月份"] == m)
        nl = sum(r["预估进件量"] for r in normal_forecast if r["预估月份"] == m)
        summary[m] = {"loop": lp, "normal": nl, "total": lp + nl}
        if verbose:
            print(f"    {m}  循环贷: {lp:>10,}  非循环贷: {nl:>10,}  合计: {lp+nl:>10,}")

    # 5. 写 Excel
    output_dir = cfg.get("pipeline", {}).get("output_dir", ".")
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"复贷进件量预估_{ts}.xlsx")

    wb = openpyxl.Workbook()

    # 参数配置
    ws_param = wb.active
    create_params_sheet(ws_param, cfg)

    # 首贷预估
    ws_fl = wb.create_sheet("首贷预估")
    headers = ["预估月份", "月安装量", "首贷进件量", "通过率×签名率",
               "首贷放款笔数", "件均($)", "首贷放款金额($)", "历史实际首贷笔数"]
    for c, h in enumerate(headers, 1):
        ws_fl.cell(1, c, h)
    header_style(ws_fl, 1)
    for row, month in enumerate(months, 2):
        ws_fl.cell(row, 1, month)
        fl_cnt = fl_forecast_dict.get(month, 0)
        hist_val = fl_dict.get(month, None)
        fl_cfg = cfg.get("first_loan", {})
        ws_fl.cell(row, 2, fl_cfg["daily_spend"] / fl_cfg["cpi"] * 31)
        ws_fl.cell(row, 3, fl_cnt / (fl_cfg["pass_rate"] * fl_cfg["sign_loan_rate"]))
        ws_fl.cell(row, 4, fl_cfg["pass_rate"] * fl_cfg["sign_loan_rate"])
        ws_fl.cell(row, 5, fl_cnt)
        ws_fl.cell(row, 6, fl_cfg["avg_amount"])
        ws_fl.cell(row, 7, fl_cnt * fl_cfg["avg_amount"])
        ws_fl.cell(row, 8, hist_val if hist_val else "历史无数据")
        ws_fl.cell(row, 4).number_format = PCT_FMT
        ws_fl.cell(row, 2).number_format = NUM_FMT
        ws_fl.cell(row, 3).number_format = NUM_FMT
        ws_fl.cell(row, 5).number_format = NUM_FMT
        ws_fl.cell(row, 6).number_format = USD_FMT_INT
        ws_fl.cell(row, 7).number_format = USD_FMT
        ws_fl.cell(row, 8).number_format = NUM_FMT

    # 复贷预估
    ws_loop = wb.create_sheet()
    loop_total_map = create_reloan_sheet(ws_loop, loop_forecast, "loop")
    ws_norm = wb.create_sheet()
    normal_total_map = create_reloan_sheet(ws_norm, normal_forecast, "normal")

    # Cohort 矩阵
    ws_cl = wb.create_sheet()
    create_cohort_sheet(ws_cl, loop_detail, fl_dict, reloan_df, "loop", window, loop_ma)
    ws_cn = wb.create_sheet()
    create_cohort_sheet(ws_cn, normal_detail, fl_dict, reloan_df, "normal", window, normal_ma)

    # 汇总
    ws_sum = wb.create_sheet("汇总")
    sum_headers = ["预估月份", "首贷放款笔数", "首贷放款金额($)",
                   "循环贷复贷进件", "非循环贷复贷进件", "复贷合计进件", "总进件量"]
    for c, h in enumerate(sum_headers, 1):
        ws_sum.cell(1, c, h)
    header_style(ws_sum, 1)
    for row, month in enumerate(months, 2):
        ws_sum.cell(row, 1, month)
        fl_cnt = fl_forecast_dict.get(month, 0)
        ws_sum.cell(row, 2, fl_cnt)
        ws_sum.cell(row, 3, fl_cnt * cfg["first_loan"]["avg_amount"])
        ws_sum.cell(row, 4, summary[month]["loop"])
        ws_sum.cell(row, 5, summary[month]["normal"])
        ws_sum.cell(row, 6, summary[month]["total"])
        ws_sum.cell(row, 7, fl_cnt + summary[month]["total"])
        for c in [2, 4, 5, 6, 7]:
            ws_sum.cell(row, c).number_format = NUM_FMT
        ws_sum.cell(row, 3).number_format = USD_FMT

    wb.save(output_file)
    if verbose:
        print(f"  输出: {output_file}")

    return {
        "status": "ok",
        "output_file": output_file,
        "summary": summary,
        "fl_forecast": fl_forecast_dict,
    }


if __name__ == "__main__":
    cfg = load_config()
    db = PrestoQuery(cfg.get("database", {}))
    db.login()
    result = run(cfg, db, verbose=True)
    print(f"\n结果: {result.get('status')}")
