
--:{author=tudalun, department=墨西哥, dagName=android_oldcust_main_creditlevel_charge_v5_1_param_table, taskName=android_oldcust_maincreditlevel_charge_v6_1_table}
-- DROP TABLE IF EXISTS mx.android_oldCust_mainCreditLevel_charge_V6_1_table;
-- CREATE TABLE mx.android_oldCust_mainCreditLevel_charge_V6_1_table (
--   externalid VARCHAR,
--   mid bigint,
--   createtime timestamp,
--   last_repay_gap_days_app_group DOUBLE,
--   stgy_advance_gd_k_136 DOUBLE,
--   stgy_advance_gd_k_292 DOUBLE,
--   stgy_advance_gd_k_104 DOUBLE,
--   beh_main_reject_applypct_day60 DOUBLE,
--   beh2_o_create_reject_pct_d7 DOUBLE,
--   stgy_amlta_d180_record_date_unique_cnt DOUBLE,
--   stgy_dyna_amlta_d60_daydiff_median DOUBLE,
--   stgy_dyna_amlba_d21_b_cnt DOUBLE,
--   stgy_dyna_amlba_d30_c_cnt DOUBLE,
--   finish_issue_rate DOUBLE,
--   stgy_bj_loan_count_1w DOUBLE,
--   question3 DOUBLE,
--   question6_v2 DOUBLE,
--   question5 DOUBLE,
--   msg2_loandue_addpctall_day1 DOUBLE,
--   android_oldCust_behavior_subscore_charge_V6_1 DOUBLE,
--   max_ovd_days_all DOUBLE,
--   emcontact_curr_ovd_cnt_all DOUBLE,
--   history_loanrec_cnt_lastprepaydays_v2 DOUBLE,
--   max_overdue_day_30d_all DOUBLE,
--   stgy_dyna_amlba_d30_f2_daydiff_max DOUBLE,
--   stgy_dyna_amlba_d60_f3_cnt DOUBLE,
--   android_oldCust_overdue_subscore_charge_V6_1 DOUBLE,
--   apply_hour DOUBLE,
--   history_loanrec_time_apply DOUBLE,
--   minstay_repayplan_second_30d_mid DOUBLE,
--   af_uninstall_cnt_30d DOUBLE,
--   unique_email_cnt DOUBLE,
--   af_uninstall_cnt_lf DOUBLE,
--   unique_phone DOUBLE,
--   android_oldCust_fraud_subscore_charge_V6_1 DOUBLE,
--   stgy_advance_gd_x_55 DOUBLE,
--   stgy_advance_gd_x_12 DOUBLE,
--   stgy_advance_gd_x_34 DOUBLE,
--   app_loan1_inst_cnt_day7 DOUBLE,
--   app3_mix_loan1_cfinst_cnt_d30 DOUBLE,
--   advance_duotou_cnt_730d DOUBLE,
--   advance_duotou_cnt_x_19 DOUBLE,
--   stgy_bj_apply_count_1w DOUBLE,
--   stgy_bj_apply_jgs_12m DOUBLE,
--   stgy_bj_apply_jgs_1w DOUBLE,
--   android_oldCust_apply_subscore_charge_V6_1 DOUBLE,
--   income DOUBLE,
--   baseinfo_userprof_age DOUBLE,
--   baseinfo_has_car DOUBLE,
--   baseinfo_has_house DOUBLE,
--   baseinfo_marry DOUBLE,
--   baseinfo_employee_type DOUBLE,
--   baseinfo_userprof_degree DOUBLE,
--   android_oldCust_income_subscore_charge_V6_1 DOUBLE,
--   android_oldCust_rule_score_charge_V6_1 DOUBLE,
--   m698_old_1t3_voting_0619rh DOUBLE,
--   pvalue_mex_b311_2025v1_p1 DOUBLE,
--   pvalue_mex_b321_2026v2_p1 DOUBLE,
--   pvalue_mex_b321_2026v1_p1 DOUBLE,
--   m696_old_1t3_bj_iz_0530_p1 DOUBLE,
--   pvalue_mex_b320_2026v1_long_p1 DOUBLE,
--   m687_old_1t3_ad_tengo_0709p1 DOUBLE,
--   pvalue_mex_b329_2026v1_byid_p1 DOUBLE,
--   android_oldCust_voting_score_charge_V6_1 DOUBLE,
--   pvalue_mex_b320_2026v2_p1 DOUBLE,
--   android_oldCust_midCreditLevel_charge_V6_1 DOUBLE,
--   android_oldCust_mainCreditLevel_charge_V6_1 DOUBLE,
--   etl_date VARCHAR
-- )
-- WITH (
--   format = 'ORC',
--   partitioned_by = ARRAY['etl_date']
-- );




