# -*- coding: utf-8 -*-
"""确认 v3_flag / v3_flag_huidu 实际取值"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 600)

def q(sql, tag="", show=300):
    print("="*140); print(tag)
    for a in range(1, 6):
        try:
            r = pq.query(sql); break
        except Exception as e:
            print(f"[retry {a}] {type(e).__name__}: {str(e)[:150]}")
            if a == 5: raise
            time.sleep(4 * a)
    if isinstance(r, str): print("[ERR]", r[:1500]); return None
    if r is None or len(r) == 0: print("[空]"); return None
    print(r.to_string() if len(r) <= show else r.head(show).to_string())
    print(f"[rows={len(r)}]"); return r

q("""
select v3_flag, count(*) cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1 order by 2 desc
""", "T0 v3_flag 取值分布")

q("""
select v3_flag_huidu, count(*) cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1 order by 2 desc
""", "T0b v3_flag_huidu 取值分布")
