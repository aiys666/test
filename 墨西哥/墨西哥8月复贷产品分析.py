# -*- coding: utf-8 -*-
"""
墨西哥 8月有放款产品 复贷分析
================================
数据源: mx.wxs_application_funnel (墨西哥全链路风险宽表)
范围  : 2026-05-01 ~ 2026-08-31 放款; 仅复贷(is_reloan='old') + 已放款(if_issue=1)
产品  : 墨西哥8月有放款产品_0826.xlsx 中的 17 个产品

输出指标:
  放款量(笔数/金额/件均) / 放款占比 / 复贷客数 / 人均件数
  期限占比(实际 loan_cycle 分布) + 期限一致率(与产品属性总期限对比)
  定价: 前砍率 / 后收率 / 总利息(合同口径)
  逾期(贷款数口径): 首逾T7%(逾期≥8天未结清) / 首逾T30% / 当前逾期率%
  TR  : TR%(T7口径) = 前砍率 + 后收率 − T7逾期本息率(对合同), 取 T7 成熟子集
校验  : 计算出的 前砍率/后收率 与 Excel 产品属性利率对比

TR 口径沿用既往框架: TR = 前砍(本金) + 后收(本金) − 本金坏账(本金) − 息费坏账(本金),
  以「T7 时点未结余额(应还总额−应还日+7前累计实还, 订单级t7_overdue_amount)」作为坏账代理,
  分母统一为合同金额。注意: 多期产品 T7 时点未结余额含尚未到期的后续期, 会令 TR 偏保守(低估);
  8月下旬放款 T7 多未成熟, 该行 TR 为部分成熟估计, 看 成熟率 判断可信度。
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

EXCEL_ATTR = r"D:\Documents\Downloads\墨西哥8月有放款产品_0826.xlsx"
OUT_XLSX   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "墨西哥8月复贷产品分析.xlsx")
START, END = "2026-05-01", "2026-09-01"   # 左闭右开

# ── 1. 读取产品属性 ─────────────────────────────────────────────
# 文件布局: R1=图例(被pandas当header→Unnamed), R2=真实表头, R3起=数据 → header=1
attr_df = pd.read_excel(EXCEL_ATTR, sheet_name=0, header=1)
attr_df = attr_df.dropna(subset=["product_name"])
attr_df["product_name"] = attr_df["product_name"].astype(str).str.strip()
# R19 是 A_07_01_50_00 的重复脏行(产品类型=E, 与A类矛盾), 按 product_name 去重保留首行
attr_df = attr_df.drop_duplicates(subset=["product_name"], keep="first")
PRODS = sorted(attr_df["product_name"].unique().tolist())
print(f"[属性] 读取产品 {len(PRODS)} 个")

ATTR_COLS = ["产品类型", "是否蝌蚪产品", "前砍利息", "后收利息", "总利息",
             "期数", "单期期限", "总期限",
             "第一期还本息比例", "第二期还本息比例", "第三期还本息比例", "第四期还本息比例"]
for c in ATTR_COLS:
    if c not in attr_df.columns:
        raise SystemExit(f"[属性] 缺少列: {c}")
PROD_LIST_SQL = "(" + ",".join(f"'{p}'" for p in PRODS) + ")"

# ── 2. 查询封装 ─────────────────────────────────────────────────
pq = PrestoQuery()
pq.login()   # 启动先建会话(防过期)

def _num(df, cols):
    """Presto返回全部为字符串, 仅对指定数值列转数值(pandas3无errors=ignore, 用coerce)"""
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out

NUM_AGG = ["loans", "custs", "ca", "ha", "si", "t7m_loans", "t7m_ca", "t7m_ha",
           "t7m_si", "t7m_ovd", "t7_ovd_flag", "t30m_loans", "t30_ovd_flag",
           "now_ovd_flag"]

def q(sql, retry=3):
    """查询, 会话过期(返回登录跳转/格式错误)时自动重登重试"""
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r):
            print(f"[重登] 会话异常, 第{i+1}次重登...")
            pq.login()
            continue
        return r
    raise SystemExit(f"[查询失败] {r}")

# ── 3. SQL ─────────────────────────────────────────────────────
M_GRP = "date_format(date_trunc('month', date(release_time)), '%Y-%m')"
W_GRP = "date_format(date_trunc('week',  date(release_time)), '%Y-%m-%d')"

def _agg_sql(grp_expr):
    return f"""
