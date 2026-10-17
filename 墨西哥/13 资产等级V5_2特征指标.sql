select * from mx.property_v5_1_feature_bin



 


--:{author=yaojia, department=墨西哥风险策略, dagName=sd_property_level_feature, taskName=property_v5_1_feature_bin}
drop table if EXISTS mx.property_v5_1_feature_bin
;
--:{author=yaojia, department=墨西哥风险策略, dagName=sd_property_level_feature, taskName=property_v5_1_feature_bin}
create table mx.property_v5_1_feature_bin as 
select
app_date,
app_month,
b.new_media_source,
case 
when b.app_date <= date('2026-05-31') then '未上线'
when b.app_date > date('2026-05-31') and b.new_media_source = 'mexdin_int' then '微财'
when b.app_date > date('2026-05-31') and b.new_media_source <> 'mexdin_int' then '其他'
else '未上线' end as weicai_label,
sd_approve_version_label,
case when bj_fk_app_rate_2w <= -3 then '00.<=-3_0'
     when bj_fk_app_rate_2w <= -2 then '01.<=-2_-1'
     when bj_fk_app_rate_2w <= -1 then '02.<=-1_-1'
     when bj_fk_app_rate_2w <= 0.4 then '03.<=0.4_-2'
     when bj_fk_app_rate_2w <= 1 then '04.<=1_0'
     when bj_fk_app_rate_2w > 1 then '05.>1_1'
     else 'else' end as bj_fk_app_rate_2w_score,

case when bj_fk_app_rate_3m <= -3 then '00.<=-3_0'
     when bj_fk_app_rate_3m <= -2 then '01.<=-2_-2'
     when bj_fk_app_rate_3m <= -1 then '02.<=-1_-1'
     when bj_fk_app_rate_3m <= 0.4 then '03.<=0.4_-2'
     when bj_fk_app_rate_3m <= 1 then '04.<=1_1'
     when bj_fk_app_rate_3m > 1 then '05.>1_1'
     else 'else' end as bj_fk_app_rate_3m_score,

case when bj_fk_app_rate_all <= -3 then '00.<=-3_0'
     when bj_fk_app_rate_all <= -2 then '01.<=-2_0'
     when bj_fk_app_rate_all <= -1 then '02.<=-1_-1'
     when bj_fk_app_rate_all <= 0.4 then '03.<=0.4_-2'
     when bj_fk_app_rate_all <= 0.92 then '04.<=0.92_-1'
     when bj_fk_app_rate_all <= 1.67 then '05.<=1.67_1'
     when bj_fk_app_rate_all > 1.67 then '06.>1.67_1'
     else 'else' end as bj_fk_app_rate_all_score,

case when bj_fk_rate_3m <= -2 then '00.<=-2_-2'
     when bj_fk_rate_3m <= -1 then '01.<=-1_-1'
     when bj_fk_rate_3m <= 1.6 then '02.<=1.6_0'
     when bj_fk_rate_3m <= 3 then '03.<=3_0'
     when bj_fk_rate_3m > 3 then '04.>3_1'
     else 'else' end as bj_fk_rate_3m_score,

case when bj_fk_rate_6m <= -2 then '00.<=-2_-2'
     when bj_fk_rate_6m <= -1 then '01.<=-1_-1'
     when bj_fk_rate_6m <= 2 then '02.<=2_0'
     when bj_fk_rate_6m <= 4 then '03.<=4_0'
     when bj_fk_rate_6m > 4 then '04.>4_2'
     else 'else' end as bj_fk_rate_6m_score,

case when bj_hk_fk_rate_1w <= -3 then '00.<=-3_0'
     when bj_hk_fk_rate_1w <= -2 then '01.<=-2_-1'
     when bj_hk_fk_rate_1w <= -1 then '02.<=-1_-1'
     when bj_hk_fk_rate_1w > -1 then '03.>-1_0'
     else 'else' end as bj_hk_fk_rate_1w_score,

case when bj_hk_fk_rate_1m <= -3 then '00.<=-3_0'
     when bj_hk_fk_rate_1m <= -2 then '01.<=-2_-2'
     when bj_hk_fk_rate_1m <= -1 then '02.<=-1_-1'
     when bj_hk_fk_rate_1m > -1 then '03.>-1_0'
     else 'else' end as bj_hk_fk_rate_1m_score,

case when bj_hk_fk_rate_3m <= -3 then '00.<=-3_0'
     when bj_hk_fk_rate_3m <= -2 then '01.<=-2_-3'
     when bj_hk_fk_rate_3m <= -1 then '02.<=-1_-1'
     when bj_hk_fk_rate_3m > -1 then '03.>-1_0'
     else 'else' end as bj_hk_fk_rate_3m_score,

CASE WHEN af_uninstall_cnt_30d <= 0 THEN '00.<=0_0'
     WHEN af_uninstall_cnt_30d > 0 THEN '01.>0_-1'
     ELSE 'else' END as af_uninstall_cnt_30d_score,

CASE WHEN af_uninstall_cnt_lf <= 0 THEN '00.<=0_0'
     WHEN af_uninstall_cnt_lf > 0 AND af_uninstall_cnt_lf <= 1 THEN '01.>0_<=1_-2'
     WHEN af_uninstall_cnt_lf > 1 THEN '02.>1_-3'
     ELSE 'else' END as af_uninstall_cnt_lf_score,

-----行为子分-----
case when finish_issue_rate >= 0.7 then '00.>=0.7_1'
     when finish_issue_rate >= 0.5 then '01.>=0.5_-1'
     when finish_issue_rate >= 0 then '02.>=0_-4'
     when finish_issue_rate < 0 then '03.<0_0'
     else 'else' end as finish_issue_rate_score,

case when message_type = 10 then '00.=10_0'
     when message_type = 9 then '01.=9_1'
     when message_type = 8 then '02.=8_-3'
     when message_type = 1 then '03.=1_-1'
     when message_type = 0 then '04.=0_-3'
     else 'else' end as message_type_score,

case when sd_bj_hk_score <= -999 then '00.<=-999_-1'
     when sd_bj_hk_score <= -6 then '01.<=-6_-2'
     when sd_bj_hk_score <= -3 then '02.<=-3_0'
     when sd_bj_hk_score > -3 then '03.>-3_1'
     else 'else' end as sd_bj_hk_score_bin,

----放款行为-----
CASE 
    -- 当日期小于 20260625 时，使用第一套规则
    WHEN app_date < date'2026-06-25' THEN
        CASE 
            WHEN sd_bj_fk_score <= -999 THEN '00.<=-999_-1'
            WHEN sd_bj_fk_score <= -5 THEN '01.<=-5_-3'
            WHEN sd_bj_fk_score <= -3 THEN '02.<=-3_-2'
            WHEN sd_bj_fk_score <= -2 THEN '03.<=-2_-1'
            WHEN sd_bj_fk_score <= 0 THEN '04.<=0_0'
            WHEN sd_bj_fk_score > 0 THEN '05.>0_1'
            ELSE 'else'
        END
    
    -- 当日期 >= 20260625 时，使用第二套规则
    ELSE
        CASE 
            WHEN sd_bj_fk_score <= -999 THEN '00.<=-999_-2'
            WHEN sd_bj_fk_score <= -5 THEN '01.<=-5_-3'
            WHEN sd_bj_fk_score <= -3 THEN '02.<=-3_-2'
            WHEN sd_bj_fk_score <= -2 THEN '03.<=-2_-1'
            WHEN sd_bj_fk_score <= 0 THEN '04.<=0_0'
            WHEN sd_bj_fk_score > 0 THEN '05.>0_1'
            ELSE 'else'
        END
