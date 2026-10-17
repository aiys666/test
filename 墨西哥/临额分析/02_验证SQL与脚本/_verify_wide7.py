# -*- coding: utf-8 -*-
"""修复后宽表回归: 报错2笔 + 已知正确样本, 对照字段"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 3200); pd.set_option('display.max_rows', 400)

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

BIZ = "('1620000479377160','1620000474757589','1620000483074755','1620000482618381',\
'1620000462179690','1620000462287861','1620000463039322','1620000464027012','1620000482922458',\
'1620000463197032','1620000466574256')"

SQL = f"""
with
app as (
  select cast(biz_id as varchar) as biz_id, mid, app_time, apply_time, release_time,
         temp_grant_amount as temp_grant
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
frz as (
  select cast(a.biz_id as varchar) as biz_id, min(e.create_time) as use_time
  from app a join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.biz_id as varchar)=e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C003' group by 1
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
    where a.temp_grant > 0
  ) t where rn=1
),
src as (
  select biz_id, gtype, gtime, g_grant, g_used from (
    select cast(a.biz_id as varchar) as biz_id, e.change_event_type as gtype,
           e.create_time as gtime, e.change_total_grantamount as g_grant,
           e.change_used_grantamount as g_used,
           row_number() over (partition by a.biz_id order by e.create_time desc) rn
    from app a left join frz z on cast(a.biz_id as varchar)=z.biz_id
    join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint)=cast(e.mid as bigint)
     and e.limit_type='TEMP' and e.change_event_type in ('C010','C013','C015')
     and e.create_time <= coalesce(z.use_time, a.release_time)
    where a.temp_grant > 0
  ) t where rn=1
),
iss as (
  select biz_id, min(createtime) as issue_time from ods.s21_risk_model_record
  where modelmainid=1386 and strategytype='CHAMPION'
    and outputdata like '%"temp_credit_amount_issue_tag":1%' group by biz_id
),
pamt as (
  select biz_id, amt from (
    select cast(biz_id as varchar) as biz_id,
           cast(regexp_extract(cast(outputdata as varchar), '"temp_credit_amount":([0-9.]+)', 1) as double) as amt,
           row_number() over (partition by biz_id order by createtime) as rn
    from ods.s21_risk_model_record
    where modelmainid=857
      and cast(regexp_extract(cast(outputdata as varchar), '"temp_credit_amount":([0-9.]+)', 1) as double) > 0
  ) t where rn=1
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
select a.biz_id,
       a.app_time,
       a.apply_time,
       a.release_time,
       o.off_time                    as "离线发放时间",
       o.off_amt                     as "离线发放金额",
       case when coalesce(r.gtype,'')='C010' then null else z.use_time end as "离线使用时间",
       case when coalesce(r.gtype,'')='C010' then 0 else f.temp_grant_amount/1000.0 end as "离线使用金额",
       case when o.biz_id is null then '无'
            when o.off_exp > a.apply_time then '仍有效' else '已过期' end as "离线当时状态",
       case when o.biz_id is null or coalesce(r.gtype,'')<>'C010' then '不适用'
            when r.g_grant >= o.off_amt then '是(在线>=离线)'
            else '否(在线<离线)' end as "在线是否覆盖离线",
       r.gtype                       as "来源gtype",
       s.issue_time                  as "在线发放时间_model1386",
       case when s.issue_time is not null
            then coalesce(p.amt, case when r.gtype='C010' then r.g_grant end) end as "在线临额发放金额",
       case when r.gtype='C010' then r.gtime end              as "在线临额使用时间_C010",
       case when r.gtype='C010' then r.g_grant - r.g_used end as "在线临额使用金额_C010",
       z.use_time                    as "临额冻结时刻_C003",
       u.temp_occupy                 as "临额占用金额",
       f.temp_grant_amount/1000.0    as "临额最终使用金额",
       case when r.gtype='C010' then f.temp_grant_amount/1000.0 else 0 end as "临额最终使用(在线临额)",
       case when r.gtype='C010' then 0 else f.temp_grant_amount/1000.0 end as "临额最终使用(离线临额)",
       f.contract_amount             as "合同金额_放款金额",
       m.main_occupy                 as "占用主额金额"
from app a
left join off  o on a.biz_id=o.biz_id
left join src  r on a.biz_id=r.biz_id
left join frz  z on a.biz_id=z.biz_id
left join iss  s on cast(a.biz_id as bigint)=s.biz_id
left join pamt p on a.biz_id=p.biz_id
left join utd  u on a.biz_id=u.biz_id
left join utdm m on a.biz_id=m.biz_id
join mx.wxs_application_funnel f on a.biz_id=cast(f.biz_id as varchar) and f.tenant='yawey'
where a.biz_id in {BIZ}
order by a.biz_id
"""
q(SQL, "修复后宽表回归(报错2笔 + 已知样本7笔)")
print("DONE-VERIFY7")
