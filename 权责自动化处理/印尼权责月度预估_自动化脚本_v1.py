"""
印尼权责月度预估自动化脚本
===============================
输入：risk_config.py 中的风险数据（进件量、件均、转化率、T30坏账率）
处理：
  1. 读取4月/5月风险死数
  2. 写入数据区1(4月)：R10/R24/R39 的 J列 进件量 + 各期K/L/M/S/V列死数
  3. 写入数据区2(5月)：R75/R89/R104 的 J列 进件量 + 各期K/L/M/S/V列死数
  4. 公式链自动联动（Q/R/T/W/X/Y/Z列均为公式，无需填写）
  5. 底部汇总1/2 的SUMIFS公式保持不变（已内嵌在模板中）
输出：新Excel文件（公式全部自动联动）
"""

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
import os
import shutil
import copy

# ═══════════════════════════════════════════════════════════════════
# 一、风险数据配置区（每月只需修改这里）
# ═══════════════════════════════════════════════════════════════════

# ── 1. 月份标题（会写入 R2 单元格）────────────
MONTH1_LABEL = "2026-04"   # 数据区1的月份
MONTH2_LABEL = "2026-05"   # 数据区2的月份

# ── 2. 汇率（固定死数）────────────
EXCHANGE_RATE = 17090

# ── 3. 首贷进件量（常规30期，只有这一行是进件量死数）────────────
#     其他期（60/90/120/150/180）的进件量列(J列)留空，Q分布系数由死数给定
FL_MONTH1_J = 581171       # 4月 首贷 常规30期 进件量
FL_MONTH2_J = 623875       # 5月 首贷 常规30期 进件量

# ── 4. 复贷循环贷进件量（常规30期，只有这一行是进件量死数）────────────
RL_LOOP_MONTH1_J = 179744   # 4月 复贷-循环贷 常规30期 进件量
RL_LOOP_MONTH2_J = 216277.7292  # 5月 复贷-循环贷 常规30期 进件量（若由放款量反推则填写计算值）

# ── 5. 复贷非循环贷进件量（常规30期，只有这一行是进件量死数）────────────
RL_NORM_MONTH1_J = 200402   # 4月 复贷-非循环贷 常规30期 进件量
RL_NORM_MONTH2_J = 159904.1875  # 5月 复贷-非循环贷 常规30期 进件量

# ── 6. 每进件成本（IDR）────────────
FL_COST_IDR_MONTH1 = 1856.66
FL_COST_IDR_MONTH2 = 2011.00
RL_COST_IDR_MONTH1 = 6822.73
RL_COST_IDR_MONTH2 = 6977.07

# ── 7. 各产品×期限 死数配置 ────────────
# 数据结构：(月份, 业务, 产品类型, 期限) → {K, L, M, S, V}
# K=机审通过率, L=确认借款率, M=后置通过率, S=件均(万盾), V=T30坏账率
# 注意：首贷 P = K×L×M×0.97；复贷 P = K×M×L×0.99

