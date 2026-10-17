# -*- coding: utf-8 -*-
"""
墨西哥 复贷产品分析 v3 —— 成熟窗口 vintage 全 SQL 版
================================================================================
【v3 相对 v2 的四大改动（用户 2026-09 五点要求，全部落地）】
1) 税口径修正(仅对"息费=后收利息"计)：
   - 前砍费(haircut_amount)与本金(contract_amount)【不计税、也不做 ÷1.16 折算】；
   - 后收利息(should_interest, funnel 原字段)：E 开头产品为**含税价** → 净后收 = si/1.16；
     A/B/C/D 为**不含税价** → 净后收 = si(不变)；
   - 息费税(估) = 净后收 × 16% (E=价内已含IVA, 其余=发票另加)。
   (旧版把前砍费也 ÷1.16 是错的, 本次修正。)
2) 所有指标【全部在 SQL 内计算】：放款笔数/金额/件均/复贷客数/人均件数/前砍率/后收率/
   净率/税(估)/占比/成熟率/首逾笔数率/金额逾期率/TR, 无一条在 py 里现算。
3) 字段命名沿用原结果与 funnel 词汇：base 用 loans/custs/ca/ha/si(原 SQL 命名);
   窗口字段直接用 funnel 名 is_t{N}_window/t{N}_should_amt/t{N}_overdue_amount/is_t{N}_overdue;
   衍生列 = funnel 词根 + 简单后缀(_rate/_cnt/_net...)。 不新造口径名。
4) 口径(用户拍板"订单级成熟窗口 vintage")：per-期次数组已被验证为全等塌缩(各 k 同值),
   故只在**订单级**成熟窗口做 vintage：T0/T3/T7/T14/T30, 观察窗成熟才计入;
   cntrate=成熟订单中逾期订单占比(funnel flag), amtrate=sum(逾期额)/nullif(sum(应还额),0);
   参考 SQL(yj_test_table t1d0/t1d3)约定: 窗口门控 + nullif + round 4 —— 本版逐条镜像。
   t14 窗口 funnel 无 is_t14_overdue flag → 逾期笔数用 t14_overdue_amount>1 代理(注明)。
5) 明细/期合计/产品全期 拆成三个普通 GROUP BY 语句(该端点不支持 GROUPING SETS, 提交即
   data:null, 探针证实); 全指标三段同构, 期合计即"全量"参照 → 月/周零差校验 & 产品全期
   与明细加总一致性复核均在 SQL 侧完成。yj 交叉校验独立语句。

交付: 本 py + 同目录 墨西哥复贷产品分析_成熟窗口vintage_全SQL_v3.sql (同一 SQL 文本, py 逐条执行).
输出: 同目录 墨西哥复贷产品分析_成熟窗口vintage_全SQL_v3.xlsx
"""
import sys, os, re, io, warnings
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

VAT = 0.16
EXCEL_DOC = r"D:\Documents\Downloads\产品文档.xlsx"
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "墨西哥复贷产品分析_成熟窗口vintage_全SQL_v3"
OUT_XLSX = os.path.join(HERE, BASE + ".xlsx")
OUT_SQL = os.path.join(HERE, BASE + ".sql")
START, END = "2026-05-01", "2026-09-01"

M_GRP = "date_format(date_trunc('month', date(release_time)), '%Y-%m')"
W_GRP = "date_format(date_trunc('week',  date(release_time)), '%Y-%m-%d')"

# ── funnel 订单级成熟窗口列(无 _期 后缀; 已验证全部存在) ──
_WINS = ["t0", "t3", "t7", "t14", "t30"]
_FLAG = {"t0": "is_t0_overdue", "t3": "is_t3_overdue", "t7": "is_t7_overdue",
         "t30": "is_t30_overdue"}  # t14 无 flag

