# -*- coding: utf-8 -*-
"""语法探针：确认 date_diff/date_add/grouping sets/least/greatest 支持情况。"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

tests = {
    "date_diff": """
select date_diff('day', date('2026-05-01'), date('2026-05-11')) as d1,
       date_diff('day', timestamp '2026-05-01 00:00:00', timestamp '2026-05-11 00:00:00') as d2
""",
    "date_add": """
select date_add('day', 3, date '2026-05-01') as a1,
       date '2026-05-01' + interval '3' day as a2
""",
    "least_greatest": """
select least(5,3) a, greatest(5,3) b
""",
    "grouping_sets": """
select a, b, count(*) n, sum(c) s
from (values (1, 10, 100), (1, 20, 200), (2, 10, 300)) t(a,b,c)
group by grouping sets ((a), (a,b))
order by a, b
""",
    "grouping_fn": """
select a, b, grouping(a) ga, grouping(b) gb, count(*) n
from (values (1,10),(1,20),(2,10)) t(a,b)
group by grouping sets ((a),(a,b))
order by a, b
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
