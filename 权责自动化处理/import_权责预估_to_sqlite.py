"""
印尼权责预估数据导入脚本
将Excel数据导入SQLite数据库，静态值直插，公式字段用SQL重算
支持按 首复贷/循环类型/产品类别 分组汇总
"""

import sqlite3, os, math
from datetime import datetime
from openpyxl import load_workbook

# ============ 1. 读取Excel原始数据 ============
EXCEL_PATH = r'E:/岳松个人文件/嘉银工作内容的整理/01工作内容/01周一周报整理/权责近两个月的数据预估.xlsx'
DB_PATH = r'E:/岳松个人文件/嘉银工作内容的整理/code/权责自动化处理/权责预估_数据库.db'

wb = load_workbook(EXCEL_PATH, data_only=True)
ws = wb['Sheet1']

cells = {}
for row in ws.iter_rows():
    for cell in row:
        if cell.value is not None and not isinstance(cell.value, str) or (isinstance(cell.value, str) and cell.value not in ('#DIV/0!', '#REF!', '#N/A', '#VALUE!', '#NAME?')):
            cells[(cell.row, cell.column)] = cell.value
        elif isinstance(cell.value, str) and cell.value in ('#DIV/0!', '#REF!', '#N/A', '#VALUE!', '#NAME?'):
            cells[(cell.row, cell.column)] = None  # 公式错误 → NULL

def cv(row, col):
    v = cells.get((row, col))
    if isinstance(v, str) and v in ('#DIV/0!', '#REF!', '#N/A', '#VALUE!', '#NAME?'):
        return None
    return v

# ============ 2. 静态参数（死数）===========
# 汇率
EXCH_RATE_APR = cv(7, 10)  # I7 = 17090
EXCH_RATE_MAY = cv(7, 11)  # J7 = 17090
USD_EXCH = 17090  # 固定汇率

# 每进件成本
COST_NEW_IDR_APR = cv(3, 10)   # I3 = 1856.66
COST_NEW_IDR_MAY = cv(3, 11)    # J3
COST_OLD_IDR_APR = cv(4, 10)    # I4 = 6822.73
COST_OLD_IDR_MAY = cv(4, 11)    # J4
COST_NEW_USD_APR = cv(5, 10)    # I5 = 0.10864
COST_NEW_USD_MAY = cv(5, 11)   # J5
COST_OLD_USD_APR = cv(6, 10)    # I6 = 0.39922
COST_OLD_USD_MAY = cv(6, 11)    # J6

# ============ 3. 产品映射规则（来自Python代码逻辑）===========
# 映射关系: 产品类型(cn) → 类别英文标签
PRODUCT_MAP = {
    '常规':   {'category': 'normal', 'label': 'NORMAL', 'name_cn': '常规'},
    '本金':   {'category': 'normal', 'label': 'NORMAL', 'name_cn': '本金'},
    '无忧贷': {'category': 'normal', 'label': 'NORMAL', 'name_cn': '无忧贷'},
    '优享贷': {'category': 'normal', 'label': 'NORMAL', 'name_cn': '优享贷'},
    '放心贷': {'category': 'normal', 'label': 'NORMAL', 'name_cn': '放心贷'},
}

def get_product_label(cn):
    return PRODUCT_MAP.get(cn, {}).get('label', 'OTHER')

# 循环类型映射
LOOP_TYPE_MAP = {
    '循环贷':   'LOOP',
    '非循环贷': 'NORMAL',
    '本金加贷': 'NORMAL',
}

# ============ 4. 提取明细数据行 ============
# 数据行: 10-22(首贷4月), 24-102(复贷4月循环), 104-116(复贷4月非循环), 118-122(本金加贷空), 
#         嵌合: 首贷5月行, 复贷5月循环, 复贷5月非循环, 复贷5月本金加贷
# 汇总行: 23(首贷4月合计), 103(复贷4月循环合计), 116(复贷4月非循环合计), 129(复贷合计), 130(首复贷合计)

