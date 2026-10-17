# -*- coding: utf-8 -*-
"""根因深挖 v5：临额 vs 非临额 坏账率对比（决定性验证）"""
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

def show(r, index_col, val, cnt='cnt', cols=('w',)):
    for c in r.columns:
        if c not in (index_col,)+cols: r[c] = pd.to_numeric(r[c], errors="coerce")
    r["w"] = r["w"].astype(str).str[:10]
    r["rate"] = r.ovd/r.shd*100
    pv = r.pivot_table(index=index_col, columns="w", values="rate")
    pc = r.pivot_table(index=index_col, columns="w", values=cnt)
    print("--- 率% ---"); print(pv.round(1).to_string())
    print("--- 量 ---"); print(pc.to_string())

# ===== 1. 复贷：临额 vs 非临额 坏账率（放款周） =====
print("="*120)
print("【1】复贷·临额 vs 非临额（放款周 1t0本金%）")
sql1 = """
select date_trunc('week', date(f.release_time)) as w,
  case when f.temp_grant_amount>0 then '有临额' else '无临额' end as tmp,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
group by 1,2 order by 1,2
"""
r = q(sql1)
if isinstance(r, str): print("[FAIL]", r[:400])
else: show(r, 'tmp', 'rate')

# ===== 2. 复贷·临额·非7天 vs 7天 坏账率 =====
print("\n" + "="*120)
print("【2】复贷·临额 × 7天/非7天（放款周 1t0本金%）")
sql2 = """
select date_trunc('week', date(f.release_time)) as w,
  case when f.loan_cycle=7 then '7天' else '非7天' end as d7,
  case when f.temp_grant_amount>0 then '有临额' else '无临额' end as tmp,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
group by 1,2,3 order by 1,2,3
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    for c in r.columns:
        if c not in ('w','d7','tmp'): r[c] = pd.to_numeric(r[c], errors="coerce")
    r["w"] = r["w"].astype(str).str[:10]
    r["rate"] = r.ovd/r.shd*100
    for d in ['7天','非7天']:
        sub = r[r.d7==d]
        print(f"\n### {d}")
        pv = sub.pivot_table(index="tmp", columns="w", values="rate")
        pc = sub.pivot_table(index="tmp", columns="w", values="cnt")
        print("--- 率% ---"); print(pv.round(1).to_string())
        print("--- 量 ---"); print(pc.to_string())

# ===== 3. 首复贷(reloan_num=2) × 临额 坏账率 =====
print("\n" + "="*120)
print("【3】首复贷(reloan_num=2) × 临额（放款周 1t0本金%）")
sql3 = """
select date_trunc('week', date(f.release_time)) as w,
  case when f.temp_grant_amount>0 then '有临额' else '无临额' end as tmp,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1 and f.reloan_num=2
  and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
group by 1,2 order by 1,2
"""
r = q(sql3)
if isinstance(r, str): print("[FAIL]", r[:400])
else: show(r, 'tmp', 'rate')

print("\n\n完成")
