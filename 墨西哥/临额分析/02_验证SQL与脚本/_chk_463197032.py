# -*- coding: utf-8 -*-
"""核查 biz 1620000463197032: 有1386发放时间、无发放金额 —— 是否为"弹窗已发但客户未领取"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 2600)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 170); print(tag, flush=True)
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

BIZ = "'1620000463197032'"

# Q1 1386 决策原文(outputdata)
q(f"""
select cast(biz_id as varchar) as biz_id, createtime, outputdata
from ods.s21_risk_model_record
where modelmainid=1386 and strategytype='CHAMPION' and cast(biz_id as varchar) in ({BIZ})
""", "Q1 1386决策原文(看tag=?)")

# Q2 本笔mid的全部TEMP事件(该窗口内)
q(f"""
select e.change_event_type, e.change_action, e.external_id, e.change_total_grantamount,
       e.change_used_grantamount, e.create_time, e.expiring_time,
       substr(cast(e.change_desc as varchar),1,44) as descr
from ods_view_presto.s05_user_creditlimit_change_record e
where e.limit_type='TEMP'
  and cast(e.mid as bigint) in (select cast(mid as bigint) from mx.wxs_application_funnel where cast(biz_id as varchar) in ({BIZ}))
  and e.create_time between timestamp '2026-09-01' and timestamp '2026-09-15'
order by e.create_time
""", "Q2 该mid的TEMP事件(9/1-9/15)")

# Q3 本笔funnel + used_detail冻结明细
q(f"""
select cast(biz_id as varchar) as biz_id, mid, temp_grant_amount/1000.0 as temp_used,
       contract_amount, use_main_credit_amount/1000.0 as main_use_amt
from mx.wxs_application_funnel where cast(biz_id as varchar) in ({BIZ})
""", "Q3 funnel金额字段")

q(f"""
select cast(u.biz_id as varchar) as biz_id, u.limit_type, u.change_action, u.risk_credit_limit, u.create_time
from ods.s05_user_creditlimit_used_detail u
where cast(u.biz_id as varchar) in ({BIZ})
order by u.create_time
""", "Q4 used_detail本笔冻结明细")

print("DONE-CHECK163")
