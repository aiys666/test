# -*- coding: utf-8 -*-
"""混合链路: 实际使用来源 + 离线"是否在放款时仍有效"精确判定"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 900)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 120); print(tag, flush=True)
    for i in range(8):
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

BIZ = "'1620000462162653','1620000462500943'"

# 4) 实际使用临额: 这两笔的 FREEZE_LIMIT 分解
q(f"""
WITH tgt AS (
  SELECT cast(biz_id as varchar) AS biz_id, mid FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND cast(biz_id as varchar) IN ({BIZ})
)
SELECT t.biz_id, u.limit_type,
       round(SUM(u.risk_credit_limit),2) AS freeze_amt, COUNT(*) AS cnt
FROM ods.s05_user_creditlimit_used_detail u
JOIN tgt t ON t.biz_id = cast(u.biz_id as varchar)
WHERE u.change_action='FREEZE_LIMIT'
GROUP BY t.biz_id, u.limit_type ORDER BY 1,2
""", "4) 两笔实际使用(FREEZE_LIMIT): MAIN vs TEMP")

# 5) 两种离线口径对比: 粗(7天) vs 严(有效期仍有效)
q(f"""
WITH app AS (
  SELECT cast(biz_id as varchar) AS biz_id, mid, app_time
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
online AS (
  SELECT DISTINCT cast(a.biz_id as varchar) AS biz_id
  FROM app a JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.biz_id as varchar)=e.external_id
  WHERE e.limit_type='TEMP' AND e.change_event_type='C010'
),
off_loose AS (
  SELECT DISTINCT cast(a.biz_id as varchar) AS biz_id
  FROM app a JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.mid as bigint)=cast(e.mid as bigint)
   AND e.limit_type='TEMP' AND e.change_event_type IN ('C013','C015')
   AND e.create_time <= a.app_time AND a.app_time < e.create_time + interval '7' day
),
off_strict AS (
  SELECT DISTINCT cast(a.biz_id as varchar) AS biz_id
  FROM app a JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.mid as bigint)=cast(e.mid as bigint)
   AND e.limit_type='TEMP' AND e.change_event_type IN ('C013','C015')
   AND e.create_time <= a.app_time AND a.app_time < e.expiring_time   -- 放款时仍在有效期
)
SELECT
  CASE WHEN o.biz_id IS NOT NULL THEN '在线' ELSE '非在线' END AS online_,
  CASE WHEN l.biz_id IS NOT NULL THEN '离线粗(7天)=1' ELSE '离线粗=0' END AS off_loose,
  CASE WHEN s.biz_id IS NOT NULL THEN '离线严(有效期)=1' ELSE '离线严=0' END AS off_strict,
  COUNT(*) AS cnt
FROM app a
LEFT JOIN online  o ON a.biz_id=o.biz_id
LEFT JOIN off_loose  l ON a.biz_id=l.biz_id
LEFT JOIN off_strict s ON a.biz_id=s.biz_id
GROUP BY 1,2,3 ORDER BY 1,2,3
""", "5) 离线口径对比: 粗(7天) vs 严(有效期有效)")

print("DONE-TRACE-MIX2")
