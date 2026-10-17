# -*- coding: utf-8 -*-
"""修正重查：月份顺序 + 首贷评级分月"""
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

# 1) 用 date_format 输出月份字符串，确认顺序
print("="*100)
print("【1】各月首贷(new) 首贷1t0本金% (放款口径, 月份字符串)")
sql1 = """
select date_format(date(f.release_time), '%Y-%m') as m,
  count(distinct f.biz_id) as biz_cnt,
  sum(f.if_issue) as issue_cnt,
  sum(f.contract_amount) as amt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd,
  sum(f.t3_overdue_capit_1) as ovd3, sum(f.t3_should_capit_1) as shd3,
  sum(f.t7_overdue_capit_1) as ovd7, sum(f.t7_should_capit_1) as shd7
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
    r["1t7本金%"] = (r.ovd7/r.shd7*100).round(2)
    res["首贷质量分月"] = r
    print(r.to_string(index=False))

# 2) 首贷评级分月（修复 biz_id 类型）
print("="*100)
print("【6】首贷(new) 按 首贷评级(new_grade_level) 分月 1t0本金%")
sql6 = """
select date_format(date(f.release_time), '%Y-%m') as m,
  coalesce(cast(fl.new_grade_level as varchar),'空') as dim,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
left join mx.ys_dl_ltv_first_loan_0511 fl on cast(f.cust_id as bigint)=fl.mid and cast(f.biz_id as varchar)=cast(fl.biz_id as varchar)
where f.is_reloan='new' and f.tenant='yawey'
  and date(f.release_time) between date '2026-06-01' and date '2026-08-31'
group by 1,2 order by 1,2
"""
r = q(sql6)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["首贷评级分月"] = r
    p = r.pivot_table(index="dim", columns="m", values="1t0本金%", aggfunc="mean")
    print(p.to_string())
    qq = r.pivot_table(index="dim", columns="m", values="issue_cnt", aggfunc="sum")
    print("\n放款量:")
    print(qq.to_string())

# 3) 首贷 source 是否只有 ANDROID？查首贷表 register_media_source 分月
print("="*100)
print("【8】首贷(new) 按 register_media_source 分月 1t0本金%")
sql8 = """
select date_format(date(f.release_time), '%Y-%m') as m,
  coalesce(fl.register_media_source,'空') as dim,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
left join mx.ys_dl_ltv_first_loan_0511 fl on cast(f.cust_id as bigint)=fl.mid and cast(f.biz_id as varchar)=cast(fl.biz_id as varchar)
where f.is_reloan='new' and f.tenant='yawey'
  and date(f.release_time) between date '2026-06-01' and date '2026-08-31'
group by 1,2 order by 1,3 desc
"""
r = q(sql8)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["首贷媒体来源分月"] = r
    print(r.to_string(index=False))

with open(os.path.join(OUT, "_probe_0812_deep2.pkl"), "wb") as f:
    pickle.dump(res, f)
print("\n\n保存完成: _probe_0812_deep2.pkl")
