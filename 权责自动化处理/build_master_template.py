"""
印尼权责预估 — Master 模板生成器
================================
生成单一 Excel 文件（Sheet1 + 使用说明）：
  - 参数配置区（底部蓝色输入格）每月只需更新件均/S 和 T30坏账率/V
  - 数据行 K/L/M/S/V/Q 由查表公式自动联动
  - SUMIFS 汇总自动刷新
"""

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
import os, shutil
from openpyxl.utils import get_column_letter

# ══ 颜色常量 ══
C_BLUE   = "0000FF"
C_BLACK  = "000000"
C_WHITE  = "FFFFFF"
C_YELLOW = "FFF2CC"

TEMPLATE_PATH = (
    r"E:\岳松个人文件\嘉银工作内容的整理\code\权责自动化处理"
    r"\权责近两个月的数据预估_模板.xlsx"
)
OUT_DIR  = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析"
OUT_NAME = "印尼权责预估_Master模板.xlsx"

# 参数配置表在 Sheet1 中起始行
PARAM_RATE_START = 300

# 列索引
COL = {l: i+1 for i, l in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}


# ═══════════════════════════════════════════════════════════════
# RATE_CONFIG
# ═══════════════════════════════════════════════════════════════
RATE_CONFIG = {
    ("4月","首贷","常规",30):   dict(K=0.26, L=0.81, M=0.523, S=60.48, V=0.18773),
    ("4月","首贷","常规",60):   dict(K=0.26, L=0.81, M=0.523, S=271.06,V=0.16350),
    ("4月","首贷","常规",90):   dict(K=0.26, L=0.81, M=0.523, S=247.23,V=0.14070),
    ("4月","首贷","优享贷",90):  dict(K=0.26, L=0.81, M=0.523, S=76.3, V=0.14070),
    ("4月","首贷","常规",120):  dict(K=0.26, L=0.81, M=0.523, S=434.65,V=0.13870),
    ("4月","首贷","无忧贷",120): dict(K=0.26, L=0.81, M=0.523, S=67.71, V=0.13870),
    ("4月","首贷","优享贷",120): dict(K=0.26, L=0.81, M=0.523, S=95.9, V=0.13870),
    ("4月","首贷","常规",150):  dict(K=0.26, L=0.81, M=0.523, S=472.55,V=0.13400),
    ("4月","首贷","放心贷",150): dict(K=0.26, L=0.81, M=0.523, S=27.3, V=0.13400),
    ("4月","首贷","本金",150):   dict(K=0.26, L=0.81, M=0.523, S=30.82, V=0.13400),
    ("4月","首贷","放心贷",180): dict(K=0.26, L=0.81, M=0.523, S=27.1, V=0.12000),
    ("4月","首贷","优享贷",180): dict(K=0.26, L=0.81, M=0.523, S=99.9, V=0.12000),
    ("4月","首贷","本金",180):   dict(K=0.26, L=0.81, M=0.523, S=27.1, V=0.12000),
    ("5月","首贷","常规",30):   dict(K=0.26, L=0.81, M=0.530, S=60.08, V=0.19377),
    ("5月","首贷","常规",60):   dict(K=0.26, L=0.81, M=0.530, S=270.00,V=0.17000),
    ("5月","首贷","常规",90):   dict(K=0.26, L=0.81, M=0.530, S=248.00,V=0.15000),
    ("5月","首贷","优享贷",90):  dict(K=0.26, L=0.81, M=0.530, S=76.3, V=0.15000),
    ("5月","首贷","常规",120):  dict(K=0.26, L=0.81, M=0.530, S=435.00,V=0.14500),
    ("5月","首贷","无忧贷",120): dict(K=0.26, L=0.81, M=0.530, S=68.00, V=0.14500),
    ("5月","首贷","优享贷",120): dict(K=0.26, L=0.81, M=0.530, S=95.9, V=0.14500),
    ("5月","首贷","常规",150):  dict(K=0.26, L=0.81, M=0.530, S=473.00,V=0.14000),
    ("5月","首贷","放心贷",150): dict(K=0.26, L=0.81, M=0.530, S=27.3, V=0.14000),
    ("5月","首贷","本金",150):   dict(K=0.26, L=0.81, M=0.530, S=31.0, V=0.14000),
    ("5月","首贷","放心贷",180): dict(K=0.26, L=0.81, M=0.530, S=27.1, V=0.12500),
    ("5月","首贷","优享贷",180): dict(K=0.26, L=0.81, M=0.530, S=100.0,V=0.12500),
    ("5月","首贷","本金",180):   dict(K=0.26, L=0.81, M=0.530, S=27.1, V=0.12500),
    ("4月","复贷-循环贷","常规",30):   dict(K=0.6143, L=1.0, M=0.9822, S=91.93, V=0.19284),
    ("4月","复贷-循环贷","常规",60):   dict(K=0.6143, L=1.0, M=0.9822, S=114.93,V=0.12000),
    ("4月","复贷-循环贷","常规",90):   dict(K=0.6143, L=1.0, M=0.9822, S=384.31,V=0.09200),
    ("4月","复贷-循环贷","无忧贷",90):  dict(K=0.6143, L=1.0, M=0.9822, S=289.59,V=0.09200),
    ("4月","复贷-循环贷","优享贷",90):  dict(K=0.6143, L=1.0, M=0.9822, S=213.85,V=0.09200),
    ("4月","复贷-循环贷","常规",120):  dict(K=0.6143, L=1.0, M=0.9822, S=583.81,V=0.08200),
    ("4月","复贷-循环贷","无忧贷",120): dict(K=0.6143, L=1.0, M=0.9822, S=284.06,V=0.08200),
    ("4月","复贷-循环贷","优享贷",120): dict(K=0.6143, L=1.0, M=0.9822, S=239.44,V=0.08200),
    ("4月","复贷-循环贷","放心贷",150): dict(K=0.6143, L=1.0, M=0.9822, S=121.85,V=0.07500),
    ("4月","复贷-循环贷","优享贷",150): dict(K=0.6143, L=1.0, M=0.9822, S=409.47,V=0.07500),
    ("4月","复贷-循环贷","本金",150):   dict(K=0.6143, L=1.0, M=0.9822, S=93.89, V=0.07500),
    ("4月","复贷-循环贷","放心贷",180): dict(K=0.6143, L=1.0, M=0.9822, S=94.45, V=0.06800),
    ("4月","复贷-循环贷","优享贷",180): dict(K=0.6143, L=1.0, M=0.9822, S=219.54,V=0.06800),
    ("4月","复贷-循环贷","本金",180):   dict(K=0.6143, L=1.0, M=0.9822, S=135.04,V=0.06800),
    ("5月","复贷-循环贷","常规",30):   dict(K=0.6086, L=1.0, M=0.9822, S=95.44, V=0.19284),
    ("5月","复贷-循环贷","常规",60):   dict(K=0.6086, L=1.0, M=0.9822, S=120.67,V=0.12000),
    ("5月","复贷-循环贷","常规",90):   dict(K=0.6086, L=1.0, M=0.9822, S=403.53,V=0.09200),
    ("5月","复贷-循环贷","无忧贷",90):  dict(K=0.6086, L=1.0, M=0.9822, S=289.59,V=0.09200),
    ("5月","复贷-循环贷","优享贷",90):  dict(K=0.6086, L=1.0, M=0.9822, S=213.85,V=0.09200),
    ("5月","复贷-循环贷","常规",120):  dict(K=0.6086, L=1.0, M=0.9822, S=613.00,V=0.08200),
    ("5月","复贷-循环贷","无忧贷",120): dict(K=0.6086, L=1.0, M=0.9822, S=275.07,V=0.08200),
    ("5月","复贷-循环贷","优享贷",120): dict(K=0.6086, L=1.0, M=0.9822, S=248.04,V=0.08200),
    ("5月","复贷-循环贷","放心贷",150): dict(K=0.6086, L=1.0, M=0.9822, S=119.46,V=0.07500),
    ("5月","复贷-循环贷","优享贷",150): dict(K=0.6086, L=1.0, M=0.9822, S=417.66,V=0.07500),
    ("5月","复贷-循环贷","本金",150):   dict(K=0.6086, L=1.0, M=0.9822, S=93.45, V=0.07500),
    ("5月","复贷-循环贷","放心贷",180): dict(K=0.6086, L=1.0, M=0.9822, S=94.19, V=0.06800),
    ("5月","复贷-循环贷","优享贷",180): dict(K=0.6086, L=1.0, M=0.9822, S=219.54,V=0.06800),
    ("5月","复贷-循环贷","本金",180):   dict(K=0.6086, L=1.0, M=0.9822, S=132.73,V=0.06800),
    ("4月","复贷-非循环贷","常规",30):   dict(K=0.3827, L=0.81, M=0.9999, S=56.28, V=0.10679),
    ("4月","复贷-非循环贷","常规",60):   dict(K=0.3827, L=0.81, M=0.9999, S=56.28, V=0.09000),
    ("4月","复贷-非循环贷","常规",90):   dict(K=0.3827, L=0.81, M=0.9999, S=56.28, V=0.07500),
    ("4月","复贷-非循环贷","无忧贷",90):  dict(K=0.3827, L=0.81, M=0.9999, S=289.59,V=0.07500),
    ("4月","复贷-非循环贷","常规",120):  dict(K=0.3827, L=0.81, M=0.9999, S=56.28, V=0.06500),
    ("4月","复贷-非循环贷","无忧贷",120): dict(K=0.3827, L=0.81, M=0.9999, S=284.06,V=0.06500),
    ("4月","复贷-非循环贷","本金",150):   dict(K=0.3827, L=0.81, M=0.9999, S=30.82, V=0.05500),
    ("4月","复贷-非循环贷","无忧贷",180): dict(K=0.3827, L=0.81, M=0.9999, S=289.59,V=0.05000),
    ("4月","复贷-非循环贷","本金",180):   dict(K=0.3827, L=0.81, M=0.9999, S=30.82, V=0.05000),
    ("5月","复贷-非循环贷","常规",30):   dict(K=0.3827, L=0.81, M=0.9999, S=56.31, V=0.10679),
    ("5月","复贷-非循环贷","常规",60):   dict(K=0.3827, L=0.81, M=0.9999, S=56.31, V=0.09000),
    ("5月","复贷-非循环贷","常规",90):   dict(K=0.3827, L=0.81, M=0.9999, S=56.31, V=0.07500),
    ("5月","复贷-非循环贷","无忧贷",90):  dict(K=0.3827, L=0.81, M=0.9999, S=289.59,V=0.07500),
    ("5月","复贷-非循环贷","常规",120):  dict(K=0.3827, L=0.81, M=0.9999, S=56.31, V=0.06500),
    ("5月","复贷-非循环贷","无忧贷",120): dict(K=0.3827, L=0.81, M=0.9999, S=284.06,V=0.06500),
    ("5月","复贷-非循环贷","本金",150):   dict(K=0.3827, L=0.81, M=0.9999, S=31.0,  V=0.05500),
    ("5月","复贷-非循环贷","无忧贷",180): dict(K=0.3827, L=0.81, M=0.9999, S=289.59,V=0.05000),
    ("5月","复贷-非循环贷","本金",180):   dict(K=0.3827, L=0.81, M=0.9999, S=31.0,  V=0.05000),
}

