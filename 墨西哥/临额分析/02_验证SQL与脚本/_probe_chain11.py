# -*- coding: utf-8 -*-
"""1504/1505 定性: 是否离线临额批量算额节点(无biz/整点/exp=5)
   Q1 全窗口分布  Q2 join change_record 验证与C013/C015金额关系"""
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

# Q1 1504/1505 全窗口分布
q("""
select modelmainid, count(*) n_rec, count(distinct mid) n_mid,
  count(distinct biz_id) n_biz_nonnull,
  min(createtime) t0, max(createtime) t1,
  min(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":(-?[0-9.]+)',1)) amin,
  max(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":(-?[0-9.]+)',1)) amax,
  array_join(array_agg(distinct regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_expired_day":([0-9]+)',1)), ',') exps,
  sum(case when minute(createtime)=0 and second(createtime)<2 then 1 else 0 end) n_exact_hour
from ods.s21_risk_model_record
where modelmainid in (1504,1505)
  and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
group by 1 order by 1
""", "Q1 1504/1505 全窗口分布(无biz?整点?exp分布?)")

# Q2: 1505 金额 vs 同 mid 近邻 C013/C015 金额
q("""
with b as (
  select cast(regexp_extract(cast(outputdata as varchar),'"mid":"([0-9]+)"',1) as bigint) mid,
         createtime as bt,
         cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double) bamt
  from ods.s21_risk_model_record
  where modelmainid=1504 and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
),
e as (
  select mid, create_time et, change_total_grantamount eamt, change_event_type etype,
         row_number() over (partition by mid order by abs(date_diff('second', create_time, b.bt))) rn
  from b join ods_view_presto.s05_user_creditlimit_change_record e
    on b.mid=cast(e.mid as bigint)
   and e.limit_type='TEMP' and e.change_event_type in ('C013','C015')
   and e.create_time between b.bt - interval '3' day and b.bt + interval '3' day
)
select etype, count(*) n_pair,
  sum(case when bamt=eamt then 1 else 0 end) n_eq,
  avg(abs(bamt-eamt)) avg_diff
from b join e on b.mid=e.mid and e.rn=1
group by 1 order by 1
""", "Q2 1504批量额 vs 同mid最近C013/C015 金额一致率(±3天)")
print("DONE-PROBE11")