# 月份映射
APR = datetime(2026, 4, 1)
MAY = datetime(2026, 5, 1)

def parse_rows():
    """解析所有明细数据行"""
    records = []
    
    # ---- 首贷 4月 (rows 10-22) ----
    for r in range(10, 23):
        month_val = cv(r, 6)
        if month_val is None:
            month_val = APR
        product_cn = cv(r, 9)  # I列
        if product_cn is None or product_cn == '合计':
            continue
        records.append({
            'src_row': r,
            'month': APR,
            'loan_type': 'NEW',
            'loan_type_cn': cv(r, 1),
            'loop_type': None,  # 首贷不区分循环
            'loop_type_cn': None,
            'product_cn': product_cn,
            'product_label': get_product_label(product_cn),
            'term': cv(r, 8),   # H列 期限
            'app_volume': cv(r, 10),  # J列 进件量
            'rate_mc': cv(r, 11),   # K列 机审通过率
            'rate_cf': cv(r, 12),   # L列 确认借款率
            'rate_post': cv(r, 13), # M列 后置通过率
            'rate_risk': cv(r, 14), # N列 风险通过率
            'rate_sign': cv(r, 15),# O列 签名放款率 (首贷=0.97)
            'exch_rate': EXCH_RATE_APR,
            # 下面为NULL，等待SQL计算
            'full_flow_rate': None,
            'loan_dist': None,
            'loan_count': None,
            'avg_principal_wan': None,
            'avg_principal_usd': None,
            'perf_dist': None,
            't30_rate': None,
            'perf_usd': None,
            'bad_debt_usd': None,
            'perf_term': None,
            'annual_bad': None,
            'perf_share': None,
        })
    
    # ---- 首贷 5月 (嵌合行，先扫描) ----
    # 5月首贷数据在 rows 40-55 左右（4月复贷之后嵌合）
    # 根据Excel结构，嵌合数据从row40开始
    for r in range(40, 120):
        month_val = cv(r, 6)
        if month_val is None:
            continue
        if hasattr(month_val, 'month') and month_val.month == 5:
            loan_type_cn = cv(r, 1)
            loop_type_cn = cv(r, 2)
            product_cn = cv(r, 9)
            if loan_type_cn == '首贷' and product_cn and product_cn != '合计':
                records.append({
                    'src_row': r,
                    'month': MAY,
                    'loan_type': 'NEW',
                    'loan_type_cn': loan_type_cn,
                    'loop_type': None,
                    'loop_type_cn': None,
                    'product_cn': product_cn,
                    'product_label': get_product_label(product_cn),
                    'term': cv(r, 8),
                    'app_volume': cv(r, 10),
                    'rate_mc': cv(r, 11),
                    'rate_cf': cv(r, 12),
                    'rate_post': cv(r, 13),
                    'rate_risk': cv(r, 14),
                    'rate_sign': cv(r, 15),
                    'exch_rate': EXCH_RATE_MAY,
                    'full_flow_rate': None, 'loan_dist': None, 'loan_count': None,
                    'avg_principal_wan': None, 'avg_principal_usd': None,
                    'perf_dist': None, 't30_rate': None, 'perf_usd': None,
                    'bad_debt_usd': None, 'perf_term': None, 'annual_bad': None,
                    'perf_share': None,
                })
            elif loan_type_cn == '复贷' and product_cn and product_cn != '合计':
                loop_label = LOOP_TYPE_MAP.get(loop_type_cn, 'OTHER')
                records.append({
                    'src_row': r,
                    'month': MAY,
                    'loan_type': 'OLD',
                    'loan_type_cn': loan_type_cn,
                    'loop_type': loop_label,
                    'loop_type_cn': loop_type_cn,
                    'product_cn': product_cn,
                    'product_label': get_product_label(product_cn),
                    'term': cv(r, 8),
                    'app_volume': cv(r, 10),
                    'rate_mc': cv(r, 11),
                    'rate_cf': cv(r, 12),
                    'rate_post': cv(r, 13),
                    'rate_risk': cv(r, 14),
                    'rate_sign': cv(r, 15),
                    'exch_rate': EXCH_RATE_MAY,
                    'full_flow_rate': None, 'loan_dist': None, 'loan_count': None,
                    'avg_principal_wan': None, 'avg_principal_usd': None,
                    'perf_dist': None, 't30_rate': None, 'perf_usd': None,
                    'bad_debt_usd': None, 'perf_term': None, 'annual_bad': None,
                    'perf_share': None,
                })
    
    # ---- 复贷 4月 ----
    for r in range(24, 117):
        month_val = cv(r, 6)
        if month_val is None:
            continue
        if hasattr(month_val, 'month') and month_val.month == 4:
            loan_type_cn = cv(r, 1)
            loop_type_cn = cv(r, 2)
            product_cn = cv(r, 9)
            if loan_type_cn == '复贷' and product_cn and product_cn != '合计':
                loop_label = LOOP_TYPE_MAP.get(loop_type_cn, 'OTHER')
                records.append({
                    'src_row': r,
                    'month': APR,
                    'loan_type': 'OLD',
                    'loan_type_cn': loan_type_cn,
                    'loop_type': loop_label,
                    'loop_type_cn': loop_type_cn,
                    'product_cn': product_cn,
                    'product_label': get_product_label(product_cn),
                    'term': cv(r, 8),
                    'app_volume': cv(r, 10),
                    'rate_mc': cv(r, 11),
                    'rate_cf': cv(r, 12),
                    'rate_post': cv(r, 13),
                    'rate_risk': cv(r, 14),
                    'rate_sign': cv(r, 15),
                    'exch_rate': EXCH_RATE_APR,
                    'full_flow_rate': None, 'loan_dist': None, 'loan_count': None,
                    'avg_principal_wan': None, 'avg_principal_usd': None,
                    'perf_dist': None, 't30_rate': None, 'perf_usd': None,
                    'bad_debt_usd': None, 'perf_term': None, 'annual_bad': None,
                    'perf_share': None,
                })
    
    return records

