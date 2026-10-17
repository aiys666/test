# -*- coding: utf-8 -*-
"""三组交叉验证:
X1 我的C015暴露标签 vs 官方8批次标签(temp_limit_tag_0819等窗口口径)
X2 在线临额: funnel.temp_grant_amount vs C010事件(external_id=biz) 数量/金额对账
X3 混合拆解: 每笔放款同时给出 offline_grant / online_grant / temp_used 三个金额
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

# ============================================================
# X1: 官方8批次标签 vs 我的C015暴露标签
# 官方口径: 窗口[load日, load日+5]共6个自然日, 标签含全部臂(含减息组)
# 我的口径: C015/C013事件精确时间起7天, 只含实际发临额者(不含减息组)
# ============================================================
q("""
WITH base AS (
  SELECT mid, temp_limit_tag,
         CASE WHEN temp_limit_tag LIKE '%临额减息%' THEN '临额减息'
              WHEN temp_limit_tag LIKE '%减息%' THEN '减息'
              ELSE '临额' END AS arm,
         data_date
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260819','20260820','20260826','20260827',
                      '20260902','20260903','20260909','20260910')
),
app AS (
  SELECT mid, biz_id, app_time, app_date
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-08-18' AND app_date <= date'2026-09-14'
),
official AS (   -- 复刻用户SQL的8个窗口
  SELECT a.mid, a.biz_id, a.app_time, b.arm, b.data_date
  FROM app a
  JOIN base b ON cast(a.mid as bigint)=cast(b.mid as bigint)
  WHERE (b.data_date='20260819' AND a.app_date BETWEEN date'2026-08-18' AND date'2026-08-23')
     OR (b.data_date='20260820' AND a.app_date BETWEEN date'2026-08-19' AND date'2026-08-24')
     OR (b.data_date='20260826' AND a.app_date BETWEEN date'2026-08-25' AND date'2026-08-30')
     OR (b.data_date='20260827' AND a.app_date BETWEEN date'2026-08-26' AND date'2026-08-31')
     OR (b.data_date='20260902' AND a.app_date BETWEEN date'2026-09-01' AND date'2026-09-06')
     OR (b.data_date='20260903' AND a.app_date BETWEEN date'2026-09-02' AND date'2026-09-07')
     OR (b.data_date='20260909' AND a.app_date BETWEEN date'2026-09-08' AND date'2026-09-13')
     OR (b.data_date='20260910' AND a.app_date BETWEEN date'2026-09-09' AND date'2026-09-14')
),
mine AS (   -- 我的C015/C013精确时间7天暴露
  SELECT DISTINCT cast(a.mid as bigint) AS mid, a.app_time
  FROM app a
  JOIN ods_view_presto.s05_user_creditlimit_change_record g
    ON cast(a.mid as bigint)=cast(g.mid as bigint)
   AND g.change_event_type IN ('C015','C013')
   AND g.create_time <= a.app_time
   AND a.app_time < g.create_time + interval '7' day
  WHERE g.create_time >= timestamp'2026-08-18 00:00:00'
    AND g.create_time <  timestamp'2026-09-15 00:00:00'
)
SELECT
  CASE WHEN o.biz_id IS NOT NULL THEN '官方有标签' ELSE '官方无标签' END AS official_flag,
  CASE WHEN m.mid IS NOT NULL THEN '我的C015暴露' ELSE '我未标暴露' END AS mine_flag,
  o.arm,
  COUNT(*) AS app_cnt
FROM app a
LEFT JOIN official o ON cast(a.mid as bigint)=cast(o.mid as bigint) AND a.app_time=o.app_time
LEFT JOIN mine m ON cast(a.mid as bigint)=m.mid AND a.app_time=m.app_time
GROUP BY 1, 2, o.arm
ORDER BY 1, 2, o.arm
""", "X1 官方8批次标签 vs 我的C015暴露(交叉表, 分臂)")

# ============================================================
# X2: 在线临额 funnel.temp_grant_amount vs C010事件 对账
# ============================================================
q("""
WITH app AS (
  SELECT mid, biz_id, app_time, app_date, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
c010 AS (
  SELECT external_id,
         MAX(change_total_grantamount) AS c010_amt,
         MAX(create_time) AS c010_time
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C010'
    AND create_time >= timestamp'2026-09-01 00:00:00'
  GROUP BY external_id
)
SELECT
  CASE WHEN a.temp_grant_amount > 0 THEN 'funnel有在线临额' ELSE 'funnel无' END AS funnel_flag,
  CASE WHEN c.external_id IS NOT NULL THEN 'C010有事件' ELSE 'C010无' END AS c010_flag,
  COUNT(*) AS loan_cnt,
  round(AVG(a.temp_grant_amount/1000.0),2) AS avg_funnel_amt_peso,
  round(AVG(c.c010_amt),2) AS avg_c010_amt,
  round(AVG(a.temp_grant_amount/1000.0 - c.c010_amt),2) AS avg_diff
FROM app a
LEFT JOIN c010 c ON cast(a.biz_id as varchar) = c.external_id
GROUP BY 1, 2
ORDER BY 1, 2
""", "X2 在线临额: funnel字段 vs C010事件 数量/金额对账(9-10月放款)")

# ============================================================
# X3: 每笔放款三金额字段 - offline_grant / online_grant / temp_used
# ============================================================
q("""
WITH off_grant AS (   -- 申请时点最近一笔离线发放(7天内)
  SELECT mid, app_time, off_amt, off_event FROM (
    SELECT cast(a.mid as bigint) AS mid, a.app_time,
           g.change_total_grantamount AS off_amt, g.change_event_type AS off_event,
           row_number() OVER (PARTITION BY cast(a.mid as bigint), a.app_time ORDER BY g.create_time DESC) rn
    FROM mx.wxs_application_funnel a
    JOIN ods_view_presto.s05_user_creditlimit_change_record g
      ON cast(a.mid as bigint)=cast(g.mid as bigint)
     AND g.change_event_type IN ('C015','C013')
     AND g.create_time <= a.app_time
     AND a.app_time < g.create_time + interval '7' day
    WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
      AND a.app_date >= date'2026-09-01' AND a.app_date < date'2026-10-16'
  ) t WHERE rn=1
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
    WHEN o.off_amt IS NOT NULL AND a.temp_grant_amount > 0 THEN '3_混合'
    WHEN o.off_amt IS NOT NULL THEN '1_仅离线发放'
    WHEN a.temp_grant_amount > 0 THEN '2_仅在线发放'
    ELSE '4_无临额'
  END AS grp,
  COUNT(*) AS loan_cnt,
  round(AVG(a.contract_amount),0) AS avg_contract,
  round(AVG(COALESCE(o.off_amt,0)),0) AS avg_offline_grant,
  round(AVG(a.temp_grant_amount/1000.0),0) AS avg_online_grant_peso,
  round(AVG(COALESCE(f.temp_used,0)),0) AS avg_temp_used,
  round(100.0*SUM(CASE WHEN COALESCE(f.temp_used,0)>0 THEN 1 ELSE 0 END)/COUNT(*),2) AS pct_actually_used
FROM mx.wxs_application_funnel a
LEFT JOIN off_grant o ON cast(a.mid as bigint)=o.mid AND a.app_time=o.app_time
LEFT JOIN freeze f ON cast(a.biz_id as bigint)=f.biz_id
WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
  AND a.app_date >= date'2026-09-01' AND a.app_date < date'2026-10-16'
GROUP BY 1
ORDER BY 1
""", "X3 每笔放款: 离线发放额/在线发放额/实际使用额 三字段(9-10月)")

print("DONE-XVALIDATE")
