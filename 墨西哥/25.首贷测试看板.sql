
--:{author=wenjing, department=墨西哥, dagName=wenj_risk_wide_table, taskName=sd_test_data}
drop table if EXISTS mx.sd_test_data
;
--:{author=wenjing, department=墨西哥, dagName=wenj_risk_wide_table, taskName=sd_test_data}
create table mx.sd_test_data as 
select 
  date_trunc('month',date(create_time)) as monthh,
	date_trunc('week',date(create_time)) as weekk,
  date(create_time) as datee,
  t23.google_reg_channel,
  t22.free_scorecard,
  case when t22.free_scorecard<=-10 then '00.<=-10' when t22.free_scorecard>-10 and t22.free_scorecard<=-1 then '01.<=-1' when t22.free_scorecard>-1 and t22.free_scorecard<=1 then '02.<=1' when t22.free_scorecard>1 then '03.>1' end as free_scorecard_bin,
  --case when product_level in ('A1','B1') then '短期' else '长期' end as product_level_flag,
  qq.product_level_org,
  t0.product_level,
  product_name,
  t1.message_type,
  case when if_in_shou_anti_fraud=1 and if_shou_anti_fraud_passed=0 then '01.强反节点'
       when if_in_shou_anti_fraud_weak=1 and if_shou_anti_fraud_weak_passed=0 then '02.弱反节点'
       when if_in_shou_free_model=1 and if_shou_free_model_passed=0 then '03.免费模型节点'
       when if_in_shou_model=1 and if_shou_model_passed=0 then '04.低成本收费节点'
       when if_in_post_model=1 then cast(cast(t4.android_newCust_mainCreditLevel_charge_V5_1 AS integer) as varchar)
  end as group_flag_5_1,
  case when cast(should_capital as double) <= 300 then '1_(inf,300]' 
     when cast(should_capital as double) <= 400 then '2_(300,400]'
     when cast(should_capital as double) <= 500 then '3_(400,500]'
     when cast(should_capital as double) <= 600 then '4_(500,600]'
     when cast(should_capital as double) <= 700 then '5_(600,700]'
     when cast(should_capital as double) <= 800 then '6_(700,800]'
     when cast(should_capital as double) <= 1000 then '7_(800,1000]'
     when cast(should_capital as double) <= 2000 then '8_(1000,2000]'
     when cast(should_capital as double) <= 3000 then '9_(2000,3000]'
     when cast(should_capital as double) <= 4000 then '10_(3000,4000]'
     when cast(should_capital as double) > 4000 then '11_(4000,inf)' end as grantcredit_7d_amount_range,
  CASE 
    WHEN sd_quota_test_label = 'V5_5_1' THEN
        CASE 
            WHEN t13.rand_no_77 < 7 THEN '低额度组'
            WHEN t13.rand_no_77 >= 7 THEN '高额度组'
            ELSE NULL  
        END
    WHEN sd_quota_test_label = 'V5_3_1' THEN
        CASE 
            WHEN t13.rand_no_77 < 7 THEN '低额度组'
            WHEN t13.rand_no_77 >= 7 THEN '高额度组'
            ELSE NULL  
        END
    WHEN sd_quota_test_label = 'V5_2_1' THEN
        CASE 
            WHEN t13.rand_no_77 < 5 THEN '低额度组'
            WHEN t13.rand_no_77 >= 5 THEN '高额度组'
            ELSE NULL  
        END
    WHEN sd_quota_test_label = 'V4_3_1' THEN   
        CASE 
            WHEN t13.rand_no_77 < 5 THEN '低额度组'
            WHEN t13.rand_no_77 >= 5 THEN '高额度组'
            ELSE NULL  
        END
    WHEN sd_quota_test_label = 'V4_1_1' THEN
        CASE 
            WHEN t13.rand_no_77 < 5 THEN '低额度组'
            WHEN t13.rand_no_77 >= 5 THEN '高额度组'
            ELSE NULL  
        END
    WHEN sd_quota_test_label = 'V3_6_2' THEN
        CASE 
            WHEN t13.rand_no_77 < 8 THEN '低额度组'
            WHEN t13.rand_no_77 >= 8 THEN '高额度组'
            ELSE NULL  
        END
    WHEN sd_quota_test_label = 'V3_6_1' THEN
        CASE 
            WHEN t13.rand_no_77 < 9 THEN '低额度组'
            WHEN t13.rand_no_77 >= 9 THEN '高额度组'
            ELSE NULL  
        END
    ELSE
        CASE 
            WHEN sd_approve_version_label = 'V_4_1' AND t13.rand_no_77 < 8 THEN '低额度组'
            WHEN sd_approve_version_label = 'V_4_1' AND t13.rand_no_77 >= 8 THEN '高额度组'
            WHEN sd_approve_version_label = 'V_4' AND t13.rand_no_77 < 8 THEN '低额度组'
            WHEN sd_approve_version_label = 'V_4' AND t13.rand_no_77 >= 8 THEN '高额度组'
            WHEN sd_approve_version_label = 'V_3_6' AND t13.rand_no_77 < 5 THEN '低额度组'
            WHEN sd_approve_version_label = 'V_3_6' AND t13.rand_no_77 >= 5 THEN '高额度组'
            WHEN date(create_time) >= date('2025-10-29') AND sd_approve_version_label = 'V_3_5' AND t13.rand_no_77 < 5 THEN '低额度组'
            WHEN date(create_time) >= date('2025-10-29') AND sd_approve_version_label = 'V_3_5' AND t13.rand_no_77 >= 5 THEN '高额度组'
            WHEN sd_approve_version_label = 'V_3_5' AND t13.rand_no_77 < 7 THEN '低额度组'
            WHEN sd_approve_version_label = 'V_3_5' AND t13.rand_no_77 >= 7 THEN '高额度组'
            WHEN sd_approve_version_label = 'V_3_4' AND t13.rand_no_77 < 7 THEN '低额度组'
            WHEN sd_approve_version_label = 'V_3_4' AND t13.rand_no_77 >= 7 THEN '高额度组'
            WHEN date(create_time) >= date('2025-10-16') AND t13.rand_no_77 < 7 THEN '低额度组'
            WHEN date(create_time) >= date('2025-10-16') AND t13.rand_no_77 >= 7 THEN '高额度组'
            WHEN date(create_time) >= date('2025-06-12') AND t13.rand_no_77 < 5 THEN '低额度组'
            WHEN date(create_time) >= date('2025-06-12') AND t13.rand_no_77 >= 5 THEN '高额度组'
            ELSE NULL  
        END
  END AS edu_flag20250910,--高低额度组标签

  --case when date(create_time) >= date('2025-09-23') and t4.sd_creditlevel_main_v3_2 <=5 and product_random<0.7 then '07_02_20_30'
  --     when date(create_time) >= date('2025-09-23') and t4.sd_creditlevel_main_v3_2 <=5 and product_random<0.9 and product_random>=0.7 then '07_02_00_50'
  --     when date(create_time) >= date('2025-09-23') and t4.sd_creditlevel_main_v3_2 <=5 and product_random>=0.9 then '07_35'
  --     when date(create_time) >= date('2025-09-23') and t4.sd_creditlevel_main_v3_2 >5 and product_random>=0.5 then '07_35'
  --     when date(create_time) >= date('2025-09-23') and t4.sd_creditlevel_main_v3_2 >5 and product_random<0.5 then '07_40'
  --     when date(create_time) >= date('2025-09-18') and product_random>=0.9 then '07_35'
  --     when date(create_time) >= date('2025-09-18') and product_random>=0.7 and product_random<0.9 then '07_02_00_50'
  --     when date(create_time) >= date('2025-09-18') and product_random<0.7 then '07_02_20_30'
  --     when date(create_time) >= date('2025-08-29') and product_random<0.5 then '测试组' 
  --     when date(create_time) >= date('2025-08-29') and product_random>=0.5 then '对照组' 
  --     when date(create_time) < date('2025-08-29') and product_random<0.2 then '测试组' 
  --     when date(create_time) < date('2025-08-29') and product_random>=0.2 then  '对照组' 
  --end as product_random_flag,

  --case 
  --  when date(create_time) >= date('2025-09-23') and t4.sd_creditlevel_main_v3_2 in (1,2,3,4,5) then '头部评级'
  --  when date(create_time) >= date('2025-09-23') and t4.sd_creditlevel_main_v3_2 not in (1,2,3,4,5) then '尾部评级'
  --  when date(create_time) >= date('2025-08-29') and product_random<0.5 then '测试组_长期限'
  --  when date(create_time) >= date('2025-08-29') and product_random>=0.5 then '对照组_短期限'
  --  when date(create_time) >= date('2025-07-09') and date(create_time) < date('2025-07-28') and sd_corrected_property_level_v3 in (1,2,3,4) and product_random<0.2 then '测试组_长期限'
  --  when date(create_time) >= date('2025-07-28') and t4.sd_creditlevel_main_v3_2 in (1,2,3,4) and product_random<0.2 then '测试组_长期限'
  --  when date(create_time) >= date('2025-07-09') and date(create_time) < date('2025-07-28') and sd_corrected_property_level_v3 in (1,2,3,4) and product_random>=0.2 then '对照组_短期限'
  --  when date(create_time) >= date('2025-07-28') and t4.sd_creditlevel_main_v3_2 in (1,2,3,4) and product_random>=0.2 then '对照组_短期限'
  --  when date(create_time) >= date('2025-07-09') and date(create_time) < date('2025-07-28') and sd_corrected_property_level_v3 not in (1,2,3,4) then '尾部评级'
  --  when date(create_time) >= date('2025-07-28') and t4.sd_creditlevel_main_v3_2 not in (1,2,3,4) then '尾部评级' end as product_test_flag_new,
  --    case when date(create_time) >= date('2025-09-23') and t4.sd_creditlevel_main_v3_2 in (1,2,3,4,5) then '头部评级'
  --  when date(create_time) >= date('2025-09-23') and t4.sd_creditlevel_main_v3_2 not in (1,2,3,4,5) then '尾部评级'
  --    when date(create_time) >= date('2025-07-28') and t4.sd_creditlevel_main_v3_2 in (1,2,3,4) then '头部评级'
  --     when date(create_time) >= date('2025-07-28') and t4.sd_creditlevel_main_v3_2 not in (1,2,3,4) then '尾部评级'
  --     when date(create_time) >= date('2025-07-09') and sd_corrected_property_level_v3 in (1,2,3,4) then '头部评级'
  --     when date(create_time) >= date('2025-07-09') and sd_corrected_property_level_v3 not in (1,2,3,4) then '尾部评级'
  --end as level_flag,

  --case when date(create_time) >= date('2025-08-15') then '2025-08-15及以后' else '2025-08-15及以前' end as time_flag,
  
  -- baihu_tag,
  --sd_property_level_V2,
  --sd_corrected_main_model_V1,
  t0.baseinfo_userprof_degree,
  t0.income,
  --sd_trade_scorecard_V2,
  --sd_property_level_V3,
  --sd_corrected_property_level_V3,
  --t4.sd_creditlevel_main_v3_2,
  --sd_creditlevel_main_v3_3,
  --sd_creditlevel_main_v3_4,
  t4.sd_creditlevel_main_v3_5,
  t4.sd_creditlevel_main_v3_6,
  t4.sd_creditlevel_main_v4,
  t4.sd_creditlevel_main_v4_1,
  --Lucy新增——新评级
  t4.android_newCust_mainCreditLevel_charge_V4_2,
  t4.android_newCust_mainCreditLevel_charge_V4_3,
  t4.android_newcust_maincreditlevel_charge_v5_1,
  t4.android_newcust_maincreditlevel_charge_v5_2,
  t4.android_newcust_maincreditlevel_charge_v5_3,
  t4.android_newcust_maincreditlevel_charge_v5_4,
  t4.android_newcust_maincreditlevel_charge_v5_5,
  --用信模型：授信策略复盘用
  t24.sd_quota_change_flag,
  t24.sd_product_change_flag,
  t24.strategy_version as sx_strategy_version,
  t24.base_test_flag as quota_base_test_flag,
  t24.v4_3bin,
  t24.pvalue_mex_m112_2026v1_pureyx_p1,
  t24.yx_model_bin, 
  t24.sd_creditlevel_yxmodel_bin,
  t24.credit_amount sx_credit_amt,
  t24.product_level sx_credit_productlevel,
  --sd_rate_flag,
  --sd_property_level_V1,
  case when date(create_time) >= date('2025-01-23') and date(create_time) < date('2025-02-21') then 'v1组'
    when date(create_time) >= date('2025-02-21') and date(create_time) < date('2025-03-05') and t4.rand_no_74 < 5 then 'v1组'
    when date(create_time) >= date('2025-02-21') and date(create_time) < date('2025-03-05') and t4.rand_no_74 >= 5 then 'v2组'
    when date(create_time) >= date('2025-03-05') and date(create_time) < date('2025-05-27') then 'v2组'
    when date(create_time) >= date('2025-05-27') and date(create_time) < date('2025-06-09') and t4.rand_no_74 < 5 then 'v3组'
    when date(create_time) >= date('2025-05-27') and date(create_time) < date('2025-06-09') and t4.rand_no_74 >= 5 then 'v2组'
    when date(create_time) >= date('2025-06-09') and date(create_time) < date('2025-06-12') then 'v3组'     
    when date(create_time) >= date('2025-06-12') and date(create_time) < date('2025-07-15') then 'v3_1组'
    when date(create_time) >= date('2025-07-15') and date(create_time) < date('2025-07-28') and t4.rand_no_74 < 5 then 'v3_1组'
    when date(create_time) >= date('2025-07-15') and date(create_time) < date('2025-07-28') and t4.rand_no_74 >= 5 then 'v3_2组'
    when date(create_time) >= date('2025-07-28') and date(create_time) < date('2025-08-08') then 'v3_2组'
    when date(create_time) >= date('2025-08-08') and date(create_time) < date('2025-08-30') and t4.rand_no_74<3 then 'v3_3组'
    when date(create_time) >= date('2025-08-08') and date(create_time) < date('2025-08-30') and t4.rand_no_74>=3 then 'v3_2组'
    when date(create_time) >= date('2025-08-30') and sd_approve_version_label='V_3_3' then 'v3_3组'
    when date(create_time) >= date('2025-08-30') and sd_approve_version_label='V_3_2' then 'v3_2组'
    when date(create_time) >= date('2025-08-30') and sd_approve_version_label='V_3_4' then 'v3_4组'
    when date(create_time) >= date('2025-08-30') and sd_approve_version_label='V_3_5' then 'v3_5组'
    when date(create_time) >= date('2025-08-30') and sd_approve_version_label='V_3_6' then 'v3_6组'
    when date(create_time) >= date('2025-08-30') and sd_approve_version_label='V_4' then 'v4组'
    when date(create_time) >= date('2026-01-01') and sd_approve_version_label='V_4_1' then 'v4_1组'
    --Lucy新增——新策略标签判断
    when date(create_time) >= date('2026-03-27') and sd_approve_version_label in ('V_4_2','V_4_3') then 'v4_3组'
    when date(create_time) >= date('2026-07-15') and date(create_time) <= date('2026-07-31') and sd_approve_version_label in ('V_5_2','V_5_1') and t4.rand_no_74<=6 then 'v5_2组'
    when date(create_time) >= date('2026-07-15') and sd_approve_version_label in ('V_5_2','V_5_1') then 'v5_3组'
    when date(create_time) >= date('2026-06-02') and sd_approve_version_label in ('V_5_2','V_5_1') then 'v5_2组'
    when date(create_time) >= date('2026-08-07') and sd_approve_version_label in ('V_5_4','V_5_5') then 'v5_4组'
    end as strategy_flag_new,
