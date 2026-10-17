# -*- coding: utf-8 -*-
"""根因深挖：风控环节通过率时间线 + 复贷非7天低评级 × 渠道 拆解"""
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
        if c not in ('d','dim','m','w','tag','pn','rl','d7','glv','ch'): df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# ===== 1. 风控环节通过率时间线（放款周） =====
print("="*120)
print("【1】风控环节通过率（放款周，复贷进件口径 if_app=1）")
sql1 = """
select date_trunc('week', date(f.app_time)) as w,
  sum(f.if_app) as app,
  sum(f.if_in_sx) as in_sx,
  sum(f.if_sx_passed) as sx_pass,
  sum(f.if_issue) as issue,
  sum(case when f.if_in_sx=1 then f.if_sx_passed else 0 end) as sx_pass2
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.app_time) between date '2026-06-01' and date '2026-09-30'
group by 1 order by 1
"""
r = q(sql1)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["进件到SX率%"] = (r.in_sx/r.app*100).round(1)
    r["SX通过率%"] = (r.sx_pass/r.in_sx*100).round(1)
    r["进件到放款率%"] = (r.issue/r.app*100).round(1)
    print(r[["w","app","in_sx","sx_pass","issue","进件到SX率%","SX通过率%","进件到放款率%"]].to_string(index=False))

# ===== 2. 复贷非7天 6-12级 × 渠道 率（放款周） =====
print("\n" + "="*120)
print("【2】复贷·非7天·6-12级 × 渠道（放款周 1t0本金%）")
sql2 = """
with f as (
  select f.*, date_trunc('week', date(f.release_time)) as w
  from mx.wxs_application_funnel f
  where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1 and f.loan_cycle<>7
    and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
),
yj as (
  SELECT biz_id, try_cast(android_oldcust_maincreditlevel_charge_v5_3 as integer) as gl,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
)
select cast(f.w as varchar) as w, coalesce(f.channel_category,'空') as ch,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from f left join yj y on f.biz_id=y.biz_id and y.rn=1
where y.gl>=6 and y.gl<=12
group by 1,2 order by 1,2
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["rate"] = r.ovd/r.shd*100
    pv = r.pivot_table(index="ch", columns="w", values="rate")
    pc = r.pivot_table(index="ch", columns="w", values="cnt")
    print("--- 率% ---"); print(pv.round(1).to_string())
    print("--- 量 ---"); print(pc.to_string())

# ===== 3. 复贷非7天 × reloan_num 复贷次数 率（8/3 vs 8/10） =====
print("\n" + "="*120)
print("【3】复贷·非7天 × 复贷次数reloan_num（放款周 1t0本金%）")
sql3 = """
select date_trunc('week', date(f.release_time)) as w,
  case when f.reloan_num<=1 then '1次及以下' when f.reloan_num<=3 then '2-3次' when f.reloan_num<=6 then '4-6次' else '7次+' end as rn_g,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1 and f.loan_cycle<>7
  and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
group by 1,2 order by 1,2
"""
r = q(sql3)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["rate"] = r.ovd/r.shd*100
    pv = r.pivot_table(index="rn_g", columns="w", values="rate")
    pc = r.pivot_table(index="rn_g", columns="w", values="cnt")
    print("--- 率% ---"); print(pv.round(1).to_string())
    print("--- 量 ---"); print(pc.to_string())

print("\n\n完成")
