# -*- coding: utf-8 -*-
"""
合并字段字典 + 对比参考字典 + 落实vintage口径更正 + 重新生成xlsx
"""
import json, re, glob, os
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

DATA_DIR = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\field_dict_data"
REF = os.path.join(DATA_DIR, "reference_dict.json")
OUT_XLSX = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\墨西哥老客核心字段字典.xlsx"
OUT_CMP = os.path.join(DATA_DIR, "comparison.json")

# ---------- 1. 加载我的数据 ----------
my_data = {}          # table -> [fields]
file_of = {}          # table -> src_file
for fp in sorted(glob.glob(os.path.join(DATA_DIR, "*.json"))):
    if "reference" in fp or "comparison" in fp:
        continue
    for t in json.load(open(fp, encoding="utf-8")):
        my_data.setdefault(t["table"], []).extend(t["fields"])
        file_of[t["table"]] = t.get("source_file", os.path.basename(fp))

# ---------- 2. 加载参考字典 ----------
ref = json.load(open(REF, encoding="utf-8"))
ref_map = defaultdict(list)   # lower(name) -> [(sheet, cn, logic)]
for sheet, fields in ref.items():
    for f in fields:
        if f["name"]:
            ref_map[f["name"].lower()].append((sheet, f["cn"], f["logic"]))

# 同表参考sheet优先
SAME_REF = {
    "mx.wxs_application_funnel_1": "wxs_application_funnel ",
    "mx.wxs_application_funnel_2": "wxs_application_funnel ",
    "mx.wxs_application_funnel": "wxs_application_funnel ",
}

# ---------- 3. vintage 口径更正（全量覆盖 all4/all5 所有字段模式） ----------
_WIN = {"pre3": "应还日前3天起窗口", "pre2": "应还日前2天起窗口", "pre1": "应还日当天起窗口",
        "0": "已过应还日", "1": "逾期≥2天", "2": "逾期≥3天", "3": "逾期≥4天",
        "7": "逾期≥8天", "15": "逾期≥16天", "30": "逾期≥31天", "now": "当前"}
_WINRE = r"(pre3|pre2|pre1|0|1|2|3|7|15|30|now)"

# 度量映射（capital/amount/amt 均为金额；注意 regex 中 capital 写在 capit 后也会正确匹配）
_MEAS = {"cnt": "笔数", "capit": "本金", "capital": "金额", "amount": "金额",
         "amt": "金额", "interest": "利息", "coupon_substract": "减免及券成本"}
_VERB = {"should": "应还", "overdue": "逾期"}

def window_desc(w):
    return _WIN.get(w, w)

def _msr(verb, meas):
    return f"{_VERB[verb]}{_MEAS.get(meas, meas)}"

# all4 源字段: should/overdue_(cnt|capit|capital|amount|interest)_(期次)_(窗口)
_PAT4 = re.compile(rf"^(should|overdue)_(cnt|capit|capital|amount|interest)_(\d+)_{_WINRE}$")
# all4 减免及券成本
_PAT_coupon = re.compile(rf"^coupon_substract_(\d+)_{_WINRE}$")
# all4 提前还款: pre_repay_tm{N}_amt_{期次}
_PAT_repay = re.compile(r"^pre_repay_tm(\d+)_amt_(\d+)$")
# all5 是否逾期标记/窗口标记
_PAT_isOvd = re.compile(rf"^is_t{_WINRE}_overdue_(\d+)$")
_PAT_isWin = re.compile(rf"^is_t{_WINRE}_window_(\d+)$")
# all5 进件级逾期: is_t{win}_overdue（无期次，取各期次最大）
_PAT_isOvdTop = re.compile(r"^is_t(0|1|2|3|7|15|30)_overdue$")
# all5 别名: t{win}_{should|overdue}_{cnt|capit|capital|amount|amt|interest}_{期次}
_PAT_tMeas = re.compile(rf"^t{_WINRE}_(should|overdue)_(cnt|capit|capital|amount|amt|interest)_(\d+)$")
# all5 别名减免: t{win}_coupon_substract_{期次}
_PAT_tCoupon = re.compile(rf"^t{_WINRE}_coupon_substract_(\d+)$")
# 当前是否逾期（无窗口）
_PAT5a = re.compile(r"^is_now_overdue_(\d+)$")

