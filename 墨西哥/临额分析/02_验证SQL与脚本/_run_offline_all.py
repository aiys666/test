# -*- coding: utf-8 -*-
"""离线临额全量分析: 所有52个批次, 用load_time作为发放基准日
   关联逻辑: load_time为批次执行日, app_date在load_time后5天内
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 620)

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

# ============================================================
# D1: 全部批次概览 - 每个data_date的放款率
# 用load_time作为基准日(批次执行日), app_date在load_time后5天内
# ============================================================
d1 = q("""
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         temp_limit_issue_amount, curr_main_credit_limit, curr_temp_credit_limit,
         onloan_bal, onloan_cnt,
         date_trunc('day', load_time) AS issue_base_date
  FROM mx.yuhan_temp_limit_base_table_his_20260924
),
app AS (
  SELECT mid, app_date, if_sx_passed, if_issue, contract_amount,
         temp_grant_amount, credit_amount_sx, daily_max_available_limit_sx
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-21' AND app_date < date'2026-10-16'
)
SELECT
  o.data_date,
  o.issue_base_date,
  o.temp_limit_tag,
  o.tagg,
  COUNT(DISTINCT o.mid) AS offline_mid_cnt,
  COUNT(DISTINCT CASE WHEN a.mid IS NOT NULL THEN o.mid END) AS apply_mid_cnt,
  COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN o.mid END) AS issue_mid_cnt,
  round(100.0*COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN o.mid END)/NULLIF(COUNT(DISTINCT o.mid),0),2) AS issue_rate,
  round(AVG(o.temp_limit_issue_amount),0) AS avg_issue_amt,
  round(AVG(o.curr_main_credit_limit),0) AS avg_main_limit
FROM offline o
LEFT JOIN app a ON cast(o.mid as bigint)=cast(a.mid as bigint)
  AND a.app_date >= o.issue_base_date
  AND a.app_date <= date_add('day', 5, o.issue_base_date)
GROUP BY o.data_date, o.issue_base_date, o.temp_limit_tag, o.tagg
ORDER BY o.data_date, o.temp_limit_tag
""", "D1 全部52批次放款率(以load_time为基准)")

# ============================================================
# D2: 汇总 - 按人群类型(有在贷/无在贷/额度不足)汇总放款率
# ============================================================
d2 = q("""
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         temp_limit_issue_amount, curr_main_credit_limit, curr_temp_credit_limit,
         onloan_bal, onloan_cnt,
         date_trunc('day', load_time) AS issue_base_date
  FROM mx.yuhan_temp_limit_base_table_his_20260924
),
app AS (
  SELECT mid, app_date, if_sx_passed, if_issue, contract_amount,
         temp_grant_amount, credit_amount_sx, daily_max_available_limit_sx
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-21' AND app_date < date'2026-10-16'
)
SELECT
  o.tagg,
  CASE
    WHEN o.temp_limit_tag LIKE '%减息%' AND o.temp_limit_tag NOT LIKE '%临额%' THEN '减息组'
    WHEN o.temp_limit_tag LIKE '%临额减息%' THEN '临额+减息组'
    WHEN o.temp_limit_tag LIKE '%临额%' THEN '临额组'
    ELSE '其他'
  END AS exp_group,
  COUNT(DISTINCT o.mid) AS mid_cnt,
  COUNT(DISTINCT CASE WHEN a.mid IS NOT NULL THEN o.mid END) AS apply_mid_cnt,
  COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN o.mid END) AS issue_mid_cnt,
  round(100.0*COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN o.mid END)/NULLIF(COUNT(DISTINCT o.mid),0),2) AS issue_rate,
  round(AVG(o.temp_limit_issue_amount),0) AS avg_issue_amt
FROM offline o
LEFT JOIN app a ON cast(o.mid as bigint)=cast(a.mid as bigint)
  AND a.app_date >= o.issue_base_date
  AND a.app_date <= date_add('day', 5, o.issue_base_date)
GROUP BY o.tagg,
  CASE
    WHEN o.temp_limit_tag LIKE '%减息%' AND o.temp_limit_tag NOT LIKE '%临额%' THEN '减息组'
    WHEN o.temp_limit_tag LIKE '%临额减息%' THEN '临额+减息组'
    WHEN o.temp_limit_tag LIKE '%临额%' THEN '临额组'
    ELSE '其他'
  END
ORDER BY o.tagg, exp_group
""", "D2 按人群x实验组汇总放款率")

# ============================================================
# D3: 有在贷人群 - 按月份汇总放款率趋势
# ============================================================
d3 = q("""
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         temp_limit_issue_amount,
         date_trunc('day', load_time) AS issue_base_date,
         date_trunc('month', date_parse(data_date,'%Y%m%d')) AS batch_month
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE temp_limit_tag LIKE '%有在贷%'
),
app AS (
  SELECT mid, app_date, if_issue
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-21' AND app_date < date'2026-10-16'
)
SELECT
  date_format(o.batch_month, '%Y-%m') AS batch_month,
  o.tagg,
  COUNT(DISTINCT o.mid) AS mid_cnt,
  COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN o.mid END) AS issue_mid_cnt,
  round(100.0*COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN o.mid END)/NULLIF(COUNT(DISTINCT o.mid),0),2) AS issue_rate,
  round(AVG(o.temp_limit_issue_amount),0) AS avg_issue_amt
FROM offline o
LEFT JOIN app a ON cast(o.mid as bigint)=cast(a.mid as bigint)
  AND a.app_date >= o.issue_base_date
  AND a.app_date <= date_add('day', 5, o.issue_base_date)
GROUP BY date_format(o.batch_month, '%Y-%m'), o.tagg
ORDER BY batch_month, o.tagg
""", "D3 有在贷人群按月放款率趋势")

# ============================================================
# D4: 对照组 - 同期非离线临额用户放款率(分有在贷/无在贷)
# ============================================================
d4 = q("""
WITH offline_mid AS (
  SELECT DISTINCT mid FROM mx.yuhan_temp_limit_base_table_his_20260924
),
app AS (
  SELECT mid, app_date, if_sx_passed, if_issue, contract_amount,
         temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-21' AND app_date < date'2026-10-16'
)
SELECT
  CASE WHEN a.temp_grant_amount > 0 THEN '有临额' ELSE '无临额' END AS has_online_temp,
  COUNT(DISTINCT a.mid) AS total_mid,
  COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN a.mid END) AS issue_mid,
  round(100.0*COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN a.mid END)/NULLIF(COUNT(DISTINCT a.mid),0),2) AS issue_rate
FROM app a
LEFT JOIN offline_mid o ON cast(a.mid as bigint)=cast(o.mid as bigint)
WHERE o.mid IS NULL
GROUP BY CASE WHEN a.temp_grant_amount > 0 THEN '有临额' ELSE '无临额' END
""", "D4 对照组放款率(非离线临额用户, 分有无在线临额)")

# 导出Excel
out = r"E:\岳松个人文件\嘉银工作内容的整理\code\离线临额效果分析_全量.xlsx"
with pd.ExcelWriter(out, engine='openpyxl') as w:
    if d1 is not None: d1.to_excel(w, sheet_name='D1_全部52批次明细', index=False)
    if d2 is not None: d2.to_excel(w, sheet_name='D2_人群x实验组汇总', index=False)
    if d3 is not None: d3.to_excel(w, sheet_name='D3_有在贷按月趋势', index=False)
    if d4 is not None: d4.to_excel(w, sheet_name='D4_对照组', index=False)

print(f"\n✅ Excel已导出: {out}")
print("DONE-ALL-OFFLINE")
