tips: 标记分子分母、口径，计数的id

1、安装量 by 日期 柱状图
2、安装量 & t0注册 by渠道
3、安装量 by app版本
4、t0安装-注册率 by 渠道 折线图
5、t0安装-注册率 by app版本 折线图
6、t0安装到注册 by 步骤、日期 折线图
7、t0安装到注册各步骤的数量、转化率 by日期 表格

8、注册量 by 日期 柱状图
9、t0注册-进件率 by app版本
10、t0注册-实名 by 步骤、日期
11、t0实名-进件 by 步骤、日期
12、t0进件-用信 by 步骤、日期
13、t0注册到进件各步骤的数量、转化率 by日期 表格

问题
1、卸载后重新安装、注册的判定：只统计install，不统计reinstall
2、媒体渠道判定，网盟劫持？调整：最后X次助攻如果为大媒体渠道，则media_source调整为助攻渠道											


自研埋点的fpid和设备绑定，卸载重新安装不变
af埋点的appsflyer_id卸载重新安装会生成新的

1、part2，注册成功的数据限制一下安装日期也是当天 done
2、活体提交后，成功率 done 
3、part1.6，比率按上一步作为分母计算，现在都是用的安装数  done 
4、在part1中加类似2.4这种分步骤的转化率 done 
5、增加一个Android、ios的平台的筛选项 done 
6、看是否能增加月维度的数据筛选

-- event data extract
这张表（7点30）

drop table if exists ind.kht_conversion_from_download_tmp;
create table IF NOT EXISTS ind.kht_conversion_from_download_tmp as
select s.* from 
    (select *
    from ods.s08_appsflyer_push_data  s
    where etl_date >= to_char(current_date - interval '30' day,'yyyymmdd')
    --and appsflyer_id is not null 
    --and app_id = 'com.sahabatmikro'
    and (event_name in ('install','reinstall') or platform='ios' or event_source='S2S' or json_extract_scalar(event_value,'$.pkg_name') = 'com.sahabatmikro' )-- only pkg=samir
    and event_name in (
        'install','reinstall',
        --start
        'app_start_banner_page',
        'unlogin_Home_page',
        -- sign-in phase1
        'Sign_in_page',
        -- sign-in phase2
        'Sign_in_input_phone',
        'Sign_in_input_phone_out',
        -- sign-in phase3
        'Sign_in_code_sent_click_new',
        'Sign_in_vcode_sent_click_new',
        'Sign_in_click_confirm',
        'Sign_in_password_click_new',
        -- sign-in phase4
        'Sign_in_click_new',
        'Sign_in_vcode_click_new',
        -- sign-in final
        'Sign_in_success_new',
        -- ktp
        'Ktp_info_page',
        'ktp_info_page_back',
        'urgeStay_KTP_1',
        'urgeStay_KTP_2',
        'urgeStay_KTP_3',
        'birthday_time',
        'name_time',
        'KTP_time',
        'selfie_click',
        -- ktp done
        'Ktp_info_next_click',
        -- person info
        'Personal_info_page',
        'Personal_info_page_back',
        'urgeStay_personalInfo_1',
        'urgeStay_personalInfo_2',
        'urgeStay_personalInfo_3',
        'religion_time',
        'birthplace_time',
        'home_ownership_time',
        'region_time',
        'address_time',
        'postcode_time',
        'location_time',
        'marriage_time',
        'children_time',
        'education_time',
        'email_time',
        -- person info done
        'Personal_info_next_click',
        -- work info
        'Work_info_page',
        'Work_info_page_back',
        'urgeStay_job_1',
        'urgeStay_job_2',
        'urgeStay_job_3',
        'work_field_time',
        'work_year_time',
        'monthly_income_time',
        'company_name_time',
        'company_phone_time',
        'company_region_time',
        'company_address_time',
        -- work info done
        'Work_info_next_click',
        -- emergency
        'Emergency_page',
        'Emergency_page_back',
        'urgeStay_contact_1',
        'urgeStay_contact_2',
        'urgeStay_contact_3',
        'contact1_relation_time',
        'contact1_name_time',
        'contact1_phone_time',
        'contact2_relation_time',
        'contact2_name_time',
        'contact2_phone_time',
        -- emergency done
        'Emergency_next_click',
        -- bank
        'Bank_account_page',
        'Bank_account_page_back',
        'urgeStay_bankcard_1',
        'urgeStay_bankcard_2',
        'urgeStay_bankcard_3',
        'bank_name_time',
        'holder_name_time',
        'bank_account_time',
        -- bank done
        'Submit_bank_account_click',
        -- liveness
        'Liveness_page_firstloan',
        'liveness_izi',
        'liveness_advance',
        -- liveness done
        'Liveness_success_firstloan',
        -- audit success
        'audit_success_firstloan_origin',
        -- agreement otp
        'agreement_page_otp',
        -- agreement otp done?
        'agreement_page_otp_fill',
        -- digi sign
        'agreement_page_digisign',
        'agreement_page_digisign_back',
        'agreement_page_digisign_draw',
        'agreement_page_digisign_delete',
        -- digi sign done
        'agreement_page_digisign_confirm',
        -- submit
        'Submit_firstloan_applications_click'
    )
) s
left join
(
select * from 
    (select appsflyer_id,date(substr(event_time_selected_timezone,1,10)) as dt,
            max(case when event_name='Sign_in_success_old' then 1 else 0 end ) as old,
            max(case when event_name='Sign_in_success_new' then 1 else 0 end ) as new
            from ods.s08_appsflyer_push_data
            where etl_date >= to_char(current_date - interval '35' day,'yyyymmdd')  
            and date(substr(event_time_selected_timezone,1,10))=date(substr(install_time_selected_timezone,1,10))
            and event_name in ('Sign_in_success_old','Sign_in_success_new')
            group by 1,2
    ) m
where old=1 and new=0
) m
on m.appsflyer_id=s.appsflyer_id and m.dt = date(substr(s.event_time_selected_timezone,1,10)) --and s.event_name='install'
where m.appsflyer_id is null
;




