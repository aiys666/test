# -*- coding: utf-8 -*-
"""下钻核验 1620000482618381 / 1620000483074755 全链路"""
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
    print("=" * 175); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception as ex:
            print(f"[err] {str(ex)[:220]}"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

BIZ = "'1620000482618381','1620000483074755'"

# 1) funnel 关键字段
q(f"""
select cast(biz_id as varchar) as biz_id, mid, app_time, apply_time, release_time,
       temp_grant_amount, contract_amount, issue_amount, if_issue, is_reloan, app_date
from mx.wxs_application_funnel
where tenant='yawey' and cast(biz_id as varchar) in ({BIZ})
""", "1) funnel 关键字段")

# 2) 该 mid 的全部 TEMP 额度变更事件（看有无 C013/C015 离线发放、C003/C004/C008）
q(f"""
with a as (
  select cast(biz_id as varchar) as biz_id, cast(mid as bigint) as mid
  from mx.wxs_application_funnel
  where tenant='yawey' and cast(biz_id as varchar) in ({BIZ})
)
select a.biz_id,
       e.change_event_type, e.change_action, e.limit_type,
       e.change_total_grantamount, e.change_used_grantamount,
       e.external_id, e.create_time, e.expiring_time, e.change_desc
from a
join ods_view_presto.s05_user_creditlimit_change_record e
  on a.mid = cast(e.mid as bigint)
where e.limit_type='TEMP'
order by a.biz_id, e.create_time
""", "2) 全部 TEMP 额度变更事件")

# 3) used_detail 冻结/解冻明细
q(f"""
with a as (
  select cast(biz_id as varchar) as biz_id, cast(mid as bigint) as mid
  from mx.wxs_application_funnel
  where tenant='yawey' and cast(biz_id as varchar) in ({BIZ})
)
select a.biz_id, u.change_action, u.limit_type, u.risk_credit_limit, u.create_time
from a
join ods.s05_user_creditlimit_used_detail u on a.mid = cast(u.mid as bigint)
order by a.biz_id, u.create_time
""", "3) used_detail 冻结/解冻明细")

# 4) model1386 弹窗决策（看 tag）
q(f"""
select cast(biz_id as varchar) as biz_id, createtime,
       regexp_extract(outputdata, '"temp_credit_amount_issue_tag":([0-9]+)', 1) as issue_tag
from ods.s21_risk_model_record
where modelmainid=1386 and strategytype='CHAMPION'
  and cast(biz_id as varchar) in ({BIZ})
order by biz_id, createtime
""", "4) model1386 弹窗决策(tag)")

# 5) 离线临额底表
q(f"""
with a as (
  select cast(biz_id as varchar) as biz_id, cast(mid as bigint) as mid
  from mx.wxs_application_funnel
  where tenant='yawey' and cast(biz_id as varchar) in ({BIZ})
)
select a.biz_id, b.temp_limit_tag, b.temp_limit_issue_amount, b.temp_limit_issue_date, b.mid
from a
join mx.yuhan_temp_limit_base_table_his_20260924 b on a.mid = cast(b.mid as bigint)
order by a.biz_id
""", "5) 离线临额底表 yuhan_..._20260924")

print("DONE-DRILL4")
