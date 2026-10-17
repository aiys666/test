SELECT
    -- ==================== 分组维度（f 表） ====================
    f.biz_id,
    f.mid,
    f.app_time,
    f.apply_time,
    is_reloan,
    android_oldcust_maincreditlevel_charge_v5_3,
    android_oldCust_mainCreditLevel_charge_V6_1,
    product_level,
    product_name_new,
    v3_flag,
    loan_cycle,            -- 总期限天数（如21天）
    source,
    app_group,
    issue_month,
    issue_week,
    issue_date,
    dd.exchange_rate_to_dollar,

    -- ==================== 产品标签拆解（基于 product_name_new 计算） ====================
    -- 前砍比例：非E类取第4段，E类为0
    CASE
        WHEN SPLIT_PART(product_name_new, '_', 1) = 'E' THEN 0
        ELSE CAST(SPLIT_PART(product_name_new, '_', 4) AS DOUBLE) / 100
    END AS product_haircut_rate,

    -- 含税总利息比例：非E类=后收利息比例×1.16，E类=日息率×总天数
    CASE
        WHEN SPLIT_PART(product_name_new, '_', 1) = 'E'
        THEN CAST(SPLIT_PART(product_name_new, '_', 4) AS DOUBLE) / 10 * loan_cycle / 100
        ELSE CAST(SPLIT_PART(product_name_new, '_', 5) AS DOUBLE) / 100 * 1.16
    END AS product_interest_rate_incl_tax,

    -- 不含税总利息比例：非E类=后收利息比例，E类=日息率×总天数÷1.16
    CASE
        WHEN SPLIT_PART(product_name_new, '_', 1) = 'E'
        THEN CAST(SPLIT_PART(product_name_new, '_', 4) AS DOUBLE) / 10 * loan_cycle / 100 / 1.16
        ELSE CAST(SPLIT_PART(product_name_new, '_', 5) AS DOUBLE) / 100
    END AS product_interest_rate_excl_tax,

    -- ==================== y 表明细字段（评级/额度，直接取出） ====================
    -- ---- V6_1 子分（a: yj_test_table_250225） ----
    y.android_oldCust_midCreditLevel_charge_V6_1,
    y.android_oldCust_overdue_subscore_charge_V6_1,
    y.android_oldCust_behavior_subscore_charge_V6_1,
    y.android_oldCust_fraud_subscore_charge_V6_1,
    y.android_oldCust_apply_subscore_charge_V6_1,
    y.android_oldCust_voting_score_charge_V6_1,
    y.android_oldCust_rule_score_charge_V6_1,
    y.android_oldCust_income_subscore_charge_V6_1,
    -- ---- V5_3 子分（a 表） ----
    y.android_oldcust_rulescore_charge_v5_3,
    y.android_oldcust_votescore_charge_v5_3,
    y.android_oldcust_midcreditlevel_charge_v5_3,
    -- ---- 历史逾期天数（a 表） ----
    y.max_ovd_days_all,
    y.max_overdue_day_30d_all,
    -- ---- 结清/额度信息（b: darren_jieqing_dt_table） ----
    y.settle_time,
    y.last_credit_amount,
    y.credit_amount,
    -- ---- 结清时评级（b 表，加 jq 前缀以区分） ----
    y.jq_android_oldcust_maincreditlevel_charge_v5_3,
    y.jq_android_oldCust_mainCreditLevel_charge_V6_1,
    y.first_settle_reloan_creditlvl_V5_3,
    y.first_settle_reloan_creditlvl_V6_1,
    -- ---- 额度/cap 相关（b 表） ----
    y.champion_global_limit,
    y.jq_global_limit,
    y.champion_fd_grantcredit_global_amount_uncapped,
    y.champion_fd_grantcredit_global_amount_add_cap,
    y.if_grantcredit_global_amount_add_cap, -- 是否触碰单日cap: champion_fd_grantcredit_global_amount_uncapped > champion_fd_grantcredit_global_amount_add_cap 时为1
    y.if_global_limit_add_cap,              -- 是否触碰全局gap: champion_fd_grantcredit_global_amount_add_cap > champion_global_limit 时为1

    -- ==================== 基础金额/笔数（明细，不聚合） ====================
    contract_amount,
    f.haircut_amount,          -- 前砍费
    amount,                     -- 到手金额
    should_interest,
    if_issue,

    -- ==================== 本金 (T0, T3, T7) 期限1 ====================
    t0_should_capit_1 AS t0_should_amt_1,
    t0_overdue_capit_1 AS t0_overdue_amount_1,
    t3_should_capit_1 AS t3_should_amt_1,
    t3_overdue_capit_1 AS t3_overdue_amount_1,
    t7_should_capit_1 AS t7_should_amt_1,
    t7_overdue_capit_1 AS t7_overdue_amount_1,

    -- 本息 (T0, T3, T7) 期限1
    t0_should_amt_1 AS t0_should_amt_interest_1,
    t0_overdue_amount_1 AS t0_overdue_amt_intere_1,
    t3_should_amt_1 AS t3_should_amt_interest_1,
    t3_overdue_amount_1 AS t3_overdue_amt_intere_1,
    t7_should_amt_1 AS t7_should_amt_interest_1,
    t7_overdue_amount_1 AS t7_overdue_amt_intere_1,

    -- ==================== 本金 期限2 ====================
    t0_should_capit_2 AS t0_should_amt_2,
    t0_overdue_capit_2 AS t0_overdue_amount_2,
    t3_should_capit_2 AS t3_should_amt_2,
    t3_overdue_capit_2 AS t3_overdue_amount_2,
    t7_should_capit_2 AS t7_should_amt_2,
    t7_overdue_capit_2 AS t7_overdue_amount_2,

    -- 本息 期限2
    t0_should_amt_2 AS t0_should_amt_interest_2,
    t0_overdue_amount_2 AS t0_overdue_amt_intere_2,
    t3_should_amt_2 AS t3_should_amt_interest_2,
    t3_overdue_amount_2 AS t3_overdue_amt_intere_2,
    t7_should_amt_2 AS t7_should_amt_interest_2,
    t7_overdue_amount_2 AS t7_overdue_amt_intere_2,

    -- ==================== 本金 期限3 ====================
    t0_should_capit_3 AS t0_should_amt_3,
    t0_overdue_capit_3 AS t0_overdue_amount_3,
    t3_should_capit_3 AS t3_should_amt_3,
    t3_overdue_capit_3 AS t3_overdue_amount_3,
    t7_should_capit_3 AS t7_should_amt_3,
    t7_overdue_capit_3 AS t7_overdue_amount_3,

    -- 本息 期限3
    t0_should_amt_3 AS t0_should_amt_interest_3,
    t0_overdue_amount_3 AS t0_overdue_amt_intere_3,
    t3_should_amt_3 AS t3_should_amt_interest_3,
    t3_overdue_amount_3 AS t3_overdue_amt_intere_3,
    t7_should_amt_3 AS t7_should_amt_interest_3,
    t7_overdue_amount_3 AS t7_overdue_amt_intere_3,

    -- ==================== 本金 期限4 ====================
    t0_should_capit_4 AS t0_should_amt_4,
    t0_overdue_capit_4 AS t0_overdue_amount_4,
    t3_should_capit_4 AS t3_should_amt_4,
    t3_overdue_capit_4 AS t3_overdue_amount_4,
    t7_should_capit_4 AS t7_should_amt_4,
    t7_overdue_capit_4 AS t7_overdue_amount_4,

    -- 本息 期限4
    t0_should_amt_4 AS t0_should_amt_interest_4,
    t0_overdue_amount_4 AS t0_overdue_amt_intere_4,
    t3_should_amt_4 AS t3_should_amt_interest_4,
    t3_overdue_amount_4 AS t3_overdue_amt_intere_4,
    t7_should_amt_4 AS t7_should_amt_interest_4,
    t7_overdue_amount_4 AS t7_overdue_amt_intere_4,

    -- ==================== 应还利息 (should_interest) 期限1~4 ====================
    -- 期限1
    t0_should_interest_1,
    t3_should_interest_1,
    t7_should_interest_1,
    -- 期限2
    t0_should_interest_2,
    t3_should_interest_2,
    t7_should_interest_2,
    -- 期限3
    t0_should_interest_3,
    t3_should_interest_3,
    t7_should_interest_3,
    -- 期限4
    t0_should_interest_4,
    t3_should_interest_4,
    t7_should_interest_4,

    -- ==================== 逾期利息 (overdue_interest) 期限1~4 ====================
    -- 期限1
    t0_overdue_interest_1,
    t3_overdue_interest_1,
    t7_overdue_interest_1,
    -- 期限2
    t0_overdue_interest_2,
    t3_overdue_interest_2,
    t7_overdue_interest_2,
    -- 期限3
    t0_overdue_interest_3,
    t3_overdue_interest_3,
    t7_overdue_interest_3,
    -- 期限4
    t0_overdue_interest_4,
    t3_overdue_interest_4,
    t7_overdue_interest_4,

    -- ==================== 优惠券减免 ====================
    t0_coupon_substract_1,
    t0_coupon_substract_2,
    t0_coupon_substract_3,
    t0_coupon_substract_4,

    t1_coupon_substract_1,
    t1_coupon_substract_2,
    t1_coupon_substract_3,
    t1_coupon_substract_4,

    t2_coupon_substract_1,
    t2_coupon_substract_2,
    t2_coupon_substract_3,
    t2_coupon_substract_4,

    t3_coupon_substract_1,
    t3_coupon_substract_2,
    t3_coupon_substract_3,
    t3_coupon_substract_4,

    t7_coupon_substract_1,
    t7_coupon_substract_2,
    t7_coupon_substract_3,
    t7_coupon_substract_4,

    -- ==================== 窗口指标 ====================
    is_t0_window_1,
    is_t7_window_1,
    is_t3_window_1,

    is_t0_window_2,
    is_t3_window_2,
    is_t7_window_2,

    is_t0_window_3,
    is_t3_window_3,
    is_t7_window_3,

    is_t0_window_4,
    is_t3_window_4,
    is_t7_window_4,

    -- ==================== 逾期笔数 ====================
    -- 期限1
    is_t0_overdue_1 AS overdue_t0_1,
    is_t3_overdue_1 AS overdue_t3_1,
    is_t7_overdue_1 AS overdue_t7_1,
    -- 期限2
    is_t0_overdue_2 AS overdue_t0_2,
    is_t3_overdue_2 AS overdue_t3_2,
    is_t7_overdue_2 AS overdue_t7_2,
    -- 期限3
    is_t0_overdue_3 AS overdue_t0_3,
    is_t3_overdue_3 AS overdue_t3_3,
    is_t7_overdue_3 AS overdue_t7_3,
    -- 期限4
    is_t0_overdue_4 AS overdue_t0_4,
    is_t3_overdue_4 AS overdue_t3_4,
    is_t7_overdue_4 AS overdue_t7_4,

    -- -- ==================== 通过率相关指标 ====================
    -- if_shou_anti_fraud_passed,
    -- if_in_shou_anti_fraud,
    -- if_shou_anti_fraud_weak_passed,
    -- if_in_shou_anti_fraud_weak,
    -- IF(LOWER(source) = 'ios', if_shou_anti_fraud_weak_passed, if_shou_model_passed) AS if_shou_model_passed,
    -- IF(LOWER(source) = 'ios', if_shou_anti_fraud_weak_passed, if_in_shou_model) AS if_in_shou_model,
    -- if_in_sx,
    -- if_sx_passed,
    -- COALESCE(if_in_shou_normal_check, 0) AS if_in_shou_normal_check,
    -- COALESCE(if_in_shou_normal_rule_check, 0) AS if_in_shou_normal_rule_check,
    -- COALESCE(if_shou_normal_rule_check_passed, 0) AS if_shou_normal_rule_check_passed,
    -- COALESCE(if_in_sd_ai, 0) AS if_in_sd_ai,
    -- COALESCE(if_shou_ai_passed, 0) AS if_shou_ai_passed,
    -- if_in_shou_external_data,
    -- if_shou_external_data_passed,

    -- ==================== 其他指标（明细，不聚合） ====================
    CASE WHEN should_amount != 0 AND should_amount IS NOT NULL THEN 1 ELSE 0 END AS total_issue_cnt,
    CASE WHEN if_issue = 1 THEN CAST(grantcredit_7d_amount AS DOUBLE) ELSE 0 END AS total_grant_amount,
    CASE WHEN if_issue = 1 THEN CAST(credit_amount_sx AS DOUBLE) ELSE 0 END AS total_credit_amount,
    CASE
        WHEN product_level IN ('B_07_02_00_50','B_07_04_00_60','B_07_02_20_30','B_07_03_00_60','B_07_03_20_40','B_07_04_20_40')
            AND if_issue = 1
        THEN CAST(SUBSTR(product_level, 4, 1) AS DOUBLE) * CAST(SUBSTR(product_level, 7, 1) AS DOUBLE)
        ELSE 0
    END AS internal_sum,

    -- ==================== 比率指标（明细行级别计算） ====================
    -- 前砍比率
    haircut_amount / contract_amount AS haircut_rate,
    -- 含税总利息率 = 底表值
    should_interest / contract_amount AS interest_rate_incl_tax,
    -- 不含税总利息率 = 含税总利息 ÷ 1.16
    should_interest / 1.16 / contract_amount AS interest_rate_excl_tax,
    -- 含税日息
    should_interest / contract_amount / loan_cycle AS daily_interest_rate_incl_tax,
    -- 不含税日息
    should_interest / 1.16 / contract_amount / loan_cycle AS daily_interest_rate_excl_tax

