-- ============================================================
-- 权责近两个月数据预估 -> ind.ba_loan_forecast
-- 说明:
--   - grant_strategy: NEW=首贷, OLD=复贷
--   - is_reloan2: N=首贷, Y=复贷
--   - avg_amt_idr: 件均IDR = 件均(万IDR) × 10000
--   - contract_amt: 合同金额 = 业绩$ (perf_usd)
--   - bad_amt: 坏账金额 = 合同金额 × T30坏账率
--   - loan_cycle_amount: 业绩(万IDR) = 放款笔数×件均/汇率×10000
--   - loan_cycle_wtd: 业绩×期限(万IDR) = 放款笔数×件均×期限/汇率×10000
--   - loan_amt_term_dist: 本行期限分布权重 = 本行loan_term_dist / SUM(所有行)
--   - loan_amt_rate: 本行金额占比 = 本行contract_amt / SUM(所有行)
--   - annual_bad_rate: 年化坏账率 = T30 × 12 / 期限
-- ============================================================

-- 步骤1: 插入4月数据
INSERT INTO ind.ba_loan_forecast (
    id, stat_month, grant_strategy, is_reloan2, loan_cycle, product_tag,
    apply_cnt, before_pass_rate, confirm_rate, after_pass_rate,
    pass_rate, sign_grant_rate, full_pass_rate, loan_term_dist, loan_cnt,
    avg_amt_idr, avg_amt_usd, loan_amt_term_dist, t30_rate,
    contract_amt, bad_amt, loan_cycle_amount, loan_cycle_wtd,
    annual_bad_rate, loan_amt_rate
)
SELECT
    ROW_NUMBER() OVER (ORDER BY loan_type, term_month, product_type) AS id,
    month AS stat_month,
    CASE WHEN loan_type = '首贷' THEN 'NEW' ELSE 'OLD' END AS grant_strategy,
    CASE WHEN loan_type = '首贷' THEN 'N' ELSE 'Y' END AS is_reloan2,
    term_month AS loan_cycle,
    product_type AS product_tag,
    CAST(app_volume AS BIGINT) AS apply_cnt,
    rate_mc AS before_pass_rate,
    rate_cf AS confirm_rate,
    rate_post AS after_pass_rate,
    rate_risk AS pass_rate,
    rate_sign AS sign_grant_rate,
    full_flow_rate AS full_pass_rate,
    loan_term_dist AS loan_term_dist,
    CAST(loan_cnt AS BIGINT) AS loan_cnt,
    avg_prin_wan * 10000.0 AS avg_amt_idr,
    avg_pran_usd AS avg_amt_usd,
    -- 期限分布权重: 本行loan_term_dist / SUM(month内所有行)
    ROUND(loan_term_dist / SUM(loan_term_dist) OVER (PARTITION BY month), 6) AS loan_amt_term_dist,
    t30_rate AS t30_rate,
    perf_usd AS contract_amt,
    bad_debt_usd AS bad_amt,
    perf_idr AS loan_cycle_amount,
    perf_term_wtd AS loan_cycle_wtd,
    annual_bad_rate AS annual_bad_rate,
    -- 金额占比: 本行contract_amt / SUM(month内所有行)
    ROUND(perf_usd / SUM(perf_usd) OVER (PARTITION BY month), 6) AS loan_amt_rate
FROM (
    SELECT month, loan_type, term_month, product_type,
           app_volume, rate_mc, rate_cf, rate_post, rate_risk, rate_sign,
           full_flow_rate, loan_term_dist, loan_cnt, avg_pran_wan, avg_pran_usd,
           t30_rate, perf_idr, perf_usd, bad_debt_usd, perf_term_wtd, wtd_term, annual_bad_rate
    FROM loan_forecast
    WHERE month = '2026-04'
) t
ORDER BY stat_month DESC, grant_strategy, term_month, product_tag;

-- 步骤2: 插入5月数据 (id 续接)
INSERT INTO ind.ba_loan_forecast (
    id, stat_month, grant_strategy, is_reloan2, loan_cycle, product_tag,
    apply_cnt, before_pass_rate, confirm_rate, after_pass_rate,
    pass_rate, sign_grant_rate, full_pass_rate, loan_term_dist, loan_cnt,
    avg_amt_idr, avg_amt_usd, loan_amt_term_dist, t30_rate,
    contract_amt, bad_amt, loan_cycle_amount, loan_cycle_wtd,
    annual_bad_rate, loan_amt_rate
)
SELECT
    ROW_NUMBER() OVER (ORDER BY loan_type, term_month, product_type) + 35 AS id,
    month AS stat_month,
    CASE WHEN loan_type = '首贷' THEN 'NEW' ELSE 'OLD' END AS grant_strategy,
    CASE WHEN loan_type = '首贷' THEN 'N' ELSE 'Y' END AS is_reloan2,
    term_month AS loan_cycle,
    product_type AS product_tag,
    CAST(app_volume AS BIGINT) AS apply_cnt,
    rate_mc AS before_pass_rate,
    rate_cf AS confirm_rate,
    rate_post AS after_pass_rate,
    rate_risk AS pass_rate,
    rate_sign AS sign_grant_rate,
    full_flow_rate AS full_pass_rate,
    loan_term_dist AS loan_term_dist,
    CAST(loan_cnt AS BIGINT) AS loan_cnt,
    avg_pran_wan * 10000.0 AS avg_amt_idr,
    avg_pran_usd AS avg_amt_usd,
    ROUND(loan_term_dist / SUM(loan_term_dist) OVER (PARTITION BY month), 6) AS loan_amt_term_dist,
    t30_rate AS t30_rate,
    perf_usd AS contract_amt,
    bad_debt_usd AS bad_amt,
    perf_idr AS loan_cycle_amount,
    perf_term_wtd AS loan_cycle_wtd,
    annual_bad_rate AS annual_bad_rate,
    ROUND(perf_usd / SUM(perf_usd) OVER (PARTITION BY month), 6) AS loan_amt_rate
FROM (
    SELECT month, loan_type, term_month, product_type,
           app_volume, rate_mc, rate_cf, rate_post, rate_risk, rate_sign,
           full_flow_rate, loan_term_dist, loan_cnt, avg_pran_wan, avg_pran_usd,
           t30_rate, perf_idr, perf_usd, bad_debt_usd, perf_term_wtd, wtd_term, annual_bad_rate
    FROM loan_forecast
    WHERE month = '2026-05'
) t
ORDER BY stat_month DESC, grant_strategy, term_month, product_tag;
