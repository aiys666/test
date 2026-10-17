

-- ============================================================
-- 方案B：建临时表 + 分批插入（推荐，结果自动合并）
-- ============================================================

-- 步骤0：建结果表
-- DROP TABLE IF EXISTS mx.tmp_effect_decomp_all_dims;
 
-- -- 步骤 1.1：第 1 批 CTE + INSERT
-- create table  mx.tmp_effect_decomp_all_dims as 


      
-- ============================================================
-- 全维度逾期率效应分解 - 方案B：临时表 + 分批INSERT
-- 88个维度，分3批执行，每批stage ~60（集群上限150）
-- 输出字段：dim_name, dim_group, week,
--          billed_cnt(出账笔数), overdue_cnt(逾期笔数),
--          billed_amt(出账金额), overdue_amt(逾期金额),
--          issue_cnt(放款笔数), contract_amt(放款金额)
-- ============================================================

-- ============================================================
-- 步骤0：建结果表
-- ============================================================
DROP TABLE IF EXISTS mx.tmp_effect_decomp_all_dims;
CREATE TABLE mx.tmp_effect_decomp_all_dims (
    dim_name      VARCHAR,
    dim_group     VARCHAR,
    week          date,
    billed_cnt    BIGINT,    -- 1T0出账笔数
    overdue_cnt   BIGINT,    -- 1T0逾期笔数
    billed_amt    DOUBLE,    -- 1T0出账金额
    overdue_amt   DOUBLE,    -- 1T0逾期金额
    issue_cnt     BIGINT,    -- 放款笔数
    contract_amt  DOUBLE     -- 放款金额
);

-- ============================================================
-- 步骤 1：第 1 批（30 个维度）
-- ============================================================
INSERT INTO mx.tmp_effect_decomp_all_dims
WITH base AS (
    SELECT
        app_week,
        is_t0_window_1,
        is_t0_overdue_1,
        t0_should_amt_1,
        t0_overdue_amount_1,
        if_issue,
        contract_amount,
        V5_3_behavior_group_score,
        V5_3_fraud_group_score,
        advance_duotou_cnt_730d_score,
        advance_duotou_cnt_x_19_score,
        af_uninstall_cnt_30d_score,
        af_uninstall_cnt_lf_score,
        android_oldCust_apply_subscore_charge_V6_1_score,
        android_oldCust_behavior_subscore_charge_V6_1_score,
        android_oldCust_fraud_subscore_charge_V6_1_score,
        android_oldCust_income_subscore_charge_V6_1_score,
        android_oldCust_overdue_subscore_charge_V6_1_score,
        android_oldCust_ruleScore_charge_V5_3_bin,
        android_oldCust_voteScore_charge_V5_3_bin,
        app3_mix_loan1_cfinst_cnt_d30_score,
        app_hour_score,
        app_loan1_inst_cnt_day7_score,
        baseinfo_employee_type_score,
        baseinfo_has_car_score,
        baseinfo_has_house_score,
        baseinfo_marry_score,
        baseinfo_userprof_age_score,
        baseinfo_userprof_degree_score,
        beh2_o_create_reject_pct_d7_score,
        beh_main_reject_applypct_day60_score,
        emcontact_curr_ovd_cnt_all_score,
        finish_issue_rate_score,
        history_loanrec_cnt_lastprepaydays_v2_score,
        if_system_run_too_short_score,
        income_score,
        last_repay_gap_days_app_group_score
    FROM mx.yj_test_table_250225
    WHERE app_time >= date'2026-08-03'
   
)

