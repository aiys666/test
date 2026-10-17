# -*- coding: utf-8 -*-
"""6-12级客群专项排查：产品?放松客群?还是其他?
1) 6-12整体大数  2) 6-9 vs 10-12 结构迁移检验  3) 内部各维度对比
4) 内部shift-share(结构vs率)  5) app基准看通过率/用信率是否放松
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd, numpy as np

pd.set_option('display.width', 400); pd.set_option('display.max_rows', 400); pd.set_option('display.max_columns', 100)
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"
BASE_WK, CUR_WK = "2026-08-03", "2026-08-10"
MIN_LOAN, MIN_WINDOW = 50, 30

def calc_metrics(d):
    d = d.copy()
    if "issue_cnt" not in d.columns and "if_issue" in d.columns: d["issue_cnt"] = d["if_issue"]
    def pct(n,m): return (n/m*100).round(2)
    d["1t0本金%"]=pct(d["t0_overdue_capit_1"],d["t0_should_capit_1"])
    d["1t3本金%"]=pct(d["t3_overdue_capit_1"],d["t3_should_capit_1"])
    d["1t7本金%"]=pct(d["t7_overdue_capit_1"],d["t7_should_capit_1"])
    d["4t0本金%"]=pct(d["t0_overdue_capit_4"],d["t0_should_capit_4"])
    d["4t3本金%"]=pct(d["t3_overdue_capit_4"],d["t3_should_capit_4"])
    d["4t7本金%"]=pct(d["t7_overdue_capit_4"],d["t7_should_capit_4"])
    d["4t3息费%"]=pct(d["t3_overdue_interest_4"],d["t3_should_capit_4"])
    d["4t7息费%"]=pct(d["t7_overdue_interest_4"],d["t7_should_capit_4"])
    d["前砍%"]=pct(d["haircut_amount"],d["contract_amount"])
    d["后收%"]=pct(d["should_interest"],d["contract_amount"])
    d["4t3TR%"]=(d["后收%"]+d["前砍%"]-d["4t3息费%"]-d["4t3本金%"]).round(2)
    d["4T7TR%"]=(d["后收%"]+d["前砍%"]-d["4t7息费%"]-d["4t7本金%"]).round(2)
    d["件均"]=(d["contract_amount"]/d["issue_cnt"]).round(0)
    d["前置%"]=pct(d["if_in_sx"],d["if_app"])
    d["后置"]=(d["issue_cnt"]/d["if_sx_passed"]).round(3)
    d["风险通过率%"]=(d["前置%"]*d["后置"]).round(2)
    d["24h用信率%"]=pct(d["if_sx_passed_24h"],d["if_in_sx_24h"])
    d["120h用信率%"]=pct(d["if_sx_passed_120h"],d["if_in_sx_120h"])
    d=d.rename(columns={"is_t0_window_1":"1t0出账","is_t3_window_4":"4t3出账","is_t7_window_4":"4t7出账"})
    return d

DIMS = ["product_name","app_group","channel_category","loan_cycle","reloan_num","contract_amount",
        "t0_should_capit","grant_score","grant_strategy","product_level",
        "评级子段","评级单级","v5_3中评级","fd_high_pass","if_reloan_24h","学历","职业","收入段","年龄段",
        "v5_3欺诈分","v5_3行为分","当前逾期笔数","本APP逾期笔数","历史最大逾期天","他APP有逾期","最近还款间隔"]
METRICS=["1t0本金%","4t0本金%","4t3本金%","4t7本金%","4t3息费%","4t7息费%","前砍%","后收%","4t3TR%","4T7TR%","件均"]

def load(key, base):
    fp=os.path.join(OUT,f"_agg612_{key}_{base}.pkl")
    if not os.path.exists(fp): return None
    df=pd.read_pickle(fp); df["d"]=pd.to_datetime(df["d"])
    df["wk"]=(df["d"]-pd.to_timedelta(df["d"].dt.weekday,unit="D")).dt.strftime("%Y-%m-%d")
    return df

# ── [1] 6-12 整体大数 issue ──
seg=load("评级子段","issue")
wk_all=calc_metrics(seg.groupby("wk",as_index=False).sum(numeric_only=True))
print("="*110); print("[1] 6-12级整体 周度大数 (issue)")
print(wk_all[["wk","issue_cnt","contract_amount","1t0本金%","4t3本金%","4t7本金%","4T7TR%","1t0出账","4t3出账","件均"]].to_string(index=False))

app_all=calc_metrics(load("评级子段","app").groupby("wk",as_index=False).sum(numeric_only=True))
print("="*110); print("[1b] 6-12级整体 周度大数 (app: 是否放松)")
print(app_all[["wk","if_app","issue_cnt","前置%","后置","风险通过率%","24h用信率%","120h用信率%","1t0本金%","4T7TR%"]].to_string(index=False))

# ── [2] 结构迁移: 6-9 vs 10-12 占比 + 各自率 ──
print("="*110); print("[2] 6-9 vs 10-12 结构迁移检验 (issue)")
sw=calc_metrics(seg.groupby(["wk","dim"],as_index=False).sum(numeric_only=True))
piv_n=sw.pivot(index="wk",columns="dim",values="issue_cnt").fillna(0)
piv_n["6-12合计"]=piv_n.sum(axis=1)
piv_n["10-12占比%"]=(piv_n.get("10-12级",0)/piv_n["6-12合计"]*100).round(2)
piv_n["6-9占比%"]=(piv_n.get("6-9级",0)/piv_n["6-12合计"]*100).round(2)
print(piv_n.loc[["2026-07-27","2026-08-03","2026-08-10","2026-08-17","2026-08-24"]].to_string())
print("\n各子段坏账率:")
piv_r=sw.pivot(index="wk",columns="dim",values="1t0本金%")
print(piv_r.loc[["2026-07-27","2026-08-03","2026-08-10","2026-08-17","2026-08-24"]].round(2).to_string())

# 评级单级迁移
print("="*110); print("[2b] 评级单级 8/03 vs 8/10 笔数占比 & 坏账率")
lv1=load("评级单级","issue")
lw=calc_metrics(lv1.groupby(["wk","dim"],as_index=False).sum(numeric_only=True))
b=lw[lw.wk==BASE_WK].set_index("dim"); c=lw[lw.wk==CUR_WK].set_index("dim")
tb=int(b["issue_cnt"].sum()); tc=int(c["issue_cnt"].sum())
rows=[]
for g in sorted(set(b.index)|set(c.index), key=lambda x: float(x)):
    nb=b["issue_cnt"].get(g,0); nc=c["issue_cnt"].get(g,0)
    rows.append({"级":g,"笔数_b":int(nb),"占比_b%":round(nb/tb*100,2),"笔数_c":int(nc),"占比_c%":round(nc/tc*100,2),
                 "1t0_b":b["1t0本金%"].get(g),"1t0_c":c["1t0本金%"].get(g),
                 "1t0_Δ":None if g not in b.index or g not in c.index else round(c["1t0本金%"].get(g)-b["1t0本金%"].get(g),2),
                 "4T7TR_c":c["4T7TR%"].get(g)})
lv1_cmp=pd.DataFrame(rows)
print(lv1_cmp.to_string(index=False))

# ── [3] 各维度 8/03 vs 8/10 对比 ──
def compare(key, base="issue"):
    df=load(key,base)
    if df is None: return None
    w=calc_metrics(df.groupby(["wk","dim"],as_index=False).sum(numeric_only=True))
    b=w[w.wk==BASE_WK].set_index("dim"); c=w[w.wk==CUR_WK].set_index("dim")
    out=[]
    for g in sorted(set(b.index)|set(c.index)):
        row={"dim":g}
        for m in (["issue_cnt","if_app","if_in_sx","if_sx_passed","1t0出账","4t3出账","4t7出账"]+METRICS+
                  (["前置%","后置","风险通过率%","24h用信率%","120h用信率%"] if base=="app" else [])):
            row[f"{m}_b"]=b[m].get(g) if g in b.index else None
            row[f"{m}_c"]=c[m].get(g) if g in c.index else None
            if m in METRICS+["前置%","风险通过率%","24h用信率%","120h用信率%"] and g in b.index and g in c.index:
                row[f"{m}_Δ"]=round(c[m].get(g)-b[m].get(g),2)
            else: row[f"{m}_Δ"]=None
        out.append(row)
    r=pd.DataFrame(out); r["dim_key"]=key
    return r

print("="*110); print("[3] 6-12内部 各维度 8/03→8/10 (issue, 当期放款>=50)")
cmps={}
for k in DIMS:
    r=compare(k,"issue")
    if r is not None: cmps[k]=r
allc=pd.concat(cmps.values(),ignore_index=True)
big=allc[allc["issue_cnt_c"]>=MIN_LOAN].copy()
show=["dim_key","dim","issue_cnt_b","issue_cnt_c","1t0本金%_b","1t0本金%_c","1t0本金%_Δ","4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4t7本金%_Δ","4T7TR%_b","4T7TR%_c","4T7TR%_Δ"]
print("切片总数:",len(allc)," 大样本:",len(big))
print("── 1t0本金% 恶化 TOP20 ──")
print(big.sort_values("1t0本金%_Δ",ascending=False)[show].head(20).to_string(index=False))

# ── [4] 内部 shift-share (1t0本金%, 应还本金加权) ──
print("="*110); print("[4] 6-12内部 shift-share (1t0本金%)")
ssr=[]
for k in DIMS:
    df=load(k,"issue")
    if df is None: continue
    w=calc_metrics(df.groupby(["wk","dim"],as_index=False).sum(numeric_only=True))
    b=w[w.wk==BASE_WK].set_index("dim"); c=w[w.wk==CUR_WK].set_index("dim")
    m=b[["t0_should_capit_1","1t0本金%"]].join(c[["t0_should_capit_1","1t0本金%"]],how="outer",lsuffix="_b",rsuffix="_c").fillna(0)
    m["sh_b"]=m["t0_should_capit_1_b"]/m["t0_should_capit_1_b"].sum()
    m["sh_c"]=m["t0_should_capit_1_c"]/m["t0_should_capit_1_c"].sum()
    mix=((m["sh_c"]-m["sh_b"])*m["1t0本金%_b"]).sum()
    rate=(m["sh_c"]*(m["1t0本金%_c"]-m["1t0本金%_b"])).sum()
    tb=(m["t0_should_capit_1_b"]*m["1t0本金%_b"]).sum()/m["t0_should_capit_1_b"].sum()
    tc=(m["t0_should_capit_1_c"]*m["1t0本金%_c"]).sum()/m["t0_should_capit_1_c"].sum()
    ssr.append({"维度":k,"总率_b":round(tb,2),"总率_c":round(tc,2),"Δ":round(tc-tb,2),
                "结构Σmix":round(mix,2),"率Σrate":round(rate,2)})
ss612=pd.DataFrame(ssr).sort_values("率Σrate",ascending=False)
print(ss612.to_string(index=False))

# ── [5] app 基准放松检验 (6-12内部关键维度) ──
print("="*110); print("[5] 6-12内部 放松检验 (app基准: 前置/风险通过率/用信率)")
for k in ["评级子段","评级单级","grant_score","grant_strategy","fd_high_pass","product_name","历史最大逾期天","当前逾期笔数","最近还款间隔"]:
    r=compare(k,"app")
    if r is None: continue
    rr=r.copy()
    rr["if_app_c"]=pd.to_numeric(rr["if_app_c"],errors="coerce")
    rr=rr[rr["if_app_c"]>=30]
    cols=["dim","if_app_b","if_app_c","前置%_b","前置%_c","风险通过率%_b","风险通过率%_c","24h用信率%_b","24h用信率%_c","120h用信率%_b","120h用信率%_c","1t0本金%_Δ"]
    cols=[x for x in cols if x in rr.columns]
    print(f"── {k} ──")
    print(rr.sort_values("if_app_c",ascending=False)[cols].head(8).to_string(index=False))

# ── 保存 ──
wk_all.to_pickle(os.path.join(OUT,"_612_wk_issue.pkl"))
app_all.to_pickle(os.path.join(OUT,"_612_wk_app.pkl"))
lv1_cmp.to_pickle(os.path.join(OUT,"_612_lv1_cmp.pkl"))
allc.to_pickle(os.path.join(OUT,"_612_cmp_all.pkl"))
ss612.to_pickle(os.path.join(OUT,"_612_shift.pkl"))
print("\n已保存 6-12 专项中间结果")
