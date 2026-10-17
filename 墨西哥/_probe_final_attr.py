# -*- coding: utf-8 -*-
"""最终定量收口：8/3→8/10 整体坏账率 +3.31pp 的贡献度分解（临额×期限 四象限）"""
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

sql = """
select date_trunc('week', date(f.release_time)) as w,
  case when f.loan_cycle=7 then '7天' else '非7天' end as d7,
  case when f.temp_grant_amount>0 then '有临额' else '无临额' end as tmp,
  case when f.reloan_num<=2 then '首复贷' else '老复贷' end as rn,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
group by 1,2,3,4 order by 1,2,3,4
"""
r = q(sql)
for c in r.columns:
    if c not in ('w','d7','tmp','rn'): r[c] = pd.to_numeric(r[c], errors="coerce")
r["w"] = r["w"].astype(str).str[:10]

# 只取两周
w0 = '2026-08-03'; w1 = '2026-08-10'
d0 = r[r.w==w0].set_index(['d7','tmp','rn'])
d1 = r[r.w==w1].set_index(['d7','tmp','rn'])

# 整体率
t0 = d0.summ() if False else (d0.shd.sum(), d0.ovd.sum())
t1 = (d1.shd.sum(), d1.ovd.sum())
R0 = t0[1]/t0[0]*100
R1 = t1[1]/t1[0]*100
print(f"整体1t0本金%: {w0}={R0:.2f}  {w1}={R1:.2f}  Δ={R1-R0:+.2f}pp")
print(f"应还本金(万): {w0}={t0[0]/10000:.0f}  {w1}={t1[0]/10000:.0f}")

# 四象限贡献分解
idx = d0.index.union(d1.index)
d0 = d0.reindex(idx); d1 = d1.reindex(idx)
d0[['shd','ovd']] = d0[['shd','ovd']].fillna(0)
d1[['shd','ovd']] = d1[['shd','ovd']].fillna(0)
S = t0[0]  # 基准总本金

print("\n=== 8/3→8/10 贡献度分解（基准=8/3总应还本金）===")
rows = []
for k in idx:
    s0, o0 = d0.loc[k,'shd'], d0.loc[k,'ovd']
    s1, o1 = d1.loc[k,'shd'], d1.loc[k,'ovd']
    r0 = o0/s0*100 if s0>0 else 0
    r1 = o1/s1*100 if s1>0 else 0
    share0 = s0/S*100
    # 贡献 = 率效应 + 结构效应
    rate_eff = (r1-r0)*share0/100
    struct_eff = (s1/S - s0/S)*(r0- R0)
    contrib = rate_eff + struct_eff
    rows.append([k[0], k[1], k[2], s0, s1, share0, r0, r1, rate_eff, struct_eff, contrib])

df = pd.DataFrame(rows, columns=['期限','临额','复贷','shd0','shd1','占比0%','率0','率1','率效应pp','结构效应pp','总贡献pp'])
df = df.sort_values('总贡献pp', ascending=False)
pd.set_option('display.width', 200); pd.set_option('display.max_columns', 20)
print(df.round(2).to_string(index=False))
print(f"\n合计贡献: {df['总贡献pp'].sum():+.2f}pp (应等于Δ {R1-R0:+.2f})")

# 汇总：临额维度贡献
print("\n=== 按 临额 汇总贡献 ===")
g = df.groupby('临额')[['率效应pp','结构效应pp','总贡献pp']].sum()
print(g.round(2).to_string())

# 汇总：期限维度
print("\n=== 按 期限 汇总贡献 ===")
g2 = df.groupby('期限')[['率效应pp','结构效应pp','总贡献pp']].sum()
print(g2.round(2).to_string())

# 汇总：复贷次数组
print("\n=== 按 复贷次数 汇总贡献 ===")
g3 = df.groupby('复贷')[['率效应pp','结构效应pp','总贡献pp']].sum()
print(g3.round(2).to_string())
