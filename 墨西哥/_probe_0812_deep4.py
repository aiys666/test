# -*- coding: utf-8 -*-
"""最后一轮查证：复贷脉冲与 7天产品 的直接关联"""
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

# R1: 8/8~8/16 复贷 按复贷期限 loan_cycle 逐日 量占比 + 1t0本金%
print("="*100)
print("【R1】复贷 按 loan_cycle(复贷期限) 逐日 1t0本金% + 量占比")
sql = """
select date(f.app_time) as d,
  cast(f.loan_cycle as varchar) as dim,
  sum(f.if_app) as app_cnt,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.app_time) between date '2026-08-08' and date '2026-08-16'
group by 1,2 order by 1,2
"""
r = q(sql)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["复贷loan_cycle逐日"] = r
    p = r.pivot_table(index="dim", columns="d", values="app_cnt", aggfunc="sum")
    pct = p.div(p.sum(axis=0), axis=1)*100
    print("复贷进件量占比%:")
    print(pct.round(1).to_string())
    b = r.pivot_table(index="dim", columns="d", values="1t0本金%", aggfunc="mean")
    print("\n1t0本金%:")
    print(b.round(2).to_string())

# R2: 7天产品复贷客群的首贷月归属（验证"7天复贷=7-8月首贷近客群"）
print("\n" + "="*100)
print("【R2】复贷期限=7 的客群 按首贷月 分布(8/8~8/16)")
sql = """
select case when fl.ltv_month >= date '2026-07-01' then '7-8月首贷(近)'
            when fl.ltv_month >= date '2026-05-01' then '5-6月首贷(中)'
            else '4月及更早(老)' end as dim,
  sum(f.if_app) as app_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
left join mx.ys_dl_ltv_first_loan_0511 fl on cast(f.cust_id as bigint)=fl.mid
where f.is_reloan='old' and f.tenant='yawey'
  and f.loan_cycle = 7
  and date(f.app_time) between date '2026-08-08' and date '2026-08-16'
group by 1 order by 2 desc
"""
r = q(sql)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r)
    r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    r["量占比%"] = (r.app_cnt/r.app_cnt.sum()*100).round(1)
    res["复贷7天按首贷月"] = r
    print(r.to_string(index=False))

# R3: 7天产品 首贷 vs 复贷 的坏账全景（4月~8月首贷，7天产品各月坏账）
print("\n" + "="*100)
print("【R3】首贷(new) loan_cycle=7 各月 1t0/1t3/1t7本金%")
sql = """
select date_format(date(f.release_time), '%Y-%m') as m,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd0, sum(f.t0_should_capit_1) as shd0,
  sum(f.t3_overdue_capit_1) as ovd3, sum(f.t3_should_capit_1) as shd3,
  sum(f.t7_overdue_capit_1) as ovd7, sum(f.t7_should_capit_1) as shd7
from mx.wxs_application_funnel f
where f.is_reloan='new' and f.tenant='yawey' and f.loan_cycle=7
  and date(f.release_time) between date '2026-06-01' and date '2026-08-31'
group by 1 order by 1
"""
r = q(sql)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r)
    r["1t0本金%"] = (r.ovd0/r.shd0*100).round(2)
    r["1t3本金%"] = (r.ovd3/r.shd3*100).round(2)
    r["1t7本金%"] = (r.ovd7/r.shd7*100).round(2)
    res["7天首贷分月"] = r
    print(r.to_string(index=False))

# R4: 全量复贷 逐日 loan_cycle=7 的 1t0本金% 和量（直接锁定8/11脉冲）
print("\n" + "="*100)
print("【R4】复贷 loan_cycle=7 vs 其他 逐日 1t0本金%")
sql = """
select date(f.app_time) as d,
  case when f.loan_cycle=7 then '7天产品' else '非7天' end as dim,
  sum(f.if_app) as app_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.app_time) between date '2026-08-08' and date '2026-08-16'
group by 1,2 order by 1,2
"""
r = q(sql)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["复贷7天vs非7天逐日"] = r
    p = r.pivot_table(index="dim", columns="d", values="1t0本金%", aggfunc="mean")
    print(p.round(2).to_string())
    qq = r.pivot_table(index="dim", columns="d", values="app_cnt", aggfunc="sum")
    print("\n进件量:")
    print(qq.to_string())

with open(os.path.join(OUT, "_probe_0812_deep4.pkl"), "wb") as f:
    pickle.dump(res, f)
print("\n\n保存完成: _probe_0812_deep4.pkl")
