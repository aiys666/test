-- ============================================================
-- 全维度逾期率效应分解 - UNNEST 单次扫表版（静态 SQL）
-- 131 个维度压成 5 条 INSERT，每条用 CROSS JOIN UNNEST(维度名数组, 字段值数组)
-- 把每一行展开成多个维度行，再普通 GROUP BY。
-- 输出字段：dim_name, dim_group, week,
--          billed_cnt(出账笔数), overdue_cnt(逾期笔数),
--          billed_amt(出账金额), overdue_amt(逾期金额),
--          issue_cnt(放款笔数), contract_amt(放款金额)
-- 口径与原 22.sql 完全一致：
--   dim_group 非 NULL 才统计（外层 WHERE dim_group IS NOT NULL）
--   app_time >= date'2026-08-03'，week 取 app_week
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
SELECT dim_name, dim_group, week, billed_cnt, overdue_cnt, billed_amt, overdue_amt, issue_cnt, contract_amt
FROM (
    SELECT
        dim_name,
        dim_group,
        app_week AS week,
        SUM(is_t0_window_1) AS billed_cnt,
        SUM(is_t0_overdue_1) AS overdue_cnt,
        SUM(t0_should_amt_1) AS billed_amt,
        SUM(t0_overdue_amount_1) AS overdue_amt,
        SUM(if_issue) AS issue_cnt,
        SUM(contract_amount) AS contract_amt
    FROM (
        SELECT
            app_week,
            is_t0_window_1, is_t0_overdue_1, t0_should_amt_1, t0_overdue_amount_1, if_issue, contract_amount,
            CAST(V5_3_behavior_group_score AS VARCHAR) AS V5_3_behavior_group_score,
            CAST(V5_3_fraud_group_score AS VARCHAR) AS V5_3_fraud_group_score,
            CAST(advance_duotou_cnt_730d_score AS VARCHAR) AS advance_duotou_cnt_730d_score,
            CAST(advance_duotou_cnt_x_19_score AS VARCHAR) AS advance_duotou_cnt_x_19_score,
            CAST(af_uninstall_cnt_30d_score AS VARCHAR) AS af_uninstall_cnt_30d_score,
            CAST(af_uninstall_cnt_lf_score AS VARCHAR) AS af_uninstall_cnt_lf_score,
            CAST(android_oldCust_apply_subscore_charge_V6_1_score AS VARCHAR) AS android_oldCust_apply_subscore_charge_V6_1_score,
            CAST(android_oldCust_behavior_subscore_charge_V6_1_score AS VARCHAR) AS android_oldCust_behavior_subscore_charge_V6_1_score,
            CAST(android_oldCust_fraud_subscore_charge_V6_1_score AS VARCHAR) AS android_oldCust_fraud_subscore_charge_V6_1_score,
            CAST(android_oldCust_income_subscore_charge_V6_1_score AS VARCHAR) AS android_oldCust_income_subscore_charge_V6_1_score,
            CAST(android_oldCust_overdue_subscore_charge_V6_1_score AS VARCHAR) AS android_oldCust_overdue_subscore_charge_V6_1_score,
            CAST(android_oldCust_ruleScore_charge_V5_3_bin AS VARCHAR) AS android_oldCust_ruleScore_charge_V5_3_bin,
            CAST(android_oldCust_voteScore_charge_V5_3_bin AS VARCHAR) AS android_oldCust_voteScore_charge_V5_3_bin,
            CAST(app3_mix_loan1_cfinst_cnt_d30_score AS VARCHAR) AS app3_mix_loan1_cfinst_cnt_d30_score,
            CAST(app_hour_score AS VARCHAR) AS app_hour_score,
            CAST(app_loan1_inst_cnt_day7_score AS VARCHAR) AS app_loan1_inst_cnt_day7_score,
            CAST(baseinfo_employee_type_score AS VARCHAR) AS baseinfo_employee_type_score,
            CAST(baseinfo_has_car_score AS VARCHAR) AS baseinfo_has_car_score,
            CAST(baseinfo_has_house_score AS VARCHAR) AS baseinfo_has_house_score,
            CAST(baseinfo_marry_score AS VARCHAR) AS baseinfo_marry_score,
            CAST(baseinfo_userprof_age_score AS VARCHAR) AS baseinfo_userprof_age_score,
            CAST(baseinfo_userprof_degree_score AS VARCHAR) AS baseinfo_userprof_degree_score,
            CAST(beh2_o_create_reject_pct_d7_score AS VARCHAR) AS beh2_o_create_reject_pct_d7_score,
            CAST(beh_main_reject_applypct_day60_score AS VARCHAR) AS beh_main_reject_applypct_day60_score,
            CAST(emcontact_curr_ovd_cnt_all_score AS VARCHAR) AS emcontact_curr_ovd_cnt_all_score,
            CAST(finish_issue_rate_score AS VARCHAR) AS finish_issue_rate_score,
            CAST(history_loanrec_cnt_lastprepaydays_v2_score AS VARCHAR) AS history_loanrec_cnt_lastprepaydays_v2_score,
            CAST(if_system_run_too_short_score AS VARCHAR) AS if_system_run_too_short_score,
            CAST(income_score AS VARCHAR) AS income_score,
            CAST(last_repay_gap_days_app_group_score AS VARCHAR) AS last_repay_gap_days_app_group_score
        FROM mx.yj_test_table_250225
        WHERE app_time >= date'2026-08-03'
    ) s
    CROSS JOIN UNNEST(
        ARRAY['V5.3行为子分','V5.3欺诈子分','730天多头','30天多头','近30天卸载次数','卸载次数LF',
              'V6.1申请子分','V6.1行为子分','V6.1欺诈子分','V6.1收入子分','V6.1逾期子分',
              'V5.3规则分','V5.3投票分','30天混合首贷机构数','申请时段','7天首贷机构数',
              '雇佣类型','是否有车','是否有房','婚姻状态','年龄','学历',
              '7天创建拒绝率','60天主拒率','紧急联系人逾期数','完成放款率','最近结清距今天数',
              '系统运行时长','收入','上次还款间隔天数'],
        ARRAY[V5_3_behavior_group_score,V5_3_fraud_group_score,advance_duotou_cnt_730d_score,advance_duotou_cnt_x_19_score,
              af_uninstall_cnt_30d_score,af_uninstall_cnt_lf_score,
              android_oldCust_apply_subscore_charge_V6_1_score,android_oldCust_behavior_subscore_charge_V6_1_score,
              android_oldCust_fraud_subscore_charge_V6_1_score,android_oldCust_income_subscore_charge_V6_1_score,
              android_oldCust_overdue_subscore_charge_V6_1_score,
              android_oldCust_ruleScore_charge_V5_3_bin,android_oldCust_voteScore_charge_V5_3_bin,
              app3_mix_loan1_cfinst_cnt_d30_score,app_hour_score,app_loan1_inst_cnt_day7_score,
              baseinfo_employee_type_score,baseinfo_has_car_score,baseinfo_has_house_score,baseinfo_marry_score,
              baseinfo_userprof_age_score,baseinfo_userprof_degree_score,
              beh2_o_create_reject_pct_d7_score,beh_main_reject_applypct_day60_score,emcontact_curr_ovd_cnt_all_score,
              finish_issue_rate_score,history_loanrec_cnt_lastprepaydays_v2_score,if_system_run_too_short_score,
              income_score,last_repay_gap_days_app_group_score]
    ) AS t(dim_name, dim_group)
    GROUP BY dim_name, dim_group, app_week
) x
WHERE dim_group IS NOT NULL;