end as sd_bj_fk_score_bin,

case when sd_bj_fk_jg_score <= -999 then '00.<=-999_-1'
     when sd_bj_fk_jg_score <= -2 then '01.<=-2_-2'
     when sd_bj_fk_jg_score <= 0 then '02.<=0_0'
     when sd_bj_fk_jg_score > 0 then '03.>0_2'
     else 'else' end as sd_bj_fk_jg_score_bin,

case when bj_p_his_loan_total_count <= 4 then '00.<=4_-1'
     when bj_p_his_loan_total_count <= 30 then '01.<=30_0'
     when bj_p_his_loan_total_count > 30 then '02.>30_1'
     else 'else' end as bj_p_his_loan_total_count_bin,

case when bj_p_his_single_loan_max_count <= 3 then '00.<=3_-1'
     when bj_p_his_single_loan_max_count <= 15 then '01.<=15_0'
     when bj_p_his_single_loan_max_count <= 65 then '02.<=65_1'
     when bj_p_his_single_loan_max_count > 65 then '03.>65_1'
     else 'else' end as bj_p_his_single_loan_max_count_bin,

-----收入----
case when income >= 10 then '00.>=10_1'
     when income < 10 then '01.<10_0'
     else 'else' end as income_bin,

case when baseinfo_userprof_degree >= 5 then '00.>=5_1'
     when baseinfo_userprof_degree >= 3 then '01.>=3_0'
     when baseinfo_userprof_degree < 3 then '02.<3_-1'
     else 'else' end as degree_bin,

case when baseinfo_userprof_age > 54 then '00.>54_1'
     when baseinfo_userprof_age > 36 then '01.>36_0'
     when baseinfo_userprof_age >= 26 then '02.>=26_-1'
     when baseinfo_userprof_age <= 25 then '03.<=25_-2'
     else 'else' end as age_bin,

case when baseinfo_has_car = 0 then '=0_1' else '0' end as has_car_bin,

case when app_creditcard_upt_cnt_day60 >= 1 then '>=1_1' else '0' end as app_creditcard_bin,

case when sd_mix_house_marry = 1 then '=1_1' else '0' end as mix_house_marry_bin,

case when sd_mix_employee_pay = 1 then '=00.1_-2'
     when sd_mix_employee_pay = 2 then '=01.2_1'
     else 'else' end as mix_employee_pay_bin,

-----负债-----
CASE WHEN gd_x_10_d_13 > 0.55 THEN '00.>0.55_-3'
     WHEN gd_x_10_d_13 >= 0.2 AND gd_x_10_d_13 <= 0.55 THEN '01.0.2<=_<=0.55_-1'
     WHEN gd_x_10_d_13 < 0.2 THEN '02.<0.2_0'
     ELSE 'else' END as gd_x_10_d_13_bin,

CASE WHEN dyna_amlba_d30_a_cnt >= 50.0 THEN '00.>=50.0_-5'
     WHEN dyna_amlba_d30_a_cnt >= 20.0 AND dyna_amlba_d30_a_cnt < 50.0 THEN '01.20.0<=_<50.0_-3'
     WHEN dyna_amlba_d30_a_cnt >= 0.0 AND dyna_amlba_d30_a_cnt < 20.0 THEN '02.0.0<=_<20.0_0'
     WHEN dyna_amlba_d30_a_cnt < 0.0 THEN '03.<0.0_-1'
     ELSE 'else' END as dyna_amlba_d30_a_cnt_bin,

CASE WHEN advance_gd_x_21 >= 14.0 THEN '00.>=14.0_-5'
     WHEN advance_gd_x_21 >= 11.0 AND advance_gd_x_21 < 14.0 THEN '01.11.0<=_<14.0_-4'
     WHEN advance_gd_x_21 >= 7.0 AND advance_gd_x_21 < 11.0 THEN '02.7.0<=_<11.0_-1'
     WHEN advance_gd_x_21 >= 1.0 AND advance_gd_x_21 < 7.0 THEN '03.1.0<=_<7.0_0'
     WHEN advance_gd_x_21 < 1.0 THEN '04.<1.0_0'
     ELSE 'else' END as advance_gd_x_21_bin,

CASE WHEN advance_gd_x_19 > 8.0 THEN '00.>8.0_-10'
     WHEN advance_gd_x_19 >= 6.0 AND advance_gd_x_19 <= 8.0 THEN '01.6.0<=_<=8.0_-4'
     WHEN advance_gd_x_19 >= 3.0 AND advance_gd_x_19 <= 5.0 THEN '02.3.0<=_<=5.0_1'
     WHEN advance_gd_x_19 > 1.0 AND advance_gd_x_19 <= 2.0 THEN '03.1.0<_<=2.0_0'
     WHEN advance_gd_x_19 > 0.0 AND advance_gd_x_19 <= 1.0 THEN '04.0.0<_<=1.0_-1'
     ELSE 'else' END as advance_gd_x_19_bin,

CASE WHEN app1_finances_inst_discnt_day90 >= 22.0 THEN '00.>=22.0_-1'
     WHEN app1_finances_inst_discnt_day90 < 22.0 THEN '01.<22.0_0'
     ELSE 'else' END as app1_finances_inst_discnt_day90_bin,

CASE WHEN app_loan1_inst_cnt_day30_d_dayall > 0.714 THEN '00.>0.714_-1'
     WHEN app_loan1_inst_cnt_day30_d_dayall <= 0.714 THEN '01.<=0.714_0'
     ELSE 'else' END as app_loan1_inst_cnt_day30_d_dayall_bin,

CASE WHEN app_finance_inst_cnt_day60_d_dayall > 0.333 THEN '00.>0.333_-1'
     WHEN app_finance_inst_cnt_day60_d_dayall <= 0.333 THEN '01.<=0.333_0'
     ELSE 'else' END as app_finance_inst_cnt_day60_d_dayall_bin,

----逾期----
CASE WHEN dyna_amlba_d30_f2_daydiff_max >= 3.0 AND dyna_amlba_d30_f2_daydiff_max < 13.0 THEN '01.3.0<=_<13.0_-4'
     WHEN dyna_amlba_d30_f2_daydiff_max > 0.0 AND dyna_amlba_d30_f2_daydiff_max < 3.0 THEN '02.0.0<_<3.0_0'
     WHEN dyna_amlba_d30_f2_daydiff_max <= 0.0 THEN '03.<=0.0_0'
     WHEN dyna_amlba_d30_f2_daydiff_max >= 13.0 THEN '00.>=13.0_-6'
     ELSE 'else' END as dyna_amlba_d30_f2_daydiff_max_bin,

CASE WHEN dyna_amlba_d60_f3_cnt >= 8.0 THEN '00.>=8.0_-6'
     WHEN dyna_amlba_d60_f3_cnt >= 2.0 AND dyna_amlba_d60_f3_cnt < 8.0 THEN '01.2.0<=_<8.0_-4'
     WHEN dyna_amlba_d60_f3_cnt >= 1.0 AND dyna_amlba_d60_f3_cnt < 2.0 THEN '02.1.0<=_<2.0_-2'
     WHEN dyna_amlba_d60_f3_cnt < 1.0 THEN '03.<1.0_0'
     ELSE 'else' END as dyna_amlba_d60_f3_cnt_bin,

