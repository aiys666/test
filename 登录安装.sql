
DROP TABLE IF EXISTS ind.ys_user_install_steps_tmp;
CREATE TABLE ind.ys_user_install_steps_tmp AS
WITH user_event_timeline AS (
    SELECT 
        
        appsflyer_id,
        DATE(SUBSTR(event_time_selected_timezone, 1, 10)) AS event_date,
        event_name,
        event_value,
        campaign,
        app_version,
        platform,
        CASE 
            WHEN platform = 'ios' AND media_source = 'Apple Search Ads' THEN 'ASA'
            WHEN platform = 'ios' AND media_source = 'restricted' THEN 'IOS-fb'
            WHEN platform = 'ios' AND media_source = 'tiktokglobal_int' THEN 'IOS-tt'
            WHEN platform = 'ios' AND media_source = 'googleadwords_int' THEN 'IOS-gg'
            WHEN platform = 'ios' AND media_source = 'vfine_int' THEN 'IOS-vfine'
            WHEN platform = 'ios' AND media_source = 'Rupiah Cepat' THEN 'IOS-RC'
            WHEN platform = 'ios' AND media_source = 'yupaamj_int' THEN 'IOS-yup'
            WHEN platform = 'ios' AND media_source = 'tangads' THEN 'IOS-tangads'
            WHEN platform = 'ios' THEN 'IOS-Organic'
            WHEN media_source = 'googleadwords_int' THEN 'Google'
            WHEN media_source = 'Facebook Ads' OR media_source = 'restricted' THEN 'Facebook'
            WHEN media_source = 'organic' THEN 'Organic'
            WHEN media_source = 'shareit_int' THEN 'Shareit'
            WHEN media_source = 'kreditlist_int' OR (media_source = 'vfine_int' AND partner LIKE '%redi%') 
                 OR (media_source IS NULL AND partner = 'kreditlist') THEN 'kreditlist_int'
            WHEN media_source = 'vfine_int' OR media_source = 'adecentptuo_int' THEN 'Vfine'
            WHEN media_source IN ('bytedanceglobal_int', 'tiktokglobal_int') THEN 'Tiktok'
            WHEN media_source = 'kwaiforbusiness_int' THEN 'Kwai'
            WHEN media_source = 'cashcashpro' THEN 'cashcashpro'
            WHEN media_source = 'cashcerdasid_int' THEN 'cashcerdas'
            WHEN media_source = 'kredit pintal' THEN 'kp'
            WHEN media_source IN ('atomcmkhg_int', 'atomfinhhl_int') THEN 'atomcm'
            WHEN REGEXP_LIKE(campaign, '^pp') THEN 'Novabeyond'
            WHEN media_source = 'pyxis_int' THEN 'pyxis'
            WHEN media_source = 'Rupiah Cepat' THEN 'Rupiah Cepat'
            WHEN media_source = 'Twitter' THEN 'twitter'
            WHEN media_source IN ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
                            ,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
                            ,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
                            ,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
                            ,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
                            ,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
                            ,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
                            ,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
                            ,'digiwhisk_int','thanhdat_int','grandemedia_int') OR LOWER(campaign) LIKE '%tecdo%' OR partner ='appscuckoobd650' THEN 'Network union'
            WHEN media_source IN ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
                            ,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') OR LOWER(campaign) LIKE '%rainbow%' THEN 'rainbow'
            WHEN media_source IN ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') THEN 'flatads_int'
            WHEN campaign LIKE '%CookeAds_CPI%' THEN 'CookeAds_CPI'
            WHEN campaign = 'CookeAds_CPS' OR LOWER(campaign) LIKE '%cookeads%' THEN 'CookeAds_CPS'
            WHEN partner = '19mobicn' THEN '19mobi'
            WHEN campaign = 'Samire_Jan2025youmi' THEN 'youmi'
            WHEN media_source = 'yupaamj_int' THEN 'yup'
            WHEN media_source = 'mintegral_int' THEN 'mintegral_int'
            WHEN LOWER(media_source) LIKE '%grab%' THEN 'Grab'
            WHEN media_source IN ('vipmanageb6_int','emilysele_int','icerainbow_int') OR LOWER(campaign) LIKE '%runto%' THEN 'RUNTOA'
            WHEN LOWER(campaign) LIKE '%mejoy%' THEN 'mejoy'
            WHEN LOWER(campaign) LIKE '%yolo%' THEN 'yolo'
            WHEN media_source = 'LinkAja_ads' THEN 'LinkAja_ads'
            WHEN media_source = 'easycash01' THEN 'easycash01'
            WHEN media_source = 'xiaomiglobal_int' THEN 'xiaomiglobal_int'
            WHEN media_source = 'tangads' THEN 'tangads'
            WHEN media_source = 'Pinjamyuk_ads' THEN 'Pinjamyuk_ads'
            WHEN media_source = 'oppoglobal_int' THEN 'oppoglobal_int'
            WHEN media_source LIKE '%_int%' THEN 'other'
            ELSE 'Organic'
        END AS media_source
    FROM ind.kht_conversion_from_download_tmp
    WHERE etl_date >= TO_CHAR(CURRENT_DATE - INTERVAL '60' DAY, 'yyyymmdd')
        AND event_name IN (
            'install','reinstall', 
            'app_start_banner_page',
            'unlogin_Home_page',
            'Sign_in_page',
            'Sign_in_input_phone',
            'Sign_in_input_phone_out',
            'Sign_in_code_sent_click_new',
            'Sign_in_vcode_sent_click_new',
            'Sign_in_click_confirm',
            'Sign_in_click_new',
            'Sign_in_vcode_click_new',
            'Sign_in_success_new','Sign_in_success_old'

        )
),
user_signin AS ( 
    SELECT 
        appsflyer_id,
        MIN(event_date) AS install_date,
        MIN(CASE WHEN platform = 'ios' THEN 'iOS' WHEN platform = 'android' THEN 'Android' ELSE NULL END) AS source,
        MAX(app_version) AS app_version,
        MAX(campaign) AS campaign,
        MAX(media_source) AS media_source
    FROM user_event_timeline
    WHERE event_name in('install','reinstall')  
    GROUP BY 1
),
user_steps AS ( 
    SELECT 
        appsflyer_id, 
        MIN(CASE WHEN event_name IN ('app_start_banner_page', 'unlogin_Home_page') 
                THEN event_date END) AS app_launch_date,
        MIN(CASE WHEN event_name = 'Sign_in_page' 
                THEN event_date END) AS signin_page_date,
        MIN(CASE WHEN event_name IN ('Sign_in_input_phone', 'Sign_in_input_phone_out') 
                THEN event_date END) AS phone_input_date,
        MIN(CASE WHEN event_name IN ('Sign_in_code_sent_click_new', 'Sign_in_vcode_sent_click_new', 'Sign_in_click_confirm') 
                THEN event_date END) AS verify_code_sent_date,
        MIN(CASE WHEN event_name IN ('Sign_in_click_new', 'Sign_in_vcode_click_new') 
                THEN event_date END) AS verify_code_input_date,
        MIN(CASE WHEN event_name IN ('Sign_in_success_new','Sign_in_success_old') 
                THEN event_date END) AS signin_success_date
    FROM user_event_timeline
    GROUP BY 1
) 