-- ============================================================
-- 步骤 2：第 2 批（30 个维度）
-- ============================================================
INSERT INTO mx.tmp_effect_decomp_all_dims
SELECT dim_name, dim_group, week, billed_cnt, overdue_cnt, billed_amt, overdue_amt, issue_cnt, contract_amt
FROM (
    SELECT
        dim_name,
        dim_group,
        app_week AS week,
        SUM(is_t0_window_1) AS billed_cnt,
        SUM(is_t0_overdue_1) AS overdue_cnt,
        SUM(t0_should_amt_1) AS billed_amt,
        SUM(t0_overdue_amount_1) AS overdue_amt,
        SUM(if_issue) AS issue_cnt,
        SUM(contract_amount) AS contract_amt
    FROM (
        SELECT
            app_week,
            is_t0_window_1, is_t0_overdue_1, t0_should_amt_1, t0_overdue_amount_1, if_issue, contract_amount,
            CAST(m687_old_1t3_ad_tengo_0709p1_score AS VARCHAR) AS m687_old_1t3_ad_tengo_0709p1_score,
            CAST(m696_old_1t3_bj_iz_0530_p1_score AS VARCHAR) AS m696_old_1t3_bj_iz_0530_p1_score,
            CAST(m698_old_1t3_voting_0619rh_score AS VARCHAR) AS m698_old_1t3_voting_0619rh_score,
            CAST(m699_rh_new_bin AS VARCHAR) AS m699_rh_new_bin,
            CAST(max_ovd_days_all_score AS VARCHAR) AS max_ovd_days_all_score,
            CAST(max_overdue_day_30d_all_score AS VARCHAR) AS max_overdue_day_30d_all_score,
            CAST(minstay_repayplan_second_30d_mid_score AS VARCHAR) AS minstay_repayplan_second_30d_mid_score,
            CAST(model_698_score AS VARCHAR) AS model_698_score,
            CAST(model_699_score AS VARCHAR) AS model_699_score,
            CAST(model_p2_1t_score AS VARCHAR) AS model_p2_1t_score,
            CAST(msg2_loandue_addpctall_day1_score AS VARCHAR) AS msg2_loandue_addpctall_day1_score,
            CAST(pvalue_mex_b311_2025v1_p1_score AS VARCHAR) AS pvalue_mex_b311_2025v1_p1_score,
            CAST(pvalue_mex_b320_2026v1_long_p1_score AS VARCHAR) AS pvalue_mex_b320_2026v1_long_p1_score,
            CAST(pvalue_mex_b321_2026v1_p1_score AS VARCHAR) AS pvalue_mex_b321_2026v1_p1_score,
            CAST(pvalue_mex_b321_2026v2_p1_score AS VARCHAR) AS pvalue_mex_b321_2026v2_p1_score,
            CAST(pvalue_mex_b329_2026v1_byid_p1_score AS VARCHAR) AS pvalue_mex_b329_2026v1_byid_p1_score,
            CAST(question3_score AS VARCHAR) AS question3_score,
            CAST(question5_score AS VARCHAR) AS question5_score,
            CAST(question6_v2_score AS VARCHAR) AS question6_v2_score,
            CAST(stgy_advance_gd_k_104_score AS VARCHAR) AS stgy_advance_gd_k_104_score,
            CAST(stgy_advance_gd_k_136_score AS VARCHAR) AS stgy_advance_gd_k_136_score,
            CAST(stgy_advance_gd_k_292_score AS VARCHAR) AS stgy_advance_gd_k_292_score,
            CAST(stgy_advance_gd_x_12_score AS VARCHAR) AS stgy_advance_gd_x_12_score,
            CAST(stgy_advance_gd_x_34_score AS VARCHAR) AS stgy_advance_gd_x_34_score,
            CAST(stgy_advance_gd_x_55_score AS VARCHAR) AS stgy_advance_gd_x_55_score,
            CAST(stgy_amlta_d180_record_date_unique_cnt_score AS VARCHAR) AS stgy_amlta_d180_record_date_unique_cnt_score,
            CAST(stgy_bj_apply_count_1w_score AS VARCHAR) AS stgy_bj_apply_count_1w_score,
            CAST(stgy_bj_apply_jgs_12m_score AS VARCHAR) AS stgy_bj_apply_jgs_12m_score,
            CAST(stgy_bj_apply_jgs_1w_score AS VARCHAR) AS stgy_bj_apply_jgs_1w_score,
            CAST(stgy_bj_loan_count_1w_score AS VARCHAR) AS stgy_bj_loan_count_1w_score
        FROM mx.yj_test_table_250225
        WHERE app_time >= date'2026-08-03'
    ) s
    CROSS JOIN UNNEST(
        ARRAY['687模型分','696模型分','698投票分','699新模型分箱','全局逾期天数','近30天逾期天数',
              '还款计划停留时长','698模型分','699模型分','短逾模型P2','到期日新增占比',
              'B311模型分','B320长窗模型分','B321V1模型分','B321V2模型分','B329模型分',
              '问卷3','问卷5','问卷6',
              '前置GD_K104','前置GD_K136','前置GD_K292','前置GD_X12','前置GD_X34','前置GD_X55',
              'AMLTA180天记录数','1周申请次数','12月申请间隔','1周申请间隔','1周借款次数'],
        ARRAY[m687_old_1t3_ad_tengo_0709p1_score,m696_old_1t3_bj_iz_0530_p1_score,m698_old_1t3_voting_0619rh_score,
              m699_rh_new_bin,max_ovd_days_all_score,max_overdue_day_30d_all_score,
              minstay_repayplan_second_30d_mid_score,model_698_score,model_699_score,model_p2_1t_score,
              msg2_loandue_addpctall_day1_score,pvalue_mex_b311_2025v1_p1_score,pvalue_mex_b320_2026v1_long_p1_score,
              pvalue_mex_b321_2026v1_p1_score,pvalue_mex_b321_2026v2_p1_score,pvalue_mex_b329_2026v1_byid_p1_score,
              question3_score,question5_score,question6_v2_score,
              stgy_advance_gd_k_104_score,stgy_advance_gd_k_136_score,stgy_advance_gd_k_292_score,
              stgy_advance_gd_x_12_score,stgy_advance_gd_x_34_score,stgy_advance_gd_x_55_score,
              stgy_amlta_d180_record_date_unique_cnt_score,stgy_bj_apply_count_1w_score,stgy_bj_apply_jgs_12m_score,
              stgy_bj_apply_jgs_1w_score,stgy_bj_loan_count_1w_score]
    ) AS t(dim_name, dim_group)
    GROUP BY dim_name, dim_group, app_week
) x
WHERE dim_group IS NOT NULL;

