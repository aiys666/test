# -*- coding: utf-8 -*-
"""复贷 8/10 周 1t0 逾期率上升 —— 全维度定位交付脚本
============================================================================
数据源 : mx.darren_risk_wide_table (darren 风险宽表, 445 字段, 含 tpreN_fact_amount_1)
客户群 : 复贷 (double_loan_2 <> 0), 放款周 2026-07-20 ~ 2026-08-18

指标口径 (与用户 SQL 一致):
    1t0        = 第1期 T0 逾期率
    成熟门控   : is_t0_window_1 = 1   (第1期应还日已过, snapshot 时点)
    逾期(贷款) : t0_overdue_amount_1 > 0.5
    逾期(金额) : t0_overdue_amount_1 (仅在成熟门控内求和)
    贷款口径率 = Σ逾期贷款 / Σ成熟贷款
    金额口径率 = Σt0_overdue_amount_1 / Σt0_should_amt_1
    自然回款率 = tpre2_fact_amount_1 / should_amount   (提前>=2天及以前累计实还)
    人工介入率 = (tpre0_fact_amount_1 - tpre2_fact_amount_1) / should_amount (提前1天+当天)

输出 : 同目录 Excel《复贷1t0上升定位_全维度拆解.xlsx》多sheet
       + 本脚本即跑数逻辑代码
============================================================================
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
import numpy as np

pd.set_option('display.width', 320)
pd.set_option('display.max_rows', 300)
pd.set_option('display.max_columns', 60)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_OUT = os.path.join(OUT_DIR, "复贷1t0上升定位_全维度拆解.xlsx")

# ────────────────────────── 连接 ──────────────────────────
pq = PrestoQuery(); pq.login()
def q(sql, retry=3):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r):
            print(f"  [重登{i+1}]"); pq.login(); continue
        return r
    raise SystemExit(f"[失败] {r}")

def _num(df, cols):
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out

# 放款周列表 (周一起)
WEEKS = ["2026-07-20", "2026-07-27", "2026-08-03", "2026-08-10", "2026-08-17"]
BASE = "2026-08-03"   # 基期周
CUR  = "2026-08-10"   # 上升周

# ────────────────────────── 1. 周度总览 ──────────────────────────
print("=" * 110)
print("[1/9] 周度总览 (贷款口径 + 金额口径 + 自然/人工回款)")
S1 = """
select date_format(date_trunc('week', date(release_time)), '%Y-%m-%d') as wk,
       count(distinct camera_id) as loans,
       count(if(should_amount is not null, camera_id, null)) as should_cnt,
       sum(if(is_t0_window_1=1, 1, 0)) as mt,
       sum(if(is_t0_window_1=1 and is_t0_overdue_1=1, 1, 0)) as ot,
       sum(if(is_t0_window_1=1, t0_should_amt_1, 0)) as mt_s,
       sum(if(is_t0_window_1=1 and is_t0_overdue_1=1, t0_overdue_amount_1, 0)) as ot_s,
       sum(if(is_t0_window_1=1, should_amount, 0)) as should_s,
       sum(if(is_t0_window_1=1, tpre2_fact_amount_1, 0)) as nat_s,
       sum(if(is_t0_window_1=1, tpre0_fact_amount_1, 0)) as tpre0_s
from mx.darren_risk_wide_table
where double_loan_2 <> 0
  and date(release_time) >= date '2026-07-20' and date(release_time) < date '2026-08-18'
