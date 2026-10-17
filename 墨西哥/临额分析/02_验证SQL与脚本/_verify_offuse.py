# -*- coding: utf-8 -*-
"""验证新增字段: 离线使用时间 / 离线使用金额（紧跟 离线发放时间/金额）"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 2600); pd.set_option('display.max_rows', 300)

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

BIZ = "'1620000463039322','1620000482922458','1620000462179690','1620000462287861','1620000464027012'"

q(f"""
with
app as (
  select cast(biz_id as varchar) as biz_id, mid, app_time, apply_time
  from mx.wxs_application_funnel
  where tenant='yawey' and cast(biz_id as varchar) in ({BIZ})
),
off as (
  select biz_id, off_time, off_amt from (
    select cast(a.biz_id as varchar) as biz_id, e.create_time as off_time,
           e.change_total_grantamount as off_amt,
           row_number() over (partition by a.biz_id order by e.create_time desc) rn
    from app a join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint)=cast(e.mid as bigint)
     and e.limit_type='TEMP' and e.change_event_type in ('C013','C015')
     and e.create_time <= a.apply_time
  ) t where rn=1
),
onl as (
  select cast(a.biz_id as varchar) as biz_id,
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
)
select a.biz_id,
       case when n.on_actual is not null then '有C010' else '无C010' end          as "是否在线",
       z.use_time                                                                   as "临额冻结时刻_C003",
       o.off_time                                                                   as "离线发放时间",
       case when n.on_actual is null then z.use_time end                            as "离线使用时间",
       case when n.on_actual is null then f.temp_grant_amount/1000.0 else 0 end     as "离线使用金额",
       f.temp_grant_amount/1000.0                                                   as "临额最终使用金额",
       case when n.on_actual is null then f.temp_grant_amount/1000.0 else 0 end     as "临额最终使用(离线临额)"
from app a
left join off o on a.biz_id=o.biz_id
left join onl n on a.biz_id=n.biz_id
left join frz z on a.biz_id=z.biz_id
join mx.wxs_application_funnel f on a.biz_id=cast(f.biz_id as varchar) and f.tenant='yawey'
order by a.biz_id
""", "新增字段验证: 离线使用时间/离线使用金额 (5笔)")

print("DONE-OFFUSE")