-- summarize，from install to sign in
drop table if exists ind.kht_conversion_from_download_t0;
create table ind.kht_conversion_from_download_t0 as
select 
    tt.*
from 
    (select 
    date_trunc('month',t1.date) as install_mt
    ,date_trunc('week',t1.date) as install_wk
    --,t1.hour as install_hour
    ,t1.date
    ,t1.app_version
    ,t1.campaign
    ,t1.media_source 
    ,case when platform='ios' then 'iOS' when platform='android' then 'Android' else null end as  source
    ,count(distinct t1.appsflyer_id)  cnt_base
    ,count(distinct case when date_diff('day',t1.date,t8.date)=0 and t8.appsflyer_id is not null then t8.appsflyer_id  end) cnt_start
    ,count(distinct case when date_diff('day',t1.date,t2.date)=0 and t2.appsflyer_id is not null then t2.appsflyer_id  end) cnt_signin_phase1
    ,count(distinct case when date_diff('day',t1.date,t3.date)=0 and t3.appsflyer_id is not null then t3.appsflyer_id  end) cnt_signin_phase2
    ,count(distinct case when date_diff('day',t1.date,t6.date)=0 and t6.appsflyer_id is not null then t6.appsflyer_id  end) cnt_signin_phase3
    ,count(distinct case when date_diff('day',t1.date,t4.date)=0 and t4.appsflyer_id is not null then t4.appsflyer_id  end) cnt_signin_phase4
    ,count(distinct case when date_diff('day',t1.date,t5.date)=0 and t5.appsflyer_id is not null then t5.appsflyer_id  end) cnt_signin_success
    from 
    (select  
        campaign,campaign_id,tenant_id,app_version,client_id,app_id,
        case when platform = 'ios' and  media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  media_source = 'restricted' then 'IOS-fb'
			when platform = 'ios' and  media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  media_source = 'tangads' then 'IOS-tangads'
		    --when platform = 'ios' and  media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when media_source='googleadwords_int' then 'Google'
            when media_source='Facebook Ads' or media_source='restricted' then 'Facebook'
            when media_source='organic' then 'Organic'
            when media_source = 'shareit_int' then 'Shareit'
            when  media_source = 'kreditlist_int' or (media_source = 'vfine_int' and partner like '%redi%'  ) 
            or 
            (media_source is null and partner = 'kreditlist')
            then 'kreditlist_int'
            when media_source = 'vfine_int' or media_source = 'adecentptuo_int' then 'Vfine'
            when media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
            when media_source = 'kwaiforbusiness_int' then 'Kwai'
            when media_source = 'cashcashpro' then 'cashcashpro'
            when media_source = 'cashcerdasid_int' then 'cashcerdas'
            when media_source = 'kredit pintal' then 'kp'
            when media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
            when regexp_like(campaign, '^pp') then 'Novabeyond'
            when media_source = 'pyxis_int' then 'pyxis'
            when media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
            when media_source = 'Twitter' then 'twitter'
            when media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
                            ,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
                            ,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
                            ,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
                            ,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
                            ,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
                            ,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
                            ,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
                            ,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' or partner ='appscuckoobd650'then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
                            ,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(campaign) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when campaign like '%CookeAds_CPI%' then 'CookeAds_CPI'
			when campaign ='CookeAds_CPS' or lower(campaign) like '%cookeads%' then 'CookeAds_CPS'
			when partner = '19mobicn' then '19mobi'
			when campaign = 'Samire_Jan2025youmi' then 'youmi'
			when media_source ='yupaamj_int' then 'yup'
			--when regexp_like(campaign, '^pp') then 'Novabeyond'
			when media_source = 'mintegral_int' then 'mintegral_int'
			when lower(media_source) like '%grab%' then 'Grab'
			when media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(campaign) like '%runto%' then 'RUNTOA'
			when lower(campaign) like '%mejoy%'  then 'mejoy'
			when lower(campaign) like '%yolo%'  then 'yolo'
			when media_source ='LinkAja_ads' then 'LinkAja_ads'
			when media_source ='easycash01' then 'easycash01'
			when media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when media_source ='tangads' then 'tangads'
			when media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when media_source ='oppoglobal_int' then 'oppoglobal_int'
			when media_source like '%_int%' then 'other'
			else 'Organic'
        end as media_source
        ,date(substr(event_time_selected_timezone,1,10)) as date
        ,substr(event_time_selected_timezone,1,13)    as hour
        ,event_time_selected_timezone  
        ,appsflyer_id
        ,platform
    from ind.kht_conversion_from_download_tmp  
    where event_name in  ('install','reinstall' ) 
    and etl_date>=to_char(current_date - interval '20' day,'yyyymmdd')
    group by 1,2,3,4,5,6,7,8,9,10,11,12
    ) t1

    left join 
    (select  
    date(substr(event_time_selected_timezone,1,10)) as date
    ,appsflyer_id
    from ind.kht_conversion_from_download_tmp  
    where event_name in (
        'app_start_banner_page',
        'unlogin_Home_page')  --start
    and etl_date>=to_char(current_date - interval '20' day,'yyyymmdd')
    group by 1,2
    ) t8
    on t1.appsflyer_id = t8.appsflyer_id  

    left join
    (
    select 
    date(substr(event_time_selected_timezone,1,10)) as date
    ,appsflyer_id
    from ind.kht_conversion_from_download_tmp 
    where event_name in 
        (-- sign-in phase1
        'Sign_in_page')  
    and etl_date>=to_char(current_date - interval '20' day,'yyyymmdd')
    group by 1,2
    ) t2
    on  t1.appsflyer_id = t2.appsflyer_id

    left join
    (
    select  
    date(substr(event_time_selected_timezone,1,10)) as date
    ,appsflyer_id
    from ind.kht_conversion_from_download_tmp 
    where event_name in 
        (-- sign-in phase2
        'Sign_in_input_phone',
        'Sign_in_input_phone_out')   
    and etl_date>=to_char(current_date - interval '20' day,'yyyymmdd')
    group by 1,2
    ) t3
    on  t1.appsflyer_id = t3.appsflyer_id

    left join
    (
    select  
    date(substr(event_time_selected_timezone,1,10)) as date
    ,appsflyer_id
    from ind.kht_conversion_from_download_tmp  
    where event_name in 
        ( -- sign-in phase3
        'Sign_in_code_sent_click_new',
        'Sign_in_vcode_sent_click_new',
        'Sign_in_click_confirm')  
    and etl_date>=to_char(current_date - interval '20' day,'yyyymmdd')
    group by 1,2
    ) t6
    on  t1.appsflyer_id = t6.appsflyer_id

    left join
    (
    select  
    date(substr(event_time_selected_timezone,1,10)) as date
    ,appsflyer_id
    from ind.kht_conversion_from_download_tmp
    where event_name in 
        (-- sign-in phase4
        'Sign_in_click_new',
        'Sign_in_vcode_click_new')  
    and etl_date>=to_char(current_date - interval '20' day,'yyyymmdd')
    group by 1,2
    ) t4
    on  t1.appsflyer_id = t4.appsflyer_id

    left join
    (
    select  
    date(substr(event_time_selected_timezone,1,10)) as date
    ,appsflyer_id
    from ind.kht_conversion_from_download_tmp  
    where event_name in 
        (-- sign-in final
        'Sign_in_success_new'
        )  
    and etl_date>=to_char(current_date - interval '20' day,'yyyymmdd')
    group by 1,2
    ) t5
    on  t1.appsflyer_id = t5.appsflyer_id
    group by 1,2,3,4,5,6,7
) tt