def fix_vintage(name):
    m = _PAT4.match(name)
    if m:
        verb, meas, idx, win = m.groups()
        return f"第{idx}期 {window_desc(win)} {_msr(verb, meas)}"
    m = _PAT_coupon.match(name)
    if m:
        idx, win = m.groups()
        return f"第{idx}期 {window_desc(win)} 减免及券成本"
    m = _PAT_repay.match(name)
    if m:
        tm, idx = m.groups()
        if tm == "0":
            return f"第{idx}期 应还日当天及之前还款金额(本+息)"
        return f"第{idx}期 提前还款金额(本+息,到期前≥{tm}天)"
    m = _PAT_isOvd.match(name)
    if m:
        win, idx = m.groups()
        return f"第{idx}期 {window_desc(win)} 是否逾期标记"
    m = _PAT_isWin.match(name)
    if m:
        win, idx = m.groups()
        return f"第{idx}期 {window_desc(win)} 窗口标记"
    m = _PAT_isOvdTop.match(name)
    if m:
        return f"进件级是否{window_desc(m.group(1))}未结清(取各期次最大)"
    m = _PAT_tMeas.match(name)
    if m:
        win, verb, meas, idx = m.groups()
        return f"第{idx}期 {window_desc(win)} {_msr(verb, meas)}"
    m = _PAT_tCoupon.match(name)
    if m:
        win, idx = m.groups()
        return f"第{idx}期 {window_desc(win)} 减免及券成本"
    m = _PAT5a.match(name)
    if m:
        return f"第{m.group(1)}期 当前是否逾期(未结清)"
    return None

# ---------- 4. 参考释义补强 ----------
# 先回滚上次运行产生的 desc_orig（保证幂等）
for tbl, fields in my_data.items():
    for f in fields:
        if "desc_orig" in f:
            f["desc"] = f["desc_orig"]
            del f["desc_orig"]

def has_detail(s):
    s = s or ""
    # 含枚举/映射/码值细节的视为"已足够细"
    if any(ch in s for ch in "()/：:=→"):
        return True
    return len(s) >= 14

# 用户确认口径：业务专家逐字段给出答案（多数采用参考字典释义，product_name 确认"产品名称"），强制覆盖
FORCE_DESC = {
    ("mx.wxs_application_funnel_1", "app_id"): "应用ID",
    ("mx.wxs_application_funnel_1", "product_name"): "产品名称",
    ("mx.wxs_application_funnel_1", "repay_amount"): "还款金额",
    ("mx.wxs_application_funnel_1", "double_loan"): "是否为复贷",
    ("mx.wxs_aurora_za", "should_capital"): "应还本金",
    ("mx.wxs_aurora_za", "if_issue"): "是否放款标志",
    ("mx.yj_reloan_prof", "if_sx_passed"): "是否用信",
    ("mx.yj_test_table_250225", "if_sx_passed"): "是否用信",
    ("mx.property_v5_1_feature_bin", "if_sx_passed"): "是否用信",
    ("darren_risk_wide_table", "credit_amount"): "授信总额",
    ("darren_risk_wide_table", "new_media_source"): "获客渠道",
    ("darren_risk_wide_table", "app_group"): "应用分组",
    ("mx.darren_jieqing_dt_table", "credit_amount"): "授信总额",
}
# 用户确认后无剩余冲突字段
KEEP_MINE = {}

# risk_ttl T系列逾期字段：截止点口径（T0=应还日当天、T3=应还日后3天截止），非all4的"逾期≥N天"窗口口径
# 来源：01号SQL L106-141，tN_fact_amt=fact_time<=should_time+N天累计实还，tN_OVERDUE_AMOUNT=总应还-该累计实还
_RTTL_FIX = {
    "T0_OVERDUE_AMOUNT": "应还日(T0)时点逾期金额(本+息)",
    "T3_OVERDUE_AMOUNT": "应还日后3天(T3)时点逾期金额(本+息)",
    "T7_OVERDUE_AMOUNT": "应还日后7天(T7)时点逾期金额(本+息)",
    "T14_OVERDUE_AMOUNT": "应还日后14天(T14)时点逾期金额(本+息)",
    "T30_OVERDUE_AMOUNT": "应还日后30天(T30)时点逾期金额(本+息)",
    "IS_T0_OVERDUE": "应还日(T0)时点是否逾期(实还应还差额>=-1视为未逾期)",
    "IS_T3_OVERDUE": "应还日后3天(T3)时点是否逾期(实还应还差额>=-1视为未逾期)",
    "IS_T7_OVERDUE": "应还日后7天(T7)时点是否逾期(实还应还差额>=-1视为未逾期)",
    "IS_T14_OVERDUE": "应还日后14天(T14)时点是否逾期(实还应还差额>=-1视为未逾期)",
    "IS_T30_OVERDUE": "应还日后30天(T30)时点是否逾期(实还应还差额>=-1视为未逾期)",
}

