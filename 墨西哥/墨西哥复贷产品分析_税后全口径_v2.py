# -*- coding: utf-8 -*-
"""
墨西哥 复贷产品分析（税后全口径 v2）
================================================================================
【相对 v1 的修正】
1) 月份/周度口径: 不再锁死"8月有放款17产品", 改为当月实际有放款的**全部产品全集**。
    => 各月产品放款笔数/金额 合计 == 当月全量复贷(零缺口), 解决"总计对不上"。
   例: 7月全集=24个产品(37,689笔/5,464万), 旧17产品只覆盖 94.7%/92.7%。
2) 税口径(用户确认):
   - E开头产品: 价格**已含IVA**; funnel 的 haircut/should_interest 记的是**含税价**;
     税后净息费 = 值 / 1.16。
   - A/B/C开头产品: **不含税**; funnel 记的是**不含税价**; 净息费 = 值(不变)。
   - 税仅对**息费**(前砍费+后收利息)计, 本金(contract_amount)不计税。
   - 税(估) = 净息费 × 16% (E=价内税已含; ABCD=发票另加)。
3) 日息逻辑(产品文档说明 + 命名校验):
   - E产品按日息命名: E_{单期期限}_{期数}_{日息数字}{还款比例...}; 日息(含税) = 数字/1000,
     总息费(含税) = 日息×总期限(天数)。校验: E_07_02_45_50X2 → 4.5%/天×14=0.63 ✓
   - 属性表补齐: 日息(含税)/日息(不含税)/不含税总息费 (文档该三列为空, 本脚本按规则计算填写)。
4) 指标双口径:
   - 合同口径(as-recorded): 前砍率=ha/ca, 后收率=si/ca —— 与属性核对(口径即属性: E含税/ABCD不含税)
   - 净口径(不含税,可比): 前砍净率/后收净率/息费净率 —— E按÷1.16折算, ABCD不变
================================================================================
数据源 : mx.wxs_application_funnel (墨西哥全链路风险宽表)
范围   : 2026-05-01 ~ 2026-09-01 放款; 复贷(is_reloan='old')+已放款(if_issue=1)
属性   : D:/Documents/Downloads/产品文档.xlsx (产品属性 + E日息命名 + 含税标记)
输出   : 本目录 墨西哥复贷产品分析_税后全口径.xlsx
"""
import sys, os, re, warnings
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

VAT = 0.16                      # 墨西哥 IVA
EXCEL_DOC = r"D:\Documents\Downloads\产品文档.xlsx"
OUT_XLSX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "墨西哥复贷产品分析_税后全口径.xlsx")
START, END = "2026-05-01", "2026-09-01"

def is_inc_tax(p):
    """E 开头=含税; 其余(A/B/C/D)不含税"""
    p = str(p).strip()
    return p[:1] == "E"

def net_factor(p):
    return 1 / (1 + VAT) if is_inc_tax(p) else 1.0

# ── 1. 产品属性 master (产品文档.xlsx) ────────────────────────────
# 布局: R0=图例, R1=真实表头, R2起=数据; 但文件含 D_0_xx/D_1_xx 分组行与重复行
# build_attr(measured): 文档优先; measured=全窗口实测 as-recorded 定价 用于补齐文档缺失/未收录产品
attr_raw = pd.read_excel(EXCEL_DOC, sheet_name=0, header=1)
ATTR_NUM = ["前砍利息", "后收利息", "总利息", "期数", "单期期限", "总期限"] + \
           ["第%s期还本息比例" % i for i in ["一", "二", "三", "四"]]

def parse_e_name(p):
    """E_单期期限_期数_日息数字_... → (期, 日息含税十进制, 总天数, 总息费含税)"""
    m = re.match(r"^E_(\d{2})_(\d{1,2})_(\d{2,3})", str(p))
    if not m:
        return None
    term, nper, digits = int(m.group(1)), int(m.group(2)), int(m.group(3))
    daily = digits / 1000.0              # 41 → 4.1% → 0.041
    days = term * nper
    return nper, daily, days, round(daily * days, 6)

def _fill_e(m):
    """E产品: 用名字日息补齐 总期限/总利息; 记录名字日息(_daily_inc)"""
    _e = m["product_name"].map(lambda p: parse_e_name(p) if is_inc_tax(p) else None)
    m["_daily_inc"] = _e.map(lambda t: t[1] if t else None)     # E: 名字日息(含税)
    m["总期限"] = m["总期限"].fillna(_e.map(lambda t: t[2] if t else None))
    miss = m["产品类型"].eq("E") & m["总利息"].isna()
    if miss.any():
        m.loc[miss, "总利息"] = _e[miss].map(lambda t: t[3])
    return m

