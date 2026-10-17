# -*- coding: utf-8 -*-
"""修正版：精确结构分解 + 三维（客群×期限×评级）率矩阵"""
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

# ===== 精确结构分解 =====
r = pickle.load(open(OUT + r"\_probe_decomp.pkl","rb"))
r["rate"] = r.ovd/r.shd*100

def decomp(w0, w1):
    d0 = r[r.w==w0].copy(); d1 = r[r.w==w1].copy()
    key = ["rl","d7"]
    d0 = d0.set_index(key); d1 = d1.set_index(key)
    idx = d0.index.union(d1.index)
    d0 = d0.reindex(idx); d1 = d1.reindex(idx)
    d0["share"] = d0.shd/d0.shd.sum()
    d1["share"] = d1.shd/d1.shd.sum()
    R0 = (d0.ovd.sum()/d0.shd.sum())*100
    R1 = (d1.ovd.sum()/d1.shd.sum())*100
    rate_eff = (d0.share * (d1.rate - d0.rate)).sum()
    struct_eff = ((d1.share - d0.share) * d0.rate).sum()
    cross = ((d1.share - d0.share) * (d1.rate - d0.rate)).sum()
    return R0, R1, rate_eff, struct_eff, cross, d0, d1

print("="*120)
print("【结构分解】8/3 → 8/10 整体1t0本金% 变化")
R0,R1,re,se,cr,d0,d1 = decomp("2026-08-03","2026-08-10")
print(f"整体率 {R0:.2f} → {R1:.2f}  (Δ{R1-R0:+.2f} pp)")
print(f"  率效应(各组自身率涨)  {re:+.2f}")
print(f"  结构效应(7天占比升)  {se:+.2f}")
print(f"  交叉项                {cr:+.2f}")

print("\n各组明细（8/3 → 8/10）：")
detail = pd.DataFrame({
    "客群": ["首贷","首贷","复贷","复贷"],
    "期限": ["7天","非7天","7天","非7天"],
    "率_8/3": d0.rate.round(2).values,
    "率_8/10": d1.rate.round(2).values,
    "本金占比_8/3": (d0.share*100).round(1).values,
    "本金占比_8/10": (d1.share*100).round(1).values,
})
detail["率变动pp"] = (detail["率_8/10"] - detail["率_8/3"]).round(2)
detail["率效应贡献pp"] = (d0.share.values * (d1.rate.values - d0.rate.values)).round(2)
print(detail.to_string(index=False))

# 8/10 → 8/17, 8/17 → 8/24 也分解一下
for w0,w1 in [("2026-08-10","2026-08-17"),("2026-08-17","2026-08-24"),("2026-08-03","2026-08-24")]:
    R0,R1,re,se,cr,_,_ = decomp(w0,w1)
    print(f"\n[{w0}→{w1}] 整体 {R0:.2f}→{R1:.2f} (Δ{R1-R0:+.2f})  率效应{re:+.2f} 结构效应{se:+.2f} 交叉{cr:+.2f}")

# ===== 三维：客群×期限×评级 =====
print("\n" + "="*120)
print("【三维率矩阵】放款周 × 客群 × 期限 × 评级档（1t0本金%）")
sqlC = """
with f as (
  select f.*, date_trunc('week', date(f.release_time)) as w
  from mx.wxs_application_funnel f
  where f.tenant='yawey' and f.if_issue=1
    and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
),
yj as (
  SELECT biz_id, try_cast(android_oldcust_maincreditlevel_charge_v5_3 as integer) as gl,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
)
select cast(f.w as varchar) as w, f.is_reloan as rl,
  case when f.loan_cycle=7 then '7d' else 'n7d' end as d7,
  case when y.gl is null then '空' when y.gl<=3 then '1-3' when y.gl<=5 then '4-5' else '6-12' end as glv,
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
    pickle.dump(r, open(OUT + r"\_probe_decomp3d.pkl","wb"))

print("\n\n完成")
