# -*- coding: utf-8 -*-
"""C系列: 循环贷损失率三因子拆解（评估临额效果）
损失率 = 户数损失率 × 限额控制比 × 额度使用率因子
  F1 户数损失率   = 坏账户数 / 总账户数
  F2 限额控制比   = 平均坏账限额 / 平均账户限额   (临额影响最大项)
  F3 额度使用率因子 = 坏账额度使用率 / 平均额度使用率
坏账户定义: 1T3(window1) 逾期金额>0; 限额=授信额度 credit_amount; 账户=biz_id
对照组: ① 发放临额 issue_tag 0/1  ② 使用临额 used 0/1
"""
import sys, io, time, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 500)
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_data"

def q(sql, name, tag=""):
    print("=" * 100); print(tag or name, flush=True)
    for i in range(8):
        try:
            r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(10)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]")
            r.to_csv(os.path.join(OUT, name + ".csv"), index=False, encoding='utf-8-sig')
            return r
        print(f"[retry {i+1}] {r[:200]}"); time.sleep(10)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {name}"); return None

for _ in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception:
        print("[login retry]"); time.sleep(12)

# 基础行集: 每账户(biz_id)取 授信额度/放款额/是否坏(1T0、1T3)/是否发临额/是否用临额/头中尾
BASE = """
with b as (
  select biz_id,
    cast(temp_credit_amount_issue_tag as integer) as issue_tag,
    if(temp_grant_amount>0,1,0) as used,
    case when android_oldcust_maincreditlevel_charge_v5_3 <= 5 then 'head_1_5'
         when android_oldcust_maincreditlevel_charge_v5_3 >= 6 then 'tail_6_13' else 'na' end as ht,
    if(if_in_sx=1, credit_amount, null) as credit_amount,
    contract_amount,
    if(t3_should_amt_1>0 and t3_overdue_amount_1>0, 1, 0) as bad3,
    if(t0_should_amt_1>0 and t0_overdue_amount_1>0, 1, 0) as bad0
  from mx.yj_test_table_250225
  where is_reloan='old' and if_issue=1
    and app_date >= date'2026-08-19' and app_date < date'2026-10-06'
)"""

FACTORS = """
  count(*) as n_all,
  sum({bad}) as n_bad,
  round(sum({bad})*100.0/count(*),2) as F1_hushu_pct,
  round(sum(credit_amount),0) as credit_all,
  round(sum(if({bad}=1,credit_amount,null)),0) as credit_bad,
  round(sum(if({bad}=1,credit_amount,null))/nullif(sum({bad}),0),0) as avg_credit_bad,
  round(sum(credit_amount)/nullif(count(credit_amount),0),0) as avg_credit_all,
  round((sum(if({bad}=1,credit_amount,null))/nullif(sum({bad}),0))
        /(sum(credit_amount)/nullif(count(credit_amount),0)),4) as F2_limitctrl,
  round(sum(if({bad}=1,contract_amount,0))/nullif(sum(if({bad}=1,credit_amount,null)),0),4) as ur_bad,
  round(sum(contract_amount)/nullif(sum(credit_amount),0),4) as ur_all,
  round((sum(if({bad}=1,contract_amount,0))/nullif(sum(if({bad}=1,credit_amount,null)),0))
        /(sum(contract_amount)/nullif(sum(credit_amount),0)),4) as F3_usage,
  round((sum({bad})*100.0/count(*))
      * ((sum(if({bad}=1,credit_amount,null))/nullif(sum({bad}),0))/(sum(credit_amount)/nullif(count(credit_amount),0)))
      * ((sum(if({bad}=1,contract_amount,0))/nullif(sum(if({bad}=1,credit_amount,null)),0))
         /(sum(contract_amount)/nullif(sum(credit_amount),0))),4) as loss_rate_3factor,
  round(sum(if({bad}=1,contract_amount,0))/nullif(sum(contract_amount),0),4) as loss_direct
"""

# C1: 发放临额 × 使用临额 两组（1T3 口径）
q(f"""{BASE}
select issue_tag, used,{FACTORS.format(bad='bad3')}
from b group by 1,2 order by 1,2
""", "C1_loss_issue_used", "C1 损失率三因子: 发放临额×使用临额 (坏=1T3)")

# C2: 头/中尾 × 发放×使用（1T3）
q(f"""{BASE}
select ht, issue_tag, used,{FACTORS.format(bad='bad3')}
from b group by 1,2,3 order by 1,2,3
""", "C2_loss_headtail", "C2 损失率三因子: 头/中尾 × 发放×使用 (坏=1T3)")

# C3: 1T0 口径（对照，退到最新窗口）
q(f"""{BASE}
select issue_tag, used,{FACTORS.format(bad='bad0')}
from b group by 1,2 order by 1,2
""", "C3_loss_1t0", "C3 损失率三因子(坏=1T0口径): 发放×使用")

print("C DONE")
