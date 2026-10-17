
--:{author=yuesong, department=墨西哥, dagName=sd_wenj_week, taskName=sd_wenj_week}
drop table if exists mx.sd_wenj_week
;
--:{author=yuesong, department=墨西哥, dagName=sd_wenj_week, taskName=sd_wenj_week}
create table mx.sd_wenj_week as 
select app_date,
  app_week,
  app_month,
  single_period_settle_time,
  date_trunc('week',date(single_period_settle_time)) as single_period_settle_week, --单期结清周
  case when new_media_source='Google' and app_group='Tuna Cash' then 'google_TC'
       when new_media_source='Google' and app_group='Balam Plata' then 'google_BP'
       when new_media_source='Google' and app_group='Mexcredo' then 'google_ME'
       when new_media_source='facebook' and app_group='Tuna Cash' then 'facebook_TC'
       when new_media_source='facebook' and app_group='Balam Plata' then 'facebook_BP'
       when new_media_source='facebook' and app_group='Mexcredo' then 'facebook_ME'
       when new_media_source='Google' and app_group='Mikredi' then 'google_MK'
       when new_media_source='facebook' and app_group='Mikredi' then 'facebook_MK'
  else 'qita'
  end as media_group,
  case when new_media_source='Google' then '谷歌'
       when new_media_source='facebook' then 'facebook'
       when new_media_source='tiktok' then 'tiktok'
       when new_media_source='多包互导' then '多包互导'
       when new_media_source='organic' then '自然流量'
       when new_media_source='bj'  then '冰鉴'
       when new_media_source='探知' then '探知'
       else '其他'
  end as new_media_source,
  
  tenant,
  source,
  case when app_group='YW' then 'YW'
       when app_group='Mexcredo' then 'ME'
       when app_group='Tuna Cash' then 'TC'
       when app_group='Balam Plata' then 'BP'
       when app_group='QuikPeso' then 'QP'
       when app_group='Mikredi' then 'MK'
       else '其他'
  end as app_group,
  product_level,
  sx_product_level,
  product_name,
  loan_cycle,
  cast(double_loan_2 as varchar) as double_loan_2,
  app_version,
  sd_creditlevel_main_v3_2,
  sd_creditlevel_main_v3_5,
  sd_cust_flag,
  case when sx_product_level is not null then 1 else 0 end as if_sx_flag,
  case when if_issue=1 then 1 else 0 end as if_issue_flag,
  case when should_capital < 1000 then '[0-1000)'
    when should_capital < 2000 then '[1000-2000)'
    when should_capital >= 3000 then '[2000,+)'
    else 'null' end as should_capital_group,
  case when repayment_clearing_count_index_tenant <= 0 then '[-inf-0]'
  	when repayment_clearing_count_index_tenant = 1 then '[1]'
    when repayment_clearing_count_index_tenant = 2 then '[2]'
    when repayment_clearing_count_index_tenant in (3,4) then '[3,4]'
    when repayment_clearing_count_index_tenant in (5,6) then '[5,6]' 
    when repayment_clearing_count_index_tenant in (7,8) then '[7,8]' 
    when repayment_clearing_count_index_tenant in (9,10) then '[9,10]' 
    when repayment_clearing_count_index_tenant >= 11 then '[11,inf]' end as repayment_clearing_count_index_tenant,
  case when mob < 0 then '[-inf-0)'
    when mob = 0 then '[0]'
  	when mob = 1 then '[1]'
    when mob = 2 then '[2]'
    when mob in (3,4) then '[3,4]'
    when mob in (5,6) then '[5,6]' 
    when mob >= 7 then '[7,inf]' end as mob,
  case when if_fu_sx_refuse_passed = 0 then '额度不足无效进件' else '有效进件' end as if_effective_tag,
  case when if_in_shou_anti_fraud=1 and if_shou_anti_fraud_passed=0 then '01.强反节点'
       when if_in_shou_anti_fraud_weak=1 and if_shou_anti_fraud_weak_passed=0 then '02.弱反节点'
       when if_in_shou_free_model=1 and if_shou_free_model_passed=0 then '03.免费模型节点'
       when if_in_shou_model=1 and if_shou_model_passed=0 then '04.低成本收费节点'
       when if_in_post_model=1 then cast(cast(sd_creditlevel_main_v3_2 AS integer) as varchar)
  end as group_flag_3_2,
  case when if_in_shou_anti_fraud=1 and if_shou_anti_fraud_passed=0 then '01.强反节点'
       when if_in_shou_anti_fraud_weak=1 and if_shou_anti_fraud_weak_passed=0 then '02.弱反节点'
       when if_in_shou_free_model=1 and if_shou_free_model_passed=0 then '03.免费模型节点'
       when if_in_shou_model=1 and if_shou_model_passed=0 then '04.低成本收费节点'
       when if_in_post_model=1 then cast(cast(sd_creditlevel_main_v3_4 AS integer) as varchar)
  end as group_flag_3_4,