group by 1 order by 1
"""
d1 = _num(q(S1), ["loans","should_cnt","mt","ot","mt_s","ot_s","should_s","nat_s","tpre0_s"])
d1["贷款口径1t0%"] = (d1["ot"]/d1["mt"]*100).round(2)
d1["金额口径1t0%"] = (d1["ot_s"]/d1["mt_s"]*100).round(2)
d1["自然回款%"] = (d1["nat_s"]/d1["should_s"]*100).round(2)
d1["人工介入%"] = ((d1["tpre0_s"]-d1["nat_s"])/d1["should_s"]*100).round(2)
print(d1[["wk","loans","should_cnt","mt","ot","贷款口径1t0%","金额口径1t0%","自然回款%","人工介入%"]].to_string(index=False))

# ────────────────────────── 2. 维度 shift-share 拆解 ──────────────────────────
# 说明: darren 表 reloan_num 字段为空, 复贷期数维度改用 funnel 表(两表贷款口径已验证一致)
DIMS = {
    "产品 product_name":       "product_name",
    "应用分组 app_group":      "app_group",
    "渠道 category":           "channel_category",
    "媒体源 new_media_source": "new_media_source",
    "期限 loan_cycle":         "cast(loan_cycle as varchar)",
    "复贷期数 reloan_num":     "__FUNNEL__",
    "金额段 contract_amount":  "case when contract_amount<500 then 'L_lt500' when contract_amount<1000 then 'L_500_1k' when contract_amount<2000 then 'L_1k_2k' when contract_amount<5000 then 'L_2k_5k' else 'L_ge5k' end",
    "T0应还段 t0_should_amt":  "case when t0_should_amt_1<500 then 'T0_lt500' when t0_should_amt_1<1000 then 'T0_500_1k' when t0_should_amt_1<2000 then 'T0_1k_2k' when t0_should_amt_1<5000 then 'T0_2k_5k' else 'T0_ge5k' end",
    "评分 grant_score":        "case when grant_score<50 then 'S_lt50' when grant_score<60 then 'S_50_60' when grant_score<70 then 'S_60_70' when grant_score<80 then 'S_70_80' when grant_score<90 then 'S_80_90' else 'S_ge90' end",
    "放款策略 grant_strategy": "grant_strategy",
    "产品等级 product_level":   "product_level",
    "风险等级 risk_level":      "risk_level",
}
FUNNEL_DIM = {
    "复贷期数 reloan_num": ("case when reloan_num=2 then '2贷' when reloan_num=3 then '3贷' when reloan_num<=5 then '4-5贷' when reloan_num<=9 then '6-9贷' else '10+贷' end", "mx.wxs_application_funnel", "is_reloan='old'"),
}

def dim_sql(expr, table="mx.darren_risk_wide_table", where="double_loan_2 <> 0"):
    return f"""
select date_format(date_trunc('week', date(release_time)), '%Y-%m-%d') as wk,
       {expr} as dim,
       count(distinct camera_id) as loans,
       sum(if(is_t0_window_1=1, 1, 0)) as mt,
       sum(if(is_t0_window_1=1 and is_t0_overdue_1=1, 1, 0)) as ot,
       sum(if(is_t0_window_1=1, t0_should_amt_1, 0)) as mt_s,
       sum(if(is_t0_window_1=1 and is_t0_overdue_1=1, t0_overdue_amount_1, 0)) as ot_s
from {table}
where {where}
  and date(release_time) >= date '2026-07-20' and date(release_time) < date '2026-08-18'
