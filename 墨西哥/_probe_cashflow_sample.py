# -*- coding: utf-8 -*-
"""确认 s02_loan 前几列 + 抽样 + 期数分布 + amount/contract 语义"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

# 1. s02_loan 前 6 列
print("=" * 80)
r = pq.query("select * from ods.s02_loan limit 1")
if isinstance(r, str):
    print("ERROR:", r)
else:
    print("s02_loan 列名:", list(r.columns)[:12])

# 2. 抽样 2026-05 后放款
print("=" * 80)
sql = """
select camera_id, customer_id, lid, loan_cycle, contract_amount, amount, haircut_amount,
       interest, fee_amount, state, release_time, finish_time, trade_end_time, double_loan, paid_type
from ods.s02_loan
where release_time >= timestamp '2026-05-01'
  and state in (1,2,3)
limit 10
"""
r = pq.query(sql)
if isinstance(r, str):
    print("ERROR:", r)
else:
    print(r.to_string())

# 3. 每笔放款的期数分布
print("=" * 80)
sql = """
select cnt, count(*) as n_loans
from (
    select camera_id, count(*) as cnt
    from ods.s02_loan_repayment
    where should_time >= timestamp '2026-05-01'
    group by camera_id
) t
group by cnt
order by cnt
"""
r = pq.query(sql)
if isinstance(r, str):
    print("ERROR:", r)
else:
    print("还款计划期数分布:", r.to_string())
