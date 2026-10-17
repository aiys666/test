# -*- coding: utf-8 -*-
"""确认 wxs_application_funnel 字段"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 620)

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

q("""
SELECT column_name
FROM information_schema.columns
WHERE table_schema='mx' AND table_name='wxs_application_funnel'
  AND (column_name LIKE '%amount%' OR column_name LIKE '%limit%' OR column_name LIKE '%issue%'
       OR column_name LIKE '%passed%' OR column_name LIKE '%grant%' OR column_name LIKE '%credit%'
       OR column_name LIKE '%available%' OR column_name LIKE '%used%' OR column_name LIKE '%temp%'
       OR column_name LIKE '%contract%' OR column_name LIKE '%risk%')
ORDER BY column_name
""", "T1 wxs_application_funnel 金额相关字段")

print("DONE")
