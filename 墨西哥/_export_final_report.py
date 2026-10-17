# -*- coding: utf-8 -*-
"""0810后坏账风险归因·最终定位报告 Excel 导出"""
import sys, io, os, pickle
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"

# 颜色
RED = PatternFill("solid", fgColor="F4CCCC")
YEL = PatternFill("solid", fgColor="FFF2CC")
GRN = PatternFill("solid", fgColor="D9EAD3")
HDR = PatternFill("solid", fgColor="4472C4")
HDRF = Font(color="FFFFFF", bold=True, size=11)
TITLE = Font(bold=True, size=14, color="1F3864")
BOLD = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center")
THIN = Border(*[Side(style="thin", color="BFBFBF")]*4)

def load(name):
    p = os.path.join(OUT, name)
    with open(p, "rb") as f:
        return pickle.load(f)

d1 = load("_probe_daily_1t0.pkl")       # 全量逐日
deep2 = load("_probe_0812_deep2.pkl")    # 首贷质量分月
deep3 = load("_probe_0812_deep3.pkl")    # loan_cycle/金额档/复贷按首贷月
deep4 = load("_probe_0812_deep4.pkl")    # 7天 vs 非7天
deep = load("_probe_0812_deep.pkl")      # 通过率逐日/7月首贷拆解

wb = Workbook()

def sheet(df, name, title=None, numfmt=None):
    ws = wb.create_sheet(name)
    if title:
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(df.columns))
        c = ws.cell(1, 1, title); c.font = TITLE
        r0 = 2
    else:
        r0 = 1
    # header
    for j, col in enumerate(df.columns, 1):
        c = ws.cell(r0, j, str(col)); c.fill = HDR; c.font = HDRF; c.alignment = CENTER; c.border = THIN
    for i, (_, row) in enumerate(df.iterrows(), r0+1):
        for j, col in enumerate(df.columns, 1):
            v = row[col]
            if isinstance(v, float) and pd.isna(v):
                v = ""
            c = ws.cell(i, j, v); c.border = THIN
            if isinstance(v, (int, float)):
                c.number_format = numfmt or "0.00"
                c.alignment = CENTER
    # 列宽
    for j, col in enumerate(df.columns, 1):
        ml = max([len(str(col))]+[len(str(x)) for x in df[col].astype(str)])
        ws.column_dimensions[get_column_letter(j)].width = min(max(ml+2, 10), 40)
    ws.freeze_panes = ws.cell(r0+1, 2)
    return ws

# ---------- Sheet 0 结论 ----------
ws = wb.active; ws.title = "0_结论"
concl = [
    ("墨西哥0810后坏账风险归因·最终定位结论", TITLE),
    ("", None),
    ("一句话结论", BOLD),
    ("0810后坏账上升不是“一天普涨5个点”的黑天鹅，而是【7天产品（loan_cycle=7）驱动的客群逆向选择螺旋】：", None),
    ("公司6月起大力推7天短期限产品(首贷放款占比 22.8%→37.3%→52.9%)，7天产品天然坏账率50%+(比14天高10~12pp)；", None),
    ("7天产品周转快，坏客户借新还旧、优质客户流失，形成逆向选择；8月上旬7天产品集中放款(8月首贷9837笔=7月的2倍)，", None),
    ("到期集中8/11~8/14，这批坏客群集中复贷，导致7天复贷坏账从35%冲到50%，把整体1t0本金%脉冲式抬升(22→32→回落28)。", None),
    ("", None),
    ("证据链(全部有数)", BOLD),
    ("① 不是“7月首贷质量差”：7月首贷1t0=35.12%反而是历史最好；真正差的是6月40.14%和8月39.25%", None),
    ("② 7天产品是坏账发动机：首贷坏账6月53.87%/7月50.75%/8月53.14%，始终50%+，而14天仅38~41%", None),
    ("③ 7天产品占比逐月飙升：6月22.8%→7月37.3%→8月52.9%(放款量)，8月首贷7天9837笔=7月2倍", None),
    ("④ 8/11脉冲=7天产品复贷坏账跳升：7天复贷1t0从8/10的35.40%→8/13的50.05%，非7天仅19.57→30.00", None),
    ("⑤ 7天复贷客群49.6%是7-8月首贷的“近客群”，这批人复贷坏账44.93%", None),
    ("⑥ 通过率未放松(风险通过率86~88%稳定)，排除了“放水”假设——是产品结构+逆向选择，不是准入放松", None),
    ("", None),
    ("可落地的动作", BOLD),
    ("1. 7天产品单独看：坏账50%+需重定价(前砍/后收)或收紧额度，否则4T7TR可能为负", None),
    ("2. 7天产品复贷客群中“7-8月首贷的近客群”是最高危切片，建议单独做准入门槛", None),
    ("3. 监控7天产品在整体放款中的占比红线(当前已超50%)，占比过快会加速逆向选择", None),
]
r = 1
for txt, font in concl:
    c = ws.cell(r, 1, txt); c.font = font
    if txt.startswith("①") or txt.startswith("②") or txt.startswith("③") or txt.startswith("④") or txt.startswith("⑤") or txt.startswith("⑥"):
        c.alignment = WRAP
    r += 1
