# -*- coding: utf-8 -*-
"""
墨西哥周报达成跟进 — 自动化脚本
================================
功能:
  1. 查询墨西哥 Presto → 宽表指标数据 → 写入 Sheet3"数据源"
  2. Sheet1 与 Sheet3 建立勾稽公式关联
  3. 查询当月每日首贷/复贷放款数据 → 写入日实际区域
  4. 9月预估列: 放款量/金额用近7天均值预估, 其余指标=实际值
 
"""

import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta
from collections import defaultdict

# ═══════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════
SRC_FILE = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\墨西哥周报达成跟进_9月模板.xlsx"
QUANZE_FILE = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\9月预估\8月墨西哥经营计划测算_v20260828.xlsx"
CURRENT_MONTH = "2026-09"
CURRENT_MONTH_NUM = 9  # 当前月份数字
PREV_MONTH_NUM = 8     # 上月月份数字
PREV_MONTH = f"2026-{PREV_MONTH_NUM:02d}"  # 上月月份字符串(8月目标查询用)
FORECAST_WINDOW = 8  # 预估用近N天均值
EXCHANGE_RATE = 17.4827  # MXN/USD 汇率（9月当前月份固定值, 待ba_kpi_targets_m更新后可改）

# 权责输出 → 周报行映射: 周报行号 → (权责输出行号, 说明)
# 权责输出列: D=1月 E=2月 F=3月 G=4月 H=5月 I=6月 J=7月 K=8月 ...
# 注意: R15-R17 息费/R21 日投放金额/R30-R36 坏账/TR/利润率 → 用户手填死数
QUANZE_ROW_MAP = {
    # ===== 第一段: 规模&收入 (R3-R17) =====
    3:  (10, "首贷-合同业绩"),       # 成交金额 首贷
    4:  (31, "复贷-合同业绩"),       # 成交金额 复贷
    # R5: 整体金额 = 首贷+复贷 (formula, 由4c段写入)
    6:  (8,  "首贷-笔数"),           # 成交标数 首贷
    7:  (29, "复贷-笔数"),           # 成交标数 复贷
    # R8: 整体标数 = 首贷+复贷 (formula, 由4c段写入)
    9:  (7,  "首贷-件均"),           # 笔均 首贷
    10: (28, "复贷-件均"),           # 笔均 复贷
    # R11: 整体笔均 = 金额/标数 (formula, 由4c段写入)
    12: (11, "首贷平均期限-天"),     # 期限 首贷
    13: (32, "复贷平均期限-天"),     # 期限 复贷
    # R14: 整体期限 = 加权 (formula, 由4c段写入)

    # ===== 第二段: 成本 (R21-R36, 插入日投放金额后整体+1) =====
    # R21: 日投放金额 — 死数
    22: (6,  "投放CPS"),            # 静态CPS (原R21→R22)
    # R23: 静态CPD% = CPS/笔均 (formula)
    # R24-R29 1T0/1T7: 不在权责输出中, VLOOKUP关联

    30: (13, "首贷-本金坏账"),       # 坏账Vintage% 首贷 (权责输出R13=0, 4a0b死数覆盖)
    31: (34, "复贷-本金坏账"),       # 坏账Vintage% 复贷 (4a0b死数覆盖)
    32: (53, "本金坏账-整体"),        # 坏账Vintage% 整体 (4a0b死数覆盖)
    # R33-R35 TR%: 死数 (见4a0b段)
    # R36: 经营利润率 — 死数 (见4a0b段)
    36: (67, "整体-经营利润率"),     # 经营利润率 整体 (权责输出先写, 4a0b死数覆盖)
}

# 用户手填死数行: J列不写VLOOKUP (E列可能是公式/死数)
# R15/R16 息费 E死数但J用VLOOKUP, 故不在此集合
# R21/R22 数据源已有日投放/CPS, J列也改为VLOOKUP
# R33-R35 TR: 改为公式计算(息费-1T7-息费坏账), J列也写公式, 不在死数行
_DEAD_NUMBER_ROWS = {30, 31, 32, 36}

# 权责输出列号映射: 月份 → Excel列(1-based)
# D=4(1月), E=5(2月), ... K=11(8月)
def quanze_col(month_num):
    """月份数字 → 权责输出列号 (D=4 → 1月)"""
    return 3 + month_num  # D=4 for 1月

# ═══════════════════════════════════════════════════════
# SQL 定义
# ═══════════════════════════════════════════════════════

# 1. 宽表指标（8指标 × 首贷/复贷/整体 × 月份）
# 口径切换(2026-09): 成交段统一切到 wxs_application_funnel+is_reloan+if_issue=1
#   - 息费分子 = should_interest(利息) + haircut_amount(砍头息)
#   - 1T0/1T7保持本金口径, 新增1T7息费坏账口径(t7_overdue_interest_4/t7_should_amt_4)
#   - TR = 息费 - 本金坏账 - 息费坏账
SQL_WIDE_TABLE = """
WITH
base_loan AS (
    SELECT
        DATE_TRUNC('month', date(r.release_time)) AS month,
        CASE WHEN r.is_reloan = 'new' THEN 0 ELSE 1 END AS double_loan,
        r.contract_amount,
        r.loan_cycle,
        r.should_interest,        -- 后收利息
        r.haircut_amount          -- 前砍息(砍头息)
    FROM mx.wxs_application_funnel r
    WHERE r.if_issue = 1
      AND r.release_time >= DATE '2026-01-01'
      AND date(r.release_time) < CURRENT_DATE
),
loan_agg AS (
    SELECT month, double_loan,
        SUM(contract_amount) AS sum_contract, COUNT(1) AS cnt_loan,
        SUM(loan_cycle * contract_amount) AS sum_weighted_term,
        SUM(coalesce(should_interest,0) + coalesce(haircut_amount,0)) AS sum_fee  -- 息费=利息+砍头息
    FROM base_loan GROUP BY 1,2
    UNION ALL
    SELECT month, NULL AS double_loan,
        SUM(contract_amount), COUNT(1),
        SUM(loan_cycle * contract_amount),
        SUM(coalesce(should_interest,0) + coalesce(haircut_amount,0))
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
        month, ROUND(sum_contract / cnt_loan, 1) FROM loan_agg
    UNION ALL
    SELECT '期限',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_weighted_term / sum_contract, 1) FROM loan_agg
    UNION ALL
    SELECT '息费',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_fee / sum_contract, 4) FROM loan_agg
),
cost_spend AS (
    SELECT DATE_TRUNC('month', ad_date) AS month, SUM(spend_usd) AS spend
    FROM dwd.dwd_ads_cost
    WHERE ad_date >= DATE '2026-01-01'
    AND ad_date < CURRENT_DATE - INTERVAL '0' DAY
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
cps_rows AS (
    SELECT '静态CPS (USD)***' AS metric, '首贷' AS loan_type, c.month,
        ROUND(c.spend / fl.cnt_loan, 2) AS value
    FROM cost_spend c LEFT JOIN first_loan_cnt fl ON c.month = fl.month
),
daily_spend_rows AS (
    SELECT '日投放金额(USD)***' AS metric, '整体' AS loan_type, month,
        ROUND(spend / days, 2) AS value
    FROM daily_spend
),
overdue_base AS (
    -- 口径: wxs_application_funnel vintage 1T0/1T7 本金逾期率 + 1T7息费坏账
    -- 首贷/复贷
    SELECT DATE_TRUNC('month', date(r.release_time)) AS month,
        CASE WHEN r.is_reloan = 'new' THEN 0 ELSE 1 END AS double_loan,
        SUM(r.t0_overdue_capit_1) AS sum_t0_overdue,
        SUM(r.t0_should_capit_1)  AS sum_t0_should,
        SUM(r.t7_overdue_capit_1) AS sum_t7_overdue,
        SUM(r.t7_should_capit_1)  AS sum_t7_should,
        SUM(coalesce(r.t7_overdue_interest_4,0)) AS sum_t7_overdue_interest,   -- 1T7息费坏账分子
        SUM(coalesce(r.t7_should_amt_4,0))       AS sum_t7_should_amt            -- 1T7息费坏账分母(本息)
    FROM mx.wxs_application_funnel r
    WHERE r.if_issue = 1
      AND r.release_time >= DATE '2026-01-01'
      AND date(r.release_time) < CURRENT_DATE
    GROUP BY 1, 2
    UNION ALL
    -- 整体
    SELECT DATE_TRUNC('month', date(r.release_time)) AS month,
        NULL AS double_loan,
        SUM(r.t0_overdue_capit_1), SUM(r.t0_should_capit_1),
        SUM(r.t7_overdue_capit_1), SUM(r.t7_should_capit_1),
        SUM(coalesce(r.t7_overdue_interest_4,0)),
        SUM(coalesce(r.t7_should_amt_4,0))
    FROM mx.wxs_application_funnel r
    WHERE r.if_issue = 1
      AND r.release_time >= DATE '2026-01-01'
      AND date(r.release_time) < CURRENT_DATE
    GROUP BY 1
),
overdue_rows AS (
    SELECT '1T0' AS metric,
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END AS loan_type,
        month, ROUND(sum_t0_overdue / NULLIF(sum_t0_should, 0), 4) AS value
    FROM overdue_base
    UNION ALL
    SELECT '1T7',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_t7_overdue / NULLIF(sum_t7_should, 0), 4)
    FROM overdue_base
    UNION ALL
    -- 1T7息费坏账口径: t7_overdue_interest_4 / t7_should_amt_4 (用于TR计算)
    SELECT '1T7息费坏账' AS metric,
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_t7_overdue_interest / NULLIF(sum_t7_should_amt, 0), 4)
    FROM overdue_base
),
all_rows AS (
    SELECT * FROM loan_metrics UNION ALL
    SELECT * FROM cps_rows UNION ALL
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
    MAX(CASE WHEN month = DATE '2026-08-01' THEN value END) AS "8月",
    MAX(CASE WHEN month = DATE '2026-09-01' THEN value END) AS "9月"
FROM all_rows
GROUP BY metric, loan_type
ORDER BY
    CASE metric
        WHEN '成交金额 (USD)***' THEN 1 WHEN '成交标数' THEN 2
        WHEN '笔均 (USD)***' THEN 3 WHEN '期限' THEN 4
        WHEN '息费' THEN 5 WHEN '日投放金额(USD)***' THEN 6
        WHEN '静态CPS (USD)***' THEN 7 WHEN '1T0' THEN 8
        WHEN '1T7' THEN 9 WHEN '1T7息费坏账' THEN 10
    END,
    CASE loan_type WHEN '首贷' THEN 1 WHEN '复贷' THEN 2 WHEN '整体' THEN 3 END
"""

