# -*- coding: utf-8 -*-
"""修正版: TR=放款金额/授信额度; V6_1档位在hash组分布; 评级画像"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 420)

def q(sql, tag="", show=150):
    print("="*130); print(tag)
    r = pq.query(sql)
    if isinstance(r, str): print("[ERR]", r[:1500]); return None
    if r is None or len(r)==0: print("[空]"); return None
    print(r.head(show).to_string() if len(r)>show else r.to_string())
    print(f"[rows={len(r)}]"); return r

HASH = """case when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'A'
     when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'C'
     else 'B' end"""

# F1: V6_1档位10/11在各hash组的分布(0922后), 确认拒尾是否均匀影响三组
q(f"""
select {HASH} hgrp,
  count(*) total,
  count(if(fd_changepro_v6_1 in (10.0,11.0),1,null)) tail_cnt,
  round(count(if(fd_changepro_v6_1 in (10.0,11.0),1,null))*100.0/count(*),2) tail_pct,
  count(if(fd_changepro_v6_1 is null,1,null)) null_cnt
from mx.yj_test_table_250225
where is_reloan='old' and app_date >= date'2026-09-15' and app_date < date'2026-09-29'
group by 1 order by 1
""", "F1 V6_1尾档(10,11)在各hash组占比(确认DID是否被V6_1污染)")

# F2: 正确TR口径 全复贷 阶段×hash组 (TR=放款金额/授信额度)
q(f"""
select
  case when app_date >= date'2026-09-03' then 'P2'
       when app_date >= date'2026-08-10' then 'P1'
       else 'P0' end as phase,
  {HASH} hgrp,
  count(*) app,
  count(if(if_issue=1,1,null)) issue,
  round(sum(if(if_issue=1,real_issue_amount,null))/1000.0,0) loan_amt_k,
  round(sum(credit_amount)/1000.0,0) credit_amt_k,
  round(sum(if(if_issue=1,real_issue_amount,null))/nullif(sum(credit_amount),0)*100,2) tr_amt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))/nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and app_date >= date'2026-07-27' and app_date < date'2026-09-22'
group by 1,2 order by 1,2
""", "F2 全复贷 阶段×hash组: TR=放款金额/授信额度 + 1t0%")

# F3: P2同期 V5_2 vs V5_3 正确TR + 坏账 + 件均 (方案参数)
q(f"""
select
  case when {HASH}='C' then 'V5_3' else 'V5_2' end stg,
  count(*) app,
  count(if(if_issue=1,1,null)) issue,
  round(sum(if(if_issue=1,real_issue_amount,null))/1000.0,0) loan_amt_k,
  round(sum(credit_amount)/1000.0,0) credit_amt_k,
  round(sum(if(if_issue=1,real_issue_amount,null))/nullif(sum(credit_amount),0)*100,2) tr_amt,
  round(avg(if(if_issue=1,real_issue_amount,null)),0) loan_avg,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))/nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate,
  count(if(if_issue=1 and temp_grant_amount>0,1,null)) temp_use,
  round(count(if(if_issue=1 and temp_grant_amount>0,1,null))*100.0/count(if(if_issue=1,1,null)),1) temp_pct
from mx.yj_test_table_250225
where is_reloan='old' and app_date >= date'2026-09-03' and app_date < date'2026-09-22'
group by 1 order by 1
""", "F3 P2同期 V5_2 vs V5_3: 正确TR/件均/坏账/临额渗透")

# F4: 发临额画像 (用 fd_creditlevel_main_v4_2 做评级)
q(f"""
select
  cast(temp_credit_amount_issue_tag as varchar) tag,
  count(*) cnt,
  round(avg(real_issue_amount),0) loan_avg,
  round(avg(temp_grant_amount)/1000.0,1) temp_avg_k,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) t0_rate,
  round(avg(cast(fd_creditlevel_main_v4_2 as double)),2) grade_v42,
  round(avg(cast(fd_creditlevel_main_v4 as double)),2) grade_v4,
  round(count(if(cast(fd_creditlevel_main_v4_2 as double) <= 5,1,null))*100.0/count(*),1) g1_5,
  round(count(if(cast(fd_creditlevel_main_v4_2 as double) between 6 and 8,1,null))*100.0/count(*),1) g6_8,
  round(count(if(cast(fd_creditlevel_main_v4_2 as double) >= 9,1,null))*100.0/count(*),1) g9p,
  round(avg(credit_amount),0) credit_avg,
  round(avg(loan_contract_amount),0) contract_avg,
  round(avg(repayment_clearing_count_tenant),1) clear_cnt,
  round(avg(fd_use_creditamount_score_v1),2) score_avg,
  round(count(if(product_name_new like '%28%',1,null))*100.0/count(*),1) p28,
  round(count(if(product_name_new like '%14%',1,null))*100.0/count(*),1) p14,
  round(count(if(product_name_new like '%7%',1,null))*100.0/count(*),1) p7
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-08-10' and app_date < date'2026-09-22'
group by 1 order by 1
""", "F4 全复贷放款(8/10-9/22) 发临额tag1 vs 未发tag0 画像(用v4_2评级)")

# F5: 发临额×评分档 坏账(控制资质后, 发与不发差异)
q(f"""
select
  cast(temp_credit_amount_issue_tag as varchar) tag,
  case when fd_use_creditamount_score_v1 <= 0 then 'S1_low'
       when fd_use_creditamount_score_v1 <= 3 then 'S2_mid'
       when fd_use_creditamount_score_v1 = 5 then 'S3_hi'
       else 'null' end sg,
  count(*) cnt,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) t0_rate,
  round(avg(cast(fd_creditlevel_main_v4_2 as double)),2) grade,
  round(avg(real_issue_amount),0) loan_avg
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-08-10' and app_date < date'2026-09-22'
group by 1,2 order by 2,1
""", "F5 发临额×评分档: 控制资质后发与不发坏账差异")

# F6: V6_1尾档(10,11)被拒的金额有多少? 评估V6_1拒尾对坏账的贡献
q(f"""
select
  case when app_date < date'2026-09-22' then 'before' else 'after' end period,
  fd_changepro_v6_1,
  count(*) app, count(if(if_issue=1,1,null)) issue,
  round(count(if(if_issue=1,1,null))*100.0/count(*),1) issue_rate
from mx.yj_test_table_250225
where is_reloan='old' and app_date >= date'2026-09-15' and app_date < date'2026-09-29'
  and fd_changepro_v6_1 in (10.0,11.0)
group by 1,2 order by 2,1
""", "F6 V6_1尾档10/11 0922前后放款率")