RATE_CONFIG = {
    # ══ 首贷 4月 ══════════════════════════════════════════
    ("4月", "首贷", "常规", 30): dict(K=0.26,  L=0.81, M=0.523, S=60.48,  V=0.187732),
    ("4月", "首贷", "常规", 60): dict(K=0.26,  L=0.81, M=0.523, S=271.06, V=0.1635),
    ("4月", "首贷", "常规", 90): dict(K=0.26,  L=0.81, M=0.523, S=247.23, V=0.1407),
    ("4月", "首贷", "常规",120): dict(K=0.26,  L=0.81, M=0.523, S=434.65, V=0.1387),
    ("4月", "首贷", "常规",150): dict(K=0.26,  L=0.81, M=0.523, S=472.55, V=0.1340),
    ("4月", "首贷", "常规",180): dict(K=0.26,  L=0.81, M=0.523, S=400.00, V=0.1200),
    ("4月", "首贷", "优享贷", 90): dict(K=0.26, L=0.81, M=0.523, S=76.3,  V=0.1407),
    ("4月", "首贷", "优享贷",120): dict(K=0.26,L=0.81, M=0.523, S=95.9,  V=0.1387),
    ("4月", "首贷", "优享贷",150): dict(K=0.26,L=0.81, M=0.523, S=150.0, V=0.1340),
    ("4月", "首贷", "优享贷",180): dict(K=0.26,L=0.81, M=0.523, S=99.9,  V=0.1200),
    ("4月", "首贷", "放心贷",150): dict(K=0.26, L=0.81, M=0.523, S=27.3,  V=0.1340),
    ("4月", "首贷", "放心贷",180): dict(K=0.26, L=0.81, M=0.523, S=27.1,  V=0.1200),
    ("4月", "首贷", "本金",  150): dict(K=0.26, L=0.81, M=0.523, S=30.82, V=0.1340),
    ("4月", "首贷", "本金",  180): dict(K=0.26, L=0.81, M=0.523, S=27.1,  V=0.1200),
    ("4月", "首贷", "无忧贷",120): dict(K=0.26, L=0.81, M=0.523, S=67.71, V=0.1387),

    # ══ 首贷 5月 ══════════════════════════════════════════
    ("5月", "首贷", "常规", 30): dict(K=0.26,  L=0.81, M=0.530, S=60.08,  V=0.19377),
    ("5月", "首贷", "常规", 60): dict(K=0.26,  L=0.81, M=0.530, S=270.0,  V=0.1700),
    ("5月", "首贷", "常规", 90): dict(K=0.26,  L=0.81, M=0.530, S=248.0,  V=0.1500),
    ("5月", "首贷", "常规",120): dict(K=0.26,  L=0.81, M=0.530, S=435.0,  V=0.1450),
    ("5月", "首贷", "常规",150): dict(K=0.26,  L=0.81, M=0.530, S=473.0,  V=0.1400),
    ("5月", "首贷", "常规",180): dict(K=0.26,  L=0.81, M=0.530, S=400.0,  V=0.1250),
    ("5月", "首贷", "优享贷", 90): dict(K=0.26, L=0.81, M=0.530, S=76.3,  V=0.1500),
    ("5月", "首贷", "优享贷",120): dict(K=0.26,L=0.81, M=0.530, S=95.9,  V=0.1450),
    ("5月", "首贷", "优享贷",150): dict(K=0.26,L=0.81, M=0.530, S=150.0, V=0.1400),
    ("5月", "首贷", "优享贷",180): dict(K=0.26,L=0.81, M=0.530, S=100.0, V=0.1250),
    ("5月", "首贷", "放心贷",150): dict(K=0.26, L=0.81, M=0.530, S=27.3,  V=0.1400),
    ("5月", "首贷", "放心贷",180): dict(K=0.26, L=0.81, M=0.530, S=27.1,  V=0.1250),
    ("5月", "首贷", "本金",  150): dict(K=0.26, L=0.81, M=0.530, S=31.0,  V=0.1400),
    ("5月", "首贷", "本金",  180): dict(K=0.26, L=0.81, M=0.530, S=27.1,  V=0.1250),
    ("5月", "首贷", "无忧贷",120): dict(K=0.26, L=0.81, M=0.530, S=68.0,  V=0.1450),

    # ══ 复贷-循环贷 4月 ═══════════════════════════════════
    ("4月", "复贷-循环贷", "常规", 30):  dict(K=0.6143, L=1.0,  M=0.9822, S=91.93,  V=0.19284),
    ("4月", "复贷-循环贷", "常规", 60):  dict(K=0.6143, L=1.0,  M=0.9822, S=114.93, V=0.1200),
    ("4月", "复贷-循环贷", "常规", 90):  dict(K=0.6143, L=1.0,  M=0.9822, S=384.31, V=0.0920),
    ("4月", "复贷-循环贷", "常规",120):  dict(K=0.6143, L=1.0,  M=0.9822, S=583.81, V=0.0820),
    ("4月", "复贷-循环贷", "常规",150):  dict(K=0.6143, L=1.0,  M=0.9822, S=121.85, V=0.0750),
    ("4月", "复贷-循环贷", "常规",180):  dict(K=0.6143, L=1.0,  M=0.9822, S=135.04, V=0.0680),
    ("4月", "复贷-循环贷", "无忧贷", 90): dict(K=0.6143, L=1.0,  M=0.9822, S=289.59, V=0.0920),
    ("4月", "复贷-循环贷", "无忧贷",120): dict(K=0.6143, L=1.0,  M=0.9822, S=284.06, V=0.0820),
    ("4月", "复贷-循环贷", "优享贷", 90): dict(K=0.6143, L=1.0,  M=0.9822, S=213.85, V=0.0920),
    ("4月", "复贷-循环贷", "优享贷",120): dict(K=0.6143, L=1.0,  M=0.9822, S=239.44, V=0.0820),
    ("4月", "复贷-循环贷", "优享贷",150): dict(K=0.6143, L=1.0,  M=0.9822, S=409.47, V=0.0750),
    ("4月", "复贷-循环贷", "优享贷",180): dict(K=0.6143, L=1.0,  M=0.9822, S=219.54, V=0.0680),
    ("4月", "复贷-循环贷", "放心贷",150): dict(K=0.6143, L=1.0,  M=0.9822, S=121.85, V=0.0750),
    ("4月", "复贷-循环贷", "放心贷",180): dict(K=0.6143, L=1.0,  M=0.9822, S=94.45,  V=0.0680),
    ("4月", "复贷-循环贷", "本金",  150): dict(K=0.6143, L=1.0,  M=0.9822, S=93.89,  V=0.0750),
    ("4月", "复贷-循环贷", "本金",  180): dict(K=0.6143, L=1.0,  M=0.9822, S=135.04, V=0.0680),

    # ══ 复贷-循环贷 5月 ═══════════════════════════════════
    ("5月", "复贷-循环贷", "常规", 30):  dict(K=0.6086, L=1.0,  M=0.9822, S=95.44,  V=0.19284),
    ("5月", "复贷-循环贷", "常规", 60):  dict(K=0.6086, L=1.0,  M=0.9822, S=120.67, V=0.1200),
    ("5月", "复贷-循环贷", "常规", 90):  dict(K=0.6086, L=1.0,  M=0.9822, S=403.53, V=0.0920),
    ("5月", "复贷-循环贷", "常规",120):  dict(K=0.6086, L=1.0,  M=0.9822, S=613.00, V=0.0820),
    ("5月", "复贷-循环贷", "常规",150):  dict(K=0.6086, L=1.0,  M=0.9822, S=119.46, V=0.0750),
    ("5月", "复贷-循环贷", "常规",180):  dict(K=0.6086, L=1.0,  M=0.9822, S=132.73, V=0.0680),
    ("5月", "复贷-循环贷", "无忧贷", 90): dict(K=0.6086, L=1.0,  M=0.9822, S=289.59, V=0.0920),
    ("5月", "复贷-循环贷", "无忧贷",120): dict(K=0.6086, L=1.0,  M=0.9822, S=275.07, V=0.0820),
    ("5月", "复贷-循环贷", "优享贷", 90): dict(K=0.6086, L=1.0,  M=0.9822, S=213.85, V=0.0920),
    ("5月", "复贷-循环贷", "优享贷",120): dict(K=0.6086, L=1.0,  M=0.9822, S=248.04, V=0.0820),
    ("5月", "复贷-循环贷", "优享贷",150): dict(K=0.6086, L=1.0,  M=0.9822, S=417.66, V=0.0750),
    ("5月", "复贷-循环贷", "优享贷",180): dict(K=0.6086, L=1.0,  M=0.9822, S=219.54, V=0.0680),
    ("5月", "复贷-循环贷", "放心贷",150): dict(K=0.6086, L=1.0,  M=0.9822, S=119.46, V=0.0750),
    ("5月", "复贷-循环贷", "放心贷",180): dict(K=0.6086, L=1.0,  M=0.9822, S=94.19,  V=0.0680),
    ("5月", "复贷-循环贷", "本金",  150): dict(K=0.6086, L=1.0,  M=0.9822, S=93.45,  V=0.0750),
    ("5月", "复贷-循环贷", "本金",  180): dict(K=0.6086, L=1.0,  M=0.9822, S=132.73, V=0.0680),

    # ══ 复贷-非循环贷 4月 ══════════════════════════════════
    ("4月", "复贷-非循环贷", "常规", 30): dict(K=0.3827, L=0.81, M=0.9999, S=56.28, V=0.10679),
    ("4月", "复贷-非循环贷", "常规", 60): dict(K=0.3827, L=0.81, M=0.9999, S=56.28, V=0.09000),
    ("4月", "复贷-非循环贷", "常规", 90): dict(K=0.3827, L=0.81, M=0.9999, S=56.28, V=0.07500),
    ("4月", "复贷-非循环贷", "常规",120): dict(K=0.3827, L=0.81, M=0.9999, S=56.28, V=0.06500),
    ("4月", "复贷-非循环贷", "常规",150): dict(K=0.3827, L=0.81, M=0.9999, S=56.28, V=0.05500),
    ("4月", "复贷-非循环贷", "常规",180): dict(K=0.3827, L=0.81, M=0.9999, S=56.28, V=0.05000),
    ("4月", "复贷-非循环贷", "无忧贷", 90): dict(K=0.3827, L=0.81, M=0.9999, S=289.59,V=0.07500),
    ("4月", "复贷-非循环贷", "无忧贷",120): dict(K=0.3827, L=0.81, M=0.9999, S=284.06,V=0.06500),
    ("4月", "复贷-非循环贷", "优享贷", 90): dict(K=0.3827, L=0.81, M=0.9999, S=213.85,V=0.07500),
    ("4月", "复贷-非循环贷", "优享贷",120): dict(K=0.3827, L=0.81, M=0.9999, S=239.44,V=0.06500),

    # ══ 复贷-非循环贷 5月 ══════════════════════════════════
    ("5月", "复贷-非循环贷", "常规", 30): dict(K=0.3827, L=0.81, M=0.9999, S=56.31, V=0.10679),
    ("5月", "复贷-非循环贷", "常规", 60): dict(K=0.3827, L=0.81, M=0.9999, S=56.31, V=0.09000),
    ("5月", "复贷-非循环贷", "常规", 90): dict(K=0.3827, L=0.81, M=0.9999, S=56.31, V=0.07500),
    ("5月", "复贷-非循环贷", "常规",120): dict(K=0.3827, L=0.81, M=0.9999, S=56.31, V=0.06500),
    ("5月", "复贷-非循环贷", "常规",150): dict(K=0.3827, L=0.81, M=0.9999, S=56.31, V=0.05500),
    ("5月", "复贷-非循环贷", "常规",180): dict(K=0.3827, L=0.81, M=0.9999, S=56.31, V=0.05000),
    ("5月", "复贷-非循环贷", "无忧贷", 90): dict(K=0.3827, L=0.81, M=0.9999, S=289.59,V=0.07500),
    ("5月", "复贷-非循环贷", "无忧贷",120): dict(K=0.3827, L=0.81, M=0.9999, S=284.06,V=0.06500),
    ("5月", "复贷-非循环贷", "优享贷", 90): dict(K=0.3827, L=0.81, M=0.9999, S=213.85,V=0.07500),
    ("5月", "复贷-非循环贷", "优享贷",120): dict(K=0.3827, L=0.81, M=0.9999, S=239.44,V=0.06500),
}

