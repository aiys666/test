# -*- coding: utf-8 -*-
"""Phase1: 分离层 - 离线(C015+C013) vs 在线(C010) 临额打标
   A1 事件流与批次底表匹配覆盖率
   A2 全部申请四分类: 纯离线/纯在线/混合/无临额 (按月)
   A3 实验臂平衡性检验: 发放前7天申请率是否跨臂一致(随机性验证)
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

GRANTS = """
grants AS (
  SELECT mid, MAX(create_time) AS grant_time, MAX(change_total_grantamount) AS grant_amt,
         MAX(change_event_type) AS src
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-04-01 00:00:00'
    AND create_time <  timestamp'2026-10-16 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
)
"""

# A1: 每个批次底表人数 vs 当天有C015/C013事件的人数 覆盖率
q(f"""
WITH {GRANTS},
offline AS (
  SELECT mid, data_date, date_trunc('day', load_time) AS base_dt
  FROM mx.yuhan_temp_limit_base_table_his_20260924
)
SELECT
  o.data_date,
  COUNT(DISTINCT o.mid) AS offline_cnt,
  COUNT(DISTINCT CASE WHEN g.mid IS NOT NULL THEN o.mid END) AS matched_cnt,
  round(100.0*COUNT(DISTINCT CASE WHEN g.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),1) AS cover_pct
FROM offline o
LEFT JOIN grants g ON cast(o.mid as bigint)=cast(g.mid as bigint)
  AND g.grant_time >= o.base_dt AND g.grant_time < date_add('day',2,o.base_dt)
GROUP BY o.data_date
ORDER BY o.data_date
""", "A1 批次底表 vs C015/C013事件 覆盖率")

# A2: 全部老客申请四分类(7天暴露窗口)
q(f"""
WITH {GRANTS},
app AS (
  SELECT mid, app_time, app_date, if_sx_passed, if_issue, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-01' AND app_date < date'2026-10-16'
),
off_exp AS (
  SELECT DISTINCT cast(a.mid as bigint) AS mid, a.app_time
  FROM app a
  JOIN grants g ON cast(a.mid as bigint)=cast(g.mid as bigint)
    AND g.grant_time <= a.app_time
    AND a.app_time < g.grant_time + interval '7' day
)
SELECT
  date_format(a.app_date,'%Y-%m') AS app_month,
  CASE
    WHEN o.mid IS NOT NULL AND a.temp_grant_amount > 0 THEN '3_混合(离线+在线)'
    WHEN o.mid IS NOT NULL THEN '1_纯离线'
    WHEN a.temp_grant_amount > 0 THEN '2_纯在线'
    ELSE '4_无临额'
  END AS grp,
  COUNT(*) AS app_cnt,
  SUM(a.if_issue) AS issue_cnt,
  round(100.0*SUM(a.if_issue)/COUNT(*),2) AS issue_rate,
  round(AVG(CASE WHEN a.if_issue=1 THEN a.contract_amount END),0) AS avg_contract
FROM app a
LEFT JOIN off_exp o ON cast(a.mid as bigint)=o.mid AND a.app_time=o.app_time
GROUP BY date_format(a.app_date,'%Y-%m'),
  CASE
    WHEN o.mid IS NOT NULL AND a.temp_grant_amount > 0 THEN '3_混合(离线+在线)'
    WHEN o.mid IS NOT NULL THEN '1_纯离线'
    WHEN a.temp_grant_amount > 0 THEN '2_纯在线'
    ELSE '4_无临额'
  END
ORDER BY app_month, grp
""", "A2 申请四分类(按月)")

# A3: 平衡性检验 - 近4个有在贷批次的_1/_2/_3臂, 发放前7天申请率
q(f"""
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         date_trunc('day', load_time) AS base_dt
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260923','20260930','20261007','20261014')
),
app AS (
  SELECT mid, app_date
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-09-10' AND app_date < date'2026-10-16'
)
SELECT
  o.data_date,
  o.temp_limit_tag,
  COUNT(DISTINCT o.mid) AS mid_cnt,
  round(AVG(o.curr_main_credit_limit),0) AS avg_main_limit,
  round(AVG(o.onloan_bal),0) AS avg_onloan_bal,
  round(100.0*COUNT(DISTINCT CASE WHEN a.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_apply_rate
FROM offline o
LEFT JOIN app a ON cast(o.mid as bigint)=cast(a.mid as bigint)
  AND a.app_date >= date_add('day',-7,o.base_dt) AND a.app_date < o.base_dt
GROUP BY o.data_date, o.temp_limit_tag
ORDER BY o.data_date, o.temp_limit_tag
""", "A3 平衡性检验: 各实验臂发放前7天申请率+主额+在贷余额")

print("DONE-PHASE1")
