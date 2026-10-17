# -*- coding: utf-8 -*-
"""验证离线临额关联窗口的污染程度:
   V1 窗口内放款用户中, 有多少笔申请同时领了在线临额(temp_grant_amount>0) -> 归因混合
   V2 C013事件真实发放时间 vs load_time 是否一致 -> 基准日是否准确
   V3 批次前5天 vs 后5天 申请率对比 -> 自发需求基线(事件研究的安慰剂检验)
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

# V1: 窗口内放款申请中在线临额占比(取9月以后批次, 数据较新)
q("""
WITH offline AS (
  SELECT mid, data_date, tagg,
         date_trunc('day', load_time) AS base_dt
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date >= '20260901'
),
app AS (
  SELECT mid, app_date, if_issue, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
    AND if_issue = 1
)
SELECT
  o.tagg,
  COUNT(*) AS issue_app_cnt,
  SUM(CASE WHEN a.temp_grant_amount > 0 THEN 1 ELSE 0 END) AS with_online_temp_cnt,
  round(100.0*SUM(CASE WHEN a.temp_grant_amount > 0 THEN 1 ELSE 0 END)/COUNT(*),2) AS online_temp_pct
FROM offline o
JOIN app a ON cast(o.mid as bigint)=cast(a.mid as bigint)
  AND a.app_date >= o.base_dt AND a.app_date <= date_add('day',5,o.base_dt)
GROUP BY o.tagg
ORDER BY o.tagg
""", "V1 窗口内放款申请同时领在线临额的比例(9-10月批次)")

# V2: C013真实发放时间 vs load_time
q("""
WITH offline AS (
  SELECT mid, data_date, date_trunc('day', load_time) AS base_dt
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date = '20261014'
),
c013 AS (
  SELECT mid, date_trunc('day', create_time) AS c013_dt, COUNT(*) AS c013_cnt
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C013'
    AND create_time >= timestamp'2026-10-12 00:00:00'
    AND create_time <  timestamp'2026-10-16 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
)
SELECT o.base_dt, c.c013_dt, COUNT(DISTINCT o.mid) AS mid_cnt
FROM offline o
JOIN c013 c ON cast(o.mid as bigint)=cast(c.mid as bigint)
GROUP BY o.base_dt, c.c013_dt
ORDER BY o.base_dt, c.c013_dt
""", "V2 1014批次用户的C013事件日期 vs load_time基准日")

# V3: 安慰剂检验 - 批次前5天 vs 后5天 申请率(有在贷人群, 近3批)
q("""
WITH offline AS (
  SELECT mid, data_date, tagg,
         date_trunc('day', load_time) AS base_dt
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260923','20260930','20261007')
    AND temp_limit_tag LIKE '%有在贷%'
),
app AS (
  SELECT mid, app_date
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-09-15' AND app_date < date'2026-10-16'
)
SELECT
  o.data_date,
  COUNT(DISTINCT o.mid) AS mid_cnt,
  -- 前5天有申请
  COUNT(DISTINCT CASE WHEN a_pre.mid IS NOT NULL THEN o.mid END) AS pre_apply_cnt,
  round(100.0*COUNT(DISTINCT CASE WHEN a_pre.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre_apply_rate,
  -- 后5天有申请
  COUNT(DISTINCT CASE WHEN a_post.mid IS NOT NULL THEN o.mid END) AS post_apply_cnt,
  round(100.0*COUNT(DISTINCT CASE WHEN a_post.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post_apply_rate
FROM offline o
LEFT JOIN app a_pre ON cast(o.mid as bigint)=cast(a_pre.mid as bigint)
  AND a_pre.app_date >= date_add('day',-5,o.base_dt) AND a_pre.app_date < o.base_dt
LEFT JOIN app a_post ON cast(o.mid as bigint)=cast(a_post.mid as bigint)
  AND a_post.app_date >= o.base_dt AND a_post.app_date <= date_add('day',5,o.base_dt)
GROUP BY o.data_date
ORDER BY o.data_date
""", "V3 安慰剂检验: 批次前5天 vs 后5天 申请率(有在贷人群)")

print("DONE-VERIFY")
