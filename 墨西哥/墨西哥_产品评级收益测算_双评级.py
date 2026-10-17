# -*- coding: utf-8 -*-
"""
墨西哥 老客放款 产品×评级 收益测算(双评级 V5_3 / V6_1) — 全 SQL 底表口径
================================================================================
底表口径(用户确认代码逐字还原): mx.wxs_application_funnel f (tenant='yawey',
  is_reloan='old', if_issue=1) 联 yj_test_table_250225 取双评级与产品键 product_name_new。
收窄到封口月份 release_time 2026-06-09 ~ 2026-08-31(V5_3 全量评级; V6_1 新模型仅8月起)。
yj biz_id 有重复(198组) → 按 biz_id 取 max 去重防双算。

逾期率/TR口径(用户给定, 分母统一 应还本金·期1):
  本金逾期率_tN = ΣtN_overdue_capit_1   / ΣtN_should_capit_1
  息费逾期率_tN = ΣtN_overdue_interest_1 / ΣtN_should_capit_1   ←分母=应还本金,同基
  TR_tN = (成熟期1前砍 + 成熟期1应还后收 − 逾期本金1 − 逾期息费1) / Σ应还本金1
税: E开头产品含IVA16%→息费÷1.16为净; A/B/C即净。税只对息费(前砍+后收)计, 本金不计。
字段全部中文可读命名(废弃 t0_should_amt_1 机器名)。
校验三层: (A)覆盖锚点SQL对拍 (B)表内速率列由金额列重算 (C)独立SQL全口径重算逐行对拍。
"""
import sys, os, time, math
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
import pandas as pd
import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from mexico_presto import PrestoQuery

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_XLSX = os.path.join(HERE, "墨西哥_产品评级收益测算_双评级.xlsx")
CACHE = os.path.join(HERE, "_dual_atomic.pkl")
FORCE = os.environ.get("FORCE") == "1"

WINS = [0, 3, 7, 15, 30]
PFX = {0: "t0", 3: "t3", 7: "t7", 15: "t15", 30: "t30"}
RATE_WINS = [0, 7, 30]
GRADE = {5: "android_oldcust_maincreditlevel_charge_v5_3",
         6: "android_oldCust_mainCreditLevel_charge_V6_1"}
GA = {5: "v5", 6: "v6"}
SYS = {5: "V5_3", 6: "V6_1"}

# ---------------- SQL 原子层: 月×产品×档 ----------------
def _sum_lines():
    L = []
    for n in WINS:
        p = PFX[n]
        for k, e in [("cs", f"{p}_should_capit_1"), ("is", f"{p}_should_interest_1"),
                     ("co", f"{p}_overdue_capit_1"), ("io", f"{p}_overdue_interest_1")]:
            L.append(f"sum(cast(f.{e} as double)) {k}_{n}")
        L.append("sum(" + "+".join(f"cast(f.{p}_overdue_capit_{j} as double)" for j in range(1, 5)) + f") coa_{n}")
        L.append("sum(" + "+".join(f"cast(f.{p}_overdue_interest_{j} as double)" for j in range(1, 5)) + f") ioa_{n}")
        L.append(f"sum(if(coalesce(is_{p}_window_1,0)=1,cast(f.haircut_amount as double),0)) h_{n}")
        L.append(f"sum(if(coalesce(is_{p}_window_1,0)=1,cast(f.should_interest as double),0)) s_{n}")
        L.append(f"sum(if(coalesce(is_{p}_window_1,0)=1 and upper(y.product_name_new) like 'E%',"
                 f"cast(f.haircut_amount as double)/1.16, if(coalesce(is_{p}_window_1,0)=1,cast(f.haircut_amount as double),0))) nh_{n}")
        L.append(f"sum(if(coalesce(is_{p}_window_1,0)=1 and upper(y.product_name_new) like 'E%',"
                 f"cast(f.should_interest as double)/1.16, if(coalesce(is_{p}_window_1,0)=1,cast(f.should_interest as double),0))) ns_{n}")
        L.append(f"sum(if(coalesce(is_{p}_window_1,0)=1 and upper(y.product_name_new) like 'E%',"
                 f"cast(f.{p}_overdue_interest_1 as double)/1.16, cast(f.{p}_overdue_interest_1 as double))) ni_{n}")
        L.append(f"sum(if(coalesce(is_{p}_window_1,0)=1,1,0)) w_{n}")
    return L

