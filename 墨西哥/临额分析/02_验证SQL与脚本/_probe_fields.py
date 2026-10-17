# -*- coding: utf-8 -*-
"""找 funnel 合同额字段 + 取两笔合同额/主额占用"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 2000); pd.set_option('display.max_rows', 500)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 150); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception as ex:
            print(f"[err] {str(ex)[:150]}"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

q("""
select column_name, data_type
from information_schema.columns
where table_schema='mx' and table_name='wxs_application_funnel'
  and (lower(column_name) like '%amount%' or lower(column_name) like '%contract%'
       or lower(column_name) like '%credit%' or lower(column_name) like '%limit%'
       or lower(column_name) like '%loan%' or lower(column_name) like '%issue%')
order by column_name
""", "A. funnel 候选列")

q("""
select biz_id, mid, app_time, apply_time, release_time,
       contract_amount, issue_amount, temp_grant_amount, grantcredit_amount
from mx.wxs_application_funnel
where tenant='yawey' and cast(biz_id as varchar) in ('1620000463039322','1620000464027012')
""", "B. funnel 金额列")

print("DONE-PROBE")
