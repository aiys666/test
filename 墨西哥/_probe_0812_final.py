# -*- coding: utf-8 -*-
"""最终定性：
1) 首贷月结构占比变化(8/8~8/16 逐日) —— 是否次新客/当月客占比突然升
2) 7月首贷客群 首贷时的1t0坏账 vs 现在复贷的1t0坏账 —— 首贷质量是否本来就差
3) 8月当月首贷复贷客群的通过率 —— 是否主动放量
"""
import sys, io, os, time
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
        if c not in ('d','dim'): df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# 1) 首贷月结构占比（按天，占比 = 各首贷月进件 / 全天进件）
sql1 = """
select date(f.app_time) as d,
  case when fl.ltv_month >= date '2026-06-01' then '2026-06及以后(次新)'
       when fl.ltv_month >= date '2026-03-01' then '2026-03~05'
       when fl.ltv_month >= date '2025-12-01' then '2025-12~2026-02'
       else '2025-12之前(老)' end as dim,
  sum(f.if_app) as app_cnt,
  sum(f.if_issue) as issue_cnt,
  sum(f.if_sx_passed) as sx_passed,
  sum(f.t0_overdue_capit_1) as t0_overdue_capit_1,
  sum(f.t0_should_capit_1) as t0_should_capit_1
from mx.wxs_application_funnel f
left join mx.ys_dl_ltv_first_loan_0511 fl on cast(f.cust_id as bigint) = fl.mid
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.create_time) between date '2026-08-08' and date '2026-08-16'
group by 1, 2 order by 1, 2
"""
r = q(sql1)
if isinstance(r, str):
    print("[FAIL sql1]", r[:300])
else:
    r = _num(r)
    # 占比
    tot = r.pivot_table(index="d", values="app_cnt", aggfunc="sum").rename(columns={"app_cnt":"total"})
    p = r.pivot_table(index="dim", columns="d", values="app_cnt", aggfunc="sum")
    pct = p.div(tot["total"], axis=1) * 100
    bad = r.copy(); bad["1t0本金%"] = (bad.t0_overdue_capit_1/bad.t0_should_capit_1*100).round(2)
    badp = bad.pivot_table(index="dim", columns="d", values="1t0本金%", aggfunc="mean")
    print("="*110)
    print("【首贷月结构占比% 逐日】")
    print(pct.round(1).to_string())
    print("\n【首贷月各段 1t0本金% 逐日】")
    print(badp.to_string())

# 2) 7月首贷客群：首贷时(7月) vs 复贷时(8月) 的坏账对比
print("\n" + "="*110)
print("【7月首贷客群 首贷 vs 复贷 的 1t0本金%】")
sql2 = """
select '首贷(7月)' as tag,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd,
  sum(f.if_issue) as issue_cnt, sum(f.contract_amount) as amt
from mx.wxs_application_funnel f
where f.is_reloan='new' and f.tenant='yawey'
  and date(f.release_time) between date '2026-07-01' and date '2026-07-31'
union all
select '复贷(8/8~8/16)' as tag,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd,
  sum(f.if_issue) as issue_cnt, sum(f.contract_amount) as amt
from mx.wxs_application_funnel f
left join mx.ys_dl_ltv_first_loan_0511 fl on cast(f.cust_id as bigint) = fl.mid
where f.is_reloan='old' and f.tenant='yawey'
  and fl.ltv_month = date '2026-07-01'
  and date(f.app_time) between date '2026-08-08' and date '2026-08-16'
"""
r2 = q(sql2)
if isinstance(r2, str):
    print("[FAIL sql2]", r2[:300])
else:
    r2 = _num(r2)
    r2["1t0本金%"] = (r2.ovd/r2.shd*100).round(2)
    print(r2.to_string(index=False))

# 3) 8月当月首贷客群复贷：通过率 + 评级分布（对比 8/8~8/10 vs 8/11~8/14）
print("\n" + "="*110)
print("【2026-08首贷当月复贷客群：8/8~8/10 vs 8/11~8/14 量/通过率/坏账】")
sql3 = """
select case when date(f.app_time) <= date '2026-08-10' then '8/8~8/10' else '8/11~8/14' end as tag,
  sum(f.if_app) as app_cnt, sum(f.if_issue) as issue_cnt, sum(f.if_sx_passed) as sx_passed,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
left join mx.ys_dl_ltv_first_loan_0511 fl on cast(f.cust_id as bigint) = fl.mid
where f.is_reloan='old' and f.tenant='yawey'
  and fl.ltv_month = date '2026-08-01'
  and date(f.app_time) between date '2026-08-08' and date '2026-08-14'
group by 1 order by 1
"""
r3 = q(sql3)
if isinstance(r3, str):
    print("[FAIL sql3]", r3[:300])
else:
    r3 = _num(r3)
    r3["1t0本金%"] = (r3.ovd/r3.shd*100).round(2)
    r3["放款率%"] = (r3.issue_cnt/r3.app_cnt*100).round(2)
    print(r3.to_string(index=False))