FROM mx.wxs_application_funnel f
LEFT JOIN (
    SELECT
        a.mid,
        a.biz_id,
        a.product_name_new,
        a.app_time,
        a.v3_flag,
        a.android_oldCust_midCreditLevel_charge_V6_1,
        a.android_oldCust_mainCreditLevel_charge_V6_1,
        a.android_oldCust_overdue_subscore_charge_V6_1,
        a.android_oldCust_behavior_subscore_charge_V6_1,
        a.android_oldCust_fraud_subscore_charge_V6_1,
        a.android_oldCust_apply_subscore_charge_V6_1,
        a.android_oldCust_voting_score_charge_V6_1,
        a.android_oldCust_rule_score_charge_V6_1,
        a.android_oldCust_income_subscore_charge_V6_1,
        a.android_oldcust_rulescore_charge_v5_3,
        a.android_oldcust_votescore_charge_v5_3,
        a.android_oldcust_maincreditlevel_charge_v5_3,
        a.android_oldcust_midcreditlevel_charge_v5_3,
        a.max_ovd_days_all,
        a.max_overdue_day_30d_all,
        b.settle_time,
        b.last_credit_amount,
        b.credit_amount,
        b.android_oldcust_maincreditlevel_charge_v5_3 AS jq_android_oldcust_maincreditlevel_charge_v5_3,
        b.android_oldCust_mainCreditLevel_charge_V6_1 AS jq_android_oldCust_mainCreditLevel_charge_V6_1,
        b.first_settle_reloan_creditlvl_V5_3,
        b.first_settle_reloan_creditlvl_V6_1,
        b.champion_global_limit,
        b.jq_global_limit,
        b.champion_fd_grantcredit_global_amount_uncapped,
        b.champion_fd_grantcredit_global_amount_add_cap,
        b.if_grantcredit_global_amount_add_cap, -- 是否触碰单日cap
        b.if_global_limit_add_cap               -- 是否触碰全局gap
    FROM mx.yj_test_table_250225 a
    LEFT JOIN mx.darren_jieqing_dt_table b
        ON a.biz_id = b.biz_id
        -- AND b.mid = 1040160066607324          -- 修复: 移到ON条件, 避免LEFT JOIN变INNER JOIN丢失a表数据
    WHERE a.app_time >= DATE '2026-08-20'
) y ON f.biz_id = y.biz_id
LEFT JOIN dim.dim_exchange_rate_cost dd
    ON DATE(DATE_PARSE(dd.month_id, '%Y%m')) = DATE(DATE_FORMAT(f.release_time, '%Y-%m-01'))
    AND dd.account_currency = 'MXN'
