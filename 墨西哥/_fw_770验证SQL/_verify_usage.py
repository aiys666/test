# -*- coding: utf-8 -*-
"""校验每笔放款实际使用的临额金额
V1 C003(FREEZE_LIMIT)事件能否关联到放款(通过external_id=biz_id?)
V2 一笔放款的C003是否拆分为MAIN+TEMP两条, 各自金额是多少
V3 核对: 用例mid, 看其放款合同额 vs MAIN冻结+TEMP冻结 是否相等
V4 funnel侧 temp_grant_amount(发放) vs change_used_grantamount(使用)
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

# V1: C003事件结构 - external_id是否=biz_id, limit_type分布
q("""
SELECT change_event_type, change_action, limit_type,
       COUNT(*) AS cnt,
       round(AVG(risk_credit_limit),2) AS avg_freeze_amt,
       SUM(CASE WHEN external_id IS NULL OR external_id='' THEN 1 ELSE 0 END) AS null_ext
FROM ods.s05_user_creditlimit_used_detail
WHERE change_event_type IN ('C003','C004','C008')
  AND create_time >= timestamp'2026-09-01 00:00:00'
GROUP BY change_event_type, change_action, limit_type
ORDER BY change_event_type, change_action, limit_type
""", "V1 C003/C004/C008按limit_type分布")

# V2: 取一个有临额的放款, 看其C003事件明细(MID已知: 1040160037579250在1014拿了250临额)
# 先找他的放款, 再看C003
q("""
WITH app AS (
  SELECT mid, app_time, app_date, if_issue, contract_amount, temp_grant_amount,
         change_used_grantamount, biz_id
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND mid = '1040160037579250'
    AND app_date >= date'2026-10-14' AND app_date < date'2026-10-16'
)
SELECT * FROM app ORDER BY app_time
""", "V2a 样例用户1040160037579250的放款")

q("""
SELECT change_event_type, change_action, limit_type,
       risk_credit_limit, create_time, external_id, biz_id
FROM ods.s05_user_creditlimit_used_detail
WHERE mid = '1040160037579250'
  AND create_time >= timestamp'2026-10-14 00:00:00'
  AND create_time <  timestamp'2026-10-16 00:00:00'
ORDER BY create_time, limit_type
""", "V2b 样例用户的额度占用明细(10/14-10/15)")

# V3: funnel里temp_grant_amount和change_used_grantamount的关系(有在线临额的放款)
q("""
SELECT
  COUNT(*) AS issue_with_online_temp,
  round(AVG(temp_grant_amount/1000.0),2) AS avg_online_temp_grant_peso,
  round(AVG(change_used_grantamount/1000.0),2) AS avg_change_used_peso,
  round(AVG(contract_amount),2) AS avg_contract,
  -- 在线临额发放额 vs 已使用
  SUM(CASE WHEN change_used_grantamount > 0 THEN 1 ELSE 0 END) AS used_cnt,
  round(100.0*SUM(CASE WHEN change_used_grantamount > 0 THEN 1 ELSE 0 END)/COUNT(*),2) AS used_pct
FROM mx.wxs_application_funnel
WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
  AND temp_grant_amount > 0
  AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
""", "V3 在线临额: 发放(temp_grant_amount) vs 已使用(change_used_grantamount)")

print("DONE-VERIFY-USAGE")
