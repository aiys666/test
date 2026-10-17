# -*- coding: utf-8 -*-
"""测试：1) limit 9999 能否取回完整行数  2) keyset 分页(order by camera_id + where camera_id > X)"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

# 1. limit 9999 完整性
df = pq.query("""
select camera_id from ods.s02_loan
where release_time >= timestamp '2026-05-01' and state in (1,2)
order by camera_id limit 9999
""", wait_sec=1)
print("limit9999 返回行数:", len(df), "首:", df.iloc[0].values, "尾:", df.iloc[-1].values)

# 2. keyset 第二页
last = df.iloc[-1]['camera_id']
df2 = pq.query(f"""
select camera_id from ods.s02_loan
where release_time >= timestamp '2026-05-01' and state in (1,2)
and camera_id > '{last}'
order by camera_id limit 9999
""", wait_sec=1)
print("keyset页2 行数:", len(df2), "首:", df2.iloc[0].values, "尾:", df2.iloc[-1].values)
print("keyset页1尾 < 页2首?", last < df2.iloc[0]['camera_id'])
