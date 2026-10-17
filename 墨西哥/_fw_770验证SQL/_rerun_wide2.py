# -*- coding: utf-8 -*-
"""用当前宽表SQL重跑这两笔，确认占用主额/临额占用是否已有值"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 3000); pd.set_option('display.max_rows', 400)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 190); print(tag, flush=True)
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

q(f"""
with
app as (
  select cast(biz_id as varchar) as biz_id, mid, app_time, apply_time
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and cast(biz_id as varchar) in ({BIZ})
),
off as (
  select biz_id, off_time, off_amt, off_exp from (
    select cast(a.biz_id as varchar) as biz_id, e.create_time as off_time,
           e.change_total_grantamount as off_amt, e.expiring_time as off_exp,
           row_number() over (partition by a.biz_id order by e.create_time desc) rn
    from app a join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint)=cast(e.mid as bigint)
     and e.limit_type='TEMP' and e.change_event_type in ('C013','C015')
     and e.create_time <= a.apply_time
  ) t where rn=1
),
onl as (
  select cast(a.biz_id as varchar) as biz_id, min(e.create_time) as on_time,
         sum(e.change_total_grantamount) as on_grant,
         sum(e.change_total_grantamount - e.change_used_grantamount) as on_actual
  from app a join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.biz_id as varchar)=e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C010' group by 1
),
frz as (
  select cast(a.biz_id as varchar) as biz_id, min(e.create_time) as use_time
  from app a join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.biz_id as varchar)=e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C003' group by 1
),
iss as (
  select biz_id, min(createtime) as issue_time
  from ods.s21_risk_model_record
  where modelmainid=1386 and strategytype='CHAMPION'
    and outputdata like '%"temp_credit_amount_issue_tag":1%'
    and cast(biz_id as varchar) in ({BIZ})
  group by 1
),
utd as (
  select cast(u.biz_id as varchar) as biz_id, sum(u.risk_credit_limit) as temp_occupy
  from ods.s05_user_creditlimit_used_detail u
  join app a on cast(u.biz_id as bigint) = cast(a.biz_id as bigint)
  where u.change_action='FREEZE_LIMIT' and u.limit_type='TEMP' group by 1
),
utdm as (
  select cast(u.biz_id as varchar) as biz_id, sum(u.risk_credit_limit) as main_occupy
  from ods.s05_user_creditlimit_used_detail u
  join app a on cast(u.biz_id as bigint) = cast(a.biz_id as bigint)
  where u.change_action='FREEZE_LIMIT' and u.limit_type='MAIN' group by 1
)
select a.biz_id                      as "biz_id",
       o.off_time                    as "离线发放时间",
       o.off_amt                     as "离线发放金额",
       case when n.on_actual is null then z.use_time end as "离线使用时间",
       case when n.on_actual is null then f.temp_grant_amount/1000.0 else 0 end as "离线使用金额",
       s.issue_time                  as "在线发放时间_1386",
       n.on_grant                    as "在线发放金额",
       n.on_time                     as "在线使用时间_C010",
       z.use_time                    as "冻结C003",
       u.temp_occupy                 as "临额占用金额",
       f.temp_grant_amount/1000.0    as "临额最终使用",
       case when n.on_actual is not null then f.temp_grant_amount/1000.0 else 0 end as "在线临额",
       case when n.on_actual is not null then 0 else f.temp_grant_amount/1000.0 end as "离线临额",
       f.contract_amount             as "合同金额",
       m.main_occupy                 as "占用主额金额"
from app a
left join off  o on a.biz_id=o.biz_id
left join onl  n on a.biz_id=n.biz_id
left join frz  z on a.biz_id=z.biz_id
left join iss  s on cast(a.biz_id as bigint)=s.biz_id
left join utd  u on a.biz_id=u.biz_id
left join utdm m on a.biz_id=m.biz_id
join mx.wxs_application_funnel f on a.biz_id=cast(f.biz_id as varchar) and f.tenant='yawey'
order by a.biz_id
""", "重跑宽表(这2笔) 现状")

print("DONE-RERUN-WIDE2")