--  last_not_overdue,
  loan_score,--applist里墨西哥借贷app出现次数（多头）
  --loan_score_group,--applist多头分组
  source,
  tenant,
  t0.app_group,
  t0.new_media_source,
  case 
    when date(t0.create_time) <= date('2026-05-31') then '未上线'
    when date(t0.create_time) > date('2026-05-31') and t0.new_media_source = 'mexdin_int' then '微财'
    when date(t0.create_time) > date('2026-05-31') and t0.new_media_source <> 'mexdin_int' then '其他'
    else '未上线' end as weicai_label,
  case 
    when date(t0.create_time) <date('2026-08-12') and  t0.new_media_source = 'bj' then 'bj_调整前'
    when date(t0.create_time) >=date('2026-08-12') and  t0.new_media_source = 'bj' then 'bj_调整后'
    when t0.new_media_source <> 'bj' then '其他'
    else '其他' end as bj_label,

  t0.campaign_name,
  --0915新增探知分客群
  t25.tanzhi_group,
  -- case when t6.batch_id=18355 then '提额50比索'
  --      when t6.batch_id=18356 then '提额100比索'
  --      when t6.batch_id=18357 then '提额150比索'
  --      when t7.batch_id=18358 then '限定减息券'
  --      when t7.batch_id=18365 then 'TC首贷减息券'
  --      when t7.batch_id=18366 then 'ME首贷减息券'
  -- else ''
  -- end as yx_flag,
  case when t9.user_phone_gather_t30user_emcontact_cnt>=1 then '01.[1,-)'
       when t9.user_phone_gather_t30user_emcontact_cnt<1 then '02.(-,1)'
       else ''
  end as t30user_emcontact_cnt_flag,

  case when t9.gathercnt_7d_ip_identity_all>=10 then '01.[10,-)'
       when t9.gathercnt_7d_ip_identity_all>=8 and t9.gathercnt_7d_ip_identity_all<10 then '02.[8,9]'
       when t9.gathercnt_7d_ip_identity_all>=6 and t9.gathercnt_7d_ip_identity_all<8 then '03.[6,7]'
       when t9.gathercnt_7d_ip_identity_all<6 then '04.(-,6)'
       else ''
  end as gathercnt_7d_ip_identity_all_flag,

  case when t9.gathercnt_3d_ip_identity_all>=8 then '01.[8,-)'
       when t9.gathercnt_3d_ip_identity_all>=6 and t9.gathercnt_3d_ip_identity_all<8 then '02.[6,7]'
       when t9.gathercnt_3d_ip_identity_all>=4 and t9.gathercnt_3d_ip_identity_all<8 then '03.[4,5]'
       when t9.gathercnt_3d_ip_identity_all<6 then '04.(-,4)'
       else ''
  end as gathercnt_3d_ip_identity_all_flag,

  case when t9.gathercnt_emcontact_identity_all>=3 then '01.[3,-)'
       when t9.gathercnt_emcontact_identity_all>=2 and t9.gathercnt_emcontact_identity_all<3 then '02.2'
       when t9.gathercnt_emcontact_identity_all<2 then '03.1'
       else ''
  end as gathercnt_emcontact_identity_all_flag,
  
  case when t9.baseinfo_userprof_worktype=2 and t9.baseinfo_userprof_job=24 then 1 else 0 end as work_job_type,
  case when t10.sms_loanrec_rate_15d_overdue>=0.5 then '01.[0.5,-)'
       when t10.sms_loanrec_rate_15d_overdue>=0.25 and t10.sms_loanrec_rate_15d_overdue<0.5 then '02.[0.25,0.5)'
       when t10.sms_loanrec_rate_15d_overdue<0.25 then '03.(-,0.25)'
       else ''
  end as sms_loanrec_rate_15d_overdue_flag,
  --CASE 
  --      WHEN bssid IS NULL THEN 'NULL值'
  --      WHEN bssid = '' THEN '空字符串'
  --      WHEN TRIM(bssid) = '' THEN '空格字符串'
  --      ELSE '正常值' END AS bssid_type,
  sd_high_pass_label,

  case when t4.rand_no_74<2 then '对照组'
       when t4.rand_no_74>=2 then '测试组'
  end as yx_test_flag,

  --third_bj_whitelist,

  --case when t14.loan_apply_gap_minutes=0 then '00.=0'
  --     when t14.loan_apply_gap_minutes=1 then '01.=1'
  --     when t14.loan_apply_gap_minutes=2 then '02.=2'
  --     when t14.loan_apply_gap_minutes>=3 and t14.loan_apply_gap_minutes<=5 then '03.[3,5]'
  --     when t14.loan_apply_gap_minutes>=6 and t14.loan_apply_gap_minutes<=10 then '04.[6,10]'
  --     when t14.loan_apply_gap_minutes>=11 and t14.loan_apply_gap_minutes<=1440 then '05.[10,1440]'
  --     when t14.loan_apply_gap_minutes>=1441 then '06.[1441,-)'
  --     else null end as loan_apply_gap_flag,
  android_newCust_tradescore_charge_V3_1,
  t17.android_newCust_tradescore_charge_V3_2,--V4_3使用
  t20.android_newCust_tradescore_charge_V4_1,
  case when t20.android_newCust_tradescore_charge_V4_1<=-10 then '00.<=-10'
       when t20.android_newCust_tradescore_charge_V4_1<=-5 then '01.<=-5'
       when t20.android_newCust_tradescore_charge_V4_1<=-2 then '02.<=-2'
       when t20.android_newCust_tradescore_charge_V4_1<=0 then '03.<=0'
       when t20.android_newCust_tradescore_charge_V4_1>0 then '04.>0'
       end as tradescore_V4_1_flag,

  t21.android_newCust_tradescore_charge_V4_2,
  case when t21.android_newCust_tradescore_charge_V4_2<=-11 then '00.<=-11'
       when t21.android_newCust_tradescore_charge_V4_2<=-8 then '01.<=-8'
       when t21.android_newCust_tradescore_charge_V4_2<=-6 then '02.<=-6'
       when t21.android_newCust_tradescore_charge_V4_2<=-3 then '03.<=-3'
       when t21.android_newCust_tradescore_charge_V4_2>-3 then '04.>-3'
       end as tradescore_V4_2_flag,

  --三方新规则分&拒绝标签（0422新增）
  android_newCust_rulescore_external_V1,
  android_newCust_external_refuse_flag,
  case when t17.baseinfo_userprof_age<=31 then '00.<=31'
       when t17.baseinfo_userprof_age<=38 then '01.<=38'
       when t17.baseinfo_userprof_age<=47 then '02.<=47'
       when t17.baseinfo_userprof_age>47 then '03.>47'
       else null end as age_flag,
  case when dyna_amlba_d90_b_cnt<0 then '00.<0'
       when dyna_amlba_d90_b_cnt<=22 then '01.<=22'
       when dyna_amlba_d90_b_cnt>22 then '02.>22'
       else null end as dyna_amlba_d90_b_cnt_flag,
  case when t17.app_loan1_inst_cnt_day30_d_dayall<=0 then '00.<0'
       when t17.app_loan1_inst_cnt_day30_d_dayall<=0.4 then '01.<=0.4'
       when t17.app_loan1_inst_cnt_day30_d_dayall>0.4 then '02.>0.4'
       else null end as app_loan1_inst_cnt_day30_d_dayall_flag,
  case when t17.degree_new<=4 then '00.<=4'
       when t17.degree_new>4 then '01.>4'
       else null end as degree_flag,
  --advance_gd_x_19 as advance_gd_x_19_flag,
  question3 as question3_flag,
  case when t17.bj_p_his_single_loan_max_count<0 then '00.<0'
       when t17.bj_p_his_single_loan_max_count<=22 then '01.<=22'
       when t17.bj_p_his_single_loan_max_count>22 then '02.>22'
       else null end as bj_p_his_single_loan_max_count_flag,