# property_v5_1_feature_bin 无期次后缀的窗口字段（均为第1期聚合，见logic sum(if(is_t0_window_1=1,...))）
_PROP_TOP = {
    "t0_should_cnt": "第1期 已过应还日 应还笔数",
    "t3_should_cnt": "第1期 逾期≥4天 应还笔数",
    "t0_should_amount": "第1期 已过应还日 应还金额",
    "t3_should_amount": "第1期 逾期≥4天 应还金额",
    "t0_overdue_amount": "第1期 已过应还日 逾期金额",
    "t3_overdue_amount": "第1期 逾期≥4天 逾期金额",
}

# risk_ttl/overdue_basetable 订单级 is_tN_window（无期次）：is_tN_window = date_diff('day',should_time,current)>N，即已过应还日后N天
_RTTL_WIN = {
    "is_t0_window": "是否已过应还日(T0窗口)(0/1)",
    "is_t3_window": "是否已过应还日后3天(T3窗口)(0/1)",
    "is_t7_window": "是否已过应还日后7天(T7窗口)(0/1)",
    "is_t14_window": "是否已过应还日后14天(T14窗口)(0/1)",
    "is_t30_window": "是否已过应还日后30天(T30窗口)(0/1)",
}

# clear_reloan 业务前缀（5天复借窗口放款）需在窗口口径修正后补回
_RELOAN_CTX = "5天复借窗口放款"

# preN 窗口解释句（用户确认：进口径定义列，与SQL逻辑并列）
_PRE_DEF = {
    "pre3": "应还日前3天起窗口：从应还日前3天起进入、跨过应还日、延续到逾期之后的累计窗口，窗口内既含未到期应还、也含已逾期未结清；",
    "pre2": "应还日前2天起窗口：从应还日前2天起进入、跨过应还日、延续到逾期之后的累计窗口，窗口内既含未到期应还、也含已逾期未结清；",
    "pre1": "应还日当天起窗口：应还日当天起进入（已到期）、延续到逾期之后的累计窗口，窗口内既含到期应还、也含已逾期未结清；",
}
_PRE_RE = re.compile(r"(?:^|_)(?:t)?pre([123])(?:_|$)")


