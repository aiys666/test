# -*- coding: utf-8 -*-
"""确认还款计划表分期结构：期次、应还时间、金额字段语义"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

# 1. loan_cycle_unit 含义（0/1 分别多少笔）
print("=" * 80)
r = pq.query("""
select loan_cycle_unit, loan_cycle, paid_type, count(*) as n
from ods.s02_loan
where release_time >= timestamp '2026-05-01' and state in (1,2,3)
group by loan_cycle_unit, loan_cycle, paid_type
order by loan_cycle_unit, loan_cycle, paid_type
limit 50
""")
print("loan_cycle_unit/loan_cycle/paid_type 分布:")
print(r if isinstance(r, str) else r.to_string())

# 2. 取一笔 14 天贷款，看其还款计划
print("=" * 80)
r = pq.query("""
select rp.camera_id, rp.indexs, rp.state, rp.should_time, rp.fact_time,
       rp.should_capital, rp.fact_capital, rp.should_interest, rp.fact_interest,
       rp.should_fine, rp.fact_fine, rp.should_overdue_fee, rp.fact_overdue_fee,
       rp.is_extends, rp.coupon_amount, rp.subtract_capital, rp.subtract_interest
from ods.s02_loan_repayment rp
where rp.camera_id = (
    select camera_id from ods.s02_loan
    where release_time >= timestamp '2026-05-01' and state in (1,2,3) and loan_cycle = 14
    limit 1
)
order by rp.indexs
""")
print("14天贷款还款计划:")
print(r if isinstance(r, str) else r.to_string())

# 3. 还款明细表抽样（同一笔）
print("=" * 80)
r = pq.query("""
select rd.camera_id, rd.rid, rd.fact_time, rd.fact_capital, rd.fact_interest,
       rd.fact_fine, rd.fact_overdue_fee, rd.fact_fee_amount, rd.payment_status, rd.channel_id
from ods.s02_loan_repayment_detail rd
where rd.camera_id = (
    select camera_id from ods.s02_loan
    where release_time >= timestamp '2026-05-01' and state in (1,2,3) and loan_cycle = 14
    limit 1
)
order by rd.fact_time
""")
print("还款明细:")
print(r if isinstance(r, str) else r.to_string())