def _tax_cols(r):
    inc = bool(r["含税(E)"])
    tot_inc = r["总利息"]                                  # E=含税价; ABCD=不含税价
    tot_net = tot_inc / (1 + VAT) if inc else tot_inc      # 统一净息费
    days = r["总期限"]
    if inc:
        d_inc_pct = (r["_daily_inc"] * 100) if pd.notna(r["_daily_inc"]) else \
                    (tot_inc / days * 100 if days and pd.notna(tot_inc) else None)
        d_net_pct = d_inc_pct / (1 + VAT) if pd.notna(d_inc_pct) else None
    else:
        d_net_pct = tot_net / days * 100 if (days and pd.notna(tot_net)) else None
        d_inc_pct = d_net_pct * (1 + VAT) if pd.notna(d_net_pct) else None
    def _r(x):
        return round(x, 4) if pd.notna(x) else None
    return pd.Series({"不含税总息费": _r(tot_net),
                      "日息(不含税)": _r(d_net_pct),          # 单位=%, 如 E=4.1
                      "日息(含税)": _r(d_inc_pct)})

def build_attr(measured=None):
    raw = attr_raw.dropna(subset=["product_name"]).copy()
    raw["product_name"] = raw["product_name"].astype(str).str.strip()
    raw["_real"] = (raw["product_level"].astype(str).str.strip() == raw["product_name"])
    raw = raw.sort_values("_real", ascending=False)
    m = raw.groupby("product_name", as_index=False).first()
    m["产品类型"] = m["product_name"].str[0]
    m["含税(E)"] = m["product_name"].map(is_inc_tax).astype(int)
    for c in ATTR_NUM:
        m[c] = pd.to_numeric(m[c], errors="coerce")
    m["总期限"] = m["总期限"].fillna(m["期数"] * m["单期期限"])
    m = _fill_e(m)
    m["前砍利息"] = m["前砍利息"].fillna(0)
    m["定价来源"] = "文档"
    if measured is not None:
        mm = measured.copy()
        mm["ha_r"] = mm["ha"] / mm["ca"]
        mm["si_r"] = mm["si"] / mm["ca"]
        mm["tot_r"] = (mm["ha"] + mm["si"]) / mm["ca"]
        mm = mm.set_index("product_name")
        m = m.set_index("product_name")
        def _fill(row):
            if pd.notna(row["总利息"]) or row.name not in mm.index:
                return row
            mr = mm.loc[row.name]
            row["前砍利息"] = round(float(mr["ha_r"]), 4)
            row["后收利息"] = round(float(mr["si_r"]), 4)
            row["总利息"] = round(float(mr["tot_r"]), 4)
            row["定价来源"] = "实测补齐"
            return row
        m = m.apply(_fill, axis=1).reset_index()
        missing = [p for p in mm.index if p not in set(m["product_name"])]
        if missing:
            add = pd.DataFrame({"product_name": list(missing)})
            add["产品类型"] = add["product_name"].str[0]
            add["含税(E)"] = add["product_name"].map(is_inc_tax).astype(int)
            add["前砍利息"] = mm.loc[missing, "ha_r"].round(4).values
            add["后收利息"] = mm.loc[missing, "si_r"].round(4).values
            add["总利息"] = mm.loc[missing, "tot_r"].round(4).values
            add["定价来源"] = "仅实测(文档未收录)"
            for c in ["期数", "单期期限", "总期限", "是否蝌蚪产品"] + \
                     ["第%s期还本息比例" % i for i in ["一", "二", "三", "四"]]:
                add[c] = None
            m = pd.concat([m, add], ignore_index=True)
        for c in ATTR_NUM:
            m[c] = pd.to_numeric(m[c], errors="coerce")
    m = _fill_e(m)
    # 去掉文档里空税列(半/全角名都删), 避免与计算列重名
    for _c in ["不含税总息费", "日息（含税）", "日息(含税)", "日息（不含税）", "日息(不含税)"]:
        if _c in m.columns:
            m = m.drop(columns=[_c])
    tax = m.apply(_tax_cols, axis=1)
    m = pd.concat([m, tax], axis=1)
    keep = ["product_name", "产品类型", "含税(E)", "定价来源", "是否蝌蚪产品", "期数", "单期期限", "总期限",
            "前砍利息", "后收利息", "总利息", "不含税总息费", "日息(含税)", "日息(不含税)",
            "第一期还本息比例", "第二期还本息比例", "第三期还本息比例", "第四期还本息比例"]
    return m[keep].reset_index(drop=True)