comparison = []
for tbl, fields in my_data.items():
    for f in fields:
        name = f["name"]
        if name.startswith("（直通"):
            continue
        key = name.lower()
        cands = ref_map.get(key, [])
        if not cands:
            continue
        same = [c for c in cands if c[0] == SAME_REF.get(tbl)]
        ordered = same + [c for c in cands if c not in same]
        chosen = next((c for c in ordered if c[1]), None)
        if not chosen:
            continue
        ref_cn, ref_logic = chosen[1], chosen[2]
        my_desc = f.get("desc", "")
        # 决定：①vintage期次口径（用户确认，权威）②用户确认口径→强制覆盖 ③我的释义已更细（含数字/码值）→保留 ④否则参考释义更好→采用
        nd = fix_vintage(name)
        if nd:
            decision = "采用期次口径（用户确认）" if tbl in ("mx.wxs_vintage_all4", "mx.wxs_vintage_all5") else "采用窗口口径（SQL验证）"
            f["desc_orig"] = my_desc
            f["desc"] = nd
        elif (tbl, name) in FORCE_DESC:
            decision = "采用用户确认口径"
            f["desc_orig"] = my_desc
            f["desc"] = FORCE_DESC[(tbl, name)]
        elif tbl in ("mx.wxs_risk_ttl", "mx.wxs_overdue_basetable") and name in _RTTL_FIX:
            decision = "采用SQL口径（应还日时点截止）"
            f["desc_orig"] = my_desc
            f["desc"] = _RTTL_FIX[name]
        elif tbl in ("mx.wxs_risk_ttl", "mx.wxs_overdue_basetable") and name in _RTTL_WIN:
            decision = "采用SQL口径（应还日窗口）"
            f["desc_orig"] = my_desc
            f["desc"] = _RTTL_WIN[name]
        elif tbl == "mx.property_v5_1_feature_bin" and name in _PROP_TOP:
            decision = "采用窗口口径（SQL验证，第1期聚合）"
            f["desc_orig"] = my_desc
            f["desc"] = _PROP_TOP[name]
        elif (tbl, name) in KEEP_MINE:
            decision = "保留原释义（用户未改）"
            f["desc"] = my_desc
            f["desc_orig"] = my_desc
        elif has_detail(my_desc):
            decision = "保留原释义（含码值细节）"
            f["desc_orig"] = my_desc
        elif ref_cn and ref_cn != my_desc:
            decision = "采用参考释义"
            f["desc_orig"] = my_desc
            f["desc"] = ref_cn
        else:
            decision = "两者一致"
        # 口径：若我的口径只是"直取X"而参考有更完整逻辑，补到ref_logic供参考（不覆盖）
        comparison.append({
            "src_file": file_of.get(tbl, ""),
            "table": tbl,
            "field": name,
            "my_desc": my_desc,
            "ref_desc": ref_cn,
            "my_logic": f.get("logic", ""),
            "ref_logic": ref_logic,
            "decision": decision,
        })

# ---------- 4.5 窗口/口径更正（在对比之后权威应用，覆盖参考释义；全表小写tN窗口字段 + 大写T截止字段） ----------
for tbl, fields in my_data.items():
    for f in fields:
        nd = fix_vintage(f["name"])
        if nd:
            if "desc_orig" not in f:
                f["desc_orig"] = f.get("desc", "")
            f["desc"] = nd
        elif tbl in ("mx.wxs_risk_ttl", "mx.wxs_overdue_basetable") and f["name"] in _RTTL_FIX:
            if "desc_orig" not in f:
                f["desc_orig"] = f.get("desc", "")
            f["desc"] = _RTTL_FIX[f["name"]]
        elif tbl in ("mx.wxs_risk_ttl", "mx.wxs_overdue_basetable") and f["name"] in _RTTL_WIN:
            if "desc_orig" not in f:
                f["desc_orig"] = f.get("desc", "")
            f["desc"] = _RTTL_WIN[f["name"]]
        elif tbl == "mx.property_v5_1_feature_bin" and f["name"] in _PROP_TOP:
            if "desc_orig" not in f:
                f["desc_orig"] = f.get("desc", "")
            f["desc"] = _PROP_TOP[f["name"]]
# clear_reloan 业务前缀（5天复借窗口放款）在窗口口径修正后补回
for f in my_data.get("mx.yj_clear_reloan", []):
    nd = fix_vintage(f["name"])
    if nd and not f["desc"].startswith(_RELOAN_CTX):
        f["desc"] = _RELOAN_CTX + " " + nd

# preN 窗口字段：口径定义列前置解释句（幂等：已含则跳过）
for tbl, fields in my_data.items():
    for f in fields:
        m = _PRE_RE.search(f["name"])
        if m:
            prefix = _PRE_DEF["pre" + m.group(1)]
            logic = f.get("logic", "")
            if not logic.startswith(prefix):
                f["logic"] = prefix + logic

# ---------- 5. 保存更新后的JSON ----------
for fp in sorted(glob.glob(os.path.join(DATA_DIR, "*.json"))):
    if "reference" in fp or "comparison" in fp:
        continue
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
    for t in data:
        if t["table"] in my_data:
            t["fields"] = my_data[t["table"]]
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

with open(OUT_CMP, "w", encoding="utf-8") as f:
    json.dump(comparison, f, ensure_ascii=False, indent=1)

# ---------- 6. 重新生成 xlsx ----------
HEADERS = ["来源文件", "表名", "字段名", "业务含义", "数据来源表", "更新频率", "口径定义"]

wb = Workbook()
ws = wb.active
ws.title = "字段字典"

