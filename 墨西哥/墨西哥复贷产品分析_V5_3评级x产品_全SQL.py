# -*- coding: utf-8 -*-
"""
墨西哥 复贷产品分析 v4 —— V5_3 主资产等级 × 产品 表现总表
================================================================================
目标(用户 2026-09 确认): funnel(订单级成熟窗口vintage + 税后净口径, 与 v3 同源同口径)
× 主资产等级 android_oldcust_maincreditlevel_charge_v5_3(档1~13), 按 biz_id join
mx.yj_test_table_250225 取 y.v3_flag='V5_3' 且评级非空的老客放款 cohort
(release_time 2026-06-09 ~ 2026-09-01)。

评级方向(探针坐实): 档号越大 = 首逾越高 / 件均越小 → 1=最优, 13=最差。

沿用 v3:
1) 税口径: 前砍费 ha 与本金 ca 不计税也不 ÷1.16; 后收利息 si: E 开头产品(含税价)
   → si_net = si/1.16, 其余 = si; 息费税(估) = si_net×16%。(funnel is_e=substr(产品名,1,1)='E')
2) 全部指标在 SQL 内算: loans/custs/ca/ha/si/si_net/成熟率/首逾率/金额逾期率/净率/税/TR 无 py 现算。
3) 字段命名沿用 funnel/参考SQL 词汇; 衍生=词根+后缀。
4) 成熟窗口 vintage 订单级 T0/T3/T7/T14/T30: is_t{N}_window=1 才计入; t14 无 flag → 用 t14_overdue_amount>1 代理。
5) 该端点不支持 GROUPING SETS → 明细(产品×评级)/评级小计/产品小计/全量/评级×月/月小计 拆普通 GROUP BY。

交付: 本 py + 同名 .sql(同一文本, py 逐条执行) + 同名 .xlsx
"""
import sys, os, warnings
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

VAT = 0.16
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "墨西哥复贷产品分析_V5_3评级x产品_全SQL"
OUT_XLSX = os.path.join(HERE, BASE + ".xlsx")
OUT_SQL = os.path.join(HERE, BASE + ".sql")

_WINS = ["t0", "t3", "t7", "t14", "t30"]
_FLAG = {"t0": "is_t0_overdue", "t3": "is_t3_overdue", "t7": "is_t7_overdue",
         "t30": "is_t30_overdue"}  # t14 无 flag

FILTER = ("f.is_reloan = 'old' AND f.if_issue = 1 AND f.product_name IS NOT NULL AND f.product_name <> '' "
          "AND date(f.release_time) >= date '2026-06-09' AND date(f.release_time) < date '2026-09-01' "
          "AND y.v3_flag = 'V5_3' AND y.android_oldcust_maincreditlevel_charge_v5_3 IS NOT NULL")
MONTH_GRP = "date_format(date_trunc('month', date(release_time)), '%Y-%m')"
FULL_GRP = "CAST('全期' AS VARCHAR)"

def _win_cols():
    cols = []
    for W in _WINS:
        mat = f"sum(if(is_{W}_window = 1, 1, 0))"
        sh = f"sum(if(is_{W}_window = 1, {W}_should_amt, 0))"
        ovd = f"sum(if(is_{W}_window = 1, {W}_overdue_amount, 0))"
        flg = _FLAG.get(W)
        bad = (f"sum(if(is_{W}_window = 1 and {flg} = 1, 1, 0))" if flg
               else f"sum(if(is_{W}_window = 1 and {W}_overdue_amount > 1, 1, 0))")
        cols += [f"{mat} as {W}_mature_cnt",
                 f"{sh}  as {W}_should_amt",
                 f"{ovd} as {W}_overdue_amount",
                 f"{bad} as {W}_ovd_cnt"]
    cols += ["sum(if(is_t7_window = 1, contract_amount, 0))    as t7_mature_ca",
             "sum(if(is_t7_window = 1, haircut_amount, 0))     as t7_mature_ha",
             "sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net",
             "sum(if(is_t7_window = 1, t7_overdue_amount, 0))  as t7_mature_ovd"]
    return "\n      ,".join(cols)

def _win_out():
    items = []
    for W in _WINS:
        items += [f",{W}_mature_cnt", f",{W}_should_amt", f",{W}_overdue_amount", f",{W}_ovd_cnt"]
    items += [",t7_mature_ca", ",t7_mature_ha", ",t7_mature_si_net", ",t7_mature_ovd"]
    return "\n      ".join(items)

def _rate_cols():
    expr = []
    for W in _WINS:
        expr.append(f",round(CAST({W}_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as {W}_mature_rate")
        expr.append(f",round(CAST({W}_ovd_cnt AS DOUBLE) / nullif({W}_mature_cnt, 0), 4) as {W}_cntrate")
        expr.append(f",round(CAST({W}_overdue_amount AS DOUBLE) / nullif({W}_should_amt, 0), 4) as {W}_amtrate")
    expr.append(""",round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca""")
    return "".join(expr)

