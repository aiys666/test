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

# Q6 事件码 -> 动作 映射(确认解冻事件码)
q("""
select change_event_type as evt, change_action, limit_type, count(*) as c
from ods_view_presto.s05_user_creditlimit_change_record
where create_time >= date'2026-07-01'
group by 1,2,3 order by c desc limit 30
""", "Q6 事件码×动作×limit_type 映射")

# Q7 纠正版冲突扫描: 冻结/解冻用 change_action 判定
BASE = """
with e as (
  select mid, create_time, change_event_type as evt, change_action,
    max(case when change_action='UNFREEZE_LIMIT' then create_time end)
      over (partition by mid order by create_time rows between unbounded preceding and 1 preceding) as last_unfz,
    max(case when change_action='FREEZE_LIMIT' then create_time end)
      over (partition by mid order by create_time rows between unbounded preceding and 1 preceding) as last_frz
  from ods_view_presto.s05_user_creditlimit_change_record
  where create_time >= date'2026-07-01' and limit_type='TEMP'
    and (change_event_type in ('C010','C013','C015') or change_action in ('FREEZE_LIMIT','UNFREEZE_LIMIT'))
)
"""
COND = "evt in ('C010','C013','C015') and last_frz is not null and (last_unfz is null or last_frz>last_unfz)"
q(f"""{BASE}
select count(if(evt in ('C010','C013','C015'),1,null)) as grant_total,
  count(if({COND},1,null)) as conflict_cnt,
  count(distinct if({COND},mid,null)) as conflict_mids
from e
""", "Q7 纠正版冲突规模")

q(f"""{BASE}
select evt as grant_evt, count(*) as conflict_cnt, count(distinct mid) as conflict_mids
from e where {COND} group by 1 order by conflict_cnt desc
""", "Q7b 纠正版冲突按类型")

print("DONE-C4")
