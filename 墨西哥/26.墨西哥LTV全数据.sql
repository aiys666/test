-- 首贷
-- 每一笔资产的首贷数据，主要用于计算首贷的LTV数据
-- 日、周、月、包、渠道、来源、版本号、等级（新）、等级（首贷）、小金额标识、注册媒体来源、合同金额、手续费、利息、应还总额、应还总额T0、应还总额T3、应还本金T0、应还本金T3、实还本金T0、实还本金T3、实还总额T0、实还总额T3、应还总额T7、应还总额T30、应还本金T7、应还本金T30、实还总额T7、实还总额T30；


drop table if exists mx.ys_dl_ltv_first_loan_0511;
create table mx.ys_dl_ltv_first_loan_0511 as
select 
    r.biz_id,
    r.issue_month as ltv_month,
    r.issue_week as ltv_week,
    r.issue_date as ltv_date,
    r.loan_cycle, 
    r.app_channel,
    r.app_group as app_channel_name, 
    r.product_name,
    	
    r.source,	
    r.app_version,	
    r.channel_category,
    coalesce(f7.credit_level, 9999) as new_grade_level,
    case 
    when r.app_time>=date'2026-01-01' then sd_creditlevel_main_v4_1 
    when r.app_time>=date'2026-06-02' then android_newcust_maincreditlevel_charge_v5_2  
    else 9999
    end as new_grade_level_main,
    case when r.contract_amount <= 500 then '小金额(<=500)' else '非小金额(>500)' end as is_low_amount_flag,
    case
        when lower(att.new_media_source) = 'facebook' then 'facebook'
        when lower(att.new_media_source) = 'google' then 'google'
        when lower(att.new_media_source) = 'tiktok' then 'tiktok'
        when lower(att.new_media_source) = 'apple search ads' then 'Apple Search Ads'
        when lower(att.new_media_source) = 'organic' then 'organic'
        when lower(att.new_media_source) = 'bj' then 'bj'
        when att.new_media_source = '探知' then '探知'
        else 'other'
        end as register_media_source, 
    cast(r.cust_id as bigint) as mid,
    
    (coalesce(r.haircut_amount, 0) + coalesce(r.should_interest, 0) ) / nullif(r.contract_amount, 0) as fee,
    r.contract_amount,
    r.haircut_amount,
    r.should_interest,
    r.should_interest+r.should_capital as should_amt,
    r.t0_should_amt_1 as should_amt_1t0,
    r.t3_should_amt_1 as should_amt_1t3,
    r.t0_should_capit_1 as contract_1t0,
    r.t3_should_capit_1 as contract_1t3,
    r.t0_should_capit_1-r.t0_overdue_capit_1 as fact_capital_1t0,
    r.t3_should_capit_1-r.t3_overdue_capit_1 as fact_capital_1t3,
    r.t0_should_amt_1-r.t0_overdue_amount_1 as fact_1t0,
    r.t3_should_amt_1-r.t3_overdue_amount_1 as fact_1t3,
    r.t7_should_amt_4 as should_amt_t7,
    r.t30_should_amt_4 as should_amt_t30,
    r.t7_should_capit_4 as contract_t7,
    r.t30_should_capit_4 as contract_t30,
    -- r.t7_fact_amt as fact_t71,
    r.t7_should_amt_4-r.t7_overdue_amount_4 as fact_t7,
    r.t7_should_amt_4-r.t7_overdue_amount_4 as fact_t7_coup,
    r.t30_should_amt_4-r.t30_overdue_amount_4 as fact_t30,
    r.t30_should_amt_4-r.t30_overdue_amount_4 as fact_t30_coup,
    case when r.t0_should_amt_4-r.t0_overdue_amount_4>0 then 1 else 0 end as fact_cnt_t0,
    case when r.t7_should_amt_4-r.t7_overdue_amount_4>0 then 1 else 0 end as fact_cnt_t7,
    case when r.t30_should_amt_4-r.t30_overdue_amount_4>0 then 1 else 0 end as fact_cnt_t30,
    0 as fact_cnt_till_now, 
    0 as re_zr_cnt_t30