def sql_atomic(g):
    return f"""with hub as (
  select biz_id, product_name_new,
    max(android_oldcust_maincreditlevel_charge_v5_3) v5,
    max(android_oldCust_mainCreditLevel_charge_V6_1) v6
  from mx.yj_test_table_250225 group by 1,2)
select date_format(cast(f.release_time as date),'%Y-%m') ym,
 y.product_name_new product, cast(y.{GA[g]} as bigint) g,
 count(distinct f.biz_id) loans, count(distinct f.mid) custs,
 sum(cast(f.contract_amount as double)) ca,
 sum(cast(f.haircut_amount as double)) ha,
 sum(cast(f.amount as double)) disp,
 sum(cast(f.should_interest as double)) si_all,
 sum(cast(f.contract_amount as double)*cast(f.loan_cycle as double)) cyc_w,
 sum(if(upper(y.product_name_new) like 'E%',cast(f.haircut_amount as double)/1.16,cast(f.haircut_amount as double))) nha,
 sum(if(upper(y.product_name_new) like 'E%',cast(f.should_interest as double)/1.16,cast(f.should_interest as double))) nsi,
 {",\n ".join(_sum_lines())}
from mx.wxs_application_funnel f
join hub y on f.biz_id = y.biz_id
where f.tenant='yawey' and f.if_issue=1 and f.is_reloan='old'
  and cast(f.release_time as date)>=date'2026-06-09'
  and cast(f.release_time as date)< date'2026-09-01'
  and y.{GA[g]} is not null
group by 1,2,3"""

# ---------------- 独立SQL复核(对拍, 同一口径重写) ----------------
CHK_EXPR = {
    "cs0": "sum(cast(f.t0_should_capit_1 as double))", "co0": "sum(cast(f.t0_overdue_capit_1 as double))",
    "io0": "sum(cast(f.t0_overdue_interest_1 as double))",
    "cs7": "sum(cast(f.t7_should_capit_1 as double))", "co7": "sum(cast(f.t7_overdue_capit_1 as double))",
    "io7": "sum(cast(f.t7_overdue_interest_1 as double))",
    "h0": "sum(if(coalesce(is_t0_window_1,0)=1,cast(f.haircut_amount as double),0))",
    "s0": "sum(if(coalesce(is_t0_window_1,0)=1,cast(f.should_interest as double),0))",
    "h7": "sum(if(coalesce(is_t7_window_1,0)=1,cast(f.haircut_amount as double),0))",
    "s7": "sum(if(coalesce(is_t7_window_1,0)=1,cast(f.should_interest as double),0))",
    "nh0": "sum(if(coalesce(is_t0_window_1,0)=1 and upper(y.product_name_new) like 'E%',cast(f.haircut_amount as double)/1.16, if(coalesce(is_t0_window_1,0)=1,cast(f.haircut_amount as double),0)))",
    "ns0": "sum(if(coalesce(is_t0_window_1,0)=1 and upper(y.product_name_new) like 'E%',cast(f.should_interest as double)/1.16, if(coalesce(is_t0_window_1,0)=1,cast(f.should_interest as double),0)))",
    "ni0": "sum(if(coalesce(is_t0_window_1,0)=1 and upper(y.product_name_new) like 'E%',cast(f.t0_overdue_interest_1 as double)/1.16, cast(f.t0_overdue_interest_1 as double)))",
    "nha": "sum(if(upper(y.product_name_new) like 'E%',cast(f.haircut_amount as double)/1.16,cast(f.haircut_amount as double)))",
    "nsi": "sum(if(upper(y.product_name_new) like 'E%',cast(f.should_interest as double)/1.16,cast(f.should_interest as double)))",
}
CHK_SIMPLE = {
    "loans": "count(distinct f.biz_id)",
    "ca": "sum(cast(f.contract_amount as double))", "ha": "sum(cast(f.haircut_amount as double))",
    "si_all": "sum(cast(f.should_interest as double))",
    "cyc_w": "sum(cast(f.contract_amount as double)*cast(f.loan_cycle as double))",
}

def sql_chk(g):
    cols = [f"{v} {k}" for k, v in CHK_SIMPLE.items()] + [f"{v} {k}" for k, v in CHK_EXPR.items()]
    return f"""with hub as (
  select biz_id, product_name_new,
    max(android_oldcust_maincreditlevel_charge_v5_3) v5,
    max(android_oldCust_mainCreditLevel_charge_V6_1) v6
  from mx.yj_test_table_250225 group by 1,2)
select y.product_name_new product, cast(y.{GA[g]} as bigint) g, {",\n ".join(cols)}
from mx.wxs_application_funnel f
join hub y on f.biz_id=y.biz_id
where f.tenant='yawey' and f.if_issue=1 and f.is_reloan='old'
  and cast(f.release_time as date)>=date'2026-06-09'
  and cast(f.release_time as date)< date'2026-09-01'
  and y.{GA[g]} is not null
group by 1,2"""