-- ============================================================
-- 步骤 3：第 3 批（28 个维度）
-- ============================================================
INSERT INTO mx.tmp_effect_decomp_all_dims
SELECT dim_name, dim_group, week, billed_cnt, overdue_cnt, billed_amt, overdue_amt, issue_cnt, contract_amt
FROM (
    SELECT
        dim_name,
        dim_group,
        app_week AS week,
        SUM(is_t0_window_1) AS billed_cnt,
        SUM(is_t0_overdue_1) AS overdue_cnt,
        SUM(t0_should_amt_1) AS billed_amt,
        SUM(t0_overdue_amount_1) AS overdue_amt,
        SUM(if_issue) AS issue_cnt,
        SUM(contract_amount) AS contract_amt
    FROM (
        SELECT
            app_week,
            is_t0_window_1, is_t0_overdue_1, t0_should_amt_1, t0_overdue_amount_1, if_issue, contract_amount,
            CAST(stgy_dyna_amlba_d21_b_cnt_score AS VARCHAR) AS stgy_dyna_amlba_d21_b_cnt_score,
            CAST(stgy_dyna_amlba_d30_c_cnt_score AS VARCHAR) AS stgy_dyna_amlba_d30_c_cnt_score,
            CAST(stgy_dyna_amlba_d30_f2_daydiff_max_score AS VARCHAR) AS stgy_dyna_amlba_d30_f2_daydiff_max_score,
            CAST(stgy_dyna_amlba_d60_f3_cnt_score AS VARCHAR) AS stgy_dyna_amlba_d60_f3_cnt_score,
            CAST(stgy_dyna_amlta_d60_daydiff_median_score AS VARCHAR) AS stgy_dyna_amlta_d60_daydiff_median_score,
            CAST(thirdparty_izi_whatsapp_register_status_score AS VARCHAR) AS thirdparty_izi_whatsapp_register_status_score,
            CAST(unique_email_cnt_score AS VARCHAR) AS unique_email_cnt_score,
            CAST(unique_phone_score AS VARCHAR) AS unique_phone_score,
            CAST(product_level AS VARCHAR) AS product_level,
            CAST(last_product_level AS VARCHAR) AS last_product_level,
            CAST(product_level_change AS VARCHAR) AS product_level_change,
            CAST(change_product_tag AS VARCHAR) AS change_product_tag,
            CAST(v3_flag AS VARCHAR) AS v3_flag,
            CAST(if_inherit_tag AS VARCHAR) AS if_inherit_tag,
            CAST(is_reloan AS VARCHAR) AS is_reloan,
            CAST(main_sanwich_loan_grp AS VARCHAR) AS main_sanwich_loan_grp,
            CAST(product_level_test_260701 AS VARCHAR) AS product_level_test_260701,
            CAST(product_level_change_test_260722 AS VARCHAR) AS product_level_change_test_260722,
            CAST(change_flag1 AS VARCHAR) AS change_flag1,
            CAST(product_test_0722 AS VARCHAR) AS product_test_0722,
            CAST(product_random_0722 AS VARCHAR) AS product_random_0722,
            CAST(daily_max_limit_tag AS VARCHAR) AS daily_max_limit_tag,
            CAST(product_level_test_251205_flag AS VARCHAR) AS product_level_test_251205_flag,
            CAST(max_overdue_day_30d_all_strategy_test AS VARCHAR) AS max_overdue_day_30d_all_strategy_test,
            CAST(cap_1point8_strategy_test AS VARCHAR) AS cap_1point8_strategy_test,
            CAST(app_group AS VARCHAR) AS app_group,
            CAST(source AS VARCHAR) AS source,
            CAST(app AS VARCHAR) AS app
        FROM mx.yj_test_table_250225
        WHERE app_time >= date'2026-08-03'
    ) s
    CROSS JOIN UNNEST(
        ARRAY['AMLBA21天B类数','AMLBA30天C类数','AMLBA30天F2间隔','AMLBA60天F3数','AMLTA60天间隔中位数',
              'WA注册状态','邮箱数量','手机号数量',
              '产品等级','上期产品等级','产品等级变化','是否转产线','V3版本标识','是否继承标签','是否复贷','贷款类型',
              '转产测试260701','转产测试260722','转产标记1','产品测试0722','产品随机分组0722','日限额标签',
              '产品测试251205','策略测试-逾期','策略测试-提额1.8','APP分组','来源','APP'],
        ARRAY[stgy_dyna_amlba_d21_b_cnt_score,stgy_dyna_amlba_d30_c_cnt_score,stgy_dyna_amlba_d30_f2_daydiff_max_score,
              stgy_dyna_amlba_d60_f3_cnt_score,stgy_dyna_amlta_d60_daydiff_median_score,
              thirdparty_izi_whatsapp_register_status_score,unique_email_cnt_score,unique_phone_score,
              product_level,last_product_level,product_level_change,change_product_tag,v3_flag,if_inherit_tag,
              is_reloan,main_sanwich_loan_grp,product_level_test_260701,product_level_change_test_260722,
              change_flag1,product_test_0722,product_random_0722,daily_max_limit_tag,product_level_test_251205_flag,
              max_overdue_day_30d_all_strategy_test,cap_1point8_strategy_test,app_group,source,app]
    ) AS t(dim_name, dim_group)
    GROUP BY dim_name, dim_group, app_week
) x
WHERE dim_group IS NOT NULL;

