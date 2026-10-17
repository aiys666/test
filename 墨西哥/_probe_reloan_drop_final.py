# -*- coding: utf-8 -*-
"""复贷坏账下降根因: 最终确认 Q31/Q32/Q33 (产品首字母 shift-share)"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 500)

def q(sql, tag="", show=200):
    print("="*140); print(tag)
    for attempt in range(1, 5):
        try:
            r = pq.query(sql)
            break
        except Exception as e:
            print(f"[retry {attempt}] {type(e).__name__}: {str(e)[:200]}")
            if attempt == 4:
                raise
            import time; time.sleep(3 * attempt)
    if isinstance(r, str): print("[ERR]", r[:1800]); return None
    if r is None or len(r)==0: print("[空]"); return None
    print(r.to_string() if len(r)<=show else r.head(show).to_string())
    print(f"[rows={len(r)}]"); return r

# Q31: 产品首字母(A/B/C/E) × 两段 金额shift-share (揪根因: 产品结构 vs 产品率)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  substr(product_name_new,1,1) pclass,
  count(if(if_issue=1,1,null)) issue_cnt,
  sum(if(if_issue=1,t0_should_amt_1,null)) should_amt,
  sum(if(if_issue=1,t0_overdue_amount_1,null)) od_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q31 产品首字母×两段 金额份额+率(最终根因)")

# Q32: 产品首字母 × 按日 放款笔数+应还金额 (看A类压缩的精确时点)
q("""
select app_date,
  substr(product_name_new,1,1) pclass,
  count(if(if_issue=1,1,null)) issue_cnt,
  sum(if(if_issue=1,t0_should_amt_1,null)) should_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1,2 order by 1,2
""", "Q32 产品首字母×按日 放款笔数+应还金额(看压缩时点)")

# Q33: A类产品(A_07_01_50_00) × V6_1评级 × 两段 (A类压缩与V6_1拒尾的关系)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) <= 5 then '1-5'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) between 6 and 8 then '6-8'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) >= 9 then '9+'
       else 'null' end g6,
  count(if(if_issue=1,1,null)) issue_cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and product_name_new like 'A_%'
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q33 A类产品×V6_1评级×两段 放款笔数")