group by 1, 2
"""

print("=" * 110)
print("[2/9] 维度 shift-share 拆解 (贷款口径, 基期 8/03 -> 8/10)")
dim_data = {}
for name, expr in DIMS.items():
    if name in FUNNEL_DIM:
        e, tbl, whr = FUNNEL_DIM[name]
        d = _num(q(dim_sql(e, table=tbl, where=whr)), ["loans","mt","ot","mt_s","ot_s"])
    else:
        d = _num(q(dim_sql(expr)), ["loans","mt","ot","mt_s","ot_s"])
    dim_data[name] = d

def shift_share(df, base_wk=BASE, curr_wk=CUR, amount=False):
    b = df[df["wk"]==base_wk].copy()
    c = df[df["wk"]==curr_wk].copy()
    if amount:
        b["rate"] = b["ot_s"]/b["mt_s"]; c["rate"] = c["ot_s"]/c["mt_s"]
        b["w"] = b["mt_s"]; c["w"] = c["mt_s"]
    else:
        b["rate"] = b["ot"]/b["mt"]; c["rate"] = c["ot"]/c["mt"]
        b["w"] = b["mt"]; c["w"] = c["mt"]
    b["share"] = b["w"]/b["w"].sum(); c["share"] = c["w"]/c["w"].sum()
    m = b.merge(c, on="dim", how="outer", suffixes=("_b","_c"))
    m["share_b"] = m["share_b"].fillna(0); m["share_c"] = m["share_c"].fillna(0)
    m["rate_b"]  = m["rate_b"].fillna(0);  m["rate_c"]  = m["rate_c"].fillna(0)
    m["mix"]      = (m["share_c"]-m["share_b"])*m["rate_b"]*100
    m["rate_eff"] = m["share_c"]*(m["rate_c"]-m["rate_b"])*100
    m["contrib"]  = m["mix"]+m["rate_eff"]
    tb = b["ot"].sum()/b["mt"].sum()*100 if not amount else b["ot_s"].sum()/b["mt_s"].sum()*100
    tc = c["ot"].sum()/c["mt"].sum()*100 if not amount else c["ot_s"].sum()/c["mt_s"].sum()*100
    return m.sort_values("contrib", ascending=False), tb, tc

ss_results = {}
print(f"\n{'维度':<26}{'总率8/03->8/10':<20}{'Δpp':<8}{'Σmix+Σrate':<10}  最大贡献切片(contrib)")
for name in DIMS:
    m, tb, tc = shift_share(dim_data[name])
    tot = round(m["mix"].sum()+m["rate_eff"].sum(), 3)
    top = m.iloc[0]
    ss_results[name] = (m, tb, tc)
    print(f"{name:<26}{tb:.2f}% -> {tc:.2f}%   {tc-tb:+.2f}   {tot:+.3f}      {top['dim']}({top['contrib']:+.3f}pp)")

# ────────────────────────── 3. 结构反事实 ──────────────────────────
print("=" * 110)
print("[3/9] 产品维度 结构反事实 (份额固定 vs 率固定, 贷款口径)")
dprod = dim_data["产品 product_name"]
base = dprod[dprod["wk"]==BASE].set_index("dim")
print("  各周: 实际率 / 结构固定(份额停8/03) / 产品率固定(率停8/03)")
for wk in WEEKS:
    cur = dprod[dprod["wk"]==wk]
    tot = cur["mt"].sum()
    if tot == 0: continue
    act = cur["ot"].sum()/tot*100
    m = cur.set_index("dim").reindex(base.index).fillna(0)
    cf  = (base["mt"]/base["mt"].sum() * m["ot"]/m["mt"].replace(0,np.nan)).sum()*100
    cf2 = (m["mt"]/m["mt"].sum() * base["ot"]/base["mt"]).sum()*100
    print(f"  {wk}: 实际 {act:.2f}% | 结构固定 {cf:.2f}% | 率固定 {cf2:.2f}%")

# ────────────────────────── 4. 交叉验证 ──────────────────────────
print("=" * 110)
print("[4/9] 交叉验证: 产品×app / 产品×复贷期数 / 金额段×产品 (8/03 vs 8/10)")
S4a = """
select date_format(date_trunc('week', date(release_time)), '%Y-%m-%d') as wk,
       product_name, app_group,
       count(distinct camera_id) as loans,
       sum(if(is_t0_window_1=1, 1, 0)) as mt,
       sum(if(is_t0_window_1=1 and is_t0_overdue_1=1, 1, 0)) as ot
from mx.darren_risk_wide_table
where double_loan_2 <> 0
  and date(release_time) >= date '2026-08-03' and date(release_time) < date '2026-08-18'
group by 1,2,3 order by 1,2
"""
S4b = """
select date_format(date_trunc('week', date(release_time)), '%Y-%m-%d') as wk,
       product_name, cast(reloan_num as varchar) as rn,
       count(distinct camera_id) as loans,
       sum(if(is_t0_window_1=1, 1, 0)) as mt,
       sum(if(is_t0_window_1=1 and is_t0_overdue_1=1, 1, 0)) as ot
from mx.darren_risk_wide_table
where double_loan_2 <> 0
  and date(release_time) >= date '2026-08-03' and date(release_time) < date '2026-08-18'
