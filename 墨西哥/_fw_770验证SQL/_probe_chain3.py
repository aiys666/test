# -*- coding: utf-8 -*-
"""探查3: 472(1379理论额)→450(857最终额) 调整规则全量破解"""
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

# A 462287861 五节点精简链路
q("""
select modelmainid, createtime, strategytype, cast(outputdata as varchar) as od
from ods.s21_risk_model_record
where biz_id=1620000462287861 and modelmainid in (1522,1523,1386,1379,857)
order by createtime
""", "A 462287861 五节点链路")

# B 全量 1379理论额 vs 857最终额: 命中率 + 取整规则检验
q("""
with a as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double)) t1379,
         max(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_expired_day":([0-9]+)',1) as double)) expday
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
select count(*) as 配对笔数,
       sum(case when a.t1379 is not null then 1 else 0 end) as 有1379理论额,
       sum(case when b.t857>0 then 1 else 0 end) as 有857最终额,
       sum(case when b.t857=a.t1379 then 1 else 0 end) as 完全相等,
       sum(case when b.t857=floor(a.t1379/50)*50 then 1 else 0 end) as 命中floor50,
       sum(case when b.t857=floor(a.t1379/100)*100 then 1 else 0 end) as 命中floor100,
       sum(case when b.t857=round(a.t1379/50)*50 then 1 else 0 end) as 命中round50,
       sum(case when b.t857<=a.t1379 then 1 else 0 end) as 最终额不大于理论额,
       avg(b.t857/nullif(a.t1379,0)) as 均值比
from a join b on a.biz=b.biz
where a.t1379 is not null
""", "B 1379理论额 vs 857最终额 规则命中率")

# C 不等样本30条(看差额定律)
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
       b.t857/nullif(a.t1379,0) as ratio,
       a.t1379-floor(a.t1379/50)*50 as 理论额除以50余数,
       floor(a.t1379/50)*50 as floor50
from a join b on a.biz=b.biz left join tp on a.biz=tp.biz
where b.t857 is not null and b.t857>0 and b.t857<>a.t1379
order by a.t1379
limit 30
""", "C 1379≠857 样本30条")

# D 857 同 biz 多变量同刻样本
q("""
select modelmainid, createtime, cast(outputdata as varchar) od
from ods.s21_risk_model_record
where biz_id=1620000470052229 and modelmainid=857
order by createtime
""", "D 857节点同biz全部变量写入(470052229)")
print("DONE-PROBE3")
