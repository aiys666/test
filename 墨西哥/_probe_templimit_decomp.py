# -*- coding: utf-8 -*-
"""在线 vs 离线临额 坏账率精算 + 期限交叉 + 贡献分解"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, tag="", show=40):
    print("="*120)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:500]); return None
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# ===== 交叉: 临额类型 × 期限(7天/非7天) =====
sql_x = """
with tmp_evt as (
  select mid, change_event_type, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
),
evt_last as (
  select biz_id, mid, change_event_type,
    row_number() over (partition by biz_id order by create_time desc) as rn
  from (
    select f.biz_id, f.mid, e.change_event_type, e.create_time
    from mx.wxs_application_funnel f
    join tmp_evt e on f.mid = e.mid and e.create_time <= f.release_time
    where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
      and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
  ) x
)
select date_trunc('week', date(f.release_time)) as w,
  case when f.loan_cycle=7 then '7天' else '非7天' end as d7,
  case
    when el.change_event_type='C010' then '在线C010'
    when el.change_event_type in ('C013','C015') then '离线C013_15'
    else '无/未匹配' end as tl,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from mx.wxs_application_funnel f
left join evt_last el on f.biz_id = el.biz_id and el.rn=1
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
group by 1,2,3 order by 1,2,3
"""
r = q(sql_x, "临额类型 × 期限 坏账率")

# 本地精算 + 贡献分解
for c in r.columns:
    if c not in ('w','d7','tl'): r[c] = pd.to_numeric(r[c], errors="coerce")
r["w"] = r["w"].astype(str).str[:10]
r["rate"] = r.ovd/r.shd*100

w0, w1 = '2026-08-03', '2026-08-10'
d0 = r[r.w==w0].set_index(['d7','tl'])
d1 = r[r.w==w1].set_index(['d7','tl'])
S = d0.shd.sum()
R0 = d0.ovd.sum()/S*100
R1 = d1.ovd.sum()/d1.shd.sum()*100
print(f"\n整体率: {w0}={R0:.2f}%  {w1}={R1:.2f}%  Δ={R1-R0:+.2f}pp  基准本金={S/10000:.0f}万")

print("\n=== 各格 坏账率 & 量 ===")
idx = d0.index.union(d1.index)
d0 = d0.reindex(idx).fillna(0); d1 = d1.reindex(idx).fillna(0)
rows=[]
for k in idx:
    s0,o0 = d0.loc[k,'shd'], d0.loc[k,'ovd']
    s1,o1 = d1.loc[k,'shd'], d1.loc[k,'ovd']
    r0 = o0/s0*100 if s0>0 else 0
    r1 = o1/s1*100 if s1>0 else 0
    share0 = s0/S*100
    rate_eff = (r1-r0)*share0/100
    struct_eff = (s1/S - s0/S)*(r0-R0)
    rows.append([k[0],k[1],s0,s1,share0,r0,r1,rate_eff,struct_eff,rate_eff+struct_eff])
df = pd.DataFrame(rows, columns=['期限','临额类型','shd0','shd1','占比0%','率0','率1','率效应','结构效应','贡献pp'])
df = df.sort_values('贡献pp', ascending=False)
print(df.round(2).to_string(index=False))
print(f"\n合计贡献: {df['贡献pp'].sum():+.2f}pp (目标Δ={R1-R0:+.2f})")

print("\n=== 按 临额类型 汇总贡献 ===")
print(df.groupby('临额类型')[['率效应','结构效应','贡献pp']].sum().round(2).to_string())

print("\n=== 按 期限 汇总贡献 ===")
print(df.groupby('期限')[['率效应','结构效应','贡献pp']].sum().round(2).to_string())
