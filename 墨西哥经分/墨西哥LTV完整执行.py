
补充区域：

-- # =========================================================
drop table if exists mx.ys_dl_ltv_first_loan_0511;
create table mx.ys_dl_ltv_first_loan_0511 as

select
    date_trunc('month', date(r.release_time)) as ltv_month, 
    r.loan_cycle, 
    r.app_channel,
    r.app_group as app_channel_name, 
    coalesce(f7.credit_level, 9999) as new_grade_level,
    case
        when lower(att.new_media_source) = 'facebook' then 'facebook'
        when lower(att.new_media_source) = 'google' then 'google'
        when lower(att.new_media_source) = 'tiktok' then 'tiktok'
        when lower(att.new_media_source) = 'apple search ads' then 'Apple Search Ads'
        when lower(att.new_media_source) = 'organic' then 'organic'
        else 'other'
        end as register_media_source,
    r.camera_id as biz_id, 
    
    
    (coalesce(r.haircut_amount, 0) + coalesce(r.should_interest, 0) ) / nullif(r.contract_amount, 0) as fee,
    r.contract_amount,
    r.haircut_amount,
    r.should_interest,
    r.should_interest+r.should_capital as should_amt,
    
    r.t7_should_amt_4 as should_amt_t7,
    r.t30_should_amt_4 as should_amt_t30,
    r.t7_should_capit_4 as contract_t7,
    r.t30_should_capit_4 as contract_t30,
    r.t7_fact_amt as fact_t7,
    r.t7_fact_amt as fact_t7_coup,
    r.t30_fact_amt as fact_t30,
    r.t30_fact_amt as fact_t30_coup,
    case when r.t0_fact_amt>0 then 1 else 0 end as fact_cnt_t0,
    case when r.t7_fact_amt>0 then 1 else 0 end as fact_cnt_t7,
    case when r.t30_fact_amt>0 then 1 else 0 end as fact_cnt_t30,
    case when r.now_fact_amt>0 then 1 else 0 end as fact_cnt_till_now,
    0 as re_zr_cnt_t30
from mx.wxs_application_funnel r 
left join ods.s02_loan t on r.camera_id=t.camera_id
left join mx.report_application_funnel7_table f7 on r.camera_id = cast(f7.biz_id as bigint)
left join mx.gm_attribution_detail  att on cast(r.cust_id as bigint) = att.mid
where r.is_reloan = 'new'
  and r.if_issue=1 ; 
 
-- # =========================================================

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
    coalesce(cm.app_channel, 'other') as app_channel, 
    sum(c.spend_usd) as spend_usd 
from dwd.dwd_ads_cost c
left join channel_mapping cm
    on c.app_channel_name = cm.app_key
where cast(c.ad_date as date) > date '2025-01-01'
group by 1, 2, 3 ; 

-- # =========================================================
-- # 3b. 首贷聚合（匹配尼日输出格式）8_首贷RAW
-- # =========================================================
  
 
with first_loan_agg as (
    select
        ltv_month,
        loan_cycle, app_channel,
        app_channel_name,
        new_grade_level,
        count(distinct biz_id) as frs_cnt,
        sum(contract_amount) as contract_amount,
        sum(contract_amount) / nullif(count(distinct biz_id), 0) as avg_amount,
        sum(fee * contract_amount) / nullif(sum(contract_amount), 0) as fee,
        sum(fee * contract_amount) as fee_amount,
        sum(should_amt) as should_amt,
        sum(should_amt_t7) as should_amt_t7,
        sum(should_amt_t30) as should_amt_t30,
        sum(contract_t7) as contract_t7,
        sum(contract_t30) as contract_t30,
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
    group by 1, 2, 3, 4 ,5
),
cost as (
    select
        ad_month,
        app_channel, 
        sum(spend_usd) as spend_usd
    from mx.ys_mx_ltv_ads_cost
    group by 1, 2 
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
        loan_cycle,
        row_number() over(partition by ltv_month,app_channel_name order by contract_amount desc) as cost_rnk
    from first_loan_agg 
)
select
    f.ltv_month,
    f.loan_cycle,
    f.app_channel_name,
    f.new_grade_level,
    f.frs_cnt,
    f.contract_amount,
    round(f.avg_amount, 2) as avg_amount,
    round(f.fee, 4) as fee,
    round(f.fee_amount, 2) as fee_amount,
    f.should_amt,
    f.should_amt_t7,
    f.should_amt_t30,
    f.contract_t7,
    f.contract_t30,
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
    coalesce(t.total_spend_usd/d.exchange_rate_to_dollar, 0) as total_spend_ngn,
    coalesce(t.total_spend_usd, 0) as total_spend_usd,
    coalesce(c.spend_usd/d.exchange_rate_to_dollar, 0) as spend_ngn,
    coalesce(c.spend_usd, 0) as spend_usd,
    d.exchange_rate_to_dollar
from first_loan_agg f
left join cost_rank cr
    on f.ltv_month = cr.ltv_month
   and f.app_channel_name = cr.app_channel_name
   and f.new_grade_level = cr.new_grade_level
   and f.loan_cycle = cr.loan_cycle
left join cost c
    on f.ltv_month = c.ad_month
   and f.app_channel = c.app_channel 
   and cr.cost_rnk=1
left join total_cost t
    on f.ltv_month = t.ad_month 
    and  cr.cost_rnk=1
left join dim.dim_exchange_rate_cost d 
on date(DATE_PARSE(d.month_id, '%Y%m'))=f.ltv_month
and d.account_currency = 'MXN' 
; 
 
 


















