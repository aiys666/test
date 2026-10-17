# -*- coding: utf-8 -*-
"""Phase0: 验证C015/C013/C010事件语义
   1. C015每日事件量 vs 批次load_time是否对齐
   2. C013每日事件量(应只在9月,少量)
   3. 单批次验证: 1014批次的mid是否都有C015且时间=load_time
   4. C015的external_id/金额 与底表temp_limit_issue_amount是否一致
   5. C014是什么(临额到期回收?)
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

# 1. C015/C013/C010/C014 每日事件量(4-10月)
q("""
SELECT date_trunc('day', create_time) AS dt, change_event_type, COUNT(*) AS cnt,
       COUNT(DISTINCT mid) AS mid_cnt
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE change_event_type IN ('C015','C013','C010','C014')
  AND create_time >= timestamp'2026-04-01 00:00:00'
  AND create_time <  timestamp'2026-10-16 00:00:00'
GROUP BY date_trunc('day', create_time), change_event_type
ORDER BY dt, change_event_type
""", "P0-1 C015/C013/C010/C014每日事件量")

# 2. C015样例: external_id/金额/动作
q("""
SELECT mid, change_event_type, change_action,
       change_total_grantamount, change_used_grantamount,
       external_id, limit_main_id, create_time
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE change_event_type='C015'
  AND create_time >= timestamp'2026-10-13 00:00:00'
  AND create_time <  timestamp'2026-10-16 00:00:00'
LIMIT 10
""", "P0-2 C015样例(10月中旬)")

# 3. 单批次对账: 1014批次底表mid vs C015事件
q("""
WITH offline AS (
  SELECT mid, temp_limit_issue_amount, date_trunc('day', load_time) AS base_dt
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date = '20261014'
),
c015 AS (
  SELECT mid, change_total_grantamount, change_action, create_time
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C015'
    AND create_time >= timestamp'2026-10-12 00:00:00'
    AND create_time <  timestamp'2026-10-15 00:00:00'
)
SELECT
  COUNT(DISTINCT o.mid) AS offline_mid_cnt,
  COUNT(DISTINCT c.mid) AS c015_mid_cnt,
  COUNT(DISTINCT CASE WHEN c.mid IS NOT NULL THEN o.mid END) AS matched_cnt,
  round(AVG(o.temp_limit_issue_amount),2) AS avg_offline_amt,
  round(AVG(c.change_total_grantamount),2) AS avg_c015_amt
FROM offline o
LEFT JOIN c015 c ON cast(o.mid as bigint)=cast(c.mid as bigint)
""", "P0-3 1014批次: 底表mid vs C015事件匹配")

# 4. C013每日明细(9月)
q("""
SELECT date_trunc('day', create_time) AS dt, COUNT(*) AS cnt, COUNT(DISTINCT mid) AS mid_cnt,
       round(AVG(change_total_grantamount),2) AS avg_amt,
       SUM(CASE WHEN external_id IS NULL OR external_id='' THEN 1 ELSE 0 END) AS null_ext_cnt
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE change_event_type='C013'
  AND create_time >= timestamp'2026-04-01 00:00:00'
GROUP BY date_trunc('day', create_time)
ORDER BY dt
""", "P0-4 C013每日明细")

# 5. C014是什么
q("""
SELECT change_event_type, change_action, COUNT(*) AS cnt,
       round(AVG(change_total_grantamount),2) AS avg_total,
       round(AVG(change_used_grantamount),2) AS avg_used,
       SUM(CASE WHEN external_id IS NULL OR external_id='' THEN 1 ELSE 0 END) AS null_ext_cnt
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE change_event_type IN ('C014','C015')
  AND create_time >= timestamp'2026-09-01 00:00:00'
GROUP BY change_event_type, change_action
""", "P0-5 C014/C015动作与金额特征")

print("DONE-PHASE0")
