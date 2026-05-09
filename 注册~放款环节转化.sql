-- 我们有以下步骤节点（按照顺序）：

-- 注册（登录成功） -> 2. 进入KTP信息页面（has_ktp） -> 3. 完成KTP信息（has_ktp_done） -> 4. 进入个人信息页面（has_personinfo） -> 5. 完成个人信息（has_personinfo_done）
-- -> 6. 进入工作信息页面（has_workinfo） -> 7. 完成工作信息（has_workinfo_done） -> 8. 进入紧急联系人页面（has_emergency） -> 9. 完成紧急联系人（has_emergency_done）
-- -> 10. 进入银行账户页面（has_bank） -> 11. 完成银行账户（has_bank_done） -> 12. 进入活体检测页面（has_liveness） -> 13. 完成活体检测（has_liveness_done）
-- -> 14. 授信成功（has_auditsuccess），
 




DROP TABLE IF EXISTS ind.ys_user_journey_steps_tmp;
CREATE TABLE ind.ys_user_journey_steps_tmp AS
WITH user_event_timeline AS (
    SELECT 
        
        customer_user_id,
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
            'Sign_in_success_new','Sign_in_success_old',
            'Ktp_info_page', 'ktp_info_page_back', 'urgeStay_KTP_1', 'urgeStay_KTP_2', 'urgeStay_KTP_3', 'birthday_time', 'name_time', 'KTP_time', 'selfie_click',
            'Ktp_info_next_click',
            'Personal_info_page', 'Personal_info_page_back', 'urgeStay_personalInfo_1', 'urgeStay_personalInfo_2', 'urgeStay_personalInfo_3', 'religion_time', 'birthplace_time', 'home_ownership_time', 'region_time', 'address_time', 'postcode_time', 'location_time', 'marriage_time', 'children_time', 'education_time', 'email_time',
            'Personal_info_next_click',
            'Work_info_page', 'Work_info_page_back', 'urgeStay_job_1', 'urgeStay_job_2', 'urgeStay_job_3', 'work_field_time', 'work_year_time', 'monthly_income_time', 'company_name_time', 'company_phone_time', 'company_region_time', 'company_address_time',
            'Work_info_next_click',
            'Emergency_page', 'Emergency_page_back', 'urgeStay_contact_1', 'urgeStay_contact_2', 'urgeStay_contact_3', 'contact1_relation_time', 'contact1_name_time', 'contact1_phone_time', 'contact2_relation_time', 'contact2_name_time', 'contact2_phone_time',
            'Emergency_next_click',
            'Bank_account_page', 'Bank_account_page_back', 'urgeStay_bankcard_1', 'urgeStay_bankcard_2', 'urgeStay_bankcard_3', 'bank_name_time', 'holder_name_time', 'bank_account_time',
            'Submit_bank_account_click',
            'Liveness_page_firstloan',
            'Liveness_success_firstloan',
            'liveness_izi', 'liveness_advance',
            'audit_success_firstloan_origin' ,
            'Submit_firstloan_applications_click' ,
            'Firstloan_submit_success',
            'Submit_firstloan_apply_click'
        )
),
user_reg AS ( 
    SELECT 
        customer_user_id,
        MIN(event_date) AS reg_date,
        MIN(CASE WHEN platform = 'ios' THEN 'iOS' WHEN platform = 'android' THEN 'Android' ELSE NULL END) AS source,
        MAX(app_version) AS app_version,
        MAX(campaign) AS campaign,
        MAX(media_source) AS media_source
    FROM user_event_timeline
    WHERE event_name in('Sign_in_success_new','Sign_in_success_old')  
    GROUP BY 1
),