thin = Side(style="thin", color="BFBFBF")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
title_font = Font(name="微软雅黑", size=14, bold=True, color="1F4E78")
header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
header_fill = PatternFill("solid", fgColor="1F4E78")
body_font = Font(name="微软雅黑", size=10)
wrap_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
wrap_left = Alignment(horizontal="left", vertical="top", wrap_text=True)

NCOL = len(HEADERS)
last_col = get_column_letter(NCOL)
ws.merge_cells(f"A1:{last_col}1")
ws["A1"] = "墨西哥老客核心字段字典（段清单+口径说明）"
ws["A1"].font = title_font
ws["A1"].alignment = wrap_center
ws.row_dimensions[1].height = 28

HROW = 2
for c, h in enumerate(HEADERS, start=1):
    cell = ws.cell(row=HROW, column=c, value=h)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = wrap_center
    cell.border = border
ws.row_dimensions[HROW].height = 22

DEFAULT_FREQ = {"mx.yj_clear_reloan": "手动"}
r = HROW + 1
total = 0
for tbl, fields in my_data.items():
    freq = DEFAULT_FREQ.get(tbl, "每日")
    for f in fields:
        vals = [file_of.get(tbl, ""), tbl, f["name"], f.get("desc", ""), f.get("source_table", f.get("source", "")), f.get("update_freq", freq), f.get("logic", "")]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = body_font
            cell.border = border
            cell.alignment = wrap_center if c in (3, 6) else wrap_left
        r += 1
        total += 1

widths = [22, 30, 30, 42, 28, 10, 70]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.freeze_panes = f"A{HROW + 1}"
ws.auto_filter.ref = f"A{HROW}:{last_col}{r - 1}"

# ---- 对比说明 sheet ----
ws3 = wb.create_sheet("对比说明")
CMP_HEADERS = ["来源文件", "表名", "字段名", "我的业务含义(原)", "参考字典释义", "我的口径", "参考字典逻辑", "采用结论"]
for c, h in enumerate(CMP_HEADERS, start=1):
    cell = ws3.cell(row=1, column=c, value=h)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = wrap_center
    cell.border = border
for i, rec in enumerate(comparison, start=2):
    vals = [rec["src_file"], rec["table"], rec["field"], rec["my_desc"], rec["ref_desc"], rec["my_logic"], rec["ref_logic"], rec["decision"]]
    for c, v in enumerate(vals, start=1):
        cell = ws3.cell(row=i, column=c, value=v)
        cell.font = body_font
        cell.border = border
        cell.alignment = wrap_center if c in (3, 8) else wrap_left
cmp_widths = [22, 28, 26, 34, 34, 50, 50, 20]
for i, w in enumerate(cmp_widths, start=1):
    ws3.column_dimensions[get_column_letter(i)].width = w
ws3.freeze_panes = "A2"
ws3.auto_filter.ref = f"A1:H{len(comparison) + 1}"

# ---- 汇总 sheet ----
ws2 = wb.create_sheet("汇总")
ws2.merge_cells("A1:C1")
ws2["A1"] = "各表字段数汇总"
ws2["A1"].font = title_font
for c, h in enumerate(["表名", "来源文件", "字段数"], start=1):
    cell = ws2.cell(row=2, column=c, value=h)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = wrap_center
    cell.border = border
cnt = defaultdict(int)
for tbl, fields in my_data.items():
    cnt[tbl] = len(fields)
rr = 3
for tbl, n in sorted(cnt.items()):
    ws2.cell(row=rr, column=1, value=tbl).font = body_font
    ws2.cell(row=rr, column=2, value=file_of.get(tbl, "")).font = body_font
    ws2.cell(row=rr, column=3, value=n).font = body_font
    for c in range(1, 4):
        ws2.cell(row=rr, column=c).border = border
    rr += 1
ws2.cell(row=rr, column=1, value="合计").font = Font(name="微软雅黑", size=11, bold=True)
ws2.cell(row=rr, column=3, value=total).font = Font(name="微软雅黑", size=11, bold=True)
for c in range(1, 4):
    ws2.column_dimensions[get_column_letter(c)].width = 42 if c == 2 else 18

wb.save(OUT_XLSX)
print(f"OK -> {OUT_XLSX}  总字段数 {total}  对比记录 {len(comparison)}")
from collections import Counter
dc = Counter(x["decision"] for x in comparison)
print("采用结论分布:", dict(dc))
