"""
印尼权责预估数据导入脚本 v2（列索引修正版）
将Excel数据导入SQLite数据库，静态值直插，公式字段用SQL重算
支持按 首复贷/循环类型/产品类别 分组汇总

列索引修正（openpyxl 1-indexed）:
Excel I=col9, J=col10, K=col11, L=col12...
"""

import sqlite3, os, math
from datetime import datetime
from openpyxl import load_workbook

EXCEL_PATH = r'E:/岳松个人文件/嘉银工作内容的整理/01工作内容/01周一周报整理/权责近两个月的数据预估.xlsx'
DB_PATH = r'E:/岳松个人文件/嘉银工作内容的整理/code/权责自动化处理/权责预估_数据库_v2.db'

wb = load_workbook(EXCEL_PATH, data_only=True)
ws = wb['Sheet1']

cells = {}
for row in ws.iter_rows():
    for cell in row:
        if cell.value is not None:
            v = cell.value
            if isinstance(v, str) and v in ('#DIV/0!','#REF!','#N/A','#VALUE!','#NAME?'):
                cells[(cell.row, cell.column)] = None
            else:
                cells[(cell.row, cell.column)] = v

def cv(row, col):
    v = cells.get((row, col))
    if isinstance(v, str) and v in ('#DIV/0!','#REF!','#N/A','#VALUE!','#NAME?'):
        return None
    return v

# ============ 静态参数（列索引已修正：I=9, J=10, K=11...）===========
EXCH_RATE_APR = cv(7, 9)   # I7 = 17090
EXCH_RATE_MAY = cv(7, 10)  # J7 = 17090
COST_NEW_IDR_APR = cv(3, 9)   # I3 = 1856.66
COST_NEW_IDR_MAY = cv(3, 10)  # J3 = 2011.00
COST_OLD_IDR_APR = cv(4, 9)   # I4
COST_OLD_IDR_MAY = cv(4, 10)  # J4
COST_NEW_USD_APR = cv(5, 9)   # I5
COST_NEW_USD_MAY = cv(5, 10)  # J5
COST_OLD_USD_APR = cv(6, 9)   # I6
COST_OLD_USD_MAY = cv(6, 10)  # J6

print(f"汇率: 4月={EXCH_RATE_APR}, 5月={EXCH_RATE_MAY}")
print(f"首贷每进件成本IDR: 4月={COST_NEW_IDR_APR}, 5月={COST_NEW_IDR_MAY}")
print(f"复贷每进件成本IDR: 4月={COST_OLD_IDR_APR}, 5月={COST_OLD_IDR_MAY}")

# ============ 产品映射规则 ============
# 常规/本金/无忧贷/优享贷/放心贷 → NORMAL
PRODUCT_MAP = {
    '常规':   {'category': 'normal', 'label': 'NORMAL'},
    '本金':   {'category': 'normal', 'label': 'NORMAL'},
    '无忧贷': {'category': 'normal', 'label': 'NORMAL'},
    '优享贷': {'category': 'normal', 'label': 'NORMAL'},
    '放心贷': {'category': 'normal', 'label': 'NORMAL'},
}
LOOP_MAP = {
    '循环贷':   'LOOP',
    '非循环贷': 'NORMAL',
    '本金加贷': 'NORMAL',
}
APR = datetime(2026, 4, 1)
MAY = datetime(2026, 5, 1)

def get_product_label(cn):
    return PRODUCT_MAP.get(cn, {}).get('label', 'OTHER')