user_steps AS ( 
    SELECT 
        customer_user_id,
        MIN(CASE WHEN event_name IN ('Ktp_info_page', 'ktp_info_page_back', 'urgeStay_KTP_1', 'urgeStay_KTP_2', 'urgeStay_KTP_3', 'birthday_time', 'name_time', 'KTP_time', 'selfie_click') 
                THEN event_date END) AS ktp_enter_date,
        MIN(CASE WHEN event_name = 'Ktp_info_next_click' THEN event_date END) AS ktp_done_date,
        MIN(CASE WHEN event_name IN ('Personal_info_page', 'Personal_info_page_back', 'urgeStay_personalInfo_1', 'urgeStay_personalInfo_2', 'urgeStay_personalInfo_3', 'religion_time', 'birthplace_time', 'home_ownership_time', 'region_time', 'address_time', 'postcode_time', 'location_time', 'marriage_time', 'children_time', 'education_time', 'email_time')
                THEN event_date END) AS personinfo_enter_date,
        MIN(CASE WHEN event_name = 'Personal_info_next_click' THEN event_date END) AS personinfo_done_date,
        MIN(CASE WHEN event_name IN ('Work_info_page', 'Work_info_page_back', 'urgeStay_job_1', 'urgeStay_job_2', 'urgeStay_job_3', 'work_field_time', 'work_year_time', 'monthly_income_time', 'company_name_time', 'company_phone_time', 'company_region_time', 'company_address_time')
                THEN event_date END) AS workinfo_enter_date,
        MIN(CASE WHEN event_name = 'Work_info_next_click' THEN event_date END) AS workinfo_done_date,
        MIN(CASE WHEN event_name IN ('Emergency_page', 'Emergency_page_back', 'urgeStay_contact_1', 'urgeStay_contact_2', 'urgeStay_contact_3', 'contact1_relation_time', 'contact1_name_time', 'contact1_phone_time', 'contact2_relation_time', 'contact2_name_time', 'contact2_phone_time')
                THEN event_date END) AS emergency_enter_date,
        MIN(CASE WHEN event_name = 'Emergency_next_click' THEN event_date END) AS emergency_done_date,
        MIN(CASE WHEN event_name IN ('Bank_account_page', 'Bank_account_page_back', 'urgeStay_bankcard_1', 'urgeStay_bankcard_2', 'urgeStay_bankcard_3', 'bank_name_time', 'holder_name_time', 'bank_account_time')
                THEN event_date END) AS bank_enter_date,
        MIN(CASE WHEN event_name = 'Submit_bank_account_click' THEN event_date END) AS bank_done_date,
        MIN(CASE WHEN event_name = 'Liveness_page_firstloan' THEN event_date END) AS liveness_enter_date,
        MIN(CASE WHEN event_name = 'Liveness_success_firstloan' THEN event_date END) AS liveness_done_date,
        MIN(CASE WHEN event_name IN ('liveness_izi', 'liveness_advance') 
                AND JSON_EXTRACT_SCALAR(JSON_EXTRACT_SCALAR(event_value, '$.entity'), '$.code') != 'SUCCESS' 
                THEN event_date END) AS liveness_fail_date,
        MIN(CASE WHEN event_name = 'audit_success_firstloan_origin' THEN event_date END) AS audit_success_date,
        MIN(CASE WHEN event_name IN ('Submit_firstloan_applications_click','Firstloan_submit_success','Submit_firstloan_apply_click') THEN event_date END) AS af_confirm_date
    FROM user_event_timeline
    GROUP BY 1
),


user_steps_issue_base AS(
select mid,biz_id,app_date,confirm_time,issue_date,if_recall,create_time 
from ind.ba_asset_base_info 
where create_time>=CURRENT_DATE - INTERVAL '60' DAY 
and if_app=1
AND grant_strategy = 'NEW' 
), 

user_steps_issue AS(
select mid,
min(date(app_date)) as app_date, 
min(date(confirm_time)) as confirm_date,
min(date(issue_date)) as issue_date
from user_steps_issue_base
group by 1
), 


