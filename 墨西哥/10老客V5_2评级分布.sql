with t0 as (
select etl_date,
  externalid,
  case when length(externalid) = 16 then '进件' else '结清' end as tag,
  android_oldcust_maincreditlevel_charge_v5_2,
  android_oldcust_midcreditlevel_charge_v5_2,
--- 变量
  case when thirdparty_izi_whatsapp_register_status = 0 then -1 
    when thirdparty_izi_whatsapp_register_status != 0 then 0 end as thirdparty_izi_whatsapp_register_status_score,
  case when if_system_run_too_short >= 1 then -1 
    when if_system_run_too_short < 1 then 0 end as if_system_run_too_short_score,
  case when unique_email_cnt > 1 then -1 
    when unique_email_cnt <= 1 then 0 end as unique_email_cnt_score,
  case when history_loanrec_cnt_lastprepaydays_v2 <= -30 then -6
    when history_loanrec_cnt_lastprepaydays_v2 <= -2 then -4 
    when history_loanrec_cnt_lastprepaydays_v2 <= -1 then -3 
    when history_loanrec_cnt_lastprepaydays_v2 <= 0 then -1 
    when history_loanrec_cnt_lastprepaydays_v2 > 0 then 0 end as history_loanrec_cnt_lastprepaydays_v2_score,
  case when max_overdue_day_30d_all < 0 then -3 
    when max_overdue_day_30d_all >= 0 then 0 end as max_overdue_day_30d_all_score,
  case when max_ovd_days_all > 3 then -1 
    when max_ovd_days_all <= 3 then 0 end as max_ovd_days_all_score,
  case when af_uninstall_cnt_30d < 1 then 0 
    when af_uninstall_cnt_30d < 2 then -2 
    when af_uninstall_cnt_30d >= 2 then -3 end as af_uninstall_cnt_30d_score,
  case when last_repay_gap_days_app_group < 1 then 0 
    when last_repay_gap_days_app_group < 14 then 1 
    when last_repay_gap_days_app_group < 30 then 0 
    when last_repay_gap_days_app_group >= 30 then -3 end as last_repay_gap_days_app_group_score,
  case when minstay_repayplan_second_30d_mid < 10 then 0 
    when minstay_repayplan_second_30d_mid >= 10 then 1 else 0 end as minstay_repayplan_second_30d_mid_score,
  case when baseinfo_userprof_age < 35 then -1 
    when baseinfo_userprof_age <= 60 then 0 
    when baseinfo_userprof_age > 60 then 2 end as baseinfo_userprof_age_score,
  case when baseinfo_userprof_degree <= 3 then -1 
    when baseinfo_userprof_degree <= 4 then 0 
    when baseinfo_userprof_degree <= 5 then 1 
    when baseinfo_userprof_degree <= 6 then 2 end as baseinfo_userprof_degree_score,
  case when question3 > 5 then 1 
    when question3 <= 5 then 0 end as question3_score,
  case when question6_v2 >= 10 then 1 
    when question6_v2 < 10 then 0 end as question6_v2_score,
  case when advance_duotou_cnt_x_19 < 2 then 0 
    when advance_duotou_cnt_x_19 <= 6 then -1 
    when advance_duotou_cnt_x_19 > 6 then -4 end as advance_duotou_cnt_x_19_score,
  case when advance_duotou_cnt_730d < 0 then 0 
    when advance_duotou_cnt_730d < 3 then 3 
    when advance_duotou_cnt_730d <= 11 then 0 
    when advance_duotou_cnt_730d > 11 then -1 end as advance_duotou_cnt_730d_score,

--- 分数
  case when v5_fraud_score <= -8 then -5 
    when v5_fraud_score <= -7 then -4
    when v5_fraud_score <= -3 then -3
    when v5_fraud_score <= -2 THEN -1 
    WHEN v5_fraud_score <= -1 THEN 0 
    when v5_fraud_score > -1 then 1 end as v5_fraud_score_group,
  case when v5_behavior_score >= 3 then 2 
    when v5_behavior_score >= 1 then 1 
    when v5_behavior_score >= -4 then -1 
    when v5_behavior_score < -4 then -2 end as v5_behavior_score_group,
  case when m698_old_1t3_voting_0619rh < 0.185 then 1 
    when m698_old_1t3_voting_0619rh < 0.31 then 0 
    when m698_old_1t3_voting_0619rh < 0.455 then -1 
    when m698_old_1t3_voting_0619rh >= 0.455 then -3 end as m698_old_1t3_voting_0619rh_score,
  case when mex_b300_2025v2  < 0.18 then 1 
    when mex_b300_2025v2 < 0.39 then 0 
    when mex_b300_2025v2 < 0.475 then -1 
    when mex_b300_2025v2 >= 0.475 then -3 end as mex_b300_2025v2_score,
  case when pvalue_mex_b321_2026v1_p1 < 0.1762 then 1 
    when pvalue_mex_b321_2026v1_p1 < 0.2381 then 0 
    when pvalue_mex_b321_2026v1_p1 < 0.3287 then -1 
    when pvalue_mex_b321_2026v1_p1 >= 0.3287 then -3 end as pvalue_mex_b321_2026v1_p1_score,


CASE 
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.1977 THEN 1
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.2416 THEN 2
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.3167 THEN 3
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.3642 THEN 4
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.4178 THEN 5
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.4805 THEN 6
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.5031 THEN 7
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.5274 THEN 8
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.5662 THEN 9
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.5961 THEN 10
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.6308 THEN 11
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.6753 THEN 12
    WHEN pvalue_mex_b320_2026v1_long_p1 >= 0.6753 THEN 13 end as pvalue_mex_b320_2026v1_long_p1_group,
CASE 
    WHEN android_oldcust_rulescore_charge_v5_1 < -3 THEN 5
    WHEN android_oldcust_rulescore_charge_v5_1 >= -3 AND android_oldcust_rulescore_charge_v5_1 < -1 THEN 4
    WHEN android_oldcust_rulescore_charge_v5_1 >= -1 AND android_oldcust_rulescore_charge_v5_1 < 0 THEN 3
    WHEN android_oldcust_rulescore_charge_v5_1 >= 0 AND android_oldcust_rulescore_charge_v5_1 < 2 THEN 2
    WHEN android_oldcust_rulescore_charge_v5_1 >= 2 THEN 1 END AS android_oldcust_rulescore_charge_v5_1_group,
  case  
    WHEN android_oldcust_votescore_charge_v5_1 > 0 THEN 1
    WHEN android_oldcust_votescore_charge_v5_1 = 0 THEN 2
    WHEN android_oldcust_votescore_charge_v5_1 >= -2 AND android_oldcust_votescore_charge_v5_1 < 0 THEN 3
    WHEN android_oldcust_votescore_charge_v5_1 > -6 THEN 4 
    WHEN android_oldcust_votescore_charge_v5_1 <= -6 THEN 5 END as android_oldcust_votescore_charge_v5_1_group
from mx.android_oldCust_main_CreditLevel_charge_V5_2_param_table)

select
  etl_date,
  tag,
  thirdparty_izi_whatsapp_register_status_score,
  if_system_run_too_short_score,
  unique_email_cnt_score,
  history_loanrec_cnt_lastprepaydays_v2_score,
  max_overdue_day_30d_all_score,
  max_ovd_days_all_score,
  af_uninstall_cnt_30d_score,
  last_repay_gap_days_app_group_score,
  minstay_repayplan_second_30d_mid_score,
  baseinfo_userprof_age_score,
  baseinfo_userprof_degree_score,
  question3_score,
  question6_v2_score,
  advance_duotou_cnt_x_19_score,
  advance_duotou_cnt_730d_score,
  v5_fraud_score_group,
  v5_behavior_score_group,
  m698_old_1t3_voting_0619rh_score,
  mex_b300_2025v2_score,
  pvalue_mex_b321_2026v1_p1_score,
  pvalue_mex_b320_2026v1_long_p1_group,
  android_oldcust_rulescore_charge_v5_1_group,
  android_oldcust_votescore_charge_v5_1_group,
  android_oldcust_maincreditlevel_charge_v5_2,
  android_oldcust_midcreditlevel_charge_v5_2,
  count(distinct externalid) as cnt 
from t0
group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27