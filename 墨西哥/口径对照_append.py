# -*- coding: utf-8 -*-
"""向 墨西哥复贷产品分析_V5_3评级x产品_全SQL.xlsx 追加『口径对照』sheet。
说明报表月度『放款笔数』= 定档评级(V5_3 且主评级非空)口径, 与 funnel 全老客放款的差拆成
未匹配hub / 非V5_3匹配 / V5_3无评级, 并给 V5_3无评级缺口的日期与产品分布(7/6 单日集中)。
数据全部现场 SQL 现取, 可重复运行; 不依赖生成器, 不改动既有 13 个 sheet。"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from mexico_presto import PrestoQuery

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "墨西哥复贷产品分析_V5_3评级x产品_全SQL.xlsx")
W = ("f.is_reloan='old' and f.if_issue=1 and f.product_name is not null "
     "and f.release_time>=date'2026-06-09' and f.release_time<date'2026-09-01'")

pq = PrestoQuery(); pq.login()

def q(sql):
    r = pq.query(sql)
    if isinstance(r, str):
        raise RuntimeError(r[:400])
    return r

# 一、按月覆盖拆解
cov = q(f"""
select substr(cast(f.release_time as varchar),1,7) as ym,
 count(distinct f.biz_id) as all_biz,
 count(distinct case when y.biz_id is not null then f.biz_id end) as matched_biz,
 count(distinct case when y.v3_flag='V5_3' then f.biz_id end) as flag_biz,
 count(distinct case when y.v3_flag='V5_3' and y.android_oldcust_maincreditlevel_charge_v5_3 is not null then f.biz_id end) as graded_biz
from mx.wxs_application_funnel f
left join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
where {W} group by 1 order by 1""")
cov = cov.sort_values("ym")

# 二、V5_3无评级缺口 日期分布
gap_d = q(f"""
select substr(cast(f.release_time as varchar),1,10) as d,
 count(distinct f.biz_id) as n
from mx.wxs_application_funnel f
join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
where {W} and y.v3_flag='V5_3' and y.android_oldcust_maincreditlevel_charge_v5_3 is null
group by 1 order by n desc""")

# 三、V5_3无评级缺口 按产品
gap_p = q(f"""
select f.product_name,
 count(distinct f.biz_id) as n, count(distinct f.mid) as cust,
 sum(cast(f.contract_amount as double)) as ca
from mx.wxs_application_funnel f
join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
where {W} and y.v3_flag='V5_3' and y.android_oldcust_maincreditlevel_charge_v5_3 is null
group by 1 order by n desc, ca desc""")

# 四、全窗口未匹配hub 按产品
unm = q(f"""
select f.product_name, count(distinct f.biz_id) as n,
 sum(cast(f.contract_amount as double)) as ca
