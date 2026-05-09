
drop table if exists ind.ba_source_basic_d;
create table if not exists ind.ba_source_basic_d as

with spend AS (
    select 
        date(ad_date) as ad_date
        ,case when media_source='ASA' then 'IOS_ASA'
                when lower(campaign_name) like  '%ios%'  or lower(media_source) like '%ios%' then 'IOS_OTHER'
                when media_source like '%oogle%' and lower(campaign_name) not like '%ios%' then 'Google'
                when media_source like '%acebook%' and lower(campaign_name) not like '%ios%' then 'Facebook'
                when media_source='organic' then 'Organic'  
                when media_source='Tiktok' then 'Tiktok'
                when media_source='Kwai' then 'Kwai'
                else 'other'
            end as media_source
        ,sum(spend_usd_discount) as spend
        from ind.tyn_ads_cost_discount a
        where ad_date >= date'2025-01-01'
        group by 1,2  
    union all
    select
        distinct
        ad_date,
        'Organic' as media_source,
        0 as spend
        from ind.tyn_ads_cost_discount  
        where ad_date >= date'2025-01-01'
    ),

install_cnt as (
    SELECT install_date,   
     case 
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai') then media_source 
    when media_source='ASA' then 'IOS_ASA'
    when lower(media_source) like '%ios%' then 'IOS_OTHER' 
    else 'other'
    end as media_source,  
    sum(install_cnt) as install_cnt 
    FROM (
    SELECT 
    DATE(event_time + INTERVAL '7' HOUR) AS install_date,
    case 	   		
		when platform = 'ios' and  media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  media_source in ('restricted','Facebook Ads') then 'IOS-fb'
			when platform = 'ios' and  media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  media_source = 'tangads' then 'IOS-tangads'
			when platform = 'ios' and  media_source = 'Pinjamyuk_ads' then 'IOS-Pinjamyuk'
		  --when platform = 'ios' and  media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when media_source='googleadwords_int' then 'Google'
             when media_source='Facebook Ads' or media_source='restricted' then 'Facebook'
             when media_source='organic' then 'Organic'
             when media_source = 'shareit_int' then 'Shareit'
             when media_source = 'kreditlist_int' or (media_source = 'vfine_int' and partner like '%redi%'  ) 
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
			when media_source in ('easycash01','easycashid_int') then 'easycash01'
			when media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when media_source ='tangads' then 'tangads'
			when media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when media_source ='oppoglobal_int' then 'oppoglobal_int'
			when media_source like '%_int%' then 'other'
			 else 'Organic'
        end as media_source,
    COUNT(DISTINCT appsflyer_id) AS install_cnt
    FROM ods.s08_appsflyer_push_data
    WHERE  etl_date>='20250101' and event_name='install' 
    and date(event_time + INTERVAL '7' HOUR) >= date'2025-01-01'
    GROUP BY 1,2 
    )t
    GROUP BY 1,2 
     ),

 mid_app_date as (
 select mid,date(min(app_time)) as app_date
 from
ind.ba_asset_base_info
where if_app = 1 AND grant_strategy = 'NEW' and is_reloan2='NEW_PURE'
group by 1 
),

reg_cnt as (
    select 
    reg_dt,
    case 
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai') then media_source 
    when media_source='ASA' then 'IOS_ASA'
    when lower(media_source) like '%ios%' then 'IOS_OTHER' 
    else 'other'
    end as media_source, 
    count(distinct t.mid) reg_cnt,
    count(distinct case when install_dt=reg_dt then t.mid else null end) t0_reg_cnt,
    count(distinct case when app_date=reg_dt then t.mid else null end) t0_app_cnt
    
    from ind.tyn_reg_install_new t
    left join mid_app_date on mid_app_date.mid=t.mid

    where reg_dt >= date'2025-01-01'
    group by 1,2 
     ),
apply_cnt AS ( 
    SELECT
        date(app_date) as app_date,  
        media_source2, 
        sum(if_app) AS if_app,
        sum(if_in_confirm_temp) AS in_confirm_cnt,
        sum(if_in_confirm) AS if_in_confirm, 
        sum(case when new_grade_level in ('1','2','3') then if_in_confirm else 0 end) AS if_in_confirm_1_3, 
        sum(case when new_grade_level in ('1','2') then if_in_confirm else 0 end) AS if_in_confirm_1_2,
        sum(apply_grantcredit_amount) AS apply_grantcredit_amount,
        sum(if_confirm_passed_final) AS confirm_passed_cnt, 
        sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
        SUM(case when if_confirm_passed_final= 1 then apply_grantcredit_amount else NULL end) AS confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_amount else NULL end) AS confirm_apply_amount,
        sum(if_external_data_4_passed ) as if_external_data_4_passed


    FROM ind.ba_asset_base_info 
    WHERE grant_strategy='NEW' 
    and if_app=1
    and if_recall=0
    and date(app_date) >= date'2025-01-01'
    GROUP BY 1,2 

),
issue_cnt AS ( 

    SELECT
        date(issue_date) as issue_date, 
        media_source2, 
        sum(if_issue) AS issue_cnt,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3') then if_issue else 0 end) AS issue_cnt_1_3,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(contract_amount_usd) as contract_amount_usd,
        sum(loan_cycle_amount) AS loan_cycle_amount,
        sum(overdue_amount_1_0) AS overdue_amount_1_0,
        sum(should_capital_1_0) AS should_capital_1_0,
        sum(overdue_amount_1_7) AS overdue_amount_1_7,
        sum(should_capital_1_7) AS should_capital_1_7
    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    and grant_strategy='NEW' 
    and date(issue_date) >= date'2025-01-01'
    GROUP BY 1,2
),