DELETE FROM mx.android_oldCust_mainCreditLevel_charge_V6_1_table
WHERE etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
;
--:{author=tudalun, department=墨西哥, dagName=android_oldcust_main_creditlevel_charge_v5_1_param_table, taskName=android_oldcust_maincreditlevel_charge_v6_1_table}
INSERT INTO mx.android_oldCust_mainCreditLevel_charge_V6_1_table
SELECT
  t0.externalid,
  t0.mid,
  t0.createtime,
  t0.last_repay_gap_days_app_group,
  t0.stgy_advance_gd_k_136,
  t0.stgy_advance_gd_k_292,
  t0.stgy_advance_gd_k_104,
  t0.beh_main_reject_applypct_day60,
  t0.beh2_o_create_reject_pct_d7,
  t0.stgy_amlta_d180_record_date_unique_cnt,
  t0.stgy_dyna_amlta_d60_daydiff_median,
  t0.stgy_dyna_amlba_d21_b_cnt,
  t0.stgy_dyna_amlba_d30_c_cnt,
  t0.finish_issue_rate,
  t0.stgy_bj_loan_count_1w,
  t0.question3,
  t0.question6_v2,
  t0.question5,
  t0.msg2_loandue_addpctall_day1,
  t0.android_oldCust_behavior_subscore_charge_V6_1,
  t1.max_ovd_days_all,
  t1.emcontact_curr_ovd_cnt_all,
  t1.history_loanrec_cnt_lastprepaydays_v2,
  t1.max_overdue_day_30d_all,
  t1.stgy_dyna_amlba_d30_f2_daydiff_max,
  t1.stgy_dyna_amlba_d60_f3_cnt,
  t1.android_oldCust_overdue_subscore_charge_V6_1,
  t2.apply_hour,
  t2.history_loanrec_time_apply,
  t2.minstay_repayplan_second_30d_mid,
  t2.af_uninstall_cnt_30d,
  t2.unique_email_cnt,
  t2.af_uninstall_cnt_lf,
  t2.unique_phone,
  t2.android_oldCust_fraud_subscore_charge_V6_1,
  t3.stgy_advance_gd_x_55,
  t3.stgy_advance_gd_x_12,
  t3.stgy_advance_gd_x_34,
  t3.app_loan1_inst_cnt_day7,
  t3.app3_mix_loan1_cfinst_cnt_d30,
  t3.advance_duotou_cnt_730d,
  t3.advance_duotou_cnt_x_19,
  t3.stgy_bj_apply_count_1w,
  t3.stgy_bj_apply_jgs_12m,
  t3.stgy_bj_apply_jgs_1w,
  t3.android_oldCust_apply_subscore_charge_V6_1,
  t4.income,
  t4.baseinfo_userprof_age,
  t4.baseinfo_has_car,
  t4.baseinfo_has_house,
  t4.baseinfo_marry,
  t4.baseinfo_employee_type,
  t4.baseinfo_userprof_degree,
  t4.android_oldCust_income_subscore_charge_V6_1,
  t5.android_oldCust_rule_score_charge_V6_1,
  t6.m698_old_1t3_voting_0619rh,
  t6.pvalue_mex_b311_2025v1_p1,
  t6.pvalue_mex_b321_2026v2_p1,
  t6.pvalue_mex_b321_2026v1_p1,
  t6.m696_old_1t3_bj_iz_0530_p1,
  t6.pvalue_mex_b320_2026v1_long_p1,
  t6.m687_old_1t3_ad_tengo_0709p1,
  t6.pvalue_mex_b329_2026v1_byid_p1,
  t6.android_oldCust_voting_score_charge_V6_1,
  t7.pvalue_mex_b320_2026v2_p1,
  t7.android_oldCust_midCreditLevel_charge_V6_1,
  t8.android_oldCust_mainCreditLevel_charge_V6_1,
  t0.etl_date
