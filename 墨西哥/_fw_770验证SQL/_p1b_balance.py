# -*- coding: utf-8 -*-
"""Phase1b: A3修正(平衡性检验) + A4(分臂覆盖率验证: 减息组应无C015)"""
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

# A4: 分实验臂覆盖率 - 验证"减息组无C015"假设
q(f"""
WITH {GRANTS},
offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         date_trunc('day', load_time) AS base_dt
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260923','20260924','20260930','20261001','20261007','20261008','20261014','20261015')
)
SELECT
  o.data_date, o.temp_limit_tag,
  COUNT(DISTINCT o.mid) AS cnt,
  COUNT(DISTINCT CASE WHEN g.mid IS NOT NULL THEN o.mid END) AS matched,
  round(100.0*COUNT(DISTINCT CASE WHEN g.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),1) AS cover_pct,
  round(AVG(g.grant_amt),0) AS avg_grant_amt
FROM offline o
LEFT JOIN grants g ON cast(o.mid as bigint)=cast(g.mid as bigint)
  AND g.grant_time >= o.base_dt AND g.grant_time < date_add('day',2,o.base_dt)
GROUP BY o.data_date, o.temp_limit_tag
ORDER BY o.data_date, o.temp_limit_tag
""", "A4 分实验臂C015/C013覆盖率(减息组应≈0)")

# A3修正: 平衡性检验
q("""
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         curr_main_credit_limit, onloan_bal,
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
""", "A3修正 有在贷批次各臂发放前7天申请率+主额+在贷余额")

print("DONE-PHASE1B")
