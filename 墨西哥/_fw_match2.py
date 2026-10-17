# -*- coding: utf-8 -*-
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.width', 400)

def q(sql, tag):
    print("=" * 90); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:160]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}"); return None

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: print("[login retry]"); time.sleep(8)

# 金额核对: C010发放额 vs C003冻结额(实际占用=使用) vs yj使用额
q("""
select
  sum(if(change_event_type='C010',change_total_grantamount,0)) as c010_grant_amt,
  sum(if(change_event_type='C010',change_used_grantamount,0)) as c010_used_field,
  sum(if(change_event_type='C003',change_total_grantamount,0)) as c003_freeze_amt,
  sum(if(change_event_type='C003',change_used_grantamount,0)) as c003_used_field,
  count(if(change_event_type='C010',1,null)) as c010_cnt,
  count(if(change_event_type='C003',1,null)) as c003_cnt
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP' and change_event_type in ('C010','C003')
  and create_time>=date'2026-08-19' and create_time<date'2026-10-06'
""", "金额核对 C010发放 vs C003冻结(TEMP)")

print("DONE-MATCH2")