signature_data AS (   
        SELECT customer_id, 
               min(sign_date) as sign_date
         FROM (
            SELECT DISTINCT customer_id,biz_id, DATE(create_time) sign_date
            FROM ods.s25_contract_record c
            WHERE c.oper_type = 4 AND c.deleted = 0
            AND DATE(create_time) < CURRENT_DATE
            AND create_time>=CURRENT_DATE - INTERVAL '60' DAY
            UNION ALL
            SELECT DISTINCT customer_id,CAST(aa.camera_id AS DECIMAL(38, 6)) AS biz_id,
                   DATE(create_time) sign_date
            FROM ods_view_presto.s02_digisign_record aa
            WHERE aa.status = 1 AND aa.type = 7 AND role_type = 1
            AND DATE(create_time) < CURRENT_DATE
            AND create_time>=CURRENT_DATE - INTERVAL '60' DAY
        ) a 
        join user_steps_issue_base  b   ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(b.biz_id AS BIGINT)                                             

        group by 1
  ) ,


user_recall AS (
    SELECT 
        mid,
        MIN(case when if_recall=1 then create_time else null end) AS if_recall_time
    FROM user_steps_issue_base a 
    GROUP BY 1 
),

external_data_4_pass AS (
SELECT 
    t.mid,
    MIN(COALESCE(t.update_time, t.if_recall_time)) AS external_data_4_pass_time 
FROM (
    SELECT 
        a.mid,
        CASE 
            WHEN LOWER(o.current_processor) IN (
                'first_loan_external_data4_set',
                'reloan_external_data4_set',
                'plus_external_data4_set',
                'plus_external_data4_set_circ',
                'm_plus_exteranl_data4_set',
                'first_loan_external_data4_set_ios',
                'reloan_external_data4_set_ios',
                'plus_external_data4_set_ios',
                'm_external_data4_set',
                'manual second'
            )   
            AND o.approve_result = 'PASSED' 
            THEN o.update_time 
            ELSE NULL 
        END AS update_time,
        a.if_recall_time                                   
    FROM ods.s05_creditx_processor_record o          
    LEFT JOIN user_recall a 
        ON TRY_CAST(a.mid AS BIGINT) = TRY_CAST(o.mid AS BIGINT)                                         
    WHERE o.update_time >= CURRENT_DATE - INTERVAL '60' DAY 
        AND o.update_time < CURRENT_DATE      
) t
GROUP BY 1 
),

user_base AS (
    SELECT
        COALESCE(m3.phone, m2.mb_phone) AS mb_phone,
        m2.mid,
        date(m2.reg_time) as reg_time,
        date(m3.del_time) as del_time,
        ROW_NUMBER() OVER (PARTITION BY COALESCE(m3.phone, m2.mb_phone) ORDER BY m2.reg_time DESC) AS register_sequence
    FROM ods.s01_mem_member_account m2
    LEFT JOIN
        ods.s05_yn_login_out_record m3 
        ON TRY_CAST(m2.mid AS BIGINT) = TRY_CAST(m3.mid AS BIGINT) 

        AND m3.status = 1 
),
 
user_reg_with_history AS (
    SELECT 
        s.customer_user_id,
        s.reg_date,
        s.source,
        s.app_version,
        s.campaign,
        s.media_source, 
        b.mb_phone, 
        CASE 
            WHEN EXISTS (
                SELECT 1 
                FROM user_base b2 
                WHERE b2.mb_phone = b.mb_phone 
                AND b2.del_time IS NOT NULL
                 AND TRY_CAST(b2.mid AS BIGINT) != TRY_CAST(s.customer_user_id AS BIGINT)

            ) THEN 1
            ELSE 0 
        END AS has_logout_history,
         (SELECT MAX(del_time) 
         FROM user_base b3 
         WHERE b3.mb_phone = b.mb_phone 
         AND b3.del_time IS NOT NULL
         AND TRY_CAST(b3.mid AS BIGINT) != TRY_CAST(s.customer_user_id AS BIGINT)
         ) AS last_logout_date,
         b.reg_time,
         CASE WHEN b.del_time IS NOT NULL THEN 1 ELSE 0 END AS is_currently_logged_out
    FROM user_reg s
    LEFT JOIN user_base b ON  TRY_CAST(s.customer_user_id AS BIGINT) = TRY_CAST(b.mid AS BIGINT)
     WHERE b.register_sequence = 1 OR b.register_sequence IS NULL
)