;

-- ###########################################################################################
-- ###########################################################################################
-- ###########################################################################################

-- summarize，from sign in to audit

drop table if exists ind.kht_conversion_from_signin_to_audit_t0_tmp;
create table ind.kht_conversion_from_signin_to_audit_t0_tmp as
With user_daily_events AS (
    SELECT
        date(substr(event_time_selected_timezone,1,10)) as date,
        appsflyer_id,
        MAX(CASE WHEN event_name in ('install','reinstall') THEN campaign END) as campaign,
        MAX(CASE WHEN event_name in ('install','reinstall') THEN app_version END) as app_version,
        MAX(CASE WHEN event_name in ('install','reinstall') THEN media_source END) as media_source,
        MAX(CASE WHEN event_name in ('install','reinstall') THEN platform END) as platform,

        MAX(CASE WHEN event_name in ('install','reinstall') THEN 1 ELSE 0 END) AS is_install_day,
        MAX(CASE WHEN event_name = 'Sign_in_success_new' THEN 1 ELSE 0 END) AS is_signin_day,
        MAX(CASE WHEN event_name IN ('Ktp_info_page', 'ktp_info_page_back', 'urgeStay_KTP_1', 'urgeStay_KTP_2', 'urgeStay_KTP_3', 'birthday_time', 'name_time', 'KTP_time', 'selfie_click') THEN 1 ELSE 0 END) AS has_ktp,
        MAX(CASE WHEN event_name = 'Ktp_info_next_click' THEN 1 ELSE 0 END) AS has_ktp_done,
        MAX(CASE WHEN event_name IN ('Personal_info_page', 'Personal_info_page_back', 'urgeStay_personalInfo_1', 'urgeStay_personalInfo_2', 'urgeStay_personalInfo_3', 'religion_time', 'birthplace_time', 'home_ownership_time', 'region_time', 'address_time', 'postcode_time', 'location_time', 'marriage_time', 'children_time', 'education_time', 'email_time') THEN 1 ELSE 0 END) AS has_personinfo,
        MAX(CASE WHEN event_name = 'Personal_info_next_click' THEN 1 ELSE 0 END) AS has_personinfo_done,
        MAX(CASE WHEN event_name IN ('Work_info_page', 'Work_info_page_back', 'urgeStay_job_1', 'urgeStay_job_2', 'urgeStay_job_3', 'work_field_time', 'work_year_time', 'monthly_income_time', 'company_name_time', 'company_phone_time', 'company_region_time', 'company_address_time') THEN 1 ELSE 0 END) AS has_workinfo,
        MAX(CASE WHEN event_name = 'Work_info_next_click' THEN 1 ELSE 0 END) AS has_workinfo_done,
        MAX(CASE WHEN event_name IN ('Emergency_page', 'Emergency_page_back', 'urgeStay_contact_1', 'urgeStay_contact_2', 'urgeStay_contact_3', 'contact1_relation_time', 'contact1_name_time', 'contact1_phone_time', 'contact2_relation_time', 'contact2_name_time', 'contact2_phone_time') THEN 1 ELSE 0 END) AS has_emergency,
        MAX(CASE WHEN event_name = 'Emergency_next_click' THEN 1 ELSE 0 END) AS has_emergency_done,
        MAX(CASE WHEN event_name IN ('Bank_account_page', 'Bank_account_page_back', 'urgeStay_bankcard_1', 'urgeStay_bankcard_2', 'urgeStay_bankcard_3', 'bank_name_time', 'holder_name_time', 'bank_account_time') THEN 1 ELSE 0 END) AS has_bank,
        MAX(CASE WHEN event_name = 'Submit_bank_account_click' THEN 1 ELSE 0 END) AS has_bank_done,
        MAX(CASE WHEN event_name = 'Liveness_page_firstloan' THEN 1 ELSE 0 END) AS has_liveness,
        MAX(CASE WHEN event_name = 'Liveness_success_firstloan' THEN 1 ELSE 0 END) AS has_liveness_done,
        MAX(CASE WHEN event_name in ('liveness_izi','liveness_advance') and json_extract_scalar(json_extract_scalar(event_value,'$.entity'),'$.code') !='SUCCESS' THEN 1 ELSE 0 END) AS has_liveness_done_fail,
        MAX(CASE WHEN event_name = 'audit_success_firstloan_origin' THEN 1 ELSE 0 END) AS has_auditsuccess
    from
    (select
        event_time_selected_timezone,
        appsflyer_id,
        event_name,
        campaign,
        app_version,
        platform,event_value,
        case when platform = 'ios' and  media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  media_source = 'restricted' then 'IOS-fb'
			when platform = 'ios' and  media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  media_source = 'tangads' then 'IOS-tangads'
		    --when platform = 'ios' and  media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when media_source='googleadwords_int' then 'Google'
            when media_source='Facebook Ads' or media_source='restricted' then 'Facebook'
            when media_source='organic' then 'Organic'
            when media_source = 'shareit_int' then 'Shareit'
            when  media_source = 'kreditlist_int' or (media_source = 'vfine_int' and partner like '%redi%'  ) 
            or 
            (media_source is null and partner = 'kreditlist')
            then 'kreditlist_int'
            when media_source = 'vfine_int' or media_source = 'adecentptuo_int' then 'Vfine'
            when media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
            when media_source = 'kwaiforbusiness_int' then 'Kwai'
            when media_source = 'cashcashpro' then 'cashcashpro'
            when media_source = 'cashcerdasid_int' then 'cashcerdas'
            when media_source = 'kredit pintal' then 'kp'
            when media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
            when regexp_like(campaign, '^pp') then 'Novabeyond'
            when media_source = 'pyxis_int' then 'pyxis'
            when media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
            when media_source = 'Twitter' then 'twitter'
            when media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
                            ,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
                            ,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
                            ,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
                            ,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
                            ,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
                            ,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
                            ,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
                            ,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' or partner ='appscuckoobd650'then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
                            ,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(campaign) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when campaign like '%CookeAds_CPI%' then 'CookeAds_CPI'
			when campaign ='CookeAds_CPS' or lower(campaign) like '%cookeads%' then 'CookeAds_CPS'
			when partner = '19mobicn' then '19mobi'
			when campaign = 'Samire_Jan2025youmi' then 'youmi'
			when media_source ='yupaamj_int' then 'yup'
			--when regexp_like(campaign, '^pp') then 'Novabeyond'
			when media_source = 'mintegral_int' then 'mintegral_int'
			when lower(media_source) like '%grab%' then 'Grab'
			when media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(campaign) like '%runto%' then 'RUNTOA'
			when lower(campaign) like '%mejoy%'  then 'mejoy'
			when lower(campaign) like '%yolo%'  then 'yolo'
			when media_source ='LinkAja_ads' then 'LinkAja_ads'
			when media_source ='easycash01' then 'easycash01'
			when media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when media_source ='tangads' then 'tangads'
			when media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when media_source ='oppoglobal_int' then 'oppoglobal_int'
			when media_source like '%_int%' then 'other'
			else 'Organic'
        end as media_source
    FROM ind.kht_conversion_from_download_tmp  
    where etl_date>=to_char(current_date - interval '20' day,'yyyymmdd')
    )
    GROUP BY 1, 2
)

