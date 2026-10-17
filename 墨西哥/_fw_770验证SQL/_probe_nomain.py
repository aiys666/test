# -*- coding: utf-8 -*-
"""下钻 biz 1620000482769098: 放款450但无MAIN/TEMP冻结、无1067/评级
Q1 funnel全字段  Q2 本biz全部s21节点  Q3 同mid跨biz节点  Q4 used_detail+change_record"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 4200)
pd.set_option('display.max_colwidth', 10000); pd.set_option('display.max_rows', 400)
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

BIZ = "1620000482769098"

# Q0 funnel 列名中含 main/grant/loan/credit/amount/quota 的
q("show columns from mx.wxs_application_funnel", "Q0 funnel全部列(本地过滤)")

# Q1 funnel 额度/金额相关列
q(f"""
select biz_id, mid, app_time, apply_time, release_time, contract_amount, temp_grant_amount
from mx.wxs_application_funnel
where tenant='yawey' and cast(biz_id as varchar)='{BIZ}'
""", "Q1 funnel关键列")

# Q2 本 biz 全部 CHAMPION 节点
q(f"""
select createtime, modelmainid, substr(cast(outputdata as varchar),1,300) od
from ods.s21_risk_model_record
where biz_id={BIZ} and strategytype='CHAMPION'
order by createtime
""", "Q2 本biz全部CHAMPION节点")

# Q3 同 mid 在 10-15 ~ 10-16 的全部节点(看1067/评级是否挂在别的biz上)
q(f"""
select biz_id, createtime, modelmainid, substr(cast(outputdata as varchar),1,200) od
from ods.s21_risk_model_record
where mid=(select cast(mid as varchar) from mx.wxs_application_funnel
           where tenant='yawey' and cast(biz_id as varchar)='{BIZ}')
  and createtime >= timestamp '2026-10-15 00:00' and createtime < timestamp '2026-10-16 06:00'
  and modelmainid in (1067,1500,1542,1635,1522,1523,1386,1379,857,661)
order by createtime
""", "Q3 同mid跨biz的关键节点(10/15-10/16)")

# Q4 used_detail 本biz + change_record MAIN
q(f"""
select 'used_detail' src, cast(biz_id as varchar) biz, limit_type, change_action,
       create_time, risk_credit_limit amt, null etype
from ods.s05_user_creditlimit_used_detail
where biz_id={BIZ}
union all
select 'change_rec', external_id, limit_type, change_action, create_time,
       change_total_grantamount, change_event_type
from ods_view_presto.s05_user_creditlimit_change_record
where mid=(select cast(mid as varchar) from mx.wxs_application_funnel
           where tenant='yawey' and cast(biz_id as varchar)='{BIZ}')
  and create_time >= timestamp '2026-10-15 00:00' and create_time < timestamp '2026-10-16 06:00'
order by create_time
""", "Q4 used_detail本biz + change_record同mid(MAIN+TEMP)")
print("DONE-NOMAIN")
