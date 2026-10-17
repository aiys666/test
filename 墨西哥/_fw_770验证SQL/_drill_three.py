# -*- coding: utf-8 -*-
"""核查单笔 biz=1620000462287861 的完整额度事件"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 1500)
pd.set_option('display.max_rows', 300)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 120); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception:
            time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

BIZ = '1620000462287861'

# 1) funnel
q(f"""
SELECT cast(biz_id as varchar) AS biz_id, mid, app_time, apply_time, release_time,
       grantcredit_amount, issue_amount, temp_grant_amount, if_issue, is_reloan, app_date
FROM mx.wxs_application_funnel
WHERE tenant='yawey' AND cast(biz_id as varchar)='{BIZ}'
""", "1) funnel 主档")

# 2) 该mid全部额度变更事件(9月)
q(f"""
SELECT e.external_id, e.change_action, e.change_event_type, e.limit_type,
       ROUND(e.change_total_grantamount,2) AS total_g,
       ROUND(e.change_used_grantamount,2) AS used_g,
       e.create_time, e.expiring_time, e.limit_main_id
FROM ods_view_presto.s05_user_creditlimit_change_record e
WHERE cast(e.mid as bigint) = (
        SELECT mid FROM mx.wxs_application_funnel
        WHERE tenant='yawey' AND cast(biz_id as varchar)='{BIZ}' LIMIT 1)
  AND e.create_time >= timestamp'2026-09-01 00:00:00'
  AND e.create_time < timestamp'2026-09-10 00:00:00'
ORDER BY e.create_time, e.change_event_type
""", "2) 该 mid 账户 9月 全部额度变更事件")

# 3) 决策流
q(f"""
SELECT biz_id, modelmainid, strategytype, createtime,
       substr(outputdata,1,100) AS out_snip
FROM ods.s21_risk_model_record
WHERE biz_id={BIZ} AND modelmainid IN (1386,1523)
ORDER BY createtime
""", "3) 决策流记录")

# 4) used_detail 本笔
q(f"""
SELECT biz_id, change_action, limit_type, risk_credit_limit, create_time
FROM ods.s05_user_creditlimit_used_detail
WHERE cast(biz_id as bigint)={BIZ}
ORDER BY create_time
""", "4) used_detail 本笔明细")

print("DONE-DRILL3")