-- 
SELECT 
    date_trunc('month', s.date) as install_mt,
    date_trunc('week', s.date) as install_wk,
    s.date,
    s.app_version,
    s.campaign,
    s.media_source,
    case when s.platform='ios' then 'iOS' when s.platform='android' then 'Android' else null end as source,
    count(distinct s.appsflyer_id) as signin_success_cnt,
    count(distinct case when e.has_ktp = 1 then e.appsflyer_id end) as cnt_ktp,
    count(distinct case when e.has_ktp_done = 1 then e.appsflyer_id end) as cnt_ktp_done,
    count(distinct case when e.has_personinfo = 1 then e.appsflyer_id end) as cnt_personinfo,
    count(distinct case when e.has_personinfo_done = 1 then e.appsflyer_id end) as cnt_personinfo_done,
    count(distinct case when e.has_workinfo = 1 then e.appsflyer_id end) as cnt_workinfo,
    count(distinct case when e.has_workinfo_done = 1 then e.appsflyer_id end) as cnt_workinfo_done,
    count(distinct case when e.has_emergency = 1 then e.appsflyer_id end) as cnt_emergency,
    count(distinct case when e.has_emergency_done = 1 then e.appsflyer_id end) as cnt_emergency_done,
    count(distinct case when e.has_bank = 1 then e.appsflyer_id end) as cnt_bank,
    count(distinct case when e.has_bank_done = 1 then e.appsflyer_id end) as cnt_bank_done,
    count(distinct case when e.has_liveness = 1 then e.appsflyer_id end) as cnt_liveness,
    count(distinct case when e.has_liveness_done = 1 then e.appsflyer_id end) as cnt_liveness_done,
    count(distinct case when e.has_liveness_done_fail = 1 then e.appsflyer_id end) as cnt_liveness_done_fail,
    count(distinct case when e.has_auditsuccess = 1 then e.appsflyer_id end) as cnt_auditsuccess