with base as (
  select {grp_expr} as grp, product_name, loan_cycle, mid, camera_id,
         contract_amount, haircut_amount, should_interest,
         t7_should_amt, t7_overdue_amount,
         t30_should_amt, t30_overdue_amount,
         now_overdue_days
  from mx.wxs_application_funnel
  where is_reloan = 'old' and if_issue = 1
    and date(release_time) >= date '{START}'
    and date(release_time) <  date '{END}'
    and product_name in {PROD_LIST_SQL}
)
select grp, product_name,
  count(distinct camera_id) as loans,
  count(distinct mid)       as custs,
  sum(contract_amount)      as ca,
  sum(haircut_amount)       as ha,
  sum(should_interest)      as si,
  -- T7 成熟子集: t7_should_amt 非空 = 已有期次到达T7观察点
  sum(if(t7_should_amt is not null, 1, 0))                as t7m_loans,
  sum(if(t7_should_amt is not null, contract_amount, 0))  as t7m_ca,
  sum(if(t7_should_amt is not null, haircut_amount, 0))   as t7m_ha,
  sum(if(t7_should_amt is not null, should_interest, 0))  as t7m_si,
  sum(if(t7_should_amt is not null, t7_overdue_amount, 0)) as t7m_ovd,  -- T7未还本息(本+息)
  sum(if(t7_should_amt is not null and t7_overdue_amount > 1, 1, 0)) as t7_ovd_flag,  -- 首逾(贷款口径)
  sum(if(t30_should_amt is not null, 1, 0))               as t30m_loans,
  sum(if(t30_should_amt is not null and t30_overdue_amount > 1, 1, 0)) as t30_ovd_flag,
  sum(if(now_overdue_days > 0, 1, 0))                     as now_ovd_flag
from base
group by 1, 2
order by 1, 2
"""

def _tot_sql(grp_expr):
    return f"""
select {grp_expr} as grp,
       count(distinct camera_id) as loans,
       sum(contract_amount)      as ca
from mx.wxs_application_funnel
where is_reloan = 'old' and if_issue = 1
  and date(release_time) >= date '{START}'
  and date(release_time) <  date '{END}'
group by 1
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
  and product_name in {PROD_LIST_SQL}
