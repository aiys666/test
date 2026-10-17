# -*- coding: utf-8 -*-
"""验证 11_在线离线临额区分逻辑.sql 的 Step2/Step1 能否执行"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 620)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 100); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception:
            time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:200]}"); time.sleep(6)
    return None

q("""
SELECT change_event_type,
  CASE change_event_type WHEN 'C010' THEN '在线临额' WHEN 'C015' THEN '离线临额' WHEN 'C013' THEN '离线临额(人工)' END AS temp_source,
  COUNT(*) AS evt_cnt,
  COUNT(DISTINCT mid) AS mid_cnt
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE limit_type='TEMP' AND change_event_type IN ('C010','C013','C015')
  AND create_time >= timestamp'2026-09-01 00:00:00'
GROUP BY 1,2 ORDER BY 1
""", "Step1 事件级(9月起)")

q("""
WITH app AS (
  SELECT mid, biz_id, app_time
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
online AS (
  SELECT DISTINCT cast(a.biz_id as bigint) AS biz_id
  FROM app a
  JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.biz_id as varchar) = e.external_id
  WHERE e.limit_type='TEMP' AND e.change_event_type='C010'
),
offline AS (
  SELECT DISTINCT cast(a.mid as bigint) AS mid
  FROM app a
  JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.mid as bigint) = cast(e.mid as bigint)
   AND e.limit_type='TEMP' AND e.change_event_type IN ('C013','C015')
   AND e.create_time <= a.app_time
   AND a.app_time < e.create_time + interval '7' day
)
SELECT
  CASE WHEN o.biz_id IS NOT NULL AND f.mid IS NOT NULL THEN '混合(在线+离线)'
       WHEN o.biz_id IS NOT NULL THEN '在线临额'
       WHEN f.mid IS NOT NULL THEN '离线临额'
       ELSE '无临额' END AS temp_source_grp,
  COUNT(*) AS loan_cnt
FROM app a
LEFT JOIN online  o ON cast(a.biz_id as bigint)=o.biz_id
LEFT JOIN offline f ON cast(a.mid as bigint)=f.mid
GROUP BY 1 ORDER BY 1
""", "Step2 笔级(9/1-10/15复贷放款)")

print("DONE-RUN11")
