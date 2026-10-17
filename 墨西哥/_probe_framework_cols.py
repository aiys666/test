# -*- coding: utf-8 -*-
"""框架取数前字段探查"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

for _i in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception:
        time.sleep(12)
pd.set_option('display.max_columns', None); pd.set_option('display.width', 460)

def q(sql, tag="", retry=8):
    print("="*120); print(tag)
    for i in range(retry):
        try:
            r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(10)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r)==0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]"); return r
        print(f"[retry {i+1}] {r[:150]}"); time.sleep(10)
        try: pq.login()
        except Exception: pass
    return None

# 1. yj表 息费/终损字段
q("""
select column_name from information_schema.columns
where table_schema='mx' and table_name='yj_test_table_250225'
  and (column_name like '%interest%' or column_name like '%t7_%' or column_name like '%t14_%'
    or column_name like '%t30_%' or column_name like '%t3_%' or column_name like '%should%'
    or column_name like '%overdue%' or column_name like '%write%')
order by 1
""", "1. yj表 息费/终损字段")

# 2. funnel表 息费/t30
q("""
select column_name from information_schema.columns
where table_schema='mx' and table_name='wxs_application_funnel'
  and (column_name like '%interest%' or column_name like '%t30_%' or column_name like '%t14_%'
    or column_name like '%write%' or column_name like '%loss%')
order by 1
""", "2. funnel表 息费/终损字段")

# 3. 离线底表字段
q("""
select column_name, data_type from information_schema.columns
where table_schema='mx' and table_name='yuhan_temp_limit_base_table_his_20260924'
order by ordinal_position
""", "3. 离线临额底表字段")