case when date(create_time) >= date('2025-01-23') and date(create_time) < date('2025-02-21') then 'v1组'
    when date(create_time) >= date('2025-02-21') and date(create_time) < date('2025-03-05') and rand_no_74 < 5 then 'v1组'
    when date(create_time) >= date('2025-02-21') and date(create_time) < date('2025-03-05') and rand_no_74 >= 5 then 'v2组'
    when date(create_time) >= date('2025-03-05') and date(create_time) < date('2025-05-27') then 'v2组'
    when date(create_time) >= date('2025-05-27') and date(create_time) < date('2025-06-09') and rand_no_74 < 5 then 'v3组'
    when date(create_time) >= date('2025-05-27') and date(create_time) < date('2025-06-09') and rand_no_74 >= 5 then 'v2组'
    when date(create_time) >= date('2025-06-09') and date(create_time) < date('2025-06-12') then 'v3组'     
    when date(create_time) >= date('2025-06-12') and date(create_time) < date('2025-07-15') then 'v3_1组'
    when date(create_time) >= date('2025-07-15') and date(create_time) < date('2025-07-28') and rand_no_74 < 5 then 'v3_1组'
    when date(create_time) >= date('2025-07-15') and date(create_time) < date('2025-07-28') and rand_no_74 >= 5 then 'v3_2组'
    when date(create_time) >= date('2025-07-28') and date(create_time) < date('2025-08-08') then 'v3_2组'
    when date(create_time) >= date('2025-08-08') and date(create_time) < date('2025-08-30') and rand_no_74<3 then 'v3_3组'
    when date(create_time) >= date('2025-08-08') and date(create_time) < date('2025-08-30') and rand_no_74>=3 then 'v3_2组'
    when date(create_time) >= date('2025-08-30') and sd_approve_version_label='V_3_3' then 'v3_3组'
    when date(create_time) >= date('2025-08-30') and sd_approve_version_label='V_3_2' then 'v3_2组'
    when date(create_time) >= date('2025-08-30') and sd_approve_version_label='V_3_4' then 'v3_4组'
    end as strategy_flag_new,
    channel,
  sx_daily_interest,
  sx_fully_interest,
  disburse_daily_interest,
  disburse_fully_interest,
  max( substr(cast(current_timestamp as varchar),1,24) )as update_time,
  count(distinct biz_id) as cnt,
  count(distinct creditno_appchan) as person_cnt,
  sum(cast(grantcredit_7d_amount as double)) as grantcredit_7d_amount,
  sum(if(issue_date is not null,cast(grantcredit_7d_amount as double),0)) as grantcredit_7d_amount_1,
  sum(haircut_amount+should_interest) as should_interest_sum,
  sum(if_in_shou_anti_fraud) as if_in_shou_anti_fraud,
  sum(if_in_sx) as if_in_sx,
  sum(if_sx_passed_within24h) as if_sx_passed_within24h,
  sum(if_sx_passed) as if_sx_passed,
  sum(if_in_sx_over24h) as if_in_sx_over24h,
  sum(if_in_sx_over48h) as if_in_sx_over48h,
  sum(if_in_sx_over72h) as if_in_sx_over72h,
  sum(if_in_sx_over120h) as if_in_sx_over120h,
  sum(if_sx_passed_within48h) as if_sx_passed_within48h,
  sum(if_sx_passed_within72h) as if_sx_passed_within72h,
  sum(if_sx_passed_within120h) as if_sx_passed_within120h,
  sum(if_shou_model_passed) as if_shou_model_passed,
  sum(if_shou_external_data_passed) as if_shou_external_data_passed,
  --新增放款拒绝pass字段
  sum(if_shou_loan_refuse_reject_passed) as if_shou_loan_refuse_passed,

  sum(if_fu_external_data_passed) as if_fu_external_data_passed,
  sum(if_in_fu_anti_fraud) as if_in_fu_anti_fraud,
  sum(if_in_fu_sx_refuse) as if_in_fu_sx_refuse,
  sum(if_fu_model_passed) as if_fu_model_passed,
  sum(if_issue) as if_issue,
  sum(should_capital) as should_capital,
  sum(pre_p2_repay) as pre_p2_repay,
  sum(p2_repay) as p2_repay,
  sum(p2_repaytt) as p2_repaytt,
  sum(p1_repay) as p1_repay,
  sum(p0_repay) as p0_repay,
  sum(tpre3_fact_amount_1) as tpre3_fact_amount_1,
  sum(tpre2_fact_amount_1) as tpre2_fact_amount_1,
  sum(tpre1_fact_amount_1) as tpre1_fact_amount_1,
  sum(tpre0_fact_amount_1) as tpre0_fact_amount_1,
  cast(sum(should_amount) as double) as should_amount,
  count(if(issue_date is not null,biz_id,null)) as should_cnt,
  sum(if(is_t0_window_1 = 1,1,0)) as t0_should_cnt_1,
  sum(if(is_t3_window_1 = 1,1,0)) as t3_should_cnt_1,
  sum(if(is_t0_window_1 = 1,t0_overdue_amount_1,0)) as t0_overdue_amount_1,
  sum(if(is_t3_window_1 = 1,t3_overdue_amount_1,0)) as t3_overdue_amount_1,
  sum(if(is_t0_window_1 = 1,t0_should_amt_1,0)) as t0_should_amt_1,
  sum(if(is_t3_window_1 = 1,t3_should_amt_1,0)) as t3_should_amt_1,
  sum(if(is_t0_window_1 = 1,is_t0_overdue_1,0)) as is_t0_overdue_1,
  sum(if(is_t3_window_1 = 1,is_t3_overdue_1,0)) as is_t3_overdue_1,
  sum(if(is_t0_window_2 = 1,1,0)) as t0_should_cnt_2,
  sum(if(is_t3_window_2 = 1,1,0)) as t3_should_cnt_2,
  sum(if(is_t0_window_2 = 1,t0_overdue_amount_2,0)) as t0_overdue_amount_2,
  sum(if(is_t3_window_2 = 1,t3_overdue_amount_2,0)) as t3_overdue_amount_2,
  sum(if(is_t0_window_2 = 1,t0_should_amt_2,0)) as t0_should_amt_2,
  sum(if(is_t3_window_2 = 1,t3_should_amt_2,0)) as t3_should_amt_2,
  sum(if(is_t0_window_2 = 1,is_t0_overdue_2,0)) as is_t0_overdue_2,
  sum(if(is_t3_window_2 = 1,is_t3_overdue_2,0)) as is_t3_overdue_2,
  sum(if(is_t0_window_3 = 1,1,0)) as t0_should_cnt_3,
  sum(if(is_t3_window_3 = 1,1,0)) as t3_should_cnt_3,
  sum(if(is_t0_window_3 = 1,t0_overdue_amount_3,0)) as t0_overdue_amount_3,
  sum(if(is_t3_window_3 = 1,t3_overdue_amount_3,0)) as t3_overdue_amount_3,
  sum(if(is_t0_window_3 = 1,t0_should_amt_3,0)) as t0_should_amt_3,
  sum(if(is_t3_window_3 = 1,t3_should_amt_3,0)) as t3_should_amt_3,
  sum(if(is_t0_window_3 = 1,is_t0_overdue_3,0)) as is_t0_overdue_3,
  sum(if(is_t3_window_3 = 1,is_t3_overdue_3,0)) as is_t3_overdue_3,
  sum(if(is_t0_window_4 = 1,1,0)) as t0_should_cnt_4,
  sum(if(is_t3_window_4 = 1,1,0)) as t3_should_cnt_4,
  sum(if(is_t0_window_4 = 1,t0_overdue_amount_4,0)) as t0_overdue_amount_4,
  sum(if(is_t3_window_4 = 1,t3_overdue_amount_4,0)) as t3_overdue_amount_4,
  sum(if(is_t0_window_4 = 1,t0_should_amt_4,0)) as t0_should_amt_4,
  sum(if(is_t3_window_4 = 1,t3_should_amt_4,0)) as t3_should_amt_4,
  sum(if(is_t0_window_4 = 1,is_t0_overdue_4,0)) as is_t0_overdue_4,
  sum(if(is_t3_window_4 = 1,is_t3_overdue_4,0)) as is_t3_overdue_4,
  sum(if(should_capital is not null and should_capital != 0,credit_amount,0)) as issue_global_limit_sum,
  sum(quota_use_rate) as quota_use_rate,
  sum(if_single_period_settle) as if_single_period_settle,
  sum(if_single_period_settle_reloan) as if_single_period_settle_reloan,
  sum(if_single_period_settle_reloan_within24h) as if_single_period_settle_reloan_within24h,
  sum(if_single_period_settle_reloan_within120h) as if_single_period_settle_reloan_within120h,
  sum(if_single_period_settle_reloan_within720h) as if_single_period_settle_reloan_within720h,


  sum(if_settle_reloan_by_credit) as if_settle_reloan_by_credit,  
  sum(if_settle_reloan_by_credit_24h) as if_settle_reloan_by_credit_24h,  
  sum(if_settle_reloan_by_credit_120h) as if_settle_reloan_by_credit_120h, 
  sum(if_settle_reloan_by_credit_720h) as if_settle_reloan_by_credit_720h,  


  sum(if_settle_reloan_by_apply) as if_settle_reloan_by_apply, 
  sum(if_settle_reloan_by_apply_24h) as if_settle_reloan_by_apply_24h, 
  sum(if_settle_reloan_by_apply_120h) as if_settle_reloan_by_apply_120h,
  sum(if_settle_reloan_by_apply_720h) as if_settle_reloan_by_apply_720h,

  sum(if_settle_reloan_by_issue) as if_settle_reloan_by_issue, 
  sum(if_settle_reloan_by_issue_24h) as if_settle_reloan_by_issue_24h, 
  sum(if_settle_reloan_by_issue_120h) as if_settle_reloan_by_issue_120h,
  sum(if_settle_reloan_by_issue_720h) as if_settle_reloan_by_issue_720h,

  ---新增本金口径
  --应还本金
  sum(if(is_t0_window_1 = 1, t0_should_capit_1, 0)) as t0_should_capit_1,--T0
  sum(if(is_t0_window_2 = 1, t0_should_capit_2, 0)) as t0_should_capit_2,
  sum(if(is_t0_window_3 = 1, t0_should_capit_3, 0)) as t0_should_capit_3,
  sum(if(is_t0_window_4 = 1, t0_should_capit_4, 0)) as t0_should_capit_4,
  
  sum(if(is_t3_window_1 = 1, t3_should_capit_1, 0)) as t3_should_capit_1,  --T3
  sum(if(is_t3_window_2 = 1, t3_should_capit_2, 0)) as t3_should_capit_2,
  sum(if(is_t3_window_3 = 1, t3_should_capit_3, 0)) as t3_should_capit_3,
  sum(if(is_t3_window_4 = 1, t3_should_capit_4, 0)) as t3_should_capit_4,

  --逾期本金
  sum(if(is_t0_window_1 = 1, t0_overdue_capit_1, 0)) as t0_overdue_capit_1,  --T0
  sum(if(is_t0_window_2 = 1, t0_overdue_capit_2, 0)) as t0_overdue_capit_2,
  sum(if(is_t0_window_3 = 1, t0_overdue_capit_3, 0)) as t0_overdue_capit_3,
  sum(if(is_t0_window_4 = 1, t0_overdue_capit_4, 0)) as t0_overdue_capit_4,

  sum(if(is_t3_window_1 = 1, t3_overdue_capit_1, 0)) as t3_overdue_capit_1,  --T3
  sum(if(is_t3_window_2 = 1, t3_overdue_capit_2, 0)) as t3_overdue_capit_2,
  sum(if(is_t3_window_3 = 1, t3_overdue_capit_3, 0)) as t3_overdue_capit_3,
  sum(if(is_t3_window_4 = 1, t3_overdue_capit_4, 0)) as t3_overdue_capit_4,


  sum(credit_amount) as credit_amount
