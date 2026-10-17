# -*- coding: utf-8 -*-
"""语法探针2：grouping sets 在真实表上的可用性 + values 语法。"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

tests = {
    "values": """
select * from (values (1,10),(2,20)) t(a,b)
""",
    "grouping_sets_real": """
select date(release_time) d, count(*) n, sum(contract_amount) s
from ods.s02_loan
where release_time >= timestamp '2026-05-01 00:00:00'
  and release_time < timestamp '2026-05-03 00:00:00'
  and state in (1,2)
group by grouping sets ((date(release_time)), ())
order by d
""",
    "grouping_fn_real": """
select date(release_time) d, grouping(date(release_time)) g, count(*) n
from ods.s02_loan
where release_time >= timestamp '2026-05-01 00:00:00'
  and release_time < timestamp '2026-05-03 00:00:00'
  and state in (1,2)
group by grouping sets ((date(release_time)), ())
order by d
""",
}

for name, sql in tests.items():
    try:
        df = pq.query(sql, wait_sec=1)
        if isinstance(df, str):
            print(f"[{name}] ERR: {df}")
        else:
            print(f"[{name}] OK {len(df)} 行")
            print(df.to_string(index=False))
    except Exception as e:
        print(f"[{name}] EXC: {e}")
    print("-" * 60)