Q_CONFIG = {
    ("4月","首贷","常规",30):   0.07117, ("4月","首贷","常规",60):   0.05316,
    ("4月","首贷","常规",90):   0.06328, ("4月","首贷","常规",120):  0.00625,
    ("4月","首贷","常规",150):  0.04588, ("4月","首贷","常规",180):  0.10655,
    ("4月","首贷","优享贷",90):  0.05689, ("4月","首贷","优享贷",120):0.02799,
    ("4月","首贷","优享贷",150):0.02500, ("4月","首贷","优享贷",180):0.09030,
    ("4月","首贷","放心贷",150):0.08940, ("4月","首贷","放心贷",180):0.00903,
    ("4月","首贷","本金",150):  0.20802, ("4月","首贷","本金",180):  0.01625,
    ("4月","首贷","无忧贷",120):0.26236,
    ("4月","复贷-循环贷","常规",30):  0.00326, ("4月","复贷-循环贷","常规",60):  0.03293,
    ("4月","复贷-循环贷","常规",90):  0.05254, ("4月","复贷-循环贷","常规",120): 0.05016,
    ("4月","复贷-循环贷","常规",150): 0.03527, ("4月","复贷-循环贷","常规",180): 0.10969,
    ("4月","复贷-循环贷","无忧贷",90): 0.04329, ("4月","复贷-循环贷","无忧贷",120):0.13146,
    ("4月","复贷-循环贷","优享贷",90): 0.05740, ("4月","复贷-循环贷","优享贷",120):0.13557,
    ("4月","复贷-循环贷","优享贷",150):0.03527, ("4月","复贷-循环贷","优享贷",180):0.05526,
    ("4月","复贷-循环贷","放心贷",150):0.05401, ("4月","复贷-循环贷","放心贷",180):0.17623,
    ("4月","复贷-循环贷","本金",150):  0.11818, ("4月","复贷-循环贷","本金",180):  0.05443,
    ("4月","复贷-非循环贷","常规",30):  0.00706, ("4月","复贷-非循环贷","常规",60):  0.30000,
    ("4月","复贷-非循环贷","常规",90):  0.20000, ("4月","复贷-非循环贷","常规",120): 0.20000,
    ("4月","复贷-非循环贷","常规",150): 0.20000, ("4月","复贷-非循环贷","常规",180): 0.10000,
    ("4月","复贷-非循环贷","无忧贷",90): 0.30000, ("4月","复贷-非循环贷","无忧贷",120):0.30000,
    ("4月","复贷-非循环贷","本金",150):  0.20000, ("4月","复贷-非循环贷","本金",180):  0.10000,
    ("5月","复贷-循环贷","常规",30):  0.00447, ("5月","复贷-循环贷","常规",60):  0.04313,
    ("5月","复贷-循环贷","常规",90):  0.06643, ("5月","复贷-循环贷","常规",120): 0.03029,
    ("5月","复贷-循环贷","常规",150): 0.06490, ("5月","复贷-循环贷","常规",180): 0.10983,
    ("5月","复贷-循环贷","无忧贷",90): 0.02687, ("5月","复贷-循环贷","无忧贷",120):0.08163,
    ("5月","复贷-循环贷","优享贷",90): 0.06349, ("5月","复贷-循环贷","优享贷",120):0.15033,
    ("5月","复贷-循环贷","优享贷",150):0.06490, ("5月","复贷-循环贷","优享贷",180):0.07637,
    ("5月","复贷-循环贷","放心贷",150):0.05889, ("5月","复贷-循环贷","放心贷",180):0.22951,
    ("5月","复贷-循环贷","本金",150):  0.07023, ("5月","复贷-循环贷","本金",180):  0.03346,
    ("5月","复贷-非循环贷","常规",30):  0.00774, ("5月","复贷-非循环贷","常规",60):  0.30000,
    ("5月","复贷-非循环贷","常规",90):  0.20000, ("5月","复贷-非循环贷","常规",120): 0.20000,
    ("5月","复贷-非循环贷","常规",150): 0.20000, ("5月","复贷-非循环贷","常规",180): 0.10000,
    ("5月","复贷-非循环贷","无忧贷",90): 0.30000, ("5月","复贷-非循环贷","无忧贷",120):0.30000,
    ("5月","复贷-非循环贷","本金",150):  0.20000, ("5月","复贷-非循环贷","本金",180):  0.10000,
}

