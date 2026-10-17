# -*- coding: utf-8 -*-
"""X1差异拆解(按申请时间vs发放时间的偏移) + X2 C010 external_id格式排查"""
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

# Y1: 官方有标签但我未标(临额/临额减息)的差异拆解 - 按申请时间距C015发放的偏移
q("""
WITH base AS (
  SELECT mid, temp_limit_tag,
         CASE WHEN temp_limit_tag LIKE '%临额减息%' THEN '临额减息'
              WHEN temp_limit_tag LIKE '%减息%' THEN '减息'
              ELSE '临额' END AS arm,
         data_date
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260819','20260820','20260826','20260827',
                      '20260902','20260903','20260909','20260910')
),
g AS (
  SELECT mid, create_time, change_event_type
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-08-18 00:00:00'
    AND create_time <  timestamp'2026-09-15 00:00:00'
),
official AS (
  SELECT a.mid, a.biz_id, a.app_time, b.arm, b.data_date
  FROM mx.wxs_application_funnel a
  JOIN base b ON cast(a.mid as bigint)=cast(b.mid as bigint)
  WHERE a.tenant='yawey' AND a.is_reloan='old'
    AND ((b.data_date='20260819' AND a.app_date BETWEEN date'2026-08-18' AND date'2026-08-23')
      OR (b.data_date='20260820' AND a.app_date BETWEEN date'2026-08-19' AND date'2026-08-24')
      OR (b.data_date='20260826' AND a.app_date BETWEEN date'2026-08-25' AND date'2026-08-30')
      OR (b.data_date='20260827' AND a.app_date BETWEEN date'2026-08-26' AND date'2026-08-31')
      OR (b.data_date='20260902' AND a.app_date BETWEEN date'2026-09-01' AND date'2026-09-06')
      OR (b.data_date='20260903' AND a.app_date BETWEEN date'2026-09-02' AND date'2026-09-07')
      OR (b.data_date='20260909' AND a.app_date BETWEEN date'2026-09-08' AND date'2026-09-13')
      OR (b.data_date='20260910' AND a.app_date BETWEEN date'2026-09-09' AND date'2026-09-14'))
),
off_matched AS (
  SELECT o.mid, o.app_time, MIN(g.create_time) AS nearest_grant
  FROM official o
  LEFT JOIN g ON cast(o.mid as bigint)=cast(g.mid as bigint)
   AND g.create_time BETWEEN o.app_time - interval '2' day AND o.app_time + interval '8' day
  GROUP BY o.mid, o.app_time
)
SELECT o.arm,
  CASE
    WHEN m.nearest_grant IS NULL THEN '0_该mid窗口附近无任何C015/C013'
    WHEN m.nearest_grant > o.app_time THEN '1_申请早于发放(同日20点前/提前进件)'
    WHEN date_diff('day', m.nearest_grant, o.app_time) = 6 THEN '2_发放后第6天(官方窗口外/我的7天内)'
    WHEN date_diff('day', m.nearest_grant, o.app_time) = 7 THEN '3_发放后第7天20点前'
    ELSE '4_其他偏移'
  END AS diff_reason,
  COUNT(*) AS cnt
FROM official o
JOIN off_matched m ON cast(o.mid as bigint)=cast(m.mid as bigint) AND o.app_time=m.app_time
WHERE o.arm IN ('临额','临额减息')
  AND NOT EXISTS (
    SELECT 1 FROM g g2
    WHERE cast(g2.mid as bigint)=cast(o.mid as bigint)
      AND g2.create_time <= o.app_time
      AND o.app_time < g2.create_time + interval '7' day)
GROUP BY 1, 2
ORDER BY 1, 2
""", "Y1 官方有/我无(临额组)差异原因拆解")

