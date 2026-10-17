# -*- coding: utf-8 -*-
"""核心对账：明细 vs 计划实还、已还+未还=放款 等式验证"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

# A. 还款计划聚合 vs 放款：应还本金=amount? 应还利息=interest?
print("=" * 80)
print("A. 计划应还 vs 放款金额（抽10笔）")
r = pq.query("""
with plan as (
    select camera_id,
           sum(should_capital) sc, sum(should_interest) si,
           sum(fact_capital) fc, sum(fact_interest) fi
    from ods.s02_loan_repayment
    group by camera_id
)
select l.camera_id, l.loan_cycle, l.state,
       l.amount, l.contract_amount, l.interest,
       p.sc, p.si, p.fc, p.fi,
       (p.sc - l.amount) as diff_capital, (p.si - l.interest) as diff_interest
from ods.s02_loan l
join plan p on p.camera_id = l.camera_id
where l.release_time >= timestamp '2026-05-01' and l.state in (1,2,3)
limit 15
""")
print(r if isinstance(r, str) else r.to_string())

# B. 明细实还 vs 计划实还（同一批贷款聚合）
print("=" * 80)
print("B. 明细实还 vs 计划实还（按 camera_id 聚合对账，抽样）")
r = pq.query("""
with plan as (
    select camera_id, sum(fact_capital) fc, sum(fact_interest) fi
    from ods.s02_loan_repayment group by camera_id
),
det as (
    select camera_id, sum(fact_capital) fc, sum(fact_interest) fi
    from ods.s02_loan_repayment_detail group by camera_id
)
select l.camera_id, l.state, l.amount,
       p.fc as plan_fc, p.fi as plan_fi, d.fc as det_fc, d.fi as det_fi,
       (d.fc - p.fc) as diff_fc, (d.fi - p.fi) as diff_fi
from ods.s02_loan l
join plan p on p.camera_id = l.camera_id
left join det d on d.camera_id = l.camera_id
where l.release_time >= timestamp '2026-05-01' and l.state in (2,3)
  and (d.fc is null or d.fc <> p.fc or d.fi <> p.fi)
limit 20
""")
print(r if isinstance(r, str) else r.to_string())

# C. 已结清贷款：实还 vs 应还 是否抹平
print("=" * 80)
print("C. state=2 已结清：应还-实还 是否=0（本金+利息）")
r = pq.query("""
with plan as (
    select camera_id, sum(should_capital) sc, sum(should_interest) si,
           sum(fact_capital) fc, sum(fact_interest) fi
    from ods.s02_loan_repayment group by camera_id
)
select
    count(*) as n,
    sum(case when (sc - fc) = 0 then 1 else 0 end) as capital_flat,
    sum(case when (si - fi) = 0 then 1 else 0 end) as interest_flat,
    sum(abs(sc - fc)) as diff_cap_sum, sum(abs(si - fi)) as diff_int_sum
from ods.s02_loan l join plan p on p.camera_id = l.camera_id
where l.release_time >= timestamp '2026-05-01' and l.state = 2
""")
print(r if isinstance(r, str) else r.to_string())

# D. 全局：未还本金+已还本金 = 放款本金
print("=" * 80)
print("D. 全部放款（2026-05-01起）：amount vs 计划本金（应还/实还）")
r = pq.query("""
with plan as (
    select camera_id, sum(should_capital) sc, sum(should_interest) si,
           sum(fact_capital) fc, sum(fact_interest) fi
    from ods.s02_loan_repayment group by camera_id
)
select
    count(*) as n,
    sum(l.amount) as amount_sum,
    sum(p.sc) as should_cap_sum, sum(p.fc) as fact_cap_sum,
    sum(p.si) as should_int_sum, sum(p.fi) as fact_int_sum
from ods.s02_loan l join plan p on p.camera_id = l.camera_id
where l.release_time >= timestamp '2026-05-01' and l.state in (1,2,3)
""")
print(r if isinstance(r, str) else r.to_string())
