# -*- coding: utf-8 -*-
"""确认展期表数据、明细表规模、每日放款量级"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

# 1. 展期表全量
print("=" * 80)
r = pq.query("select count(*) as n from ods.s02_loan_postpone_order")
print("展期表全量行数:", r if isinstance(r, str) else r.to_string())

# 2. 明细表规模（这批贷款）
print("=" * 80)
r = pq.query("""
select count(*) as n
from ods.s02_loan_repayment_detail rd
join ods.s02_loan l on l.camera_id = rd.camera_id
where l.release_time >= timestamp '2026-05-01' and l.state in (1,2)
""")
print("明细表行数(本批):", r if isinstance(r, str) else r.to_string())

# 3. 每日放款量级（笔数+合同本金）
print("=" * 80)
r = pq.query("""
select date(release_time) as d, count(*) as n,
       sum(contract_amount) as contract_sum, sum(amount) as amount_sum
from ods.s02_loan
where release_time >= timestamp '2026-05-01' and state in (1,2)
group by date(release_time)
order by d
""")
print("每日放款:")
print(r if isinstance(r, str) else r.to_string())
