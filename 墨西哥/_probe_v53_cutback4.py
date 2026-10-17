# -*- coding: utf-8 -*-
"""Q9 评分分层(fd_use_creditamount_score_v1) × 策略 P2同期 — 精准收缩方案参数
Q10 各周成熟度确认(9/21/9/28周 t0成熟比例)
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

HASH = """case when from_base(substr(to_hex(sha256(to_utf8('20260811'||y.credit_no||y.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'A_V5_2'
     when from_base(substr(to_hex(sha256(to_utf8('20260811'||y.credit_no||y.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'C_V5_3'
     else 'B_switch' end"""

# Q9: P2(9/3-9/22) 全复贷放款 策略×评分档
r9 = q(f"""
select
  case when {HASH} = 'C_V5_3' then 'V5_3' else 'V5_2' end as stg,
  case when y.fd_use_creditamount_score_v1 is null then 'null'
       when y.fd_use_creditamount_score_v1 <= 0 then 'S1_低分<=0'
       when y.fd_use_creditamount_score_v1 <= 3 then 'S2_中分1-3'
       else 'S3_高分5' end as score_grp,
  count(*) as loan_cnt,
  round(sum(real_issue_amount)/1000.0,0) as loan_amt_k,
  round(avg(real_issue_amount),0) as loan_avg,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) as t0_rate,
  count(if(temp_grant_amount>0,1,null)) as temp_use_cnt,
  round(count(if(temp_grant_amount>0,1,null))*100.0/count(*),1) as temp_pct
from mx.yj_test_table_250225 y
where y.if_issue=1 and y.is_reloan='old'
  and y.app_date >= date'2026-09-03' and y.app_date < date'2026-09-22'
group by 1,2 order by 1,2
""", "Q9 P2(9/3-9/22) 策略×用信评分档: 坏账/件均/临额渗透")

# Q9b: P1(8/10-9/3) 同口径, 看B组V5_3策略时评分分层效果(与A对照)
r9b = q(f"""
select
  {HASH} as hgrp,
  case when y.fd_use_creditamount_score_v1 is null then 'null'
       when y.fd_use_creditamount_score_v1 <= 0 then 'S1_low<=0'
       when y.fd_use_creditamount_score_v1 <= 3 then 'S2_mid1-3'
       else 'S3_hi5' end as score_grp,
  count(*) as loan_cnt,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) as t0_rate,
  count(if(temp_grant_amount>0,1,null)) as temp_use_cnt,
  round(count(if(temp_grant_amount>0,1,null))*100.0/count(*),1) as temp_pct
from mx.yj_test_table_250225 y
where y.if_issue=1 and y.is_reloan='old'
  and y.app_date >= date'2026-08-10' and y.app_date < date'2026-09-03'
group by 1,2 order by 1,2
""", "Q9b P1(8/10-9/3) hash组×评分档 (A=V5_2对照, B/C=V5_3)")

# Q10: 周成熟度
r10 = q(f"""
select date_format(date_trunc('week', issue_date),'%Y-%m-%d') iwk,
  count(*) loan_cnt,
  count(if(t0_should_amt_1>0,1,null)) mature_cnt,
  round(count(if(t0_should_amt_1>0,1,null))*100.0/count(*),1) mature_pct
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old' and issue_date >= date'2026-09-07'
group by 1 order by 1
""", "Q10 各放款周t0成熟度")

import pickle
with open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_v53_results3.pkl", "wb") as f:
    pickle.dump({"r9": r9, "r9b": r9b, "r10": r10}, f)
print("saved.")
