# -*- coding: utf-8 -*-
"""全量校验: 临额占用金额(used_detail FREEZE TEMP) == 临额最终使用金额(temp_grant_amount)"""
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

q("""
WITH app AS (
  SELECT cast(biz_id as varchar) AS biz_id, temp_grant_amount AS used_temp
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
utd AS (
  SELECT cast(u.biz_id as varchar) AS biz_id, SUM(u.risk_credit_limit) AS occ
  FROM ods.s05_user_creditlimit_used_detail u
  WHERE u.change_action='FREEZE_LIMIT' AND u.limit_type='TEMP'
  GROUP BY 1
)
SELECT
  count(*) AS "放款笔数",
  count(u.biz_id) AS "有TEMP冻结笔数",
  sum(CASE WHEN u.occ IS NOT NULL AND abs(u.occ - a.used_temp/1000.0) < 0.01 THEN 1 ELSE 0 END) AS "占用=最终使用(<=0.01)",
  sum(CASE WHEN u.occ IS NOT NULL AND abs(u.occ - a.used_temp/1000.0) >= 0.01 THEN 1 ELSE 0 END) AS "占用≠最终使用",
  sum(CASE WHEN a.used_temp > 0 AND u.biz_id IS NULL THEN 1 ELSE 0 END) AS "有使用但无冻结明细",
  sum(CASE WHEN a.used_temp = 0 AND u.biz_id IS NOT NULL THEN 1 ELSE 0 END) AS "无使用但有冻结"
FROM app a
LEFT JOIN utd u ON a.biz_id = u.biz_id
""", "全量口径校验(9/1-10/16)")

q("""
WITH app AS (
  SELECT cast(biz_id as varchar) AS biz_id, temp_grant_amount AS used_temp
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
utd AS (
  SELECT cast(u.biz_id as varchar) AS biz_id, SUM(u.risk_credit_limit) AS occ
  FROM ods.s05_user_creditlimit_used_detail u
  WHERE u.change_action='FREEZE_LIMIT' AND u.limit_type='TEMP'
  GROUP BY 1
)
SELECT a.biz_id, a.used_temp/1000.0 AS "最终使用", u.occ AS "占用", (u.occ - a.used_temp/1000.0) AS "差额"
FROM app a JOIN utd u ON a.biz_id = u.biz_id
WHERE abs(u.occ - a.used_temp/1000.0) >= 0.01
ORDER BY abs(u.occ - a.used_temp/1000.0) DESC
LIMIT 20
""", "失配样例(前20)")

print("DONE-OCC")