# ============ 解析明细数据行 ============
# 列索引: A=1 B=2 C=3 D=4 E=5 F=6 G=7 H=8 I=9 J=10 K=11 L=12 M=13 N=14 O=15 P=16 Q=17 R=18 S=19 T=20 U=21 V=22 W=23 X=24 Y=25 Z=26 AA=27 AB=28
def parse_detail_rows():
    """解析所有有进件量(J=10)或计算结果的数据行"""
    records = []

    def add_record(r, month, loan_type, loop_type, product_cn, term_col=8):
        if product_cn is None or product_cn == '合计':
            return
        records.append({
            'src_row': r,
            'month': month,
            'loan_type': loan_type,
            'loop_type': loop_type,
            'product_cn': product_cn,
            'product_label': get_product_label(product_cn),
            'term': cv(r, 8),      # H列 期限
            'app_volume': cv(r, 10),  # J列 进件量
            'rate_mc': cv(r, 11),     # K列 机审通过率
            'rate_cf': cv(r, 12),     # L列 确认借款率
            'rate_post': cv(r, 13),   # M列 后置通过率
            'rate_risk': cv(r, 14),   # N列 风险通过率
            'rate_sign': cv(r, 15),   # O列 签名放款率
            'full_flow': cv(r, 16),   # P列 全流程通过率
            'exch_rate': EXCH_RATE_APR if month == APR else EXCH_RATE_MAY,
            # 公式计算字段（从Excel读取）
            'loan_dist': cv(r, 17),   # Q列 放款量_期限分布
            'loan_count': cv(r, 18),  # R列 放款笔数
            'avg_prin_wan': cv(r, 19),  # S列 件均(万IDR)
            'avg_prin_usd': cv(r, 20),  # T列 件均(USD)
            'perf_dist': cv(r, 21),   # U列 业绩_期限分布
            't30_rate': cv(r, 22),    # V列 T30坏账率
            'perf_usd': cv(r, 23),    # W列 业绩$
            'bad_debt_usd': cv(r, 24),# X列 坏账$
            'perf_term': cv(r, 25),   # Y列 业绩*期限
            'term_z': cv(r, 26),      # Z列 期限(同H)
            'annual_bad': cv(r, 27), # AA列 年化坏账
            'perf_share': cv(r, 28),  # AB列 业绩占比
        })

    # ---- 首贷 4月 rows 10-22 ----
    for r in range(10, 23):
        month_val = cv(r, 6)
        if month_val is None: continue
        product_cn = cv(r, 9)
        add_record(r, APR, 'NEW', None, product_cn)

    # ---- 复贷 4月 rows 24-116 ----
    for r in range(24, 117):
        month_val = cv(r, 6)
        if month_val is None: continue
        if hasattr(month_val, 'month') and month_val.month == 4:
            loan_type_cn = cv(r, 1)
            loop_type_cn = cv(r, 2)
            product_cn = cv(r, 9)
            if loan_type_cn == '复贷' and product_cn and product_cn != '合计':
                loop_label = LOOP_MAP.get(loop_type_cn, None)
                add_record(r, APR, 'OLD', loop_label, product_cn)

    # ---- 5月数据 rows 40-130 ----
    for r in range(40, 131):
        month_val = cv(r, 6)
        if month_val is None: continue
        if hasattr(month_val, 'month') and month_val.month == 5:
            loan_type_cn = cv(r, 1)
            loop_type_cn = cv(r, 2)
            product_cn = cv(r, 9)
            if loan_type_cn == '首贷' and product_cn and product_cn != '合计':
                add_record(r, MAY, 'NEW', None, product_cn)
            elif loan_type_cn == '复贷' and product_cn and product_cn != '合计':
                loop_label = LOOP_MAP.get(loop_type_cn, None)
                add_record(r, MAY, 'OLD', loop_label, product_cn)

    return records

records = parse_detail_rows()
print(f"\n提取明细行数: {len(records)}")

