# -*- coding: utf-8 -*-
"""复贷坏账下降根因 v2: 校验转产线策略 + 期限关系 + 0921单日骤降机理"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 600)

def q(sql, tag="", show=300):
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

# V1: 产品名 × loan_cycle 交叉 (转产线是否=期限变化)
q("""
select product_name_new, cast(loan_cycle as int) cycle,
  count(if(if_issue=1,1,null)) cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 1,2
""", "V1 产品名×期限 交叉(转产线是否=期限变化)")

# V2: 产品名完整 × 两段 金额 (产品级shift-share)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  product_name_new,
  count(if(if_issue=1,1,null)) issue_cnt,
  sum(if(if_issue=1,t0_should_amt_1,null)) should_amt,
  sum(if(if_issue=1,t0_overdue_amount_1,null)) od_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "V2 产品名×两段 金额(产品级shift-share)")

# V3: V5_3评级段(1-6/7-10/11-12/13+) × 关键产品 × 两段 笔数 (转产线执行范围校验)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) <= 6 then '1-6'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 7 and 10 then '7-10'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 11 and 12 then '11-12'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) >= 13 then '13+'
       else 'null' end g5seg,
  case when product_name_new='B_07_02_00_75' then 'B_07_02_75'
       when product_name_new='C_07_03_00_85' then 'C_07_03_85'
       when product_name_new='C_07_03_00_75' then 'C_07_03_75'
       when product_name_new='B_07_03_00_60' then 'B_07_03_60'
       when product_name_new='A_07_01_50_00' then 'A_07_01_50'
       else '其他' end prod,
  count(if(if_issue=1,1,null)) issue_cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2,3 order by 2,3,1
""", "V3 V5_3评级段×关键产品×两段 笔数(转产线范围校验)")

# V4: 关键产品 B_07_02_00_75 / C_07_03_00_85 / C_07_03_00_75 率 按日
q("""
select app_date,
  count(if(if_issue=1 and product_name_new='B_07_02_00_75',1,null)) b75_cnt,
  round(sum(if(if_issue=1 and product_name_new='B_07_02_00_75',t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1 and product_name_new='B_07_02_00_75',t0_should_amt_1,null)),0)*100,2) b75_rate,
  count(if(if_issue=1 and product_name_new='C_07_03_00_85',1,null)) c85_cnt,
  round(sum(if(if_issue=1 and product_name_new='C_07_03_00_85',t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1 and product_name_new='C_07_03_00_85',t0_should_amt_1,null)),0)*100,2) c85_rate,
  count(if(if_issue=1 and product_name_new='C_07_03_00_75',1,null)) c75_cnt,
  round(sum(if(if_issue=1 and product_name_new='C_07_03_00_75',t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1 and product_name_new='C_07_03_00_75',t0_should_amt_1,null)),0)*100,2) c75_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1 order by 1
""", "V4 关键产品率×按日(B75/C85/C75)")

# V5: 0921单日 od_avg 按产品 (全局口径骤降 vs 局部结构)
q("""
select app_date, product_name_new,
  count(if(if_issue=1,1,null)) cnt,
  round(sum(if(if_issue=1,t0_should_amt_1,null))/count(if(if_issue=1,1,null)),0) sh_avg,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))/count(if(if_issue=1,1,null)),0) od_avg
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-18' and app_date <= date'2026-09-23'
group by 1,2 order by 2,1
""", "V5 0921单日 od_avg 按产品(全局vs局部)")
