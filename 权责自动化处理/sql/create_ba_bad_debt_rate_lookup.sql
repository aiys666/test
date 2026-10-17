-- ind.ba_bad_debt_rate_lookup 建表语句
-- 经营计划自动化系统 — Step 1 使用

CREATE TABLE IF NOT EXISTS ind.ba_bad_debt_rate_lookup (
    grant_month    VARCHAR(10),
    product_tag    VARCHAR(10),
    period_tag     VARCHAR(10),
    grant_strategy VARCHAR(10),
    loan_cycle     INT,
    bad_debt_rate  DOUBLE
);