# 数据块行定义：(月份, 业务) → (J合并格行, 数据起始行, 数据结束行, 合计行)
BLOCKS = {
    ("4月","首贷"):          (10, 10, 22, 23),
    ("4月","复贷-循环贷"):   (24, 24, 37, 38),
    ("4月","复贷-非循环贷"): (39, 39, 47, 51),
    ("4月","本金加贷"):      (52, 52, 57, None),
    ("5月","首贷"):          (75, 75, 87, 88),
    ("5月","复贷-循环贷"):   (89, 89, 102, 103),
    ("5月","复贷-非循环贷"): (104,104, 112, 117),
    ("5月","本金加贷"):      (117,117, 122, None),
}

# 参数表：月份=A, 业务=B, 产品=C, 期限=D, K=E(5), L=F(6), M=G(7), O=H(8), S=I(9), V=J(10), Q=K(11)
PARAM_COL = dict(month=1, biz=2, prod=3, term=4, K=5, L=6, M=7, O=8, S=9, V=10, Q=11)


# ═══════════════════════════════════════════════════════════════
# 样式辅助
# ═══════════════════════════════════════════════════════════════
def fill(c):   return PatternFill("solid", fgColor=c)
def fnt(c, bold=False, sz=10):
    return Font(color=c, bold=bold, size=sz, name="Arial")
