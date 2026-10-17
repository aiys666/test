# -*- coding: utf-8 -*-
"""探查6: type1 50%/60%二分规律(时间/策略/评级) + type2失配明细 + label分布"""
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

# A type1 按天 x 比例桶
q("""
with s1523 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_type":([0-9.]+)',1) as double)) utype,
         max(createtime) ct
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
select substr(cast(t3.ct as varchar),1,10) d,
       sum(case when abs(t.t1379/m.main_frz-0.5)<0.005 then 1 else 0 end) r50,
       sum(case when abs(t.t1379/m.main_frz-0.6)<0.005 then 1 else 0 end) r60,
       sum(case when abs(t.t1379/m.main_frz-0.5)>=0.005 and abs(t.t1379/m.main_frz-0.6)>=0.005 then 1 else 0 end) other
from s1379 t join s1523 t3 on t.biz=t3.biz join mm m on t.biz=m.biz
where t.t1379 is not null and t3.utype=1
group by 1 order by 1
""", "A type1 50%/60% 按日分布")

# B type1 比例 vs yj 策略分桶/评级
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
select y.temp_credit_amount_strategy_test_flag as strat,
       case when abs(t.t1379/m.main_frz-0.5)<0.005 then '50%'
            when abs(t.t1379/m.main_frz-0.6)<0.005 then '60%' else 'other' end rbucket,
       count(*) n
from s1379 t join s1523 t3 on t.biz=t3.biz join mm m on t.biz=m.biz
join mx.yj_test_table_250225 y on cast(y.biz_id as varchar)=t.biz
where t.t1379 is not null and t3.utype=1
group by 1,2 order by 1,2
""", "B type1比例 vs 策略分桶(yj)")

# C type2/type3 不精确命中样本
q("""
with s1523 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_type":([0-9.]+)',1) as double)) utype
  from ods.s21_risk_model_record
  where modelmainid=1523 and strategytype='CHAMPION'
    and createtime>=timestamp '2026-09-20' and createtime<timestamp '2026-10-16'
  group by 1
),
s1379 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double)) t1379
  from ods.s21_risk_model_record
  where modelmainid=1379 and strategytype='CHAMPION'
    and createtime>=timestamp '2026-09-20' and createtime<timestamp '2026-10-16'
  group by 1
),
mm as (
  select cast(biz_id as varchar) biz, sum(risk_credit_limit) main_frz
  from ods.s05_user_creditlimit_used_detail
  where change_action='FREEZE_LIMIT' and limit_type='MAIN'
  group by 1
)
select t.biz, t3.utype, t.t1379, m.main_frz,
       t.t1379/m.main_frz r_actual,
       t.t1379 - m.main_frz*case t3.utype when 2 then 0.4 when 3 then 0.2 end diff
from s1379 t join s1523 t3 on t.biz=t3.biz join mm m on t.biz=m.biz
where t.t1379 is not null and t3.utype in (2,3)
  and abs(t.t1379 - m.main_frz*case t3.utype when 2 then 0.4 when 3 then 0.2 end) > 0.01
order by t3.utype, abs(t.t1379 - m.main_frz*case t3.utype when 2 then 0.4 when 3 then 0.2 end) desc
limit 25
""", "C type2/3 失配明细TOP25")

# D 1379 decision_tree_label 分布
q("""
select cast(regexp_extract(cast(outputdata as varchar),'"decision_tree_label":([0-9]+)',1) as integer) label,
       cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_expired_day":([0-9]+)',1) as integer) expday,
       count(*) n,
       sum(case when outputdata not like '%"temp_credit_amount":null%' then 1 else 0 end) amt_notnull
from ods.s21_risk_model_record
where modelmainid=1379 and strategytype='CHAMPION'
  and createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
group by 1,2 order by 1,2
""", "D 1379 label/expired_day 分布")
print("DONE-PROBE6")
