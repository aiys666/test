--TABLE 1:ind.xly_loop_creditinfo 
drop table if exists ind.xly_loop_creditinfo;
create table ind.xly_loop_creditinfo as
-- 循环贷授信
  SELECT 
    externalid,SUBSTRING(externalid,1,16) as custid
    ,createtime, date(date_add('hour',8,createtime)) as loop_creditdate, data as loop_creditinfo
    ,case 
      when productId = 20010137 then 'plus' 
      when productId = 20010138 then 'single'
    else null end as reloan_type
  FROM ods.s21_strategyrecordentity
    where STRATEGYTYPE = 'CHAMPION'
  AND productId in (20010137,20010138) --循环贷授信流
  and iotype = 'OUT'
  ;

--TABLE 2:ind.xly_reloan_num
drop table if exists ind.xly_reloan_num;
create table  ind.xly_reloan_num as

  select 
    t1.id,mid,create_time
    ,case when issue_num is null then 1 else issue_num end as  reloan_num
    ,case when issue_num is null then  'NEW' ELSE 'OLD' end as grant_strategy
  from 
  (select  create_time,id,mid from ods.s09_os_credit_snapshot ) t1
  left join
  (
    select t1.id,count(t2.biz_id) +1 as issue_num from 
    (select  create_time,id,mid  from ods.s09_os_credit_snapshot) t1
    left join 
    (select cast(ceil(camera_id) as varchar) as biz_id,release_time, customer_id  
    from ods.s02_loan where state in (1,2,3,15)) t2 --放款表（走到放款节点）
    on t1.mid = t2.customer_id
    where create_time > release_time and release_time  is not null
    group by create_time, t1.id ,t1.mid
  ) t2
  on t1.id = t2.id
  ;

--TABLE 3:ind.xly_reloan_num2
drop table if exists ind.xly_reloan_num2;
create table  ind.xly_reloan_num2 as
  SELECT CAST(t1.ID as varchar) biz_id
  ,grant_strategy 
  ,baseinfo_onloan_hit_mid
  ,baseinfo_m_onloan_hit_mid
  ,if_hit_white_list
  ,case 
  when if_hit_white_list = 1 then 'WHITELIST'
  when grant_strategy = 'OLD' and baseinfo_m_onloan_hit_mid>=1 THEN 'OLD_PLUS_M'
  when grant_strategy = 'OLD' and  baseinfo_onloan_hit_mid>=1 THEN 'OLD_PLUS'
  when grant_strategy = 'NEW'  and mid_rn =0 then 'NEW_PURE' 
  when grant_strategy = 'NEW'  and mid_rn>0 then 'NEW_IMPURE' 
  when grant_strategy = 'OLD' THEN 'OLD_SINGLE'
  end as is_reloan2
  FROM 
  (
    select 
      a.id 
      ,grant_strategy
      ,CASE WHEN C.baseinfo_onloan_hit_mid IS NULL THEN B.baseinfo_onloan_hit_mid ELSE C.baseinfo_onloan_hit_mid END AS baseinfo_onloan_hit_mid
      ,baseinfo_m_onloan_hit_mid
    from ind.xly_reloan_num a
    left join 
    (
      select 
        mid
        ,date(date_parse(data_date, '%Y%m%d')) as data_date
        ,max(onloan_cnt) as baseinfo_onloan_hit_mid
      from dws.dws_loop_quota_while_list_his --循环贷白名单历史
      group by 1,2
    )b on a.mid =  b.mid AND DATE(A.create_time) = date_add('day',1,b.data_date)
    left join 
    (
      select CID,baseinfo_onloan_hit_mid
      from
      (
        SELECT A.CID,A.CREATE_TIME, B.CREATE_TIME,baseinfo_onloan_hit_mid
        ,row_number() over (partition by cid order by A.create_time) rn
        FROM 
        (
          SELECT cid,create_TIME, cast(json_extract(value,'$.baseinfo_onloan_hit_mid') as bigint) as baseinfo_onloan_hit_mid
          from ods.s09_os_variable_log 
          where name='baseinfo_onloan_hit_mid' and cid != 'null'
        ) a 
        left join 
        (select create_time,biz_id from ods.s05_creditx_order) b on A.cid = B.biz_id
        where A.create_TIME>B.create_time
      ) where rn = 1
    )C on a.ID = CAST(C.cid AS BIGINT) 
    left join 
    (
      select CID,baseinfo_m_onloan_hit_mid
      from 
      (
        SELECT A.CID,A.CREATE_TIME, B.CREATE_TIME,baseinfo_m_onloan_hit_mid
        ,row_number() over (partition by cid order by A.create_time) rn
        FROM 
        (
          SELECT cid,create_TIME, cast(json_extract(value,'$.baseinfo_m_onloan_hit_mid') as bigint)  as baseinfo_m_onloan_hit_mid
          from ods.s09_os_variable_log 
          where name='baseinfo_m_onloan_hit_mid' and cid != 'null'
        ) a
        left join 
        (select create_time,biz_id from ods.s05_creditx_order) b on A.cid = B.biz_id
        where  A.create_TIME>B.create_time
      ) where rn = 1
    ) d on a.ID =  CAST(d.cid AS BIGINT) 
  ) T1
  LEFT JOIN 
  (
    select a.id , count(b.biz_id) as mid_rn
    from ind.xly_reloan_num a
    left join 
    (SELECT biz_id,mid , create_time FROM ods.s05_creditx_order) b on a.mid = cast(b.mid as bigint) and a.create_time > b.create_time
    group by 1
  ) T2 ON T1.ID = T2.id
  left join 
  (
    select 
      CID
      , CASE WHEN if_hit_white_list_phone>0 OR if_hit_white_list_identity>0 THEN 1 ELSE 0 END AS if_hit_white_list
    FROM 
    (
      SELECT CID 
      , MAX(CAST(json_extract_scalar (value, '$.if_hit_white_list_phone') AS BIGINT)) AS if_hit_white_list_phone
      , MAX(CAST(json_extract_scalar (value, '$.if_hit_white_list_identity') AS BIGINT)) AS if_hit_white_list_identity
      FROM   ods.s09_os_variable_log
      WHERE  name IN ('if_hit_white_list_phone','if_hit_white_list_identity')  and cid != 'null'
      GROUP BY 1
    )
  ) t3 on T1.ID = cast(T3.CID as bigint)
  ;