from mx.wxs_application_funnel r 
left join ods.s02_loan t on r.camera_id=t.camera_id
left join mx.report_application_funnel7_table f7 on r.camera_id = cast(f7.biz_id as bigint)

-- 取首贷等级分组；
left join
  (select 
    externalid7, 
    sd_creditlevel_main_v4_1,  
    android_newcust_maincreditlevel_charge_v5_2 
  from mx.wenj_sd_market  
  ) t4 on r.biz_id = t4.externalid7
left join mx.gm_attribution_detail att on cast(r.cust_id as bigint) = att.mid
where r.is_reloan = 'new'
  and r.if_issue=1 ;
 

  -- 2投放
drop table if exists mx.ys_mx_ltv_ads_cost;
create table mx.ys_mx_ltv_ads_cost as

with channel_mapping as (
    select app_key, app_channel
    from (
        values
            ('com.tiri.mx', '2930a02e-07b9-4851-aedd-200244a62b75'),
            ('com.tengoprestamos.cash.credito.mx', '2930a02e-07b9-4851-aedd-200244a62b75'),
            ('com.prestamos.credito.peso.cashvivas', '5653600e-256f-4768-8b27-8020e16c2587'),
            ('com.cash.prestamo.yaweycredito', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.cash.rapido.dinero.credito.yawey', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.cash.rapido.dinero.credito.yaweycredito', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.prestamo.credito.cash.loan.yawey', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.mx.dinero.yawey', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.cash.credito.prestamo.holapresto', 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5'),
            ('com.mxprestamo.credito.cash.rapido.holapresto', 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5'),
            ('id6504391085', 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5'),
            ('com.voltrixcredito.prestamos', '91379659-2dc0-42d2-8205-9de6d81f7550'),
            ('com.cash.prestamos.credito.prontofondo', '026f5e80-4582-4821-847a-4665660d8451'),
            ('com.holapresto.se', 'faa92afe-b81a-4d94-ba1a-15eb9d536833'),
            ('com.holapresto.pro', 'db0d289f-d217-49ea-a889-c191776115ef'),
            ('com.holapresto.max', '4cc31ae6-937e-4fd3-bc98-862314e7cb68'),
            ('com.cash.prestamo.yaweycredito.plus', 'cdf58da5-801a-4575-9af4-a56453cea6f3'),
            ('com.cash.prestamo.yaweycredito.ultra', '9922eb08-b998-46d9-b81e-469ae4c2e0ec'),
            ('com.mexcredo.loan.mx', '002e5068-2b82-443e-9447-88ddba989753'),
            ('com.efectivo.presto.credi.tuna', '38cb07f1-21ce-47ed-b552-384381fbaa92'),
            ('com.dinero.prest.balam.plata', 'f280d23f-8d33-49c8-8aff-cbbda6045c75'),
            ('id6751942954', 'a73166d6-364d-405f-bb38-a06ba2141a0f'),
            ('com.quikpeso.credito.dinerorapido', 'a73166d6-364d-405f-bb38-a06ba2141a0f'),
            ('com.rapido.credito.mikredi', '20fbd6af-b9f8-48d4-bc30-4ad3040e7205')
    ) as t(app_key, app_channel)
)
 

select
    date(c.ad_date) as ad_date,
    date_trunc('month', date(c.ad_date)) as ad_month,
    date_trunc('week', date(c.ad_date)) as ad_week,
    case
        when lower(media_source) = 'facebook' then 'facebook'
        when lower(media_source) = 'google' then 'google'
        when lower(media_source) = 'tiktok' then 'tiktok'
        when lower(media_source) = 'apple search ads' then 'Apple Search Ads'
        when lower(media_source) = 'organic' then 'organic'
        when lower(media_source) = 'bj' then 'bj'
        when media_source = '探知' then '探知'
        else 'other'
        end as media_source, 
    coalesce(cm.app_channel, 'other') as app_channel, 
    sum(c.spend_usd) as spend_usd 
from dwd.dwd_ads_cost c
left join channel_mapping cm
    on c.app_channel_name = cm.app_key
where cast(c.ad_date as date) > date '2025-01-01'
group by 1, 2, 3, 4,5 ; 


drop table if exists mx.ys_mx_ltv_first_loan_cac;
create table mx.ys_mx_ltv_first_loan_cac as
-- with first_loan_agg as (
--     select
--         ltv_week,
--         loan_cycle,
--         app_channel,
--         app_channel_name,
--         new_grade_level,
--         is_low_amount_flag,
--         count(distinct biz_id) as frs_cnt,
--         sum(contract_amount) as contract_amount,
--         sum(contract_amount) / nullif(count(distinct biz_id), 0) as avg_amount,
--         sum(fee * contract_amount) / nullif(sum(contract_amount), 0) as fee,
--         sum(fee * contract_amount) as fee_amount,
--         sum(should_amt) as should_amt,
--         sum(should_amt_1t0) as should_amt_1t0,
--         sum(should_amt_1t3) as should_amt_1t3,
--         sum(should_amt_t7) as should_amt_t7,
--         sum(should_amt_t30) as should_amt_t30,
--         sum(contract_1t0) as contract_1t0,
--         sum(contract_1t3) as contract_1t3,
--         sum(contract_t7) as contract_t7,
--         sum(contract_t30) as contract_t30,
--         sum(fact_capital_1t0) as fact_capital_1t0,
--         sum(fact_capital_1t3) as fact_capital_1t3,
--         sum(fact_1t0) as fact_1t0,
--         sum(fact_1t3) as fact_1t3,
--         sum(fact_t7) as fact_t7,
--         sum(fact_t7_coup) as fact_t7_coup,
--         sum(fact_t30) as fact_t30,
--         sum(fact_t30_coup) as fact_t30_coup,
--         sum(fact_cnt_t0) as fact_cnt_t0,
--         sum(fact_cnt_t7) as fact_cnt_t7,
--         sum(fact_cnt_t30) as fact_cnt_t30,
--         sum(fact_cnt_till_now) as fact_cnt_till_now,
--         sum(re_zr_cnt_t30) as re_zr_cnt_t30 
--     from mx.ys_dl_ltv_first_loan_0511
--     group by 1, 2, 3, 4, 5,6
-- ),
-- cost as (
--     select
--         ad_week,
--         app_channel, 
--         sum(spend_usd) as spend_usd
--     from mx.ys_mx_ltv_ads_cost
--     group by 1, 2 
-- ),
-- total_cost as (
--     select
--         ad_week,
--         sum(spend_usd) as total_spend_usd
--     from mx.ys_mx_ltv_ads_cost
--     group by 1
-- ),
-- cost_rank as (
--     select
--         ltv_week,
--         app_channel_name,
--         new_grade_level,
--         loan_cycle,
--         is_low_amount_flag,
--         row_number() over(partition by ltv_week,app_channel_name order by contract_amount desc) as cost_rnk
--     from first_loan_agg 
-- )
-- select
--     f.ltv_week,
--     f.loan_cycle,
--     f.app_channel_name,
--     f.new_grade_level,
--     f.is_low_amount_flag,
--     f.frs_cnt,
--     f.contract_amount,
--     round(f.avg_amount, 2) as avg_amount,
--     round(f.fee, 4) as fee,
--     round(f.fee_amount, 2) as fee_amount,
--     f.should_amt,
--     f.should_amt_1t0,
--     f.should_amt_1t3,
--     f.should_amt_t7,
--     f.should_amt_t30,
--     f.contract_1t0,
--     f.contract_1t3,
--     f.contract_t7,
--     f.contract_t30,
--     (f.contract_1t0 - f.fact_capital_1t0) / nullif(f.contract_1t0, 0) as bad_1t0_capital,
--     (f.contract_1t3 - f.fact_capital_1t3) / nullif(f.contract_1t3, 0) as bad_1t3_capital,
--     (f.should_amt_1t0 - f.fact_1t0) / nullif(f.should_amt_1t0, 0) as bad_1t0_amt,
--     (f.should_amt_1t3 - f.fact_1t3) / nullif(f.should_amt_1t3, 0) as bad_1t3_amt,
--     f.fact_capital_1t0,
--     f.fact_capital_1t3,
--     f.fact_1t0,
--     f.fact_1t3,
--     f.fact_t7,
--     f.fact_t7_coup,
--     f.fact_t30,
--     f.fact_t30_coup,
--     f.fact_cnt_t0,
--     f.fact_cnt_t7,
--     f.fact_cnt_t30,
--     f.fact_cnt_till_now,
--     f.re_zr_cnt_t30,
--     cast(0 as double) as pass_rate,
--     cr.cost_rnk,
--     coalesce(t.total_spend_usd*d.exchange_rate_to_dollar, 0) as total_spend_ngn,
--     coalesce(t.total_spend_usd, 0) as total_spend_usd,
--     coalesce(c.spend_usd*d.exchange_rate_to_dollar, 0) as spend_ngn,
--     coalesce(c.spend_usd, 0) as spend_usd,
--     d.exchange_rate_to_dollar
-- from first_loan_agg f
-- left join cost_rank cr
--     on f.ltv_week = cr.ltv_week
--    and f.app_channel_name = cr.app_channel_name
--    and f.new_grade_level = cr.new_grade_level
--    and f.loan_cycle = cr.loan_cycle
--    and f.is_low_amount_flag = cr.is_low_amount_flag
-- left join cost c
--     on f.ltv_week = c.ad_week
--    and f.app_channel = c.app_channel 
--    and cr.cost_rnk=1
-- left join total_cost t
--     on f.ltv_week = t.ad_week 
--     and cr.cost_rnk=1
-- left join dim.dim_exchange_rate_cost d 
--     on date(DATE_PARSE(d.month_id, '%Y%m'))=date_trunc('month', f.ltv_week)
--     and d.account_currency = 'MXN';














    
with first_loan_agg as (
    select
        ltv_month,
        loan_cycle,
        app_channel,
        app_channel_name,
        new_grade_level,
        new_grade_level_main,
        register_media_source,
        product_name,
        is_low_amount_flag,
        count(distinct biz_id) as frs_cnt,
        sum(contract_amount) as contract_amount,
        sum(contract_amount) / nullif(count(distinct biz_id), 0) as avg_amount,
        sum(fee * contract_amount) / nullif(sum(contract_amount), 0) as fee,
        sum(fee * contract_amount) as fee_amount,
        sum(should_amt) as should_amt,
        sum(should_amt_1t0) as should_amt_1t0,
        sum(should_amt_1t3) as should_amt_1t3,
        sum(should_amt_t7) as should_amt_t7,
        sum(should_amt_t30) as should_amt_t30,
        sum(contract_1t0) as contract_1t0,
        sum(contract_1t3) as contract_1t3,
        sum(contract_t7) as contract_t7,
        sum(contract_t30) as contract_t30,
        sum(fact_capital_1t0) as fact_capital_1t0,
        sum(fact_capital_1t3) as fact_capital_1t3,
        sum(fact_1t0) as fact_1t0,
        sum(fact_1t3) as fact_1t3,
        sum(fact_t7) as fact_t7,
        sum(fact_t7_coup) as fact_t7_coup,
        sum(fact_t30) as fact_t30,
        sum(fact_t30_coup) as fact_t30_coup,
        sum(fact_cnt_t0) as fact_cnt_t0,
        sum(fact_cnt_t7) as fact_cnt_t7,
        sum(fact_cnt_t30) as fact_cnt_t30,
        sum(fact_cnt_till_now) as fact_cnt_till_now,
        sum(re_zr_cnt_t30) as re_zr_cnt_t30 
    from mx.ys_dl_ltv_first_loan_0511
    group by 1, 2, 3, 4, 5, 6, 7, 8, 9
),
cost as (
    select
        ad_month,
        app_channel, 
        media_source,
        sum(spend_usd) as spend_usd
    from mx.ys_mx_ltv_ads_cost
    group by 1, 2 ,3
),
total_cost as (
    select
        ad_month,
        sum(spend_usd) as total_spend_usd
    from mx.ys_mx_ltv_ads_cost
    group by 1
),
cost_rank as (
    select
        ltv_month,
        app_channel_name,
        new_grade_level,
        new_grade_level_main,
        loan_cycle,
        is_low_amount_flag,
        product_name,
        register_media_source,
        row_number() over(partition by ltv_month,app_channel_name,register_media_source order by contract_amount desc) as cost_rnk
    from first_loan_agg 
)
select
    f.ltv_month,
    f.loan_cycle,
    f.app_channel_name,
    f.new_grade_level,
    f.new_grade_level_main,
    f.product_name,
    f.register_media_source,
    f.is_low_amount_flag,
    f.frs_cnt,
    f.contract_amount,
    round(f.avg_amount, 2) as avg_amount,
    round(f.fee, 4) as fee,
    round(f.fee_amount, 2) as fee_amount,
    f.should_amt,
    f.should_amt_1t0,
    f.should_amt_1t3,
    f.should_amt_t7,
    f.should_amt_t30,
    f.contract_1t0,
    f.contract_1t3,
    f.contract_t7,
    f.contract_t30,
    (f.contract_1t0 - f.fact_capital_1t0) / nullif(f.contract_1t0, 0) as bad_1t0_capital,
    (f.contract_1t3 - f.fact_capital_1t3) / nullif(f.contract_1t3, 0) as bad_1t3_capital,
    (f.should_amt_1t0 - f.fact_1t0) / nullif(f.should_amt_1t0, 0) as bad_1t0_amt,
    (f.should_amt_1t3 - f.fact_1t3) / nullif(f.should_amt_1t3, 0) as bad_1t3_amt,
    f.fact_capital_1t0,
    f.fact_capital_1t3,
    f.fact_1t0,
    f.fact_1t3,
    f.fact_t7,
    f.fact_t7_coup,
    f.fact_t30,
    f.fact_t30_coup,
    f.fact_cnt_t0,
    f.fact_cnt_t7,
    f.fact_cnt_t30,
    f.fact_cnt_till_now,
    f.re_zr_cnt_t30,
    cast(0 as double) as pass_rate,
    cr.cost_rnk,
    coalesce(t.total_spend_usd*d.exchange_rate_to_dollar, 0) as total_spend_ngn,
    coalesce(t.total_spend_usd, 0) as total_spend_usd,
    coalesce(c.spend_usd*d.exchange_rate_to_dollar, 0) as spend_ngn,
    coalesce(c.spend_usd, 0) as spend_usd,
    d.exchange_rate_to_dollar
from first_loan_agg f
left join cost_rank cr
    on f.ltv_month = cr.ltv_month
   and f.app_channel_name = cr.app_channel_name
   and f.new_grade_level = cr.new_grade_level
   and f.new_grade_level_main = cr.new_grade_level_main
   and f.register_media_source=cr.register_media_source
   and f.product_name = cr.product_name
   and f.loan_cycle = cr.loan_cycle
   and f.is_low_amount_flag = cr.is_low_amount_flag
left join cost c
    on f.ltv_month = c.ad_month
   and f.app_channel = c.app_channel 
   and f.register_media_source=c.media_source
   and cr.cost_rnk=1
left join total_cost t
    on f.ltv_month = t.ad_month 
    and cr.cost_rnk=1
left join dim.dim_exchange_rate_cost d 
    on date(DATE_PARSE(d.month_id, '%Y%m'))=date_trunc('month', f.ltv_month)
    and d.account_currency = 'MXN';
  



