# -*- coding: utf-8 -*-
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 400)

def q(sql, tag):
    print("=" * 90); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception as e:
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

# 案例用户 TEMP 事件(在线C010 / 离线C013,C015)
q("""
select id, change_event_type as evt, limit_type, change_action,
  round(change_total_grantamount,1) as total_grant, round(change_used_grantamount,1) as used_grant,
  create_time, expiring_time, limit_main_id
from ods_view_presto.s05_user_creditlimit_change_record
where mid=1040160040722566 and limit_type='TEMP' order by create_time
""", "Q3b 案例用户 TEMP 事件明细")

# 案例用户各笔放款: 主额冻结/临额使用/授信
q("""
select app_date, biz_id, if_issue, if_in_sx,
  temp_credit_amount_issue_tag as on_tag, round(temp_grant_amount/1000.0,1) as temp_use,
  round(risk_credit_limit/1000.0,1) as main_freeze, round(credit_amount/1000.0,1) as credit, round(contract_amount,1) as contract
from mx.yj_test_table_250225
where mid=1040160040722566 order by app_date, biz_id
""", "Q7 案例用户各笔放款(主额/临额/授信)")

print("DONE2")