"""墨西哥LTV完整执行脚本 - 整合所有修复代码"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功!")

def exec_sql(sql, desc):
    print(f"\n{'='*60}")
    print(f"{desc}")
    print(f"{'='*60}")
    try:
        result = pq.query(sql)
        if isinstance(result, pd.DataFrame):
            print(f"  查询完成，返回 {len(result)} 行")
            if len(result) <= 5 and len(result.columns) <= 10:
                print(result.to_string())
        else:
            print(f"  DDL执行完成: {result}")
        return result
    except Exception as e:
        print(f"  错误: {e}")
        return None

def check_table(table_name):
    count_sql = f"select count(*) as cnt from {table_name}"
    try:
        result = pq.query(count_sql)
        if isinstance(result, pd.DataFrame):
            cnt = int(result.iloc[0]['cnt'])
            print(f"  {table_name}: {cnt} 行")
            return cnt
    except Exception as e:
        print(f"  {table_name}: 检查失败 - {e}")
    return -1

print("="*60)
print("开始执行墨西哥LTV完整流程")
print("="*60)

# =========================================================
# 0. 基础宽表
# =========================================================

exec_sql("""
drop table if exists mx.ys_mx_ltv_base_funnel;
create table mx.ys_mx_ltv_base_funnel as
select
    cast(app_id as varchar) as biz_id,
    cast(mid as bigint) as mid,
    cast(app_time as timestamp) as app_time,
    date(app_time) as app_date,
    date_trunc('week', date(app_time)) as app_week,
    date_trunc('month', date(app_time)) as app_month,
    status,
    double_loan,
    is_reloan,
    reloan_num,
    app,
    app_channel,
    app_group,
    channel_category,
    product_name,
    product_level,
    risk_level,
    cast(loan_cycle as integer) as loan_cycle,
    cast(contract_amount as double) as contract_amount,
    cast(amount as double) as amount,
    cast(haircut_amount as double) as haircut_amount,
    cast(release_time as timestamp) as release_time,
    date(release_time) as release_date,
    date_trunc('week', date(release_time)) as release_week,
    date_trunc('month', date(release_time)) as release_month,
    cast(finish_time as timestamp) as finish_time,
    loan_state,
    cast(loan_indexs as integer) as loan_indexs,
    if_app,
    if_pass,
    if_bid,
    if_issue,
    cast(apply_amount as double) as apply_amount,
    cast(approve_amount as double) as approve_amount,
    cast(issue_amount as double) as issue_amount,

    coalesce(if_in_shou_model, 0) as if_in_shou_model,
    coalesce(if_shou_model_passed, 0) as if_shou_model_passed,
    coalesce(if_in_fu_model, 0) as if_in_fu_model,
    coalesce(if_fu_model_passed, 0) as if_fu_model_passed,
    coalesce(if_in_sx, 0) as if_in_sx,
    coalesce(if_sx_passed, 0) as if_sx_passed,
    coalesce(if_in_fu_sx_refuse, 0) as if_in_fu_sx_refuse,
    coalesce(if_fu_sx_refuse_passed, 0) as if_fu_sx_refuse_passed,
    coalesce(if_in_post_model, 0) as if_in_post_model,

    cast(t7_should_amt_1 as double) as t7_should_amt_1,
    cast(t7_should_amt_2 as double) as t7_should_amt_2,
    cast(t7_should_amt_3 as double) as t7_should_amt_3,
    cast(t7_should_amt_4 as double) as t7_should_amt_4,
    cast(t7_overdue_amount_1 as double) as t7_overdue_amount_1,
    cast(t7_overdue_amount_2 as double) as t7_overdue_amount_2,
    cast(t7_overdue_amount_3 as double) as t7_overdue_amount_3,
    cast(t7_overdue_amount_4 as double) as t7_overdue_amount_4,
    cast(t30_should_amt_1 as double) as t30_should_amt_1,
    cast(t30_should_amt_2 as double) as t30_should_amt_2,
    cast(t30_should_amt_3 as double) as t30_should_amt_3,
    cast(t30_should_amt_4 as double) as t30_should_amt_4,
    cast(t30_overdue_amount_1 as double) as t30_overdue_amount_1,
    cast(t30_overdue_amount_2 as double) as t30_overdue_amount_2,
    cast(t30_overdue_amount_3 as double) as t30_overdue_amount_3,
    cast(t30_overdue_amount_4 as double) as t30_overdue_amount_4,

    cast(t7_should_capit_1 as double) as t7_should_capit_1,
    cast(t7_should_capit_2 as double) as t7_should_capit_2,
    cast(t7_should_capit_3 as double) as t7_should_capit_3,
    cast(t7_should_capit_4 as double) as t7_should_capit_4,
    cast(t7_overdue_capit_1 as double) as t7_overdue_capit_1,
    cast(t7_overdue_capit_2 as double) as t7_overdue_capit_2,
    cast(t7_overdue_capit_3 as double) as t7_overdue_capit_3,
    cast(t7_overdue_capit_4 as double) as t7_overdue_capit_4,
    cast(t30_should_capit_1 as double) as t30_should_capit_1,
    cast(t30_should_capit_2 as double) as t30_should_capit_2,
    cast(t30_should_capit_3 as double) as t30_should_capit_3,
    cast(t30_should_capit_4 as double) as t30_should_capit_4,
    cast(t30_overdue_capit_1 as double) as t30_overdue_capit_1,
    cast(t30_overdue_capit_2 as double) as t30_overdue_capit_2,
    cast(t30_overdue_capit_3 as double) as t30_overdue_capit_3,
    cast(t30_overdue_capit_4 as double) as t30_overdue_capit_4
from mx.wxs_application_funnel
where app_date >= date '2025-01-01'
  and app_date < current_date;
""", "0.1 基础宽表 funnel")
check_table("mx.ys_mx_ltv_base_funnel")

# =========================================================
# 0.2 基础宽表 loan（修复 biz_id 格式）
# =========================================================

exec_sql("""
drop table if exists mx.ys_mx_ltv_base_loan;
create table mx.ys_mx_ltv_base_loan as
with attribution as (
    select
        cast(mid as bigint) as mid,
        case
            when max(case when lower(new_media_source) = 'facebook' then 1 else 0 end) = 1 then 'facebook'
            when max(case when lower(new_media_source) = 'google' then 1 else 0 end) = 1 then 'Google'
            when max(case when lower(new_media_source) = 'tiktok' then 1 else 0 end) = 1 then 'tiktok'
            when max(case when lower(new_media_source) = 'apple search ads' then 1 else 0 end) = 1 then 'Apple Search Ads'
            when max(case when lower(new_media_source) = 'organic' then 1 else 0 end) = 1 then 'organic'
            else 'other'
        end as register_media_source
    from mx.gm_attribution_detail
    group by 1
)
select
    cast(cast(t.camera_id as bigint) as varchar) as biz_id,
    cast(t.customer_id as bigint) as mid,
    t.release_time,
    date(t.release_time) as release_date,
    date_trunc('week', date(t.release_time)) as release_week,
    date_trunc('month', date(t.release_time)) as release_month,
    t.trade_end_time,
    date(t.trade_end_time) as trade_end_date,
    t.finish_time,
    cast(t.loan_cycle as integer) as loan_cycle,
    cast(t.contract_amount as double) as contract_amount,
    cast(t.amount as double) as amount,
    cast(t.fee_amount as double) as fee_amount,
    cast(t.interest as double) as interest,
    cast(t.haircut_amount as double) as haircut_amount,
    t.state as loan_state,
    rt.double_loan,
    t.double_loan as raw_double_loan,
    t.app_channel,
    t.product_name,
    t.risk_level,
    row_number() over(partition by t.customer_id order by t.release_time) as loan_rank,
    coalesce(att.register_media_source, 'other') as register_media_source
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt
    on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
left join attribution att
    on cast(t.customer_id as bigint) = att.mid
where date(t.release_time) >= date '2025-01-01'
  and t.state in (1, 2, 3)
  and rt.double_loan in (0, 1);
""", "0.2 基础宽表 loan（修复 biz_id 格式）")
check_table("mx.ys_mx_ltv_base_loan")

# =========================================================
# 1. 汇率
# =========================================================

exec_sql("""
drop table if exists mx.ys_dl_ltv_exchange_rate;
create table mx.ys_dl_ltv_exchange_rate as
select
    month_id,
    account_currency,
    exchange_rate_to_dollar