CASE WHEN max_ovd_days_all >= 2.0 AND max_ovd_days_all < 30.0 THEN '01.2.0<=_<30.0_-2'
     WHEN max_ovd_days_all < 2.0 THEN '00.<2.0_0'
     WHEN max_ovd_days_all >= 30.0 THEN '02.>=30.0_-5'
     ELSE 'else' END as max_ovd_days_all_bin,

----欺诈----
CASE WHEN unique_finger >= 4 THEN '00.>=4_-3'
     WHEN unique_finger >= 1 AND unique_finger < 4 THEN '01.1<=_<4_-2'
     WHEN unique_finger < 1 THEN '02.<1_0'
     ELSE 'else' END as unique_finger_bin,

CASE WHEN unique_phone >= 4 THEN '00.>=4_-3'
     WHEN unique_phone >= 1 AND unique_phone < 4 THEN '01.1<=_<4_-2'
     WHEN unique_phone < 1 THEN '02.<1_0'
     ELSE 'else' END as unique_phone_bin,

CASE WHEN shared_contact_cnt_1d > 0 THEN '00.>0_-2'
     WHEN shared_contact_cnt_1d <= 0 THEN '01.<=0_0'
     ELSE 'else' END as shared_contact_cnt_1d_bin,

CASE WHEN finger_30d > 0 THEN '00.>0_-1'
     WHEN finger_30d <= 0 THEN '01.<=0_0'
     ELSE 'else' END as finger_30d_bin,

CASE WHEN phone_30d > 0 THEN '00.>0_-1'
     WHEN phone_30d <= 0 THEN '01.<=0_0'
     ELSE 'else' END as phone_30d_bin,

CASE WHEN email_30d > 0 THEN '00.>0_-1'
     WHEN email_30d <= 0 THEN '01.<=0_0'
     ELSE 'else' END as email_30d_bin,

CASE WHEN phone_with_application_cnt_all > 0 THEN '00.>0_-1'
     WHEN phone_with_application_cnt_all <= 0 THEN '01.<=0_0'
     ELSE 'else' END as phone_with_application_cnt_all_bin,

CASE WHEN phone_with_application_cnt_1d > 0 THEN '00.>0_-1'
     WHEN phone_with_application_cnt_1d <= 0 THEN '01.<=0_0'
     ELSE 'else' END as phone_with_application_cnt_1d_bin,

CASE WHEN other_credit_cnt_all > 0 THEN '00.>0_-1'
     WHEN other_credit_cnt_all <= 0 THEN '01.<=0_0'
     ELSE 'else' END as other_credit_cnt_all_bin,

CASE WHEN other_credit_cnt_1d > 0 THEN '00.>0_-1'
     WHEN other_credit_cnt_1d <= 0 THEN '01.<=0_0'
     ELSE 'else' END as other_credit_cnt_1d_bin,

CASE WHEN register_apply_gap_minutes <= 0 THEN '00.<=0_-3'
     WHEN register_apply_gap_minutes > 0 AND register_apply_gap_minutes <= 6 THEN '01.0<_<=6_-1'
     WHEN register_apply_gap_minutes > 6 AND register_apply_gap_minutes < 250 THEN '02.6<_<250_0'
     WHEN register_apply_gap_minutes >= 250 AND register_apply_gap_minutes < 10000 THEN '03.250<=_<10000_1'
     WHEN register_apply_gap_minutes >= 10000 THEN '04.>=10000_0'
     ELSE 'else' END as register_apply_gap_minutes_bin,

CASE WHEN gathercnt_7d_ip_identity_all >= 8 THEN '00.>=8_-2'
     WHEN gathercnt_7d_ip_identity_all >= 6 AND gathercnt_7d_ip_identity_all < 8 THEN '01.6<=_<8_0'
     WHEN gathercnt_7d_ip_identity_all < 6 THEN '02.<6_0'
     ELSE 'else' END as gathercnt_7d_ip_identity_all_bin,

CASE WHEN gathercnt_3d_ip_identity_all >= 6 THEN '00.>=6_-2'
     WHEN gathercnt_3d_ip_identity_all >= 4 AND gathercnt_3d_ip_identity_all < 6 THEN '01.4<=_<6_-2'
     WHEN gathercnt_3d_ip_identity_all < 4 THEN '02.<4_0'
     ELSE 'else' END as gathercnt_3d_ip_identity_all_bin,

CASE WHEN user_phone_gather_t30user_emcontact_cnt >= 2 THEN '00.>=2_-1'
     WHEN user_phone_gather_t30user_emcontact_cnt < 2 THEN '01.<2_0'
     ELSE 'else' END as user_phone_gather_t30user_emcontact_cnt_bin,

CASE WHEN bank_couse_cnt <= 0 THEN '00.<=0_0'
     WHEN bank_couse_cnt > 0 AND bank_couse_cnt <= 1 THEN '01.0<_<=1_-2'
     WHEN bank_couse_cnt > 1 THEN '02.>1_-4'
     ELSE 'else' END as bank_couse_cnt_bin,

CASE WHEN create_hour >= 0 AND create_hour <= 2 THEN '00.0<=_<=2_-1'
     WHEN create_hour > 2 AND create_hour <= 5 THEN '01.2<_<=5_-2'
     WHEN create_hour > 5 THEN '02.>5_0'
     ELSE 'else' END as create_hour_bin,

CASE WHEN app_uninstall_score <= -4.0 THEN '00.<=-4.0_-4'
     WHEN app_uninstall_score > -4.0 AND app_uninstall_score <= -3.0 THEN '01.-4.0<_<=-3.0_-3'
     WHEN app_uninstall_score > -3.0 AND app_uninstall_score <= -2.0 THEN '02.-3.0<_<=-2.0_-2'
     WHEN app_uninstall_score > -2.0 THEN '03.>-2.0_0'
     ELSE 'else' END as app_uninstall_score_bin,

-----找好投票分----
CASE WHEN m684_new_fqz_0509_p1 <= 0.15 THEN '00.<=0.15_1'
     WHEN m684_new_fqz_0509_p1 > 0.15 THEN '01.>0.15_0'
     ELSE 'else' END as m684_new_fqz_0509_p1_bin,

CASE WHEN m688_new_1t3_ad_0827p1 <= 0.3 THEN '00.<=0.3_1'
     WHEN m688_new_1t3_ad_0827p1 > 0.3 THEN '01.>0.3_0'
     ELSE 'else' END as m688_new_1t3_ad_0827p1_bin,


CASE WHEN m687_old_1t3_ad_tengo_0709p1 <= 0.25 THEN '00.<=0.25_1'
     WHEN m687_old_1t3_ad_tengo_0709p1 > 0.25 THEN '01.>0.25_0'
     ELSE 'else' END as m687_old_1t3_ad_tengo_0709p1_bin,

CASE WHEN m693_new_1t3_ad_0120_p1 <= 0.4 THEN '00.<=0.4_1'
     WHEN m693_new_1t3_ad_0120_p1 > 0.4 THEN '01.>0.4_0'
     ELSE 'else' END as m693_new_1t3_ad_0120_p1_bin,