# 2. 近8天每日首贷/复贷放款明细（预估基准数据源，供校验）
# 口径切换(2026-09): 切到 funnel+is_reloan+if_issue=1, 与宽表口径一致
SQL_RECENT_DAILY = f"""
SELECT
    CAST(r.release_time AS DATE) AS loan_date,
    CASE WHEN r.is_reloan = 'new' THEN 0 ELSE 1 END AS double_loan,
    COUNT(1) AS loan_cnt,
    SUM(r.contract_amount) AS loan_amt
FROM mx.wxs_application_funnel r
WHERE r.if_issue = 1
  AND r.release_time >= DATE '{CURRENT_MONTH}-01' - INTERVAL '{FORECAST_WINDOW}' DAY
  AND r.release_time < DATE '{CURRENT_MONTH}-01' + INTERVAL '1' MONTH
GROUP BY 1, 2
ORDER BY 1, 2
"""

# 3. 历史月份汇率（从 dim.dim_exchange_rate_cost 取）
SQL_EXCHANGE_RATE = """
SELECT
    month_id,
    exchange_rate_to_dollar
FROM dim.dim_exchange_rate_cost
WHERE account_currency = 'MXN'
  AND month_id >= '202601'
ORDER BY month_id
"""

# 4. 9月KPI目标值（从 mx.ba_kpi_targets_m 读取, 替代手填死数）
SQL_TARGETS = f"""
SELECT
    daily_avg_spend,                -- R21 日投放金额
    cps,                            -- R22 静态CPS
    fl_avg_amt,                     -- R9  首贷笔均
    fl_issue_cnt,                   -- R6  首贷标数
    fl_contract_amt,                -- R3  首贷成交金额
    fl_loan_cycle,                  -- R12 首贷期限
    fl_fee_rate,                    -- R15 首贷息费率(目标)
    fl_bad_rate,                    -- R30 首贷本金坏账(负数)
    rl_avg_amt,                     -- R10 复贷笔均
    rl_issue_cnt,                   -- R7  复贷标数
    rl_contract_amt,                -- R4  复贷成交金额
    rl_loan_cycle,                  -- R13 复贷期限
    rl_fee_rate,                    -- R16 复贷息费率(目标)
    rl_bad_rate,                    -- R31 复贷本金坏账(负数)
    total_fee_rate,                 -- R17 整体息费率(目标)
    total_bad_rate,                 -- R32 整体本金坏账(负数)
    exchange_rate                   -- 汇率
FROM mx.ba_kpi_targets_m
WHERE month = '{CURRENT_MONTH}-01'
  AND ba_type = 'kpi'
LIMIT 1
"""

# 4a. 8月KPI目标值（活动表 ba_kpi_targets_m 同时保留 7/8/9 月, 直接按 month 字符串查）
SQL_TARGETS_AUG = f"""
SELECT
    daily_avg_spend,                -- R21 日投放金额
    cps,                            -- R22 静态CPS
    fl_avg_amt, fl_issue_cnt, fl_contract_amt, fl_loan_cycle,
    fl_fee_rate, fl_bad_rate,
    rl_avg_amt, rl_issue_cnt, rl_contract_amt, rl_loan_cycle,
    rl_fee_rate, rl_bad_rate,
    total_fee_rate, total_bad_rate,
    exchange_rate
FROM mx.ba_kpi_targets_m
WHERE month = '{PREV_MONTH}-01'
  AND ba_type = 'kpi'
LIMIT 1
"""

# ═══════════════════════════════════════════════════════
# 辅助: 指标→Sheet1行号映射
# ═══════════════════════════════════════════════════════

# 第一段（规模&收入 R3-R17）: VLOOKUP + 比率H(G/E) + 比率K((G-J)/J)
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
    ("息费", "首贷"): 15,
    ("息费", "复贷"): 16,
    ("息费", "整体"): 17,
}

# 第二段 VLOOKUP 指标（成本段）: VLOOKUP + 绝对差H(G-E) + 绝对差K(G-J) + G=F
# R22=静态CPS(权责输出), R23=静态CPD(formula), R24-R26=1T0, R27-R29=1T7
SECOND_SECTION_VLOOKUP_MAP = {
    ("1T0", "首贷"): 24,
    ("1T0", "复贷"): 25,
    ("1T0", "整体"): 26,
    ("1T7", "首贷"): 27,
    ("1T7", "复贷"): 28,
    ("1T7", "整体"): 29,
}

# 合并映射（用于G列公式写入: 非金额/标数/笔均的指标 → G=F）
METRIC_ROW_MAP = {**FIRST_SECTION_MAP, **SECOND_SECTION_VLOOKUP_MAP}

# 第二段手工指标行（无VLOOKUP, 用户手填E/J, H=G-E, K=G-J）
# R30-R32=本金坏账Vintage%, R33-R35=TR%, R36=经营利润率
MANUAL_ROWS = list(range(30, 37))  # R30-R36

# Sheet1 列号
COL_MAP = {
    "9月目标": 5,        # E
    "9月实际": 6,        # F
    "9月预估": 7,        # G
    "9月预估达成%": 8,   # H
    "8月目标": 10,       # J
    "8月实际": 11,       # K
    "8月实际达成率": 12, # L
    "9月 vs 8月 环比%": 13,  # M
}

# 预估参数辅助列 (M列=环比, N列=空白分隔, O/P/Q列=预估参数)
FC_LABEL_COL = 15   # O 预估参数标签
FC_VALUE_COL = 16   # P 预估参数数值
FC_NOTE_COL = 17    # Q 预估参数备注

# 息费行 (用户要求留空白, 不使用底表)
_FEE_ROWS = {15, 16, 17}

