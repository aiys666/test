
--:{author=tudalun, department=墨西哥风险策略, dagName=android_oldcust_main_creditlevel_charge_v5_1_param_table, taskName=android_oldcust_main_creditlevel_charge_v5_3}
delete from mx.android_oldCust_mainCreditLevel_charge_V5_3_table
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
;
--:{author=tudalun, department=墨西哥风险策略, dagName=android_oldcust_main_creditlevel_charge_v5_1_param_table, taskName=android_oldcust_main_creditlevel_charge_v5_3}
insert into mx.android_oldCust_mainCreditLevel_charge_V5_3_table
select t0.externalid,
  t0.mid,
  t0.createtime,
  V5_3_fraud_score,
  V5_3_behavior_score,
  android_oldCust_voteScore_charge_V5_3,
  android_oldCust_mainCreditLevel_charge_V5_3,
  android_oldCust_midCreditLevel_charge_V5_3,
  android_oldCust_ruleScore_charge_V5_3,
  pvalue_mex_b321_2026v1_p1,
  pvalue_mex_b320_2026v1_long_p1,
  mex_b300_2025v2,
  m698_old_1t3_voting_0619rh,
  thirdparty_izi_whatsapp_register_status,
  if_system_run_too_short,
  unique_email_cnt,
  history_loanrec_cnt_lastprepaydays_v2,
  max_overdue_day_30d_all,
  max_ovd_days_all,
  af_uninstall_cnt_30d,
  last_repay_gap_days_app_group,
  minstay_repayplan_second_30d_mid,
  baseinfo_userprof_age,
  baseinfo_userprof_degree,
  question3,
  question6_v2,
  advance_duotou_cnt_730d,
  advance_duotou_cnt_x_19,
  applist_casino_cnt,
  t0.etl_date
from (
select externalid,
  mid,
  max(try_cast(json_extract_scalar(inputdata,'$.max_ovd_days_all') as double)) max_ovd_days_all,
  max(try_cast(json_extract_scalar(inputdata,'$.af_uninstall_cnt_30d') as double)) af_uninstall_cnt_30d,
  max(try_cast(json_extract_scalar(inputdata,'$.history_loanrec_cnt_lastprepaydays_v2') as double)) history_loanrec_cnt_lastprepaydays_v2,
  max(try_cast(json_extract_scalar(inputdata,'$.unique_email_cnt') as double)) unique_email_cnt,
  max(try_cast(json_extract_scalar(inputdata,'$.thirdparty_izi_whatsapp_register_status') as double)) thirdparty_izi_whatsapp_register_status,
  max(try_cast(json_extract_scalar(inputdata,'$.max_overdue_day_30d_all') as double)) max_overdue_day_30d_all,
  max(try_cast(json_extract_scalar(inputdata,'$.if_system_run_too_short') as double)) if_system_run_too_short,
  max(try_cast(json_extract_scalar(inputdata,'$.applist_casino_cnt') as double)) applist_casino_cnt,
  max(try_cast(json_extract_scalar(outputdata,'$.V5_3_fraud_score') as double)) V5_3_fraud_score,
  etl_date,
  createtime
  from (select externalid,
    mid,
    inputdata,
    outputdata,
    etl_date,
    createtime,
    row_number() over(partition by externalid order by createtime) as rn 
    from ods.s21_risk_model_record
    where modelmainid = 1540
    -- and etl_date >= '20260509'
    and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
    and strategytype = 'CHAMPION') tt0
    where rn = 1 
group by 1,2,etl_date,createtime) t0 
left join (
select externalid,
  mid,
  max(try_cast(json_extract_scalar(inputdata,'$.baseinfo_userprof_age') as double)) baseinfo_userprof_age,
  max(try_cast(json_extract_scalar(inputdata,'$.last_repay_gap_days_app_group') as double)) last_repay_gap_days_app_group,
  max(try_cast(json_extract_scalar(inputdata,'$.minstay_repayplan_second_30d_mid') as double)) minstay_repayplan_second_30d_mid,
  max(try_cast(json_extract_scalar(inputdata,'$.baseinfo_userprof_degree') as double)) baseinfo_userprof_degree,
  max(try_cast(json_extract_scalar(inputdata,'$.advance_duotou_cnt_x_19') as double)) advance_duotou_cnt_x_19,
  max(try_cast(json_extract_scalar(inputdata,'$.advance_duotou_cnt_730d') as double)) advance_duotou_cnt_730d,
  max(try_cast(json_extract_scalar(inputdata,'$.question3') as double)) question3,
  max(try_cast(json_extract_scalar(inputdata,'$.question6_v2') as double)) question6_v2,
  max(try_cast(json_extract_scalar(outputdata,'$.V5_3_behavior_score') as double)) V5_3_behavior_score,
  etl_date,
  createtime
    from (select externalid,
    mid,
    inputdata,
    outputdata,
    etl_date,
    createtime,
    row_number() over(partition by externalid order by createtime) as rn 
    from ods.s21_risk_model_record
    where modelmainid = 1539
    -- and etl_date >= '20260509'
    and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
    and strategytype = 'CHAMPION') tt0
    where rn = 1 
group by 1,2,etl_date,createtime) t1 
on t0.externalid = t1.externalid

