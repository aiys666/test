# -*- coding: utf-8 -*-
"""追查 mid=1040160040722566 在 2026-10-01 发放临额2800时被占用的770.4来源"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 460)
MID = "1040160040722566"

def q(sql, tag):
    print("=" * 110); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]\n", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:160]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}\n"); return None

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: print("[login retry]"); time.sleep(8)

# Q1 change_record 全字段(含 used_grant / daily_max_available), 2026-08起
q(f"""
select limit_type, limit_main_id, create_time, change_event_type as evt, change_action,
  round(change_total_grantamount,1) as total_grant,
  round(change_used_grantamount,1) as used_grant,
  round(change_daily_max_available_limit,1) as daily_max_avail,
  expiring_time, change_desc
from ods_view_presto.s05_user_creditlimit_change_record
where mid={MID} and create_time >= date'2026-08-01'
order by create_time
""", "Q1 change_record 全字段(2026-08起,重点看 used_grant)")

# Q2 used_detail 全部记录(FREEZE/UNFREEZE, MAIN+TEMP), 2026-08起
q(f"""
select biz_id, limit_type, change_action, round(risk_credit_limit,1) as risk_credit_limit,
  change_desc, create_time, update_time
from ods.s05_user_creditlimit_used_detail
where mid={MID} and create_time >= date'2026-08-01'
order by create_time
""", "Q2 used_detail 明细(占用/释放源)")

# Q3 全表搜 770.4 相关记录(该mid所有历史, 不限limit_type)
q(f"""
select limit_type, limit_main_id, create_time, change_event_type as evt, change_action,
  round(change_total_grantamount,1) as total_grant, round(change_used_grantamount,1) as used_grant,
  expiring_time
from ods_view_presto.s05_user_creditlimit_change_record
where mid={MID}
  and (abs(change_total_grantamount-770.4)<0.6 or abs(change_used_grantamount-770.4)<0.6)
order by create_time
""", "Q3 搜 770.4 来源(K行)")

q(f"""
select biz_id, limit_type, change_action, round(risk_credit_limit,1) as risk_credit_limit,
  create_time
from ods.s05_user_creditlimit_used_detail
where mid={MID} and abs(risk_credit_limit-770.4)<0.6
order by create_time
""", "Q3b 搜 770.4 来源(used_detail)")

print("DONE-770")