group by 1,2,3 order by 1,2
"""
S4c = """
select date_format(date_trunc('week', date(release_time)), '%Y-%m-%d') as wk,
       case when contract_amount<500 then 'lt500' when contract_amount<1000 then '500_1k'
            when contract_amount<2000 then '1k_2k' else 'ge2k' end as amt,
       product_name,
       count(distinct camera_id) as loans,
       sum(if(is_t0_window_1=1, 1, 0)) as mt,
       sum(if(is_t0_window_1=1 and is_t0_overdue_1=1, 1, 0)) as ot
from mx.darren_risk_wide_table
where double_loan_2 <> 0
  and date(release_time) >= date '2026-08-03' and date(release_time) < date '2026-08-18'
group by 1,2,3 order by 1,2
"""
x4a = _num(q(S4a), ["loans","mt","ot"]); x4a["率%"]=(x4a["ot"]/x4a["mt"]*100).round(2)
x4b = _num(q(S4b), ["loans","mt","ot"]); x4b["率%"]=(x4b["ot"]/x4b["mt"]*100).round(2)
x4c = _num(q(S4c), ["loans","mt","ot"]); x4c["率%"]=(x4c["ot"]/x4c["mt"]*100).round(2)
print("  产品×app 主要行:")
p4a = x4a.pivot_table(index="product_name", columns="wk", values="率%")
print(p4a.round(2).to_string())

# ────────────────────────── 5. 逐日 1t0 ──────────────────────────
print("=" * 110)
print("[5/9] 逐日 1t0 (贷款口径)")
S5 = """
select date(release_time) as d,
       count(distinct camera_id) as loans,
       sum(if(is_t0_window_1=1, 1, 0)) as mt,
       sum(if(is_t0_window_1=1 and is_t0_overdue_1=1, 1, 0)) as ot
from mx.darren_risk_wide_table
where double_loan_2 <> 0
  and date(release_time) >= date '2026-07-27' and date(release_time) < date '2026-08-18'
group by 1 order by 1
"""
d5 = _num(q(S5), ["loans","mt","ot"]); d5["率%"]=(d5["ot"]/d5["mt"]*100).round(2)
print(d5.to_string(index=False))

# ────────────────────────── 6. 还款节奏 按放款周 ──────────────────────────
print("=" * 110)
print("[6/9] 还款节奏: 提前>=3d/2d/1d/当天/T0逾期 (金额占比, 分母=should_amount)")
S6 = """
select date_format(date_trunc('week', date(release_time)), '%Y-%m-%d') as wk,
       count(distinct camera_id) as loans,
       sum(if(is_t0_window_1=1, should_amount, 0)) as should_s,
       sum(if(is_t0_window_1=1, tpre3_fact_amount_1, 0)) as pre3,
       sum(if(is_t0_window_1=1, tpre2_fact_amount_1, 0)) as pre2,
       sum(if(is_t0_window_1=1, tpre1_fact_amount_1, 0)) as pre1,
       sum(if(is_t0_window_1=1, tpre0_fact_amount_1, 0)) as pre0,
       sum(if(is_t0_window_1=1, t0_overdue_amount_1, 0)) as ovd,
       sum(if(is_t0_window_1=1, t0_should_amt_1, 0)) as t0s
from mx.darren_risk_wide_table
where double_loan_2 <> 0
  and date(release_time) >= date '2026-07-20' and date(release_time) < date '2026-08-18'
