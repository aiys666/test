# ============================================================
# 权责近两个月数据预估 - 数据导入SQLite
# 输入: 权责近两个月的数据预估.xlsx
# 输出: loan_forecast.db
# ============================================================

import sqlite3
import openpyxl
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(r'E:\岳松个人文件\嘉银工作内容的整理\code\权责自动化处理')
DB_PATH = BASE_DIR / 'loan_forecast.db'
SRC_FILE = Path(r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\01周一周报整理\权责近两个月的数据预估.xlsx')

# ============================================================
# CREATE TABLE 语句
# ============================================================
CREATE_SQL = """
CREATE TABLE IF NOT EXISTS loan_forecast (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    month           TEXT    NOT NULL,          -- 报表月份 YYYY-MM
    loan_type       TEXT    NOT NULL,          -- 贷款类型: 首贷/复贷
    is_repeat       INTEGER NOT NULL,          -- 是否复贷: 0=首贷 1=复贷
    loop_type       TEXT,                      -- 循环类型: 循环贷/非循环贷 (仅复贷有效)
    term_month      INTEGER NOT NULL,          -- 期限(月)
    product_type    TEXT    NOT NULL,          -- 产品类型: 常规/无忧贷/优享贷/放心贷/本金

    -- 进件与漏斗
    app_volume      REAL,                      -- 进件量
    rate_mc         REAL,                      -- 机审通过率
    rate_cf         REAL,                      -- 确认借款率
    rate_post       REAL,                      -- 后置通过率
    rate_risk       REAL,                      -- 风险通过率
    rate_sign       REAL,                      -- 签名放款率

    -- 放款与件均
    loan_term_dist  REAL,                      -- 放款量_期限分布
    loan_cnt        REAL,                      -- 放款笔数
    avg_prin_wan    REAL,                      -- 件均(万印尼盾)
    avg_prin_usd    REAL,                      -- 件均($)

    -- 业绩与坏账
    full_flow_rate  REAL,                      -- 全流程通过率
    t30_rate        REAL,                      -- 全账龄T30
    perf_idr        REAL,                      -- 业绩(万IDR) = 业绩$/件均$/汇率×10000
    perf_usd        REAL,                      -- 业绩$
    bad_debt_usd    REAL,                      -- 坏账$

    -- 衍生指标
    perf_term_wtd   REAL,                      -- 业绩*期限(万IDR)
    wtd_term        REAL,                      -- 加权期限(月)
    annual_bad_rate REAL,                      -- 年化坏账率 = T30×12/期限
    perf_share      REAL                       -- 业绩占比
);
"""

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_month ON loan_forecast(month);
CREATE INDEX IF NOT EXISTS idx_loan_type ON loan_forecast(loan_type);
CREATE INDEX IF NOT EXISTS idx_product ON loan_forecast(product_type);
"""

INSERT_SQL = """
INSERT INTO loan_forecast (
    month, loan_type, is_repeat, loop_type, term_month, product_type,
    app_volume, rate_mc, rate_cf, rate_post, rate_risk, rate_sign,
    loan_term_dist, loan_cnt, avg_prin_wan, avg_prin_usd,
    full_flow_rate, t30_rate, perf_idr, perf_usd, bad_debt_usd,
    perf_term_wtd, wtd_term, annual_bad_rate, perf_share
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

# 列映射 (openpyxl 1-indexed)
COL = {
    'col2': 2, 'col6': 6, 'col8': 8, 'col9': 9, 'col10': 10,
    'col11': 11, 'col12': 12, 'col13': 13, 'col14': 14, 'col15': 15,
    'col16': 16, 'col17': 17, 'col18': 18, 'col19': 19, 'col20': 20,
    'col21': 21, 'col22': 22, 'col23': 23, 'col24': 24, 'col25': 25,
    'col26': 26, 'col27': 27, 'col28': 28
}

def cv(row, col_idx):
    v = wb_data.cell(row, col_idx).value
    if isinstance(v, str): v = None
    return v

def parse_row(row_num):
    col6  = wb_data.cell(row_num, COL['col6']).value
    col2  = wb_data.cell(row_num, COL['col2']).value
    col9  = wb_data.cell(row_num, COL['col9']).value

    # 必须有月份和产品类型
    if not isinstance(col6, datetime) or not col9 or col9 == '合计':
        return None

    # col2 为 None 时(如首贷子行)，向前查找
    if col2 is None:
        for r in range(row_num - 1, 0, -1):
            v = wb_data.cell(r, COL['col2']).value
            if v is not None:
                col2 = v
                break

    month = col6.strftime('%Y-%m')

    # 贷款类型判断
    if col2 in ('循环贷', '非循环贷', '本金加贷'):
        loan_type = '复贷'
        is_repeat = 1
        loop_type = col2 if col2 in ('循环贷', '非循环贷') else None
    else:
        loan_type = '首贷'
        is_repeat = 0
        loop_type = None

    # 排除无数据的本金加贷行
    if col2 == '本金加贷':
        if wb_data.cell(row_num, COL['col10']).value is None and \
           wb_data.cell(row_num, COL['col22']).value is None:
            return None

    term_month    = cv(row_num, COL['col8'])
    product_type  = col9
    app_volume    = cv(row_num, COL['col10'])
    rate_mc       = cv(row_num, COL['col11'])
    rate_cf       = cv(row_num, COL['col12'])
    rate_post     = cv(row_num, COL['col13'])
    rate_risk      = cv(row_num, COL['col14'])
    rate_sign     = cv(row_num, COL['col15'])
    loan_term_dist= cv(row_num, COL['col17'])
    loan_cnt      = cv(row_num, COL['col18'])
    avg_prin_wan  = cv(row_num, COL['col19'])
    avg_prin_usd  = cv(row_num, COL['col20'])
    full_flow_rate= cv(row_num, COL['col16'])
    t30_rate      = cv(row_num, COL['col22'])
    perf_idr      = cv(row_num, COL['col25'])
    perf_usd      = cv(row_num, COL['col23'])
    bad_debt_usd  = cv(row_num, COL['col24'])
    perf_term_wtd = cv(row_num, COL['col25'])
    wtd_term      = cv(row_num, COL['col26'])
    annual_bad    = cv(row_num, COL['col27'])
    perf_share    = cv(row_num, COL['col28'])

    # 处理年化坏账率 #DIV/0! 异常
    if annual_bad == '#DIV/0!': annual_bad = None

    return (
        month, loan_type, is_repeat, loop_type, term_month, product_type,
        app_volume, rate_mc, rate_cf, rate_post, rate_risk, rate_sign,
        loan_term_dist, loan_cnt, avg_prin_wan, avg_prin_usd,
        full_flow_rate, t30_rate, perf_idr, perf_usd, bad_debt_usd,
        perf_term_wtd, wtd_term, annual_bad, perf_share
    )


# ============================================================
# 主逻辑
# ============================================================
wb_data = openpyxl.load_workbook(SRC_FILE, data_only=True)['Sheet1']

# 收集所有数据行
rows_to_insert = []
for r in range(10, wb_data.max_row + 1):
    row_data = parse_row(r)
    if row_data:
        rows_to_insert.append(row_data)

print(f'共解析 {len(rows_to_insert)} 条数据行')

# 建库
conn = sqlite3.connect(str(DB_PATH))
conn.execute("DROP TABLE IF EXISTS loan_forecast")
conn.executescript(CREATE_SQL)
conn.executescript(CREATE_INDEX)

# 插入数据
conn.executemany(INSERT_SQL, rows_to_insert)
conn.commit()

# 验证
cur = conn.execute("""
    SELECT month, loan_type, loop_type, product_type, term_month,
           app_volume, t30_rate, perf_usd, bad_debt_usd
    FROM loan_forecast
    ORDER BY month DESC, loan_type, term_month, product_type
""")
rows = cur.fetchall()

print(f'\n数据库共 {len(rows)} 行\n')
print(f"{'月份':<8} {'贷款类型':<6} {'循环类型':<8} {'产品':<8} {'期限':<4} "
      f"{'进件量':>12} {'T30':>10} {'业绩$':>14} {'坏账$':>12}")
print('-' * 100)
for r in rows:
    month, loan_type, loop_type, prod, term, app, t30, perf, bad = r
    app_s = f'{app:,.0f}' if app else '-'
    t30_s = f'{t30:.2%}' if t30 else '-'
    perf_s = f'${perf:,.0f}' if perf else '-'
    bad_s = f'${bad:,.0f}' if bad else '-'
    print(f'{month:<8} {loan_type:<6} {(loop_type or "-"):<8} {prod:<8} {term or 0:<4} '
          f'{app_s:>12} {t30_s:>10} {perf_s:>14} {bad_s:>12}')

conn.close()
print(f'\n数据库已保存至: {DB_PATH}')
