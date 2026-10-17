# -*- coding: utf-8 -*-
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.width', 2000)
for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)
def q(sql, tag):
    print("=" * 140); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception as ex:
            print(f"[err] {str(ex)[:200]}"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

q("""
select cast(u.biz_id as varchar) as biz_id, u.change_action, u.limit_type, u.risk_credit_limit, u.create_time
from ods.s05_user_creditlimit_used_detail u
where cast(u.biz_id as varchar) in ('1620000482922458','1620000463039322')
order by u.biz_id, u.create_time
""", "used_detail 直接查 biz 1620000482922458 / 1620000463039322")

q("""
select cast(biz_id as varchar) as biz_id, mid, app_time, apply_time, release_time, is_reloan, if_issue, contract_amount, temp_grant_amount
from mx.wxs_application_funnel
where tenant='yawey' and cast(biz_id as varchar)='1620000482922458'
""", "funnel 1620000482922458")
print("DONE-CHK")