group by 1 order by 1
"""
d6 = _num(q(S6), ["loans","should_s","pre3","pre2","pre1","pre0","ovd","t0s"])
d6["预3d%"]=(d6["pre3"]/d6["should_s"]*100).round(2)
d6["预2d%"]=((d6["pre2"]-d6["pre3"])/d6["should_s"]*100).round(2)
d6["预1d%"]=((d6["pre1"]-d6["pre2"])/d6["should_s"]*100).round(2)
d6["当天%"]=((d6["pre0"]-d6["pre1"])/d6["should_s"]*100).round(2)
d6["T0逾%"]=(d6["ovd"]/d6["should_s"]*100).round(2)
d6["自然回款%"]=(d6["pre2"]/d6["should_s"]*100).round(2)
d6["人工介入%"]=((d6["pre0"]-d6["pre2"])/d6["should_s"]*100).round(2)
print(d6[["wk","loans","预3d%","预2d%","预1d%","当天%","T0逾%","自然回款%","人工介入%"]].to_string(index=False))

# ────────────────────────── 7. 还款节奏 按期限 ──────────────────────────
print("=" * 110)
print("[7/9] 还款节奏 × 期限 (8/03 vs 8/10)")
S7 = """
select date_format(date_trunc('week', date(release_time)), '%Y-%m-%d') as wk,
       cast(loan_cycle as varchar) as term,
       count(distinct camera_id) as loans,
       sum(if(is_t0_window_1=1, should_amount, 0)) as should_s,
       sum(if(is_t0_window_1=1, tpre3_fact_amount_1, 0)) as pre3,
       sum(if(is_t0_window_1=1, tpre2_fact_amount_1, 0)) as pre2,
       sum(if(is_t0_window_1=1, tpre1_fact_amount_1, 0)) as pre1,
       sum(if(is_t0_window_1=1, tpre0_fact_amount_1, 0)) as pre0,
       sum(if(is_t0_window_1=1, t0_overdue_amount_1, 0)) as ovd,
       sum(if(is_t0_window_1=1, t0_should_amt_1, 0)) as t0s
from mx.darren_risk_wide_table
where double_loan_2 <> 0
  and date(release_time) >= date '2026-07-20' and date(release_time) < date '2026-08-18'
group by 1,2 order by 1,2
"""
d7 = _num(q(S7), ["loans","should_s","pre3","pre2","pre1","pre0","ovd","t0s"])
d7["预3d%"]=(d7["pre3"]/d7["should_s"]*100).round(2)
d7["预2d%"]=((d7["pre2"]-d7["pre3"])/d7["should_s"]*100).round(2)
d7["预1d%"]=((d7["pre1"]-d7["pre2"])/d7["should_s"]*100).round(2)
d7["当天%"]=((d7["pre0"]-d7["pre1"])/d7["should_s"]*100).round(2)
d7["T0逾%"]=(d7["ovd"]/d7["should_s"]*100).round(2)
for t in sorted(d7["term"].unique(), key=lambda x:int(x)):
    sub = d7[d7["term"]==t]
    sub = sub[sub["wk"].isin([BASE, CUR, "2026-08-17"])]
    print(f"  --- 期限 {t}天 ---")
    print(sub[["wk","loans","预3d%","预2d%","预1d%","当天%","T0逾%"]].to_string(index=False))

# ────────────────────────── 8. 补还率 T0->T1/T2/T3 ──────────────────────────
print("=" * 110)
print("[8/9] 逾期补还率 (7/14天产品, 金额; 预提醒弱则补还率高)")
S8 = """
select date_format(date_trunc('week', date(release_time)), '%Y-%m-%d') as wk,
       cast(loan_cycle as varchar) as term,
       count(distinct camera_id) as loans,
       sum(if(is_t0_window_1=1, t0_overdue_amount_1, 0)) as ovd0,
       sum(if(is_t1_window_1=1, t1_overdue_amount_1, 0)) as ovd1,
       sum(if(is_t2_window_1=1, t2_overdue_amount_1, 0)) as ovd2,
       sum(if(is_t3_window_1=1, t3_overdue_amount_1, 0)) as ovd3,
       sum(if(is_t7_window_1=1, t7_overdue_amount_1, 0)) as ovd7,
       sum(if(is_t0_window_1=1, t0_should_amt_1, 0)) as t0s
from mx.darren_risk_wide_table
where double_loan_2 <> 0
  and date(release_time) >= date '2026-07-20' and date(release_time) < date '2026-08-18'
  and loan_cycle in (7,14)