# ============ 构建SQLite数据库 ============
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 静态参数表
cur.execute('''
CREATE TABLE static_params (
    param_key TEXT PRIMARY KEY,
    param_value REAL,
    description_cn TEXT
)
''')
params = [
    ('EXCH_RATE_APR',  EXCH_RATE_APR,  '汇率4月(IDR/USD)'),
    ('EXCH_RATE_MAY',  EXCH_RATE_MAY,  '汇率5月(IDR/USD)'),
    ('COST_NEW_IDR_APR', COST_NEW_IDR_APR, '首贷每进件成本IDR4月'),
    ('COST_NEW_IDR_MAY', COST_NEW_IDR_MAY, '首贷每进件成本IDR5月'),
    ('COST_OLD_IDR_APR', COST_OLD_IDR_APR, '复贷每进件成本IDR4月'),
    ('COST_OLD_IDR_MAY', COST_OLD_IDR_MAY, '复贷每进件成本IDR5月'),
    ('COST_NEW_USD_APR', COST_NEW_USD_APR, '首贷每进件成本USD4月'),
    ('COST_NEW_USD_MAY', COST_NEW_USD_MAY, '首贷每进件成本USD5月'),
    ('COST_OLD_USD_APR', COST_OLD_USD_APR, '复贷每进件成本USD4月'),
    ('COST_OLD_USD_MAY', COST_OLD_USD_MAY, '复贷每进件成本USD5月'),
]
cur.executemany('INSERT INTO static_params VALUES (?,?,?)', params)

# 明细数据表（静态+公式字段均从Excel读取）
cur.execute('''
CREATE TABLE detail_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    src_row         INTEGER,
    month           TEXT,
    loan_type       TEXT,
    loop_type       TEXT,
    product_cn      TEXT,
    product_label   TEXT,
    term            INTEGER,
    app_volume      REAL,
    rate_mc         REAL,
    rate_cf         REAL,
    rate_post       REAL,
    rate_risk       REAL,
    rate_sign       REAL,
    full_flow       REAL,
    exch_rate       REAL,
    loan_dist       REAL,
    loan_count      REAL,
    avg_prin_wan    REAL,
    avg_prin_usd    REAL,
    perf_dist       REAL,
    t30_rate        REAL,
    perf_usd        REAL,
    bad_debt_usd    REAL,
    annual_bad      REAL,
    perf_share      REAL
)
''')

