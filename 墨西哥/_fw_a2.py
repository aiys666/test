# -*- coding: utf-8 -*-
"""额度框架 A-精简: A1临额特有月度字段 + A2三阶段 + A3评分"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
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
    print("="*120); print(tag or name, flush=True)
    for i in range(retry):
        try:
            r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]", flush=True); time.sleep(10)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r)==0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]")
            r.to_csv(os.path.join(OUT, name+".csv"), index=False, encoding='utf-8-sig')
            return r
        print(f"[retry {i+1}] {r[:150]}", flush=True); time.sleep(10)
        try: pq.login()
        except Exception: pass
    return None

# A1精简: 月度临额特有字段(放款口径)
q("""
select date_format(app_date,'%Y-%m') as mth,
  count(if(temp_credit_amount_issue_tag=1,1,null)) as online_tag1_cnt,
  round(count(if(temp_credit_amount_issue_tag=1,1,null))*100.0/count(*),2) as online_tag1_pct,
  count(distinct if(temp_grant_amount>0,biz_id,null)) as temp_use_cnt,
  round(sum(temp_grant_amount/1000.0),0) as temp_use_sum_k,
  round(avg(if(temp_grant_amount>0,temp_grant_amount/1000.0,null)),1) as temp_use_avg_k
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-01' and app_date < date'2026-10-01'
group by 1 order by 1
""", "A1_online_monthly", "A1精简 月度在线临额发放/使用")

# A2: 三阶段 × flag × tag
q("""
select
  case when date(app_time) < date'2026-08-10' then 'P0_pre0810'
       when date(app_time) < date'2026-09-03' then 'P1_0810_0903'
       else 'P2_after0903' end as phase,
  coalesce(temp_credit_amount_strategy_test_flag,'no_bucket') as flag,
  case when temp_credit_amount_issue_tag=1 then 'tag1' else 'tag0' end as issue_tag,
  count(*) as loan_cnt,
  round(avg(credit_amount),0) as credit_avg,
  round(avg(real_issue_amount),0) as issue_avg,
  round(sum(real_issue_amount)/nullif(sum(credit_amount),0)*100,2) as tr_rate,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))
       /nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) as t0_rate,
  round(avg(if(temp_grant_amount!=0, temp_grant_amount/1000.0,null)),1) as temp_use_avg_k,
  count(distinct if(temp_grant_amount>0,biz_id,null)) as temp_use_cnt,
  round(sum(temp_grant_amount/1000.0),0) as temp_use_sum_k,
  round(avg(cast(fd_creditlevel_main_v4_2 as double)),2) as grade_avg
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-15' and app_date < date'2026-09-22'
group by 1,2,3 order by 1,2,3
""", "A2_online_phase_flag", "A2 在线临额三阶段×flag×tag")

# A3: 评分×类型 月度
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