from dim.dim_exchange_rate_cost
where account_currency = 'MXN';
""", "1. 汇率")
check_table("mx.ys_dl_ltv_exchange_rate")

# =========================================================
# 1b. 投放花费
# =========================================================

exec_sql("""
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
    date_trunc('month', date(c.ad_date)) as cost_month,
    coalesce(cm.app_channel, 'other') as app_channel,
    case
        when c.campaign_name like '%IOS%' or c.app_channel_name in ('id6751942954') then 'iOS'
        else 'ANDROID'
    end as os,
    case
        when lower(c.media_source) like '%google%' then 'Google'
        when lower(c.media_source) like '%facebook%' or c.media_source = 'restricted' then 'facebook'
        when lower(c.media_source) like '%tiktok%' or lower(c.media_source) like '%cyberads%' then 'tiktok'
        when lower(c.media_source) like '%apple%' then 'Apple Search Ads'
        when lower(c.media_source) like '%ads%' then c.media_source
        when c.agency is not null then c.agency
        when lower(c.media_source) like '%vfine_int%' then 'vfine_int'
        when c.media_source like 'dc1' then 'dc1'
        when c.media_source like 'tz1' then 'jc'
        when c.media_source = 'SMS' and c.campaign_name like '%cl%' then '创蓝'
        when (c.media_source = 'SMS' and c.campaign_name like '%TZ%') or lower(c.media_source) like '%tanzhi%' then '探知'
        when c.media_source = '11Y' then '11Y'
        when c.media_source = 'bj' then 'bj'
        when c.media_source = 'ziyouke' then 'ziyouke'
        when lower(c.media_source) like '%outside%' then '短信营销'
        when lower(c.media_source) like '%duobao%'
          or lower(c.media_source) like '%多包互导%'
          or lower(c.media_source) like '%yawey%'
          or lower(c.media_source) like '%tengo%'
          or lower(c.media_source) like '%hola%'
          or c.media_source = 'Email'
          or lower(c.media_source) like '%sms%'
          or lower(c.media_source) like '%app%' then '多包互导'
        when c.media_source like 'organic' then 'organic'
        when lower(c.media_source) like '%smark%' then 'smark'
        when c.media_source = '其他' then '其他'
        else '其他'
    end as new_media_source,
    sum(c.spend_usd) as spend_usd,
    cast(0 as bigint) as installs,
    sum(c.impressions) as impressions,
    sum(c.clicks) as clicks
from dwd.dwd_ads_cost c
left join channel_mapping cm
    on c.app_channel_name = cm.app_key
where cast(c.ad_date as date) > date '2025-01-01'
group by 1, 2, 3, 4, 5;
""", "1b. 投放花费")
check_table("mx.ys_mx_ltv_ads_cost")

# =========================================================
# 2. 复贷准入
# =========================================================

exec_sql("""
drop table if exists mx.ys_dl_ltv_zr;
create table mx.ys_dl_ltv_zr as
with prev_loan as (
    select
        mid,
        loan_rank,
        trade_end_date,
        finish_time
    from mx.ys_mx_ltv_base_loan
)
select
    f.app_date as zr_date,
    f.app_time as zr_time,
    f.mid as zr_mid,
    coalesce(f.reloan_num - 1, f.double_loan, 1) as deal_num,
    cast(0 as varchar) as zr_result,
    f.biz_id as zr_id,
    case
        when date_diff('day', p.trade_end_date, date(p.finish_time)) <= 7
         and date_diff('day', date(p.finish_time), f.app_date) between 0 and 30
        then '有效'
    end as is_t30_zhunru
from mx.ys_mx_ltv_base_funnel f
left join prev_loan p
    on f.mid = p.mid
   and p.loan_rank = coalesce(f.reloan_num - 1, f.double_loan, 1)
where (f.is_reloan = 'old' or f.double_loan > 0 or f.reloan_num > 1)
  and f.biz_id is not null;
""", "2. 复贷准入")
check_table("mx.ys_dl_ltv_zr")

# =========================================================
# 3. 前置/机审
# =========================================================

exec_sql("""
drop table if exists mx.ys_dl_ltv_qz_danti;
create table mx.ys_dl_ltv_qz_danti as
select
    f.app_date as qz_date,
    f.app_time as qz_time,
    f.mid as qz_mid,
    f.biz_id as qz_id,
    cast(null as varchar) as phone,
    f.app as qz_app_channel_name,
    cast(0 as varchar) as pre_credit_result,
    coalesce(f.reloan_num - 1, f.double_loan, 1) as deal_num,
    coalesce(f.product_level, f.risk_level) as rl_product_level,
    f.reloan_num as rl_loan_times
from mx.ys_mx_ltv_base_funnel f
where (f.is_reloan = 'old' or f.double_loan > 0 or f.reloan_num > 1)
  and f.biz_id is not null;
""", "3. 前置/机审")
check_table("mx.ys_dl_ltv_qz_danti")

# =========================================================
# 4. 后置申请
# =========================================================

exec_sql("""
drop table if exists mx.ys_dl_ltv_apply;
create table mx.ys_dl_ltv_apply as
select
    f.app_date as apply_date,
    f.mid,
    f.biz_id,
    f.double_loan,
    cast(0 as integer) as status,
    f.apply_amount,
    f.loan_cycle as loan_period,
    coalesce(f.reloan_num - 1, f.double_loan, 1) as deal_num
from mx.ys_mx_ltv_base_funnel f
where f.biz_id is not null
  and coalesce(f.apply_amount, 0) > 0;
