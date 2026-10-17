# -*- coding: utf-8 -*-
"""追溯两个"混合"笔的临额事件链路"""
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

# 1) funnel: biz -> mid/app_time/金额
q(f"""
SELECT cast(biz_id as varchar) as biz_id, mid, app_time, app_date,
       contract_amount, temp_grant_amount
FROM mx.wxs_application_funnel
WHERE tenant='yawey' AND cast(biz_id as varchar) IN ({BIZ})
""", "1) funnel 两笔基础信息")

# 2) 该 mid 全部临额/授信事件时间线
q(f"""
WITH tgt AS (
  SELECT DISTINCT mid FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND cast(biz_id as varchar) IN ({BIZ})
)
SELECT e.change_event_type, e.limit_type, e.mid, e.external_id,
       round(e.change_total_grantamount,2) AS total_grant,
       round(e.change_used_grantamount,2)  AS used_before,
       round(e.change_total_grantamount - e.change_used_grantamount,2) AS real_grant,
       e.limit_main_id, e.create_time, e.expiring_time
FROM ods_view_presto.s05_user_creditlimit_change_record e
JOIN tgt ON cast(e.mid as bigint) = cast(tgt.mid as bigint)
WHERE e.limit_type='TEMP'
  AND e.create_time >= timestamp'2026-08-01 00:00:00'
ORDER BY e.mid, e.create_time
""", "2) 该mid的TEMP事件时间线(8月起)")

# 3) C010 精确匹配(按biz_id)
q(f"""
SELECT e.change_event_type, e.limit_type, e.mid, e.external_id,
       round(e.change_total_grantamount,2) AS total_grant,
       round(e.change_total_grantamount - e.change_used_grantamount,2) AS real_grant,
       e.create_time, e.expiring_time
FROM ods_view_presto.s05_user_creditlimit_change_record e
WHERE e.limit_type='TEMP' AND e.change_event_type='C010'
  AND e.external_id IN ({BIZ})
ORDER BY e.create_time
""", "3) C010(在线)按 biz_id 精确命中")

print("DONE-TRACE-MIX")
