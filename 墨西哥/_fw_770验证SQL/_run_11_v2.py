# -*- coding: utf-8 -*-
"""验证字段版v2"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 900)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 100); print(tag, flush=True)
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
        print(f"[retry {i+1}] {str(r)[:200]}"); time.sleep(6)
    return None

q("""
with
app as (
  select cast(biz_id as varchar) as biz_id, mid, app_time, temp_grant_amount as used_temp
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
online as (
  select distinct cast(a.biz_id as varchar) as biz_id
  from app a join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.biz_id as varchar)=e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C010'
),
offline_last as (
  select biz_id, expiring_time from (
    select cast(a.biz_id as varchar) as biz_id, e.expiring_time,
           row_number() over (partition by a.biz_id order by e.create_time desc) rn
    from app a join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint)=cast(e.mid as bigint)
     and e.limit_type='TEMP' and e.change_event_type in ('C013','C015')
     and e.create_time <= a.app_time and a.app_time < e.create_time + interval '7' day
  ) t where rn=1
)
select
  case
    when o.biz_id is not null and l.biz_id is not null and l.expiring_time > a.app_time then '真混合'
    when o.biz_id is not null and l.biz_id is not null then '在线(离线已过期)'
    when o.biz_id is not null then '在线'
    when l.biz_id is not null and l.expiring_time > a.app_time then '离线(有效)'
    when l.biz_id is not null then '离线(已过期)'
    else '无' end as temp_grp2,
  COUNT(*) AS cnt,
  SUM(case when l.biz_id is not null and l.expiring_time <= a.app_time then 1 else 0 end) AS offline_expired_cnt,
  SUM(case when l.biz_id is not null and l.expiring_time <= a.app_time and o.biz_id is not null and a.used_temp>0 then 1 else 0 end) AS used_after_expired_cnt
from app a
left join online       o on cast(a.biz_id as varchar)=o.biz_id
left join offline_last l on cast(a.biz_id as varchar)=l.biz_id
GROUP BY 1 ORDER BY 1
""", "v2 temp_grp2 计数")

print("DONE-V2")
