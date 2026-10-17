# -*- coding: utf-8 -*-
"""重跑Q2 w0803对照"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

for _i in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception as e:
        print(f"[login retry {_i+1}] {type(e).__name__}"); time.sleep(15)
pd.set_option('display.max_columns', None); pd.set_option('display.width', 460)

def q(sql, tag="", show=300, retry=8):
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

w0, w1, wn = '2026-08-04','2026-08-11','w0803'
q(f"""
with evt as (
  select distinct y.biz_id
  from mx.yj_test_table_250225 y
  join ods_view_presto.s05_user_creditlimit_change_record e
    on y.mid = e.mid and e.create_time <= y.release_time
  where y.if_issue=1 and y.is_reloan='old'
    and y.app_date >= date'{w0}' and y.app_date < date'{w1}'
    and e.limit_type='TEMP' and e.change_event_type in ('C010','C013','C015')
)
select '{wn}' as awk,
  cast(y.is_loop_limit_expired as varchar) as loop_expired,
  case when cast(y.loan_cycle as double) < 5 then 'c_lt5'
       when cast(y.loan_cycle as double) < 10 then 'c_5_10'
       when cast(y.loan_cycle as double) < 20 then 'c_10_20'
       else 'c_20p' end as cyc,
  count(*) as cnt,
  round(sum(if(y.t0_should_amt_1>0, y.t0_overdue_amount_1, null))
       /nullif(sum(if(y.t0_should_amt_1>0, y.t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(avg(cast(y.curr_ovd_cnt_all as double)),2) as ovd_avg
from mx.yj_test_table_250225 y
where y.if_issue=1 and y.is_reloan='old'
  and y.app_date >= date'{w0}' and y.app_date < date'{w1}'
  and y.biz_id not in (select biz_id from evt)
  and cast(y.fd_creditlevel_main_v4_2 as double) >= 9
group by 2,3 order by 2,3
""", f"Q2 {wn} none组g9p: 循环额度过期×复贷周期")