for rec in records:
    cur.execute('''
    INSERT INTO detail_data
        (src_row, month, loan_type, loop_type, product_cn, product_label,
         term, app_volume, rate_mc, rate_cf, rate_post, rate_risk, rate_sign,
         full_flow, exch_rate, loan_dist, loan_count, avg_prin_wan, avg_prin_usd,
         perf_dist, t30_rate, perf_usd, bad_debt_usd, annual_bad, perf_share)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        rec['src_row'], rec['month'].strftime('%Y-%m'), rec['loan_type'],
        rec['loop_type'], rec['product_cn'], rec['product_label'],
        rec['term'], rec['app_volume'], rec['rate_mc'], rec['rate_cf'],
        rec['rate_post'], rec['rate_risk'], rec['rate_sign'],
        rec['full_flow'], rec['exch_rate'],
        rec['loan_dist'], rec['loan_count'], rec['avg_prin_wan'], rec['avg_prin_usd'],
        rec['perf_dist'], rec['t30_rate'], rec['perf_usd'], rec['bad_debt_usd'],
        rec['annual_bad'], rec['perf_share']
    ))
conn.commit()
print(f"明细数据已插入 {len(records)} 行")

# ============ SQL视图：重算公式字段 ============

# 全流程通过率 = K*L*M*N*O
cur.execute('''
CREATE VIEW v_calc_full_flow AS
SELECT id, src_row, month, loan_type, loop_type,
    app_volume, rate_mc, rate_cf, rate_post, rate_risk, rate_sign, exch_rate,
    ROUND(rate_mc*rate_cf*rate_post*rate_risk*rate_sign, 8) AS full_flow_calc,
    ROUND(app_volume*rate_mc*rate_cf*rate_post*rate_risk*rate_sign, 4) AS loan_count_calc
FROM detail_data
WHERE app_volume IS NOT NULL
''')

# 放款量 = 放款笔数 * 件均(万IDR)
cur.execute('''
CREATE VIEW v_calc_loan_amt AS
SELECT id, src_row, month, loan_type,
    loan_count, avg_prin_wan,
    ROUND(loan_count * avg_prin_wan * 10000, 2) AS loan_amt_idr_calc,
    ROUND(loan_count * avg_prin_usd, 2)         AS loan_amt_usd_calc
FROM detail_data
WHERE loan_count IS NOT NULL
''')

# 业绩$ = 放款量 / 汇率 = loan_count * avg_prin_wan * 10000 / exch_rate
cur.execute('''
CREATE VIEW v_calc_perf AS
SELECT id, src_row, month, loan_type,
    loan_count, avg_prin_wan, exch_rate,
    ROUND(loan_count * avg_prin_wan * 10000.0 / exch_rate, 2) AS perf_usd_calc,
    ROUND(loan_count * avg_prin_wan * 10000.0 / exch_rate * t30_rate, 2) AS bad_debt_usd_calc
FROM detail_data
WHERE loan_count IS NOT NULL AND exch_rate IS NOT NULL AND exch_rate != 0
''')

# 年化坏账 = T30_rate * 12 / 期限
cur.execute('''
CREATE VIEW v_calc_annual_bad AS
SELECT id, src_row, t30_rate, term,
    ROUND(t30_rate * 12.0 / term, 6) AS annual_bad_calc
FROM detail_data
WHERE t30_rate IS NOT NULL AND term > 0
''')

conn.commit()

# ============ 分组汇总视图 ============

# V1: 首复贷 x 月份
cur.execute('''
CREATE VIEW v_sum_loan_type AS
SELECT
    month,
    loan_type,
    SUM(app_volume)           AS total_app,
    SUM(loan_count)          AS total_loans,
    ROUND(SUM(perf_usd),2)   AS total_perf,
    ROUND(SUM(bad_debt_usd),2) AS total_bad,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0), 6) AS blended_t30,
    ROUND(SUM(perf_usd)*1.0/NULLIF(SUM(loan_count),0), 2)   AS avg_prin_usd,
    ROUND(SUM(perf_usd)*1.0/NULLIF(SUM(app_volume),0), 6)   AS cps_usd
FROM detail_data WHERE perf_usd IS NOT NULL
GROUP BY month, loan_type
ORDER BY month, loan_type
''')

# V2: 循环类型 x 月份（仅复贷）
cur.execute('''
CREATE VIEW v_sum_loop_type AS
SELECT
    month,
    loop_type,
    SUM(app_volume)         AS total_app,
    SUM(loan_count)         AS total_loans,
    ROUND(SUM(perf_usd),2) AS total_perf,
    ROUND(SUM(bad_debt_usd),2) AS total_bad,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0), 6) AS blended_t30
FROM detail_data WHERE perf_usd IS NOT NULL AND loop_type IS NOT NULL
GROUP BY month, loop_type
ORDER BY month, loop_type
''')

# V3: 产品类别 x 月份
cur.execute('''
CREATE VIEW v_sum_product AS
SELECT
    month,
    product_cn,
    product_label,
    SUM(app_volume)         AS total_app,
    SUM(loan_count)         AS total_loans,
    ROUND(SUM(perf_usd),2) AS total_perf,
    ROUND(SUM(bad_debt_usd),2) AS total_bad,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0), 6) AS blended_t30
FROM detail_data WHERE perf_usd IS NOT NULL
GROUP BY month, product_cn
ORDER BY month, product_label
''')

# V4: 首复贷 x 循环类型 x 月份
cur.execute('''
CREATE VIEW v_sum_loan_loop AS
SELECT
    month, loan_type, loop_type,
    SUM(app_volume)         AS total_app,
    SUM(loan_count)         AS total_loans,
    ROUND(SUM(perf_usd),2) AS total_perf,
    ROUND(SUM(bad_debt_usd),2) AS total_bad,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0), 6) AS blended_t30