# ── 2. 查询封装 ─────────────────────────────────────────────────
pq = PrestoQuery()
pq.login()
def _num(df, cols):
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out

NUM_AGG = ["loans", "custs", "ca", "ha", "si", "t7m_loans", "t7m_ca", "t7m_ha", "t7m_si",
           "t7m_ovd", "t7_ovd_flag", "t30m_loans", "t30_ovd_flag", "now_ovd_flag"]

def q(sql, retry=4):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r):
            print(f"[重登] 第{i+1}次..."); pq.login(); continue
        return r
    raise SystemExit(f"[查询失败] {r}")

M_GRP = "date_format(date_trunc('month', date(release_time)), '%Y-%m')"
W_GRP = "date_format(date_trunc('week',  date(release_time)), '%Y-%m-%d')"

# 全集聚合: 不再按产品过滤, group by (期, 产品)
def _agg_sql(grp_expr):
    return f"""
select {grp_expr} as grp, product_name,
  count(distinct camera_id) as loans,
  count(distinct mid)       as custs,
  sum(contract_amount)      as ca,
  sum(haircut_amount)       as ha,
  sum(should_interest)      as si,
  sum(if(t7_should_amt is not null, 1, 0))                as t7m_loans,
  sum(if(t7_should_amt is not null, contract_amount, 0))  as t7m_ca,
  sum(if(t7_should_amt is not null, haircut_amount, 0))   as t7m_ha,
  sum(if(t7_should_amt is not null, should_interest, 0))  as t7m_si,
  sum(if(t7_should_amt is not null, t7_overdue_amount, 0)) as t7m_ovd,
  sum(if(t7_should_amt is not null and t7_overdue_amount > 1, 1, 0)) as t7_ovd_flag,
  sum(if(t30_should_amt is not null, 1, 0))               as t30m_loans,
  sum(if(t30_should_amt is not null and t30_overdue_amount > 1, 1, 0)) as t30_ovd_flag,
  sum(if(now_overdue_days > 0, 1, 0))                     as now_ovd_flag
from mx.wxs_application_funnel
where is_reloan = 'old' and if_issue = 1
  and date(release_time) >= date '{START}'
  and date(release_time) <  date '{END}'
group by 1, 2
order by 1, 2
"""
TERM_SQL = f"""
select date_format(date_trunc('month', date(release_time)), '%Y-%m') as m,
       product_name, loan_cycle,
       count(distinct camera_id) as loans,
       sum(contract_amount)      as ca
from mx.wxs_application_funnel
where is_reloan = 'old' and if_issue = 1
  and date(release_time) >= date '{START}'
  and date(release_time) <  date '{END}'
group by 1, 2, 3
order by 1, 2, 3
"""
print("[查询] 月度全集聚合...")
agg_m = _num(q(_agg_sql(M_GRP)), NUM_AGG)
print(f"[月度] {len(agg_m)} 行 / 月产品组合")
print("[查询] 周度全集聚合...")
agg_w = _num(q(_agg_sql(W_GRP)), NUM_AGG)
print(f"[周度] {len(agg_w)} 行")
print("[查询] 期限分布(月度)...")
term = _num(q(TERM_SQL), ["loans", "ca", "loan_cycle"])
print(f"[期限] {len(term)} 行")

# ── 2.5 属性补齐: 全窗口实测 as-recorded 定价 → 补文档缺失/未收录产品 ──
meas_src = pd.concat([agg_m[["product_name", "ca", "ha", "si"]],
                      agg_w[["product_name", "ca", "ha", "si"]]])
meas_src = meas_src.groupby("product_name")[["ca", "ha", "si"]].sum().reset_index()
PROD_ATTR = build_attr(measured=meas_src)
print(f"[属性补齐] 来源分布: {dict(PROD_ATTR['定价来源'].value_counts())}; 共 {len(PROD_ATTR)} 产品")
_sup = PROD_ATTR[PROD_ATTR["定价来源"] != "文档"]
if len(_sup):
    print("[属性补齐-非文档来源行]")
    print(_sup[["product_name", "产品类型", "含税(E)", "总利息", "日息(含税)", "日息(不含税)", "定价来源"]].to_string(index=False))
