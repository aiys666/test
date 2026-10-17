# -*- coding: utf-8 -*-
"""发薪日切分(轻量单表)"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 420)

def q(sql, tag="", show=250, retry=5):
    print("="*130); print(tag)
    for i in range(retry):
        try:
            r = pq.query(sql)
        except Exception as e:
            print(f"[conn retry {i+1}] {type(e).__name__}"); time.sleep(10)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r)==0: print("[空]"); return None
            print(r.to_string() if len(r)<=show else r.head(show).to_string())
            print(f"[rows={len(r)}]"); return r
        print(f"[sql retry {i+1}] {r[:200]}"); time.sleep(10)
        try: pq.login()
        except Exception: pass
    return None

# R2: 放款日×日段×首复贷
q("""
select
  date_format(issue_date,'%Y-%m') as mth,
  case when day(issue_date) between 1 and 7 then 'd01_07'
       when day(issue_date) between 8 and 14 then 'd08_14'
       when day(issue_date) between 15 and 21 then 'd15_21'
       when day(issue_date) between 22 and 28 then 'd22_28'
       else 'd29_31' end as day_seg,
  is_reloan,
  count(*) as loan_cnt,
  round(sum(if(t0_should_amt_1>0, t0_overdue_amount_1, null))
       /nullif(sum(if(t0_should_amt_1>0, t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(sum(if(t0_should_amt_1>0, t0_should_amt_1, null))/1000.0,0) as should_k
from mx.wxs_application_funnel
where tenant='yawey' and if_issue=1
  and issue_date >= date'2026-07-01' and issue_date < date'2026-09-22'
group by 1,2,3 order by 1,3,2
""", "R2 放款日×日段×首复贷 1t0%")

# R3: 按期限细分
q("""
select
  date_format(issue_date,'%Y-%m') as mth,
  case when day(issue_date) between 1 and 7 then 'd01_07'
       when day(issue_date) between 8 and 14 then 'd08_14'
       when day(issue_date) between 15 and 21 then 'd15_21'
       when day(issue_date) between 22 and 28 then 'd22_28'
       else 'd29_31' end as day_seg,
  case when product_day <= 10 then 'short<=10d' else 'long>10d' end as pterm,
  is_reloan,
  count(*) as loan_cnt,
  round(sum(if(t0_should_amt_1>0, t0_overdue_amount_1, null))
       /nullif(sum(if(t0_should_amt_1>0, t0_should_amt_1, null)),0)*100,2) as t0_rate
from mx.wxs_application_funnel
where tenant='yawey' and if_issue=1
  and issue_date >= date'2026-07-01' and issue_date < date'2026-09-22'
group by 1,2,3,4 order by 1,4,3,2
""", "R3 放款日×日段×期限×首复贷")
