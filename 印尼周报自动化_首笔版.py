# -*- coding: utf-8 -*-
"""
印尼周报达成跟进 — 自动化脚本
================================
功能:
  1. 查询印尼 Presto → 宽表指标数据 → 写入 Sheet3"数据源"
  2. Sheet1 与 Sheet3 建立勾稽公式关联
  3. 查询当月每日首贷/复贷放款数据 → 写入日实际区域
  4. 8月预估列: 放款量/金额用近7天均值预估, 其余指标=实际值
  5. 8月目标: 从 ind.ba_kpi_targets_m 表读取
  6. TR/经营利润率: 从【7月】印尼经营计划测算_20260730.xlsx 读取
  7. 印尼不使用息费字段

模板基于墨西哥周报自动化.py,行号/合并/格式完全对齐
"""

import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from indonesia_presto import PrestoQuery
import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta
from collections import defaultdict

# ═══════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════
SRC_FILE = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\印尼周报达成跟进_8月模板.xlsx"
QUANZE_FILE = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\8月预估\【7月】印尼经营计划测算_20260730.xlsx"
CURRENT_MONTH = "2026-08"
CURRENT_MONTH_NUM = 8  # 当前月份数字
PREV_MONTH_NUM = 7     # 上月月份数字
FORECAST_WINDOW = 8    # 预估用近N天均值
EXCHANGE_RATE = 18099  # IDR/USD 汇率（8月当前月份固定值）

# ═══════════════════════════════════════════════════════
# SQL 定义
# ═══════════════════════════════════════════════════════

# 1. 宽表指标（成交金额/成交标数/笔均/期限/日投放/静态CPS/1T0/1T7 × 首贷/复贷/整体 × 月份）
# 注意: 印尼不用加息费字段, 因此宽表不含息费指标
SQL_WIDE_TABLE = """
WITH
base_loan AS (
    SELECT
        DATE_TRUNC('month', release_time) AS month,
        CASE WHEN grant_strategy='NEW' THEN 0 WHEN grant_strategy='OLD' THEN 1 END AS double_loan,
        contract_amount_usd1 AS contract_amount,
        loan_cycle,
        reloan_num
    FROM ind.ba_asset_base_info
    WHERE release_time >= DATE '2026-01-01'
      AND if_issue = 1
      AND release_time < CURRENT_DATE
),
loan_agg AS (
    SELECT month, double_loan,
        SUM(contract_amount) AS sum_contract, COUNT(1) AS cnt_loan,
        SUM(loan_cycle * contract_amount) AS sum_weighted_term,
        SUM(CASE WHEN reloan_num = 1 THEN 1 ELSE 0 END) AS issue_cnt_1,
        SUM(CASE WHEN reloan_num = 1 THEN contract_amount ELSE 0 END) AS contract_amount_usd_1
    FROM base_loan GROUP BY 1,2
    UNION ALL
    SELECT month, NULL AS double_loan,
        SUM(contract_amount), COUNT(1),
        SUM(loan_cycle * contract_amount),
        SUM(CASE WHEN reloan_num = 1 THEN 1 ELSE 0 END),
        SUM(CASE WHEN reloan_num = 1 THEN contract_amount ELSE 0 END)
    FROM base_loan GROUP BY 1
),
loan_metrics AS (
    SELECT '成交金额 (USD)***' AS metric,
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END AS loan_type,
        month, ROUND(sum_contract, 0) AS value FROM loan_agg
    UNION ALL
    SELECT '成交标数',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(cnt_loan, 0) FROM loan_agg
    UNION ALL
    SELECT '笔均 (USD)***',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_contract / NULLIF(cnt_loan, 0), 1) FROM loan_agg
    UNION ALL
    SELECT '期限',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_weighted_term / NULLIF(sum_contract, 0), 1) FROM loan_agg
    UNION ALL
    SELECT '首贷笔数（首笔）',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(issue_cnt_1, 0) FROM loan_agg
    UNION ALL
    SELECT '首贷金额（首笔）',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(contract_amount_usd_1, 0) FROM loan_agg
),
cost_spend AS (
    SELECT DATE_TRUNC('month', ad_date) AS month, SUM(spend_usd_discount) AS spend
    FROM ind.tyn_ads_cost_discount
    WHERE ad_date >= DATE '2026-01-01'
    AND ad_date < CURRENT_DATE
    GROUP BY 1
),
daily_spend AS (
    SELECT
        month,
        spend,
        CASE
            WHEN DATE_FORMAT(DATE(month), '%Y-%m') = DATE_FORMAT(CURRENT_DATE - INTERVAL '1' DAY, '%Y-%m')
            THEN DAY_OF_MONTH(CURRENT_DATE - INTERVAL '1' DAY)
            ELSE DAY_OF_MONTH(DATE_TRUNC('month', DATE(month)) + INTERVAL '1' MONTH - INTERVAL '1' DAY)
        END AS days
    FROM cost_spend
),
first_loan_cnt AS (
    SELECT month, cnt_loan FROM loan_agg WHERE double_loan = 0
),
first_issue_cnt AS (
    SELECT month,
        SUM(CASE WHEN reloan_num = 1 THEN 1 ELSE 0 END) AS issue_cnt_1,
        SUM(CASE WHEN reloan_num = 1 THEN contract_amount ELSE 0 END) AS contract_amount_usd_1
    FROM base_loan
    GROUP BY month
),
cps_rows AS (
    SELECT '静态CPS (USD)***' AS metric, '首贷' AS loan_type, c.month,
        ROUND(c.spend / NULLIF(fl.cnt_loan, 0), 2) AS value
    FROM cost_spend c LEFT JOIN first_loan_cnt fl ON c.month = fl.month
),
first_loan_cps_rows AS (
    SELECT '静态CPS（首笔）' AS metric, '首贷' AS loan_type, c.month,
        ROUND(c.spend / NULLIF(fl.issue_cnt_1, 0), 2) AS value
    FROM cost_spend c 
    LEFT JOIN first_issue_cnt fl ON c.month = fl.month
    WHERE fl.issue_cnt_1 > 0
    
    UNION ALL
    
    SELECT '静态CPD%（首笔）' AS metric, '首贷' AS loan_type, c.month,
        ROUND(c.spend / NULLIF(fl.contract_amount_usd_1, 0), 4) AS value
    FROM cost_spend c 
    LEFT JOIN first_issue_cnt fl ON c.month = fl.month
    WHERE fl.contract_amount_usd_1 > 0
),
daily_spend_rows AS (
    SELECT '日投放金额(USD)***' AS metric, '整体' AS loan_type, month,
        ROUND(spend / NULLIF(days, 0), 2) AS value
    FROM daily_spend
),
overdue_base AS (
    SELECT
        DATE_TRUNC('month', release_time) AS month,
        CASE WHEN grant_strategy='NEW' THEN 0 WHEN grant_strategy='OLD' THEN 1 END AS double_loan,
        SUM(overdue_amount_1_0) AS sum_overdue_t0,
        SUM(overdue_amount_1_7) AS sum_overdue_t7,
        SUM(should_capital_1_0) AS sum_should_t0,
        SUM(should_capital_1_7) AS sum_should_t7
    FROM ind.ba_asset_base_info
    WHERE should_cnt_1_0 = 1
      AND release_time >= DATE '2026-01-01'
      AND release_time < CURRENT_DATE
      AND grant_strategy IN ('NEW', 'OLD')
    GROUP BY 1, 2
    UNION ALL
    SELECT
        DATE_TRUNC('month', release_time) AS month,
        NULL AS double_loan,
        SUM(overdue_amount_1_0),
        SUM(overdue_amount_1_7),
        SUM(should_capital_1_0),
        SUM(should_capital_1_7)
    FROM ind.ba_asset_base_info
    WHERE should_cnt_1_0 = 1
      AND release_time >= DATE '2026-01-01'
      AND release_time < CURRENT_DATE
    GROUP BY 1
),
overdue_rows AS (
    SELECT '1T0' AS metric,
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END AS loan_type,
        month, ROUND(sum_overdue_t0 / NULLIF(sum_should_t0, 0), 4) AS value
    FROM overdue_base
    UNION ALL
    SELECT '1T7',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_overdue_t7 / NULLIF(sum_should_t7, 0), 4)
    FROM overdue_base
),
all_rows AS (
    SELECT * FROM loan_metrics UNION ALL
    SELECT * FROM cps_rows UNION ALL
    SELECT * FROM first_loan_cps_rows UNION ALL
    SELECT * FROM daily_spend_rows UNION ALL
    SELECT * FROM overdue_rows
)
SELECT metric, loan_type,
    MAX(CASE WHEN month = DATE '2026-01-01' THEN value END) AS "1月",
    MAX(CASE WHEN month = DATE '2026-02-01' THEN value END) AS "2月",
    MAX(CASE WHEN month = DATE '2026-03-01' THEN value END) AS "3月",
    MAX(CASE WHEN month = DATE '2026-04-01' THEN value END) AS "4月",
    MAX(CASE WHEN month = DATE '2026-05-01' THEN value END) AS "5月",
    MAX(CASE WHEN month = DATE '2026-06-01' THEN value END) AS "6月",
    MAX(CASE WHEN month = DATE '2026-07-01' THEN value END) AS "7月",
    MAX(CASE WHEN month = DATE '2026-08-01' THEN value END) AS "8月"
FROM all_rows
GROUP BY metric, loan_type
ORDER BY
    CASE metric
        WHEN '成交金额 (USD)***' THEN 1 WHEN '成交标数' THEN 2
        WHEN '首贷笔数（首笔）' THEN 3 WHEN '首贷金额（首笔）' THEN 4
        WHEN '笔均 (USD)***' THEN 5 WHEN '期限' THEN 6
        WHEN '日投放金额(USD)***' THEN 7
        WHEN '静态CPS (USD)***' THEN 8
        WHEN '静态CPS（首笔）' THEN 9
        WHEN '静态CPD%（首笔）' THEN 10
        WHEN '1T0' THEN 11 WHEN '1T7' THEN 12
    END,
    CASE loan_type WHEN '首贷' THEN 1 WHEN '复贷' THEN 2 WHEN '整体' THEN 3 END
"""

