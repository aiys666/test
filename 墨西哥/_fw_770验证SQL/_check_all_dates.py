# -*- coding: utf-8 -*-
"""重新仔细审视 yuhan_temp_limit_base_table_his_20260924 表
   1. 所有 data_date 有哪些
   2. 每个日期的数据量、temp_limit_tag 分布
   3. 确认截止今天(2026-10-15)所有发临额批次
"""
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

# T1: 所有 data_date 及数据量
q("""
SELECT data_date,
       COUNT(*) AS cnt,
       COUNT(DISTINCT mid) AS mid_cnt,
       COUNT(DISTINCT temp_limit_tag) AS tag_cnt,
       SUM(CASE WHEN temp_limit_issue_amount > 0 THEN 1 ELSE 0 END) AS issue_cnt,
       round(AVG(temp_limit_issue_amount),0) AS avg_issue_amt
FROM mx.yuhan_temp_limit_base_table_his_20260924
GROUP BY data_date
ORDER BY data_date
""", "T1 所有data_date分布")

# T2: 每个data_date的temp_limit_tag分布
q("""
SELECT data_date, temp_limit_tag,
       COUNT(*) AS cnt,
       round(AVG(temp_limit_issue_amount),0) AS avg_amt,
       round(AVG(curr_temp_credit_limit),0) AS avg_curr_temp,
       round(AVG(curr_main_credit_limit),0) AS avg_main
FROM mx.yuhan_temp_limit_base_table_his_20260924
GROUP BY data_date, temp_limit_tag
ORDER BY data_date, temp_limit_tag
""", "T2 所有data_date x temp_limit_tag")

# T3: 每个data_date的tagg分布
q("""
SELECT data_date, tagg, COUNT(*) AS cnt
FROM mx.yuhan_temp_limit_base_table_his_20260924
GROUP BY data_date, tagg
ORDER BY data_date, tagg
""", "T3 所有data_date x tagg")

# T4: 表中有哪些字段能标记"发临额的日期" vs "观察日期"
#     比如 temp_limit_issue_date 是发放时间吗？
q("""
SELECT data_date,
       MIN(temp_limit_issue_date) AS min_issue_dt,
       MAX(temp_limit_issue_date) AS max_issue_dt,
       MIN(load_time) AS min_load,
       MAX(load_time) AS max_load
FROM mx.yuhan_temp_limit_base_table_his_20260924
WHERE temp_limit_issue_date IS NOT NULL
GROUP BY data_date
ORDER BY data_date
""", "T4 temp_limit_issue_date vs load_time vs data_date")

print("DONE-CHECK-ALL")
