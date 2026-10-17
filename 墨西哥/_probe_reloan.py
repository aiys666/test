# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
pq = PrestoQuery(); pq.login()

sql = """
select reloan_num, count(*) c, sum(if_issue) iss
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey' and if_issue=1
  and date(release_time) between date '2026-08-03' and date '2026-08-24'
group by 1 order by 2 desc limit 30
"""
r = pq.query(sql)
print(r if isinstance(r, str) else r.to_string(index=False))