--   新增的交易分策略by yuhan   并且做swap in/out 监控
  android_newCust_tradescore_charge_V3_3,
  trade_score_V3_3_reject_flag,
  trade_score_V3_2_reject_flag,
  low_model_test,----免费模型随机数标签
  test_flag,
  -----强反放松测试：20260702-----
  test_20260702,
  apply_emcontact_discnt_flag,
  onorder_cnt_uuid_appchan_flag,
  onorder_cnt_device_appchan_flag,
  baseinfo_onorder_hit_phone_single_flag,
  case when date(create_time) >= date('2025-08-08') and t4.rand_no_74<3 and policy_version is not null then policy_version else null end as policy_version_flag,

  --支用转产标签
  tradescore_V3_2_bin,--V5_2交易分bin
  tradescore_V4_1_bin,
  tradescore_V4_2_bin,
  test_Proportion,---支用转产灰度
  group_tag,
  if_support_disburse_change,--标签逻辑：case when t1.app_name='Mexcredo' and t1.app_version>='1.0.4' then 1 else 0 end
  strategy_type,--标签逻辑：case when rand_no_74<=6 then '1_v4_1策略' when rand_no_74>6 then '1_v4_3策略' end
  disburseChange,--标签逻辑：研发给的是否具有支用功能标签
  myDecisionResult,--标签逻辑：最终输出的review/passed
  sd_disburse_cust_label,--标签逻辑：支用转产标签（2-提额(review)；1-降额(review)；3-不变(pass)）
  sd_disburse_change_amount,--标签逻辑：支用转产额度变化（
  disburse_change_amount_type,
  sd_disburse_amt_temp,
  sd_disburse_custflag_temp,
  disburse_custflag_temp_type,
  sd_disburse_change_type_label,--标签逻辑：支用转产规则标签V4_3_1_1,第一个1是支用转产标签的1，第二个1是支用策略版本
  last_product_level,--上次授信产品
  user_choice,----支用转产弹窗选择情况
  amt_type_v5_2,
  amt_type_v5_3,
  amt_type_v5_5,
  amt_type_v4_3,

  --0509新增支用转产后拒绝入参
  android_newCust_tradescore_disburse_V1,
  case when android_newCust_tradescore_disburse_V1<='-5' then '<=-5' when android_newCust_tradescore_disburse_V1<='-2' then '<=-2' when android_newCust_tradescore_disburse_V1<='-1' then '<=-1' when android_newCust_tradescore_disburse_V1>'-1' then '>-1' end as rule_score_disburse_bin,
  if_disburse_ovrtime_reduceamt,
  if_disburse_ovrtime_addamt,
  disburse_final_DecisionResult,

  is_student,
  emcontact_samechild_diffname,
  emcontact_t30,
  contact_t30,
  address_abnormal,
  phone_identity,
  case when is_student=1 or emcontact_samechild_diffname=1 or emcontact_t30=1 or contact_t30=1 or address_abnormal=1 or phone_identity=1 then 1 else 0 end as fraud_test_hz,
  case when sha256_random_260721>0.7 then '产品包' when sha256_random_260721<=0.7 then '单产品' else null end as product_pack_flag,
  curr_ovd_cnt_all,
  curr_ovd_cnt_other_app_group,
  curr_ovd_cnt_other_app_group_30d,
  curr_ovd_other_app_group_30_60d,
  curr_ovd_cnt_other_app_group_60d,
  curr_ovd_other_app_group_60_90d,
  curr_ovd_cnt_other_app_group_90d,
  curr_ovd_other_app_group_over90d,
  --0918强反规则放松测试
  sf.is_user_applist_contain_sexapp,
  sf.sha256_random_260915,
  sf.hint,
  case 
    when sf.sha256_random_260915 <= 0.5 then '规则未放松'   -- 规则未放松客群
    else '规则放松'                                    -- 规则放松客群
  end as sex_app_relax_group,

  sum(last_credit_amount) as disburse_last_credit_amount,--上次授信额度
  sum(m.credit_amount) as disburse_credit_amount,--调整后授信额度

  max( substr(cast(current_timestamp as varchar),1,24) )as update_time,
  count(distinct phone_num) as cnt,
  count(distinct creditno_appchan) as person_cnt,
	count(distinct if(t0.biz_id is not null,phone_num,null)) as total_apply_person, 
	count(distinct t0.biz_id) as total_apply_cnt,
	sum(if_shou_anti_fraud_passed) as if_shou_anti_fraud_passed,
	sum(if_in_shou_anti_fraud) as if_in_shou_anti_fraud,
	sum(if_shou_anti_fraud_weak_passed) as if_shou_anti_fraud_weak_passed,
	sum(if_in_shou_anti_fraud_weak) as if_in_shou_anti_fraud_weak,
	sum(if(lower(source)= 'ios',if_shou_anti_fraud_weak_passed,if_shou_model_passed)) as if_shou_model_passed,
	sum(if(lower(source)= 'ios',if_shou_anti_fraud_weak_passed,if_in_shou_model)) as if_in_shou_model,
  sum(if_in_sx) as if_in_sx,
  sum(if_sx_passed) as if_sx_passed,
  sum(if_sx_passed_within24h) as if_sx_passed_within24h,
  sum(if_in_sx_over24h) as if_in_sx_over24h,
  sum(if_sx_passed_within48h) as if_sx_passed_within48h,
  sum(if_in_sx_over48h) as if_in_sx_over48h,
  sum(if_sx_passed_within72h) as if_sx_passed_within72h,
  -- sum(if_in_sx_over72h) as if_in_sx_over72h,
  sum(if_sx_passed_within120h) as if_sx_passed_within120h,
  sum(if_in_sx_over120h) as if_in_sx_over120h,
  sum(if(date_diff('minute',sx_time,cast(now() as timestamp)) >= 72*60,if_sx_passed,0)) as if_72h_sx_passed,
  sum(if(date_diff('minute',sx_time,cast(now() as timestamp)) >= 72*60,if_in_sx,0)) as if_in_sx_over72h,
  sum(if(if_sx_passed_within24h = 0,if_sx_passed,0)) as if_24h_72h_sx_passed,
  count(if(if_sx_passed_within24h = 0,t0.biz_id,null)) as if_sx_notpassed_within24h,
  sum(if(lower(source)= 'ios',1,if(if_sx_passed = 1 and if_in_post_model is null,1,if_in_post_model))) as if_in_post_model,
  sum(if(lower(source)= 'ios',1,if(if_sx_passed = 1 and if_post_model_passed is null,1,if_post_model_passed))) as if_post_model_passed,
  sum(case when if_in_shou_normal_check is null then 0 else if_in_shou_normal_check end) as if_in_shou_normal_check,
	sum(case when if_in_shou_normal_rule_check is null then 0 else if_in_shou_normal_rule_check end) as if_in_shou_normal_rule_check,  
  sum(case when if_shou_normal_rule_check_passed is null then 0 else if_shou_normal_rule_check_passed end) as if_shou_normal_rule_check_passed,  
  sum(case when if_in_sd_ai is null then 0 else if_in_sd_ai end) as if_in_sd_ai,  
  sum(case when if_shou_ai_passed is null then 0 else if_shou_ai_passed end) as if_shou_ai_passed,    
	sum(if_in_shou_external_data) as if_in_shou_external_data,
	sum(if_shou_external_data_passed) as if_shou_external_data_passed,
  sum(if_shou_external_data_review) as if_shou_external_data_review,
  --新增节点
  sum(if_in_shou_loan_refuse) as if_in_shou_loan_refuse,
	sum(if_shou_loan_refuse_reject_passed) as if_shou_loan_refuse_passed,
  sum(if_shou_loan_refuse_reject_refused) as if_shou_loan_refuse_refused,

	count(if(should_amount != 0 and should_amount is not null,t0.biz_id,null)) as total_issue_cnt,
	sum(cast(t0.grantcredit_7d_amount as double)) as total_grant_amount,
	sum(cast(apply_amount as double)/1000) as total_apply_amount,
  sum(if(cast(apply_amount as double)/1000!=0,cast(t0.grantcredit_7d_amount as double),0)) as total_apply_amount_fenmu,
  sum(if(is_t0_window_1 = 1,1,0)) as t0_should_cnt,
  sum(if(is_t3_window_1 = 1,1,0)) as t3_should_cnt,
  sum(if(is_t0_window_2 = 1,1,0)) as t0_should_cnt_2,
  sum(if(is_t3_window_2 = 1,1,0)) as t3_should_cnt_2,
  sum(if(is_t0_window_3 = 1,1,0)) as t0_should_cnt_3,
  sum(if(is_t3_window_3 = 1,1,0)) as t3_should_cnt_3,
  sum(if(is_t0_window_4 = 1,1,0)) as t0_should_cnt_4,
  sum(if(is_t3_window_4 = 1,1,0)) as t3_should_cnt_4,
  sum(if(is_t0_window_1 = 1,is_t0_overdue_1,0)) as is_t0_overdue_1,
  sum(if(is_t3_window_1 = 1,is_t3_overdue_1,0)) as is_t3_overdue_1,
  sum(if(is_t0_window_2 = 1,is_t0_overdue_2,0)) as is_t0_overdue_2,
  sum(if(is_t3_window_2 = 1,is_t3_overdue_2,0)) as is_t3_overdue_2,
  sum(if(is_t0_window_3 = 1,is_t0_overdue_3,0)) as is_t0_overdue_3,
  sum(if(is_t3_window_3 = 1,is_t3_overdue_3,0)) as is_t3_overdue_3,
  sum(if(is_t0_window_4 = 1,is_t0_overdue_4,0)) as is_t0_overdue_4,
  sum(if(is_t3_window_4 = 1,is_t3_overdue_4,0)) as is_t3_overdue_4,
	sum(if(is_t0_window_1 = 1,t0_overdue_amount_1,0)) as t0_overdue_amount,
  sum(if(is_t3_window_1 = 1,t3_overdue_amount_1,0)) as t3_overdue_amount,
  sum(if(is_t0_window_1 = 1,t0_should_amt_1,0)) as t0_should_amount,
  sum(if(is_t3_window_1 = 1,t3_should_amt_1,0)) as t3_should_amount,
  sum(if(is_t0_window_2 = 1,t0_overdue_amount_2,0)) as t0_overdue_amount_2,
  sum(if(is_t3_window_2 = 1,t3_overdue_amount_2,0)) as t3_overdue_amount_2,
  sum(if(is_t0_window_2 = 1,t0_should_amt_2,0)) as t0_should_amount_2,
  sum(if(is_t3_window_2 = 1,t3_should_amt_2,0)) as t3_should_amount_2,
  sum(if(is_t0_window_3 = 1,t0_overdue_amount_3,0)) as t0_overdue_amount_3,
  sum(if(is_t3_window_3 = 1,t3_overdue_amount_3,0)) as t3_overdue_amount_3,
  sum(if(is_t0_window_3 = 1,t0_should_amt_3,0)) as t0_should_amount_3,
  sum(if(is_t3_window_3 = 1,t3_should_amt_3,0)) as t3_should_amount_3,
  sum(if(is_t0_window_4 = 1,t0_overdue_amount_4,0)) as t0_overdue_amount_4,
  sum(if(is_t3_window_4 = 1,t3_overdue_amount_4,0)) as t3_overdue_amount_4,
  sum(if(is_t0_window_4 = 1,t0_should_amt_4,0)) as t0_should_amount_4,
  sum(if(is_t3_window_4 = 1,t3_should_amt_4,0)) as t3_should_amount_4,
  sum(should_capital) as should_capital,
  sum(should_interest) as should_interest,
  sum(loan_cycle) as loan_cycle,
  sum(cast(should_amount as double)) as should_amount,
  sum(pre_p2_repay) as pre_p2_repay,
  sum(p1_repay) as p1_repay,
  sum(p2_repay) as p2_repay,
  --新增本金逾期
  sum(if(is_t0_window_1 = 1,t0_overdue_amount_1,0)-if(is_t0_window_1 = 1,t0_overdue_interest_1,0)) as t0_overdue_capital,
  sum(if(is_t3_window_1 = 1,t3_overdue_amount_1,0)-if(is_t3_window_1 = 1,t3_overdue_interest_1,0)) as t3_overdue_capital,
  sum(if(is_t0_window_1 = 1,t0_should_amt_1,0)-if(is_t0_window_1 = 1,t0_should_interest_1,0)) as t0_should_capital,
  sum(if(is_t3_window_1 = 1,t3_should_amt_1,0)-if(is_t3_window_1 = 1,t3_should_interest_1,0)) as t3_should_capital,
  sum(if(is_t0_window_2 = 1,t0_overdue_amount_2,0)-if(is_t0_window_2 = 1,t0_overdue_interest_2,0)) as t0_overdue_capital_2,
  sum(if(is_t3_window_2 = 1,t3_overdue_amount_2,0)-if(is_t3_window_2 = 1,t3_overdue_interest_2,0)) as t3_overdue_capital_2,
  sum(if(is_t0_window_2 = 1,t0_should_amt_2,0)-if(is_t0_window_2 = 1,t0_should_interest_2,0)) as t0_should_capital_2,
  sum(if(is_t3_window_2 = 1,t3_should_amt_2,0)-if(is_t3_window_2 = 1,t3_should_interest_2,0)) as t3_should_capital_2,
  sum(if(is_t0_window_3 = 1,t0_overdue_amount_3,0)-if(is_t0_window_3 = 1,t0_overdue_interest_3,0)) as t0_overdue_capital_3,
  sum(if(is_t3_window_3 = 1,t3_overdue_amount_3,0)-if(is_t3_window_3 = 1,t3_overdue_interest_3,0)) as t3_overdue_capital_3,
  sum(if(is_t0_window_3 = 1,t0_should_amt_3,0)-if(is_t0_window_3 = 1,t0_should_interest_3,0)) as t0_should_capital_3,
  sum(if(is_t3_window_3 = 1,t3_should_amt_3,0)-if(is_t3_window_3 = 1,t3_should_interest_3,0)) as t3_should_capital_3,
  sum(if(is_t0_window_4 = 1,t0_overdue_amount_4,0)-if(is_t0_window_4 = 1,t0_overdue_interest_4,0)) as t0_overdue_capital_4,
  sum(if(is_t3_window_4 = 1,t3_overdue_amount_4,0)-if(is_t3_window_4 = 1,t3_overdue_interest_4,0)) as t3_overdue_capital_4,
  sum(if(is_t0_window_4 = 1,t0_should_amt_4,0)-if(is_t0_window_4 = 1,t0_should_interest_4,0)) as t0_should_capital_4,
  sum(if(is_t3_window_4 = 1,t3_should_amt_4,0)-if(is_t3_window_4 = 1,t3_should_interest_4,0)) as t3_should_capital_4
	--sum(if(if_t3_expired = 1,t0_should_amount_1,0)) as t3_should_amount
