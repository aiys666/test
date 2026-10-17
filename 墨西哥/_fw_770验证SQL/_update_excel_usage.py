# -*- coding: utf-8 -*-
"""把修正后的真实使用量逾期分析更新到Excel"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 620)

def q(sql, tag):
    print("=" * 100); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return pd.DataFrame()
            print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:200]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}"); return pd.DataFrame()

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: print("[login retry]"); time.sleep(8)

BASE = """
grants AS (
  SELECT mid, MAX(create_time) AS grant_time
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-04-01 00:00:00'
    AND create_time <  timestamp'2026-09-01 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
),
freeze AS (
  SELECT biz_id,
         SUM(CASE WHEN limit_type='MAIN' THEN risk_credit_limit ELSE 0 END) AS main_used,
         SUM(CASE WHEN limit_type='TEMP' THEN risk_credit_limit ELSE 0 END) AS temp_used
  FROM ods.s05_user_creditlimit_used_detail
  WHERE change_action='FREEZE_LIMIT'
    AND create_time >= timestamp'2026-04-01 00:00:00'
  GROUP BY biz_id
),
app AS (
  SELECT a.mid, a.biz_id, a.app_time, a.app_date, a.contract_amount, a.temp_grant_amount,
         f.is_t0_overdue_1, f.is_t0_overdue_2, f.is_t0_overdue_3, f.is_t0_overdue_4,
         f.t0_overdue_amount_1,
         CASE WHEN g.mid IS NOT NULL THEN 1 ELSE 0 END AS has_offline
  FROM mx.wxs_application_funnel a
  JOIN mx.report_application_funnel7 f
    ON cast(a.mid as bigint)=cast(f.mid as bigint) AND a.app_time = f.app_time
  LEFT JOIN grants g ON cast(a.mid as bigint)=cast(g.mid as bigint)
    AND g.grant_time <= a.app_time AND a.app_time < g.grant_time + interval '7' day
  WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
    AND a.app_date >= date'2026-04-01' AND a.app_date <= date'2026-08-31'
),
cls AS (
  SELECT a.*, fr.temp_used, fr.main_used,
    CASE
      WHEN fr.temp_used > 0 AND a.temp_grant_amount > 0 AND a.has_offline=1 THEN 'D_混合'
      WHEN fr.temp_used > 0 AND a.temp_grant_amount > 0 THEN 'C_纯在线使用'
      WHEN fr.temp_used > 0 AND a.temp_grant_amount = 0 THEN 'B_纯离线使用'
      ELSE 'A_未使用临额'
    END AS real_grp
  FROM app a
  JOIN freeze fr ON cast(a.biz_id as bigint) = fr.biz_id
)
"""

s8 = q(f"""
WITH {BASE}
SELECT
  CASE
    WHEN temp_used = 0 THEN '0_未使用'
    WHEN temp_used <= 500 THEN '1_<=500'
    WHEN temp_used <= 1000 THEN '2_500~1k'
    WHEN temp_used <= 2000 THEN '3_1k~2k'
    ELSE '4_>2k'
  END AS temp_used_bucket,
  COUNT(*) AS issue_cnt,
  round(AVG(contract_amount),0) AS avg_contract,
  round(AVG(main_used),0) AS avg_main_used,
  round(AVG(temp_used),0) AS avg_temp_used,
  round(100.0*AVG(is_t0_overdue_1),2) AS t0_1_rate,
  round(100.0*AVG(is_t0_overdue_2),2) AS t0_2_rate,
  round(100.0*AVG(greatest(is_t0_overdue_1,is_t0_overdue_2,is_t0_overdue_3,is_t0_overdue_4)),2) AS tr_rate,
  round(100.0*SUM(t0_overdue_amount_1)/SUM(contract_amount),2) AS t0_1_amt_rate
FROM cls
GROUP BY 1 ORDER BY 1
""", "S8")

s9 = q(f"""
WITH {BASE}
SELECT real_grp,
  COUNT(*) AS issue_cnt,
  round(AVG(contract_amount),0) AS avg_contract,
  round(AVG(temp_used),0) AS avg_temp_used,
  round(100.0*AVG(is_t0_overdue_1),2) AS t0_1_rate,
  round(100.0*AVG(is_t0_overdue_2),2) AS t0_2_rate,
  round(100.0*AVG(greatest(is_t0_overdue_1,is_t0_overdue_2,is_t0_overdue_3,is_t0_overdue_4)),2) AS tr_rate,
  round(100.0*SUM(t0_overdue_amount_1)/SUM(contract_amount),2) AS t0_1_amt_rate
