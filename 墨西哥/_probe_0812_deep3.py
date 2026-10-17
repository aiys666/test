# -*- coding: utf-8 -*-
"""深挖第二轮：6月/8月首贷质量差的来源(loan_cycle/金额结构) + 复贷脉冲的首贷月归属"""
import sys, io, os, pickle
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
        if c not in ('d','dim','tag','m'): df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

res = {}

# Q1: 各月首贷 loan_cycle 结构占比
print("="*100)
print("【Q1】各月首贷(new) 按 loan_cycle 放款量占比%")
sql = """
select date_format(date(f.release_time), '%Y-%m') as m,
  cast(f.loan_cycle as varchar) as dim,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='new' and f.tenant='yawey'
  and date(f.release_time) between date '2026-04-01' and date '2026-08-31'
group by 1,2 order by 1,2
"""
r = q(sql)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["首贷loan_cycle分月"] = r
    p = r.pivot_table(index="dim", columns="m", values="issue_cnt", aggfunc="sum")
    pct = p.div(p.sum(axis=0), axis=1)*100
    print("放款量占比%:")
    print(pct.round(1).to_string())
    b = r.pivot_table(index="dim", columns="m", values="1t0本金%", aggfunc="mean")
    print("\n1t0本金%:")
    print(b.round(2).to_string())

# Q2: 各月首贷 金额档结构占比
print("\n" + "="*100)
print("【Q2】各月首贷(new) 按 金额档 放款量占比%")
sql = """
select date_format(date(f.release_time), '%Y-%m') as m,
  case when f.contract_amount<=500 then '<=500'
       when f.contract_amount<=1000 then '500-1000'
       when f.contract_amount<=2000 then '1000-2000' else '>2000' end as dim,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='new' and f.tenant='yawey'
  and date(f.release_time) between date '2026-04-01' and date '2026-08-31'
group by 1,2 order by 1,2
"""
r = q(sql)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["首贷金额档分月"] = r
    p = r.pivot_table(index="dim", columns="m", values="issue_cnt", aggfunc="sum")
    pct = p.div(p.sum(axis=0), axis=1)*100
    print("放款量占比%:")
    print(pct.round(1).to_string())
    b = r.pivot_table(index="dim", columns="m", values="1t0本金%", aggfunc="mean")
    print("\n1t0本金%:")
    print(b.round(2).to_string())

# Q3: 8/8~8/16 复贷客群按首贷月细分，复贷坏账+量
print("\n" + "="*100)
print("【Q3】8/8~8/16 复贷(old) 按首贷月 复贷1t0本金% + 量")
sql = """
select case when fl.ltv_month = date '2026-08-01' then '8月首贷'
            when fl.ltv_month = date '2026-07-01' then '7月首贷'
            when fl.ltv_month = date '2026-06-01' then '6月首贷'
            when fl.ltv_month = date '2026-05-01' then '5月首贷'
            when fl.ltv_month = date '2026-04-01' then '4月首贷'
            else '更早' end as dim,
  sum(f.if_app) as app_cnt,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd,
  sum(f.t3_overdue_capit_1) as ovd3, sum(f.t3_should_capit_1) as shd3
from mx.wxs_application_funnel f
left join mx.ys_dl_ltv_first_loan_0511 fl on cast(f.cust_id as bigint)=fl.mid
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.app_time) between date '2026-08-08' and date '2026-08-16'
group by 1 order by 2 desc
"""
r = q(sql)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r)
    r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    r["1t3本金%"] = (r.ovd3/r.shd3*100).round(2)
    r["量占比%"] = (r.app_cnt/r.app_cnt.sum()*100).round(1)
    res["复贷按首贷月"] = r
    print(r.to_string(index=False))

# Q4: 8/8~8/16 复贷按 首贷月 × 复贷日，定位 8/11 脉冲来自哪个首贷月
print("\n" + "="*100)
print("【Q4】复贷 按 首贷月 × 复贷日 的 1t0本金% (看8/11脉冲归属)")
sql = """
select date(f.app_time) as d,
  case when fl.ltv_month >= date '2026-07-01' then '7-8月首贷(近)'
       when fl.ltv_month >= date '2026-05-01' then '5-6月首贷(中)'
       else '4月及更早(老)' end as dim,
  sum(f.if_app) as app_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
left join mx.ys_dl_ltv_first_loan_0511 fl on cast(f.cust_id as bigint)=fl.mid
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.app_time) between date '2026-08-08' and date '2026-08-16'
group by 1,2 order by 1,2
"""
r = q(sql)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["复贷首贷月x日"] = r
    p = r.pivot_table(index="dim", columns="d", values="1t0本金%", aggfunc="mean")
    print(p.round(2).to_string())
    qq = r.pivot_table(index="dim", columns="d", values="app_cnt", aggfunc="sum")
    print("\n进件量:")
    print(qq.to_string())

with open(os.path.join(OUT, "_probe_0812_deep3.pkl"), "wb") as f:
    pickle.dump(res, f)
print("\n\n保存完成: _probe_0812_deep3.pkl")
