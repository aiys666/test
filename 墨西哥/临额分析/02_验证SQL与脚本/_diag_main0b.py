# -*- coding: utf-8 -*-
"""②核查"无占用主额"到底是不是真缺失: used_detail MAIN行是否存在 + 全量分布"""
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
    print("=" * 170); print(tag, flush=True)
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

BIZ = "'1620000479377160','1620000474757589','1620000483074755'"

# Q2' used_detail 明细(去掉不存在的 expiration_time 列)
q(f"""
select cast(biz_id as varchar) as biz_id, limit_type, change_action, risk_credit_limit,
       create_time, limit_main_id
from ods.s05_user_creditlimit_used_detail
where cast(biz_id as varchar) in ({BIZ})
order by 1, 5
""", "Q2' used_detail 明细(本笔实际冻结)")

# Q5 全量: 占用主额为空到底有多少、是不是都因为"全额走临额"
q("""
with app as (
  select cast(biz_id as varchar) as biz_id, temp_grant_amount/1000.0 as temp_used, contract_amount,
         substr(cast(release_time as varchar),1,7) as rel_month,
         release_time
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
utd as (   -- TEMP 冻结
  select cast(u.biz_id as varchar) as biz_id, sum(u.risk_credit_limit) as temp_occ
  from ods.s05_user_creditlimit_used_detail u
  join app a on cast(u.biz_id as bigint)=cast(a.biz_id as bigint)
  where u.change_action='FREEZE_LIMIT' and u.limit_type='TEMP' group by 1
),
utdm as (  -- MAIN 冻结
  select cast(u.biz_id as varchar) as biz_id, sum(u.risk_credit_limit) as main_occ
  from ods.s05_user_creditlimit_used_detail u
  join app a on cast(u.biz_id as bigint)=cast(a.biz_id as bigint)
  where u.change_action='FREEZE_LIMIT' and u.limit_type='MAIN' group by 1
)
select a.rel_month as "放款月", count(*) as "放款笔数",
  sum(case when m.biz_id is null then 1 else 0 end) as "占用主额为空",
  sum(case when m.biz_id is null and u.biz_id is null then 1 else 0 end) as "主额空且临额也空",
  sum(case when m.biz_id is null and coalesce(u.temp_occ,0)>0 then 1 else 0 end) as "主额空但用了临额",
  sum(case when m.biz_id is not null and abs(a.contract_amount - m.main_occ - coalesce(u.temp_occ,0))<0.01 then 1 else 0 end) as "恒等式成立",
  sum(case when m.biz_id is not null then 1 else 0 end) as "主额有值",
  sum(case when a.release_time > timestamp '2026-10-14 00:00:00' then 1 else 0 end) as "近2日放款"
from app a
left join utd  u on a.biz_id=u.biz_id
left join utdm m on a.biz_id=m.biz_id
group by 1 order by 1
""", "Q5 全量: 占用主额为空分布(按放款月)")

print("DONE-DIAG2")
