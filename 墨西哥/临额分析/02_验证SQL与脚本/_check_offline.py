# -*- coding: utf-8 -*-
"""离线临额效果分析: 基于 mx.yuhan_temp_limit_base_table_his_20260924 + wxs_application_funnel"""
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

# 1. 离线临额表结构
q("""
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema='mx' AND table_name='yuhan_temp_limit_base_table_his_20260924'
ORDER BY column_name
""", "T1 离线临额表结构")

# 2. 各批次离线临额的 temp_limit_tag 分布
q("""
SELECT data_date,
       COUNT(*) AS cnt,
       COUNT(DISTINCT mid) AS mid_cnt,
       SUM(CASE WHEN temp_limit_tag IS NOT NULL AND temp_limit_tag != '' THEN 1 ELSE 0 END) AS has_temp_tag_cnt
FROM mx.yuhan_temp_limit_base_table_his_20260924
WHERE data_date IN ('20260819','20260820','20260826','20260827','20260902','20260903','20260909','20260910')
GROUP BY data_date
ORDER BY data_date
""", "T2 各批次离线临额tag分布")

# 3. temp_limit_tag 的取值
q("""
SELECT data_date, temp_limit_tag, COUNT(*) AS cnt
FROM mx.yuhan_temp_limit_base_table_his_20260924
WHERE data_date IN ('20260819','20260820','20260826','20260827','20260902','20260903','20260909','20260910')
GROUP BY data_date, temp_limit_tag
ORDER BY data_date, temp_limit_tag
""", "T3 temp_limit_tag取值")

print("DONE-CHECK")