group by 1, 2, 3
order by 1, 2, 3
"""

print("[查询] 月度聚合...")
agg_m = _num(q(_agg_sql(M_GRP)), NUM_AGG)
print(f"[月度] {len(agg_m)} 行")
print("[查询] 周度聚合...")
agg_w = _num(q(_agg_sql(W_GRP)), NUM_AGG)
print(f"[周度] {len(agg_w)} 行")
print("[查询] 月度全复贷总量...")
tot_m = _num(q(_tot_sql(M_GRP)), ["loans", "ca"]).rename(columns={"grp": "m"})
print("[查询] 周度全复贷总量...")
tot_w = _num(q(_tot_sql(W_GRP)), ["loans", "ca"]).rename(columns={"grp": "w"})
print("[查询] 期限分布(月度)...")
term = _num(q(TERM_SQL), ["loans", "ca", "loan_cycle"])
print(f"[期限] {len(term)} 行")

# ── 4. 计算指标 ─────────────────────────────────────────────────
def _pct(x, y):
    """百分比, 除零安全"""
    return pd.Series([round(a / b * 100, 2) if (b and pd.notna(a) and pd.notna(b)) else None
                      for a, b in zip(pd.to_numeric(x, errors="coerce"), pd.to_numeric(y, errors="coerce"))],
                     index=x.index)

def build(df, tot, tot_key, out_col):
    d = df.copy()
    d["放款笔数"]  = d["loans"]
    d["放款金额"]  = d["ca"].round(2)
    d["件均"]      = (d["ca"] / d["loans"]).round(2)
    d["复贷客数"]  = d["custs"]
    d["人均件数"]  = (d["loans"] / d["custs"]).round(2)
    d["前砍率%"]   = _pct(d["ha"], d["ca"])                       # 当期全量合同口径
    d["后收率%"]   = _pct(d["si"], d["ca"])
    d["T7成熟率%"] = _pct(d["t7m_loans"], d["loans"])
    d["首逾T7%(贷款)"] = _pct(d["t7_ovd_flag"], d["t7m_loans"])   # T7时点未清余额>1
    d["首逾T30%(贷款)"] = _pct(d["t30_ovd_flag"], d["t30m_loans"])
    d["当前逾期率%(贷款)"] = _pct(d["now_ovd_flag"], d["loans"])  # now_overdue_days>0
    d["T7逾期本息率(对合同)%"] = _pct(d["t7m_ovd"], d["t7m_ca"])  # T7未还本息/合同, 成熟子集
    d["TR%(T7口径)"] = _pct(d["t7m_ha"] + d["t7m_si"] - d["t7m_ovd"], d["t7m_ca"])
    # 放款占比(对同期全复贷)
    d = d.merge(tot.rename(columns={tot_key: "grp"}), on="grp", suffixes=("", "_tot"))
    d["笔数占比%"] = _pct(d["loans"], d["loans_tot"])
    d["金额占比%"] = _pct(d["ca"],    d["ca_tot"])
    return d.rename(columns={"grp": out_col})

mon = build(agg_m, tot_m, "m", "m")
wk  = build(agg_w, tot_w, "w", "w")

# 期限一致率(对属性总期限)
attr_term = attr_df.set_index("product_name")["总期限"]
term_merge = term.copy()
term_merge["attr_term"] = term_merge["product_name"].map(attr_term)
term_merge["一致"] = (term_merge["loan_cycle"] == term_merge["attr_term"]).astype(int)
term_ok = term_merge.groupby(["m", "product_name"]).apply(
    lambda g: round(g.loc[g["一致"] == 1, "loans"].sum() / g["loans"].sum() * 100, 2),
    include_groups=False
).rename("期限一致率%").reset_index()
mon = mon.merge(term_ok, on=["m", "product_name"], how="left")

# 合并产品属性
mon = mon.merge(attr_df[["product_name"] + ATTR_COLS], on="product_name", how="left")
wk  = wk.merge(attr_df[["product_name"] + ATTR_COLS], on="product_name", how="left")

MON_COLS = ["m", "product_name"] + ATTR_COLS + [
    "放款笔数", "放款金额", "件均", "复贷客数", "人均件数",
    "笔数占比%", "金额占比%", "期限一致率%",
    "前砍率%", "后收率%", "T7成熟率%",
    "首逾T7%(贷款)", "首逾T30%(贷款)", "当前逾期率%(贷款)",
    "T7逾期本息率(对合同)%", "TR%(T7口径)",
]
WEEK_COLS = ["w", "product_name"] + ATTR_COLS + [
    "放款笔数", "放款金额", "件均", "复贷客数", "人均件数",
    "笔数占比%", "金额占比%",
    "前砍率%", "后收率%", "T7成熟率%",
    "首逾T7%(贷款)", "首逾T30%(贷款)", "当前逾期率%(贷款)",
    "T7逾期本息率(对合同)%", "TR%(T7口径)",
]
mon = mon[MON_COLS].sort_values(["m", "product_name"]).rename(columns={"m": "月份"})
wk  = wk[WEEK_COLS].sort_values(["w", "product_name"]).rename(columns={"w": "周(周一)"})

# 期限分布(笔数/金额占比)
term_attr = term_merge.copy()
term_attr["是否匹配属性"] = term_attr["一致"].map({1: "✓", 0: "✗"})
term_attr = term_attr.merge(tot_m, on="m", suffixes=("", "_tot"))
tg = term_attr.groupby(["m", "product_name"])[["loans", "ca"]].transform("sum")
term_attr["笔数占比%"] = (term_attr["loans"] / tg["loans"] * 100).round(2)
term_attr["金额占比%"] = (term_attr["ca"] / tg["ca"] * 100).round(2)
term_attr["占总复贷笔数%"] = (term_attr["loans"] / term_attr["loans_tot"] * 100).round(2)
term_attr = term_attr.rename(columns={"loans": "放款笔数", "ca": "放款金额"})
TERM_COLS = ["m", "product_name", "loan_cycle", "是否匹配属性", "attr_term",
             "放款笔数", "笔数占比%", "放款金额", "金额占比%", "占总复贷笔数%"]
term_attr = term_attr[TERM_COLS].sort_values(["m", "product_name", "loan_cycle"]).rename(
    columns={"m": "月份", "attr_term": "属性总期限"})

# ── 5. 校验: 计算利率 vs 产品属性利率 ────────────────────────────
chk = attr_df.copy()
full = pd.concat([agg_m, agg_w]).groupby("product_name")[
    ["ca", "ha", "si", "loans", "t7m_ca", "t7m_ha", "t7m_si", "t7m_ovd"]].sum().reset_index()
chk = chk.merge(full, on="product_name", how="left")
chk["计算前砍率%"] = _pct(chk["ha"], chk["ca"])
chk["计算后收率%"] = _pct(chk["si"], chk["ca"])
chk["前砍差异pp"] = round(chk["计算前砍率%"] - chk["前砍利息"] * 100, 2)
chk["后收差异pp"] = round(chk["计算后收率%"] - chk["后收利息"] * 100, 2)
chk["总利息对比"] = round(chk["前砍利息"] + chk["后收利息"] - chk["总利息"], 3)
chk["TR%(T7口径,全窗口)"] = _pct(chk["t7m_ha"] + chk["t7m_si"] - chk["t7m_ovd"], chk["t7m_ca"])
chk["成熟合同额"] = chk["t7m_ca"].round(2)
term_ok_all = term_merge.groupby("product_name").apply(
    lambda g: round(g.loc[g["一致"] == 1, "loans"].sum() / g["loans"].sum() * 100, 2),
    include_groups=False
).rename("期限一致率%").reset_index()
chk = chk.merge(term_ok_all, on="product_name", how="left")

def flag(row):
    issues = []
    if abs(row.get("前砍差异pp") or 0) > 2: issues.append("前砍率偏离属性>2pp")
    if abs(row.get("后收差异pp") or 0) > 2: issues.append("后收率偏离属性>2pp")
    if (row.get("期限一致率%") or 0) < 95:  issues.append("期限一致率<95%")
    return "PASS" if not issues else "; ".join(issues)
chk["校验结论"] = chk.apply(flag, axis=1)
CHK_COLS = ["product_name", "产品类型", "是否蝌蚪产品", "前砍利息", "后收利息", "总利息",
            "计算前砍率%", "计算后收率%", "前砍差异pp", "后收差异pp", "总利息对比",
            "期限一致率%", "TR%(T7口径,全窗口)", "成熟合同额", "校验结论"]
chk = chk[CHK_COLS]

# ── 6. 写出 Excel ───────────────────────────────────────────────
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()
HDR_FILL = PatternFill("solid", fgColor="1F4E78")
HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
GRP_FONT = Font(bold=True, size=11, color="1F4E78")
THIN = Border(*[Side(style="thin", color="D9D9D9")] * 4)

def write_sheet(ws, df, header_note=None):
    if header_note:
        ws.append(header_note)
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(df.columns))
        ws.cell(1, 1).font = Font(bold=True, size=10, color="C00000")
        start = 2
    else:
        start = 1
    ws.append(list(df.columns))
    for c in ws[start]:
        c.fill, c.font, c.alignment = HDR_FILL, HDR_FONT, Alignment(vertical="center", horizontal="center")
    for r in df.itertuples(index=False):
        ws.append(list(r))
    for row in ws.iter_rows(min_row=start + 1, min_col=1, max_col=len(df.columns)):
        for c in row:
            c.border = THIN
            if isinstance(c.value, float):
                c.number_format = "#,##0.00"
    for i, col in enumerate(df.columns, 1):
        w = max((len(str(v)) for v in df[col].tolist()), default=0)
        ws.column_dimensions[get_column_letter(i)].width = min(max(w, len(str(col)), 8) + 2, 40)
    ws.freeze_panes = ws.cell(start + 1, 1)

# 说明
ws = wb.active; ws.title = "说明"
notes = [
    ["墨西哥 8月有放款产品(17个) 复贷分析", ""],
    ["数据源", "mx.wxs_application_funnel (墨西哥全链路风险宽表)"],
    ["范围", "2026-05-01 ~ 2026-08-31 放款; 仅复贷(is_reloan='old') + 已放款(if_issue=1)"],
    ["维度", "月度(5~8月) + 周度(8月W31~W35, 周起=周一); 期限分布按月度"],
    ["放款量", "放款笔数=distinct camera_id; 放款金额=Σ合同金额; 件均=金额/笔数"],
    ["放款占比", "该产品占当月/当周全复贷放款的 笔数占比 / 金额占比 (含17产品之外少量其他复贷)"],
    ["复贷客数", "distinct mid(客户数); 人均件数=笔数/客数"],
    ["期限占比", "实际 loan_cycle(产品期限,天) 分布见「期限分布」表; 期限一致率=loan_cycle与属性总期限一致的放款占比"],
    ["定价", "前砍率=Σ前砍金额/Σ合同金额; 后收率=Σ应还利息/Σ合同金额; 均按当期放款全量口径"],
    ["成熟率", "T7成熟率=已有期次到达T7观察点(t7_should_amt非空)的放款占比; 8月下旬放款成熟率低, 逾期/TR参考性有限"],
    ["首逾T7%(贷款)", "Σ(成熟且T7未还本息>1)/Σ成熟, 贷款数口径, 定义=到T7观察点时仍有未还余额的贷款占比; t7_overdue_amount=应还总额−各期次应还日+7前累计实还"],
    ["首逾T30%(贷款)", "同上, T30观察点口径"],
    ["当前逾期率%(贷款)", "Σ(now_overdue_days>0)/放款笔数, 当前实际逾期天数>0的贷款占比"],
    ["T7逾期本息率(对合同)%", "Σt7_overdue_amount/Σ合同金额 (T7成熟子集); T7未还本息占合同金额, 本+息口径"],
    ["TR口径", "TR% = 前砍率 + 后收率 − T7逾期本息率(对合同), 分母=合同金额; 在T7成熟子集上计算, 以T7未还本息作为坏账代理. 多期产品在部分成熟阶段T7未还含尚未到期的后续期应还, TR偏保守(低估); 成熟率高(如5~6月放款)时更可信"],
    ["校验", "「校验」表: 计算前砍率/后收率 vs Excel产品属性利率, 偏差>2pp 或 期限一致率<95% 标为关注"],
    ["", ""],
    ["注", "产品属性取自 墨西哥8月有放款产品_0826.xlsx (A=单期, B=多期等本等息, C=多期蝌蚪, E=按日息命名; 蝌蚪产品后收息分期还)"],
]
for r in notes:
    ws.append(r)
ws.column_dimensions["A"].width = 18
ws.column_dimensions["B"].width = 100
for row in ws.iter_rows(min_row=2, max_row=len(notes)):
    row[0].font = GRP_FONT
    if row[1].value: row[1].alignment = Alignment(wrap_text=True, vertical="top")

write_sheet(wb.create_sheet("产品属性"), attr_df[["product_name"] + ATTR_COLS])
write_sheet(wb.create_sheet("月度明细"), mon, ["★ 首逾/TR 在 T7成熟子集 上计算, 8月下旬放款成熟率低, 参考性有限; 前砍率/后收率为当期全量合同口径"])
write_sheet(wb.create_sheet("周度明细"), wk, ["★ 周度以8月W31~W35为主, 8月下旬放款T7多未成熟, 逾期/TR参考性低; 前砍率/后收率为当周全量合同口径"])
write_sheet(wb.create_sheet("期限分布"), term_attr, ["★ 期限=实际loan_cycle(天); 是否匹配属性 = 与实际产品总期限是否一致"])
write_sheet(wb.create_sheet("校验"), chk)

wb.save(OUT_XLSX)
print(f"\n[输出] {OUT_XLSX}")
print(f"[校验] PASS: {(chk['校验结论']=='PASS').sum()}/{len(chk)}; 关注: {chk[chk['校验结论']!='PASS'].shape[0]}")
if (chk["校验结论"] != "PASS").any():
    print(chk[chk["校验结论"] != "PASS"][["product_name", "校验结论"]].to_string(index=False))

# ── 7. 控制台摘要 ───────────────────────────────────────────────
print("\n=== 8月(月度) 各产品放款 & 逾期 & TR 摘要 ===")
summ = mon[mon["月份"] == "2026-08"].sort_values("放款笔数", ascending=False)
print(summ[["product_name", "产品类型", "放款笔数", "放款金额", "件均",
            "笔数占比%", "金额占比%", "期限一致率%", "前砍率%", "后收率%",
            "T7成熟率%", "首逾T7%(贷款)", "首逾T30%(贷款)", "当前逾期率%(贷款)",
            "TR%(T7口径)"]].to_string(index=False))