--TABLE 4:ind.xly_application_funnel_1
drop table if exists ind.xly_application_funnel_1;  
create table ind.xly_application_funnel_1 as
select 
    a.*,case when product_level in ('M7','M8','M9','M10','M11','M12','M13','M14','M16') then 'M_4T'
   when product_level in ('M15','M17') then 'M_2T'
   when product_level in ('M18') then 'M_6T'
   when product_level like 'M%' and ceil(c.loan_cycle) >=120 then 'M_3T' 
   when product_level like 'M%' then 'M_3T'
        when product_level in ('A14','B10','B12','C8','A15','B13','B14','C9','G1','H3','H4','I5')  then 'F_NofeeNew_single'
        when product_level in ('H1') and ceil(c.loan_cycle) = 60 then 'F_NofeeNew_single'
        when product_level in ('A16','B15','B16','C10','G2','H2','I4','I6') then 'F_NofeeNew_double' 
        when product_level in ('H1') and ceil(c.loan_cycle) = 90 then 'F_NofeeNew_double'
        when a.product_level in ('B7','C7','A9','B8') then 'F-NofeeOld' 
        when substring(a.product_level,1,1) in ('D','E','F') then 'R_30D'
        when product_level is not null then 'R_15D'
        end as product_tag_detail
  ,  case when product_level in ('M7','M8','M9','M10','M11','M12','M13','M14','M16') then 'M'
   when product_level in ('M15','M17') then 'M'
   when product_level in ('M18') then 'M'
   when product_level like 'M%' and ceil(c.loan_cycle) >=120 then 'M'
   when product_level like 'M%' then 'M'
        when product_level in ('A14','B10','B12','C8','A15','B13','B14','C9','G1','H3','H4','I5','I6')  then 'F'
        when product_level in ('H1') and ceil(c.loan_cycle) = 60 then 'F'
        when product_level in ('A16','B15','B16','C10','G2','H2','I4') then 'F' 
        when product_level in ('H1') and ceil(c.loan_cycle) = 90 then 'F'
        when a.product_level in ('B7','C7','A9','B8') then 'F' 
        when substring(a.product_level,1,1) in ('D','E','F') then 'R'
        when product_level is not null then 'R'
        end as product_tag  
    ,case when loan_type = 2 or source = 'CIRCULAR' then 'loop' else 'normal' end as loan_type2 
    ,case 
    when a.app_version>='2.1.5' then 'new_process' 
    when a.app_version='0.0.0' then 'new_process' 
    ELSE 'old_process' end as apply_version 
    ,a1.reloan_num
    ,a1.grant_strategy              
    ,case 
    when b.source = '360' then 'R360' 
    when b.source = 'ATOM' then 'atomapi'
    else a2.media_source end as media_source
    ,a2.media_source_orig
    ,a2.objective
    ,a2.campaign_name 
    ,case 
    when a2.media_source = 'organic' then 'organic' 
    when a2.objective ='high_acquisition' then 'high_acquisition'
    else 'low_acquisition' end as acquisition_type  
    ,b.biz_id as app_id 
    ,b.lid
    ,b.product_type
    ,b.product_name
    ,b.grantcredit_amount/1000 AS order_credit_amount  
    ,b.create_time as app_time
    ,b.status 
    ,b.user_confirm_status 
    ,b.is_loan
    ,b.double_loan
    ,CASE 
    WHEN b.double_loan = 0 then 'NEW' 
    WHEN b.double_loan =1 THEN 'OLD' 
    else 'others' end as is_reloan
    ,b2.is_reloan2
    ,b.repayment
    ,b.bank_name
    ,b.source
    ,b.circular_amount
    ,b.source_channel
    ,case 
    when b.source_channel = 'AppStore' then 'IOS'
    when b.source_channel = 'google-play' then 'Android'
    when b.source_channel = '360' then 'R360'
    else 'OTHERS' end as source_channel2
    --,b.apply_period
    ,b1.interval_start
    ,b2.baseinfo_onloan_hit_mid
    ,c.loan_indexs
    ,ceil(c.loan_cycle) as loan_cycle
    ,c.contract_amount
    ,c.amount
    ,c.haircut_amount
    ,c.release_time
    ,c.cancel_time 
    ,c.finish_time
    ,c.state as loan_state 
    ,CASE WHEN b.biz_id IS NOT NULL THEN 1 ELSE 0 END AS if_app  
    ,CASE WHEN b.status = 372 then 1 else 0 end as if_pass 
    ,CASE WHEN b.is_loan = '1' THEN 1 ELSE 0 END AS IF_BID 

    ,cast(json_extract(a.grantcredit_info,'$.credit_raise_indexs') as decimal(10,3))  as credit_raise_indexs
    ,case when a.grantcredit_amount is not null then a.grantcredit_amount/1000  else cast(json_extract(grantcredit_info,'$.credit_amount') as bigint)  end as credit_amount 
    ,case when a.grantcredit_amount is not null then a.grantcredit_amount/1000  else cast(json_extract(grantcredit_info,'$.grantcredit_30d_amount') as bigint)  end as grantcredit_30d_amount
    ,case when a.grantcredit_amount is not null then a.grantcredit_amount/1000  else cast(json_extract(grantcredit_info,'$.grantcredit_60d_amount') as bigint)  end as grantcredit_60d_amount
    ,case when a.grantcredit_amount is not null then a.grantcredit_amount/1000  else cast(json_extract(grantcredit_info,'$.grantcredit_90d_amount') as bigint)  end as grantcredit_90d_amount
    ,case when a.grantcredit_amount is not null then a.grantcredit_amount/1000  else cast(json_extract(grantcredit_info,'$.grantcredit_120d_amount') as bigint)  end as grantcredit_120d_amount
    ,case when a.grantcredit_amount is not null then a.grantcredit_amount/1000  else cast(json_extract(grantcredit_info,'$.grantcredit_150d_amount') as bigint)  end as grantcredit_150d_amount
    ,case when a.grantcredit_amount is not null then a.grantcredit_amount/1000  else cast(json_extract(grantcredit_info,'$.grantcredit_180d_amount') as bigint)  end as grantcredit_180d_amount
    ,case when a.grantcredit_amount is not null then a.grantcredit_amount/1000  else cast(json_extract(grantcredit_info,'$.grantcredit_210d_amount') as bigint)  end as grantcredit_210d_amount
    ,cast(json_extract(grantcredit_info,'$.grant_amount_total') as bigint)  as grant_amount_total
    ,cast(json_extract(grantcredit_info,'$.baseinfo_grant_amount_total_last') as bigint)  as baseinfo_grant_amount_total_last
    ,cast(json_extract(grantcredit_info,'$.history_last_grantcredit_amount') as bigint)  as history_last_grantcredit_amount
    ,cast(json_extract(grantcredit_info,'$.baseinfo_onloan_amount') as bigint)  as baseinfo_onloan_amount
    ,json_extract_scalar(grantcredit_info, '$.if_regular_backup')  as if_regular_backup
    ,try_cast(json_extract(grantcredit_info,'$.hide_cut') as bigint) as hide_cut --0721 update

    ,cast(b.apply_amount/1000 as decimal)  as apply_amount 
    ,cast(b.approve_amount/1000 as decimal)  as approve_amount 
    ,to_char(date(b.create_time),'yyyy-mm-dd') as app_date
    ,to_char(date_trunc('week',date(b.create_time)),'yyyy-mm-dd') as app_week 
    ,to_char(date_trunc('month',date(b.create_time)),'yyyy-mm-dd') as app_month

    ,CASE WHEN c.cancel_time IS NOT NULL THEN 1 ELSE 0 END AS if_cancel 
    ,CASE WHEN d.camera_id IS NOT NULL THEN 1 ELSE 0 END AS if_issue  

    ,to_char(date(c.release_time),'yyyy-mm-dd') as issue_date
    ,to_char(date_trunc('week',date(c.release_time)),'yyyy-mm-dd') as issue_week 
    ,to_char(date_trunc('month',date(c.release_time)),'yyyy-mm-dd') as issue_month
    ,e.lender_name
    ,f.loop_credit_time
    ,case when f1.recall_biz_id is not null then 1 else 0 end as if_recall --拒绝后转产品标签
  from
  (
    select create_time
      ,to_char(date(create_time),'yyyy-mm-dd') as create_date
      ,to_char(date_trunc('week',date(create_time)),'yyyy-mm-dd') as create_week 
      ,to_char(date_trunc('month',date(create_time)),'yyyy-mm-dd') as create_month

      ,cust_id,identity,id,device_id,fpid
      ,mid,name,phone,tenant_id,app_channel,grantcredit_amount, risk_level,product_day
      ,grant_score
      ,product_level,grantcredit_info,new_grade_level,credit_asset_quality
      ,app_version
      ,loan_type
      ,if_backup_switch
      ,product_level_before
      ,product_level_after
    from ods.s09_os_credit_snapshot a2
    left join 
    (select biz_id,loan_type from ods.s09_os_credit_snapshot_extend ) a4 on a2.id = a4.biz_id --循环贷
    left join 
    (
      select biz_id
        ,1 as if_backup_switch
        ,cast(json_extract(grant_info_before,'$.product_level') as varchar)  as product_level_before
        ,cast(json_extract(grant_info_after,'$.product_level') as varchar)  as product_level_after
        ,row_number() over(partition by biz_id order by create_time desc) as rn
      from ods.s09_grant_product_switch_log --用信时转产品
    ) a5 on cast(a2.id as varchar) = cast(a5.biz_id as varchar) and a5.rn=1
  ) a 
  left join ind.xly_reloan_num a1 on a.id = a1.id
  left join
  (select customer_user_id, media_source as media_source_orig
    ,case 
    when platform = 'ios' and  media_source = 'Apple Search Ads' then 'ASA'
    when platform = 'ios' and  media_source = 'restricted' then 'IOS-fb'
    when platform = 'ios' and  media_source = 'Rupiah Cepat' then 'IOS-RC'
    when platform = 'ios' and  media_source = 'yupaamj_int' then 'IOS-yup'
    --when platform = 'ios' and  media_source = 'organic' then 'IOS-Organic'    
    when platform = 'ios'  then 'IOS-Organic'    
    when media_source='googleadwords_int' then 'Google'
    when media_source='Facebook Ads' or media_source='restricted' then 'Facebook'
    when media_source='organic' then 'Organic'
    when media_source = 'shareit_int' then 'Shareit'
    when media_source = 'kreditlist_int' or (media_source = 'vfine_int' and partner like '%redi%') or (media_source is null and partner = 'kreditlist') then 'kreditlist_int'
    when media_source = 'vfine_int' or media_source = 'adecentptuo_int' then 'Vfine'
    when media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
    when media_source = 'kwaiforbusiness_int' then 'Kwai'
    when media_source = 'cashcashpro' then 'cashcashpro'
    when media_source = 'cashcerdasid_int' then 'cashcerdas'
    when media_source = 'kredit pintal' then 'kp'
    when media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
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
    ,'digiwhisk_int','thanhdat_int','grandemedia_int') then 'Network union'
    when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int'
    ,'mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
    ,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') then 'rainbow'
    when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
    when campaign ='CookeAds_CPS' then 'CookeAds_CPS'
    when campaign ='CookeAds_CPI' then 'CookeAds_CPI'
    when partner = '19mobicn' then '19mobi'
    when campaign = 'Samire_Jan2025youmi' then 'youmi'
    when media_source ='yupaamj_int' then 'yup'
    when regexp_like(campaign, '^pp') then 'Novabeyond'
    else media_source end as media_source
    ,campaign as campaign_name
    ,case 
      when campaign like '%GP2%' then 'high_acquisition'
      when campaign='inhouse_samir_ID_20230412_Willys_Order_normal_test_1' then 'high_acquisition'
      when campaign like '%FB2%' and campaign<>'inhouse_FB2_samir_ID_20230504_Willys_cpx05_all_1' then 'high_acquisition'
      when (lower(campaign) like '%cpi%') or (lower(campaign) like '%install%')  then 'cpi'
      when lower(campaign) like '%cpr' then 'cpr'
      when (lower(campaign) like '%cpa%') or (lower(campaign) like '%apply%') then 'cpa'
      when lower(campaign) like '%cpq%' then 'cpq'
      when lower(campaign) like '%cps%' then 'cps'
      when lower(campaign) like '%cpx10%' then 'cpx10'
      when lower(campaign) like '%cpx09%' then 'cpx09'
      when lower(campaign) like '%cpx08%' then 'cpx08'
      when lower(campaign) like '%cpx07%' then 'cpx07'
      when lower(campaign) like '%cpx06%' then 'cpx06'
      when lower(campaign) like '%cpx05%' then 'cpx05'
      when lower(campaign) like '%cpx04%' then 'cpx04'
      when lower(campaign) like '%cpx03%' then 'cpx03'
      when lower(campaign) like '%cpx02%' then 'cpx02'
      when lower(campaign) like '%cpx01%' then 'cpx01'
      when lower(campaign) like '%cpk%' then 'cpk'
    else 'non-type' end as objective   
    ,row_number() over (partition by customer_user_id  order by event_time) as event_rn
  from ods.s08_appsflyer_push_data -- 投放（记录埋点）
  where event_name = 'Sign_in_success_new'
  )a2 on CAST(a.mid AS VARCHAR)= cast(a2.customer_user_id as VARCHAR) and event_rn=1
  left join 



  -- 这里没有落数仓；
  (SELECT * FROM ods.s05_creditx_order WHERE DATE(CREATE_TIME) >= DATE'2022-07-01')b on cast(a.id as varchar)= b.biz_id 
  left join 
  (SELECT did, interval_start FROM ods.s03_product_due ) b1 --用信产品期限
  on b.apply_period = cast(b1.did as varchar)
  left join 
  (select biz_id , is_reloan2 ,baseinfo_onloan_hit_mid from ind.xly_reloan_num2) b2 on cast(a.id as varchar) = b2.biz_id 
  left join ods.s02_loan c on cast(a.id as varchar) = cast(ceil(c.camera_id) as varchar) 
  left join 
  (select distinct camera_id from ods.s02_loan_repayment where state!=7 ) d --还款信息（放款必定成功）
  on cast(a.id as varchar) = cast(ceil(d.camera_id) as varchar) 
  left join
  (
    select 
      camera_id
      ,case 
        when lend_customer_id = 10001 then 'JET'  
        when lend_customer_id = 10002 then 'JAYA' 
        when lend_customer_id = 10010 then 'BNC' 
        when lend_customer_id in (10012,10014) then 'WESHARE' --0625update
        when lend_customer_id = 10003 then 'TELKO'
        when lend_customer_id = 10013 then 'GEERONG'
        when lend_customer_id = 10015 then 'Finovary' --0807update
      end as lender_name
    from ods.s02_lend where state in (3) --资方信息
  ) e on cast(a.id as varchar) = cast(ceil(e.camera_id) as varchar) 
  left join 
  (
    select a.biz_id,max(b.create_time ) as loop_credit_time --最近一次循环贷授信时间
    from ods.s05_creditx_order a 
    left join ods.s22_circular_quota_whitelist_log b on cast(a.mid as bigint)= b.mid and a.create_time >b.create_time
    group by 1 
  ) f on b.biz_id = f.biz_id
  left join 
  (
      select 
        mid 
        , recall_biz_id
      from ods.s09_tiny_flow_record 
      where product_code = 'SWITCH_AFTERREJECTED_PROD'
      and output is not null
      and cast(json_extract(output,'$.if_recall') as bigint) = 1
      and recall_biz_id is not null 
      and date(create_time) >= date'2025-05-19'
  ) f1 on b.biz_id = cast(f1.recall_biz_id as varchar) --拒绝后转产品
  ;

