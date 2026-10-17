# -*- coding: utf-8 -*-
"""补跑S2并更新Excel"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

sql = """
WITH grants AS (
  SELECT mid, MAX(create_time) AS grant_time
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-04-01 00:00:00'
    AND create_time <  timestamp'2026-10-16 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
),
app AS (
  SELECT mid, app_time, app_date, if_issue, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-01' AND app_date < date'2026-10-16'
),
off_exp AS (
  SELECT DISTINCT cast(a.mid as bigint) AS mid, a.app_time
  FROM app a
  JOIN grants g ON cast(a.mid as bigint)=cast(g.mid as bigint)
    AND g.grant_time <= a.app_time AND a.app_time < g.grant_time + interval '7' day
),
cls AS (
  SELECT a.app_date, a.if_issue, a.contract_amount,
    CASE
      WHEN o.mid IS NOT NULL AND a.temp_grant_amount > 0 THEN '3_混合(离线+在线)'
      WHEN o.mid IS NOT NULL THEN '1_纯离线'
      WHEN a.temp_grant_amount > 0 THEN '2_纯在线'
      ELSE '4_无临额'
    END AS grp
  FROM app a
  LEFT JOIN off_exp o ON cast(a.mid as bigint)=o.mid AND a.app_time=o.app_time
)
SELECT date_format(app_date,'%Y-%m') AS app_month, grp,
  COUNT(*) AS app_cnt,
  round(100.0*SUM(if_issue)/COUNT(*),2) AS issue_rate,
  round(AVG(CASE WHEN if_issue=1 THEN contract_amount END),0) AS avg_contract
FROM cls
GROUP BY 1, 2
ORDER BY 1, 2
"""
s2 = None
for i in range(6):
    r = pq.query(sql)
    if not isinstance(r, str):
        s2 = r; break
    print(f"[retry {i+1}] {r[:200]}"); time.sleep(6)
    try: pq.login()
    except Exception: pass

assert s2 is not None, "S2 failed"
print(s2.to_string())

out = r"E:\岳松个人文件\嘉银工作内容的整理\code\离线临额效果分析_C015口径_重点结论.xlsx"
xls = pd.ExcelFile(out)
existing = {s: pd.read_excel(out, sheet_name=s) for s in xls.sheet_names}
with pd.ExcelWriter(out, engine='openpyxl') as w:
    written = False
    for s, df in existing.items():
        if s == 'S2_四分类总览_按月':
            s2.to_excel(w, sheet_name=s, index=False); written = True
        else:
            df.to_excel(w, sheet_name=s, index=False)
    if not written:
        s2.to_excel(w, sheet_name='S2_四分类总览_按月', index=False)
print("✅ S2已更新")
