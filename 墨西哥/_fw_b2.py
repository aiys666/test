# -*- coding: utf-8 -*-
"""B1月度重跑(20261011口径修订):
- tr_rate 改名 util_rate(额度使用率=放款/授信, 不是TR)
- 新增: 利息占比/砍头占比/息费率(含砍头)/1t0本金&总额坏账/1t7本金坏账/1t7息费坏账/TR
- TR = 息费率 - 1T7本金坏账 - 1T7息费坏账 (口径=墨西哥周报自动化.py)
- A1 补 issue_sum_k 用于计算临额使用占放款额比例
"""
import sys, io, time, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

for _i in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception:
        print("[login retry]", flush=True); time.sleep(12)
pd.set_option('display.max_columns', None); pd.set_option('display.width', 460)
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_data"

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
            if r is None or len(r)==0: print("[空]", flush=True); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True)
            r.to_csv(os.path.join(OUT, name+".csv"), index=False, encoding='utf-8-sig')
            return r
        print(f"[retry {i+1}] {r[:200]}", flush=True); time.sleep(10)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {name}", flush=True)
    return None

# ---------- B1 月度 (放款月口径, funnel) ----------
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
  -- 额度使用率 = 放款金额/授信额度 (不是TR)
  round(sum(if(if_issue=1, issue_amount, null))
       /nullif(sum(if(if_issue=1, credit_amount_sx, null)),0)*100,2) as util_rate,
  -- 收入侧: 利息占比 / 砍头占比 / 息费率(含砍头), 分母=合同金额
  round(sum(if(if_issue=1, should_interest, null))
       /nullif(sum(if(if_issue=1, contract_amount, null)),0)*100,2) as int_rate,
  round(sum(if(if_issue=1, haircut_amount, null))
       /nullif(sum(if(if_issue=1, contract_amount, null)),0)*100,2) as haircut_rate,
  round(sum(if(if_issue=1, coalesce(should_interest,0)+coalesce(haircut_amount,0), null))
       /nullif(sum(if(if_issue=1, contract_amount, null)),0)*100,2) as fee_rate,
  -- 坏账: 1t0 本金/总额双口径
  round(sum(if(if_issue=1 and t0_should_capit_1>0, t0_overdue_capit_1, null))
       /nullif(sum(if(if_issue=1 and t0_should_capit_1>0, t0_should_capit_1, null)),0)*100,2) as t0_capit_rate,
  round(sum(if(if_issue=1 and t0_should_amt_1>0, t0_overdue_amount_1, null))
       /nullif(sum(if(if_issue=1 and t0_should_amt_1>0, t0_should_amt_1, null)),0)*100,2) as t0_amt_rate,
  -- 1t7 本金坏账 + 1t7息费坏账
  round(sum(if(if_issue=1 and t7_should_capit_1>0, t7_overdue_capit_1, null))
       /nullif(sum(if(if_issue=1 and t7_should_capit_1>0, t7_should_capit_1, null)),0)*100,2) as t7_capit_rate,
  round(sum(if(if_issue=1 and t7_should_amt_4>0, t7_overdue_interest_4, null))
       /nullif(sum(if(if_issue=1 and t7_should_amt_4>0, t7_should_amt_4, null)),0)*100,2) as t7_int_rate,
  -- TR = 息费率 - 1T7本金坏账 - 1T7息费坏账 (盈利口径, 1T7需4期账龄, 7月成熟/8月部分/9月未成熟)
  round((sum(if(if_issue=1, coalesce(should_interest,0)+coalesce(haircut_amount,0), null))
        /nullif(sum(if(if_issue=1, contract_amount, null)),0)
        - sum(if(if_issue=1 and t7_should_capit_1>0, t7_overdue_capit_1, null))
        /nullif(sum(if(if_issue=1 and t7_should_capit_1>0, t7_should_capit_1, null)),0)
        - sum(if(if_issue=1 and t7_should_amt_4>0, t7_overdue_interest_4, null))
        /nullif(sum(if(if_issue=1 and t7_should_amt_4>0, t7_should_amt_4, null)),0)
        )*100, 2) as tr_rate,
  round(sum(if(if_issue=1 and t30_should_amt_1>0, t30_overdue_amount_1, null))
       /nullif(sum(if(if_issue=1 and t30_should_amt_1>0, t30_should_amt_1, null)),0)*100,2) as t30_rate,
  round(sum(if(if_issue=1 and t30_should_capit_1>0, t30_overdue_capit_1, null))
       /nullif(sum(if(if_issue=1 and t30_should_capit_1>0, t30_should_capit_1, null)),0)*100,2) as t30_capit_rate,
  round(sum(if(if_issue=1, fact_interest, null))/1000.0,0) as fact_interest_k,
  round(sum(if(if_issue=1, contract_amount, null))/1000.0,0) as contract_sum_k
from mx.wxs_application_funnel
where tenant='yawey'
  and app_time >= cast('2026-07-01 00:00:00.000' as timestamp)
  and app_time <  cast('2026-10-01 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "B1_monthly_newold", "B1 月度(额度使用率/息费/砍头/1t0双口径/1t7/TR)")

# ---------- A1 月度在线临额 (+放款总额, 算临额使用占比) ----------
q("""
select date_format(app_date,'%Y-%m') as mth,
  count(*) as loan_cnt,
  count(if(temp_credit_amount_issue_tag=1,1,null)) as online_tag1_cnt,
  round(count(if(temp_credit_amount_issue_tag=1,1,null))*100.0/count(*),2) as online_tag1_pct,
  count(distinct if(temp_grant_amount>0,biz_id,null)) as temp_use_cnt,
  round(sum(temp_grant_amount/1000.0),0) as temp_use_sum_k,
  round(avg(if(temp_grant_amount>0,temp_grant_amount/1000.0,null)),1) as temp_use_avg_k,
  round(sum(real_issue_amount)/1000.0,0) as issue_sum_k,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) as t0_rate
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-01' and app_date < date'2026-10-01'
group by 1 order by 1
""", "A1_online_monthly", "A1 月度在线临额(+放款总额)")

print("B2 DONE", flush=True)