--TABLE 5:ind.xly_application_funnel_2
drop table if exists ind.xly_application_funnel_2;
create table  ind.xly_application_funnel_2 as

  SELECT 
    B.BIZ_ID
    ,if_in_anti_fraud 
    ,if_anti_fraud_passed
    ,if_anti_fraud_refused
    ,if_in_anti_fraud_weak  
    ,if_anti_fraud_weak_passed
    ,if_anti_fraud_weak_refused
    ,if_in_model  
    ,if_model_passed 
    ,if_model_refused
    ,if_in_confirm 
    ,if_confirm_passed 
    ,if_confirm_refused
    ,confirm_time 
    ,confirm_date
    ,if_in_AI
    ,if_AI_passed
    ,if_in_manual_check --人审打标
    ,if_manual_divide_passed
    ,if_manual_divide_refused
    ,if_in_manual_check_1 
    ,if_manual_check_1_passed
    ,if_manual_check_1_refused
    ,if_manual_check_1_canceled
    ,if_in_manual_check_2 --人审决策
    ,if_manual_check_2_passed
    ,if_manual_check_2_refused
    ,if_manual_check_2_canceled
    ,if_in_external_data_1  
    ,if_external_data_1_passed
    ,if_external_data_1_refused
    ,if_in_external_data_2 
    ,if_external_data_2_passed
    ,if_external_data_2_refused
    ,if_in_external_data_pre2  
    ,if_external_data_pre2_passed
    ,if_external_data_pre2_refused
    ,if_in_external_data_3  
    ,if_external_data_3_passed
    ,if_external_data_3_refused
    ,if_in_external_data_4  
    ,if_external_data_4_passed
    ,if_external_data_4_refused
    ,pass_time
    ,pass_date
  FROM (SELECT DISTINCT BIZ_ID,status,double_loan FROM ods.s05_creditx_order) b 
  left join
  (
    SELECT distinct
      biz_id, 
      1 as if_in_anti_fraud,
      case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as if_anti_fraud_passed,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_anti_fraud_refused
    FROM  ods.s05_creditx_processor_record 
    where lower(current_processor) in ('first_loan_strong_rule_set','reloan_strong_rule_set','plus_strong_rule_set','plus_strong_rule_set_circ','m_plus_strong_rule_set'
    ,'first_loan_strong_rule_set_ios','reloan_strong_rule_set_ios','plus_strong_rule_set_ios','m_strong_rule_set')
    group by 1 
  )p1 on b.biz_id = p1.biz_id
  left join
  (
    SELECT distinct
      biz_id,
      1 as if_in_anti_fraud_weak,
      case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as if_anti_fraud_weak_passed,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_anti_fraud_weak_refused
    FROM  ods.s05_creditx_processor_record 
    where lower(current_processor) in ('first_loan_weak_rule_set','reloan_weak_rule_set','plus_weak_rule_set','plus_weak_rule_set_circ','m_plus_weak_rule_set'
    ,'first_loan_weak_rule_set_ios','reloan_weak_rule_set_ios','plus_weak_rule_set_ios','m_weak_rule_set')
    group by 1 
  )p3 on b.biz_id = p3.biz_id
  left join
  (
    SELECT distinct
      biz_id,
      1 as if_in_model,
      case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as if_model_passed,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_model_refused
    FROM  ods.s05_creditx_processor_record 
    where lower(current_processor) in ('first_loan_model_score_set','reloan_model_score_set','plus_model_score_set','plus_model_score_set_circ','m_plus_model_score_set'
    ,'first_loan_model_score_set_ios','reloan_model_score_set_ios','plus_model_score_set_ios','m_model_score_set','single_model_score_set')
    group by 1 
  )p5 on b.biz_id = p5.biz_id
  left join 
  (  
    SELECT  
      biz_id
      ,1 as if_in_confirm
      ,case when (sum(case when approve_result='PASSED' then 1 end))>=1 then 1 else 0 end as if_confirm_passed
      ,case when (sum(case when approve_result!='PASSED' then 1 end))>=1 then 1 else 0 end as if_confirm_refused
      ,max(case when approve_result='PASSED' then update_time else null end ) as confirm_time
      ,max(case when approve_result='PASSED' then date(update_time) else null end ) as confirm_date
    FROM  ods.s05_creditx_processor_record 
    where lower(current_processor) in ('confirm','confirm_ios')
    group by 1
  )p6 on b.biz_id = p6.biz_id
  left join
  (
    select biz_id, 1 as if_in_AI
    ,case when (sum(case when approve_result='PASSED' then 1 end))>=1 then 1 else 0 end as  if_AI_passed
    FROM ods.s05_creditx_processor_record 
    where current_processor in ('AI') group by 1
)p15 on b.biz_id = p15.biz_id
  left join
  (
    SELECT 
      biz_id, 1 as if_in_manual_check,
      case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as if_manual_divide_passed,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_manual_divide_refused
    FROM  ods.s05_creditx_processor_record 
    where lower(current_processor) in ('first_loan_manual_divide_ios','first_loan_manual_divide','reloan_manual_divide','plus_manual_divide')
    group by 1
)p14 on b.biz_id = p14.biz_id
  left join
  (
    SELECT distinct
      biz_id,  1 as if_in_manual_check_1,
      case when (sum(case when approve_result='REFUSED' then 1 end)) is null and (sum(case when approve_result='CANCELED' then 1 end)) is null then 1 else 0 end as if_manual_check_1_passed, 
      case when (sum(case when approve_result='CANCELED' then 1 end))>=1 then 1 else 0 end as if_manual_check_1_canceled,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as  if_manual_check_1_refused
    FROM  ods.s05_creditx_processor_record 
    where lower(current_processor) in ('first_loan_manual_first','reloan_manual_first') 
    group by 1
  )p7 on b.biz_id = p7.biz_id
  left join
  (
    SELECT distinct
      biz_id,  1 as if_in_manual_check_2,
      case when (sum(case when approve_result='REFUSED' then 1 end)) is null and (sum(case when approve_result='CANCELED' then 1 end)) is null then 1 else 0 end as if_manual_check_2_passed, 
      case when (sum(case when approve_result='CANCELED' then 1 end))>=1 then 1 else 0 end as if_manual_check_2_canceled,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as  if_manual_check_2_refused
    FROM  ods.s05_creditx_processor_record 
    where lower(current_processor) in ('first_loan_manual_second','reloan_manual_second','first_loan_manual_flag_decision','reloan_manual_flag_decision'
    ,'first_loan_manual_flag_decision_ios')
    group by 1
  )p8 on b.biz_id = p8.biz_id   
  left join
  (
    SELECT distinct
      biz_id, 1 as if_in_external_data_1
      ,case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as  if_external_data_1_passed
      ,case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as  if_external_data_1_refused
    FROM  ods.s05_creditx_processor_record
    where lower(current_processor) in ('first_loan_external_data1_set','reloan_external_data1_set','plus_external_data1_set','plus_external_data1_set_circ','m_plus_external_data1_set'
    ,'first_loan_external_data1_set_ios','reloan_external_data1_set_ios','plus_external_data1_set_ios','m_external_data1_set') 
    group by 1 
  ) p9 on b.biz_id = p9.biz_id
  left join
  (
    SELECT distinct
      biz_id, 1 as if_in_external_data_pre2
      ,case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as  if_external_data_pre2_passed
      ,case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as  if_external_data_pre2_refused
    FROM  ods.s05_creditx_processor_record
    where lower(current_processor) in ('first_loan_external_datapre2_set','reloan_external_datapre2_set','plus_external_datapre2_set','plus_external_datapre2_set_circ','m_plus_external_datapre2_set'
    ,'first_loan_external_datapre2_set_ios','reloan_external_datapre2_set_ios','plus_external_datapre2_set_ios','m_external_datapre2_set') 
    group by 1 
  ) p10 on b.biz_id = p10.biz_id

  (
    SELECT distinct
      biz_id, 1 as if_in_external_data_2
      ,case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as  if_external_data_2_passed
      ,case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as  if_external_data_2_refused
    FROM  ods.s05_creditx_processor_record
    where lower(current_processor) in ('first_loan_external_data2_set','reloan_external_data2_set','plus_external_data2_set','plus_external_data2_set_circ','m_plus_external_data2_set'
    ,'first_loan_external_data2_set_ios','reloan_external_data2_set_ios','plus_external_data2_set_ios','m_external_data2_set') 
    group by 1 
  ) p11 on b.biz_id = p11.biz_id
  left join
  (
    SELECT distinct
      biz_id, 1 as if_in_external_data_3
      ,case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as  if_external_data_3_passed
      ,case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as  if_external_data_3_refused
    FROM  ods.s05_creditx_processor_record
    where lower(current_processor) in ('first_loan_external_data3_set','reloan_external_data3_set','plus_external_data3_set','plus_external_data3_set_circ','m_plus_external_data3_set'
    ,'first_loan_external_data3_set_ios','reloan_external_data3_set_ios','plus_external_data3_set_ios','m_external_data3_set') 
    group by 1 
  ) p12 on b.biz_id = p12.biz_id
  left join
  (
    SELECT distinct
      biz_id, 1 as if_in_external_data_4
      ,case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as  if_external_data_4_passed
      ,case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as  if_external_data_4_refused
    FROM  ods.s05_creditx_processor_record
    where lower(current_processor) in ('first_loan_external_data4_set','reloan_external_data4_set','plus_external_data4_set','plus_external_data4_set_circ','m_plus_exteranl_data4_set'
    ,'first_loan_external_data4_set_ios','reloan_external_data4_set_ios','plus_external_data4_set_ios','m_external_data4_set') 
    group by 1 
  ) p13 on b.biz_id = p13.biz_id
  left join 
  (
    select
      biz_id,min(create_time) as pass_time,date(min(create_time)) as pass_date
    FROM ods.s05_creditx_processor_record 
    where current_processor in ('fundRouting','loan')
    group by 1
  ) p17 on b.biz_id = p17.biz_id
  ; 