# ═══════════════════════════════════════════════════════
# 主逻辑
# ═══════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("墨西哥周报达成跟进 — 自动化")
    print(f"  目标月份: {CURRENT_MONTH}  |  预估窗口: 近{FORECAST_WINDOW}天")
    print("=" * 60)

    # ── 1. 连接数据库 ────────────────────────────────
    print("\n[1/5] 连接墨西哥 Presto...")
    pq = PrestoQuery()
    pq.login()
    print("  连接成功")

    # ── 2. 查询宽表数据 ──────────────────────────────
    print("\n[2/5] 查询宽表指标...")
    df_wide = pq.query(SQL_WIDE_TABLE, wait_sec=5)
    if isinstance(df_wide, str):
        print(f"  查询失败: {df_wide[:200]}")
        return
    if not isinstance(df_wide, pd.DataFrame):
        print(f"  ⚠ 查询返回类型异常: {type(df_wide)}, value={str(df_wide)[:200]}")
        return
    print(f"  返回 {len(df_wide)} 行 × {len(df_wide.columns)} 列")
    print(f"  列名: {list(df_wide.columns)}")

    # ── 2a. 查询9月KPI目标值 ─────────────────────
    print("  查询9月KPI目标值(ba_kpi_targets_m)...")
    df_targets = pq.query(SQL_TARGETS, wait_sec=5)
    global EXCHANGE_RATE
    if isinstance(df_targets, pd.DataFrame) and len(df_targets) > 0:
        tgt = df_targets.iloc[0]
        # 用ba_kpi_targets_m的汇率覆盖9月固定值
        if pd.notna(tgt.get("exchange_rate")):
            EXCHANGE_RATE = float(tgt["exchange_rate"])
            print(f"  9月汇率(来自ba_kpi_targets_m): {EXCHANGE_RATE}")
        print(f"  目标: 首贷金额={tgt['fl_contract_amt']}, 复贷金额={tgt['rl_contract_amt']}")
    else:
        print(f"  ⚠ KPI目标查询失败, 使用8月死数兜底")
        tgt = None

    # ── 2a2. 查询8月KPI目标值 ─────────────────────
    print("  查询8月KPI目标值(归档表)...")
    df_targets_aug = pq.query(SQL_TARGETS_AUG, wait_sec=5)
    if isinstance(df_targets_aug, pd.DataFrame) and len(df_targets_aug) > 0:
        tgt_aug = df_targets_aug.iloc[0]
        print(f"  8月目标: 首贷金额={tgt_aug['fl_contract_amt']}, 复贷金额={tgt_aug['rl_contract_amt']}")
    else:
        print(f"  ⚠ 8月KPI目标查询失败, 使用死数兜底")
        tgt_aug = None

    # ── 2b. 查询历史汇率 ─────────────────────────────
    print("  查询历史汇率...")
    df_fx = pq.query(SQL_EXCHANGE_RATE, wait_sec=5)
    exchange_rates = {}  # {month_num: rate}
    if isinstance(df_fx, pd.DataFrame) and len(df_fx) > 0:
        for _, row in df_fx.iterrows():
            month_id = str(row["month_id"]).strip()  # e.g. "202601"
            month_num = int(month_id[4:6])  # 1~12
            rate = float(row["exchange_rate_to_dollar"])
            # 9月强制使用 ba_kpi_targets_m 的汇率
            if month_num == 9:
                rate = EXCHANGE_RATE
            exchange_rates[month_num] = rate
        rates_str = ", ".join(f"{m}月={exchange_rates[m]:.4f}" for m in sorted(exchange_rates))
        print(f"  历史汇率: {rates_str}")
    else:
        print(f"  ⚠ 汇率查询失败，全部使用默认 {EXCHANGE_RATE}")
        for m in range(1, 10):
            exchange_rates[m] = EXCHANGE_RATE

    # 确保9月汇率在字典中（Presto可能还没有9月数据）
    current_month_num = int(CURRENT_MONTH.split('-')[1])
    if current_month_num not in exchange_rates:
        exchange_rates[current_month_num] = EXCHANGE_RATE
        print(f"  当前月({current_month_num}月)汇率使用预设值: {EXCHANGE_RATE}")

    # 数值列 string→float + 成交金额/笔均 MXN→USD（按月使用对应汇率）
    num_cols = [c for c in df_wide.columns if c not in ("metric", "loan_type")]
    for col in num_cols:
        df_wide[col] = pd.to_numeric(df_wide[col], errors="coerce")

    for idx, row in df_wide.iterrows():
        metric = row["metric"]
        if metric in ("成交金额 (USD)***", "笔均 (USD)***"):
            for col in num_cols:
                val = row[col]
                if pd.notna(val) and val != 0:
                    # 从列名提取月份号，使用对应汇率
                    month_num = int(col.replace("月", ""))
                    rate = exchange_rates.get(month_num, EXCHANGE_RATE)
                    if metric == "成交金额 (USD)***":
                        df_wide.at[idx, col] = round(float(val) / rate, 0)
                    else:
                        df_wide.at[idx, col] = round(float(val) / rate, 1)

    # ── 3. 查询预估基准 ─────────────────────────────
    print("\n[3/5] 查询预估数据...")
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    date_7d_ago = today - timedelta(days=FORECAST_WINDOW)
    date_from = date_7d_ago.strftime('%Y-%m-%d')
    date_to = today.strftime('%Y-%m-%d')
    print(f"  查询预估基准(最近{FORECAST_WINDOW}天: {date_from} ~ {date_to})...")

    # 查询近7天每日明细（预估数据源）
    print(f"  查询近{FORECAST_WINDOW}天每日明细...")
    df_recent_daily = pq.query(SQL_RECENT_DAILY, wait_sec=5)
    if isinstance(df_recent_daily, str):
        print(f"  ⚠ 每日明细查询失败: {df_recent_daily[:200]}")
        df_recent_daily = pd.DataFrame()
    else:
        print(f"  近{FORECAST_WINDOW}天每日明细: {len(df_recent_daily)} 行")

    # 聚合近7天每日首贷/复贷笔数、金额，并判断最后一天数据是否完整
    recent_avg = {0: {"cnt": 0, "amt": 0}, 1: {"cnt": 0, "amt": 0}}
    completeness = {}   # date_key -> 1完整 / 0不完整
    agg = defaultdict(lambda: {"fl_cnt": 0, "fl_amt": 0, "rl_cnt": 0, "rl_amt": 0})

    if isinstance(df_recent_daily, pd.DataFrame) and len(df_recent_daily) > 0:
        # 仅取 [today-7天, today) 的日期作为近7天窗口
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
                agg[date_key]["fl_amt"] = amt / exchange_rates.get(9, EXCHANGE_RATE)
            else:
                agg[date_key]["rl_cnt"] = cnt
                agg[date_key]["rl_amt"] = amt / exchange_rates.get(9, EXCHANGE_RATE)

        sorted_dates = sorted(agg.keys())
        data_last_date = yesterday  # 数据实际截止日（默认昨天，有数据时修正为最新完整日期）
        if len(sorted_dates) > 0:
            last_date = sorted_dates[-1]
            last_total = agg[last_date]["fl_cnt"] + agg[last_date]["rl_cnt"]
            prev_total_counts = [agg[d]["fl_cnt"] + agg[d]["rl_cnt"] for d in sorted_dates[:-1]]
            prev_avg = sum(prev_total_counts) / len(prev_total_counts) if prev_total_counts else 0
            if prev_avg > 0 and last_total < 0.6 * prev_avg:
                for d in sorted_dates:
                    completeness[d] = 0 if d == last_date else 1
                print(f"  排除不完整日期: {last_date}，首贷+复贷总笔数 {last_total} < 前6天平均 {prev_avg:.0f} 的60%")
            else:
                for d in sorted_dates:
                    completeness[d] = 1

            # 找到最后一个完整日期作为数据截止日
            for d in reversed(sorted_dates):
                if completeness.get(d, 0) == 1:
                    data_last_date = datetime.strptime(d, "%Y-%m-%d")
                    break
            else:
                data_last_date = datetime.strptime(sorted_dates[-1], "%Y-%m-%d")

            # 仅使用完整日期计算日均
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
        print("  ⚠ 最近8天数据查询失败，预估将使用0基准")

    # ── 4. 加载并更新 Excel ──────────────────────────
    print("\n[4/5] 更新 Excel 文件...")
    wb = openpyxl.load_workbook(SRC_FILE)
    ws1 = wb["Sheet1"]

    # ★ 首先解除 Sheet1 所有合并单元格，避免后续写入 MergedCell 报错
    for mr in list(ws1.merged_cells.ranges):
        ws1.unmerge_cells(str(mr))

    # ════════════════════════════════════════════════════
    # --- 4a0. 9月目标(E列) + 8月目标(J列)从ba_kpi_targets_m读取 ---
    # 模板已含R21日投放金额行, 行号即最终行号, 不再insert_rows
    # ════════════════════════════════════════════════════
    print("\n  写入9月目标(E) + 8月目标(J)从ba_kpi_targets_m...")

    E_COL = COL_MAP["9月目标"]    # E=5
    J_COL = COL_MAP["8月目标"]    # J=10

    # 9月目标兜底死数(查询失败时用8月值)
    _T = {
        'fl_contract_amt': 999185, 'rl_contract_amt': 3245057,
        'fl_issue_cnt': 15255, 'rl_issue_cnt': 38403,
        'fl_avg_amt': 65.5, 'rl_avg_amt': 84.5,
        'fl_loan_cycle': 18, 'rl_loan_cycle': 25,
        'fl_fee_rate': 0.505, 'rl_fee_rate': 0.576250, 'total_fee_rate': 0.559476,
        'fl_bad_rate': -0.375, 'rl_bad_rate': -0.305, 'total_bad_rate': -0.321479,
        'daily_avg_spend': 18000, 'cps': 36.578806,
    }
    if tgt is not None:
        for k in _T:
            v = tgt.get(k)
            if pd.notna(v):
                _T[k] = float(v)

    # 8月目标兜底死数(与9月同源, 查询失败时用死数)
    _TA = dict(_T)
    if tgt_aug is not None:
        for k in _TA:
            v = tgt_aug.get(k)
            if pd.notna(v):
                _TA[k] = float(v)

    # ── 第一段: 规模&收入(R3-R17) ──
    # R3-R4 成交金额
    ws1.cell(3, E_COL).value = _T['fl_contract_amt']      # 9月首贷金额
    ws1.cell(4, E_COL).value = _T['rl_contract_amt']      # 9月复贷金额
    ws1.cell(3, J_COL).value = _TA['fl_contract_amt']     # 8月首贷金额
    ws1.cell(4, J_COL).value = _TA['rl_contract_amt']     # 8月复贷金额

    # R6-R7 成交标数
    ws1.cell(6, E_COL).value = _T['fl_issue_cnt']         # 9月首贷标数
    ws1.cell(7, E_COL).value = _T['rl_issue_cnt']         # 9月复贷标数
    ws1.cell(6, J_COL).value = _TA['fl_issue_cnt']        # 8月首贷标数
    ws1.cell(7, J_COL).value = _TA['rl_issue_cnt']        # 8月复贷标数

    # R9 首贷笔均 = 金额/标数 (公式)
    ws1.cell(9, E_COL).value = '=E3/E6'
    ws1.cell(9, J_COL).value = '=J3/J6'

    # R10 复贷笔均 = 公式 (E4/E7)
    ws1.cell(10, E_COL).value = '=E4/E7'
    ws1.cell(10, J_COL).value = '=J4/J7'

    # R12-R13 期限
    ws1.cell(12, E_COL).value = _T['fl_loan_cycle']       # 首贷期限
    ws1.cell(13, E_COL).value = _T['rl_loan_cycle']       # 复贷期限
    ws1.cell(12, J_COL).value = _TA['fl_loan_cycle']
    ws1.cell(13, J_COL).value = _TA['rl_loan_cycle']

    # ── 第二段: 成本(R21-R36) ──
    # R21 日投放金额(USD)
    ws1.cell(21, E_COL).value = _T['daily_avg_spend']
    ws1.cell(21, J_COL).value = _TA['daily_avg_spend']

    # R22 静态CPS
    ws1.cell(22, E_COL).value = _T['cps']
    ws1.cell(22, J_COL).value = _TA['cps']

    # R23 静态CPD% = CPS/笔均 (公式, 在4b段写入)

    # R30-R32 本金坏账Vintage% — 从tgt读(负数取绝对值)
    ws1.cell(30, E_COL).value = abs(_T['fl_bad_rate'])     # 9月首贷本金坏账
    ws1.cell(31, E_COL).value = abs(_T['rl_bad_rate'])     # 9月复贷本金坏账
    ws1.cell(32, E_COL).value = abs(_T['total_bad_rate'])  # 9月整体本金坏账
    ws1.cell(30, J_COL).value = abs(_TA['fl_bad_rate'])    # 8月首贷本金坏账
    ws1.cell(31, J_COL).value = abs(_TA['rl_bad_rate'])    # 8月复贷本金坏账
    ws1.cell(32, J_COL).value = abs(_TA['total_bad_rate']) # 8月整体本金坏账

    # R33-R35 TR% — 9月目标死数(用户指定); 8月目标留空白(表内无对应字段)
    ws1.cell(33, E_COL).value = 0.156       # 首贷TR目标
    ws1.cell(34, E_COL).value = 0.324       # 复贷TR目标
    ws1.cell(35, E_COL).value = 0.251425    # 整体TR目标
    # R36 经营利润率 — 9月死数; 8月目标留空白
    ws1.cell(36, E_COL).value = 0.052724

    # 1T0/1T7(R24-R29)/TR%(R33-R35)/经营利润率(R36): 8月目标留空白 (用户要求)
    for r in [24, 25, 26, 27, 28, 29, 33, 34, 35, 36]:
        ws1.cell(r, J_COL).value = None

    # 格式化死数行
    for r in [30, 31, 32, 33, 34, 35, 36]:
        ws1.cell(r, E_COL).number_format = '0.0%'
        ws1.cell(r, J_COL).number_format = '0.0%'
    for r in [3, 4, 6, 7, 21, 22]:
        ws1.cell(r, E_COL).number_format = '#,##0'
        ws1.cell(r, J_COL).number_format = '#,##0'
    for r in [9, 10, 12, 13]:
        ws1.cell(r, E_COL).number_format = '0.0'
        ws1.cell(r, J_COL).number_format = '0.0'

    print(f"    第一段: R3/R4/R6/R7/R9/R10/R12/R13 E/J 目标写入")
    print(f"    成本: R21/R22/R30-R32 E/J 目标写入, R33-R36仅9月目标")
    print(f"    息费R15-R17: 留空白(用户要求, 不用底表)")

    print(f"  9月/8月目标列 写入完成")

    # --- 4a. 创建/更新 Sheet3 数据源 ---
    if "数据源" in wb.sheetnames:
        ws3 = wb["数据源"]
        # 清空旧数据
        for row in ws3.iter_rows(min_row=1, max_row=ws3.max_row, max_col=ws3.max_column):
            for cell in row:
                cell.value = None
    else:
        ws3 = wb.create_sheet("数据源")

    # 写入宽表数据作为数据源（加辅助列：metric|loan_type 用于VLOOKUP）
    # Sheet3列结构: A=lookup_key, B=metric, C=loan_type, D=1月, E=2月, ... K=8月
    ws3.cell(1, 1).value = "lookup_key"
    ws3.cell(1, 2).value = "metric"
    ws3.cell(1, 3).value = "loan_type"
    month_cols = [c for c in df_wide.columns if c not in ("metric", "loan_type")]
    for ci, m_name in enumerate(month_cols, 4):
        ws3.cell(1, ci).value = m_name + "实际"  # "1月" → "1月实际"

    src_data_start = 2
    for ri, (_, row) in enumerate(df_wide.iterrows(), src_data_start):
        key = f"{row['metric']}|{row['loan_type']}"
        ws3.cell(ri, 1).value = key
        ws3.cell(ri, 2).value = row["metric"]
        ws3.cell(ri, 3).value = row["loan_type"]
        # 月份数据从第4列开始
        for ci, m_name in enumerate(month_cols, 4):
            val = row[m_name]
            if pd.notna(val):
                ws3.cell(ri, ci).value = val

    src_last_col_letter = get_column_letter(3 + len(month_cols))  # 数据源最后一列字母
    august_col_idx = 3 + month_cols.index("8月") + 1  # 8月(对比月)在数据源中的列号
    september_col_idx = 3 + month_cols.index("9月") + 1  # 9月(当前月)在数据源中的列号

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
    # --- 4b. Sheet1 勾稽公式 ---
    # ════════════════════════════════════════════════════
    src_last_row = len(df_wide) + 1  # 数据源最后一行
    vlkp_range = f"数据源!A1:{src_last_col_letter}{src_last_row}"

    # === 第一段（规模&收入 R3-R17）: VLOOKUP + 比率 ===
    # F = 9月实际(VLOOKUP)
    # H = IF(E=0,"",G/E)  — 9月预估达成%
    # K = 8月实际(VLOOKUP)
    # L = IF(J=0,"",K/J)  — 8月实际达成率
    # M = IF(K=0,"",(G-K)/K)  — 9月vs8月环比% (用预估值G)
    for (metric, loan_type), s1_row in FIRST_SECTION_MAP.items():
        # 息费 R15-R17 整体留空白 (用户要求不使用底表)
        if s1_row in _FEE_ROWS:
            continue
        lookup_val = f'{metric}|{loan_type}'

        # 9月实际 = VLOOKUP
        ws1.cell(s1_row, COL_MAP["9月实际"]).value = (
            f'=VLOOKUP("{lookup_val}",{vlkp_range},'
            f'MATCH(F$2,数据源!$1:$1,0),FALSE)'
        )

        # 9月预估达成% = 9月预估 / 9月目标
        tgt = f"{get_column_letter(COL_MAP['9月目标'])}{s1_row}"
        est = f"{get_column_letter(COL_MAP['9月预估'])}{s1_row}"
        ws1.cell(s1_row, COL_MAP["9月预估达成%"]).value = (
            f'=IF({tgt}=0,"",{est}/{tgt})'
        )
        ws1.cell(s1_row, COL_MAP["9月预估达成%"]).number_format = '0.0%'

        # 8月实际 = VLOOKUP
        ws1.cell(s1_row, COL_MAP["8月实际"]).value = (
            f'=VLOOKUP("{lookup_val}",{vlkp_range},'
            f'MATCH(K$2,数据源!$1:$1,0),FALSE)'
        )

        # 8月实际达成率 = 8月实际 / 8月目标
        aug_act = f"{get_column_letter(COL_MAP['8月实际'])}{s1_row}"
        aug_tgt = f"{get_column_letter(COL_MAP['8月目标'])}{s1_row}"
        ws1.cell(s1_row, COL_MAP["8月实际达成率"]).value = (
            f'=IF(OR({aug_tgt}=0,{aug_tgt}=""),"",{aug_act}/{aug_tgt})'
        )
        ws1.cell(s1_row, COL_MAP["8月实际达成率"]).number_format = '0.0%'

        # 9月vs8月环比% = (9月预估 - 8月实际) / 8月实际
        ws1.cell(s1_row, COL_MAP["9月 vs 8月 环比%"]).value = (
            f'=IF({aug_act}=0,"",({est}-{aug_act})/{aug_act})'
        )
        ws1.cell(s1_row, COL_MAP["9月 vs 8月 环比%"]).number_format = '0.0%'

    print(f"  第一段(规模&收入): {len(FIRST_SECTION_MAP)} 个指标行已关联")

    # === 第二段 VLOOKUP 指标（1T0/1T7）: VLOOKUP + 绝对差 ===
    # F = 9月实际(VLOOKUP), G = F (预估=实际)
    # H = IF(E=0,"",G-E)  — 9月目标绝对值差值
    # K = 8月实际(VLOOKUP)
    # L = IF(J=0,"",K/J)  — 8月实际达成率
    # M = IF(K=0,"",G-K)  — 9月vs8月绝对值变动
    for (metric, loan_type), s1_row in SECOND_SECTION_VLOOKUP_MAP.items():
        lookup_val = f'{metric}|{loan_type}'

        # 9月实际 = VLOOKUP
        ws1.cell(s1_row, COL_MAP["9月实际"]).value = (
            f'=VLOOKUP("{lookup_val}",{vlkp_range},'
            f'MATCH(F$2,数据源!$1:$1,0),FALSE)'
        )

        # 9月预估 = 9月实际
        ws1.cell(s1_row, COL_MAP["9月预估"]).value = (
            f'={get_column_letter(COL_MAP["9月实际"])}{s1_row}'
        )

        # H: 绝对值差值 = G - E
        tgt = f"{get_column_letter(COL_MAP['9月目标'])}{s1_row}"
        est = f"{get_column_letter(COL_MAP['9月预估'])}{s1_row}"
        ws1.cell(s1_row, COL_MAP["9月预估达成%"]).value = (
            f'=IF({tgt}=0,"",{est}-{tgt})'
        )
        ws1.cell(s1_row, COL_MAP["9月预估达成%"]).number_format = '0.0%'

        # 8月实际 = VLOOKUP
        ws1.cell(s1_row, COL_MAP["8月实际"]).value = (
            f'=VLOOKUP("{lookup_val}",{vlkp_range},'
            f'MATCH(K$2,数据源!$1:$1,0),FALSE)'
        )

        # 8月实际达成率 = 8月实际 / 8月目标 (1T0/1T7目标留空白 → L空)
        aug_act = f"{get_column_letter(COL_MAP['8月实际'])}{s1_row}"
        aug_tgt = f"{get_column_letter(COL_MAP['8月目标'])}{s1_row}"
        ws1.cell(s1_row, COL_MAP["8月实际达成率"]).value = (
            f'=IF(OR({aug_tgt}=0,{aug_tgt}=""),"",{aug_act}/{aug_tgt})'
        )
        ws1.cell(s1_row, COL_MAP["8月实际达成率"]).number_format = '0.0%'

        # M: 绝对值变动 = G - K
        ws1.cell(s1_row, COL_MAP["9月 vs 8月 环比%"]).value = (
            f'=IF({aug_act}=0,"",({est}-{aug_act}))'
        )
        ws1.cell(s1_row, COL_MAP["9月 vs 8月 环比%"]).number_format = '0.0%'

    print(f"  第二段VLOOKUP(1T0/1T7): {len(SECOND_SECTION_VLOOKUP_MAP)} 个指标行已关联")

    # === 静态CPD % (R23) — 计算公式非VLOOKUP ===
    # E23 = E22/E9 (9月CPS目标/9月首贷笔均目标)
    # J23 = J22/J9 (8月CPS目标/8月首贷笔均目标)
    # F23 = F22/F9 (CPS实际/首贷笔均实际)
    # G23 = F23 (预估=实际)
    # H23 = G23-E23 (绝对差)
    # K23 = VLOOKUP(8月实际), L23 = K/J, M23 = G-K
    ws1.cell(23, COL_MAP["9月目标"]).value = '=IF(E9=0,"",E22/E9)'
    ws1.cell(23, COL_MAP["8月目标"]).value = '=IF(J9=0,"",J22/J9)'
    ws1.cell(23, COL_MAP["9月实际"]).value = '=F22/F9'
    ws1.cell(23, COL_MAP["9月预估"]).value = '=F23'
    ws1.cell(23, COL_MAP["9月预估达成%"]).value = '=IF(E23="","",G23-E23)'
    ws1.cell(23, COL_MAP["8月实际"]).value = (
        f'=VLOOKUP("静态CPD %|首贷",{vlkp_range},'
        f'MATCH(K$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(23, COL_MAP["8月实际达成率"]).value = '=IF(OR(J23=0,J23=""),"",K23/J23)'
    ws1.cell(23, COL_MAP["9月 vs 8月 环比%"]).value = '=IF(K23=0,"",(G23-K23))'
    for col in [COL_MAP["9月目标"], COL_MAP["8月目标"], COL_MAP["9月实际"], COL_MAP["9月预估"],
                COL_MAP["8月实际"]]:
        ws1.cell(23, col).number_format = '0.0%'
    for col in [COL_MAP["9月预估达成%"], COL_MAP["8月实际达成率"], COL_MAP["9月 vs 8月 环比%"]]:
        ws1.cell(23, col).number_format = '0.0%'
    print(f"  静态CPD%(R23): 计算公式已写入")

    # R21 日投放金额(USD): F/G/H/K/L/M = VLOOKUP + 绝对差
    ws1.cell(21, COL_MAP["9月实际"]).value = (
        f'=VLOOKUP("日投放金额(USD)***|整体",{vlkp_range},'
        f'MATCH(F$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(21, COL_MAP["9月预估"]).value = '=F21'  # G=F
    ws1.cell(21, COL_MAP["9月预估达成%"]).value = '=IF(E21=0,"",G21-E21)'
    ws1.cell(21, COL_MAP["9月预估达成%"]).number_format = '#,##0_ '
    ws1.cell(21, COL_MAP["8月实际"]).value = (
        f'=VLOOKUP("日投放金额(USD)***|整体",{vlkp_range},'
        f'MATCH(K$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(21, COL_MAP["8月实际达成率"]).value = '=IF(OR(J21=0,J21=""),"",K21/J21)'
    ws1.cell(21, COL_MAP["8月实际达成率"]).number_format = '#,##0.0_ '
    ws1.cell(21, COL_MAP["9月 vs 8月 环比%"]).value = '=IF(K21=0,"",(G21-K21))'
    ws1.cell(21, COL_MAP["9月 vs 8月 环比%"]).number_format = '#,##0_ '

    # R22 静态CPS: H/K使用数值格式(美元), 不是百分比
    ws1.cell(22, COL_MAP["9月实际"]).value = (
        f'=VLOOKUP("静态CPS (USD)***|首贷",{vlkp_range},'
        f'MATCH(F$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(22, COL_MAP["9月预估"]).value = '=F22'  # G=F
    ws1.cell(22, COL_MAP["9月预估达成%"]).value = '=IF(E22=0,"",G22-E22)'
    ws1.cell(22, COL_MAP["9月预估达成%"]).number_format = '#,##0.0_ '
    ws1.cell(22, COL_MAP["8月实际"]).value = (
        f'=VLOOKUP("静态CPS (USD)***|首贷",{vlkp_range},'
        f'MATCH(K$2,数据源!$1:$1,0),FALSE)'
    )
    ws1.cell(22, COL_MAP["8月实际达成率"]).value = '=IF(OR(J22=0,J22=""),"",K22/J22)'
    ws1.cell(22, COL_MAP["8月实际达成率"]).number_format = '#,##0.0_ '
    ws1.cell(22, COL_MAP["9月 vs 8月 环比%"]).value = '=IF(K22=0,"",(G22-K22))'
    ws1.cell(22, COL_MAP["9月 vs 8月 环比%"]).number_format = '#,##0.0_ '

    # === 坏账/TR/利润率 (R30-R36) — 手工指标 ===
    # R30-R36 均为用户手填死数行 (坏账/TR/利润率不在数据源中)
    # 息费已留空白, TR公式(息费-1T7-息费坏账)不再可计算, 一并留空白由用户手填

    for row in MANUAL_ROWS:  # R30-R36
        # F(9月实际)/G(9月预估)/K(8月实际) 由用户手填, 脚本清空避免残留旧值
        ws1.cell(row, COL_MAP["9月实际"]).value = None
        ws1.cell(row, COL_MAP["9月预估"]).value = None
        ws1.cell(row, COL_MAP["8月实际"]).value = None
        # H = G - E
        ws1.cell(row, COL_MAP["9月预估达成%"]).value = f'=IF(G{row}="","",G{row}-E{row})'
        ws1.cell(row, COL_MAP["9月预估达成%"]).number_format = '0.0%'
        # L = K / J (8月实际达成率; TR/利润率/坏账8月目标空 → L空)
        ws1.cell(row, COL_MAP["8月实际达成率"]).value = f'=IF(OR(J{row}=0,J{row}=""),"",K{row}/J{row})'
        ws1.cell(row, COL_MAP["8月实际达成率"]).number_format = '0.0%'
        # M = G - K (9月vs8月绝对值变动)
        ws1.cell(row, COL_MAP["9月 vs 8月 环比%"]).value = f'=IF(G{row}="","",G{row}-K{row})'
        ws1.cell(row, COL_MAP["9月 vs 8月 环比%"]).number_format = '0.0%'
    print(f"  坏账/TR/利润率(R30-R36): F/G/K清空留手填, H=G-E, L=K/J, M=G-K")

    # ════════════════════════════════════════════════════
    # --- 4c. 整体行 = 首贷+复贷 公式联动 ---
    # ════════════════════════════════════════════════════
    # 第一段整体行: R5(金额)/R8(标数)/R11(笔均)/R14(期限)
    # (R17 息费按用户要求留空白, 不写公式)
    for col_idx in [COL_MAP["9月目标"], COL_MAP["9月实际"], COL_MAP["9月预估"],
                     COL_MAP["8月目标"], COL_MAP["8月实际"]]:
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

    # 第一段整体行 H/L/M: H=达成率(G/E), L=8月达成率(K/J), M=环比((G-K)/K) 用预估
    for row in [5, 8, 11, 14]:
        tgt = f"{get_column_letter(COL_MAP['9月目标'])}{row}"
        est = f"{get_column_letter(COL_MAP['9月预估'])}{row}"
        aug_tgt = f"{get_column_letter(COL_MAP['8月目标'])}{row}"
        aug_act = f"{get_column_letter(COL_MAP['8月实际'])}{row}"
        ws1.cell(row, COL_MAP["9月预估达成%"]).value = f'=IF({tgt}=0,"",{est}/{tgt})'
        ws1.cell(row, COL_MAP["9月预估达成%"]).number_format = '0.0%'
        # 8月实际达成率 = 8月实际 / 8月目标
        ws1.cell(row, COL_MAP["8月实际达成率"]).value = f'=IF(OR({aug_tgt}=0,{aug_tgt}=""),"",{aug_act}/{aug_tgt})'
        ws1.cell(row, COL_MAP["8月实际达成率"]).number_format = '0.0%'
        # 环比 (9月预估 vs 8月实际)
        ws1.cell(row, COL_MAP["9月 vs 8月 环比%"]).value = f'=IF({aug_act}=0,"",({est}-{aug_act})/{aug_act})'
        ws1.cell(row, COL_MAP["9月 vs 8月 环比%"]).number_format = '0.0%'

    print(f"  整体行公式已写入 (R17息费留空白)")

    # --- 4d. 更新9月预估 ---
    # 累计实际从宽表9月列取值（不查日实际SQL）
    def get_wide_value(metric, loan_type, col="9月"):
        row = df_wide[(df_wide["metric"] == metric) & (df_wide["loan_type"] == loan_type)]
        if len(row) > 0:
            val = row[col].values[0]
            return float(val) if pd.notna(val) else 0
        return 0

    # 9月累计实际（从宽表取，成交金额已在前面完成MXN→USD转换）
    total_fl_cnt = get_wide_value("成交标数", "首贷")
    total_fl_amt = get_wide_value("成交金额 (USD)***", "首贷")
    total_rl_cnt = get_wide_value("成交标数", "复贷")
    total_rl_amt = get_wide_value("成交金额 (USD)***", "复贷")

    print(f"  9月累计实际: 首贷{total_fl_cnt:.0f}笔/${total_fl_amt:,.0f}, "
          f"复贷{total_rl_cnt:.0f}笔/${total_rl_amt:,.0f}")

    # 清空日实际区域（R40-R71，原文件有但不再写入每日数据）
    daily_start_row = 40
    for row in range(daily_start_row, daily_start_row + 32):
        for col in range(1, 8):
            ws1.cell(row, col).value = None

    # --- 4e. 更新9月预估 ---
    # 规则:
    #   - 始终用最近8天日均预估（跨月取数，含8月末+9月数据）
    #   - 成交金额/成交标数 → 累计实际 + 日均 × 剩余天数
    #   - 笔均 → 预估金额 / 预估标数
    #   - 其他指标 → =9月实际
    import calendar
    year, month = map(int, CURRENT_MONTH.split('-'))
    days_total = calendar.monthrange(year, month)[1]  # 9月=30天
    days_passed = data_last_date.day  # 数据截止到实际最新日期
    days_remaining = max(0, days_total - days_passed)

    # 始终使用最近7天日均
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

    # --- 4e. 样式定义（提前到L列之前，确保后续代码可用）---
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

    # --- 4e. 辅助列：预估参数（O列=标签，P列=数值，Q列=备注）---
    # O/P/Q列引用"预估数据源"的完整日期，使用公式便于用户查看/校验
    ws1.cell(2, FC_LABEL_COL).value = "预估参数"
    ws1.cell(2, FC_VALUE_COL).value = "数值"
    ws1.cell(2, FC_NOTE_COL).value = "备注"
    forecast_params = [
        ("首贷日均金额", '=SUMIFS(预估数据源!C:C,预估数据源!G:G,1)/COUNTIFS(预估数据源!G:G,1)', "完整日期首贷成交金额均值"),
        ("复贷日均金额", '=SUMIFS(预估数据源!E:E,预估数据源!G:G,1)/COUNTIFS(预估数据源!G:G,1)', "完整日期复贷成交金额均值"),
        ("剩余天数", f'=DAY(EOMONTH(DATE({year},{month},1),0))-DAY(MAXIFS(预估数据源!A:A,预估数据源!G:G,1))', "当月总天数 - 数据完整日"),
        ("首贷日均笔数", '=SUMIFS(预估数据源!B:B,预估数据源!G:G,1)/COUNTIFS(预估数据源!G:G,1)', "完整日期首贷成交笔数均值"),
        ("复贷日均笔数", '=SUMIFS(预估数据源!D:D,预估数据源!G:G,1)/COUNTIFS(预估数据源!G:G,1)', "完整日期复贷成交笔数均值"),
    ]
    for i, (label, formula, note) in enumerate(forecast_params, 3):
        ws1.cell(i, FC_LABEL_COL).value = label
        ws1.cell(i, FC_VALUE_COL).value = formula
        ws1.cell(i, FC_NOTE_COL).value = note
    # 格式
    for r in range(2, 8):
        for col_idx in [FC_LABEL_COL, FC_VALUE_COL, FC_NOTE_COL]:
            c = ws1.cell(r, col_idx)
            c.font = FONT_DATA
            c.alignment = ALIGN_CENTER if col_idx in (FC_LABEL_COL, FC_VALUE_COL) else ALIGN_LEFT
            c.border = BORDER
    ws1.cell(2, FC_LABEL_COL).font = Font(name="微软雅黑", size=10, bold=True, color="FF000000")
    ws1.cell(2, FC_VALUE_COL).font = Font(name="微软雅黑", size=10, bold=True, color="FF000000")
    ws1.cell(2, FC_NOTE_COL).font = Font(name="微软雅黑", size=10, bold=True, color="FF000000")
    ws1.column_dimensions['O'].width = 16
    ws1.column_dimensions['P'].width = 14
    ws1.column_dimensions['Q'].width = 28
    for r in [3, 4, 5, 6, 7]:
        ws1.cell(r, FC_VALUE_COL).number_format = '#,##0'

    # --- 4f. 更新9月预估（公式形式，引用F列实际 + P列日均参数）---
    # 成交金额/成交标数 → 累计实际 + 日均 × 剩余天数
    # 整体行已在4c写入=首贷+复贷公式，此处不重复
    fl = get_column_letter(COL_MAP["9月预估"])
    act = get_column_letter(COL_MAP["9月实际"])
    p = get_column_letter(FC_VALUE_COL)  # P列=数值
    ws1.cell(3, COL_MAP["9月预估"]).value = f'={act}3+{p}3*{p}5'   # 首贷金额
    ws1.cell(4, COL_MAP["9月预估"]).value = f'={act}4+{p}4*{p}5'   # 复贷金额
    ws1.cell(6, COL_MAP["9月预估"]).value = f'={act}6+{p}6*{p}5'   # 首贷标数
    ws1.cell(7, COL_MAP["9月预估"]).value = f'={act}7+{p}7*{p}5'   # 复贷标数

    # 笔均 = 预估金额 / 预估标数（整体已在4c写入公式）
    ws1.cell(9, COL_MAP["9月预估"]).value = f'=IF(G6=0,"",G3/G6)'   # 首贷笔均
    ws1.cell(10, COL_MAP["9月预估"]).value = f'=IF(G7=0,"",G4/G7)'  # 复贷笔均
    ws1.cell(11, COL_MAP["9月预估"]).value = f'=IF(G8=0,"",G5/G8)'  # 整体笔均

    # 其他指标 → 等于9月实际值 (期限/CPS/1T0/1T7; 息费留空白)
    # 注意: CPD(R22)和第二段VLOOKUP指标的G=F已在4b写入, 此处只处理第一段非金额/标数/笔均
    for (metric, loan_type), s1_row in METRIC_ROW_MAP.items():
        if metric in ("成交金额 (USD)***", "成交标数", "笔均 (USD)***"):
            continue
        # 息费行留空白, 不写G公式
        if s1_row in _FEE_ROWS:
            continue
        # 第二段VLOOKUP指标的G=F已在4b写入, 跳过避免重复
        if s1_row >= 21:
            continue
        ws1.cell(s1_row, COL_MAP["9月预估"]).value = (
            f'={get_column_letter(COL_MAP["9月实际"])}{s1_row}'
        )

    print(f"  9月预估: 放款量/金额=公式(实际+日均×剩余天数), 日均参数写入O/P/Q列")


    # ═══════════════════════════════════════════════════════
    # --- 4g. 格式美化 + 删Sheet2 ---
    # ═══════════════════════════════════════════════════════
    print("\n[4g] 格式化 + 清理...")

    # ---- R2/R20 表头文字（确保一致）----
    ws1.cell(2, 2).value = "类目1"
    ws1.cell(2, 3).value = "类目2"
    ws1.cell(2, 4).value = "类目3"
    ws1.cell(2, 5).value = "9月目标"
    ws1.cell(2, 6).value = "9月实际"
    ws1.cell(2, 7).value = "9月预估"
    ws1.cell(2, 8).value = "9月预估达成%**"
    ws1.cell(2, 8).number_format = '0.0%'
    ws1.cell(2, 9).value = None  # I 空白分隔
    ws1.cell(2, 10).value = "8月目标"
    ws1.cell(2, 11).value = "8月实际"
    ws1.cell(2, 12).value = "8月实际达成率**"
    ws1.cell(2, 12).number_format = '0.0%'
    ws1.cell(2, 13).value = "9月 vs 8月\n环比%**"
    ws1.cell(2, 13).number_format = '0.0%'
    ws1.cell(2, 14).value = None  # N 空白分隔

    ws1.cell(20, 2).value = "类目1"
    ws1.cell(20, 3).value = "类目2"
    ws1.cell(20, 4).value = "类目3"
    ws1.cell(20, 5).value = "9月目标"
    ws1.cell(20, 6).value = "9月实际"
    ws1.cell(20, 7).value = "9月预估"
    ws1.cell(20, 8).value = "9月目标绝对值差值**"
    ws1.cell(20, 8).number_format = '0.0%'
    ws1.cell(20, 9).value = None
    ws1.cell(20, 10).value = "8月目标"
    ws1.cell(20, 11).value = "8月实际"
    ws1.cell(20, 12).value = "8月实际达成率**"
    ws1.cell(20, 12).number_format = '0.0%'
    ws1.cell(20, 13).value = "9月 vs 8月\n绝对值变动**"
    ws1.cell(20, 13).number_format = '0.0%'
    ws1.cell(20, 14).value = None

    # ---- 清空 E15/E16/E17 背景色 (模板遗留灰调) ----
    NO_FILL = PatternFill(fill_type=None)
    for row in [15, 16, 17]:
        ws1.cell(row, 5).fill = NO_FILL

    # ---- C列类目2标签 (已插入 R21 日投放金额行, 标签整体+1) ----
    ws1.cell(3, 3).value = "成交金额 (USD)***"
    ws1.cell(6, 3).value = "成交标数"
    ws1.cell(9, 3).value = "笔均 (USD)***"
    ws1.cell(12, 3).value = "期限"
    ws1.cell(15, 3).value = "息费（不含坏账）"
    ws1.cell(21, 3).value = "日投放金额(USD)***"
    ws1.cell(22, 3).value = "静态CPS (USD)***"
    ws1.cell(23, 3).value = "静态CPD %"
    ws1.cell(24, 3).value = "1T0"
    ws1.cell(27, 3).value = "1T7"
    ws1.cell(30, 3).value = "本金坏账Vintage%"
    ws1.cell(33, 3).value = "TR%"
    ws1.cell(36, 3).value = "经营利润率"

    # ---- D列类目3标签 ----
    for row, label in [(3,"首贷"),(4,"复贷"),(5,"整体"),
                        (6,"首贷"),(7,"复贷"),(8,"整体"),
                        (9,"首贷"),(10,"复贷"),(11,"整体"),
                        (12,"首贷"),(13,"复贷"),(14,"整体"),
                        (15,"首贷"),(16,"复贷"),(17,"整体")]:
        ws1.cell(row, 4).value = label
    # 第二段D列 (已插入日投放金额行, 整体+1)
    for row, label in [(24,"首贷"),(25,"复贷"),(26,"整体"),
                        (27,"首贷"),(28,"复贷"),(29,"整体"),
                        (30,"首贷"),(31,"复贷"),(32,"整体"),
                        (33,"首贷"),(34,"复贷"),(35,"整体"),
                        (36,"整体")]:
        ws1.cell(row, 4).value = label
    # R21/R22/R23 无D列标签 (日投/CPS/CPD是单行指标)
    ws1.cell(21, 4).value = None
    ws1.cell(22, 4).value = None
    ws1.cell(23, 4).value = None

    # ---- 列宽（完全对齐新列布局）----
    col_widths = {
        'A': 12.7, 'B': 10.7, 'C': 24.8, 'D': 12.4,
        'E': 12.6, 'F': 12.4, 'G': 12.8, 'H': 12.8,
        'I': 6.0,   # 空白分隔列
        'J': 12.4, 'K': 12.4, 'L': 12.8, 'M': 12.8,
        'N': 6.0,   # 空白分隔列
        'O': 16.0, 'P': 14.0, 'Q': 28.0,
    }
    for col_letter, width in col_widths.items():
        if ws1.column_dimensions.get(col_letter):
            ws1.column_dimensions[col_letter].width = width

    # ---- 行高（对齐原文件：R2=32.5，其余默认）----
    ws1.row_dimensions[2].height = 32.5
    # 清空之前设置的行高，恢复默认
    for r in list(ws1.row_dimensions):
        if r not in (2,):
            ws1.row_dimensions[r].height = None

    # ---- 合并单元格 ----
    # （旧合并已在文件加载后第一时间解除，此处直接建新合并）

    merge_ranges = [
        'C3:C5', 'C6:C8', 'C9:C11',       # 成交金额 / 成交标数 / 笔均
        'C12:C14', 'C15:C17',              # 期限 / 息费
        'C18:C19',                          # 空白分隔
        'C24:C26', 'C27:C29',              # 1T0 / 1T7 (已插入日投放金额行)
        'C30:C32', 'C33:C35',              # 本金坏账Vintage% / TR%
    ]
    for mr in merge_ranges:
        ws1.merge_cells(mr)

    # ---- B列类目1纵向合并 + 垂直居中 ----
    ws1.cell(3, 2).value = "规模&收入"
    ws1.cell(21, 2).value = "成本"
    ws1.merge_cells('B3:B17')   # 规模&收入 → 覆盖成交金额~息费
    ws1.merge_cells('B21:B35')  # 成本 → 覆盖日投~TR%
    for r in [3, 21]:
        c = ws1.cell(r, 2)
        c.font = FONT_DATA
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER

    # ---- R1：清空日期进度 ----
    for c in range(1, 18):
        ws1.cell(1, c).value = None
        ws1.cell(1, c).font = Font(name="微软雅黑", size=10, color="000000")

    # ---- 表头行 R2 格式 ----
    for col in range(1, 18):
        c = ws1.cell(2, col)
        if c.value is not None:
            c.font = FONT_HDR
            c.fill = HDR_FILL
            c.border = BORDER
            c.alignment = ALIGN_CENTER
    ws1.cell(2, 7).border = Border(left=THIN, right=None, top=THIN, bottom=THIN)

    # ---- 数据行 R3-R39 格式：字体 + 对齐 ----
    for row in range(3, 40):
        for col in range(1, 18):
            cell = ws1.cell(row, col)
            if cell.value is None and col > 2:
                continue
            cell.border = Border()  # 先清空默认细框线
            cell.font = FONT_DATA
            if col in (3, 4):
                cell.alignment = ALIGN_LEFT
            elif col in (5, 6, 7, 8, 10, 11, 12, 13):
                cell.alignment = ALIGN_RIGHT
            else:
                cell.alignment = ALIGN_CENTER

    # ---- 按"类目2"分组画框线 ----
    category_groups = [
        (3, 5), (6, 8), (9, 11), (12, 14), (15, 17),        # 截面1: 规模&收入
        (21, 21), (22, 22), (23, 23),                        # 日投放 / CPS / CPD
        (24, 26), (27, 29),                                  # 1T0 / 1T7
        (30, 32), (33, 35), (36, 36),                        # 坏账 / TR% / 利润率
    ]
    col_borders_sec1 = {2:(1,1), 3:(1,1), 4:(1,0), 5:(1,1), 6:(0,1), 7:(1,0), 8:(1,1),
                        10:(1,1), 11:(1,1), 12:(1,1), 13:(1,1)}
    col_borders_sec2 = {2:(1,1), 3:(1,1), 4:(1,1), 5:(1,1), 6:(1,1), 7:(1,1), 8:(1,1),
                        10:(1,1), 11:(1,1), 12:(1,1), 13:(1,1)}
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

    # ---- 表头行 R20 格式（第二段表头）----
    for col in range(1, 18):
        c = ws1.cell(20, col)
        if c.value is not None:
            c.font = FONT_HDR
            c.fill = HDR_FILL
            c.border = BORDER
            c.alignment = ALIGN_CENTER
    ws1.row_dimensions[20].height = 32.5

    # ---- 数值格式 ----
    # 第一段 R3-R17
    for row in range(3, 18):
        for col in [5, 6, 7, 10, 11, 12, 13]:
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
            elif row in (15, 16, 17):
                c.number_format = '0.0%'       # 息费
    # 第二段 R21-R36
    for row in range(21, 37):
        for col in [5, 6, 7, 10, 11, 12, 13]:
            c = ws1.cell(row, col)
            if c.value is None:
                continue
            if row in (21, 22):
                c.number_format = '#,##0'       # 日投放金额 / 静态CPS (USD)
            else:
                c.number_format = '0.0%'        # CPD/1T0/1T7/坏账/TR/利润率

    # ---- 息费：R15-R17 整体留空白, 灰调全部数据列 ----
    for row in [15, 16, 17]:
        for col_idx in [5, 6, 7, 8, 10, 11, 12, 13]:  # E/F/G/H/J/K/L/M
            cell = ws1.cell(row, col_idx)
            cell.value = None
            cell.fill = GRAY_FILL

    # ---- 1T0/1T7：G列（8月预估）不灰调 ----
    for row in [24, 25, 26, 27, 28, 29]:
        ws1.cell(row, 7).fill = NO_FILL

    # ---- 日实际区域 R40-R70 ----
    for col in range(1, 8):
        c = ws1.cell(40, col)
        if c.value is not None:
            c.font = FONT_HDR
            c.fill = HDR_FILL
            c.border = BORDER
            c.alignment = ALIGN_CENTER
    for row in range(41, 72):
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

    # ---- 预估数据源 sheet（近8天每日明细，横向布局：每天一行）----
    ws_fc = None
    if "预估数据源" in wb.sheetnames:
        ws_fc = wb["预估数据源"]
        for row in ws_fc.iter_rows(min_row=1, max_row=ws_fc.max_row, max_col=ws_fc.max_column):
            for cell in row:
                cell.value = None
    else:
        ws_fc = wb.create_sheet("预估数据源")

    # 横向布局：日期 | 首贷笔数 | 首贷金额 | 复贷笔数 | 复贷金额 | 总金额 | 是否完整
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
        print(f"  预估数据源: {len(agg)} 天已写入（'是否完整'改为公式）")
    else:
        fc_last_row = 1
        print("  ⚠ 预估数据源无数据")

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

    # ---- 脚注 R37-R39：动态日期 + 汇率(仅近2个月) ----
    # 注: R36 是经营利润率数据行, 脚注整体下移一行避免冲突
    yesterday_str = data_last_date.strftime('%Y/%m/%d')
    ws1.cell(37, 2).value = f"* 数据截止于{yesterday_str}"
    ws1.cell(38, 2).value = "** 红底数据表示对应指标差于上月或未达成本月目标"
    # 汇率脚注: 仅显示最近2个月
    current_month_num = int(CURRENT_MONTH.split('-')[1])
    prev_month_num = current_month_num - 1
    recent_months = sorted([m for m in exchange_rates if m in (prev_month_num, current_month_num)])
    rates_display = "  ".join(f"{m}月={exchange_rates[m]:.4f}" for m in recent_months)
    ws1.cell(39, 2).value = f"*** 各月汇率(MXN/USD): {rates_display}"
    for r in [37, 38, 39]:
        c = ws1.cell(r, 2)
        c.font = FONT_DATA
        c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)

    # ---- 脚注 R37-R39：去除框线、字号小一号 ----
    for r in [37, 38, 39]:
        c = ws1.cell(r, 2)
        c.border = Border()
        c.font = Font(name="微软雅黑", size=9, color="FF000000")

    # 删Sheet2
    if "Sheet2" in wb.sheetnames:
        del wb["Sheet2"]
        print("  Sheet2 已删除")

    print("  格式已对齐原文件（微软雅黑10pt/原列宽/无冻结/C列合并）")

    # ---- 字体颜色：死数蓝色，公式黑色（表头行保持白色） ----
    BLUE_FONT = Font(name="微软雅黑", size=10, color="FF0070C0")
    WHITE_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFFFF")
    # 确保R2/R20表头文字为白色
    for hdr_row in [2, 20]:
        for col_idx in range(1, 18):
            c = ws1.cell(hdr_row, col_idx)
            if c.value is not None:
                c.font = WHITE_FONT
    for col_idx in [5, 6, 10, 11]:  # E(9月目标), F(9月实际), J(8月目标), K(8月实际)
        for row in range(3, 40):
            if row == 20:
                continue  # 第二段表头保持白色
            cell = ws1.cell(row, col_idx)
            if cell.value is None or cell.value == "":
                continue
            # 公式以 = 开头，保持黑色；死数设为蓝色
            if isinstance(cell.value, str) and cell.value.startswith("="):
                continue
            else:
                cell.font = BLUE_FONT

    # ---- E3/E4: 手工汇率转换公式，模板中为蓝色 ----
    for row in [3, 4]:
        ws1.cell(row, 5).font = BLUE_FONT

    # ---- 类目1 (B列) 和类目2 (C列) 加粗；整体行 (D列) 加粗 ----
    # B列合并单元格左上角
    for row in [3, 21]:
        c = ws1.cell(row, 2)
        if c.value is not None:
            c.font = Font(name=c.font.name or "微软雅黑",
                          size=c.font.size or 10,
                          bold=True,
                          color=c.font.color.rgb if c.font.color else "FF000000")
    # C列合并单元格左上角 / 单行类目2标签
    for row in [3, 6, 9, 12, 15, 21, 22, 23, 24, 27, 30, 33, 36]:
        c = ws1.cell(row, 3)
        if c.value is not None:
            c.font = Font(name=c.font.name or "微软雅黑",
                          size=c.font.size or 10,
                          bold=True,
                          color=c.font.color.rgb if c.font.color else "FF000000")
    # ---- D列整体行 + E/F/G/H/J/K/L/M 整行加粗 ----
    OVERALL_ROWS = [5, 8, 11, 14, 17, 26, 29, 32, 35, 36]
    for row in OVERALL_ROWS:
        for col in [4, 5, 6, 7, 8, 10, 11, 12, 13]:  # D/E/F/G/H/J/K/L/M
            c = ws1.cell(row, col)
            if c.value is not None:
                existing_color = c.font.color.rgb if (c.font.color and c.font.color.rgb) else "FF000000"
                c.font = Font(name=c.font.name or "微软雅黑",
                              size=c.font.size or 10,
                              bold=True,
                              color=existing_color)

    # ---- H/M 列条件格式：按标准模板精确规则 ----
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.styles.colors import Color
    # 两种填色：theme浅色(未达目标/成本超标) + 红色(差于上月/利润下滑)
    THEME_FILL = PatternFill(patternType='solid', fgColor='00000000',
                             bgColor=Color(theme=9, tint=0.599963377788629))
    RED_FILL = PatternFill(patternType='solid', fgColor='00000000',
                           bgColor=Color(rgb='FFFFC7CE'))
    # 清理旧条件格式后按标准模板添加
    ws1.conditional_formatting._cf_rules.clear()
    # H列 (当月 vs 目标绝对值差值)
    ws1.conditional_formatting.add('H3:H17', CellIsRule(operator='lessThanOrEqual', formula=['1'], fill=THEME_FILL))
    ws1.conditional_formatting.add('H21:H23', CellIsRule(operator='greaterThan', formula=['0'], fill=THEME_FILL))
    ws1.conditional_formatting.add('H30:H31', CellIsRule(operator='greaterThan', formula=['0'], fill=THEME_FILL))
    ws1.conditional_formatting.add('H32:H35', CellIsRule(operator='lessThan', formula=['0'], fill=RED_FILL))
    # M列 (当月 vs 上月绝对值变动)
    ws1.conditional_formatting.add('M3:M17', CellIsRule(operator='lessThan', formula=['0'], fill=RED_FILL))
    ws1.conditional_formatting.add('M21:M31', CellIsRule(operator='greaterThan', formula=['0'], fill=THEME_FILL))
    ws1.conditional_formatting.add('M32:M35', CellIsRule(operator='lessThan', formula=['0'], fill=RED_FILL))

    # ── 5. 保存 ────────────────────────────────────
    print("\n[5/5] 保存文件...")
    out_path = SRC_FILE.replace(".xlsx", f"_更新_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    wb.save(out_path)
    print(f"  已保存: {out_path}")
    print("=" * 60)
    print("完成! 打开文件检查 Sheet1 公式联动 + Sheet3 数据源")


if __name__ == "__main__":
    main()
