# -*- coding: utf-8 -*-
"""确认 detail 覆盖率、state 分布、展期影响"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

# 1. detail vs repayment 全量差异
print("=" * 80)
print("1. 明细 vs 计划 实还差异（全量 2026-05-01起）")
r = pq.query("""
with plan as (
    select camera_id, sum(fact_capital) fc, sum(fact_interest) fi
    from ods.s02_loan_repayment group by camera_id
),
det as (
    select camera_id, sum(fact_capital) fc, sum(fact_interest) fi
    from ods.s02_loan_repayment_detail group by camera_id
),
loans as (
    select camera_id from ods.s02_loan
    where release_time >= timestamp '2026-05-01' and state in (1,2,3)
)
select
    count(*) as n_loans,
    sum(case when d.camera_id is null then 1 else 0 end) as n_no_detail,
    sum(p.fc) as plan_fc, sum(p.fi) as plan_fi,
    sum(coalesce(d.fc,0)) as det_fc, sum(coalesce(d.fi,0)) as det_fi,
    sum(abs(p.fc - coalesce(d.fc,0))) as diff_fc_sum,
    sum(abs(p.fi - coalesce(d.fi,0))) as diff_fi_sum
from loans l
join plan p on p.camera_id = l.camera_id
left join det d on d.camera_id = l.camera_id
""")
print(r if isinstance(r, str) else r.to_string())

# 2. state 分布
print("=" * 80)
print("2. state 分布（2026-05-01起）")
r = pq.query("""
select state, count(*) as n, sum(contract_amount) as contract_sum, sum(amount) as amount_sum
from ods.s02_loan
where release_time >= timestamp '2026-05-01'
group by state order by state
""")
print(r if isinstance(r, str) else r.to_string())

# 3. 展期覆盖
print("=" * 80)
print("3. 展期记录（2026-05-01起放款中，有展期的笔数）")
r = pq.query("""
select status, count(*) as n, sum(postpone_amount) as p_amt, sum(real_amount) as r_amt
from ods.s02_loan_postpone_order
where camera_id in (select camera_id from ods.s02_loan where release_time >= timestamp '2026-05-01' and state in (1,2,3))
group by status order by status
""")
print(r if isinstance(r, str) else r.to_string())

# 4. 还款计划 state 分布
print("=" * 80)
print("4. 还款计划 state 分布")
r = pq.query("""
select rp.state, count(*) as n, sum(should_capital) as sc, sum(fact_capital) as fc
from ods.s02_loan_repayment rp
join ods.s02_loan l on l.camera_id = rp.camera_id
where l.release_time >= timestamp '2026-05-01' and l.state in (1,2,3)
group by rp.state order by rp.state
""")
print(r if isinstance(r, str) else r.to_string())
