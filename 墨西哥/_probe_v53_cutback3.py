# -*- coding: utf-8 -*-
"""Q5 全复贷口径(不做C010过滤) × hash组 × 阶段 — 策略总因果效应(ITT)
Q6 P2同期 V5_2(A+B) vs V5_3(C) 直接对比 — 剩余30%切掉的方案参数
Q7 反事实参考: V5_3组内 issue_tag=1 vs 0 (观察性)
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 420)

def q(sql, tag="", show=200):
    print("="*130)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:1000]); return None
    if r is None or len(r) == 0:
        print("[空数据]"); return None
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

HASH = """case when from_base(substr(to_hex(sha256(to_utf8('20260811'||y.credit_no||y.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'A_V5_2锚'
     when from_base(substr(to_hex(sha256(to_utf8('20260811'||y.credit_no||y.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'C_V5_3锚'
     else 'B_切换组' end"""

BASE = f"""select
    y.biz_id, y.if_issue, y.app_date, y.issue_date,
    y.temp_grant_amount, y.temp_credit_amount_issue_tag as issue_tag,
    y.t0_should_amt_1, y.t0_overdue_amount_1, y.real_issue_amount,
    {HASH} as hgrp
  from mx.yj_test_table_250225 y
  where y.is_reloan='old'
    and y.app_time >= cast('2026-08-01 00:00:00.000' as timestamp)
    and y.app_time <  cast('2026-10-06 00:00:00.000' as timestamp)"""

# Q5: 全复贷 阶段×hash组 (进件/放款/take_rate/1t0%)
r5 = q(f"""
with base as ({BASE})
select
  case when app_date >= date'2026-09-22' then 'P3_0922后(成熟中)'
       when app_date >= date'2026-09-03' then 'P2_0903后(切30%)'
       when app_date >= date'2026-08-10' then 'P1_0810-0903(70%)'
       else 'P0_0810前' end as phase,
  hgrp,
  count(*) as app_cnt,
  count(if(if_issue=1,1,null)) as loan_cnt,
  round(count(if(if_issue=1,1,null))*100.0/count(*),2) as take_rate,
  round(sum(if(if_issue=1,real_issue_amount,null))/1000.0,0) as loan_amt_k,
  round(avg(if(if_issue=1,real_issue_amount,null)),0) as loan_avg,
  count(if(if_issue=1 and t0_should_amt_1>0,1,null)) as mature_cnt,
  round(sum(if(if_issue=1,t0_should_amt_1,null))/1000.0,0) as should_k,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))/1000.0,0) as od_k,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))/nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) as t0_rate,
  count(if(if_issue=1 and temp_grant_amount>0,1,null)) as temp_use_cnt,
  round(sum(if(if_issue=1,temp_grant_amount,0))/1000.0/1000.0,0) as temp_kpeso
from base
group by 1,2 order by 1,2
""", "Q5 全复贷(无C010过滤) 阶段×hash组: 策略总ITT效应")

# Q6: P2同期(9/3-9/22) V5_2(A+B合并) vs V5_3(C) — 方案参数
r6 = q(f"""
with base as ({BASE})
select
  case when hgrp='C_V5_3锚' then 'V5_3(剩余30%灰度)' else 'V5_2(70%基准)' end as stg,
  count(*) as app_cnt,
  count(if(if_issue=1,1,null)) as loan_cnt,
  round(count(if(if_issue=1,1,null))*100.0/count(*),2) as take_rate,
  round(sum(if(if_issue=1,real_issue_amount,null))/1000.0,0) as loan_amt_k,
  round(avg(if(if_issue=1,real_issue_amount,null)),0) as loan_avg,
  count(if(if_issue=1 and t0_should_amt_1>0,1,null)) as mature_cnt,
  round(sum(if(if_issue=1,t0_should_amt_1,null))/1000.0,0) as should_k,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))/1000.0,0) as od_k,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))/nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) as t0_rate,
  count(if(if_issue=1 and temp_grant_amount>0,1,null)) as temp_use_cnt,
  round(count(if(if_issue=1 and temp_grant_amount>0,1,null))*100.0/count(if(if_issue=1,1,null)),2) as temp_use_pct,
  round(sum(if(if_issue=1,temp_grant_amount,0))/1000.0/1000.0,0) as temp_kpeso
from base
where app_date >= date'2026-09-03' and app_date < date'2026-09-22'
group by 1 order by 1
""", "Q6 P2同期(9/3-9/22) V5_2 vs V5_3 方案对比参数")

# Q7: V5_3组(C) P2 放款内 issue_tag 1 vs 0 (观察性参考)
r7 = q(f"""
with base as ({BASE})
select
  cast(issue_tag as varchar) as issue_tag,
  count(*) as loan_cnt,
  count(if(t0_should_amt_1>0,1,null)) as mature_cnt,
  round(sum(t0_should_amt_1)/1000.0,0) as should_k,
  round(sum(t0_overdue_amount_1)/1000.0,0) as od_k,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) as t0_rate
from base
where if_issue=1 and hgrp='C_V5_3锚' and app_date >= date'2026-09-03' and app_date < date'2026-09-22'
group by 1 order by 1
""", "Q7 C组(V5_3) P2内 发临额tag1 vs 未发tag0 坏账(观察性参考)")

# Q8: 全复贷 P2 整体(不分hash) — 方案测算大盘分母
r8 = q(f"""
with base as ({BASE})
select
  count(*) as app_cnt,
  count(if(if_issue=1,1,null)) as loan_cnt,
  round(count(if(if_issue=1,1,null))*100.0/count(*),2) as take_rate,
  round(sum(if(if_issue=1,real_issue_amount,null))/1000.0,0) as loan_amt_k,
  round(sum(if(if_issue=1,t0_should_amt_1,null))/1000.0,0) as should_k,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))/1000.0,0) as od_k,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))/nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) as t0_rate
from base
where app_date >= date'2026-09-03' and app_date < date'2026-09-22'
""", "Q8 全复贷 P2(9/3-9/22)大盘分母")

import pickle
with open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_v53_results2.pkl", "wb") as f:
    pickle.dump({"r5": r5, "r6": r6, "r7": r7, "r8": r8}, f)
print("saved.")