SELECT 'V5.3行为子分' AS dim_name,
       CAST(V5_3_behavior_group_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE V5_3_behavior_group_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'V5.3欺诈子分' AS dim_name,
       CAST(V5_3_fraud_group_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE V5_3_fraud_group_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '730天多头' AS dim_name,
       CAST(advance_duotou_cnt_730d_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE advance_duotou_cnt_730d_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '30天多头' AS dim_name,
       CAST(advance_duotou_cnt_x_19_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE advance_duotou_cnt_x_19_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '近30天卸载次数' AS dim_name,
       CAST(af_uninstall_cnt_30d_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE af_uninstall_cnt_30d_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '卸载次数LF' AS dim_name,
       CAST(af_uninstall_cnt_lf_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE af_uninstall_cnt_lf_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'V6.1申请子分' AS dim_name,
       CAST(android_oldCust_apply_subscore_charge_V6_1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE android_oldCust_apply_subscore_charge_V6_1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'V6.1行为子分' AS dim_name,
       CAST(android_oldCust_behavior_subscore_charge_V6_1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE android_oldCust_behavior_subscore_charge_V6_1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'V6.1欺诈子分' AS dim_name,
       CAST(android_oldCust_fraud_subscore_charge_V6_1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE android_oldCust_fraud_subscore_charge_V6_1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'V6.1收入子分' AS dim_name,
       CAST(android_oldCust_income_subscore_charge_V6_1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE android_oldCust_income_subscore_charge_V6_1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'V6.1逾期子分' AS dim_name,
       CAST(android_oldCust_overdue_subscore_charge_V6_1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE android_oldCust_overdue_subscore_charge_V6_1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'V5.3规则分' AS dim_name,
       CAST(android_oldCust_ruleScore_charge_V5_3_bin AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE android_oldCust_ruleScore_charge_V5_3_bin IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'V5.3投票分' AS dim_name,
       CAST(android_oldCust_voteScore_charge_V5_3_bin AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE android_oldCust_voteScore_charge_V5_3_bin IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '30天混合首贷机构数' AS dim_name,
       CAST(app3_mix_loan1_cfinst_cnt_d30_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE app3_mix_loan1_cfinst_cnt_d30_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '申请时段' AS dim_name,
       CAST(app_hour_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE app_hour_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '7天首贷机构数' AS dim_name,
       CAST(app_loan1_inst_cnt_day7_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE app_loan1_inst_cnt_day7_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '雇佣类型' AS dim_name,
       CAST(baseinfo_employee_type_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE baseinfo_employee_type_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '是否有车' AS dim_name,
       CAST(baseinfo_has_car_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE baseinfo_has_car_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '是否有房' AS dim_name,
       CAST(baseinfo_has_house_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE baseinfo_has_house_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '婚姻状态' AS dim_name,
       CAST(baseinfo_marry_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE baseinfo_marry_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '年龄' AS dim_name,
       CAST(baseinfo_userprof_age_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE baseinfo_userprof_age_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '学历' AS dim_name,
       CAST(baseinfo_userprof_degree_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE baseinfo_userprof_degree_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '7天创建拒绝率' AS dim_name,
       CAST(beh2_o_create_reject_pct_d7_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE beh2_o_create_reject_pct_d7_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '60天主拒率' AS dim_name,
       CAST(beh_main_reject_applypct_day60_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE beh_main_reject_applypct_day60_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '紧急联系人逾期数' AS dim_name,
       CAST(emcontact_curr_ovd_cnt_all_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE emcontact_curr_ovd_cnt_all_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '完成放款率' AS dim_name,
       CAST(finish_issue_rate_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE finish_issue_rate_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '最近结清距今天数' AS dim_name,
       CAST(history_loanrec_cnt_lastprepaydays_v2_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE history_loanrec_cnt_lastprepaydays_v2_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '系统运行时长' AS dim_name,
       CAST(if_system_run_too_short_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE if_system_run_too_short_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '收入' AS dim_name,
       CAST(income_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE income_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '上次还款间隔天数' AS dim_name,
       CAST(last_repay_gap_days_app_group_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE last_repay_gap_days_app_group_score IS NOT NULL
GROUP BY 1, 2, 3

;

-- ============================================================
-- 步骤 2：第 2 批（30 个维度）
-- ============================================================
INSERT INTO mx.tmp_effect_decomp_all_dims
WITH base AS (
    SELECT
        app_week,
        is_t0_window_1,
        is_t0_overdue_1,
        t0_should_amt_1,
        t0_overdue_amount_1,
        if_issue,
        contract_amount,
        m687_old_1t3_ad_tengo_0709p1_score,
        m696_old_1t3_bj_iz_0530_p1_score,
        m698_old_1t3_voting_0619rh_score,
        m699_rh_new_bin,
        max_ovd_days_all_score,
        max_overdue_day_30d_all_score,
        minstay_repayplan_second_30d_mid_score,
        model_698_score,
        model_699_score,
        model_p2_1t_score,
        msg2_loandue_addpctall_day1_score,
        pvalue_mex_b311_2025v1_p1_score,
        pvalue_mex_b320_2026v1_long_p1_score,
        pvalue_mex_b321_2026v1_p1_score,
        pvalue_mex_b321_2026v2_p1_score,
        pvalue_mex_b329_2026v1_byid_p1_score,
        question3_score,
        question5_score,
        question6_v2_score,
        stgy_advance_gd_k_104_score,
        stgy_advance_gd_k_136_score,
        stgy_advance_gd_k_292_score,
        stgy_advance_gd_x_12_score,
        stgy_advance_gd_x_34_score,
        stgy_advance_gd_x_55_score,
        stgy_amlta_d180_record_date_unique_cnt_score,
        stgy_bj_apply_count_1w_score,
        stgy_bj_apply_jgs_12m_score,
        stgy_bj_apply_jgs_1w_score,
        stgy_bj_loan_count_1w_score
    FROM mx.yj_test_table_250225
    WHERE app_time >= date'2026-08-03'
)

SELECT '687模型分' AS dim_name,
       CAST(m687_old_1t3_ad_tengo_0709p1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE m687_old_1t3_ad_tengo_0709p1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '696模型分' AS dim_name,
       CAST(m696_old_1t3_bj_iz_0530_p1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE m696_old_1t3_bj_iz_0530_p1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '698投票分' AS dim_name,
       CAST(m698_old_1t3_voting_0619rh_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE m698_old_1t3_voting_0619rh_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '699新模型分箱' AS dim_name,
       CAST(m699_rh_new_bin AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE m699_rh_new_bin IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '全局逾期天数' AS dim_name,
       CAST(max_ovd_days_all_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE max_ovd_days_all_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '近30天逾期天数' AS dim_name,
       CAST(max_overdue_day_30d_all_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE max_overdue_day_30d_all_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '还款计划停留时长' AS dim_name,
       CAST(minstay_repayplan_second_30d_mid_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE minstay_repayplan_second_30d_mid_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '698模型分' AS dim_name,
       CAST(model_698_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE model_698_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '699模型分' AS dim_name,
       CAST(model_699_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE model_699_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '短逾模型P2' AS dim_name,
       CAST(model_p2_1t_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE model_p2_1t_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '到期日新增占比' AS dim_name,
       CAST(msg2_loandue_addpctall_day1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE msg2_loandue_addpctall_day1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'B311模型分' AS dim_name,
       CAST(pvalue_mex_b311_2025v1_p1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE pvalue_mex_b311_2025v1_p1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'B320长窗模型分' AS dim_name,
       CAST(pvalue_mex_b320_2026v1_long_p1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE pvalue_mex_b320_2026v1_long_p1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'B321V1模型分' AS dim_name,
       CAST(pvalue_mex_b321_2026v1_p1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE pvalue_mex_b321_2026v1_p1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'B321V2模型分' AS dim_name,
       CAST(pvalue_mex_b321_2026v2_p1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE pvalue_mex_b321_2026v2_p1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'B329模型分' AS dim_name,
       CAST(pvalue_mex_b329_2026v1_byid_p1_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE pvalue_mex_b329_2026v1_byid_p1_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '问卷3' AS dim_name,
       CAST(question3_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE question3_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '问卷5' AS dim_name,
       CAST(question5_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE question5_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '问卷6' AS dim_name,
       CAST(question6_v2_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE question6_v2_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '前置GD_K104' AS dim_name,
       CAST(stgy_advance_gd_k_104_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_advance_gd_k_104_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '前置GD_K136' AS dim_name,
       CAST(stgy_advance_gd_k_136_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_advance_gd_k_136_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '前置GD_K292' AS dim_name,
       CAST(stgy_advance_gd_k_292_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_advance_gd_k_292_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '前置GD_X12' AS dim_name,
       CAST(stgy_advance_gd_x_12_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_advance_gd_x_12_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '前置GD_X34' AS dim_name,
       CAST(stgy_advance_gd_x_34_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_advance_gd_x_34_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '前置GD_X55' AS dim_name,
       CAST(stgy_advance_gd_x_55_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_advance_gd_x_55_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'AMLTA180天记录数' AS dim_name,
       CAST(stgy_amlta_d180_record_date_unique_cnt_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_amlta_d180_record_date_unique_cnt_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '1周申请次数' AS dim_name,
       CAST(stgy_bj_apply_count_1w_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_bj_apply_count_1w_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '12月申请间隔' AS dim_name,
       CAST(stgy_bj_apply_jgs_12m_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_bj_apply_jgs_12m_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '1周申请间隔' AS dim_name,
       CAST(stgy_bj_apply_jgs_1w_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_bj_apply_jgs_1w_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '1周借款次数' AS dim_name,
       CAST(stgy_bj_loan_count_1w_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_bj_loan_count_1w_score IS NOT NULL
GROUP BY 1, 2, 3

;

-- ============================================================
-- 步骤 3：第 3 批（28 个维度）
-- ============================================================
INSERT INTO mx.tmp_effect_decomp_all_dims
WITH base AS (
    SELECT
        app_week,
        is_t0_window_1,
        is_t0_overdue_1,
        t0_should_amt_1,
        t0_overdue_amount_1,
        if_issue,
        contract_amount,
        stgy_dyna_amlba_d21_b_cnt_score,
        stgy_dyna_amlba_d30_c_cnt_score,
        stgy_dyna_amlba_d30_f2_daydiff_max_score,
        stgy_dyna_amlba_d60_f3_cnt_score,
        stgy_dyna_amlta_d60_daydiff_median_score,
        thirdparty_izi_whatsapp_register_status_score,
        unique_email_cnt_score,
        unique_phone_score,
        product_level,
        last_product_level,
        product_level_change,
        change_product_tag,
        v3_flag,
        if_inherit_tag,
        is_reloan,
        main_sanwich_loan_grp,
        product_level_test_260701,
        product_level_change_test_260722,
        change_flag1,
        product_test_0722,
        product_random_0722,
        daily_max_limit_tag,
        product_level_test_251205_flag,
        max_overdue_day_30d_all_strategy_test,
        cap_1point8_strategy_test,
        app_group,
        source,
        app
    FROM mx.yj_test_table_250225
    WHERE app_time >= date'2026-08-03'

)

SELECT 'AMLBA21天B类数' AS dim_name,
       CAST(stgy_dyna_amlba_d21_b_cnt_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_dyna_amlba_d21_b_cnt_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'AMLBA30天C类数' AS dim_name,
       CAST(stgy_dyna_amlba_d30_c_cnt_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_dyna_amlba_d30_c_cnt_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'AMLBA30天F2间隔' AS dim_name,
       CAST(stgy_dyna_amlba_d30_f2_daydiff_max_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_dyna_amlba_d30_f2_daydiff_max_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'AMLBA60天F3数' AS dim_name,
       CAST(stgy_dyna_amlba_d60_f3_cnt_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_dyna_amlba_d60_f3_cnt_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'AMLTA60天间隔中位数' AS dim_name,
       CAST(stgy_dyna_amlta_d60_daydiff_median_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE stgy_dyna_amlta_d60_daydiff_median_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'WA注册状态' AS dim_name,
       CAST(thirdparty_izi_whatsapp_register_status_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE thirdparty_izi_whatsapp_register_status_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '邮箱数量' AS dim_name,
       CAST(unique_email_cnt_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE unique_email_cnt_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '手机号数量' AS dim_name,
       CAST(unique_phone_score AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE unique_phone_score IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '产品等级' AS dim_name,
       CAST(product_level AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE product_level IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '上期产品等级' AS dim_name,
       CAST(last_product_level AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE last_product_level IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '产品等级变化' AS dim_name,
       CAST(product_level_change AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE product_level_change IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '是否转产线' AS dim_name,
       CAST(change_product_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE change_product_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'V3版本标识' AS dim_name,
       CAST(v3_flag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE v3_flag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '是否继承标签' AS dim_name,
       CAST(if_inherit_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE if_inherit_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '是否复贷' AS dim_name,
       CAST(is_reloan AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE is_reloan IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '贷款类型' AS dim_name,
       CAST(main_sanwich_loan_grp AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE main_sanwich_loan_grp IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '转产测试260701' AS dim_name,
       CAST(product_level_test_260701 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE product_level_test_260701 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '转产测试260722' AS dim_name,
       CAST(product_level_change_test_260722 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE product_level_change_test_260722 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '转产标记1' AS dim_name,
       CAST(change_flag1 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE change_flag1 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '产品测试0722' AS dim_name,
       CAST(product_test_0722 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE product_test_0722 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '产品随机分组0722' AS dim_name,
       CAST(product_random_0722 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE product_random_0722 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '日限额标签' AS dim_name,
       CAST(daily_max_limit_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE daily_max_limit_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '产品测试251205' AS dim_name,
       CAST(product_level_test_251205_flag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE product_level_test_251205_flag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '策略测试-逾期' AS dim_name,
       CAST(max_overdue_day_30d_all_strategy_test AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE max_overdue_day_30d_all_strategy_test IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '策略测试-提额1.8' AS dim_name,
       CAST(cap_1point8_strategy_test AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE cap_1point8_strategy_test IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'APP分组' AS dim_name,
       CAST(app_group AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE app_group IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '来源' AS dim_name,
       CAST(source AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE source IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'APP' AS dim_name,
       CAST(app AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE app IS NOT NULL
GROUP BY 1, 2, 3

;

-- ============================================================
-- 步骤 4：第 4 批（14 个维度：13个V6口径分箱 + B320 15档细分箱）
-- ============================================================
INSERT INTO mx.tmp_effect_decomp_all_dims
WITH base AS (
    SELECT
        app_week,
        is_t0_window_1,
        is_t0_overdue_1,
        t0_should_amt_1,
        t0_overdue_amount_1,
        if_issue,
        contract_amount,
        advance_duotou_cnt_x_19_score_v6,
        advance_duotou_cnt_730d_score_v6,
        last_repay_gap_days_app_group_score_v6,
        question3_score_v6,
        question6_v2_score_v6,
        max_ovd_days_all_score_v6,
        max_overdue_day_30d_all_score_v6,
        history_loanrec_cnt_lastprepaydays_v2_score_v6,
        unique_email_cnt_score_v6,
        af_uninstall_cnt_30d_score_v6,
        minstay_repayplan_second_30d_mid_score_v6,
        baseinfo_userprof_age_score_v6,
        baseinfo_userprof_degree_score_v6,
        pvalue_mex_b320_2026v1_long_p1_group
    FROM mx.yj_test_table_250225
    WHERE app_time >= date'2026-08-03'
)

SELECT '30天多头V6' AS dim_name,
       CAST(advance_duotou_cnt_x_19_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE advance_duotou_cnt_x_19_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '730天多头V6' AS dim_name,
       CAST(advance_duotou_cnt_730d_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE advance_duotou_cnt_730d_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '上次还款间隔天数V6' AS dim_name,
       CAST(last_repay_gap_days_app_group_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE last_repay_gap_days_app_group_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '问卷3-V6' AS dim_name,
       CAST(question3_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE question3_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '问卷6-V6' AS dim_name,
       CAST(question6_v2_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE question6_v2_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '全局逾期天数V6' AS dim_name,
       CAST(max_ovd_days_all_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE max_ovd_days_all_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '近30天逾期天数V6' AS dim_name,
       CAST(max_overdue_day_30d_all_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE max_overdue_day_30d_all_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '最近结清距今天数V6' AS dim_name,
       CAST(history_loanrec_cnt_lastprepaydays_v2_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE history_loanrec_cnt_lastprepaydays_v2_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '邮箱数量V6' AS dim_name,
       CAST(unique_email_cnt_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE unique_email_cnt_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '近30天卸载次数V6' AS dim_name,
       CAST(af_uninstall_cnt_30d_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE af_uninstall_cnt_30d_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '还款计划停留时长V6' AS dim_name,
       CAST(minstay_repayplan_second_30d_mid_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE minstay_repayplan_second_30d_mid_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '年龄V6' AS dim_name,
       CAST(baseinfo_userprof_age_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE baseinfo_userprof_age_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '学历V6' AS dim_name,
       CAST(baseinfo_userprof_degree_score_v6 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE baseinfo_userprof_degree_score_v6 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT 'B320长窗细分15档' AS dim_name,
       CAST(pvalue_mex_b320_2026v1_long_p1_group AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE pvalue_mex_b320_2026v1_long_p1_group IS NOT NULL
GROUP BY 1, 2, 3

;

-- ============================================================
-- 步骤 5：第 5 批（29 个维度：测试策略/发临额/其他包标签等非分箱字段）
-- ============================================================
INSERT INTO mx.tmp_effect_decomp_all_dims
WITH base AS (
    SELECT
        app_week,
        is_t0_window_1,
        is_t0_overdue_1,
        t0_should_amt_1,
        t0_overdue_amount_1,
        if_issue,
        contract_amount,
        cap_1point8cap_strategy_test_flag,
        temp_limit_test_flag,
        strategy_temp_limit_test_flag,
        temp_credit_amount_strategy_test_flag,
        strategy_temp_limit_interval_test_flag,
        emcontact_curr_ovd_cnt_all_test_flag,
        tagg_0819,
        tagg_0826,
        tagg_0902,
        tagg_0909,
        temp_limit_0819_tag,
        temp_limit_0820_tag,
        temp_limit_0826_tag,
        temp_limit_0827_tag,
        temp_limit_0902_tag,
        temp_limit_0903_tag,
        temp_limit_0909_tag,
        temp_limit_0910_tag,
        if_product_or_maxlimit_change_tag,
        repayment_clearing_count_tenant_flag,
        repayment_clearing_count_index_tenant_flag,
        other_app_has_loan_tag,
        other_app_has_overdue_tag,
        other_app_has_overdue_interval_tag,
        last_product_origin,
        change_flag,
        if_reloan_24h,
        product_name_new,
        global_limit
    FROM mx.yj_test_table_250225
    WHERE app_time >= date'2026-08-03'
)

SELECT '1.8倍cap测试分组' AS dim_name,
       CAST(cap_1point8cap_strategy_test_flag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE cap_1point8cap_strategy_test_flag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '发临额测试分组' AS dim_name,
       CAST(temp_limit_test_flag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE temp_limit_test_flag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '策略发临额测试' AS dim_name,
       CAST(strategy_temp_limit_test_flag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE strategy_temp_limit_test_flag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '临额金额策略分组' AS dim_name,
       CAST(temp_credit_amount_strategy_test_flag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE temp_credit_amount_strategy_test_flag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '临额间隔策略分组' AS dim_name,
       CAST(strategy_temp_limit_interval_test_flag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE strategy_temp_limit_interval_test_flag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '紧急联系人逾期标识' AS dim_name,
       CAST(emcontact_curr_ovd_cnt_all_test_flag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE emcontact_curr_ovd_cnt_all_test_flag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '0819离线发临额在贷' AS dim_name,
       CAST(tagg_0819 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE tagg_0819 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '0826离线发临额在贷' AS dim_name,
       CAST(tagg_0826 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE tagg_0826 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '0902离线发临额在贷' AS dim_name,
       CAST(tagg_0902 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE tagg_0902 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '0909离线发临额在贷' AS dim_name,
       CAST(tagg_0909 AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE tagg_0909 IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '0819发临额标签' AS dim_name,
       CAST(temp_limit_0819_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE temp_limit_0819_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '0820发临额标签' AS dim_name,
       CAST(temp_limit_0820_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE temp_limit_0820_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '0826发临额标签' AS dim_name,
       CAST(temp_limit_0826_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE temp_limit_0826_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '0827发临额标签' AS dim_name,
       CAST(temp_limit_0827_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE temp_limit_0827_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '0902发临额标签' AS dim_name,
       CAST(temp_limit_0902_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE temp_limit_0902_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '0903发临额标签' AS dim_name,
       CAST(temp_limit_0903_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE temp_limit_0903_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '0909发临额标签' AS dim_name,
       CAST(temp_limit_0909_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE temp_limit_0909_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '0910发临额标签' AS dim_name,
       CAST(temp_limit_0910_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE temp_limit_0910_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '产品/最大额度变更标签' AS dim_name,
       CAST(if_product_or_maxlimit_change_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE if_product_or_maxlimit_change_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '结清次数分档' AS dim_name,
       CAST(repayment_clearing_count_tenant_flag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE repayment_clearing_count_tenant_flag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '结清次数指数分档' AS dim_name,
       CAST(repayment_clearing_count_index_tenant_flag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE repayment_clearing_count_index_tenant_flag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '其他包放款标签' AS dim_name,
       CAST(other_app_has_loan_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE other_app_has_loan_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '其他包在逾标签' AS dim_name,
       CAST(other_app_has_overdue_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE other_app_has_overdue_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '其他包在逾区间' AS dim_name,
       CAST(other_app_has_overdue_interval_tag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE other_app_has_overdue_interval_tag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '上笔产品来源' AS dim_name,
       CAST(last_product_origin AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE last_product_origin IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '转产标记' AS dim_name,
       CAST(change_flag AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE change_flag IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '24H复贷' AS dim_name,
       CAST(if_reloan_24h AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE if_reloan_24h IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '产品名称' AS dim_name,
       CAST(product_name_new AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE product_name_new IS NOT NULL
GROUP BY 1, 2, 3

UNION ALL
SELECT '全局额度' AS dim_name,
       CAST(global_limit AS VARCHAR) AS dim_group,
       app_week AS week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM base
WHERE global_limit IS NOT NULL
GROUP BY 1, 2, 3

;

-- ============================================================
-- 最后：查询全部结果（导出到CSV粘进网页）
-- ============================================================
SELECT * FROM mx.tmp_effect_decomp_all_dims
ORDER BY dim_name, week, dim_group;


-- ============================================================
-- 统一贡献度分解（Kitagawa 效应分解）
-- 口径：滚动相邻周 × 笔数/金额双口径 × 全部维度
-- 输出：各 (周对, 维度, 分组) 的个体/结构/交互效应 + 对总变化的贡献占比
-- 说明：rate 为逾期率，个体=基期占比×率差，结构=基期率×占比差，
--       交互=率差×占比差；三者之和 = 该分组对总体率变化的贡献
-- ============================================================
WITH
-- 所有出现的周
weeks AS (
    SELECT DISTINCT week
    FROM mx.tmp_effect_decomp_all_dims
),
-- 滚动相邻周对（LAG 自动配对）
week_pairs AS (
    SELECT
        LAG(week) OVER (ORDER BY week) AS base_week,
        week AS comp_week
    FROM weeks
),
pairs AS (
    SELECT base_week, comp_week
    FROM week_pairs
    WHERE base_week IS NOT NULL
),
-- 每个 (周对, 维度, 分组) 的基期/对比期分子分母，双口径长表
cell AS (
    -- 笔数口径
    SELECT
        p.base_week,
        p.comp_week,
        d.dim_name,
        d.dim_group,
        '笔数' AS basis,
        SUM(CASE WHEN d.week = p.base_week THEN d.billed_cnt  ELSE 0 END) AS base_n,
        SUM(CASE WHEN d.week = p.base_week THEN d.overdue_cnt ELSE 0 END) AS base_o,
        SUM(CASE WHEN d.week = p.comp_week THEN d.billed_cnt  ELSE 0 END) AS comp_n,
        SUM(CASE WHEN d.week = p.comp_week THEN d.overdue_cnt ELSE 0 END) AS comp_o
    FROM pairs p
    JOIN mx.tmp_effect_decomp_all_dims d
      ON (d.week = p.base_week OR d.week = p.comp_week)
    GROUP BY p.base_week, p.comp_week, d.dim_name, d.dim_group

    UNION ALL

    -- 金额口径
    SELECT
        p.base_week,
        p.comp_week,
        d.dim_name,
        d.dim_group,
        '金额' AS basis,
        SUM(CASE WHEN d.week = p.base_week THEN d.billed_amt  ELSE 0 END) AS base_n,
        SUM(CASE WHEN d.week = p.base_week THEN d.overdue_amt ELSE 0 END) AS base_o,
        SUM(CASE WHEN d.week = p.comp_week THEN d.billed_amt  ELSE 0 END) AS comp_n,
        SUM(CASE WHEN d.week = p.comp_week THEN d.overdue_amt ELSE 0 END) AS comp_o
    FROM pairs p
    JOIN mx.tmp_effect_decomp_all_dims d
      ON (d.week = p.base_week OR d.week = p.comp_week)
    GROUP BY p.base_week, p.comp_week, d.dim_name, d.dim_group
),
-- 每个 (周对, 口径) 的总出账（分母）
totals AS (
    SELECT
        base_week,
        comp_week,
        basis,
        SUM(base_n) AS base_total_n,
        SUM(comp_n) AS comp_total_n
    FROM cell
    GROUP BY 1, 2, 3
),
-- 各分组效应
effects AS (
    SELECT
        c.base_week,
        c.comp_week,
        c.dim_name,
        c.dim_group,
        c.basis,
        c.base_n,
        c.comp_n,
        c.base_o,
        c.comp_o,
        COALESCE(c.base_o * 1.0 / NULLIF(c.base_n, 0), 0) AS base_rate,
        COALESCE(c.comp_o * 1.0 / NULLIF(c.comp_n, 0), 0) AS comp_rate,
        c.base_n * 1.0 / NULLIF(t.base_total_n, 0) AS base_share,
        c.comp_n * 1.0 / NULLIF(t.comp_total_n, 0) AS comp_share,
        -- 个体效应 = 基期占比 × (对比期率 - 基期率)
        c.base_n * 1.0 / NULLIF(t.base_total_n, 0)
            * (COALESCE(c.comp_o * 1.0 / NULLIF(c.comp_n, 0), 0)
               - COALESCE(c.base_o * 1.0 / NULLIF(c.base_n, 0), 0)) AS individual_effect,
        -- 结构效应 = 基期率 × (对比期占比 - 基期占比)
        COALESCE(c.base_o * 1.0 / NULLIF(c.base_n, 0), 0)
            * (c.comp_n * 1.0 / NULLIF(t.comp_total_n, 0)
               - c.base_n * 1.0 / NULLIF(t.base_total_n, 0)) AS structural_effect,
        -- 交互效应 = 率差 × 占比差
        (COALESCE(c.comp_o * 1.0 / NULLIF(c.comp_n, 0), 0)
         - COALESCE(c.base_o * 1.0 / NULLIF(c.base_n, 0), 0))
            * (c.comp_n * 1.0 / NULLIF(t.comp_total_n, 0)
               - c.base_n * 1.0 / NULLIF(t.base_total_n, 0)) AS interaction_effect
    FROM cell c
    JOIN totals t
      ON t.base_week = c.base_week
     AND t.comp_week = c.comp_week
     AND t.basis     = c.basis
),
-- 每个 (周对, 维度, 口径) 的总变化
tot_change AS (
    SELECT
        base_week,
        comp_week,
        dim_name,
        basis,
        SUM(individual_effect + structural_effect + interaction_effect) AS total_change
    FROM effects
    GROUP BY 1, 2, 3, 4
)
SELECT
    e.base_week,
    e.comp_week,
    e.dim_name,
    e.dim_group,
    e.basis,
    round(e.base_n, 0) AS base_n,
    round(e.comp_n, 0) AS comp_n,
    round(e.base_rate * 100, 2) AS base_rate_pct,
    round(e.comp_rate * 100, 2) AS comp_rate_pct,
    round((e.comp_rate - e.base_rate) * 100, 2) AS rate_diff_pct,
    round(e.base_share * 100, 2) AS base_share_pct,
    round(e.comp_share * 100, 2) AS comp_share_pct,
    -- 三类效应（百分点）
    round(e.individual_effect * 100, 4) AS individual_effect_pct,
    round(e.structural_effect * 100, 4) AS structural_effect_pct,
    round(e.interaction_effect * 100, 4) AS interaction_effect_pct,
    -- 对总变化的贡献占比
    case when tc.total_change <> 0
         then round(e.individual_effect / tc.total_change * 100, 2)
         else 0 end AS individual_contrib_pct,
    case when tc.total_change <> 0
         then round(e.structural_effect / tc.total_change * 100, 2)
         else 0 end AS structural_contrib_pct,
    case when tc.total_change <> 0
         then round(e.interaction_effect / tc.total_change * 100, 2)
         else 0 end AS interaction_contrib_pct
FROM effects e
JOIN tot_change tc
  ON tc.base_week = e.base_week
 AND tc.comp_week = e.comp_week
 AND tc.dim_name  = e.dim_name
 AND tc.basis     = e.basis
ORDER BY e.base_week, e.comp_week, e.dim_name,
         (e.individual_effect + e.structural_effect + e.interaction_effect) DESC;

    