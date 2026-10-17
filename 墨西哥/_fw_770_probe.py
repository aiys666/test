# -*- coding: utf-8 -*-
"""核对: fact_capital 是实际还款还是预填计划? 用 10/01 那笔 + 3/12 那笔对照"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 620)

def q(sql, tag):
    print("=" * 116); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]\n", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:250]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}\n"); return None

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: print("[login retry]"); time.sleep(8)

q("""
select camera_id as biz, rid, indexs, state, should_time, fact_time,
  should_capital, fact_capital, update_time
from ods_view_presto.s02_loan_repayment
where camera_id in (1620000474884411, 1620000476104529, 1620000395926822)
order by camera_id, indexs
""", "N1 10/01笔 vs 3/12笔 还款计划对照(判 fact 是否预填)")

# N2 s02_loan 表(订单级) 看结清/放款状态
q("""
select camera_id as biz, customer_id, state, finish_time, create_time, update_time,
  contract_amount, issue_amount
from ods_view_presto.s02_loan
where camera_id in (1620000474884411, 1620000476104529, 1620000395926822, 1620000396309679)
order by camera_id
""", "N2 s02_loan 订单级状态")

print("DONE-N")
