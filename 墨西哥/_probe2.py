# -*- coding: utf-8 -*-
"""探针：确认 state/paid_type 分布、date_diff 语法、wxs_risk_ttl 可用性。"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

queries = {
    "loan_state": """
select state, count(*) n, count(distinct camera_id) n_ord
from ods.s02_loan
where release_time >= timestamp '2026-05-01 00:00:00' and release_time < timestamp '2026-09-30 00:00:00'
group by state order by state
""",
    "paid_type": """
select paid_type, loan_cycle, loan_cycle_unit, count(*) n, sum(contract_amount) amt
from ods.s02_loan
where release_time >= timestamp '2026-05-01 00:00:00' and release_time < timestamp '2026-09-30 00:00:00'
  and state in (1,2)
group by 1,2,3 order by 1,2
""",
    "date_diff_test": """
select date_diff('day', date('2026-05-01'), date('2026-05-11')) as d1,
       date_diff('day', timestamp '2026-05-01 00:00:00', timestamp '2026-05-11 00:00:00') as d2
""",
    "wxs_risk_ttl": """
select count(*) n, count(distinct camera_id) n_ord, min(release_time) mn, max(release_time) mx
from mx.wxs_risk_ttl
""",
}

for name, sql in queries.items():
    try:
        df = pq.query(sql, wait_sec=1)
        if isinstance(df, str):
            print(f"[{name}] ERR: {df}")
        else:
            print(f"[{name}] {len(df)} 行")
            print(df.to_string(index=False))
    except Exception as e:
        print(f"[{name}] EXC: {e}")
    print("-" * 70)
