# -*- coding: utf-8 -*-
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
        except Exception:
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

BASE = """
with e as (
  select mid, create_time, change_event_type as evt,
    max(case when change_event_type='C004' then create_time end)
      over (partition by mid order by create_time rows between unbounded preceding and 1 preceding) as last_unfz,
    max(case when change_event_type='C003' then create_time end)
      over (partition by mid order by create_time rows between unbounded preceding and 1 preceding) as last_frz
  from ods_view_presto.s05_user_creditlimit_change_record
  where create_time >= date'2026-07-01'
    and change_event_type in ('C010','C013','C015','C003','C004') and limit_type='TEMP'
)
"""
COND = "evt in ('C010','C013','C015') and last_frz is not null and (last_unfz is null or last_frz>last_unfz)"

# Q4 冲突按调额类型拆分
q(f"""{BASE}
select evt as grant_evt, count(*) as conflict_cnt, count(distinct mid) as conflict_mids
from e where {COND} group by 1 order by conflict_cnt desc
""", "Q4 冲突按调额事件类型拆分")

# Q5 在线(C010)与离线(C013/C015)调额在72h内相邻的mid(两路径近距离)
q("""
with g as (
  select mid, create_time, change_event_type as evt
  from ods_view_presto.s05_user_creditlimit_change_record
  where create_time >= date'2026-07-01' and limit_type='TEMP'
    and change_event_type in ('C010','C015','C013')
)
select count(distinct o.mid) as mids_online_offline_within72h
from (select mid, create_time from g where evt='C010') o
join g on o.mid=g.mid and g.evt in ('C015','C013')
  and abs(to_unixtime(g.create_time)-to_unixtime(o.create_time)) <= 259200
""", "Q5 在线×离线调额72h内相邻的mid数")

# Q5b 在线调额时"上一次调额也是临额且未释放"的mid(真正的在线侧冲突)
q(f"""{BASE}
select count(distinct mid) as mid_cnt, count(*) as cnt
from e where evt='C010' and last_frz is not null and (last_unfz is null or last_frz>last_unfz)
""", "Q5b 在线C010 调额时临额未释放")

print("DONE-C2")
