"""墨西哥LTV WOB复贷数据校验"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功!")

def exec_sql(sql, desc):
    print(f"\n{'='*70}")
    print(f"【校验指标】{desc}")
    print(f"{'='*70}")
    try:
        result = pq.query(sql)
        if isinstance(result, pd.DataFrame):
            print(f"查询完成，返回 {len(result)} 行")
            print(result.to_string())
            return result
        else:
            print(f"执行完成: {result}")
            return result
    except Exception as e:
        print(f"错误: {e}")
        return None

print("="*70)
print("墨西哥LTV WOB复贷数据校验")
print("="*70)

exec_sql("""
show tables from mx like 'ys_dl_ltv_double_loan%'
""", "0. 查看复贷相关表")

exec_sql("""
select '当前代码' as source, 
       d.ltv_month, 
       date_diff('week', d.ltv_week, date_trunc('week', date(r.release_time))) as wob, 
       count(distinct r.camera_id) as double_cnt,
       sum(r.contract_amount) as double_contract_amount,
       sum(r.contract_amount) / nullif(count(distinct r.camera_id), 0) as avg_amount
from mx.wxs_application_funnel r
inner join mx.ys_dl_ltv_first_loan_0511 d
    on cast(r.cust_id as bigint) = d.mid
where r.is_reloan = 'old'
  and r.if_issue = 1
  and d.ltv_month >= date '2025-06-01'
  and date_diff('week', d.ltv_week, date_trunc('week', date(r.release_time))) <= 20
group by 1, 2, 3
order by 2, 3
limit 50
""", "1. 当前代码 - WOB复贷放款量&件均(按月)")

exec_sql("""
select '参考代码' as source,
       date_trunc('month', a.dt_week) as ltv_month,
       date_diff('week', a.dt_week, b.dt_week) as wob,
       count(distinct b.camera_id) as double_cnt,
       sum(b.contract_amount) as double_contract_amount,
       sum(b.contract_amount) / nullif(count(distinct b.camera_id), 0) as avg_amount
from (
    select distinct date(t.release_time) dt, 
           date_add('day',-day_of_week(date(t.release_time))+1,date(t.release_time)) as dt_week,
           t.customer_id, t.contract_amount
    from ods.s02_loan t
    inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
    where rt.double_loan = 0 and t.state in (1,2,3)
) a
inner join (
    select distinct date(t.release_time) dt, 
           date_add('day',-day_of_week(date(t.release_time))+1,date(t.release_time)) as dt_week,
           t.customer_id, t.camera_id, t.contract_amount
    from ods.s02_loan t
    inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
    where rt.double_loan = 1 and t.state in (1,2,3)
) b on a.customer_id = b.customer_id
where a.dt_week >= date '2025-06-01'
  and date_diff('week', a.dt_week, b.dt_week) >= 0
  and date_diff('week', a.dt_week, b.dt_week) <= 20
group by 1, 2, 3
order by 2, 3
limit 50
""", "2. 参考代码 - WOB复贷放款量&件均(按月)")

exec_sql("""
select 
    coalesce(c.ltv_month, r.ltv_month) as ltv_month,
    coalesce(c.wob, r.wob) as wob,
    c.double_cnt as current_double_cnt,
    r.double_cnt as ref_double_cnt,
    abs(c.double_cnt - r.double_cnt) as cnt_diff,
    c.double_contract_amount as current_amount,
    r.double_contract_amount as ref_amount,
    abs(c.double_contract_amount - r.double_contract_amount) as amount_diff