from(
select tt0.*,
  tt1.first_issue_date,
  repayment_clearing_count_index_tenant,
  ceiling(date_diff('day',first_issue_date,create_time)/7) as mob,
  -- fd_inloan_order_amount_tenant,
  -- global_limit,
  sd_creditlevel_main_v3_2,
  sd_creditlevel_main_v3_4,
  sd_creditlevel_main_v3_5,
  sd_approve_version_label,
  rand_no_74,
  tt7.single_period_settle_time,
  if_single_period_settle,
  if_single_period_settle_reloan,
  if_single_period_settle_reloan_within24h,
  if_single_period_settle_reloan_within120h,
  if_single_period_settle_reloan_within720h,
  if_settle_reloan_by_credit,  
  if_settle_reloan_by_credit_24h,  
  if_settle_reloan_by_credit_120h, 
  if_settle_reloan_by_credit_720h,  
  if_settle_reloan_by_apply, 
  if_settle_reloan_by_apply_24h, 
  if_settle_reloan_by_apply_120h,
  if_settle_reloan_by_apply_720h,
  if_settle_reloan_by_issue, 
  if_settle_reloan_by_issue_24h, 
  if_settle_reloan_by_issue_120h,
  if_settle_reloan_by_issue_720h,

  sd_cust_flag,
  one_click_loan_tag,
  tt10.channel,
  if(should_capital is not null and should_capital != 0,should_capital,0)/if(should_capital is not null and should_capital != 0,grantcredit_amount,1e-5) as quota_use_rate
from(
select *,
  row_number() over(partition by creditno_appchan order by create_time) as rn 
from(
select a.*,b.product_level as sx_product_level,
CASE 
    WHEN product_name = 'D_0_05' then 0.041
    WHEN product_name = 'D_0_06' then 0.062
    WHEN product_name = 'D_0_07' then 0
    WHEN SUBSTRING(product_name, 1, 1) = 'A' THEN 0
    WHEN product_name = 'B1' THEN 0
    WHEN SUBSTRING(product_name, 1, 1) IN ('B', 'C') THEN 
        
            ROUND(
                CAST(SUBSTRING(product_name, -2, 2) AS double) * 1.16 / 
                (CAST(SUBSTRING(product_name, 7, 1) AS double) * 
                CAST(SUBSTRING(product_name, 4, 1) AS double))/100,
                3
            )    
    WHEN SUBSTRING(product_name, 1, 1) = 'E' THEN 
        
            ROUND(CAST(SUBSTRING(product_name, 9, 2) AS double) / 1000, 3)
                  
    ELSE NULL
END AS disburse_daily_interest,
CASE 
    WHEN product_name = 'D_0_05' then 0.041 * 21
    WHEN product_name = 'D_0_06' then 0.062 * 14
    WHEN product_name = 'D_0_07' then 0
    WHEN SUBSTRING(product_name, 1, 1) = 'A' THEN 0
    WHEN product_name = 'B1' THEN 0
    WHEN SUBSTRING(product_name, 1, 1) IN ('B', 'C') THEN 
            ROUND(
                CAST(SUBSTRING(product_name, -2, 2) AS double) * 1.16 /100 ,3 )
        
    WHEN SUBSTRING(product_name, 1, 1) = 'E' THEN 
        
            ROUND(CAST(SUBSTRING(product_name, 9, 2) AS double) / 1000, 3) * CAST(SUBSTRING(product_name, 4, 1) AS double) * CAST(SUBSTRING(product_name, 7, 1) AS double)
            
    ELSE NULL
END AS disburse_fully_interest,
CASE 
    WHEN b.product_level = 'D_0_05' then 0.041
    WHEN b.product_level = 'D_0_06' then 0.062
    WHEN b.product_level = 'D_0_07' then 0
    WHEN SUBSTRING(b.product_level, 1, 1) = 'A' THEN 0
    WHEN b.product_level = 'B1' THEN 0
    WHEN SUBSTRING(b.product_level, 1, 1) IN ('B', 'C') THEN 
        
            ROUND(
                CAST(SUBSTRING(b.product_level, -2, 2) AS double) * 1.16 / 
                (CAST(SUBSTRING(b.product_level, 7, 1) AS double) * 
                CAST(SUBSTRING(b.product_level, 4, 1) AS double))/100,
                3
            )    
    WHEN SUBSTRING(b.product_level, 1, 1) = 'E' THEN 
        
            ROUND(CAST(SUBSTRING(b.product_level, 9, 2) AS double) / 1000, 3)
                  
    ELSE NULL
END AS sx_daily_interest,
CASE 
    WHEN b.product_level = 'D_0_05' then 0.041 * 21
    WHEN b.product_level = 'D_0_06' then 0.062 * 14
    WHEN b.product_level = 'D_0_07' then 0
    WHEN SUBSTRING(b.product_level, 1, 1) = 'A' THEN 0
    WHEN b.product_level = 'B1' THEN 0
    WHEN SUBSTRING(b.product_level, 1, 1) IN ('B', 'C') THEN 
            ROUND(
                CAST(SUBSTRING(b.product_level, -2, 2) AS double) * 1.16 /100 ,3 )
        
    WHEN SUBSTRING(b.product_level, 1, 1) = 'E' THEN 
        
            ROUND(CAST(SUBSTRING(b.product_level, 9, 2) AS double) / 1000, 3) * CAST(SUBSTRING(b.product_level, 4, 1) AS double) * CAST(SUBSTRING(b.product_level, 7, 1) AS double)
            
    ELSE NULL
END AS sx_fully_interest
from mx.darren_risk_wide_table a left join mx.wenj_sd_feature_credit b 
on a.biz_id=b.externalid10
where date_diff('day',date(create_time),current_date) <= 365 and date_diff('day',date(create_time),current_date) >= 1 ) t0) tt0 
left join (
select creditno_appchan,
  issue_date as first_issue_date,
  row_number() over(partition by creditno_appchan order by create_time) as rn 
from(
select *
from mx.darren_risk_wide_table
where date_diff('day',date(issue_date),current_date) <= 365
and double_loan_2 = 0) t0) tt1 
on tt0.creditno_appchan = tt1.creditno_appchan 
left join (
select biz_id,
  repayment_clearing_count_index_tenant
from mx.darren_behave_var) tt2 
on tt0.biz_id = tt2.biz_id
-- left join (SELECT
-- externalid
-- ,max(cast(json_extract(outputdata,'$.grantcredit_7d_amount') as integer)) as grantcredit_7d_amount
-- ,max(cast(json_extract(inputdata,'$.global_limit') as integer)) as global_limit
-- -- ,max(cast(json_extract(inputdata,'$.repayment_clearing_count_index_tenant') as integer)) as repayment_clearing_count_index_tenant
-- FROM ods.s21_risk_strategy_record 
-- where createtime>=cast('2025-02-21 22:00:00.000' as timestamp)
-- and etl_date >= '20250221'
-- and productid in (196) 
-- and strategytype='CHAMPION'
-- group by 1) tt3
-- on tt0.biz_id = tt3.externalid
-- left join (SELECT externalid,
--   max(cast(json_extract(outputdata, '$.fd_inloan_order_amount_tenant') as double)) as fd_inloan_order_amount_tenant
-- FROM ods.s21_risk_strategy_record 
-- where productid=355
-- and strategytype='CHAMPION'
-- and etl_date>='20250428'
-- group by 1) tt4 
-- on tt0.biz_id = tt4.externalid
left join (select 
externalid7,sd_creditlevel_main_v3_2,sd_creditlevel_main_v3_4,sd_creditlevel_main_v3_5,rand_no_74 from 
mx.wenj_sd_market
)tt5 
on tt0.biz_id = tt5.externalid7
left join (select externalid,sd_approve_version_label from mx.sd_wenj_approve_version_label) tt6 
on tt0.biz_id = tt6.externalid
left join 
(
-- 计算结清复借率，24h结清复借率等
SELECT
    t0.biz_id AS bid_id7,
    MAX(t1.single_period_settle_time) AS single_period_settle_time,   -- 新增：结清时间
    MAX(t1.if_single_period_settle) AS if_single_period_settle,
    -- 是否发生复借（不限时间）
    MAX(CASE WHEN (t3.one_click_loan_tag = '1' AND t2.if_sx_passed = 1 AND t1.single_period_settle_time < t2.apply_time)
            OR (t2.biz_id is not null and COALESCE(t3.one_click_loan_tag, '0') != '1' AND t1.single_period_settle_time < t2.create_time) THEN 1 ELSE 0 END) AS if_single_period_settle_reloan,
    -- 24小时内复借
    MAX(CASE WHEN (t3.one_click_loan_tag = '1' AND t2.if_sx_passed = 1 AND t1.single_period_settle_time < t2.apply_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.apply_time) <= 24 * 60) OR (t2.biz_id is not null and COALESCE(t3.one_click_loan_tag, '0') != '1' AND t1.single_period_settle_time < t2.create_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.create_time) <= 24 * 60) THEN 1 ELSE 0 END) AS if_single_period_settle_reloan_within24h,
    -- 120小时内复借
    MAX(CASE WHEN (t3.one_click_loan_tag = '1' AND t2.if_sx_passed = 1 AND t1.single_period_settle_time < t2.apply_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.apply_time) <= 120 * 60) OR (t2.biz_id is not null and COALESCE(t3.one_click_loan_tag, '0') != '1' AND t1.single_period_settle_time < t2.create_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.create_time) <= 120 * 60) THEN 1 ELSE 0 END) AS if_single_period_settle_reloan_within120h,
    -- 720小时内复借
    MAX(CASE WHEN (t3.one_click_loan_tag = '1' AND t2.if_sx_passed = 1 AND t1.single_period_settle_time < t2.apply_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.apply_time) <= 720 * 60) OR (t2.biz_id is not null and COALESCE(t3.one_click_loan_tag, '0') != '1' AND t1.single_period_settle_time < t2.create_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.create_time) <= 720 * 60) THEN 1 ELSE 0 END) AS if_single_period_settle_reloan_within720h,

  --- 统一取到用信

  MAX(CASE WHEN t2.if_sx_passed = 1 AND t1.single_period_settle_time < t2.apply_time THEN 1 ELSE 0 END) AS if_settle_reloan_by_credit,  -- 1. 是否发生复借（不限时间）
  MAX(CASE WHEN t2.if_sx_passed = 1 AND t1.single_period_settle_time < t2.apply_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.apply_time) <= 24 * 60 THEN 1 ELSE 0 END) AS if_settle_reloan_by_credit_24h,   -- 2. 24小时内复借
  MAX(CASE WHEN t2.if_sx_passed = 1 AND t1.single_period_settle_time < t2.apply_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.apply_time) <= 120 * 60 THEN 1 ELSE 0 END) AS if_settle_reloan_by_credit_120h,  -- 3. 120小时内复借
  MAX(CASE WHEN t2.if_sx_passed = 1 AND t1.single_period_settle_time < t2.apply_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.apply_time) <= 720 * 60 THEN 1 ELSE 0 END) AS if_settle_reloan_by_credit_720h,  -- 4. 720小时内复借
  --- 统一取到进件

  MAX(CASE WHEN t2.biz_id is not null AND t1.single_period_settle_time < t2.create_time THEN 1 ELSE 0 END) AS if_settle_reloan_by_apply, -- 1. 是否发生复借（不限时间）
  MAX(CASE WHEN t2.biz_id is not null AND t1.single_period_settle_time < t2.create_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.create_time) <= 24 * 60 THEN 1 ELSE 0 END) AS if_settle_reloan_by_apply_24h, -- 2. 24小时内复借
  MAX(CASE WHEN t2.biz_id is not null AND t1.single_period_settle_time < t2.create_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.create_time) <= 120 * 60 THEN 1 ELSE 0 END) AS if_settle_reloan_by_apply_120h,-- 3. 120小时内复借
  MAX(CASE WHEN t2.biz_id is not null AND t1.single_period_settle_time < t2.create_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.create_time) <= 720 * 60 THEN 1 ELSE 0 END) AS if_settle_reloan_by_apply_720h, -- 4. 720小时内复借

  --- 统一取到放款

  MAX(CASE WHEN t2.biz_id is not null AND t1.single_period_settle_time < t2.release_time AND t2.if_issue = 1 THEN 1 ELSE 0 END) AS if_settle_reloan_by_issue, -- 1. 是否发生复借（不限时间）
  MAX(CASE WHEN t2.biz_id is not null AND t1.single_period_settle_time < t2.release_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.release_time) <= 24 * 60 AND t2.if_issue = 1 THEN 1 ELSE 0 END) AS if_settle_reloan_by_issue_24h, -- 2. 24小时内复借
  MAX(CASE WHEN t2.biz_id is not null AND t1.single_period_settle_time < t2.release_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.release_time) <= 120 * 60 AND t2.if_issue = 1 THEN 1 ELSE 0 END) AS if_settle_reloan_by_issue_120h,-- 3. 120小时内复借
  MAX(CASE WHEN t2.biz_id is not null AND t1.single_period_settle_time < t2.release_time AND DATE_DIFF('minute', t1.single_period_settle_time, t2.release_time) <= 720 * 60 AND t2.if_issue = 1 THEN 1 ELSE 0 END) AS if_settle_reloan_by_issue_720h -- 4. 720小时内复借

