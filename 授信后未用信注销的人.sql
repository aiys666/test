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
            WHEN media_source = 'kreditlist_int' OR (media_source = 'vfine_int' AND partner LIKE '%redi%') OR (media_source IS NULL AND partner = 'kreditlist') THEN 'kreditlist_int'
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
            WHEN media_source IN (
                'medproad_int', 'influencet_int', 'safmobi_int', 'brightligkw_int', 'futuremobxgk_int',
                'cryptosprkw_int', 'sundvika_int', 'lianhualu4df_int', 'mobisummer_int', 'jmmobied_int',
                'madheadga1ml_int', 'datagon_int', 'nzzgmobi_int', 'wedifice7v_int', 'qizhimobi_int',
                'zacharyj_int', 'moreadspdi_int', 'otterseagv3_int', 'coooladsi5n_int', 'wirelesshdk_int',
                'magicmobs_int', 'inforaftssh_int', 'adtiming_int', 'pybzltdio_int', 'fimobil_int',
                'flashuplt0gh_int', 'bhglobals7u_int', 'souththird9_int', 'dashdigitbj_int', 'geostar3d_int',
                'nativenation_int', 'qqiwatx_int', 'oytexpd_int', 'boomob_int', 'acabusoe5i_int',
                'plugcloq6_int', 'muldigi_int', 'goatbizeezh_int', 'lonnimobi_int', 'jjexany_int',
                'searchus5g_int', 'callaads_int', 'signoadsz1_int', 'yydsmobi_int', 'cloudappmxx_int',
                'nzxfguide_int', 'wupenpenpk_int', 'ralumadsxe_int', 'netmobile26_int', 'pearllsns_int',
                'agencyonet_int', 'appnext_int', 'nzkamobi_int', 'polybridges_int', 'gameappzo45i_int',
                'seoultsy_int', 'devmobilejw_int', 'commondex_int', 'digiwhisk_int', 'thanhdat_int',
                'grandemedia_int'
            ) OR LOWER(campaign) LIKE '%tecdo%' OR partner = 'appscuckoobd650' THEN 'Network union'
            WHEN media_source IN (
                'maalook8r_int', 'oauthhook9o_int', 'apppro_int', 'primeadsdr_int', 'adssharpltd_int',
                'birdpenguin_int', 'mikkyyw_int', 'pearllsns_int', 'citronnn9_int', 'motechhubkki_int',
                'flybype4_int', 'ciroocle69_int', 'applenutsnc_int', 'jampp_int', 'thetradedesk_int',
                'beepinkmedia_int', 'blackteatech_int', 'oarreal_int', 'plustep5y_int'
            ) OR LOWER(campaign) LIKE '%rainbow%' THEN 'rainbow'
            WHEN media_source IN ('graffitilt_int', 'flatads_int', 'onetraffijs_int', 'desmob_int', 'goodliveqpf_int') THEN 'flatads_int'
            WHEN campaign LIKE '%CookeAds_CPI%' THEN 'CookeAds_CPI'
            WHEN campaign = 'CookeAds_CPS' OR LOWER(campaign) LIKE '%cookeads%' THEN 'CookeAds_CPS'
            WHEN partner = '19mobicn' THEN '19mobi'
            WHEN campaign = 'Samire_Jan2025youmi' THEN 'youmi'
            WHEN media_source = 'yupaamj_int' THEN 'yup'
            WHEN media_source = 'mintegral_int' THEN 'mintegral_int'
            WHEN LOWER(media_source) LIKE '%grab%' THEN 'Grab'
            WHEN media_source IN ('vipmanageb6_int', 'emilysele_int', 'icerainbow_int') OR LOWER(campaign) LIKE '%runto%' THEN 'RUNTOA'
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
            'install', 'reinstall', 'Sign_in_success_new', 'Sign_in_success_old',
            'Ktp_info_page', 'ktp_info_page_back', 'urgeStay_KTP_1', 'urgeStay_KTP_2', 'urgeStay_KTP_3',
            'birthday_time', 'name_time', 'KTP_time', 'selfie_click', 'Ktp_info_next_click',
            'Personal_info_page', 'Personal_info_page_back', 'urgeStay_personalInfo_1', 'urgeStay_personalInfo_2', 'urgeStay_personalInfo_3',
            'religion_time', 'birthplace_time', 'home_ownership_time', 'region_time', 'address_time',
            'postcode_time', 'location_time', 'marriage_time', 'children_time', 'education_time', 'email_time',
            'Personal_info_next_click', 'Work_info_page', 'Work_info_page_back', 'urgeStay_job_1', 'urgeStay_job_2', 'urgeStay_job_3',
            'work_field_time', 'work_year_time', 'monthly_income_time', 'company_name_time', 'company_phone_time',
            'company_region_time', 'company_address_time', 'Work_info_next_click',
            'Emergency_page', 'Emergency_page_back', 'urgeStay_contact_1', 'urgeStay_contact_2', 'urgeStay_contact_3',
            'contact1_relation_time', 'contact1_name_time', 'contact1_phone_time', 'contact2_relation_time', 'contact2_name_time', 'contact2_phone_time',
            'Emergency_next_click', 'Bank_account_page', 'Bank_account_page_back', 'urgeStay_bankcard_1', 'urgeStay_bankcard_2', 'urgeStay_bankcard_3',
            'bank_name_time', 'holder_name_time', 'bank_account_time', 'Submit_bank_account_click',
            'Liveness_page_firstloan', 'Liveness_success_firstloan', 'liveness_izi', 'liveness_advance',
            'audit_success_firstloan_origin', 'Submit_firstloan_applications_click', 'Firstloan_submit_success', 'Submit_firstloan_apply_click'
        )
),
user_signin AS (
    SELECT 
        customer_user_id,
        MIN(event_date) AS signin_date,
        MIN(CASE WHEN platform = 'ios' THEN 'iOS' WHEN platform = 'android' THEN 'Android' ELSE NULL END) AS source,
        MAX(app_version) AS app_version,
        MAX(campaign) AS campaign,
        MAX(media_source) AS media_source
    FROM user_event_timeline
    WHERE event_name IN ('install', 'reinstall')
    GROUP BY 1
),
user_steps AS (
    SELECT 
        customer_user_id,
        MIN(CASE WHEN event_name IN (
            'Ktp_info_page', 'ktp_info_page_back', 'urgeStay_KTP_1', 'urgeStay_KTP_2', 'urgeStay_KTP_3',
            'birthday_time', 'name_time', 'KTP_time', 'selfie_click'
        ) THEN event_date END) AS ktp_enter_date,
        MIN(CASE WHEN event_name = 'Ktp_info_next_click' THEN event_date END) AS ktp_done_date,
        MIN(CASE WHEN event_name IN (
            'Personal_info_page', 'Personal_info_page_back', 'urgeStay_personalInfo_1', 'urgeStay_personalInfo_2', 'urgeStay_personalInfo_3',
            'religion_time', 'birthplace_time', 'home_ownership_time', 'region_time', 'address_time',
            'postcode_time', 'location_time', 'marriage_time', 'children_time', 'education_time', 'email_time'
        ) THEN event_date END) AS personinfo_enter_date,
        MIN(CASE WHEN event_name = 'Personal_info_next_click' THEN event_date END) AS personinfo_done_date,
        MIN(CASE WHEN event_name IN (
            'Work_info_page', 'Work_info_page_back', 'urgeStay_job_1', 'urgeStay_job_2', 'urgeStay_job_3',
            'work_field_time', 'work_year_time', 'monthly_income_time', 'company_name_time', 'company_phone_time',
            'company_region_time', 'company_address_time'
        ) THEN event_date END) AS workinfo_enter_date,
        MIN(CASE WHEN event_name = 'Work_info_next_click' THEN event_date END) AS workinfo_done_date,
        MIN(CASE WHEN event_name IN (
            'Emergency_page', 'Emergency_page_back', 'urgeStay_contact_1', 'urgeStay_contact_2', 'urgeStay_contact_3',
            'contact1_relation_time', 'contact1_name_time', 'contact1_phone_time', 'contact2_relation_time', 'contact2_name_time', 'contact2_phone_time'
        ) THEN event_date END) AS emergency_enter_date,
        MIN(CASE WHEN event_name = 'Emergency_next_click' THEN event_date END) AS emergency_done_date,
        MIN(CASE WHEN event_name IN (
            'Bank_account_page', 'Bank_account_page_back', 'urgeStay_bankcard_1', 'urgeStay_bankcard_2', 'urgeStay_bankcard_3',
            'bank_name_time', 'holder_name_time', 'bank_account_time'
        ) THEN event_date END) AS bank_enter_date,
        MIN(CASE WHEN event_name = 'Submit_bank_account_click' THEN event_date END) AS bank_done_date,
        MIN(CASE WHEN event_name = 'Liveness_page_firstloan' THEN event_date END) AS liveness_enter_date,
        MIN(CASE WHEN event_name = 'Liveness_success_firstloan' THEN event_date END) AS liveness_done_date,
        MIN(CASE WHEN event_name IN ('liveness_izi', 'liveness_advance')
            AND JSON_EXTRACT_SCALAR(JSON_EXTRACT_SCALAR(event_value, '$.entity'), '$.code') != 'SUCCESS' THEN event_date END) AS liveness_fail_date,
        MIN(CASE WHEN event_name = 'audit_success_firstloan_origin' THEN event_date END) AS audit_success_date,
        MIN(CASE WHEN event_name IN ('Submit_firstloan_applications_click', 'Firstloan_submit_success', 'Submit_firstloan_apply_click') THEN event_date END) AS af_confirm_date
    FROM user_event_timeline
    GROUP BY 1
),
user_steps_issue AS (
    SELECT 
        mid,
        MIN(DATE(app_date)) AS app_date,
        MIN(DATE(confirm_time)) AS confirm_date,
        MIN(DATE(issue_date)) AS issue_date
    FROM ind.ba_asset_base_info
    WHERE create_time >= CURRENT_DATE - INTERVAL '60' DAY
        AND if_app = 1
        AND grant_strategy = 'NEW'
    GROUP BY 1
)
SELECT 
    s.customer_user_id,
    s.signin_date,
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
    sti.issue_date,
    DATE_DIFF('day', s.signin_date, st.ktp_enter_date) AS days_to_ktp_enter,
    DATE_DIFF('day', s.signin_date, st.ktp_done_date) AS days_to_ktp_done,
    DATE_DIFF('day', s.signin_date, st.personinfo_done_date) AS days_to_personinfo_done,
    DATE_DIFF('day', s.signin_date, st.workinfo_done_date) AS days_to_workinfo_done,
    DATE_DIFF('day', s.signin_date, st.emergency_done_date) AS days_to_emergency_done,
    DATE_DIFF('day', s.signin_date, st.bank_done_date) AS days_to_bank_done,
    DATE_DIFF('day', s.signin_date, st.liveness_done_date) AS days_to_liveness_done,
    DATE_DIFF('day', s.signin_date, st.audit_success_date) AS days_to_audit_success,
    DATE_DIFF('day', s.signin_date, st.af_confirm_date) AS days_to_af_confirm,
    DATE_DIFF('day', s.signin_date, sti.app_date) AS days_to_app,
    DATE_DIFF('day', s.signin_date, sti.confirm_date) AS days_to_confirm,
    DATE_DIFF('day', s.signin_date, sti.issue_date) AS days_to_issue
FROM user_signin s
LEFT JOIN user_steps st ON s.customer_user_id = st.customer_user_id
LEFT JOIN user_steps_issue sti ON TRY_CAST(s.customer_user_id AS BIGINT) = TRY_CAST(sti.mid AS BIGINT);