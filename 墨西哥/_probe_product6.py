# -*- coding: utf-8 -*-
"""首贷(is_reloan='new') vs 复贷('old') 放款周结构 + 7天占比，回答8/17、8/24持续高坏账原因"""
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

def _num(df):
    for c in df.columns:
        if c not in ('d','dim','m','w','tag','pn','rl','d7'): df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# 1) 首贷 vs 复贷 放款周 量 + 坏账
print("="*120)
print("【1】放款周 × is_reloan（new首贷/old复贷）量 + 1t0本金%")
sql1 = """
select date_trunc('week', date(f.release_time)) as w,
  f.is_reloan as rl,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-06-01' and date '2026-09-30'
group by 1,2 order by 1,2
"""
r = q(sql1)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    pv = r.pivot_table(index="w", columns="rl", values="issue_cnt", fill_value=0)
    pr = r.pivot_table(index="w", columns="rl", values="1t0本金%", fill_value=0)
    print("--- 放款量 ---"); print(pv.to_string())
    print("--- 1t0本金% ---"); print(pr.round(2).to_string())
    pickle.dump(r, open(OUT + r"\_probe_product6.pkl","wb"))

# 2) 首贷放款里 7天占比
print("\n" + "="*120)
print("【2】放款周 × is_reloan × 是否7天 的 1t0本金%（看首贷7天的坏账水平）")
sql2 = """
select date_trunc('week', date(f.release_time)) as w,
  f.is_reloan as rl,
  case when f.loan_cycle=7 then '7天' else '非7天' end as d7,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-07-01' and date '2026-09-30'
group by 1,2,3 order by 1,2,3
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    for rl in ['new','old']:
        sub = r[r.rl==rl]
        print(f"\n===== is_reloan={rl} =====")
        pv = sub.pivot_table(index="w", columns="d7", values="issue_cnt", fill_value=0)
        pr = sub.pivot_table(index="w", columns="d7", values="1t0本金%", fill_value=0)
        print("--- 放款量 ---"); print(pv.to_string())
        print("--- 1t0本金% ---"); print(pr.round(2).to_string())

print("\n\n完成")