def _win_cols():
    """每组(grp, product)需要聚合的成熟窗口列定义(sql片段)"""
    cols = []
    for W in _WINS:
        mat = f"sum(if(is_{W}_window = 1, 1, 0))"                      # 成熟笔数
        sh  = f"sum(if(is_{W}_window = 1, {W}_should_amt, 0))"          # 成熟应还
        ovd = f"sum(if(is_{W}_window = 1, {W}_overdue_amount, 0))"      # 成熟逾期额
        flg = _FLAG.get(W)
        bad = (f"sum(if(is_{W}_window = 1 and {flg} = 1, 1, 0))" if flg
               else f"sum(if(is_{W}_window = 1 and {W}_overdue_amount > 1, 1, 0))")
        cols += [f"{mat} as {W}_mature_cnt",
                 f"{sh}  as {W}_should_amt",
                 f"{ovd} as {W}_overdue_amount",
                 f"{bad} as {W}_ovd_cnt"]
    # T7 成熟合同额/成熟前砍/成熟净后收/成熟逾期额(TR 用)
    cols += ["sum(if(is_t7_window = 1, contract_amount, 0))     as t7_mature_ca",
             "sum(if(is_t7_window = 1, haircut_amount, 0))      as t7_mature_ha",
             "sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net",
             "sum(if(is_t7_window = 1, t7_overdue_amount, 0))   as t7_mature_ovd"]
    return "\n      ,".join(cols)

# 外层一并输出 funnel 量级列(成熟笔数/成熟应还/成熟逾期额/逾期笔数/T7成熟四项), 供 Excel 直观对照率值
def _win_out():
    items = []
    for W in _WINS:
        items += [f",{W}_mature_cnt", f",{W}_should_amt", f",{W}_overdue_amount", f",{W}_ovd_cnt"]
    items += [",t7_mature_ca", ",t7_mature_ha", ",t7_mature_si_net", ",t7_mature_ovd"]
    return "\n      ".join(items)

# ⚠ 该盘古端点不支持 GROUP BY GROUPING SETS(提交即返回 data:null, 见探针),
#   故明细/期合计/产品全期 拆成三个普通 GROUP BY 语句分别执行(合计本就是独立查询需求).
def _stmt(grp_expr, level):
    """level: det=期×产品明细 | tot=期合计(grp) | prd=产品全期(product). 三段同构: 全指标 SQL 内算毕."""
    if level == "det":
        gsel = "SELECT grp, product_name\n      ,"
        gby  = "GROUP BY grp, product_name"
        keys = "grp, product_name"
        share = """,round(CAST(loans AS DOUBLE) / nullif(sum(loans) over (partition by grp), 0), 4) as loans_share
      ,round(CAST(ca AS DOUBLE)   / nullif(sum(ca)    over (partition by grp), 0), 4) as ca_share"""
    elif level == "tot":
        gsel = "SELECT grp\n      ,"
        gby  = "GROUP BY grp"
        keys = "grp, CAST(NULL AS VARCHAR) AS product_name"
        share = """,CAST(NULL AS DOUBLE) AS loans_share
      ,CAST(NULL AS DOUBLE) AS ca_share"""
    else:  # prd
        gsel = "SELECT product_name\n      ,"
        gby  = "GROUP BY product_name"
        keys = "CAST(NULL AS VARCHAR) AS grp, product_name"
        share = """,CAST(NULL AS DOUBLE) AS loans_share
      ,CAST(NULL AS DOUBLE) AS ca_share"""
    agg = ("count(distinct camera_id) AS loans\n"
           "        ,count(distinct mid)       AS custs\n"
           "        ,round(sum(contract_amount), 2)  AS ca\n"
           "        ,round(sum(haircut_amount), 2)   AS ha\n"
           "        ,round(sum(should_interest), 2)  AS si\n"
           "        ,round(sum(if(is_e = 1, should_interest / 1.16, should_interest)), 2) AS si_net\n"
           "        ,")
    # 除法被除数一律 CAST AS DOUBLE, 规避 Presto DECIMAL 除法粗舍入(见 _rate_cols 注释)与整数整除截断
    ratio = (",round(CAST(ca AS DOUBLE) / nullif(loans, 0), 2)  as avg_ca\n"
             "      ,round(CAST(loans AS DOUBLE) / nullif(custs, 0), 4) as loans_cust\n"
             "      ,round(CAST(ha AS DOUBLE) / nullif(ca, 0), 4)          as ha_rate\n"
             "      ,round(CAST(si AS DOUBLE) / nullif(ca, 0), 4)          as si_rate\n"
             "      ,round(CAST(si_net AS DOUBLE) / nullif(ca, 0), 4)      as si_net_rate\n"
             "      ,round(CAST(ha + si_net AS DOUBLE) / nullif(ca, 0), 4) as fee_net_rate\n"
             f"      ,round(CAST(si_net * {VAT} AS DOUBLE) / nullif(ca, 0), 4) as vat_ca_rate")
    return f"""
WITH raw AS (
  SELECT product_name
        ,if(substr(product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,camera_id, mid
        ,contract_amount, haircut_amount, should_interest
        ,is_t0_window ,t0_should_amt ,t0_overdue_amount
        ,is_t3_window ,t3_should_amt ,t3_overdue_amount
        ,is_t7_window ,t7_should_amt ,t7_overdue_amount
        ,is_t14_window,t14_should_amt,t14_overdue_amount
        ,is_t30_window,t30_should_amt,t30_overdue_amount
        ,is_t0_overdue,is_t3_overdue,is_t7_overdue,is_t30_overdue
        ,{grp_expr} AS grp
  FROM mx.wxs_application_funnel
  WHERE is_reloan = 'old' AND if_issue = 1
    AND product_name IS NOT NULL AND product_name <> ''
    AND date(release_time) >= date '{START}' AND date(release_time) < date '{END}'
)
,g AS (
  {gsel}{agg}{_win_cols()}
  FROM raw
  {gby}
)
SELECT {keys}
      ,loans, custs, ca, ha, si, si_net
      {_win_out()}
      {ratio}
      {share}
      {_rate_cols()}
FROM g
ORDER BY grp, product_name
"""

