# -*- coding: utf-8 -*-
"""额度分析框架 脚本A(yj单表): 模块1-3 复贷额度供给/TR/在线临额策略三阶段"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd, os

for _i in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(12)
pd.set_option('display.max_columns', None); pd.set_option('display.width', 460)
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_data"
os.makedirs(OUT, exist_ok=True)

def q(sql, name, tag="", retry=8):
    print("="*120); print(tag or name)
    for i in range(retry):
        try:
            r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(10)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r)==0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]")
            r.to_csv(os.path.join(OUT, name+".csv"), index=False, encoding='utf-8-sig')
            return r
        print(f"[retry {i+1}] {r[:150]}"); time.sleep(10)
        try: pq.login()
        except Exception: pass
    return None

# ============ A1: 复贷月度大盘: 供给/使用/TR/坏账/t3 ============
q("""
select date_format(app_date,'%Y-%m') as mth,
  count(*) as app_cnt,
  count(if(if_issue=1,1,null)) as loan_cnt,
  round(count(if(if_issue=1,1,null))*100.0/count(*),2) as pass_rate,
  round(avg(if(if_issue=1, credit_amount, null)),0) as credit_avg,
  round(avg(if(if_issue=1, real_issue_amount, null)),0) as issue_avg,
  round(sum(if(if_issue=1, real_issue_amount, null))/1000.0,0) as issue_sum_k,
  round(sum(if(if_issue=1, credit_amount, null))/1000.0,0) as credit_sum_k,
  round(sum(if(if_issue=1, real_issue_amount, null))
       /nullif(sum(if(if_issue=1, credit_amount, null)),0)*100,2) as tr_rate,
  round(sum(if(if_issue=1 and t0_should_amt_1>0, t0_overdue_amount_1, null))
       /nullif(sum(if(if_issue=1 and t0_should_amt_1>0, t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(sum(if(if_issue=1 and t3_should_amt_1>0, t3_overdue_amount_1, null))
       /nullif(sum(if(if_issue=1 and t3_should_amt_1>0, t3_should_amt_1, null)),0)*100,2) as t3_rate,
  round(sum(if(if_issue=1, equal_houshou_should_interest, null))/1000.0,0) as interest_k,
  round(sum(if(if_issue=1, temp_grant_amount, null))/1000.0,0) as temp_use_sum_k,
  count(if(if_issue=1 and temp_credit_amount_issue_tag=1,1,null)) as online_tag1_cnt
from mx.yj_test_table_250225
where is_reloan='old'
  and app_date >= date'2026-07-01' and app_date < date'2026-10-01'
group by 1 order by 1
""", "A1_reloan_monthly", "A1 复贷月度大盘: 供给/TR/坏账/息费")

# ============ A2: 在线临额三阶段 × flag × tag ============
q("""
select
  case when date(app_time) < date'2026-08-10' then 'P0_pre0810'
       when date(app_time) >= date'2026-08-10' and date(app_time) < date'2026-09-03' then 'P1_0810_0903'
       else 'P2_after0903' end as phase,
  coalesce(temp_credit_amount_strategy_test_flag,'no_bucket') as flag,
  case when temp_credit_amount_issue_tag=1 then 'tag1' else 'tag0' end as issue_tag,
  count(*) as loan_cnt,
  round(avg(credit_amount),0) as credit_avg,
  round(avg(real_issue_amount),0) as issue_avg,
  round(sum(real_issue_amount)/nullif(sum(credit_amount),0)*100,2) as tr_rate,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))
       /nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) as t0_rate,
  round(sum(if(t3_should_amt_1>0,t3_overdue_amount_1,null))
       /nullif(sum(if(t3_should_amt_1>0,t3_should_amt_1,null)),0)*100,2) as t3_rate,
  round(avg(if(temp_grant_amount!=0, temp_grant_amount/1000.0,null)),1) as temp_use_avg_k,
  count(distinct if(temp_grant_amount>0,biz_id,null)) as temp_use_cnt,
  round(sum(temp_grant_amount/1000.0),0) as temp_use_sum_k,
  round(sum(temp_grant_amount)/1000.0/nullif(count(if(temp_credit_amount_issue_tag=1,1,null)),0)*100,2) as temp_used_rate
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-15' and app_date < date'2026-09-22'
group by 1,2,3 order by 1,2,3
""", "A2_online_phase_flag", "A2 在线临额三阶段×flag×tag")

# ============ A3: 用信评分/类型 月度分布(放款口径) ============
q("""
select date_format(app_date,'%Y-%m') as mth,
  cast(fd_use_creditamount_score_v1 as varchar) as score_v1,
  cast(fd_use_creditamount_type as varchar) as use_type,
  count(*) as cnt,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))
       /nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) as t0_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  round(sum(temp_grant_amount/1000.0),0) as temp_sum_k
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-01' and app_date < date'2026-10-01'
group by 1,2,3 order by 1,2,3
""", "A3_score_dist", "A3 用信评分×类型 月度分布")
