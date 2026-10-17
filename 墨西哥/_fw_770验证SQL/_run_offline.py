# -*- coding: utf-8 -*-
"""离线临额效果分析: 发临额后5天内的放款率/额度使用率, 对比非离线临额用户"""
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
# D1: 离线临额用户 发临额后5天内的放款率 (按批次)
# ============================================================
d1 = q("""
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         temp_limit_issue_amount, curr_main_credit_limit, curr_temp_credit_limit,
         onloan_bal, onloan_cnt
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260819','20260820','20260826','20260827','20260902','20260903','20260909','20260910')
),
app AS (
  SELECT mid, app_date, if_sx_passed, if_issue, contract_amount,
         temp_grant_amount, credit_amount_sx,
         daily_max_available_limit_sx
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-08-19' AND app_date < date'2026-09-16'
)
SELECT
  o.data_date,
  o.tagg,
  o.temp_limit_tag,
  COUNT(DISTINCT o.mid) AS offline_mid_cnt,
  COUNT(DISTINCT CASE WHEN a.mid IS NOT NULL THEN o.mid END) AS apply_mid_cnt,
  COUNT(DISTINCT CASE WHEN a.if_sx_passed=1 THEN o.mid END) AS passed_mid_cnt,
  COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN o.mid END) AS issue_mid_cnt,
  round(100.0*COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN o.mid END)/NULLIF(COUNT(DISTINCT o.mid),0),2) AS issue_rate
FROM offline o
LEFT JOIN app a ON cast(o.mid as bigint)=cast(a.mid as bigint)
  AND a.app_date >= date_parse(o.data_date,'%Y%m%d')
  AND a.app_date <= date_add('day', 5, date_parse(o.data_date,'%Y%m%d'))
GROUP BY o.data_date, o.tagg, o.temp_limit_tag
ORDER BY o.data_date, o.temp_limit_tag
""", "D1 离线临额用户放款率(发临额后5天内)")

# ============================================================
# D2: 对照组 - 同期非离线临额用户的放款率
# ============================================================
d2 = q("""
WITH offline_mid AS (
  SELECT DISTINCT mid FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260819','20260820','20260826','20260827','20260902','20260903','20260909','20260910')
),
app AS (
  SELECT mid, app_date, if_sx_passed, if_issue, contract_amount,
         temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-08-19' AND app_date < date'2026-09-16'
)
SELECT
  '非离线临额用户' AS grp,
  COUNT(DISTINCT a.mid) AS total_mid,
  COUNT(DISTINCT CASE WHEN a.if_sx_passed=1 THEN a.mid END) AS passed_mid,
  COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN a.mid END) AS issue_mid,
  round(100.0*COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN a.mid END)/NULLIF(COUNT(DISTINCT a.mid),0),2) AS issue_rate
FROM app a
LEFT JOIN offline_mid o ON cast(a.mid as bigint)=cast(o.mid as bigint)
WHERE o.mid IS NULL
""", "D2 对照组(非离线临额用户)放款率")

# ============================================================
# D3: 离线临额用户的额度使用率 (发临额后5天内放款的合同)
# ============================================================
d3 = q("""
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         temp_limit_issue_amount, curr_main_credit_limit, curr_temp_credit_limit
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260819','20260820','20260826','20260827','20260902','20260903','20260909','20260910')
),
app AS (
  SELECT mid, app_date, if_issue, contract_amount,
         temp_grant_amount, credit_amount_sx,
         daily_max_available_limit_sx
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-08-19' AND app_date < date'2026-09-16'
    AND if_issue = 1
)
SELECT
  o.tagg,
  COUNT(*) AS issue_cnt,
  round(AVG(a.contract_amount),0) AS avg_contract,
  round(AVG(o.temp_limit_issue_amount),0) AS avg_offline_temp,
  round(AVG(a.temp_grant_amount/1000.0),0) AS avg_online_temp,
  round(AVG(o.curr_main_credit_limit),0) AS avg_main_limit,
  -- 额度使用率 = 合同额 / (主额+临额)
  round(100.0*AVG(a.contract_amount / NULLIF(o.curr_main_credit_limit + o.curr_temp_credit_limit, 0)),2) AS amount_use_rate
FROM offline o
JOIN app a ON cast(o.mid as bigint)=cast(a.mid as bigint)
  AND a.app_date >= date_parse(o.data_date,'%Y%m%d')
  AND a.app_date <= date_add('day', 5, date_parse(o.data_date,'%Y%m%d'))
GROUP BY o.tagg
ORDER BY o.tagg
""", "D3 离线临额用户额度使用率(放款样本)")

# ============================================================
# D4: 临额金额分桶对放款率的影响
# ============================================================
d4 = q("""
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         temp_limit_issue_amount, curr_main_credit_limit
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260819','20260820','20260826','20260827','20260902','20260903','20260909','20260910')
),
app AS (
  SELECT mid, app_date, if_issue, contract_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-08-19' AND app_date < date'2026-09-16'
)
SELECT
  CASE
    WHEN o.temp_limit_issue_amount <= 500 THEN '1_<=500'
    WHEN o.temp_limit_issue_amount <= 1000 THEN '2_500~1k'
    WHEN o.temp_limit_issue_amount <= 2000 THEN '3_1k~2k'
    WHEN o.temp_limit_issue_amount <= 3000 THEN '4_2k~3k'
    ELSE '5_>3k'
  END AS temp_amt_bucket,
  o.tagg,
  COUNT(DISTINCT o.mid) AS mid_cnt,
  COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN o.mid END) AS issue_mid,
  round(100.0*COUNT(DISTINCT CASE WHEN a.if_issue=1 THEN o.mid END)/NULLIF(COUNT(DISTINCT o.mid),0),2) AS issue_rate,
  round(AVG(o.temp_limit_issue_amount),0) AS avg_temp_amt
FROM offline o
LEFT JOIN app a ON cast(o.mid as bigint)=cast(a.mid as bigint)
  AND a.app_date >= date_parse(o.data_date,'%Y%m%d')
  AND a.app_date <= date_add('day', 5, date_parse(o.data_date,'%Y%m%d'))
GROUP BY 1, o.tagg
ORDER BY 1, o.tagg
""", "D4 临额金额分桶对放款率的影响")

# 导出Excel
out = r"E:\岳松个人文件\嘉银工作内容的整理\code\离线临额效果分析_重点结论.xlsx"
with pd.ExcelWriter(out, engine='openpyxl') as w:
    if d1 is not None: d1.to_excel(w, sheet_name='D1_各批次放款率', index=False)
    if d2 is not None: d2.to_excel(w, sheet_name='D2_对照组放款率', index=False)
    if d3 is not None: d3.to_excel(w, sheet_name='D3_额度使用率', index=False)
    if d4 is not None: d4.to_excel(w, sheet_name='D4_临额金额分桶放款率', index=False)

print(f"\n✅ Excel已导出: {out}")
print("DONE-OFFLINE")