""", "4. 后置申请")
check_table("mx.ys_dl_ltv_apply")

# =========================================================
# 5. 还款/T7/T30
# =========================================================

exec_sql("""
drop table if exists mx.ys_dl_ltv_repay;
create table mx.ys_dl_ltv_repay as
with coupon as (
    select
        a.camera_id,
        a.rid,
        sum(subtract_capital) as now_subtract_amt,
        sum(
            case
                when date(fact_time) <= date(should_time)
                 and date(should_time) < current_date then subtract_capital
            end
        ) as t0_subtract_amt,
        sum(
            case
                when date(fact_time) <= interval '3' day + date(should_time)
                 and date(should_time) + interval '3' day < current_date then subtract_capital
            end
        ) as t3_subtract_amt,
        sum(
            case
                when date(fact_time) <= interval '7' day + date(should_time)
                 and date(should_time) + interval '7' day < current_date then subtract_capital
            end
        ) as t7_subtract_amt,
        sum(
            case
                when date(fact_time) <= interval '14' day + date(should_time)
                 and date(should_time) + interval '14' day < current_date then subtract_capital
            end
        ) as t14_subtract_amt,
        sum(
            case
                when date(fact_time) <= interval '30' day + date(should_time)
                 and date(should_time) + interval '30' day < current_date then subtract_capital
            end
        ) as t30_subtract_amt,
        sum(greatest(coupon_amount - (should_fine - fact_fine - subtract_fine), 0)) as now_coupon_amt,
        sum(
            case
                when date(fact_time) <= date(should_time)
                 and date(should_time) < current_date
                then greatest(coupon_amount - (should_fine - fact_fine - subtract_fine), 0)
            end
        ) as t0_coupon_amt,
        sum(
            case
                when date(fact_time) <= interval '3' day + date(should_time)
                 and date(should_time) + interval '3' day < current_date
                then greatest(coupon_amount - (should_fine - fact_fine - subtract_fine), 0)
            end
        ) as t3_coupon_amt,
        sum(
            case
                when date(fact_time) <= interval '7' day + date(should_time)
                 and date(should_time) + interval '7' day < current_date
                then greatest(coupon_amount - (should_fine - fact_fine - subtract_fine), 0)
            end
        ) as t7_coupon_amt,
        sum(
            case
                when date(fact_time) <= interval '14' day + date(should_time)
                 and date(should_time) + interval '14' day < current_date
                then greatest(coupon_amount - (should_fine - fact_fine - subtract_fine), 0)
            end
        ) as t14_coupon_amt,
        sum(
            case
                when date(fact_time) <= interval '30' day + date(should_time)
                 and date(should_time) + interval '30' day < current_date
                then greatest(coupon_amount - (should_fine - fact_fine - subtract_fine), 0)
            end
        ) as t30_coupon_amt
    from ods.s02_loan_repayment a
    group by 1, 2
),
should as (
    select
        camera_id,
        rid,
        fact_time,
        should_time,
        should_capital,
        should_interest,
        should_fine,
        case when date(should_time) + interval '7' day < current_date then should_capital end as t7_should_capital,
        case when date(should_time) + interval '7' day < current_date then should_capital + should_interest end as t7_should_amt,
        case when date(should_time) + interval '30' day < current_date then should_capital end as t30_should_capital,
        case when date(should_time) + interval '30' day < current_date then should_capital + should_interest end as t30_should_amt
    from (
        select
            a.camera_id,
            a.rid,
            a.fact_time,
            sum(a.should_capital) as should_capital,
            sum(a.should_interest) as should_interest,
            sum(a.should_fine) as should_fine,
            max(a.should_time) as should_time
        from ods.s02_loan_repayment a
        left join ods.s02_loan b
            on a.camera_id = b.camera_id
        where b.state in (1, 2, 3)
        group by 1, 2, 3
    )
),
repay as (
    select
        a.camera_id,
        a.rid,
        sum(a.fact_capital) as fact_capital,
        sum(a.fact_interest) as fact_interest,
        sum(a.fact_fine) as fact_fine,
        sum(
            case
                when date(a.fact_time) <= interval '7' day + date(should_time)
                 and date(should_time) + interval '7' day < current_date then a.fact_capital
            end
        ) as t7_fact_capital,
        sum(
            case
                when date(a.fact_time) <= interval '7' day + date(should_time)
                 and date(should_time) + interval '7' day < current_date then a.fact_capital + a.fact_interest
            end
        ) as t7_fact_amt,
        sum(
            case
                when date(a.fact_time) <= interval '30' day + date(should_time)
                 and date(should_time) + interval '30' day < current_date then a.fact_capital
            end
        ) as t30_fact_capital,
        sum(
            case
                when date(a.fact_time) <= interval '30' day + date(should_time)
                 and date(should_time) + interval '30' day < current_date then a.fact_capital + a.fact_interest
            end
        ) as t30_fact_amt
    from ods.s02_loan_repayment_detail a
    group by 1, 2
)
select
    cast(t2.camera_id as varchar) as camera_id,
    cast(t2.rid as varchar) as rid,
    t2.fact_time,
    t2.should_time as should_time_ins,
    t2.should_capital,
    t2.should_interest,
    t2.should_fine,
    t2.should_capital + t2.should_interest as should_amt,
    t2.t7_should_amt,
    t2.t30_should_amt,
    t2.t7_should_capital,
    t2.t30_should_capital,
    t3.fact_capital,
    t3.fact_interest,
    t3.fact_fine,
    coalesce(t3.t7_fact_amt, 0) + coalesce(t4.t7_subtract_amt, 0) + coalesce(t4.t7_coupon_amt, 0) as t7_fact_amt_coup,
    coalesce(t3.t30_fact_amt, 0) + coalesce(t4.t30_subtract_amt, 0) + coalesce(t4.t30_coupon_amt, 0) as t30_fact_amt_coup,
    coalesce(t3.t7_fact_capital, 0) + coalesce(t4.t7_subtract_amt, 0) + coalesce(t4.t7_coupon_amt, 0) as t7_fact_capital_coup,
    coalesce(t3.t30_fact_capital, 0) + coalesce(t4.t30_subtract_amt, 0) + coalesce(t4.t30_coupon_amt, 0) as t30_fact_capital_coup,
    t3.t7_fact_amt,
    t3.t30_fact_amt,
    t3.t7_fact_capital,
    t3.t30_fact_capital,
    t4.now_subtract_amt,
    t4.now_coupon_amt
from should t2
left join repay t3
    on t2.rid = t3.rid
left join coupon t4
    on t2.rid = t4.rid;
""", "5. 还款/T7/T30")
check_table("mx.ys_dl_ltv_repay")

# =========================================================
# 5b. 还款订单聚合（修复 camera_id 格式）
# =========================================================

exec_sql("""

drop table if exists mx.ys_dl_ltv_repay_order;
create table mx.ys_dl_ltv_repay_order as
select 
    cast(TRY_CAST(t.camera_id AS BIGINT) as varchar) as camera_id,
    max(rid) as rid,
    max(fact_time) as fact_time,
    max(should_time_ins) as should_time_ins,
    sum(should_capital) as should_capital,
    sum(should_interest) as should_interest,
    sum(should_fine) as should_fine,
    sum(should_amt) as should_amt,
    sum(t7_should_amt) as t7_should_amt,
    sum(t30_should_amt) as t30_should_amt,
    sum(t7_should_capital) as t7_should_capital,
    sum(t30_should_capital) as t30_should_capital,
    sum(fact_capital) as fact_capital,
    sum(fact_interest) as fact_interest,
    sum(fact_fine) as fact_fine,
    sum(t7_fact_amt_coup) as t7_fact_amt_coup,
    sum(t30_fact_amt_coup) as t30_fact_amt_coup,
    sum(t7_fact_capital_coup) as t7_fact_capital_coup,
    sum(t30_fact_capital_coup) as t30_fact_capital_coup,
    sum(t7_fact_amt) as t7_fact_amt,
    sum(t30_fact_amt) as t30_fact_amt,
    sum(t7_fact_capital) as t7_fact_capital,
    sum(t30_fact_capital) as t30_fact_capital,
    sum(now_subtract_amt) as now_subtract_amt,
    sum(now_coupon_amt) as now_coupon_amt