# ── 8. 各期 Q 分布系数（4月死数，5月沿用）────────────
# 若5月有新分布，可在此覆盖
# 格式：(月份, 业务, 产品类型, 期限) → Q值
Q_CONFIG = {
    # ══ 4月 首贷 ════════════════════════
    ("4月", "首贷", "常规",  30): 0.07117,
    ("4月", "首贷", "常规",  60): 0.05316,
    ("4月", "首贷", "常规",  90): 0.06328,
    ("4月", "首贷", "常规", 120): 0.00625,
    ("4月", "首贷", "常规", 150): 0.04588,
    ("4月", "首贷", "常规", 180): 0.10655,
    ("4月", "首贷", "优享贷", 90): 0.05689,
    ("4月", "首贷", "优享贷",120): 0.02799,
    ("4月", "首贷", "优享贷",150): 0.02500,
    ("4月", "首贷", "优享贷",180): 0.09030,
    ("4月", "首贷", "放心贷",150): 0.08940,
    ("4月", "首贷", "放心贷",180): 0.00903,
    ("4月", "首贷", "本金",  150): 0.20802,
    ("4月", "首贷", "本金",  180): 0.01625,
    ("4月", "首贷", "无忧贷",120): 0.26236,

    # ══ 4月 复贷-循环贷 ══════════════════
    ("4月", "复贷-循环贷", "常规",  30): 0.00326,
    ("4月", "复贷-循环贷", "常规",  60): 0.03293,
    ("4月", "复贷-循环贷", "常规",  90): 0.05254,
    ("4月", "复贷-循环贷", "常规", 120): 0.05016,
    ("4月", "复贷-循环贷", "常规", 150): 0.03527,
    ("4月", "复贷-循环贷", "常规", 180): 0.10969,
    ("4月", "复贷-循环贷", "无忧贷", 90): 0.04329,
    ("4月", "复贷-循环贷", "无忧贷",120): 0.13146,
    ("4月", "复贷-循环贷", "优享贷", 90): 0.05740,
    ("4月", "复贷-循环贷", "优享贷",120): 0.13557,
    ("4月", "复贷-循环贷", "优享贷",150): 0.03527,
    ("4月", "复贷-循环贷", "优享贷",180): 0.05526,
    ("4月", "复贷-循环贷", "放心贷",150): 0.05401,
    ("4月", "复贷-循环贷", "放心贷",180): 0.17623,
    ("4月", "复贷-循环贷", "本金",  150): 0.11818,
    ("4月", "复贷-循环贷", "本金",  180): 0.05443,

    # ══ 4月 复贷-非循环贷 ══════════════════
    ("4月", "复贷-非循环贷", "常规",  30): 0.00706,
    ("4月", "复贷-非循环贷", "常规",  60): 0.30000,
    ("4月", "复贷-非循环贷", "常规",  90): 0.20000,
    ("4月", "复贷-非循环贷", "常规", 120): 0.20000,
    ("4月", "复贷-非循环贷", "常规", 150): 0.20000,
    ("4月", "复贷-非循环贷", "常规", 180): 0.10000,
    ("4月", "复贷-非循环贷", "无忧贷", 90): 0.30000,
    ("4月", "复贷-非循环贷", "无忧贷",120): 0.30000,
    ("4月", "复贷-非循环贷", "优享贷", 90): 0.30000,
    ("4月", "复贷-非循环贷", "优享贷",120): 0.30000,

    # ══ 5月首贷（若与4月不同，填写；否则留空则沿用4月）═══════════
    # 5月若未填写，沿用4月的Q值
    # 示例：(5月相同则不填)
}

