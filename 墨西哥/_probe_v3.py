# -*- coding: utf-8 -*-
"""复贷坏账下降根因 v3: 期限迁移时点 + 总量收缩 + 低评级段期限迁移"""
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

# T1 复贷按日 × loan_cycle 笔数 => 期限迁移时点
q("""
select app_date, cast(loan_cycle as int) cycle,
  count(if(if_issue=1,1,null)) issue_cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-08' and app_date <= date'2026-09-28'
group by 1,2 order by 1,2
""", "T1 复贷按日×期限 笔数(期限迁移时点)")

# T2 复贷按日 总笔数 + 放款率(总量收缩时点)
q("""
select app_date,
  count(*) apply_cnt,
  sum(if(if_issue=1,1,0)) issue_cnt,
  round(sum(if(if_issue=1,1.0,0.0))/count(*)*100,2) issue_rate
from mx.yj_test_table_250225
where is_reloan='old'
  and app_date >= date'2026-09-08' and app_date <= date'2026-09-28'
group by 1 order by 1
""", "T2 复贷按日 申请/放款/通过率(总量收缩时点)")

# T3 V5_3 1-6段 按日×期限 笔数 => 验证低评级段也发生期限迁移
q("""
select app_date, cast(loan_cycle as int) cycle,
  count(if(if_issue=1,1,null)) issue_cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-08' and app_date <= date'2026-09-28'
  and cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 1 and 6
group by 1,2 order by 1,2
""", "T3 V5_3 1-6段 按日×期限 笔数(低评级段期限迁移)")

# T4 各评级段 × 两段 × 期限 笔数 => 各段是否都期限拉长
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) <= 6 then '1-6'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 7 and 10 then '7-10'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 11 and 12 then '11-12'
       else '13+' end g5seg,
  cast(loan_cycle as int) cycle,
  count(if(if_issue=1,1,null)) issue_cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2,3 order by 2,1,3
""", "T4 各评级段×两段×期限 笔数(各段期限拉长验证)")