# 2. 近8天每日首贷/复贷放款明细（预估基准数据源）
SQL_RECENT_DAILY = f"""
SELECT
    CAST(release_time AS DATE) AS loan_date,
    CASE WHEN grant_strategy='NEW' THEN 0 WHEN grant_strategy='OLD' THEN 1 END AS double_loan,
    COUNT(1) AS loan_cnt,
    SUM(contract_amount_usd1) AS loan_amt
FROM ind.ba_asset_base_info
WHERE release_time >= DATE '{CURRENT_MONTH}-01' - INTERVAL '{FORECAST_WINDOW}' DAY
  AND release_time < DATE '{CURRENT_MONTH}-01' + INTERVAL '1' MONTH
  AND if_issue = 1
GROUP BY 1, 2
ORDER BY 1, 2
"""

# 3. 8月KPI目标（从 ind.ba_kpi_targets_m 读取，WHERE条件会导致查询被kill，改为SELECT *后Python筛选）
SQL_KPI_TARGETS = "SELECT * FROM ind.ba_kpi_targets_m"

# 4. 历史月份汇率（从 dim.dim_exchange_rate_cost 取 IDR）
SQL_EXCHANGE_RATE = """
SELECT
    month_id,
    exchange_rate_to_dollar
FROM dim.dim_exchange_rate_cost
WHERE account_currency = 'IDR'
  AND month_id >= '202601'
ORDER BY month_id
"""

# ═══════════════════════════════════════════════════════
# 辅助: 指标→Sheet1行号映射 (与墨西哥周报完全一致)
# 注意: 印尼不用息费, R15-R17 保留空白
# ═══════════════════════════════════════════════════════

# 第一段（规模&收入 R3-R14）: VLOOKUP + 比率H(G/E) + 比率K((G-J)/J)
# R15-R17 息费位置在印尼版保留为空白（不填数据）
FIRST_SECTION_MAP = {
    ("成交金额 (USD)***", "首贷"): 3,
    ("成交金额 (USD)***", "复贷"): 4,
    ("成交金额 (USD)***", "整体"): 5,
    ("成交标数", "首贷"): 6,
    ("成交标数", "复贷"): 7,
    ("成交标数", "整体"): 8,
    ("笔均 (USD)***", "首贷"): 9,
    ("笔均 (USD)***", "复贷"): 10,
    ("笔均 (USD)***", "整体"): 11,
    ("期限", "首贷"): 12,
    ("期限", "复贷"): 13,
    ("期限", "整体"): 14,
}

# 首笔指标（R24-R27）: 首贷-only, 无目标值, VLOOKUP来自数据源
# R24: 首贷笔数（首笔）  R25: 首贷金额（首笔）  R26: 静态CPS(首笔)  R27: 静态CPD%(首笔)
FIRST_LOAN_VLOOKUP_MAP = {
    ("首贷笔数（首笔）", "首贷"): 24,
    ("首贷金额（首笔）", "首贷"): 25,
}
FIRST_LOAN_CALC_ROWS = [26, 27]  # CPS(首笔)和CPD%(首笔)是计算行

# 第二段 VLOOKUP 指标（1T0/1T7）: VLOOKUP + 绝对差H(G-E) + 绝对差K(G-J) + G=F
SECOND_SECTION_VLOOKUP_MAP = {
    ("1T0", "首贷"): 28,
    ("1T0", "复贷"): 29,
    ("1T0", "整体"): 30,
    ("1T7", "首贷"): 31,
    ("1T7", "复贷"): 32,
    ("1T7", "整体"): 33,
}

# 合并映射（用于G列公式写入: 非金额/标数/笔均的指标 → G=F）
METRIC_ROW_MAP = {**FIRST_SECTION_MAP, **FIRST_LOAN_VLOOKUP_MAP, **SECOND_SECTION_VLOOKUP_MAP}

# 第二段手工指标行（无VLOOKUP, 用户手填E/J, H=G-E, K=G-J）
# R34-R36=本金坏账Vintage%, R37-R39=TR%, R40=经营利润率
MANUAL_ROWS = list(range(34, 40))  # R34-R39 (R40 经营利润率单独处理)

# Sheet1 列号
COL_MAP = {
    "8月目标": 5,      # E
    "8月实际": 6,      # F
    "8月预估": 7,      # G
    "8月预估达成%": 8,  # H
    "7月实际": 10,     # J
    "8月 vs 7月 环比%": 11,  # K
}

# ═══════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════

def read_quanze_data(file_path):
    """从【7月】印尼经营计划测算_20260730.xlsx 读取 TR%、经营利润率%、本金坏账%
    同时读取 7月实际 和 8月目标 数据

    返回 dict:
        {
            'aug': {
                'TR%': {'首贷': x, '复贷': y, '整体': z},
                '经营利润率': {'首贷': x, '复贷': y, '整体': z},
                '本金坏账': {'首贷': x, '复贷': y, '整体': z},
            },
            'jul': {
                'TR%': {'首贷': x, '复贷': y, '整体': z},
                '经营利润率': {'首贷': x, '复贷': y, '整体': z},
                '本金坏账': {'首贷': x, '复贷': y, '整体': z},
            },
        }

    数据源:
        P&L sheet:
            row 15 = 整体-take rate
            row 56 = 首贷-take rate
            row 177 = 复贷-take rate
            row 34 = 整体-经营利润率
            row 193 = 复贷-经营利润率
        总结 sheet (场景1):
            row 12 = 首贷TR%, row 14 = 复贷TR%
            row 13 = 首贷经营利润率%, row 15 = 复贷经营利润率%, row 16 = 整体经营利润率%
        权责格式 sheet:
            row 13 = 首贷本金坏账, row 34 = 复贷本金坏账, row 53 = 整体本金坏账
    """
    import openpyxl
    from datetime import datetime, timedelta

    wb = openpyxl.load_workbook(file_path, data_only=True)

    def to_pos(x):
        if x is None:
            return None
        try:
            v = float(x)
            return abs(v)
        except (TypeError, ValueError):
            return None

    def find_summary_col(ws_summary, target_year, target_month):
        """在总结 sheet row 3 中查找指定月份对应的列号"""
        base_date = datetime(1899, 12, 30)
        for col in range(2, 12):
            val = ws_summary.cell(3, col).value
            if val is not None and isinstance(val, (int, float)):
                try:
                    date_obj = base_date + timedelta(days=int(val))
                    if date_obj.year == target_year and date_obj.month == target_month:
                        return col
                except Exception:
                    continue
        return None

    def read_month_data(ws_pl, ws_summary, ws_format, pl_col, summary_col, format_col):
        """读取指定月份的 TR%、经营利润率、本金坏账数据"""
        # P&L sheet
        tr_total = ws_pl.cell(15, pl_col).value
        tr_fst = ws_pl.cell(56, pl_col).value
        tr_rl = ws_pl.cell(177, pl_col).value
        profit_total_pl = ws_pl.cell(34, pl_col).value
        profit_rl_pl = ws_pl.cell(193, pl_col).value

        # 总结 sheet
        if summary_col is not None:
            tr_fst_summary = ws_summary.cell(12, summary_col).value
            tr_rl_summary = ws_summary.cell(14, summary_col).value
            profit_fst_summary = ws_summary.cell(13, summary_col).value
            profit_rl_summary = ws_summary.cell(15, summary_col).value
            profit_total_summary = ws_summary.cell(16, summary_col).value
        else:
            tr_fst_summary = None
            tr_rl_summary = None
            profit_fst_summary = None
            profit_rl_summary = None
            profit_total_summary = None

        # 优先 P&L, 其次 总结 sheet
        result_tr_fst = tr_fst if tr_fst is not None else tr_fst_summary
        result_tr_rl = tr_rl if tr_rl is not None else tr_rl_summary
        result_tr_total = tr_total if tr_total is not None else None

        result_profit_fst = profit_fst_summary if profit_fst_summary is not None else None
        result_profit_rl = profit_rl_pl if profit_rl_pl is not None else profit_rl_summary
        result_profit_total = profit_total_pl if profit_total_pl is not None else profit_total_summary

        # 权责格式 sheet: 本金坏账
        bad_fst = ws_format.cell(13, format_col).value
        bad_rl = ws_format.cell(34, format_col).value
        bad_total = ws_format.cell(53, format_col).value

        return {
            'TR%': {
                '首贷': result_tr_fst,
                '复贷': result_tr_rl,
                '整体': result_tr_total,
            },
            '经营利润率': {
                '首贷': result_profit_fst,
                '复贷': result_profit_rl,
                '整体': result_profit_total,
            },
            '本金坏账': {
                '首贷': to_pos(bad_fst),
                '复贷': to_pos(bad_rl),
                '整体': to_pos(bad_total),
            },
        }

    ws_pl = wb["P&L"]
    ws_summary = wb["总结"]
    ws_format = wb["权责格式"]

    # P&L 列: col 52=8月(AZ), col 51=7月(AY)
    # 总结 sheet: 动态查找 8月 和 7月
    aug_summary_col = find_summary_col(ws_summary, 2026, 8)
    jul_summary_col = find_summary_col(ws_summary, 2026, 7)

    # 权责格式: col 23=8月(W), col 22=7月(V)
    result_aug = read_month_data(ws_pl, ws_summary, ws_format, 52, aug_summary_col, 23)
    result_jul = read_month_data(ws_pl, ws_summary, ws_format, 51, jul_summary_col, 22)

    return {
        'aug': result_aug,
        'jul': result_jul,
    }


