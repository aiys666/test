# -*- coding: utf-8 -*-
"""根因深挖 v4：首贷时间分布(修正) + 临额发放 + grant_strategy"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, retry=4):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r):
            print(f"  [重登{i+1}]"); pq.login(); continue
        return r
    raise SystemExit(f"[失败] {r}")

# ===== 1. 首复贷客户首贷放款周分布（修正） =====
print("="*120)
print("【1】8/10周新增首复贷(reloan_num=2)客户，其首贷放款月分布")
sql1 = """
with first as (
  select cust_id, date_trunc('month', date(release_time)) as fm
  from mx.wxs_application_funnel
  where tenant='yawey' and if_issue=1 and reloan_num=1
)
select cast(fl.fm as varchar) as fm, count(*) as cnt
from mx.wxs_application_funnel f
join first fl on f.cust_id=fl.cust_id
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1 and f.reloan_num=2
  and date(f.release_time) between date '2026-08-10' and date '2026-08-16'
group by 1 order by 1
"""
r = q(sql1)
print(r if isinstance(r, str) else r.to_string(index=False))

# ===== 2. 临额发放时间线（放款周，复贷） =====
print("\n" + "="*120)
print("【2】临额 temp_grant_amount 发放（放款周，复贷）")
sql2 = """
select date_trunc('week', date(f.release_time)) as w,
  count(*) as cnt,
  sum(case when f.temp_grant_amount>0 then 1 else 0 end) as tmp_cnt,
  sum(f.temp_grant_amount) as tmp_amt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-07-27' and date '2026-09-07'
group by 1 order by 1
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    for c in r.columns:
        if c != 'w': r[c] = pd.to_numeric(r[c], errors="coerce")
    r["w"] = r["w"].astype(str).str[:10]
    r["临额笔数占比%"] = (r.tmp_cnt/r.cnt*100).round(1)
    print(r.to_string(index=False))

# ===== 3. grant_strategy 分布变化（放款周，复贷） =====
print("\n" + "="*120)
print("【3】grant_strategy 授信策略分布（放款周，复贷 1t0本金%）")
sql3 = """
select date_trunc('week', date(f.release_time)) as w,
  coalesce(f.grant_strategy,'空') as gs,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
group by 1,2 order by 1,2
"""
r = q(sql3)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    for c in r.columns:
        if c not in ('w','gs'): r[c] = pd.to_numeric(r[c], errors="coerce")
    r["w"] = r["w"].astype(str).str[:10]
    r["rate"] = r.ovd/r.shd*100
    pv = r.pivot_table(index="gs", columns="w", values="rate")
    pc = r.pivot_table(index="gs", columns="w", values="cnt")
    print("--- 率% ---"); print(pv.round(1).to_string())
    print("--- 量 ---"); print(pc.to_string())

print("\n\n完成")