from mx.wxs_application_funnel f
left join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
where {W} and y.biz_id is null
group by 1 order by n desc""")

# —— 组装 ——
def num(x):
    return None if (x is None or pd.isna(x)) else float(x)

S1 = []
tot = {"all": 0, "match": 0, "flag": 0, "graded": 0, "unm": 0, "other": 0, "nogr": 0}
for _, r in cov.iterrows():
    all_, m, fl, gr = (int(r["all_biz"]), int(r["matched_biz"]), int(r["flag_biz"]), int(r["graded_biz"]))
    unm_, other, nogr = (all_ - m, m - fl, fl - gr)
    S1.append([str(r["ym"]), all_, m, fl, gr, gr / all_ if all_ else None, unm_, other, nogr])
    for k, v in zip(("all", "match", "flag", "graded", "unm", "other", "nogr"),
                    (all_, m, fl, gr, unm_, other, nogr)):
        tot[k] += v
S1.append(["合计", tot["all"], tot["match"], tot["flag"], tot["graded"],
           tot["graded"] / tot["all"], tot["unm"], tot["other"], tot["nogr"]])

# 连接器把 decimal 型 sum 结果返回成字符串; 统一转数值再算
for _df in (gap_p, unm):
    for _col in ("ca", "n", "cust"):
        if _col in _df.columns:
            _df[_col] = pd.to_numeric(_df[_col], errors="coerce")

gsum = int(gap_p["n"].sum()) if len(gap_p) else 0
S2 = [[str(r["d"]), int(r["n"]), int(r["n"]) / gsum] for _, r in gap_d.iterrows()]
S2.append(["合计", gsum, 1.0])

S3 = []
for _, r in gap_p.iterrows():
    ca = num(r["ca"]); ca = round(ca, 2) if ca is not None else None
    S3.append([r["product_name"], int(r["n"]), int(r["cust"]), ca,
               round(ca / int(r["n"]), 2) if r["n"] else None])
if len(gap_p):
    tc = round(num(gap_p["ca"].sum()), 2); tn = int(gap_p["n"].sum())
    S3.append(["合计", tn, int(gap_p["cust"].sum()), tc, round(tc / tn, 2) if tn else None])

S4 = []
for _, r in unm.iterrows():
    S4.append([r["product_name"], int(r["n"]), round(num(r["ca"]), 2) if r["ca"] is not None else None])
if len(unm):
    S4.append(["合计", int(unm["n"].sum()), round(num(unm["ca"].sum()), 2)])

# —— 写入 ——
HDR_FILL = PatternFill("solid", fgColor="1F4E78"); HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
SUB_FILL = PatternFill("solid", fgColor="DDEBF7")
TOT_FILL = PatternFill("solid", fgColor="FFF2CC"); TOT_FONT = Font(bold=True, color="C00000")
NOTE_F = Font(bold=True, size=10, color="C00000"); SMALL_F = Font(size=9, color="808080")

wb = openpyxl.load_workbook(XLSX)
name = "口径对照"
if name in wb.sheetnames:
    del wb[name]
ws = wb.create_sheet(name)

def note(txt):
    ws.append([txt]); ws.merge_cells(start_row=ws.max_row, start_column=1,
                                     end_row=ws.max_row, end_column=9)
    ws.cell(ws.max_row, 1).font = NOTE_F

def table(title, headers, rows, fmts, tot_row=None):
    ws.append([title]); ws.merge_cells(start_row=ws.max_row, start_column=1,
                                       end_row=ws.max_row, end_column=len(headers))
    ws.cell(ws.max_row, 1).font = NOTE_F
    ws.append(headers)
    hr = ws.max_row
    for c in ws[hr]: c.fill, c.font = HDR_FILL, HDR_FONT
    for i, r in enumerate(rows):
        is_tot = tot_row is not None and i == len(rows) - 1
        ws.append([None if v is None else (round(v, 6) if isinstance(v, float) else v) for v in r])
        if is_tot:
            for c in ws[ws.max_row]: c.fill, c.font = TOT_FILL, TOT_FONT
    for i, (col, f) in enumerate(zip(headers, fmts), 1):
        L = get_column_letter(i)
        wid = max([len(str(h)) for h in headers] + [len(str(v)) for r in rows for v in r if v is not None])
        ws.column_dimensions[L].width = min(max(wid, 8) + 2, 24)
        if f:
            for rowcell in ws.iter_rows(min_row=hr + 1, min_col=i, max_col=i):
                cell = rowcell[0]
                if isinstance(cell.value, (int, float)): cell.number_format = f

note("★ 『口径对照』——解释报表月度『放款笔数』的确切口径: =定档评级(funnel 老客已放款 且 v3_flag='V5_3' 且主评级非空)。")
note("★ 全老客放款(if_issue=1,产品非空) 减去 未匹配hub/非V5_3匹配/V5_3无评级 三部分 = 定档评级; 6/7/8 月 = 30,264 / 37,381 / 32,371, 合计 100,016(与报表各月小计一致)。")
note("★ V5_3无评级缺口集中 2026-07-06 单日 290 笔(占 95%), 疑当天主评级表灌入缺失; 属单日数据问题, 非系统性排除某产品。")
note("★ 8 月全老客 36,659 中 V5_3 仅 32,375(约 4,284 笔为其他模型标记) —— 报表只含 V5_3 评级人群, 勿与 8 月全老客放款直接对。")
table("一、按月覆盖拆解(单位:笔; 覆盖率=定档/全老客)",
      ["期", "全老客放款", "匹配hub", "V5_3标记", "定档评级(=报表放款)", "覆盖率", "未匹配hub", "非V5_3匹配", "V5_3无评级"],
      S1, [None, "#,##0", "#,##0", "#,##0", "#,##0", "0.00%", "#,##0", "#,##0", "#,##0"],
      tot_row=True)
table("二、V5_3无评级缺口 —— 放款日分布",
      ["放款日", "笔数", "占缺口%"],
      S2, [None, "#,##0", "0.00%"], tot_row=True)
table("三、V5_3无评级缺口 —— 产品构成",
      ["产品", "笔数", "客数", "放款金额", "件均"],
      S3, [None, "#,##0", "#,##0", "#,##0.00", "#,##0.00"], tot_row=True)
table("四、无hub匹配订单 —— 产品构成(取不到 v3_flag/评级)",
      ["产品", "笔数", "放款金额"],
      S4, [None, "#,##0", "#,##0.00"], tot_row=True)

ws.freeze_panes = "A2"

try:
    wb.save(XLSX)
    print("已追加 sheet『口径对照』到:", os.path.basename(XLSX))
    print("现有 sheets:", wb.sheetnames)
except PermissionError:
    print("ERROR: xlsx 被 Excel 占用(文件锁)。请关闭该文件后重跑本脚本。")