FROM cls
GROUP BY 1 ORDER BY 1
""", "S9")

s10 = q(f"""
WITH {BASE}
SELECT
  CASE WHEN has_offline=1 THEN '持有离线临额' ELSE '未持有离线' END AS hold_offline,
  CASE WHEN temp_used > 0 THEN '实际使用了临额' ELSE '未使用临额' END AS use_temp,
  COUNT(*) AS issue_cnt,
  round(AVG(contract_amount),0) AS avg_contract,
  round(100.0*AVG(is_t0_overdue_1),2) AS t0_1_rate,
  round(100.0*AVG(is_t0_overdue_2),2) AS t0_2_rate
FROM cls
GROUP BY 1, 2 ORDER BY 1, 2
""", "S10")

# 标签准确性核对
s11 = q(f"""
WITH grants AS (
  SELECT mid, MAX(create_time) AS grant_time
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-09-01 00:00:00'
    AND create_time <  timestamp'2026-10-16 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
),
freeze AS (
  SELECT biz_id, SUM(CASE WHEN limit_type='TEMP' THEN risk_credit_limit ELSE 0 END) AS temp_used
  FROM ods.s05_user_creditlimit_used_detail
  WHERE change_action='FREEZE_LIMIT' AND create_time >= timestamp'2026-09-01 00:00:00'
  GROUP BY biz_id
),
app AS (
  SELECT a.mid, a.biz_id, a.app_time, a.contract_amount, a.temp_grant_amount,
         CASE WHEN g.mid IS NOT NULL THEN 1 ELSE 0 END AS has_offline
  FROM mx.wxs_application_funnel a
  LEFT JOIN grants g ON cast(a.mid as bigint)=cast(g.mid as bigint)
    AND g.grant_time <= a.app_time AND a.app_time < g.grant_time + interval '7' day
  WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
    AND a.app_date >= date'2026-09-01' AND a.app_date < date'2026-10-16'
),
cls AS (
  SELECT a.biz_id,
    CASE
      WHEN a.has_offline=1 AND a.temp_grant_amount > 0 THEN '3_混合(持有)'
      WHEN a.has_offline=1 THEN '1_纯离线(持有)'
      WHEN a.temp_grant_amount > 0 THEN '2_纯在线(持有)'
      ELSE '4_无临额(持有)'
    END AS hold_grp,
    CASE WHEN fr.temp_used > 0 THEN 1 ELSE 0 END AS actual_use
  FROM app a
  JOIN freeze fr ON cast(a.biz_id as bigint) = fr.biz_id
)
SELECT hold_grp,
  COUNT(*) AS issue_cnt,
  round(100.0*SUM(actual_use)/COUNT(*),2) AS actual_use_temp_pct,
  round(AVG(fr.temp_used),0) AS avg_temp_used_all,
  round(AVG(CASE WHEN fr.temp_used > 0 THEN fr.temp_used END),0) AS avg_temp_used_when_used
FROM cls
GROUP BY 1 ORDER BY 1
""", "S11")

out = r"E:\岳松个人文件\嘉银工作内容的整理\code\离线临额效果分析_C015口径_重点结论.xlsx"
xls = pd.ExcelFile(out)
existing = {s: pd.read_excel(out, sheet_name=s) for s in xls.sheet_names}

with pd.ExcelWriter(out, engine='openpyxl') as w:
    for s, df in existing.items():
        if s in ('S6_四分类逾期','S7_纯离线分档逾期'):
            continue  # 旧口径sheet删除
        df.to_excel(w, sheet_name=s, index=False)
    s8.to_excel(w, sheet_name='S6_按实际使用量分桶逾期', index=False)
    s9.to_excel(w, sheet_name='S7_真实四分类逾期', index=False)
    s10.to_excel(w, sheet_name='S8_持有x使用交叉逾期', index=False)
    s11.to_excel(w, sheet_name='S9_标签准确性核对', index=False)

print("✅ Excel已更新，旧S6/S7(持有口径)已替换为真实使用量口径")