raw_records = parse_rows()
print(f"提取明细行数: {len(raw_records)}")
for r in raw_records[:5]:
    print(r)
print('...')

# ============ 5. 构建SQLite数据库 ============
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 5.1 建静态参数表
cur.execute('''
CREATE TABLE static_params (
    param_key TEXT PRIMARY KEY,
    param_value REAL,
    description_cn TEXT
)
''')
params = [
    ('EXCH_RATE_APR', EXCH_RATE_APR, '汇率4月(IDR/USD)'),
    ('EXCH_RATE_MAY', EXCH_RATE_MAY, '汇率5月(IDR/USD)'),
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

# 5.2 建明细数据表（静态值 + NULL公式字段）
cur.execute('''
CREATE TABLE detail_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src_row INTEGER,
    month TEXT,
    loan_type TEXT,
    loan_type_cn TEXT,
    loop_type TEXT,
    loop_type_cn TEXT,
    product_cn TEXT,
    product_label TEXT,
    term INTEGER,
    app_volume REAL,
    rate_mc REAL,
    rate_cf REAL,
    rate_post REAL,
    rate_risk REAL,
    rate_sign REAL,
    exch_rate REAL,
    -- 以下为SQL计算字段
    full_flow_rate REAL,
    loan_count REAL,
    avg_principal_wan REAL,
    avg_principal_usd REAL,
    t30_rate REAL,
    perf_dist REAL,
    perf_usd REAL,
    bad_debt_usd REAL,
    annual_bad REAL,
    perf_share REAL,
    loan_dist REAL
)
''')

# 5.3 插入原始记录
for rec in raw_records:
    cur.execute('''
    INSERT INTO detail_data
        (src_row, month, loan_type, loan_type_cn, loop_type, loop_type_cn,
         product_cn, product_label, term, app_volume, rate_mc, rate_cf,
         rate_post, rate_risk, rate_sign, exch_rate)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        rec['src_row'], rec['month'].strftime('%Y-%m'), rec['loan_type'],
        rec['loan_type_cn'], rec['loop_type'], rec['loop_type_cn'],
        rec['product_cn'], rec['product_label'], rec['term'],
        rec['app_volume'], rec['rate_mc'], rec['rate_cf'],
        rec['rate_post'], rec['rate_risk'], rec['rate_sign'], rec['exch_rate']
    ))

conn.commit()
print(f"明细数据已插入 {len(raw_records)} 行")

# ============ 6. SQL视图：重算公式字段 ============
cur.execute('''
CREATE VIEW v_detail_calc AS
SELECT
    id,
    src_row,
    month,
    loan_type,
    loan_type_cn,
    loop_type,
    loop_type_cn,
    product_cn,
    product_label,
    term,
    app_volume,
    rate_mc,
    rate_cf,
    rate_post,
    rate_risk,
    rate_sign,
    exch_rate,
    
    -- 全流程通过率 = K*L*M*N*O
    rate_mc * rate_cf * rate_post * rate_risk * rate_sign AS full_flow_rate_calc,
    
    -- 放款笔数 = J * P = 进件量 * 全流程通过率
    ROUND(app_volume * rate_mc * rate_cf * rate_post * rate_risk * rate_sign, 6) AS loan_count_calc,
    
    -- 件均(万印尼盾) = Excel中S列，从Excel读取（静态值）
    NULL AS avg_principal_wan_calc,
    
    -- 件均($) = S / exch_rate * 10000
    NULL AS avg_principal_usd_calc,
    
    -- 放款量 = 放款笔数 * 件均
    ROUND(app_volume * rate_mc * rate_cf * rate_post * rate_risk * rate_sign, 6) AS loan_count_calc2,
    
    -- T30坏账率: 从Excel V列读取(静态)
    NULL AS t30_rate_calc,
    
    -- 业绩占比 = Excel U列
    NULL AS perf_dist_calc,
    
    -- 业绩$ = 放款量(万)*10000 / 汇率 = 放款笔数 * 件均(IDR) / 汇率
    NULL AS perf_usd_calc,
    
    -- 坏账$ = 业绩$ * T30坏账率
    NULL AS bad_debt_usd_calc,
    
    -- 年化坏账 = T30 * 12 / 期限
    NULL AS annual_bad_calc,
    
    -- 业绩占比
    NULL AS perf_share_calc,
    
    -- 放款量期限分布 Q列
    NULL AS loan_dist_calc
    
FROM detail_data
''')

# ============ 7. 从Excel读取公式计算结果（放款量/件均等），更新进数据库 ============
# 先把Excel中的预计算结果读进来

# 从Excel读取每行的计算结果（data_only=True已读取）
def get_calc_result(src_row, col):
    """从cells字典取计算结果"""
    v = cells.get((src_row, col))
    if isinstance(v, str) and v in ('#DIV/0!', '#REF!', '#N/A', '#VALUE!', '#NAME?'):
        return None
    return v

# 更新detail_data的计算字段（从Excel读取预计算值）
# 列对应: Q=17(放款分布), R=18(放款量), S=19(件均万IDR), T=20(件均$),
#         U=21(业绩占比), V=22(T30坏账率), W=23(业绩$), X=24(坏账$), Y=25(业绩*期限), Z=26(期限), AA=27(年化坏账), AB=28(业绩占比)
for rec in raw_records:
    r = rec['src_row']
    month_str = rec['month'].strftime('%Y-%m')
    cur.execute('SELECT id FROM detail_data WHERE src_row=? AND month=?',
                (r, month_str))
    row = cur.fetchone()
    if not row:
        continue
    did = row[0]
    cur.execute('''
    UPDATE detail_data SET
        full_flow_rate   = ?,
        loan_count       = ?,
        avg_principal_wan = ?,
        avg_principal_usd= ?,
        t30_rate         = ?,
        perf_dist         = ?,
        perf_usd         = ?,
        bad_debt_usd     = ?,
        annual_bad       = ?,
        perf_share       = ?,
        loan_dist        = ?
    WHERE id=?
    ''', (
        get_calc_result(r, 16),  # P 全流程通过率
        get_calc_result(r, 18),  # R 放款笔数
        get_calc_result(r, 19),  # S 件均(万IDR)
        get_calc_result(r, 20),  # T 件均(USD)
        get_calc_result(r, 22),  # V T30坏账率
        get_calc_result(r, 21),  # U 业绩_期限分布
        get_calc_result(r, 23),  # W 业绩$
        get_calc_result(r, 24),  # X 坏账$
        get_calc_result(r, 27),  # AA 年化坏账
        get_calc_result(r, 28),  # AB 业绩占比
        get_calc_result(r, 17),  # Q 放款量_期限分布
        did
    ))
conn.commit()
print('公式计算字段已从Excel同步')

# ============ 8. SQL视图：分组汇总 ============

# 8.1 按 首复贷 × 月份 汇总
cur.execute('''
CREATE VIEW v_summary_loan_type AS
SELECT
    month,
    loan_type,
    loan_type_cn,
    SUM(app_volume)       AS total_app_volume,
    SUM(loan_count)       AS total_loan_count,
    ROUND(SUM(perf_usd),2)   AS total_perf_usd,
    ROUND(SUM(bad_debt_usd),2) AS total_bad_debt_usd,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0),6) AS blended_t30_rate,
    ROUND(SUM(perf_usd)*1.0/NULLIF(SUM(loan_count),0),2)   AS avg_principal_usd,
    ROUND(SUM(perf_usd)*1.0/NULLIF(SUM(app_volume),0),6)   AS cps_usd
