# -*- coding: utf-8 -*-
"""量化来源判定修复的影响面: 旧口径(biz级C010) vs 新口径(mid+release前最近发放)"""
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
    print("=" * 185); print(tag, flush=True)
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

q("""
with app as (
  select cast(biz_id as varchar) as biz_id, mid, release_time
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
used as (
  select cast(biz_id as varchar) as biz_id, temp_grant_amount/1000.0 as tg,
         substr(cast(release_time as varchar),1,7) as rel_month
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
    and temp_grant_amount > 0
),
src as (
  select biz_id, gtype from (
    select cast(a.biz_id as varchar) as biz_id, e.change_event_type as gtype,
           row_number() over (partition by a.biz_id order by e.create_time desc) rn
    from app a
    join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint)=cast(e.mid as bigint)
     and e.limit_type='TEMP' and e.change_event_type in ('C010','C013','C015')
     and e.create_time <= a.release_time
  ) t where rn=1
),
old as (
  select distinct cast(a.biz_id as varchar) as biz_id
  from app a
  join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.biz_id as varchar)=e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C010'
)
select coalesce(u.rel_month,'合计')                                                     as "放款月",
       count(*)                                                                          as "用了临额笔数",
       sum(case when old.biz_id is not null then 1 else 0 end)                            as "旧_在线笔数",
       sum(case when src.gtype='C010' then 1 else 0 end)                                  as "新_在线笔数",
       sum(case when (old.biz_id is not null) <> (src.gtype='C010') then 1 else 0 end)    as "判定变化笔数",
       sum(case when old.biz_id is null and src.gtype='C010' then 1 else 0 end)           as "离线改在线",
       sum(case when old.biz_id is not null and coalesce(src.gtype,'')<>'C010' then 1 else 0 end) as "在线改离线",
       sum(case when old.biz_id is null and src.gtype='C010' then u.tg else 0 end)        as "离线改在线_金额",
       sum(case when old.biz_id is not null and coalesce(src.gtype,'')<>'C010' then u.tg else 0 end) as "在线改离线_金额"
from used u
left join src on u.biz_id=src.biz_id
left join old on u.biz_id=old.biz_id
group by rollup(u.rel_month)
order by 1
""", "来源判定修复影响面 (9/1-10/16, 仅用临额笔)")

print("DONE-IMPACT-SRC")
