# -*- coding: utf-8 -*-
"""额度分析框架 脚本B(funnel单表): 大盘月度/周度 + t7/t30终损 + 首贷"""
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

# ============ B1: 月度×首复贷 供给/TR/全期数坏账 ============
q("""
select date_format(date_trunc('month', cast(app_time as timestamp)),'%Y-%m') as mth,
  is_reloan,
  count(*) as app_cnt,
  count(if(if_issue=1,1,null)) as loan_cnt,
  round(count(if(if_issue=1,1,null))*100.0/count(*),2) as pass_rate,
  round(avg(if(if_issue=1, credit_amount_sx, null)),0) as credit_avg,
  round(avg(if(if_issue=1, issue_amount, null)),0) as issue_avg,
  round(sum(if(if_issue=1, issue_amount, null))/1000.0,0) as issue_sum_k,
  round(sum(if(if_issue=1, credit_amount_sx, null))/1000.0,0) as credit_sum_k,
  round(sum(if(if_issue=1, issue_amount, null))
       /nullif(sum(if(if_issue=1, credit_amount_sx, null)),0)*100,2) as tr_rate,
  round(sum(if(if_issue=1 and t0_should_amt_1>0, t0_overdue_amount_1, null))
       /nullif(sum(if(if_issue=1 and t0_should_amt_1>0, t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(sum(if(if_issue=1 and t7_should_amt_1>0, t7_overdue_amount_1, null))
       /nullif(sum(if(if_issue=1 and t7_should_amt_1>0, t7_should_amt_1, null)),0)*100,2) as t7_rate,
  round(sum(if(if_issue=1 and t30_should_amt_1>0, t30_overdue_amount_1, null))
       /nullif(sum(if(if_issue=1 and t30_should_amt_1>0, t30_should_amt_1, null)),0)*100,2) as t30_rate,
  round(sum(if(if_issue=1 and t30_should_capit_1>0, t30_overdue_capit_1, null))
       /nullif(sum(if(if_issue=1 and t30_should_capit_1>0, t30_should_capit_1, null)),0)*100,2) as t30_capit_rate,
  round(sum(if(if_issue=1, fact_interest, null))/1000.0,0) as fact_interest_k
from mx.wxs_application_funnel
where tenant='yawey'
  and app_time >= cast('2026-07-01 00:00:00.000' as timestamp)
  and app_time <  cast('2026-10-01 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "B1_monthly_newold", "B1 月度×首复贷: TR/t0/t7/t30/息费")

# ============ B2: 进件周×首复贷 t0/t7/t30 (成熟度标注) ============
q("""
select date_format(date_trunc('week', cast(app_time as timestamp)),'%Y-%m-%d') as app_week,
  is_reloan,
  count(if(if_issue=1,1,null)) as loan_cnt,
  round(sum(if(if_issue=1 and t0_should_amt_1>0, t0_overdue_amount_1, null))
       /nullif(sum(if(if_issue=1 and t0_should_amt_1>0, t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(sum(if(if_issue=1 and t7_should_amt_1>0, t7_overdue_amount_1, null))
       /nullif(sum(if(if_issue=1 and t7_should_amt_1>0, t7_should_amt_1, null)),0)*100,2) as t7_rate,
  round(sum(if(if_issue=1 and t30_should_amt_1>0, t30_overdue_amount_1, null))
       /nullif(sum(if(if_issue=1 and t30_should_amt_1>0, t30_should_amt_1, null)),0)*100,2) as t30_rate,
  round(sum(if(if_issue=1 and t0_should_amt_1>0, t0_should_amt_1, null))/1000.0,0) as t0_should_k,
  round(sum(if(if_issue=1 and t0_should_amt_1>0, t0_overdue_amount_1, null))/1000.0,0) as t0_od_k
from mx.wxs_application_funnel
where tenant='yawey'
  and app_time >= cast('2026-07-27 00:00:00.000' as timestamp)
  and app_time <  cast('2026-10-06 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "B2_weekly_newold", "B2 进件周×首复贷: t0/t7/t30")
