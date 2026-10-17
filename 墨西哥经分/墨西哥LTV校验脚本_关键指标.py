"""墨西哥LTV校验脚本 - 关键指标对比"""
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
            print(result.to_string())
        else:
            print(f"  执行完成: {result}")
        return result
    except Exception as e:
        print(f"  错误: {e}")
        return None

print("="*60)
print("墨西哥LTV数据校验 - 关键指标对比")
print("="*60)

exec_sql("""
select '当前代码-首贷' as source, ltv_month, count(*) as cnt, sum(contract_amount) as total_amount
from mx.ys_dl_ltv_first_loan_0511
group by 1, 2
order by 2 desc
limit 12
""", "1. 当前代码 - 首贷放款规模(按月)")

exec_sql("""
select '参考代码-ods.s02_loan' as source, date_trunc('month', date(t.release_time)) as ltv_month, 
       count(*) as cnt, sum(t.contract_amount) as total_amount
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
where rt.double_loan = 0 and t.state in (1,2,3)
group by 1, 2
order by 2 desc
limit 12
""", "2. 参考代码(ods.s02_loan) - 首贷放款规模(按月)")

exec_sql("""
select '当前代码-复贷' as source, ltv_month, count(*) as cnt, sum(contract_amount) as total_amount
from mx.ys_dl_ltv_doulbe_loan_0511
group by 1, 2
order by 2 desc
limit 12
""", "3. 当前代码 - 复贷放款规模(按月)")

exec_sql("""
select '参考代码-ods.s02_loan' as source, date_trunc('month', date(t.release_time)) as ltv_month, 
       count(*) as cnt, sum(t.contract_amount) as total_amount
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
where rt.double_loan = 1 and t.state in (1,2,3)
group by 1, 2
order by 2 desc
limit 12
""", "4. 参考代码(ods.s02_loan) - 复贷放款规模(按月)")

exec_sql("""
select '数据源对比' as source, 
       '当前代码(mx.wxs_application_funnel)' as data_source,
       count(*) as total_cnt, 
       sum(contract_amount) as total_amount
from mx.wxs_application_funnel
where is_reloan = 'new' and if_issue = 1
union all
select '数据源对比' as source, 
       '参考代码(ods.s02_loan)' as data_source,
       count(*) as total_cnt, 
       sum(t.contract_amount) as total_amount
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
where rt.double_loan = 0 and t.state in (1,2,3)
""", "5. 数据源对比 - 首贷总量")

exec_sql("""
select '数据源对比' as source, 
       '当前代码(mx.wxs_application_funnel)' as data_source,
       count(*) as total_cnt, 
       sum(contract_amount) as total_amount
from mx.wxs_application_funnel
where is_reloan = 'old' and if_issue = 1
union all
select '数据源对比' as source, 
       '参考代码(ods.s02_loan)' as data_source,
       count(*) as total_cnt, 
       sum(t.contract_amount) as total_amount
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
where rt.double_loan = 1 and t.state in (1,2,3)
""", "6. 数据源对比 - 复贷总量")

exec_sql("""
select '当前代码' as source, ltv_month, wob, sum(contract_amount) as double_contract_amount
from mx.ys_dl_ltv_double_loan_group
where ltv_month >= date '2025-06-01'
group by 1, 2, 3
order by 2, 3
limit 30
""", "7. 当前代码 - 首贷放款月对应的WOB复贷金额(2025年6月后)")