FROM 
    (select * FROM user_daily_events  WHERE is_signin_day = 1 and is_install_day = 1) s
LEFT JOIN 
    user_daily_events e ON s.appsflyer_id = e.appsflyer_id AND s.date = e.date
GROUP BY 1, 2, 3, 4, 5, 6, 7;



























注册成功-授信成功（暂不参考）

-- ###########################################################################################
-- ###########################################################################################
-- ###########################################################################################

-- install/reinstall to sign in
drop table if exists ind.kht_conversion_from_install_and_reinstall_to_signin_tmp;
create table ind.kht_conversion_from_install_and_reinstall_to_signin_tmp as
select 
    date_trunc('month',t1.date) as install_mt
    ,date_trunc('week',t1.date) as install_wk
    --,t1.hour as install_hour
    ,t1.date
    -- ,t1.app_version
    -- ,t1.campaign
    -- ,t1.media_source 
    -- ,case when platform='ios' then 'iOS' when platform='android' then 'Android' else null end as  source
    ,count(distinct t1.appsflyer_id) as cnt_total
    ,count(distinct case when  t8.appsflyer_id is not null then t8.appsflyer_id  end) as uninstall_cnt
    ,count(distinct case when  t1.event_name='install' then t1.appsflyer_id end ) as cnt_install
    ,count(distinct case when  t1.event_name='reinstall' then t1.appsflyer_id end ) as cnt_reinstall
    ,count(distinct case when  t5.appsflyer_id is not null then t5.appsflyer_id  end) as cnt_signin_success_new
    ,count(distinct case when  t6.appsflyer_id is not null then t6.appsflyer_id  end) as cnt_signin_success_old
    ,count(distinct case when  t7.appsflyer_id is not null then t7.appsflyer_id  end) as cnt_signin_success_all    
    from 
