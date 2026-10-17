# -*- coding: utf-8 -*-
"""核实 biz 1620000463039322 / 1620000464027012 全链路 + 找 funnel 合同额/主额占用字段"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 2000); pd.set_option('display.max_rows', 300)

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

BIZ = "'1620000463039322','1620000464027012'"

# A. funnel 候选金额/额度列
q("""
select column_name
from mx.information_schema.columns
where table_schema='mx' and table_name='wxs_application_funnel'
  and (lower(column_name) like '%amount%' or lower(column_name) like '%contract%'
       or lower(column_name) like '%credit%' or lower(column_name) like '%limit%'
       or lower(column_name) like '%loan%')
order by column_name
""", "A. funnel 金额/额度候选列")

# B. funnel 行
q(f"""
select biz_id, mid, app_time, apply_time, release_time,
       temp_grant_amount, issue_amount, grantcredit_amount,
       credit_amount, contract_amount
from mx.wxs_application_funnel
where tenant='yawey' and cast(biz_id as varchar) in ({BIZ})
""", "B. funnel 行")

# C. change_record 全部 TEMP 事件(按 mid)
q(f"""
select cast(f.biz_id as varchar) as biz_id, e.change_event_type, e.change_action,
       e.change_total_grantamount, e.change_used_grantamount, e.create_time, e.expiring_time,
       e.change_desc
from mx.wxs_application_funnel f
join ods_view_presto.s05_user_creditlimit_change_record e
  on cast(f.mid as bigint)=cast(e.mid as bigint)
where f.tenant='yawey' and cast(f.biz_id as varchar) in ({BIZ})
  and e.limit_type='TEMP'
order by f.biz_id, e.create_time
""", "C. change_record TEMP 事件")

# D. used_detail MAIN + TEMP
q(f"""
select cast(u.biz_id as varchar) as biz_id, u.change_action, u.limit_type,
       u.risk_credit_limit, u.create_time
from ods.s05_user_creditlimit_used_detail u
where cast(u.biz_id as varchar) in ({BIZ})
order by u.biz_id, u.create_time
""", "D. used_detail MAIN+TEMP")

# E. model1386
q(f"""
select biz_id, createtime, outputdata
from ods.s21_risk_model_record
where modelmainid=1386 and strategytype='CHAMPION' and cast(biz_id as varchar) in ({BIZ})
""", "E. model1386 决策")

print("DONE-DRILL2")
