# -*- coding: utf-8 -*-
"""按月: 在线/离线临额最终使用占比 + 临额占合同金额比"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 2600); pd.set_option('display.max_rows', 300)
for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)
def q(sql, tag):
    print("=" * 160); print(tag, flush=True)
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
  select cast(biz_id as varchar) as biz_id, mid,
         substr(cast(release_time as varchar),1,7) as rel_month,
         temp_grant_amount/1000.0 as used_temp, contract_amount
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-07-01' and app_date < date'2026-10-16'
),
onl as (
  select distinct cast(a.biz_id as varchar) as biz_id
  from app a join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.biz_id as varchar)=e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C010'
),
x as (
  select a.rel_month, a.used_temp, a.contract_amount,
         case when n.biz_id is not null then a.used_temp else 0 end as online_used,
         case when n.biz_id is not null then 0 else a.used_temp end as offline_used
  from app a left join onl n on a.biz_id=n.biz_id
)
select rel_month                        as "放款月",
       count(*)                         as "放款笔数",
       sum(contract_amount)             as "合同金额合计",
       sum(used_temp)                   as "临额最终使用合计",
       sum(online_used)                 as "在线临额使用合计",
       sum(offline_used)                as "离线临额使用合计",
       sum(online_used)/nullif(sum(contract_amount),0)  as "在线临额占合同比",
       sum(offline_used)/nullif(sum(contract_amount),0) as "离线临额占合同比",
       sum(used_temp)/nullif(sum(contract_amount),0)    as "临额占合同比",
       sum(online_used)/nullif(sum(used_temp),0)   as "在线占临额比",
       sum(offline_used)/nullif(sum(used_temp),0)  as "离线占临额比"
from x group by 1 order by 1
""", "按月: 临额使用占合同金额比 (放款月 7/1-10/16)")
print("DONE-MONTH")