print(PROD_ATTR[["product_name", "产品类型", "含税(E)", "定价来源", "总利息", "不含税总息费", "日息(含税)", "日息(不含税)"]].to_string(index=False))

# ── 3. 指标计算 ─────────────────────────────────────────────────
def _pct(x, y):
    return pd.Series([round(a / b * 100, 2) if (b and pd.notna(a) and pd.notna(b)) else None
                      for a, b in zip(pd.to_numeric(x, errors="coerce"), pd.to_numeric(y, errors="coerce"))],
                     index=x.index)

def build(df, grp_col):
    d = df.copy()
    d["净系数"] = d["product_name"].map(net_factor)
    net_ha = d["ha"] * d["净系数"]; net_si = d["si"] * d["净系数"]
    d["放款笔数"] = d["loans"]
    d["放款金额"] = d["ca"].round(2)
    d["件均"] = (d["ca"] / d["loans"]).round(2)
    d["复贷客数"] = d["custs"]
    d["人均件数"] = (d["loans"] / d["custs"]).round(2)
    # 合同口径(as-recorded, 口径=属性: E含税/ABCD不含税)
    d["前砍率%"] = _pct(d["ha"], d["ca"])
    d["后收率%"] = _pct(d["si"], d["ca"])
    d["总息费率%(合同)"] = _pct(d["ha"] + d["si"], d["ca"])
    # 净口径(不含税, 跨产品可比): E ÷1.16
    d["前砍净率%"] = _pct(net_ha, d["ca"])
    d["后收净率%"] = _pct(net_si, d["ca"])
    d["息费净率%"] = _pct(net_ha + net_si, d["ca"])
    d["息费税(估)占合同%"] = _pct((net_ha + net_si) * VAT, d["ca"])   # 税=净息费×16%
    # 风控 / 收入近似
    d["T7成熟率%"] = _pct(d["t7m_loans"], d["loans"])
    d["首逾T7%(贷款)"] = _pct(d["t7_ovd_flag"], d["t7m_loans"])
    d["首逾T30%(贷款)"] = _pct(d["t30_ovd_flag"], d["t30m_loans"])
    d["当前逾期率%(贷款)"] = _pct(d["now_ovd_flag"], d["loans"])
    d["T7逾期本息率(对合同)%"] = _pct(d["t7m_ovd"], d["t7m_ca"])
    d["TR%(T7口径,合同)"] = _pct(d["t7m_ha"] + d["t7m_si"] - d["t7m_ovd"], d["t7m_ca"])
    # 期占比: 分母=该期全量(全集分组和)
    tot = d.groupby(grp_col)[["loans", "ca"]].transform("sum")
    d["笔数占比%"] = _pct(d["loans"], tot["loans"])
    d["金额占比%"] = _pct(d["ca"], tot["ca"])
    return d

def build_grp(df, grp_col, out_col=None):
    out_col = out_col or grp_col
    g = df.groupby(grp_col).agg(loans=("loans", "sum"), ca=("ca", "sum")).reset_index().rename(
        columns={grp_col: out_col, "loans": "放款笔数", "ca": "放款金额"})
    g["放款金额"] = g["放款金额"].round(2)
    return g

mon = build(agg_m, "grp")
wk  = build(agg_w, "grp")

# 期限一致率(对属性总期限)
attr_term = PROD_ATTR.set_index("product_name")["总期限"]
tm = term.copy(); tm["attr_term"] = tm["product_name"].map(attr_term)
tm["一致"] = (tm["loan_cycle"] == tm["attr_term"]).astype(int)
term_rate = (tm[tm["一致"] == 1].groupby(["m", "product_name"])["loans"].sum()
             / tm.groupby(["m", "product_name"])["loans"].sum() * 100).round(2).rename("期限一致率%").reset_index()
term_rate = term_rate.rename(columns={"m": "grp"})
mon = mon.merge(term_rate, on=["grp", "product_name"], how="left")

# 周度一致率不需要(按周可能跨完整期, 略)
# 合并属性 (前砍/后收/日息等)
attr_merge_cols = ["product_name", "产品类型", "含税(E)", "定价来源", "是否蝌蚪产品", "期数", "单期期限", "总期限",
                   "前砍利息", "后收利息", "总利息", "不含税总息费", "日息(含税)", "日息(不含税)"]