FROM (
  SELECT
    externalid,
    mid,
    createtime,
    etl_date,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.last_repay_gap_days_app_group') AS DOUBLE)) AS last_repay_gap_days_app_group,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_advance_gd_k_136') AS DOUBLE)) AS stgy_advance_gd_k_136,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_advance_gd_k_292') AS DOUBLE)) AS stgy_advance_gd_k_292,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_advance_gd_k_104') AS DOUBLE)) AS stgy_advance_gd_k_104,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.beh_main_reject_applypct_day60') AS DOUBLE)) AS beh_main_reject_applypct_day60,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.beh2_o_create_reject_pct_d7') AS DOUBLE)) AS beh2_o_create_reject_pct_d7,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_amlta_d180_record_date_unique_cnt') AS DOUBLE)) AS stgy_amlta_d180_record_date_unique_cnt,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_dyna_amlta_d60_daydiff_median') AS DOUBLE)) AS stgy_dyna_amlta_d60_daydiff_median,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_dyna_amlba_d21_b_cnt') AS DOUBLE)) AS stgy_dyna_amlba_d21_b_cnt,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_dyna_amlba_d30_c_cnt') AS DOUBLE)) AS stgy_dyna_amlba_d30_c_cnt,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.finish_issue_rate') AS DOUBLE)) AS finish_issue_rate,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_bj_loan_count_1w') AS DOUBLE)) AS stgy_bj_loan_count_1w,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.question3') AS DOUBLE)) AS question3,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.question6_v2') AS DOUBLE)) AS question6_v2,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.question5') AS DOUBLE)) AS question5,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.msg2_loandue_addpctall_day1') AS DOUBLE)) AS msg2_loandue_addpctall_day1,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(outputdata, '$.android_oldCust_behavior_subscore_charge_V6_1') AS DOUBLE)) AS android_oldCust_behavior_subscore_charge_V6_1
  FROM (
    SELECT
      externalid,
      mid,
      inputdata,
      outputdata,
      etl_date,
      createtime,
      ROW_NUMBER() OVER (PARTITION BY externalid ORDER BY createtime) AS rn
    FROM ods.s21_risk_model_record
    WHERE modelmainid = 1628
      AND etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
      AND strategytype = 'CHAMPION'
  ) tt0
  WHERE rn = 1
  GROUP BY externalid, mid, etl_date, createtime
) t0
LEFT JOIN (
  SELECT
    externalid,
    mid,
    createtime,
    etl_date,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.max_ovd_days_all') AS DOUBLE)) AS max_ovd_days_all,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.emcontact_curr_ovd_cnt_all') AS DOUBLE)) AS emcontact_curr_ovd_cnt_all,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.history_loanrec_cnt_lastprepaydays_v2') AS DOUBLE)) AS history_loanrec_cnt_lastprepaydays_v2,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.max_overdue_day_30d_all') AS DOUBLE)) AS max_overdue_day_30d_all,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_dyna_amlba_d30_f2_daydiff_max') AS DOUBLE)) AS stgy_dyna_amlba_d30_f2_daydiff_max,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_dyna_amlba_d60_f3_cnt') AS DOUBLE)) AS stgy_dyna_amlba_d60_f3_cnt,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(outputdata, '$.android_oldCust_overdue_subscore_charge_V6_1') AS DOUBLE)) AS android_oldCust_overdue_subscore_charge_V6_1
  FROM (
    SELECT
      externalid,
      mid,
      inputdata,
      outputdata,
      etl_date,
      createtime,
      ROW_NUMBER() OVER (PARTITION BY externalid ORDER BY createtime) AS rn
    FROM ods.s21_risk_model_record
    WHERE modelmainid = 1629
      AND etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
      AND strategytype = 'CHAMPION'
  ) tt0
  WHERE rn = 1
  GROUP BY externalid, mid, etl_date, createtime
) t1 ON t0.externalid = t1.externalid
LEFT JOIN (
  SELECT
    externalid,
    mid,
    etl_date,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.apply_hour') AS DOUBLE)) AS apply_hour,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.history_loanrec_time_apply') AS DOUBLE)) AS history_loanrec_time_apply,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.minstay_repayplan_second_30d_mid') AS DOUBLE)) AS minstay_repayplan_second_30d_mid,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.af_uninstall_cnt_30d') AS DOUBLE)) AS af_uninstall_cnt_30d,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.unique_email_cnt') AS DOUBLE)) AS unique_email_cnt,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.af_uninstall_cnt_lf') AS DOUBLE)) AS af_uninstall_cnt_lf,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.unique_phone') AS DOUBLE)) AS unique_phone,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(outputdata, '$.android_oldCust_fraud_subscore_charge_V6_1') AS DOUBLE)) AS android_oldCust_fraud_subscore_charge_V6_1
  FROM (
    SELECT
      externalid,
      mid,
      inputdata,
      outputdata,
      etl_date,
      createtime,
      ROW_NUMBER() OVER (PARTITION BY externalid ORDER BY createtime) AS rn
    FROM ods.s21_risk_model_record
    WHERE modelmainid = 1630
      AND etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
      AND strategytype = 'CHAMPION'
  ) tt0
  WHERE rn = 1
  GROUP BY externalid, mid, etl_date
) t2 ON t0.externalid = t2.externalid
LEFT JOIN (
  SELECT
    externalid,
    mid,
    etl_date,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_advance_gd_x_55') AS DOUBLE)) AS stgy_advance_gd_x_55,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_advance_gd_x_12') AS DOUBLE)) AS stgy_advance_gd_x_12,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_advance_gd_x_34') AS DOUBLE)) AS stgy_advance_gd_x_34,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.app_loan1_inst_cnt_day7') AS DOUBLE)) AS app_loan1_inst_cnt_day7,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.app3_mix_loan1_cfinst_cnt_d30') AS DOUBLE)) AS app3_mix_loan1_cfinst_cnt_d30,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.advance_duotou_cnt_730d') AS DOUBLE)) AS advance_duotou_cnt_730d,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.advance_duotou_cnt_x_19') AS DOUBLE)) AS advance_duotou_cnt_x_19,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_bj_apply_count_1w') AS DOUBLE)) AS stgy_bj_apply_count_1w,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_bj_apply_jgs_12m') AS DOUBLE)) AS stgy_bj_apply_jgs_12m,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.stgy_bj_apply_jgs_1w') AS DOUBLE)) AS stgy_bj_apply_jgs_1w,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(outputdata, '$.android_oldCust_apply_subscore_charge_V6_1') AS DOUBLE)) AS android_oldCust_apply_subscore_charge_V6_1
  FROM (
    SELECT
      externalid,
      mid,
      inputdata,
      outputdata,
      etl_date,
      createtime,
      ROW_NUMBER() OVER (PARTITION BY externalid ORDER BY createtime) AS rn
    FROM ods.s21_risk_model_record
    WHERE modelmainid = 1627
      AND etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
      AND strategytype = 'CHAMPION'
  ) tt0
  WHERE rn = 1
  GROUP BY externalid, mid, etl_date
) t3 ON t0.externalid = t3.externalid
LEFT JOIN (
  SELECT
    externalid,
    mid,
    etl_date,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.income') AS DOUBLE)) AS income,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.baseinfo_userprof_age') AS DOUBLE)) AS baseinfo_userprof_age,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.baseinfo_has_car') AS DOUBLE)) AS baseinfo_has_car,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.baseinfo_has_house') AS DOUBLE)) AS baseinfo_has_house,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.baseinfo_marry') AS DOUBLE)) AS baseinfo_marry,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.baseinfo_employee_type') AS DOUBLE)) AS baseinfo_employee_type,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.baseinfo_userprof_degree') AS DOUBLE)) AS baseinfo_userprof_degree,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(outputdata, '$.android_oldCust_income_subscore_charge_V6_1') AS DOUBLE)) AS android_oldCust_income_subscore_charge_V6_1
  FROM (
    SELECT
      externalid,
      mid,
      inputdata,
      outputdata,
      etl_date,
      createtime,
      ROW_NUMBER() OVER (PARTITION BY externalid ORDER BY createtime) AS rn
    FROM ods.s21_risk_model_record
    WHERE modelmainid = 1632
      AND etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
      AND strategytype = 'CHAMPION'
  ) tt0
  WHERE rn = 1
  GROUP BY externalid, mid, etl_date
) t4 ON t0.externalid = t4.externalid
LEFT JOIN (
  SELECT
    externalid,
    mid,
    etl_date,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(outputdata, '$.android_oldCust_rule_score_charge_V6_1') AS DOUBLE)) AS android_oldCust_rule_score_charge_V6_1
  FROM (
    SELECT
      externalid,
      mid,
      inputdata,
      outputdata,
      etl_date,
      createtime,
      ROW_NUMBER() OVER (PARTITION BY externalid ORDER BY createtime) AS rn
    FROM ods.s21_risk_model_record
    WHERE modelmainid = 1636
      AND etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
      AND strategytype = 'CHAMPION'
  ) tt0
  WHERE rn = 1
  GROUP BY externalid, mid, etl_date
) t5 ON t0.externalid = t5.externalid
LEFT JOIN (
  SELECT
    externalid,
    mid,
    etl_date,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.m698_old_1t3_voting_0619rh') AS DOUBLE)) AS m698_old_1t3_voting_0619rh,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.pvalue_mex_b311_2025v1_p1') AS DOUBLE)) AS pvalue_mex_b311_2025v1_p1,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.pvalue_mex_b321_2026v2_p1') AS DOUBLE)) AS pvalue_mex_b321_2026v2_p1,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.pvalue_mex_b321_2026v1_p1') AS DOUBLE)) AS pvalue_mex_b321_2026v1_p1,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.m696_old_1t3_bj_iz_0530_p1') AS DOUBLE)) AS m696_old_1t3_bj_iz_0530_p1,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.pvalue_mex_b320_2026v1_long_p1') AS DOUBLE)) AS pvalue_mex_b320_2026v1_long_p1,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.m687_old_1t3_ad_tengo_0709p1') AS DOUBLE)) AS m687_old_1t3_ad_tengo_0709p1,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.pvalue_mex_b329_2026v1_byid_p1') AS DOUBLE)) AS pvalue_mex_b329_2026v1_byid_p1,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(outputdata, '$.android_oldCust_voting_score_charge_V6_1') AS DOUBLE)) AS android_oldCust_voting_score_charge_V6_1
  FROM (
    SELECT
      externalid,
      mid,
      inputdata,
      outputdata,
      etl_date,
      createtime,
      ROW_NUMBER() OVER (PARTITION BY externalid ORDER BY createtime) AS rn
    FROM ods.s21_risk_model_record
    WHERE modelmainid = 1633
      AND etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
      AND strategytype = 'CHAMPION'
  ) tt0
  WHERE rn = 1
  GROUP BY externalid, mid, etl_date
) t6 ON t0.externalid = t6.externalid
LEFT JOIN (
  SELECT
    externalid,
    mid,
    etl_date,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(inputdata, '$.pvalue_mex_b320_2026v2_p1') AS DOUBLE)) AS pvalue_mex_b320_2026v2_p1,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(outputdata, '$.android_oldCust_midCreditLevel_charge_V6_1') AS DOUBLE)) AS android_oldCust_midCreditLevel_charge_V6_1
  FROM (
    SELECT
      externalid,
      mid,
      inputdata,
      outputdata,
      etl_date,
      createtime,
      ROW_NUMBER() OVER (PARTITION BY externalid ORDER BY createtime) AS rn
    FROM ods.s21_risk_model_record
    WHERE modelmainid = 1634
      AND etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
      AND strategytype = 'CHAMPION'
  ) tt0
  WHERE rn = 1
  GROUP BY externalid, mid, etl_date
) t7 ON t0.externalid = t7.externalid
LEFT JOIN (
  SELECT
    externalid,
    mid,
    etl_date,
    MAX(TRY_CAST(JSON_EXTRACT_SCALAR(outputdata, '$.android_oldCust_mainCreditLevel_charge_V6_1') AS DOUBLE)) AS android_oldCust_mainCreditLevel_charge_V6_1
  FROM (
    SELECT
      externalid,
      mid,
      inputdata,
      outputdata,
      etl_date,
      createtime,
      ROW_NUMBER() OVER (PARTITION BY externalid ORDER BY createtime) AS rn
    FROM ods.s21_risk_model_record
    WHERE modelmainid = 1635
      AND etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
      AND strategytype = 'CHAMPION'
  ) tt0
  WHERE rn = 1
  GROUP BY externalid, mid, etl_date
) t8 ON t0.externalid = t8.externalid
;