# -*- coding: utf-8 -*-
"""最终导出: 离线临额C015口径效果分析 Excel
   Sheet:
   S1 机制验证_分臂覆盖率
   S2 四分类总览_按月
   S3 无在贷RCT(全量+首次推送)
   S4 有在贷首次推送分档
   S5 疲劳度
   S6 四分类逾期
   S7 纯离线分档逾期(±1天修正)
"""
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

GRANTS = """
grants AS (
  SELECT mid, MAX(create_time) AS grant_time, MAX(change_total_grantamount) AS grant_amt
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-04-01 00:00:00'
    AND create_time <  timestamp'2026-10-16 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
)
"""
APP_W = """
app AS (
  SELECT mid, app_time, app_date, if_sx_passed, if_issue, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-01' AND app_date < date'2026-10-16'
)
"""

# S1 机制验证: 分臂覆盖率(近8批)
s1 = q(f"""
WITH {GRANTS},
offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         date_trunc('day', load_time) AS base_dt
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260923','20260924','20260930','20261001','20261007','20261008','20261014','20261015')
)
SELECT o.data_date, o.temp_limit_tag,
  COUNT(DISTINCT o.mid) AS cnt,
  round(100.0*COUNT(DISTINCT CASE WHEN g.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),1) AS c015_cover_pct,
  round(AVG(g.grant_amt),0) AS avg_grant_amt
FROM offline o
LEFT JOIN grants g ON cast(o.mid as bigint)=cast(g.mid as bigint)
  AND g.grant_time >= o.base_dt AND g.grant_time < date_add('day',2,o.base_dt)
GROUP BY o.data_date, o.temp_limit_tag
ORDER BY o.data_date, o.temp_limit_tag
""", "S1")

# S2 四分类总览按月
s2 = q(f"""
WITH {GRANTS}, {APP_W},
off_exp AS (
  SELECT DISTINCT cast(a.mid as bigint) AS mid, a.app_time
  FROM app a
  JOIN grants g ON cast(a.mid as bigint)=cast(g.mid as bigint)
    AND g.grant_time <= a.app_time AND a.app_time < g.grant_time + interval '7' day
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
  round(100.0*SUM(a.if_issue)/COUNT(*),2) AS issue_rate,
  round(AVG(CASE WHEN a.if_issue=1 THEN a.contract_amount END),0) AS avg_contract
FROM app a
LEFT JOIN off_exp o ON cast(a.mid as bigint)=o.mid AND a.app_time=o.app_time
GROUP BY 1, 3
ORDER BY 1, 2
""", "S2")

# S3a 无在贷RCT全量
s3a = q(f"""
WITH offline AS (
  SELECT mid, data_date, curr_main_credit_limit,
         date_trunc('day', load_time) AS base_dt,
         CASE
           WHEN temp_limit_tag LIKE '%临额减息%' THEN '3_临额+减息'
           WHEN temp_limit_tag LIKE '%减息%'     THEN '2_减息(对照:无临额)'
           ELSE '1_临额' END AS arm
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE temp_limit_tag LIKE '%无在贷%'
), {APP_W}
SELECT o.arm,
  COUNT(DISTINCT o.mid) AS mid_cnt,
  round(AVG(o.curr_main_credit_limit),0) AS avg_main_limit,
  round(100.0*COUNT(DISTINCT CASE WHEN ap.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_apply_rate,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_apply_rate,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_issue_rate,
  round(AVG(CASE WHEN aq.if_issue=1 THEN aq.contract_amount END),0) AS avg_contract
FROM offline o
LEFT JOIN app ap ON cast(o.mid as bigint)=cast(ap.mid as bigint)
  AND ap.app_date >= date_add('day',-7,o.base_dt) AND ap.app_date < o.base_dt
LEFT JOIN app aq ON cast(o.mid as bigint)=cast(aq.mid as bigint)
  AND aq.app_date >= o.base_dt AND aq.app_date < date_add('day',7,o.base_dt)
GROUP BY 1 ORDER BY 1
""", "S3a")

