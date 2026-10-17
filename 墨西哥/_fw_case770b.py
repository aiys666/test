# -*- coding: utf-8 -*-
"""锁定 770.4 的占用来源: 修正 used_detail 查询(无 change_desc) + TEMP 全事件 trail"""
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
        print(f"[retry {i+1}] {str(r)[:200]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}\n"); return None

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: print("[login retry]"); time.sleep(8)

# A used_detail: 该 mid 全部记录(2026-02起), 重点 TEMP
q(f"""
select id, biz_id, limit_type, change_action, round(risk_credit_limit,1) as risk_credit_limit,
  create_time, update_time
from ods.s05_user_creditlimit_used_detail
where mid={MID} and create_time >= date'2026-02-01' and create_time < date'2026-10-12'
order by create_time
""", "A used_detail 全部(mid, 2026-02起) 看 TEMP 占用")

# B K表: 该 mid 全部 TEMP 事件 + used_grant(全历史), 找 770.4 首次出现
q(f"""
select limit_main_id, create_time, change_event_type as evt, change_action,
  round(change_total_grantamount,1) as total_grant, round(change_used_grantamount,1) as used_grant,
  expiring_time
from ods_view_presto.s05_user_creditlimit_change_record
where mid={MID} and limit_type='TEMP'
order by create_time
""", "B TEMP 全事件(含 used_grant) 找 770.4 起点")

# C 3/03 那笔(biz=1620000392574325) 的额度占用记录
q("""
select id, biz_id, limit_type, change_action, round(risk_credit_limit,1) as risk_credit_limit,
  create_time, update_time
from ods.s05_user_creditlimit_used_detail
where biz_id=1620000392574325
order by create_time
""", "C 3/03那笔(biz ...392574325)的 used_detail")

# D 案例用户8月那笔(8/29 biz)的 used_detail, 看 MAIN/TEMP 冻结
q("""
select id, biz_id, limit_type, change_action, round(risk_credit_limit,1) as risk_credit_limit,
  create_time, update_time
from ods.s05_user_creditlimit_used_detail
where biz_id in (1620000460693942, 1620000465739710, 1620000474884411)
order by create_time
""", "D 8/29、9/10、10/01 三笔的 used_detail(MAIN+TEMP)")

print("DONE-770B")
