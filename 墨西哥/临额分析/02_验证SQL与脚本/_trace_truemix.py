# -*- coding: utf-8 -*-
"""真混合样例(离线放款时仍有效) + 事件链路 + 新增两字段计数"""
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

APP = """
app AS (
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
off_strict AS (
  SELECT DISTINCT cast(a.biz_id as varchar) AS biz_id
  FROM app a JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.mid as bigint)=cast(e.mid as bigint)
   AND e.limit_type='TEMP' AND e.change_event_type IN ('C013','C015')
   AND e.create_time <= a.app_time AND a.app_time < e.expiring_time
)
"""

# 真混合样例(离线放款时有效 + 在线)
mdf = q(f"""
WITH {APP}
SELECT a.biz_id, a.mid, a.app_time,
       f.temp_grant_amount
FROM app a
JOIN online o ON a.biz_id=o.biz_id
JOIN off_strict s ON a.biz_id=s.biz_id
JOIN mx.wxs_application_funnel f ON a.biz_id=cast(f.biz_id as varchar) AND f.tenant='yawey'
ORDER BY a.app_time LIMIT 4
""", "真混合样例(取4笔)")

bizs = list(mdf['biz_id']) if mdf is not None else []
print("样例biz:", bizs)
bl = ",".join("'" + str(b) + "'" for b in bizs)

# 真混合样例的时间线
q(f"""
WITH tgt AS (SELECT DISTINCT mid FROM mx.wxs_application_funnel
             WHERE tenant='yawey' AND cast(biz_id as varchar) IN ({bl}))
SELECT cast(e.mid as bigint) AS mid, e.change_event_type, e.limit_type, e.external_id,
       round(e.change_total_grantamount,2) AS total_grant,
       round(e.change_total_grantamount-e.change_used_grantamount,2) AS real_grant,
       e.create_time, e.expiring_time
FROM ods_view_presto.s05_user_creditlimit_change_record e
JOIN tgt ON cast(e.mid as bigint)=cast(tgt.mid as bigint)
WHERE e.limit_type='TEMP' AND e.create_time >= timestamp'2026-08-01 00:00:00'
ORDER BY e.mid, e.create_time
""", "真混合样例: TEMP事件时间线")

# 新字段计数
q(f"""
WITH {APP},
off_expired AS (   -- 离线在放款时已过期(有离线且expiring<=app_time)
  SELECT DISTINCT cast(a.biz_id as varchar) AS biz_id
  FROM app a JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.mid as bigint)=cast(e.mid as bigint)
   AND e.limit_type='TEMP' AND e.change_event_type IN ('C013','C015')
   AND e.create_time <= a.app_time AND e.expiring_time <= a.app_time
)
SELECT
  CASE WHEN o.biz_id IS NOT NULL THEN '在线' ELSE '非在线' END AS online_,
  CASE WHEN x.biz_id IS NOT NULL THEN '离线已过期=1' ELSE '离线未过期/无离线' END AS offline_expired,
  CASE WHEN f.temp_grant_amount>0 THEN '实际用了临额' ELSE '未用临额' END AS used,
  COUNT(*) AS cnt
FROM app a
LEFT JOIN online o ON a.biz_id=o.biz_id
LEFT JOIN off_expired x ON a.biz_id=x.biz_id
JOIN mx.wxs_application_funnel f ON a.biz_id=cast(f.biz_id as varchar) AND f.tenant='yawey'
GROUP BY 1,2,3 ORDER BY 1,2,3
""", "新字段: 在线 × 离线是否已过期 × 是否用临额")

print("DONE-TRUEMIX")