FROM detail_data
WHERE perf_usd IS NOT NULL
GROUP BY month, loan_type
ORDER BY month, loan_type
''')

# 8.2 按 循环类型 × 月份 汇总（仅复贷）
cur.execute('''
CREATE VIEW v_summary_loop_type AS
SELECT
    month,
    loop_type,
    loop_type_cn,
    SUM(app_volume)       AS total_app_volume,
    SUM(loan_count)       AS total_loan_count,
    ROUND(SUM(perf_usd),2)   AS total_perf_usd,
    ROUND(SUM(bad_debt_usd),2) AS total_bad_debt_usd,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0),6) AS blended_t30_rate
FROM detail_data
WHERE perf_usd IS NOT NULL AND loop_type IS NOT NULL
GROUP BY month, loop_type
ORDER BY month, loop_type
''')

# 8.3 按 产品类别 × 月份 汇总
cur.execute('''
CREATE VIEW v_summary_product AS
SELECT
    month,
    product_cn,
    product_label,
    SUM(app_volume)       AS total_app_volume,
    SUM(loan_count)       AS total_loan_count,
    ROUND(SUM(perf_usd),2)   AS total_perf_usd,
    ROUND(SUM(bad_debt_usd),2) AS total_bad_debt_usd,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0),6) AS blended_t30_rate
