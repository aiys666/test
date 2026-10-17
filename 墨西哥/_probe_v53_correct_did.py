# -*- coding: utf-8 -*-
"""正确DID: 聚焦tag1发放临额人群 & 实际使用临额人群, B组切换 vs A组对照
   不做C010打标, 纯flag/tag/temp_grant口径"""
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
    print(r.head(show).to_string() if len(r)>show else r.to_string())
    print(f"[rows={len(r)}]"); return r

HASH = """case when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'A'
     when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'C'
     else 'B' end"""

# G1: tag1发放临额人群, 阶段×hash组: 坏账率/金额/件均
q(f"""
select
  case when app_date >= date'2026-09-03' then 'P2'
       when app_date >= date'2026-08-10' then 'P1'
       else 'P0' end phase,
  {HASH} hgrp,
  count(*) deal,
  count(if(t0_should_amt_1>0,1,null)) mature,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) t0_rate,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/1000.0,0) od_k,
  round(sum(if(t0_should_amt_1>0,t0_should_amt_1,null))/1000.0,0) should_k,
  round(sum(real_issue_amount)/1000.0,0) loan_k,
  round(avg(real_issue_amount),0) loan_avg,
  round(avg(temp_grant_amount)/1000.0,0) temp_avg,
  round(avg(cast(fd_creditlevel_main_v4_2 as double)),2) grade
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old' and temp_credit_amount_issue_tag=1
  and app_date >= date'2026-07-27' and app_date < date'2026-09-22'
group by 1,2 order by 1,2
""", "G1 tag1发放临额人群 阶段×hash组 (桶内坏账DID)")

# G2: 实际使用临额(temp>0)人群, 阶段×hash组
q(f"""
select
  case when app_date >= date'2026-09-03' then 'P2'
       when app_date >= date'2026-08-10' then 'P1'
       else 'P0' end phase,
  {HASH} hgrp,
  count(*) deal,
  count(if(t0_should_amt_1>0,1,null)) mature,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) t0_rate,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/1000.0,0) od_k,
  round(sum(if(t0_should_amt_1>0,t0_should_amt_1,null))/1000.0,0) should_k,
  round(avg(real_issue_amount),0) loan_avg,
  round(avg(temp_grant_amount)/1000.0,0) temp_avg,
  round(avg(cast(fd_creditlevel_main_v4_2 as double)),2) grade
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old' and temp_grant_amount > 0
  and app_date >= date'2026-07-27' and app_date < date'2026-09-22'
group by 1,2 order by 1,2
""", "G2 实际使用临额(temp>0)人群 阶段×hash组")

# G3: 全组(所有放款) 阶段×hash组 坏账【金额】和放款金额 — 看绝对额
q(f"""
select
  case when app_date >= date'2026-09-03' then 'P2'
       when app_date >= date'2026-08-10' then 'P1'
       else 'P0' end phase,
  {HASH} hgrp,
  count(*) deal,
  round(sum(real_issue_amount)/1000.0,0) loan_k,
  round(avg(real_issue_amount),0) loan_avg,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) t0_rate,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/1000.0,0) od_k,
  round(sum(if(t0_should_amt_1>0,t0_should_amt_1,null))/1000.0,0) should_k,
  round(count(if(temp_credit_amount_issue_tag=1,1,null))*100.0/count(*),1) tag1_pct
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-27' and app_date < date'2026-09-22'
group by 1,2 order by 1,2
""", "G3 全组放款 阶段×hash组: 坏账率/坏账金额/件均/tag1占比")

# G4: P2同期 边际客户识别 — V5_3的tag1 vs V5_2的tag0 同评级坏账(反事实)
q(f"""
select
  case when {HASH}='C' then 'V5_3' else 'V5_2' end stg,
  cast(temp_credit_amount_issue_tag as varchar) tag,
  case when cast(fd_creditlevel_main_v4_2 as double) <= 5 then 'a_g1_5'
       when cast(fd_creditlevel_main_v4_2 as double) <= 8 then 'b_g6_8'
       else 'c_g9p' end grade_grp,
  count(*) deal,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) t0_rate,
  round(avg(real_issue_amount),0) loan_avg,
  round(avg(temp_grant_amount)/1000.0,0) temp_avg
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-09-03' and app_date < date'2026-09-22'
group by 1,2,3 order by 3,1,2
""", "G4 P2 策略×tag×评级档 (边际客户反事实坏账)")