FROM (
    -- 近365天的原始订单
    SELECT biz_id,mid
    FROM mx.darren_risk_wide_table
    WHERE DATE_DIFF('day', DATE(issue_date), CURRENT_DATE) <= 365
) t0
LEFT JOIN (
    -- 结清状态及结清时间（按订单聚合）
    SELECT CAST(camera_id AS BIGINT) AS camera_id,
        MIN(CASE WHEN state IN (1, 3) THEN fact_time ELSE NULL END) AS single_period_settle_time,
        MAX(CASE WHEN state IN (1, 3) THEN 1 ELSE 0 END) AS if_single_period_settle
    FROM ods_view_presto.s02_loan_repayment
    WHERE fact_time IS NOT NULL
      AND DATE_DIFF('day', DATE(create_time), CURRENT_DATE) <= 365
    GROUP BY 1) t1
    ON t0.biz_id = CAST(t1.camera_id AS VARCHAR)
LEFT JOIN (
    -- 潜在复借订单（近365天）
    SELECT biz_id,mid,create_time,if_sx_passed,apply_time,if_issue,release_time
    FROM mx.darren_risk_wide_table
    WHERE DATE_DIFF('day', DATE(create_time), CURRENT_DATE) <= 365) t2
    ON t0.mid = t2.mid
    AND t1.if_single_period_settle = 1    -- 仅当原订单已结清才考虑复借
    and t1.single_period_settle_time < t2.create_time
LEFT JOIN mx.tmp_one_click_loan_tag t3
ON t2.biz_id = CAST(t3.biz_id AS VARCHAR)
GROUP BY 1
) tt7 
on tt0.biz_id = tt7.bid_id7 
left join mx.sd_good_cust_base tt8
on tt0.biz_id = tt8.externalid 
left join mx.tmp_one_click_loan_tag tt9 
on tt0.biz_id = cast(tt9.biz_id as varchar)
left join mx.install_channel tt10
on tt0.mid=tt10.mid
) ttt1 
group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33
;