--TABLE 6:ind.xly_application_funnel_overdue_p1
drop table if exists ind.xly_application_funnel_overdue_p1;  
create table  ind.xly_application_funnel_overdue_p1 as

  select 
    d.camera_id as camera_id1
    ,d.state as repayment_state_p1 
    ,date(d.should_time) as deadline_p1 
    ,d.should_time as should_time_p1 
    ,d.fact_time as fact_time_p1 
    ,d.should_capital as should_capital_p1 
    ,d.fact_capital as fact_capital_p1 
    ,d.should_interest as should_interest_p1 
    ,d.fact_interest as fact_interest_p1 
    ,d.should_fine as should_fine_p1 
    ,d.fact_fine as fact_fine_p1
    ,cast(d.should_capital as decimal) + cast(d.should_interest as decimal) as should_amount_p1 
    ,cast(d.fact_capital as decimal) + cast(d.fact_interest as decimal) as repay_amount_p1 
    ,d.overdue_days as overdue_days_p1
    ,case when date_diff('day',date(d.fact_time),date(d.should_time))>4 then cast(d.fact_capital as decimal) else 0 end as pre_p4_repay_p1
    ,case when date_diff('day',date(d.fact_time),date(d.should_time))=4 then cast(d.fact_capital as decimal) else 0 end as p4_repay_p1
    ,case when date_diff('day',date(d.fact_time),date(d.should_time))=3 then cast(d.fact_capital as decimal) else 0 end as p3_repay_p1
    ,case when date_diff('day',date(d.fact_time),date(d.should_time))=2 then cast(d.fact_capital as decimal) else 0 end as p2_repay_p1
    ,case when date_diff('day',date(d.fact_time),date(d.should_time))=1 then cast(d.fact_capital as decimal) else 0 end as p1_repay_p1
    ,case when date_diff('day',date(d.fact_time),date(d.should_time))=0 then cast(d.fact_capital as decimal) else 0 end as p0_repay_p1

    ,case when date_diff('day',date(d.fact_time),date(d.should_time))=-1 then cast(d.fact_capital as decimal) else 0 end as t1_repay_p1
    ,case when date_diff('day',date(d.fact_time),date(d.should_time))=-2 then cast(d.fact_capital as decimal) else 0 end as t2_repay_p1
    ,case when date_diff('day',date(d.fact_time),date(d.should_time))=-3 then cast(d.fact_capital as decimal) else 0 end as t3_repay_p1

    ,case when date_diff('day',date(d.should_time),CURRENT_DATE)>-1 then 1 else 0 end as is_p1_window_p1
    ,case when date_diff('day',date(d.should_time),CURRENT_DATE)>-2 then 1 else 0 end as is_p2_window_p1
    ,case when date_diff('day',date(d.should_time),CURRENT_DATE)>-3 then 1 else 0 end as is_p3_window_p1
    ,case when date_diff('day',date(d.should_time),CURRENT_DATE)>-4 then 1 else 0 end as is_p4_window_p1

    ,case when date_diff('day',date(d.should_time),CURRENT_DATE)>0 then 1 else 0 end as is_t0_window_p1
    ,CASE WHEN d.overdue_days > 0 THEN 1 ELSE 0 END AS IS_T0_OVERDUE_p1
    ,CASE 
    WHEN d.overdue_days <= 0 THEN 0
    WHEN d.overdue_days > 0 AND date_diff('day',date(d.should_time),date(d.fact_time)) <= 0 THEN cast(d.should_capital as decimal)-cast(d.fact_capital as decimal) 
    WHEN d.overdue_days > 0 AND (date_diff('day',date(d.should_time),date(d.fact_time)) > 0 OR date(d.fact_time) IS NULL) THEN cast(d.should_capital as decimal)
    else 0 END AS T0_OVERDUE_AMOUNT_p1

    ,case when date_diff('day',date(d.should_time),CURRENT_DATE)>1 then 1 else 0 end as is_t1_window_p1
    ,CASE WHEN d.overdue_days > 1 THEN 1 ELSE 0 END AS IS_T1_OVERDUE_p1
    ,CASE 
    WHEN d.overdue_days <= 1 THEN 0
    WHEN d.overdue_days > 1 AND date_diff('day',date(d.should_time),date(d.fact_time)) <= 1 THEN cast(d.should_capital as decimal)-cast(d.fact_capital as decimal) 
    WHEN d.overdue_days > 1 AND (date_diff('day',date(d.should_time),date(d.fact_time)) > 1 OR date(d.fact_time) IS NULL) THEN cast(d.should_capital as decimal)
    else 0 END AS T1_OVERDUE_AMOUNT_p1

    ,case when date_diff('day',date(d.should_time),CURRENT_DATE)>2 then 1 else 0 end as is_t2_window_p1
    ,CASE WHEN d.overdue_days > 2 THEN 1 ELSE 0 END AS IS_T2_OVERDUE_p1
    ,CASE 
    WHEN d.overdue_days <= 2 THEN 0
    WHEN d.overdue_days > 2 AND date_diff('day',date(d.should_time),date(d.fact_time)) <= 2 THEN cast(d.should_capital as decimal)-cast(d.fact_capital as decimal) 
    WHEN d.overdue_days > 2 AND (date_diff('day',date(d.should_time),date(d.fact_time)) > 2 OR date(d.fact_time) IS NULL) THEN cast(d.should_capital as decimal)
    else 0 END AS T2_OVERDUE_AMOUNT_p1

    ,case when date_diff('day',date(d.should_time),CURRENT_DATE)>3 then 1 else 0 end as is_t3_window_p1
    ,CASE WHEN d.overdue_days > 3 THEN 1 ELSE 0 END AS IS_T3_OVERDUE_p1
    ,CASE 
    WHEN d.overdue_days <= 3 THEN 0
    WHEN d.overdue_days > 3 AND date_diff('day',date(d.should_time),date(d.fact_time)) <= 3 THEN cast(d.should_capital as decimal)-cast(d.fact_capital as decimal) 
    WHEN d.overdue_days > 3 AND (date_diff('day',date(d.should_time),date(d.fact_time)) > 3 OR date(d.fact_time) IS NULL) THEN cast(d.should_capital as decimal)
    else 0 END AS T3_OVERDUE_AMOUNT_p1

    ,case when date_diff('day',date(d.should_time),CURRENT_DATE)>7 then 1 else 0 end as is_t7_window_p1
    ,CASE WHEN d.overdue_days > 7 THEN 1 ELSE 0 END AS IS_T7_OVERDUE_p1
    ,CASE 
    WHEN d.overdue_days <= 7 THEN 0
    WHEN d.overdue_days > 7 AND date_diff('day',date(d.should_time),date(d.fact_time)) <= 7 THEN cast(d.should_capital as decimal)-cast(d.fact_capital as decimal) 
    WHEN d.overdue_days > 7 AND (date_diff('day',date(d.should_time),date(d.fact_time)) > 7 OR date(d.fact_time) IS NULL) THEN cast(d.should_capital as decimal)
    else 0 END AS T7_OVERDUE_AMOUNT_p1

    ,case when date_diff('day',date(d.should_time),CURRENT_DATE)>14 then 1 else 0 end as is_t14_window_p1
    ,CASE WHEN d.overdue_days > 14 THEN 1 ELSE 0 END AS IS_T14_OVERDUE_p1
    ,CASE 
    WHEN d.overdue_days <= 14 THEN 0
    WHEN d.overdue_days > 14 AND date_diff('day',date(d.should_time),date(d.fact_time)) <= 14 THEN cast(d.should_capital as decimal)-cast(d.fact_capital as decimal) 
    WHEN d.overdue_days > 14 AND (date_diff('day',date(d.should_time),date(d.fact_time)) > 14 OR date(d.fact_time) IS NULL) THEN cast(d.should_capital as decimal)
    else 0 END AS T14_OVERDUE_AMOUNT_p1

    ,case when date_diff('day',date(d.should_time),CURRENT_DATE)>30 then 1 else 0 end as is_t30_window_p1
    ,CASE WHEN d.overdue_days > 30 THEN 1 ELSE 0 END AS IS_T30_OVERDUE_p1
    ,CASE 
    WHEN d.overdue_days <= 30 THEN 0
    WHEN d.overdue_days > 30 AND date_diff('day',date(d.should_time),date(d.fact_time)) <= 30 THEN cast(d.should_capital as decimal)-cast(d.fact_capital as decimal) 
    WHEN d.overdue_days > 30 AND (date_diff('day',date(d.should_time),date(d.fact_time)) > 30 OR date(d.fact_time) IS NULL) THEN cast(d.should_capital as decimal)
    else 0 END AS T30_OVERDUE_AMOUNT_p1

    , case when d.overdue_days <= 0 then 0
    when d.overdue_days > 0 and date_diff('day',date(d.should_time),date(d.fact_time)) <= 0 then cast(d.should_interest as decimal)-cast(d.fact_interest as decimal) 
    when d.overdue_days > 0 and (date_diff('day',date(d.should_time),date(d.fact_time)) > 0 or date(d.fact_time) is null) then cast(d.should_interest as decimal)
    else 0 
    end as t0_overdue_interest_p1

    , case when d.overdue_days <= 7 then 0
    when d.overdue_days > 7 and date_diff('day',date(d.should_time),date(d.fact_time)) <= 7 then cast(d.should_interest as decimal)-cast(d.fact_interest as decimal) 
    when d.overdue_days > 7 and (date_diff('day',date(d.should_time),date(d.fact_time)) > 7 or date(d.fact_time) is null) then cast(d.should_interest as decimal)
    else 0 
    end as t7_overdue_interest_p1

    , case when d.overdue_days <= 30 then 0
    when d.overdue_days > 30 and date_diff('day',date(d.should_time),date(d.fact_time)) <= 30 then cast(d.should_interest as decimal)-cast(d.fact_interest as decimal) 
    when d.overdue_days > 30 and (date_diff('day',date(d.should_time),date(d.fact_time)) > 30 or date(d.fact_time) is null) then cast(d.should_interest as decimal)
    else 0 
    end as t30_overdue_interest_p1
  from 
  (
    select distinct 
      * 
      ,case when state = 1 then 0
      when state in (3,5) or (state=6 and should_capital<=fact_capital) then date_diff('day',date(should_time),date(fact_time))
      else date_diff('day',date(should_time),date(CURRENT_DATE)) end as overdue_days  
    from ods.s02_loan_repayment where state!=7 and indexs =1
  ) d 
  ;

