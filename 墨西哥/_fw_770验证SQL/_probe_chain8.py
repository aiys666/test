# -*- coding: utf-8 -*-
"""探查8: 评级节点1500/1542/1635、授信节点1067 覆盖率与取值; 异常桶复核"""
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

# 分母: 9/1-10/16 复贷放款笔数
q("""
select count(distinct cast(biz_id as varchar)) n_loan
from mx.wxs_application_funnel
where tenant='yawey' and is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
""", "DENOM 放款笔数")

# A 各节点覆盖率 + CHAMPION 占比(节点, key)
q("""
with loan as (
  select distinct cast(biz_id as varchar) biz
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
)
select s.modelmainid,
       count(distinct cast(s.biz_id as varchar)) n_biz,
       count(distinct case when s.strategytype='CHAMPION' then cast(s.biz_id as varchar) end) n_champ
from (
  select modelmainid, biz_id, strategytype from ods.s21_risk_model_record
  where createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
    and modelmainid in (1067,1500,1542,1635,1522,1523,1386,1379,857)
) s join loan l on cast(s.biz_id as varchar)=l.biz
group by 1 order by 1
""", "A 各节点在放款笔上的覆盖率")

# B 1067 节点 outputdata 取值样本(确认 credit_amount/daily_max 取数)
q("""
select cast(biz_id as varchar) biz, createtime,
       cast(regexp_extract(cast(outputdata as varchar),'"credit_amount":([0-9.]+)',1) as double) credit_amt,
       cast(regexp_extract(cast(outputdata as varchar),'"daily_max_available_limit":([0-9.]+)',1) as double) daily_max,
       cast(regexp_extract(cast(outputdata as varchar),'"grantcredit_7d_amount":([0-9.]+)',1) as double) g7d,
       cast(regexp_extract(cast(outputdata as varchar),'"credit_amount_expired_day":([0-9]+)',1) as integer) expday
from ods.s21_risk_model_record
where modelmainid=1067 and createtime>=timestamp '2026-09-20' and createtime<timestamp '2026-09-21'
  and outputdata like '%"credit_amount":%' and outputdata not like '%"credit_amount":null%'
limit 10
""", "B 1067授信节点样本")

# C 评级节点取值分布(1500 V5_2 / 1542 V5_3 / 1635 V6_1)
q("""
select modelmainid,
       regexp_extract(cast(outputdata as varchar),':([0-9]+)',1) grade,
       count(*) n
from ods.s21_risk_model_record
where modelmainid in (1500,1542,1635) and strategytype='CHAMPION'
  and createtime>=timestamp '2026-09-20' and createtime<timestamp '2026-09-27'
group by 1,2 order by 1,2
""", "C 评级节点取值分布(一周)")

# D V5_2桶出现type1=0.6的3笔复核(决策时刻vs yj快照)
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
select t.biz, t3.utype, t.t1379, m.main_frz,
       t.t1379/(floor(m.main_frz/20.0)*20) r_actual,
       y.temp_credit_amount_strategy_test_flag flag, y.dt
from s1379 t join s1523 t3 on t.biz=t3.biz join mm m on t.biz=m.biz
left join mx.yj_test_table_250225 y on cast(y.biz_id as varchar)=t.biz
where t3.utype=1 and abs(t.t1379/(floor(m.main_frz/20.0)*20)-0.6)<0.005
  and y.temp_credit_amount_strategy_test_flag like '%V5_2%'
""", "D V5_2桶type1=0.6异常笔")
print("DONE-PROBE8")