_AGG = ("count(distinct biz_id) AS loans\n"
        "        ,count(distinct mid)       AS custs\n"
        "        ,round(sum(contract_amount), 2)  AS ca\n"
        "        ,round(sum(haircut_amount), 2)   AS ha\n"
        "        ,round(sum(should_interest), 2)  AS si\n"
        "        ,round(sum(if(is_e = 1, should_interest / 1.16, should_interest)), 2) AS si_net\n"
        "        ,")

_RATIO = (" ,round(CAST(ca AS DOUBLE) / nullif(loans, 0), 2)  as avg_ca\n"
          "      ,round(CAST(loans AS DOUBLE) / nullif(custs, 0), 4) as loans_cust\n"
          "      ,round(CAST(ha AS DOUBLE) / nullif(ca, 0), 4)          as ha_rate\n"
          "      ,round(CAST(si AS DOUBLE) / nullif(ca, 0), 4)          as si_rate\n"
          "      ,round(CAST(si_net AS DOUBLE) / nullif(ca, 0), 4)      as si_net_rate\n"
          "      ,round(CAST(ha + si_net AS DOUBLE) / nullif(ca, 0), 4) as fee_net_rate\n"
          f"      ,round(CAST(si_net * {VAT} AS DOUBLE) / nullif(ca, 0), 4) as vat_ca_rate")

_SHARE = (" ,round(CAST(loans AS DOUBLE) / nullif(sum(loans) over (partition by grade), 0), 4) as loans_share_g\n"
          "      ,round(CAST(ca    AS DOUBLE) / nullif(sum(ca)    over (partition by grade), 0), 4) as ca_share_g\n"
          "      ,round(CAST(loans AS DOUBLE) / nullif(sum(loans) over (partition by product_name), 0), 4) as loans_share_p\n"
          "      ,round(CAST(ca    AS DOUBLE) / nullif(sum(ca)    over (partition by product_name), 0), 4) as ca_share_p")

_NULL_SHARE = (" ,CAST(NULL AS DOUBLE) AS loans_share_g\n"
               "      ,CAST(NULL AS DOUBLE) AS ca_share_g\n"
               "      ,CAST(NULL AS DOUBLE) AS loans_share_p\n"
               "      ,CAST(NULL AS DOUBLE) AS ca_share_p")

_RAW = f"""
WITH raw AS (
  SELECT f.product_name
        ,CAST(y.android_oldcust_maincreditlevel_charge_v5_3 AS INTEGER) AS grade
        ,if(substr(f.product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,f.biz_id, f.mid
        ,f.contract_amount, f.haircut_amount, f.should_interest
        ,f.release_time
        ,f.is_t0_window ,f.t0_should_amt ,f.t0_overdue_amount
        ,f.is_t3_window ,f.t3_should_amt ,f.t3_overdue_amount
        ,f.is_t7_window ,f.t7_should_amt ,f.t7_overdue_amount
        ,f.is_t14_window,f.t14_should_amt,f.t14_overdue_amount
        ,f.is_t30_window,f.t30_should_amt,f.t30_overdue_amount
        ,f.is_t0_overdue,f.is_t3_overdue,f.is_t7_overdue,f.is_t30_overdue
  FROM mx.wxs_application_funnel f
  JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
  WHERE {FILTER}
)"""

# level: det=产品×评级(占比双口径) | gm=评级小计 | pm=产品小计 | tot=全量
#        | mg=月×评级 | mm=月小计 | mpm=月×产品×评级 | mp=月×产品
def _stmt(level):
    cfg = {
        "det": (FULL_GRP, "product_name", "grade", "GROUP BY product_name, grade", _SHARE, "product_name, grade"),
        "gm":  (FULL_GRP, "CAST(NULL AS VARCHAR) AS product_name", "grade", "GROUP BY grade", _NULL_SHARE, "grade"),
        "pm":  (FULL_GRP, "product_name", "CAST(NULL AS INTEGER) AS grade", "GROUP BY product_name", _NULL_SHARE, "product_name"),
        "tot": (FULL_GRP, "CAST(NULL AS VARCHAR) AS product_name", "CAST(NULL AS INTEGER) AS grade", "", _NULL_SHARE, "1"),
        "mg":  (MONTH_GRP, "CAST(NULL AS VARCHAR) AS product_name", "grade",
                f"GROUP BY {MONTH_GRP}, grade", _NULL_SHARE, "grade"),
        "mm":  (MONTH_GRP, "CAST(NULL AS VARCHAR) AS product_name", "CAST(NULL AS INTEGER) AS grade",
                f"GROUP BY {MONTH_GRP}", _NULL_SHARE, "1"),
        "mpm": (MONTH_GRP, "product_name", "grade",
                f"GROUP BY {MONTH_GRP}, product_name, grade", _NULL_SHARE, "product_name, grade"),
        "mp":  (MONTH_GRP, "product_name", "CAST(NULL AS INTEGER) AS grade",
                f"GROUP BY {MONTH_GRP}, product_name", _NULL_SHARE, "product_name"),
    }[level]
    grp, prod, grad, gby, share, order = cfg
    sel = (f"SELECT {grp} AS grp\n      ,{prod}\n      ,{grad}\n      ,{_AGG}{_win_cols()}\n"
           f"  FROM raw\n" + (f"  {gby}\n" if gby else ""))
    return f"""{_RAW}
,g AS (
  {sel}
)
SELECT grp, product_name, grade
      ,loans, custs, ca, ha, si, si_net
      {_win_out()}
      {_RATIO}
      {share}
      {_rate_cols()}
FROM g
ORDER BY grp, {order}"""