def sql_cov():
    return """with hub as (
  select biz_id,
    max(android_oldcust_maincreditlevel_charge_v5_3) v5,
    max(android_oldCust_mainCreditLevel_charge_V6_1) v6
  from mx.yj_test_table_250225 group by 1)
select date_format(cast(f.release_time as date),'%Y-%m') ym,
 count(distinct f.biz_id) all_biz,
 count(distinct if(y.biz_id is not null,f.biz_id,null)) matched_biz,
 count(distinct if(y.v5 is not null,f.biz_id,null)) has_v5,
 count(distinct if(y.v6 is not null,f.biz_id,null)) has_v6,
 count(distinct if(z53.biz_id is not null,f.biz_id,null)) flag_v53
from mx.wxs_application_funnel f
left join hub y on f.biz_id=y.biz_id
left join (select distinct biz_id from mx.yj_test_table_250225
           where v3_flag='V5_3' and android_oldcust_maincreditlevel_charge_v5_3 is not null) z53
  on f.biz_id=z53.biz_id
where f.tenant='yawey' and f.if_issue=1 and f.is_reloan='old'
  and cast(f.release_time as date)>=date'2026-06-09'
  and cast(f.release_time as date)< date'2026-09-01'
group by 1 order by 1"""

# ---------------- 展示列 ----------------
AMT = ["应还本金_期1", "逾期本金_期1", "逾期本金_各期合计", "应还息费_期1", "逾期息费_期1",
       "逾期息费_各期合计", "成熟前收(期1)", "成熟后收(期1)", "成熟笔数_期1"]
def all_cols():
    c = ["放款笔数", "复贷客数", "放款金额", "件均", "人均件数", "前砍费", "到手金额", "应还后收(总额)",
         "前收率_税前%", "前收率_税后%", "后收率_税前%", "后收率_税后%",
         "总息费率_税前%", "总息费率_税后%", "息费税(估)占合同%",
         "加权期限(天)", "日息_税后%", "日息_税前%"]
    for n in WINS:
        c += [f"{t}_{n}" for t in AMT]
    for n in RATE_WINS:
        c += [f"本金逾期率_{n}%", f"息费逾期率_{n}%", f"TR_{n}_税前%", f"TR_{n}_税后%"]
    return c
ALL = all_cols()
MONEY_KIND = {"放款金额", "前砍费", "到手金额", "应还后收(总额)"}
CNT_KIND = {"放款笔数", "复贷客数"}
def col_kind(col):
    if col in CNT_KIND or col.startswith("成熟笔数"):
        return "cnt"
    if col.endswith("%") or col in ("件均", "人均件数", "加权期限(天)"):
        return "rate"
    return "money"

def fmt(col):
    k = col_kind(col)
    return "#,##0" if k == "cnt" else ('0.00"%"' if k == "rate" else "#,##0.00")

# ---------------- 聚合 & 指标内核 ----------------
SUM_BASE = ["ca", "ha", "disp", "si_all", "cyc_w", "nha", "nsi"]
SUM_ALL = SUM_BASE + [f"{k}_{n}" for n in WINS for k in
                      ["cs", "is", "co", "io", "coa", "ioa", "h", "s", "nh", "ns", "ni", "w"]]
GRP_SPEC = {"loans": ("loans", "sum"), "custs": ("custs", "sum"),
            **{c: (c, "sum") for c in SUM_ALL}}

def sub_to_sum(sub):
    S = {}
    for c in ["loans", "custs"] + SUM_ALL:
        S[c] = float(sub[c].sum())
    return S

def aggregate(df):
    """整段df → 汇总sum dict."""
    return sub_to_sum(df)

def rd(num, den, scale=100.0):
    if den is None or np.isnan(den) or den == 0:
        return np.nan
    return num / den * scale