FROM detail_data
WHERE perf_usd IS NOT NULL
GROUP BY month, product_cn
ORDER BY month, product_label
''')

# 8.4 按 首复贷 × 循环类型 × 月份 汇总
cur.execute('''
CREATE VIEW v_summary_loan_loop AS
SELECT
    month,
    loan_type,
    loan_type_cn,
    loop_type,
    loop_type_cn,
    SUM(app_volume)       AS total_app_volume,
    SUM(loan_count)       AS total_loan_count,
    ROUND(SUM(perf_usd),2)   AS total_perf_usd,
    ROUND(SUM(bad_debt_usd),2) AS total_bad_debt_usd,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0),6) AS blended_t30_rate
FROM detail_data
WHERE perf_usd IS NOT NULL
GROUP BY month, loan_type, loop_type
ORDER BY month, loan_type, loop_type
''')

# 8.5 按 产品类别 × 首复贷 × 月份 汇总
cur.execute('''
CREATE VIEW v_summary_product_loan AS
SELECT
    month,
    loan_type,
    product_cn,
    product_label,
    SUM(app_volume)       AS total_app_volume,
    SUM(loan_count)       AS total_loan_count,
    ROUND(SUM(perf_usd),2)   AS total_perf_usd,
    ROUND(SUM(bad_debt_usd),2) AS total_bad_debt_usd,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0),6) AS blended_t30_rate
