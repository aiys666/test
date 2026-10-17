# -*- coding: utf-8 -*-
"""一个放款笔的完整临额时间轴宽表: 离线/在线发放时间+金额、使用时间+金额、放款时间"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 1000)

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

# 0) 探测 funnel 时间类字段名
q("""
SELECT column_name FROM information_schema.columns
WHERE table_schema='mx' AND table_name='wxs_application_funnel'
  AND (lower(column_name) LIKE '%time%' OR lower(column_name) LIKE '%date%'
       OR lower(column_name) LIKE '%release%' OR lower(column_name) LIKE '%grant%')
ORDER BY column_name
""", "0) funnel 时间/日期类字段")

BIZ = "'1620000462179690','1620000462187912','1620000462202779','1620000462219275'"

# 1) 宽表: 进件时刻 + 离线发放(时/额) + 在线C010(时/额) + 冻结使用(时) + 实际使用额
q(f"""
WITH app AS (
  SELECT cast(biz_id as varchar) AS biz_id, mid, app_time
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND cast(biz_id as varchar) IN ({BIZ})
),
off AS (   -- 放款前最近一笔离线发放
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
onl AS (   -- 在线 C010 按 biz_id
  SELECT cast(a.biz_id as varchar) AS biz_id, MIN(e.create_time) AS on_time,
         SUM(e.change_total_grantamount) AS on_amt
  FROM app a JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.biz_id as varchar)=e.external_id
  WHERE e.limit_type='TEMP' AND e.change_event_type='C010'
  GROUP BY 1
),
frz AS (   -- 冻结使用时刻 C003 按 biz_id
  SELECT cast(a.biz_id as varchar) AS biz_id, MIN(e.create_time) AS use_time
  FROM app a JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.biz_id as varchar)=e.external_id
  WHERE e.limit_type='TEMP' AND e.change_event_type='C003'
  GROUP BY 1
),
iss AS (
  SELECT biz_id, MIN(createtime) AS issue_time
  FROM ods.s21_risk_model_record
  WHERE modelmainid=1386 AND strategytype='CHAMPION'
  GROUP BY biz_id
)
SELECT a.biz_id,
       a.app_time                       AS "进件时刻_app_time",
       f.apply_time                     AS "申请时刻_apply_time",
       f.release_time                   AS "实际放款_release_time",
       o.off_time                       AS "离线发放时间",
       o.off_amt                        AS "离线发放金额",
       CASE WHEN o.biz_id IS NULL THEN '无'
            WHEN o.off_exp > a.app_time THEN '仍有效' ELSE '已过期' END AS "离线当时状态",
       n.on_time                        AS "在线临额使用时间_C010",
       s.issue_time                     AS "在线临额发放时间_1386",
       n.on_amt                         AS "在线发放金额",
       z.use_time                       AS "临额冻结时刻",
       f.temp_grant_amount/1000.0       AS "实际使用临额比索"
FROM app a
LEFT JOIN off o ON a.biz_id=o.biz_id
LEFT JOIN onl n ON a.biz_id=n.biz_id
LEFT JOIN frz z ON a.biz_id=z.biz_id
LEFT JOIN iss s ON cast(a.biz_id as bigint)=s.biz_id
JOIN mx.wxs_application_funnel f ON a.biz_id=cast(f.biz_id as varchar) AND f.tenant='yawey'
ORDER BY a.app_time
""", "1) 完整时间轴宽表(4样例)")

print("DONE-TIMELINE")