SQL_DET = _stmt("det")
SQL_GM = _stmt("gm")
SQL_PM = _stmt("pm")
SQL_TOT = _stmt("tot")
SQL_MG = _stmt("mg")
SQL_MM = _stmt("mm")
SQL_MPM = _stmt("mpm")
SQL_MP = _stmt("mp")

with open(OUT_SQL, "w", encoding="utf-8") as f:
    f.write("-- 墨西哥复贷产品分析 v4: V5_3 主资产等级 × 产品 表现总表 (与 .py 同一文本)\n")
    f.write("-- 口径: 老客复贷(old)+放款(if_issue=1)+有产品名; y.v3_flag='V5_3' 且主等级非空; release 2026-06-09~2026-09-01; 按 biz_id join mx.yj_test_table_250225\n")
    f.write("-- 税: 仅后收利息计税(E 含税÷1.16), 前砍费/本金不计税; 成熟窗口 vintage T0/T3/T7/T14/T30; t14 无 flag 用金额>1 代理\n\n")
    for tag, sql in [("Q1 全期明细(产品×评级)", SQL_DET), ("Q2 评级小计(档1~13)", SQL_GM),
                     ("Q3 产品小计", SQL_PM), ("Q4 全量合计", SQL_TOT),
                     ("Q5 月×评级", SQL_MG), ("Q6 月小计", SQL_MM),
                     ("Q7 月度明细(月×产品×评级)", SQL_MPM), ("Q8 月度产品小计(月×产品)", SQL_MP)]:
        f.write(f"-- ==== {tag} ====\n")
        f.write(sql.strip() + ";\n\n")
print(f"[SQL] 已落盘 -> {OUT_SQL}")
if os.environ.get("SQL_ONLY"):
    sys.exit(0)

pq = PrestoQuery(); pq.login()
def q(sql, retry=4):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r):
            print(f"[重登] {i + 1}次"); pq.login(); continue
        return r
    raise SystemExit(f"[查询失败] {r}")

