# -*- coding: utf-8 -*-
"""确认逾期字段口径, 然后计算笔数逾期率/金额逾期率, 拆临额影响"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 620)

def q(sql, tag):
    print("=" * 116); print(tag, flush=True)
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

# 1. 确认逾期字段 (1T0/2T0/3T0/4T7/TR 对应哪些列)
q("""
SELECT column_name
FROM information_schema.columns
WHERE table_schema='mx' AND table_name='report_application_funnel7'
  AND (column_name LIKE '%overdue%' OR column_name LIKE '%should_amt%'
       OR column_name LIKE '%loan_bal%' OR column_name LIKE '%t0%' OR column_name LIKE '%t7%'
       OR column_name LIKE '%t30%' OR column_name LIKE '%tr%')
  AND column_name NOT LIKE '%is_t%'
ORDER BY column_name
""", "T1 funnel7 逾期相关字段(排除is标记)")

# 2. 确认有多少期 (_1到_4)
q("""
SELECT column_name
FROM information_schema.columns
WHERE table_schema='mx' AND table_name='report_application_funnel7'
  AND column_name LIKE '%overdue_amount%'
ORDER BY column_name
""", "T2 全部overdue_amount字段")

print("DONE-CHECK")
