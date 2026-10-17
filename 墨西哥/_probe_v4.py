# -*- coding: utf-8 -*-
"""复贷坏账下降根因 v4: 严格按 v3_flag 分版本重跑核心探针"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

for _l in range(1, 8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception as e:
        print(f"[login retry {_l}] {type(e).__name__}: {str(e)[:120]}")
        if _l == 7: raise
        time.sleep(15)
pd.set_option('display.max_columns', None); pd.set_option('display.width', 600)

def q(sql, tag="", show=400):
    print("="*140); print(tag)
    for a in range(1, 6):
        try:
            r = pq.query(sql); break
        except Exception as e:
            print(f"[retry {a}] {type(e).__name__}: {str(e)[:150]}")
            if a == 5: raise
            time.sleep(4 * a)
    if isinstance(r, str): print("[ERR]", r[:1500]); return None
    if r is None or len(r) == 0: print("[空]"); return None
    print(r.to_string() if len(r) <= show else r.head(show).to_string())
    print(f"[rows={len(r)}]"); return r

# Q1 分版本 × 按日 1t0率 + 笔数 => 两个版本各自坏账趋势
q("""
select app_date, v3_flag,
  sum(if(if_issue=1,1,0)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,0.0))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,0.0)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-08' and app_date <= date'2026-09-28'
group by 1,2 order by 1,2
""", "Q1 分版本×按日 1t0率(各自趋势)")

# Q2 V5_3版本内: V5_3评级段 × 两段 金额率 => 验证V5_3自身是否所有段降
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) <= 6 then '1-6'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 7 and 10 then '7-10'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 11 and 12 then '11-12'
       else '13+' end g5seg,
  sum(if(if_issue=1,1,0)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,0.0))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,0.0)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1 and v3_flag='V5_3'
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q2 V5_3版本内 评级段×两段 率(是否所有段降)")

# Q3 V6_1版本内: V6_1评级段 × 两段 金额率
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) <= 6 then '1-6'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) between 7 and 10 then '7-10'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) between 11 and 12 then '11-12'
       else '13+' end g6seg,
  sum(if(if_issue=1,1,0)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,0.0))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,0.0)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1 and v3_flag='V6_1'
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q3 V6_1版本内 评级段×两段 率")

# Q4 分版本 × 两段 × 期限 笔数 => 各版本期限迁移
q("""
select v3_flag,
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  cast(loan_cycle as int) cycle,
  sum(if(if_issue=1,1,0)) issue_cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2,3 order by 1,2,3
""", "Q4 分版本×两段×期限 笔数")

# Q5 分版本 × 按日 期限14/21笔数占比 => 期限迁移时点(分版本)
q("""
select app_date, v3_flag,
  sum(if(if_issue=1 and cast(loan_cycle as int)=7,1,0)) c7,
  sum(if(if_issue=1 and cast(loan_cycle as int)=14,1,0)) c14,
  sum(if(if_issue=1 and cast(loan_cycle as int)=21,1,0)) c21,
  sum(if(if_issue=1 and cast(loan_cycle as int)=28,1,0)) c28
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-08' and app_date <= date'2026-09-28'
group by 1,2 order by 1,2
""", "Q5 分版本×按日 期限笔数")
