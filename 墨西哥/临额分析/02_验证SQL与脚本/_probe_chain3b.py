# -*- coding: utf-8 -*-
"""探查3b: 1379理论额→857最终额 调整规则(英文别名) + 定位472→450原笔"""
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

# B 全量命中率(英文别名)
q("""
with a as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double)) t1379
  from ods.s21_risk_model_record
  where modelmainid=1379 and createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
  group by 1
),
b as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double)) t857
  from ods.s21_risk_model_record
  where modelmainid=857 and createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
  group by 1
)
select count(*) as n_pair,
       sum(case when a.t1379 is not null then 1 else 0 end) as n_1379,
       sum(case when b.t857>0 then 1 else 0 end) as n_857pos,
       sum(case when b.t857=a.t1379 then 1 else 0 end) as n_eq,
       sum(case when b.t857=floor(a.t1379/50)*50 then 1 else 0 end) as n_floor50,
       sum(case when b.t857=floor(a.t1379/100)*100 then 1 else 0 end) as n_floor100,
       sum(case when b.t857=round(a.t1379/50)*50 then 1 else 0 end) as n_round50,
       sum(case when b.t857=floor(a.t1379/20)*20 then 1 else 0 end) as n_floor20,
       sum(case when b.t857<=a.t1379 then 1 else 0 end) as n_le,
       avg(b.t857/nullif(a.t1379,0)) as avg_ratio
from a join b on a.biz=b.biz
where a.t1379 is not null
""", "B 1379 vs 857 rule hit")

# C 不等样本40条 + type
q("""
with a as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double)) t1379
  from ods.s21_risk_model_record
  where modelmainid=1379 and createtime>=timestamp '2026-09-20' and createtime<timestamp '2026-10-16'
  group by 1
),
b as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double)) t857
  from ods.s21_risk_model_record
  where modelmainid=857 and createtime>=timestamp '2026-09-20' and createtime<timestamp '2026-10-16'
  group by 1
),
tp as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_type":([0-9.]+)',1) as double)) utype
  from ods.s21_risk_model_record
  where modelmainid=1523 and createtime>=timestamp '2026-09-20' and createtime<timestamp '2026-10-16'
  group by 1
)
select a.biz, tp.utype, a.t1379, b.t857,
       b.t857-a.t1379 as diff,
       a.t1379-floor(a.t1379/50)*50 as mod50,
       a.t1379-floor(a.t1379/100)*100 as mod100
from a join b on a.biz=b.biz left join tp on a.biz=tp.biz
where b.t857 is not null and b.t857>0 and b.t857<>a.t1379
order by a.t1379
limit 40
""", "C neq samples")

# E 定位 1379=472 的笔
q("""
select cast(biz_id as varchar) biz, createtime, cast(outputdata as varchar) od
from ods.s21_risk_model_record
where modelmainid=1379
  and outputdata like '%"temp_credit_amount":472%'
  and createtime>=timestamp '2026-08-01'
order by createtime
limit 10
""", "E locate t1379=472")
print("DONE-PROBE3B")
