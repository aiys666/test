# -*- coding: utf-8 -*-
"""1504批量额 vs C015实发: 差值分布 + 同mid同日是否多笔(叠额?)"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 4000)
pd.set_option('display.max_colwidth', 10000); pd.set_option('display.max_rows', 300)
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

q("""
with b as (
  select cast(regexp_extract(cast(outputdata as varchar),'"mid":"([0-9]+)"',1) as bigint) as bmid,
         createtime as bt,
         cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double) as bamt
  from ods.s21_risk_model_record
  where modelmainid=1504 and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
    and cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double) > 0
),
j as (
  select b.bmid, b.bt, b.bamt, e.change_total_grantamount eamt,
         row_number() over (partition by b.bmid, b.bt
           order by abs(date_diff('second', e.create_time, b.bt))) rn
  from b join ods_view_presto.s05_user_creditlimit_change_record e
    on b.bmid=cast(e.mid as bigint)
   and e.limit_type='TEMP' and e.change_event_type='C015'
   and e.create_time between b.bt - interval '3' day and b.bt + interval '3' day
)
select cast(eamt-bamt as bigint) diff, count(*) n
from j where rn=1
group by 1 order by n desc limit 20
""", "Q1 C015实发-1504推荐 差值分布top20")

# 同mid同一天 1504 笔数分布(重复圈人?)
q("""
select n_per_day, count(*) n_groups from (
  select cast(regexp_extract(cast(outputdata as varchar),'"mid":"([0-9]+)"',1) as bigint) mid,
         date(createtime) d, count(*) n_per_day
  from ods.s21_risk_model_record
  where modelmainid=1504 and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
  group by 1,2
) t group by 1 order by 1
""", "Q2 同mid同日 1504 记录数分布")
print("DONE-PROBE11C")