# Y2: 官方无标签但我标了的2665笔 - 是否都在D+6/D+7边界 或 C013修单
q("""
WITH base AS (
  SELECT mid, data_date FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260819','20260820','20260826','20260827',
                      '20260902','20260903','20260909','20260910')
),
g AS (
  SELECT mid, create_time, change_event_type
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-08-18 00:00:00'
    AND create_time <  timestamp'2026-09-15 00:00:00'
),
app AS (
  SELECT mid, biz_id, app_time, app_date
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-08-18' AND app_date <= date'2026-09-14'
),
official AS (
  SELECT DISTINCT cast(a.mid as bigint) AS mid, a.app_time
  FROM app a JOIN base b ON cast(a.mid as bigint)=cast(b.mid as bigint)
  WHERE (b.data_date='20260819' AND a.app_date BETWEEN date'2026-08-18' AND date'2026-08-23')
     OR (b.data_date='20260820' AND a.app_date BETWEEN date'2026-08-19' AND date'2026-08-24')
     OR (b.data_date='20260826' AND a.app_date BETWEEN date'2026-08-25' AND date'2026-08-30')
     OR (b.data_date='20260827' AND a.app_date BETWEEN date'2026-08-26' AND date'2026-08-31')
     OR (b.data_date='20260902' AND a.app_date BETWEEN date'2026-09-01' AND date'2026-09-06')
     OR (b.data_date='20260903' AND a.app_date BETWEEN date'2026-09-02' AND date'2026-09-07')
     OR (b.data_date='20260909' AND a.app_date BETWEEN date'2026-09-08' AND date'2026-09-13')
     OR (b.data_date='20260910' AND a.app_date BETWEEN date'2026-09-09' AND date'2026-09-14')
),
mine AS (
  SELECT cast(a.mid as bigint) AS mid, a.app_time, MIN(g.create_time) AS grant_time,
         MIN(g.change_event_type) AS evt
  FROM app a JOIN g ON cast(a.mid as bigint)=cast(g.mid as bigint)
   AND g.create_time <= a.app_time AND a.app_time < g.create_time + interval '7' day
  GROUP BY cast(a.mid as bigint), a.app_time
)
SELECT
  m.evt,
  date_diff('day', m.grant_time, m.app_time) AS days_after_grant,
  CASE WHEN b.mid IS NOT NULL THEN 'mid在8批次内' ELSE 'mid不在8批次底表' END AS in_base,
  COUNT(*) AS cnt
FROM mine m
LEFT JOIN official o ON m.mid=o.mid AND m.app_time=o.app_time
LEFT JOIN (SELECT DISTINCT cast(mid as bigint) AS mid FROM base) b ON m.mid=b.mid
WHERE o.mid IS NULL
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
""", "Y2 我有/官方无的2665笔拆解")

# Y3: C010 external_id 长什么样
q("""
SELECT change_event_type, external_id, change_total_grantamount, create_time
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE change_event_type='C010'
  AND create_time >= timestamp'2026-09-09 00:00:00'
  AND create_time <  timestamp'2026-09-10 00:00:00'
LIMIT 15
""", "Y3 C010 external_id样例(09-09)")

# Y4: funnel有临额但C010按biz关联不到的5376笔 - 换mid+时间邻近能否关联上C010
q("""
WITH app AS (
  SELECT mid, biz_id, app_time, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
    AND temp_grant_amount > 0
),
c010_by_biz AS (
  SELECT DISTINCT external_id FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C010' AND create_time >= timestamp'2026-09-01 00:00:00'
),
unmatched AS (
  SELECT a.* FROM app a
  LEFT JOIN c010_by_biz c ON cast(a.biz_id as varchar)=c.external_id
  WHERE c.external_id IS NULL
)
SELECT
  CASE WHEN c.mid IS NOT NULL THEN '同mid有C010事件(时间邻近)' ELSE '同mid完全无C010' END AS mid_has_c010,
  COUNT(*) AS cnt,
  round(AVG(u.temp_grant_amount/1000.0),2) AS avg_funnel_temp_peso
FROM unmatched u
LEFT JOIN (
  SELECT DISTINCT cast(mid as bigint) AS mid
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C010' AND create_time >= timestamp'2026-08-25 00:00:00'
) c ON cast(u.mid as bigint)=c.mid
GROUP BY 1
""", "Y4 funnel有临额但biz关联不到C010的5376笔: 同mid是否有C010")

print("DONE-DRILL")
