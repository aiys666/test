# -*- coding: utf-8 -*-
"""关键验证: temp_grant_amount 的真实语义
Z1: temp_grant_amount vs freeze.TEMP(temp_used) 是否恒等 → 若恒等, 它是"本笔使用临额"而非"在线发放"
Z2: 5376笔有temp_grant但无C010的, 是否来自C015/C013离线发放(mid级历史发放)
Z3: 这5376笔的"距最近一次离线发放天数"分布
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 620)

def q(sql, tag):
    print("=" * 120); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); print(); return None
            print(r.to_string()); print(f"[rows={len(r)}]\n", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:300]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}\n"); return None

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: print("[login retry]"); time.sleep(8)

# Z1: temp_grant_amount vs 实际TEMP冻结额 恒等性
q("""
WITH freeze AS (
  SELECT biz_id, SUM(CASE WHEN limit_type='TEMP' THEN risk_credit_limit ELSE 0 END) AS temp_used
  FROM ods.s05_user_creditlimit_used_detail
  WHERE change_action='FREEZE_LIMIT' AND create_time >= timestamp'2026-09-01 00:00:00'
  GROUP BY biz_id
)
SELECT
  CASE
    WHEN ABS(a.temp_grant_amount/1000.0 - f.temp_used) < 1 THEN '1_完全相等'
    WHEN ABS(a.temp_grant_amount/1000.0 - f.temp_used) < 50 THEN '2_差<50'
    ELSE '3_差异大'
  END AS match_level,
  COUNT(*) AS cnt,
  round(AVG(a.temp_grant_amount/1000.0),2) AS avg_funnel_temp,
  round(AVG(f.temp_used),2) AS avg_temp_used
FROM mx.wxs_application_funnel a
JOIN freeze f ON cast(a.biz_id as bigint)=f.biz_id
WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
  AND a.app_date >= date'2026-09-01' AND a.app_date < date'2026-10-16'
  AND a.temp_grant_amount > 0
GROUP BY 1 ORDER BY 1
""", "Z1 temp_grant_amount vs 实际TEMP冻结额 恒等性")

# Z2+Z3: 无C010的5376笔, 查C015/C013历史发放 + 距发放天数
q("""
WITH app AS (
  SELECT mid, biz_id, app_time, app_date, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
    AND temp_grant_amount > 0
),
c010_biz AS (
  SELECT DISTINCT external_id FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C010' AND create_time >= timestamp'2026-09-01 00:00:00'
),
off_grant AS (
  SELECT mid, MAX(create_time) AS last_off_time, MAX(change_total_grantamount) AS last_off_amt
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-04-01 00:00:00'
  GROUP BY mid
)
SELECT
  CASE
    WHEN og.mid IS NULL THEN '0_无任何离线发放'
    WHEN date_diff('day', og.last_off_time, a.app_time) <= 7 THEN '1_离线发放后7天内'
    WHEN date_diff('day', og.last_off_time, a.app_time) <= 14 THEN '2_8-14天'
    WHEN date_diff('day', og.last_off_time, a.app_time) <= 30 THEN '3_15-30天'
    ELSE '4_30天以上'
  END AS off_grant_gap,
  COUNT(*) AS cnt,
  round(AVG(a.temp_grant_amount/1000.0),0) AS avg_funnel_temp,
  round(AVG(og.last_off_amt),0) AS avg_last_offline_grant
FROM app a
LEFT JOIN c010_biz c ON cast(a.biz_id as varchar)=c.external_id
LEFT JOIN off_grant og ON cast(a.mid as bigint)=cast(og.mid as bigint)
WHERE c.external_id IS NULL
GROUP BY 1 ORDER BY 1
""", "Z2 无C010的放款: 距最近离线发放天数分布")

# Z4: 反过来 - 有C010的6294笔, temp_grant_amount与C010金额恒等性
q("""
WITH c010 AS (
  SELECT external_id, MAX(change_total_grantamount) AS c010_amt
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C010' AND create_time >= timestamp'2026-09-01 00:00:00'
  GROUP BY external_id
)
SELECT
  CASE
    WHEN ABS(a.temp_grant_amount/1000.0 - c.c010_amt) < 1 THEN '1_完全相等'
    WHEN ABS(a.temp_grant_amount/1000.0 - c.c010_amt) < 50 THEN '2_差<50'
    ELSE '3_差异大'
  END AS match_level,
  COUNT(*) AS cnt,
  round(AVG(a.temp_grant_amount/1000.0),2) AS avg_funnel_temp,
  round(AVG(c.c010_amt),2) AS avg_c010_amt
FROM mx.wxs_application_funnel a
JOIN c010 c ON cast(a.biz_id as varchar)=c.external_id
WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
  AND a.app_date >= date'2026-09-01' AND a.app_date < date'2026-10-16'
GROUP BY 1 ORDER BY 1
""", "Z4 有C010放款: temp_grant_amount vs C010金额恒等性")

print("DONE-SEMANTIC")
