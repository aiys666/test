/*
【变更记录】
0524更新:增加用户手机号，邮箱，adid,省份，地区等个人信息;
0525更新：部分匹不到渠道的注册用户匹配'Sign_in_success_old'事件对应的渠道;
0526更新：清洗Vfine和kreditlist;
0609更新：清洗kreditlist;
VFINE site_id：
593-贷超位置1   
720-pinjamduit拒量
667-贷超位置2
0705更新：增加TIKTOK渠道
0731更新：site_id字段(vfine贷超的版位)
0811更新：增加channel,adset_name,adset_id字段
0818更新：增加Kwai渠道
0821更新：增加campaign_id
0824更新：增加Finmart
0327更新：增加cashcerdasid_int,cashcashpro
0410更新：增加kp拒量
0418更新：增加atomcm
0617更新：Tiktok渠道新增名tiktokglobal_int
0813更新：增加Rupiah Cepat
0904更新：新增touch_time
20241223更新:增加reg_channel,platform
20250117更新：增加youmi
20250310更新：增加Novabeyond,yup(这俩都是pp开头)
20250410更新：增加grab，mintegral_int
20250801更新：增加yolo
*/


drop table if exists ind.yolee_reg_install_new;
create table ind.yolee_reg_install_new as

select * from (
select * 
,row_number() over (partition by mid order by reg_dt desc) as rk
from (
 select
 distinct
mm.reg_dt
,mm.reg_time
,mm.mid
,mm.sex 
,mm.age 
,mm.degree_name --education
,mm.income_code 
,mm.phone_num 
,mm.email  
,mm.region
,mm.province
,mm.county
,mm.reg_channel
,coalesce(mm.media_source,zz.media_source) as media_source
,coalesce(mm.agency,zz.agency) as agency
,coalesce(mm.campaign,zz.campaign) as campaign
,coalesce(mm.campaign_id,zz.campaign_id) as campaign_id
,coalesce(mm.objective,zz.objective) as objective
,coalesce(mm.acquisition_type,zz.acquisition_type) as acquisition_type
,coalesce(mm.install_dt,zz.install_dt) as install_dt
,coalesce(mm.touch_dt,zz.touch_dt) as touch_dt
,coalesce(mm.device_model_type,zz.device_model_type) as device_model_type-- mobile_type 
,coalesce(mm.device_model_main,zz.device_model_main)  as device_model_main--mobile_detail
,coalesce(mm.advertising_id,zz.advertising_id) as  advertising_id
,coalesce(mm.site_id,zz.site_id) as  site_id 
,coalesce(mm.channel,zz.channel) as  channel 
,coalesce(mm.adset_name,zz.adset_name) as  adset_name 
,coalesce(mm.adset_id,zz.adset_id) as  adset_id 
,coalesce(mm.platform,zz.platform) as  platform 
  from 
(select 
distinct
date(a.reg_time) as reg_dt
,a.reg_time
,a.mid
,a.sex 
,date_diff('year',a.birthday,CURRENT_DATE) as age 
,a.degree_name 
,a.income_code 
,a.phone_num 
,a.email  
,a.region 
,split_part(a.region, ',', 1) as province
,split_part(a.region, ',', 2) as county
,a.reg_channel
,b.media_source
,b.agency
,b.campaign
,b.campaign_id
,b.objective
,b.acquisition_type
,b.install_dt
,b.touch_dt
,b.device_model_type 
,b.device_model_main 
,b.advertising_id
,b.site_id
,b.channel
,b.adset_name
,b.adset_id
,b.platform
from 
dwd.dwd_mem_info a 
left join (
select 
distinct             
             case when lower(campaign) like '%inhouse%' or lower(campaign) like '%kip1%' then 'inhouse'
     when lower(campaign) like '%yojoy%' then 'yojoy'
     when lower(campaign) like '%adtiger%' then 'adtiger'
     when lower(campaign) like '%mudplayer%' then 'mudplayer'
     when lower(campaign) like '%sino%' or lower(campaign) like '%meetsocial%' or  lower(campaign) like '%kip2%' then 'sino'
     when lower(campaign) like '%uniagency%' then 'uniagency'
     end as agency
             --,partner
       ,case 	   		
			when platform = 'ios' and  media_source = 'Apple Search Ads' then 'ASA'
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
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(campaign) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			--when campaign ='CookeAds_CPI' then 'CookeAds_CPI'
            when lower(campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
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
            when media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as media_source
       ,case when lower(campaign) like '%cpi%' or lower(campaign) like '%install%' then 'cpi'
when lower(campaign) like '%cprk%' then 'RK'
when lower(campaign) like '%cpr%' then 'cpr'
when lower(campaign) like '%cpalive%' then 'cpalive'
when lower(campaign) like '%cpa%' then 'cpa'
when lower(campaign) like '%cpx10%' then 'x-persona'
when lower(campaign) like '%cpx05%' then 'cpx05'
when lower(campaign) like '%cpx09%' then 'cpx07'
when lower(campaign) like '%cpx06%' then 'cpx06'
when lower(campaign) like '%cpx03%' then 'cpx03'
when lower(campaign) like '%cpq09%' then 'cpq09'
when lower(campaign) like '%cpq08%' then 'cpq08'
when lower(campaign) like '%cpq07%' then 'cpq07'   
when lower(campaign) like '%cpq06%' then 'cpq06'   
when lower(campaign) like '%cpq05%' then 'cpq05'   
when lower(campaign) like '%cpq04%' then 'cpq04'       
when lower(campaign) like '%order%' or lower(campaign) like '%creditall%' or lower(campaign) like '%crediall%' then 'CreditAll'
when lower(campaign) like '%cpk%' or lower(campaign) like '%firstloan%' then 'K'
  else 'none' end as objective
       ,campaign
       ,case when campaign like '%GP2%' or campaign='inhouse_samir_ID_20230412_Willys_Order_normal_test_1' 
--or campaign like '%FB2%' and campaign !='inhouse_FB2_samir_ID_20230504_Willys_cpx05_all_1'
or media_source in ('Facebook Ads','restricted') 
--or campaign like '%TT2%'
or media_source = 'bytedanceglobal_int'
or media_source = 'kwaiforbusiness_int'
then 'high_acquisition' 
   when media_source = 'organic' then 'Organic'
    else 'low_acquisition' 
  end as acquisition_type
   ,campaign_id
    ,customer_user_id
    ,split_part(device_model, '::', 1) as device_model_type 
    ,split_part(device_model, '::', 2) as device_model_main 
    ,date(substr(install_time_selected_timezone,1,10)) install_dt
    ,date(substr(event_time_selected_timezone,1,10)) reg_dt
    ,date(substr(attributed_touch_time_selected_timezone,1,10)) touch_dt
    ,advertising_id
    ,site_id
    ,channel
    ,adset_name
    ,adset_id
	,platform
from
ods.s08_appsflyer_push_data
where 
  event_name = 'Sign_in_success_new'
  ) b 
  on b.customer_user_id=cast(a.mid as varchar) 
  and b.reg_dt = date(a.reg_time)
 ) mm 
  left join 
  (
    select 
      case when lower(campaign) like '%inhouse%' or lower(campaign) like '%kip1%' then 'inhouse'
     when lower(campaign) like '%yojoy%' then 'yojoy'
     when lower(campaign) like '%adtiger%' then 'adtiger'
     when lower(campaign) like '%mudplayer%' then 'mudplayer'
     when lower(campaign) like '%sino%' or lower(campaign) like '%meetsocial%' or  lower(campaign) like '%kip2%' then 'sino'
     when lower(campaign) like '%uniagency%' then 'uniagency'
     end as agency
       ,case 
		when platform = 'ios' and  media_source = 'Apple Search Ads' then 'ASA'
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
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(campaign) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
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
            when media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as media_source
       ,case when lower(campaign) like '%cpi%' or lower(campaign) like '%install%' then 'cpi'
when lower(campaign) like '%cprk%' then 'RK'
when lower(campaign) like '%cpr%' then 'cpr'
when lower(campaign) like '%cpalive%' then 'cpalive'
when lower(campaign) like '%cpa%' then 'cpa'
when lower(campaign) like '%cpx10%' then 'x-persona'
when lower(campaign) like '%cpx05%' then 'cpx05'
when lower(campaign) like '%cpx09%' then 'cpx07'
when lower(campaign) like '%cpx06%' then 'cpx06'
when lower(campaign) like '%cpx03%' then 'cpx03'
when lower(campaign) like '%cpq09%' then 'cpq09'
when lower(campaign) like '%cpq08%' then 'cpq08'
when lower(campaign) like '%cpq07%' then 'cpq07'   
when lower(campaign) like '%cpq06%' then 'cpq06'   
when lower(campaign) like '%cpq05%' then 'cpq05'   
when lower(campaign) like '%cpq04%' then 'cpq04'       
when lower(campaign) like '%order%' or lower(campaign) like '%creditall%' or lower(campaign) like '%crediall%' then 'CreditAll'
when lower(campaign) like '%cpk%' or lower(campaign) like '%firstloan%' then 'K'
  else 'none' end as objective
       ,campaign
       ,case when campaign like '%GP2%' or campaign='inhouse_samir_ID_20230412_Willys_Order_normal_test_1' 
--or campaign like '%FB2%' and campaign !='inhouse_FB2_samir_ID_20230504_Willys_cpx05_all_1'
or media_source in ('Facebook Ads','restricted') 
--or campaign like '%TT2%'
or media_source = 'bytedanceglobal_int'
or media_source = 'kwaiforbusiness_int'
then 'high_acquisition' 
   when media_source = 'organic' then 'Organic'
    else 'low_acquisition' 
  end as acquisition_type
  ,campaign_id
  ,customer_user_id
    ,split_part(device_model, '::', 1) as device_model_type 
    ,split_part(device_model, '::', 2) as device_model_main 
    ,date(substr(install_time_selected_timezone,1,10)) install_dt
    ,date(substr(event_time_selected_timezone,1,10)) reg_dt
	,date(substr(attributed_touch_time_selected_timezone,1,10)) touch_dt
    ,advertising_id
    ,site_id
    ,channel
    ,adset_name
    ,adset_id
	,platform
    from 
  (	
select 
    customer_user_id
    ,min_by(device_model,event_time_selected_timezone) as device_model  --null the last
    ,min_by(media_source,event_time_selected_timezone) as media_source
    ,min_by(campaign,event_time_selected_timezone) as campaign
    ,min_by(campaign_id,event_time_selected_timezone) as campaign_id
    ,min_by(advertising_id,event_time_selected_timezone) as advertising_id
    ,min_by(install_time_selected_timezone,event_time_selected_timezone) install_time_selected_timezone  
	,min_by(attributed_touch_time_selected_timezone,event_time_selected_timezone) attributed_touch_time_selected_timezone  
    ,min_by(event_time_selected_timezone,event_time_selected_timezone ) event_time_selected_timezone
    ,min_by(partner,event_time_selected_timezone) as partner
    ,min_by(site_id,event_time_selected_timezone) as site_id
    ,min_by(channel,event_time_selected_timezone) as channel
    ,min_by(adset_name,event_time_selected_timezone) as adset_name
    ,min_by(adset_id,event_time_selected_timezone) as adset_id
	,min_by(platform,event_time_selected_timezone) as platform
from
ods.s08_appsflyer_push_data
where 
  event_name = 'Sign_in_success_old'
  group by 1
  ) oo ) zz 
  on zz.customer_user_id=cast(mm.mid as varchar) 
  and zz.reg_dt >= mm.reg_dt 
  and mm.media_source is null  and mm.agency is null and mm.campaign is null and mm.device_model_type is null
  and mm.install_dt is null and mm.advertising_id is null  and mm.campaign_id is null and mm.touch_dt is null
  and mm.device_model_main is null    
) nn ) qq where rk = 1















---advertising_id !='00000000-0000-0000-0000-000000000000' 为IOS

drop table if exists ind.cyl_install_register;
create table if not exists ind.cyl_install_register as
select distinct advertising_id,app_version,platform,date(event_time + interval'7' hour) as install_date,customer_user_id,appsflyer_id,
case 
when platform = 'ios' and  media_source = 'Apple Search Ads' then 'ASA'
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
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(campaign) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
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
            when media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as media_source
        ,case 
		when platform = 'ios' and  contributor_1_media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  contributor_1_media_source = 'restricted' then 'IOS-fb'
			when platform = 'ios' and  contributor_1_media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  contributor_1_media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  contributor_1_media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  contributor_1_media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  contributor_1_media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  contributor_1_media_source = 'tangads' then 'IOS-tangads'
		  --when platform = 'ios' and  contributor_1_media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when contributor_1_media_source='googleadwords_int' then 'Google'
             when contributor_1_media_source='Facebook Ads' or contributor_1_media_source='restricted' then 'Facebook'
             when contributor_1_media_source='organic' then 'Organic'
             when contributor_1_media_source = 'shareit_int' then 'Shareit'
			       when  contributor_1_media_source = 'kreditlist_int' then 'kreditlist_int'
			       when contributor_1_media_source = 'vfine_int' or contributor_1_media_source = 'adecentptuo_int' then 'Vfine'

             --when  contributor_1_media_source = 'kreditlist_int' or (contributor_1_media_source = 'vfine_int' and partner like '%redi%'  ) 
             --or 
             --(contributor_1_media_source is null and partner = 'kreditlist')
             --then 'kreditlist_int'
			       --when contributor_1_media_source = 'vfine_int' or contributor_1_media_source = 'adecentptuo_int' then 'Vfine'
             when contributor_1_media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when contributor_1_media_source = 'kwaiforbusiness_int' then 'Kwai'
             when contributor_1_media_source = 'cashcashpro' then 'cashcashpro'
			 when contributor_1_media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when contributor_1_media_source = 'kredit pintal' then 'kp'
			 when contributor_1_media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(contributor_1_campaign, '^pp') then 'Novabeyond'
			 when contributor_1_media_source = 'pyxis_int' then 'pyxis'
			 when contributor_1_media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when contributor_1_media_source = 'Twitter' then 'twitter'
			 when contributor_1_media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(contributor_1_campaign) like '%tecdo%' then 'Network union'
			when contributor_1_media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(contributor_1_campaign) like '%rainbow%' then 'rainbow'
			when contributor_1_media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(contributor_1_campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
			when contributor_1_campaign ='CookeAds_CPS' or lower(contributor_1_campaign) like '%cookeads%' then 'CookeAds_CPS'
			--when partner = '19mobicn' then '19mobi'
			when contributor_1_campaign = 'Samire_Jan2025youmi' then 'youmi'
			when contributor_1_media_source ='yupaamj_int' then 'yup'
			--when regexp_like(contributor_1_campaign, '^pp') then 'Novabeyond'
			when contributor_1_media_source = 'mintegral_int' then 'mintegral_int'
			when lower(contributor_1_media_source) like '%grab%' then 'Grab'
			when contributor_1_media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(contributor_1_campaign) like '%runto%' then 'RUNTOA'
			when lower(contributor_1_campaign) like '%mejoy%'  then 'mejoy'
			when lower(contributor_1_campaign) like '%yolo%'  then 'yolo'
			when contributor_1_media_source ='LinkAja_ads' then 'LinkAja_ads'
			when contributor_1_media_source ='easycash01' then 'easycash01'
			when contributor_1_media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when contributor_1_media_source ='tangads' then 'tangads'
			when contributor_1_media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when contributor_1_media_source ='oppoglobal_int' then 'oppoglobal_int'
            when contributor_1_media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as contributor_1_media_source
        ,case 
		when platform = 'ios' and  contributor_2_media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  contributor_2_media_source = 'restricted' then 'IOS-fb'
			when platform = 'ios' and  contributor_2_media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  contributor_2_media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  contributor_2_media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  contributor_2_media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  contributor_2_media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  contributor_2_media_source = 'tangads' then 'IOS-tangads'
		  --when platform = 'ios' and  contributor_2_media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when contributor_2_media_source='googleadwords_int' then 'Google'
             when contributor_2_media_source='Facebook Ads' or contributor_2_media_source='restricted' then 'Facebook'
             when contributor_2_media_source='organic' then 'Organic'
             when contributor_2_media_source = 'shareit_int' then 'Shareit'
			       when  contributor_2_media_source = 'kreditlist_int' then 'kreditlist_int'
			       when contributor_2_media_source = 'vfine_int' or contributor_2_media_source = 'adecentptuo_int' then 'Vfine'

             --when  contributor_2_media_source = 'kreditlist_int' or (contributor_2_media_source = 'vfine_int' and partner like '%redi%'  ) 
             --or 
             --(contributor_2_media_source is null and partner = 'kreditlist')
             --then 'kreditlist_int'
			       --when contributor_2_media_source = 'vfine_int' or contributor_2_media_source = 'adecentptuo_int' then 'Vfine'
             when contributor_2_media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when contributor_2_media_source = 'kwaiforbusiness_int' then 'Kwai'
             when contributor_2_media_source = 'cashcashpro' then 'cashcashpro'
			 when contributor_2_media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when contributor_2_media_source = 'kredit pintal' then 'kp'
			 when contributor_2_media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(contributor_2_campaign, '^pp') then 'Novabeyond'
			 when contributor_2_media_source = 'pyxis_int' then 'pyxis'
			 when contributor_2_media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when contributor_2_media_source = 'Twitter' then 'twitter'
			 when contributor_2_media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(contributor_2_campaign) like '%tecdo%' then 'Network union'
			when contributor_2_media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(contributor_2_campaign) like '%rainbow%' then 'rainbow'
			when contributor_2_media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(contributor_2_campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
			when contributor_2_campaign ='CookeAds_CPS' or lower(contributor_2_campaign) like '%cookeads%' then 'CookeAds_CPS'
			--when partner = '19mobicn' then '19mobi'
			when contributor_2_campaign = 'Samire_Jan2025youmi' then 'youmi'
			when contributor_2_media_source ='yupaamj_int' then 'yup'
			--when regexp_like(contributor_2_campaign, '^pp') then 'Novabeyond'
			when contributor_2_media_source = 'mintegral_int' then 'mintegral_int'
			when lower(contributor_2_media_source) like '%grab%' then 'Grab'
			when contributor_2_media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(contributor_2_campaign) like '%runto%' then 'RUNTOA'
			when lower(contributor_2_campaign) like '%mejoy%'  then 'mejoy'
			when lower(contributor_2_campaign) like '%yolo%'  then 'yolo'
			when contributor_2_media_source ='LinkAja_ads' then 'LinkAja_ads'
			when contributor_2_media_source ='easycash01' then 'easycash01'
			when contributor_2_media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when contributor_2_media_source ='tangads' then 'tangads'
			when contributor_2_media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when contributor_2_media_source ='oppoglobal_int' then 'oppoglobal_int'
            when contributor_2_media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as contributor_2_media_source
        ,case 
		when platform = 'ios' and  contributor_3_media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  contributor_3_media_source = 'restricted' then 'IOS-fb'
			when platform = 'ios' and  contributor_3_media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  contributor_3_media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  contributor_3_media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  contributor_3_media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  contributor_3_media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  contributor_3_media_source = 'tangads' then 'IOS-tangads'
		  --when platform = 'ios' and  contributor_3_media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when contributor_3_media_source='googleadwords_int' then 'Google'
             when contributor_3_media_source='Facebook Ads' or contributor_3_media_source='restricted' then 'Facebook'
             when contributor_3_media_source='organic' then 'Organic'
             when contributor_3_media_source = 'shareit_int' then 'Shareit'
			       when  contributor_3_media_source = 'kreditlist_int' then 'kreditlist_int'
			       when contributor_3_media_source = 'vfine_int' or contributor_3_media_source = 'adecentptuo_int' then 'Vfine'

             --when  contributor_3_media_source = 'kreditlist_int' or (contributor_3_media_source = 'vfine_int' and partner like '%redi%'  ) 
             --or 
             --(contributor_3_media_source is null and partner = 'kreditlist')
             --then 'kreditlist_int'
			       --when contributor_3_media_source = 'vfine_int' or contributor_3_media_source = 'adecentptuo_int' then 'Vfine'
             when contributor_3_media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when contributor_3_media_source = 'kwaiforbusiness_int' then 'Kwai'
             when contributor_3_media_source = 'cashcashpro' then 'cashcashpro'
			 when contributor_3_media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when contributor_3_media_source = 'kredit pintal' then 'kp'
			 when contributor_3_media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(contributor_3_campaign, '^pp') then 'Novabeyond'
			 when contributor_3_media_source = 'pyxis_int' then 'pyxis'
			 when contributor_3_media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when contributor_3_media_source = 'Twitter' then 'twitter'
			 when contributor_3_media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(contributor_3_campaign) like '%tecdo%' then 'Network union'
			when contributor_3_media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(contributor_3_campaign) like '%rainbow%' then 'rainbow'
			when contributor_3_media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(contributor_3_campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
			when contributor_3_campaign ='CookeAds_CPS' or lower(contributor_3_campaign) like '%cookeads%' then 'CookeAds_CPS'
			--when partner = '19mobicn' then '19mobi'
			when contributor_3_campaign = 'Samire_Jan2025youmi' then 'youmi'
			when contributor_3_media_source ='yupaamj_int' then 'yup'
			--when regexp_like(contributor_3_campaign, '^pp') then 'Novabeyond'
			when contributor_3_media_source = 'mintegral_int' then 'mintegral_int'
			when lower(contributor_3_media_source) like '%grab%' then 'Grab'
			when contributor_3_media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(contributor_3_campaign) like '%runto%' then 'RUNTOA'
			when lower(contributor_3_campaign) like '%mejoy%'  then 'mejoy'
			when lower(contributor_3_campaign) like '%yolo%'  then 'yolo'
			when contributor_3_media_source ='LinkAja_ads' then 'LinkAja_ads'
			when contributor_3_media_source ='easycash01' then 'easycash01'
			when contributor_3_media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when contributor_3_media_source ='tangads' then 'tangads'
			when contributor_3_media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when contributor_3_media_source ='oppoglobal_int' then 'oppoglobal_int'
            when contributor_3_media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as contributor_3_media_source
        ,contributor_1_media_source as contributor_1_media_source_Initially
        ,contributor_2_media_source as contributor_2_media_source_Initially
        ,contributor_3_media_source as contributor_3_media_source_Initially
        ,contributor_1_campaign
        ,contributor_2_campaign
        ,contributor_3_campaign
        from 
        (select 
        a.*
        ,cast(json_extract(contributor_json,'$.contributor_1_media_source') as varchar) as contributor_1_media_source
        ,cast(json_extract(contributor_json,'$.contributor_2_media_source') as varchar) as contributor_2_media_source
        ,cast(json_extract(contributor_json,'$.contributor_3_media_source') as varchar) as contributor_3_media_source
        ,cast(json_extract(contributor_json,'$.contributor_1_touch_time') as varchar) as contributor_1_touch_time
        ,cast(json_extract(contributor_json,'$.contributor_2_touch_time') as varchar) as contributor_2_touch_time
        ,cast(json_extract(contributor_json,'$.contributor_3_touch_time') as varchar) as contributor_3_touch_time
        ,cast(json_extract(contributor_json,'$.contributor_1_campaign') as varchar) as contributor_1_campaign
        ,cast(json_extract(contributor_json,'$.contributor_2_campaign') as varchar) as contributor_2_campaign
        ,cast(json_extract(contributor_json,'$.contributor_3_campaign') as varchar) as contributor_3_campaign
        from ods.s08_appsflyer_push_data a
        where etl_date>='20220101' and event_name='install' 
        --and advertising_id !='00000000-0000-0000-0000-000000000000' 
        )a


drop table if exists ind.cyl_sign_click;
create table if not exists ind.cyl_sign_click as
select distinct advertising_id,app_version,platform,date(event_time + interval'7' hour) as install_date,customer_user_id,appsflyer_id
           ,case 
		when platform = 'ios' and  media_source = 'Apple Search Ads' then 'ASA'
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
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(campaign) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
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
            when media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as media_source
        ,case 
		when platform = 'ios' and  contributor_1_media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  contributor_1_media_source = 'restricted' then 'IOS-fb'
			when platform = 'ios' and  contributor_1_media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  contributor_1_media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  contributor_1_media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  contributor_1_media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  contributor_1_media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  contributor_1_media_source = 'tangads' then 'IOS-tangads'
		  --when platform = 'ios' and  contributor_1_media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when contributor_1_media_source='googleadwords_int' then 'Google'
             when contributor_1_media_source='Facebook Ads' or contributor_1_media_source='restricted' then 'Facebook'
             when contributor_1_media_source='organic' then 'Organic'
             when contributor_1_media_source = 'shareit_int' then 'Shareit'
			       when  contributor_1_media_source = 'kreditlist_int' then 'kreditlist_int'
			       when contributor_1_media_source = 'vfine_int' or contributor_1_media_source = 'adecentptuo_int' then 'Vfine'

             --when  contributor_1_media_source = 'kreditlist_int' or (contributor_1_media_source = 'vfine_int' and partner like '%redi%'  ) 
             --or 
             --(contributor_1_media_source is null and partner = 'kreditlist')
             --then 'kreditlist_int'
			       --when contributor_1_media_source = 'vfine_int' or contributor_1_media_source = 'adecentptuo_int' then 'Vfine'
             when contributor_1_media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when contributor_1_media_source = 'kwaiforbusiness_int' then 'Kwai'
             when contributor_1_media_source = 'cashcashpro' then 'cashcashpro'
			 when contributor_1_media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when contributor_1_media_source = 'kredit pintal' then 'kp'
			 when contributor_1_media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(contributor_1_campaign, '^pp') then 'Novabeyond'
			 when contributor_1_media_source = 'pyxis_int' then 'pyxis'
			 when contributor_1_media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when contributor_1_media_source = 'Twitter' then 'twitter'
			 when contributor_1_media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(contributor_1_campaign) like '%tecdo%' then 'Network union'
			when contributor_1_media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(contributor_1_campaign) like '%rainbow%' then 'rainbow'
			when contributor_1_media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(contributor_1_campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
			when contributor_1_campaign ='CookeAds_CPS' or lower(contributor_1_campaign) like '%cookeads%' then 'CookeAds_CPS'
			--when partner = '19mobicn' then '19mobi'
			when contributor_1_campaign = 'Samire_Jan2025youmi' then 'youmi'
			when contributor_1_media_source ='yupaamj_int' then 'yup'
			--when regexp_like(contributor_1_campaign, '^pp') then 'Novabeyond'
			when contributor_1_media_source = 'mintegral_int' then 'mintegral_int'
			when lower(contributor_1_media_source) like '%grab%' then 'Grab'
			when contributor_1_media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(contributor_1_campaign) like '%runto%' then 'RUNTOA'
			when lower(contributor_1_campaign) like '%mejoy%'  then 'mejoy'
			when lower(contributor_1_campaign) like '%yolo%'  then 'yolo'
			when contributor_1_media_source ='LinkAja_ads' then 'LinkAja_ads'
			when contributor_1_media_source ='easycash01' then 'easycash01'
			when contributor_1_media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when contributor_1_media_source ='tangads' then 'tangads'
			when contributor_1_media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when contributor_1_media_source ='oppoglobal_int' then 'oppoglobal_int'
            when contributor_1_media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as contributor_1_media_source
        ,case 
		when platform = 'ios' and  contributor_2_media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  contributor_2_media_source = 'restricted' then 'IOS-fb'
			when platform = 'ios' and  contributor_2_media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  contributor_2_media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  contributor_2_media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  contributor_2_media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  contributor_2_media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  contributor_2_media_source = 'tangads' then 'IOS-tangads'
		  --when platform = 'ios' and  contributor_2_media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when contributor_2_media_source='googleadwords_int' then 'Google'
             when contributor_2_media_source='Facebook Ads' or contributor_2_media_source='restricted' then 'Facebook'
             when contributor_2_media_source='organic' then 'Organic'
             when contributor_2_media_source = 'shareit_int' then 'Shareit'
			       when  contributor_2_media_source = 'kreditlist_int' then 'kreditlist_int'
			       when contributor_2_media_source = 'vfine_int' or contributor_2_media_source = 'adecentptuo_int' then 'Vfine'

             --when  contributor_2_media_source = 'kreditlist_int' or (contributor_2_media_source = 'vfine_int' and partner like '%redi%'  ) 
             --or 
             --(contributor_2_media_source is null and partner = 'kreditlist')
             --then 'kreditlist_int'
			       --when contributor_2_media_source = 'vfine_int' or contributor_2_media_source = 'adecentptuo_int' then 'Vfine'
             when contributor_2_media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when contributor_2_media_source = 'kwaiforbusiness_int' then 'Kwai'
             when contributor_2_media_source = 'cashcashpro' then 'cashcashpro'
			 when contributor_2_media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when contributor_2_media_source = 'kredit pintal' then 'kp'
			 when contributor_2_media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(contributor_2_campaign, '^pp') then 'Novabeyond'
			 when contributor_2_media_source = 'pyxis_int' then 'pyxis'
			 when contributor_2_media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when contributor_2_media_source = 'Twitter' then 'twitter'
			 when contributor_2_media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(contributor_2_campaign) like '%tecdo%' then 'Network union'
			when contributor_2_media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(contributor_2_campaign) like '%rainbow%' then 'rainbow'
			when contributor_2_media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(contributor_2_campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
			when contributor_2_campaign ='CookeAds_CPS' or lower(contributor_2_campaign) like '%cookeads%' then 'CookeAds_CPS'
			--when partner = '19mobicn' then '19mobi'
			when contributor_2_campaign = 'Samire_Jan2025youmi' then 'youmi'
			when contributor_2_media_source ='yupaamj_int' then 'yup'
			--when regexp_like(contributor_2_campaign, '^pp') then 'Novabeyond'
			when contributor_2_media_source = 'mintegral_int' then 'mintegral_int'
			when lower(contributor_2_media_source) like '%grab%' then 'Grab'
			when contributor_2_media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(contributor_2_campaign) like '%runto%' then 'RUNTOA'
			when lower(contributor_2_campaign) like '%mejoy%'  then 'mejoy'
			when lower(contributor_2_campaign) like '%yolo%'  then 'yolo'
			when contributor_2_media_source ='LinkAja_ads' then 'LinkAja_ads'
			when contributor_2_media_source ='easycash01' then 'easycash01'
			when contributor_2_media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when contributor_2_media_source ='tangads' then 'tangads'
			when contributor_2_media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when contributor_2_media_source ='oppoglobal_int' then 'oppoglobal_int'
            when contributor_2_media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as contributor_2_media_source
        ,case 
		when platform = 'ios' and  contributor_3_media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  contributor_3_media_source = 'restricted' then 'IOS-fb'
			when platform = 'ios' and  contributor_3_media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  contributor_3_media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  contributor_3_media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  contributor_3_media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  contributor_3_media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  contributor_3_media_source = 'tangads' then 'IOS-tangads'
		  --when platform = 'ios' and  contributor_3_media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when contributor_3_media_source='googleadwords_int' then 'Google'
             when contributor_3_media_source='Facebook Ads' or contributor_3_media_source='restricted' then 'Facebook'
             when contributor_3_media_source='organic' then 'Organic'
             when contributor_3_media_source = 'shareit_int' then 'Shareit'
			       when  contributor_3_media_source = 'kreditlist_int' then 'kreditlist_int'
			       when contributor_3_media_source = 'vfine_int' or contributor_3_media_source = 'adecentptuo_int' then 'Vfine'

             --when  contributor_3_media_source = 'kreditlist_int' or (contributor_3_media_source = 'vfine_int' and partner like '%redi%'  ) 
             --or 
             --(contributor_3_media_source is null and partner = 'kreditlist')
             --then 'kreditlist_int'
			       --when contributor_3_media_source = 'vfine_int' or contributor_3_media_source = 'adecentptuo_int' then 'Vfine'
             when contributor_3_media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when contributor_3_media_source = 'kwaiforbusiness_int' then 'Kwai'
             when contributor_3_media_source = 'cashcashpro' then 'cashcashpro'
			 when contributor_3_media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when contributor_3_media_source = 'kredit pintal' then 'kp'
			 when contributor_3_media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(contributor_3_campaign, '^pp') then 'Novabeyond'
			 when contributor_3_media_source = 'pyxis_int' then 'pyxis'
			 when contributor_3_media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when contributor_3_media_source = 'Twitter' then 'twitter'
			 when contributor_3_media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(contributor_3_campaign) like '%tecdo%' then 'Network union'
			when contributor_3_media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(contributor_3_campaign) like '%rainbow%' then 'rainbow'
			when contributor_3_media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(contributor_3_campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
			when contributor_3_campaign ='CookeAds_CPS' or lower(contributor_3_campaign) like '%cookeads%' then 'CookeAds_CPS'
			--when partner = '19mobicn' then '19mobi'
			when contributor_3_campaign = 'Samire_Jan2025youmi' then 'youmi'
			when contributor_3_media_source ='yupaamj_int' then 'yup'
			--when regexp_like(contributor_3_campaign, '^pp') then 'Novabeyond'
			when contributor_3_media_source = 'mintegral_int' then 'mintegral_int'
			when lower(contributor_3_media_source) like '%grab%' then 'Grab'
			when contributor_3_media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(contributor_3_campaign) like '%runto%' then 'RUNTOA'
			when lower(contributor_3_campaign) like '%mejoy%'  then 'mejoy'
			when lower(contributor_3_campaign) like '%yolo%'  then 'yolo'
			when contributor_3_media_source ='LinkAja_ads' then 'LinkAja_ads'
			when contributor_3_media_source ='easycash01' then 'easycash01'
			when contributor_3_media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when contributor_3_media_source ='tangads' then 'tangads'
			when contributor_3_media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when contributor_3_media_source ='oppoglobal_int' then 'oppoglobal_int'
            when contributor_3_media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as contributor_3_media_source
        ,contributor_1_media_source as contributor_1_media_source_Initially
        ,contributor_2_media_source as contributor_2_media_source_Initially
        ,contributor_3_media_source as contributor_3_media_source_Initially
        ,contributor_1_campaign
        ,contributor_2_campaign
        ,contributor_3_campaign
        ,event_name
        from 
        (select 
        a.*
        ,cast(json_extract(contributor_json,'$.contributor_1_media_source') as varchar) as contributor_1_media_source
        ,cast(json_extract(contributor_json,'$.contributor_2_media_source') as varchar) as contributor_2_media_source
        ,cast(json_extract(contributor_json,'$.contributor_3_media_source') as varchar) as contributor_3_media_source
        ,cast(json_extract(contributor_json,'$.contributor_1_touch_time') as varchar) as contributor_1_touch_time
        ,cast(json_extract(contributor_json,'$.contributor_2_touch_time') as varchar) as contributor_2_touch_time
        ,cast(json_extract(contributor_json,'$.contributor_3_touch_time') as varchar) as contributor_3_touch_time
        ,cast(json_extract(contributor_json,'$.contributor_1_campaign') as varchar) as contributor_1_campaign
        ,cast(json_extract(contributor_json,'$.contributor_2_campaign') as varchar) as contributor_2_campaign
        ,cast(json_extract(contributor_json,'$.contributor_3_campaign') as varchar) as contributor_3_campaign
        from ods.s08_appsflyer_push_data a
        where etl_date>='20220101' and event_name in('Sign_in_click_confirm','Sign_in_input_phone')
        --and advertising_id !='00000000-0000-0000-0000-000000000000' 
        )a



drop table if exists ind.cyl_Sign_in_input_phone;
create table if not exists ind.cyl_Sign_in_input_phone as
select distinct advertising_id,app_version,platform,date(event_time + interval'7' hour) as install_date,customer_user_id,appsflyer_id
           ,case 
		when platform = 'ios' and  media_source = 'Apple Search Ads' then 'ASA'
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
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(campaign) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
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
            when media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as media_source
        ,case 
		when platform = 'ios' and  contributor_1_media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  contributor_1_media_source = 'restricted' then 'IOS-fb'
			when platform = 'ios' and  contributor_1_media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  contributor_1_media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  contributor_1_media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  contributor_1_media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  contributor_1_media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  contributor_1_media_source = 'tangads' then 'IOS-tangads'
		  --when platform = 'ios' and  contributor_1_media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when contributor_1_media_source='googleadwords_int' then 'Google'
             when contributor_1_media_source='Facebook Ads' or contributor_1_media_source='restricted' then 'Facebook'
             when contributor_1_media_source='organic' then 'Organic'
             when contributor_1_media_source = 'shareit_int' then 'Shareit'
			       when  contributor_1_media_source = 'kreditlist_int' then 'kreditlist_int'
			       when contributor_1_media_source = 'vfine_int' or contributor_1_media_source = 'adecentptuo_int' then 'Vfine'

             --when  contributor_1_media_source = 'kreditlist_int' or (contributor_1_media_source = 'vfine_int' and partner like '%redi%'  ) 
             --or 
             --(contributor_1_media_source is null and partner = 'kreditlist')
             --then 'kreditlist_int'
			       --when contributor_1_media_source = 'vfine_int' or contributor_1_media_source = 'adecentptuo_int' then 'Vfine'
             when contributor_1_media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when contributor_1_media_source = 'kwaiforbusiness_int' then 'Kwai'
             when contributor_1_media_source = 'cashcashpro' then 'cashcashpro'
			 when contributor_1_media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when contributor_1_media_source = 'kredit pintal' then 'kp'
			 when contributor_1_media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(contributor_1_campaign, '^pp') then 'Novabeyond'
			 when contributor_1_media_source = 'pyxis_int' then 'pyxis'
			 when contributor_1_media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when contributor_1_media_source = 'Twitter' then 'twitter'
			 when contributor_1_media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(contributor_1_campaign) like '%tecdo%' then 'Network union'
			when contributor_1_media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(contributor_1_campaign) like '%rainbow%' then 'rainbow'
			when contributor_1_media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(contributor_1_campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
			when contributor_1_campaign ='CookeAds_CPS' or lower(contributor_1_campaign) like '%cookeads%' then 'CookeAds_CPS'
			--when partner = '19mobicn' then '19mobi'
			when contributor_1_campaign = 'Samire_Jan2025youmi' then 'youmi'
			when contributor_1_media_source ='yupaamj_int' then 'yup'
			--when regexp_like(contributor_1_campaign, '^pp') then 'Novabeyond'
			when contributor_1_media_source = 'mintegral_int' then 'mintegral_int'
			when lower(contributor_1_media_source) like '%grab%' then 'Grab'
			when contributor_1_media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(contributor_1_campaign) like '%runto%' then 'RUNTOA'
			when lower(contributor_1_campaign) like '%mejoy%'  then 'mejoy'
			when lower(contributor_1_campaign) like '%yolo%'  then 'yolo'
			when contributor_1_media_source ='LinkAja_ads' then 'LinkAja_ads'
			when contributor_1_media_source ='easycash01' then 'easycash01'
			when contributor_1_media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when contributor_1_media_source ='tangads' then 'tangads'
			when contributor_1_media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when contributor_1_media_source ='oppoglobal_int' then 'oppoglobal_int'
            when contributor_1_media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as contributor_1_media_source
        ,case 
		when platform = 'ios' and  contributor_2_media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  contributor_2_media_source = 'restricted' then 'IOS-fb'
			when platform = 'ios' and  contributor_2_media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  contributor_2_media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  contributor_2_media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  contributor_2_media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  contributor_2_media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  contributor_2_media_source = 'tangads' then 'IOS-tangads'
		  --when platform = 'ios' and  contributor_2_media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when contributor_2_media_source='googleadwords_int' then 'Google'
             when contributor_2_media_source='Facebook Ads' or contributor_2_media_source='restricted' then 'Facebook'
             when contributor_2_media_source='organic' then 'Organic'
             when contributor_2_media_source = 'shareit_int' then 'Shareit'
			       when  contributor_2_media_source = 'kreditlist_int' then 'kreditlist_int'
			       when contributor_2_media_source = 'vfine_int' or contributor_2_media_source = 'adecentptuo_int' then 'Vfine'

             --when  contributor_2_media_source = 'kreditlist_int' or (contributor_2_media_source = 'vfine_int' and partner like '%redi%'  ) 
             --or 
             --(contributor_2_media_source is null and partner = 'kreditlist')
             --then 'kreditlist_int'
			       --when contributor_2_media_source = 'vfine_int' or contributor_2_media_source = 'adecentptuo_int' then 'Vfine'
             when contributor_2_media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when contributor_2_media_source = 'kwaiforbusiness_int' then 'Kwai'
             when contributor_2_media_source = 'cashcashpro' then 'cashcashpro'
			 when contributor_2_media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when contributor_2_media_source = 'kredit pintal' then 'kp'
			 when contributor_2_media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(contributor_2_campaign, '^pp') then 'Novabeyond'
			 when contributor_2_media_source = 'pyxis_int' then 'pyxis'
			 when contributor_2_media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when contributor_2_media_source = 'Twitter' then 'twitter'
			 when contributor_2_media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(contributor_2_campaign) like '%tecdo%' then 'Network union'
			when contributor_2_media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(contributor_2_campaign) like '%rainbow%' then 'rainbow'
			when contributor_2_media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(contributor_2_campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
			when contributor_2_campaign ='CookeAds_CPS' or lower(contributor_2_campaign) like '%cookeads%' then 'CookeAds_CPS'
			--when partner = '19mobicn' then '19mobi'
			when contributor_2_campaign = 'Samire_Jan2025youmi' then 'youmi'
			when contributor_2_media_source ='yupaamj_int' then 'yup'
			--when regexp_like(contributor_2_campaign, '^pp') then 'Novabeyond'
			when contributor_2_media_source = 'mintegral_int' then 'mintegral_int'
			when lower(contributor_2_media_source) like '%grab%' then 'Grab'
			when contributor_2_media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(contributor_2_campaign) like '%runto%' then 'RUNTOA'
			when lower(contributor_2_campaign) like '%mejoy%'  then 'mejoy'
			when lower(contributor_2_campaign) like '%yolo%'  then 'yolo'
			when contributor_2_media_source ='LinkAja_ads' then 'LinkAja_ads'
			when contributor_2_media_source ='easycash01' then 'easycash01'
			when contributor_2_media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when contributor_2_media_source ='tangads' then 'tangads'
			when contributor_2_media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when contributor_2_media_source ='oppoglobal_int' then 'oppoglobal_int'
            when contributor_2_media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as contributor_2_media_source
        ,case 
		when platform = 'ios' and  contributor_3_media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  contributor_3_media_source = 'restricted' then 'IOS-fb'
			when platform = 'ios' and  contributor_3_media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  contributor_3_media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  contributor_3_media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  contributor_3_media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  contributor_3_media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  contributor_3_media_source = 'tangads' then 'IOS-tangads'
		  --when platform = 'ios' and  contributor_3_media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when contributor_3_media_source='googleadwords_int' then 'Google'
             when contributor_3_media_source='Facebook Ads' or contributor_3_media_source='restricted' then 'Facebook'
             when contributor_3_media_source='organic' then 'Organic'
             when contributor_3_media_source = 'shareit_int' then 'Shareit'
			       when  contributor_3_media_source = 'kreditlist_int' then 'kreditlist_int'
			       when contributor_3_media_source = 'vfine_int' or contributor_3_media_source = 'adecentptuo_int' then 'Vfine'

             --when  contributor_3_media_source = 'kreditlist_int' or (contributor_3_media_source = 'vfine_int' and partner like '%redi%'  ) 
             --or 
             --(contributor_3_media_source is null and partner = 'kreditlist')
             --then 'kreditlist_int'
			       --when contributor_3_media_source = 'vfine_int' or contributor_3_media_source = 'adecentptuo_int' then 'Vfine'
             when contributor_3_media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when contributor_3_media_source = 'kwaiforbusiness_int' then 'Kwai'
             when contributor_3_media_source = 'cashcashpro' then 'cashcashpro'
			 when contributor_3_media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when contributor_3_media_source = 'kredit pintal' then 'kp'
			 when contributor_3_media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(contributor_3_campaign, '^pp') then 'Novabeyond'
			 when contributor_3_media_source = 'pyxis_int' then 'pyxis'
			 when contributor_3_media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when contributor_3_media_source = 'Twitter' then 'twitter'
			 when contributor_3_media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(contributor_3_campaign) like '%tecdo%' then 'Network union'
			when contributor_3_media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(contributor_3_campaign) like '%rainbow%' then 'rainbow'
			when contributor_3_media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when lower(contributor_3_campaign) like '%cookeads_cpi%' then 'CookeAds_CPI'
			when contributor_3_campaign ='CookeAds_CPS' or lower(contributor_3_campaign) like '%cookeads%' then 'CookeAds_CPS'
			--when partner = '19mobicn' then '19mobi'
			when contributor_3_campaign = 'Samire_Jan2025youmi' then 'youmi'
			when contributor_3_media_source ='yupaamj_int' then 'yup'
			--when regexp_like(contributor_3_campaign, '^pp') then 'Novabeyond'
			when contributor_3_media_source = 'mintegral_int' then 'mintegral_int'
			when lower(contributor_3_media_source) like '%grab%' then 'Grab'
			when contributor_3_media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(contributor_3_campaign) like '%runto%' then 'RUNTOA'
			when lower(contributor_3_campaign) like '%mejoy%'  then 'mejoy'
			when lower(contributor_3_campaign) like '%yolo%'  then 'yolo'
			when contributor_3_media_source ='LinkAja_ads' then 'LinkAja_ads'
			when contributor_3_media_source ='easycash01' then 'easycash01'
			when contributor_3_media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when contributor_3_media_source ='tangads' then 'tangads'
			when contributor_3_media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when contributor_3_media_source ='oppoglobal_int' then 'oppoglobal_int'
            when contributor_3_media_source like '%int%' then 'Affiliate'
			 else 'Organic'
        end as contributor_3_media_source
        ,contributor_1_media_source as contributor_1_media_source_Initially
        ,contributor_2_media_source as contributor_2_media_source_Initially
        ,contributor_3_media_source as contributor_3_media_source_Initially
        ,contributor_1_campaign
        ,contributor_2_campaign
        ,contributor_3_campaign
        ,event_name
        ,event_value
        from 
        (select 
        a.*
        ,cast(json_extract(contributor_json,'$.contributor_1_media_source') as varchar) as contributor_1_media_source
        ,cast(json_extract(contributor_json,'$.contributor_2_media_source') as varchar) as contributor_2_media_source
        ,cast(json_extract(contributor_json,'$.contributor_3_media_source') as varchar) as contributor_3_media_source
        ,cast(json_extract(contributor_json,'$.contributor_1_touch_time') as varchar) as contributor_1_touch_time
        ,cast(json_extract(contributor_json,'$.contributor_2_touch_time') as varchar) as contributor_2_touch_time
        ,cast(json_extract(contributor_json,'$.contributor_3_touch_time') as varchar) as contributor_3_touch_time
        ,cast(json_extract(contributor_json,'$.contributor_1_campaign') as varchar) as contributor_1_campaign
        ,cast(json_extract(contributor_json,'$.contributor_2_campaign') as varchar) as contributor_2_campaign
        ,cast(json_extract(contributor_json,'$.contributor_3_campaign') as varchar) as contributor_3_campaign
        from ods.s08_appsflyer_push_data a
        where etl_date>='20220101' and event_name in('Sign_in_input_phone')
        --and advertising_id !='00000000-0000-0000-0000-000000000000' 
        )a









{"contributor_3_campaign":"inhouse_FB2_samir_ID_20250626_L3_lal_1","contributor_3_touch_time":"2025-08-11T12:30:56","contributor_1_touch_time":"2025-08-13T22:42:02.026","contributor_2_media_source":"logisticss4_int","contributor_2_touch_type":"click","contributor_3_media_source":"facebook_int","contributor_2_match_type":"id_matching","contributor_1_media_source":"tiktokglobal_int","contributor_1_campaign":"inhouse_TT3_samir_20250122_VO_LAL","contributor_1_engagement_type":"click_to_app","contributor_1_touch_type":"click","contributor_2_touch_time":"2025-08-12T01:07:21.471","contributor_3_engagement_type":"click_to_app","contributor_3_touch_type":"click","contributor_2_campaign":"CookeAds_CPS_1425","contributor_2_engagement_type":"click_unspecified","contributor_3_match_type":"fb_referrer","contributor_1_match_type":"id_matching"}
tiktokglobal_int
logisticss4_int
facebook_int
2025-08-13T22:42:02.026
2025-08-12T01:07:21.471
2025-08-11T12:30:56
　
　









---
select 
to_char(date_trunc('month',date(t1.install_date)),'yyyy-mm-dd') as install_month
--,t1.app_version
--,t1.media_source
,t1.media_source2
,t1.platform
,grant_strategy
--,contributor_1_media_source
--,contributor_2_media_source
--,contributor_3_media_source
,contributor_1_media_source2
,contributor_2_media_source2
,contributor_3_media_source2
,case when contributor_1_media_source2 in('Google','Facebook','Tiktok','Kwai') 
then contributor_1_media_source2 else media_source2 end 
as re1_media_source2
,case when contributor_1_media_source2 in('Google','Facebook','Tiktok','Kwai') 
then contributor_1_media_source2
when contributor_1_media_source2 not in('Google','Facebook','Tiktok','Kwai')
and contributor_2_media_source2 in('Google','Facebook','Tiktok','Kwai') 
then contributor_2_media_source2 else media_source2 
end as re2_media_source2
,case when contributor_1_media_source2 in('Google','Facebook','Tiktok','Kwai') 
then contributor_1_media_source2
when contributor_1_media_source2 not in('Google','Facebook','Tiktok','Kwai')
and contributor_2_media_source2 in('Google','Facebook','Tiktok','Kwai') then contributor_2_media_source2
when contributor_1_media_source2 not in('Google','Facebook','Tiktok','Kwai')
and contributor_2_media_source2 not in('Google','Facebook','Tiktok','Kwai') 
and contributor_3_media_source2 in('Google','Facebook','Tiktok','Kwai') 
then contributor_3_media_source2 else media_source2 
end as re3_media_source2
,new_grade_level
,case when rn2=1 then '1'
when rn2=2 then '2'
when rn2=3 then '3'
when rn2>=4 then '4+'
else 'other'
end as rn2
,count(distinct t1.appsflyer_id) as install_num
,count(distinct case when date_diff('day',install_date,date(reg_time2))=0 then mid end) as t0_reg
,count(distinct case when date_diff('day',install_date,date(reg_time2)) between 0 and 1 then mid end) as t1_reg
,count(distinct case when date_diff('day',install_date,date(reg_time2)) between 0 and 3 then mid end) as t3_reg
,count(distinct case when date_diff('day',install_date,date(reg_time2)) between 0 and 7 then mid end) as t7_reg
,count(distinct case when date_diff('day',install_date,date(app_date))=0 then mid end) as t0_apply
,count(distinct case when date_diff('day',install_date,date(app_date)) between 0 and 1 then mid end) as t1_apply
,count(distinct case when date_diff('day',install_date,date(app_date)) between 0 and 7 then mid end) as t7_apply
,count(distinct case when date_diff('day',install_date,date(app_date))=0 and if_in_confirm_final=1 then mid end) as t0_grant
,count(distinct case when (date_diff('day',install_date,date(app_date)) between 0 and 1) and if_in_confirm_final=1 then mid end) as t1_grant
,count(distinct case when (date_diff('day',install_date,date(app_date)) between 0 and 7) and if_in_confirm_final=1 then mid end) as t7_grant
,count(distinct case when date_diff('day',install_date,date(app_date))=0 and if_in_confirm_final=1 and new_grade_level in('1','2') then mid end) as t0_grant_1_2
,count(distinct case when (date_diff('day',install_date,date(app_date)) between 0 and 1) and if_in_confirm_final=1 and new_grade_level in('1','2') then mid end) as t1_grant_1_2
,count(distinct case when (date_diff('day',install_date,date(app_date)) between 0 and 7) and if_in_confirm_final=1 and new_grade_level in('1','2') then mid end) as t7_grant_1_2
,count(distinct case when date_diff('day',install_date,date(app_date))=0 and if_in_confirm_final=1 and new_grade_level in('1','2','3','4') then mid end) as t0_grant_1_4
,count(distinct case when (date_diff('day',install_date,date(app_date)) between 0 and 1) and if_in_confirm_final=1 and new_grade_level in('1','2','3','4') then mid end) as t1_grant_1_4
,count(distinct case when (date_diff('day',install_date,date(app_date)) between 0 and 7) and if_in_confirm_final=1 and new_grade_level in('1','2','3','4') then mid end) as t7_grant_1_4
from
(select a.*,
case when a.platform = 'ios' then 'IOS'
when a.media_source in('Google','Facebook','Organic','Tiktok','Kwai') then a.media_source
else 'Affiliate'
end as media_source2
,case when a.contributor_1_media_source = 'ios' then 'IOS'
when a.contributor_1_media_source in('Google','Facebook','Organic','Tiktok','Kwai') then a.contributor_1_media_source
else 'Affiliate'
end as contributor_1_media_source2
,case when a.contributor_2_media_source = 'ios' then 'IOS'
when a.contributor_2_media_source in('Google','Facebook','Organic','Tiktok','Kwai') then a.contributor_2_media_source
else 'Affiliate'
end as contributor_2_media_source2
,case when a.contributor_3_media_source = 'ios' then 'IOS'
when a.contributor_3_media_source in('Google','Facebook','Organic','Tiktok','Kwai') then a.contributor_3_media_source
else 'Affiliate'
end as contributor_3_media_source2
,case when a.install_date>date(m.reg_time) then 'impure' else 'pure' end as grant_strategy
,case when a.install_date>date(m.reg_time) then install_date else m.reg_time end as reg_time2
,m.reg_time
,m.mid
,c.app_date
,c.new_grade_level
,c.if_in_confirm_final
,c.if_confirm_passed_final
from  
    (select *
    ,row_number() over (partition by advertising_id,customer_user_id order by install_date asc) rn1
    ,row_number() over (partition by advertising_id order by install_date asc) rn2
    --,row_number() over (partition by appsflyer_id order by install_date asc) rn3
    --,row_number() over (partition by advertising_id,appsflyer_id order by install_date asc) rn4
    from ind.cyl_install_register
    where advertising_id !='00000000-0000-0000-0000-000000000000' 
    ) a
    left join dwd.dwd_mem_info m 
    on a.advertising_id=m.advertising_id
    left join
    (select * from
        (select mid,app_date,row_number() over (partition by mid order by app_date asc) rn,new_grade_level,
        case when source_channel2 not in ('IOS')
        and app_version <= '2.1.4' then 1
        when loan_type2 = 'loop' then if_app
        else if_in_confirm
      end as if_in_confirm_final,
      case
        when source_channel2 not in ('IOS')
        and app_version <= '2.1.4' then 1
        when confirm_date is not null then 1
        when loan_type2 = 'loop' then if_app
        else if_confirm_passed
        end as if_confirm_passed_final
        from ind.xly_application_funnel
        where if_app=1
        and grant_strategy='NEW'
        )c
        where rn=1
    )c
    on m.mid=c.mid
    where install_date <CURRENT_DATE
    --and install_date >=date('2024-01-01')
    
)t1
group by 1,2,3,4,5,6,7,8,9,10,11,12
limit 100000


select
a.*
from
    (select *
    from ind.cyl_install_register
    where advertising_id !='00000000-0000-0000-0000-000000000000' 
    )a 
    join
    (select distinct advertising_id
    from
        (select *
        ,row_number() over (partition by advertising_id,customer_user_id order by install_date asc) rn1
        ,row_number() over (partition by advertising_id order by install_date asc) rn2
        --,row_number() over (partition by appsflyer_id order by install_date asc) rn3
        --,row_number() over (partition by advertising_id,appsflyer_id order by install_date asc) rn4
        from ind.cyl_install_register
        where advertising_id !='00000000-0000-0000-0000-000000000000' 
        )b 
        where rn3>=3
    )b
    on a.advertising_id=b.advertising_id





---安装注册

select 
to_char(date_trunc('month',date(t1.install_date)),'yyyy-mm-dd') as install_month
--,t1.app_version
--,t1.media_source
,t1.media_source2
,t1.platform
,grant_strategy
--,contributor_1_media_source
--,contributor_2_media_source
--,contributor_3_media_source
,contributor_1_media_source2
,contributor_2_media_source2
,contributor_3_media_source2
,case when contributor_1_media_source2 in('Google','Facebook','Tiktok','Kwai') 
then contributor_1_media_source2 else media_source2 end 
as re1_media_source2
,case when contributor_1_media_source2 in('Google','Facebook','Tiktok','Kwai') 
then contributor_1_media_source2
when contributor_1_media_source2 not in('Google','Facebook','Tiktok','Kwai')
and contributor_2_media_source2 in('Google','Facebook','Tiktok','Kwai') 
then contributor_2_media_source2 else media_source2 
end as re2_media_source2
,case when contributor_1_media_source2 in('Google','Facebook','Tiktok','Kwai') 
then contributor_1_media_source2
when contributor_1_media_source2 not in('Google','Facebook','Tiktok','Kwai')
and contributor_2_media_source2 in('Google','Facebook','Tiktok','Kwai') then contributor_2_media_source2
when contributor_1_media_source2 not in('Google','Facebook','Tiktok','Kwai')
and contributor_2_media_source2 not in('Google','Facebook','Tiktok','Kwai') 
and contributor_3_media_source2 in('Google','Facebook','Tiktok','Kwai') 
then contributor_3_media_source2 else media_source2 
end as re3_media_source2
,new_grade_level
,case when rn2=1 then '1'
when rn2=2 then '2'
when rn2=3 then '3'
when rn2>=4 then '4+'
else 'other'
end as rn2
,count(distinct t1.appsflyer_id) as install_num
,count(distinct case when date_diff('day',install_date,date(reg_time2))=0 then mid end) as t0_reg
,count(distinct case when date_diff('day',install_date,date(reg_time2)) between 0 and 1 then mid end) as t1_reg
,count(distinct case when date_diff('day',install_date,date(reg_time2)) between 0 and 3 then mid end) as t3_reg
,count(distinct case when date_diff('day',install_date,date(reg_time2)) between 0 and 7 then mid end) as t7_reg
,count(distinct case when date_diff('day',install_date,date(app_date))=0 then mid end) as t0_apply
,count(distinct case when date_diff('day',install_date,date(app_date)) between 0 and 1 then mid end) as t1_apply
,count(distinct case when date_diff('day',install_date,date(app_date)) between 0 and 7 then mid end) as t7_apply
,count(distinct case when date_diff('day',install_date,date(app_date))=0 and if_in_confirm_final=1 then mid end) as t0_grant
,count(distinct case when (date_diff('day',install_date,date(app_date)) between 0 and 1) and if_in_confirm_final=1 then mid end) as t1_grant
,count(distinct case when (date_diff('day',install_date,date(app_date)) between 0 and 7) and if_in_confirm_final=1 then mid end) as t7_grant
,count(distinct case when date_diff('day',install_date,date(app_date))=0 and if_in_confirm_final=1 and new_grade_level in('1','2') then mid end) as t0_grant_1_2
,count(distinct case when (date_diff('day',install_date,date(app_date)) between 0 and 1) and if_in_confirm_final=1 and new_grade_level in('1','2') then mid end) as t1_grant_1_2
,count(distinct case when (date_diff('day',install_date,date(app_date)) between 0 and 7) and if_in_confirm_final=1 and new_grade_level in('1','2') then mid end) as t7_grant_1_2
,count(distinct case when date_diff('day',install_date,date(app_date))=0 and if_in_confirm_final=1 and new_grade_level in('1','2','3','4') then mid end) as t0_grant_1_4
,count(distinct case when (date_diff('day',install_date,date(app_date)) between 0 and 1) and if_in_confirm_final=1 and new_grade_level in('1','2','3','4') then mid end) as t1_grant_1_4
,count(distinct case when (date_diff('day',install_date,date(app_date)) between 0 and 7) and if_in_confirm_final=1 and new_grade_level in('1','2','3','4') then mid end) as t7_grant_1_4
,count(distinct appsflyer_id1) as Sign_in_click_confirm_num
,count(distinct appsflyer_id2) as Sign_in_input_phone_num
from
(select a.*,
case when a.platform = 'ios' then 'IOS'
when a.media_source in('Google','Facebook','Organic','Tiktok','Kwai') then a.media_source
else 'Affiliate'
end as media_source2
,case when a.contributor_1_media_source = 'ios' then 'IOS'
when a.contributor_1_media_source in('Google','Facebook','Organic','Tiktok','Kwai') then a.contributor_1_media_source
else 'Affiliate'
end as contributor_1_media_source2
,case when a.contributor_2_media_source = 'ios' then 'IOS'
when a.contributor_2_media_source in('Google','Facebook','Organic','Tiktok','Kwai') then a.contributor_2_media_source
else 'Affiliate'
end as contributor_2_media_source2
,case when a.contributor_3_media_source = 'ios' then 'IOS'
when a.contributor_3_media_source in('Google','Facebook','Organic','Tiktok','Kwai') then a.contributor_3_media_source
else 'Affiliate'
end as contributor_3_media_source2
,case when a.install_date>date(m.reg_time) then 'impure' else 'pure' end as grant_strategy
,case when a.install_date>date(m.reg_time) then a.install_date else m.reg_time end as reg_time2
,m.reg_time
,m.mid
,c.app_date
,c.new_grade_level
,c.if_in_confirm_final
,c.if_confirm_passed_final
,d.appsflyer_id as appsflyer_id1
,f.appsflyer_id as appsflyer_id2
from  
    (select *
    ,row_number() over (partition by advertising_id,customer_user_id order by install_date asc) rn1
    ,row_number() over (partition by advertising_id order by install_date asc) rn2
    --,row_number() over (partition by appsflyer_id order by install_date asc) rn3
    --,row_number() over (partition by advertising_id,appsflyer_id order by install_date asc) rn4
    from ind.cyl_install_register
    where advertising_id !='00000000-0000-0000-0000-000000000000' 
    ) a
    left join dwd.dwd_mem_info m 
    on a.advertising_id=m.advertising_id
    left join
    (select * from
        (select mid,app_date,row_number() over (partition by mid order by app_date asc) rn,new_grade_level,
        case when source_channel2 not in ('IOS')
        and app_version <= '2.1.4' then 1
        when loan_type2 = 'loop' then if_app
        else if_in_confirm
      end as if_in_confirm_final,
      case
        when source_channel2 not in ('IOS')
        and app_version <= '2.1.4' then 1
        when confirm_date is not null then 1
        when loan_type2 = 'loop' then if_app
        else if_confirm_passed
        end as if_confirm_passed_final
        from ind.xly_application_funnel
        where if_app=1
        and grant_strategy='NEW'
        )c
        where rn=1
    )c
    on m.mid=c.mid
    left join
    (select distinct install_date,advertising_id,appsflyer_id from ind.cyl_sign_click
    where event_name in('Sign_in_click_confirm'))d
    on date(a.install_date)=date(d.install_date) and a.appsflyer_id=d.appsflyer_id
    left join
    (select distinct install_date,advertising_id,appsflyer_id from ind.cyl_sign_click
    where event_name in('Sign_in_input_phone'))f
    on date(a.install_date)=date(f.install_date) and a.appsflyer_id=f.appsflyer_id
    where a.install_date <CURRENT_DATE
    --and install_date >=date('2024-01-01')   
)t1
group by 1,2,3,4,5,6,7,8,9,10,11,12
limit 100000


select
install_month,
case when length>=0 and length<=6 then '0-6'
when length>=7 and length<=10 then '7-10'
when length>=11 and length<=12 then '11-12'
when length>=13 then '13+'
else 'other' end as length,
count(distinct appsflyer_id)phone_num
from
    (select
    to_char(date_trunc('month',date(install_date)),'yyyy-mm-dd') as install_month,
    advertising_id,appsflyer_id,
    coalesce(cast(json_extract(event_value,'$.length') as bigint),-9999) as length
    from ind.cyl_Sign_in_input_phone
    where event_name in('Sign_in_input_phone')
    )a
    group by 1,2






----花费代码

    select
    to_char(date_trunc('month',date(ad_date)),'yyyy-mm-dd') as app_month
    ,case when media_source_1 in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source_1
    else 'Affiliate'
    end as media_source2
    ,media_source_1 as media_source
    ,sum(spend_usd_discount) as spend
    from
        (select
        a.*
        ,case when lower(campaign_name) like  '%ios%' or media_source='ASA' or lower(media_source) like '%ios%' then 'IOS'
                when media_source like '%oogle%' and lower(campaign_name) not like '%ios%' then 'Google'
                when media_source like '%acebook%' and lower(campaign_name) not like '%ios%' then 'Facebook'
                when media_source='organic' then 'Organic'
                when media_source = 'vfine_int' then 'Vfine'
                when media_source = 'shareit_int' then 'Shareit'
                when media_source = 'kreditlist_int' or media_source = 'kreditlist' then 'kreditlist_int'
                            when media_source = 'cashcashpro' then 'cashcashpro'
                            when media_source = 'cashcerdasid_int' then 'cashcerdas'
                            when media_source = 'kredit pintal' then 'kp'
                            when media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
                            when media_source = 'pyxis_int' then 'pyxis'
                            when media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
                else media_source
            end as media_source_1
        from ind.tyn_ads_cost_discount a
        where ad_date >= date'2024-01-01'
        )a
    group by 1,2,3

----不同渠道CPI/CPR/CPA/CPS,以及TOP 1-2/1-4的CPS;by渠道用户的mob0-4复借率
select 
a.install_month,
a.media_source,
a.media_source2,
a.install_num,
b.reg_num,
c.apply_num,
d.issue_num,
f.spend
from  
    (select 
    to_char(date_trunc('month',date(install_date)),'yyyy-mm-dd') as install_month,
    media_source,
    case when platform = 'ios' then 'IOS'
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai') then media_source
    else 'Affiliate'
    end as media_source2
    ,count(distinct appsflyer_id)install_num
    from ind.cyl_install_register
    group by 1,2,3
    )a
    left join
    (select to_char(date_trunc('month',date(reg_dt)),'yyyy-mm-dd') as reg_month,
    media_source,
    case when platform = 'ios' then 'IOS'
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai') then media_source
    else 'Affiliate'
    end as media_source2
    ,count(distinct mid)reg_num
    from ind.yolee_reg_install_new a
    group by 1,2,3
    )b 
    on a.install_month=b.reg_month
    and a.media_source=b.media_source
    and a.media_source2=b.media_source2
    left join 
    (select app_month,
    b.media_source,
    case when b.platform = 'ios' then 'IOS'
    when b.media_source in('Google','Facebook','Organic','Tiktok','Kwai') then b.media_source
    else 'Affiliate'
    end as media_source2
    ,count(distinct biz_id)apply_num
    from
        (select * 
        from ind.xly_application_funnel
        where if_app=1
        and grant_strategy='NEW')a
        left join
        ind.yolee_reg_install_new b
        on a.mid=b.mid
        group by 1,2,3
    )c
    on a.install_month=c.app_month
    and a.media_source=c.media_source
    and a.media_source2=c.media_source2
    left join
    (select issue_month,
    b.media_source,
    case when b.platform = 'ios' then 'IOS'
    when b.media_source in('Google','Facebook','Organic','Tiktok','Kwai') then b.media_source
    else 'Affiliate'
    end as media_source2
    ,count(distinct biz_id)issue_num
    from
        (select * 
        from ind.xly_application_funnel
        where if_app=1
        and grant_strategy='NEW'
        and if_issue=1
        )a
        left join
        ind.yolee_reg_install_new b
        on a.mid=b.mid
        group by 1,2,3
    )d
    on a.install_month=d.issue_month
    and a.media_source=d.media_source
    and a.media_source=d.media_source2
    left join
    (select
    to_char(date_trunc('month',date(ad_date)),'yyyy-mm-dd') as spend_month
    ,media_source1 as media_source
    ,case when media_source1 in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source1
    else 'Affiliate'
    end as media_source2
    ,sum(spend_usd_discount) as spend
    from
        (select
        a.*
        ,case when lower(campaign_name) like  '%ios%' or media_source='ASA' or lower(media_source) like '%ios%' then 'IOS'
                when media_source like '%oogle%' and lower(campaign_name) not like '%ios%' then 'Google'
                when media_source like '%acebook%' and lower(campaign_name) not like '%ios%' then 'Facebook'
                when media_source='organic' then 'Organic'
                when media_source = 'vfine_int' then 'Vfine'
                when media_source = 'shareit_int' then 'Shareit'
                when media_source = 'kreditlist_int' or media_source = 'kreditlist' then 'kreditlist_int'
                            when media_source = 'cashcashpro' then 'cashcashpro'
                            when media_source = 'cashcerdasid_int' then 'cashcerdas'
                            when media_source = 'kredit pintal' then 'kp'
                            when media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
                            when media_source = 'pyxis_int' then 'pyxis'
                            when media_source = 'Rupiah Cepat' then 'Rupiah Cepat'        
                else media_source
            end as media_source1
        from ind.tyn_ads_cost_discount a
        --where ad_date >= date'2024-01-01'
        )a
        group by 1,2,3
    )f
    on a.install_month=f.spend_month
    and a.media_source=f.media_source
    and a.media_source2=f.media_source2


--by 渠道
select 
a.install_month,
a.media_source2,
a.install_num,
b.reg_num,
c.apply_num,
d.issue_num,
f.spend
from  
    (select 
    to_char(date_trunc('month',date(install_date)),'yyyy-mm-dd') as install_month,
    case when platform = 'ios' then 'IOS'
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai') then media_source
    else 'Affiliate'
    end as media_source2
    ,count(distinct appsflyer_id)install_num
    from ind.cyl_install_register
    group by 1,2
    )a
    left join
    (select to_char(date_trunc('month',date(reg_dt)),'yyyy-mm-dd') as reg_month,
    case when platform = 'ios' then 'IOS'
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai') then media_source
    else 'Affiliate'
    end as media_source2
    ,count(distinct mid)reg_num
    from ind.yolee_reg_install_new a
    group by 1,2
    )b 
    on a.install_month=b.reg_month
    and a.media_source2=b.media_source2
    left join 
    (select app_month,
    case when b.platform = 'ios' then 'IOS'
    when b.media_source in('Google','Facebook','Organic','Tiktok','Kwai') then b.media_source
    else 'Affiliate'
    end as media_source2
    ,count(distinct biz_id)apply_num
    from
        (select * 
        from ind.xly_application_funnel
        where if_app=1
        and grant_strategy='NEW')a
        left join
        ind.yolee_reg_install_new b
        on a.mid=b.mid
        group by 1,2
    )c
    on a.install_month=c.app_month
    and a.media_source2=c.media_source2
    left join
    (select issue_month,
    case when b.platform = 'ios' then 'IOS'
    when b.media_source in('Google','Facebook','Organic','Tiktok','Kwai') then b.media_source
    else 'Affiliate'
    end as media_source2
    ,count(distinct biz_id)issue_num
    from
        (select * 
        from ind.xly_application_funnel
        where if_app=1
        and grant_strategy='NEW'
        and if_issue=1
        )a
        left join
        ind.yolee_reg_install_new b
        on a.mid=b.mid
        group by 1,2
    )d
    on a.install_month=d.issue_month
    and a.media_source2=d.media_source2
    left join
    (select
    to_char(date_trunc('month',date(ad_date)),'yyyy-mm-dd') as spend_month
    ,case when media_source1 in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source1
    else 'Affiliate'
    end as media_source2
    ,sum(spend_usd_discount) as spend
    from
        (select
        a.*
        ,case when lower(campaign_name) like  '%ios%' or media_source='ASA' or lower(media_source) like '%ios%' then 'IOS'
                when media_source like '%oogle%' and lower(campaign_name) not like '%ios%' then 'Google'
                when media_source like '%acebook%' and lower(campaign_name) not like '%ios%' then 'Facebook'
                when media_source='organic' then 'Organic'
                when media_source = 'vfine_int' then 'Vfine'
                when media_source = 'shareit_int' then 'Shareit'
                when media_source = 'kreditlist_int' or media_source = 'kreditlist' then 'kreditlist_int'
                            when media_source = 'cashcashpro' then 'cashcashpro'
                            when media_source = 'cashcerdasid_int' then 'cashcerdas'
                            when media_source = 'kredit pintal' then 'kp'
                            when media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
                            when media_source = 'pyxis_int' then 'pyxis'
                            when media_source = 'Rupiah Cepat' then 'Rupiah Cepat'        
                else media_source
            end as media_source1
        from ind.tyn_ads_cost_discount a
        --where ad_date >= date'2024-01-01'
        )a
        group by 1,2
    )f
    on a.install_month=f.spend_month
    and a.media_source2=f.media_source2



select
a.*,b.*
from
    (select issue_month,
    b.media_source,
    case when b.platform = 'ios' then 'IOS'
    when b.media_source in('Google','Facebook','Organic','Tiktok','Kwai') then b.media_source
    else 'Affiliate'
    end as media_source2
    ,count(distinct biz_id)issue_num
    from
        (select * 
        from ind.xly_application_funnel
        where if_app=1
        and grant_strategy='NEW'
        and if_issue=1
        )a
        left join
        ind.yolee_reg_install_new b
        on a.mid=b.mid
        group by 1,2,3
    )a
    left join
    (select 
    to_char(date_trunc('month',date(install_date)),'yyyy-mm-dd') as install_month,
    media_source,
    case when platform = 'ios' then 'IOS'
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai') then media_source
    else 'Affiliate'
    end as media_source2
    ,count(distinct appsflyer_id)install_num
    from ind.cyl_install_register
    group by 1,2,3
    )b 
    on a.issue_month=b.install_month
    and a.media_source=b.media_source
    and a.media_source2=b.media_source2








select mid,app_date,row_number() over (partition by mid order by app_date asc) rn,new_grade_level,
        case when source_channel2 not in ('IOS')
        and app_version <= '2.1.4' then 1
        when loan_type2 = 'loop' then if_app
        else if_in_confirm
      end as if_in_confirm_final,
      case
        when source_channel2 not in ('IOS')
        and app_version <= '2.1.4' then 1
        when confirm_date is not null then 1
        when loan_type2 = 'loop' then if_app
        else if_confirm_passed
        end as if_confirm_passed_final
        from ind.xly_application_funnel
        where if_app=1
        and grant_strategy='NEW'











first_open：
cpi
真实埋点
点点：

安装---注册


安装数据，广告ID,最初一次，


select to_char(date(t1.install_date),'yyyy-mm-dd') as install_dt
,to_char(date_trunc('month',date(t1.install_date)),'yyyy-mm-dd') as install_month
,t1.app_version
,t1.media_source2
,t1.platform
,grant_strategy
,count(distinct t1.appsflyer_id) as install_num
,count(distinct case when date_diff('day',install_date,date(reg_time2))=0 then mid end) as t0_reg
,count(distinct case when date_diff('day',install_date,date(reg_time2)) between 0 and 1 then mid end) as t1_reg
,count(distinct case when date_diff('day',install_date,date(reg_time2)) between 0 and 3 then mid end) as t3_reg
,count(distinct case when date_diff('day',install_date,date(reg_time2)) between 0 and 7 then mid end) as t7_reg
,count(distinct case when date_diff('day',install_date,date(reg_time2)) between 0 and 90 then mid end) as reg_num
from 
(select a.*,
case when a.platform = 'ios' then 'IOS'
when a.media_source in('Google','Facebook','Organic','Tiktok','Kwai') then a.media_source
else 'Affiliate'
end as media_source2
,case when a.install_date>date(m.reg_time) then 'impure' else 'pure' end as grant_strategy
,case when a.install_date>date(m.reg_time) then install_date else m.reg_time end as reg_time2
,m.reg_time
,m.mid
from  
    (select * from ind.cyl_install_register) a
    left join dwd.dwd_mem_info m 
    on a.advertising_id=m.advertising_id
    where install_date <CURRENT_DATE 
    --and install_date >=date('2024-01-01')
)t1
group by 1,2,3,4,5,6
limit 100000




select
install_month,
sum(af_num)
from
(select
to_char(date(t1.install_date),'yyyy-mm-dd') as install_dt,
to_char(date_trunc('month',date(t1.install_date)),'yyyy-mm-dd') as install_month,
count(distinct t1.appsflyer_id)af_num
from ind.cyl_install_register
group by 1,2
)a1
group by 1



----mob0-4付