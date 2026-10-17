# -*- coding: utf-8 -*-
"""用宽表SQL跑单笔 biz=1620000482922458, 核对与真实事件是否一致"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 1400)

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
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

BIZ = '1620000482922458'

# 1) funnel 主档(用真实字段名)
q(f"""
SELECT cast(biz_id as varchar) AS biz_id, mid, app_time, apply_time, release_time,
       grantcredit_amount, real_issue_amount, temp_grant_amount, issue_amount,
       if_issue, is_reloan, app_date
FROM mx.wxs_application_funnel
WHERE tenant='yawey' AND cast(biz_id as varchar)='{BIZ}'
""", "1) funnel 主档(真实字段)")

# 2) 宽表SQL 单笔(与11_*.sql一致)
q(f"""
WITH app AS (
  SELECT cast(biz_id as varchar) AS biz_id, mid, app_time
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND cast(biz_id as varchar)='{BIZ}'
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
frz AS (
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
       o.off_time   AS "离线发放时间",
       o.off_amt    AS "离线发放金额",
       s.issue_time AS "在线临额发放时间_model1386",
       n.on_time    AS "在线临额使用时间_C010",
       n.on_amt     AS "在线临额使用金额_C010",
       z.use_time   AS "临额冻结时刻_C003",
       f.temp_grant_amount/1000.0 AS "实际使用临额比索"
FROM app a
LEFT JOIN off o ON a.biz_id=o.biz_id
LEFT JOIN onl n ON a.biz_id=n.biz_id
LEFT JOIN frz z ON a.biz_id=z.biz_id
LEFT JOIN iss s ON cast(a.biz_id as bigint)=s.biz_id
JOIN mx.wxs_application_funnel f ON a.biz_id=cast(f.biz_id as varchar) AND f.tenant='yawey'
""", "2) 宽表SQL 单笔输出")

# 3) 该mid 全窗口 C010 是否存在
q(f"""
SELECT change_event_type, limit_type, count(*) AS cnt, min(create_time) AS min_t, max(create_time) AS max_t
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE cast(mid as bigint)=1040160074981862
GROUP BY 1,2 ORDER BY 1,2
""", "3) 该mid 全部事件类型汇总")

# 4) used_detail 明细(该biz)
q(f"""
SELECT biz_id, change_action, limit_type, risk_credit_limit, create_time
FROM ods.s05_user_creditlimit_used_detail
WHERE cast(biz_id as bigint)={BIZ}
ORDER BY create_time
""", "4) used_detail 本笔明细")

print("DONE-DRILL2")
