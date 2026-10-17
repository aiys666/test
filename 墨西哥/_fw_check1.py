# -*- coding: utf-8 -*-
"""确认首贷授信额度字段口径"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

for _i in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(12)
pd.set_option('display.max_columns', None); pd.set_option('display.width', 460)

def q(sql, retry=8):
    for i in range(retry):
        try:
            r = pq.query(sql)
        except Exception:
            time.sleep(10)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            return r
        print(f"[retry {i+1}] {r[:150]}"); time.sleep(10)
        try: pq.login()
        except Exception: pass
    return None

# 首贷 各额度字段对比 (9月放款)
r = q("""
select
  round(avg(issue_amount),0) as issue_avg,
  round(avg(credit_amount_sx),0) as credit_sx,
  round(avg(approve_amount),0) as approve_amt,
  round(avg(credit_amount),0) as credit_amt,
  round(avg(risk_credit_limit),0) as risk_credit,
  round(sum(issue_amount)/nullif(sum(approve_amount),0)*100,2) as tr_approve,
  round(sum(issue_amount)/nullif(sum(credit_amount),0)*100,2) as tr_credit
from mx.wxs_application_funnel
where tenant='yawey' and is_reloan='new' and if_issue=1
  and app_time >= cast('2026-09-01 00:00:00.000' as timestamp)
  and app_time <  cast('2026-09-22 00:00:00.000' as timestamp)
""")
print(r.to_string() if r is not None else "FAIL")
