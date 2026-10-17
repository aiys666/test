# -*- coding: utf-8 -*-
"""Phase2: 核心效果层
   B0 无在贷批次三臂平衡性(临额/减息/临额减息 是否随机)
   B1 无在贷批次: 三臂 前7天vs后7天 申请率/放款率 (准RCT: 临额vs减息)
   B2 有在贷批次: _1/_2/_3档 前后对比 (申请率/放款率/合同额提升)
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

# B0+B1: 无在贷批次 三臂平衡性 + 前后7天效果(全量批次汇总)
q("""
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag,
         curr_main_credit_limit,
         date_trunc('day', load_time) AS base_dt,
         CASE
           WHEN temp_limit_tag LIKE '%临额减息%' THEN '3_临额+减息'
           WHEN temp_limit_tag LIKE '%减息%'     THEN '2_减息(对照:无临额)'
           ELSE '1_临额'
         END AS arm
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE temp_limit_tag LIKE '%无在贷%'
),
app AS (
  SELECT mid, app_date, if_sx_passed, if_issue, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-15' AND app_date < date'2026-10-16'
)
SELECT
  o.arm,
  COUNT(DISTINCT o.mid) AS mid_cnt,
  round(AVG(o.curr_main_credit_limit),0) AS avg_main_limit,
  -- 前7天
  round(100.0*COUNT(DISTINCT CASE WHEN ap.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_apply_rate,
  round(100.0*COUNT(DISTINCT CASE WHEN ap.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_issue_rate,
  -- 后7天
  round(100.0*COUNT(DISTINCT CASE WHEN aq.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_apply_rate,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.mid IS NOT NULL AND aq.if_sx_passed=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_pass_rate,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_issue_rate,
  -- 后7天放款用户合同件均 + 其中领在线临额的占比
  round(AVG(CASE WHEN aq.if_issue=1 THEN aq.contract_amount END),0) AS avg_contract,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.if_issue=1 AND aq.temp_grant_amount>0 THEN o.mid END)
        /NULLIF(COUNT(DISTINCT CASE WHEN aq.if_issue=1 THEN o.mid END),0),2) AS issue_with_online_pct
FROM offline o
LEFT JOIN app ap ON cast(o.mid as bigint)=cast(ap.mid as bigint)
  AND ap.app_date >= date_add('day',-7,o.base_dt) AND ap.app_date < o.base_dt
LEFT JOIN app aq ON cast(o.mid as bigint)=cast(aq.mid as bigint)
  AND aq.app_date >= o.base_dt AND aq.app_date < date_add('day',7,o.base_dt)
GROUP BY 1
ORDER BY 1
""", "B0+B1 无在贷批次三臂: 平衡性+前后7天效果(全量4-10月)")

# B2: 有在贷批次 _1/_2/_3档 前后7天对比
q("""
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag,
         curr_main_credit_limit, onloan_bal, temp_limit_issue_amount,
         date_trunc('day', load_time) AS base_dt,
         CASE
           WHEN temp_limit_tag LIKE '%\_1' THEN '1_小额档(~450)'
           WHEN temp_limit_tag LIKE '%\_2' THEN '2_中额档(~1700)'
           WHEN temp_limit_tag LIKE '%\_3' THEN '3_大额档(~4800)'
           ELSE '9_其他'
         END AS tier
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE temp_limit_tag LIKE '%有在贷%'
),
app AS (
  SELECT mid, app_date, if_sx_passed, if_issue, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-15' AND app_date < date'2026-10-16'
)
SELECT
  o.tier,
  COUNT(DISTINCT o.mid) AS mid_cnt,
  round(AVG(o.curr_main_credit_limit),0) AS avg_main_limit,
  round(AVG(o.temp_limit_issue_amount),0) AS avg_temp_amt,
  -- 前7天
  round(100.0*COUNT(DISTINCT CASE WHEN ap.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_apply_rate,
  round(100.0*COUNT(DISTINCT CASE WHEN ap.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_issue_rate,
  -- 后7天
  round(100.0*COUNT(DISTINCT CASE WHEN aq.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_apply_rate,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_issue_rate,
  round(AVG(CASE WHEN aq.if_issue=1 THEN aq.contract_amount END),0) AS avg_contract,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.if_issue=1 AND aq.temp_grant_amount>0 THEN o.mid END)
        /NULLIF(COUNT(DISTINCT CASE WHEN aq.if_issue=1 THEN o.mid END),0),2) AS issue_with_online_pct
FROM offline o
LEFT JOIN app ap ON cast(o.mid as bigint)=cast(ap.mid as bigint)
  AND ap.app_date >= date_add('day',-7,o.base_dt) AND ap.app_date < o.base_dt
LEFT JOIN app aq ON cast(o.mid as bigint)=cast(aq.mid as bigint)
  AND aq.app_date >= o.base_dt AND aq.app_date < date_add('day',7,o.base_dt)
WHERE o.tier <> '9_其他'
GROUP BY 1
ORDER BY 1
""", "B2 有在贷批次三档: 前后7天对比(全量4-10月)")

# B2b: 有在贷 按月看提升幅度是否衰减
q("""
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag,
         date_trunc('day', load_time) AS base_dt,
         date_format(date_parse(data_date,'%Y%m%d'),'%Y-%m') AS batch_month
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE temp_limit_tag LIKE '%有在贷%'
),
app AS (
  SELECT mid, app_date, if_issue
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-15' AND app_date < date'2026-10-16'
)
SELECT
  o.batch_month,
  COUNT(DISTINCT o.mid) AS mid_cnt,
  round(100.0*COUNT(DISTINCT CASE WHEN ap.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_apply_rate,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_apply_rate,
  round(100.0*COUNT(DISTINCT CASE WHEN ap.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_issue_rate,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_issue_rate
FROM offline o
LEFT JOIN app ap ON cast(o.mid as bigint)=cast(ap.mid as bigint)
  AND ap.app_date >= date_add('day',-7,o.base_dt) AND ap.app_date < o.base_dt
LEFT JOIN app aq ON cast(o.mid as bigint)=cast(aq.mid as bigint)
  AND aq.app_date >= o.base_dt AND aq.app_date < date_add('day',7,o.base_dt)
GROUP BY 1
ORDER BY 1
""", "B2b 有在贷按月: 前后7天申请率/放款率(看是否衰减)")

print("DONE-PHASE2")