CASE WHEN mx_sd_lgb674_p1 <= 0.4 THEN '00.<=0.4_1'
     WHEN mx_sd_lgb674_p1 > 0.4 THEN '01.>0.4_0'
     ELSE 'else' END as mx_sd_lgb674_p1_bin,

CASE WHEN m681_new_1t3_advance_0118_p1 <= 0.35 THEN '00.<=0.35_1'
     WHEN m681_new_1t3_advance_0118_p1 > 0.35 THEN '01.>0.35_0'
     ELSE 'else' END as m681_new_1t3_advance_0118_p1_bin,

CASE WHEN m695_new_1t3_ad_0217_p1 <= 0.35 THEN '00.<=0.35_1'
     WHEN m695_new_1t3_ad_0217_p1 > 0.35 THEN '01.>0.35_0'
     ELSE 'else' END as m695_new_1t3_ad_0217_p1_bin,

CASE WHEN m685_new_1t3_adyawey_0612_p1 <= 0.35 THEN '00.<=0.35_1'
     WHEN m685_new_1t3_adyawey_0612_p1 > 0.35 THEN '01.>0.35_0'
     ELSE 'else' END as m685_new_1t3_adyawey_0612_p1_bin,

CASE WHEN m689_old_1t3_ad_0925p1 <= 0.3 THEN '00.<=0.3_1'
     WHEN m689_old_1t3_ad_0925p1 > 0.3 THEN '01.>0.3_0'
     ELSE 'else' END as m689_old_1t3_ad_0925p1_bin,

CASE WHEN mx_sd_lgb678_p1 <= 0.35 THEN '00.<=0.35_1'
     WHEN mx_sd_lgb678_p1 > 0.35 THEN '01.>0.35_0'
     ELSE 'else' END as mx_sd_lgb678_p1_bin,

CASE WHEN m694nocall_new_1t7_ad_0219rh <= 0.15 THEN '00.<=0.15_1'
     WHEN m694nocall_new_1t7_ad_0219rh > 0.15 THEN '01.>0.15_0'
     ELSE 'else' END as m694nocall_new_1t7_ad_0219rh_bin,

CASE WHEN mex_a301_2025v2_nonyy <= 0.21 THEN '00.<=0.21_1'
     WHEN mex_a301_2025v2_nonyy > 0.21 THEN '01.>0.21_0'
     ELSE 'else' END as mex_a301_2025v2_nonyy_bin,

-----找坏投票分----
CASE WHEN m688_new_1t3_ad_0827p1 > 0.55 THEN '00.>0.55_2'
     WHEN m688_new_1t3_ad_0827p1 > 0.5 AND m688_new_1t3_ad_0827p1 <= 0.55 THEN '01.0.5<_<=0.55_1'
     WHEN m688_new_1t3_ad_0827p1 <= 0.5 THEN '02.<=0.5_0'
     ELSE 'else' END as m688_new_1t3_ad_0827p1_bin1,

CASE WHEN m687_old_1t3_ad_tengo_0709p1 > 0.55 THEN '00.>0.55_2'
     WHEN m687_old_1t3_ad_tengo_0709p1 > 0.4 AND m687_old_1t3_ad_tengo_0709p1 <= 0.55 THEN '01.0.4<_<=0.55_1'
     WHEN m687_old_1t3_ad_tengo_0709p1 <= 0.4 THEN '02.<=0.4_0'
     ELSE 'else' END as m687_old_1t3_ad_tengo_0709p1_bin1,

CASE WHEN mx_sd_lgb674_p1 > 0.8 THEN '00.>0.8_2'
     WHEN mx_sd_lgb674_p1 > 0.7 AND mx_sd_lgb674_p1 <= 0.8 THEN '01.0.7<_<=0.8_1'
     WHEN mx_sd_lgb674_p1 <= 0.7 THEN '02.<=0.7_0'
     ELSE 'else' END as mx_sd_lgb674_p1_bin1,

CASE WHEN m685_new_1t3_adyawey_0612_p1 > 0.75 THEN '00.>0.75_2'
     WHEN m685_new_1t3_adyawey_0612_p1 > 0.65 AND m685_new_1t3_adyawey_0612_p1 <= 0.75 THEN '01.0.65<_<=0.75_1'
     WHEN m685_new_1t3_adyawey_0612_p1 <= 0.65 THEN '02.<=0.65_0'
     ELSE 'else'  END as m685_new_1t3_adyawey_0612_p1_bin1,

CASE WHEN m681_new_1t3_advance_0118_p1 > 0.7 THEN '00.>0.7_2'
     WHEN m681_new_1t3_advance_0118_p1 > 0.55 AND m681_new_1t3_advance_0118_p1 <= 0.7 THEN '01.0.55<_<=0.7_1'
     WHEN m681_new_1t3_advance_0118_p1 <= 0.55 THEN '02.<=0.55_0'
     ELSE 'else' END as m681_new_1t3_advance_0118_p1_bin1,

CASE WHEN m695_new_1t3_ad_0217_p1 > 0.65 THEN '00.>0.65_2'
     WHEN m695_new_1t3_ad_0217_p1 > 0.6 AND m695_new_1t3_ad_0217_p1 <= 0.65 THEN '01.0.6<_<=0.65_1'
     WHEN m695_new_1t3_ad_0217_p1 <= 0.6 THEN '02.<=0.6_0'
     ELSE 'else' END as m695_new_1t3_ad_0217_p1_bin1,

CASE WHEN m694nocall_new_1t7_ad_0219rh > 0.54 THEN '00.>0.54_2'
     WHEN m694nocall_new_1t7_ad_0219rh > 0.3 AND m694nocall_new_1t7_ad_0219rh <= 0.54 THEN '01.0.3<_<=0.54_1'
     WHEN m694nocall_new_1t7_ad_0219rh <= 0.3 THEN '02.<=0.3_0'
     ELSE 'else' END as m694nocall_new_1t7_ad_0219rh_bin1,

CASE WHEN m689_old_1t3_ad_0925p1 > 0.65 THEN '00.>0.65_2'
     WHEN m689_old_1t3_ad_0925p1 > 0.5 AND m689_old_1t3_ad_0925p1 <= 0.65 THEN '01.0.5<_<=0.65_1'
     WHEN m689_old_1t3_ad_0925p1 <= 0.5 THEN '02.<=0.5_0'
     ELSE 'else' END as m689_old_1t3_ad_0925p1_bin1,

CASE WHEN mex_a301_2025v2_nonyy > 0.51 THEN '00.>0.51_2'
     WHEN mex_a301_2025v2_nonyy > 0.33 AND mex_a301_2025v2_nonyy <= 0.51 THEN '01.0.33<_<=0.51_1'
     WHEN mex_a301_2025v2_nonyy <= 0.33 THEN '02.<=0.33_0'
     ELSE 'else' END as mex_a301_2025v2_nonyy_bin1,

CASE WHEN sd_duomodel_votegood_scorecard_202605 >= 9.0 THEN '00.>=9'
     WHEN sd_duomodel_votegood_scorecard_202605 >= 6.0 AND sd_duomodel_votegood_scorecard_202605 < 9.0 THEN '01.[6,9)'
     WHEN sd_duomodel_votegood_scorecard_202605 >= 3.0 AND sd_duomodel_votegood_scorecard_202605 < 6.0 THEN '02.[3,6)'
     WHEN sd_duomodel_votegood_scorecard_202605 >= 1.0 AND sd_duomodel_votegood_scorecard_202605 < 3.0 THEN '03.[1,3)'
     WHEN sd_duomodel_votegood_scorecard_202605 < 1.0 THEN '04.<1'
     ELSE 'else' END as vote_good_new,