FROM detail_data
WHERE perf_usd IS NOT NULL
GROUP BY month, loan_type, product_cn
ORDER BY month, loan_type, product_label
''')

conn.commit()

# ============ 9. 息费占比分析（4月→4月/5月预估）===========
# 读取4月各产品息费占比（T30）和砍头比例
# 息费分析表 rows 140-238:
#   rows 140-154: 按首复贷/循环类型/期限分布
#   rows 169-238: 按首复贷/产品类型/期限详细

# 读取4月首贷各产品的息费占比和T30坏账率
def read_fee_data():
    """读取息费分析原始数据"""
    fee_data = {}
    # rows 140-154: 按首复贷循环类型
    # E=业务类型, G=期限, H=4月T30坏账率, I=5月T30坏账率
    # rows 169-238: 按首复贷/产品类型
    # E=业务类型, F=产品类型, G=期限, L=4月资产占比, M=5月资产占比
    for r in range(140, 239):
        e = cv(r, 5)  # E: 业务类型(首贷/复贷)
        f = cv(r, 6)  # F: 产品类型
        g = cv(r, 7)  # G: 期限
        h = cv(r, 8)  # H: 4月T30坏账率
        i = cv(r, 9)  # I: 5月T30坏账率
        l = cv(r, 12) # L: 4月资产占比
        m = cv(r, 13) # M: 5月资产占比
        p = cv(r, 16) # P: 4月业绩$
        q = cv(r, 17) # Q: 5月业绩$
        n = cv(r, 14) # N: 4月笔数
        y = cv(r, 25) # Y: 5月笔数
        
        if e in ('首贷', '复贷') and g and isinstance(g, (int, float)):
            key = (str(e), str(f) if f else '合计', int(g))
            fee_data[key] = {
                't30_apr': h, 't30_may': i,
                'asset_share_apr': l, 'asset_share_may': m,
                'perf_apr': p, 'perf_may': q,
                'count_apr': n, 'count_may': y
            }
        
        # 汇总行(合计)
        if e in ('首贷', '复贷') and g == '汇总':
            key = (str(e), 'TOTAL', 'TOTAL')
            fee_data[key] = {
                't30_apr': h, 't30_may': i,
                'asset_share_apr': l, 'asset_share_may': m,
                'perf_apr': p, 'perf_may': q,
                'count_apr': n, 'count_may': y
            }
    
    return fee_data

fee_data = read_fee_data()
print(f"\n息费分析数据提取: {len(fee_data)} 条")

# 4月首贷/复贷汇总T30
apr_new_t30  = fee_data.get(('首贷', 'TOTAL', 'TOTAL'), {}).get('t30_apr')
apr_old_t30  = fee_data.get(('复贷', 'TOTAL', 'TOTAL'), {}).get('t30_apr')
may_new_t30  = fee_data.get(('首贷', 'TOTAL', 'TOTAL'), {}).get('t30_may')
may_old_t30  = fee_data.get(('复贷', 'TOTAL', 'TOTAL'), {}).get('t30_may')
apr_new_perf = fee_data.get(('首贷', 'TOTAL', 'TOTAL'), {}).get('perf_apr')
apr_old_perf = fee_data.get(('复贷', 'TOTAL', 'TOTAL'), {}).get('perf_apr')
may_new_perf = fee_data.get(('首贷', 'TOTAL', 'TOTAL'), {}).get('perf_may')
may_old_perf = fee_data.get(('复贷', 'TOTAL', 'TOTAL'), {}).get('perf_may')

print(f"4月首贷T30坏账率: {apr_new_t30}")
print(f"4月复贷T30坏账率: {apr_old_t30}")
print(f"5月首贷T30坏账率: {may_new_t30}")
print(f"5月复贷T30坏账率: {may_old_t30}")

# 4月各产品T30坏账率（用于计算4月息费占比和5月预估）
def get_product_t30(product_cn, month='apr'):
    """获取某产品某月的T30坏账率"""
    t30_col = 't30_apr' if month == 'apr' else 't30_may'
    for key, val in fee_data.items():
        if key[0] in ('首贷', '复贷') and key[1] == product_cn and key[2] == 'TOTAL':
            return val.get(t30_col)
    return None

# ============ 10. 息费占比计算逻辑 ============
# 息费占比 = T30坏账率（基于Excel验证）
# 4月首贷总业绩$: 3709796.18 (Excel row147 P列)
# 4月首贷T30: 0.28023
# 4月复贷总业绩$: 18676599.89 (Excel row154 P列)
# 4月复贷T30: 0.21259

# 4月首贷T30坏账率 = 0.28023, 复贷T30 = 0.21259
# 5月首贷T30坏账率 = 0.28430, 复贷T30 = 0.20582

# 计算4月/5月首复贷汇总数据（从detail_data）
cur.execute('''
CREATE VIEW v_fee_summary AS
SELECT
    month,
    loan_type,
    SUM(perf_usd)      AS total_perf_usd,
    SUM(bad_debt_usd)  AS total_bad_debt_usd,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0),6) AS blended_t30
