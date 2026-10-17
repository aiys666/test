# -*- coding: utf-8 -*-
"""验证修复: 过滤issue_tag=1后, 单笔应为空; 并量化影响面"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 1400)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 120); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception:
            time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

BIZ = '1620000482922458'

# 1) 修复后单笔: issue_time 应为空
q(f"""
WITH app AS (SELECT cast(biz_id as varchar) AS biz_id, mid FROM mx.wxs_application_funnel
             WHERE tenant='yawey' AND cast(biz_id as varchar)='{BIZ}'),
iss AS (
  SELECT biz_id, MIN(createtime) AS issue_time
  FROM ods.s21_risk_model_record
  WHERE modelmainid=1386 AND strategytype='CHAMPION'
    AND outputdata LIKE '%"temp_credit_amount_issue_tag":1%'
  GROUP BY biz_id
)
SELECT a.biz_id, s.issue_time AS "修复后_在线发放时间"
FROM app a LEFT JOIN iss s ON cast(a.biz_id as bigint)=s.biz_id
""", "1) 修复后单笔(应显示空)")

# 2) 对照: 另一笔 issue_tag=1 的样例应有值
q("""
SELECT biz_id, createtime, outputdata
FROM ods.s21_risk_model_record
WHERE modelmainid=1386 AND strategytype='CHAMPION'
  AND biz_id IN (1620000482922458, 1620000462179690)
ORDER BY biz_id
""", "2) 对照两笔的 issue_tag 原始值")

# 3) 影响面: 窗口内 有1386决策 但 tag=0(未发放) 且 无C010 的笔数
q("""
WITH app AS (
  SELECT cast(biz_id as varchar) AS biz_id
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
m_any AS (
  SELECT DISTINCT biz_id FROM ods.s21_risk_model_record
  WHERE modelmainid=1386 AND strategytype='CHAMPION'
),
m_t1 AS (
  SELECT DISTINCT biz_id FROM ods.s21_risk_model_record
  WHERE modelmainid=1386 AND strategytype='CHAMPION'
    AND outputdata LIKE '%"temp_credit_amount_issue_tag":1%'
),
c010 AS (
  SELECT DISTINCT cast(external_id as bigint) AS biz_id
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE limit_type='TEMP' AND change_event_type='C010'
)
SELECT
  COUNT(*) AS total,
  SUM(CASE WHEN a1.biz_id IS NOT NULL THEN 1 ELSE 0 END) AS has_1386_any,
  SUM(CASE WHEN t1.biz_id IS NOT NULL THEN 1 ELSE 0 END) AS has_1386_tag1,
  SUM(CASE WHEN c.biz_id IS NOT NULL THEN 1 ELSE 0 END) AS has_c010,
  SUM(CASE WHEN a1.biz_id IS NOT NULL AND t1.biz_id IS NULL THEN 1 ELSE 0 END) AS tag0_any_notissued
FROM app a
LEFT JOIN m_any a1 ON cast(a.biz_id as bigint)=a1.biz_id
LEFT JOIN m_t1 t1 ON cast(a.biz_id as bigint)=t1.biz_id
LEFT JOIN c010 c ON cast(a.biz_id as bigint)=c.biz_id
""", "3) 影响面: 1386跑过但tag=0 的笔数")

print("DONE-FIX")
