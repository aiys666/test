# -*- coding: utf-8 -*-
"""墨西哥坏账风险归因 - 完整分析 (SQL按天聚合 -> 滚周 -> 26+1指标 -> 全维度定位)
输出: 墨西哥坏账风险归因_全维度分析.xlsx
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import numpy as np

pd.set_option('display.width', 400)
pd.set_option('display.max_rows', 400)
pd.set_option('display.max_columns', 80)

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"
EXCEL_OUT = os.path.join(OUT, "墨西哥坏账风险归因_全维度分析.xlsx")

BASE_WK = "2026-08-03"   # 基期周
CUR_WK  = "2026-08-10"   # 上升周
MIN_LOAN = 50            # 放款笔数下限
MIN_WINDOW = 30          # 出账笔数下限

# ── 工具 ──
def calc_metrics(d):
    d = d.copy()
    if "issue_cnt" not in d.columns and "if_issue" in d.columns:
        d["issue_cnt"] = d["if_issue"]
    def pct(n, m): return (n / m * 100).round(2)
    d["1t0本金%"] = pct(d["t0_overdue_capit_1"], d["t0_should_capit_1"])
    d["1t3本金%"] = pct(d["t3_overdue_capit_1"], d["t3_should_capit_1"])
    d["1t7本金%"] = pct(d["t7_overdue_capit_1"], d["t7_should_capit_1"])
    d["2t0本金%"] = pct(d["t0_overdue_capit_2"], d["t0_should_capit_2"])
    d["3t0本金%"] = pct(d["t0_overdue_capit_3"], d["t0_should_capit_3"])
    d["4t0本金%"] = pct(d["t0_overdue_capit_4"], d["t0_should_capit_4"])
    d["4t3本金%"] = pct(d["t3_overdue_capit_4"], d["t3_should_capit_4"])
    d["4t7本金%"] = pct(d["t7_overdue_capit_4"], d["t7_should_capit_4"])
    d["4t3息费%"] = pct(d["t3_overdue_interest_4"], d["t3_should_capit_4"])
    d["4t7息费%"] = pct(d["t7_overdue_interest_4"], d["t7_should_capit_4"])
    d["前砍%"] = pct(d["haircut_amount"], d["contract_amount"])
    d["后收%"] = pct(d["should_interest"], d["contract_amount"])
    d["4t3TR%"] = (d["后收%"] + d["前砍%"] - d["4t3息费%"] - d["4t3本金%"]).round(2)
    d["4T7TR%"] = (d["后收%"] + d["前砍%"] - d["4t7息费%"] - d["4t7本金%"]).round(2)
    d["件均"] = (d["contract_amount"] / d["issue_cnt"]).round(0)
    d["期限"] = (d["loan_cycle_amount"] / d["contract_amount"]).round(2)
    d["前置%"] = pct(d["if_in_sx"], d["if_app"])
    d["后置"] = (d["issue_cnt"] / d["if_sx_passed"]).round(3)
    d["风险通过率%"] = (d["前置%"] * d["后置"]).round(2)
    d["24h用信率%"] = pct(d["if_sx_passed_24h"], d["if_in_sx_24h"])
    d["120h用信率%"] = pct(d["if_sx_passed_120h"], d["if_in_sx_120h"])
    d["1t0出账"] = d["is_t0_window_1"]; d["1t3出账"] = d["is_t3_window_1"]; d["1t7出账"] = d["is_t7_window_1"]
    d["2t0出账"] = d["is_t0_window_2"]; d["3t0出账"] = d["is_t0_window_3"]; d["4t0出账"] = d["is_t0_window_4"]
    d["4t3出账"] = d["is_t3_window_4"]; d["4t7出账"] = d["is_t7_window_4"]
    return d

METRICS = ["1t0本金%","1t3本金%","1t7本金%","2t0本金%","3t0本金%","4t0本金%",
           "4t3本金%","4t7本金%","4t3息费%","4t7息费%","前砍%","后收%","4t3TR%","4T7TR%",
           "件均","期限","前置%","后置","风险通过率%","24h用信率%","120h用信率%"]

def load_dim(key, base):
    fp = os.path.join(OUT, f"_aggdim_{key}_{base}.pkl")
    if not os.path.exists(fp): return None
    df = pd.read_pickle(fp)
    df["d"] = pd.to_datetime(df["d"])
    df["wk"] = (df["d"] - pd.to_timedelta(df["d"].dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
    return df

def parse_level(x):
    try: return int(round(float(x)))
    except Exception: return None

def level_bucket(x):
    n = parse_level(x)
    if n is None: return "空"
    if n <= 3: return "1-3"
    if n <= 7: return "4-7"
    return "8+"

def prod_line(x):
    return str(x).split("_")[0] if isinstance(x, str) else str(x)

FUNNEL_DIMS = ["product_name","app_group","channel_category","source","product_type","product_day",
               "loan_cycle","reloan_num","contract_amount","t0_should_capit","grant_score",
               "grant_strategy","product_level","risk_level"]
YJ_DIMS = ["product_name_new","v5_3主评级","v6_1主评级","v5_3中评级","v6_1中评级","v3_flag","v3_flag_huidu",
           "fd_high_pass","if_reloan_24h","学历","婚姻","职业","有车","有房","收入段","年龄段",
           "v5_3欺诈分","v5_3行为分","当前逾期笔数","本APP逾期笔数","历史最大逾期天","他APP有逾期","最近还款间隔"]
ALL_DIMS = FUNNEL_DIMS + YJ_DIMS

# ═══════════════ 1. 大数校验 + 逐日 ═══════════════
base_all = load_dim("product_name", "issue")
all_daily = base_all.groupby(["wk", "d"], as_index=False).sum(numeric_only=True)
all_wk = all_daily.groupby("wk").sum(numeric_only=True).reset_index()
weekly = calc_metrics(all_wk)
daily = calc_metrics(all_daily)

print("=" * 110)
print("[1] 周度总览 issue基准 (放款周)")
print(weekly[["wk","issue_cnt","contract_amount","1t0本金%","4t3本金%","4t7本金%","4t3TR%","4T7TR%",
              "1t0出账","4t3出账","4t7出账","件均","期限"]].to_string(index=False))

print("=" * 110)
print("[2] 周度总览 app基准 (进件周, 含前置/风险通过率)")
base_app_all = load_dim("product_name", "app")
app_all_daily = base_app_all.groupby(["wk", "d"], as_index=False).sum(numeric_only=True)
app_all_wk = app_all_daily.groupby("wk").sum(numeric_only=True).reset_index()
app_weekly = calc_metrics(app_all_wk)
print(app_weekly[["wk","if_app","issue_cnt","前置%","后置","风险通过率%","24h用信率%","120h用信率%",
                  "1t0本金%","4t3本金%","4T7TR%"]].to_string(index=False))

# ═══════════════ 2. 全维度对比 + shift-share ═══════════════
def compare_dim(df, base_wk=BASE_WK, cur_wk=CUR_WK):
    g = df.groupby("wk")
    if base_wk not in g.groups or cur_wk not in g.groups: return None
    b = df[df["wk"] == base_wk].groupby("dim", as_index=False).sum(numeric_only=True)
    c = df[df["wk"] == cur_wk].groupby("dim", as_index=False).sum(numeric_only=True)
    bm = calc_metrics(b); cm = calc_metrics(c)
    m = bm.merge(cm, on="dim", suffixes=("_b", "_c"), how="outer").fillna(0)
    out = m[["dim","issue_cnt_b","issue_cnt_c","if_app_b","if_app_c",
             "1t0出账_b","1t0出账_c","4t3出账_b","4t3出账_c","4t7出账_b","4t7出账_c",
             "t0_should_capit_1_b","t0_should_capit_1_c","t3_should_capit_4_b","t3_should_capit_4_c"]].copy()
    for met in METRICS:
        out[f"{met}_b"] = m[f"{met}_b"]; out[f"{met}_c"] = m[f"{met}_c"]
        out[f"{met}_Δ"] = (m[f"{met}_c"] - m[f"{met}_b"]).round(2)
    return out

def shift_share(df, met, wcol, base_wk=BASE_WK, cur_wk=CUR_WK):
    """结构效应 vs 率效应。met=率指标列(百分数), wcol=权重列(should本金); 效应单位=pp"""
    b = df[df["wk"] == base_wk].groupby("dim", as_index=False).sum(numeric_only=True)
    c = df[df["wk"] == cur_wk].groupby("dim", as_index=False).sum(numeric_only=True)
    bm = calc_metrics(b); cm = calc_metrics(c)
    bm["w"] = bm[wcol]; cm["w"] = cm[wcol]
    bm["share"] = bm["w"]/bm["w"].sum(); cm["share"] = cm["w"]/cm["w"].sum()
    m = bm[["dim","w","share",met]].merge(cm[["dim","w","share",met]], on="dim", how="outer", suffixes=("_b","_c"))
    for col in ["w_b","w_c","share_b","share_c"]: m[col] = m[col].fillna(0)
    m[f"{met}_b"] = m[f"{met}_b"].fillna(0); m[f"{met}_c"] = m[f"{met}_c"].fillna(0)
    m["mix"] = (m["share_c"]-m["share_b"])*m[f"{met}_b"]          # 结构效应 pp
    m["rate_eff"] = m["share_c"]*(m[f"{met}_c"]-m[f"{met}_b"])    # 率效应 pp
    m["contrib"] = m["mix"]+m["rate_eff"]
    tb = (bm["w"]*bm[met]).sum()/bm["w"].sum()
    tc = (cm["w"]*cm[met]).sum()/cm["w"].sum()
    return m.sort_values("contrib", ascending=False), tb, tc

print("=" * 110)
print("[3] 各维度 8/03 -> 8/10 对比 (issue基准, 过滤小样本: 当期放款<50 或 4t3出账<30)")
cmp_results = {}
for key in ALL_DIMS:
    df = load_dim(key, "issue")
    if df is None: continue
    cmp = compare_dim(df)
    if cmp is None or len(cmp) == 0: continue
    cmp["dim_key"] = key
    cmp_results[key] = cmp

all_cmp = pd.concat(cmp_results.values(), ignore_index=True)
# 过滤: 当期放款笔数>=50
big = all_cmp[all_cmp["issue_cnt_c"] >= MIN_LOAN].copy()
print(f"  切片总数={len(all_cmp)}, 放款>=50笔切片数={len(big)}")

# 4t3本金% 劣化榜 (大样本)
big_sorted = big.sort_values("4t3本金%_Δ", ascending=False)
show_cols = ["dim_key","dim","issue_cnt_b","issue_cnt_c","1t0本金%_b","1t0本金%_c","1t0本金%_Δ",
             "4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4t7本金%_Δ","4T7TR%_b","4T7TR%_c","4T7TR%_Δ"]
print("  ── 4t3本金% 恶化TOP20 (大样本) ──")
print(big_sorted[show_cols].head(20).to_string(index=False))
print("  ── 4t3本金% 改善TOP10 (大样本) ──")
print(big_sorted[show_cols].tail(10).to_string(index=False))

# ═══════════════ 3. shift-share (issue, 金额口径) ═══════════════
print("=" * 110)
print("[4] shift-share 分解 (issue基准, 1t0本金% 金额口径, Σmix=结构 Σrate=率效应)")
ss_rows = []
for key in ALL_DIMS:
    df = load_dim(key, "issue")
    if df is None: continue
    try:
        m, tb, tc = shift_share(df, "1t0本金%", "t0_should_capit_1")
    except Exception as e:
        continue
    mix_sum = m["mix"].sum(); rate_sum = m["rate_eff"].sum()
    top = m.iloc[0]
    ss_rows.append({"维度": key, "总率基期": round(tb,2), "总率当期": round(tc,2),
                    "Δpp": round(tc-tb,2), "结构Σmix": round(mix_sum,2), "率效应Σrate": round(rate_sum,2),
                    "最大贡献切片": top["dim"], "贡献pp": round(top["contrib"],2)})
ss = pd.DataFrame(ss_rows).sort_values("率效应Σrate", ascending=False)
print(ss.to_string(index=False))

# ═══════════════ 4. 评级聚类 (1-3/4-7/8+) ═══════════════
print("=" * 110)
print("[5] 评级聚类三段 1-3 / 4-7 / 8+ (issue基准, 8/03 vs 8/10)")
lv_rows = []
for lk in ["v5_3主评级","v6_1主评级","v5_3中评级","v6_1中评级"]:
    df = load_dim(lk, "issue")
    if df is None: continue
    df["dim"] = df["dim"].map(level_bucket)
    agg = df.groupby(["wk","d","dim"], as_index=False).sum(numeric_only=True)
    cmp = compare_dim(agg)
    if cmp is None: continue
    cmp["dim_key"] = lk
    lv_rows.append(cmp)
lv = pd.concat(lv_rows, ignore_index=True)
print(lv[["dim_key","dim","issue_cnt_b","issue_cnt_c","1t0本金%_b","1t0本金%_c","1t0本金%_Δ",
         "4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4T7TR%_b","4T7TR%_c","4T7TR%_Δ"]].to_string(index=False))

# ═══════════════ 5. 产品聚类: 产品线首字母 + loan_cycle ═══════════════
print("=" * 110)
print("[6] 产品聚类: 产品线(首字母) (issue基准)")
pl_df = load_dim("product_name", "issue")
pl_df["dim"] = pl_df["dim"].map(prod_line)
pl_agg = pl_df.groupby(["wk","d","dim"], as_index=False).sum(numeric_only=True)
pl_cmp = compare_dim(pl_agg)
print(pl_cmp[["dim","issue_cnt_b","issue_cnt_c","1t0本金%_b","1t0本金%_c","1t0本金%_Δ",
              "4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4T7TR%_b","4T7TR%_c"]].to_string(index=False))

# ═══════════════ 6. TR利润空间 + 逾期最高榜单 ═══════════════
print("=" * 110)
print("[7] TR利润空间: 4T7TR 当期最低TOP15 (大样本, 4T7TR<0=亏)")
big_tr = big[big["4t7出账_c"] >= MIN_WINDOW].sort_values("4T7TR%_c")
print(big_tr[["dim_key","dim","issue_cnt_c","4t7出账_c","前砍%_c","后收%_c","4t7本金%_c","4t7息费%_c","4T7TR%_c","4T7TR%_Δ"]].head(15).to_string(index=False))

print("=" * 110)
print("[8] 逾期最高榜单: 4t7本金% 当期最高TOP15 (大样本)")
big_ovd = big[big["4t7出账_c"] >= MIN_WINDOW].sort_values("4t7本金%_c", ascending=False)
print(big_ovd[["dim_key","dim","issue_cnt_c","4t7出账_c","1t0本金%_c","4t3本金%_c","4t7本金%_c","4T7TR%_c"]].head(15).to_string(index=False))

# ═══════════════ 7. 逐日拐点 ═══════════════
print("=" * 110)
print("[8b] 逐日拐点 (issue基准, 放款日 8/01-8/25)")
dg = daily[(daily["d"] >= "2026-08-01") & (daily["d"] <= "2026-08-25")].copy()
print(dg[["d","issue_cnt","contract_amount","1t0本金%","4t3本金%","4t7本金%","4T7TR%","件均"]].to_string(index=False))

# ═══════════════ 保存中间 ═══════════════
all_cmp.to_pickle(os.path.join(OUT, "_cmp_all.pkl"))
ss.to_pickle(os.path.join(OUT, "_shift_share.pkl"))
lv.to_pickle(os.path.join(OUT, "_level_cluster.pkl"))
pl_cmp.to_pickle(os.path.join(OUT, "_prodline_cluster.pkl"))
weekly.to_pickle(os.path.join(OUT, "_weekly_issue_metrics.pkl"))
app_weekly.to_pickle(os.path.join(OUT, "_weekly_app_metrics.pkl"))
daily.to_pickle(os.path.join(OUT, "_daily_issue_metrics.pkl"))
print("\n中间结果已保存")

# ═══════════════ 8. 导出 Excel ═══════════════
def sheet(df, ws_name, w):
    if df is None or len(df) == 0: return
    df.to_excel(w, sheet_name=ws_name, index=False)

def cmp_wide(dim_key, df):
    """比较明细 -> 宽表(仅指标, 含Δ)"""
    cols = ["dim","issue_cnt_b","issue_cnt_c","1t0出账_b","1t0出账_c","4t3出账_b","4t3出账_c","4t7出账_b","4t7出账_c"]
    for met in METRICS:
        cols += [f"{met}_b", f"{met}_c", f"{met}_Δ"]
    return df[cols].copy()

print("导出 Excel ...")
with pd.ExcelWriter(EXCEL_OUT, engine="openpyxl") as w:
    sheet(weekly[["wk","issue_cnt","contract_amount","1t0本金%","1t3本金%","1t7本金%","2t0本金%","3t0本金%","4t0本金%",
                  "4t3本金%","4t7本金%","4t3息费%","4t7息费%","前砍%","后收%","4t3TR%","4T7TR%",
                  "件均","期限","1t0出账","4t3出账","4t7出账"]], "1_周度总览_issue", w)
    sheet(app_weekly[["wk","if_app","issue_cnt","前置%","后置","风险通过率%","24h用信率%","120h用信率%",
                      "1t0本金%","4t3本金%","4T7TR%"]], "2_周度总览_app", w)
    sheet(daily[["d","issue_cnt","contract_amount","1t0本金%","4t3本金%","4t7本金%","4T7TR%","件均"]], "3_逐日_issue", w)
    # 各维度对比
    for key, cmp in cmp_results.items():
        if cmp is None or len(cmp) == 0: continue
        wd = cmp_wide(key, cmp)
        wd = wd.sort_values("4t3本金%_Δ", ascending=False)
        sheet(wd, f"d_{key}"[:31], w)
    # shift-share
    sheet(ss, "4_shift_share_1t0", w)
    sheet(lv, "5_评级聚类三段", w)
    sheet(pl_cmp, "6_产品线聚类", w)
    # TR利润空间 & 逾期榜单
    sheet(big_tr[["dim_key","dim","issue_cnt_c","4t7出账_c","前砍%_c","后收%_c","4t7本金%_c","4t7息费%_c","4T7TR%_c","4T7TR%_Δ"]], "7_TR利润空间最低", w)
    sheet(big_ovd[["dim_key","dim","issue_cnt_c","4t7出账_c","1t0本金%_c","4t3本金%_c","4t7本金%_c","4T7TR%_c"]], "8_逾期最高榜单", w)
print("已导出:", EXCEL_OUT)