CASE WHEN sd_duomodel_votebad_scorecard_202605 >= 6.0 THEN '00.>=6'
     WHEN sd_duomodel_votebad_scorecard_202605 >= 2.0 AND sd_duomodel_votebad_scorecard_202605 < 6.0 THEN '01.[2,6)'
     WHEN sd_duomodel_votebad_scorecard_202605 >= 1.0 AND sd_duomodel_votebad_scorecard_202605 < 2.0 THEN '02.[1,2)'
     WHEN sd_duomodel_votebad_scorecard_202605 < 1.0 THEN '03.<1'
     ELSE 'else' END as vote_bad_new,

CASE 
     WHEN sum_vote_core_202605 <= -7.0 THEN '00.<=-7'
     WHEN sum_vote_core_202605 <= -5.0 THEN '01.<=-5'
     WHEN sum_vote_core_202605 <= -2.0 THEN '02.<=-2'
     WHEN sum_vote_core_202605 <= 1 THEN '03.<=1'
     WHEN sum_vote_core_202605 > 1 THEN '04.>1'
     ELSE 'else' END AS sum_vote_core_202605_bin,
    
    -- subscore_behavior_V2
    CASE 
        WHEN app_date < date'2026-06-25' THEN
            CASE 
                WHEN subscore_behavior_V2 <= -5.0 THEN '00.<=-5.0_-6'
                WHEN subscore_behavior_V2 > -5.0 AND subscore_behavior_V2 <= -4.0 THEN '01.-5.0<_<=-4.0_-4'
                WHEN subscore_behavior_V2 > -4.0 AND subscore_behavior_V2 <= 0.0 THEN '02.-4.0<_<=0.0_0'
                WHEN subscore_behavior_V2 > 0.0 THEN '03.>0.0_1'
                ELSE 'else' 
            END
        ELSE
            CASE 
                WHEN subscore_behavior_V2 <= -5.0 THEN '00.<=-5.0_-10'
                WHEN subscore_behavior_V2 > -5.0 AND subscore_behavior_V2 <= -4.0 THEN '01.-5.0<_<=-4.0_-5'
                WHEN subscore_behavior_V2 > -4.0 AND subscore_behavior_V2 <= 0.0 THEN '02.-4.0<_<=0.0_-1'
                WHEN subscore_behavior_V2 > 0.0 THEN '03.>0.0_2' 
                ELSE 'else'
            END
    END AS subscore_behavior_V2_bin,
    
    -- subscore_fk_behavior_V1
    CASE 
        WHEN app_date < date'2026-06-25' THEN
            CASE 
                WHEN subscore_fk_behavior_V1 <= -6.0 THEN '00.<=-6.0_-10'
                WHEN subscore_fk_behavior_V1 > -6.0 AND subscore_fk_behavior_V1 <= -3.0 THEN '01.-6.0<_<=-3.0_-3'
                WHEN subscore_fk_behavior_V1 > -3.0 AND subscore_fk_behavior_V1 <= 2.0 THEN '02.-3.0<_<=2.0_0'
                WHEN subscore_fk_behavior_V1 > 2.0 THEN '03.>2.0_2'
                ELSE 'else' 
            END
        ELSE
            CASE 
                WHEN subscore_fk_behavior_V1 <= -6.0 THEN '00.<=-6.0_-15'
                WHEN subscore_fk_behavior_V1 > -6.0 AND subscore_fk_behavior_V1 <= -3.0 THEN '01.-6.0<_<=-3.0_-4'
                WHEN subscore_fk_behavior_V1 > -3.0 AND subscore_fk_behavior_V1 <= 2.0 THEN '02.-3.0<_<=2.0_1'
                WHEN subscore_fk_behavior_V1 > 2.0 THEN '03.>2.0_1' 
                ELSE 'else'
            END
    END AS subscore_fk_behavior_V1_bin,
    
    -- subscore_income_V5
    CASE 
        WHEN app_date < date'2026-06-25' THEN
            CASE 
                WHEN subscore_income_V5 <= -5.0 THEN '00.<=-5.0_-20'
                WHEN subscore_income_V5 > -5.0 AND subscore_income_V5 <= -2.0 THEN '01.-5.0<_<=-2.0_-2'
                WHEN subscore_income_V5 > -2.0 AND subscore_income_V5 <= 1.0 THEN '02.-2.0<_<=1.0_0'
                WHEN subscore_income_V5 > 1.0 THEN '03.>1.0_2'
                ELSE 'else' 
            END
        ELSE
            CASE 
                WHEN subscore_income_V5 <= -5.0 THEN '00.<=-5.0_-25'
                WHEN subscore_income_V5 > -5.0 AND subscore_income_V5 <= -2.0 THEN '01.-5.0<_<=-2.0_-3'
                WHEN subscore_income_V5 > -2.0 AND subscore_income_V5 <= 1.0 THEN '02.-2.0<_<=1.0_0'
                WHEN subscore_income_V5 > 1.0 THEN '03.>1.0_3'
                ELSE 'else'
            END
    END AS subscore_income_V5_bin,
    
    -- subscore_fraud_V6
    CASE 
        WHEN app_date < date'2026-06-25' THEN
            CASE 
                WHEN subscore_fraud_V6 <= -9.0 THEN '00.<=-9.0_-15'
                WHEN subscore_fraud_V6 > -9.0 AND subscore_fraud_V6 <= -6.0 THEN '01.-9.0<_<=-6.0_-5'
                WHEN subscore_fraud_V6 > -6.0 AND subscore_fraud_V6 <= -1.0 THEN '02.-6.0<_<=-1.0_0'
                WHEN subscore_fraud_V6 > -1.0 THEN '03.>-1.0_1'
                ELSE 'else' 
            END
        ELSE
            CASE 
                WHEN subscore_fraud_V6 <= -9.0 THEN '00.<=-9.0_-20'
                WHEN subscore_fraud_V6 > -9.0 AND subscore_fraud_V6 <= -6.0 THEN '01.-9.0<_<=-6.0_-5'
                WHEN subscore_fraud_V6 > -6.0 AND subscore_fraud_V6 <= -1.0 THEN '02.-6.0<_<=-1.0_-1'
                WHEN subscore_fraud_V6 > -1.0 THEN '03.>-1.0_2' 
                ELSE 'else' 
            END
    END AS subscore_fraud_V6_bin,
    
    -- subscore_debt_V5
    CASE 
        WHEN app_date < date'2026-06-25' THEN
            CASE 
                WHEN subscore_debt_V5 <= -8.0 THEN '00.<=-8.0_-15'
                WHEN subscore_debt_V5 > -8.0 AND subscore_debt_V5 <= -4.0 THEN '01.-8.0<_<=-4.0_-3'
                WHEN subscore_debt_V5 > -4.0 AND subscore_debt_V5 <= -2.0 THEN '02.-4.0<_<=-2.0_0'
                WHEN subscore_debt_V5 > -2.0 THEN '03.>-2.0_2'
                ELSE 'else'
            END
        ELSE
            CASE 
                WHEN subscore_debt_V5 <= -8.0 THEN '00.<=-8.0_-15'
                WHEN subscore_debt_V5 > -8.0 AND subscore_debt_V5 <= -4.0 THEN '01.-8.0<_<=-4.0_-3'
                WHEN subscore_debt_V5 > -4.0 AND subscore_debt_V5 <= -2.0 THEN '02.-4.0<_<=-2.0_-1'
                WHEN subscore_debt_V5 > -2.0 THEN '03.>-2.0_3' 
                ELSE 'else'
            END
    END AS subscore_debt_V5_bin,
    
    -- subscore_overdue_V2
    CASE 
        WHEN app_date < date'2026-06-25' THEN
            CASE 
                WHEN subscore_overdue_V2 <= -9.0 THEN '00.<=-9.0_-15'
                WHEN subscore_overdue_V2 > -9.0 AND subscore_overdue_V2 <= -1.0 THEN '01.-9.0<_<=-1.0_-5'
                WHEN subscore_overdue_V2 > -1.0 THEN '02.>-1.0_0'
                ELSE 'else' 
            END
        ELSE
            CASE 
                WHEN subscore_overdue_V2 <= -9.0 THEN '00.<=-9.0_-20'
                WHEN subscore_overdue_V2 > -9.0 AND subscore_overdue_V2 <= -1.0 THEN '01.-9.0<_<=-1.0_-6'
                WHEN subscore_overdue_V2 > -1.0 THEN '02.>-1.0_0' 
                ELSE 'else' 
            END
    END AS subscore_overdue_V2_bin,



