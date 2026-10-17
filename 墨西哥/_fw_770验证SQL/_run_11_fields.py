# -*- coding: utf-8 -*-
"""验证【字段版】四字段: 计数须与Step2一致 + 抽样证明无重复biz_id/标签不互污"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 620)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 100); print(tag, flush=True)
    for i in range(6):
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

CTE = """
app as (
  select cast(biz_id as varchar) as biz_id, mid, app_time
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
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
),
temp_tag as (
  select cast(a.biz_id as varchar) as biz_id,
    case when f.biz_id is not null then 1 else 0 end as offline_temp_tag,
    case when o.biz_id is not null then 1 else 0 end as online_temp_tag,
    case when o.biz_id is not null and f.biz_id is not null then '混合'
         when o.biz_id is not null then '在线'
         when f.biz_id is not null then '离线'
         else '无' end as temp_grp
  from app a
  left join online  o on cast(a.biz_id as varchar) = o.biz_id
  left join offline f on cast(a.biz_id as varchar) = f.biz_id
)
"""

# V1 计数对账(须与Step2一致: 在线4670/离线23858/混合1714/无27255)
q(f"WITH {CTE} SELECT temp_grp, COUNT(*) AS cnt, COUNT(DISTINCT biz_id) AS biz_cnt FROM temp_tag GROUP BY 1 ORDER BY 1",
  "V1 四字段计数对账")

# V2 标签组合一致性
q(f"WITH {CTE} SELECT offline_temp_tag, online_temp_tag, COUNT(*) AS cnt FROM temp_tag GROUP BY 1,2 ORDER BY 1,2",
  "V2 两标签组合(证明独立不互污)")

# V3 样例(含混合行, 两标签都=1)
q(f"WITH {CTE} SELECT biz_id, offline_temp_tag, online_temp_tag, temp_grp FROM temp_tag WHERE temp_grp='混合' LIMIT 5",
  "V3 混合行样例(两标签同时=1)")
q(f"WITH {CTE} SELECT biz_id, offline_temp_tag, online_temp_tag, temp_grp FROM temp_tag ORDER BY temp_grp, biz_id LIMIT 12",
  "V3b 各分类样例")

print("DONE-11FIELDS")
