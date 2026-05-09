
with  
apply_cnt AS ( 
    SELECT
        date(app_date) as app_date,  
        media_source2, 
        new_grade_level,loan_cycle,interval_start_old,
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
    COALESCE(bs.spend_account, 0) AS spend_account,

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
left join before_spend bs on a.ad_date = bs.ad_date AND a.media_source = bs.media_source 
FULL OUTER JOIN install_cnt b ON a.ad_date = b.install_date AND a.media_source = b.media_source 

FULL OUTER JOIN reg_cnt c ON a.ad_date = c.reg_dt AND a.media_source = c.media_source

FULL OUTER JOIN apply_cnt d ON a.ad_date = d.app_date AND a.media_source = d.media_source2
left join score_a100 a100 on d.app_date = a100.add_day AND d.media_source2 = a100.media_source
left join score_724 a724 on d.app_date = a724.add_day AND d.media_source2 = a724.media_source
left join score_a101 a101 on d.app_date = a101.add_day AND d.media_source2 = a101.media_source

FULL OUTER JOIN issue_cnt e ON a.ad_date = e.issue_date AND a.media_source = e.media_source2;