SELECT 
    s.appsflyer_id,
    s.install_date,
    s.source,
    s.app_version,
    s.campaign,
    s.media_source,
    st.app_launch_date,
    st.signin_page_date,
    st.phone_input_date,
    st.verify_code_sent_date,
    st.verify_code_input_date,
    st.signin_success_date, 
    DATE_DIFF('day',s.install_date, st.app_launch_date) AS days_to_app_launch,
    DATE_DIFF('day',s.install_date, st.signin_page_date) AS days_to_signin_page,
    DATE_DIFF('day',s.install_date, st.phone_input_date) AS days_to_phone_input,
    DATE_DIFF('day',s.install_date, st.verify_code_sent_date) AS days_to_verify_code_sent,
    DATE_DIFF('day',s.install_date, st.verify_code_input_date) AS days_to_verify_code_input,
    DATE_DIFF('day',s.install_date, st.signin_success_date) AS days_to_signin_success 
    
FROM user_signin s
LEFT JOIN user_steps st ON s.appsflyer_id = st.appsflyer_id;
  













 
DROP TABLE IF EXISTS ind.ys_install_conversion_funnel_ttype;
CREATE TABLE ind.ys_install_conversion_funnel_ttype AS
WITH user_flags AS (
    SELECT 
        appsflyer_id,
        install_date,
        source,
        app_version,
        campaign,
        media_source,
        days_to_app_launch,
        days_to_signin_page,
        days_to_phone_input,
        days_to_verify_code_sent,
        days_to_verify_code_input,
        days_to_signin_success
 
    FROM ind.ys_user_install_steps_tmp
),
time_windows AS ( 
    SELECT 0 AS t_type, 'T0' AS time_period
    UNION ALL
    SELECT 7 AS t_type, 'T7' AS time_period
    UNION ALL
    SELECT 30 AS t_type, 'T30' AS time_period
),

ys_conversion_funnel_ttype as(
SELECT  
    DATE_TRUNC('month', u.install_date) AS install_month,
    DATE_TRUNC('week', u.install_date) AS install_week,
    u.install_date,
    u.app_version,
    u.campaign,
    u.media_source,
    u.appsflyer_id,
    u.source,
    t.t_type,
    t.time_period, 
    CASE WHEN u.days_to_app_launch BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_app_launch,
    CASE WHEN u.days_to_signin_page BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_signin_page,
    CASE WHEN u.days_to_phone_input BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_phone_input,
    CASE WHEN u.days_to_verify_code_sent BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_verify_code_sent,
    CASE WHEN u.days_to_verify_code_input BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_verify_code_input,
    CASE WHEN u.days_to_signin_success BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_signin_success,  

  
    u.days_to_app_launch,
    u.days_to_signin_page,
    u.days_to_phone_input,
    u.days_to_verify_code_sent,
    u.days_to_verify_code_input,
    u.days_to_signin_success

FROM user_flags u
CROSS JOIN time_windows t)


SELECT  
    install_month,
    install_week,
    install_date,
    app_version,
    campaign,
    media_source,
    source,
    t_type,
    time_period,
     
    COUNT(DISTINCT appsflyer_id) AS install_users,  
    COUNT(DISTINCT CASE WHEN has_app_launch = 1 THEN appsflyer_id END) AS app_launch_count,
    COUNT(DISTINCT CASE WHEN has_signin_page = 1 THEN appsflyer_id END) AS signin_page_count,
    COUNT(DISTINCT CASE WHEN has_phone_input = 1 THEN appsflyer_id END) AS phone_input_count,
    COUNT(DISTINCT CASE WHEN has_verify_code_sent = 1 THEN appsflyer_id END) AS verify_code_sent_count,
    COUNT(DISTINCT CASE WHEN has_verify_code_input = 1 THEN appsflyer_id END) AS verify_code_input_count,
    COUNT(DISTINCT CASE WHEN has_signin_success = 1 THEN appsflyer_id END) AS signin_success_count
      


FROM ys_conversion_funnel_ttype
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9;