-- install + reinstall
    (
    select  
    date(substr(event_time_selected_timezone,1,10)) as date
    ,event_name
    ,appsflyer_id
    from ods.s08_appsflyer_push_data
    where event_name in 
        (-- sign-in final
        'install','reinstall'
        )  
    and (event_name in ('install','reinstall') or platform='ios' or event_source='S2S' or json_extract_scalar(event_value,'$.pkg_name') = 'com.sahabatmikro' )-- only pkg=samir
    and etl_date>=to_char(current_date - interval '20' day,'yyyymmdd')
    group by 1,2,3
    ) t1
-- sign in new
    left join
    (
    select  
    date(substr(event_time_selected_timezone,1,10)) as date
    ,appsflyer_id
    from ods.s08_appsflyer_push_data
    where event_name in 
        (-- sign-in final
        'Sign_in_success_new'
        )  
    and etl_date>=to_char(current_date - interval '20' day,'yyyymmdd')
    group by 1,2
    ) t5
    on  t1.appsflyer_id = t5.appsflyer_id and date_diff('day',t1.date,t5.date)=0 
-- sign in old
    left join
    (
    select  
    date(substr(event_time_selected_timezone,1,10)) as date
    ,appsflyer_id
    from ods.s08_appsflyer_push_data
    where event_name in 
        (-- sign-in final
        'Sign_in_success_old'
        )  
    and etl_date>=to_char(current_date - interval '20' day,'yyyymmdd')
    group by 1,2
    ) t6
    on  t1.appsflyer_id = t6.appsflyer_id and date_diff('day',t1.date,t6.date)=0 
