# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("login", pq.login())
sql = """select loan_cycle, count(*) n, sum(contract_amount) amt
from ods.s02_loan
where release_time >= timestamp '2026-05-01 00:00:00'
  and release_time < timestamp '2026-09-30 00:00:00'
  and state in (1,2)
group by 1 order by 1"""
df = pq.query(sql)
print(df.to_string(index=False))