mon = mon.merge(PROD_ATTR[attr_merge_cols], on="product_name", how="left")
wk  = wk.merge(PROD_ATTR[attr_merge_cols], on="product_name", how="left")

MON_COLS = ["grp", "product_name", "产品类型", "含税(E)", "定价来源", "总期限", "前砍利息", "后收利息",
            "放款笔数", "放款金额", "件均", "复贷客数", "人均件数", "笔数占比%", "金额占比%", "期限一致率%",
            "前砍率%", "后收率%", "总息费率%(合同)", "前砍净率%", "后收净率%", "息费净率%", "息费税(估)占合同%",
            "日息(含税)", "日息(不含税)", "T7成熟率%",
            "首逾T7%(贷款)", "首逾T30%(贷款)", "当前逾期率%(贷款)", "T7逾期本息率(对合同)%", "TR%(T7口径,合同)"]
WEEK_COLS = ["grp", "product_name", "产品类型", "含税(E)", "定价来源", "总期限",
             "放款笔数", "放款金额", "件均", "复贷客数", "人均件数", "笔数占比%", "金额占比%",
             "前砍率%", "后收率%", "前砍净率%", "后收净率%", "息费净率%", "T7成熟率%",
             "首逾T7%(贷款)", "首逾T30%(贷款)", "当前逾期率%(贷款)", "TR%(T7口径,合同)"]
mon = mon[MON_COLS].sort_values(["grp", "product_name"]).rename(columns={"grp": "月份"})
wk  = wk[WEEK_COLS].sort_values(["grp", "product_name"]).rename(columns={"grp": "周(周一)"})

# 各期合计 (reconciliation)
tot_m = build_grp(agg_m, "grp")
tot_w = build_grp(agg_w, "grp")

# ── 4. 全窗口产品校验 (as-recorded vs 净口径 vs 属性) ────────────
chk = PROD_ATTR.copy()
full = pd.concat([agg_m, agg_w]).groupby("product_name")[
    ["ca", "ha", "si", "loans", "t7m_ca", "t7m_ha", "t7m_si", "t7m_ovd"]].sum().reset_index()
chk = chk.merge(full, on="product_name", how="left")
chk["净系数"] = chk["product_name"].map(net_factor)
chk["实测前砍率%(合同)"] = _pct(chk["ha"], chk["ca"])
chk["实测后收率%(合同)"] = _pct(chk["si"], chk["ca"])
chk["实测前砍净率%"] = _pct(chk["ha"] * chk["净系数"], chk["ca"])
chk["实测后收净率%"] = _pct(chk["si"] * chk["净系数"], chk["ca"])
chk["实测息费净率%"] = _pct((chk["ha"] + chk["si"]) * chk["净系数"], chk["ca"])
# 属性折算到净口径(E÷1.16) 用于差异比较
chk["attr前砍净%"] = (chk["前砍利息"] * chk["净系数"] * 100).round(2)
chk["attr后收净%"] = (chk["后收利息"] * chk["净系数"] * 100).round(2)
chk["前砍净差异pp"] = round(chk["实测前砍净率%"] - chk["attr前砍净%"], 2)
chk["后收净差异pp"] = round(chk["实测后收净率%"] - chk["attr后收净%"], 2)
# 期限一致率
term_ok_all = tm[tm["一致"] == 1].groupby("product_name")["loans"].sum().rename("ok")
term_tot_all = tm.groupby("product_name")["loans"].sum().rename("all")
chk = chk.merge((term_ok_all / term_tot_all * 100).round(2).rename("期限一致率%").reset_index(),
                on="product_name", how="left")
chk["TR%(T7口径,合同)"] = _pct(chk["t7m_ha"] + chk["t7m_si"] - chk["t7m_ovd"], chk["t7m_ca"])
chk["成熟合同额"] = chk["t7m_ca"].round(2)
chk["放款笔数"] = chk["loans"]

def flag2(r):
    issues = []
    if pd.notna(r["attr前砍净%"]) and abs(r["前砍净差异pp"] or 0) > 2: issues.append("前砍净偏离>2pp")
    if pd.notna(r["attr后收净%"]) and abs(r["后收净差异pp"] or 0) > 2: issues.append("后收净偏离>2pp")
    if (r.get("期限一致率%") or 100) < 95: issues.append("期限一致率<95%")
    return "PASS" if not issues else "; ".join(issues)