CASE WHEN rule_score_sum_v5_1 <= -13.0 THEN '01.<=-13'
     WHEN rule_score_sum_v5_1 <= -6.0 THEN '02.<=-6'
     WHEN rule_score_sum_v5_1 <= -1.0 THEN '03.<=-1'
     WHEN rule_score_sum_v5_1 > -1.0 THEN '04.>-1'
     ELSE null END as rule_score_sum_v5_1_bin,

CASE 
    WHEN pvalue_mex_a320_2026v1_p1 <= 0.29 THEN '00.<=0.29'
    WHEN pvalue_mex_a320_2026v1_p1 <= 0.332 THEN '01.<=0.332'
    WHEN pvalue_mex_a320_2026v1_p1 <= 0.364 THEN '02.<=0.364'
    WHEN pvalue_mex_a320_2026v1_p1 <= 0.404 THEN '03.<=0.404'
    WHEN pvalue_mex_a320_2026v1_p1 <= 0.435 THEN '04.<=0.435'
    WHEN pvalue_mex_a320_2026v1_p1 <= 0.458 THEN '05.<=0.458'
    WHEN pvalue_mex_a320_2026v1_p1 <= 0.477 THEN '06.<=0.477'
    WHEN pvalue_mex_a320_2026v1_p1 <= 0.511 THEN '07.<=0.511'
    WHEN pvalue_mex_a320_2026v1_p1 <= 0.532 THEN '08.<=0.532'
    WHEN pvalue_mex_a320_2026v1_p1 <= 0.551 THEN '09.<=0.551'
    WHEN pvalue_mex_a320_2026v1_p1 <= 0.578 THEN '10.<=0.578'
    WHEN pvalue_mex_a320_2026v1_p1 > 0.578 THEN '11.>0.578'
END as mex_a320_2026v1_p1_bin,
android_newcust_maincreditlevel_charge_v5_1,
android_newcust_maincreditlevel_charge_v5_2,
android_newcust_maincreditlevel_charge_v4_3,

count(distinct phone_num) as cnt,
count(distinct creditno_appchan) as person_cnt,
count(distinct if(b.biz_id is not null,phone_num,null)) as total_apply_person, 
count(distinct b.biz_id) as total_apply_cnt,
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
  count(if(if_sx_passed_within24h = 0,b.biz_id,null)) as if_sx_notpassed_within24h,
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
	count(if(should_amount != 0 and should_amount is not null,b.biz_id,null)) as total_issue_cnt,
	sum(cast(b.grantcredit_7d_amount as double)) as total_grant_amount,
	sum(cast(apply_amount as double)/1000) as total_apply_amount,
  sum(if(cast(apply_amount as double)/1000!=0,cast(b.grantcredit_7d_amount as double),0)) as total_apply_amount_fenmu,
  sum(if(b.is_t0_window_1 = 1,1,0)) as t0_should_cnt,
  sum(if(b.is_t3_window_1 = 1,1,0)) as t3_should_cnt,
  sum(if(b.is_t0_window_2 = 1,1,0)) as t0_should_cnt_2,
  sum(if(b.is_t3_window_2 = 1,1,0)) as t3_should_cnt_2,
  sum(if(b.is_t0_window_1 = 1,b.is_t0_overdue_1,0)) as is_t0_overdue_1,
  sum(if(b.is_t3_window_1 = 1,b.is_t3_overdue_1,0)) as is_t3_overdue_1,
  sum(if(b.is_t0_window_1 = 1,b.t0_overdue_amount_1,0)) as t0_overdue_amount,
  sum(if(b.is_t3_window_1 = 1,b.t3_overdue_amount_1,0)) as t3_overdue_amount,
  sum(if(b.is_t0_window_1 = 1,b.t0_should_amt_1,0)) as t0_should_amount,
  sum(if(b.is_t3_window_1 = 1,b.t3_should_amt_1,0)) as t3_should_amount,
  sum(if(b.is_t0_window_2 = 1,b.t0_overdue_amount_2,0)) as t0_overdue_amount_2,
  sum(if(b.is_t3_window_2 = 1,b.t3_overdue_amount_2,0)) as t3_overdue_amount_2,
  sum(if(b.is_t0_window_2 = 1,b.t0_should_amt_2,0)) as t0_should_amount_2,
  sum(if(b.is_t3_window_2 = 1,b.t3_should_amt_2,0)) as t3_should_amount_2,
  sum(b.should_capital) as should_capital,
  sum(cast(b.should_amount as double)) as should_amount,
  sum(pre_p2_repay) as pre_p2_repay,
  sum(p1_repay) as p1_repay,
  sum(p2_repay) as p2_repay
from mx.property_level_v5_2 a left join mx.darren_risk_wide_table b 
on a.externalid=b.biz_id
left join (select externalid,sd_approve_version_label from mx.sd_wenj_approve_version_label) t5 
on a.externalid = t5.externalid
left join mx.lucy_property_level_v4_3 c 
on a.externalid = c.externalid
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88 ,89,90,91
;





-- 补充1
drop table if exists mx.sd_wenj_approve_version_label;
create table mx.sd_wenj_approve_version_label as 
select externalid,
max(json_extract_scalar(outputdata, '$.sd_approve_version_label'))  as sd_approve_version_label
 from ods.s21_risk_strategy_record 
where productid in (352) and strategytype='CHAMPION' and etl_date >= '20250829'
 group by 1;



 -- 补充2
 
--:{author=zhangluoxi1, department=墨西哥风险策略, dagName=wenj_risk_wide_table, taskName=lucy_property_level_v4_3}
drop table if EXISTS mx.sd_lucy_property_feature_base
;
--:{author=zhangluoxi1, department=墨西哥风险策略, dagName=wenj_risk_wide_table, taskName=lucy_property_level_v4_3}
create table mx.sd_lucy_property_feature_base as
WITH
  filtered_data AS (
    SELECT
      externalid,
      date(createtime) createdate,
      inputdata,
      outputdata,
      ROW_NUMBER() OVER (
        PARTITION BY
          externalid
        ORDER BY
          createtime desc
      ) AS rk
    FROM
      ods.s21_risk_strategy_record
    WHERE
      strategytype = 'CHAMPION'
      AND productid IN (195)
      AND etl_date >= '20260327'
  )