def _num(df):
    if df is None or not hasattr(df, "columns") or len(df) == 0:
        return df
    for c in df.columns:
        if c not in ("grp", "product_name"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

_CACHE = os.path.join(HERE, ".v4cache")
def _q(name, sql):
    if os.environ.get("USE_CACHE"):
        p = os.path.join(_CACHE, name + ".csv")
        if os.path.exists(p):
            return _num(pd.read_csv(p))
    r = q(sql)
    if isinstance(r, str):
        print(f"[{name}] 查询返回错误串:"); print(r); raise SystemExit(1)
    df = _num(r)
    if os.environ.get("USE_CACHE"):
        os.makedirs(_CACHE, exist_ok=True); df.to_csv(p, index=False)
    return df

print("[查询] Q1 全期明细(产品×评级)..."); det = _q("det", SQL_DET)
print(f"[明细] {len(det)} 行")
print("[查询] Q2 评级小计..."); gm = _q("gm", SQL_GM)
print("[查询] Q3 产品小计..."); pm = _q("pm", SQL_PM)
print("[查询] Q4 全量合计..."); tot = _q("tot", SQL_TOT)
print("[查询] Q5 月×评级..."); mg = _q("mg", SQL_MG)
print("[查询] Q6 月小计..."); mm = _q("mm", SQL_MM)
print("[查询] Q7 月度明细(月×产品×评级)..."); mpm = _q("mpm", SQL_MPM)
print(f"[月度明细] {len(mpm)} 行")
print("[查询] Q8 月度产品小计(月×产品)..."); mpmonth = _q("mp", SQL_MP)

def _grade_int(df):
    df = df.copy()
    df["grade"] = df["grade"].fillna(-1).astype(int).replace(-1, pd.NA)
    return df
det = _grade_int(det); gm = _grade_int(gm); mg = _grade_int(mg); mpm = _grade_int(mpm)
for d in (pm, tot, mm, mpmonth):
    d = d.copy(); d["grade"] = pd.NA
# 重新赋值 pm/tot/mm/mpmonth (上面循环里副本没写回)
pm["grade"] = pd.NA; tot["grade"] = pd.NA; mm["grade"] = pd.NA; mpmonth["grade"] = pd.NA

# ── 零差校验 ──
errs = []
mp = det.groupby("product_name", dropna=False)[["loans", "ca"]].sum().reset_index().merge(
    pm[["product_name", "loans", "ca"]].rename(columns={"loans": "pl", "ca": "pca"}), on="product_name", how="outer")
errs.append(("产品小计", float((mp["loans"] - mp["pl"].fillna(0)).abs().max() if len(mp) else 0),
             float((mp["ca"] - mp["pca"].fillna(0)).abs().max() if len(mp) else 0)))
mgp = det.groupby("grade", dropna=False)[["loans", "ca"]].sum().reset_index().merge(
    gm[["grade", "loans", "ca"]].rename(columns={"loans": "gl", "ca": "gca"}), on="grade", how="outer")
errs.append(("评级小计", float((mgp["loans"] - mgp["gl"].fillna(0)).abs().max() if len(mgp) else 0),
             float((mgp["ca"] - mgp["gca"].fillna(0)).abs().max() if len(mgp) else 0)))
errs.append(("全量合计", float(abs(det["loans"].sum() - tot.iloc[0]["loans"])), float(abs(det["ca"].sum() - tot.iloc[0]["ca"]))))
mm_agg = mg.groupby("grp", dropna=False)[["loans", "ca"]].sum().reset_index().merge(
    mm[["grp", "loans", "ca"]].rename(columns={"loans": "ml", "ca": "mca"}), on="grp", how="outer")
errs.append(("月×评级→月小计", float((mm_agg["loans"] - mm_agg["ml"].fillna(0)).abs().max() if len(mm_agg) else 0),
             float((mm_agg["ca"] - mm_agg["mca"].fillna(0)).abs().max() if len(mm_agg) else 0)))
# 月度明细 vs 全期明细 / 月×产品小计 / 月小计
md_agg = mpm.groupby(["grp", "product_name"], dropna=False)[["loans", "ca"]].sum().reset_index().merge(
    mpmonth[["grp", "product_name", "loans", "ca"]].rename(columns={"loans": "ml", "ca": "mca"}), on=["grp", "product_name"], how="outer")
errs.append(("月产品×档→月产品小计", float((md_agg["loans"] - md_agg["ml"].fillna(0)).abs().max() if len(md_agg) else 0),
             float((md_agg["ca"] - md_agg["mca"].fillna(0)).abs().max() if len(md_agg) else 0)))
md2 = mpm.groupby("grp", dropna=False)[["loans", "ca"]].sum().reset_index().merge(
    mm[["grp", "loans", "ca"]].rename(columns={"loans": "ml", "ca": "mca"}), on="grp", how="outer")
errs.append(("月×产品×档→月合计", float((md2["loans"] - md2["ml"].fillna(0)).abs().max() if len(md2) else 0),
             float((md2["ca"] - md2["mca"].fillna(0)).abs().max() if len(md2) else 0)))
mpm_all = mpm.groupby("product_name", dropna=False)[["loans", "ca"]].sum().reset_index().merge(
    pm[["product_name", "loans", "ca"]].rename(columns={"loans": "pl", "ca": "pca"}), on="product_name", how="outer")
errs.append(("月度明细跨月加总→全期产品", float((mpm_all["loans"] - mpm_all["pl"].fillna(0)).abs().max() if len(mpm_all) else 0),
             float((mpm_all["ca"] - mpm_all["pca"].fillna(0)).abs().max() if len(mpm_all) else 0)))
print("\n=== 零差校验(明细加总 vs SQL小计; 应≈0) ===")
ok = True
for name, dl, dc in errs:
    flag = "OK" if abs(dl) < 1e-6 and abs(dc) < 1e-6 else "FAIL"
    if flag == "FAIL": ok = False
    print(f"  [{flag}] {name}: 笔数差={dl:.4f}, 金额差={dc:.4f}")

print("\n=== 评级档 质量方向(档1=最优) ===")
print(gm.sort_values("grade")[["grade", "loans", "avg_ca", "t0_cntrate", "t30_amtrate", "fee_net_rate", "tr_net7"]].to_string(index=False))

# ── 列级公式复核: 用每行原始列(SQL 输出) 镜像 SQL 公式逐行复算全部比率/占比/件均,
#    逐位对比(SQL/Presto 四舍五入远离零, py 侧显式 half-away; 分母0/null 双 NaN 视为一致) ──
import numpy as np

def _rh(x, n):
    x = np.asarray(x, dtype="float64")
    fac = 10.0 ** n
    with np.errstate(invalid="ignore"):
        return np.where(np.isnan(x), np.nan, np.sign(x) * np.floor(np.abs(x) * fac + 0.5) / fac)

def audit_frame(df, with_shares):
    def C(c):
        return df[c].astype("float64").to_numpy()
    loans, custs = C("loans"), C("custs")
    ca, ha, si, si_net = C("ca"), C("ha"), C("si"), C("si_net")
    def safe(a, b, n):
        with np.errstate(divide="ignore", invalid="ignore"):
            d = np.where(np.isnan(b) | (b == 0), np.nan, a / b)
        return _rh(d, n)
    exp = {"avg_ca": safe(ca, loans, 2),
           "loans_cust": safe(loans, custs, 4),
           "ha_rate": safe(ha, ca, 4),
           "si_rate": safe(si, ca, 4),
           "si_net_rate": safe(si_net, ca, 4),
           "fee_net_rate": safe(ha + si_net, ca, 4),
           "vat_ca_rate": safe(si_net * 0.16, ca, 4)}
    t7ca = C("t7_mature_ca"); t7ha = C("t7_mature_ha"); t7si = C("t7_mature_si_net"); t7ovd = C("t7_mature_ovd")
    exp["tr_net7"] = safe(t7ha + t7si - t7ovd, t7ca, 4)
    exp["t7_ovd_amtrate_ca"] = safe(t7ovd, t7ca, 4)
    for W in _WINS:
        mc, sh, ovd, oc = C(f"{W}_mature_cnt"), C(f"{W}_should_amt"), C(f"{W}_overdue_amount"), C(f"{W}_ovd_cnt")
        exp[f"{W}_mature_rate"] = safe(mc, loans, 4)
        exp[f"{W}_cntrate"] = safe(oc, mc, 4)
        exp[f"{W}_amtrate"] = safe(ovd, sh, 4)
    # 占比列仅 det 帧真实存在(SQL 填值); 其余帧 SQL 输出 NULL, 复算无意义
    if with_shares:
        exp["loans_share_g"] = safe(loans, df.groupby("grade", dropna=False)["loans"].transform("sum").astype("float64").to_numpy(), 4)
        exp["ca_share_g"] = safe(ca, df.groupby("grade", dropna=False)["ca"].transform("sum").astype("float64").to_numpy(), 4)
        exp["loans_share_p"] = safe(loans, df.groupby("product_name", dropna=False)["loans"].transform("sum").astype("float64").to_numpy(), 4)
        exp["ca_share_p"] = safe(ca, df.groupby("product_name", dropna=False)["ca"].transform("sum").astype("float64").to_numpy(), 4)
    fails = []
    for col, e in exp.items():
        a = C(col)
        same = np.isclose(a, e, rtol=0, atol=0, equal_nan=True)
        nbad = int((~same).sum())
        if nbad:
            idx = int(np.where(~same)[0][0])
            fails.append(f"{col}: {nbad}行不符, 例row{idx} sql={a[idx]!r} vs 复算={e[idx]!r}")
    return len(exp), fails

audits = []
for tag, fr, has_sh in [("全期明细 产品×评级", det, True), ("评级小计", gm, False), ("产品小计", pm, False),
                        ("全量合计", tot, False), ("月×评级", mg, False), ("月小计", mm, False),
                        ("月度明细 月×产品×评级", mpm, False), ("月度产品小计", mpmonth, False)]:
    nc, fails = audit_frame(fr, has_sh)
    audits.append((tag, int(len(fr)), nc, fails))
    print(f"[列级复核] {tag}: {len(fr)}行 x {nc}比率/占比列 -> " + ("全部一致" if not fails else f"{len(fails)} 列不符"))
    for fl in fails:
        print("      ", fl)

# ── Excel 装配 ──
import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()
HDR_FILL = PatternFill("solid", fgColor="1F4E78"); HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
SUB_FILL = PatternFill("solid", fgColor="DDEBF7"); SUB_FONT = Font(bold=True, color="1F4E78")
TOT_FILL = PatternFill("solid", fgColor="FFF2CC"); TOT_FONT = Font(bold=True, color="C00000")

def cn_head(c):
    m = {"grp": "期", "product_name": "产品", "grade": "主等级V5_3",
         "loans": "放款笔数", "custs": "复贷客数", "ca": "放款金额", "ha": "前砍费",
         "si": "后收利息", "si_net": "后收净息", "avg_ca": "件均", "loans_cust": "人均件数",
         "ha_rate": "前砍率", "si_rate": "后收率", "si_net_rate": "后收净率",
         "fee_net_rate": "总息费净率", "vat_ca_rate": "息费税占合同%",
         "loans_share_g": "档内产品笔数占比", "ca_share_g": "档内产品金额占比",
         "loans_share_p": "产品内档位笔数占比", "ca_share_p": "产品内档位金额占比",
         "t7_mature_ca": "T7成熟合同额", "t7_mature_ovd": "T7成熟逾期额",
         "tr_net7": "TR净%(T7,税后)", "t7_ovd_amtrate_ca": "T7逾期额/合同%",
         "grade_str": "档位:笔数结构"}
    for W in _WINS:
        m[f"{W}_mature_cnt"] = f"{W}成熟笔数"; m[f"{W}_mature_rate"] = f"{W}成熟率"
        m[f"{W}_ovd_cnt"] = f"{W}逾期笔数"; m[f"{W}_cntrate"] = f"{W}首逾率%(笔数)"
        m[f"{W}_should_amt"] = f"{W}成熟应还"; m[f"{W}_overdue_amount"] = f"{W}成熟逾期额"
        m[f"{W}_amtrate"] = f"{W}金额逾期率"
    return m.get(c, c)

def fmt_of(c):
    if c in ("grp", "product_name", "grade", "grade_str"):
        return None
    if c in ("loans", "custs") or c.endswith("_cnt"):
        return "#,##0"
    if c.endswith("_rate") or c in ("tr_net7", "t7_ovd_amtrate_ca",
                                    "loans_share_g", "ca_share_g", "loans_share_p", "ca_share_p"):
        return "0.00%"
    return "#,##0.00"

def clean(v):
    if v is None: return None
    try:
        if pd.isna(v): return None
    except (TypeError, ValueError):
        pass
    return v

def emit(ws, eng_df, note=None, subtotal=None):
    """eng_df: 英文列 df; subtotal: 与行同长的类别列表('sub'/'tot'/None), 决定加粗底纹"""
    note = note if isinstance(note, list) else ([note] if note else [])
    r0 = len(note) + 1
    for j, n in enumerate(note, 1):
        ws.append([n]); ws.merge_cells(start_row=j, start_column=1, end_row=j, end_column=max(len(eng_df.columns), 1))
        ws.cell(j, 1).font = Font(bold=True, size=10, color="C00000")
    heads = [cn_head(c) for c in eng_df.columns]
    fmts = [fmt_of(c) for c in eng_df.columns]
    ws.append(heads)
    for cell in ws[r0]: cell.fill, cell.font = HDR_FILL, HDR_FONT
    data0 = r0 + 1
    for r, row in enumerate(eng_df.itertuples(index=False), start=data0):
        ws.append([clean(v) for v in row])
        kind = subtotal[r - data0] if subtotal else None
        if kind:
            for cell in ws[r]:
                if kind == "sub": cell.fill, cell.font = SUB_FILL, SUB_FONT
                else: cell.fill, cell.font = TOT_FILL, TOT_FONT
    for i, (c, f) in enumerate(zip(eng_df.columns, fmts), 1):
        L = get_column_letter(i)
        w = max((len(str(v)) for v in eng_df.iloc[:, i - 1].tolist()), default=0)
        ws.column_dimensions[L].width = min(max(w, len(str(heads[i - 1])), 8) + 2, 46)
        if f:
            for rowcell in ws.iter_rows(min_row=data0, min_col=i, max_col=i):
                cell = rowcell[0]
                if isinstance(cell.value, (int, float)): cell.number_format = f
    ws.freeze_panes = ws.cell(data0, 1)
    return data0

note_main = ["★ 人群: 老客复贷放款 release 2026-06-09~2026-09-01, y.v3_flag='V5_3' 且主资产等级非空(≈10.0万单, 占同期老客95%+)",
             "★ 评级=android_oldcust_maincreditlevel_charge_v5_3(档1~13); 实测档号越大首逾越高/件均越小 → 1=最优、13=最差",
             "★ 表按 biz_id 联 funnel×yj_test_table_250225 取评级; 成熟窗口 vintage T0/T3/T7/T14/T30, is_tN_window=1 才计入",
             "★ 税: 前砍费 ha/本金 ca 不计税不÷1.16; 后收利息 si: E 开头产品(含税)→净=si÷1.16 其余=si; 息费税(估)=净息×16%",
             "★ 首逾率%=逾期笔数÷成熟笔数(funnel flag, t14 用金额>1 代理); 金额逾期率=Σ逾期额÷Σ成熟应还; 比率 round4, 除法 CAST AS DOUBLE",
             "★ TR净%(T7,税后)=(T7成熟前砍+T7成熟净后收−T7成熟逾期额)÷T7成熟合同额; 8月近端放款 T30/T14 成熟率低=观察窗未满属正常",
             "★ 占比双口径: 档内产品占比(评级的钱流向哪些产品)/产品内档位占比(产品被哪些档用); 指标全 SQL 计算, py 仅改名/拼小计",
             "★ 两张明细: 『明细_产品×评级』=全期合计; 『月度明细_产品×评级×月』=按月拆开(期列=2026-06/07/08), 每月逐产品小计+月合计; 评级×月附表=仅档级按月"]
ws = wb.active; ws.title = "说明"
for n in note_main:
    ws.append([n]); ws.cell(ws.max_row, 1).font = Font(bold=True, size=10, color="C00000")
ws.column_dimensions["A"].width = 150

DET_KEYS = (["grp", "product_name", "grade", "loans", "custs", "ca", "ha", "si", "si_net",
             "avg_ca", "loans_cust", "loans_share_g", "ca_share_g", "loans_share_p", "ca_share_p",
             "fee_net_rate", "si_net_rate", "vat_ca_rate", "tr_net7", "t7_ovd_amtrate_ca"]
            + [f"{W}_{s}" for W in _WINS for s in ("mature_cnt", "mature_rate", "should_amt", "overdue_amount", "ovd_cnt", "cntrate", "amtrate")])
DET_KEYS = list(dict.fromkeys(DET_KEYS))
det_k = det[DET_KEYS]

# —— 明细: 产品×评级 + 每产品插『产品小计』, 末尾『全量合计』——
pm_order = pm.sort_values("ca", ascending=False)["product_name"].tolist()
parts, kinds = [], []
for pname in pm_order:
    sub = det_k[det_k["product_name"] == pname]
    if len(sub):
        parts.append(sub); kinds += [None] * len(sub)
    psrc = pm[pm["product_name"] == pname].iloc[0]
    row = {c: None for c in DET_KEYS}; row["product_name"] = pname
    for c in DET_KEYS:
        if c != "product_name": row[c] = psrc.get(c) if c in psrc.index else None
    parts.append(pd.DataFrame([row])); kinds.append("sub")
tsrc = tot.iloc[0]
row = {c: None for c in DET_KEYS}
for c in DET_KEYS:
    if c not in ("product_name", "grade"): row[c] = tsrc.get(c)
parts.append(pd.DataFrame([row])); kinds.append("tot")
det_full = pd.concat(parts, ignore_index=True)
ws = wb.create_sheet("明细_产品×评级")
emit(ws, det_full, note="全期 产品×主等级V5_3(档1~13): 完整指标; 每个产品下插『产品小计』(该产品全档合计), 末行『全量合计』; 排序=产品按放款额降序×档升序",
     subtotal=kinds)

# —— 月度明细: 期(月) × 产品×评级, 每月每产品插小计 + 月末合计 ——
months = sorted(mm["grp"].astype(str).unique())
mpm_show = mpm[DET_KEYS].copy()
mpm_show["_mm"] = mpm_show["grp"].astype(str)
mpm_show["_gg"] = mpm_show["grade"].astype("Int64")
mpm_show = mpm_show.sort_values(["_mm", "product_name", "_gg"]).reset_index(drop=True)
mpidx = mpmonth.set_index(["grp", "product_name"])
mmidx = mm.set_index("grp")
parts, kinds = [], []
for m in months:
    sub = mpm_show[mpm_show["_mm"] == m]
    for pname in pm_order:  # 与全期主表同产品序(按全期放款额降序), 便于跨月对照
        prow = sub[sub["product_name"] == pname]
        if len(prow):
            parts.append(prow[DET_KEYS]); kinds += [None] * len(prow)
            row = {c: None for c in DET_KEYS}; row["grp"] = m; row["product_name"] = pname
            if (m, pname) in mpidx.index:
                mrow = mpidx.loc[(m, pname)]
                for c in DET_KEYS:
                    if c in mrow.index: row[c] = mrow[c]
            parts.append(pd.DataFrame([row])); kinds.append("sub")
    mrow = mmidx.loc[m]
    row = {c: None for c in DET_KEYS}; row["grp"] = m
    for c in DET_KEYS:
        if c not in ("product_name", "grade") and c in mrow.index: row[c] = mrow[c]
    parts.append(pd.DataFrame([row])); kinds.append("tot")
ws = wb.create_sheet("月度明细_产品×评级×月")
emit(ws, pd.concat(parts, ignore_index=True),
     note=["月度明细: 期=放款月(2026-06/07/08), 每月 产品×主等级V5_3 逐行(完整指标); 每个产品下插该月『产品小计』, 每月末『月合计』",
           "与『明细_产品×评级』同构只是加『期』列; 产品排序=全期放款额降序×档升序; 8月近端 T30/T14 成熟率低属正常"],
     subtotal=kinds)

# —— 评级小计 ——
gm_show = gm.sort_values("grade")[DET_KEYS]
parts, kinds = [gm_show], [None] * len(gm_show)
row = {c: None for c in DET_KEYS}
for c in DET_KEYS:
    if c not in ("product_name", "grade"): row[c] = tot.iloc[0].get(c)
parts.append(pd.DataFrame([row])); kinds.append("tot")
emit(wb.create_sheet("评级小计_档位"), pd.concat(parts, ignore_index=True),
     note=["评级小计(档1~13, 全产品合计): 各评级人群总量与贷后质量; 档越大首逾越高/件均越小",
           "行尾为全量合计; 每档的钱流向哪些产品(档内占比)请看『明细_产品×评级』sheet 的 档内产品笔数/金额占比"],
     subtotal=kinds)

# —— 产品小计 + 档位结构 ——
gser = det.assign(g_=det["grade"].astype("Int64")).groupby("product_name", dropna=False).apply(
    lambda d: "|".join(f"{int(r.g_)}:{int(r.loans)}" for r in d.sort_values("g_").itertuples()), include_groups=False)
pm_show = pm.sort_values("ca", ascending=False)[DET_KEYS].copy()
pm_show["grade_str"] = pm_show["product_name"].map(gser)
parts, kinds = [pm_show], [None] * len(pm_show)
row = {c: None for c in pm_show.columns}
for c in pm_show.columns:
    if c in tot.columns: row[c] = tot.iloc[0].get(c)
row["grade_str"] = None
parts.append(pd.DataFrame([row])); kinds.append("tot")
emit(wb.create_sheet("产品小计"), pd.concat(parts, ignore_index=True),
     note=["产品小计(V5_3 cohort 全档合计): 产品规模与质量; 『档位:笔数结构』=档:笔数|..., 见该产品被哪些评级用",
           "排序按放款金额降序"],
     subtotal=kinds)

# —— 评级×月 附表(每月 13 档 + 月合计) ——
K_MON = ["grp", "grade", "loans", "custs", "ca", "avg_ca", "loans_cust",
         "t0_mature_cnt", "t0_mature_rate", "t0_cntrate", "t0_amtrate",
         "t30_mature_cnt", "t30_mature_rate", "t30_cntrate", "t30_amtrate"]
parts, kinds = [], []
mg_s = mg.sort_values(["grp", "grade"])
for m in sorted(mm["grp"].astype(str).unique()):
    sub = mg_s[mg_s["grp"].astype(str) == m]
    if len(sub):
        parts.append(sub[K_MON]); kinds += [None] * len(sub)
    mr = mm[mm["grp"].astype(str) == m].iloc[0]
    row = {c: None for c in K_MON}; row["grp"] = m
    for c in K_MON:
        if c != "grade": row[c] = mr.get(c) if c in mr.index else None
    parts.append(pd.DataFrame([row])); kinds.append("sub")
emit(wb.create_sheet("评级×月附表"), pd.concat(parts, ignore_index=True),
     note=["按月×评级看量级与首逾(T0 成熟组)及长尾(T30 成熟组; 8月未满月多为空); 每月末插『月合计』; 档1最优→13最差"],
     subtotal=kinds)

# —— 矩阵: 行=评级档 1~13, 列=产品(按放款额降序) ——
mat_prod = pm_order
MTRX = {"loans": ("放款笔数", "#,##0"), "t0_cntrate": ("T0首逾率%(笔数)", "0.00%"),
        "t30_amtrate": ("T30金额逾期率", "0.00%"), "fee_net_rate": ("总息费净率", "0.00%"),
        "tr_net7": ("TR净%(T7,税后)", "0.00%")}
det_idx = det.set_index(["grade", "product_name"])
for metric, (title, fmt) in MTRX.items():
    ws = wb.create_sheet("矩阵_" + title.split("%")[0].replace("(", "")[:14])
    note = [f"矩阵_{title}: 行=主等级V5_3档(1最优→13最差), 列=产品(全期放款额降序); 空=无放款/未成熟/分母0",
            "数值来自『明细_产品×评级』SQL 结果, 无现算; 末列=该档合计"]
    ws.append([note[0]]); ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(mat_prod) + 2)
    ws.cell(1, 1).font = Font(bold=True, size=10, color="C00000")
    ws.append([note[1]]); ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(mat_prod) + 2)
    ws.cell(2, 1).font = Font(bold=True, size=9, color="808080")
    gmetric = "loans" if metric == "loans" else metric
    gvals = gm.set_index("grade")[gmetric]
    head = ["评级档"] + mat_prod + ["该档合计"]
    ws.append(head)
    for cell in ws[3]: cell.fill, cell.font = HDR_FILL, HDR_FONT
    data0 = 4
    for g in range(1, 14):
        vals = [det_idx.loc[(g, p), metric] if (g, p) in det_idx.index else None for p in mat_prod]
        ws.append([g] + vals + [gvals.get(g)])
    for i in range(2, len(head) + 1):
        L = get_column_letter(i)
        ws.column_dimensions[L].width = max(max(len(p) for p in head[1:]) + 2, 9)
        for rowcell in ws.iter_rows(min_row=data0, min_col=i, max_col=i):
            cell = rowcell[0]
            if isinstance(cell.value, (int, float)): cell.number_format = fmt
    ws.column_dimensions["A"].width = 8
    ws.freeze_panes = "B4"