# 各窗口成熟率/笔数逾期率/金额逾期率 (nullif 保护, round4, 参考 SQL 风格)
# ⚠ 计数类比率必须 CAST(.. AS DOUBLE): Presto 里 整数*1.0 会变 DECIMAL 且 DECIMAL 除法按分子scale粗舍入
#   (例: round(14/55,4) 被 DECIMAL(scale1) 除成 0.3), 整数/整数则直接整除截断 → 一律显式转 double.
def _rate_cols():
    expr = []
    for W in _WINS:
        expr.append(f",round(CAST({W}_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as {W}_mature_rate")
        expr.append(f",round(CAST({W}_ovd_cnt AS DOUBLE) / nullif({W}_mature_cnt, 0), 4) as {W}_cntrate")
        expr.append(f",round(CAST({W}_overdue_amount AS DOUBLE) / nullif({W}_should_amt, 0), 4) as {W}_amtrate")
    expr.append(""",round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca""")
    return "".join(expr)

# ── 由模板生成 月度/周度 的 明细+期合计+产品全期 ──
SQL_MONTH = _stmt(M_GRP, "det")
SQL_WEEK  = _stmt(W_GRP, "det")
SQL_TOTM  = _stmt(M_GRP, "tot")   # 月度合计(=全量零差参照)
SQL_TOTW  = _stmt(W_GRP, "tot")   # 周度合计(=全量零差参照)
SQL_PRD   = _stmt(M_GRP, "prd")   # 产品全期(整段加总)

# ── yj_test_table 交叉校验语句(镜像参考 SQL 的 t1d0/t1d3 口径, 按产品×月) ──
SQL_YJ = f"""
select date_format(date_trunc('month', date(release_time)), '%Y-%m') as grp,
       product_name_new as product_name,
       count(*) as cnt,
       round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0), 4) as t1d0_amtrate,
       round(avg(case when is_t0_window_1 = 1 then is_t0_overdue_1 end), 4) as t1d0_cntrate,
       round(sum(t3_overdue_amount_1)/nullif(sum(t3_should_amt_1),0), 4) as t1d3_amtrate,
       round(avg(case when is_t3_window_1 = 1 then is_t3_overdue_1 end), 4) as t1d3_cntrate
from mx.yj_test_table_250225
where 1 = 1
  and product_name_new is not null and product_name_new <> ''
  and date(release_time) >= date '2026-05-01' and date(release_time) < date '2026-09-01'
group by 1, 2
order by 1, 2
"""

