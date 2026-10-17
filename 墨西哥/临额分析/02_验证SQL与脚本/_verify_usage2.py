# -*- coding: utf-8 -*-
"""校验每笔放款实际使用的临额金额(通过C003 FREEZE_LIMIT按limit_type拆分)
   关联: used_detail.biz_id = funnel.biz_id
   V1 一笔放款是否拆MAIN+TEMP两条, 金额之和是否=合同额
   V2 整体核对: 放款样本中, temp_used_amt分布
   V3 在线临额: C010事件的change_used_grantamount vs funnel.temp_grant_amount
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

# V1: 单笔核对 - 取1014批次有在贷用户的一笔放款, 看used_detail
q("""
WITH app AS (
  SELECT mid, biz_id, app_time, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date = date'2026-10-14'
    AND temp_grant_amount = 0  -- 纯离线场景(无在线临额)
  LIMIT 20
)
SELECT a.mid, a.biz_id, a.contract_amount, a.temp_grant_amount,
       u.limit_type, u.risk_credit_limit AS freeze_amt, u.create_time AS freeze_time
FROM app a
LEFT JOIN ods.s05_user_creditlimit_used_detail u
  ON a.biz_id = u.biz_id AND u.change_action='FREEZE_LIMIT'
ORDER BY a.biz_id, u.limit_type
""", "V1 纯离线放款的MAIN/TEMP冻结明细(10/14,20笔)")

# V2: 整体核对 - 9-10月放款, 按实际TEMP使用量分桶
q("""
WITH app AS (
  SELECT mid, biz_id, app_time, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
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
    WHEN f.temp_used = 0 THEN '0_未用临额'
    WHEN f.temp_used <= 500 THEN '1_临额<=500'
    WHEN f.temp_used <= 1000 THEN '2_500~1k'
    WHEN f.temp_used <= 2000 THEN '3_1k~2k'
    ELSE '4_>2k'
  END AS temp_used_bucket,
  COUNT(*) AS issue_cnt,
  round(AVG(a.contract_amount),0) AS avg_contract,
  round(AVG(f.main_used),0) AS avg_main_used,
  round(AVG(f.temp_used),0) AS avg_temp_used,
  -- 核对: main+temp 是否=合同额
  round(AVG(a.contract_amount - f.main_used - f.temp_used),2) AS diff_contract_vs_used,
  round(100.0*SUM(CASE WHEN ABS(a.contract_amount - f.main_used - f.temp_used) < 1 THEN 1 ELSE 0 END)/COUNT(*),2) AS exact_match_pct
FROM app a
JOIN freeze f ON a.biz_id = f.biz_id
GROUP BY 1
ORDER BY 1
""", "V2 9-10月放款: 实际临额使用量分布+核对main+temp=contract")

# V3: 在线临额发放vs使用 - 从C010事件的change_used_grantamount
q("""
SELECT
  COUNT(*) AS c010_cnt,
  round(AVG(change_total_grantamount),2) AS avg_online_grant,
  round(AVG(change_used_grantamount),2) AS avg_online_used,
  round(AVG(change_total_grantamount - change_used_grantamount),2) AS avg_unused,
  SUM(CASE WHEN change_used_grantamount > 0 THEN 1 ELSE 0 END) AS used_cnt,
  round(100.0*SUM(CASE WHEN change_used_grantamount > 0 THEN 1 ELSE 0 END)/COUNT(*),2) AS used_pct,
  round(AVG(CASE WHEN change_used_grantamount > 0 THEN change_used_grantamount END),2) AS avg_used_when_used
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE change_event_type='C010'
  AND create_time >= timestamp'2026-09-01 00:00:00'
""", "V3 在线临额C010: 发放(change_total) vs 已使用(change_used)")

print("DONE-USAGE-VERIFY")
