# -*- coding: utf-8 -*-
"""确认展期表结构 + 字段类型问题"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

# 1. 展期表样例
print("=" * 80)
r = pq.query("select * from ods.s02_loan_postpone_order limit 5")
print("展期表列名:", list(r.columns))
print(r.to_string())

# 2. 用 lid 关联放款表试试（展期表是否有 lid）
print("=" * 80)
r = pq.query("""
select count(*) as n
from ods.s02_loan_postpone_order p
join ods.s02_loan l on cast(l.lid as varchar) = cast(p.lid as varchar)
where l.release_time >= timestamp '2026-05-01'
""")
print("展期 lid 关联放款:", r if isinstance(r, str) else r.to_string())

# 3. 展期表 camera_id 精度对比
print("=" * 80)
r = pq.query("""
select p.camera_id as p_cam, count(*) as n
from ods.s02_loan_postpone_order p
group by p.camera_id
limit 5
""")
print("展期 camera_id 样例:", r if isinstance(r, str) else r.to_string())