--TABLE 7:ind.xly_application_funnel_overdue_middle
drop table if exists ind.xly_application_funnel_overdue_middle;  
create table  ind.xly_application_funnel_overdue_middle as

  select 
    a.camera_id, T0_date, T7_date, T14_date, T30_date
    ,sum( case when date(fact_time)<=T0_date then  fact_capital else 0 end) as t0_fact_capital
    ,sum( case when date(fact_time)<=T7_date then  fact_capital else 0 end) as t7_fact_capital
    ,sum( case when date(fact_time)<=T14_date then  fact_capital else 0 end) as t14_fact_capital
    ,sum( case when date(fact_time)<=T30_date then  fact_capital else 0 end) as t30_fact_capital
  from 
  (select camera_id,loan_indexs from ods.s02_loan) a 
  left join 
  (
    select 
      camera_id
      ,indexs
      ,should_time 
      ,date_add('day',0,date(should_time)) as T0_date
      ,date_add('day',7,date(should_time)) as T7_date
      ,date_add('day',14,date(should_time)) as T14_date
      ,date_add('day',30,date(should_time)) as T30_date
    from ods.s02_loan_repayment 
    where state!=7 
  ) b on a.camera_id = b.camera_id and a.loan_indexs = b.indexs
  left join 
  (
    select camera_id, fact_time, fact_capital
    from ods.s02_loan_repayment 
    where state!=7 
  ) c on a.camera_id = c.camera_id 
  group by 1,2,3,4,5
  ;

--TABLE 8:ind.xly_application_funnel_overdue_all
drop table if exists ind.xly_application_funnel_overdue_all;  
create table  ind.xly_application_funnel_overdue_all as

  select 
    camera_id as camera_id
    ,should_capital + should_interest as should_amount
    ,should_capital
    ,should_interest
    ,fact_capital + fact_interest as repay_amount
    , fact_capital 
    , fact_interest
    , fact_time
    ,date(should_time) as deadline
    ,case when date_diff('day',date(should_time),CURRENT_DATE)>0 then 1 else 0 end as is_t0_window
    ,CASE WHEN overdue_days > 0 THEN 1 ELSE 0 END AS IS_T0_OVERDUE
    ,CASE 
    WHEN overdue_days <= 0 THEN 0
    WHEN overdue_days > 0  THEN cast(should_capital as decimal)-cast(t0_fact_capital as decimal) 
    else 0 END AS T0_OVERDUE_AMOUNT

    ,case when date_diff('day',date(should_time),CURRENT_DATE)>7 then 1 else 0 end as is_t7_window
    ,CASE WHEN overdue_days > 7 THEN 1 ELSE 0 END AS IS_T7_OVERDUE
    ,CASE 
    WHEN overdue_days <= 7 THEN 0
    WHEN overdue_days > 7  THEN cast(should_capital as decimal)-cast(t7_fact_capital as decimal) 
    else 0 END AS T7_OVERDUE_AMOUNT

    ,case when date_diff('day',date(should_time),CURRENT_DATE)>14 then 1 else 0 end as is_t14_window
    ,CASE WHEN overdue_days > 14 THEN 1 ELSE 0 END AS IS_T14_OVERDUE
    ,CASE 
    WHEN overdue_days <= 14 THEN 0
    WHEN overdue_days > 14  THEN cast(should_capital as decimal)-cast(t14_fact_capital as decimal) 
    else 0 END AS T14_OVERDUE_AMOUNT

    ,case when date_diff('day',date(should_time),CURRENT_DATE)>30 then 1 else 0 end as is_t30_window  
    ,CASE WHEN overdue_days > 30 THEN 1 ELSE 0 END AS IS_T30_OVERDUE
    ,CASE 
    WHEN overdue_days <= 30 THEN 0
    WHEN overdue_days > 30 THEN cast(should_capital as decimal)-cast(t30_fact_capital as decimal) 
    else 0 END AS T30_OVERDUE_AMOUNT
  from
  (
    select a.camera_id
      ,should_capital ,should_interest, fact_capital ,fact_fine, fact_interest
      ,should_time, fact_time ,state 
      ,t0_fact_capital,t7_fact_capital,t14_fact_capital,t30_fact_capital
      ,case when state=1 then 0
      when state in (3,5) or (state=6 and should_capital<=fact_capital) then date_diff('day',date(should_time),date(fact_time))
      else date_diff('day',date(should_time),date(CURRENT_DATE))
      end as overdue_days  
    from (select camera_id,loan_indexs from ods.s02_loan) a 
    left join 
    (
      select camera_id
        ,sum(cast(should_capital as decimal)) as should_capital 
        ,sum(cast(fact_capital as decimal)) as fact_capital 
        ,sum(cast(fact_fine as decimal)) as fact_fine 
        ,sum(cast(fact_interest as decimal)) as fact_interest
        ,sum(cast(should_interest as decimal )) as should_interest 
      from ods.s02_loan_repayment 
      where state!=7 
      group by 1
    ) b on a.camera_id = b.camera_id
    left join 
    (
      select 
        camera_id
        ,indexs
        ,should_time 
        ,fact_time  
        ,state 
      from ods.s02_loan_repayment 
      where state!=7 
    ) c on a.camera_id = c.camera_id and a.loan_indexs = c.indexs
    left join 
    (select * from   ind.xly_application_funnel_overdue_middle) d on a.camera_id = d.camera_id
  );

--TABLE 9:ind.xly_vintage_1
drop table if exists ind.xly_vintage_1;
create table ind.xly_vintage_1 as
  select 
    camera_id
    , r.should_time 
    , r.indexs 
    , if(date_diff('day', date(r.should_time), current_date) > 0, 1, 0) as due0_flag
    , if(date_diff('day', date(r.should_time), if(r.fact_time is null, current_date, date(r.fact_time))) > 0, 1, 0) as ovd0_flag
    , if(date_diff('day', date(r.should_time), current_date) > 3, 1, 0) as due3_flag
    , if(date_diff('day', date(r.should_time), if(r.fact_time is null, current_date, date(r.fact_time))) > 3, 1, 0) as ovd3_flag
    , if(date_diff('day', date(r.should_time), current_date) > 7, 1, 0) as due7_flag
    , if(date_diff('day', date(r.should_time), if(r.fact_time is null, current_date, date(r.fact_time))) > 7, 1, 0) as ovd7_flag
    , if(date_diff('day', date(r.should_time), current_date) > 14, 1, 0) as due14_flag
    , if(date_diff('day', date(r.should_time), if(r.fact_time is null, current_date, date(r.fact_time))) > 14, 1, 0) as ovd14_flag
    , if(date_diff('day', date(r.should_time), current_date) > 15, 1, 0) as due15_flag
    , if(date_diff('day', date(r.should_time), if(r.fact_time is null, current_date, date(r.fact_time))) > 15, 1, 0) as ovd15_flag
    , if(date_diff('day', date(r.should_time), current_date) > 30, 1, 0) as due30_flag
    , if(date_diff('day', date(r.should_time), if(r.fact_time is null, current_date, date(r.fact_time))) > 30, 1, 0) as ovd30_flag
  from ods.s02_loan_repayment r 
  ;

--TABLE 10:ind.xly_vintage_2
drop table if exists ind.xly_vintage_2;
create table ind.xly_vintage_2 as
  select 
    t1.camera_id
    , t1.should_time 
    , t1.indexs 
    , due0_flag, ovd0_flag
    , due3_flag, ovd3_flag
    , due7_flag, ovd7_flag
    , due14_flag, ovd14_flag
    , due15_flag, ovd15_flag
    , due30_flag, ovd30_flag
    , sum(case when date_diff('day', date(t1.should_time), date(rd.fact_time)) <= 0 then rd.fact_capital else 0 end) as repay_t0_amt_all 
    , sum(case when date_diff('day', date(t1.should_time), date(rd.fact_time)) <= 3 then rd.fact_capital else 0 end) as repay_t3_amt_all 
    , sum(case when date_diff('day', date(t1.should_time), date(rd.fact_time)) <= 7 then rd.fact_capital else 0 end) as repay_t7_amt_all 
    , sum(case when date_diff('day', date(t1.should_time), date(rd.fact_time)) <= 14 then rd.fact_capital else 0 end) as repay_t14_amt_all 
    , sum(case when date_diff('day', date(t1.should_time), date(rd.fact_time)) <= 15 then rd.fact_capital else 0 end) as repay_t15_amt_all 
    , sum(case when date_diff('day', date(t1.should_time), date(rd.fact_time)) <= 30 then rd.fact_capital else 0 end) as repay_t30_amt_all 
  from ind.xly_vintage_1 t1
  left join ods.s02_loan_repayment_detail rd on rd.camera_id = t1.camera_id
  group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
  ;

