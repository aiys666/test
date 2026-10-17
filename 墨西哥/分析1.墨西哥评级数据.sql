SELECT 
    -- 分组维度
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
    SUM(f.haircut_amount) AS haircut_amount,          -- 前砍费
    SUM(amount) AS amount,                            -- 到手金额
    SUM(should_interest) AS should_interest,
    SUM(if_issue) AS issue_cnt,

    -- ==================== 本金 (T0, T3, T7, T15, T30) 期限1 ====================
    SUM(t0_should_capit_1) AS t0_should_amt_1,
    SUM(t0_overdue_capit_1) AS t0_overdue_amount_1,
    SUM(t3_should_capit_1) AS t3_should_amt_1,
    SUM(t3_overdue_capit_1) AS t3_overdue_amount_1,
    SUM(t7_should_capit_1) AS t7_should_amt_1,
    SUM(t7_overdue_capit_1) AS t7_overdue_amount_1,
    SUM(t15_should_capit_1) AS t15_should_amt_1,
    SUM(t15_overdue_capit_1) AS t15_overdue_amount_1,
    SUM(t30_should_capit_1) AS t30_should_amt_1,
    SUM(t30_overdue_capit_1) AS t30_overdue_amount_1,

    -- 本息 (T0, T3, T7, T15, T30) 期限1
    SUM(t0_should_amt_1) AS t0_should_amt_interest_1,
    SUM(t0_overdue_amount_1) AS t0_overdue_amt_intere_1,
    SUM(t3_should_amt_1) AS t3_should_amt_interest_1,
    SUM(t3_overdue_amount_1) AS t3_overdue_amt_intere_1,
    SUM(t7_should_amt_1) AS t7_should_amt_interest_1,
    SUM(t7_overdue_amount_1) AS t7_overdue_amt_intere_1,
    SUM(t15_should_amt_1) AS t15_should_amt_interest_1,
    SUM(t15_overdue_amount_1) AS t15_overdue_amt_intere_1,
    SUM(t30_should_amt_1) AS t30_should_amt_interest_1,
    SUM(t30_overdue_amount_1) AS t30_overdue_amt_intere_1,

    -- ==================== 本金 期限2 ====================
    SUM(t0_should_capit_2) AS t0_should_amt_2,
    SUM(t0_overdue_capit_2) AS t0_overdue_amount_2,
    SUM(t3_should_capit_2) AS t3_should_amt_2,
    SUM(t3_overdue_capit_2) AS t3_overdue_amount_2,
    SUM(t7_should_capit_2) AS t7_should_amt_2,
    SUM(t7_overdue_capit_2) AS t7_overdue_amount_2,
    SUM(t15_should_capit_2) AS t15_should_amt_2,
    SUM(t15_overdue_capit_2) AS t15_overdue_amount_2,
    SUM(t30_should_capit_2) AS t30_should_amt_2,
    SUM(t30_overdue_capit_2) AS t30_overdue_amount_2,

    -- 本息 期限2
    SUM(t0_should_amt_2) AS t0_should_amt_interest_2,
    SUM(t0_overdue_amount_2) AS t0_overdue_amt_intere_2,
    SUM(t3_should_amt_2) AS t3_should_amt_interest_2,
    SUM(t3_overdue_amount_2) AS t3_overdue_amt_intere_2,
    SUM(t7_should_amt_2) AS t7_should_amt_interest_2,
    SUM(t7_overdue_amount_2) AS t7_overdue_amt_intere_2,
    SUM(t15_should_amt_2) AS t15_should_amt_interest_2,
    SUM(t15_overdue_amount_2) AS t15_overdue_amt_intere_2,
    SUM(t30_should_amt_2) AS t30_should_amt_interest_2,
    SUM(t30_overdue_amount_2) AS t30_overdue_amt_intere_2,

    -- ==================== 本金 期限3 ====================
    SUM(t0_should_capit_3) AS t0_should_amt_3,
    SUM(t0_overdue_capit_3) AS t0_overdue_amount_3,
    SUM(t3_should_capit_3) AS t3_should_amt_3,
    SUM(t3_overdue_capit_3) AS t3_overdue_amount_3,
    SUM(t7_should_capit_3) AS t7_should_amt_3,
    SUM(t7_overdue_capit_3) AS t7_overdue_amount_3,
    SUM(t15_should_capit_3) AS t15_should_amt_3,
    SUM(t15_overdue_capit_3) AS t15_overdue_amount_3,
    SUM(t30_should_capit_3) AS t30_should_amt_3,
    SUM(t30_overdue_capit_3) AS t30_overdue_amount_3,

    -- 本息 期限3
    SUM(t0_should_amt_3) AS t0_should_amt_interest_3,
    SUM(t0_overdue_amount_3) AS t0_overdue_amt_intere_3,
    SUM(t3_should_amt_3) AS t3_should_amt_interest_3,
    SUM(t3_overdue_amount_3) AS t3_overdue_amt_intere_3,
    SUM(t7_should_amt_3) AS t7_should_amt_interest_3,
    SUM(t7_overdue_amount_3) AS t7_overdue_amt_intere_3,
    SUM(t15_should_amt_3) AS t15_should_amt_interest_3,
    SUM(t15_overdue_amount_3) AS t15_overdue_amt_intere_3,
    SUM(t30_should_amt_3) AS t30_should_amt_interest_3,
    SUM(t30_overdue_amount_3) AS t30_overdue_amt_intere_3,

    -- ==================== 本金 期限4 ====================
    SUM(t0_should_capit_4) AS t0_should_amt_4,
    SUM(t0_overdue_capit_4) AS t0_overdue_amount_4,
    SUM(t3_should_capit_4) AS t3_should_amt_4,
    SUM(t3_overdue_capit_4) AS t3_overdue_amount_4,
    SUM(t7_should_capit_4) AS t7_should_amt_4,
    SUM(t7_overdue_capit_4) AS t7_overdue_amount_4,
    SUM(t15_should_capit_4) AS t15_should_amt_4,
    SUM(t15_overdue_capit_4) AS t15_overdue_amount_4,
    SUM(t30_should_capit_4) AS t30_should_amt_4,
    SUM(t30_overdue_capit_4) AS t30_overdue_amount_4,

    -- 本息 期限4
    SUM(t0_should_amt_4) AS t0_should_amt_interest_4,
    SUM(t0_overdue_amount_4) AS t0_overdue_amt_intere_4,
    SUM(t3_should_amt_4) AS t3_should_amt_interest_4,
    SUM(t3_overdue_amount_4) AS t3_overdue_amt_intere_4,
    SUM(t7_should_amt_4) AS t7_should_amt_interest_4,
    SUM(t7_overdue_amount_4) AS t7_overdue_amt_intere_4,
    SUM(t15_should_amt_4) AS t15_should_amt_interest_4,
    SUM(t15_overdue_amount_4) AS t15_overdue_amt_intere_4,
    SUM(t30_should_amt_4) AS t30_should_amt_interest_4,
    SUM(t30_overdue_amount_4) AS t30_overdue_amt_intere_4,

    -- ==================== 应还利息 (should_interest) 期限1~4 ====================
    -- 期限1
    SUM(t0_should_interest_1) AS t0_should_interest_1,
    SUM(t3_should_interest_1) AS t3_should_interest_1,
    SUM(t7_should_interest_1) AS t7_should_interest_1,
    SUM(t15_should_interest_1) AS t15_should_interest_1,
    SUM(t30_should_interest_1) AS t30_should_interest_1,

    -- 期限2
    SUM(t0_should_interest_2) AS t0_should_interest_2,
    SUM(t3_should_interest_2) AS t3_should_interest_2,
    SUM(t7_should_interest_2) AS t7_should_interest_2,
    SUM(t15_should_interest_2) AS t15_should_interest_2,
    SUM(t30_should_interest_2) AS t30_should_interest_2,

    -- 期限3
    SUM(t0_should_interest_3) AS t0_should_interest_3,
    SUM(t3_should_interest_3) AS t3_should_interest_3,
    SUM(t7_should_interest_3) AS t7_should_interest_3,
    SUM(t15_should_interest_3) AS t15_should_interest_3,
    SUM(t30_should_interest_3) AS t30_should_interest_3,

    -- 期限4
    SUM(t0_should_interest_4) AS t0_should_interest_4,
    SUM(t3_should_interest_4) AS t3_should_interest_4,
    SUM(t7_should_interest_4) AS t7_should_interest_4,
    SUM(t15_should_interest_4) AS t15_should_interest_4,
    SUM(t30_should_interest_4) AS t30_should_interest_4,

    -- ==================== 逾期利息 (overdue_interest) 期限1~4 ====================
    -- 期限1
    SUM(t0_overdue_interest_1) AS t0_overdue_interest_1,
    SUM(t3_overdue_interest_1) AS t3_overdue_interest_1,
    SUM(t7_overdue_interest_1) AS t7_overdue_interest_1,
    SUM(t15_overdue_interest_1) AS t15_overdue_interest_1,
    SUM(t30_overdue_interest_1) AS t30_overdue_interest_1,

    -- 期限2
    SUM(t0_overdue_interest_2) AS t0_overdue_interest_2,
    SUM(t3_overdue_interest_2) AS t3_overdue_interest_2,
    SUM(t7_overdue_interest_2) AS t7_overdue_interest_2,
    SUM(t15_overdue_interest_2) AS t15_overdue_interest_2,
    SUM(t30_overdue_interest_2) AS t30_overdue_interest_2,

    -- 期限3
    SUM(t0_overdue_interest_3) AS t0_overdue_interest_3,
    SUM(t3_overdue_interest_3) AS t3_overdue_interest_3,
    SUM(t7_overdue_interest_3) AS t7_overdue_interest_3,
    SUM(t15_overdue_interest_3) AS t15_overdue_interest_3,
    SUM(t30_overdue_interest_3) AS t30_overdue_interest_3,

    -- 期限4
    SUM(t0_overdue_interest_4) AS t0_overdue_interest_4,
    SUM(t3_overdue_interest_4) AS t3_overdue_interest_4,
    SUM(t7_overdue_interest_4) AS t7_overdue_interest_4,
    SUM(t15_overdue_interest_4) AS t15_overdue_interest_4,
    SUM(t30_overdue_interest_4) AS t30_overdue_interest_4,

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

    SUM(t15_coupon_substract_1) AS t15_coupon_substract_1,
    SUM(t15_coupon_substract_2) AS t15_coupon_substract_2,
    SUM(t15_coupon_substract_3) AS t15_coupon_substract_3,
    SUM(t15_coupon_substract_4) AS t15_coupon_substract_4,

    SUM(t30_coupon_substract_1) AS t30_coupon_substract_1,
    SUM(t30_coupon_substract_2) AS t30_coupon_substract_2,
    SUM(t30_coupon_substract_3) AS t30_coupon_substract_3,
    SUM(t30_coupon_substract_4) AS t30_coupon_substract_4,

    -- ==================== 窗口指标 ====================
    SUM(is_t0_window_1) AS is_t0_window_1,
    SUM(is_t7_window_1) AS is_t7_window_1,
    SUM(is_t3_window_1) AS is_t3_window_1,
    SUM(is_t15_window_1) AS is_t15_window_1,
    SUM(is_t30_window_1) AS is_t30_window_1,

    SUM(is_t0_window_2) AS is_t0_window_2,
    SUM(is_t3_window_2) AS is_t3_window_2,
    SUM(is_t7_window_2) AS is_t7_window_2,
    SUM(is_t15_window_2) AS is_t15_window_2,
    SUM(is_t30_window_2) AS is_t30_window_2,

    SUM(is_t0_window_3) AS is_t0_window_3,
    SUM(is_t3_window_3) AS is_t3_window_3,
    SUM(is_t7_window_3) AS is_t7_window_3,
    SUM(is_t15_window_3) AS is_t15_window_3,
    SUM(is_t30_window_3) AS is_t30_window_3,

    SUM(is_t0_window_4) AS is_t0_window_4,
    SUM(is_t3_window_4) AS is_t3_window_4,
    SUM(is_t7_window_4) AS is_t7_window_4,
    SUM(is_t15_window_4) AS is_t15_window_4,
    SUM(is_t30_window_4) AS is_t30_window_4,

    -- ==================== 逾期笔数 ====================
    SUM(is_t0_overdue_1) AS overdue_t0_1,
    SUM(is_t3_overdue_1) AS overdue_t3_1,
    SUM(is_t7_overdue_1) AS overdue_t7_1,
    SUM(is_t15_overdue_1) AS overdue_t15_1,
    SUM(is_t30_overdue_1) AS overdue_t30_1,
 

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
        v3_flag,
        android_oldcust_maincreditlevel_charge_v5_3,
        android_oldCust_mainCreditLevel_charge_V6_1 
    FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id
left join dim.dim_exchange_rate_cost dd
    on date(DATE_PARSE(dd.month_id, '%Y%m'))=date(date_format(f.release_time,'%Y-%m-01'))  
    and dd.account_currency = 'MXN'
WHERE f.if_issue = 1 
    AND f.is_reloan = 'old'
    AND f.tenant = 'yawey'
    AND f.app_time >= CAST('2026-01-01 00:00:00.000' AS TIMESTAMP)
GROUP BY  1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16
LIMIT 100000


'
,'20260730'
,'20260731'
,'20260801'
,'20260802'
,'20260803'
,'20260804'
,'20260805'
,'20260806'
,'20260807'
,'20260808'
,'20260809'
,'20260810'
,'20260811'
,'20260812'
,'20260813'
,'20260814'
,'20260815'
,'20260816'
,'20260817'
,'20260818'