-- ============================================================
-- 步骤 4：第 4 批（14 个维度：13个V6口径分箱 + B320 15档细分箱）
-- ============================================================
INSERT INTO mx.tmp_effect_decomp_all_dims
SELECT dim_name, dim_group, week, billed_cnt, overdue_cnt, billed_amt, overdue_amt, issue_cnt, contract_amt
FROM (
    SELECT
        dim_name,
        dim_group,
        app_week AS week,
        SUM(is_t0_window_1) AS billed_cnt,
        SUM(is_t0_overdue_1) AS overdue_cnt,
        SUM(t0_should_amt_1) AS billed_amt,
        SUM(t0_overdue_amount_1) AS overdue_amt,
        SUM(if_issue) AS issue_cnt,
        SUM(contract_amount) AS contract_amt
    FROM (
        SELECT
            app_week,
            is_t0_window_1, is_t0_overdue_1, t0_should_amt_1, t0_overdue_amount_1, if_issue, contract_amount,
            CAST(advance_duotou_cnt_x_19_score_v6 AS VARCHAR) AS advance_duotou_cnt_x_19_score_v6,
            CAST(advance_duotou_cnt_730d_score_v6 AS VARCHAR) AS advance_duotou_cnt_730d_score_v6,
            CAST(last_repay_gap_days_app_group_score_v6 AS VARCHAR) AS last_repay_gap_days_app_group_score_v6,
            CAST(question3_score_v6 AS VARCHAR) AS question3_score_v6,
            CAST(question6_v2_score_v6 AS VARCHAR) AS question6_v2_score_v6,
            CAST(max_ovd_days_all_score_v6 AS VARCHAR) AS max_ovd_days_all_score_v6,
            CAST(max_overdue_day_30d_all_score_v6 AS VARCHAR) AS max_overdue_day_30d_all_score_v6,
            CAST(history_loanrec_cnt_lastprepaydays_v2_score_v6 AS VARCHAR) AS history_loanrec_cnt_lastprepaydays_v2_score_v6,
            CAST(unique_email_cnt_score_v6 AS VARCHAR) AS unique_email_cnt_score_v6,
            CAST(af_uninstall_cnt_30d_score_v6 AS VARCHAR) AS af_uninstall_cnt_30d_score_v6,
            CAST(minstay_repayplan_second_30d_mid_score_v6 AS VARCHAR) AS minstay_repayplan_second_30d_mid_score_v6,
            CAST(baseinfo_userprof_age_score_v6 AS VARCHAR) AS baseinfo_userprof_age_score_v6,
            CAST(baseinfo_userprof_degree_score_v6 AS VARCHAR) AS baseinfo_userprof_degree_score_v6,
            CAST(pvalue_mex_b320_2026v1_long_p1_group AS VARCHAR) AS pvalue_mex_b320_2026v1_long_p1_group
        FROM mx.yj_test_table_250225
        WHERE app_time >= date'2026-08-03'
    ) s
    CROSS JOIN UNNEST(
        ARRAY['30天多头V6','730天多头V6','上次还款间隔天数V6','问卷3-V6','问卷6-V6',
              '全局逾期天数V6','近30天逾期天数V6','最近结清距今天数V6','邮箱数量V6','近30天卸载次数V6',
              '还款计划停留时长V6','年龄V6','学历V6','B320长窗细分15档'],
        ARRAY[advance_duotou_cnt_x_19_score_v6,advance_duotou_cnt_730d_score_v6,last_repay_gap_days_app_group_score_v6,
              question3_score_v6,question6_v2_score_v6,max_ovd_days_all_score_v6,max_overdue_day_30d_all_score_v6,
              history_loanrec_cnt_lastprepaydays_v2_score_v6,unique_email_cnt_score_v6,af_uninstall_cnt_30d_score_v6,
              minstay_repayplan_second_30d_mid_score_v6,baseinfo_userprof_age_score_v6,baseinfo_userprof_degree_score_v6,
              pvalue_mex_b320_2026v1_long_p1_group]
    ) AS t(dim_name, dim_group)
    GROUP BY dim_name, dim_group, app_week
) x
WHERE dim_group IS NOT NULL;