# ═══════════════════════════════════════════════════════════════════
# 二、模板行列映射定义
# ═══════════════════════════════════════════════════════════════════
# 数据区1(4月)：行9=标题, 10-22=首贷, 24-37=循环贷, 39-47=非循环贷, 52-57=本金加贷
# 数据区2(5月)：行74=标题, 75-87=首贷, 89-102=循环贷, 104-116=非循环贷, 117-122=本金加贷
#
# 列对照：
#   A=业务(首贷/复贷), B=产品细分(首贷/循环贷/非循环贷/本金加贷),
#   H=期限, I=产品类型, J=进件量,
#   K=机审通过率, L=确认借款率, M=后置通过率,
#   N=K×M, O=签名放款率, P=全流程(K×L×M×O),
#   Q=各期分布系数, R=放款量(J×P×Q),
#   S=件均(万盾), T=S/汇率×10000, U=件均权重,
#   V=T30坏账率, W=业绩$(T×R), X=坏账$(W×V),
#   Y=W×H, Z=平均期限=Y/W

# 4月数据区行列结构
MONTH1_ROWS = {
    "首贷":          list(range(10, 23)),   # 10-22数据 + 23合计
    "复贷-循环贷":   list(range(24, 38)),   # 24-37数据 + 38合计
    "复贷-非循环贷": list(range(39, 51)),   # 39-50数据 + 51合计
    "本金加贷":      list(range(52, 64)),   # 52-63数据 + 63合计(预留)
}

