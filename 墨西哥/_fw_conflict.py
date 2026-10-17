# -*- coding: utf-8 -*-
"""冲突扫描: 同一 mid 在同一 TEMP 账户上"未解冻即再调额"(C010/C013/C015)
判据: 某次调额事件之前, 最近一次 C003(FREEZE) 晚于最近一次 C004(UNFREEZE) => 冻结尚未释放就再次调额
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 400)

def q(sql, tag):
    print("=" * 90); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception as e:
            print(f"[conn retry {i+1}]"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:160]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}"); return None

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: print("[login retry]"); time.sleep(8)

# Q1 事件类型 × limit_type 分布(确认 C013/C015 归属)
q("""
select change_event_type as evt, limit_type, count(*) as c, count(distinct mid) as mids
from ods_view_presto.s05_user_creditlimit_change_record
where create_time >= date'2026-07-01'
  and change_event_type in ('C010','C013','C015','C003','C004')
group by 1,2 order by c desc
""", "Q1 临额相关事件 × limit_type 分布")

# Q2 冲突规模: 调额前最近一次冻结未解冻
q("""
with e as (
  select mid, create_time, change_event_type as evt, limit_type,
    max(case when change_event_type='C004' then create_time end)
      over (partition by mid order by create_time rows between unbounded preceding and 1 preceding) as last_unfz,
    max(case when change_event_type='C003' then create_time end)
      over (partition by mid order by create_time rows between unbounded preceding and 1 preceding) as last_frz
  from ods_view_presto.s05_user_creditlimit_change_record
  where create_time >= date'2026-07-01'
    and change_event_type in ('C010','C013','C015','C003','C004')
    and limit_type='TEMP'
)
select
  count(if(evt in ('C010','C013','C015'),1,null)) as grant_total,
  count(if(evt in ('C010','C013','C015') and last_frz is not null and (last_unfz is null or last_frz>last_unfz),1,null)) as grant_while_frozen,
  count(distinct mid) as mid_total
from e
""", "Q2 冲突规模(TEMP账户: 调额时冻结未释放)")

# Q2b 分别统计冲突mid
q("""
with e as (
  select mid, create_time, change_event_type as evt,
    max(case when change_event_type='C004' then create_time end)
      over (partition by mid order by create_time rows between unbounded preceding and 1 preceding) as last_unfz,
    max(case when change_event_type='C003' then create_time end)
      over (partition by mid order by create_time rows between unbounded preceding and 1 preceding) as last_frz
  from ods_view_presto.s05_user_creditlimit_change_record
  where create_time >= date'2026-07-01'
    and change_event_type in ('C010','C013','C015','C003','C004')
    and limit_type='TEMP'
)
select count(distinct mid) as conflict_mids
from e
where evt in ('C010','C013','C015') and last_frz is not null and (last_unfz is null or last_frz>last_unfz)
""", "Q2b 冲突 mid 数")

# Q3 样例10个冲突mid + 下一次调额/冻结时间
q("""
with e as (
  select mid, create_time, change_event_type as evt,
    max(case when change_event_type='C004' then create_time end)
      over (partition by mid order by create_time rows between unbounded preceding and 1 preceding) as last_unfz,
    max(case when change_event_type='C003' then create_time end)
      over (partition by mid order by create_time rows between unbounded preceding and 1 preceding) as last_frz
  from ods_view_presto.s05_user_creditlimit_change_record
  where create_time >= date'2026-07-01'
    and change_event_type in ('C010','C013','C015','C003','C004')
    and limit_type='TEMP'
)
select mid, evt as grant_evt, create_time as grant_time, last_frz, last_unfz,
  cast(round((to_unixtime(create_time)-to_unixtime(last_frz))/3600.0,1) as double) as frozen_hours
from e
where evt in ('C010','C013','C015') and last_frz is not null and (last_unfz is null or last_frz>last_unfz)
order by create_time desc limit 10
""", "Q3 冲突样例(最近10个)")

print("DONE-CONFLICT")