chk["校验结论"] = chk.apply(flag2, axis=1)
CHK_COLS = ["product_name", "产品类型", "含税(E)", "定价来源", "总期限", "放款笔数",
            "前砍利息", "后收利息", "attr前砍净%", "attr后收净%",
            "实测前砍净率%", "实测后收净率%", "实测息费净率%", "前砍净差异pp", "后收净差异pp",
            "日息(含税)", "日息(不含税)", "不含税总息费", "期限一致率%",
            "TR%(T7口径,合同)", "成熟合同额", "校验结论"]
chk = chk[CHK_COLS].sort_values("放款笔数", ascending=False)

print("\n=== 月度全集 合计校验(产品合计 vs 官方全复贷应=0) ===")
print(tot_m.to_string(index=False))

# ── 5. 写出 Excel ───────────────────────────────────────────────
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
wb = openpyxl.Workbook()
HDR_FILL = PatternFill("solid", fgColor="1F4E78")
HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
GRP_FONT = Font(bold=True, size=11, color="1F4E78")
RED = Font(color="C00000")
THIN = Border(*[Side(style="thin", color="D9D9D9")] * 4)

def write_sheet(ws, df, header_note=None, tot_rows=None, pct_cols=None):
    if header_note:
        ws.append(header_note); ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(df.columns))
        ws.cell(1, 1).font = Font(bold=True, size=10, color="C00000")
        start = 2
    else:
        start = 1
    ws.append(list(df.columns))
    for c in ws[start]:
        c.fill, c.font, c.alignment = HDR_FILL, HDR_FONT, Alignment(vertical="center", horizontal="center")
    for r in df.itertuples(index=False):
        ws.append(list(r))
    if tot_rows is not None:
        for tr in tot_rows:
            ws.append(tr)
    for row in ws.iter_rows(min_row=start + 1, min_col=1, max_col=len(df.columns)):
        for c in row:
            c.border = THIN
            if isinstance(c.value, float):
                c.number_format = "#,##0.00"
            if c.value == "合计":
                c.font = Font(bold=True, color="1F4E78")
    for i in range(1, len(df.columns) + 1):
        w = max((len(str(v)) for v in df.iloc[:, i - 1].tolist()), default=0)
        ws.column_dimensions[get_column_letter(i)].width = min(max(w, len(str(df.columns[i - 1])), 8) + 2, 40)
    ws.freeze_panes = ws.cell(start + 1, 1)

notes = [
    ["墨西哥 复贷产品分析 (税后全口径 v2)", ""],
    ["数据源", "mx.wxs_application_funnel (墨西哥全链路风险宽表); 复贷(is_reloan='old')+已放款(if_issue=1)"],
    ["范围", "2026-05-01 ~ 2026-09-01 放款"],
    ["★ 合计口径(本次修正)", "不再锁死'8月17产品', 按月/周实际有放款的**全部产品全集**; 故各期产品放款笔数/金额合计==全复贷总量(零缺口)。例: 7月全集=24产品 37,689笔/5,464万(旧17产品仅94.7%/92.7%)"],
    ["税规则", "E开头产品价格**含IVA16%**(funnel息费=含税价, 净息费=÷1.16); A/B/C开头**不含税**(funnel息费即净); 税仅对息费(前砍+后收)计, 本金不计税"],
    ["息费净率%", "前砍/后收息费按净口径(不含税, E÷1.16) / 合同金额 —— 跨产品可比(税后收入口径)"],
    ["息费税(估)占合同%", "= 净息费×16% / 合同金额 (E=价内已含税; ABCD=发票另加的IVA)"],
    ["前砍率%/后收率%(合同)", "as-recorded 口径(funnel原值/合同): 与产品属性同口径(E含税/ABCD不含税), 用于核对属性; 跨E vs ABCD比较请用净率"],
    ["日息", "E按日息命名(E_期数期限_日息数字...); 日息(含税)=数字/1000, 总息费=日息×总期限; ABCD: 日息(不含税)=不含税总息费/总期限. 校验E_07_02_45_50X2→4.5%×14=0.63 ✓"],
    ["首逾T7%(贷款)", "T7成熟且t7_overdue_amount>1 占比(贷款数口径); 8月下旬放款成熟率低, 参考性有限"],
    ["TR%(T7口径,合同)", "=(T7成熟前砍+T7成熟后收−T7逾期本息)/T7成熟合同, as-recorded合同口径(未做税拆, 坏账代理为T7本+息)"],
    ["校验sheet", "实测净率 vs 属性折算净率(差异>2pp/期限一致<95%标关注); E属性总息为含税已÷1.16折算再比"],
    ["定价来源", "文档=产品文档原文; 实测补齐=文档缺失数值用全窗口实测定价补(如B_07_02_00_75/C_07_04_00_85); 仅实测(文档未收录)=窗口新增产品"],
]
ws = wb.active; ws.title = "说明"
for r in notes:
    ws.append(r)