from mx.darren_group_data t0
left join (select externalid,message_type  from mx.sd_wenj_add) t1 on t0.biz_id = t1.externalid
left join
  (select externalid,
  case when sha256_random_20250810 is not null and date(createtime) >= date('2025-08-08') and date(createtime) < date('2025-08-11') then sha256_random_20250810
      else sha256_random_250708
  end as product_random
  from mx.wenj_sd_random) t2 on t0.biz_id = t2.externalid
left join
  (select 
    externalid7,
    policy_version,
    sd_creditlevel_main_v3_2,
    sd_creditlevel_main_v3_3,
    sd_creditlevel_main_v3_4,
    sd_creditlevel_main_v3_5,
    sd_creditlevel_main_v3_6,
    sd_creditlevel_main_v4,
    sd_property_level_V1,
    sd_property_level_V2,
    sd_property_level_V3,
    sd_corrected_property_level_V3,
    sd_corrected_main_model_V1,
    subscore_income,
    rand_no_74,
    sd_creditlevel_main_v4_1,
    --lucy新增
    android_newCust_mainCreditLevel_charge_V4_3,
    android_newCust_mainCreditLevel_charge_V4_2,
    android_newcust_maincreditlevel_charge_v5_1,
    android_newcust_maincreditlevel_charge_v5_2,
    android_newcust_maincreditlevel_charge_v5_3,
    android_newcust_maincreditlevel_charge_v5_4,
    android_newcust_maincreditlevel_charge_v5_5
  from mx.wenj_sd_market 
  ) t4 on t0.biz_id = t4.externalid7