group by 1,2 order by 1,2
"""
d8 = _num(q(S8), ["loans","ovd0","ovd1","ovd2","ovd3","ovd7","t0s"])
d8["T0逾%"]=(d8["ovd0"]/d8["t0s"]*100).round(2)
for nn, col in [("T1","ovd1"),("T2","ovd2"),("T3","ovd3"),("T7","ovd7")]:
    d8[f"{nn}补%"]=((1-d8[col]/d8["ovd0"])*100).round(2)
print(d8[["wk","term","loans","T0逾%","T1补%","T2补%","T3补%","T7补%"]].to_string(index=False))

# ────────────────────────── 9. 应还日周 还款节奏 ──────────────────────────
print("=" * 110)
print("[9/9] 应还日周(should_time) 还款节奏")
S9 = """
select date_format(date_trunc('week', date(should_time)), '%Y-%m-%d') as duwk,
       count(distinct camera_id) as loans,
       sum(if(is_t0_window_1=1, should_amount, 0)) as should_s,
       sum(if(is_t0_window_1=1, tpre3_fact_amount_1, 0)) as pre3,
       sum(if(is_t0_window_1=1, tpre2_fact_amount_1, 0)) as pre2,
       sum(if(is_t0_window_1=1, tpre1_fact_amount_1, 0)) as pre1,
       sum(if(is_t0_window_1=1, tpre0_fact_amount_1, 0)) as pre0,
       sum(if(is_t0_window_1=1, t0_overdue_amount_1, 0)) as ovd,
       sum(if(is_t0_window_1=1, t0_should_amt_1, 0)) as t0s
from mx.darren_risk_wide_table
where double_loan_2 <> 0
  and date(release_time) >= date '2026-07-01' and date(release_time) < date '2026-08-25'