# 5月数据区行列结构
MONTH2_ROWS = {
    "首贷":          list(range(75, 88)),    # 75-87数据 + 88合计
    "复贷-循环贷":   list(range(89, 103)),  # 89-102数据 + 103合计
    "复贷-非循环贷": list(range(104, 117)), # 104-116数据 + 117合计
    "本金加贷":      list(range(117, 130)), # 117-129数据 + 130合计
}

# 月份-数据区起始行映射
MONTH1_DATA_START = 10  # 4月首贷第1行
MONTH2_DATA_START = 75  # 5月首贷第1行

# 列索引（openpyxl 1-based）
COL_J  = 10  # J=进件量
COL_K  = 11  # K=机审通过率
COL_L  = 12  # L=确认借款率
COL_M  = 13  # M=后置通过率
COL_N  = 14  # N=K×M
COL_O  = 15  # O=签名放款率
COL_P  = 16  # P=全流程通过率
COL_Q  = 17  # Q=各期分布系数
COL_R  = 18  # R=放款量
COL_S  = 19  # S=件均(万盾)
COL_T  = 20  # T=件均$
COL_U  = 21  # U=件均权重
COL_V  = 22  # V=T30坏账率
COL_W  = 23  # W=业绩$
COL_X  = 24  # X=坏账$
COL_Y  = 25  # Y=W×H
COL_Z  = 26  # Z=Y/W(平均期限)

# 固定值
FL_SIGN_RATE = 0.97   # 首贷签名放款率
RL_SIGN_RATE = 0.99   # 复贷签名放款率


# ═══════════════════════════════════════════════════════════════════
# 三、工具函数
# ═══════════════════════════════════════════════════════════════════