def bdr():
    s = Side(style="thin")
    return Border(left=s, right=s, top=s, bottom=s)
def aln(h="center", v="center", wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

from openpyxl.cell.cell import MergedCell

def sc(ws, row, col, val=None, formula=None,
       fc=C_BLACK, bg=None, bold=False,
       ah="center", av="center", wrap=False, fmt=None):
    """set cell helper — 跳过合并单元格"""
    try:
        c = ws.cell(row, col)
    except AttributeError:
        return None
    if isinstance(c, MergedCell):
        return None
    c.value = formula if formula is not None else val
    c.font  = fnt(fc, bold)
    if bg:  c.fill  = fill(bg)
    c.alignment = aln(ah, av, wrap)
    c.border = bdr()
    if fmt: c.number_format = fmt
    return c

def addr(row, col_n):
    return f"{get_column_letter(col_n)}{row}"


# ═══════════════════════════════════════════════════════════════
# 使用说明 Sheet
# ═══════════════════════════════════════════════════════════════
def build_instructions(wb):
    ws = wb.create_sheet("使用说明")
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 58
    ws.column_dimensions["D"].width = 18

    def hdr(row, text):
        ws.merge_cells(start_row=row, start_column=1,
                       end_row=row, end_column=4)
        c = ws.cell(row, 1)
        c.value = text
        c.font  = fnt(C_WHITE, bold=True, sz=12)
        c.fill  = fill("1F497D")
        c.alignment = aln("left")

    def row3(row, label, content, note=""):
        sc(ws, row, 2, val=label, bold=True, bg="EBF3FB", ah="left")
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=4)
        sc(ws, row, 3, val=content, ah="left", wrap=True)
        ws.row_dimensions[row].height = 28 if len(str(content)) > 45 else 18

    # 标题
    ws.merge_cells("B1:D1")
    t = ws.cell(1, 2)
    t.value = "📊 印尼权责预估 Master 模板 — 使用说明"
    t.font  = fnt(C_WHITE, bold=True, sz=14)
    t.fill  = fill("1F497D")
    t.alignment = aln("left")
    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 6

    hdr(3,  "一、文件说明")
    row3(4,  "文件性质", "单一可复用 Excel 模板，每月只需更新参数配置区")
    row3(5,  "Sheet 结构", "Sheet1 = 预估模板（含 SUMIFS 自动汇总）\n使用说明 = 本页")
    row3(6,  "核心原理", "风险死数写入参数配置区 → 查表公式自动填充数据行 → SUMIFS 自动联动汇总")
    ws.row_dimensions[7].height = 6

    hdr(8,  "二、每月操作步骤（风险返回文档后，5 分钟搞定）")
    row3(9,  "Step 1", "打开 Sheet1 → 按 Ctrl+End 跳到最底部（行 300 以下）")
    row3(10, "Step 2", "找到【参数配置区】紫色标题区域")
    row3(11, "Step 3", "更新全局参数：汇率(J7)、4月/5月进件量（蓝色粗体格）")
    row3(12, "Step 4", "更新风险参数表：S列=件均(万盾)、V列=T30坏账率（蓝色输入格）")
    row3(13, "Step 5", "Q分布系数：仅5月有变化时更新（5月列，无则自动沿用4月）")
    row3(14, "Step 6", "回到 Sheet1 数据区，滚动查看，全表已自动刷新 ✅")
    ws.row_dimensions[15].height = 6

    hdr(16, "三、全局参数（蓝色粗体格）")
    def prow(r, cell_ref, name, desc):
        sc(ws, r, 2, val=name,   bold=True, bg="EBF3FB", ah="left")
        sc(ws, r, 3, formula=f"={cell_ref}", fc=C_BLUE, bg=C_YELLOW, bold=True, ah="left")
        sc(ws, r, 4, val=desc,  ah="left")
        ws.row_dimensions[r].height = 16
    prow(17, "J7",  "汇率 (IDR/USD)",       "当前 17090")
    prow(18, "J10", "4月首贷进件量",         "常规30期合并格 = 总进件量")
    prow(19, "J24", "4月复贷循环进件量",      "合并格首行")
    prow(20, "J39", "4月复贷非循环进件量",    "合并格首行")
    prow(21, "J75", "5月首贷进件量",         "常规30期合并格 = 总进件量")
    prow(22, "J89", "5月复贷循环进件量",      "合并格首行")
    prow(23, "J104","5月复贷非循环进件量",    "合并格首行")
    prow(24, "I3",  "4月首贷进件成本(IDR)",  "如 1856.66")
    prow(25, "J3",  "5月首贷进件成本(IDR)",  "如 2011.00")
    prow(26, "I4",  "4月复贷进件成本(IDR)",  "如 6822.73")
    prow(27, "J4",  "5月复贷进件成本(IDR)",  "如 6977.07")
    ws.row_dimensions[28].height = 6

    hdr(29, "四、风险参数配置区（行 300+，蓝色输入格）")
    row3(30, "位置",     "Sheet1 行 300 ~ 356（紫色标题区域）", "")
    row3(31, "更新哪列", "S列 = 件均(万盾) | V列 = T30坏账率（填 0.18 表示 18%）", "")
    row3(32, "其他列",   "K/L/M/Q 无需手动修改（由查表公式锁定）", "")
    row3(33, "5月Q系数", "若有新Q分布，直接在参数表右侧5月Q列覆盖", "")
    ws.row_dimensions[34].height = 6

    hdr(35, "五、颜色含义（金融建模标准）")
    row3(36, "蓝色字+黄底", "输入格：每月手动修改的位置")
    row3(37, "黑色字",       "公式格：自动计算，请勿修改")
    row3(38, "紫色标题",     "参数配置区标题行")
    row3(39, "绿色表头",     "参数配置表表头")
    ws.row_dimensions[40].height = 6

    hdr(41, "六、公式链（无需修改，了解即可）")
    chains = [
        ("N = K × M",       "机审通过率 × 后置通过率"),
        ("P = L × N × O",   "确认率 × 机审通过 × 签名放款率"),
        ("R = J × P × Q",   "进件量 × 全流程率 × Q分布 → 放款笔数"),
        ("T = S/汇率×10000","件均(万盾) → 件均($)"),
        ("U = T × R",       "件均$ × 放款笔数 = 放款金额"),
        ("W = T × R",       "件均权重 = 放款金额"),
        ("X = W × V",       "放款金额 × T30坏账率 = 坏账$"),
        ("底部汇总",         "SUMIFS → 坏账率 = 坏账$/业绩$"),
    ]
    for i, (f, n) in enumerate(chains, start=42):
        sc(ws, i, 2, val=f,  bold=True, bg="F2F2F2", ah="left")
        ws.merge_cells(start_row=i, start_column=3, end_row=i, end_column=4)
        sc(ws, i, 3, val=n,  ah="left", wrap=True)
        ws.row_dimensions[i].height = 16
    ws.row_dimensions[51].height = 6

    hdr(52, "七、Q分布系数说明")
    row3(53, "含义",   "每个产品在各期限的放款量占比（各Q之和≈1）")
    row3(54, "4月死数","首次填写后不变，公式自动沿用至5月")
    row3(55, "5月更新","若5月Q分布有变化，直接在参数表5月Q列覆盖新值")
    row3(56, "若无5月值","查表公式优先取5月，无则自动回退至4月值")
    ws.row_dimensions[57].height = 6

    hdr(58, "八、如有新产品类型（本文件支持扩展）")
    row3(59, "操作",   "在参数配置表末尾追加新行 → 数据行查表公式自动覆盖")
    ws.freeze_panes = "B2"