FROM detail_data WHERE perf_usd IS NOT NULL
GROUP BY month, loan_type, loop_type
ORDER BY month, loan_type, loop_type
''')

# V5: 首复贷 x 产品类别 x 月份
cur.execute('''
CREATE VIEW v_sum_loan_product AS
SELECT
    month, loan_type, product_cn, product_label,
    SUM(app_volume)         AS total_app,
    SUM(loan_count)         AS total_loans,
    ROUND(SUM(perf_usd),2) AS total_perf,
    ROUND(SUM(bad_debt_usd),2) AS total_bad,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0), 6) AS blended_t30
FROM detail_data WHERE perf_usd IS NOT NULL
GROUP BY month, loan_type, product_cn
ORDER BY month, loan_type, product_label
''')

# V6: 全部维度交叉
cur.execute('''
CREATE VIEW v_sum_all AS
SELECT
    month, loan_type, loop_type, product_cn, product_label, term,
    SUM(app_volume)         AS total_app,
    SUM(loan_count)         AS total_loans,
    ROUND(SUM(perf_usd),2) AS total_perf,
    ROUND(SUM(bad_debt_usd),2) AS total_bad,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0), 6) AS blended_t30
FROM detail_data WHERE perf_usd IS NOT NULL
GROUP BY month, loan_type, loop_type, product_cn, term
ORDER BY month, loan_type, loop_type, product_label, term
''')

conn.commit()

# ============ 息费占比分析（4月→4月/5月预估）===========
# 息费分析表 rows 140-238
# H=8(4月T30), I=9(5月T30), L=12(4月资产占比), M=13(5月资产占比)
# P=16(4月业绩), Q=17(5月业绩), N=14(4月笔数), Y=25(5月笔数)
# 按 业务类型(首/复) x 产品类型 x 期限 汇总

def read_fee_rows():
    """读取息费分析原始数据"""
    fee_rows = []
    for r in range(140, 239):
        e = cv(r, 5)   # E: 首贷/复贷
        f = cv(r, 6)   # F: 产品类型
        g = cv(r, 7)   # G: 期限
        h = cv(r, 8)   # H: 4月T30坏账率
        i = cv(r, 9)   # I: 5月T30坏账率
        l = cv(r, 12)  # L: 4月资产占比
        m = cv(r, 13)  # M: 5月资产占比
        p = cv(r, 16)  # P: 4月业绩$
        q = cv(r, 17)  # Q: 5月业绩$
        n = cv(r, 14)  # N: 4月笔数
        y = cv(r, 25)  # Y: 5月笔数
        if e in ('首贷', '复贷'):
            fee_rows.append({
                'row': r, 'loan_type': 'NEW' if e == '首贷' else 'OLD',
                'product_cn': str(f) if f else 'TOTAL',
                'term': int(g) if isinstance(g, (int,float)) else g,
                't30_apr': h, 't30_may': i,
                'asset_apr': l, 'asset_may': m,
                'perf_apr': p, 'perf_may': q,
                'count_apr': n, 'count_may': y
            })
    return fee_rows

fee_rows = read_fee_rows()
print(f"\n息费分析数据: {len(fee_rows)} 行")

# 汇总4月/5月首复贷T30坏账率
apr_new = [f for f in fee_rows if f['loan_type']=='NEW' and f['term']=='汇总']
apr_old = [f for f in fee_rows if f['loan_type']=='OLD' and f['term']=='汇总']
may_new = [f for f in fee_rows if f['loan_type']=='NEW' and f['term']=='汇总']
may_old = [f for f in fee_rows if f['loan_type']=='OLD' and f['term']=='汇总']

print(f"4月首贷T30: {apr_new[0]['t30_apr'] if apr_new else 'N/A'}")
print(f"4月复贷T30: {apr_old[0]['t30_apr'] if apr_old else 'N/A'}")
print(f"5月首贷T30: {may_new[0]['t30_may'] if may_new else 'N/A'}")
print(f"5月复贷T30: {may_old[0]['t30_may'] if may_old else 'N/A'}")

# 插入息费分析表
cur.execute('''
CREATE TABLE fee_analysis (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    src_row     INTEGER,
    month       TEXT,
    loan_type   TEXT,
    product_cn  TEXT,
    term        TEXT,
    t30_rate    REAL,
    asset_ratio REAL,
    perf_usd    REAL,
    loan_count  REAL
)
''')

for f in fee_rows:
    if f['term'] == '汇总':
        cur.execute('''INSERT INTO fee_analysis (src_row, month, loan_type, product_cn, term,
            t30_rate, asset_ratio, perf_usd, loan_count)
            VALUES (?,?,?,?,?,?,?,?,?)''',
            (f['row'], '2026-04', f['loan_type'], f['product_cn'], f['term'],
             f['t30_apr'], f['asset_apr'], f['perf_apr'], f['count_apr']))
        cur.execute('''INSERT INTO fee_analysis (src_row, month, loan_type, product_cn, term,
            t30_rate, asset_ratio, perf_usd, loan_count)
            VALUES (?,?,?,?,?,?,?,?,?)''',
            (f['row'], '2026-05', f['loan_type'], f['product_cn'], f['term'],
             f['t30_may'], f['asset_may'], f['perf_may'], f['count_may']))
conn.commit()

# 4月各产品息费占比（T30坏账率）
cur.execute('''
CREATE VIEW v_fee_product AS
SELECT
    month, loan_type, product_cn,
    ROUND(SUM(perf_usd)*1.0/NULLIF(SUM(perf_usd*NULLIF(t30_rate/t30_rate,0)),0),6) AS avg_t30,
    SUM(perf_usd) AS total_perf,
    SUM(perf_usd*t30_rate) AS total_bad
