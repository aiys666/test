# -*- coding: utf-8 -*-
"""7天产品 amount vs contract_amount 差值去向"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

# 7天产品字段全景
print("=" * 80)
r = pq.query("""
select lid, camera_id, loan_cycle, loan_cycle_unit, rate,
       contract_amount, amount, haircut_amount, interest, fee_amount,
       state, release_time, trade_end_time, paid_type, double_loan
from ods.s02_loan
where release_time >= timestamp '2026-05-01' and loan_cycle = 7 and state in (1,2,3)
limit 8
""")
print(r if isinstance(r, str) else r.to_string())

# 7天产品金额关系聚合：amount + haircut + fee = contract?
print("=" * 80)
r = pq.query("""
select
    count(*) as n,
    sum(contract_amount) as contract_sum,
    sum(amount) as amount_sum,
    sum(haircut_amount) as haircut_sum,
    sum(interest) as interest_sum,
    sum(fee_amount) as fee_sum,
    sum(amount + haircut_amount + fee_amount) as amount_haircut_fee_sum,
    sum(amount + interest + fee_amount) as amount_interest_fee_sum
from ods.s02_loan
where release_time >= timestamp '2026-05-01' and loan_cycle = 7 and state in (1,2,3)
""")
print("7天产品金额关系:")
print(r if isinstance(r, str) else r.to_string())

# 7天产品的还款计划：should_capital 到底是多少
print("=" * 80)
r = pq.query("""
with plan as (
    select camera_id, sum(should_capital) sc, sum(should_interest) si,
           sum(fact_capital) fc, sum(fact_interest) fi, sum(subtract_capital) subc, sum(subtract_interest) subi
    from ods.s02_loan_repayment group by camera_id
)
select l.camera_id, l.contract_amount, l.amount, l.interest, l.fee_amount,
       p.sc, p.si, p.fc, p.fi, p.subc, p.subi
from ods.s02_loan l join plan p on p.camera_id = l.camera_id
where l.release_time >= timestamp '2026-05-01' and l.loan_cycle = 7 and l.state in (1,2,3)
limit 8
""")
print("7天产品还款计划:")
print(r if isinstance(r, str) else r.to_string())