# —— 校验零差 ——
_chk_ws = wb.create_sheet("校验零差")
_chk_ws.append(["校验", "结果", "说明"])
for c in _chk_ws[1]: c.fill, c.font = HDR_FILL, HDR_FONT
for name, dl, dc in errs:
    _chk_ws.append([name, "通过" if abs(dl) < 1e-6 and abs(dc) < 1e-6 else "失败",
                    f"笔数差={dl:.4f} 金额差={dc:.4f}"])
_chk_ws.append(["整体通过", "是" if ok else "否", "明细加总恒等于 SQL 小计"])
for c in _chk_ws[_chk_ws.max_row]: c.font = Font(bold=True, color="C00000")
_chk_ws.column_dimensions["A"].width = 22; _chk_ws.column_dimensions["B"].width = 10; _chk_ws.column_dimensions["C"].width = 30

# —— 复核: 列级公式逐行复算 ——
_au_ws = wb.create_sheet("复核_列级公式")
_au_ws.append(["数据表", "行数", "复算比率/占比列数", "结果", "不符明细(首个)"])
for c in _au_ws[1]: c.fill, c.font = HDR_FILL, HDR_FONT
all_ok = True
for tag, nrows, ncol, fails in audits:
    fl = len(fails) == 0
    all_ok = all_ok and fl
    _au_ws.append([tag, nrows, ncol, "全部一致" if fl else f"{len(fails)}列不符", fails[0] if fails else "—"])
_au_ws.append(["整体", sum(a[1] for a in audits), sum(a[2] for a in audits),
               "通过" if all_ok else "失败", "镜像 SQL 公式 round(half-away) 逐位比对, 双NaN视为一致"])
for c in _au_ws[_au_ws.max_row]: c.font = Font(bold=True, color="C00000")
for i, wd in enumerate(["A", "B", "C", "D", "E"], 1):
    _au_ws.column_dimensions[wd].width = [26, 8, 16, 12, 90][i - 1]

wb.save(OUT_XLSX)
print(f"\n[输出] {OUT_XLSX}")
print(f"[规模] 明细产品×评级组合: {len(det)} | 评级档: {gm['grade'].nunique()} | 产品数: {len(pm)} | 全量笔数: {int(tot.iloc[0]['loans'])}")
print("完成。")