from mx.ys_dl_ltv_repay t 
where camera_id is not null
group by 1; 
""", "5b. 还款订单聚合（修复 camera_id 格式）")
check_table("mx.ys_dl_ltv_repay_order")

# =========================================================
# 6. 首贷 LTV 明细
# =========================================================

exec_sql("""
drop table if exists mx.ys_dl_ltv_first_loan_0511;
create table mx.ys_dl_ltv_first_loan_0511 as
select
    date_trunc('month', date(r.release_time)) as ltv_month,
    date_trunc('week', date(r.release_time)) as ltv_week,
    cast(r.cust_id as bigint) as mid,
    r.app_group as app_channel_name,
    r.app_channel as cost_app_channel,
    case
        when lower(att.new_media_source) = 'facebook' then 'facebook'
        when lower(att.new_media_source) = 'google' then 'google'
        when lower(att.new_media_source) = 'tiktok' then 'tiktok'
        when lower(att.new_media_source) = 'apple search ads' then 'Apple Search Ads'
        when lower(att.new_media_source) = 'organic' then 'organic'
        else 'other'
    end as register_media_source,
    r.camera_id as order_no,
    r.camera_id as lid,
    r.loan_cycle,
    case when coalesce(r.haircut_amount, 0) > 0 then '前置' else '后置' end as fee_type,
    (coalesce(r.haircut_amount, 0) + coalesce(r.should_interest, 0)) / nullif(r.contract_amount, 0) as fee,
    r.contract_amount,
    coalesce(r.should_interest, 0) + coalesce(r.should_capital, 0) as should_amt,
    coalesce(f7.credit_level, 9999) as new_grade_level,
    r.t7_should_amt_4 as should_amt_t7,
    r.t30_should_amt_4 as should_amt_t30,
    r.t7_should_capit_4 as contract_t7,
    r.t30_should_capit_4 as contract_t30,
    r.t7_fact_amt as fact_t7,
    r.t7_fact_amt as fact_t7_coup,
    r.t30_fact_amt as fact_t30,
    r.t30_fact_amt as fact_t30_coup,
    case when r.t0_fact_amt > 0 then 1 else 0 end as fact_cnt_t0,
    case when r.t7_fact_amt > 0 then 1 else 0 end as fact_cnt_t7,
    case when r.t30_fact_amt > 0 then 1 else 0 end as fact_cnt_t30,
    case when r.now_fact_amt > 0 then 1 else 0 end as fact_cnt_till_now,
    cast(0 as bigint) as re_zr_cnt_t30
from mx.wxs_application_funnel r
left join ods.s02_loan t on r.camera_id = t.camera_id
left join mx.report_application_funnel7_table f7 on r.camera_id = cast(f7.biz_id as bigint)
left join mx.gm_attribution_detail att on cast(r.cust_id as bigint) = att.mid
where r.is_reloan = 'new'
  and r.if_issue = 1;
""", "6. 首贷 LTV 明细")
check_table("mx.ys_dl_ltv_first_loan_0511")

# =========================================================
# 6b. 首贷聚合（匹配尼日输出格式）
# =========================================================

exec_sql("""
drop table if exists mx.ys_mx_ltv_first_loan_cac;
create table mx.ys_mx_ltv_first_loan_cac as
with first_loan_agg as (
    select
        ltv_month,
        loan_cycle,
        app_channel_name,
        new_grade_level,
        count(distinct mid) as frs_cnt,
        sum(contract_amount) as contract_amount,
        sum(contract_amount) / nullif(count(distinct lid), 0) as avg_amount,
        sum(fee * contract_amount) / nullif(sum(contract_amount), 0) as fee,
        sum(fee * contract_amount) as fee_amount,
        sum(should_amt) as should_amt,
        sum(should_amt_t7) as should_amt_t7,
        sum(should_amt_t30) as should_amt_t30,
        sum(contract_t7) as contract_t7,
        sum(contract_t30) as contract_t30,
        sum(fact_t7) as fact_t7,
        sum(fact_t7_coup) as fact_t7_coup,
        sum(fact_t30) as fact_t30,
        sum(fact_t30_coup) as fact_t30_coup,
        sum(fact_cnt_t0) as fact_cnt_t0,
        sum(fact_cnt_t7) as fact_cnt_t7,
        sum(fact_cnt_t30) as fact_cnt_t30,
        sum(fact_cnt_till_now) as fact_cnt_till_now,
        sum(re_zr_cnt_t30) as re_zr_cnt_t30,
        cost_app_channel,
        register_media_source
    from mx.ys_dl_ltv_first_loan_0511
    group by 1, 2, 3, 4, 19, 20
),
cost as (
    select
        cost_month,
        app_channel,
        case
            when new_media_source in ('facebook', 'Google', 'tiktok', 'Apple Search Ads', 'organic') then new_media_source
            else 'other'
        end as new_media_source,
        sum(spend_usd) as spend_usd
    from mx.ys_mx_ltv_ads_cost
    group by 1, 2, 3
),
total_cost as (
    select
        cost_month,
        sum(spend_usd) as total_spend_usd
    from mx.ys_mx_ltv_ads_cost
    group by 1
),
cost_rank as (
    select
        ltv_month,
        app_channel_name,
        new_grade_level,
        loan_cycle,
        row_number() over(partition by ltv_month order by contract_amount desc) as cost_rnk
    from first_loan_agg
)
select
    f.ltv_month,
    f.loan_cycle,
    f.app_channel_name,
    f.new_grade_level,
    f.frs_cnt,
    f.contract_amount,
    round(f.avg_amount, 2) as avg_amount,
    round(f.fee, 4) as fee,
    round(f.fee_amount, 2) as fee_amount,
    f.should_amt,
    f.should_amt_t7,
    f.should_amt_t30,
    f.contract_t7,
    f.contract_t30,
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
    cast(0 as double) as total_spend_ngn,
    coalesce(t.total_spend_usd, 0) as total_spend_usd,
    cast(0 as double) as spend_ngn,
    coalesce(c.spend_usd, 0) as spend_usd
from first_loan_agg f
left join cost c
    on f.ltv_month = c.cost_month
   and f.cost_app_channel = c.app_channel
   and f.register_media_source = c.new_media_source
left join total_cost t
    on f.ltv_month = t.cost_month
left join cost_rank cr
    on f.ltv_month = cr.ltv_month
   and f.app_channel_name = cr.app_channel_name
   and f.new_grade_level = cr.new_grade_level
   and f.loan_cycle = cr.loan_cycle;
