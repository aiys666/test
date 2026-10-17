# -*- coding: utf-8 -*-
"""修正biz_id类型后重跑 V1/V2"""
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

# V1 单笔核对
q("""
WITH app AS (
  SELECT mid, biz_id, app_time, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date = date'2026-10-14'
    AND temp_grant_amount = 0
  LIMIT 20
)
SELECT a.mid, a.biz_id, a.contract_amount, a.temp_grant_amount,
       u.limit_type, u.risk_credit_limit AS freeze_amt, u.create_time AS freeze_time
FROM app a
LEFT JOIN ods.s05_user_creditlimit_used_detail u
  ON cast(a.biz_id as bigint) = u.biz_id AND u.change_action='FREEZE_LIMIT'
ORDER BY a.biz_id, u.limit_type
""", "V1 纯离线放款MAIN/TEMP冻结明细")

# V2 整体核对
q("""
WITH app AS (
  SELECT mid, biz_id, app_time, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
freeze AS (
  SELECT biz_id,
         SUM(CASE WHEN limit_type='MAIN' THEN risk_credit_limit ELSE 0 END) AS main_used,
         SUM(CASE WHEN limit_type='TEMP' THEN risk_credit_limit ELSE 0 END) AS temp_used
  FROM ods.s05_user_creditlimit_used_detail
  WHERE change_action='FREEZE_LIMIT'
    AND create_time >= timestamp'2026-09-01 00:00:00'
  GROUP BY biz_id
)
SELECT
  CASE
    WHEN f.temp_used = 0 THEN '0_未用临额'
    WHEN f.temp_used <= 500 THEN '1_临额<=500'
    WHEN f.temp_used <= 1000 THEN '2_500~1k'
    WHEN f.temp_used <= 2000 THEN '3_1k~2k'
    ELSE '4_>2k'
  END AS temp_used_bucket,
  COUNT(*) AS issue_cnt,
  round(AVG(a.contract_amount),0) AS avg_contract,
  round(AVG(f.main_used),0) AS avg_main_used,
  round(AVG(f.temp_used),0) AS avg_temp_used,
  round(AVG(a.contract_amount - f.main_used - f.temp_used),2) AS diff,
  round(100.0*SUM(CASE WHEN ABS(a.contract_amount - f.main_used - f.temp_used) < 1 THEN 1 ELSE 0 END)/COUNT(*),2) AS exact_match_pct
FROM app a
JOIN freeze f ON cast(a.biz_id as bigint) = f.biz_id
GROUP BY 1
ORDER BY 1
""", "V2 实际临额使用量分布 + main+temp=contract核对")

# V4: 标签准确性核对 - 之前标的"纯离线"用户放款中, 实际有多少真的用了临额(temp_used>0)
q("""
WITH grants AS (
  SELECT mid, MAX(create_time) AS grant_time
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-09-01 00:00:00'
    AND create_time <  timestamp'2026-10-16 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
),
app AS (
  SELECT mid, biz_id, app_time, if_issue, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
off_exp AS (
  SELECT DISTINCT cast(a.mid as bigint) AS mid, a.app_time
  FROM app a
  JOIN grants g ON cast(a.mid as bigint)=cast(g.mid as bigint)
    AND g.grant_time <= a.app_time AND a.app_time < g.grant_time + interval '7' day
),
freeze AS (
  SELECT biz_id,
         SUM(CASE WHEN limit_type='TEMP' THEN risk_credit_limit ELSE 0 END) AS temp_used
  FROM ods.s05_user_creditlimit_used_detail
  WHERE change_action='FREEZE_LIMIT'
    AND create_time >= timestamp'2026-09-01 00:00:00'
  GROUP BY biz_id
),
cls AS (
  SELECT a.biz_id, a.contract_amount,
    CASE
      WHEN o.mid IS NOT NULL AND a.temp_grant_amount > 0 THEN '3_混合'
      WHEN o.mid IS NOT NULL THEN '1_纯离线(持有)'
      WHEN a.temp_grant_amount > 0 THEN '2_纯在线(持有)'
      ELSE '4_无临额(持有)'
    END AS grp
  FROM app a
  LEFT JOIN off_exp o ON cast(a.mid as bigint)=o.mid AND a.app_time=o.app_time
)
SELECT cls.grp,
  COUNT(*) AS issue_cnt,
  round(100.0*SUM(CASE WHEN f.temp_used > 0 THEN 1 ELSE 0 END)/COUNT(*),2) AS actual_use_temp_pct,
  round(AVG(CASE WHEN f.temp_used > 0 THEN f.temp_used END),0) AS avg_temp_used_when_used,
  round(AVG(f.temp_used),0) AS avg_temp_used_all
FROM cls
LEFT JOIN freeze f ON cast(cls.biz_id as bigint) = f.biz_id
GROUP BY cls.grp
ORDER BY cls.grp
""", "V4 标签准确性: 之前四分类中, 实际用了临额(temp_used>0)的占比")

print("DONE-USAGE-VERIFY2")