def unmerge_and_fill_data_block(ws, data_rows):
    """
    对一个数据块（若干连续行）取消J-P列的大范围合并，
    然后对每行分别填入死数值。
    
    data_rows: 行号列表 [start, start+1, ..., end]
    cols_to_write: 要写入的列索引列表，如 [COL_K, COL_L, COL_M, COL_S, COL_V, COL_Q]
    """
    import copy
    # 收集要取消合并的列范围
    # J-P 列是列 10-16
    for col in range(10, 17):  # J=10 到 P=16
        # 查找这个列在data_rows范围内是否有合并单元格
        for merge in list(ws.merged_cells.ranges):
            # 检查合并范围是否包含这个列，以及是否与data_rows重叠
            if (merge.min_col <= col <= merge.max_col and
                max(merge.min_row, data_rows[0]) <= min(merge.max_row, data_rows[-1])):
                # 取消合并
                ws.merged_cells.remove(merge)


def find_data_row(ws, month_rows, business, product, term):
    """
    在指定业务的数据块中，找到匹配 (产品类型, 期限) 的行号
    month_rows: MONTH1_ROWS 或 MONTH2_ROWS
    返回: 行号(int)，找不到返回 None
    """
    for row in month_rows[business]:
        # 读取该行的 H列(期限) 和 I列(产品类型)
        h_val = ws.cell(row, 8).value   # H=期限
        i_val = ws.cell(row, 9).value   # I=产品类型
        if h_val == term and i_val == product:
            return row
    return None


def get_month_key(month_label):
    """把月份标签转为配置字典的key前缀"""
    return "4月" if "04" in month_label else "5月"


def calc_p(k, l, m, sign_rate):
    """全流程通过率 P = K×L×M×签名放款率"""
    return k * l * m * sign_rate


# ═══════════════════════════════════════════════════════════════════
# 四、主逻辑
# ═══════════════════════════════════════════════════════════════════