score_base as (
    select 
    case 
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai') then media_source 
    when lower(media_source) like '%ios%' then 'IOS_OTHER' 
    when media_source='ASA' then 'IOS_ASA' 
    else 'other'
    end as media_source
    ,date(create_time) add_day 
    ,biz_id
    ,model_score_a100_5bin 
    ,model_score_724fdc_5bin_all
    ,model_score_a101_10bin_ios
    from ind.tyn_allconvers_detail_new   
    where date(create_time) >= date'2025-01-01' 
), 

score_a100 AS (  select  add_day,media_source 
,sum(avg_pvalue_fenzi)as avg_pvalue_fenzi_a100
,sum(orders) as orders_a100
from ( select media_source ,add_day ,model_score_a100_5bin 
    ,count(biz_id) orders  
    ,avg(model_score_a100_5bin)*count(biz_id) as avg_pvalue_fenzi
    from score_base group by 1,2,3
) t group by 1,2
),

score_724 AS (  select  add_day,media_source 
,sum(avg_pvalue_fenzi)as avg_pvalue_fenzi_724
,sum(orders) as orders_724
from ( select  media_source ,add_day ,model_score_724fdc_5bin_all 
    ,count(biz_id) orders  
    ,avg(model_score_724fdc_5bin_all)*count(biz_id) as avg_pvalue_fenzi
    from score_base group by 1,2,3
) t group by 1,2
),


score_a101 AS (  select  add_day,media_source 
,sum(avg_pvalue_fenzi)as avg_pvalue_fenzi_a101
,sum(orders) as orders_a101
from ( select media_source ,add_day ,model_score_a101_10bin_ios 
    ,count(biz_id) orders  
    ,avg(model_score_a101_10bin_ios)*count(biz_id) as avg_pvalue_fenzi
    from score_base group by 1,2,3
) t group by 1,2
) 

          


SELECT
    COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date) AS ad_date,
    to_char(date_trunc('month', COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date)), 'yyyy-mm-dd') AS ad_date_month,
    to_char(date_trunc('week', COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date)), 'yyyy-mm-dd') AS ad_date_week,
    COALESCE(a.media_source, b.media_source, c.media_source, d.media_source2, e.media_source2) AS media_source,
    COALESCE(a.spend, 0) AS spend,
    COALESCE(b.install_cnt, 0) AS install_cnt,  
  
    COALESCE(c.reg_cnt, 0) AS reg_cnt,
    COALESCE(c.t0_reg_cnt, 0) AS t0_reg_cnt,
    COALESCE(c.t0_app_cnt, 0) AS t0_app_cnt,
    COALESCE(d.if_app, 0) AS if_app,
    COALESCE(d.in_confirm_cnt, 0) AS in_confirm_cnt,
    COALESCE(d.confirm_passed_cnt, 0) AS confirm_passed_cnt, 
    COALESCE(d.if_confirm_passed_num_t0, 0) AS if_confirm_passed_num_t0,
    COALESCE(d.confirm_grantcredit_amount, 0) AS confirm_grantcredit_amount,
    COALESCE(d.confirm_apply_amount, 0) AS confirm_apply_amount,
    COALESCE(d.apply_grantcredit_amount, 0) AS apply_grantcredit_amount, 
    COALESCE(d.if_in_confirm_1_2, 0) AS if_in_confirm_1_2,
    COALESCE(d.if_in_confirm_1_3, 0) AS if_in_confirm_1_3, 
    COALESCE(d.if_external_data_4_passed, 0) AS if_external_data_4_passed, 
    COALESCE(a101.avg_pvalue_fenzi_a101, 0) AS avg_pvalue_fenzi_a101,
    COALESCE(a100.avg_pvalue_fenzi_a100, 0) AS avg_pvalue_fenzi_a100,
    COALESCE(a724.avg_pvalue_fenzi_724, 0) AS avg_pvalue_fenzi_724,
    COALESCE(a101.orders_a101, 0) AS orders_a101,
    COALESCE(a100.orders_a100, 0) AS orders_a100,
    COALESCE(a724.orders_724, 0) AS orders_724, 
    COALESCE(e.issue_cnt, 0) AS issue_cnt,
    COALESCE(e.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(e.issue_cnt_1_3, 0) AS issue_cnt_1_3,
    COALESCE(e.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(e.contract_amount_usd, 0) AS contract_amount_usd,
    COALESCE(e.loan_cycle_amount, 0) AS loan_cycle_amount,
    COALESCE(e.overdue_amount_1_0, 0) AS overdue_amount_1_0,
    COALESCE(e.should_capital_1_0, 0) AS should_capital_1_0,
    COALESCE(e.overdue_amount_1_7, 0) AS overdue_amount_1_7,
    COALESCE(e.should_capital_1_7, 0) AS should_capital_1_7 



FROM spend a
FULL OUTER JOIN install_cnt b ON a.ad_date = b.install_date AND a.media_source = b.media_source 

FULL OUTER JOIN reg_cnt c ON a.ad_date = c.reg_dt AND a.media_source = c.media_source

FULL OUTER JOIN apply_cnt d ON a.ad_date = d.app_date AND a.media_source = d.media_source2
left join score_a100 a100 on d.app_date = a100.add_day AND d.media_source2 = a100.media_source
left join score_724 a724 on d.app_date = a724.add_day AND d.media_source2 = a724.media_source
left join score_a101 a101 on d.app_date = a101.add_day AND d.media_source2 = a101.media_source

FULL OUTER JOIN issue_cnt e ON a.ad_date = e.issue_date AND a.media_source = e.media_source2;
