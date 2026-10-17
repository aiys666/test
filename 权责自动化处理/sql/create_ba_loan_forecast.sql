-- ind.ba_loan_forecast 建表语句
-- 经营计划自动化系统 — Step 4 使用

CREATE TABLE IF NOT EXISTS ind.ba_loan_forecast (
     id                 BIGINT,
     stat_month         VARCHAR(10),
     grant_strategy     VARCHAR(10),
     is_reloan2         VARCHAR(10),
     loan_cycle         SMALLINT,
     product_tag        VARCHAR(10),
     apply_cnt          BIGINT,
     before_pass_rate   DECIMAL(5,4),
     confirm_rate       DECIMAL(5,4),
     after_pass_rate    DECIMAL(5,4),
     pass_rate          DECIMAL(5,4),
     sign_grant_rate    DECIMAL(5,4),
     full_pass_rate     DECIMAL(18,10),
     loan_term_dist     DECIMAL(18,8),
     loan_cnt           DECIMAL(18,6),
     avg_amt_idr        DECIMAL(18,6),
     avg_amt_usd        DECIMAL(18,6),
     loan_amt_term_dist DECIMAL(18,8),
     t30_rate           DECIMAL(5,4),
     contract_amt       DECIMAL(18,6),
     bad_amt            DECIMAL(18,6),
     loan_cycle_amount  DECIMAL(18,6),
     loan_cycle_wtd     DECIMAL(18,6),
     annual_bad_rate    DECIMAL(18,10),
     loan_amt_rate      DECIMAL(18,8)
);
