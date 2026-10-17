# -*- coding: utf-8 -*-
"""精准收缩方案测算数据:
Q1 P2窗口(9/3-9/22) V5_3(C组)/V5_2(A+B) × tag × 评级档 全指标
Q2 全复贷P2大盘分母(放款金额/授信/应还/逾期)
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 420)

def q(sql, tag="", show=200):
    print("="*130); print(tag)
    r = pq.query(sql)
    if isinstance(r, str): print("[ERR]", r[:1500]); return None
    if r is None or len(r)==0: print("[空]"); return None
    print(r.to_string() if len(r)<=show else r.head(show).to_string())
    print(f"[rows={len(r)}]"); return r

HASH = """case when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'V5_3' else 'V5_2' end"""

# Q1: 策略×tag×评级档 (P2全成熟窗口)
r1 = q(f"""
select
  {HASH} as stg,
  case when temp_credit_amount_issue_tag=1 then 'tag1' else 'tag0' end as tag,
  case when cast(fd_creditlevel_main_v4_2 as double) >= 9 then 'c_g9p'
       when cast(fd_creditlevel_main_v4_2 as double) >= 6 then 'b_g6_8'
       else 'a_g1_5' end as grade_grp,
  count(*) as deal,
  round(sum(real_issue_amount)/1000.0,1) as loan_k,
  round(avg(real_issue_amount),0) as loan_avg,
  round(sum(t0_should_amt_1)/1000.0,1) as should_k,
  round(sum(t0_overdue_amount_1)/1000.0,1) as od_k,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) as t0_rate,
  round(sum(credit_amount)/1000.0,1) as credit_k,
  round(avg(temp_grant_amount)/1000.0,0) as temp_avg
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-09-03' and app_date < date'2026-09-22'
group by 1,2,3 order by 3,1,2
""", "Q1 P2(9/3-9/22) 策略×tag×评级档")

# Q2: 全复贷P2大盘
r2 = q("""
select
  count(*) as deal,
  round(sum(real_issue_amount)/1000.0,1) as loan_k,
  round(sum(credit_amount)/1000.0,1) as credit_k,
  round(sum(t0_should_amt_1)/1000.0,1) as should_k,
  round(sum(t0_overdue_amount_1)/1000.0,1) as od_k,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) as t0_rate
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-09-03' and app_date < date'2026-09-22'
""", "Q2 全复贷P2大盘分母")

# Q3: 全复贷P2进件口径授信(含未放款, TR分母)
r3 = q("""
select
  count(*) as app_cnt,
  round(sum(credit_amount)/1000.0,1) as credit_k,
  round(sum(if(if_issue=1,real_issue_amount,null))/1000.0,1) as loan_k,
  round(sum(if(if_issue=1,real_issue_amount,null))/nullif(sum(credit_amount),0)*100,2) as tr_amt
from mx.yj_test_table_250225
where is_reloan='old'
  and app_date >= date'2026-09-03' and app_date < date'2026-09-22'
""", "Q3 全复贷P2进件口径(TR分母含未放款授信)")

import pickle
pickle.dump({"r1":r1,"r2":r2,"r3":r3}, open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_plan_precise.pkl","wb"))
print("saved.")