""", "6b. 首贷聚合（匹配尼日输出格式）")
check_table("mx.ys_mx_ltv_first_loan_cac")

# =========================================================
# 7. 复贷 LTV 明细（基于wxs_application_funnel）
# =========================================================

exec_sql("""
drop table if exists mx.ys_dl_ltv_doulbe_loan_0511;
create table mx.ys_dl_ltv_doulbe_loan_0511 as
select
    cast(null as date) as zr_date,
    cast(r.cust_id as bigint) as zr_mid,
    cast(null as varchar) as zr_result,
    cast(0 as integer) as zr_rank,
    cast(null as varchar) as zr_id,
    cast(null as varchar) as is_t30_zhunru,
    cast(null as date) as qz_date,
    cast(r.cust_id as bigint) as qz_mid,
    cast(null as varchar) as pre_credit_result,
    cast(0 as integer) as qz_rank,
    cast(null as varchar) as qz_id,
    cast(r.cust_id as bigint) as apply_mid,
    cast(null as date) as apply_date,
    cast(0 as integer) as status,
    cast(0 as integer) as apply_rank,
    cast(null as varchar) as apply_id,
    r.loan_cycle as loan_period,
    date_trunc('month', date(r.release_time)) as release_month,
    date_trunc('week', date(r.release_time)) as release_week,
    d.ltv_month,
    r.app_channel as cost_app_channel,
    case
        when lower(att.new_media_source) = 'facebook' then 'facebook'
        when lower(att.new_media_source) = 'google' then 'google'
        when lower(att.new_media_source) = 'tiktok' then 'tiktok'
        when lower(att.new_media_source) = 'apple search ads' then 'Apple Search Ads'
        when lower(att.new_media_source) = 'organic' then 'organic'
        else 'other'
    end as register_media_source,
    date_diff('week', d.ltv_week, date_trunc('week', date(r.release_time))) as wob,
    cast(r.cust_id as bigint) as mid,
    r.app_group as app_channel_name,
    coalesce(f7.credit_level, 9999) as new_grade_level,
    r.camera_id as lid,
    date(r.release_time) as trade_start_date,
    date(date_add('day', r.loan_cycle, r.release_time)) as trade_end_date,
    cast(null as timestamp) as finish_time,
    cast(0 as integer) as rank,
    cast(0 as integer) as is_T30_wp,
    cast(0 as integer) as is_T7_wp,
    r.loan_cycle,
    case when coalesce(r.haircut_amount, 0) > 0 then '前置' else '后置' end as fee_type,
    (coalesce(r.haircut_amount, 0) + coalesce(r.should_interest, 0)) / nullif(r.contract_amount, 0) as fee,
    r.contract_amount as contract_amt,
    coalesce(r.should_interest, 0) + coalesce(r.should_capital, 0) as should_amt,
    cast(null as varchar) as lid_status_code,
    cast(null as varchar) as rid,
    cast(null as timestamp) as fact_time,
    cast(0 as double) as fact_capital,
    cast(0 as double) as fact_interest,
    cast(0 as double) as now_subtract_amt,
    cast(0 as double) as now_coupon_amt,
    r.t7_should_amt_4 as t7_should_amt,
    r.t30_should_amt_4 as t30_should_amt,
    r.t7_should_capit_4 as t7_should_capital,
    r.t30_should_capit_4 as t30_should_capital,
    r.t7_fact_amt as t7_fact_amt,
    r.t7_fact_amt as t7_fact_amt_coup,
    r.t30_fact_amt as t30_fact_amt,
    r.t30_fact_amt as t30_fact_amt_coup,
    cast(null as varchar) as rz_id,
    cast(null as timestamp) as rz_time,
    cast(1 as bigint) as l_rnk,
    cast(1 as bigint) as r_rnk
from mx.wxs_application_funnel r
left join mx.ys_dl_ltv_first_loan_0511 d
    on cast(r.cust_id as bigint) = d.mid
left join mx.gm_attribution_detail att
    on cast(r.cust_id as bigint) = att.mid
left join mx.report_application_funnel7_table f7
    on r.camera_id = cast(f7.biz_id as bigint)
left join ods.s02_loan t
    on r.camera_id = t.camera_id
where r.is_reloan = 'old'
  and r.if_issue = 1
  and d.mid is not null;
""", "7. 复贷 LTV 明细（基于wxs_application_funnel）")
check_table("mx.ys_dl_ltv_doulbe_loan_0511")

# =========================================================
# 8. 复贷 RAW 聚合（通过率等字段置0）
# =========================================================

exec_sql("""
drop table if exists mx.ys_dl_ltv_double_loan_group;
create table mx.ys_dl_ltv_double_loan_group as
with base as (
    select
        ltv_month,
        wob,
        app_channel_name,
        loan_period,
        new_grade_level,
        lid,
        mid,
        contract_amt,
        fee,
        trade_end_date,
        should_amt,
        t7_should_amt,
        t30_should_amt,
        t7_should_capital,
        t30_should_capital,
        t7_fact_amt,
        t7_fact_amt_coup,
        t30_fact_amt,
        t30_fact_amt_coup,
        loan_cycle,
        (loan_cycle = 7) as is_7d,
        (loan_cycle = 14) as is_14d,
        (trade_end_date < current_date) as is_trade_end_t0,
        (trade_end_date + interval '7' day < current_date) as is_trade_end_t7,
        (trade_end_date + interval '30' day < current_date) as is_trade_end_t30
    from mx.ys_dl_ltv_doulbe_loan_0511
)
select
    ltv_month as ltv_month_d,
    wob as wob_d,
    app_channel_name as app_channel_name_d,
    loan_period,
    new_grade_level as new_grade_level_d,
    count(distinct lid) as double_cnt,
    count(distinct mid) as double_mid,
    sum(contract_amt) as contract_amount,
    sum(fee * contract_amt) as fee_amount,
    sum(contract_amt) / nullif(count(distinct lid), 0) as avg_amount,
    sum(case when is_trade_end_t0 then should_amt end) as should_amt_t0,
    sum(case when is_trade_end_t7 then coalesce(t7_should_amt, should_amt) end) as should_amt_t7,
    sum(case when is_trade_end_t30 then coalesce(t30_should_amt, should_amt) end) as should_amt_t30,
    sum(case when is_trade_end_t0 then contract_amt end) as contract_t0,
    sum(case when is_trade_end_t7 then coalesce(t7_should_capital, contract_amt) end) as contract_t7,
    sum(case when is_trade_end_t30 then coalesce(t30_should_capital, contract_amt) end) as contract_t30,
    count(distinct case when is_trade_end_t0 then lid end) as should_cnt_t0,
    count(distinct case when is_trade_end_t7 then lid end) as should_cnt_t7,
    cast(0 as double) as fact_t0,
    sum(case when is_trade_end_t7 then t7_fact_amt end) as fact_t7,
    sum(case when is_trade_end_t7 then coalesce(t7_fact_amt_coup, t7_fact_amt) end) as fact_t7_coup,
    sum(case when is_trade_end_t30 then t30_fact_amt end) as fact_t30,
    sum(case when is_trade_end_t30 then coalesce(t30_fact_amt_coup, t30_fact_amt) end) as fact_t30_coup,
    cast(0 as bigint) as fact_cnt_t0,
    count(distinct case when is_trade_end_t7 and t7_fact_amt >= t7_should_amt then lid end) as fact_cnt_t7,
    count(distinct case when is_trade_end_t30 and t30_fact_amt >= t30_should_amt then lid end) as fact_cnt_t30,
    count(distinct lid) as fact_cnt_till_now,
    sum(case when is_7d then contract_amt end) as contract_amount_7d,
    sum(case when is_14d then contract_amt end) as contract_amount_14d,
    sum(case when is_7d and is_trade_end_t30 then coalesce(t30_should_amt, should_amt) end) as should_amt_7d,
    sum(case when is_14d and is_trade_end_t30 then coalesce(t30_should_amt, should_amt) end) as should_amt_14d,
    sum(case when is_7d and is_trade_end_t30 then t30_fact_amt end) as fact_t30_7d,
    sum(case when is_14d and is_trade_end_t30 then t30_fact_amt end) as fact_t30_14d,
    count(distinct case when is_7d then lid end) as double_cnt_7d,
    count(distinct case when is_14d then lid end) as double_cnt_14d,
    sum(case when is_7d then contract_amt end) / nullif(count(distinct case when is_7d then lid end), 0) as avg_amount_7d,
    sum(case when is_14d then contract_amt end) / nullif(count(distinct case when is_14d then lid end), 0) as avg_amount_14d,
    cast(0 as bigint) as zr_mid,
    cast(0 as bigint) as zr_pass_mid,
    cast(0 as bigint) as zr_cnt,
    cast(0 as bigint) as zr_pass_cnt,
    cast(0 as bigint) as qz_mid,
    cast(0 as bigint) as qz_pass_mid,
    cast(0 as bigint) as qz_cnt,
    cast(0 as bigint) as qz_pass_cnt,
    cast(0 as bigint) as apply_mid,
    cast(0 as bigint) as apply_pass_mid,
    cast(0 as bigint) as apply_cnt,
    cast(0 as bigint) as apply_pass_cnt,
    cast(0 as bigint) as fact_cnt_t7_for_rzt30,
    cast(0 as bigint) as fact_cnt_t7_for_rzt7,
    cast(0 as bigint) as re_zr_cnt_t30,
    cast(0 as bigint) as re_zr_cnt_t7
