# -*- coding: utf-8 -*-
"""补跑S11标签准确性核对并追加到Excel"""
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
    AND create_time >= timestamp'2026-09-01 00:00:00'
    AND create_time <  timestamp'2026-10-16 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
),
freeze AS (
  SELECT biz_id, SUM(CASE WHEN limit_type='TEMP' THEN risk_credit_limit ELSE 0 END) AS temp_used
  FROM ods.s05_user_creditlimit_used_detail
  WHERE change_action='FREEZE_LIMIT' AND create_time >= timestamp'2026-09-01 00:00:00'
  GROUP BY biz_id
),
app AS (
  SELECT a.mid, a.biz_id, a.app_time,
         CASE WHEN g.mid IS NOT NULL THEN 1 ELSE 0 END AS has_offline,
         a.temp_grant_amount
  FROM mx.wxs_application_funnel a
  LEFT JOIN grants g ON cast(a.mid as bigint)=cast(g.mid as bigint)
    AND g.grant_time <= a.app_time AND a.app_time < g.grant_time + interval '7' day
  WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
    AND a.app_date >= date'2026-09-01' AND a.app_date < date'2026-10-16'
),
cls AS (
  SELECT a.biz_id, fr.temp_used,
    CASE
      WHEN a.has_offline=1 AND a.temp_grant_amount > 0 THEN '3_混合(持有)'
      WHEN a.has_offline=1 THEN '1_纯离线(持有)'
      WHEN a.temp_grant_amount > 0 THEN '2_纯在线(持有)'
      ELSE '4_无临额(持有)'
    END AS hold_grp
  FROM app a
  JOIN freeze fr ON cast(a.biz_id as bigint) = fr.biz_id
)
SELECT hold_grp,
  COUNT(*) AS issue_cnt,
  round(100.0*SUM(CASE WHEN temp_used > 0 THEN 1 ELSE 0 END)/COUNT(*),2) AS actual_use_temp_pct,
  round(AVG(temp_used),0) AS avg_temp_used_all,
  round(AVG(CASE WHEN temp_used > 0 THEN temp_used END),0) AS avg_temp_used_when_used
FROM cls
GROUP BY 1 ORDER BY 1
"""
s11 = None
for i in range(6):
    r = pq.query(sql)
    if not isinstance(r, str): s11 = r; break
    print(f"[retry {i+1}]"); time.sleep(6)
    try: pq.login()
    except Exception: pass

assert s11 is not None
print(s11.to_string())

out = r"E:\岳松个人文件\嘉银工作内容的整理\code\离线临额效果分析_C015口径_重点结论.xlsx"
xls = pd.ExcelFile(out)
existing = {s: pd.read_excel(out, sheet_name=s) for s in xls.sheet_names}
with pd.ExcelWriter(out, engine='openpyxl') as w:
    for s, df in existing.items():
        if s == 'S9_标签准确性核对': continue
        df.to_excel(w, sheet_name=s, index=False)
    s11.to_excel(w, sheet_name='S9_标签准确性核对', index=False)
print("✅ S11已追加")