SELECT
  externalid,
  createdate,
  t1.rand_no_74,
  cast(date(now()) as varchar) as data_date,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.gd_k_101') AS DOUBLE
    )
  ) AS gd_k_101,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.gd_k_109') AS DOUBLE
    )
  ) AS gd_k_109,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.GD_K_101_109') AS DOUBLE
    )
  ) AS GD_K_101_109,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.gd_k_434') AS DOUBLE
    )
  ) AS gd_k_434,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.AdvanceCollectionType_60d') AS DOUBLE
    )
  ) AS AdvanceCollectionType_60d,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.gd_k_112') AS DOUBLE
    )
  ) AS gd_k_112,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.gd_k_104') AS DOUBLE
    )
  ) AS gd_k_104,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.GD_K_104_112') AS DOUBLE
    )
  ) AS GD_K_104_112,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.gd_k_445') AS DOUBLE
    )
  ) AS gd_k_445,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.AdvanceCollectionType_360d') AS DOUBLE
    )
  ) AS AdvanceCollectionType_360d,
  max(
    CAST(
      JSON_EXTRACT_scalar(outputdata, '$.gd_k_135') AS DOUBLE
    )
  ) AS gd_k_135,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(
        outputdata,
        '$.android_newCust_ruleScore_charge_V4_3'
      ) AS DOUBLE
    )
  ) AS android_newCust_ruleScore_charge_V4_3,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(
        inputdata,
        '$.android_newCust_mainCreditLevel_charge_V4_2'
      ) AS DOUBLE
    )
  ) AS android_newCust_mainCreditLevel_charge_V4_2,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(
        outputdata,
        '$.android_newCust_mainCreditLevel_charge_V4_3'
      ) AS DOUBLE
    )
  ) AS android_newCust_mainCreditLevel_charge_V4_3,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.newcust_creditlevel_version') AS varchar
    )
  ) AS newcust_creditlevel_version,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.rand_no_77') AS DOUBLE
    )
  ) AS rand_no_77,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.product_level') AS varchar
    )
  ) AS product_level,
  max(
    CAST(
      JSON_EXTRACT_SCALAR(outputdata, '$.grantcredit_7d_amount') AS DOUBLE
    )
  ) AS grantcredit_7d_amount
FROM
  filtered_data t
  left join mx.wenj_sd_market_base t1 on t.externalid = t1.externalid7
where
  rk = 1
group by
  1,
  2,
  3
;
--:{author=zhangluoxi1, department=墨西哥风险策略, dagName=wenj_risk_wide_table, taskName=lucy_property_level_v4_3}
drop table if EXISTS mx.lucy_property_level_v4_3
;
--:{author=zhangluoxi1, department=墨西哥风险策略, dagName=wenj_risk_wide_table, taskName=lucy_property_level_v4_3}
create table mx.lucy_property_level_v4_3 as
select
  *
from
  (
    select
      *,
      ROW_NUMBER() OVER (
        PARTITION BY
          externalid
        ORDER BY
          data_date desc
      ) AS rk
    from
      mx.sd_lucy_property_feature_base
  )
where
  rk = 1
;













