# -*- coding: utf-8 -*-
"""Phase3主分析: 四分类 x 逾期率 + 纯离线分档逾期
   口径: 放款样本, app_date<=2026-08-31(保证2T0账龄)
   E1 四分类 x 1T0/2T0/TR逾期率(笔数+金额)
   E2 纯离线组分档(有在贷_1/_2/_3, 无在贷臂)逾期
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

BASE = """
grants AS (
  SELECT mid, MAX(create_time) AS grant_time, MAX(change_total_grantamount) AS grant_amt
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-04-01 00:00:00'
    AND create_time <  timestamp'2026-09-01 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
),
off_batch AS (
  SELECT mid, temp_limit_tag, date_trunc('day', load_time) AS base_dt
  FROM mx.yuhan_temp_limit_base_table_his_20260924
),
grants2 AS (
  SELECT g.mid, g.grant_time, g.grant_amt, ob.temp_limit_tag
  FROM grants g
  LEFT JOIN off_batch ob ON cast(g.mid as bigint)=cast(ob.mid as bigint)
    AND date_trunc('day', g.grant_time) = ob.base_dt
),
f AS (
  SELECT mid, app_time, app_date, contract_amount, temp_grant_amount,
         is_t0_overdue_1, is_t0_overdue_2, is_t0_overdue_3, is_t0_overdue_4,
         t0_overdue_amount_1, t0_overdue_amount_2, t0_overdue_amount_3, t0_overdue_amount_4
  FROM mx.report_application_funnel7
  WHERE if_issue = 1 AND app_date >= date'2026-04-01' AND app_date <= date'2026-08-31'
),
exp AS (
  SELECT mid, app_time, temp_limit_tag FROM (
    SELECT cast(f.mid as bigint) AS mid, f.app_time, g.temp_limit_tag,
           row_number() OVER (PARTITION BY cast(f.mid as bigint), f.app_time ORDER BY g.grant_time DESC) AS rn
    FROM f
    JOIN grants2 g ON cast(f.mid as bigint)=cast(g.mid as bigint)
      AND g.grant_time <= f.app_time
      AND f.app_time < g.grant_time + interval '7' day
  ) t WHERE rn = 1
),
cls AS (
  SELECT f.*,
    CASE
      WHEN e.mid IS NOT NULL AND f.temp_grant_amount > 0 THEN '3_混合'
      WHEN e.mid IS NOT NULL THEN '1_纯离线'
      WHEN f.temp_grant_amount > 0 THEN '2_纯在线'
      ELSE '4_无临额'
    END AS grp,
    e.temp_limit_tag
  FROM f LEFT JOIN exp e ON cast(f.mid as bigint)=e.mid AND f.app_time=e.app_time
)
"""

# E1: 四分类 x 逾期
q(f"""
WITH {BASE}
SELECT
  grp,
  COUNT(*) AS issue_cnt,
  round(AVG(contract_amount),0) AS avg_contract,
  round(100.0*AVG(is_t0_overdue_1),2) AS t0_1_rate,
  round(100.0*AVG(is_t0_overdue_2),2) AS t0_2_rate,
  round(100.0*AVG(greatest(is_t0_overdue_1,is_t0_overdue_2,is_t0_overdue_3,is_t0_overdue_4)),2) AS tr_rate,
  round(100.0*SUM(t0_overdue_amount_1)/SUM(contract_amount),2) AS t0_1_amt_rate,
  round(100.0*SUM(t0_overdue_amount_1+t0_overdue_amount_2+t0_overdue_amount_3+t0_overdue_amount_4)/SUM(contract_amount),2) AS tr_amt_rate
FROM cls
GROUP BY grp
ORDER BY grp
""", "E1 四分类 x 逾期率(4-8月放款)")

# E2: 纯离线+混合组 分档/分臂逾期
q(f"""
WITH {BASE}
SELECT
  grp,
  CASE
    WHEN temp_limit_tag LIKE '%有在贷%' THEN substr(temp_limit_tag,-2) || '档'
    WHEN temp_limit_tag LIKE '%临额减息%' THEN '无在贷_临额减息'
    WHEN temp_limit_tag LIKE '%减息%' THEN '无在贷_减息(不应出现)'
    WHEN temp_limit_tag LIKE '%无在贷%' THEN '无在贷_临额'
    ELSE '未匹配批次'
  END AS sub,
  COUNT(*) AS issue_cnt,
  round(AVG(contract_amount),0) AS avg_contract,
  round(100.0*AVG(is_t0_overdue_1),2) AS t0_1_rate,
  round(100.0*AVG(is_t0_overdue_2),2) AS t0_2_rate,
  round(100.0*AVG(greatest(is_t0_overdue_1,is_t0_overdue_2,is_t0_overdue_3,is_t0_overdue_4)),2) AS tr_rate
FROM cls
WHERE grp IN ('1_纯离线','3_混合')
GROUP BY grp,
  CASE
    WHEN temp_limit_tag LIKE '%有在贷%' THEN substr(temp_limit_tag,-2) || '档'
    WHEN temp_limit_tag LIKE '%临额减息%' THEN '无在贷_临额减息'
    WHEN temp_limit_tag LIKE '%减息%' THEN '无在贷_减息(不应出现)'
    WHEN temp_limit_tag LIKE '%无在贷%' THEN '无在贷_临额'
    ELSE '未匹配批次'
  END
ORDER BY grp, sub
""", "E2 纯离线/混合 分档分臂逾期")

print("DONE-PHASE3")
