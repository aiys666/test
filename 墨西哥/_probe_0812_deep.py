# -*- coding: utf-8 -*-
"""深挖：7月首贷质量差的来源 + 复贷通过率放松验证"""
import sys, io, os, time, pickle
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
        if c not in ('d','dim','tag','month'): df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

res = {}

# 1) 首贷质量时间线：各月首贷(new)客群的首贷1t0本金%
print("="*100)
print("【1】各月首贷(new)客群 首贷1t0本金% (放款口径)")
sql1 = """
select date_trunc('month', date(f.release_time)) as m,
  count(distinct f.biz_id) as biz_cnt,
  sum(f.if_issue) as issue_cnt,
  sum(f.contract_amount) as amt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd,
  sum(f.t3_overdue_capit_1) as ovd3, sum(f.t3_should_capit_1) as shd3
from mx.wxs_application_funnel f
where f.is_reloan='new' and f.tenant='yawey'
  and date(f.release_time) between date '2026-04-01' and date '2026-08-31'
group by 1 order by 1
"""
r = q(sql1)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r)
    r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    r["1t3本金%"] = (r.ovd3/r.shd3*100).round(2)
    res["首贷质量分月"] = r
    print(r.to_string(index=False))

# 2) 7月首贷质量差的来源：按 source / app_group / loan_cycle / 金额档 / 评级
print("="*100)
print("【2】7月首贷(new) 按 source 拆 1t0本金%")
sql2 = """
select coalesce(f.source,'空') as dim,
  sum(f.if_issue) as issue_cnt, sum(f.contract_amount) as amt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='new' and f.tenant='yawey'
  and date(f.release_time) between date '2026-07-01' and date '2026-07-31'
group by 1 order by 2 desc
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["7月首贷source"] = r
    print(r.to_string(index=False))

print("="*100)
print("【3】7月首贷(new) 按 app_group 拆 1t0本金%")
sql3 = """
select coalesce(f.app_group,'空') as dim,
  sum(f.if_issue) as issue_cnt, sum(f.contract_amount) as amt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='new' and f.tenant='yawey'
  and date(f.release_time) between date '2026-07-01' and date '2026-07-31'
group by 1 order by 2 desc
"""
r = q(sql3)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["7月首贷app_group"] = r
    print(r.to_string(index=False))

print("="*100)
print("【4】7月首贷(new) 按 loan_cycle 拆 1t0本金%")
sql4 = """
select cast(f.loan_cycle as varchar) as dim,
  sum(f.if_issue) as issue_cnt, sum(f.contract_amount) as amt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='new' and f.tenant='yawey'
  and date(f.release_time) between date '2026-07-01' and date '2026-07-31'
group by 1 order by 1
"""
r = q(sql4)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["7月首贷loan_cycle"] = r
    print(r.to_string(index=False))

print("="*100)
print("【5】7月首贷(new) 按 金额档 拆 1t0本金%")
sql5 = """
select case when f.contract_amount<=500 then '小金额(<=500)'
            when f.contract_amount<=1000 then '500~1000'
            when f.contract_amount<=2000 then '1000~2000' else '>2000' end as dim,
  sum(f.if_issue) as issue_cnt, sum(f.contract_amount) as amt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='new' and f.tenant='yawey'
  and date(f.release_time) between date '2026-07-01' and date '2026-07-31'
group by 1 order by 2 desc
"""
r = q(sql5)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["7月首贷金额档"] = r
    print(r.to_string(index=False))

# 6) 首贷评级：7月 vs 6月 vs 8月 各等级首贷坏账
print("="*100)
print("【6】首贷(new) 按 首贷评级(new_grade_level) 分月 1t0本金%")
sql6 = """
select date_trunc('month', date(f.release_time)) as m,
  coalesce(cast(fl.new_grade_level as varchar),'空') as dim,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
left join mx.ys_dl_ltv_first_loan_0511 fl on cast(f.cust_id as bigint)=fl.mid and f.biz_id=fl.biz_id
where f.is_reloan='new' and f.tenant='yawey'
  and date(f.release_time) between date '2026-06-01' and date '2026-08-31'
group by 1,2 order by 1,2
"""
r = q(sql6)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["首贷评级分月"] = r
    print(r.to_string(index=False))

# 7) 复贷通过率放松验证：8/8~8/16 逐日 前置/后置/风险通过率
print("="*100)
print("【7】复贷(old) 8/8~8/16 逐日通过率")
sql7 = """
select date(f.app_time) as d,
  sum(f.if_app) as app_cnt, sum(f.if_in_sx) as in_sx, sum(f.if_sx_passed) as sx_passed,
  sum(f.if_issue) as issue_cnt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.app_time) between date '2026-08-08' and date '2026-08-16'
group by 1 order by 1
"""
r = q(sql7)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r)
    r["前置%"] = (r.in_sx/r.app_cnt*100).round(2)
    r["后置(通过->放款)"] = (r.issue_cnt/r.sx_passed).round(4)
    r["风险通过率%"] = (r["前置%"]*r["后置(通过->放款)"]).round(2)
    res["复贷通过率逐日"] = r
    print(r.to_string(index=False))

with open(os.path.join(OUT, "_probe_0812_deep.pkl"), "wb") as f:
    pickle.dump(res, f)
print("\n\n保存完成: _probe_0812_deep.pkl")