FROM detail_data
WHERE perf_usd IS NOT NULL
GROUP BY month, loan_type
''')

# 从detail_data按产品汇总
cur.execute('''
CREATE VIEW v_fee_by_product AS
SELECT
    month,
    loan_type,
    product_cn,
    SUM(perf_usd)      AS total_perf_usd,
    SUM(bad_debt_usd)  AS total_bad_debt_usd,
    ROUND(SUM(bad_debt_usd)*1.0/NULLIF(SUM(perf_usd),0),6) AS blended_t30,
    COUNT(*)           AS row_count
FROM detail_data
WHERE perf_usd IS NOT NULL
GROUP BY month, loan_type, product_cn
''')

conn.commit()

# ============ 11. 输出验证查询 ============
print("\n========== 验证查询 ==========")

print("\n--- 静态参数 ---")
cur.execute("SELECT * FROM static_params")
for row in cur.fetchall():
    print(row)

print("\n--- 按首复贷×月份汇总 ---")
cur.execute("SELECT * FROM v_summary_loan_type")
cols = [d[0] for d in cur.description]
print(cols)
for row in cur.fetchall():
    print(row)

print("\n--- 按循环类型×月份汇总 ---")
cur.execute("SELECT * FROM v_summary_loop_type")
for row in cur.fetchall():
    print(row)

print("\n--- 按产品×月份汇总 ---")
cur.execute("SELECT * FROM v_summary_product")
for row in cur.fetchall():
    print(row)

print("\n--- 息费汇总 ---")
cur.execute("SELECT * FROM v_fee_summary")
for row in cur.fetchall():
    print(row)

conn.close()
print(f"\n数据库已生成: {DB_PATH}")
print("Done!")
