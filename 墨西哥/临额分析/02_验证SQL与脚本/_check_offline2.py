# -*- coding: utf-8 -*-
"""离线临额效果分析: 实验组vs对照组 放款率/额度使用率/逾期率"""
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

# 1. tagg字段取值 + 临额发放金额统计
q("""
SELECT data_date, tagg,
       COUNT(*) AS cnt,
       round(AVG(temp_limit_issue_amount),2) AS avg_issue_amt,
       round(SUM(CASE WHEN temp_limit_issue_amount > 0 THEN 1 ELSE 0 END),0) AS has_issue_cnt
FROM mx.yuhan_temp_limit_base_table_his_20260924
WHERE data_date IN ('20260819','20260820','20260826','20260827','20260902','20260903','20260909','20260910')
GROUP BY data_date, tagg
ORDER BY data_date, tagg
""", "T1 tagg字段 + 临额发放金额")

# 2. 各批次的临额发放金额分布(按temp_limit_tag)
q("""
SELECT data_date, temp_limit_tag,
       COUNT(*) AS cnt,
       round(AVG(temp_limit_issue_amount),2) AS avg_issue_amt,
       round(AVG(curr_temp_credit_limit),2) AS avg_curr_temp_limit,
       round(AVG(curr_main_credit_limit),2) AS avg_main_limit,
       round(AVG(onloan_bal),2) AS avg_onloan_bal,
       round(AVG(onloan_cnt),2) AS avg_onloan_cnt
FROM mx.yuhan_temp_limit_base_table_his_20260924
WHERE data_date IN ('20260819','20260820','20260826','20260827','20260902','20260903','20260909','20260910')
GROUP BY data_date, temp_limit_tag
ORDER BY data_date, temp_limit_tag
""", "T2 各实验组临额发放金额+主额+在贷")

print("DONE-CHECK2")