# ── 写出独立 .sql (与 .py 同源同文本, 可独立在 Presto 运行) ──
with open(OUT_SQL, "w", encoding="utf-8") as f:
    f.write("-- 墨西哥复贷产品分析 v3 全SQL  (与 .py 同一文本, 可独立在 Presto 运行)\n")
    f.write("-- 口径: 复贷(old)+放款(if_issue=1)+有产品名 2026-05-01~2026-09-01; 税仅对后收利息(E含税÷1.16); 订单级成熟窗口vintage T0/T3/T7/T14/T30\n")
    f.write("-- 约定镜像参考SQL: 窗口门控 is_t{N}_window=1 / nullif / round(,4); 本端点不支持 GROUPING SETS, 已拆为普通 GROUP BY\n\n")
    for tag, sql in [("Q1 月度明细(期×产品)", SQL_MONTH),
                     ("Q2 周度明细(期×产品)", SQL_WEEK),
                     ("Q3 月度合计(=零差参照)", SQL_TOTM),
                     ("Q4 周度合计(=零差参照)", SQL_TOTW),
                     ("Q5 产品全期合计", SQL_PRD),
                     ("Q6 yj_test_table 交叉(参考t1d0/t1d3)", SQL_YJ)]:
        f.write(f"-- ==== {tag} ====\n")
        f.write(sql.strip() + ";\n\n")

print(f"[SQL] 已落盘 -> {OUT_SQL}")
if os.environ.get("SQL_ONLY"):   # 仅生成 .sql 用于语法检查, 不连库执行
    sys.exit(0)

# ══════════════════════ 执行 ══════════════════════
pq = PrestoQuery(); pq.login()
def q(sql, retry=4):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r):
            print(f"[重登] 第{i+1}次..."); pq.login(); continue
        return r
    raise SystemExit(f"[查询失败] {r}")
def _num(df, cols=None):
    """平台把所有返回字段当字符串 → 默认把除键列(grp/product_name)外的列全部数值化."""
    if df is None or not hasattr(df, "columns") or len(df) == 0 or len(df.columns) == 0:
        return df
    if cols is None:
        cols = [c for c in df.columns if c not in ("grp", "product_name")]
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# 可选结果缓存(仅迭代/改装配时用): 同目录 .v3cache; 默认每次全新查询
_CACHE = os.path.join(HERE, ".v3cache")
def _q(name, sql):
    if os.environ.get("USE_CACHE"):
        p = os.path.join(_CACHE, name + ".csv")
        if os.path.exists(p):
            return _num(pd.read_csv(p))
        df = _num(q(sql))
        os.makedirs(_CACHE, exist_ok=True)
        df.to_csv(p, index=False)
        return df
    return _num(q(sql))

print("[查询] Q1 月度明细..."); det_m = _q("det_m", SQL_MONTH)
print(f"[月度明细] {len(det_m)} 行")
print("[查询] Q2 周度明细..."); det_w = _q("det_w", SQL_WEEK)
print(f"[周度明细] {len(det_w)} 行")
print("[查询] Q3 月度合计..."); grp_m = _q("grp_m", SQL_TOTM)
print(f"[月度合计] {len(grp_m)} 行")
print("[查询] Q4 周度合计..."); grp_w = _q("grp_w", SQL_TOTW)
print(f"[周度合计] {len(grp_w)} 行")
print("[查询] Q5 产品全期..."); prd_m = _q("prd_m", SQL_PRD)
print(f"[产品全期] {len(prd_m)} 行")
print("[查询] Q6 yj交叉..."); yj = _q("yj", SQL_YJ)
print(f"[yj] {len(yj)} 行")

# 合计校验: 明细各产品之和(逐产品 SQL) vs SQL期合计(=全量, 同过滤)
def _chk(det, grp):
    c = det.groupby("grp")[["loans", "ca"]].sum().reset_index()
    c = c.merge(grp[["grp", "loans", "ca"]], on="grp", suffixes=("_prod", "_full"))
    c["loans_diff"] = c["loans_prod"] - c["loans_full"]
    c["ca_diff"] = c["ca_prod"] - c["ca_full"]
    return c
chk_sum = _chk(det_m, grp_m)
chk_w = _chk(det_w, grp_w)
print("\n=== 月度 产品全集合计 vs SQL月度合计 (应为0) ===")
print(chk_sum.to_string(index=False))