def metric(S):
    o = {}
    lo, cu, ca = S["loans"], S["custs"], S["ca"]
    ha, si = S["ha"], S["si_all"]; nha, nsi = S["nha"], S["nsi"]
    o["放款笔数"] = lo; o["复贷客数"] = cu; o["放款金额"] = ca
    o["件均"] = rd(ca, lo, 1); o["人均件数"] = rd(lo, cu, 1)
    o["前砍费"] = ha; o["到手金额"] = S["disp"]; o["应还后收(总额)"] = si
    o["前收率_税前%"] = rd(ha, ca); o["前收率_税后%"] = rd(nha, ca)
    o["后收率_税前%"] = rd(si, ca); o["后收率_税后%"] = rd(nsi, ca)
    o["总息费率_税前%"] = rd(ha + si, ca); o["总息费率_税后%"] = rd(nha + nsi, ca)
    o["息费税(估)占合同%"] = rd((nha + nsi) * 0.16, ca)
    cyc = S["cyc_w"]
    o["加权期限(天)"] = rd(cyc, ca, 1)
    o["日息_税后%"] = rd(nha + nsi, cyc); o["日息_税前%"] = rd(ha + si, cyc)
    for n in WINS:
        cs, isv, co, io = S[f"cs_{n}"], S[f"is_{n}"], S[f"co_{n}"], S[f"io_{n}"]
        o[f"应还本金_期1_{n}"] = cs; o[f"逾期本金_期1_{n}"] = co
        o[f"逾期本金_各期合计_{n}"] = S[f"coa_{n}"]
        o[f"应还息费_期1_{n}"] = isv; o[f"逾期息费_期1_{n}"] = io
        o[f"逾期息费_各期合计_{n}"] = S[f"ioa_{n}"]
        o[f"成熟前收(期1)_{n}"] = S[f"h_{n}"]; o[f"成熟后收(期1)_{n}"] = S[f"s_{n}"]
        o[f"成熟笔数_期1_{n}"] = S[f"w_{n}"]
    for n in RATE_WINS:
        cs, co, io = S[f"cs_{n}"], S[f"co_{n}"], S[f"io_{n}"]
        o[f"本金逾期率_{n}%"] = rd(co, cs)
        o[f"息费逾期率_{n}%"] = rd(io, cs)
        o[f"TR_{n}_税前%"] = rd(S[f"h_{n}"] + S[f"s_{n}"] - co - io, cs)
        o[f"TR_{n}_税后%"] = rd(S[f"nh_{n}"] + S[f"ns_{n}"] - co - S[f"ni_{n}"], cs)
    return o

def chk_to_sum(r):
    """独立SQL复核结果(chk别名 cs0/co7/...) → 汇总sum dict(内部键 cs_0/co_7/...)."""
    S = {}
    for c in ["loans", "custs"]:
        S[c] = float(r.get(c, 0) or 0)
    for c in ["ca", "ha", "disp", "si_all", "cyc_w", "nha", "nsi"]:
        S[c] = float(r.get(c, np.nan)) if r.get(c) is not None else np.nan
    for k, n in [("cs", 0), ("co", 0), ("io", 0), ("h", 0), ("s", 0), ("nh", 0), ("ns", 0), ("ni", 0),
                 ("cs", 7), ("co", 7), ("io", 7), ("h", 7), ("s", 7)]:
        col = f"{k}{n}"
        S[f"{k}_{n}"] = float(r.get(col, np.nan)) if r.get(col) is not None else np.nan
    for n in WINS:
        for k in ["cs", "is", "co", "io", "coa", "ioa", "h", "s", "nh", "ns", "ni", "w"]:
            S.setdefault(f"{k}_{n}", np.nan)
    return S

# ---------------- 取数 ----------------
def load_atom():
    if (not FORCE) and os.path.exists(CACHE):
        return pd.read_pickle(CACHE)
    pq = PrestoQuery(); pq.login()
    out = {}
    for g in (5, 6):
        t = time.time()
        r = pq.query(sql_atomic(g))
        if isinstance(r, str):
            raise RuntimeError(f"atomic g{g}: {r}")
        for c in r.columns:
            if c not in ("ym", "product", "g"):
                r[c] = pd.to_numeric(r[c], errors="coerce")
        r["g"] = pd.to_numeric(r["g"], errors="coerce").astype("Int64")
        out[g] = r
        print(f"[取数] {SYS[g]} 原子行 {len(r)}, {time.time()-t:.0f}s | 月笔数 "
              f"{ {str(k): int(v) for k, v in r.groupby('ym')['loans'].sum().items()} }")
    pd.to_pickle(out, CACHE)
    return out

def run_sql(sql):
    pq = PrestoQuery(); pq.login()
    r = pq.query(sql)
    if isinstance(r, str):
        raise RuntimeError(r)
    for c in r.columns:
        if c not in ("ym", "product", "g"):
            r[c] = pd.to_numeric(r[c], errors="coerce")
    return r