from base
group by 1, 2, 3, 4, 5;
""", "8. 复贷 RAW 聚合（通过率等字段置0）")
check_table("mx.ys_dl_ltv_double_loan_group")

# =========================================================
# 9. WOB 补全
# =========================================================

exec_sql("""
drop table if exists mx.ys_dl_ltv_double_loan_draw;
create table mx.ys_dl_ltv_double_loan_draw as
with frst_loan as (
    select
        ltv_month,
        app_channel_name,
        new_grade_level,
        count(distinct mid) as frs_cnt,
        sum(contract_amount) as frs_contract_amount
    from mx.ys_dl_ltv_first_loan_0511
    group by 1, 2, 3
),
maxwob as (
    select coalesce(max(wob_d), 110) as max_wob
    from mx.ys_dl_ltv_double_loan_group
),
wob_range as (
    select wob
    from maxwob
    cross join unnest(sequence(0, least(max_wob, 110))) as t(wob)
),
all_groups as (
    select distinct
        ltv_month,
        app_channel_name,
        new_grade_level
    from frst_loan
),
all_combinations as (
    select
        g.ltv_month,
        g.app_channel_name,
        g.new_grade_level,
        w.wob
    from all_groups g
    cross join wob_range w
),
double_combinations as (
    select
        c.ltv_month,
        c.app_channel_name,
        c.new_grade_level,
        c.wob,
        a.*,
        row_number() over(
            partition by c.ltv_month, c.app_channel_name, c.new_grade_level, c.wob
        ) as double_rnk
    from all_combinations c
    left join mx.ys_dl_ltv_double_loan_group a
        on a.ltv_month_d = c.ltv_month
       and a.app_channel_name_d = c.app_channel_name
       and a.new_grade_level_d = c.new_grade_level
       and a.wob_d = c.wob
)
select
    c.*,
    b.frs_cnt,
    b.frs_contract_amount,
    row_number() over(
        order by c.ltv_month, c.wob, c.app_channel_name, c.loan_period, c.new_grade_level
    ) as rnk
from double_combinations c
left join frst_loan b
    on c.ltv_month = b.ltv_month
   and c.app_channel_name = b.app_channel_name
   and c.new_grade_level = b.new_grade_level
   and c.double_rnk = 1
where c.wob <= 110;
""", "9. WOB 补全")
check_table("mx.ys_dl_ltv_double_loan_draw")

# =========================================================
# 10. 90天复借率校验
# =========================================================

exec_sql("""
drop table if exists mx.ys_mx_ltv_reloan_90d_check;
create table mx.ys_mx_ltv_reloan_90d_check as
with first_loans as (
    select
        date_trunc('month', release_time) as issue_month,
        mid,
        release_time,
        contract_amount
    from mx.ys_mx_ltv_base_loan
    where double_loan = 0
      and release_time >= timestamp '2025-07-01 00:00:00'
      and loan_state in (1, 2, 3)
),
reloans as (
    select
        mid,
        biz_id,
        release_time,
        contract_amount
    from mx.ys_mx_ltv_base_loan
    where double_loan = 1
      and release_time >= timestamp '2025-07-01 00:00:00'
      and loan_state in (1, 2, 3)
)
select
    a.issue_month,
    count(distinct a.mid) as first_loan_cnt,
    count(distinct b.biz_id) as reloan_bizid_cnt_90d,
    count(distinct b.mid) as reloan_mid_cnt_90d,
    sum(b.contract_amount) as reloan_amount_90d_mxn,
    round(count(distinct b.biz_id) * 1.0 / nullif(count(distinct a.mid), 0), 4) as reloan_rate_biz,
    round(count(distinct b.mid) * 1.0 / nullif(count(distinct a.mid), 0), 4) as reloan_rate_mid
from first_loans a
left join reloans b
    on a.mid = b.mid
   and b.release_time > a.release_time
   and date_diff('day', a.release_time, b.release_time) <= 90