left join (
select externalid,
  mid,
  max(try_cast(json_extract_scalar(inputdata,'$.android_oldCust_ruleScore_charge_V5_3') as double)) android_oldCust_ruleScore_charge_V5_3,
  max(try_cast(json_extract_scalar(inputdata,'$.pvalue_mex_b320_2026v1_long_p1') as double)) pvalue_mex_b320_2026v1_long_p1,
  max(try_cast(json_extract_scalar(outputdata,'$.android_oldCust_midCreditLevel_charge_V5_3') as double)) android_oldCust_midCreditLevel_charge_V5_3,
  etl_date,
  createtime
    from (select externalid,
    mid,
    inputdata,
    outputdata,
    etl_date,
    createtime,
    row_number() over(partition by externalid order by createtime) as rn 
    from ods.s21_risk_model_record
    where modelmainid = 1543
    -- and etl_date >= '20260509'
    and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
    and strategytype = 'CHAMPION') tt0
    where rn = 1
group by 1,2,etl_date,createtime) t2
on t0.externalid = t2.externalid

left join (
select externalid,
  mid,
  max(try_cast(json_extract_scalar(inputdata,'$.mex_b300_2025v2') as double)) mex_b300_2025v2,
  max(try_cast(json_extract_scalar(inputdata,'$.m698_old_1t3_voting_0619rh') as double)) m698_old_1t3_voting_0619rh,
  max(try_cast(json_extract_scalar(inputdata,'$.pvalue_mex_b321_2026v1_p1') as double)) pvalue_mex_b321_2026v1_p1,
  max(try_cast(json_extract_scalar(outputdata,'$.android_oldCust_voteScore_charge_V5_3') as double)) android_oldCust_voteScore_charge_V5_3,
  etl_date,
  createtime
    from (select externalid,
    mid,
    inputdata,
    outputdata,
    etl_date,
    createtime,
    row_number() over(partition by externalid order by createtime) as rn 
    from ods.s21_risk_model_record
    where modelmainid = 1537
    -- and etl_date >= '20260509'
    and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
    and strategytype = 'CHAMPION') tt0
    where rn = 1 
group by 1,2,etl_date,createtime) t3
on t0.externalid = t3.externalid

left join (
select externalid,
  mid,
  max(try_cast(json_extract_scalar(outputdata,'$.android_oldCust_mainCreditLevel_charge_V5_3') as double)) android_oldCust_mainCreditLevel_charge_V5_3,
  etl_date,
  createtime
    from (select externalid,
    mid,
    inputdata,
    outputdata,
    etl_date,
    createtime,
    row_number() over(partition by externalid order by createtime) as rn 
    from ods.s21_risk_model_record
    where modelmainid = 1542
    -- and etl_date >= '20260509'
    and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
    and strategytype = 'CHAMPION') tt0
    where rn = 1 
group by 1,2,etl_date,createtime) t4
on t0.externalid = t4.externalid
;