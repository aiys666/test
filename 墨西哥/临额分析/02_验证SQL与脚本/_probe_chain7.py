# -*- coding: utf-8 -*-
"""探查7: 底数公式定稿 floor(MAIN/20)*20 × 比例(V5_2/V5_3) 全量验证"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 4000)
pd.set_option('display.max_colwidth', 10000); pd.set_option('display.max_rows', 400)
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

# A 实际比值分布: t1379 / floor(MAIN/20)*20, 按 type × 策略
q("""
with s1523 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_type":([0-9.]+)',1) as double)) utype
  from ods.s21_risk_model_record
  where modelmainid=1523 and strategytype='CHAMPION'
    and createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
  group by 1
),
s1379 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double)) t1379
  from ods.s21_risk_model_record
  where modelmainid=1379 and strategytype='CHAMPION'
    and createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
  group by 1
),
mm as (
  select cast(biz_id as varchar) biz, sum(risk_credit_limit) main_frz
  from ods.s05_user_creditlimit_used_detail
  where change_action='FREEZE_LIMIT' and limit_type='MAIN'
  group by 1
)
select t3.utype,
       case when y.temp_credit_amount_strategy_test_flag like '%V5_3%' then 'V5_3' else 'V5_2' end strat,
       round(t.t1379/(floor(m.main_frz/20.0)*20),3) r_actual,
       count(*) n
from s1379 t join s1523 t3 on t.biz=t3.biz join mm m on t.biz=m.biz
left join mx.yj_test_table_250225 y on cast(y.biz_id as varchar)=t.biz
where t.t1379 is not null and m.main_frz>=40
group by 1,2,3
order by 1,2,4 desc
""", "A 实际比值分布(type×策略)")

# B 全量公式命中率: base20×比例(按策略选0.5/0.6) == t1379
q("""
with s1523 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_type":([0-9.]+)',1) as double)) utype
  from ods.s21_risk_model_record
  where modelmainid=1523 and strategytype='CHAMPION'
    and createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
  group by 1
),
s1379 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double)) t1379
  from ods.s21_risk_model_record
  where modelmainid=1379 and strategytype='CHAMPION'
    and createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
  group by 1
),
mm as (
  select cast(biz_id as varchar) biz, sum(risk_credit_limit) main_frz
  from ods.s05_user_creditlimit_used_detail
  where change_action='FREEZE_LIMIT' and limit_type='MAIN'
  group by 1
),
x as (
  select t3.utype,
         case when y.temp_credit_amount_strategy_test_flag like '%V5_3%' then 0.6
              when t3.utype=1 then 0.5 when t3.utype=2 then 0.4 when t3.utype=3 then 0.2 end rto,
         t.t1379, floor(m.main_frz/20.0)*20 as base20
  from s1379 t join s1523 t3 on t.biz=t3.biz join mm m on t.biz=m.biz
  left join mx.yj_test_table_250225 y on cast(y.biz_id as varchar)=t.biz
  where t.t1379 is not null
)
select utype, rto, count(*) n,
       sum(case when abs(t1379-base20*rto)<0.01 then 1 else 0 end) exact,
       avg(abs(t1379-base20*rto)) avg_diff,
       max(abs(t1379-base20*rto)) max_diff
from x group by 1,2 order by 1,2
""", "B 公式全量命中率(base20×比例)")

# C type4 有金额的10笔
q("""
with s1523 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_type":([0-9.]+)',1) as double)) utype
  from ods.s21_risk_model_record
  where modelmainid=1523 and strategytype='CHAMPION'
    and createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
  group by 1
),
s1379 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double)) t1379
  from ods.s21_risk_model_record
  where modelmainid=1379 and strategytype='CHAMPION'
    and createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
  group by 1
),
mm as (
  select cast(biz_id as varchar) biz, sum(risk_credit_limit) main_frz
  from ods.s05_user_creditlimit_used_detail
  where change_action='FREEZE_LIMIT' and limit_type='MAIN'
  group by 1
)
select t.biz, t.t1379, m.main_frz
from s1379 t join s1523 t3 on t.biz=t3.biz join mm m on t.biz=m.biz
where t.t1379 is not null and t3.utype=4
order by t.t1379 desc
""", "C type4有金额笔")
print("DONE-PROBE7")