# ═══════════════════════════════════════════════════════
# 主逻辑
# ═══════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("印尼周报达成跟进 — 自动化")
    print(f"  目标月份: {CURRENT_MONTH}  |  预估窗口: 近{FORECAST_WINDOW}天")
    print("=" * 60)

    # ── 1. 连接数据库 ────────────────────────────────
    print("\n[1/6] 连接印尼 Presto...")
    pq = PrestoQuery()
    pq.login_process()
    print("  连接成功")

    # ── 2. 查询宽表数据 ──────────────────────────────
    print("\n[2/6] 查询宽表指标...")
    df_wide = pq.submit_query(SQL_WIDE_TABLE, wait_sec=5)
    if df_wide is None or not isinstance(df_wide, pd.DataFrame):
        print(f"  [!] 宽表查询失败: {df_wide}")
        return
    print(f"  返回 {len(df_wide)} 行 × {len(df_wide.columns)} 列")
    print(f"  列名: {list(df_wide.columns)}")

    # ── 2b. 查询历史汇率 ─────────────────────────────
    print("  查询历史汇率...")
    df_fx = pq.submit_query(SQL_EXCHANGE_RATE, wait_sec=5)
    exchange_rates = {}  # {month_num: rate}
    if isinstance(df_fx, pd.DataFrame) and len(df_fx) > 0:
        for _, row in df_fx.iterrows():
            month_id = str(row["month_id"]).strip()
            month_num = int(month_id[4:6])
            rate = float(row["exchange_rate_to_dollar"])
            if month_num == 8:
                rate = EXCHANGE_RATE
            exchange_rates[month_num] = rate
        rates_str = ", ".join(f"{m}月={exchange_rates[m]:.4f}" for m in sorted(exchange_rates))
        print(f"  历史汇率: {rates_str}")
    else:
        print(f"  [!] 汇率查询失败，全部使用默认 {EXCHANGE_RATE}")
        for m in range(1, 9):
            exchange_rates[m] = EXCHANGE_RATE

    # 确保8月汇率在字典中
    if CURRENT_MONTH_NUM not in exchange_rates:
        exchange_rates[CURRENT_MONTH_NUM] = EXCHANGE_RATE
        print(f"  当前月({CURRENT_MONTH_NUM}月)汇率使用预设值: {EXCHANGE_RATE}")

    # 印尼数据已经是 USD, 不需要汇率转换（保留 exchange_rates 用于脚注）
    # 数值列 string→float
    num_cols = [c for c in df_wide.columns if c not in ("metric", "loan_type")]
    for col in num_cols:
        df_wide[col] = pd.to_numeric(df_wide[col], errors="coerce")

    # ── 3. 查询 KPI 目标 ─────────────────────────────
    print("\n[3/6] 查询8月KPI目标...")
    df_kpi = pq.submit_query(SQL_KPI_TARGETS, wait_sec=5)
    if df_kpi is None or not isinstance(df_kpi, pd.DataFrame) or len(df_kpi) == 0:
        print(f"  [!] KPI目标查询失败, 使用权责Excel读取")
        kpi = {}
        kpi_jul = {}
    else:
        print(f"  返回 {len(df_kpi)} 行, 筛选8月...")
        # 在Python中筛选8月数据（WHERE条件会导致Presto查询被kill）
        df_kpi['month_str'] = df_kpi['month'].astype(str)
        df_aug = df_kpi[df_kpi['month_str'].str.startswith(CURRENT_MONTH)]
        if len(df_aug) == 0:
            print(f"  [!] 未找到{CURRENT_MONTH}的KPI目标")
            kpi = {}
        else:
            kpi_row = df_aug.iloc[0]
            kpi = {
                'fl_contract_amt': float(kpi_row['fl_contract_amt']),
                'fl_issue_cnt': float(kpi_row['fl_issue_cnt']),
                'fl_avg_amt': float(kpi_row['fl_avg_amt']),
                'fl_loan_cycle': float(kpi_row['fl_loan_cycle']),
                'rl_contract_amt': float(kpi_row['rl_contract_amt']),
                'rl_issue_cnt': float(kpi_row['rl_issue_cnt']),
                'rl_avg_amt': float(kpi_row['rl_avg_amt']),
                'rl_loan_cycle': float(kpi_row['rl_loan_cycle']),
                'total_amt': float(kpi_row['total_amt']),
                'cps': float(kpi_row['cps']),
                'fl_bad_rate': abs(float(kpi_row['fl_bad_rate'])),
                'rl_bad_rate': abs(float(kpi_row['rl_bad_rate'])),
                'total_bad_rate': abs(float(kpi_row['total_bad_rate'])),
                'daily_avg_spend': float(kpi_row['daily_avg_spend']),
            }
            for k, v in kpi.items():
                print(f"    {k}: {v}")

        # 读取7月KPI数据（用于J列7月实际坏账）
        df_jul_kpi = df_kpi[df_kpi['month_str'].str.startswith('2026-07')]
        if len(df_jul_kpi) > 0:
            jul_row = df_jul_kpi.iloc[0]
            kpi_jul = {
                'fl_bad_rate': abs(float(jul_row['fl_bad_rate'])),
                'rl_bad_rate': abs(float(jul_row['rl_bad_rate'])),
                'total_bad_rate': abs(float(jul_row['total_bad_rate'])),
            }
            print(f"  [7月KPI] 首贷坏账={kpi_jul['fl_bad_rate']}, 复贷坏账={kpi_jul['rl_bad_rate']}, 整体坏账={kpi_jul['total_bad_rate']}")
        else:
            kpi_jul = {}

    # ── 3b. 读取权责Excel TR/经营利润率(8月目标 + 7月实际) ─────────────
    print("\n  读取权责Excel TR/经营利润率...")
    try:
        quanze_result = read_quanze_data(QUANZE_FILE)
        quanze_aug = quanze_result['aug']  # 8月目标
        quanze_jul = quanze_result['jul']  # 7月实际
        print(f"    [8月目标] TR%: 首贷={quanze_aug['TR%']['首贷']}, 复贷={quanze_aug['TR%']['复贷']}, 整体={quanze_aug['TR%']['整体']}")
        print(f"    [8月目标] 经营利润率: 首贷={quanze_aug['经营利润率']['首贷']}, 复贷={quanze_aug['经营利润率']['复贷']}, 整体={quanze_aug['经营利润率']['整体']}")
        print(f"    [8月目标] 本金坏账: 首贷={quanze_aug['本金坏账']['首贷']}, 复贷={quanze_aug['本金坏账']['复贷']}, 整体={quanze_aug['本金坏账']['整体']}")
        print(f"    [7月实际] TR%: 首贷={quanze_jul['TR%']['首贷']}, 复贷={quanze_jul['TR%']['复贷']}, 整体={quanze_jul['TR%']['整体']}")
        print(f"    [7月实际] 经营利润率: 首贷={quanze_jul['经营利润率']['首贷']}, 复贷={quanze_jul['经营利润率']['复贷']}, 整体={quanze_jul['经营利润率']['整体']}")
        print(f"    [7月实际] 本金坏账: 首贷={quanze_jul['本金坏账']['首贷']}, 复贷={quanze_jul['本金坏账']['复贷']}, 整体={quanze_jul['本金坏账']['整体']}")
    except Exception as e:
        print(f"  [!] 权责Excel读取失败: {e}")
        quanze_aug = {
            'TR%': {'首贷': None, '复贷': None, '整体': None},
            '经营利润率': {'首贷': None, '复贷': None, '整体': None},
            '本金坏账': {'首贷': None, '复贷': None, '整体': None},
        }
        quanze_jul = {
            'TR%': {'首贷': None, '复贷': None, '整体': None},
            '经营利润率': {'首贷': None, '复贷': None, '整体': None},
            '本金坏账': {'首贷': None, '复贷': None, '整体': None},
        }

    # ── 4. 查询预估基准 ─────────────────────────────
    print(f"\n[4/6] 查询预估数据(近{FORECAST_WINDOW}天)...")
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    date_7d_ago = today - timedelta(days=FORECAST_WINDOW)
    date_from = date_7d_ago.strftime('%Y-%m-%d')
    date_to = today.strftime('%Y-%m-%d')
    print(f"  查询预估基准(最近{FORECAST_WINDOW}天: {date_from} ~ {date_to})...")

    df_recent_daily = pq.submit_query(SQL_RECENT_DAILY, wait_sec=5)
    if df_recent_daily is None or not isinstance(df_recent_daily, pd.DataFrame):
        print(f"  [!] 每日明细查询失败, 使用空DataFrame")
        df_recent_daily = pd.DataFrame()

    # 聚合近7天每日首贷/复贷笔数、金额，并判断最后一天数据是否完整
    recent_avg = {0: {"cnt": 0, "amt": 0}, 1: {"cnt": 0, "amt": 0}}
    completeness = {}
    agg = defaultdict(lambda: {"fl_cnt": 0, "fl_amt": 0, "rl_cnt": 0, "rl_amt": 0})

    if isinstance(df_recent_daily, pd.DataFrame) and len(df_recent_daily) > 0:
        df_recent_daily["loan_date_dt"] = pd.to_datetime(df_recent_daily["loan_date"])
        window_mask = (df_recent_daily["loan_date_dt"] >= pd.Timestamp(date_from)) & \
                      (df_recent_daily["loan_date_dt"] < pd.Timestamp(date_to))
        df_window = df_recent_daily.loc[window_mask].copy()

        for _, row in df_window.iterrows():
            date_key = str(row["loan_date"])[:10]
            dl = int(row["double_loan"])
            cnt = int(row["loan_cnt"]) if row["loan_cnt"] else 0
            amt = float(row["loan_amt"]) if row["loan_amt"] else 0
            if dl == 0:
                agg[date_key]["fl_cnt"] = cnt
                agg[date_key]["fl_amt"] = amt
            else:
                agg[date_key]["rl_cnt"] = cnt
                agg[date_key]["rl_amt"] = amt

        sorted_dates = sorted(agg.keys())
        data_last_date = yesterday
        if len(sorted_dates) > 0:
            last_date = sorted_dates[-1]
            last_total = agg[last_date]["fl_cnt"] + agg[last_date]["rl_cnt"]
            prev_total_counts = [agg[d]["fl_cnt"] + agg[d]["rl_cnt"] for d in sorted_dates[:-1]]
            prev_avg = sum(prev_total_counts) / len(prev_total_counts) if prev_total_counts else 0
            if prev_avg > 0 and last_total < 0.6 * prev_avg:
                for d in sorted_dates:
                    completeness[d] = 0 if d == last_date else 1
                print(f"  排除不完整日期: {last_date}，总笔数 {last_total} < 前6天平均 {prev_avg:.0f} 的60%")
            else:
                for d in sorted_dates:
                    completeness[d] = 1

            for d in reversed(sorted_dates):
                if completeness.get(d, 0) == 1:
                    data_last_date = datetime.strptime(d, "%Y-%m-%d")
                    break
            else:
                data_last_date = datetime.strptime(sorted_dates[-1], "%Y-%m-%d")

            complete_dates = [d for d, flag in completeness.items() if flag == 1]
            n = len(complete_dates)
            if n > 0:
                recent_avg[0]["cnt"] = sum(agg[d]["fl_cnt"] for d in complete_dates) / n
                recent_avg[0]["amt"] = sum(agg[d]["fl_amt"] for d in complete_dates) / n
                recent_avg[1]["cnt"] = sum(agg[d]["rl_cnt"] for d in complete_dates) / n
                recent_avg[1]["amt"] = sum(agg[d]["rl_amt"] for d in complete_dates) / n

        print(f"  最近{FORECAST_WINDOW}天日均(已排除不完整): 首贷{recent_avg[0]['cnt']:.0f}笔/${recent_avg[0]['amt']:,.0f}  "
              f"复贷{recent_avg[1]['cnt']:.0f}笔/${recent_avg[1]['amt']:,.0f}")
    else:
        print("  [!] 最近8天数据查询失败，预估将使用0基准")

    # ── 5. 创建/更新 Excel ──────────────────────────
    print("\n[5/6] 创建 Excel 文件...")

    # 如果模板文件不存在, 创建一个新的; 否则加载并清理
    if os.path.exists(SRC_FILE):
        wb = openpyxl.load_workbook(SRC_FILE)
        # 清理 Sheet1 内容
        if "Sheet1" in wb.sheetnames:
            ws1 = wb["Sheet1"]
            # 解除所有合并
            for mr in list(ws1.merged_cells.ranges):
                ws1.unmerge_cells(str(mr))
            # 清空所有内容
            for row in ws1.iter_rows(min_row=1, max_row=ws1.max_row, max_col=ws1.max_column):
                for cell in row:
                    cell.value = None
                    cell.fill = openpyxl.styles.PatternFill(fill_type=None)
                    cell.font = openpyxl.styles.Font()
                    cell.border = openpyxl.styles.Border()
                    cell.number_format = 'General'
        else:
            ws1 = wb.create_sheet("Sheet1", 0)
    else:
        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "Sheet1"

    # ════════════════════════════════════════════════════
    # --- 5a0. 写入8月目标(E列)和7月实际(J列)死数 ---
    # ════════════════════════════════════════════════════
    print("\n  写入8月目标(E)和7月实际(J)...")

    E_JUN = COL_MAP["8月目标"]   # E=5
    J_JUN = COL_MAP["7月实际"]   # J=10

    # ── 第一段: 规模&收入(R3-R14) ──
    # R3/R4 成交金额 (来自 KPI 表)
    ws1.cell(3, E_JUN).value = kpi.get('fl_contract_amt', 0)    # 首贷金额目标
    ws1.cell(4, E_JUN).value = kpi.get('rl_contract_amt', 0)    # 复贷金额目标

    # R6/R7 成交标数 (来自 KPI 表)
    ws1.cell(6, E_JUN).value = kpi.get('fl_issue_cnt', 0)       # 首贷标数目标
    ws1.cell(7, E_JUN).value = kpi.get('rl_issue_cnt', 0)       # 复贷标数目标

    # R9 首贷笔均 = 金额/标数 (公式)
    ws1.cell(9, E_JUN).value = '=E3/E6'
    # R10 复贷笔均 = 公式 (E4/E7)
    ws1.cell(10, E_JUN).value = '=E4/E7'

    # R12/R13 期限 (来自 KPI 表)
    ws1.cell(12, E_JUN).value = kpi.get('fl_loan_cycle', 0)     # 首贷期限目标
    ws1.cell(13, E_JUN).value = kpi.get('rl_loan_cycle', 0)     # 复贷期限目标

    # R15-R17 息费位置留空 (印尼不用加息费)

    # ── 第二段: 成本(R21-R40) ──
    # R21 日投放金额(USD) — E列死数 (来自 KPI daily_avg_spend)
    ws1.cell(21, E_JUN).value = kpi.get('daily_avg_spend', 0)

    # R22 静态CPS — E列死数 (来自 KPI 表)
    ws1.cell(22, E_JUN).value = kpi.get('cps', 0)

    # R23 静态CPD% — E/J列公式
    # E23 = IF(E9=0,"",E22/E9)  已在5b段写入
    # J23 = IF(J9=0,"",J22/J9)  已在5b段写入

    # ── 首笔指标 R24-R27 (无目标值) ──
    # R24: 首贷笔数（首笔）, R25: 首贷金额（首笔）— 无目标值, E列不写
    # R26: 静态CPS(首笔) = 投放金额 / 首贷笔数(首笔) — 无目标值
    # R27: 静态CPD%(首笔) = 投放金额 / 首贷金额(首笔) — 无目标值

    # R34-R36 本金坏账Vintage% — E列死数(来自KPI表), J列死数(来自7月KPI或权责)
    ws1.cell(34, E_JUN).value = kpi.get('fl_bad_rate', 0)
    ws1.cell(35, E_JUN).value = kpi.get('rl_bad_rate', 0)
    ws1.cell(36, E_JUN).value = kpi.get('total_bad_rate', 0)
    # J列7月实际: 直接使用权责Excel中的最新数据
    ws1.cell(34, J_JUN).value = quanze_jul['本金坏账']['首贷'] if quanze_jul['本金坏账']['首贷'] is not None else 0
    ws1.cell(35, J_JUN).value = quanze_jul['本金坏账']['复贷'] if quanze_jul['本金坏账']['复贷'] is not None else 0
    ws1.cell(36, J_JUN).value = quanze_jul['本金坏账']['整体'] if quanze_jul['本金坏账']['整体'] is not None else 0

    # R37-R39 TR% — E列死数(来自权责Excel 8月), J列死数(来自权责Excel 7月)
    ws1.cell(37, E_JUN).value = quanze_aug['TR%']['首贷'] if quanze_aug['TR%']['首贷'] is not None else 0
    ws1.cell(38, E_JUN).value = quanze_aug['TR%']['复贷'] if quanze_aug['TR%']['复贷'] is not None else 0
    ws1.cell(39, E_JUN).value = quanze_aug['TR%']['整体'] if quanze_aug['TR%']['整体'] is not None else 0
    ws1.cell(37, J_JUN).value = quanze_jul['TR%']['首贷'] if quanze_jul['TR%']['首贷'] is not None else 0
    ws1.cell(38, J_JUN).value = quanze_jul['TR%']['复贷'] if quanze_jul['TR%']['复贷'] is not None else 0
    ws1.cell(39, J_JUN).value = quanze_jul['TR%']['整体'] if quanze_jul['TR%']['整体'] is not None else 0

    # R40 经营利润率 — E列死数(来自权责Excel 8月), J列死数(来自权责Excel 7月)
    ws1.cell(40, E_JUN).value = quanze_aug['经营利润率']['整体'] if quanze_aug['经营利润率']['整体'] is not None else 0
    ws1.cell(40, J_JUN).value = quanze_jul['经营利润率']['整体'] if quanze_jul['经营利润率']['整体'] is not None else 0

    # 格式化 R34-R40 的 E/J 列
    for r in [34, 35, 36, 37, 38, 39, 40]:
        ws1.cell(r, E_JUN).number_format = '0.0%'
        ws1.cell(r, J_JUN).number_format = '0.0%'

    print(f"    第一段: R3/R4/R6/R7/R9/R10/R12/R13 E列目标已写入")
    print(f"    第二段: R21/R22/R34-R40 E列目标 + J列7月实际已写入")

    # --- 5a. 创建/更新 Sheet3 数据源 ---
    if "数据源" in wb.sheetnames:
        ws3 = wb["数据源"]
        for row in ws3.iter_rows(min_row=1, max_row=ws3.max_row, max_col=ws3.max_column):
            for cell in row:
                cell.value = None
    else:
        ws3 = wb.create_sheet("数据源")

    # 写入宽表数据作为数据源
    ws3.cell(1, 1).value = "lookup_key"
    ws3.cell(1, 2).value = "metric"
    ws3.cell(1, 3).value = "loan_type"
    month_cols = [c for c in df_wide.columns if c not in ("metric", "loan_type")]
    for ci, m_name in enumerate(month_cols, 4):
        ws3.cell(1, ci).value = m_name + "实际"

    src_data_start = 2
    for ri, (_, row) in enumerate(df_wide.iterrows(), src_data_start):
        key = f"{row['metric']}|{row['loan_type']}"
        ws3.cell(ri, 1).value = key
        ws3.cell(ri, 2).value = row["metric"]
        ws3.cell(ri, 3).value = row["loan_type"]
        for ci, m_name in enumerate(month_cols, 4):
            val = row[m_name]
            if pd.notna(val):
                ws3.cell(ri, ci).value = float(val)

    src_last_col_letter = get_column_letter(3 + len(month_cols))

    print(f"  Sheet3'数据源': {len(df_wide)} 行数据")

    # Sheet3 格式: 笔均和期限保留1位小数
    for ri in range(src_data_start, src_data_start + len(df_wide)):
        metric = ws3.cell(ri, 2).value
        if metric in ("笔均 (USD)***", "期限"):
            for ci in range(4, 4 + len(month_cols)):
                cell = ws3.cell(ri, ci)
                if cell.value is not None:
                    cell.number_format = '0.0'

    # ════════════════════════════════════════════════════
    # --- 5b. Sheet1 勾稽公式 ---
    # ════════════════════════════════════════════════════
    src_last_row = len(df_wide) + 1
    vlkp_range = f"数据源!A1:{src_last_col_letter}{src_last_row}"

    # === 第一段（规模&收入 R3-R14）: VLOOKUP + 比率 ===
    for (metric, loan_type), s1_row in FIRST_SECTION_MAP.items():
        lookup_val = f'{metric}|{loan_type}'

        # 8月实际 = VLOOKUP
        ws1.cell(s1_row, COL_MAP["8月实际"]).value = (
            f'=VLOOKUP("{lookup_val}",{vlkp_range},'
            f'MATCH(F$2,数据源!$1:$1,0),FALSE)'
        )

        # 8月预估达成% = 8月预估 / 8月目标
        tgt = f"{get_column_letter(COL_MAP['8月目标'])}{s1_row}"
        est = f"{get_column_letter(COL_MAP['8月预估'])}{s1_row}"
        ws1.cell(s1_row, COL_MAP["8月预估达成%"]).value = (
            f'=IF({tgt}=0,"",{est}/{tgt})'
        )
        ws1.cell(s1_row, COL_MAP["8月预估达成%"]).number_format = '0.0%'

        # 7月实际 = VLOOKUP
        ws1.cell(s1_row, COL_MAP["7月实际"]).value = (
            f'=VLOOKUP("{lookup_val}",{vlkp_range},'
            f'MATCH(J$2,数据源!$1:$1,0),FALSE)'
        )

        # 环比% = (8月预估 - 7月实际) / 7月实际
        july_comp = f"{get_column_letter(COL_MAP['7月实际'])}{s1_row}"
        aug_est = f"{get_column_letter(COL_MAP['8月预估'])}{s1_row}"
        ws1.cell(s1_row, COL_MAP["8月 vs 7月 环比%"]).value = (
            f'=IF({july_comp}=0,"",({aug_est}-{july_comp})/{july_comp})'
        )
        ws1.cell(s1_row, COL_MAP["8月 vs 7月 环比%"]).number_format = '0.0%'

    print(f"  第一段(规模&收入): {len(FIRST_SECTION_MAP)} 个指标行已关联")

    # === 第二段 VLOOKUP 指标（1T0/1T7）: VLOOKUP + 绝对差 ===
    for (metric, loan_type), s1_row in SECOND_SECTION_VLOOKUP_MAP.items():
        lookup_val = f'{metric}|{loan_type}'

        # 8月实际 = VLOOKUP
        ws1.cell(s1_row, COL_MAP["8月实际"]).value = (
            f'=VLOOKUP("{lookup_val}",{vlkp_range},'
            f'MATCH(F$2,数据源!$1:$1,0),FALSE)'
        )

        # 8月预估 = 8月实际
        ws1.cell(s1_row, COL_MAP["8月预估"]).value = (
            f'={get_column_letter(COL_MAP["8月实际"])}{s1_row}'
        )

        # H: 绝对值差值 = G - E
        tgt = f"{get_column_letter(COL_MAP['8月目标'])}{s1_row}"
        est = f"{get_column_letter(COL_MAP['8月预估'])}{s1_row}"
        ws1.cell(s1_row, COL_MAP["8月预估达成%"]).value = (
            f'=IF({tgt}=0,"",{est}-{tgt})'
        )
        ws1.cell(s1_row, COL_MAP["8月预估达成%"]).number_format = '0.0%'

        # 7月实际 = VLOOKUP
        ws1.cell(s1_row, COL_MAP["7月实际"]).value = (
            f'=VLOOKUP("{lookup_val}",{vlkp_range},'
            f'MATCH(J$2,数据源!$1:$1,0),FALSE)'
        )

        # K: 绝对值变动 = G - J
        july_comp = f"{get_column_letter(COL_MAP['7月实际'])}{s1_row}"
        ws1.cell(s1_row, COL_MAP["8月 vs 7月 环比%"]).value = (
            f'=IF({july_comp}=0,"",({est}-{july_comp}))'
        )
        ws1.cell(s1_row, COL_MAP["8月 vs 7月 环比%"]).number_format = '0.0%'

    print(f"  第二段VLOOKUP(1T0/1T7): {len(SECOND_SECTION_VLOOKUP_MAP)} 个指标行已关联")

    # === 静态CPD % (R23) — 计算公式非VLOOKUP ===
    ws1.cell(23, 5).value = '=IF(E9=0,"",E22/E9)'   # E: 8月目标 = CPS目标/首贷笔均目标
    ws1.cell(23, 6).value = '=F22/F9'    # F: 8月实际 = CPS实际/首贷笔均实际
    ws1.cell(23, 7).value = '=F23'       # G: 8月预估 = F
    ws1.cell(23, 8).value = '=IF(E23="","",G23-E23)'   # H: 绝对差
    ws1.cell(23, 10).value = '=IF(J9=0,"",J22/J9)'  # J: 7月实际 = CPS7月/首贷笔均7月
    ws1.cell(23, 11).value = '=IF(J23="","",G23-J23)'  # K: 绝对变动
    for col in [5, 6, 7, 10]:
        ws1.cell(23, col).number_format = '0.0%'
    for col in [8, 11]:
        ws1.cell(23, col).number_format = '0.0%'
    print(f"  静态CPD%(R23): 计算公式已写入")

    # R21 日投放金额(USD): F/G/H/K = VLOOKUP + 绝对差
    ws1.cell(21, COL_MAP["8月实际"]).value = (
        f'=VLOOKUP("日投放金额(USD)***|整体",{vlkp_range},'
        f'MATCH(F$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(21, COL_MAP["8月预估"]).value = '=F21'  # G=F
    ws1.cell(21, COL_MAP["8月预估达成%"]).value = '=IF(E21=0,"",G21-E21)'
    ws1.cell(21, COL_MAP["8月预估达成%"]).number_format = '#,##0_ '
    ws1.cell(21, COL_MAP["7月实际"]).value = (
        f'=VLOOKUP("日投放金额(USD)***|整体",{vlkp_range},'
        f'MATCH(J$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(21, COL_MAP["8月 vs 7月 环比%"]).value = '=IF(J21=0,"",(G21-J21))'
    ws1.cell(21, COL_MAP["8月 vs 7月 环比%"]).number_format = '#,##0_ '

    # R22 静态CPS: F/G/H/K = VLOOKUP + 绝对差
    ws1.cell(22, COL_MAP["8月实际"]).value = (
        f'=VLOOKUP("静态CPS (USD)***|首贷",{vlkp_range},'
        f'MATCH(F$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(22, COL_MAP["8月预估"]).value = '=F22'  # G=F
    ws1.cell(22, COL_MAP["8月预估达成%"]).value = '=IF(E22=0,"",G22-E22)'
    ws1.cell(22, COL_MAP["8月预估达成%"]).number_format = '#,##0.0_ '
    ws1.cell(22, COL_MAP["7月实际"]).value = (
        f'=VLOOKUP("静态CPS (USD)***|首贷",{vlkp_range},'
        f'MATCH(J$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(22, COL_MAP["8月 vs 7月 环比%"]).value = '=IF(J22=0,"",(G22-J22))'
    ws1.cell(22, COL_MAP["8月 vs 7月 环比%"]).number_format = '#,##0.0_ '

    # === 首笔指标 R24-R27 ===
    # R24: 首贷笔数（首笔）— VLOOKUP (首贷-only)
    for (metric, loan_type), s1_row in FIRST_LOAN_VLOOKUP_MAP.items():
        lookup_val = f'{metric}|{loan_type}'
        # 8月实际 = VLOOKUP
        ws1.cell(s1_row, COL_MAP["8月实际"]).value = (
            f'=VLOOKUP("{lookup_val}",{vlkp_range},'
            f'MATCH(F$2,数据源!$1:$1,0),FALSE)'
        )
        # 8月预估 = 8月实际 (无目标值)
        ws1.cell(s1_row, COL_MAP["8月预估"]).value = (
            f'={get_column_letter(COL_MAP["8月实际"])}{s1_row}'
        )
        # H列无目标值, 留空
        ws1.cell(s1_row, COL_MAP["8月预估达成%"]).value = None
        # 7月实际 = VLOOKUP
        ws1.cell(s1_row, COL_MAP["7月实际"]).value = (
            f'=VLOOKUP("{lookup_val}",{vlkp_range},'
            f'MATCH(J$2,数据源!$1:$1,0),FALSE)'
        )
        # K列: 环比% = (G-J)/J
        july_comp = f"{get_column_letter(COL_MAP['7月实际'])}{s1_row}"
        ws1.cell(s1_row, COL_MAP["8月 vs 7月 环比%"]).value = (
            f'=IF({july_comp}=0,"",(G{s1_row}-J{s1_row})/J{s1_row})'
        )
        ws1.cell(s1_row, COL_MAP["8月 vs 7月 环比%"]).number_format = '0.0%'

    # R26 静态CPS(首笔): VLOOKUP + 绝对差
    ws1.cell(26, COL_MAP["8月实际"]).value = (
        f'=VLOOKUP("静态CPS（首笔）|首贷",{vlkp_range},'
        f'MATCH(F$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(26, COL_MAP["8月预估"]).value = '=F26'  # G=F
    ws1.cell(26, COL_MAP["8月预估达成%"]).value = None  # 无目标值
    ws1.cell(26, COL_MAP["7月实际"]).value = (
        f'=VLOOKUP("静态CPS（首笔）|首贷",{vlkp_range},'
        f'MATCH(J$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(26, COL_MAP["8月 vs 7月 环比%"]).value = '=IF(J26=0,"",(G26-J26))'
    ws1.cell(26, COL_MAP["8月实际"]).number_format = '#,##0.0_ '
    ws1.cell(26, COL_MAP["8月预估"]).number_format = '#,##0.0_ '
    ws1.cell(26, COL_MAP["8月 vs 7月 环比%"]).number_format = '#,##0.0_ '

    # R27 静态CPD%(首笔): VLOOKUP + 环比
    ws1.cell(27, COL_MAP["8月实际"]).value = (
        f'=VLOOKUP("静态CPD%（首笔）|首贷",{vlkp_range},'
        f'MATCH(F$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(27, COL_MAP["8月预估"]).value = '=F27'  # G=F
    ws1.cell(27, COL_MAP["8月预估达成%"]).value = None  # 无目标值
    ws1.cell(27, COL_MAP["7月实际"]).value = (
        f'=VLOOKUP("静态CPD%（首笔）|首贷",{vlkp_range},'
        f'MATCH(J$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(27, COL_MAP["8月 vs 7月 环比%"]).value = '=IF(J27=0,"",(G27-J27)/J27)'
    ws1.cell(27, COL_MAP["8月实际"]).number_format = '0.0%'
    ws1.cell(27, COL_MAP["8月预估"]).number_format = '0.0%'
    ws1.cell(27, COL_MAP["8月 vs 7月 环比%"]).number_format = '0.0%'

    print(f"  首笔指标(R24-R27): VLOOKUP+计算行公式已写入")

    # === 坏账/TR (R34-R39) — 手工指标, 无VLOOKUP, E/J死数 ===
    for row in MANUAL_ROWS:
        # 清空F列(无VLOOKUP)
        ws1.cell(row, COL_MAP["8月实际"]).value = None
        # H = G - E
        ws1.cell(row, COL_MAP["8月预估达成%"]).value = f'=G{row}-E{row}'
        ws1.cell(row, COL_MAP["8月预估达成%"]).number_format = '0.0%'
        # K = G - J
        ws1.cell(row, COL_MAP["8月 vs 7月 环比%"]).value = f'=G{row}-J{row}'
        ws1.cell(row, COL_MAP["8月 vs 7月 环比%"]).number_format = '0.0%'

    # R40 经营利润率 — 单独处理 (F/G有值, 不从MANUAL_ROWS循环清空)
    row = 40
    ws1.cell(row, COL_MAP["8月实际"]).value = quanze_aug['经营利润率']['整体'] if quanze_aug['经营利润率']['整体'] is not None else 0
    ws1.cell(row, COL_MAP["8月预估"]).value = f'={get_column_letter(COL_MAP["8月实际"])}{row}'
    ws1.cell(row, COL_MAP["8月预估达成%"]).value = f'=G{row}-E{row}'
    ws1.cell(row, COL_MAP["8月 vs 7月 环比%"]).value = f'=G{row}-J{row}'
    for col in [COL_MAP["8月实际"], COL_MAP["8月预估"], COL_MAP["8月预估达成%"], COL_MAP["8月 vs 7月 环比%"]]:
        ws1.cell(row, col).number_format = '0.0%'

    print(f"  坏账/TR(R34-R39): H/K绝对差公式已写入")
    print(f"  经营利润率(R40): F/G有值, H/K公式已写入")

    # ════════════════════════════════════════════════════
    # --- 5c. 整体行 = 首贷+复贷 公式联动 ---
    # ════════════════════════════════════════════════════
    for col_idx in [COL_MAP["8月目标"], COL_MAP["8月实际"], COL_MAP["8月预估"],
                     COL_MAP["7月实际"]]:
        cl = get_column_letter(col_idx)
        # R5 整体金额 = R3+R4
        ws1.cell(5, col_idx).value = f"={cl}3+{cl}4"
        ws1.cell(5, col_idx).number_format = '#,##0'
        # R8 整体标数 = R6+R7
        ws1.cell(8, col_idx).value = f"={cl}6+{cl}7"
        ws1.cell(8, col_idx).number_format = '#,##0'
        # R11 整体笔均 = R5/R8
        ws1.cell(11, col_idx).value = f'=IF({cl}8=0,"",{cl}5/{cl}8)'
        ws1.cell(11, col_idx).number_format = '0.0'
        # R14 整体期限 = (金额加权) = (R3*R12+R4*R13)/R5
        ws1.cell(14, col_idx).value = f'=IF({cl}5=0,"",({cl}3*{cl}12+{cl}4*{cl}13)/{cl}5)'
        ws1.cell(14, col_idx).number_format = '0.0'

    # 第一段整体行 H/K: H=比率(G/E), K=环比((G-J)/J) 用预估
    for row in [5, 8, 11, 14]:
        tgt = f"{get_column_letter(COL_MAP['8月目标'])}{row}"
        est = f"{get_column_letter(COL_MAP['8月预估'])}{row}"
        ws1.cell(row, COL_MAP["8月预估达成%"]).value = f'=IF({tgt}=0,"",{est}/{tgt})'
        ws1.cell(row, COL_MAP["8月预估达成%"]).number_format = '0.0%'
        july_comp = f"{get_column_letter(COL_MAP['7月实际'])}{row}"
        ws1.cell(row, COL_MAP["8月 vs 7月 环比%"]).value = f'=IF({july_comp}=0,"",({est}-{july_comp})/{july_comp})'
        ws1.cell(row, COL_MAP["8月 vs 7月 环比%"]).number_format = '0.0%'

    print(f"  整体行公式已写入")

    # --- 5d. 更新8月预估 ---
    def get_wide_value(metric, loan_type, col="8月"):
        row = df_wide[(df_wide["metric"] == metric) & (df_wide["loan_type"] == loan_type)]
        if len(row) > 0:
            val = row[col].values[0]
            return float(val) if pd.notna(val) else 0
        return 0

    # 8月累计实际
    total_fl_cnt = get_wide_value("成交标数", "首贷")
    total_fl_amt = get_wide_value("成交金额 (USD)***", "首贷")
    total_rl_cnt = get_wide_value("成交标数", "复贷")
    total_rl_amt = get_wide_value("成交金额 (USD)***", "复贷")

    print(f"  8月累计实际: 首贷{total_fl_cnt:.0f}笔/${total_fl_amt:,.0f}, "
          f"复贷{total_rl_cnt:.0f}笔/${total_rl_amt:,.0f}")

    # 清空日实际区域 (R40是经营利润率, 不清空)
    daily_start_row = 40
    for row in range(daily_start_row + 1, daily_start_row + 32):  # 从R41开始, 跳过R40经营利润率
        for col in range(1, 8):
            ws1.cell(row, col).value = None

    # --- 5e. 更新8月预估 ---
    days_total = 31
    days_passed = data_last_date.day
    days_remaining = max(0, days_total - days_passed)

    avg_fl_cnt = recent_avg[0]["cnt"]
    avg_fl_amt = recent_avg[0]["amt"]
    avg_rl_cnt = recent_avg[1]["cnt"]
    avg_rl_amt = recent_avg[1]["amt"]

    fcst_fl_cnt = total_fl_cnt + avg_fl_cnt * days_remaining
    fcst_fl_amt = total_fl_amt + avg_fl_amt * days_remaining
    fcst_rl_cnt = total_rl_cnt + avg_rl_cnt * days_remaining
    fcst_rl_amt = total_rl_amt + avg_rl_amt * days_remaining

    print(f"\n  预估基准: 最近{FORECAST_WINDOW}天日均（已排除不完整日期）")
    print(f"  日均: 首贷{avg_fl_cnt:.0f}笔/${avg_fl_amt:,.0f}, "
          f"复贷{avg_rl_cnt:.0f}笔/${avg_rl_amt:,.0f}")
    print(f"  累计{days_passed}天 + 剩余{days_remaining}天 → ")
    print(f"  预估: 首贷{fcst_fl_cnt:,.0f}笔/${fcst_fl_amt:,.0f}, "
          f"复贷{fcst_rl_cnt:,.0f}笔/${fcst_rl_amt:,.0f}")

    # --- 5e. 样式定义 ---
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    FONT_HDR  = Font(name="微软雅黑", size=10, bold=True, color="FFFFFFFF")
    FONT_BOLD = Font(name="微软雅黑", size=10, bold=True, color="FF000000")
    FONT_DATA = Font(name="微软雅黑", size=10, color="FF000000")
    HDR_FILL  = PatternFill("solid", fgColor="FF4472C4")
    THIN = Side(style="thin")
    THICK = Side(style="thick")
    BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
    BORDER_OUTER = Border(left=THICK, right=THICK, top=THICK, bottom=THICK)
    GRAY_FILL = PatternFill("solid", fgColor="FFD9D9D9")
    ALIGN_LEFT   = Alignment(horizontal="left",   vertical="center")
    ALIGN_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ALIGN_RIGHT  = Alignment(horizontal="right",  vertical="center")

    # --- 5e. 辅助列：预估参数（M列=标签，N列=数值，O列=备注）---
    year, month = map(int, CURRENT_MONTH.split('-'))
    ws1.cell(2, 13).value = "预估参数"
    ws1.cell(2, 14).value = "数值"
    ws1.cell(2, 15).value = "备注"
    forecast_params = [
        ("首贷日均金额", '=SUMIFS(预估数据源!C:C,预估数据源!G:G,1)/COUNTIFS(预估数据源!G:G,1)', "完整日期首贷成交金额均值"),
        ("复贷日均金额", '=SUMIFS(预估数据源!E:E,预估数据源!G:G,1)/COUNTIFS(预估数据源!G:G,1)', "完整日期复贷成交金额均值"),
        ("剩余天数", f'=DAY(EOMONTH(DATE({year},{month},1),0))-DAY(MAXIFS(预估数据源!A:A,预估数据源!G:G,1))', "当月总天数 - 数据完整日"),
        ("首贷日均笔数", '=SUMIFS(预估数据源!B:B,预估数据源!G:G,1)/COUNTIFS(预估数据源!G:G,1)', "完整日期首贷成交笔数均值"),
        ("复贷日均笔数", '=SUMIFS(预估数据源!D:D,预估数据源!G:G,1)/COUNTIFS(预估数据源!G:G,1)', "完整日期复贷成交笔数均值"),
    ]
    for i, (label, formula, note) in enumerate(forecast_params, 3):
        ws1.cell(i, 13).value = label
        ws1.cell(i, 14).value = formula
        ws1.cell(i, 15).value = note
    for r in range(2, 8):
        for col_idx in [13, 14, 15]:
            c = ws1.cell(r, col_idx)
            c.font = FONT_DATA
            c.alignment = ALIGN_CENTER if col_idx in (13, 14) else ALIGN_LEFT
            c.border = BORDER
    ws1.cell(2, 13).font = Font(name="微软雅黑", size=10, bold=True, color="FF000000")
    ws1.cell(2, 14).font = Font(name="微软雅黑", size=10, bold=True, color="FF000000")
    ws1.cell(2, 15).font = Font(name="微软雅黑", size=10, bold=True, color="FF000000")
    ws1.column_dimensions['L'].width = 12
    ws1.column_dimensions['M'].width = 16
    ws1.column_dimensions['N'].width = 14
    ws1.column_dimensions['O'].width = 28
    for r in [3, 4, 5, 6, 7]:
        ws1.cell(r, 14).number_format = '#,##0'

    # --- 5f. 更新8月预估（公式形式，引用F列实际 + N列日均参数）---
    act = get_column_letter(COL_MAP["8月实际"])
    ws1.cell(3, COL_MAP["8月预估"]).value = f'={act}3+N3*N5'   # 首贷金额
    ws1.cell(4, COL_MAP["8月预估"]).value = f'={act}4+N4*N5'   # 复贷金额
    ws1.cell(6, COL_MAP["8月预估"]).value = f'={act}6+N6*N5'   # 首贷标数
    ws1.cell(7, COL_MAP["8月预估"]).value = f'={act}7+N7*N5'   # 复贷标数

    # 笔均 = 预估金额 / 预估标数
    ws1.cell(9, COL_MAP["8月预估"]).value = f'=IF(G6=0,"",G3/G6)'   # 首贷笔均
    ws1.cell(10, COL_MAP["8月预估"]).value = f'=IF(G7=0,"",G4/G7)'  # 复贷笔均
    ws1.cell(11, COL_MAP["8月预估"]).value = f'=IF(G8=0,"",G5/G8)'  # 整体笔均

    # 其他指标 → 等于8月实际值 (期限/CPS/1T0/1T7)
    for (metric, loan_type), s1_row in METRIC_ROW_MAP.items():
        if metric in ("成交金额 (USD)***", "成交标数", "笔均 (USD)***"):
            continue
        if s1_row >= 21:
            continue
        ws1.cell(s1_row, COL_MAP["8月预估"]).value = (
            f'={get_column_letter(COL_MAP["8月实际"])}{s1_row}'
        )

    print(f"  8月预估: 放款量/金额=公式(实际+日均×剩余天数), 日均参数写入M/N/O列")

    # ═══════════════════════════════════════════════════════
    # --- 5g. 格式美化 ---
    # ═══════════════════════════════════════════════════════
    print("\n  格式化...")

    # ---- R2/R20 表头文字 ----
    ws1.cell(2, 2).value = "类目1"
    ws1.cell(2, 3).value = "类目2"
    ws1.cell(2, 4).value = "类目3"
    ws1.cell(2, 5).value = "8月目标"
    ws1.cell(2, 6).value = "8月实际"
    ws1.cell(2, 7).value = "8月预估"
    ws1.cell(2, 8).value = "8月预估达成%**"
    ws1.cell(2, 8).number_format = '0.0%'
    ws1.cell(2, 10).value = "7月实际"
    ws1.cell(2, 11).value = "8月 vs 7月\n环比%**"
    ws1.cell(2, 11).number_format = '0.0%'

    ws1.cell(20, 2).value = "类目1"
    ws1.cell(20, 3).value = "类目2"
    ws1.cell(20, 4).value = "类目3"
    ws1.cell(20, 5).value = "8月目标"
    ws1.cell(20, 6).value = "8月实际"
    ws1.cell(20, 7).value = "8月预估"
    ws1.cell(20, 8).value = "8月目标绝对值差值**"
    ws1.cell(20, 8).number_format = '0.0%'
    ws1.cell(20, 10).value = "7月实际"
    ws1.cell(20, 11).value = "8月 vs 7月\n绝对值变动**"
    ws1.cell(20, 11).number_format = '0.0%'

    # ---- C列类目2标签 ----
    ws1.cell(3, 3).value = "成交金额 (USD)***"
    ws1.cell(6, 3).value = "成交标数"
    ws1.cell(9, 3).value = "笔均 (USD)***"
    ws1.cell(12, 3).value = "期限"
    # R15-R17 息费位置留空 (印尼不用)
    ws1.cell(21, 3).value = "日投放金额(USD)***"
    ws1.cell(22, 3).value = "静态CPS (USD)***"
    ws1.cell(23, 3).value = "静态CPD %"
    ws1.cell(24, 3).value = "首贷笔数（首笔）"
    ws1.cell(25, 3).value = "首贷金额（首笔）"
    ws1.cell(26, 3).value = "静态CPS（首笔）"
    ws1.cell(27, 3).value = "静态CPD%（首笔）"
    ws1.cell(28, 3).value = "1T0"
    ws1.cell(31, 3).value = "1T7"
    ws1.cell(34, 3).value = "本金坏账Vintage%"
    ws1.cell(37, 3).value = "TR%"
    ws1.cell(40, 3).value = "经营利润率"

    # ---- D列类目3标签 ----
    for row, label in [(3,"首贷"),(4,"复贷"),(5,"整体"),
                        (6,"首贷"),(7,"复贷"),(8,"整体"),
                        (9,"首贷"),(10,"复贷"),(11,"整体"),
                        (12,"首贷"),(13,"复贷"),(14,"整体")]:
        ws1.cell(row, 4).value = label
    # 第二段D列
    for row, label in [(24,"首贷"),(25,"首贷"),
                        (28,"首贷"),(29,"复贷"),(30,"整体"),
                        (31,"首贷"),(32,"复贷"),(33,"整体"),
                        (34,"首贷"),(35,"复贷"),(36,"整体"),
                        (37,"首贷"),(38,"复贷"),(39,"整体"),
                        (40,"整体")]:
        ws1.cell(row, 4).value = label
    # R21/R22/R23/R26/R27 无D列标签
    for r in [21, 22, 23, 26, 27]:
        ws1.cell(r, 4).value = None

    # ---- 列宽 ----
    col_widths = {
        'A': 12.7, 'B': 10.7, 'C': 24.8, 'D': 12.4,
        'E': 12.6, 'F': 12.4, 'G': 12.8, 'H': 12.8,
        'I': 16.9,
        'J': 12.4, 'K': 12.4,
    }
    for col_letter, width in col_widths.items():
        ws1.column_dimensions[col_letter].width = width

    # ---- 行高 ----
    ws1.row_dimensions[2].height = 32.5

    # ---- 合并单元格 ----
    merge_ranges = [
        'C3:C5', 'C6:C8', 'C9:C11',       # 成交金额 / 成交标数 / 笔均
        'C12:C14',                          # 期限
        'C18:C19',                          # 空白分隔
        'C28:C30', 'C31:C33',              # 1T0 / 1T7
        'C34:C36', 'C37:C39',              # 本金坏账Vintage% / TR%
    ]
    for mr in merge_ranges:
        ws1.merge_cells(mr)

    # ---- B列类目1纵向合并 ----
    ws1.cell(3, 2).value = "规模&收入"
    ws1.cell(21, 2).value = "成本"
    ws1.merge_cells('B3:B14')   # 规模&收入 (不含已隐藏的息费行R15-R17)
    ws1.merge_cells('B21:B40')  # 成本
    for r in [3, 21]:
        c = ws1.cell(r, 2)
        c.font = FONT_DATA
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER

    # ---- R1：清空日期进度 ----
    for c in range(1, 12):
        ws1.cell(1, c).value = None
        ws1.cell(1, c).font = Font(name="微软雅黑", size=10, color="000000")

    # ---- 表头行 R2 格式 ----
    for col in range(1, 12):
        c = ws1.cell(2, col)
        if c.value is not None:
            c.font = FONT_HDR
            c.fill = HDR_FILL
            c.border = BORDER
            c.alignment = ALIGN_CENTER
    ws1.cell(2, 7).border = Border(left=THIN, right=None, top=THIN, bottom=THIN)

    # ---- 数据行 R3-R43 格式 ----
    for row in range(3, 44):
        for col in range(1, 12):
            cell = ws1.cell(row, col)
            if cell.value is None and col > 2:
                continue
            cell.border = Border()
            cell.font = FONT_DATA
            if col in (3, 4):
                cell.alignment = ALIGN_LEFT
            elif col in (5, 6, 7, 8, 10, 11):
                cell.alignment = ALIGN_RIGHT
            else:
                cell.alignment = ALIGN_CENTER

    # ---- 按"类目2"分组画框线 ----
    category_groups = [
        (3, 5), (6, 8), (9, 11), (12, 14),
        (21, 21), (22, 22), (23, 23),
        (24, 24), (25, 25), (26, 26), (27, 27),
        (28, 30), (31, 33),
        (34, 36), (37, 39), (40, 40),
    ]
    col_borders_sec1 = {2:(1,1), 3:(1,1), 4:(1,0), 5:(1,1), 6:(0,1), 7:(1,0), 8:(1,1), 10:(1,1), 11:(1,1)}
    col_borders_sec2 = {2:(1,1), 3:(1,1), 4:(1,1), 5:(1,1), 6:(1,1), 7:(1,1), 8:(1,1), 10:(1,1), 11:(1,1)}
    for g_start, g_end in category_groups:
        is_sec2 = g_start >= 21
        col_borders = col_borders_sec2 if is_sec2 else col_borders_sec1
        is_single = g_start == g_end
        for row in range(g_start, g_end + 1):
            for col, (has_l, has_r) in col_borders.items():
                cell = ws1.cell(row, col)
                top = THIN if row == g_start else None
                bottom = THIN if row == g_end else None
                left = THIN if (has_l or is_single) else None
                right = THIN if (has_r or is_single) else None
                cell.border = Border(top=top, bottom=bottom, left=left, right=right)

    # ---- 表头行 R20 格式 ----
    for col in range(1, 12):
        c = ws1.cell(20, col)
        if c.value is not None:
            c.font = FONT_HDR
            c.fill = HDR_FILL
            c.border = BORDER
            c.alignment = ALIGN_CENTER
    ws1.row_dimensions[20].height = 32.5

    # ---- 数值格式 ----
    for row in range(3, 15):  # 跳过已隐藏的息费行R15-R17
        for col in [5, 6, 7, 10]:
            c = ws1.cell(row, col)
            if c.value is None:
                continue
            if row in (3, 4, 5):
                c.number_format = '#,##0'       # 成交金额
            elif row in (6, 7, 8):
                c.number_format = '#,##0'       # 成交标数
            elif row in (9, 10, 11):
                c.number_format = '0.0'         # 笔均
            elif row in (12, 13, 14):
                c.number_format = '0.0'         # 期限
    # 第二段 R21-R40
    for row in range(21, 41):
        for col in [5, 6, 7, 10]:
            c = ws1.cell(row, col)
            if c.value is None:
                continue
            if row in (21, 24, 25):
                c.number_format = '#,##0'       # 日投放金额 / 首贷笔数 / 首贷金额
            elif row in (22, 26):
                c.number_format = '#,##0.0_ '   # 静态CPS / 静态CPS(首笔)
            elif row in (23, 27):
                c.number_format = '0.0%'        # 静态CPD% / 静态CPD%(首笔)
            else:
                c.number_format = '0.0%'        # 1T0/1T7/坏账/TR/利润率

    # ---- R15-R17 息费行：清除所有内容和颜色，分组隐藏 ----
    NO_FILL = PatternFill(fill_type=None)
    for row in [15, 16, 17]:
        for col_idx in range(1, 12):
            cell = ws1.cell(row, col_idx)
            cell.value = None
            cell.fill = NO_FILL
            cell.font = Font()
            cell.border = Border()
            cell.number_format = 'General'
    # 分组隐藏息费行
    ws1.row_dimensions.group(15, 17, outline_level=1, hidden=True)
    ws1.sheet_properties.outlinePr.summaryBelow = True

    # ---- 1T0/1T7：G列（8月预估）不灰调 ----
    for row in [28, 29, 30, 31, 32, 33]:
        ws1.cell(row, 7).fill = NO_FILL

    # ---- 日实际区域 R41-R70 (R40已改为经营利润率) ----
    for col in range(1, 8):
        c = ws1.cell(41, col)
        if c.value is not None:
            c.font = FONT_HDR
            c.fill = HDR_FILL
            c.border = BORDER
            c.alignment = ALIGN_CENTER
    for row in range(42, 72):
        for col in range(1, 8):
            c = ws1.cell(row, col)
            if c.value is not None:
                c.border = BORDER
                c.font = FONT_DATA
                c.alignment = ALIGN_CENTER
                if col in (2, 4):
                    c.number_format = '#,##0'
                elif col in (3, 5, 6, 7):
                    c.number_format = '#,##0'

    # ---- 无冻结窗格 + 不显示网格线 ----
    ws1.freeze_panes = None
    ws1.sheet_view.showGridLines = False

    # ---- Sheet3 数据源格式 ----
    if "数据源" in wb.sheetnames:
        ws3 = wb["数据源"]
        ws3.column_dimensions['A'].width = 32
        ws3.column_dimensions['B'].width = 20
        ws3.column_dimensions['C'].width = 10
        for col in range(4, 12):
            ws3.column_dimensions[get_column_letter(col)].width = 12
        for col in range(1, 12):
            c = ws3.cell(1, col)
            if c.value is not None:
                c.font = FONT_HDR
                c.fill = HDR_FILL
                c.border = BORDER
                c.alignment = ALIGN_CENTER
        ws3.row_dimensions[1].height = 28
        for row in range(2, ws3.max_row + 1):
            for col in range(1, 12):
                c = ws3.cell(row, col)
                if c.value is not None:
                    c.border = BORDER
                    c.font = FONT_DATA
                    c.alignment = ALIGN_CENTER

    # ---- 预估数据源 sheet ----
    ws_fc = None
    if "预估数据源" in wb.sheetnames:
        ws_fc = wb["预估数据源"]
        for row in ws_fc.iter_rows(min_row=1, max_row=ws_fc.max_row, max_col=ws_fc.max_column):
            for cell in row:
                cell.value = None
    else:
        ws_fc = wb.create_sheet("预估数据源")

    headers_fc = ["放款日期", "首贷成交笔数", "首贷成交金额(USD)",
                  "复贷成交笔数", "复贷成交金额(USD)", "总成交金额(USD)", "是否完整"]
    for ci, h in enumerate(headers_fc, 1):
        ws_fc.cell(1, ci).value = h

    if len(agg) > 0:
        first_data_row = 2
        fc_last_row = len(agg) + 1
        prev_last_row = fc_last_row - 1
        prev_count = fc_last_row - first_data_row
        for ri, (date_key, v) in enumerate(sorted(agg.items()), 2):
            ws_fc.cell(ri, 1).value = datetime.strptime(date_key, "%Y-%m-%d").date()
            ws_fc.cell(ri, 1).number_format = 'yyyy-mm-dd'
            ws_fc.cell(ri, 2).value = v["fl_cnt"]
            ws_fc.cell(ri, 3).value = round(v["fl_amt"], 2)
            ws_fc.cell(ri, 4).value = v["rl_cnt"]
            ws_fc.cell(ri, 5).value = round(v["rl_amt"], 2)
            ws_fc.cell(ri, 6).value = round(v["fl_amt"] + v["rl_amt"], 2)
            if ri < fc_last_row:
                ws_fc.cell(ri, 7).value = 1
            else:
                if prev_count > 0:
                    ws_fc.cell(ri, 7).value = (
                        f'=IF((B{ri}+D{ri})<((SUM(B{first_data_row}:B{prev_last_row})+SUM(D{first_data_row}:D{prev_last_row}))/{prev_count})*0.6, 0, 1)'
                    )
                else:
                    ws_fc.cell(ri, 7).value = 1
        print(f"  预估数据源: {len(agg)} 天已写入")
    else:
        fc_last_row = 1
        print("  [!] 预估数据源无数据")

    # 格式化预估数据源
    ws_fc.column_dimensions['A'].width = 14
    ws_fc.column_dimensions['B'].width = 14
    ws_fc.column_dimensions['C'].width = 20
    ws_fc.column_dimensions['D'].width = 14
    ws_fc.column_dimensions['E'].width = 20
    ws_fc.column_dimensions['F'].width = 20
    ws_fc.column_dimensions['G'].width = 12
    for col in range(1, 8):
        c = ws_fc.cell(1, col)
        c.font = FONT_HDR
        c.fill = HDR_FILL
        c.border = BORDER
        c.alignment = ALIGN_CENTER
    ws_fc.row_dimensions[1].height = 32.5
    for row in range(2, fc_last_row + 1):
        for col in range(1, 8):
            c = ws_fc.cell(row, col)
            if c.value is not None:
                c.border = BORDER
                c.font = FONT_DATA
                c.alignment = ALIGN_CENTER
                if col in (2, 4, 7):
                    c.number_format = '#,##0'
                elif col in (3, 5, 6):
                    c.number_format = '#,##0'

    # ---- 脚注 R41-R43：动态日期 + 汇率(仅近2个月) ----
    yesterday_str = data_last_date.strftime('%Y/%m/%d')
    ws1.cell(41, 2).value = f"* 数据截止于{yesterday_str}"
    ws1.cell(42, 2).value = "** 红底数据表示对应指标差于上月或未达成本月目标"
    prev_month_num = CURRENT_MONTH_NUM - 1
    recent_months = sorted([m for m in exchange_rates if m in (prev_month_num, CURRENT_MONTH_NUM)])
    rates_display = "  ".join(f"{m}月={exchange_rates[m]:.4f}" for m in recent_months)
    ws1.cell(43, 2).value = f"*** 各月汇率(IDR/USD): {rates_display}"
    for r in [41, 42, 43]:
        c = ws1.cell(r, 2)
        c.font = FONT_DATA
        c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)

    for r in [41, 42, 43]:
        c = ws1.cell(r, 2)
        c.border = Border()
        c.font = Font(name="微软雅黑", size=9, color="FF000000")

    # 删Sheet2
    if "Sheet2" in wb.sheetnames:
        del wb["Sheet2"]
        print("  Sheet2 已删除")

    print("  格式已对齐墨西哥周报（微软雅黑10pt/原列宽/无冻结/C列合并）")

    # ---- 字体颜色：死数蓝色，公式黑色 ----
    BLUE_FONT = Font(name="微软雅黑", size=10, color="FF0070C0")
    WHITE_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFFFF")
    for hdr_row in [2, 20]:
        for col_idx in range(1, 12):
            c = ws1.cell(hdr_row, col_idx)
            if c.value is not None:
                c.font = WHITE_FONT
    for col_idx in [5, 6, 9, 10]:  # E/F/I/J
        for row in range(3, 44):
            if row == 20:
                continue
            cell = ws1.cell(row, col_idx)
            if cell.value is None or cell.value == "":
                continue
            if isinstance(cell.value, str) and cell.value.startswith("="):
                continue
            else:
                cell.font = BLUE_FONT

    # ---- E3/E4: 蓝色 ----
    for row in [3, 4]:
        ws1.cell(row, 5).font = BLUE_FONT

    # ---- 类目1 (B列) 和类目2 (C列) 加粗 ----
    for row in [3, 21]:
        c = ws1.cell(row, 2)
        if c.value is not None:
            c.font = Font(name=c.font.name or "微软雅黑",
                          size=c.font.size or 10,
                          bold=True,
                          color=c.font.color.rgb if c.font.color else "FF000000")
    for row in [3, 6, 9, 12, 21, 22, 23, 24, 25, 28, 31, 34, 37, 40]:
        c = ws1.cell(row, 3)
        if c.value is not None:
            c.font = Font(name=c.font.name or "微软雅黑",
                          size=c.font.size or 10,
                          bold=True,
                          color=c.font.color.rgb if c.font.color else "FF000000")
    # ---- D列整体行 + E/F/G/H/J/K 整行加粗 ----
    OVERALL_ROWS = [5, 8, 11, 14, 30, 33, 36, 39, 40]
    for row in OVERALL_ROWS:
        for col in [4, 5, 6, 7, 8, 10, 11]:
            c = ws1.cell(row, col)
            if c.value is not None:
                existing_color = c.font.color.rgb if (c.font.color and c.font.color.rgb) else "FF000000"
                c.font = Font(name=c.font.name or "微软雅黑",
                              size=c.font.size or 10,
                              bold=True,
                              color=existing_color)

    # ---- H/K 列条件格式 ----
    # 统一使用浅红色 (与墨西哥周报一致)
    from openpyxl.formatting.rule import CellIsRule
    RED_FILL = PatternFill(patternType='solid', fgColor='FFFFC7CE', bgColor='FFFFC7CE')
    ws1.conditional_formatting._cf_rules.clear()
    # H列: 8月预估达成% / 绝对值差值
    ws1.conditional_formatting.add('H3:H14', CellIsRule(operator='lessThanOrEqual', formula=['1'], fill=RED_FILL))
    ws1.conditional_formatting.add('H21:H33', CellIsRule(operator='greaterThan', formula=['0'], fill=RED_FILL))
    ws1.conditional_formatting.add('H34:H36', CellIsRule(operator='greaterThan', formula=['0'], fill=RED_FILL))
    ws1.conditional_formatting.add('H37:H40', CellIsRule(operator='lessThan', formula=['0'], fill=RED_FILL))
    # K列: 8月 vs 7月 环比% / 绝对值变动
    ws1.conditional_formatting.add('K3:K14', CellIsRule(operator='lessThan', formula=['0'], fill=RED_FILL))
    ws1.conditional_formatting.add('K21:K23', CellIsRule(operator='greaterThan', formula=['0'], fill=RED_FILL))
    ws1.conditional_formatting.add('K24:K25', CellIsRule(operator='lessThan', formula=['0'], fill=RED_FILL))
    ws1.conditional_formatting.add('K26:K36', CellIsRule(operator='greaterThan', formula=['0'], fill=RED_FILL))
    ws1.conditional_formatting.add('K37:K40', CellIsRule(operator='lessThan', formula=['0'], fill=RED_FILL))

    # ── 6. 保存 ────────────────────────────────────
    print("\n[6/6] 保存文件...")
    out_dir = os.path.dirname(SRC_FILE)
    out_path = os.path.join(out_dir, f"印尼周报达成跟进_8月_更新_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    wb.save(out_path)
    print(f"  已保存: {out_path}")
    print("=" * 60)
    print("完成! 打开文件检查 Sheet1 公式联动 + Sheet3 数据源")


if __name__ == "__main__":
    main()