取消全部选择
biz_id
app_group
release_time
app_group_sha256
if_reloan_24h
finish_biz_id
first_loan_finish_people
first_loan_finish_biz_id
app_version
app_date
app_week
app_month
app
tenant
source
if_in_fu_anti_fraud
if_fu_anti_fraud_passed
if_in_fu_anti_fraud_weak
if_fu_anti_fraud_weak_passed
if_in_fu_model
if_fu_model_passed
if_in_fu_sx_refuse
if_fu_sx_refuse_passed
if_in_sx
if_in_sx_6h
if_in_sx_24h
if_in_sx_72h
if_sx_passed
if_sx_passed_6h
if_sx_passed_24h
if_sx_passed_72h
if_issue
contract_amount
loan_cycle
credit_no
is_t0_window_1
is_t0_overdue_1
t0_overdue_amount_1
t0_should_amt_1
is_t3_window_1
is_t3_overdue_1
t3_overdue_amount_1
t3_should_amt_1
if_fu_external_data_passed
mid
app_time
credit_no_new
issue_date
main_sanwich_loan_grp
is_reloan
product_level
tenant_id
phone
repayment_clearing_count_index_tenant_flag
global_limit
repayment_clearing_count_index_tenant
grantcredit_7d_amount
update_time
v3_flag
grantcredit_amount
fd_creditlevel_main_v3_3
fd_creditlevel_main_v4
mex_b300_2025v2
m699_rh_new_bin
fd_creditlevel_main_v4_2
fd_high_pass_label
t0_overdue_amount_2
t0_should_amt_2
t0_overdue_amount_3
t0_should_amt_3
t0_overdue_amount_4
t0_should_amt_4
t3_overdue_amount_2
t3_should_amt_2
t3_overdue_amount_3
t3_should_amt_3
t3_overdue_amount_4
t3_should_amt_4
is_t0_window_2
is_t0_window_3
is_t0_window_4
is_t0_overdue_2
is_t0_overdue_3
is_t0_overdue_4
is_t3_window_2
is_t3_window_3
is_t3_window_4
is_t3_overdue_2
is_t3_overdue_3
is_t3_overdue_4
change_used_grantamount
oneday_used_grantamount
credit_amount
daily_max_available_limit
last_product_level
product_level_change
if_in_sx_120h
if_sx_passed_120h
if_in_fu_post_anti_fraud_rerun
if_fu_post_anti_fraud_rerun_passed
if_in_fu_post_weak_anti_fraud_rerun
if_fu_post_weak_anti_fraud_rerun_passed
if_in_fu_post_model_reject_rerun
if_fu_post_model_reject_rerun_passed
if_in_fu_external_data
increase_limit_batch_id
use_time
coupon_use_status
transfer_time
m698_old_1t3_voting_0619rh
first_grantcredit_7d_amount
first_issue_date
product_level_test_251205_flag
equal_houshou_should_interest
real_issue_amount
randd
temp_grant_amount
temp_limit_test_flag
strategy_temp_limit_test_flag
is_loop_limit_expired
if_inherit_tag
android_oldcust_maincreditlevel_charge_v5_1
max_overdue_day_30d_all_strategy_test
product_name_new
change_product_tag
strategy_temp_limit_interval_test_flag
temp_credit_amount_issue_tag
if_product_or_maxlimit_change_tag
cap_1point8_strategy_test
cap_1point8cap_strategy_test_flag
pvalue_mex_b320_2026v1_long_p1_group
cap_test_fd_global_limit_cap
cap_test_credit_amount
repayment_clearing_count_tenant_flag
repayment_clearing_count_tenant
last_product_origin
max_overdue_day_30d_all
android_oldcust_maincreditlevel_charge_v5_2
android_oldcust_votescore_charge_v5_1
curr_biz_id
one_click_loan_tag
daily_max_limit_tag
v5_fraud_score
v5_behavior_score
android_oldcust_midcreditlevel_charge_v5_1
android_oldcust_rulescore_charge_v5_1
pvalue_mex_b321_2026v1_p1
thirdparty_izi_whatsapp_register_status
if_system_run_too_short
unique_email_cnt
history_loanrec_cnt_lastprepaydays_v2
max_ovd_days_all
af_uninstall_cnt_30d
last_repay_gap_days_app_group
minstay_repayplan_second_30d_mid
baseinfo_userprof_age
baseinfo_userprof_degree
question3
question6_v2
advance_duotou_cnt_730d
advance_duotou_cnt_x_19
apply_amount
pvalue_mex_b320_2026v1_long_p1
android_oldcust_midcreditlevel_charge_v5_2
temp_credit_amount_strategy_test_flag
v5_3_fraud_score
v5_3_behavior_score
android_oldcust_votescore_charge_v5_3
android_oldcust_maincreditlevel_charge_v5_3
android_oldcust_midcreditlevel_charge_v5_3
other_app_has_loan_flag
other_app_has_loan_tag
other_app_has_overdue_tag
other_app_has_overdue_interval_tag
curr_ovd_cnt_all
curr_ovd_cnt_other_app_group_30d
curr_ovd_cnt_other_app_group_60d
curr_ovd_cnt_other_app_group_90d
curr_ovd_cnt_this_app_group
curr_ovd_cnt_other_app_group
loan_contract_amount
android_oldcust_rulescore_charge_v5_3
thirdparty_izi_whatsapp_register_status_score
if_system_run_too_short_score
unique_email_cnt_score
history_loanrec_cnt_lastprepaydays_v2_score
max_overdue_day_30d_all_score
max_ovd_days_all_score
af_uninstall_cnt_30d_score
last_repay_gap_days_app_group_score
minstay_repayplan_second_30d_mid_score
baseinfo_userprof_age_score
baseinfo_userprof_degree_score
question3_score
question6_v2_score
advance_duotou_cnt_x_19_score
advance_duotou_cnt_730d_score
v5_3_fraud_group_score
v5_3_behavior_group_score
model_698_score
model_699_score
model_p2_1t_score
android_oldcust_votescore_charge_v5_3_bin
android_oldcust_rulescore_charge_v5_3_bin
change_flag
if_in_sx_48h
if_sx_passed_48h
cust_id
product_level_test_260701
change_flag1
fd_changepro_v5_3
emcontact_curr_ovd_cnt_all_test_flag
product_level_change_test_260722
product_test_0722
product_random_0722
tagg_0729
temp_limit_0729_tag
curr_main_credit_limit_0730
temp_limit_0730_tag
risk_credit_limit
tagg_0805
temp_limit_0805_tag
curr_main_credit_limit_0806
temp_limit_0806_tag
fd_use_creditamount_score_v1
fd_use_creditamount_type
tagg_0812
temp_limit_0812_tag
curr_main_credit_limit_0813
temp_limit_0813_tag
stgy_advance_gd_k_136
stgy_advance_gd_k_292
stgy_advance_gd_k_104
beh_main_reject_applypct_day60
beh2_o_create_reject_pct_d7
stgy_amlta_d180_record_date_unique_cnt
stgy_dyna_amlta_d60_daydiff_median
stgy_dyna_amlba_d21_b_cnt
stgy_dyna_amlba_d30_c_cnt
finish_issue_rate
stgy_bj_loan_count_1w
question5
msg2_loandue_addpctall_day1
android_oldcust_behavior_subscore_charge_v6_1
emcontact_curr_ovd_cnt_all
stgy_dyna_amlba_d30_f2_daydiff_max
stgy_dyna_amlba_d60_f3_cnt
android_oldcust_overdue_subscore_charge_v6_1
apply_hour
history_loanrec_time_apply
af_uninstall_cnt_lf
unique_phone
android_oldcust_fraud_subscore_charge_v6_1
stgy_advance_gd_x_55
stgy_advance_gd_x_12
stgy_advance_gd_x_34
app_loan1_inst_cnt_day7
app3_mix_loan1_cfinst_cnt_d30
stgy_bj_apply_count_1w
stgy_bj_apply_jgs_12m
stgy_bj_apply_jgs_1w
android_oldcust_apply_subscore_charge_v6_1
income
baseinfo_has_car
baseinfo_has_house
baseinfo_marry
baseinfo_employee_type
android_oldcust_income_subscore_charge_v6_1
android_oldcust_rule_score_charge_v6_1
pvalue_mex_b311_2025v1_p1
pvalue_mex_b321_2026v2_p1
m696_old_1t3_bj_iz_0530_p1
m687_old_1t3_ad_tengo_0709p1
pvalue_mex_b329_2026v1_byid_p1
android_oldcust_voting_score_charge_v6_1
pvalue_mex_b320_2026v2_p1
android_oldcust_midcreditlevel_charge_v6_1
android_oldcust_maincreditlevel_charge_v6_1
tagg_0819
temp_limit_0819_tag
curr_main_credit_limit_0820
temp_limit_0820_tag
stgy_advance_gd_x_34_score
stgy_advance_gd_x_12_score
stgy_advance_gd_x_55_score
stgy_bj_apply_jgs_12m_score
stgy_bj_apply_jgs_1w_score
stgy_bj_apply_count_1w_score
app_loan1_inst_cnt_day7_score
app3_mix_loan1_cfinst_cnt_d30_score
advance_duotou_cnt_x_19_score_v6
advance_duotou_cnt_730d_score_v6
beh2_o_create_reject_pct_d7_score
beh_main_reject_applypct_day60_score
stgy_dyna_amlta_d60_daydiff_median_score
stgy_amlta_d180_record_date_unique_cnt_score
stgy_dyna_amlba_d30_c_cnt_score
stgy_dyna_amlba_d21_b_cnt_score
stgy_advance_gd_k_104_score
stgy_advance_gd_k_136_score
stgy_advance_gd_k_292_score
stgy_bj_loan_count_1w_score
last_repay_gap_days_app_group_score_v6
finish_issue_rate_score
msg2_loandue_addpctall_day1_score
question3_score_v6
question5_score
question6_v2_score_v6
stgy_dyna_amlba_d60_f3_cnt_score
max_ovd_days_all_score_v6
emcontact_curr_ovd_cnt_all_score
stgy_dyna_amlba_d30_f2_daydiff_max_score
max_overdue_day_30d_all_score_v6
history_loanrec_cnt_lastprepaydays_v2_score_v6
unique_email_cnt_score_v6
unique_phone_score
af_uninstall_cnt_30d_score_v6
af_uninstall_cnt_lf_score
minstay_repayplan_second_30d_mid_score_v6
app_hour_score
baseinfo_userprof_age_score_v6
baseinfo_userprof_degree_score_v6
income_score
baseinfo_employee_type_score
baseinfo_marry_score
baseinfo_has_house_score
baseinfo_has_car_score
m687_old_1t3_ad_tengo_0709p1_score
m698_old_1t3_voting_0619rh_score
m696_old_1t3_bj_iz_0530_p1_score
pvalue_mex_b311_2025v1_p1_score
pvalue_mex_b329_2026v1_byid_p1_score
pvalue_mex_b320_2026v1_long_p1_score
pvalue_mex_b321_2026v2_p1_score
pvalue_mex_b321_2026v1_p1_score
android_oldcust_behavior_subscore_charge_v6_1_score
android_oldcust_fraud_subscore_charge_v6_1_score
android_oldcust_overdue_subscore_charge_v6_1_score
android_oldcust_apply_subscore_charge_v6_1_score
android_oldcust_income_subscore_charge_v6_1_score
