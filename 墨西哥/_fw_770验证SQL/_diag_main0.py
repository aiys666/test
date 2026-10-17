# -*- coding: utf-8 -*-
"""下钻核查: ①在线列出现"过期旧C010"被误挂 ②"无占用主额"到底是延迟还是主额真=0"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 2600); pd.set_option('display.max_rows', 400)

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

BIZ = "'1620000479377160','1620000474757589','1620000483074755'"

# Q1 本笔 funnel 关键字段
q(f"""
select cast(biz_id as varchar) as biz_id, mid, app_time, apply_time, release_time,
       contract_amount, temp_grant_amount/1000.0 as temp_used
from mx.wxs_application_funnel
where cast(biz_id as varchar) in ({BIZ})
""", "Q1 funnel 本笔金额/时刻")

# Q2 used_detail 全部明细(不限 limit_type)
q(f"""
select cast(biz_id as varchar) as biz_id, limit_type, change_action, risk_credit_limit,
       create_time, limit_main_id, expiration_time
from ods.s05_user_creditlimit_used_detail
where cast(biz_id as varchar) in ({BIZ})
order by 1, 5
""", "Q2 used_detail 全部冻结/解冻明细")

# Q3 这三个 mid 的全量 TEMP 事件
q(f"""
select cast(mid as varchar) as mid, change_event_type, change_action, external_id,
       change_total_grantamount, change_used_grantamount, create_time, expiring_time,
       limit_main_id, substr(cast(change_desc as varchar),1,40) as descr
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP'
  and cast(mid as bigint) in (select cast(mid as bigint) from mx.wxs_application_funnel where cast(biz_id as varchar) in ({BIZ}))
order by 1, 7
""", "Q3 三个mid的TEMP事件全量(发放/冻结/解冻)")

# Q4 1386 决策
q(f"""
select cast(biz_id as varchar) as biz_id, createtime,
       substr(cast(outputdata as varchar),1,200) as outdata
from ods.s21_risk_model_record
where modelmainid=1386 and strategytype='CHAMPION' and cast(biz_id as varchar) in ({BIZ})
order by 1, 2
""", "Q4 1386临额发放弹窗决策")

print("DONE-DIAG")
