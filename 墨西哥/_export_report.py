# -*- coding: utf-8 -*-
"""生成带格式的归因分析 Excel 报告"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"
XLSX = os.path.join(OUT, "墨西哥0810后坏账风险归因分析_报告.xlsx")

# ── 样式 ──
DARK_BLUE = "1F4E79"
LIGHT_BLUE = "D6E4F0"
HEADER_FONT = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="微软雅黑", size=14, bold=True, color="FFFFFF")
SECTION_FONT = Font(name="微软雅黑", size=12, bold=True, color="1F4E79")
NORMAL_FONT = Font(name="微软雅黑", size=10)
BOLD_FONT = Font(name="微软雅黑", size=10, bold=True)
RED_FONT = Font(name="微软雅黑", size=10, bold=True, color="C00000")
GREEN_FONT = Font(name="微软雅黑", size=10, bold=True, color="00B050")
RED_FILL = PatternFill("solid", fgColor="FFC7CE")
GREEN_FILL = PatternFill("solid", fgColor="C6EFCE")
YELLOW_FILL = PatternFill("solid", fgColor="FFEB9C")
TITLE_FILL = PatternFill("solid", fgColor=DARK_BLUE)
HEADER_FILL = PatternFill("solid", fgColor=DARK_BLUE)
SUBHEADER_FILL = PatternFill("solid", fgColor=LIGHT_BLUE)
THIN = Side(border_style="thin", color="B4B4B4")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
RIGHT = Alignment(horizontal="right", vertical="center")

def write_df(ws, df, start_row, start_col=1, header_fill=HEADER_FILL, header_font=HEADER_FONT,
             num_cols=None, pct_cols=None, highlight_col=None, highlight_bad=True):
    """写 DataFrame 到 ws, 带表头格式. highlight_col: 需要红绿色标的列名列表 (数值, 越大越差=red if bad)"""
    cols = list(df.columns)
    # 表头
    for j, c in enumerate(cols):
        cell = ws.cell(row=start_row, column=start_col+j, value=str(c))
        cell.fill = header_fill; cell.font = header_font; cell.alignment = CENTER; cell.border = BORDER
    # 数据
    for i, (_, row) in enumerate(df.iterrows()):
        r = start_row + 1 + i
        for j, c in enumerate(cols):
            v = row[c]
            cell = ws.cell(row=r, column=start_col+j, value=None if pd.isna(v) else v)
            cell.font = NORMAL_FONT; cell.border = BORDER
            if num_cols and c in num_cols:
                cell.alignment = RIGHT
                cell.number_format = "#,##0"
            elif pct_cols and c in pct_cols:
                cell.alignment = RIGHT
                cell.number_format = "0.00"
            else:
                cell.alignment = LEFT if j == 0 else CENTER
            # 高亮
            if highlight_col and c in highlight_col and isinstance(v, (int, float)) and not pd.isna(v):
                if highlight_bad:
                    if v >= 5: cell.fill = RED_FILL
                    elif v >= 2: cell.fill = YELLOW_FILL
                    elif v <= -2: cell.fill = GREEN_FILL
                else:
                    if v <= 5: cell.fill = RED_FILL
                    elif v <= 10: cell.fill = YELLOW_FILL
                    elif v >= 20: cell.fill = GREEN_FILL
    return start_row + len(df) + 1

def set_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

def add_title(ws, text, row=1, col=1, span=8):
    ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col+span-1)
    c = ws.cell(row=row, column=col, value=text)
    c.fill = TITLE_FILL; c.font = TITLE_FONT; c.alignment = CENTER
    ws.row_dimensions[row].height = 28

def add_section(ws, text, row, col=1, span=8):
    ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col+span-1)
    c = ws.cell(row=row, column=col, value=text)
    c.font = SECTION_FONT; c.alignment = LEFT
    ws.row_dimensions[row].height = 22

# ── 加载数据 ──
weekly = pd.read_pickle(os.path.join(OUT, "_weekly_issue_metrics.pkl"))
app_weekly = pd.read_pickle(os.path.join(OUT, "_weekly_app_metrics.pkl"))
daily = pd.read_pickle(os.path.join(OUT, "_daily_issue_metrics.pkl"))
all_cmp = pd.read_pickle(os.path.join(OUT, "_cmp_all.pkl"))
ss = pd.read_pickle(os.path.join(OUT, "_shift_share.pkl"))
lv = pd.read_pickle(os.path.join(OUT, "_level_cluster.pkl"))
pl_cmp = pd.read_pickle(os.path.join(OUT, "_prodline_cluster.pkl"))

MIN_LOAN = 50; MIN_WINDOW = 30
big = all_cmp[all_cmp["issue_cnt_c"] >= MIN_LOAN].copy()

wb = Workbook()
wb.remove(wb.active)

# ════════════════════════════════════════════════════
# Sheet 0: 封面 + 核心结论
# ════════════════════════════════════════════════════
ws = wb.create_sheet("0_核心结论")
add_title(ws, "墨西哥 0810 后坏账风险上升归因分析", row=1, span=6)
ws.cell(row=2, column=1, value="口径：复贷 is_reloan=old / tenant=yawey；基期 2026-08-03 周 vs 当期 2026-08-10 周；数据底表：mx.wxs_application_funnel ⋈ yj_test_table_250225").font = Font(name="微软雅黑", size=9, italic=True, color="595959")
ws.merge_cells("A2:F2")

# 三大结论卡
conclusions = [
    ("结论一 · 拐点", "风险拐点在 2026-08-12",
     "8/8–8/11 1t0本金% 稳定 23–25%，8/12 单日跳升至 30.33%（+6.5pp），4T7TR 从 32 跌至 27 以下，此后整周维持高位。"),
    ("结论二 · 性质", "全客群普惠性劣化（率效应主导）",
     "shift-share 分解：所有维度结构效应 Σmix≈0，率效应 Σrate≈+3.3pp，解释了几乎全部上升。产品线 A/B/C/E 全员恶化，非结构迁移。"),
    ("结论三 · 主力", "V5_3 高评级(8+) + 逾期痕迹客群",
     "v5_3主评级 8+ 段 1t0本金 33.43→37.94（+4.51pp，体量最大占60%），4T7TR 24→17；逾期痕迹客群（历史逾期/当前在逾/还款间隔>14天）1t0本金 +6~12pp。这批客群 4T7TR 已降至 5–17%，逼近盈亏线。"),
]
r = 4
for title, head, body in conclusions:
    add_section(ws, f"■ {title}：{head}", row=r, span=6)
    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    c = ws.cell(row=r, column=1, value=body)
    c.font = NORMAL_FONT; c.alignment = LEFT
    ws.row_dimensions[r].height = 45
    r += 2

# 大数速览
add_section(ws, "大数速览（放款周 issue 基准）", row=r, span=6); r += 1
quick = pd.DataFrame([
    ["放款笔数", "7,933", "8,186", "+253", "—"],
    ["1t0本金%", "25.36", "28.63", "+3.27pp", "恶化"],
    ["4t3本金%", "28.78", "31.49", "+2.71pp", "恶化"],
    ["4t7本金%", "28.36", "30.94", "+2.58pp", "恶化"],
    ["4T7TR%", "32.06", "27.05", "-5.01pp", "利润收窄"],
], columns=["指标", "8/03周", "8/10周", "变化", "判定"])
r = write_df(ws, quick, r, num_cols=["8/03周","8/10周"])
set_widths(ws, [22, 14, 14, 14, 12, 30])

# ════════════════════════════════════════════════════
# Sheet 1: 大数对比
# ════════════════════════════════════════════════════
ws = wb.create_sheet("1_大数对比_issue_app")
add_title(ws, "一、风险上升已确认（issue / app 双基准）", row=1, span=12)

add_section(ws, "1.1 放款周（issue_week）基准", row=3, span=12)
iss = weekly[["wk","issue_cnt","contract_amount","1t0本金%","4t3本金%","4t7本金%","4t3TR%","4T7TR%","件均","期限"]].copy()
r = write_df(ws, iss, 4, num_cols=["issue_cnt","contract_amount","件均"],
             pct_cols=["1t0本金%","4t3本金%","4t7本金%","4t3TR%","4T7TR%","期限"],
             highlight_col=["1t0本金%","4t3本金%","4t7本金%"], highlight_bad=True)

add_section(ws, "1.2 进件周（app_week）基准", row=r+1, span=12)
app = app_weekly[["wk","if_app","issue_cnt","前置%","后置","风险通过率%","24h用信率%","120h用信率%","1t0本金%","4t3本金%","4T7TR%"]].copy()
r = write_df(ws, app, r+2, num_cols=["if_app","issue_cnt"],
             pct_cols=["前置%","后置","风险通过率%","24h用信率%","120h用信率%","1t0本金%","4t3本金%","4T7TR%"],
             highlight_col=["1t0本金%","4t3本金%"], highlight_bad=True)
set_widths(ws, [12,10,14,10,8,12,12,12,10,10,10,10])

# ════════════════════════════════════════════════════
# Sheet 2: 逐日拐点
# ════════════════════════════════════════════════════
ws = wb.create_sheet("2_逐日拐点")
add_title(ws, "二、拐点定位：8 月 12 日", row=1, span=8)
add_section(ws, "放款日 8/01 – 8/25 逐日 1t0本金% / 4T7TR%", row=3, span=8)
dg = daily[(daily["d"] >= "2026-08-01") & (daily["d"] <= "2026-08-25")].copy()
dg["d"] = dg["d"].dt.strftime("%Y-%m-%d")
dg = dg[["d","issue_cnt","contract_amount","1t0本金%","4t3本金%","4t7本金%","4T7TR%","件均"]]
write_df(ws, dg, 4, num_cols=["issue_cnt","contract_amount","件均"],
         pct_cols=["1t0本金%","4t3本金%","4t7本金%","4T7TR%"],
         highlight_col=["1t0本金%"], highlight_bad=True)
set_widths(ws, [12,10,16,10,10,10,10,10])

# ════════════════════════════════════════════════════
# Sheet 3: shift-share
# ════════════════════════════════════════════════════
ws = wb.create_sheet("3_shift_share")
add_title(ws, "三、劣化性质：全客群率效应主导（1t0本金%，应还本金加权）", row=1, span=8)
add_section(ws, "结构效应 Σmix≈0，率效应 Σrate≈+3.3pp → 非结构迁移，每客群内部同步恶化", row=3, span=8)
ss_s = ss.sort_values("率效应Σrate", ascending=False).copy()
write_df(ws, ss_s, 4, pct_cols=["总率基期","总率当期","Δpp","结构Σmix","率效应Σrate","贡献pp"])
set_widths(ws, [16,10,10,8,10,10,16,10])

# ════════════════════════════════════════════════════
# Sheet 4: 评级三段聚类
# ════════════════════════════════════════════════════
ws = wb.create_sheet("4_评级三段聚类")
add_title(ws, "四(1)、V5_3 评级三段聚类 1-3 / 4-7 / 8+", row=1, span=10)
add_section(ws, "8+ 段体量最大（占~60%）且恶化最猛（1t0 +4.51pp，4T7TR 24→17）", row=3, span=10)
lv_show = lv[["dim_key","dim","issue_cnt_b","issue_cnt_c","1t0本金%_b","1t0本金%_c","1t0本金%_Δ",
              "4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4T7TR%_b","4T7TR%_c","4T7TR%_Δ"]].copy()
write_df(ws, lv_show, 4, num_cols=["issue_cnt_b","issue_cnt_c"],
         pct_cols=["1t0本金%_b","1t0本金%_c","1t0本金%_Δ","4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4T7TR%_b","4T7TR%_c","4T7TR%_Δ"],
         highlight_col=["1t0本金%_Δ","4t3本金%_Δ","4T7TR%_Δ"], highlight_bad=True)
set_widths(ws, [12,6,10,10,10,10,10,10,10,10,10,10,10])

# ════════════════════════════════════════════════════
# Sheet 5: 产品线聚类
# ════════════════════════════════════════════════════
ws = wb.create_sheet("5_产品线聚类")
add_title(ws, "四(2)、产品线全员恶化（首字母聚类）", row=1, span=10)
add_section(ws, "A/B/C/E 四条线 1t0本金% 全部上升，B、C 最猛（+3.5~4.4pp）", row=3, span=10)
pl = pl_cmp[["dim","issue_cnt_b","issue_cnt_c","1t0本金%_b","1t0本金%_c","1t0本金%_Δ",
             "4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4T7TR%_b","4T7TR%_c","4T7TR%_Δ"]].copy()
write_df(ws, pl, 4, num_cols=["issue_cnt_b","issue_cnt_c"],
         pct_cols=["1t0本金%_b","1t0本金%_c","1t0本金%_Δ","4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4T7TR%_b","4T7TR%_c","4T7TR%_Δ"],
         highlight_col=["1t0本金%_Δ","4t3本金%_Δ"], highlight_bad=True)
set_widths(ws, [8,10,10,10,10,10,10,10,10,10,10,10])

# ════════════════════════════════════════════════════
# Sheet 6: 恶化主力切片
# ════════════════════════════════════════════════════
ws = wb.create_sheet("6_恶化主力切片")
add_title(ws, "五、恶化主力切片（大样本 放款≥50笔，按 4t3本金%_Δ 排序）", row=1, span=14)

add_section(ws, "5.1 4t3本金% 恶化 TOP25", row=3, span=14)
big_sorted = big.sort_values("4t3本金%_Δ", ascending=False)
top = big_sorted[["dim_key","dim","issue_cnt_b","issue_cnt_c","1t0本金%_b","1t0本金%_c","1t0本金%_Δ",
                  "4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4t7本金%_Δ","4T7TR%_b","4T7TR%_c","4T7TR%_Δ"]].head(25).copy()
r = write_df(ws, top, 4, num_cols=["issue_cnt_b","issue_cnt_c"],
             pct_cols=["1t0本金%_b","1t0本金%_c","1t0本金%_Δ","4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4t7本金%_Δ","4T7TR%_b","4T7TR%_c","4T7TR%_Δ"],
             highlight_col=["1t0本金%_Δ","4t3本金%_Δ","4T7TR%_Δ"], highlight_bad=True)

add_section(ws, "5.2 4t3本金% 改善 TOP10（反向验证）", row=r+1, span=14)
bot = big_sorted[["dim_key","dim","issue_cnt_b","issue_cnt_c","1t0本金%_b","1t0本金%_c","1t0本金%_Δ",
                  "4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4t7本金%_Δ","4T7TR%_b","4T7TR%_c","4T7TR%_Δ"]].tail(10).copy()
write_df(ws, bot, r+2, num_cols=["issue_cnt_b","issue_cnt_c"],
         pct_cols=["1t0本金%_b","1t0本金%_c","1t0本金%_Δ","4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4t7本金%_Δ","4T7TR%_b","4T7TR%_c","4T7TR%_Δ"],
         highlight_col=["1t0本金%_Δ","4t3本金%_Δ","4T7TR%_Δ"], highlight_bad=True)
set_widths(ws, [16,22,10,10,10,10,10,10,10,10,10,10,10,10])

# ════════════════════════════════════════════════════
# Sheet 7: TR利润空间
# ════════════════════════════════════════════════════
ws = wb.create_sheet("7_TR利润空间")
add_title(ws, "六、TR 利润空间：4T7TR 最低切片（已无利润）", row=1, span=10)
big_tr = big[big["4t7出账_c"] >= MIN_WINDOW].sort_values("4T7TR%_c")
tr = big_tr[["dim_key","dim","issue_cnt_c","4t7出账_c","前砍%_c","后收%_c","4t7本金%_c","4t7息费%_c","4T7TR%_c","4T7TR%_Δ"]].head(20).copy()
write_df(ws, tr, 3, num_cols=["issue_cnt_c","4t7出账_c"],
         pct_cols=["前砍%_c","后收%_c","4t7本金%_c","4t7息费%_c","4T7TR%_c","4T7TR%_Δ"],
         highlight_col=["4T7TR%_c"], highlight_bad=False)
set_widths(ws, [16,22,10,10,10,10,10,10,10,10])

# ════════════════════════════════════════════════════
# Sheet 8: 逾期最高榜单
# ════════════════════════════════════════════════════
ws = wb.create_sheet("8_逾期最高榜单")
add_title(ws, "七、逾期最高榜单：4t7本金% 当期最高（大样本，4t7出账≥30）", row=1, span=8)
big_ovd = big[big["4t7出账_c"] >= MIN_WINDOW].sort_values("4t7本金%_c", ascending=False)
ovd = big_ovd[["dim_key","dim","issue_cnt_c","4t7出账_c","1t0本金%_c","4t3本金%_c","4t7本金%_c","4T7TR%_c"]].head(20).copy()
write_df(ws, ovd, 3, num_cols=["issue_cnt_c","4t7出账_c"],
         pct_cols=["1t0本金%_c","4t3本金%_c","4t7本金%_c","4T7TR%_c"],
         highlight_col=["4t7本金%_c"], highlight_bad=True)
set_widths(ws, [16,22,10,10,10,10,10,10])

# ════════════════════════════════════════════════════
# Sheet 9: 结论建议
# ════════════════════════════════════════════════════
ws = wb.create_sheet("9_结论建议")
add_title(ws, "八、核心结论与行动建议", row=1, span=5)

add_section(ws, "■ 归因（一句话）", row=3, span=5)
ws.merge_cells("A4:E4")
c = ws.cell(row=4, column=1, value="0810 后（拐点 8/12）的坏账上升是一次全客群普惠性劣化（shift-share 率效应≈全部+3.3pp，结构效应≈0），恶化主力集中在 V5_3 高评级（8+，尤其 10–12 级）与带逾期痕迹客群（历史逾期/当前在逾/还款间隔>14天），且这些客群 4T7TR 已降至 5–17%、逼近盈亏线。")
c.font = BOLD_FONT; c.alignment = LEFT; ws.row_dimensions[4].height = 50

add_section(ws, "■ 行动建议（按优先级）", row=6, span=5)
advice = pd.DataFrame([
    ["P0", "收紧 V5_3 评级 8+ 准入/额度，重点 10–12 级", "v5_3主/中评级 8+，尤其 10/11/12 级", "8+段放款 4720→5005（体量最大），1t0本金 +4.51pp，4T7TR 24→17；10–12级 4T7TR 仅 5–7%"],
    ["P0", "对带逾期痕迹客群降额/拒贷", "当前逾期 ovd_1/ovd_2、历史逾期 mxovd_8_30/mxovd_gt90、还款间隔 gap_gt14", "1t0本金 +6~12pp，远超大盘；4T7TR 8–20%，利润极薄"],
    ["P1", "单独核查 fd_high_pass=1 放行客群", "fd_high_pass=1", "4t3本金 +18pp、4T7TR 45→10，信号最强"],
    ["P1", "关注 B、C 产品线策略", "产品 B_07_02_00_75 / C_07_03_00_75", "1t0本金 +3.5~4.4pp，产品线中恶化最猛"],
    ["P2", "排查 8/12 当日策略/模型/客群切换事件", "—", "拐点单日跳升，需结合当日运营日志定位"],
], columns=["优先级", "动作", "目标切片", "数据依据"])
write_df(ws, advice, 7)
set_widths(ws, [8, 32, 30, 50])

# 冻结首行
for s in wb.sheetnames:
    wb[s].freeze_panes = "A2"

wb.save(XLSX)
print("已导出:", XLSX)
print("Sheet 列表:", wb.sheetnames)
