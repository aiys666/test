# -*- coding: utf-8 -*-
"""最终方案: 双字段重建
每笔放款三个金额:
  online_grant = C010事件(external_id=biz_id)的发放额  -> 进件时领的在线临额
  offline_grant= 申请前7天内最近C015/C013发放额        -> 离线推送发放
  temp_used    = FREEZE_LIMIT的TEMP额(=temp_grant_amount) -> 本笔实际使用临额
来源判定:
  有C010(by biz) -> 在线使用(Z4证明99.7% temp_used=C010金额, 领即用)
  无C010但temp_used>0 -> 离线池使用
W1: 5344笔纯离线使用: temp_used vs offline_grant金额关系
W2: 最终2x3分类 x 数量/金额
W3: 最终分类逾期率
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

# W1: 纯离线使用笔(无C010+temp>0) 的 temp_used vs offline_grant
q("""
WITH app AS (
  SELECT mid, biz_id, app_time, app_date, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
    AND temp_grant_amount > 0
),
c010_biz AS (
  SELECT DISTINCT external_id FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C010' AND create_time >= timestamp'2026-08-25 00:00:00'
),
off AS (
  SELECT mid, off_amt, off_time FROM (
    SELECT cast(mid as bigint) AS mid, change_total_grantamount AS off_amt, create_time AS off_time,
           row_number() OVER (PARTITION BY mid ORDER BY create_time DESC) rn
    FROM ods_view_presto.s05_user_creditlimit_change_record
    WHERE change_event_type IN ('C015','C013')
      AND create_time >= timestamp'2026-04-01 00:00:00'
  ) t WHERE rn=1
),
u AS (
  SELECT a.mid, a.biz_id, a.app_time, a.temp_grant_amount/1000.0 AS temp_used,
         o.off_amt, o.off_time,
         date_diff('day', o.off_time, a.app_time) AS gap_days
  FROM app a
  LEFT JOIN c010_biz c ON cast(a.biz_id as varchar)=c.external_id
  JOIN off o ON cast(a.mid as bigint)=o.mid
  WHERE c.external_id IS NULL
)
SELECT
  CASE
    WHEN gap_days <= 7 THEN '1_离线发放后7天内'
    WHEN gap_days <= 14 THEN '2_8-14天'
    WHEN gap_days <= 30 THEN '3_15-30天'
    ELSE '4_30天以上'
  END AS gap_bucket,
  COUNT(*) AS cnt,
  round(AVG(temp_used),0) AS avg_temp_used,
  round(AVG(off_amt),0) AS avg_offline_grant,
  round(100.0*SUM(CASE WHEN temp_used <= off_amt + 1 THEN 1 ELSE 0 END)/COUNT(*),2) AS used_le_grant_pct
FROM u
GROUP BY 1 ORDER BY 1
""", "W1 纯离线使用笔: 实际使用额 vs 离线发放额")

# W2+W3: 最终2x3分类
FINAL = """
c010 AS (
  SELECT external_id, MAX(change_total_grantamount) AS online_grant
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C010'
    AND create_time >= timestamp'2026-04-01 00:00:00'
  GROUP BY external_id
),
off7 AS (
  SELECT mid, app_time, offline_grant FROM (
    SELECT cast(a.mid as bigint) AS mid, a.app_time,
           g.change_total_grantamount AS offline_grant,
           row_number() OVER (PARTITION BY cast(a.mid as bigint), a.app_time ORDER BY g.create_time DESC) rn
    FROM mx.wxs_application_funnel a
    JOIN ods_view_presto.s05_user_creditlimit_change_record g
      ON cast(a.mid as bigint)=cast(g.mid as bigint)
     AND g.change_event_type IN ('C015','C013')
     AND g.create_time <= a.app_time
     AND a.app_time < g.create_time + interval '7' day
    WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
      AND a.app_date >= date'2026-04-01' AND a.app_date <= date'2026-08-31'
  ) t WHERE rn=1
),
app AS (
  SELECT a.mid, a.biz_id, a.app_time, a.app_date, a.contract_amount,
         a.temp_grant_amount/1000.0 AS temp_used,
         f.is_t0_overdue_1, f.is_t0_overdue_2, f.is_t0_overdue_3, f.is_t0_overdue_4,
         f.t0_overdue_amount_1,
         c.online_grant,
         o.offline_grant
  FROM mx.wxs_application_funnel a
  JOIN mx.report_application_funnel7 f
    ON cast(a.mid as bigint)=cast(f.mid as bigint) AND a.app_time=f.app_time
  LEFT JOIN c010 c ON cast(a.biz_id as varchar)=c.external_id
  LEFT JOIN off7 o ON cast(a.mid as bigint)=o.mid AND a.app_time=o.app_time
  WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
    AND a.app_date >= date'2026-04-01' AND a.app_date <= date'2026-08-31'
),
cls AS (
  SELECT *,
    CASE WHEN offline_grant IS NOT NULL THEN '持有离线(7d内)' ELSE '未持有离线' END AS hold_offline,
    CASE
      WHEN temp_used = 0 THEN '0_未使用临额'
      WHEN online_grant IS NOT NULL THEN '1_在线临额使用(C010)'
      ELSE '2_离线临额池使用'
    END AS use_source
  FROM app
)
"""

q(f"""
WITH {FINAL}
SELECT hold_offline, use_source,
  COUNT(*) AS loan_cnt,
  round(AVG(contract_amount),0) AS avg_contract,
  round(AVG(COALESCE(offline_grant,0)),0) AS avg_offline_grant,
  round(AVG(COALESCE(online_grant,0)),0) AS avg_online_grant,
  round(AVG(temp_used),0) AS avg_temp_used
FROM cls
GROUP BY 1, 2
ORDER BY 1, 2
""", "W2 最终2x3分类: 数量+三金额字段(4-8月)")

q(f"""
WITH {FINAL}
SELECT hold_offline, use_source,
  COUNT(*) AS loan_cnt,
  round(AVG(contract_amount),0) AS avg_contract,
  round(AVG(temp_used),0) AS avg_temp_used,
  round(100.0*AVG(is_t0_overdue_1),2) AS t0_1_rate,
  round(100.0*AVG(is_t0_overdue_2),2) AS t0_2_rate,
  round(100.0*AVG(greatest(is_t0_overdue_1,is_t0_overdue_2,is_t0_overdue_3,is_t0_overdue_4)),2) AS tr_rate,
  round(100.0*SUM(t0_overdue_amount_1)/SUM(contract_amount),2) AS t0_1_amt_rate
FROM cls
GROUP BY 1, 2
ORDER BY 1, 2
""", "W3 最终分类逾期率(4-8月放款)")

print("DONE-FINAL")