exec_sql("""
select '参考代码' as source, a.dt_week, date_diff('week', a.dt_week, b.dt_week) as wk_diff,
       sum(b.contract_amount) as fu_contract_amt
from (
    select distinct date(t.release_time) dt, date_add('day',-day_of_week(date(t.release_time))+1,date(t.release_time)) as dt_week,
           t.customer_id, t.contract_amount
    from ods.s02_loan t
    inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
    where rt.double_loan = 0 and t.state in (1,2,3)
) a
left join (
    select distinct date(t.release_time) dt, date_add('day',-day_of_week(date(t.release_time))+1,date(t.release_time)) as dt_week,
           t.customer_id, t.contract_amount
    from ods.s02_loan t
    inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
    where rt.double_loan = 1 and t.state in (1,2,3)
) b on a.customer_id = b.customer_id
where a.dt_week >= date '2025-06-01'
  and date_diff('week', a.dt_week, b.dt_week) >= 0
group by 1, 2, 3
order by 2, 3
limit 30
""", "8. 参考代码 - 首贷放款周对应的WK_DIFF复贷金额(2025年6月后)")

exec_sql("""
select '当前代码-首贷' as source, ltv_month, app_channel_name, sum(contract_amount) as total_amount,
       count(distinct biz_id) as cnt
from mx.ys_dl_ltv_first_loan_0511
group by 1, 2, 3
order by 1 desc, 4 desc
limit 20
""", "9. 当前代码 - 首贷按渠道分布")

exec_sql("""
select '参考代码-首贷' as source, date_trunc('month', date(t.release_time)) as ltv_month, 
       t.app_channel, sum(t.contract_amount) as total_amount, count(*) as cnt
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
where rt.double_loan = 0 and t.state in (1,2,3)
group by 1, 2, 3
order by 1 desc, 4 desc
limit 20
""", "10. 参考代码 - 首贷按渠道分布")

exec_sql("""
select '当前代码-首贷' as source, ltv_month, 
       sum(case when loan_cycle = 7 then contract_amount end) as amount_7d,
       sum(case when loan_cycle = 14 then contract_amount end) as amount_14d,
       count(case when loan_cycle = 7 then biz_id end) as cnt_7d,
       count(case when loan_cycle = 14 then biz_id end) as cnt_14d
from mx.ys_dl_ltv_first_loan_0511
group by 1, 2
order by 2 desc
limit 10
""", "11. 当前代码 - 首贷按期限分布")

exec_sql("""
select '参考代码-首贷' as source, date_trunc('month', date(t.release_time)) as ltv_month, 
       sum(case when t.loan_cycle = 7 then t.contract_amount end) as amount_7d,
       sum(case when t.loan_cycle = 14 then t.contract_amount end) as amount_14d,
       count(case when t.loan_cycle = 7 then t.camera_id end) as cnt_7d,
       count(case when t.loan_cycle = 14 then t.camera_id end) as cnt_14d
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
where rt.double_loan = 0 and t.state in (1,2,3)
group by 1, 2
order by 2 desc
limit 10
""", "12. 参考代码 - 首贷按期限分布")

exec_sql("""
select '当前代码-WOB分布' as source, wob, count(*) as cnt, sum(contract_amount) as total_amount
from mx.ys_dl_ltv_double_loan_group
group by 1, 2
order by 2
limit 15
""", "13. 当前代码 - WOB分布")

exec_sql("""
select '当前代码-复贷按月' as source, ltv_month, sum(contract_amount) as total_amount, count(*) as cnt
from mx.ys_dl_ltv_doulbe_loan_0511
group by 1, 2
order by 2 desc
limit 12
""", "14. 当前代码 - 复贷按月统计")

exec_sql("""
select '当前代码-首贷复贷对比' as source, f.ltv_month,
       sum(f.contract_amount) as first_contract_amount,
       count(distinct f.biz_id) as first_cnt,
       sum(d.contract_amount) as double_contract_amount,
       count(distinct d.biz_id) as double_cnt,
       sum(d.contract_amount) / nullif(sum(f.contract_amount), 0) as double_ratio
from mx.ys_dl_ltv_first_loan_0511 f
left join mx.ys_dl_ltv_doulbe_loan_0511 d on f.ltv_month = d.ltv_month
group by 1, 2
order by 2 desc
limit 10
""", "15. 当前代码 - 首贷与复贷放款金额对比(按月)")

print("\n" + "="*60)
print("墨西哥LTV数据校验完成")
print("="*60)