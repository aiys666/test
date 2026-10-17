# -*- coding: utf-8 -*-
"""验证新增3字段: 在线是否覆盖离线 / 临额占用金额 / 临额最终使用金额"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 1600)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 130); print(tag, flush=True)
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
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

BIZ = "'1620000462287861','1620000482922458','1620000462179690'"

q(f"""
WITH app AS (
  SELECT cast(biz_id as varchar) AS biz_id, mid, app_time
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND cast(biz_id as varchar) IN ({BIZ})
),
off AS (
  SELECT biz_id, off_time, off_amt, off_exp FROM (
    SELECT cast(a.biz_id as varchar) AS biz_id, e.create_time AS off_time,
           e.change_total_grantamount AS off_amt, e.expiring_time AS off_exp,
           row_number() OVER (PARTITION BY a.biz_id ORDER BY e.create_time DESC) rn
    FROM app a JOIN ods_view_presto.s05_user_creditlimit_change_record e
      ON cast(a.mid as bigint)=cast(e.mid as bigint)
     AND e.limit_type='TEMP' AND e.change_event_type IN ('C013','C015')
     AND e.create_time <= a.app_time
  ) t WHERE rn=1
),
onl AS (
  SELECT cast(a.biz_id as varchar) AS biz_id, MIN(e.create_time) AS on_time,
         SUM(e.change_total_grantamount) AS on_amt
  FROM app a JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.biz_id as varchar)=e.external_id
  WHERE e.limit_type='TEMP' AND e.change_event_type='C010'
  GROUP BY 1
),
utd AS (
  SELECT cast(u.biz_id as varchar) AS biz_id, SUM(u.risk_credit_limit) AS temp_occupy
  FROM ods.s05_user_creditlimit_used_detail u
  JOIN app a ON cast(u.biz_id as bigint)=cast(a.biz_id as bigint)
  WHERE u.change_action='FREEZE_LIMIT' AND u.limit_type='TEMP'
  GROUP BY 1
)
SELECT a.biz_id,
       o.off_amt                      AS "离线发放金额",
       CASE WHEN o.biz_id IS NULL THEN '无' WHEN o.off_exp>a.app_time THEN '仍有效' ELSE '已过期' END AS "离线当时状态",
       CASE WHEN o.biz_id IS NULL OR n.on_amt IS NULL THEN '不适用'
            WHEN n.on_amt >= o.off_amt THEN '是(在线>=离线)' ELSE '否(在线<离线)' END AS "在线是否覆盖离线",
       n.on_amt                       AS "在线发放额_C010",
       u.temp_occupy                  AS "临额占用金额",
       f.temp_grant_amount/1000.0     AS "临额最终使用金额"
FROM app a
LEFT JOIN off o ON a.biz_id=o.biz_id
LEFT JOIN onl n ON a.biz_id=n.biz_id
LEFT JOIN utd u ON a.biz_id=u.biz_id
JOIN mx.wxs_application_funnel f ON a.biz_id=cast(f.biz_id as varchar) AND f.tenant='yawey'
ORDER BY a.biz_id
""", "新增3字段验证(3笔)")

print("DONE-NEW3")
