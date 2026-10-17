# -*- coding: utf-8 -*-
"""严谨归因：全客群放款周坏账率变化的结构分解 + 三维普涨检验"""
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
        if c not in ('d','dim','m','w','tag','pn','rl','d7','glv'): df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# ============ A. 全客群 × 客群 × 期限 的率与量（放款周） ============
print("="*120)
print("【A】放款周 × 客群(首贷/复贷) × 期限(7天/非7天)：量 + 应还本金 + 逾期本金")
sqlA = """
select date_trunc('week', date(f.release_time)) as w,
  f.is_reloan as rl,
  case when f.loan_cycle=7 then '7d' else 'n7d' end as d7,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_should_capit_1) as shd,
  sum(f.t0_overdue_capit_1) as ovd
from mx.wxs_application_funnel f
where f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-06-01' and date '2026-09-30'
group by 1,2,3 order by 1,2,3
"""
r = q(sqlA)
if isinstance(r, str): print("[FAIL]", r[:400]); raise SystemExit
r = _num(r); r["w"] = r["w"].astype(str).str[:10]
r["rate"] = r.ovd/r.shd*100
pickle.dump(r, open(OUT + r"\_probe_decomp.pkl","wb"))

# 打印率矩阵
for rl in ['new','old']:
    sub = r[r.rl==rl]
    pr = sub.pivot_table(index="w", columns="d7", values="rate")
    pv = sub.pivot_table(index="w", columns="d7", values="issue_cnt")
    pshd = sub.pivot_table(index="w", columns="d7", values="shd")
    print(f"\n===== {rl} 率% ====="); print(pr.round(2).to_string())
    print(f"===== {rl} 量 ====="); print(pv.to_string())
    print(f"===== {rl} 应还本金(万) ====="); print((pshd/10000).round(0).to_string())

# ============ B. 全客群整体率序列 + 结构分解 ============
print("\n" + "="*120)
print("【B】全客群整体1t0本金% + 对8/3→8/10跳升做贡献分解")
tot = r.groupby("w").agg(shd=("shd","sum"), ovd=("ovd","sum"), cnt=("issue_cnt","sum")).reset_index()
tot["rate"] = tot.ovd/tot.shd*100
print(tot.round(2).to_string(index=False))

def decomp(w0, w1, dim_col):
    """对 w0->w1 整体率变化做分解：率效应 vs 结构效应（以应还本金为权重）"""
    d0 = r[r.w==w0].copy(); d1 = r[r.w==w1].copy()
    R0 = d0.ovd.sum()/d0.shd.sum()*100
    R1 = d1.ovd.sum()/d1.shd.sum()*100
    d0["share"] = d0.shd/d0.shd.sum()
    d1["share"] = d1.shd/d1.shd.sum()
    # 率效应：结构固定在 w0，率变化
    rate_eff = (d0["share"] * (d1.set_index(dim_col)["rate"] - d0.set_index(dim_col)["rate"])).sum()
    # 结构效应：率固定在 w0，结构变化
    struct_eff = ((d1["share"] - d0["share"]) * d0.set_index(dim_col)["rate"]).sum()
    # 交叉项
    cross = ((d1["share"] - d0["share"]) * (d1.set_index(dim_col)["rate"] - d0.set_index(dim_col)["rate"])).sum()
    return R0, R1, rate_eff, struct_eff, cross

for dim in ['d7','rl']:
    R0,R1,re,se,cr = decomp("2026-08-03","2026-08-10",dim)
    print(f"\n[8/3→8/10 按{dim}分解] 整体率 {R0:.2f}→{R1:.2f} (Δ{R1-R0:+.2f})")
    print(f"  率效应 {re:+.2f}  结构效应 {se:+.2f}  交叉 {cr:+.2f}")

# ============ C. 三维普涨检验：客群×期限×评级 8/3 vs 8/10 vs 8/24 ============
print("\n" + "="*120)
print("【C】放款周 × 客群 × 期限 × 评级档 率%（普涨检验）")
sqlC = """
with f as (
  select f.*, date_trunc('week', date(f.release_time)) as w
  from mx.wxs_application_funnel f
  where f.tenant='yawey' and f.if_issue=1
    and date(f.release_time) in (date '2026-08-03', date '2026-08-10', date '2026-08-17', date '2026-08-24')
),
yj as (
  SELECT biz_id, try_cast(android_oldcust_maincreditlevel_charge_v5_3 as integer) as gl,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
)
select cast(f.w as varchar) as w, f.is_reloan as rl,
  case when f.loan_cycle=7 then '7d' else 'n7d' end as d7,
  case when y.gl is null then '空' when y.gl<=3 then '1-3级' when y.gl<=5 then '4-5级' else '6-12级' end as glv,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from f left join yj y on f.biz_id=y.biz_id and y.rn=1
group by 1,2,3,4 order by 1,2,3,4
"""
r = q(sqlC)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["rate"] = r.ovd/r.shd*100
    for w in ['2026-08-03','2026-08-10','2026-08-17','2026-08-24']:
        sub = r[r.w==w]
        pv = sub.pivot_table(index=["rl","d7"], columns="glv", values="rate")
        print(f"\n----- {w} 率%（行=客群×期限, 列=评级档） -----")
        print(pv.round(1).to_string())

print("\n\n完成")
