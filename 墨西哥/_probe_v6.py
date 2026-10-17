# -*- coding: utf-8 -*-
"""v6: 各评级段内部期限迁移 + 件均摊薄 (解释1-6段为何也降)"""
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
    for a in range(1, 8):
        try:
            r = pq.query(sql); break
        except Exception as e:
            print(f"[retry {a}] {type(e).__name__}: {str(e)[:120]}")
            if a == 7: raise
            time.sleep(8 * a)
    if isinstance(r, str): print("[ERR]", r[:1500]); return None
    if r is None or len(r) == 0: print("[空]"); return None
    print(r.to_string() if len(r) <= show else r.head(show).to_string())
    print(f"[rows={len(r)}]"); return r

# R1 V5_3版本 × 评级段 × 两段 × 期限 笔数
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) <= 6 then '1-6'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 7 and 10 then '7-10'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 11 and 12 then '11-12'
       else '13+' end g5seg,
  cast(loan_cycle as int) cycle,
  sum(if(if_issue=1,1,0)) issue_cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1 and v3_flag='V5_3'
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2,3 order by 2,1,3
""", "R1 V5_3×评级段×两段×期限 笔数")

# R2 V6_1版本 × 评级段 × 两段 × 期限 笔数
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) <= 6 then '1-6'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) between 7 and 10 then '7-10'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) between 11 and 12 then '11-12'
       else '13+' end g6seg,
  cast(loan_cycle as int) cycle,
  sum(if(if_issue=1,1,0)) issue_cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1 and v3_flag='V6_1'
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2,3 order by 2,1,3
""", "R2 V6_1×评级段×两段×期限 笔数")

# R3 V5_3版本 × 评级段 × 两段 件均 should/od (验证1-6段摊薄)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) <= 6 then '1-6'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 7 and 10 then '7-10'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 11 and 12 then '11-12'
       else '13+' end g5seg,
  sum(if(if_issue=1,1,0)) issue_cnt,
  round(sum(if(if_issue=1,t0_should_amt_1,0.0))/sum(if(if_issue=1,1,0)),0) should_avg,
  round(sum(if(if_issue=1,t0_overdue_amount_1,0.0))/sum(if(if_issue=1,1,0)),0) od_avg
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1 and v3_flag='V5_3'
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "R3 V5_3×评级段×两段 件均(摊薄验证)")

# R4 V6_1版本 × 评级段 × 两段 件均 should/od
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) <= 6 then '1-6'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) between 7 and 10 then '7-10'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) between 11 and 12 then '11-12'
       else '13+' end g6seg,
  sum(if(if_issue=1,1,0)) issue_cnt,
  round(sum(if(if_issue=1,t0_should_amt_1,0.0))/sum(if(if_issue=1,1,0)),0) should_avg,
  round(sum(if(if_issue=1,t0_overdue_amount_1,0.0))/sum(if(if_issue=1,1,0)),0) od_avg
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1 and v3_flag='V6_1'
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "R4 V6_1×评级段×两段 件均(摊薄验证)")