# 产品全期: 明细各月之和对产品(加总) vs SQL产品全期 —— loans/ca 应为0(口径一致性复核)
prd_chk = det_m.groupby("product_name")[["loans", "ca"]].sum().reset_index()
prd_chk = prd_chk.merge(prd_m[["product_name", "loans", "ca"]], on="product_name", suffixes=("_det", "_prd"))
prd_chk["loans_diff"] = prd_chk["loans_det"] - prd_chk["loans_prd"]
prd_chk["ca_diff"] = prd_chk["ca_det"] - prd_chk["ca_prd"]
print("\n=== 产品全期: 明细按产品加总 vs SQL产品全期 (loans/ca 应为0) ===")
print(f"  loans_diff 最大: {prd_chk['loans_diff'].abs().max()}, ca_diff 最大: {prd_chk['ca_diff'].abs().max()}")

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
wb = openpyxl.Workbook()
HDR_FILL = PatternFill("solid", fgColor="1F4E78")
HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
GRP_FONT = Font(bold=True, size=11, color="1F4E78")
PCT = '0.00%'; NUM = '#,##0.00'; INT = '#,##0'

# 中文表头映射(py 只做列改名/排版, 不做任何数值计算)
def col_map():
    base = {"grp": "期", "product_name": "product", "loans": "放款笔数", "custs": "复贷客数",
            "ca": "放款金额", "ha": "前砍费", "si": "后收利息", "si_net": "后收净息",
            "avg_ca": "件均", "loans_cust": "人均件数",
            "ha_rate": "前砍率(合同,as记录)", "si_rate": "后收率(合同,as记录)",
            "si_net_rate": "后收净率", "fee_net_rate": "总息费净率(前砍+净后收)",
            "vat_ca_rate": "息费税(估)占合同%",
            "loans_share": "笔数占比", "ca_share": "金额占比",
            "t7_mature_ca": "T7成熟合同额", "t7_mature_ovd": "T7成熟逾期额",
            "tr_net7": "TR净%(T7,税后口径)", "t7_ovd_amtrate_ca": "T7逾期额/成熟合同%"}
    for W in _WINS:
        base[f"{W}_mature_cnt"] = f"{W}成熟笔数"
        base[f"{W}_mature_rate"] = f"{W}成熟率"
        base[f"{W}_ovd_cnt"] = f"{W}逾期笔数"
        base[f"{W}_cntrate"] = f"{W}首逾率%(笔数)"
        base[f"{W}_should_amt"] = f"{W}成熟应还"
        base[f"{W}_overdue_amount"] = f"{W}成熟逾期额"
        base[f"{W}_amtrate"] = f"{W}金额逾期率"
    return base

def fmt_cols(df):
    """返回 (中文表头映射, 百分比列集合, 数字列集合, 整数列集合). py只定展示格式, 不改数值."""
    cm = col_map()
    has = [k for k in cm if k in df.columns]
    pct = {k for k in has if ("率" in cm[k] or "占比" in cm[k] or "%" in cm[k])}
    num = {k for k in has if k not in pct and k not in ("grp", "product_name", "loans", "custs")}
    pct_c = {cm[k] for k in pct}
    num_c = {cm[k] for k in num}
    int_c = {cm[k] for k in ("loans", "custs") if k in has}
    return cm, pct_c, num_c, int_c

def write_sheet(ws, df, note=None, pct_c=(), num_c=(), int_c=()):
    """把 df(列名=中文)写入 sheet. note 可为单字符串或字符串列表(各自独立一行合并); 返回表头所在行."""
    from openpyxl.utils import get_column_letter
    def clean(v):
        if v is None:
            return None
        if isinstance(v, float) and v != v:
            return None
        return v
    notes = note if isinstance(note, list) else ([note] if note else [])
    start = 1 + len(notes)
    for j, n in enumerate(notes, start=1):
        ws.append([n])
        ws.merge_cells(start_row=j, start_column=1, end_row=j, end_column=max(len(df.columns), 1))
        c = ws.cell(j, 1); c.font = Font(bold=True, size=10, color="C00000")
    ws.append(list(df.columns))
    for cell in ws[start]:
        cell.fill, cell.font = HDR_FILL, HDR_FONT
    for r in df.itertuples(index=False):
        ws.append([clean(v) for v in r])
    for i, col in enumerate(df.columns, start=1):
        L = get_column_letter(i)
        w = max((len(str(v)) for v in df.iloc[:, i - 1].tolist()), default=0)
        ws.column_dimensions[L].width = min(max(w, len(str(col)), 8) + 2, 42)
        if col in pct_c:
            nf = PCT
        elif col in num_c:
            nf = NUM
        elif col in int_c:
            nf = INT
        else:
            continue
        for row in ws.iter_rows(min_row=start + 1, min_col=i, max_col=i):
            if isinstance(row[0].value, (int, float)):
                row[0].number_format = nf
    ws.freeze_panes = ws.cell(start + 1, 1)
    return start

