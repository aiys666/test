# -*- coding: utf-8 -*-
"""查 1386 落表字段 + 本笔落表内容(找在线临额发放金额来源)"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 2400)
for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)
def q(sql, tag):
    print("=" * 150); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception as ex:
            print(f"[err] {str(ex)[:180]}"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

q("""
select column_name, data_type from information_schema.columns
where table_schema='mx' and table_name='tmp_darren_temp_limit_table' order by column_name
""", "tmp_darren_temp_limit_table 字段")

q("""
select * from mx.tmp_darren_temp_limit_table
where cast(biz_id as varchar)='1620000466574256'
""", "本笔 1386 落表内容")

q("""
select column_name, data_type from information_schema.columns
where table_name='s21_risk_model_record'
  and (lower(column_name) like '%amount%' or lower(column_name) like '%input%' or lower(column_name) like '%output%')
order by column_name
""", "s21_risk_model_record 候选列")
print("DONE-P1386")