# ---------------- 校验 ----------------
def check_B_rows(rows):
    """对每行 用金额列重算速率列, 与指标值比对."""
    bad = []
    for tag, key, m in rows:
        def close(a, b):
            if pd.isna(a) and pd.isna(b):
                return True
            if pd.isna(a) or pd.isna(b):
                return False
            return abs(a - b) < 1e-6
        ca = m["放款金额"]
        if ca:
            for a, b in (("前收率_税前%", 100 * m["前砍费"] / ca),
                         ("后收率_税前%", 100 * m["应还后收(总额)"] / ca)):
                if not close(m[a], b):
                    bad.append((tag, key, a))
        for n in RATE_WINS:
            cs = m[f"应还本金_期1_{n}"]
            if cs and not np.isnan(cs) and cs != 0:
                co, io = m[f"逾期本金_期1_{n}"], m[f"逾期息费_期1_{n}"]
                if not close(m[f"本金逾期率_{n}%"], 100 * co / cs):
                    bad.append((tag, key, f"本金逾期率_{n}"))
                if not close(m[f"息费逾期率_{n}%"], 100 * io / cs):
                    bad.append((tag, key, f"息费逾期率_{n}"))
                hh, ss = m[f"成熟前收(期1)_{n}"], m[f"成熟后收(期1)_{n}"]
                if not close(m[f"TR_{n}_税前%"], 100 * (hh + ss - co - io) / cs):
                    bad.append((tag, key, f"TR_{n}_税前"))
    return bad

# ---------------- Excel ----------------
HDR_FILL = PatternFill("solid", fgColor="1F4E78"); HDR_FONT = Font(color="FFFFFF", bold=True, size=9)
SUB_FILL = PatternFill("solid", fgColor="DDEBF7")
TOT_FILL = PatternFill("solid", fgColor="FFF2CC"); TOT_FONT = Font(bold=True, color="9C0006")
NOTE_F = Font(bold=True, size=10, color="C00000"); SMALL_F = Font(size=9, color="595959")

def emit(ws, rr, keyvals, m, nk, kind="D", headers=None):
    """写一行: 前 nk 列为key(非metric), 之后为ALL."""
    for j in range(1, nk + 1):
        cell = ws.cell(rr, j, keyvals[j - 1])
        if kind == "S":
            cell.fill = SUB_FILL
        elif kind == "T":
            cell.fill = TOT_FILL; cell.font = TOT_FONT
    for j, col in enumerate(ALL):
        v = m[col]
        cell = ws.cell(rr, nk + 1 + j)
        if col == "复贷客数" and kind in ("S", "T"):
            v = None  # 小计/合计去重客数不可由行加总 → 留空
        if v is None or (isinstance(v, float) and np.isnan(v)):
            cell.value = None
        elif col_kind(col) == "cnt":
            cell.value = int(v) if v is not None else None
        elif col_kind(col) == "money":
            cell.value = round(float(v), 2)
        else:
            cell.value = round(float(v), 4)
        cell.number_format = fmt(col)
        if kind == "S":
            cell.fill = SUB_FILL
        elif kind == "T":
            cell.fill = TOT_FILL; cell.font = TOT_FONT
    return rr + 1

def header(ws, rr, keynames, width=22):
    for j, h in enumerate(keynames + ALL, 1):
        c = ws.cell(rr, j, h)
        c.fill, c.font = HDR_FILL, HDR_FONT
        c.alignment = Alignment(wrap_text=True, vertical="center")
    return rr + 1

