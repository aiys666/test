# -*- coding: utf-8 -*-
"""
墨西哥经分 — 宽表指标查询
输出：8个指标 × 3种贷款类型 × 1-7月 横向宽表 Excel
"""

import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
from datetime import datetime

# ═══════════════════════════════════════════════════════
SQL = """
WITH
-- 基础放款数据（含首复贷标签）
base_loan AS (
    SELECT
        DATE_TRUNC('month', t.release_time) AS month,
        rt.double_loan,
        t.contract_amount,
        t.loan_cycle,
        t.fee_amount,
        t.interest AS interest_amount,
        t.haircut_amount
    FROM ods.s02_loan t
    INNER JOIN mx.risk_double_loan_tag rt
        ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
    WHERE t.release_time >= DATE '2026-01-01'
      AND t.state IN (1, 2, 3)
      AND rt.double_loan IN (0, 1)
),

-- 按月、按类型汇总放款数据
loan_agg AS (
    SELECT
        month,
        double_loan,
        SUM(contract_amount) AS sum_contract,
        COUNT(1) AS cnt_loan,
        SUM(loan_cycle * contract_amount) AS sum_weighted_term,
        SUM(fee_amount + interest_amount + haircut_amount) AS sum_fee
    FROM base_loan
    GROUP BY 1,2

    UNION ALL

    SELECT
        month,
        NULL AS double_loan,
        SUM(contract_amount),
        COUNT(1),
        SUM(loan_cycle * contract_amount),
        SUM(fee_amount + interest_amount + haircut_amount)
    FROM base_loan
    GROUP BY 1
),

-- 放款指标行
loan_metrics AS (
    SELECT '成交金额 (USD)***' AS metric,
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END AS loan_type,
        month, ROUND(sum_contract, 0) AS value
    FROM loan_agg
    UNION ALL
    SELECT '成交标数',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(cnt_loan, 0)
    FROM loan_agg
    UNION ALL
    SELECT '笔均 (USD)***',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_contract / cnt_loan, 0)
    FROM loan_agg
    UNION ALL
    SELECT '期限',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_weighted_term / sum_contract, 0)
    FROM loan_agg
    UNION ALL
    SELECT '息费率',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND(sum_fee / sum_contract, 4)
    FROM loan_agg
),

-- 月度投放花费
cost_spend AS (
    SELECT
        DATE_TRUNC('month', ad_date) AS month,
        SUM(spend_usd) AS spend
    FROM dwd.dwd_ads_cost
    WHERE ad_date >= DATE '2026-01-01' AND ad_date < DATE '2026-08-01'
    GROUP BY 1
),

-- 月度首贷放款笔数（CPS只算首贷）
first_loan_cnt AS (
    SELECT month, cnt_loan FROM loan_agg WHERE double_loan = 0
),

-- 静态CPS = 花费 / 首贷放款笔数（只有首贷才有CPS）
cps_rows AS (
    SELECT
        '静态CPS (USD)***' AS metric,
        '首贷' AS loan_type,
        c.month,
        ROUND(c.spend / fl.cnt_loan, 2) AS value
    FROM cost_spend c
    LEFT JOIN first_loan_cnt fl ON c.month = fl.month
),

-- 逾期还款数据（indexs=1）
overdue_base AS (
    SELECT
        DATE_TRUNC('month', release_dte) AS month,
        double_loan,
        SUM(hasrepayment_sum_t0) AS sum_has_t0,
        SUM(hasrepayment_sum_t7) AS sum_has_t7,
        SUM(t0_should_sum) AS sum_t0_should,
        SUM(t7_should_sum) AS sum_t7_should
    FROM mx.mxepd_gyq_multyproduct_overdue_tmp_huizong_all
    WHERE release_dte >= DATE '2026-01-01'
      AND indexs = 1
    GROUP BY 1, 2

    UNION ALL

    SELECT
        DATE_TRUNC('month', release_dte) AS month,
        NULL AS double_loan,
        SUM(hasrepayment_sum_t0),
        SUM(hasrepayment_sum_t7),
        SUM(t0_should_sum),
        SUM(t7_should_sum)
    FROM mx.mxepd_gyq_multyproduct_overdue_tmp_huizong_all
    WHERE release_dte >= DATE '2026-01-01'
      AND indexs = 1
    GROUP BY 1
),

-- 1T0 = (T0到期金额 - T0已还金额) / T0到期金额
-- 1T7 = (T7到期金额 - T7已还金额) / T7到期金额
overdue_rows AS (
    SELECT '1T0' AS metric,
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END AS loan_type,
        month, ROUND((sum_t0_should - sum_has_t0) / NULLIF(sum_t0_should, 0), 4) AS value
    FROM overdue_base
    UNION ALL
    SELECT '1T7',
        CASE WHEN double_loan=0 THEN '首贷' WHEN double_loan=1 THEN '复贷' ELSE '整体' END,
        month, ROUND((sum_t7_should - sum_has_t7) / NULLIF(sum_t7_should, 0), 4)
    FROM overdue_base
),

-- 合并所有指标
all_rows AS (
    SELECT * FROM loan_metrics
    UNION ALL
    SELECT * FROM cps_rows
    UNION ALL
    SELECT * FROM overdue_rows
)

-- 转置宽表
SELECT
    metric,
    loan_type,
    MAX(CASE WHEN month = DATE '2026-01-01' THEN value END) AS "1月",
    MAX(CASE WHEN month = DATE '2026-02-01' THEN value END) AS "2月",
    MAX(CASE WHEN month = DATE '2026-03-01' THEN value END) AS "3月",
    MAX(CASE WHEN month = DATE '2026-04-01' THEN value END) AS "4月",
    MAX(CASE WHEN month = DATE '2026-05-01' THEN value END) AS "5月",
    MAX(CASE WHEN month = DATE '2026-06-01' THEN value END) AS "6月",
    MAX(CASE WHEN month = DATE '2026-07-01' THEN value END) AS "7月"
FROM all_rows
GROUP BY metric, loan_type
ORDER BY
    CASE metric
        WHEN '成交金额 (USD)***' THEN 1
        WHEN '成交标数' THEN 2
        WHEN '笔均 (USD)***' THEN 3
        WHEN '期限' THEN 4
        WHEN '息费率' THEN 5
        WHEN '静态CPS (USD)***' THEN 6
        WHEN '1T0' THEN 7
        WHEN '1T7' THEN 8
    END,
    CASE loan_type WHEN '首贷' THEN 1 WHEN '复贷' THEN 2 WHEN '整体' THEN 3 END
"""

# ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("墨西哥经分宽表 — 8指标 × 3类型 × 1~7月")
    print("=" * 60)

    # 1. 连接数据库
    print("\n[1/3] 连接墨西哥 Presto...")
    pq = PrestoQuery()
    pq.login()
    print("  连接成功")

    # 2. 执行查询
    print("\n[2/3] 执行宽表查询...")
    df = pq.query(SQL, wait_sec=5)

    if isinstance(df, str):
        print(f"  查询失败:\n{df}")
        sys.exit(1)

    print(f"  返回 {len(df)} 行 × {len(df.columns)} 列")
    print()
    print(df.to_string(index=False))

    # 3. 保存 Excel
    out_dir = os.path.dirname(os.path.abspath(__file__))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"墨西哥宽表指标_{ts}.xlsx")

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="宽表指标", index=False)

    print(f"\n[3/3] 已保存: {out_path}")
    print("=" * 60)
