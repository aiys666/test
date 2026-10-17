"""直接运行 first_loan 创建SQL"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()
print("登录成功!")

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

print("执行 first_loan DDL...")
result = pq.query(sql)
print(f"结果: {result}")

print("\n检查 first_loan 表:")
try:
    result = pq.query("select count(1) from mx.ys_dl_ltv_first_loan_0511")
    print(f"行数: {result}")
except Exception as e:
    print(f"错误: {e}")
    
try:
    result = pq.query("select * from mx.ys_dl_ltv_first_loan_0511 limit 1")
    print(f"首行: {result}")
except Exception as e:
    print(f"首行错误: {e}")