--TABLE 11:ind.xly_vintage_3
drop table if exists ind.xly_vintage_3;
create table ind.xly_vintage_3 as
  select 
    camera_id as camera_id3
    , max(case when indexs = 1 then due0_flag else 0 end) as should_cnt_1_0
    , max(case when indexs = 2 then due0_flag else 0 end) as should_cnt_2_0
    , max(case when indexs = 3 then due0_flag else 0 end) as should_cnt_3_0
    , max(case when indexs = 4 then due0_flag else 0 end) as should_cnt_4_0
    , max(case when indexs = 5 then due0_flag else 0 end) as should_cnt_5_0
    , max(case when indexs = 6 then due0_flag else 0 end) as should_cnt_6_0
    , max(case when indexs = 7 then due0_flag else 0 end) as should_cnt_7_0
    , max(case when indexs = 8 then due0_flag else 0 end) as should_cnt_8_0
    , max(case when indexs = 9 then due0_flag else 0 end) as should_cnt_9_0
    , max(case when indexs = 10 then due0_flag else 0 end) as should_cnt_10_0

    , max(case when indexs = 1 then due3_flag else 0 end) as should_cnt_1_3
    , max(case when indexs = 2 then due3_flag else 0 end) as should_cnt_2_3
    , max(case when indexs = 3 then due3_flag else 0 end) as should_cnt_3_3
    , max(case when indexs = 4 then due3_flag else 0 end) as should_cnt_4_3
    , max(case when indexs = 5 then due3_flag else 0 end) as should_cnt_5_3
    , max(case when indexs = 6 then due3_flag else 0 end) as should_cnt_6_3
    , max(case when indexs = 7 then due3_flag else 0 end) as should_cnt_7_3
    , max(case when indexs = 8 then due3_flag else 0 end) as should_cnt_8_3
    , max(case when indexs = 9 then due3_flag else 0 end) as should_cnt_9_3
    , max(case when indexs = 10 then due3_flag else 0 end) as should_cnt_10_3  

    , max(case when indexs = 1 then due7_flag else 0 end) as should_cnt_1_7
    , max(case when indexs = 2 then due7_flag else 0 end) as should_cnt_2_7
    , max(case when indexs = 3 then due7_flag else 0 end) as should_cnt_3_7
    , max(case when indexs = 4 then due7_flag else 0 end) as should_cnt_4_7
    , max(case when indexs = 5 then due7_flag else 0 end) as should_cnt_5_7
    , max(case when indexs = 6 then due7_flag else 0 end) as should_cnt_6_7
    , max(case when indexs = 7 then due7_flag else 0 end) as should_cnt_7_7
    , max(case when indexs = 8 then due7_flag else 0 end) as should_cnt_8_7
    , max(case when indexs = 9 then due7_flag else 0 end) as should_cnt_9_7  
    , max(case when indexs = 10 then due7_flag else 0 end) as should_cnt_10_7  

    , max(case when indexs = 1 then due15_flag else 0 end) as should_cnt_1_15
    , max(case when indexs = 2 then due15_flag else 0 end) as should_cnt_2_15
    , max(case when indexs = 3 then due15_flag else 0 end) as should_cnt_3_15
    , max(case when indexs = 4 then due15_flag else 0 end) as should_cnt_4_15
    , max(case when indexs = 5 then due15_flag else 0 end) as should_cnt_5_15
    , max(case when indexs = 6 then due15_flag else 0 end) as should_cnt_6_15
    , max(case when indexs = 7 then due15_flag else 0 end) as should_cnt_7_15
    , max(case when indexs = 8 then due15_flag else 0 end) as should_cnt_8_15
    , max(case when indexs = 9 then due15_flag else 0 end) as should_cnt_9_15  
    , max(case when indexs = 10 then due15_flag else 0 end) as should_cnt_10_15

    , max(case when indexs = 1 then due30_flag else 0 end) as should_cnt_1_30
    , max(case when indexs = 2 then due30_flag else 0 end) as should_cnt_2_30
    , max(case when indexs = 3 then due30_flag else 0 end) as should_cnt_3_30
    , max(case when indexs = 4 then due30_flag else 0 end) as should_cnt_4_30
    , max(case when indexs = 5 then due30_flag else 0 end) as should_cnt_5_30
    , max(case when indexs = 6 then due30_flag else 0 end) as should_cnt_6_30
    , max(case when indexs = 7 then due30_flag else 0 end) as should_cnt_7_30
    , max(case when indexs = 8 then due30_flag else 0 end) as should_cnt_8_30
    , max(case when indexs = 9 then due30_flag else 0 end) as should_cnt_9_30
    , max(case when indexs = 10 then due30_flag else 0 end) as should_cnt_10_30    

    , max(case when indexs = 1 then ovd0_flag else 0 end) as overdue_cnt_1_0
    , max(case when indexs = 2 then ovd0_flag else 0 end) as overdue_cnt_2_0
    , max(case when indexs = 3 then ovd0_flag else 0 end) as overdue_cnt_3_0
    , max(case when indexs = 4 then ovd0_flag else 0 end) as overdue_cnt_4_0
    , max(case when indexs = 5 then ovd0_flag else 0 end) as overdue_cnt_5_0
    , max(case when indexs = 6 then ovd0_flag else 0 end) as overdue_cnt_6_0
    , max(case when indexs = 7 then ovd0_flag else 0 end) as overdue_cnt_7_0
    , max(case when indexs = 8 then ovd0_flag else 0 end) as overdue_cnt_8_0
    , max(case when indexs = 9 then ovd0_flag else 0 end) as overdue_cnt_9_0
    , max(case when indexs = 10 then ovd0_flag else 0 end) as overdue_cnt_10_0
    
    , max(case when indexs = 1 then ovd3_flag else 0 end) as overdue_cnt_1_3
    , max(case when indexs = 2 then ovd3_flag else 0 end) as overdue_cnt_2_3
    , max(case when indexs = 3 then ovd3_flag else 0 end) as overdue_cnt_3_3
    , max(case when indexs = 4 then ovd3_flag else 0 end) as overdue_cnt_4_3
    , max(case when indexs = 5 then ovd3_flag else 0 end) as overdue_cnt_5_3
    , max(case when indexs = 6 then ovd3_flag else 0 end) as overdue_cnt_6_3
    , max(case when indexs = 7 then ovd3_flag else 0 end) as overdue_cnt_7_3
    , max(case when indexs = 8 then ovd3_flag else 0 end) as overdue_cnt_8_3
    , max(case when indexs = 9 then ovd3_flag else 0 end) as overdue_cnt_9_3  
    , max(case when indexs = 10 then ovd3_flag else 0 end) as overdue_cnt_10_3  

    , max(case when indexs = 1 then ovd7_flag else 0 end) as overdue_cnt_1_7
    , max(case when indexs = 2 then ovd7_flag else 0 end) as overdue_cnt_2_7
    , max(case when indexs = 3 then ovd7_flag else 0 end) as overdue_cnt_3_7
    , max(case when indexs = 4 then ovd7_flag else 0 end) as overdue_cnt_4_7
    , max(case when indexs = 5 then ovd7_flag else 0 end) as overdue_cnt_5_7
    , max(case when indexs = 6 then ovd7_flag else 0 end) as overdue_cnt_6_7
    , max(case when indexs = 7 then ovd7_flag else 0 end) as overdue_cnt_7_7
    , max(case when indexs = 8 then ovd7_flag else 0 end) as overdue_cnt_8_7
    , max(case when indexs = 9 then ovd7_flag else 0 end) as overdue_cnt_9_7
    , max(case when indexs = 10 then ovd7_flag else 0 end) as overdue_cnt_10_7

    , max(case when indexs = 1 then ovd15_flag else 0 end) as overdue_cnt_1_15
    , max(case when indexs = 2 then ovd15_flag else 0 end) as overdue_cnt_2_15
    , max(case when indexs = 3 then ovd15_flag else 0 end) as overdue_cnt_3_15
    , max(case when indexs = 4 then ovd15_flag else 0 end) as overdue_cnt_4_15
    , max(case when indexs = 5 then ovd15_flag else 0 end) as overdue_cnt_5_15
    , max(case when indexs = 6 then ovd15_flag else 0 end) as overdue_cnt_6_15
    , max(case when indexs = 7 then ovd15_flag else 0 end) as overdue_cnt_7_15
    , max(case when indexs = 8 then ovd15_flag else 0 end) as overdue_cnt_8_15
    , max(case when indexs = 9 then ovd15_flag else 0 end) as overdue_cnt_9_15
    , max(case when indexs = 10 then ovd15_flag else 0 end) as overdue_cnt_10_15  

    , max(case when indexs = 1 then ovd30_flag else 0 end) as overdue_cnt_1_30
    , max(case when indexs = 2 then ovd30_flag else 0 end) as overdue_cnt_2_30
    , max(case when indexs = 3 then ovd30_flag else 0 end) as overdue_cnt_3_30
    , max(case when indexs = 4 then ovd30_flag else 0 end) as overdue_cnt_4_30
    , max(case when indexs = 5 then ovd30_flag else 0 end) as overdue_cnt_5_30
    , max(case when indexs = 6 then ovd30_flag else 0 end) as overdue_cnt_6_30
    , max(case when indexs = 7 then ovd30_flag else 0 end) as overdue_cnt_7_30
    , max(case when indexs = 8 then ovd30_flag else 0 end) as overdue_cnt_8_30
    , max(case when indexs = 9 then ovd30_flag else 0 end) as overdue_cnt_9_30  
    , max(case when indexs = 10 then ovd30_flag else 0 end) as overdue_cnt_10_30  

    , max(case when indexs = 1 then due0_amount else 0 end) as should_capital_1_0
    , max(case when indexs = 2 then due0_amount else 0 end) as should_capital_2_0
    , max(case when indexs = 3 then due0_amount else 0 end) as should_capital_3_0
    , max(case when indexs = 4 then due0_amount else 0 end) as should_capital_4_0
    , max(case when indexs = 5 then due0_amount else 0 end) as should_capital_5_0
    , max(case when indexs = 6 then due0_amount else 0 end) as should_capital_6_0
    , max(case when indexs = 7 then due0_amount else 0 end) as should_capital_7_0
    , max(case when indexs = 8 then due0_amount else 0 end) as should_capital_8_0
    , max(case when indexs = 9 then due0_amount else 0 end) as should_capital_9_0
    , max(case when indexs = 10 then due0_amount else 0 end) as should_capital_10_0  

    , max(case when indexs = 1 then due3_amount else 0 end) as should_capital_1_3
    , max(case when indexs = 2 then due3_amount else 0 end) as should_capital_2_3
    , max(case when indexs = 3 then due3_amount else 0 end) as should_capital_3_3
    , max(case when indexs = 4 then due3_amount else 0 end) as should_capital_4_3
    , max(case when indexs = 5 then due3_amount else 0 end) as should_capital_5_3
    , max(case when indexs = 6 then due3_amount else 0 end) as should_capital_6_3
    , max(case when indexs = 7 then due3_amount else 0 end) as should_capital_7_3
    , max(case when indexs = 8 then due3_amount else 0 end) as should_capital_8_3
    , max(case when indexs = 9 then due3_amount else 0 end) as should_capital_9_3  
    , max(case when indexs = 10 then due3_amount else 0 end) as should_capital_10_3

    , max(case when indexs = 1 then due7_amount else 0 end) as should_capital_1_7
    , max(case when indexs = 2 then due7_amount else 0 end) as should_capital_2_7
    , max(case when indexs = 3 then due7_amount else 0 end) as should_capital_3_7
    , max(case when indexs = 4 then due7_amount else 0 end) as should_capital_4_7
    , max(case when indexs = 5 then due7_amount else 0 end) as should_capital_5_7
    , max(case when indexs = 6 then due7_amount else 0 end) as should_capital_6_7
    , max(case when indexs = 7 then due7_amount else 0 end) as should_capital_7_7
    , max(case when indexs = 8 then due7_amount else 0 end) as should_capital_8_7
    , max(case when indexs = 9 then due7_amount else 0 end) as should_capital_9_7
    , max(case when indexs = 10 then due7_amount else 0 end) as should_capital_10_7

    , max(case when indexs = 1 then due15_amount else 0 end) as should_capital_1_15
    , max(case when indexs = 2 then due15_amount else 0 end) as should_capital_2_15
    , max(case when indexs = 3 then due15_amount else 0 end) as should_capital_3_15
    , max(case when indexs = 4 then due15_amount else 0 end) as should_capital_4_15
    , max(case when indexs = 5 then due15_amount else 0 end) as should_capital_5_15
    , max(case when indexs = 6 then due15_amount else 0 end) as should_capital_6_15
    , max(case when indexs = 7 then due15_amount else 0 end) as should_capital_7_15
    , max(case when indexs = 8 then due15_amount else 0 end) as should_capital_8_15
    , max(case when indexs = 9 then due15_amount else 0 end) as should_capital_9_15  
    , max(case when indexs = 10 then due15_amount else 0 end) as should_capital_10_15  

    , max(case when indexs = 1 then due30_amount else 0 end) as should_capital_1_30
    , max(case when indexs = 2 then due30_amount else 0 end) as should_capital_2_30
    , max(case when indexs = 3 then due30_amount else 0 end) as should_capital_3_30
    , max(case when indexs = 4 then due30_amount else 0 end) as should_capital_4_30
    , max(case when indexs = 5 then due30_amount else 0 end) as should_capital_5_30
    , max(case when indexs = 6 then due30_amount else 0 end) as should_capital_6_30
    , max(case when indexs = 7 then due30_amount else 0 end) as should_capital_7_30
    , max(case when indexs = 8 then due30_amount else 0 end) as should_capital_8_30
    , max(case when indexs = 9 then due30_amount else 0 end) as should_capital_9_30
    , max(case when indexs = 10 then due30_amount else 0 end) as should_capital_10_30  

    , max(case when indexs = 1 then ovd0_amount else 0 end) as overdue_amount_1_0
    , max(case when indexs = 2 then ovd0_amount else 0 end) as overdue_amount_2_0
    , max(case when indexs = 3 then ovd0_amount else 0 end) as overdue_amount_3_0
    , max(case when indexs = 4 then ovd0_amount else 0 end) as overdue_amount_4_0
    , max(case when indexs = 5 then ovd0_amount else 0 end) as overdue_amount_5_0
    , max(case when indexs = 6 then ovd0_amount else 0 end) as overdue_amount_6_0
    , max(case when indexs = 7 then ovd0_amount else 0 end) as overdue_amount_7_0
    , max(case when indexs = 8 then ovd0_amount else 0 end) as overdue_amount_8_0
    , max(case when indexs = 9 then ovd0_amount else 0 end) as overdue_amount_9_0  
    , max(case when indexs = 10 then ovd0_amount else 0 end) as overdue_amount_10_0  

    , max(case when indexs = 1 then ovd3_amount else 0 end) as overdue_amount_1_3
    , max(case when indexs = 2 then ovd3_amount else 0 end) as overdue_amount_2_3
    , max(case when indexs = 3 then ovd3_amount else 0 end) as overdue_amount_3_3
    , max(case when indexs = 4 then ovd3_amount else 0 end) as overdue_amount_4_3
    , max(case when indexs = 5 then ovd3_amount else 0 end) as overdue_amount_5_3
    , max(case when indexs = 6 then ovd3_amount else 0 end) as overdue_amount_6_3
    , max(case when indexs = 7 then ovd3_amount else 0 end) as overdue_amount_7_3
    , max(case when indexs = 8 then ovd3_amount else 0 end) as overdue_amount_8_3
    , max(case when indexs = 9 then ovd3_amount else 0 end) as overdue_amount_9_3
    , max(case when indexs = 10 then ovd3_amount else 0 end) as overdue_amount_10_3  

    , max(case when indexs = 1 then ovd7_amount else 0 end) as overdue_amount_1_7
    , max(case when indexs = 2 then ovd7_amount else 0 end) as overdue_amount_2_7
    , max(case when indexs = 3 then ovd7_amount else 0 end) as overdue_amount_3_7
    , max(case when indexs = 4 then ovd7_amount else 0 end) as overdue_amount_4_7
    , max(case when indexs = 5 then ovd7_amount else 0 end) as overdue_amount_5_7
    , max(case when indexs = 6 then ovd7_amount else 0 end) as overdue_amount_6_7
    , max(case when indexs = 7 then ovd7_amount else 0 end) as overdue_amount_7_7
    , max(case when indexs = 8 then ovd7_amount else 0 end) as overdue_amount_8_7
    , max(case when indexs = 9 then ovd7_amount else 0 end) as overdue_amount_9_7
    , max(case when indexs = 10 then ovd7_amount else 0 end) as overdue_amount_10_7 

    , max(case when indexs = 1 then ovd15_amount else 0 end) as overdue_amount_1_15
    , max(case when indexs = 2 then ovd15_amount else 0 end) as overdue_amount_2_15
    , max(case when indexs = 3 then ovd15_amount else 0 end) as overdue_amount_3_15
    , max(case when indexs = 4 then ovd15_amount else 0 end) as overdue_amount_4_15
    , max(case when indexs = 5 then ovd15_amount else 0 end) as overdue_amount_5_15
    , max(case when indexs = 6 then ovd15_amount else 0 end) as overdue_amount_6_15
    , max(case when indexs = 7 then ovd15_amount else 0 end) as overdue_amount_7_15
    , max(case when indexs = 8 then ovd15_amount else 0 end) as overdue_amount_8_15
    , max(case when indexs = 9 then ovd15_amount else 0 end) as overdue_amount_9_15 
    , max(case when indexs = 10 then ovd15_amount else 0 end) as overdue_amount_10_15  

    , max(case when indexs = 1 then ovd30_amount else 0 end) as overdue_amount_1_30
    , max(case when indexs = 2 then ovd30_amount else 0 end) as overdue_amount_2_30
    , max(case when indexs = 3 then ovd30_amount else 0 end) as overdue_amount_3_30
    , max(case when indexs = 4 then ovd30_amount else 0 end) as overdue_amount_4_30
    , max(case when indexs = 5 then ovd30_amount else 0 end) as overdue_amount_5_30
    , max(case when indexs = 6 then ovd30_amount else 0 end) as overdue_amount_6_30
    , max(case when indexs = 7 then ovd30_amount else 0 end) as overdue_amount_7_30
    , max(case when indexs = 8 then ovd30_amount else 0 end) as overdue_amount_8_30
    , max(case when indexs = 9 then ovd30_amount else 0 end) as overdue_amount_9_30
    , max(case when indexs = 10 then ovd30_amount else 0 end) as overdue_amount_10_30  
  from 
  (
    select 
      *
      , if(due0_flag = 1, should_capital, 0) as due0_amount
      , if(ovd0_flag = 1, should_capital - repay_t0_amt_all, 0) as ovd0_amount
      , if(due3_flag = 1, should_capital, 0) as due3_amount
      , if(ovd3_flag = 1, should_capital - repay_t3_amt_all, 0) as ovd3_amount
      , if(due7_flag = 1, should_capital, 0) as due7_amount
      , if(ovd7_flag = 1, should_capital - repay_t7_amt_all, 0) as ovd7_amount
      , if(due14_flag = 1, should_capital, 0) as due14_amount
      , if(ovd14_flag = 1, should_capital - repay_t14_amt_all, 0) as ovd14_amount
      , if(due15_flag = 1, should_capital, 0) as due15_amount
      , if(ovd15_flag = 1, should_capital - repay_t15_amt_all, 0) as ovd15_amount
      , if(due30_flag = 1, should_capital, 0) as due30_amount
      , if(ovd30_flag = 1, should_capital - repay_t30_amt_all, 0) as ovd30_amount
    from ind.xly_vintage_2 a 
    left join 
    (select camera_id as camera_id2,sum(cast(should_capital as decimal)) as should_capital 
    from ods.s02_loan_repayment where state!=7 
    group by 1) b on a.camera_id = b.camera_id2 
  )
  group by 1
  ;

