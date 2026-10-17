-- ============================================================
-- Field Mapping (Source: 权责输出 Sheet, Column V = 2026-07)
-- ============================================================
-- daily_avg_spend    = V5    首贷-日均投放量级
-- cps                = V6    投放CPS
-- fl_avg_amt         = V7    首贷-件均
-- fl_issue_cnt       = V8    首贷-笔数
-- fl_pass_rate       = V9    首贷-通过率
-- fl_contract_amt    = V10   首贷-合同业绩
-- fl_loan_cycle      = V11   首贷平均期限-天
-- fl_fee_rate        = V12   首贷-预计实收息费
-- fl_bad_rate        = V13   首贷-本金坏账
-- fl_cust_cost       = V16   首贷-获客成本
-- rl_avg_amt         = V28   复贷-件均
-- rl_issue_cnt       = V29   复贷-笔数
-- rl_pass_rate       = V30   复贷-通过率
-- rl_contract_amt    = V31   复贷-合同业绩
-- rl_loan_cycle      = V32   复贷平均期限-天
-- rl_fee_rate        = V33   复贷-预计实收息费
-- rl_bad_rate        = V34   复贷-本金坏账
-- total_amt          = V48   整体业绩-美金
-- rl_amt_ratio       = V49   复贷业绩占比
-- lend_biz_ratio     = V50   [MISSING]
-- lend_biz_amt       = V51   [MISSING]
-- total_fee_rate     = V52   整体-预计实收息费
-- total_bad_rate     = V53   整体-本金坏账
-- total_cust_cost    = V55   整体-获客成本
-- exchange_rate      = P&L!AL1  USD:MXN
-- ============================================================
-- Data source: 7月墨西哥经营计划测算_v20260728.xlsx
-- Generated: 2026-08-04
-- Exchange rate: 18.1884 (USD:MXN)
-- ============================================================

-- Step 1: Backup current table
CREATE TABLE mx.ba_kpi_targets_m_20260701 AS
SELECT * FROM mx.ba_kpi_targets_m;

-- Step 2: Clear target table
DELETE FROM mx.ba_kpi_targets_m;

-- Step 3: Restore backup (keep history)
INSERT INTO mx.ba_kpi_targets_m
SELECT * FROM mx.ba_kpi_targets_m_20260701;

-- Step 4: Verify backup
SELECT * FROM mx.ba_kpi_targets_m_20260701;

-- Step 5: Insert Jul 2026 KPI target
INSERT INTO mx.ba_kpi_targets_m (
    month,
    ba_type,
    daily_avg_spend,
    cps,
    fl_confirm_1_2_rate,
    fl_issue_1_4_cnt,
    fl_1_4_cps_rate,
    fl_avg_amt,
    fl_issue_cnt,
    fl_pass_rate,
    fl_contract_amt,
    fl_loan_cycle,
    fl_fee_rate,
    fl_bad_rate,
    fl_cust_cost,
    rl_avg_amt,
    rl_issue_cnt,
    rl_pass_rate,
    rl_contract_amt,
    rl_loan_cycle,
    rl_fee_rate,
    rl_bad_rate,
    total_amt,
    rl_amt_ratio,
    lend_biz_ratio,
    lend_biz_amt,
    total_fee_rate,
    total_bad_rate,
    total_cust_cost,
    exchange_rate
)
VALUES
(
    '2026-07-01',
    'kpi',
    16129.032260,
    35.186869,
    0.000000,
    0.000000,
    0.000000,
    62.822986,
    14210,
    0.129000,
    892705,
    17,
    0.513870,
    -0.386000,
    -0.560095,
    80.523896,
    39040,
    0.845000,
    3143654,
    24,
    0.587057,
    -0.317000,
    4036359,
    0.778834,
    0.000000,
    0,
    0.570871,
    -0.332260,
    -0.123874,
    18.1884
);
