# -*- coding: utf-8 -*-
"""Phase2b补跑: C1首次推送(有在贷)分档 + C3疲劳度曲线"""
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

APP = """
app AS (
  SELECT mid, app_date, if_sx_passed, if_issue, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-01' AND app_date < date'2026-10-16'
)
"""

q(f"""
WITH first_push AS (
  SELECT mid, MIN(data_date) AS first_date
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  GROUP BY mid
),
offline AS (
  SELECT o.mid, o.data_date, o.temp_limit_issue_amount, o.curr_main_credit_limit,
         date_trunc('day', o.load_time) AS base_dt,
         CASE substr(o.temp_limit_tag, -2)
           WHEN '_1' THEN '1_小额档(~450)'
           WHEN '_2' THEN '2_中额档(~1700)'
           WHEN '_3' THEN '3_大额档(~4800)'
           ELSE '9_其他' END AS tier
  FROM mx.yuhan_temp_limit_base_table_his_20260924 o
  JOIN first_push f ON cast(o.mid as bigint)=cast(f.mid as bigint) AND o.data_date=f.first_date
  WHERE o.temp_limit_tag LIKE '%有在贷%'
),
{APP}
SELECT
  o.tier,
  COUNT(DISTINCT o.mid) AS mid_cnt,
  round(AVG(o.curr_main_credit_limit),0) AS avg_main,
  round(AVG(o.temp_limit_issue_amount),0) AS avg_temp,
  round(100.0*COUNT(DISTINCT CASE WHEN ap.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_apply,
  round(100.0*COUNT(DISTINCT CASE WHEN ap.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_issue,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_apply,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_issue,
  round(AVG(CASE WHEN ap.if_issue=1 THEN ap.contract_amount END),0) AS pre_contract,
  round(AVG(CASE WHEN aq.if_issue=1 THEN aq.contract_amount END),0) AS post_contract
FROM offline o
LEFT JOIN app ap ON cast(o.mid as bigint)=cast(ap.mid as bigint)
  AND ap.app_date >= date_add('day',-7,o.base_dt) AND ap.app_date < o.base_dt
LEFT JOIN app aq ON cast(o.mid as bigint)=cast(aq.mid as bigint)
  AND aq.app_date >= o.base_dt AND aq.app_date < date_add('day',7,o.base_dt)
WHERE o.tier <> '9_其他'
GROUP BY 1
ORDER BY 1
""", "C1 首次被推送(有在贷): 前后7天对比 分档")

q(f"""
WITH ranked AS (
  SELECT mid, data_date, temp_limit_tag,
         date_trunc('day', load_time) AS base_dt,
         row_number() OVER (PARTITION BY mid ORDER BY data_date) AS push_seq
  FROM mx.yuhan_temp_limit_base_table_his_20260924
),
{APP}
SELECT
  CASE WHEN r.temp_limit_tag LIKE '%有在贷%' THEN '有在贷' ELSE '无在贷' END AS crowd,
  CASE WHEN r.push_seq >= 4 THEN '4+' ELSE cast(r.push_seq AS varchar) END AS push_seq,
  COUNT(*) AS obs_cnt,
  round(100.0*SUM(CASE WHEN aq.mid IS NOT NULL THEN 1 ELSE 0 END)/COUNT(*),2) AS post7d_apply_rate,
  round(100.0*SUM(CASE WHEN aq.if_issue=1 THEN 1 ELSE 0 END)/COUNT(*),2) AS post7d_issue_rate
FROM ranked r
LEFT JOIN app aq ON cast(r.mid as bigint)=cast(aq.mid as bigint)
  AND aq.app_date >= r.base_dt AND aq.app_date < date_add('day',7,r.base_dt)
GROUP BY 1, 2
ORDER BY 1, 2
""", "C3 疲劳度: 第N次被推送的后7天响应")

print("DONE-PHASE2B-FIX")