SELECT 
    s.customer_user_id,
    h.has_logout_history,
    h.last_logout_date, 
    s.reg_date,
    s.source,
    s.app_version,
    s.campaign,
    s.media_source,
    st.ktp_enter_date,
    st.ktp_done_date,
    st.personinfo_enter_date,
    st.personinfo_done_date,
    st.workinfo_enter_date,
    st.workinfo_done_date,
    st.emergency_enter_date,
    st.emergency_done_date,
    st.bank_enter_date,
    st.bank_done_date,
    st.liveness_enter_date,
    st.liveness_done_date,
    st.liveness_fail_date,
    st.audit_success_date,
    st.af_confirm_date,
    sti.app_date,
    sti.confirm_date, 
    ex.external_data_4_pass_time,
    sgn.sign_date, 
    sti.issue_date,
  
    DATE_DIFF('day',s.reg_date, st.ktp_enter_date) AS days_to_ktp_enter,
    DATE_DIFF('day',s.reg_date, st.ktp_done_date) AS days_to_ktp_done,
    DATE_DIFF('day',s.reg_date, st.personinfo_done_date) AS days_to_personinfo_done,
    DATE_DIFF('day',s.reg_date, st.workinfo_done_date) AS days_to_workinfo_done,
    DATE_DIFF('day',s.reg_date, st.emergency_done_date) AS days_to_emergency_done,
    DATE_DIFF('day',s.reg_date, st.bank_done_date) AS days_to_bank_done,
    DATE_DIFF('day',s.reg_date, st.liveness_done_date) AS days_to_liveness_done,
    DATE_DIFF('day',s.reg_date, st.audit_success_date) AS days_to_audit_success,
    DATE_DIFF('day',s.reg_date, st.af_confirm_date) AS days_to_af_confirm,
    DATE_DIFF('day',s.reg_date, sti.app_date) AS days_to_app,
    DATE_DIFF('day',s.reg_date, sti.confirm_date) AS days_to_confirm,
    DATE_DIFF('day',s.reg_date, ex.external_data_4_pass_time) AS days_to_external_data_4_pass,
    DATE_DIFF('day',s.reg_date, sgn.sign_date) AS days_to_sign,
    DATE_DIFF('day',s.reg_date, sti.issue_date) AS days_to_issue
    