def main():
    # ── 0. 加载模板 ──────────────────────────────
    template_path = os.path.join(
        os.path.dirname(__file__),
        "权责近两个月的数据预估_模板.xlsx"
    )
    # 若模板不存在，复制源文件作为模板
    source_path = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\202605月预估\权责近两个月的数据预估.xlsx"
    if not os.path.exists(template_path):
        shutil.copy2(source_path, template_path)
        print(f"[OK] 已复制源文件为模板: {template_path}")

    wb = openpyxl.load_workbook(template_path)
    ws = wb["Sheet1"]

    print("=" * 60)
    print("印尼权责月度预估自动化")
    print(f"  月份1: {MONTH1_LABEL}  |  月份2: {MONTH2_LABEL}")
    print("=" * 60)

    # ── 0b. 取消数据区合并单元格（允许每行单独写入）────────────
    # 4月：首贷10-22, 循环贷24-37, 非循环贷39-47, 本金加贷52-63
    # 5月：首贷75-87, 循环贷89-102, 非循环贷104-116, 本金加贷117-130
    unmerge_and_fill_data_block(ws, list(range(10, 23)))
    unmerge_and_fill_data_block(ws, list(range(24, 38)))
    unmerge_and_fill_data_block(ws, list(range(39, 51)))
    unmerge_and_fill_data_block(ws, list(range(52, 64)))
    unmerge_and_fill_data_block(ws, list(range(75, 88)))
    unmerge_and_fill_data_block(ws, list(range(89, 103)))
    unmerge_and_fill_data_block(ws, list(range(104, 117)))
    unmerge_and_fill_data_block(ws, list(range(117, 131)))
    print("[OK] 已取消数据区J-P列合并单元格")

    # ── 1. 写入死数参数区 ──────────────────────────────
    # I7/J7=汇率, I3/I4/J3/J4=进件成本(IDR), I5/I6/J5/J6=公式
    ws.cell(7, 8).value = EXCHANGE_RATE  # H7=汇率标签, I7=J7=汇率值
    ws.cell(7, 9).value = EXCHANGE_RATE
    ws.cell(3, 9).value = FL_COST_IDR_MONTH1   # I3=首贷4月成本IDR
    ws.cell(3, 10).value = FL_COST_IDR_MONTH2  # J3=首贷5月成本IDR
    ws.cell(4, 9).value = RL_COST_IDR_MONTH1   # I4=复贷4月成本IDR
    ws.cell(4, 10).value = RL_COST_IDR_MONTH2  # J4=复贷5月成本IDR
    print("[OK] 死数参数区已写入 (汇率, 进件成本)")

    # ── 2. 写入数据区1(4月) ──────────────────────────────
    print("\n[DATA] 写入 4月 数据区...")
    month_key_1 = get_month_key(MONTH1_LABEL)

    # 写入首贷进件量(常规30期)
    fl_row1 = MONTH1_DATA_START
    ws.cell(fl_row1, COL_J).value = FL_MONTH1_J
    sign_rate_fl = FL_SIGN_RATE

    for (m_key, biz, prod, term), cfg in RATE_CONFIG.items():
        if m_key != month_key_1:
            continue
        row = find_data_row(ws, MONTH1_ROWS, biz, prod, term)
        if row is None:
            print(f"  [WARN] 4月未找到: {biz} {prod} {term}期")
            continue

        # K/L/M: 转化率死数
        ws.cell(row, COL_K).value = cfg["K"]
        ws.cell(row, COL_L).value = cfg["L"]
        ws.cell(row, COL_M).value = cfg["M"]
        # O: 签名放款率
        ws.cell(row, COL_O).value = FL_SIGN_RATE if biz == "首贷" else RL_SIGN_RATE
        # S: 件均(万盾)
        ws.cell(row, COL_S).value = cfg["S"]
        # V: T30坏账率
        ws.cell(row, COL_V).value = cfg["V"]

        # Q: 各期分布系数（若有配置）
        q_key = (m_key, biz, prod, term)
        if q_key in Q_CONFIG:
            ws.cell(row, COL_Q).value = Q_CONFIG[q_key]

        # P=全流程公式已嵌入模板，这里不需要写
        # N=K×M公式已嵌入模板
        # R=J×P×Q公式已嵌入模板（依赖J、P、Q）
        # T/S/U/W/X/Y/Z公式已嵌入模板

    print(f"  [OK] 首贷 4月: J{MONTH1_DATA_START}={FL_MONTH1_J}")

    # 复贷-循环贷
    rl_loop_base_row1 = MONTH1_ROWS["复贷-循环贷"][0]
    ws.cell(rl_loop_base_row1, COL_J).value = RL_LOOP_MONTH1_J
    for (m_key, biz, prod, term), cfg in RATE_CONFIG.items():
        if m_key != month_key_1 or biz != "复贷-循环贷":
            continue
        row = find_data_row(ws, MONTH1_ROWS, biz, prod, term)
        if row is None:
            print(f"  [WARN]️  4月复贷-循环贷未找到: {prod} {term}期")
            continue
        ws.cell(row, COL_K).value = cfg["K"]
        ws.cell(row, COL_L).value = cfg["L"]
        ws.cell(row, COL_M).value = cfg["M"]
        ws.cell(row, COL_O).value = RL_SIGN_RATE
        ws.cell(row, COL_S).value = cfg["S"]
        ws.cell(row, COL_V).value = cfg["V"]
        q_key = (m_key, biz, prod, term)
        if q_key in Q_CONFIG:
            ws.cell(row, COL_Q).value = Q_CONFIG[q_key]
    print(f"  [OK] 复贷-循环贷 4月: J{rl_loop_base_row1}={RL_LOOP_MONTH1_J}")

    # 复贷-非循环贷
    rl_norm_base_row1 = MONTH1_ROWS["复贷-非循环贷"][0]
    ws.cell(rl_norm_base_row1, COL_J).value = RL_NORM_MONTH1_J
    for (m_key, biz, prod, term), cfg in RATE_CONFIG.items():
        if m_key != month_key_1 or biz != "复贷-非循环贷":
            continue
        row = find_data_row(ws, MONTH1_ROWS, biz, prod, term)
        if row is None:
            print(f"  [WARN]️  4月复贷-非循环贷未找到: {prod} {term}期")
            continue
        ws.cell(row, COL_K).value = cfg["K"]
        ws.cell(row, COL_L).value = cfg["L"]
        ws.cell(row, COL_M).value = cfg["M"]
        ws.cell(row, COL_O).value = RL_SIGN_RATE
        ws.cell(row, COL_S).value = cfg["S"]
        ws.cell(row, COL_V).value = cfg["V"]
        q_key = (m_key, biz, prod, term)
        if q_key in Q_CONFIG:
            ws.cell(row, COL_Q).value = Q_CONFIG[q_key]
    print(f"  [OK] 复贷-非循环贷 4月: J{rl_norm_base_row1}={RL_NORM_MONTH1_J}")

    # ── 3. 写入数据区2(5月) ──────────────────────────────
    print("\n[DATA] 写入 5月 数据区...")
    month_key_2 = get_month_key(MONTH2_LABEL)

    # 5月首贷
    fl_row2 = MONTH2_DATA_START
    ws.cell(fl_row2, COL_J).value = FL_MONTH2_J
    for (m_key, biz, prod, term), cfg in RATE_CONFIG.items():
        if m_key != month_key_2:
            continue
        row = find_data_row(ws, MONTH2_ROWS, biz, prod, term)
        if row is None:
            print(f"  [WARN]️  5月未找到: {biz} {prod} {term}期")
            continue
        ws.cell(row, COL_K).value = cfg["K"]
        ws.cell(row, COL_L).value = cfg["L"]
        ws.cell(row, COL_M).value = cfg["M"]
        ws.cell(row, COL_O).value = FL_SIGN_RATE if biz == "首贷" else RL_SIGN_RATE
        ws.cell(row, COL_S).value = cfg["S"]
        ws.cell(row, COL_V).value = cfg["V"]
        # Q: 5月若无单独配置，沿用4月
        q_key_2 = (m_key, biz, prod, term)
        if q_key_2 in Q_CONFIG:
            ws.cell(row, COL_Q).value = Q_CONFIG[q_key_2]
        else:
            # 沿用4月的Q
            q_key_4 = ("4月", biz, prod, term)
            if q_key_4 in Q_CONFIG:
                ws.cell(row, COL_Q).value = Q_CONFIG[q_key_4]
    print(f"  [OK] 首贷 5月: J{MONTH2_DATA_START}={FL_MONTH2_J}")

    # 5月复贷-循环贷
    rl_loop_base_row2 = MONTH2_ROWS["复贷-循环贷"][0]
    ws.cell(rl_loop_base_row2, COL_J).value = RL_LOOP_MONTH2_J
    for (m_key, biz, prod, term), cfg in RATE_CONFIG.items():
        if m_key != month_key_2 or biz != "复贷-循环贷":
            continue
        row = find_data_row(ws, MONTH2_ROWS, biz, prod, term)
        if row is None:
            print(f"  [WARN]️  5月复贷-循环贷未找到: {prod} {term}期")
            continue
        ws.cell(row, COL_K).value = cfg["K"]
        ws.cell(row, COL_L).value = cfg["L"]
        ws.cell(row, COL_M).value = cfg["M"]
        ws.cell(row, COL_O).value = RL_SIGN_RATE
        ws.cell(row, COL_S).value = cfg["S"]
        ws.cell(row, COL_V).value = cfg["V"]
        q_key_2 = (m_key, biz, prod, term)
        if q_key_2 in Q_CONFIG:
            ws.cell(row, COL_Q).value = Q_CONFIG[q_key_2]
        else:
            q_key_4 = ("4月", biz, prod, term)
            if q_key_4 in Q_CONFIG:
                ws.cell(row, COL_Q).value = Q_CONFIG[q_key_4]
    print(f"  [OK] 复贷-循环贷 5月: J{rl_loop_base_row2}={RL_LOOP_MONTH2_J}")

    # 5月复贷-非循环贷
    rl_norm_base_row2 = MONTH2_ROWS["复贷-非循环贷"][0]
    ws.cell(rl_norm_base_row2, COL_J).value = RL_NORM_MONTH2_J
    for (m_key, biz, prod, term), cfg in RATE_CONFIG.items():
        if m_key != month_key_2 or biz != "复贷-非循环贷":
            continue
        row = find_data_row(ws, MONTH2_ROWS, biz, prod, term)
        if row is None:
            print(f"  [WARN]️  5月复贷-非循环贷未找到: {prod} {term}期")
            continue
        ws.cell(row, COL_K).value = cfg["K"]
        ws.cell(row, COL_L).value = cfg["L"]
        ws.cell(row, COL_M).value = cfg["M"]
        ws.cell(row, COL_O).value = RL_SIGN_RATE
        ws.cell(row, COL_S).value = cfg["S"]
        ws.cell(row, COL_V).value = cfg["V"]
        q_key_2 = (m_key, biz, prod, term)
        if q_key_2 in Q_CONFIG:
            ws.cell(row, COL_Q).value = Q_CONFIG[q_key_2]
        else:
            q_key_4 = ("4月", biz, prod, term)
            if q_key_4 in Q_CONFIG:
                ws.cell(row, COL_Q).value = Q_CONFIG[q_key_4]
    print(f"  [OK] 复贷-非循环贷 5月: J{rl_norm_base_row2}={RL_NORM_MONTH2_J}")

    # ── 4. 保存输出文件 ──────────────────────────────
    output_dir = os.path.join(
        r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析",
        f"{MONTH2_LABEL}月预估"
    )
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"权责两个月数据预估_{MONTH2_LABEL}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

    wb.save(output_path)
    print(f"\n[OK] 输出文件已保存: {output_path}")
    print("   打开Excel后，底部汇总1/2的SUMIFS公式将自动联动！")
    return output_path


if __name__ == "__main__":
    main()