from (
    select d.ltv_month, 
           date_diff('week', d.ltv_week, date_trunc('week', date(r.release_time))) as wob, 
           count(distinct r.camera_id) as double_cnt,
           sum(r.contract_amount) as double_contract_amount
    from mx.wxs_application_funnel r
    inner join mx.ys_dl_ltv_first_loan_0511 d
        on cast(r.cust_id as bigint) = d.mid
    where r.is_reloan = 'old'
      and r.if_issue = 1
      and d.ltv_month >= date '2025-06-01'
      and date_diff('week', d.ltv_week, date_trunc('week', date(r.release_time))) <= 20
    group by 1, 2
) c
full outer join (
    select date_trunc('month', a.dt_week) as ltv_month,
           date_diff('week', a.dt_week, b.dt_week) as wob,
           count(distinct b.camera_id) as double_cnt,
           sum(b.contract_amount) as double_contract_amount
    from (
        select distinct date(t.release_time) dt, 
               date_add('day',-day_of_week(date(t.release_time))+1,date(t.release_time)) as dt_week,
               t.customer_id, t.contract_amount
        from ods.s02_loan t
        inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
        where rt.double_loan = 0 and t.state in (1,2,3)
    ) a
    inner join (
        select distinct date(t.release_time) dt, 
               date_add('day',-day_of_week(date(t.release_time))+1,date(t.release_time)) as dt_week,
               t.customer_id, t.camera_id, t.contract_amount
        from ods.s02_loan t
        inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
        where rt.double_loan = 1 and t.state in (1,2,3)
    ) b on a.customer_id = b.customer_id
    where a.dt_week >= date '2025-06-01'
      and date_diff('week', a.dt_week, b.dt_week) >= 0
      and date_diff('week', a.dt_week, b.dt_week) <= 20
    group by 1, 2
) r on c.ltv_month = r.ltv_month and c.wob = r.wob
order by 1, 2
limit 50
""", "3. 当前代码 vs 参考代码 - WOB复贷差异对比")

exec_sql("""
select '当前代码' as source,
       date_diff('week', d.ltv_week, date_trunc('week', date(r.release_time))) as wob,
       count(distinct r.camera_id) as total_double_cnt,
       sum(r.contract_amount) as total_double_amount,
       sum(r.contract_amount) / nullif(count(distinct r.camera_id), 0) as avg_amount
from mx.wxs_application_funnel r
inner join mx.ys_dl_ltv_first_loan_0511 d
    on cast(r.cust_id as bigint) = d.mid
where r.is_reloan = 'old'
  and r.if_issue = 1
  and d.ltv_month >= date '2025-06-01'
  and date_diff('week', d.ltv_week, date_trunc('week', date(r.release_time))) <= 20
group by 1, 2
order by 2
""", "4. 当前代码 - WOB汇总复贷放款量&件均")

exec_sql("""
select '参考代码' as source,
       date_diff('week', a.dt_week, b.dt_week) as wob,
       count(distinct b.camera_id) as total_double_cnt,
       sum(b.contract_amount) as total_double_amount,
       sum(b.contract_amount) / nullif(count(distinct b.camera_id), 0) as avg_amount
from (
    select distinct date(t.release_time) dt, 
           date_add('day',-day_of_week(date(t.release_time))+1,date(t.release_time)) as dt_week,
           t.customer_id, t.contract_amount
    from ods.s02_loan t
    inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
    where rt.double_loan = 0 and t.state in (1,2,3)
) a
inner join (
    select distinct date(t.release_time) dt, 
           date_add('day',-day_of_week(date(t.release_time))+1,date(t.release_time)) as dt_week,
           t.customer_id, t.camera_id, t.contract_amount
    from ods.s02_loan t
    inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
    where rt.double_loan = 1 and t.state in (1,2,3)
) b on a.customer_id = b.customer_id
where a.dt_week >= date '2025-06-01'
  and date_diff('week', a.dt_week, b.dt_week) >= 0
  and date_diff('week', a.dt_week, b.dt_week) <= 20
group by 1, 2
order by 2
""", "5. 参考代码 - WOB汇总复贷放款量&件均")

print("\n" + "="*70)
print("墨西哥LTV WOB复贷数据校验完成")
print("="*70)