WHERE 1=1
    -- and f.if_issue = 1
    AND f.is_reloan = 'old'
    AND f.app_time >= CAST('2026-08-20 00:00:00.000' AS TIMESTAMP)
    -- AND f.mid = 1040160066607324
ORDER BY f.app_time 
 limit 100000
;;




------------ excel中使用的代码；
SELECT 
    -- 分组维度
    is_reloan,
    android_oldcust_maincreditlevel_charge_v5_3,
    android_oldCust_mainCreditLevel_charge_V6_1,
    max_ovd_30d_bucket,
    product_level,
    product_name_new, 
    other_app_has_overdue_tag,other_app_has_overdue_interval_tag,emcontact_curr_ovd_cnt_all_test_flag,
    v3_flag,
    loan_cycle,            -- 总期限天数（如21天） 
    source,
    app_group,
	app_month,
    app_week,
    app_date,
    case
        when app_date >= date '2026-08-20' and app_date <= date '2026-09-03' then 'phase1_V6_30%_V5_70%'
        when app_date >= date '2026-09-04' and app_date <= date '2026-09-14' then 'phase2_V6_70%_V5_30%'
        when app_date >= date '2026-09-15' then 'phase3_V6_50%_V5_50%'
        else 'pre_phase1_20260820前' -- 灰度上线前基线组
    end as gray_phase,  
     v3_flag_huidu,
  
    issue_month,
    issue_week,
    issue_date,
    dd.exchange_rate_to_dollar,


    -- ==================== 新增：产品标签拆解 ====================
    -- 前砍比例：非E类取第4段，E类为0
    CASE 
        WHEN SPLIT_PART(product_name_new, '_', 1) = 'E' THEN 0
        ELSE CAST(SPLIT_PART(product_name_new, '_', 4) AS DOUBLE) / 100 
    END AS product_haircut_rate,
    
    -- 含税总利息比例：非E类=后收利息比例×1.16，E类=日息率×总天数
    CASE 
        WHEN SPLIT_PART(product_name_new, '_', 1) = 'E' 
        THEN CAST(SPLIT_PART(product_name_new, '_', 4) AS DOUBLE) / 10 * loan_cycle / 100
        ELSE CAST(SPLIT_PART(product_name_new, '_', 5) AS DOUBLE) / 100 * 1.16
    END AS product_interest_rate_incl_tax,
    
    -- 不含税总利息比例：非E类=后收利息比例，E类=日息率×总天数÷1.16
    CASE 
        WHEN SPLIT_PART(product_name_new, '_', 1) = 'E' 
        THEN CAST(SPLIT_PART(product_name_new, '_', 4) AS DOUBLE) / 10 * loan_cycle / 100 / 1.16
        ELSE CAST(SPLIT_PART(product_name_new, '_', 5) AS DOUBLE) / 100
    END AS product_interest_rate_excl_tax,

    -- ==================== 基础汇总 ====================
    SUM(contract_amount) AS contract_amount,
    SUM(loan_cycle*contract_amount) AS loan_cycle_amount,
    SUM(f.haircut_amount) AS haircut_amount,          -- 前砍费
    SUM(amount) AS amount,                            -- 到手金额
    SUM(should_interest) AS should_interest,
    SUM(if_issue) AS issue_cnt,
    SUM(if_app) AS if_app,
    

    -- ==================== 本金 (T0, T3, T7) 期限1 ====================
    SUM(t0_should_capit_1) AS t0_should_amt_1,
    SUM(t0_overdue_capit_1) AS t0_overdue_amount_1,
    SUM(t3_should_capit_1) AS t3_should_amt_1,
    SUM(t3_overdue_capit_1) AS t3_overdue_amount_1,
    SUM(t7_should_capit_1) AS t7_should_amt_1,
    SUM(t7_overdue_capit_1) AS t7_overdue_amount_1,

    -- 本息 (T0, T3, T7) 期限1
    SUM(t0_should_amt_1) AS t0_should_amt_interest_1,
    SUM(t0_overdue_amount_1) AS t0_overdue_amt_intere_1,
    SUM(t3_should_amt_1) AS t3_should_amt_interest_1,
    SUM(t3_overdue_amount_1) AS t3_overdue_amt_intere_1,
    SUM(t7_should_amt_1) AS t7_should_amt_interest_1,
    SUM(t7_overdue_amount_1) AS t7_overdue_amt_intere_1,

    -- ==================== 本金 期限2 ====================
    SUM(t0_should_capit_2) AS t0_should_amt_2,
    SUM(t0_overdue_capit_2) AS t0_overdue_amount_2,
    SUM(t3_should_capit_2) AS t3_should_amt_2,
    SUM(t3_overdue_capit_2) AS t3_overdue_amount_2,
    SUM(t7_should_capit_2) AS t7_should_amt_2,
    SUM(t7_overdue_capit_2) AS t7_overdue_amount_2,

    -- 本息 期限2
    SUM(t0_should_amt_2) AS t0_should_amt_interest_2,
    SUM(t0_overdue_amount_2) AS t0_overdue_amt_intere_2,
    SUM(t3_should_amt_2) AS t3_should_amt_interest_2,
    SUM(t3_overdue_amount_2) AS t3_overdue_amt_intere_2,
    SUM(t7_should_amt_2) AS t7_should_amt_interest_2,
    SUM(t7_overdue_amount_2) AS t7_overdue_amt_intere_2,

    -- ==================== 本金 期限3 ====================
    SUM(t0_should_capit_3) AS t0_should_amt_3,
    SUM(t0_overdue_capit_3) AS t0_overdue_amount_3,
    SUM(t3_should_capit_3) AS t3_should_amt_3,
    SUM(t3_overdue_capit_3) AS t3_overdue_amount_3,
    SUM(t7_should_capit_3) AS t7_should_amt_3,
    SUM(t7_overdue_capit_3) AS t7_overdue_amount_3,

    -- 本息 期限3
    SUM(t0_should_amt_3) AS t0_should_amt_interest_3,
    SUM(t0_overdue_amount_3) AS t0_overdue_amt_intere_3,
    SUM(t3_should_amt_3) AS t3_should_amt_interest_3,
    SUM(t3_overdue_amount_3) AS t3_overdue_amt_intere_3,
    SUM(t7_should_amt_3) AS t7_should_amt_interest_3,
    SUM(t7_overdue_amount_3) AS t7_overdue_amt_intere_3,

    -- ==================== 本金 期限4 ====================
    SUM(t0_should_capit_4) AS t0_should_amt_4,
    SUM(t0_overdue_capit_4) AS t0_overdue_amount_4,
    SUM(t3_should_capit_4) AS t3_should_amt_4,
    SUM(t3_overdue_capit_4) AS t3_overdue_amount_4,
    SUM(t7_should_capit_4) AS t7_should_amt_4,
    SUM(t7_overdue_capit_4) AS t7_overdue_amount_4,

    -- 本息 期限4
    SUM(t0_should_amt_4) AS t0_should_amt_interest_4,
    SUM(t0_overdue_amount_4) AS t0_overdue_amt_intere_4,
    SUM(t3_should_amt_4) AS t3_should_amt_interest_4,
    SUM(t3_overdue_amount_4) AS t3_overdue_amt_intere_4,
    SUM(t7_should_amt_4) AS t7_should_amt_interest_4,
    SUM(t7_overdue_amount_4) AS t7_overdue_amt_intere_4,

    -- ==================== 应还利息 (should_interest) 期限1~4 ====================
    -- 期限1
    SUM(t0_should_interest_1) AS t0_should_interest_1,
    SUM(t3_should_interest_1) AS t3_should_interest_1,
    SUM(t7_should_interest_1) AS t7_should_interest_1,

    -- 期限2
    SUM(t0_should_interest_2) AS t0_should_interest_2,
    SUM(t3_should_interest_2) AS t3_should_interest_2,
    SUM(t7_should_interest_2) AS t7_should_interest_2,

    -- 期限3
    SUM(t0_should_interest_3) AS t0_should_interest_3,
    SUM(t3_should_interest_3) AS t3_should_interest_3,
    SUM(t7_should_interest_3) AS t7_should_interest_3,

    -- 期限4
    SUM(t0_should_interest_4) AS t0_should_interest_4,
    SUM(t3_should_interest_4) AS t3_should_interest_4,
    SUM(t7_should_interest_4) AS t7_should_interest_4,

    -- ==================== 逾期利息 (overdue_interest) 期限1~4 ====================
    -- 期限1
    SUM(t0_overdue_interest_1) AS t0_overdue_interest_1,
    SUM(t3_overdue_interest_1) AS t3_overdue_interest_1,
    SUM(t7_overdue_interest_1) AS t7_overdue_interest_1,

    -- 期限2
    SUM(t0_overdue_interest_2) AS t0_overdue_interest_2,
    SUM(t3_overdue_interest_2) AS t3_overdue_interest_2,
    SUM(t7_overdue_interest_2) AS t7_overdue_interest_2,

    -- 期限3
    SUM(t0_overdue_interest_3) AS t0_overdue_interest_3,
    SUM(t3_overdue_interest_3) AS t3_overdue_interest_3,
    SUM(t7_overdue_interest_3) AS t7_overdue_interest_3,

    -- 期限4
    SUM(t0_overdue_interest_4) AS t0_overdue_interest_4,
    SUM(t3_overdue_interest_4) AS t3_overdue_interest_4,
    SUM(t7_overdue_interest_4) AS t7_overdue_interest_4,

    -- ==================== 优惠券减免 ====================
    SUM(t0_coupon_substract_1) AS t0_coupon_substract_1,
    SUM(t0_coupon_substract_2) AS t0_coupon_substract_2,
    SUM(t0_coupon_substract_3) AS t0_coupon_substract_3,
    SUM(t0_coupon_substract_4) AS t0_coupon_substract_4,

    SUM(t1_coupon_substract_1) AS t1_coupon_substract_1,
    SUM(t1_coupon_substract_2) AS t1_coupon_substract_2,
    SUM(t1_coupon_substract_3) AS t1_coupon_substract_3,
    SUM(t1_coupon_substract_4) AS t1_coupon_substract_4,

    SUM(t2_coupon_substract_1) AS t2_coupon_substract_1,
    SUM(t2_coupon_substract_2) AS t2_coupon_substract_2,
    SUM(t2_coupon_substract_3) AS t2_coupon_substract_3,
    SUM(t2_coupon_substract_4) AS t2_coupon_substract_4,

    SUM(t3_coupon_substract_1) AS t3_coupon_substract_1,
    SUM(t3_coupon_substract_2) AS t3_coupon_substract_2,
    SUM(t3_coupon_substract_3) AS t3_coupon_substract_3,
    SUM(t3_coupon_substract_4) AS t3_coupon_substract_4,

    SUM(t7_coupon_substract_1) AS t7_coupon_substract_1,
    SUM(t7_coupon_substract_2) AS t7_coupon_substract_2,
    SUM(t7_coupon_substract_3) AS t7_coupon_substract_3,
    SUM(t7_coupon_substract_4) AS t7_coupon_substract_4,

    -- ==================== 窗口指标 ====================
    SUM(is_t0_window_1) AS is_t0_window_1,
    SUM(is_t7_window_1) AS is_t7_window_1,
    SUM(is_t3_window_1) AS is_t3_window_1,

    SUM(is_t0_window_2) AS is_t0_window_2,
    SUM(is_t3_window_2) AS is_t3_window_2,
    SUM(is_t7_window_2) AS is_t7_window_2,

    SUM(is_t0_window_3) AS is_t0_window_3,
    SUM(is_t3_window_3) AS is_t3_window_3,
    SUM(is_t7_window_3) AS is_t7_window_3,

    SUM(is_t0_window_4) AS is_t0_window_4,
    SUM(is_t3_window_4) AS is_t3_window_4,
    SUM(is_t7_window_4) AS is_t7_window_4,

    -- ==================== 逾期笔数 ====================
    -- 期限1
    SUM(is_t0_overdue_1) AS overdue_t0_1,
    SUM(is_t3_overdue_1) AS overdue_t3_1,
    SUM(is_t7_overdue_1) AS overdue_t7_1,
    -- 期限2
    SUM(is_t0_overdue_2) AS overdue_t0_2,
    SUM(is_t3_overdue_2) AS overdue_t3_2,
    SUM(is_t7_overdue_2) AS overdue_t7_2,
    -- 期限3
    SUM(is_t0_overdue_3) AS overdue_t0_3,
    SUM(is_t3_overdue_3) AS overdue_t3_3,
    SUM(is_t7_overdue_3) AS overdue_t7_3,
    -- 期限4
    SUM(is_t0_overdue_4) AS overdue_t0_4,
    SUM(is_t3_overdue_4) AS overdue_t3_4,
    SUM(is_t7_overdue_4) AS overdue_t7_4,

		
