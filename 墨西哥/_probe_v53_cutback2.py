# -*- coding: utf-8 -*-
"""0903回调效果评估 核心查询
Q2 放款周 × hash组: 1t0%/放款金额/临额使用/成熟度
Q3 阶段P1(8/10-9/3) vs P2(9/3后) × hash组: 进件/放款/take_rate/1t0% (ITT + 实际使用临额子群)
Q4 全复贷大盘按周
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 420)
pd.set_option('display.max_colwidth', 40)

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

EVT = f"""tmp_evt as (
  select mid, change_event_type, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
),
evt_last as (
  select biz_id, change_event_type,
    row_number() over (partition by biz_id order by create_time desc) as rn
  from (
    select y.biz_id, e.change_event_type, e.create_time
    from mx.yj_test_table_250225 y
    join tmp_evt e on y.mid = e.mid and e.create_time <= y.release_time
    where y.is_reloan='old'
      and y.app_time >= cast('2026-07-01 00:00:00.000' as timestamp)
      and y.app_time <  cast('2026-10-06 00:00:00.000' as timestamp)
  ) x
),
base as (
  select
    y.biz_id, y.if_issue, y.app_date, y.issue_date,
    y.temp_grant_amount, y.temp_credit_amount_issue_tag as issue_tag,
    y.t0_should_amt_1, y.t0_overdue_amount_1,
    y.real_issue_amount,
    el.change_event_type as tl_type,
    {HASH} as hgrp
  from mx.yj_test_table_250225 y
  left join evt_last el on y.biz_id = el.biz_id and el.rn=1
  where y.is_reloan='old'
    and y.app_time >= cast('2026-07-01 00:00:00.000' as timestamp)
    and y.app_time <  cast('2026-10-06 00:00:00.000' as timestamp)
)"""

# Q2: 放款周 × hash组 (C010在线临额放款)
r2 = q(f"""
with {EVT}
select
  date_format(date_trunc('week', issue_date), '%Y-%m-%d') as iwk,
  hgrp,
  count(*) as loan_cnt,
  round(sum(real_issue_amount)/1000.0, 0) as loan_amt_k,
  count(if(t0_should_amt_1 > 0, 1, null)) as t0_mature_cnt,
  round(sum(t0_should_amt_1)/1000.0, 0) as t0_should_k,
  round(sum(t0_overdue_amount_1)/1000.0, 0) as t0_od_k,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100, 2) as t0_rate,
  count(if(temp_grant_amount > 0, 1, null)) as use_cnt,
  round(sum(temp_grant_amount)/1000.0/1000.0, 0) as temp_used_kpeso,
  count(if(issue_tag=1,1,null)) as tag1_cnt
from base
where if_issue=1 and tl_type='C010' and issue_date >= date'2026-07-27'
group by 1,2 order by 1,2
""", "Q2 C010在线临额 放款周×hash组 1t0%(成熟口径)")

# Q3a: 阶段×hash组 ITT(全部C010放款)
r3a = q(f"""
with {EVT}
select
  case when app_date >= date'2026-09-03' then 'P2_0903后(切30%)'
       when app_date >= date'2026-08-10' then 'P1_0810-0903(70%)'
       else 'P0_0810前' end as phase,
  hgrp,
  count(if(if_issue=1,1,null)) as loan_cnt,
  round(sum(if(if_issue=1, real_issue_amount, null))/1000.0,0) as loan_amt_k,
  count(if(if_issue=1 and t0_should_amt_1>0,1,null)) as mature_cnt,
  round(sum(if(if_issue=1, t0_should_amt_1, null))/1000.0,0) as should_k,
  round(sum(if(if_issue=1, t0_overdue_amount_1, null))/1000.0,0) as od_k,
  round(sum(if(if_issue=1, t0_overdue_amount_1, null))/nullif(sum(if(if_issue=1, t0_should_amt_1, null)),0)*100,2) as t0_rate,
  count(if(if_issue=1 and issue_tag=1,1,null)) as tag1_cnt,
  count(if(if_issue=1 and temp_grant_amount>0,1,null)) as use_cnt,
  round(sum(if(if_issue=1, temp_grant_amount,0))/1000.0/1000.0,0) as temp_kpeso
from base
where tl_type='C010' and app_date >= date'2026-08-01'
group by 1,2 order by 1,2
""", "Q3a C010 阶段×hash组 ITT全部放款")

# Q3b: 阶段×hash组 实际使用临额子群(temp>0)的1t0%
r3b = q(f"""
with {EVT}
select
  case when app_date >= date'2026-09-03' then 'P2_0903后(切30%)'
       when app_date >= date'2026-08-10' then 'P1_0810-0903(70%)'
       else 'P0_0810前' end as phase,
  hgrp,
  count(*) as use_loan_cnt,
  round(sum(t0_should_amt_1)/1000.0,0) as should_k,
  round(sum(t0_overdue_amount_1)/1000.0,0) as od_k,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) as t0_rate
from base
where if_issue=1 and tl_type='C010' and temp_grant_amount > 0
  and app_date >= date'2026-08-01'
group by 1,2 order by 1,2
""", "Q3b 实际使用临额(temp>0)子群 阶段×hash组 1t0%")

# Q3c: 进件口径 take_rate (C010全部进件)
r3c = q(f"""
with {EVT}
select
  case when app_date >= date'2026-09-03' then 'P2_0903后(切30%)'
       when app_date >= date'2026-08-10' then 'P1_0810-0903(70%)'
       else 'P0_0810前' end as phase,
  hgrp,
  count(*) as app_cnt,
  count(if(if_issue=1,1,null)) as loan_cnt,
  round(count(if(if_issue=1,1,null))*1.0/count(*)*100, 2) as take_rate,
  round(avg(if(if_issue=1, real_issue_amount, null)),1) as loan_avg
from base
where tl_type='C010' and app_date >= date'2026-08-01'
group by 1,2 order by 1,2
""", "Q3c C010进件口径 阶段×hash组 take_rate")

# Q4: 全复贷大盘按放款周
r4 = q(f"""
select
  date_format(date_trunc('week', issue_date), '%Y-%m-%d') as iwk,
  count(*) as loan_cnt,
  round(sum(real_issue_amount)/1000.0,0) as loan_amt_k,
  count(if(t0_should_amt_1>0,1,null)) as mature_cnt,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) as t0_rate
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and issue_date >= date'2026-07-27'
group by 1 order by 1
""", "Q4 全复贷大盘 放款周 1t0%")

# 保存结果
import pickle
with open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_v53_results.pkl", "wb") as f:
    pickle.dump({"r2": r2, "r3a": r3a, "r3b": r3b, "r3c": r3c, "r4": r4}, f)
print("saved.")