left join (select externalid,sd_approve_version_label from mx.sd_wenj_approve_version_label) t5 on t0.biz_id = t5.externalid
left join mx.sd_limit_coupon t6 on t0.mid=cast(t6.mid as varchar)
left join mx.sd_interest_coupon t7 on t0.biz_id=cast(t7.biz_id as varchar)
left join mx.wenj_sd_high_rate t8 on t0.biz_id=t8.externalid
left join 
  (select 
    externalid,
    gathercnt_3d_ip_identity_all,
    gathercnt_7d_ip_identity_all,
    user_phone_gather_t30user_emcontact_cnt,
    baseinfo_userprof_worktype,
    baseinfo_userprof_job,
    gathercnt_emcontact_identity_all
  from mx.wenj_sd_anti_fraud_strong) t9 on t0.biz_id=t9.externalid
left join 
  (select 
  externalid3,
  sms_loanrec_rate_15d_overdue
  from mx.wenj_sd_anti_fraud_weak) t10 on t0.biz_id=t10.externalid3
left join 
  (select 
  biz_id,
  bssid
  from mx.wenj_mobile_device) t11 on t0.biz_id=t11.biz_id
left join (select externalid10,sd_quota_test_label,rand_no_77,sd_rate_flag from mx.wenj_sd_feature_credit) t13 on t0.biz_id=t13.externalid10
left join (select externalid,sd_trade_scorecard_V2,loan_apply_gap_minutes from mx.sd_wenj_trade_v2) t14 on t0.biz_id=t14.externalid
left join mx.sd_wenj_trade_v3 t15 on t0.biz_id=t15.externalid
left join (select *,baseinfo_userprof_degree as degree_new from mx.sd_wenj_trade_v3_2) t17 on t0.biz_id=t17.externalid
-- 新增的交易分策略by yuhan
left join mx.sd_wenj_trade_v3_3 t18 on t0.biz_id=t18.externalid
left join mx.sd_wenj_trade_v4_1 t20 on t0.biz_id=t20.externalid
left join mx.trade_random t16 on t0.biz_id=t16.externalid
left join mx.model_low t19 on t0.biz_id=t19.externalid
left join tmp.lucy_disbursechange_basedata m on cast(t0.biz_id as bigint)=m.camera_id --支用转产标签表
left join mx.fraud_data_test_20260429 f on t0.biz_id=f.externalid
left join mx.curr_ovd_data_test_0525 ll on t0.biz_id=ll.externalid
left join mx.fraud_data_test_20260702 tt on t0.biz_id=tt.externalid
left join mx.sexapp_data_test_0915    sf on t0.biz_id=sf.externalid --yj新增强反规则放松测试
left join 
  (select 
    externalid,
    max(cast(json_extract_scalar(outputdata, '$.product_level') as varchar)) as product_level_org
  from ods.s21_risk_strategy_record
  where productid =195 and strategymainid=239  and strategytype='CHAMPION' and etl_date >= '20260101'and createtime >= cast('2026-01-01 00:00:00.000' as timestamp)
  group by 1) qq on t0.biz_id=qq.externalid