--TABLE 12:ind.xly_vintage_4
drop table if exists ind.xly_vintage_4;
create table ind.xly_vintage_4 as
  select 
    a.*
    ,case
    when loan_indexs = 1 then should_cnt_1_7
    when loan_indexs = 2 then should_cnt_2_7
    when loan_indexs = 3 then should_cnt_3_7
    when loan_indexs = 4 then should_cnt_4_7
    when loan_indexs = 5 then should_cnt_5_7
    when loan_indexs = 6 then should_cnt_6_7
    when loan_indexs = 7 then should_cnt_7_7
    when loan_indexs = 8 then should_cnt_8_7
    when loan_indexs = 9 then should_cnt_9_7
    when loan_indexs = 10 then should_cnt_10_7
    else null end as should_cnt_total_7
    ,case 
    when loan_indexs = 1 then should_cnt_1_30
    when loan_indexs = 2 then should_cnt_2_30
    when loan_indexs = 3 then should_cnt_3_30
    when loan_indexs = 4 then should_cnt_4_30
    when loan_indexs = 5 then should_cnt_5_30
    when loan_indexs = 6 then should_cnt_6_30
    when loan_indexs = 7 then should_cnt_7_30
    when loan_indexs = 8 then should_cnt_8_30
    when loan_indexs = 9 then should_cnt_9_30
    when loan_indexs = 10 then should_cnt_10_30
    else null end as should_cnt_total_30
    ,case 
    when loan_indexs = 1 then overdue_cnt_1_7
    when loan_indexs = 2 then overdue_cnt_2_7
    when loan_indexs = 3 then overdue_cnt_3_7
    when loan_indexs = 4 then overdue_cnt_4_7
    when loan_indexs = 5 then overdue_cnt_5_7
    when loan_indexs = 6 then overdue_cnt_6_7
    when loan_indexs = 7 then overdue_cnt_7_7
    when loan_indexs = 8 then overdue_cnt_8_7
    when loan_indexs = 9 then overdue_cnt_9_7
    when loan_indexs = 10 then overdue_cnt_10_7
    else null end as overdue_cnt_total_7
    ,case
    when loan_indexs = 1 then overdue_cnt_1_30
    when loan_indexs = 2 then overdue_cnt_2_30
    when loan_indexs = 3 then overdue_cnt_3_30
    when loan_indexs = 4 then overdue_cnt_4_30
    when loan_indexs = 5 then overdue_cnt_5_30
    when loan_indexs = 6 then overdue_cnt_6_30
    when loan_indexs = 7 then overdue_cnt_7_30
    when loan_indexs = 8 then overdue_cnt_8_30
    when loan_indexs = 9 then overdue_cnt_9_30
    when loan_indexs = 10 then overdue_cnt_10_30
    else null end as overdue_cnt_total_30
    ,case
    when loan_indexs = 1 then should_capital_1_7
    when loan_indexs = 2 then should_capital_2_7
    when loan_indexs = 3 then should_capital_3_7
    when loan_indexs = 4 then should_capital_4_7
    when loan_indexs = 5 then should_capital_5_7
    when loan_indexs = 6 then should_capital_6_7
    when loan_indexs = 7 then should_capital_7_7
    when loan_indexs = 8 then should_capital_8_7
    when loan_indexs = 9 then should_capital_9_7
    when loan_indexs = 10 then should_capital_10_7
    else null end as should_capital_total_7
    ,case
    when loan_indexs = 1 then should_capital_1_30
    when loan_indexs = 2 then should_capital_2_30
    when loan_indexs = 3 then should_capital_3_30
    when loan_indexs = 4 then should_capital_4_30
    when loan_indexs = 5 then should_capital_5_30
    when loan_indexs = 6 then should_capital_6_30
    when loan_indexs = 7 then should_capital_7_30
    when loan_indexs = 8 then should_capital_8_30
    when loan_indexs = 9 then should_capital_9_30
    when loan_indexs = 10 then should_capital_10_30
    else null end as should_capital_total_30
    ,case
    when loan_indexs = 1 then overdue_amount_1_7
    when loan_indexs = 2 then overdue_amount_2_7
    when loan_indexs = 3 then overdue_amount_3_7
    when loan_indexs = 4 then overdue_amount_4_7
    when loan_indexs = 5 then overdue_amount_5_7
    when loan_indexs = 6 then overdue_amount_6_7
    when loan_indexs = 7 then overdue_amount_7_7
    when loan_indexs = 8 then overdue_amount_8_7
    when loan_indexs = 9 then overdue_amount_9_7
    when loan_indexs = 10 then overdue_amount_10_7
    else null end as overdue_amount_total_7
    ,case
    when loan_indexs = 1 then overdue_amount_1_30
    when loan_indexs = 2 then overdue_amount_2_30
    when loan_indexs = 3 then overdue_amount_3_30
    when loan_indexs = 4 then overdue_amount_4_30
    when loan_indexs = 5 then overdue_amount_5_30
    when loan_indexs = 6 then overdue_amount_6_30
    when loan_indexs = 7 then overdue_amount_7_30
    when loan_indexs = 8 then overdue_amount_8_30
    when loan_indexs = 9 then overdue_amount_9_30
    when loan_indexs = 10 then overdue_amount_10_30
    else null end as overdue_amount_total_30
  from ind.xly_vintage_3 a 
  left join ods.s02_loan b on a.camera_id3 = b.camera_id
  ;