FROM fee_analysis
WHERE perf_usd IS NOT NULL AND t30_rate IS NOT NULL
GROUP BY month, loan_type, product_cn
''')

# ============ 输出验证查询 ============
print("\n========== 验证查询 ==========\n")

print("=== 静态参数 ===")
cur.execute("SELECT * FROM static_params")
for row in cur.fetchall():
    print(f"  {row}")

print("\n=== V1: 首复贷x月份汇总 ===")
print(f"{'月份':<8} {'类型':<6} {'进件量':>12} {'放款笔数':>12} {'业绩USD':>14} {'坏账USD':>14} {'综合T30':>10} {'件均USD':>10} {'CPS(USD)':>12}")
print("-"*100)
cur.execute("SELECT * FROM v_sum_loan_type")
for row in cur.fetchall():
    print(f"  {row[0]:<8} {row[1]:<6} {row[2]:>12.1f} {row[3]:>12.1f} {row[4]:>14.2f} {row[5]:>14.2f} {row[6]:>10.6f} {row[7]:>10.2f} {row[8]:>12.6f}")

print("\n=== V2: 循环类型x月份汇总 ===")
cur.execute("SELECT * FROM v_sum_loop_type")
for row in cur.fetchall():
    print(f"  {row}")

print("\n=== V3: 产品类别x月份汇总 ===")
cur.execute("SELECT * FROM v_sum_product")
for row in cur.fetchall():
    print(f"  {row}")

print("\n=== V4: 首复贷x循环类型x月份 ===")
cur.execute("SELECT * FROM v_sum_loan_loop")
for row in cur.fetchall():
    print(f"  {row}")

print("\n=== 息费分析(4月汇总) ===")
cur.execute("SELECT * FROM fee_analysis WHERE month='2026-04' AND term='汇总'")
for row in cur.fetchall():
    print(f"  {row}")

conn.close()
print(f"\n[OK] 数据库已生成: {DB_PATH}")