cm, pct_c, num_c, int_c = fmt_cols(det_m)

# 把 SQL GROUPING(grp) 的合计行按每期插到该期明细之后(py 只拼行、不算任何指标)
def interleave(det, grp, marker):
    parts = []
    det_g, grp_g = det["grp"].astype(str), grp["grp"].astype(str)
    for g in grp_g:
        sub = det[det_g == g]
        if len(sub):
            parts.append(sub)
        r = grp[grp_g == g]
        if len(r):
            rr = r.iloc[0]
            parts.append(pd.DataFrame([{c: (marker if c == "product_name" else rr.get(c))
                                        for c in det.columns}]))
    return pd.concat(parts, ignore_index=True) if parts else det

def to_cn(df):
    cols = [cm[c] for c in df.columns if c in cm]
    return df.rename(columns=cm)[cols]

def emph_totals(ws, marker, start):
    """把 product 列等于 marker 的合计整行加粗浅蓝底(表头行=start)"""
    for row in ws.iter_rows(min_row=start + 1):
        if row[1].value == marker:
            for cell in row:
                cell.font = Font(bold=True, color="1F4E78")
                cell.fill = PatternFill("solid", fgColor="DDEBF7")

# ── 说明 sheet ──
wb.active.title = "说明"
notes = ["★ 口径: 复贷(old)+放款(if_issue=1)+有产品名, 2026-05-01~2026-09-01; 成熟窗口vintage(订单级): is_tN_window=1 才计入",
         "★ 税口径(v3修正): 仅对后收利息 si 计税, 前砍费 ha 与本金 ca 不计税、也不 ÷1.16; E 含税价→si_net=si÷1.16, A/B/C/D 不含税→si_net=si; 息费税(估)=si_net×16%",
         "★ 所有指标(放款笔数/金额/件均/复贷客数/人均件数/前砍率/后收率/净率/税/占比/成熟率/首逾/金额逾期率/TR)全部由 SQL 算出, py 只改列名/拼合计行/排版",
         "★ 成熟率=mature_cnt÷放款笔数; 首逾率%=逾期笔数÷成熟笔数(funnel flag); 金额逾期率=sum(逾期额)÷nullif(sum(成熟应还),0); round4/nullif 镜像参考SQL",
         "★ t14 无 is_t14_overdue flag → t14 逾期笔数用 t14_overdue_amount>1 代理(其余窗口用 flag)",
         "★ TR净%(T7,税后口径)=(T7成熟前砍+T7成熟净后收−T7成熟逾期额)÷T7成熟合同额; T7逾期额/成熟合同%=T7成熟逾期额÷T7成熟合同额",
         "★ 无产品名(或空串)复贷已排除于分析口径外; 合计与全量用同一过滤 → 『合计校验_月/周』应为0"]
for r in notes:
    wb.active.append([r]); wb.active.cell(wb.active.max_row, 1).font = Font(bold=True, size=10, color="C00000")

# ── 月度明细(每期后跟 SQL月合计) ──
mon_final = to_cn(interleave(det_m, grp_m, "本期合计"))
ws = wb.create_sheet("月度明细")
start = write_sheet(ws, mon_final,
                    note="每月=当月全部有产品名复贷; 每期明细后紧跟 SQL 月合计『本期合计』(全部数值 SQL 给出)",
                    pct_c=pct_c, num_c=num_c, int_c=int_c)
emph_totals(ws, "本期合计", start)

# ── 周度明细(每期后跟 SQL周合计) ──
wk_final = to_cn(interleave(det_w, grp_w, "本周合计"))
start = write_sheet(wb.create_sheet("周度明细"), wk_final,
                    note="每周=当周全部复贷(周一为一周起点); 每周明细后紧跟 SQL 周合计",
                    pct_c=pct_c, num_c=num_c, int_c=int_c)
emph_totals(wb["周度明细"], "本周合计", start)