# ═══════════════════════════════════════════════════════════════
# Sheet1: 模板 + 参数配置区 + 查表公式
# ═══════════════════════════════════════════════════════════════
def build_template(wb):
    ws = wb["Sheet1"]

    # ── 参数表起始/结束行 ──
    PT = PARAM_RATE_START   # =300
    HDR_ROW = PT            # 参数表表头行

    # ── 参数表标题行 ──
    title_row = PT - 1
    ws.merge_cells(start_row=title_row, start_column=1,
                   end_row=title_row, end_column=11)
    c = ws.cell(title_row, 1)
    c.value = "【参数配置区】— 蓝色格每月更新：S列=件均(万盾) | V列=T30坏账率 | Q列=分布系数"
    c.font  = fnt(C_WHITE, bold=True, sz=11)
    c.fill  = fill("7B2C8E")
    c.alignment = aln("left")

    # ── 参数表表头 ──
    for ci, h in enumerate(["月份","业务","产品","期限","K","L","M","O","S(件均)","V(T30坏账率)","Q"], start=1):
        sc(ws, HDR_ROW, ci, val=h, bold=True, fc=C_WHITE, bg="C9A7EB")
    ws.row_dimensions[HDR_ROW].height = 18

    # ── 写入 RATE_CONFIG 数据 ──
    param_row = HDR_ROW + 1
    for (month, biz, prod, term), cfg in sorted(RATE_CONFIG.items()):
        O_val = 0.97 if biz == "首贷" else 0.99
        q_val = Q_CONFIG.get((month, biz, prod, term), "")

        vals = [month, biz, prod, term,
                cfg["K"], cfg["L"], cfg["M"], O_val,
                cfg["S"], cfg["V"], q_val]
        for ci, v in enumerate(vals, start=1):
            cell = ws.cell(param_row, ci)
            cell.value = v
            if ci in (9, 10):   # S 和 V 列：蓝色输入格
                cell.font = fnt(C_BLUE, sz=9)
                cell.fill = fill(C_YELLOW)
            elif ci == 11 and q_val != "":
                cell.font = fnt(C_BLUE, sz=9)
                cell.fill = fill(C_YELLOW)
            else:
                cell.font = fnt("595959", sz=9)
            cell.alignment = aln()
            cell.border = bdr()
            cell.number_format = "0.00000" if ci >= 5 else "General"
        ws.row_dimensions[param_row].height = 15
        param_row += 1

    PE = param_row - 1  # 参数表结束行（= 372，72条数据 + 1表头）

    # ── 数据行：替换 K/L/M/S/V/Q → 查表公式 ──
    def iv(month_lit, biz_ref, prod_ref, term_ref, pcol):
        """4条件 INDEX/MATCH 查表公式"""
        return (
            f"=IFERROR(INDEX($A${PT}:$K${PE},"
            f"MATCH(1,($A${PT}:$A${PE}={month_lit})"
            f"*($B${PT}:$B${PE}={biz_ref})"
            f"*($C${PT}:$C${PE}={prod_ref})"
            f"*($D${PT}:$D${PE}={term_ref}),0),"
            f"{pcol}),\"\")"
        )

    def qv(month_lit, biz_ref, prod_ref, term_ref, qcol):
        """Q系数：优先当月，无则回退4月"""
        q1 = (f"IFERROR(INDEX($A${PT}:$K${PE},"
              f"MATCH(1,($A${PT}:$A${PE}={month_lit})"
              f"*($B${PT}:$B${PE}={biz_ref})"
              f"*($C${PT}:$C${PE}={prod_ref})"
              f"*($D${PT}:$D${PE}={term_ref}),0),{qcol}),\"\")")
        q2 = (f"IFERROR(INDEX($A${PT}:$K${PE},"
              f"MATCH(1,($A${PT}:$A${PE}=\"4月\")"
              f"*($B${PT}:$B${PE}={biz_ref})"
              f"*($C${PT}:$C${PE}={prod_ref})"
              f"*($D${PT}:$D${PE}={term_ref}),0),{qcol}),\"\")")
        return f"=IF({q1}=\"\",{q2},{q1})"

    def ov(biz_ref):
        return f'=IF({biz_ref}="首贷",0.97,0.99)'

    for (month, biz), (j_row, start_row, end_row, total_row) in BLOCKS.items():
        for row in range(start_row, (total_row or end_row) + 1):
            if row > ws.max_row:
                break
            h_val = ws.cell(row, COL["H"]).value
            if h_val in ("合计", "汇总", None):
                continue
            prod_ref  = addr(row, COL["I"])
            term_ref  = addr(row, COL["H"])
            month_lit = f'"{month}"'
            biz_ref   = addr(row, COL["B"])

            sc(ws, row, COL["K"], formula=iv(month_lit, biz_ref, prod_ref, term_ref, PARAM_COL["K"]))
            sc(ws, row, COL["L"], formula=iv(month_lit, biz_ref, prod_ref, term_ref, PARAM_COL["L"]))
            sc(ws, row, COL["M"], formula=iv(month_lit, biz_ref, prod_ref, term_ref, PARAM_COL["M"]))
            sc(ws, row, COL["O"], formula=ov(biz_ref))
            sc(ws, row, COL["S"], formula=iv(month_lit, biz_ref, prod_ref, term_ref, PARAM_COL["S"]))
            sc(ws, row, COL["V"], formula=iv(month_lit, biz_ref, prod_ref, term_ref, PARAM_COL["V"]))
            sc(ws, row, COL["Q"], formula=qv(month_lit, biz_ref, prod_ref, term_ref, PARAM_COL["Q"]))

    # ── 全局参数格：蓝色粗体标注 ──
    ws.cell(7, COL["J"]).font  = fnt(C_BLUE, bold=True)
    ws.cell(7, COL["J"]).fill  = fill(C_YELLOW)
    for jj in [10, 24, 39, 75, 89, 104]:
        cj = ws.cell(jj, COL["J"])
        cj.font = fnt(C_BLUE, bold=True)
        cj.fill = fill(C_YELLOW)
    for rr, cc in [(3,9),(3,10),(4,9),(4,10)]:
        cx = ws.cell(rr, cc)
        cx.font = fnt(C_BLUE)
        cx.fill = fill(C_YELLOW)

    ws.freeze_panes = "B9"


# ═══════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = os.path.join(OUT_DIR, OUT_NAME)
    shutil.copy2(TEMPLATE_PATH, tmp)

    wb = openpyxl.load_workbook(tmp)
    build_instructions(wb)
    build_template(wb)

    wb.save(tmp)
    print(f"OK. Saved: {tmp}")
    return tmp


if __name__ == "__main__":
    main()
