# -*- coding: utf-8 -*-
"""根因深挖 v2：reloan_num分档修复 + 件均金额 + 流量来源(app_group)结构变化"""
import sys, io, pickle
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"
pq = PrestoQuery(); pq.login()

def q(sql, retry=4):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r):
            print(f"  [重登{i+1}]"); pq.login(); continue
        return r
    raise SystemExit(f"[失败] {r}")

def _num(df, keep=('d','dim','m','w','tag','pn','rl','d7','glv','ch','rn_g','grp','ag')):
    for c in df.columns:
        if c not in keep: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# ===== 1. 复贷·非7天 × reloan_num 分档（放款周 1t0本金%） =====
print("="*120)
print("【1】复贷·非7天 × reloan_num 分档（放款周 1t0本金%）")
sql1 = """
select date_trunc('week', date(f.release_time)) as w,
  case when f.reloan_num<=2 then '2次(首复贷)'
       when f.reloan_num<=4 then '3-4次'
       when f.reloan_num<=7 then '5-7次'
       else '8次+' end as rn_g,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1 and f.loan_cycle<>7
  and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
group by 1,2 order by 1,2
"""
r = q(sql1)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["rate"] = r.ovd/r.shd*100
    pv = r.pivot_table(index="rn_g", columns="w", values="rate")
    pc = r.pivot_table(index="rn_g", columns="w", values="cnt")
    print("--- 率% ---"); print(pv.round(1).to_string())
    print("--- 量 ---"); print(pc.to_string())

# ===== 2. 全量(含7天) × reloan_num 分档 =====
print("\n" + "="*120)
print("【2】全量复贷 × reloan_num 分档（放款周 1t0本金%）")
sql2 = """
select date_trunc('week', date(f.release_time)) as w,
  case when f.reloan_num<=2 then '2次(首复贷)'
       when f.reloan_num<=4 then '3-4次'
       when f.reloan_num<=7 then '5-7次'
       else '8次+' end as rn_g,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
group by 1,2 order by 1,2
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["rate"] = r.ovd/r.shd*100
    pv = r.pivot_table(index="rn_g", columns="w", values="rate")
    pc = r.pivot_table(index="rn_g", columns="w", values="cnt")
    print("--- 率% ---"); print(pv.round(1).to_string())
    print("--- 量 ---"); print(pc.to_string())

# ===== 3. 件均金额 + 进件量（放款周，全量复贷） =====
print("\n" + "="*120)
print("【3】件均金额 + 进件量（放款周，全量复贷）")
sql3 = """
select date_trunc('week', date(f.release_time)) as w,
  count(*) as cnt,
  sum(f.contract_amount) as contract_amt,
  sum(f.amount) as amount,
  sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-07-27' and date '2026-09-07'
group by 1 order by 1
"""
r = q(sql3)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["件均contract"] = (r.contract_amt/r.cnt).round(0)
    r["件均amount"] = (r.amount/r.cnt).round(0)
    print(r[["w","cnt","contract_amt","amount","件均contract","件均amount","shd"]].to_string(index=False))

# ===== 4. 流量来源 app_group 结构变化（放款周，全量复贷） =====
print("\n" + "="*120)
print("【4】流量来源 app_group 结构变化（放款周，全量复贷 1t0本金%）")
sql4 = """
select date_trunc('week', date(f.release_time)) as w,
  coalesce(f.app_group,'空') as ag,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
group by 1,2 order by 1,2
"""
r = q(sql4)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["rate"] = r.ovd/r.shd*100
    pv = r.pivot_table(index="ag", columns="w", values="rate")
    pc = r.pivot_table(index="ag", columns="w", values="cnt")
    print("--- 率% ---"); print(pv.round(1).to_string())
    print("--- 量 ---"); print(pc.to_string())

print("\n\n完成")
