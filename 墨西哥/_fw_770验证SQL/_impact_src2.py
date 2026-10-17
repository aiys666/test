# -*- coding: utf-8 -*-
"""修复2 影响面: 旧规则(release锚点+无门槛) 会污染多少笔"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 2000)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 150); print(tag, flush=True)
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

q("""
with app as (
  select cast(biz_id as varchar) as biz_id, mid, apply_time, release_time,
         temp_grant_amount/1000.0 as temp_used
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
old_src as (   -- 旧口径: mid + release前最近一次发放(无 temp>0 门槛)
  select biz_id, gtype from (
    select cast(a.biz_id as varchar) as biz_id, e.change_event_type as gtype,
           row_number() over (partition by a.biz_id order by e.create_time desc) rn
    from app a join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint)=cast(e.mid as bigint)
     and e.limit_type='TEMP' and e.change_event_type in ('C010','C013','C015')
     and e.create_time <= a.release_time
  ) t where rn=1
),
frz as (
  select cast(a.biz_id as varchar) as biz_id, min(e.create_time) as use_time
  from app a join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.biz_id as varchar)=e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C003' group by 1
),
new_src as (   -- 新口径: C003锚点 + temp>0 门槛
  select biz_id, gtype from (
    select cast(a.biz_id as varchar) as biz_id, e.change_event_type as gtype,
           row_number() over (partition by a.biz_id order by e.create_time desc) rn
    from app a left join frz z on cast(a.biz_id as varchar)=z.biz_id
    join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint)=cast(e.mid as bigint)
     and e.limit_type='TEMP' and e.change_event_type in ('C010','C013','C015')
     and e.create_time <= coalesce(z.use_time, a.release_time)
    where a.temp_used > 0
  ) t where rn=1
)
select count(*) as "复贷放款笔数",
  sum(case when a.temp_used=0 then 1 else 0 end)                            as "无临额笔(temp=0)",
  sum(case when a.temp_used=0 and o.biz_id is not null then 1 else 0 end)   as "★被旧规则污染的笔(无临额却挂发放)",
  sum(case when a.temp_used>0 then 1 else 0 end)                            as "临额笔(temp>0)",
  sum(case when a.temp_used>0 and coalesce(o.gtype,'')<>coalesce(n.gtype,'') then 1 else 0 end) as "临额笔中来源判定被改",
  sum(case when a.temp_used>0 and coalesce(o.gtype,'')='C010' then 1 else 0 end) as "旧判在线",
  sum(case when a.temp_used>0 and coalesce(n.gtype,'')='C010' then 1 else 0 end) as "新判在线"
from app a
left join old_src o on a.biz_id=o.biz_id
left join new_src n on a.biz_id=n.biz_id
""", "修复2 影响面(9/1-10/16)")
print("DONE-IMPACT2")
