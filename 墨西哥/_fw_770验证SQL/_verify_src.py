# -*- coding: utf-8 -*-
"""验证新来源判定(src=mid+release前最近一次发放) vs 旧口径(biz级C010) 的差异与正确性"""
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

BIZ = "'1620000482618381','1620000483074755','1620000482922458','1620000462179690','1620000462287861','1620000463039322','1620000464027012'"

q(f"""
with app as (
  select cast(biz_id as varchar) as biz_id, mid, release_time
  from mx.wxs_application_funnel
  where tenant='yawey' and cast(biz_id as varchar) in ({BIZ})
),
src as (   -- 新口径: mid+放款前最近一次发放事件
  select biz_id, gtype, gtime, g_grant, g_used from (
    select cast(a.biz_id as varchar) as biz_id, e.change_event_type as gtype,
           e.create_time as gtime, e.change_total_grantamount as g_grant,
           e.change_used_grantamount as g_used,
           row_number() over (partition by a.biz_id order by e.create_time desc) rn
    from app a
    join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint)=cast(e.mid as bigint)
     and e.limit_type='TEMP' and e.change_event_type in ('C010','C013','C015')
     and e.create_time <= a.release_time
  ) t where rn=1
),
old as (   -- 旧口径: 本笔 biz 自身有 C010
  select distinct cast(a.biz_id as varchar) as biz_id
  from app a
  join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.biz_id as varchar)=e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C010'
)
select a.biz_id,
       case when l.biz_id is not null then '在线' else '离线' end        as "旧判定",
       coalesce(r.gtype,'(无发放)')                                      as "新口径_最近发放类型",
       r.gtime                                                           as "最近发放时刻",
       f.temp_grant_amount/1000.0                                        as "临额最终使用",
       case when r.gtype='C010' then f.temp_grant_amount/1000.0 else 0 end as "在线临额_新",
       case when r.gtype='C010' then 0 else f.temp_grant_amount/1000.0 end as "离线临额_新",
       f.contract_amount                                                 as "合同金额"
from app a
left join src r on a.biz_id=r.biz_id
left join old l on a.biz_id=l.biz_id
join mx.wxs_application_funnel f on a.biz_id=cast(f.biz_id as varchar) and f.tenant='yawey'
order by a.biz_id
""", "新来源判定 vs 旧口径 (7笔)")

print("DONE-VERIFY-SRC")
