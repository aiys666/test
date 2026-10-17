# -*- coding: utf-8 -*-
"""验证: 在线临额"发放时刻"(s21 model1386 createtime) vs "使用时刻"(C010) 是否分离"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 1100)

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

BIZ = "1620000462179690,1620000462187912,1620000462202779,1620000462219275"

# A) 样例: model 1386 / 1523 决策时刻
q(f"""
SELECT biz_id, mid, modelmainid, strategytype,
       createtime,
       substr(outputdata, 1, 120) AS out_snip
FROM ods.s21_risk_model_record
WHERE biz_id IN ({BIZ}) AND modelmainid IN (1386,1523)
ORDER BY biz_id, createtime
""", "A) 样例 model1386/1523 决策流记录")

# B) 样例: model1386落表
q(f"""
SELECT biz_id, mid, dt, temp_credit_amount_issue_tag, etl_date
FROM mx.tmp_darren_temp_limit_table
WHERE biz_id IN ({BIZ})
ORDER BY biz_id, dt
""", "B) 样例 model1386落表(dt/issue_tag)")

# C) 分布: C010 使用时刻 与 model1386 发放时刻 的间隔 (抽一批 biz)
q("""
WITH c010 AS (
  SELECT cast(external_id as bigint) AS biz, mid, create_time AS use_time
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE limit_type='TEMP' AND change_event_type='C010'
    AND create_time >= timestamp'2026-09-01 00:00:00' AND create_time < timestamp'2026-10-10 00:00:00'
),
m1386 AS (
  SELECT biz_id AS biz, min(createtime) AS issue_time
  FROM ods.s21_risk_model_record
  WHERE modelmainid=1386 AND strategytype='CHAMPION'
  GROUP BY biz_id
)
SELECT
  COUNT(*) AS c010_cnt,
  SUM(CASE WHEN m.biz IS NOT NULL THEN 1 ELSE 0 END) AS matched_1386,
  ROUND(AVG(CASE WHEN m.biz IS NOT NULL THEN date_diff('second', m.issue_time, c.use_time) END),1) AS avg_gap_sec,
  ROUND(APPROX_PERCENTILE(CASE WHEN m.biz IS NOT NULL THEN date_diff('second', m.issue_time, c.use_time) END, 0.5),1) AS p50_gap_sec,
  SUM(CASE WHEN m.biz IS NOT NULL AND date_diff('second', m.issue_time, c.use_time) BETWEEN -5 AND 5 THEN 1 ELSE 0 END) AS within_5s,
  SUM(CASE WHEN m.biz IS NOT NULL AND date_diff('second', m.issue_time, c.use_time) BETWEEN -60 AND 60 THEN 1 ELSE 0 END) AS within_60s,
  SUM(CASE WHEN m.biz IS NOT NULL AND date_diff('second', m.issue_time, c.use_time) > 60 THEN 1 ELSE 0 END) AS gt_60s,
  SUM(CASE WHEN m.biz IS NOT NULL AND date_diff('second', m.issue_time, c.use_time) < -5 THEN 1 ELSE 0 END) AS use_before_issue
FROM c010 c LEFT JOIN m1386 m ON c.biz=m.biz
""", "C) C010使用时刻 vs model1386发放时刻 间隔分布")

print("DONE-ISSUE")
