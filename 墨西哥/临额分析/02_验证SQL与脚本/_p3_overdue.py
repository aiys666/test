# -*- coding: utf-8 -*-
"""Phase3: 逾期层 - 四分类口径下的资产质量
   E0 确认funnel7逾期字段
   E1 放款样本四分类 x 逾期率(1T0/TR), 限制app<=8月保证账龄
   E2 纯离线组内: 分档看逾期(小额/中额/大额)
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

# E0: funnel7逾期相关字段
q("""
SELECT column_name
FROM information_schema.columns
WHERE table_schema='mx' AND table_name='report_application_funnel7'
  AND (column_name LIKE '%overdue%' OR column_name IN ('mid','app_time','app_date','if_issue','contract_amount','temp_grant_amount'))
ORDER BY column_name
""", "E0 funnel7逾期字段确认")

print("DONE-PHASE3-E0")
