# -*- coding: utf-8 -*-
"""导出四字段打标结果表: biz_id | offline_temp_tag | online_temp_tag | temp_grp"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

SQL = """
with
app as (
  select cast(biz_id as varchar) as biz_id, mid, app_time
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'{d0}' and app_date < date'{d1}'
),
online as (
  select distinct cast(a.biz_id as varchar) as biz_id
  from app a
  join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.biz_id as varchar) = e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C010'
),
offline as (
  select distinct cast(a.biz_id as varchar) as biz_id
  from app a
  join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.mid as bigint) = cast(e.mid as bigint)
   and e.limit_type='TEMP' and e.change_event_type in ('C013','C015')
   and e.create_time <= a.app_time
   and a.app_time < e.create_time + interval '7' day
)
select
  cast(a.biz_id as varchar) as biz_id,
  case when f.biz_id is not null then 1 else 0 end as offline_temp_tag,
  case when o.biz_id is not null then 1 else 0 end as online_temp_tag,
  case when o.biz_id is not null and f.biz_id is not null then '混合'
       when o.biz_id is not null then '在线'
       when f.biz_id is not null then '离线'
       else '无' end as temp_grp
from app a
left join online  o on cast(a.biz_id as varchar) = o.biz_id
left join offline f on cast(a.biz_id as varchar) = f.biz_id
"""

import datetime
def run(sql):
    for i in range(8):
        r = pq.query(sql)
        if not isinstance(r, str): return r
        print(f"[retry {i+1}] {str(r)[:200]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    raise RuntimeError("query failed")

# 平台单次上限 10000 行 -> 按 5 天窗口切片
start = datetime.date(2026, 9, 1)
end = datetime.date(2026, 10, 16)
parts = []
d = start
while d < end:
    d2 = min(d + datetime.timedelta(days=5), end)
    df = run(SQL.format(d0=d.isoformat(), d1=d2.isoformat()))
    print(f"  {d} ~ {d2}: rows={len(df)}")
    parts.append(df)
    d = d2
r = pd.concat(parts, ignore_index=True)

print(f"[rows={len(r)}]")
print(r['temp_grp'].value_counts().to_string())

out = r"E:\岳松个人文件\嘉银工作内容的整理\code\临额打标_biz_id在线离线_20260910月.xlsx"
with pd.ExcelWriter(out, engine='openpyxl') as w:
    r.to_excel(w, sheet_name='临额打标', index=False)
print("✅ 已导出:", out)