FROM user_reg s
LEFT JOIN signature_data sgn ON TRY_CAST(s.customer_user_id AS BIGINT) = TRY_CAST(sgn.customer_id AS BIGINT)
LEFT JOIN user_reg_with_history h ON TRY_CAST(s.customer_user_id AS BIGINT) = TRY_CAST(h.customer_user_id AS BIGINT)
LEFT JOIN user_steps st ON s.customer_user_id = st.customer_user_id
LEFT JOIN user_steps_issue sti ON TRY_CAST(s.customer_user_id AS BIGINT) = TRY_CAST(sti.mid AS BIGINT)
LEFT JOIN external_data_4_pass ex ON TRY_CAST(s.customer_user_id AS BIGINT) = TRY_CAST(ex.mid AS BIGINT);
 













 
DROP TABLE IF EXISTS ind.ys_conversion_funnel_ttype;
CREATE TABLE ind.ys_conversion_funnel_ttype AS
WITH user_flags AS (
    SELECT 
        customer_user_id,
        has_logout_history,
        last_logout_date,

        reg_date,
        source,
        app_version,
        campaign,
        media_source,
        days_to_ktp_done,
        days_to_personinfo_done,
        days_to_workinfo_done,
        days_to_emergency_done,
        days_to_bank_done,
        days_to_liveness_done,
        days_to_audit_success,
        days_to_af_confirm,
        days_to_app,
        days_to_confirm,
        days_to_external_data_4_pass,
        days_to_sign,
        days_to_issue
    FROM ind.ys_user_journey_steps_tmp
),
time_windows AS ( 
    SELECT 0 AS t_type, 'T0' AS time_period
    UNION ALL
    SELECT 7 AS t_type, 'T7' AS time_period
    UNION ALL
    SELECT 30 AS t_type, 'T30' AS time_period
)
SELECT  
    DATE_TRUNC('month', u.reg_date) AS reg_month,
    DATE_TRUNC('week', u.reg_date) AS reg_week,
    u.reg_date,
    u.app_version,
    u.campaign,
    u.media_source,
    u.customer_user_id,
    u.has_logout_history,
    u.last_logout_date,

    u.source,
    t.t_type,
    t.time_period, 
    CASE WHEN u.days_to_ktp_done BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_ktp_done,
    CASE WHEN u.days_to_personinfo_done BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_personinfo_done,
    CASE WHEN u.days_to_workinfo_done BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_workinfo_done,
    CASE WHEN u.days_to_emergency_done BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_emergency_done,
    CASE WHEN u.days_to_bank_done BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_bank_done,
    CASE WHEN u.days_to_liveness_done BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_liveness_done,
    CASE WHEN u.days_to_audit_success BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_audit_success,
    CASE WHEN u.days_to_af_confirm BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_af_confirm,
    CASE WHEN u.days_to_app BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_app,
    CASE WHEN u.days_to_confirm BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_confirm,
    CASE WHEN u.days_to_external_data_4_pass BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_external_data_4_pass,
    CASE WHEN u.days_to_sign BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_sign,

    CASE WHEN u.days_to_issue BETWEEN 0 AND t.t_type THEN 1 ELSE 0 END AS has_issue,
    u.days_to_ktp_done,
    u.days_to_personinfo_done,
    u.days_to_workinfo_done,
    u.days_to_emergency_done,
    u.days_to_bank_done,
    u.days_to_liveness_done,
    u.days_to_audit_success,
    u.days_to_af_confirm,
    u.days_to_app,
    u.days_to_confirm,
    u.days_to_external_data_4_pass,
    u.days_to_sign,
    u.days_to_issue

FROM user_flags u
CROSS JOIN time_windows t;


 








DROP TABLE IF EXISTS ind.ys_conversion_funnel_agg;
CREATE TABLE ind.ys_conversion_funnel_agg AS
SELECT  
    reg_month,
    reg_week,
    reg_date,
    app_version,
    campaign,
    media_source,
    source,
    t_type,
    time_period,
    has_logout_history,
     
    COUNT(DISTINCT customer_user_id) AS reg_users,
    -- COUNT(DISTINCT CASE WHEN has_logout_history = 1 THEN customer_user_id END) AS logout_users,
     
    COUNT(DISTINCT CASE WHEN has_ktp_done = 1 THEN customer_user_id END) AS ktp_done_count,
    COUNT(DISTINCT CASE WHEN has_personinfo_done = 1 THEN customer_user_id END) AS personinfo_done_count,
    COUNT(DISTINCT CASE WHEN has_workinfo_done = 1 THEN customer_user_id END) AS workinfo_done_count,
    COUNT(DISTINCT CASE WHEN has_emergency_done = 1 THEN customer_user_id END) AS emergency_done_count,
    COUNT(DISTINCT CASE WHEN has_bank_done = 1 THEN customer_user_id END) AS bank_done_count,
    COUNT(DISTINCT CASE WHEN has_liveness_done = 1 THEN customer_user_id END) AS liveness_done_count,
    COUNT(DISTINCT CASE WHEN has_audit_success = 1 THEN customer_user_id END) AS audit_success_count,
    COUNT(DISTINCT CASE WHEN has_af_confirm = 1 THEN customer_user_id END) AS af_confirm_count, 
    COUNT(DISTINCT CASE WHEN has_confirm = 1 THEN customer_user_id END) AS confirm_count,
    COUNT(DISTINCT CASE WHEN has_external_data_4_pass = 1 THEN customer_user_id END) AS external_data_4_pass_count,
    COUNT(DISTINCT CASE WHEN has_sign = 1 THEN customer_user_id END) AS sign_count,

    COUNT(DISTINCT CASE WHEN has_issue = 1 THEN customer_user_id END) AS issue_count


FROM ind.ys_conversion_funnel_ttype
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9,10;