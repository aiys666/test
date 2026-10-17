"""墨西哥LTV代码修复 - 针对无数据问题"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功!")

def exec_and_check(sql, desc):
    print(f"\n{desc}")
    try:
        result = pq.query(sql)
        if isinstance(result, pd.DataFrame):
            print(result.to_string())
        else:
            print(f"  结果: {result}")
        return result
    except Exception as e:
        print(f"  错误: {e}")
        return None

print("===== 问题1: 修复 loan 表 biz_id 格式 =====")
sql = """drop table if exists mx.ys_mx_ltv_base_loan;
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
  and rt.double_loan in (0, 1)"""

exec_and_check(sql, "执行 loan 表DDL...")
exec_and_check("select biz_id, length(biz_id) as len from mx.ys_mx_ltv_base_loan limit 3", "检查 loan 表 biz_id 格式:")

print("\n===== 问题2: 重新执行复贷准入DDL =====")
sql = """drop table if exists mx.ys_dl_ltv_zr;
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
  and f.biz_id is not null"""

exec_and_check(sql, "执行复贷准入DDL...")
exec_and_check("select count(*) as cnt from mx.ys_dl_ltv_zr", "检查复贷准入表:")

print("\n===== 问题3: 重新执行前置/机审DDL =====")
sql = """drop table if exists mx.ys_dl_ltv_qz_danti;
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
  and f.biz_id is not null"""

exec_and_check(sql, "执行前置/机审DDL...")
exec_and_check("select count(*) as cnt from mx.ys_dl_ltv_qz_danti", "检查前置/机审表:")

print("\n===== 问题4: 重新执行后置申请DDL =====")
sql = """drop table if exists mx.ys_dl_ltv_apply;
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
  and coalesce(f.apply_amount, 0) > 0"""

exec_and_check(sql, "执行后置申请DDL...")
exec_and_check("select count(*) as cnt from mx.ys_dl_ltv_apply", "检查后置申请表:")

print("\n===== 问题5: 修复 repay_order 表 =====")
sql = """drop table if exists mx.ys_dl_ltv_repay_order;
create table mx.ys_dl_ltv_repay_order as
select
    camera_id,
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
from mx.ys_dl_ltv_repay
where camera_id is not null
group by 1"""

exec_and_check(sql, "执行 repay_order DDL...")
exec_and_check("select count(*) as cnt from mx.ys_dl_ltv_repay_order", "检查 repay_order 表:")

print("\n===== 问题6: 修复首贷LTV明细表 =====")
sql = """drop table if exists mx.ys_dl_ltv_first_loan_0511;
create table mx.ys_dl_ltv_first_loan_0511 as
select
    date_trunc('month', date(l.release_time)) as ltv_month,
    date_trunc('week', date(l.release_time)) as ltv_week,
    l.mid,
    coalesce(f.app, l.app_channel, 'unknown') as app_channel_name,
    l.app_channel as cost_app_channel,
    l.register_media_source,
    l.biz_id as order_no,
    l.biz_id as lid,
    l.loan_cycle,
    case when coalesce(l.haircut_amount, 0) > 0 then '前置' else '后置' end as fee_type,
    (coalesce(l.fee_amount, 0) + coalesce(l.interest, 0) + coalesce(l.haircut_amount, 0)) / nullif(l.contract_amount, 0) as fee,
    l.contract_amount,
    coalesce(r.should_amt, l.amount + coalesce(l.fee_amount, 0) + coalesce(l.interest, 0) + coalesce(l.haircut_amount, 0)) as should_amt,
    coalesce(f7.credit_level, 9999) as new_grade_level,
    r.t7_should_amt as should_amt_t7,
    r.t30_should_amt as should_amt_t30,
    r.t7_should_capital as contract_t7,
    r.t30_should_capital as contract_t30,
    r.t7_fact_amt as fact_t7,
    r.t7_fact_amt_coup as fact_t7_coup,
    r.t30_fact_amt as fact_t30,
    r.t30_fact_amt_coup as fact_t30_coup,
    case when r.fact_capital >= r.should_capital then 1 else 0 end as fact_cnt_t0,
    case when r.t7_fact_amt >= r.t7_should_amt then 1 else 0 end as fact_cnt_t7,
    case when r.t30_fact_amt >= r.t30_should_amt then 1 else 0 end as fact_cnt_t30,
    case when l.finish_time is not null then 1 else 0 end as fact_cnt_till_now,
    cast(0 as bigint) as re_zr_cnt_t30
from mx.ys_mx_ltv_base_loan l
left join mx.ys_mx_ltv_base_funnel f
    on l.biz_id = f.biz_id
left join mx.report_application_funnel7_table f7
    on l.biz_id = cast(f7.biz_id as bigint)
left join mx.ys_dl_ltv_repay_order r
    on l.biz_id = r.camera_id
where coalesce(l.double_loan, 0) = 0
  and l.loan_state in (1, 2, 3)"""

exec_and_check(sql, "执行首贷LTV明细DDL...")
exec_and_check("select count(*) as cnt from mx.ys_dl_ltv_first_loan_0511", "检查首贷LTV明细表:")

print("\n===== 最终检查所有表 =====")
tables = [
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
]

print("\n表数据检查:")
for table in tables:
    try:
        result = pq.query(f"select count(*) as cnt from {table}")
        if isinstance(result, pd.DataFrame):
            cnt = result.iloc[0]['cnt']
            print(f"  {table}: {cnt} 行")
        else:
            print(f"  {table}: {result}")
    except Exception as e:
        print(f"  {table}: 错误 - {e}")