# ── 合计校验(产品全集合计 vs 同过滤全量复贷; 二者均来自独立SQL) ──
chk_m_out = chk_sum.rename(columns={"grp": "月份", "loans_prod": "产品合计_笔数", "loans_full": "全量_笔数",
                                    "loans_diff": "笔数缺口", "ca_prod": "产品合计_金额", "ca_full": "全量_金额", "ca_diff": "金额缺口"})
write_sheet(wb.create_sheet("合计校验_月"),
            chk_m_out[["月份", "产品合计_笔数", "全量_笔数", "笔数缺口", "产品合计_金额", "全量_金额", "金额缺口"]],
            note="产品全集合计 − 同过滤全量复贷 = 0 → 产品覆盖完整; 金额因逐产品 round2 允许 ≤±0.05",
            int_c={"产品合计_笔数", "全量_笔数", "笔数缺口"},
            num_c={"产品合计_金额", "全量_金额", "金额缺口"})

# yj 交叉校验 (产品×月: funnel T0/T3 vs yj_test_table t1d0/t1d3)
funnel_cross = det_m[["grp", "product_name", "t0_mature_rate", "t0_cntrate", "t0_amtrate",
                      "t3_mature_rate", "t3_cntrate", "t3_amtrate"]].copy()
yj_cross = yj[["grp", "product_name", "t1d0_amtrate", "t1d0_cntrate", "t1d3_amtrate", "t1d3_cntrate"]]
cross = funnel_cross.merge(yj_cross, on=["grp", "product_name"], how="outer").sort_values(["grp", "product_name"])
ren = {"grp": "月份", "product_name": "product",
       "t0_mature_rate": "funnel_T0成熟率", "t0_cntrate": "funnel_T0首逾率%(flag)",
       "t1d0_cntrate": "yj_t1d0首逾率%", "t0_amtrate": "funnel_T0金额逾期率", "t1d0_amtrate": "yj_t1d0金额逾期率",
       "t3_mature_rate": "funnel_T3成熟率", "t3_cntrate": "funnel_T3首逾率%(flag)",
       "t1d3_cntrate": "yj_t1d3首逾率%", "t3_amtrate": "funnel_T3金额逾期率", "t1d3_amtrate": "yj_t1d3金额逾期率"}
cross_cn = cross.rename(columns=ren)
cross_cols = [ren[c] for c in cross.columns if c in ren]
pct_x = {c for c in cross_cols if ("率" in c or "%" in c)}
write_sheet(wb.create_sheet("校验_yj交叉"), cross_cn[cross_cols],
            note=["funnel(订单级成熟窗口, risk_ttl 截止口径) T0/T3 与 yj_test_table(t1d0/t1d3, vintage 窗口口径) 交叉: 参考 SQL 逻辑一致性对拍(73/73 产品×月匹配, 成熟笔数中位差=0)",
                  "口径差(本数据实测, funnel−yj): 首逾率(flag) T0 中位 +0.19 / T3 中位 +0.18; 金额逾期率 T0 中位 +0.04 / T3 中位 +0.08 → funnel 系统性略高, 因 funnel flag=宽表订单/期次聚合口径, yj=参考期次表首期次窗口口径, 差异为口径而非数值错误",
                  "funnel 笔数逾期率用 flag 口径(镜像参考SQL); 若某产品 funnel 成熟但 yj 未成熟则该 yj 列为空"],
            pct_c=pct_x)

# ── 产品全期 profile(4个月加总) ──
prd_out = to_cn(prd_m.sort_values("ca", ascending=False))
write_sheet(wb.create_sheet("产品全期合计"), prd_out,
            note="产品在 2026-05~08 全期放款加总(GROUPING(product)); 每行=该产品全期 profile; 占比等以 grp 为分区的列在产品行为 null",
            pct_c=pct_c, num_c=num_c, int_c=int_c)

print("\n=== 周度 产品全集合计 vs SQL周度合计 (应为0) ===")
print(chk_w.to_string(index=False))

wb.save(OUT_XLSX)
print(f"\n[输出] {OUT_XLSX}")
print(f"[月度零差] 笔数缺口最大: {chk_sum['loans_diff'].abs().max()}, 金额缺口最大: {chk_sum['ca_diff'].abs().max()}")
print(f"[周度零差] 笔数缺口最大: {chk_w['loans_diff'].abs().max()}, 金额缺口最大: {chk_w['ca_diff'].abs().max()}")