-- sign in all
    left join
    (
    select  
    date(substr(event_time_selected_timezone,1,10)) as date
    ,appsflyer_id
    from ods.s08_appsflyer_push_data
    where event_name in 
        (-- sign-in final
        'Sign_in_success_new',
        'Sign_in_success_old'
        )  
    and etl_date>=to_char(current_date - interval '20' day,'yyyymmdd')
    group by 1,2
    ) t7
    on  t1.appsflyer_id = t7.appsflyer_id and date_diff('day',t1.date,t7.date)=0 

-- uninstall
    left join
    (
    select  
    date(event_time) as date
    ,appsflyer_id
    from ods.s08_appsflyer_app_data
    where event_name in 
        (-- sign-in final
        'uninstall'
        )  
    and date(event_time) >= current_date - interval '22' day
    group by 1,2
    ) t8
    on  t1.appsflyer_id = t8.appsflyer_id and date_diff('day',t1.date,t8.date)=0 

group by 1,2,3--,4,5,6,7
order by 3 desc



-- ###############################################################################################################################################################
-- ######### Draft Below ############### Draft Below ######### Draft Below #######################################################################################
-- ######### Draft Below ############### Draft Below ######### Draft Below #######################################################################################
-- ######### Draft Below ############### Draft Below ######### Draft Below #######################################################################################
-- ######### Draft Below ############### Draft Below ######### Draft Below #######################################################################################
-- ###############################################################################################################################################################

