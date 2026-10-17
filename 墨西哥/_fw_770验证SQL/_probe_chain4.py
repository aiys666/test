# -*- coding: utf-8 -*-
"""探查4: 底数链验证 1379理论额 vs MAIN冻结×type比例; 两笔样例全链路核对"""
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

# A 两笔样例全链路核对
q("""
select cast(f.biz_id as varchar) biz_id, f.mid, f.contract_amount,
       f.temp_grant_amount/1000.0 as temp_grant,
       f.apply_time, f.release_time
from mx.wxs_application_funnel f
where f.tenant='yawey' and f.biz_id in ('1620000462179690','1620000462287861')
""", "A1 funnel两笔")

q("""
select cast(biz_id as varchar) biz_id, limit_type, change_action,
       create_time, risk_credit_limit
from ods.s05_user_creditlimit_used_detail
where biz_id in (1620000462179690,1620000462287861)
order by biz_id, create_time
""", "A2 used_detail两笔")

q("""
select cast(external_id as varchar) biz_id, change_event_type, create_time,
       change_total_grantamount total_amt, change_used_grantamount used_amt,
       expiring_time
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP'
  and (external_id in ('1620000462179690','1620000462287861')
       or mid in (select mid from mx.wxs_application_funnel
                  where biz_id in ('1620000462179690','1620000462287861')))
  and create_time >= timestamp '2026-08-25'
order by mid, create_time
""", "A3 TEMP事件两笔(同mid全量)")

# B 全量底数链: 1379理论额 vs MAIN冻结×type比例 (CHAMPION, 9/1-10/16)
q("""
with s1522 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_score_v1":(-?[0-9.]+)',1) as double)) score
  from ods.s21_risk_model_record
  where modelmainid=1522 and strategytype='CHAMPION'
    and createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
  group by 1
),
s1523 as (
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
s857 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double)) t857
  from ods.s21_risk_model_record
  where modelmainid=857 and strategytype='CHAMPION'
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
  select t.utype, t.t1379, b.t857, m.main_frz,
         case t.utype when 1 then 0.5 when 2 then 0.4 when 3 then 0.2 end as ratio
  from s1379 t join s1523 t3 on t.biz=t3.biz
  left join s1522 t2 on t.biz=t2.biz
  left join s857 b on t.biz=b.biz
  left join mm m on t.biz=m.biz
  where t.t1379 is not null
)
select utype, ratio, count(*) n,
       sum(case when abs(t1379-main_frz*ratio)<0.01 then 1 else 0 end) exact_hit,
       sum(case when main_frz is null then 1 else 0 end) no_main_frz,
       avg(abs(t1379-main_frz*ratio)) avg_absdiff,
       max(abs(t1379-main_frz*ratio)) max_absdiff,
       sum(case when t857=round(t1379/50.0)*50 then 1 else 0 end) round50_hit
from x group by 1,2 order by 1
""", "B 底数链分层验证 type × (MAIN冻结×比例)")

# C 失配样本(理论额≠MAIN×比例)看原因
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
       m.main_frz*case t3.utype when 1 then 0.5 when 2 then 0.4 when 3 then 0.2 end as calc,
       t.t1379 - m.main_frz*case t3.utype when 1 then 0.5 when 2 then 0.4 when 3 then 0.2 end as diff
from s1379 t join s1523 t3 on t.biz=t3.biz join mm m on t.biz=m.biz
where t.t1379 is not null and t3.utype in (1,2,3)
  and abs(t.t1379 - m.main_frz*case t3.utype when 1 then 0.5 when 2 then 0.4 when 3 then 0.2 end) > 0.01
order by abs(t.t1379 - m.main_frz*case t3.utype when 1 then 0.5 when 2 then 0.4 when 3 then 0.2 end) desc
limit 20
""", "C 底数失配样本TOP20")
print("DONE-PROBE4")