group by 1;
""", "10. 90天复借率校验")
check_table("mx.ys_mx_ltv_reloan_90d_check")

# =========================================================
# 11. 通过率校验
# =========================================================

exec_sql("""
drop table if exists mx.ys_mx_ltv_pass_rate_check;
create table mx.ys_mx_ltv_pass_rate_check as
with base as (
    select *
    from mx.daily_order_base
),
processor_flags as (
    select
        biz_id,
        max(case when current_processor in ('复贷授信拒绝') then 1 else 0 end) as if_in_fu_sx_refuse,
        case
            when sum(case when current_processor in ('首贷模型拒绝', '复贷模型拒绝') and approve_result = 'REFUSED' then 1 else 0 end) >= 1 then 0
            when sum(case when current_processor in ('首贷模型拒绝', '复贷模型拒绝') then 1 else 0 end) >= 1 then 1
            else 0
        end as if_model_passed,
        max(case when current_processor in ('首贷授信节点', '复贷授信节点') then 1 else 0 end) as if_in_confirm,
        max(case when current_processor in ('首贷授信等待节点', '复贷授信等待节点', '授信等待节点') then 1 else 0 end) as if_in_ruleDetermine_data,
        case
            when sum(case when current_processor in ('首贷授信等待节点', '复贷授信等待节点', '授信等待节点') and approve_result = 'PASSED' then 1 else 0 end) >= 1 then 1
            else 0
        end as if_normal_ruleDetermine_passed,
        case
            when sum(case when current_processor in ('首贷三方节点', '复贷三方节点') and approve_result = 'REFUSED' then 1 else 0 end) >= 1 then 0
            when sum(case when current_processor in ('首贷三方节点', '复贷三方节点') then 1 else 0 end) >= 1 then 1
            else 0
        end as if_external_data_passed
    from ods.s05_creditx_processor_record
    group by 1
),
global_limit_exclude as (
    select externalid as biz_id
    from ods.s21_risk_strategy_record
    where etl_date >= '20250226'
      and productid = 194
      and strategytype = 'CHAMPION'
      and cast(json_extract(outputdata, '$.available_limit_zero_mark') as int) = 1
      and cast(json_extract(outputdata, '$.global_limit_mark') as int) = 1
    group by 1
)
select
    b.create_date as data_date,
    b.app_channel,
    b.double_loan_new,
    b.reloan_num,
    b.product_name,
    b.os,
    b.new_media_source,
    count(distinct b.biz_id) as apply_cnt,
    count(distinct case when b.order_status = 372 then b.biz_id end) as pass_cnt,
    count(distinct case when pf.if_model_passed = 1 then b.biz_id end) as if_model_passed,
    count(distinct case when pf.if_in_ruleDetermine_data = 1 then b.biz_id end) as if_in_ruleDetermine_data,
    count(distinct case when pf.if_in_fu_sx_refuse = 1 then b.biz_id end) as if_in_fu_sx_refuse,
    count(distinct case when pf.if_normal_ruleDetermine_passed = 1 then b.biz_id end) as rule_determine_passed_cnt,
    count(distinct case when pf.if_external_data_passed = 1 then b.biz_id end) as if_external_data_passed,
    count(distinct case when pf.if_in_confirm = 1 then b.biz_id end) as if_in_confirm,
    round(count(distinct case when pf.if_model_passed = 1 then b.biz_id end) * 1.0 / nullif(count(distinct b.biz_id), 0), 4) as model_pass_rate,
    round(count(distinct case when b.order_status = 372 then b.biz_id end) * 1.0 / nullif(count(distinct case when pf.if_in_ruleDetermine_data = 1 then b.biz_id end), 0), 4) as post_pass_rate
from base b
left join processor_flags pf
    on b.biz_id = pf.biz_id
left join global_limit_exclude ge
    on b.biz_id = ge.biz_id
where b.create_date >= date '2025-01-01'
  and ge.biz_id is null
group by 1, 2, 3, 4, 5, 6, 7;
""", "11. 通过率校验")
check_table("mx.ys_mx_ltv_pass_rate_check")

# =========================================================
# 12. 最终校验与结果输出
# =========================================================

print("\n" + "="*60)
print("最终校验与结果输出")
print("="*60)

all_tables = [
    "mx.ys_mx_ltv_base_funnel",
    "mx.ys_mx_ltv_base_loan",
    "mx.ys_dl_ltv_exchange_rate",
    "mx.ys_mx_ltv_ads_cost",
    "mx.ys_dl_ltv_zr",
    "mx.ys_dl_ltv_qz_danti",
    "mx.ys_dl_ltv_apply",
    "mx.ys_dl_ltv_repay",
    "mx.ys_dl_ltv_repay_order",
    "mx.ys_dl_ltv_first_loan_0511",
    "mx.ys_mx_ltv_first_loan_cac",
    "mx.ys_dl_ltv_doulbe_loan_0511",
    "mx.ys_dl_ltv_double_loan_group",
    "mx.ys_dl_ltv_double_loan_draw",
    "mx.ys_mx_ltv_reloan_90d_check",
    "mx.ys_mx_ltv_pass_rate_check",
]

print("\n所有表数据汇总:")
table_results = []
for table in all_tables:
    cnt = check_table(table)
    table_results.append({"表名": table, "行数": cnt})

print("\n关键指标校验:")

check_results = {}

result = pq.query("""
select ltv_month, count(*) as first_loan_cnt, sum(contract_amount) as first_contract_amount
from mx.ys_dl_ltv_first_loan_0511
group by 1
order by 1 desc
limit 10
""")
if isinstance(result, pd.DataFrame):
    print("\n首贷量(最近10个月):")
    print(result.to_string())
    check_results["首贷量"] = result

result = pq.query("""
select * from mx.ys_mx_ltv_reloan_90d_check
order by issue_month desc
""")
if isinstance(result, pd.DataFrame):
    print("\n90天复借率:")
    print(result.to_string())
    check_results["90天复借率"] = result

result = pq.query("""
select
    ltv_month,
    sum(should_amt_t7) as should_amt_t7,
    sum(should_amt_t7 - fact_t7) / nullif(sum(should_amt_t7), 0) as bad_t7,
    sum(should_amt_t30) as should_amt_t30,
    sum(should_amt_t30 - fact_t30) / nullif(sum(should_amt_t30), 0) as bad_t30
from mx.ys_dl_ltv_first_loan_0511
group by 1
order by 1 desc
limit 12
""")
if isinstance(result, pd.DataFrame):
    print("\nT7/T30坏账率(最近12个月):")
    print(result.to_string())
    check_results["T7/T30坏账率"] = result

result = pq.query("""
select
    date(data_date) as month,
    double_loan_new,
    sum(apply_cnt) as apply_cnt,
    sum(if_model_passed) as if_model_passed,
    sum(pass_cnt) as pass_cnt,
    sum(if_in_ruleDetermine_data) as if_in_ruleDetermine_data,
    round(sum(if_model_passed) * 1.0 / nullif(sum(apply_cnt), 0), 4) as model_pass_rate,
    round(sum(pass_cnt) * 1.0 / nullif(sum(if_in_ruleDetermine_data), 0), 4) as post_pass_rate
from mx.ys_mx_ltv_pass_rate_check
group by 1, 2
order by 1 desc, 2
limit 10
""")
if isinstance(result, pd.DataFrame):
    print("\n通过率(最近5个月):")
    print(result.to_string())
    check_results["通过率"] = result

output_path = r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥经分\墨西哥LTV完整执行结果.xlsx"
with pd.ExcelWriter(output_path) as writer:
    pd.DataFrame(table_results).to_excel(writer, sheet_name="表数据汇总", index=False)
    for name, df in check_results.items():
        clean_name = name.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace("[", "_").replace("]", "_")
        df.to_excel(writer, sheet_name=clean_name, index=False)

print(f"\n结果已保存到: {output_path}")
print("\n" + "="*60)
print("墨西哥LTV完整执行流程结束")
print("="*60)