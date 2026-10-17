# -*- coding: utf-8 -*-
"""查 used_detail 自身的 biz_id 列值，判断 utd/utdm 按 biz_id 关联是否命中"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 2600); pd.set_option('display.max_rows', 400)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 175); print(tag, flush=True)
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

MIDS = "1040160073822454,1040160073517835"

# used_detail 自身 biz_id 列值（不借用 funnel 的 biz_id）
q(f"""
select cast(u.biz_id as varchar) as u_own_biz_id,
       cast(u.mid as varchar) as u_mid,
       u.limit_main_id, u.change_action, u.limit_type,
       u.risk_credit_limit, u.create_time
from ods.s05_user_creditlimit_used_detail u
where cast(u.mid as bigint) in ({MIDS})
order by u.mid, u.create_time
""", "A) used_detail 自身 biz_id 列 (两 mid 全部行)")

# 复现宽表口径：按 used_detail.biz_id 关联 funnel.biz_id 聚合
q(f"""
with a as (
  select cast(biz_id as varchar) as biz_id, cast(mid as bigint) as mid
  from mx.wxs_application_funnel
  where tenant='yawey' and cast(biz_id as varchar) in ('1620000482618381','1620000483074755')
),
agg as (
  select cast(u.biz_id as varchar) as biz_id,
         sum(case when u.limit_type='MAIN' then u.risk_credit_limit else 0 end) as main_occupy,
         sum(case when u.limit_type='TEMP' then u.risk_credit_limit else 0 end) as temp_occupy,
         count(*) as n_rows
  from ods.s05_user_creditlimit_used_detail u
  join a on cast(u.biz_id as bigint)=cast(a.biz_id as bigint)
  where u.change_action='FREEZE_LIMIT'
  group by 1
)
select a.biz_id, g.main_occupy, g.temp_occupy, g.n_rows
from a left join agg g on a.biz_id=g.biz_id
order by a.biz_id
""", "B) 复现宽表: 按 u.biz_id=funnel.biz_id 关联聚合(FREEZE)")

print("DONE-UTD2")