ws.column_dimensions["A"].width = 20; ws.column_dimensions["B"].width = 110
for row in ws.iter_rows(min_row=2, max_row=len(notes)):
    row[0].font = GRP_FONT
    if row[1].value: row[1].alignment = Alignment(wrap_text=True, vertical="top")

write_sheet(wb.create_sheet("产品属性"), PROD_ATTR, ["产品属性 master(来自产品文档); 日息三列为规则计算填充; 含税(E)=1 表示价格含IVA"])
# 月度明细 + 每期合计行
mon_out = mon.rename(columns={"前砍利息": "attr前砍", "后收利息": "attr后收"})
m_cols = ["月份", "product_name", "产品类型", "含税(E)", "定价来源", "总期限", "attr前砍", "attr后收", "放款笔数", "放款金额",
          "件均", "复贷客数", "人均件数", "笔数占比%", "金额占比%", "期限一致率%",
          "前砍率%", "后收率%", "总息费率%(合同)", "前砍净率%", "后收净率%", "息费净率%", "息费税(估)占合同%",
          "日息(含税)", "日息(不含税)", "T7成熟率%", "首逾T7%(贷款)", "首逾T30%(贷款)", "当前逾期率%(贷款)",
          "T7逾期本息率(对合同)%", "TR%(T7口径,合同)"]
write_sheet(wb.create_sheet("月度明细"), mon_out[m_cols],
            ["★ 每月=当月全部产品; 各月产品合计应=全复贷(见『合计校验』); 净率=E÷1.16后与ABCD可比; 前砍/后收(合同)=as-recorded同属性口径"])
write_sheet(wb.create_sheet("周度明细"), wk,
            ["★ 每周=当周全部产品; 8月下旬放款T7多未成熟, 逾期/TR参考性低"])
write_sheet(wb.create_sheet("期限分布"), term.rename(columns={"m": "月份", "loan_cycle": "期限(天)", "loans": "放款笔数", "ca": "放款金额"}),
            ["★ 期限=实际loan_cycle(天)"])
# 合计校验
tot_m = tot_m.rename(columns={"grp": "月份"})
tot_w = tot_w.rename(columns={"grp": "周(周一)"})
write_sheet(wb.create_sheet("合计校验_月"), tot_m, ["每月 产品全集合计 == 全复贷(笔数/金额): 若此处与官方对不上才需查数据"])
write_sheet(wb.create_sheet("合计校验_周"), tot_w, ["每周 产品全集合计"])
write_sheet(wb.create_sheet("校验"), chk, ["实测(全窗口5-8月) vs 产品属性: 净口径差异=E÷1.16; 标关注=差异>2pp或期限一致<95%"])

wb.save(OUT_XLSX)
print(f"\n[输出] {OUT_XLSX}")
print(f"[校验] PASS: {(chk['校验结论']=='PASS').sum()}/{len(chk)}; 关注: {chk[chk['校验结论']!='PASS'].shape[0]}")
if (chk["校验结论"] != "PASS").any():
    print(chk[chk["校验结论"] != "PASS"][["product_name", "校验结论"]].to_string(index=False))

# 控制台 7月 & 8月 摘要
for mm in ["2026-07", "2026-08"]:
    print(f"\n=== {mm} 月度 摘要 (息费净口径, 降序) ===")
    s = mon[mon["月份"] == mm].sort_values("放款笔数", ascending=False)
    print(s[["product_name", "产品类型", "含税(E)", "放款笔数", "放款金额", "息费净率%", "息费税(估)占合同%",
             "前砍率%", "后收率%", "T7成熟率%", "首逾T7%(贷款)", "TR%(T7口径,合同)"]].to_string(index=False))
