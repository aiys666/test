# -*- coding: utf-8 -*-
"""核实 biz 1620000466574256 全链路 + 复现宽表行"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 2400); pd.set_option('display.max_rows', 300)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 150); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception as ex:
            print(f"[err] {str(ex)[:180]}"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

BIZ = "'1620000466574256'"

q(f"""
select cast(biz_id as varchar) as biz_id, mid, app_time, apply_time, release_time,
       contract_amount, issue_amount, temp_grant_amount, grantcredit_amount
from mx.wxs_application_funnel
where tenant='yawey' and cast(biz_id as varchar) in ({BIZ})
""", "B. funnel")

q(f"""
select e.change_event_type, e.change_action, e.change_total_grantamount, e.change_used_grantamount,
       e.create_time, e.expiring_time, e.change_desc
from mx.wxs_application_funnel f
join ods_view_presto.s05_user_creditlimit_change_record e on cast(f.mid as bigint)=cast(e.mid as bigint)
where f.tenant='yawey' and cast(f.biz_id as varchar) in ({BIZ}) and e.limit_type='TEMP'
order by e.create_time
""", "C. change_record TEMP")

q(f"""
select cast(u.biz_id as varchar) as biz_id, u.change_action, u.limit_type, u.risk_credit_limit, u.create_time
from ods.s05_user_creditlimit_used_detail u
where cast(u.biz_id as varchar) in ({BIZ}) order by u.create_time
""", "D. used_detail MAIN+TEMP")

q(f"""
select biz_id, createtime, outputdata
from ods.s21_risk_model_record
where modelmainid=1386 and strategytype='CHAMPION' and cast(biz_id as varchar) in ({BIZ})
""", "E. model1386")

# 复现宽表行
q(f"""
with
app as (
  select cast(biz_id as varchar) as biz_id, mid, app_time, apply_time
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1 and cast(biz_id as varchar) in ({BIZ})
),
off as (
  select biz_id, off_time, off_amt, off_exp from (
    select cast(a.biz_id as varchar) as biz_id, e.create_time as off_time,
           e.change_total_grantamount as off_amt, e.expiring_time as off_exp,
           row_number() over (partition by a.biz_id order by e.create_time desc) rn
    from app a join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint)=cast(e.mid as bigint)
     and e.limit_type='TEMP' and e.change_event_type in ('C013','C015') and e.create_time <= a.apply_time
  ) t where rn=1
),
onl as (
  select cast(a.biz_id as varchar) as biz_id, min(e.create_time) as on_time,
         sum(e.change_total_grantamount) as on_grant,
         sum(e.change_total_grantamount - e.change_used_grantamount) as on_actual
  from app a join ods_view_presto.s05_user_creditlimit_change_record e on cast(a.biz_id as varchar)=e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C010' group by 1
),
frz as (
  select cast(a.biz_id as varchar) as biz_id, min(e.create_time) as use_time
  from app a join ods_view_presto.s05_user_creditlimit_change_record e on cast(a.biz_id as varchar)=e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C003' group by 1
),
iss as (
  select biz_id, min(createtime) as issue_time from ods.s21_risk_model_record
  where modelmainid=1386 and strategytype='CHAMPION'
    and outputdata like '%"temp_credit_amount_issue_tag":1%' and cast(biz_id as varchar) in ({BIZ}) group by biz_id
),
utd as (
  select cast(u.biz_id as varchar) as biz_id, sum(u.risk_credit_limit) as temp_occupy
  from ods.s05_user_creditlimit_used_detail u join app a on cast(u.biz_id as bigint)=cast(a.biz_id as bigint)
  where u.change_action='FREEZE_LIMIT' and u.limit_type='TEMP' group by 1
),
utdm as (
  select cast(u.biz_id as varchar) as biz_id, sum(u.risk_credit_limit) as main_occupy
  from ods.s05_user_creditlimit_used_detail u join app a on cast(u.biz_id as bigint)=cast(a.biz_id as bigint)
  where u.change_action='FREEZE_LIMIT' and u.limit_type='MAIN' group by 1
)
select a.biz_id, a.app_time as "进件", f.apply_time as "申请", f.release_time as "放款",
       o.off_time as "离线发放时间", o.off_amt as "离线发放金额",
       case when o.biz_id is null then '无' when o.off_exp > a.apply_time then '仍有效' else '已过期' end as "离线状态",
       case when o.biz_id is null or n.on_grant is null then '不适用' when n.on_grant >= o.off_amt then '是' else '否' end as "在线覆盖离线",
       s.issue_time as "在线发放时间1386", n.on_grant as "在线发放金额", n.on_time as "在线使用时间C010",
       n.on_actual as "在线使用金额C010", z.use_time as "冻结C003", u.temp_occupy as "临额占用", 
       f.temp_grant_amount/1000.0 as "临额最终使用", f.contract_amount as "合同金额", m.main_occupy as "占用主额"
from app a
left join off o on a.biz_id=o.biz_id
left join onl n on a.biz_id=n.biz_id
left join frz z on a.biz_id=z.biz_id
left join iss s on cast(a.biz_id as bigint)=s.biz_id
left join utd u on a.biz_id=u.biz_id
left join utdm m on a.biz_id=m.biz_id
join mx.wxs_application_funnel f on a.biz_id=cast(f.biz_id as varchar) and f.tenant='yawey'
""", "F. 复现宽表行")

print("DONE-DRILL3")