--TABLE 13:ind.xly_application_funnel
drop table if exists ind.xly_application_funnel;  
create table  ind.xly_application_funnel as
  select 
    *
    , case when source_channel2 != 'IOS' and is_reloan2 = 'OLD_PLUS' and new_grade_level in ('1', '2') then 1 
   when source_channel2 != 'IOS' and is_reloan2 = 'OLD_PLUS' and new_grade_level in ('3', '4') then 2
   when source_channel2 != 'IOS' and is_reloan2 = 'OLD_PLUS' and new_grade_level in ('5', '6') then 3
   when source_channel2 != 'IOS' and is_reloan2 = 'OLD_PLUS' and new_grade_level >= '7' then 4

   when source_channel2 = 'IOS' and is_reloan2 = 'OLD_PLUS' and new_grade_level in ('1') and product_level not like 'M%' then 1
   when source_channel2 = 'IOS' and is_reloan2 = 'OLD_PLUS' and new_grade_level >= '2' and product_level not like 'M%' then 2
   when source_channel2 = 'IOS' and is_reloan2 = 'OLD_PLUS' and product_level like 'M%' then 3
   
   when source_channel2 != 'IOS' and is_reloan2 = 'OLD_SINGLE' and new_grade_level in ('1', '2') and product_level not like 'M%' then 2
   when source_channel2 != 'IOS' and is_reloan2 = 'OLD_SINGLE' and new_grade_level in ('3', '4') and product_level not like 'M%' then 3
   when source_channel2 != 'IOS' and is_reloan2 = 'OLD_SINGLE' and new_grade_level in ('5', '6') and product_level not like 'M%' then 4
   when source_channel2 != 'IOS' and is_reloan2 = 'OLD_SINGLE' and new_grade_level >= '7' and product_level not like 'M%' then 5

   when source_channel2 = 'IOS' and is_reloan2 = 'OLD_SINGLE' and new_grade_level = '1' and product_level not like 'M%' then 2
   when source_channel2 = 'IOS' and is_reloan2 = 'OLD_SINGLE' and new_grade_level >= '2' and product_level not like 'M%' then 3

   when source_channel2 != 'IOS' and is_reloan2 = 'OLD_SINGLE' and new_grade_level in ('1') and product_level like 'M%' then 2
   when source_channel2 != 'IOS' and is_reloan2 = 'OLD_SINGLE' and new_grade_level in ('2') and product_level like 'M%' then 3
   when source_channel2 != 'IOS' and is_reloan2 = 'OLD_SINGLE' and new_grade_level in ('3') and product_level like 'M%' then 4
   when source_channel2 != 'IOS' and is_reloan2 = 'OLD_SINGLE' and new_grade_level >= '4' and product_level like 'M%' then 5

   when source_channel2 = 'IOS' and is_reloan2 = 'OLD_SINGLE' and new_grade_level <= '2' and product_level like 'M%' then 3
   when source_channel2 = 'IOS' and is_reloan2 = 'OLD_SINGLE' and new_grade_level >= '3' and product_level like 'M%' then 4

   when is_reloan2 = 'OLD_PLUS_M' and new_grade_level <= '2' then 2
   when is_reloan2 = 'OLD_PLUS_M' and new_grade_level in ('3', '4') then 3
   when is_reloan2 = 'OLD_PLUS_M' and new_grade_level >= '5' then 4
   
   else 5
   end as user_level 
    ,to_char(date_trunc('week',date(fd_ltv_date)),'yyyy-mm-dd') as fd_ltv_week
    ,to_char(date_trunc('month',date(fd_ltv_date)),'yyyy-mm-dd') as fd_ltv_month
  from ind.xly_application_funnel_1 a 
  left join ind.xly_application_funnel_2 b on cast(a.id as varchar) = b.biz_id
  left join ind.xly_application_funnel_overdue_p1 c1 on cast(a.id as varchar) = cast(ceil(c1.camera_id1) as varchar) 
  left join ind.xly_application_funnel_overdue_all c2 on cast(a.id as varchar) = cast(ceil(c2.camera_id) as varchar) 
  left join ind.xly_vintage_4 c3 on cast(a.id as varchar) = cast(ceil(c3.camera_id3) as varchar)
  left join 
  (
    select cid, max(cast(json_extract(value,'$.thirdparty_duotou_is_found_fdc_v4') as bigint)) as is_found_fdc
    from ods.s09_os_variable_log where name='fdc_inquiry_v4' and update_time is not null AND date(create_time)>=date'2022-10-01' 
    group by 1
  ) e on a.id = cast(e.cid as bigint)
  left join 
  (
    SELECT mid as mid2 ,min(date(create_time)) as fd_ltv_date
    FROM ods.s05_creditx_order 
    WHERE double_loan =0 and status=372  GROUP BY 1 
  ) f on a.mid = cast(f.mid2 as bigint)