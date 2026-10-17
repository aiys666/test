# -*- coding: utf-8 -*-
"""首贷额度字段确认(只查存在的)"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

for _i in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(12)

r = pq.query("""
select column_name from information_schema.columns
where table_schema='mx' and table_name='wxs_application_funnel'
  and (column_name like '%credit%amount%' or column_name like '%approve%' or column_name like '%grant%')
order by 1
""")
print(r.to_string() if not isinstance(r,str) else r)