group by 1 order by 1
"""
d9 = _num(q(S9), ["loans","should_s","pre3","pre2","pre1","pre0","ovd","t0s"])
d9["预3d%"]=(d9["pre3"]/d9["should_s"]*100).round(2)
d9["预2d%"]=((d9["pre2"]-d9["pre3"])/d9["should_s"]*100).round(2)
d9["预1d%"]=((d9["pre1"]-d9["pre2"])/d9["should_s"]*100).round(2)
d9["当天%"]=((d9["pre0"]-d9["pre1"])/d9["should_s"]*100).round(2)
d9["T0逾%"]=(d9["ovd"]/d9["should_s"]*100).round(2)
print(d9[["duwk","loans","预3d%","预2d%","预1d%","当天%","T0逾%"]].to_string(index=False))

# ═══════════════════════════ 导出 Excel ═══════════════════════════
print("=" * 110)
print("导出 Excel ...")
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()
thin = Side(style="thin", color="DDDDDD")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
hdr_fill = PatternFill("solid", fgColor="2F5597")
hdr_font = Font(color="FFFFFF", bold=True)
warn_fill = PatternFill("solid", fgColor="FFF2CC")
up_fill   = PatternFill("solid", fgColor="FCE4EC")

def sheet_from_df(ws, df, title=None, pct_cols=None, up_cols=None, money_cols=None):
    pct_cols = pct_cols or []; up_cols = up_cols or []; money_cols = money_cols or []
    r0 = 1
    if title:
        ws.cell(1,1,title).font = Font(bold=True, size=12)
        r0 = 2
    if df is None or len(df)==0:
        return
    cols = list(df.columns)
    for j,c in enumerate(cols,1):
        cell = ws.cell(r0, j, c); cell.fill=hdr_fill; cell.font=hdr_font; cell.border=border
        cell.alignment=Alignment(horizontal="center")
    for i,row in df.iterrows():
        for j,c in enumerate(cols,1):
            v = row[c]
            if c in money_cols and pd.notna(v):
                v = round(float(v),0)
            if c in pct_cols and pd.notna(v):
                v = float(v)
            cell = ws.cell(r0+1+i, j, v)
            cell.border=border
            if c in pct_cols and pd.notna(v):
                cell.number_format="0.00"
            if c in money_cols and pd.notna(v):
                cell.number_format="#,##0"
            if c in up_cols and pd.notna(v) and v>0:
                cell.fill = up_fill
    for j,c in enumerate(cols,1):
        L = get_column_letter(j)
        ws.column_dimensions[L].width = max(9, min(28, len(str(c))*2+2))
    ws.freeze_panes = ws.cell(r0+1, 1)

ws1 = wb.active; ws1.title = "00_口径说明"
notes = [
    ["复贷 8/10 周 1t0 逾期率上升 —— 全维度定位分析 (数据源: mx.darren_risk_wide_table)"],
    [""],
    ["客户群"] + ["复贷 double_loan_2<>0, 放款周 2026-07-20~08-18"],
    ["1t0 定义"] + ["第1期 T0 逾期率; 成熟门控 is_t0_window_1=1; 逾期(贷款) is_t0_overdue_1=1 (darren表flag口径, 与funnel表31.86%一致)"],
    ["贷款口径率"] + ["Σ逾期贷款 / Σ成熟贷款 (is_t0_window_1=1 内)"],
    ["金额口径率"] + ["Σt0_overdue_amount_1 / Σt0_should_amt_1 (is_t0_window_1=1 内)"],
    ["自然回款率"] + ["tpre2_fact_amount_1/should_amount (应还日前>=2天及以前累计实还)"],
    ["人工介入率"] + ["(tpre0_fact_amount_1-tpre2_fact_amount_1)/should_amount (提前1天+当天)"],
    ["还款节奏差分"] + ["提前>=3天=tpre3; 提前2天=tpre2-tpre3; 提前1天=tpre1-tpre2; 当天=tpre0-tpre1"],
    ["补还率"] + ["1 - tN_overdue_amount_1/t0_overdue_amount_1, 反映T0逾期后是否快速补还"],
    ["基期周"] + ["2026-08-03 (上升前基线); 上升周=2026-08-10; 后续=2026-08-17"],
    ["核心结论"] + ["约99%上升来自同类产品内FPD恶化(结构反事实), 8/12启动, 全产品/金额/期数广谱上升"],
    [""],
    ["关键证据"] + ["① 结构固定=31.86%≈实际31.88% → 非结构混入; ② 还款节奏: 当天还款占比反而下降(12.84→11.91)"],
    [""] + ["③ 补还率下降(14天T1补还13.02→10.09) → 非预提醒弱化/遗忘, 是真实还款能力/意愿恶化"],
    [""],
    ["维度可用性"] + ["复贷期数: darren表reloan_num为空, 改用funnel表(两表贷款口径一致29.51→31.86); 2贷贡献+1.30pp"],
    [""] + ["评分/风险等级: 复贷客群评分全部≥90、风险等级全部A → 无区分度(佐证非客群结构变化)"],
    [""] + ["放款策略: darren表字段为空; 渠道99.9% organic; 通过率100%无政策信号"],
]
for i,row in enumerate(notes,1):
    for j,v in enumerate(row,1):
        cell = ws1.cell(i,j,v)
        if j==1: cell.font=Font(bold=True)
ws1.column_dimensions["A"].width=22; ws1.column_dimensions["B"].width=110

# 周度总览
ws2 = wb.create_sheet("01_周度总览")
sheet_from_df(ws2, d1, "周度总览 (复贷 1t0, 贷款+金额口径)",
              pct_cols=["贷款口径1t0%","金额口径1t0%","自然回款%","人工介入%"],
              up_cols=["贷款口径1t0%"], money_cols=["loans","should_cnt","mt","ot","mt_s","ot_s","should_s","nat_s","tpre0_s"])

# 各维度 shift-share
for name,(m,tb,tc) in ss_results.items():
    ws = wb.create_sheet(f"SS_{name.split()[0]}")
    m2 = m[["dim","share_b","share_c","rate_b","rate_c","mix","rate_eff","contrib"]].copy()
    m2["share_b"]=m2["share_b"]*100; m2["share_c"]=m2["share_c"]*100
    m2["rate_b"]=m2["rate_b"]*100; m2["rate_c"]=m2["rate_c"]*100
    m2 = m2.sort_values("contrib", ascending=False).head(30)
    m2.columns = ["维度","份额8/03%","份额8/10%","率8/03%","率8/10%","结构mix pp","率effect pp","总贡献pp"]
    sheet_from_df(ws, m2, f"{name}  shift-share (贷款口径, 总率 {tb:.2f}%->{tc:.2f}%)",
                  pct_cols=["份额8/03%","份额8/10%","率8/03%","率8/10%","结构mix pp","率effect pp","总贡献pp"])

# 反事实
ws = wb.create_sheet("02_结构反事实")
cf_rows = []
for wk in WEEKS:
    cur = dprod[dprod["wk"]==wk]
    if cur["mt"].sum()==0: continue
    act = cur["ot"].sum()/cur["mt"].sum()*100
    m = cur.set_index("dim").reindex(base.index).fillna(0)
    cf  = (base["mt"]/base["mt"].sum() * m["ot"]/m["mt"].replace(0,np.nan)).sum()*100
    cf2 = (m["mt"]/m["mt"].sum() * base["ot"]/base["mt"]).sum()*100
    cf_rows.append({"放款周":wk,"实际1t0%":round(act,2),"结构固定%(份额8/03)":round(cf,2),"率固定%(率8/03)":round(cf2,2)})
cfdf = pd.DataFrame(cf_rows)
sheet_from_df(ws, cfdf, "产品维度结构反事实: 结构固定≈实际 → 上升来自产品率恶化, 非结构混入",
              pct_cols=["实际1t0%","结构固定%(份额8/03)","率固定%(率8/03)"])

# 交叉验证
ws = wb.create_sheet("03_交叉验证_产品app")
sheet_from_df(ws, x4a, "产品×app_group 1t0率% (8/03 vs 8/10)", pct_cols=["率%"])
ws = wb.create_sheet("04_交叉验证_产品期数")
sheet_from_df(ws, x4b, "产品×复贷期数 1t0率% (8/03 vs 8/10)", pct_cols=["率%"])
ws = wb.create_sheet("05_交叉验证_金额产品")
sheet_from_df(ws, x4c, "金额段×产品 1t0率% (8/03 vs 8/10)", pct_cols=["率%"])

# 逐日
ws = wb.create_sheet("06_逐日1t0")
sheet_from_df(ws, d5, "复贷 1t0 逐日 (贷款口径, 转折点≈8/12)", pct_cols=["率%"], up_cols=["率%"], money_cols=["loans","mt","ot"])

# 还款节奏
ws = wb.create_sheet("07_还款节奏_周")
sheet_from_df(ws, d6[["wk","loans","预3d%","预2d%","预1d%","当天%","T0逾%","自然回款%","人工介入%"]],
              "还款节奏 按放款周 (金额占比, 分母=should_amount)", pct_cols=["预3d%","预2d%","预1d%","当天%","T0逾%","自然回款%","人工介入%"], money_cols=["loans"])
ws = wb.create_sheet("08_还款节奏_期限")
sheet_from_df(ws, d7[["wk","term","loans","预3d%","预2d%","预1d%","当天%","T0逾%"]],
              "还款节奏 × 期限", pct_cols=["预3d%","预2d%","预1d%","当天%","T0逾%"], money_cols=["loans"])

# 补还率
ws = wb.create_sheet("09_补还率")
sheet_from_df(ws, d8[["wk","term","loans","T0逾%","T1补%","T2补%","T3补%","T7补%"]],
              "T0->T1/T2/T3/T7 逾期补还率 (7/14天; 下降=非预提醒弱化)", pct_cols=["T0逾%","T1补%","T2补%","T3补%","T7补%"], money_cols=["loans"])

# 应还日周
ws = wb.create_sheet("10_应还日周")
sheet_from_df(ws, d9[["duwk","loans","预3d%","预2d%","预1d%","当天%","T0逾%"]],
              "应还日周(should_time) 还款节奏", pct_cols=["预3d%","预2d%","预1d%","当天%","T0逾%"], money_cols=["loans"])

wb.save(EXCEL_OUT)
print(f"\n已导出: {EXCEL_OUT}")
print("完成。")