-- ============================================================
-- 步骤 5：第 5 批（29 个维度：测试策略/发临额/其他包标签等非分箱字段）
-- ============================================================
INSERT INTO mx.tmp_effect_decomp_all_dims
SELECT dim_name, dim_group, week, billed_cnt, overdue_cnt, billed_amt, overdue_amt, issue_cnt, contract_amt
FROM (
    SELECT
        dim_name,
        dim_group,
        app_week AS week,
        SUM(is_t0_window_1) AS billed_cnt,
        SUM(is_t0_overdue_1) AS overdue_cnt,
        SUM(t0_should_amt_1) AS billed_amt,
        SUM(t0_overdue_amount_1) AS overdue_amt,
        SUM(if_issue) AS issue_cnt,
        SUM(contract_amount) AS contract_amt
    FROM (
        SELECT
            app_week,
            is_t0_window_1, is_t0_overdue_1, t0_should_amt_1, t0_overdue_amount_1, if_issue, contract_amount,
            CAST(cap_1point8cap_strategy_test_flag AS VARCHAR) AS cap_1point8cap_strategy_test_flag,
            CAST(temp_limit_test_flag AS VARCHAR) AS temp_limit_test_flag,
            CAST(strategy_temp_limit_test_flag AS VARCHAR) AS strategy_temp_limit_test_flag,
            CAST(temp_credit_amount_strategy_test_flag AS VARCHAR) AS temp_credit_amount_strategy_test_flag,
            CAST(strategy_temp_limit_interval_test_flag AS VARCHAR) AS strategy_temp_limit_interval_test_flag,
            CAST(emcontact_curr_ovd_cnt_all_test_flag AS VARCHAR) AS emcontact_curr_ovd_cnt_all_test_flag,
            CAST(tagg_0819 AS VARCHAR) AS tagg_0819,
            CAST(tagg_0826 AS VARCHAR) AS tagg_0826,
            CAST(tagg_0902 AS VARCHAR) AS tagg_0902,
            CAST(tagg_0909 AS VARCHAR) AS tagg_0909,
            CAST(temp_limit_0819_tag AS VARCHAR) AS temp_limit_0819_tag,
            CAST(temp_limit_0820_tag AS VARCHAR) AS temp_limit_0820_tag,
            CAST(temp_limit_0826_tag AS VARCHAR) AS temp_limit_0826_tag,
            CAST(temp_limit_0827_tag AS VARCHAR) AS temp_limit_0827_tag,
            CAST(temp_limit_0902_tag AS VARCHAR) AS temp_limit_0902_tag,
            CAST(temp_limit_0903_tag AS VARCHAR) AS temp_limit_0903_tag,
            CAST(temp_limit_0909_tag AS VARCHAR) AS temp_limit_0909_tag,
            CAST(temp_limit_0910_tag AS VARCHAR) AS temp_limit_0910_tag,
            CAST(if_product_or_maxlimit_change_tag AS VARCHAR) AS if_product_or_maxlimit_change_tag,
            CAST(repayment_clearing_count_tenant_flag AS VARCHAR) AS repayment_clearing_count_tenant_flag,
            CAST(repayment_clearing_count_index_tenant_flag AS VARCHAR) AS repayment_clearing_count_index_tenant_flag,
            CAST(other_app_has_loan_tag AS VARCHAR) AS other_app_has_loan_tag,
            CAST(other_app_has_overdue_tag AS VARCHAR) AS other_app_has_overdue_tag,
            CAST(other_app_has_overdue_interval_tag AS VARCHAR) AS other_app_has_overdue_interval_tag,
            CAST(last_product_origin AS VARCHAR) AS last_product_origin,
            CAST(change_flag AS VARCHAR) AS change_flag,
            CAST(if_reloan_24h AS VARCHAR) AS if_reloan_24h,
            CAST(product_name_new AS VARCHAR) AS product_name_new,
            CAST(global_limit AS VARCHAR) AS global_limit
        FROM mx.yj_test_table_250225
        WHERE app_time >= date'2026-08-03'
    ) s
    CROSS JOIN UNNEST(
        ARRAY['1.8倍cap测试分组','发临额测试分组','策略发临额测试','临额金额策略分组','临额间隔策略分组',
              '紧急联系人逾期标识','0819离线发临额在贷','0826离线发临额在贷','0902离线发临额在贷','0909离线发临额在贷',
              '0819发临额标签','0820发临额标签','0826发临额标签','0827发临额标签',
              '0902发临额标签','0903发临额标签','0909发临额标签','0910发临额标签',
              '产品/最大额度变更标签','结清次数分档','结清次数指数分档','其他包放款标签','其他包在逾标签','其他包在逾区间',
              '上笔产品来源','转产标记','24H复贷','产品名称','全局额度'],
        ARRAY[cap_1point8cap_strategy_test_flag,temp_limit_test_flag,strategy_temp_limit_test_flag,
              temp_credit_amount_strategy_test_flag,strategy_temp_limit_interval_test_flag,emcontact_curr_ovd_cnt_all_test_flag,
              tagg_0819,tagg_0826,tagg_0902,tagg_0909,
              temp_limit_0819_tag,temp_limit_0820_tag,temp_limit_0826_tag,temp_limit_0827_tag,
              temp_limit_0902_tag,temp_limit_0903_tag,temp_limit_0909_tag,temp_limit_0910_tag,
              if_product_or_maxlimit_change_tag,repayment_clearing_count_tenant_flag,repayment_clearing_count_index_tenant_flag,
              other_app_has_loan_tag,other_app_has_overdue_tag,other_app_has_overdue_interval_tag,
              last_product_origin,change_flag,if_reloan_24h,product_name_new,global_limit]
    ) AS t(dim_name, dim_group)
    GROUP BY dim_name, dim_group, app_week
) x
WHERE dim_group IS NOT NULL;

-- ============================================================
-- 最后：查询全部结果（导出到CSV）
-- ============================================================
SELECT * FROM mx.tmp_effect_decomp_all_dims
ORDER BY dim_name, week, dim_group;
