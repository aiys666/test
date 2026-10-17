# -*- coding: utf-8 -*-
"""none组深查 Q0字段排查 + Q1 四组×7周×评级"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 420)

def q(sql, tag="", show=300, retry=6):
    print("="*130); print(tag)
    for i in range(retry):
        try:
            r = pq.query(sql)
        except Exception as e:
            print(f"[conn retry {i+1}] {type(e).__name__}"); time.sleep(8)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r)==0: print("[空]"); return None
            print(r.to_string() if len(r)<=show else r.head(show).to_string())
            print(f"[rows={len(r)}]"); return r
        print(f"[sql retry {i+1}] {r[:200]}"); time.sleep(8)
        try: pq.login()
        except Exception: pass
    return None

# Q0: yj表 复贷深度/逾期历史/终损相关字段
q("""
select column_name from information_schema.columns
where table_schema='mx' and table_name='yj_test_table_250225'
  and (column_name like '%finish%' or column_name like '%loan_num%' or column_name like '%loan_cnt%'
    or column_name like '%cycle%' or column_name like '%num%' or column_name like '%cnt%'
    or column_name like '%fpd%' or column_name like '%write%' or column_name like '%loss%'
    or column_name like '%expire%' or column_name like '%reloan%' or column_name like '%order%'
    or column_name like '%hist%' or column_name like '%his_%')
order by 1
""", "Q0 yj表 复贷深度/历史/终损字段")
