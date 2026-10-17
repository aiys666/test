-- ============================================================
-- 字段映射说明 (Source: 权责格式 Sheet, Column W = 2026-08)
-- ============================================================
-- daily_avg_spend    = W5    首贷-日均投放量级
-- cps                = W6    投放CPS
-- fl_avg_amt         = W7    首贷-件均
-- fl_issue_cnt       = W8    首贷-笔数
-- fl_pass_rate       = W9    首贷-通过率
-- fl_contract_amt    = W10   首贷-合同业绩
-- fl_loan_cycle      = W11   首贷平均期限-天
-- fl_fee_rate        = W12   首贷-预计实收息费
-- fl_bad_rate        = W13   首贷-本金坏账
-- fl_cust_cost       = W16   首贷-获客成本
-- rl_avg_amt         = W28   复贷-件均
-- rl_issue_cnt       = W29   复贷-笔数
-- rl_pass_rate       = W30   复贷-通过率
-- rl_contract_amt    = W31   复贷-合同业绩
-- rl_loan_cycle      = W32   复贷平均期限-天
-- rl_fee_rate        = W33   复贷-预计实收息费
-- rl_bad_rate        = W34   复贷-本金坏账
-- total_amt          = W48   整体业绩-美金
-- rl_amt_ratio       = W49   复贷业绩占比
-- lend_biz_ratio     = W50   助贷业绩占比
-- lend_biz_amt       = W51   助贷业绩
-- total_fee_rate     = W52   整体-预计实收息费
-- total_bad_rate     = W53   整体-本金坏账
-- total_cust_cost    = W55   整体-获客成本
-- exchange_rate      = P&L!AM1  USD:IDR
-- ============================================================
-- Data source: 【7月】印尼经营计划测算_20260730.xlsx
-- Generated: 2026-07-30
-- Exchange rate: 18099 (USD:IDR)
-- ============================================================

-- Step 1: Backup current table
CREATE TABLE ind.ba_kpi_targets_m_20260801 AS
SELECT * FROM ind.ba_kpi_targets_m;



-- Step 4: Verify backup
SELECT * FROM ind.ba_kpi_targets_m_20260801;

-- Step 5: Insert Aug 2026 KPI target
INSERT INTO ind.ba_kpi_targets_m (
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
    '2026-08-01',
    'kpi',
    12000.000000,
    16.931994,
    0.000000,
    0.000000,
    0.000000,
    102.407628,
    21970,
    0.051300,
    2249920,
    132,
    0.295184,
    -0.296174,
    -0.165339,
    161.651406,
    124445,
    0.732943,
    20116647,
    143,
    0.355365,
    -0.215000,
    22366567,
    0.899407,
    0.984045,
    22009718,
    0.349311,
    -0.223166,
    -0.016632,
    18099
);



-- Step 2: Clear target table
DELETE FROM ind.ba_kpi_targets_m;

-- Step 3: Restore backup (keep history)
INSERT INTO ind.ba_kpi_targets_m
SELECT * FROM ind.ba_kpi_targets_m_20260801;