# ---------------- 主流程 ----------------
def main():
    ATOM = load_atom()
    wb = openpyxl.Workbook(); wb.remove(wb.active)

    # ---- 说明 ----
    ws = wb.create_sheet("说明")
    notes = [
        "墨西哥 老客放款 产品×评级 收益测算(双评级体系 V5_3 / V6_1) — 全 SQL 底表口径版",
        "底表(用户确认代码逐字还原): mx.wxs_application_funnel f(tenant=yawey, is_reloan=old, if_issue=1) ",
        "    联 mx.yj_test_table_250225 按 biz_id 取 max 去重后取 双评级列 与产品键 product_name_new",
        "    收窄到封口月份 release_time 2026-06-09 ~ 2026-08-31 (V5_3该区间全量; V6_1新模型仅8月出现)",
        "V5_3 = 旧主评级(1~13档, 档大=风险高);  V6_1 = 新评级(1~11档)。同一笔放款两体系都展示(各体系独立成表)。",
        "",
        "★ 逾期率 / TR 口径(用户给定, 分母统一 应还本金·期1):",
        "    本金逾期率_tN = ΣtN_overdue_capit_1     / ΣtN_should_capit_1",
        "    息费逾期率_tN = ΣtN_overdue_interest_1  / ΣtN_should_capit_1   ←分母=应还本金, 与本金逾期率同基",
        "    TR_tN = (成熟期1 前砍 + 成熟期1 应还后收 − 逾期本金1 − 逾期息费1) / Σ应还本金1",
        "    tN = 第1期还款日后 N 天; 成熟期1子集 = is_tN_window_1=1(应还本金>0 自动门控), 未到期笔自动排除。",
        "    一致性: 分子分母同批成熟 cohort ⇒ TR = 成熟前收率+成熟后收率−本金逾期率−息费逾期率 精确成立。",
        "",
        "★ 税: E 开头产品定价含 IVA16% → 息费(前砍+后收)÷1.16 为净额; A/B/C 前缀定价即净额。",
        "    税只对息费计, 本金(合同额)不计税。税后速率按净额重算; 本金逾期率不过税。",
        "    『息费税(估)占合同%』 = 净息费×16% / 合同金额 (估算)。",
        "",
        "★ 定价/期限/日息(放款 cohort 合同口径):",
        "    前收率 = 前砍费/合同金额; 后收率 = 应还后收(整单)/合同金额;",
        "    加权期限(天) = Σ(合同金额×loan_cycle)/Σ合同金额;",
        "    日息_税后% = 净息费总额/Σ(合同×期限)×100;  日息_税前% = 息费总额/Σ(合同×期限)×100。",
        "",
        "★ 可读列名对照(废弃 t0_should_amt_1 类机器名):",
        "    应还本金_期1_tN=ΣtN_should_capit_1  应还息费_期1_tN=ΣtN_should_interest_1",
        "    逾期本金_期1_tN=ΣtN_overdue_capit_1  逾期息费_期1_tN=ΣtN_overdue_interest_1",
        "    *_各期合计_tN = 期1~4逾期之和;  成熟前收(期1)_tN/成熟后收(期1)_tN = 成熟期1子集的前砍/整单应还后收",
        "    成熟笔数_期1_tN = 已成熟到 tN 的期1笔数(应还本金>0)。",
        "",
        "★ 口径与局限:",
        "    1) 复贷客数(去重)只在『月度_产品×档×月』明细行给出; 小计/合计行客数列留空(跨月/跨档去重不能由行加总)。",
        "    2) 前收率/后收率/总息费率/期限/日息按放款 cohort; 逾期率/TR 按各自成熟子集——分子分母严格同批。",
        "    3) 后收按放款时整单应还后收计(非权责逐期), 一笔放款到其期1到期日(及更晚tN)才进对应窗口。",
        "    4) TR 为粗口径经营代理(成熟息费总额 − 已现逾期), 非账务口径; 请 t0/t7/t30 同看。",
        "    5) 不含 2026-09 未封口数据; 6月为 06-09 起。",
        "    6) ★重要: 本表遵用户底表 SQL(不按 v3_flag 过滤), V5_3体系=凡评级字段非空即入表。2026-08 该口径=36,655笔,",
        "       其中含新模型(V6_1/V5_2 标记行但带 V5_3 评级)约 4,284 笔; 若仅按 v3_flag='V5_3' 过滤则 8月=32,371(6/7月两者相同)。",
        "       『校验』覆盖表给出 has_v5(无flag) 与 flag_v53(V5_3-flag) 两列可互查。",
        "",
        "★ 校验: (A) 覆盖锚点SQL对拍; (B) 表内速率列由金额列重算; (C) 独立SQL全口径重算 逐行对拍——结果见『校验』。",
    ]
    for i, t in enumerate(notes, 1):
        c = ws.cell(i, 1, t)
        c.font = Font(bold=(i <= 5 or t.startswith("★")), size=10 if i <= 5 else 9)
    ws.column_dimensions["A"].width = 156

    # ---- 行数据构建 ----
    def full_rows(g):
        """返回 rows: list[(keyvals, metric, kind)]  detail/product小计/体系合计."""
        df = ATOM[g]
        rows = []
        order = df.groupby("product")["loans"].sum().sort_values(ascending=False).index
        for prod in order:
            sub = df[df["product"] == prod]
            for gv in sorted(int(x) for x in sub["g"].dropna().unique()):
                S = sub_to_sum(sub[sub["g"] == gv])
                rows.append(([SYS[g], prod, int(gv)], metric(S), "D"))
            rows.append(([SYS[g], prod, "产品小计"], metric(aggregate(sub)), "S"))
        rows.append(([SYS[g], "全部产品", "体系合计"], metric(aggregate(df)), "T"))
        return rows

    def month_rows(g):
        df = ATOM[g]
        rows = []
        for ym in sorted(df["ym"].unique()):
            sub = df[df["ym"] == ym]
            order = sub.groupby("product")["loans"].sum().sort_values(ascending=False).index
            for prod in order:
                ps = sub[sub["product"] == prod]
                for gv in sorted(int(x) for x in ps["g"].dropna().unique()):
                    rows.append(([str(ym), SYS[g], prod, int(gv)], metric(sub_to_sum(ps[ps["g"] == gv])), "D"))
                rows.append(([str(ym), SYS[g], prod, "产品小计"], metric(aggregate(ps)), "S"))
            rows.append(([str(ym), SYS[g], "全部产品", "月合计"], metric(aggregate(sub)), "T"))
        return rows

    def grade_month_rows(g):
        df = ATOM[g]
        rows = []
        for gv in sorted(int(x) for x in df["g"].dropna().unique()):
            dg = df[df["g"] == gv]
            for ym in sorted(dg["ym"].unique()):
                rows.append(([SYS[g], int(gv), str(ym)], metric(sub_to_sum(dg[dg["ym"] == ym])), "D"))
            rows.append(([SYS[g], int(gv), "档合计"], metric(aggregate(dg)), "T"))
        return rows

    # ---- 写表 ----
    def write_sheet(name, keynames, rows, freeze):
        ws = wb.create_sheet(name)
        rr = header(ws, 1, keynames)
        nk = len(keynames)
        for keyvals, m, kind in rows:
            rr = emit(ws, rr, keyvals, m, nk, kind)
        ws.freeze_panes = freeze
        return ws, rows

    _, R_full = write_sheet("全期_产品×档", ["评级体系", "产品", "档位"],
                            full_rows(5) + full_rows(6), "D2")
    _, R_month = write_sheet("月度_产品×档×月", ["月", "评级体系", "产品", "档位"],
                             month_rows(5) + month_rows(6), "E2")
    _, R_gm = write_sheet("评级×月", ["评级体系", "档位", "月"],
                          grade_month_rows(5) + grade_month_rows(6), "D2")
    print("[装配] 全期", len(R_full), "行 / 月度", len(R_month), "行 / 评级×月", len(R_gm), "行")

    # ---- 校验(B): 表内速率列重算 ----
    badB = check_B_rows([("全期", k, m) for k, m, _ in R_full] +
                        [("月度", k, m) for k, m, _ in R_month] +
                        [("评级×月", k, m) for k, m, _ in R_gm])
    print(f"[校验B] 速率列金额重算: 异常 {len(badB)}")

    # ---- 校验(A): 覆盖锚点 ----
    cov = run_sql(sql_cov())
    print("[校验A] 覆盖(LEFT JOIN 全老客):\n", cov.to_string(index=False))

    # ---- 校验(C): 独立SQL对拍 ----
    chk_res = {}
    for g in (5, 6):
        df = run_sql(sql_chk(g))
        chk_res[g] = df
    maxdiff = 0.0; n_cmp = 0; badC = []
    for g in (5, 6):
        chk = chk_res[g]
        atom = ATOM[g]
        exp = {}
        for _, row in chk.iterrows():
            key = (row["product"], int(row["g"]))
            exp[key] = row
        # expected via atom regroup
        for (prod, gv), sub in atom.groupby(["product", "g"]):
            if (prod, int(gv)) not in exp:
                badC.append((prod, gv, "chk缺行")); continue
            m1 = metric(sub_to_sum(sub))
            m2 = metric(chk_to_sum(exp[(prod, int(gv))]))
            for col in ["放款笔数", "放款金额", "前砍费", "应还后收(总额)",
                        "前收率_税前%", "前收率_税后%", "后收率_税前%", "后收率_税后%",
                        "总息费率_税前%", "总息费率_税后%", "加权期限(天)", "日息_税后%", "日息_税前%",
                        "应还本金_期1_0", "逾期本金_期1_0", "逾期息费_期1_0", "本金逾期率_0%", "息费逾期率_0%",
                        "TR_0_税前%", "TR_0_税后%",
                        "应还本金_期1_7", "逾期本金_期1_7", "逾期息费_期1_7", "本金逾期率_7%", "息费逾期率_7%",
                        "TR_7_税前%"]:
                a, b = m1[col], m2[col]
                n_cmp += 1
                if pd.isna(a) and pd.isna(b):
                    continue
                if pd.isna(a) or pd.isna(b):
                    badC.append((prod, gv, col)); continue
                d = abs(a - b)
                if d > maxdiff:
                    maxdiff = d
                if d > 1e-4:
                    badC.append((prod, gv, col, round(a, 4), round(b, 4)))
    print(f"[校验C] 独立SQL对拍: {n_cmp} 单元格, max abs diff={maxdiff:.6g}, 异常 {len(badC)}")
    if badC[:5]:
        for x in badC[:5]:
            print("   mismatch:", x)

    # ---- 校验sheet ----
    ws = wb.create_sheet("校验")
    rr = 1
    def line(t, font=None):
        nonlocal rr
        c = ws.cell(rr, 1, t); c.font = font or SMALL_F
        rr += 1
    line("三层校验汇总", NOTE_F)
    line(f"B) 表内速率列由金额列重算: 异常 {len(badB)} 处(应为0)", NOTE_F if badB else Font(bold=True, color="006100"))
    for x in badB[:20]:
        line(f"    {x}")
    line(f"C) 独立SQL全口径对拍: 比对 {n_cmp} 个指标单元格, 最大绝对差 {maxdiff:.2e}, 异常 {len(badC)} 处(应为0)",
         NOTE_F if badC else Font(bold=True, color="006100"))
    for x in badC[:20]:
        line(f"    {x}")
    line("", SMALL_F)
    line("A) 覆盖锚点(独立LEFT JOIN全老客口径): 下表核对『原子层含档笔数』与漏斗全老客/匹配/两体系评级人数的关系",
         SMALL_F)
    cov2 = cov.copy()
    for g in (5, 6):
        cov2[f"{SYS[g]}_原子loans"] = cov2["ym"].map(
            ATOM[g].groupby("ym")["loans"].sum()).fillna(0).astype("Int64")
    rr += 1  # 空行
    cov_cols = list(cov2.columns)
    for j, cname in enumerate(cov_cols, 1):
        cell = ws.cell(rr, j, cname)
        cell.fill, cell.font = HDR_FILL, HDR_FONT
    rr += 1
    for _, r in cov2.iterrows():
        for j, cname in enumerate(cov_cols, 1):
            v = r[cname]
            if cname == "ym":
                cell = ws.cell(rr, j, str(v))
            else:
                cell = ws.cell(rr, j, int(v) if pd.notna(v) else None)
                if "biz" in cname or "loans" in cname:
                    cell.number_format = "#,##0"
        rr += 1
    line("", SMALL_F)
    line("解读: V5_3原子loans = has_v5(无flag过滤的底表口径, 与用户SQL一致); flag_v53 = 仅 v3_flag='V5_3' 口径。",
         SMALL_F)
    line("       8月 has_v5(36,655) − flag_v53(≈32,371) ≈ 4,284 笔为其他模型(V6_1/V5_2)标记行但带V5_3评级值; 6/7月两者几乎一致。",
         SMALL_F)
    line("       V6_1原子loans = has_v6(仅8月起, 15,941笔)。", SMALL_F)
    ws.column_dimensions["A"].width = 140

    wb.save(OUT_XLSX)
    print("已保存:", OUT_XLSX)

    # ---- 控制台关键读数 ----
    print("\n=== 关键读数 ===")
    for g in (5, 6):
        tot = metric(aggregate(ATOM[g]))
        print(f"{SYS[g]} 全期: 笔数 {tot['放款笔数']:.0f}  金额 {tot['放款金额']:,.0f}  "
              f"件均 {tot['件均']:.0f}  期限 {tot['加权期限(天)']:.1f}天  "
              f"前收率税前 {tot['前收率_税前%']:.2f}%  后收率税前 {tot['后收率_税前%']:.2f}%  "
              f"日息税后 {tot['日息_税后%']:.3f}%")
        for n in RATE_WINS:
            print(f"    t{n}: 本金逾期率 {tot[f'本金逾期率_{n}%']:.2f}%  息费逾期率 {tot[f'息费逾期率_{n}%']:.2f}%  "
                  f"TR税前 {tot[f'TR_{n}_税前%']:.2f}%  TR税后 {tot[f'TR_{n}_税后%']:.2f}%")

if __name__ == "__main__":
    main()
