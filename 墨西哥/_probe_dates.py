# -*- coding: utf-8 -*-
"""获取放款日期范围"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())
df = pq.query("""
select min(cast(release_time as date)) as d0, max(cast(release_time as date)) as d1,
       count(distinct cast(release_time as date)) as ndays
from ods.s02_loan
where release_time >= timestamp '2026-05-01' and state in (1,2)
""", wait_sec=1)
print(df.to_dict('records'))