----通过率
    -- sum(if_shou_anti_fraud_passed) as if_shou_anti_fraud_passed,
    -- sum(if_in_shou_anti_fraud) as if_in_shou_anti_fraud,
    -- sum(if_shou_anti_fraud_weak_passed) as if_shou_anti_fraud_weak_passed,
    -- sum(if_in_shou_anti_fraud_weak) as if_in_shou_anti_fraud_weak,
    -- sum(if(lower(source)= 'ios',if_shou_anti_fraud_weak_passed,if_shou_model_passed)) as if_shou_model_passed,
    -- sum(if(lower(source)= 'ios',if_shou_anti_fraud_weak_passed,if_in_shou_model)) as if_in_shou_model,
  sum(if_in_sx) as if_in_sx,
  sum(if_sx_passed) as if_sx_passed,
  sum(if_in_sx_24h) as if_in_sx_24h,
  sum(if_sx_passed_24h) as if_sx_passed_24h, 
  sum(if_in_sx_120h) as if_in_sx_120h,
  sum(if_sx_passed_120h) as if_sx_passed_120h, 
--   sum(case when if_in_shou_normal_check is null then 0 else if_in_shou_normal_check end) as if_in_shou_normal_check,
--     sum(case when if_in_shou_normal_rule_check is null then 0 else if_in_shou_normal_rule_check end) as if_in_shou_normal_rule_check,  
--   sum(case when if_shou_normal_rule_check_passed is null then 0 else if_shou_normal_rule_check_passed end) as if_shou_normal_rule_check_passed,  
--   sum(case when if_in_sd_ai is null then 0 else if_in_sd_ai end) as if_in_sd_ai,  
--   sum(case when if_shou_ai_passed is null then 0 else if_shou_ai_passed end) as if_shou_ai_passed,    
--     sum(if_in_shou_external_data) as if_in_shou_external_data,
--     sum(if_shou_external_data_passed) as if_shou_external_data_passed, 
 

    -- ==================== 其他汇总指标 ====================
    COUNT(IF(should_amount != 0 AND should_amount IS NOT NULL, f.biz_id, NULL)) AS total_issue_cnt,
    SUM(CASE WHEN if_issue = 1 THEN CAST(grantcredit_7d_amount AS DOUBLE) ELSE 0 END) AS total_grant_amount,
    SUM(CASE WHEN if_issue = 1 THEN CAST(credit_amount_sx AS DOUBLE) ELSE 0 END) AS total_credit_amount,
    SUM(CASE 
        WHEN product_level IN ('B_07_02_00_50','B_07_04_00_60','B_07_02_20_30','B_07_03_00_60','B_07_03_20_40','B_07_04_20_40') 
        AND if_issue = 1 
        THEN CAST(SUBSTR(product_level, 4, 1) AS DOUBLE) * CAST(SUBSTR(product_level, 7, 1) AS DOUBLE) 
        ELSE 0 
    END) AS internal_sum,
    -- 前砍比率 = 底表值 
    SUM(haircut_amount) / SUM(contract_amount) AS haircut_rate,
    -- ==================== 方式2：含税/不含税利息（底表含税，墨西哥税率16%） ====================
    -- 含税总利息率 = 底表值（E类和非E类都一样）
    SUM(should_interest) / SUM(contract_amount) AS  interest_rate_incl_tax,
    
    -- 不含税总利息率 = 含税总利息 ÷ 1.16
    SUM(should_interest) / 1.16 / SUM(contract_amount) AS  interest_rate_excl_tax,
    
    -- 含税日息 = 含税总利息 / 合同总额 / 总天数
    SUM(should_interest) / SUM(contract_amount) / loan_cycle AS daily_interest_rate_incl_tax,
    
    -- 不含税日息 = 不含税总利息 / 合同总额 / 总天数
    SUM(should_interest) / 1.16 / SUM(contract_amount) / loan_cycle AS daily_interest_rate_excl_tax

FROM mx.wxs_application_funnel f
LEFT JOIN (
    SELECT 
        biz_id,
        product_name_new,
        v3_flag,v3_flag_huidu,
        other_app_has_overdue_tag,other_app_has_overdue_interval_tag,emcontact_curr_ovd_cnt_all_test_flag,
        CASE
         WHEN max_overdue_day_30d_all <= 0 THEN 0
         WHEN max_overdue_day_30d_all >= 7 THEN 7
         ELSE CAST(max_overdue_day_30d_all AS INT)
        END AS max_ovd_30d_bucket,
        android_oldcust_maincreditlevel_charge_v5_3,
        android_oldCust_mainCreditLevel_charge_V6_1 
    FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id
left join dim.dim_exchange_rate_cost dd
    on date(DATE_PARSE(dd.month_id, '%Y%m'))=date(date_format(f.release_time,'%Y-%m-01'))  
    and dd.account_currency = 'MXN'
WHERE 1=1 
    -- and f.if_issue = 1 
    AND f.is_reloan = 'old'
    AND f.tenant = 'yawey'
    AND f.app_time >= CAST('2026-08-15 00:00:00.000' AS TIMESTAMP)
GROUP BY  1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25
LIMIT 100000