left join mx.sd_wenj_trade_4_2 t21 on t0.biz_id=t21.externalid
left join mx.sd_good_cust_base t22 on t0.biz_id=t22.externalid
left join mx.property_level_v5_2 t23 on t0.biz_id=t23.externalid
left join mx.sd_sx_feature_v5_5 t24 on t0.biz_id=t24.externalid
left join 
  (select 
    externalid,
    max(cast(json_extract_scalar(outputdata, '$.sha256_random_260721') as double)) as sha256_random_260721
  from ods.s21_risk_strategy_record
  where productid =195 and strategymainid=239  and strategytype='CHAMPION' and etl_date >= '20260901'
  group by 1) t26 on t0.biz_id=t26.externalid
left join (
  select  mid,
  -- media_source,
  -- campaign,
  case when  campaign like '%09_07' then 'B'
  when  campaign like '%26_01' then 'A'
  when  campaign like '%09_07_02' then 'C'
  else '探知其他' end as tanzhi_group
  from (
     SELECt
      customer_user_id AS mid,
      appsflyer_id,
      campaign,
      media_source,
ROW_NUMBER() OVER (
        PARTITION BY
          customer_user_id
        ORDER BY
          event_time_selected_timezone desc
      ) AS rank1
    FROM
      ods.s08_appsflyer_push_data
  )
  where lower(media_source)='tanzhi' and rank1 =1 
) t25 on t0.mid =t25.mid
where date(create_time) >= date_add('day',-180,date(now())) and double_loan_2 = 0
group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126
;