# S3b 无在贷RCT首次推送
s3b = q(f"""
WITH first_push AS (
  SELECT mid, MIN(data_date) AS first_date
  FROM mx.yuhan_temp_limit_base_table_his_20260924 GROUP BY mid
),
offline AS (
  SELECT o.mid, o.temp_limit_issue_amount, o.curr_main_credit_limit,
         date_trunc('day', o.load_time) AS base_dt,
         CASE
           WHEN o.temp_limit_tag LIKE '%临额减息%' THEN '3_临额+减息'
           WHEN o.temp_limit_tag LIKE '%减息%'     THEN '2_减息(对照)'
           ELSE '1_临额' END AS arm
  FROM mx.yuhan_temp_limit_base_table_his_20260924 o
  JOIN first_push f ON cast(o.mid as bigint)=cast(f.mid as bigint) AND o.data_date=f.first_date
  WHERE o.temp_limit_tag LIKE '%无在贷%'
), {APP_W}
SELECT o.arm,
  COUNT(DISTINCT o.mid) AS mid_cnt,
  round(AVG(o.curr_main_credit_limit),0) AS avg_main,
  round(AVG(o.temp_limit_issue_amount),0) AS avg_temp,
  round(100.0*COUNT(DISTINCT CASE WHEN ap.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_apply,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_apply,
  round(100.0*COUNT(DISTINCT CASE WHEN aq.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_issue,
  round(AVG(CASE WHEN aq.if_issue=1 THEN aq.contract_amount END),0) AS post_contract
FROM offline o
LEFT JOIN app ap ON cast(o.mid as bigint)=cast(ap.mid as bigint)
  AND ap.app_date >= date_add('day',-7,o.base_dt) AND ap.app_date < o.base_dt
LEFT JOIN app aq ON cast(o.mid as bigint)=cast(aq.mid as bigint)
  AND aq.app_date >= o.base_dt AND aq.app_date < date_add('day',7,o.base_dt)
GROUP BY 1 ORDER BY 1
""", "S3b")

# S4 有在贷首次推送分档
s4 = q(f"""
WITH first_push AS (
  SELECT mid, MIN(data_date) AS first_date
  FROM mx.yuhan_temp_limit_base_table_his_20260924 GROUP BY mid
),
offline AS (
  SELECT o.mid, o.temp_limit_issue_amount, o.curr_main_credit_limit,
         date_trunc('day', o.load_time) AS base_dt,
         CASE substr(o.temp_limit_tag,-2)
           WHEN '_1' THEN '1_小额档(~450)'
           WHEN '_2' THEN '2_中额档(~1700)'
           WHEN '_3' THEN '3_大额档(~4800)'
           ELSE '9_其他' END AS tier
  FROM mx.yuhan_temp_limit_base_table_his_20260924 o
  JOIN first_push f ON cast(o.mid as bigint)=cast(f.mid as bigint) AND o.data_date=f.first_date
  WHERE o.temp_limit_tag LIKE '%有在贷%'
), {APP_W}
SELECT o.tier,
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
GROUP BY 1 ORDER BY 1
""", "S4")

# S5 疲劳度
s5 = q(f"""
WITH ranked AS (
  SELECT mid, data_date, temp_limit_tag,
         date_trunc('day', load_time) AS base_dt,
         row_number() OVER (PARTITION BY mid ORDER BY data_date) AS push_seq
  FROM mx.yuhan_temp_limit_base_table_his_20260924
), {APP_W}
SELECT
  CASE WHEN r.temp_limit_tag LIKE '%有在贷%' THEN '有在贷' ELSE '无在贷' END AS crowd,
  CASE WHEN r.push_seq >= 4 THEN '4+' ELSE cast(r.push_seq AS varchar) END AS push_seq,
  COUNT(*) AS obs_cnt,
  round(100.0*SUM(CASE WHEN aq.mid IS NOT NULL THEN 1 ELSE 0 END)/COUNT(*),2) AS post7d_apply_rate,
  round(100.0*SUM(CASE WHEN aq.if_issue=1 THEN 1 ELSE 0 END)/COUNT(*),2) AS post7d_issue_rate
FROM ranked r
LEFT JOIN app aq ON cast(r.mid as bigint)=cast(aq.mid as bigint)
  AND aq.app_date >= r.base_dt AND aq.app_date < date_add('day',7,r.base_dt)
GROUP BY 1, 2 ORDER BY 1, 2
""", "S5")