ws.column_dimensions["A"].width = 120

# ---------- Sheet 1 全量逐日曲线 ----------
d = d1[["d","app_cnt","issue_cnt","contract_amount","1t0本金%","1t3本金%","1t7本金%","4t0本金%"]].copy()
d["d"] = d["d"].astype(str)
sheet(d, "1_全量逐日曲线", "全量复贷老客 按进件日 逐日坏账曲线（8/10异常低点→8/11脉冲→8/14见顶→8/16回落）")

# ---------- Sheet 2 首贷质量分月 ----------
s2 = deep2["首贷质量分月"][["m","biz_cnt","issue_cnt","1t0本金%","1t3本金%","1t7本金%"]].copy()
sheet(s2, "2_首贷质量分月", "各月首贷(new)客群 首贷坏账（7月最好35.12，6月最差40.14，8月又差39.25）")

# ---------- Sheet 3 首贷loan_cycle结构 ----------
r = deep3["首贷loan_cycle分月"].copy()
pct = r.pivot_table(index="dim", columns="m", values="issue_cnt", aggfunc="sum")
pct = pct.div(pct.sum(axis=0), axis=1)*100
pct = pct.round(1).reset_index()
bad = r.pivot_table(index="dim", columns="m", values="1t0本金%", aggfunc="mean").round(2).reset_index()
bad.columns = ["dim"]+[f"{c}_坏账%" for c in bad.columns[1:]]
merged = pct.merge(bad, on="dim")
sheet(merged, "3_首贷loan_cycle结构", "首贷(new)各期限 放款量占比%(上行)与1t0本金%(下行)——7天产品占比6月22.8%→8月52.9%，坏账始终50%+")

# ---------- Sheet 4 7天vs非7天复贷 ----------
r = deep4["复贷7天vs非7天逐日"].copy()
p = r.pivot_table(index="dim", columns="d", values="1t0本金%", aggfunc="mean").round(2).reset_index()
q = r.pivot_table(index="dim", columns="d", values="app_cnt", aggfunc="sum").reset_index()
q.columns = ["dim"]+[f"{c}_量" for c in q.columns[1:]]
merged = p.merge(q, on="dim")
sheet(merged, "4_复贷7天vs非7天", "复贷 7天产品 vs 非7天 逐日坏账%与量——7天8/10的35.40→8/13的50.05，非7天仅19.57→30.00")

# ---------- Sheet 5 复贷按首贷月 ----------
s5 = deep3["复贷按首贷月"][["dim","app_cnt","issue_cnt","1t0本金%","1t3本金%","量占比%"]].copy()
sheet(s5, "5_复贷按首贷月", "8/8~8/16复贷客群 按首贷月分布——7月首贷复贷量最大(30.6%)，8月首贷复贷坏账最高(34.87%)")

# ---------- Sheet 6 复贷首贷月×日 ----------
r = deep3["复贷首贷月x日"].copy()
p = r.pivot_table(index="dim", columns="d", values="1t0本金%", aggfunc="mean").round(2).reset_index()
q = r.pivot_table(index="dim", columns="d", values="app_cnt", aggfunc="sum").reset_index()
q.columns = ["dim"]+[f"{c}_量" for c in q.columns[1:]]
merged = p.merge(q, on="dim")
sheet(merged, "6_复贷首贷月x日", "复贷 按首贷月(近/中/老) × 复贷日——7-8月首贷近客群是8/11~8/14脉冲主力(20.98→37.01)")

# ---------- Sheet 7 7天复贷按首贷月 ----------
s7 = deep4["复贷7天按首贷月"][["dim","app_cnt","1t0本金%","量占比%"]].copy()
sheet(s7, "7_7天复贷按首贷月", "7天产品复贷客群 按首贷月——49.6%是7-8月近客群，坏账44.93%")

# ---------- Sheet 8 通过率逐日 ----------
s8 = deep["复贷通过率逐日"][["d","app_cnt","前置%","后置(通过->放款)","风险通过率%"]].copy()
s8["d"] = s8["d"].astype(str)
sheet(s8, "8_通过率逐日", "复贷通过率逐日——风险通过率86~88%稳定，未放松，排除放水假设")

# ---------- Sheet 9 7月首贷拆解 ----------
s9a = deep["7月首贷app_group"][["dim","issue_cnt","1t0本金%"]].copy()
s9a.columns = ["app_group","放款量","1t0本金%"]
s9b = deep["7月首贷loan_cycle"][["dim","issue_cnt","1t0本金%"]].copy()
s9b.columns = ["loan_cycle","放款量","1t0本金%"]
sheet(pd.concat([pd.DataFrame({"app_group":["——按loan_cycle——"],"放款量":[""],"1t0本金%":[""]}), s9a], ignore_index=True),
      "9_7月首贷拆解", "7月首贷(new) 按app_group/loan_cycle拆解——7天产品50.75%、Mikredi 52.52%最高")

fname = os.path.join(OUT, "墨西哥0810后坏账归因_最终定位报告.xlsx")
wb.save(fname)
print("已保存:", fname)
