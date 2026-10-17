# -*- coding: utf-8 -*-
"""在线临额口径对账: 我的C010口径 vs mx.yj_test_table_250225 自带字段
YJ1 覆盖率: funnel(9-10月复贷放款) 能否按 biz_id 命中 yj表
YJ2 字段恒等: funnel.temp_grant_amount vs yj.temp_grant_amount (逐笔)
YJ3 在线标记对账: 我的C010(biz级) vs yj.temp_credit_amount_issue_tag 交叉表
YJ4 金额对账: 各部分 sum(元)
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
yj AS (
  SELECT biz_id, temp_credit_amount_issue_tag AS issue_tag, temp_grant_amount AS yj_temp,
         temp_credit_amount_strategy_test_flag AS flag, app_time, app_date, release_time
  FROM mx.yj_test_table_250225
  WHERE is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
yj1 AS (   -- biz_id 去重取最新
  SELECT * FROM (
    SELECT *, row_number() OVER (PARTITION BY biz_id ORDER BY app_time DESC) rn FROM yj
  ) t WHERE rn=1
),
app AS (
  SELECT biz_id, temp_grant_amount AS fn_temp, contract_amount, app_time, app_date
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
c010 AS (
  SELECT DISTINCT cast(external_id as varchar) AS biz_str
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C010' AND limit_type='TEMP'
    AND create_time >= timestamp'2026-08-25 00:00:00'
)
"""

# YJ1 覆盖率
q(f"""
WITH {BASE}
SELECT
  CASE WHEN y.biz_id IS NOT NULL THEN '命中yj表' ELSE '未命中yj表' END AS yj_match,
  COUNT(*) AS funnel_cnt,
  COUNT(DISTINCT a.biz_id) AS biz_cnt,
  round(100.0*SUM(CASE WHEN a.fn_temp>0 THEN 1 ELSE 0 END)/COUNT(*),2) AS funnel_temp_gt0_pct,
  SUM(a.contract_amount) AS contract_sum
FROM app a
LEFT JOIN yj1 y ON a.biz_id = y.biz_id
GROUP BY 1 ORDER BY 1
""", "YJ1 funnel(9月-10月复贷放款) 与 yj表 biz_id 覆盖率")

# YJ2 temp_grant_amount 恒等性(命中行内)
q(f"""
WITH {BASE}
SELECT
  CASE
    WHEN a.fn_temp = y.yj_temp THEN '1_完全相等'
    WHEN a.fn_temp = 0 AND y.yj_temp = 0 THEN '1_完全相等(都0)'
    WHEN ABS(a.fn_temp - y.yj_temp) <= 1000 THEN '2_差<=1000(分)'
    ELSE '3_差异大'
  END AS match_level,
  COUNT(*) AS cnt,
  round(AVG(a.fn_temp/1000.0),2) AS avg_funnel_peso,
  round(AVG(y.yj_temp/1000.0),2) AS avg_yj_peso,
  SUM(a.fn_temp/1000.0) AS sum_funnel_peso,
  SUM(y.yj_temp/1000.0) AS sum_yj_peso
FROM app a
JOIN yj1 y ON a.biz_id = y.biz_id
GROUP BY 1 ORDER BY 1
""", "YJ2 命中行: funnel.temp_grant_amount vs yj.temp_grant_amount 恒等性")

# YJ3 在线标记对账: 我的C010(biz有C010) vs yj.issue_tag
q(f"""
WITH {BASE}
SELECT
  CASE WHEN c.biz_str IS NOT NULL THEN '我_C010有' ELSE '我_C010无' END AS my_c010,
  CASE WHEN y.issue_tag = 1 THEN 'yj_tag=1'
       WHEN y.issue_tag = 0 THEN 'yj_tag=0'
       ELSE 'yj_tag=null' END AS yj_tag,
  COUNT(*) AS cnt,
  SUM(CASE WHEN a.fn_temp>0 THEN 1 ELSE 0 END) AS temp_used_cnt,
  round(AVG(a.fn_temp/1000.0),2) AS avg_temp_peso
FROM app a
JOIN yj1 y ON a.biz_id = y.biz_id
LEFT JOIN c010 c ON cast(a.biz_id as varchar) = c.biz_str
GROUP BY 1, 2 ORDER BY 1, 2
""", "YJ3 在线标记对账: 我的C010(biz级) vs yj.temp_credit_amount_issue_tag")

# YJ4 金额对账
q(f"""
WITH {BASE}
SELECT
  '整个9-10月口径' AS scope,
  COUNT(*) AS funnel_loans,
  SUM(a.contract_amount) AS contract_sum,
  SUM(a.fn_temp/1000.0) AS funnel_temp_sum_peso,
  SUM(CASE WHEN c.biz_str IS NOT NULL THEN a.fn_temp/1000.0 ELSE 0 END) AS my_c010_src_peso,
  SUM(CASE WHEN y.issue_tag=1 THEN a.fn_temp/1000.0 ELSE 0 END) AS yj_tag1_peso,
  SUM(CASE WHEN a.fn_temp>0 THEN 1 ELSE 0 END) AS temp_used_cnt
FROM app a
LEFT JOIN yj1 y ON a.biz_id = y.biz_id
LEFT JOIN c010 c ON cast(a.biz_id as varchar) = c.biz_str
""", "YJ4 金额口径对账(funnel全量 9月-10月)")

print("DONE-RECON-YJ")