# S6/S7 逾期(匹配放宽±1天)
BASE_F7 = """
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
    AND date_trunc('day', g.grant_time) >= ob.base_dt
    AND date_trunc('day', g.grant_time) <= date_add('day',1,ob.base_dt)
),
f AS (
  SELECT mid, app_time, app_date, contract_amount, temp_grant_amount,
         is_t0_overdue_1, is_t0_overdue_2, is_t0_overdue_3, is_t0_overdue_4,
         t0_overdue_amount_1
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
s6 = q(f"""
WITH {BASE_F7}
SELECT grp,
  COUNT(*) AS issue_cnt,
  round(AVG(contract_amount),0) AS avg_contract,
  round(100.0*AVG(is_t0_overdue_1),2) AS t0_1_rate,
  round(100.0*AVG(is_t0_overdue_2),2) AS t0_2_rate,
  round(100.0*AVG(greatest(is_t0_overdue_1,is_t0_overdue_2,is_t0_overdue_3,is_t0_overdue_4)),2) AS tr_rate,
  round(100.0*SUM(t0_overdue_amount_1)/SUM(contract_amount),2) AS t0_1_amt_rate
FROM cls GROUP BY grp ORDER BY grp
""", "S6")

s7 = q(f"""
WITH {BASE_F7}
SELECT grp,
  CASE
    WHEN temp_limit_tag LIKE '%有在贷%' AND substr(temp_limit_tag,-2) IN ('_1','_2','_3')
      THEN '有在贷_' || substr(temp_limit_tag,-2) || '档'
    WHEN temp_limit_tag LIKE '%有在贷%' THEN '有在贷_早期无分档'
    WHEN temp_limit_tag LIKE '%临额减息%' THEN '无在贷_临额减息'
    WHEN temp_limit_tag LIKE '%减息%' THEN '无在贷_减息(不应有C015)'
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
    WHEN temp_limit_tag LIKE '%有在贷%' AND substr(temp_limit_tag,-2) IN ('_1','_2','_3')
      THEN '有在贷_' || substr(temp_limit_tag,-2) || '档'
    WHEN temp_limit_tag LIKE '%有在贷%' THEN '有在贷_早期无分档'
    WHEN temp_limit_tag LIKE '%临额减息%' THEN '无在贷_临额减息'
    WHEN temp_limit_tag LIKE '%减息%' THEN '无在贷_减息(不应有C015)'
    WHEN temp_limit_tag LIKE '%无在贷%' THEN '无在贷_临额'
    ELSE '未匹配批次'
  END
ORDER BY grp, sub
""", "S7")

out = r"E:\岳松个人文件\嘉银工作内容的整理\code\离线临额效果分析_C015口径_重点结论.xlsx"
with pd.ExcelWriter(out, engine='openpyxl') as w:
    s1.to_excel(w, sheet_name='S1_机制验证_分臂覆盖率', index=False)
    s2.to_excel(w, sheet_name='S2_四分类总览_按月', index=False)
    s3a.to_excel(w, sheet_name='S3a_无在贷RCT_全量', index=False)
    s3b.to_excel(w, sheet_name='S3b_无在贷RCT_首次推送', index=False)
    s4.to_excel(w, sheet_name='S4_有在贷首次推送_分档', index=False)
    s5.to_excel(w, sheet_name='S5_疲劳度', index=False)
    s6.to_excel(w, sheet_name='S6_四分类逾期', index=False)
    s7.to_excel(w, sheet_name='S7_纯离线分档逾期', index=False)

print(f"\n✅ Excel已导出: {out}")
print("DONE-EXPORT")
