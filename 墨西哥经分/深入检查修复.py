"""深入检查 repay_order 和 first_loan 无数据问题"""
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

print("===== 检查 repay 表 camera_id 格式 =====")
exec_and_check("""
select camera_id, 
       cast(camera_id as varchar) as str_id,
       length(cast(camera_id as varchar)) as len,
       cast(camera_id as bigint) as bigint_id
from mx.ys_dl_ltv_repay 
where camera_id is not null
limit 5
""", "repay camera_id 格式:")

exec_and_check("""
select count(*) as cnt from mx.ys_dl_ltv_repay where camera_id like '%.%'
""", "camera_id带小数点数量:")

print("\n===== 修复 repay_order 表 =====")
sql = """drop table if exists mx.ys_dl_ltv_repay_order;
create table mx.ys_dl_ltv_repay_order as
select
    regexp_replace(cast(t.camera_id as varchar), '\\.0+$', '') as camera_id,
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
group by 1"""

exec_and_check(sql, "执行 repay_order DDL...")
exec_and_check("select count(*) as cnt from mx.ys_dl_ltv_repay_order", "repay_order 行数:")
exec_and_check("select camera_id, length(camera_id) as len from mx.ys_dl_ltv_repay_order limit 3", "repay_order camera_id 格式:")

print("\n===== 验证 loan 与 repay_order 关联 =====")
exec_and_check("""
select count(*) as cnt from mx.ys_mx_ltv_base_loan l
inner join mx.ys_dl_ltv_repay_order r
    on l.biz_id = r.camera_id
where l.double_loan = 0
""", "首贷loan与repay_order关联数:")

print("\n===== 重新创建首贷LTV明细表 =====")
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
exec_and_check("select count(*) as cnt from mx.ys_dl_ltv_first_loan_0511", "首贷LTV明细表行数:")

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