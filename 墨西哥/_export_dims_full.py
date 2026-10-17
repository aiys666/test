# -*- coding: utf-8 -*-
"""全维度每日/每周明细导出: 每个维度下所有子项目的逐日+逐周指标表现(issue基准)"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"
XLSX = os.path.join(OUT, "墨西哥坏账_全维度每日每周明细.xlsx")

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
    return d

FUNNEL_DIMS = ["product_name","app_group","channel_category","source","product_type","product_day",
               "loan_cycle","reloan_num","contract_amount","t0_should_capit","grant_score",
               "grant_strategy","product_level","risk_level"]
YJ_DIMS = ["product_name_new","v5_3主评级","v6_1主评级","v5_3中评级","v6_1中评级","v3_flag","v3_flag_huidu",
           "fd_high_pass","if_reloan_24h","学历","婚姻","职业","有车","有房","收入段","年龄段",
           "v5_3欺诈分","v5_3行为分","当前逾期笔数","本APP逾期笔数","历史最大逾期天","他APP有逾期","最近还款间隔"]
ALL_DIMS = FUNNEL_DIMS + YJ_DIMS

SHOW_COLS = ["issue_cnt","contract_amount","件均","期限",
             "1t0本金%","1t3本金%","1t7本金%","2t0本金%","3t0本金%","4t0本金%",
             "4t3本金%","4t7本金%","4t3息费%","4t7息费%","前砍%","后收%","4t3TR%","4T7TR%",
             "is_t0_window_1","is_t3_window_4","is_t7_window_4"]
COL_RENAME = {"is_t0_window_1":"1t0出账","is_t3_window_4":"4t3出账","is_t7_window_4":"4t7出账"}

def load_dim(key):
    fp = os.path.join(OUT, f"_aggdim_{key}_issue.pkl")
    if not os.path.exists(fp): return None
    df = pd.read_pickle(fp)
    df["d"] = pd.to_datetime(df["d"])
    df["wk"] = (df["d"] - pd.to_timedelta(df["d"].dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
    return df

def build_frames(key):
    """返回 (周表, 日表), 子项目按8/10周放款笔数降序排序"""
    df = load_dim(key)
    if df is None: return None, None
    # 周表
    wk = df.groupby(["wk","dim"], as_index=False).sum(numeric_only=True)
    wk = calc_metrics(wk)
    # 日表
    dy = calc_metrics(df)
    # 排序键: 8/10周放款笔数
    order = wk[wk["wk"] == "2026-08-10"].set_index("dim")["issue_cnt"].sort_values(ascending=False)
    dim_order = list(order.index)
    # 当期没出现的子项目补到末尾
    dim_order += [x for x in wk["dim"].unique() if x not in dim_order]
    cat = pd.Categorical(wk["dim"], categories=dim_order, ordered=True)
    wk = wk.assign(_o=cat).sort_values(["_o","wk"]).drop(columns="_o")
    cat2 = pd.Categorical(dy["dim"], categories=dim_order, ordered=True)
    dy = dy.assign(_o=cat2).sort_values(["_o","d"]).drop(columns="_o")
    wk_out = wk[["wk","dim"] + SHOW_COLS].rename(columns=COL_RENAME)
    dy_out = dy[["d","dim"] + SHOW_COLS].rename(columns=COL_RENAME)
    dy_out["d"] = dy_out["d"].dt.strftime("%Y-%m-%d")
    return wk_out, dy_out

# ── 样式 ──
DARK_BLUE = "1F4E79"
HEADER_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor=DARK_BLUE)
DIM_FILL = PatternFill("solid", fgColor="E2EFDA")
RED_FILL = PatternFill("solid", fgColor="FFC7CE")
YELLOW_FILL = PatternFill("solid", fgColor="FFEB9C")
GREEN_FILL = PatternFill("solid", fgColor="C6EFCE")
NORMAL_FONT = Font(name="微软雅黑", size=9)
THIN = Side(border_style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center")
RIGHT = Alignment(horizontal="right", vertical="center")

NUM_COLS = {"issue_cnt","contract_amount","件均","1t0出账","4t3出账","4t7出账"}

def safe_name(prefix, key, used):
    name = f"{prefix}_{key}"[:31]
    base = name; i = 2
    while name in used:
        name = f"{base[:28]}_{i}"[:31]; i += 1
    used.add(name)
    return name

def write_sheet(wb, name, df, used, tcol):
    ws = wb.create_sheet(name)
    cols = list(df.columns)
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row=1, column=j, value=str(c))
        cell.fill = HEADER_FILL; cell.font = HEADER_FONT; cell.alignment = CENTER; cell.border = BORDER
    for i, (_, row) in enumerate(df.iterrows(), 2):
        for j, c in enumerate(cols, 1):
            v = row[c]
            if pd.isna(v): v = None
            cell = ws.cell(row=i, column=j, value=v)
            cell.font = NORMAL_FONT; cell.border = BORDER
            if c in NUM_COLS:
                cell.alignment = RIGHT; cell.number_format = "#,##0"
            elif c.endswith("%") or c == "期限":
                cell.alignment = RIGHT; cell.number_format = "0.00"
            elif c == "dim":
                cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = CENTER
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(df)+1}"
    widths = {"wk":11,"d":11,"dim":24,"issue_cnt":8,"contract_amount":13,"件均":8,"期限":7}
    for j, c in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(j)].width = widths.get(c, 9)
    return ws

wb = Workbook(); wb.remove(wb.active)
used = set()

# 导航页
nav = wb.create_sheet("00_导航说明")
nav["A1"] = "墨西哥坏账全维度 · 每日/每周明细（issue 放款基准，复贷 is_reloan=old）"
nav["A1"].font = Font(name="微软雅黑", size=13, bold=True, color="1F4E79")
nav["A3"] = "使用说明"
nav["A3"].font = Font(name="微软雅黑", size=11, bold=True)
notes = [
    "1. 每个维度两个 Sheet：W_维度名 = 按放款周；D_维度名 = 按放款日。",
    "2. 每个 Sheet 内子项目（dim）按 8/10 周放款笔数从大到小排序，大客群在前。",
    "3. 已冻结前两列（时间+dim）并开启筛选，可直接筛某个子项目看时间序列。",
    "4. 指标口径与 Excel 透视表完全一致（本金=逾期本金/应还本金）；4T7TR=后收%+前砍%-4t7息费%-4t7本金%。",
    "5. 出账=is_t0_window_1 / is_t3_window_4 / is_t7_window_4；近几周窗口未成熟，出账为0时坏账率为空属正常。",
    "6. 评级 dim 取值如 1.0E0=1级、1.0E1=10级、1.1E1=11级、1.2E1=12级；『空』为无评级。",
]
for i, t in enumerate(notes, 4):
    nav.cell(row=i, column=1, value=t).font = Font(name="微软雅黑", size=10)
nav.column_dimensions["A"].width = 110

nav_rows = []
for key in ALL_DIMS:
    wk_df, dy_df = build_frames(key)
    if wk_df is None:
        print(f"[skip] {key} 无数据"); continue
    wn = safe_name("W", key, used); dn = safe_name("D", key, used)
    write_sheet(wb, wn, wk_df, used, "wk")
    write_sheet(wb, dn, dy_df, used, "d")
    nav_rows.append((key, len(wk_df["dim"].unique()), wn, dn))
    print(f"[ok] {key}: 子项目 {len(wk_df['dim'].unique())} 个")

# ═══════════════ V5_3 评级自定义分档（主评级+中评级） ═══════════════
def parse_level(x):
    try: return int(round(float(x)))
    except Exception: return None

def bucket3(x):
    n = parse_level(x)
    if n is None: return "空"
    if n <= 5: return "1-5级"
    if n <= 9: return "6-9级"
    if n <= 12: return "10-12级"
    return "13级(参照)"

def bucket2(x):
    n = parse_level(x)
    if n is None: return "空"
    if n <= 5: return "1-5级"
    if n <= 12: return "6-12级"
    return "13级(参照)"

B3_ORDER = ["1-5级","6-9级","10-12级","13级(参照)","空"]
B2_ORDER = ["1-5级","6-12级","13级(参照)","空"]

def build_bucket_frames(src_key, bfn, border):
    fp = os.path.join(OUT, f"_aggdim_{src_key}_issue.pkl")
    df = pd.read_pickle(fp)
    df["d"] = pd.to_datetime(df["d"])
    df["wk"] = (df["d"] - pd.to_timedelta(df["d"].dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
    df["dim"] = df["dim"].map(bfn)
    wk = calc_metrics(df.groupby(["wk","dim"], as_index=False).sum(numeric_only=True))
    dy = calc_metrics(df)
    cat = pd.Categorical(wk["dim"], categories=border, ordered=True)
    wk = wk.assign(_o=cat).sort_values(["_o","wk"]).drop(columns="_o")
    cat2 = pd.Categorical(dy["dim"], categories=border, ordered=True)
    dy = dy.assign(_o=cat2).sort_values(["_o","d"]).drop(columns="_o")
    wk_out = wk[["wk","dim"] + SHOW_COLS].rename(columns=COL_RENAME)
    dy_out = dy[["d","dim"] + SHOW_COLS].rename(columns=COL_RENAME)
    dy_out["d"] = dy_out["d"].dt.strftime("%Y-%m-%d")
    return wk_out, dy_out

def bucket_compare(src_key, bfn, border, tag):
    """8/03 vs 8/10 分档对比表(全指标)"""
    wk, _ = build_bucket_frames(src_key, bfn, border)
    b = wk[wk["wk"] == "2026-08-03"].set_index("dim")
    c = wk[wk["wk"] == "2026-08-10"].set_index("dim")
    rows = []
    met_cols = [x for x in wk.columns if x not in ("wk","dim")]
    for d_ in border:
        if d_ not in b.index and d_ not in c.index: continue
        row = {"分档": d_}
        for m in ["issue_cnt","1t0出账","4t3出账","4t7出账"]:
            row[f"{m}_b"] = b[m].get(d_) if d_ in b.index else None
            row[f"{m}_c"] = c[m].get(d_) if d_ in c.index else None
        for m in ["1t0本金%","4t0本金%","4t3本金%","4t7本金%","4t3息费%","4t7息费%","前砍%","后收%","4t3TR%","4T7TR%","件均","期限"]:
            vb = b[m].get(d_) if d_ in b.index else None
            vc = c[m].get(d_) if d_ in c.index else None
            row[f"{m}_b"] = vb; row[f"{m}_c"] = vc
            if pd.notna(vb) and pd.notna(vc): row[f"{m}_Δ"] = round(vc - vb, 2)
            else: row[f"{m}_Δ"] = None
        rows.append(row)
    out = pd.DataFrame(rows)
    out.insert(0, "评级口径", tag)
    return out

bucket_sheets = []
cmp_frames = []
for src, tag in [("v5_3主评级","主评级"), ("v5_3中评级","中评级")]:
    for bname, bfn, border in [("三档(1-5_6-9_10-12)", bucket3, B3_ORDER), ("两档(1-5_6-12)", bucket2, B2_ORDER)]:
        wkd, dyd = build_bucket_frames(src, bfn, border)
        short = "三档" if "三档" in bname else "两档"
        wn = safe_name(f"W", f"{tag}_{short}", used)
        dn = safe_name(f"D", f"{tag}_{short}", used)
        write_sheet(wb, wn, wkd, used, "wk")
        write_sheet(wb, dn, dyd, used, "d")
        bucket_sheets.append((f"{tag}·{bname}", len(border), wn, dn))
        cmp_frames.append(bucket_compare(src, bfn, border, f"{tag}·{short}"))
        print(f"[ok] {tag} {bname}: {list(wkd['dim'].unique())}")

# 分档周对比汇总 sheet
cmp_all_df = pd.concat(cmp_frames, ignore_index=True)
wsx = wb.create_sheet("评级分档_周对比0803vs0810", 0)
cols = list(cmp_all_df.columns)
for j, c in enumerate(cols, 1):
    cell = wsx.cell(row=1, column=j, value=str(c))
    cell.fill = HEADER_FILL; cell.font = HEADER_FONT; cell.alignment = CENTER; cell.border = BORDER
for i, (_, row) in enumerate(cmp_all_df.iterrows(), 2):
    for j, c in enumerate(cols, 1):
        v = row[c]
        if pd.isna(v): v = None
        cell = wsx.cell(row=i, column=j, value=v)
        cell.font = NORMAL_FONT; cell.border = BORDER; cell.alignment = CENTER
        if c.endswith("%") or c == "期限": cell.number_format = "0.00"
        elif c in ("issue_cnt_b","issue_cnt_c","1t0出账_b","1t0出账_c","4t3出账_b","4t3出账_c","4t7出账_b","4t7出账_c","件均_b","件均_c"):
            cell.number_format = "#,##0"
        if c.endswith("_Δ") and isinstance(v, (int, float)):
            if "TR" in c or "前砍" in c or "后收" in c:
                if v <= -3: cell.fill = RED_FILL
            else:
                if v >= 4: cell.fill = RED_FILL
                elif v >= 2: cell.fill = YELLOW_FILL
                elif v <= -2: cell.fill = GREEN_FILL
wsx.freeze_panes = "C2"
wsx.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(cmp_all_df)+1}"
wsx.column_dimensions["A"].width = 14; wsx.column_dimensions["B"].width = 12
for j in range(3, len(cols)+1):
    wsx.column_dimensions[get_column_letter(j)].width = 9

# 填充导航目录
nav["A11"] = "维度目录"
nav["A11"].font = Font(name="微软雅黑", size=11, bold=True)
hdr = ["维度","子项目数","周表Sheet","日表Sheet"]
for j, h in enumerate(hdr, 1):
    c = nav.cell(row=12, column=j, value=h)
    c.fill = HEADER_FILL; c.font = HEADER_FONT
for i, (k, n, wn, dn) in enumerate(nav_rows, 13):
    nav.cell(row=i, column=1, value=k)
    nav.cell(row=i, column=2, value=n)
    nav.cell(row=i, column=3, value=wn)
    nav.cell(row=i, column=4, value=dn)
# 分档维度追加到目录
base_r = 13 + len(nav_rows)
nav.cell(row=base_r, column=1, value="—— V5_3评级自定义分档 ——").font = Font(name="微软雅黑", size=10, bold=True, color="C00000")
for i, (k, n, wn, dn) in enumerate(bucket_sheets, base_r+1):
    nav.cell(row=i, column=1, value=k)
    nav.cell(row=i, column=2, value=n)
    nav.cell(row=i, column=3, value=wn)
    nav.cell(row=i, column=4, value=dn)
for col, w in zip("ABCD", [26,10,28,28]):
    nav.column_dimensions[col].width = w

wb.save(XLSX)
print("\n已导出:", XLSX)
print("Sheet 数:", len(wb.sheetnames))
