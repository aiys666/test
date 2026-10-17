# -*- coding: utf-8 -*-
"""看 C010实到账 != temp_grant 的28笔特征"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.width', 2200); pd.set_option('display.max_rows', 300)
for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)
def q(sql, tag):
    print("=" * 140); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception as ex:
            print(f"[err] {str(ex)[:180]}"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

q("""
WITH app AS (
  SELECT cast(biz_id as varchar) AS biz_id, temp_grant_amount AS used
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
onl AS (
  SELECT cast(a.biz_id as varchar) AS biz_id,
         sum(e.change_total_grantamount - e.change_used_grantamount) AS on_actual
  FROM app a JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.biz_id as varchar)=e.external_id
  WHERE e.limit_type='TEMP' AND e.change_event_type='C010' GROUP BY 1
)
SELECT a.biz_id, n.on_actual AS "C010实到账", a.used/1000.0 AS "temp_grant",
       (n.on_actual - a.used/1000.0) AS "差额"
FROM app a JOIN onl n ON a.biz_id=n.biz_id
WHERE abs(n.on_actual - a.used/1000.0) >= 0.01
ORDER BY abs(n.on_actual - a.used/1000.0) DESC
""", "C010实到账≠temp_grant 全部")
print("DONE-28")
