# ============================================================
# 权责近两个月数据预估 → ind.ba_loan_forecast INSERT 语句
# 修正版 v3: 正确处理合并单元格向下填充
# 4月区域: 首贷行10-23, 循环贷24-38, 非循环贷39-51
# 5月区域: 首贷行75-88, 循环贷89-103, 非循环贷104-116
# ============================================================

import openpyxl
from datetime import datetime
from collections import defaultdict

SRC = r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\01周一周报整理\权责近两个月的数据预估.xlsx'
OUT = r'E:\岳松个人文件\嘉银工作内容的整理\code\权责自动化处理\INSERT_ba_loan_forecast_v3.sql'

wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb['Sheet1']

# ============================================================
# 1. 预处理：合并单元格填充
#    所有在合并范围内的单元格，都用 top-left 的值
# ============================================================
merged_filled = {}

for mr in ws.merged_cells.ranges:
    top_val = ws.cell(mr.min_row, mr.min_col).value
    for r in range(mr.min_row, mr.max_row + 1):
        for c in range(mr.min_col, mr.max_col + 1):
            merged_filled[(r, c)] = top_val

def gv(row, col):
    """读取单元格值（合并格自动取top-left值）"""
    if (row, col) in merged_filled:
        return merged_filled[(row, col)]
    return ws.cell(row, col).value

# ============================================================
# 2. 产品映射
# ============================================================
PRODUCT_MAP = {
    '常规': 'R',
    '本金': 'M',
    '无忧贷': 'NR',
    '优享贷': 'NF',
    '放心贷': 'NW',
}

def safe_val(v):
    """安全转换，字符串和异常值返回None"""
    if v is None: return None
    if isinstance(v, str): return None
    if v == '#DIV/0!': return None
    return v

# ============================================================
# 3. 解析每一行
# ============================================================
# Excel列布局（行9为表头）：
# A=业务(首贷/复贷)  B=循环类型  C=期限  D=期限  E=产品  F=月份  G=业务  H=期限  I=产品
# J=进件量  K=机审  L=确认  M=后置  N=风险  O=签名  P=全流程
# Q=放款期限分布  R=放款笔数  S=件均万IDR  T=件均$  U=业绩期限分布  V=T30
# W=业绩$  X=坏账$  Y=业绩×期限  Z=期限  AA=年化  AB=业绩占比

def build_row(row_num):
    col_a = gv(row_num, 1)  # A: 首贷 / 复贷
    col_b = gv(row_num, 2)  # B: 循环贷 / 非循环贷 / 本金加贷
    col_e = gv(row_num, 5)  # E: 产品

    # 月份 (F列)
    f_val = gv(row_num, 6)
    if not isinstance(f_val, datetime): return None
    stat_month = f_val.strftime('%Y-%m')

    # 排除：本金加贷行 / 无产品行 / 合计行
    if col_b in ('本金加贷',) or col_e == '合计' or col_e is None:
        return None

    # 排除纯分隔行：C(期限) 和 E(产品) 原生值都为空
    # 用 ws.cell 直接读，不用 gv()（gv会把合并格的值填充进去）
    raw_c = ws.cell(row_num, 3).value  # C列原始
    raw_e = ws.cell(row_num, 5).value  # E列原始
    raw_a = ws.cell(row_num, 1).value  # A列原始：分隔行A=None，数据行A='首贷'/'复贷'
    if raw_c is None and raw_e is None and raw_a is None:
        return None

    # 排除无实际放款数据的子行（常规120在5月无放款，业绩=0）
    contract_amt_raw = safe_val(gv(row_num, 23))  # W列 = 业绩$
    if contract_amt_raw == 0:
        return None

    # grant_strategy / is_reloan2 / loop_type
    if col_a == '首贷':
        grant_strategy = 'NEW'
        is_reloan2     = 'new'    # 三分类: new/loop/normal
        loop_type      = 'N'
    elif col_a == '复贷':
        grant_strategy = 'OLD'
        is_reloan2     = 'loop' if col_b == '循环贷' else 'normal'
        loop_type      = 'Y' if col_b == '循环贷' else 'N'
    else:
        return None

    product_tag = PRODUCT_MAP.get(str(col_e))
    if not product_tag:
        return None

    term_month         = safe_val(gv(row_num, 26))  # Z列 = 期限(月)
    apply_cnt          = safe_val(gv(row_num, 10))  # J列 = 进件量
    before_pass_rate   = safe_val(gv(row_num, 11))  # K列 = 机审通过率
    confirm_rate       = safe_val(gv(row_num, 12))  # L列 = 确认借款率
    after_pass_rate    = safe_val(gv(row_num, 13))  # M列 = 后置通过率
    pass_rate          = safe_val(gv(row_num, 14))  # N列 = 风险通过率
    sign_grant_rate    = safe_val(gv(row_num, 15))  # O列 = 签名放款率
    full_pass_rate     = safe_val(gv(row_num, 16))  # P列 = 全流程通过率
    loan_term_dist     = safe_val(gv(row_num, 17))  # Q列 = 放款期限分布
    loan_cnt           = safe_val(gv(row_num, 18))  # R列 = 放款笔数
    avg_amt_idr_wan    = safe_val(gv(row_num, 19))  # S列 = 件均(万印尼盾)
    avg_amt_usd        = safe_val(gv(row_num, 20))  # T列 = 件均($)
    # U列 = 业绩_期限分布 (备用)
    t30_rate           = safe_val(gv(row_num, 22))  # V列 = 全账龄T30
    contract_amt       = safe_val(gv(row_num, 23))  # W列 = 业绩$
    bad_amt            = safe_val(gv(row_num, 24))  # X列 = 坏账$
    loan_cycle_amount  = safe_val(gv(row_num, 25))  # Y列 = 业绩×期限(万IDR)
    annual_bad_rate    = safe_val(gv(row_num, 27))  # AA列 = 年化坏账率
    ab_orig            = safe_val(gv(row_num, 28))  # AB列 = 业绩占比

    # avg_amt_idr: 件均(万IDR) × 10000 = 件均(IDR)
    avg_amt_idr = round(avg_amt_idr_wan * 10000, 6) if avg_amt_idr_wan else None

    # loan_amt_rate = 业绩占比 (AB列原始值)
    loan_amt_rate = ab_orig

    return {
        'stat_month': stat_month,
        'grant_strategy': grant_strategy,
        'is_reloan2': is_reloan2,
        'loan_cycle': term_month,
        'product_tag': product_tag,
        'apply_cnt': apply_cnt,
        'before_pass_rate': before_pass_rate,
        'confirm_rate': confirm_rate,
        'after_pass_rate': after_pass_rate,
        'pass_rate': pass_rate,
        'sign_grant_rate': sign_grant_rate,
        'full_pass_rate': full_pass_rate,
        'loan_term_dist': loan_term_dist,
        'loan_cnt': loan_cnt,
        'avg_amt_idr': avg_amt_idr,
        'avg_amt_usd': avg_amt_usd,
        'loan_amt_term_dist': None,   # 待计算 (合同额/当月SUM)
        't30_rate': t30_rate,
        'contract_amt': contract_amt,
        'bad_amt': bad_amt,
        'loan_cycle_amount': loan_cycle_amount,
        'loan_cycle_wtd': loan_cycle_amount,
        'annual_bad_rate': annual_bad_rate,
        'loan_amt_rate': loan_amt_rate,
        # 调试信息
        '_row': row_num,
        '_col_a': col_a,
        '_col_b': col_b,
        '_col_e': col_e,
    }

# ============================================================
# 4. 收集所有行
# ============================================================
all_rows = []
for r in list(range(10, 52)) + list(range(75, 117)):
    row_data = build_row(r)
    if row_data:
        all_rows.append(row_data)

print(f'共解析 {len(all_rows)} 行数据')

# ============================================================
# 5. 计算 loan_amt_term_dist = contract_amt / SUM(contract_amt)
#    按 (stat_month, grant_strategy) 分组
# ============================================================
sum_by_key = defaultdict(float)
for row in all_rows:
    key = (row['stat_month'], row['grant_strategy'])
    v = row['contract_amt']
    if v: sum_by_key[key] += v

print('\n月份+策略 SUM(contract_amt):')
for k, s in sorted(sum_by_key.items()):
    print(f'  {k}: ${s:,.2f}')

for row in all_rows:
    key = (row['stat_month'], row['grant_strategy'])
    total = sum_by_key.get(key, 0)
    v = row['contract_amt']
    if total > 0 and v:
        row['loan_amt_term_dist'] = round(v / total, 8)

# ============================================================
# 6. 生成 INSERT SQL
# ============================================================
FIELDS = [
    'stat_month', 'grant_strategy', 'is_reloan2', 'loan_cycle', 'product_tag',
    'apply_cnt', 'before_pass_rate', 'confirm_rate', 'after_pass_rate',
    'pass_rate', 'sign_grant_rate', 'full_pass_rate',
    'loan_term_dist', 'loan_cnt', 'avg_amt_idr', 'avg_amt_usd',
    'loan_amt_term_dist', 't30_rate', 'contract_amt', 'bad_amt',
    'loan_cycle_amount', 'loan_cycle_wtd', 'annual_bad_rate', 'loan_amt_rate',
]

def fmt_sql(v, is_decimal=False):
    if v is None: return 'NULL'
    if isinstance(v, float):
        if is_decimal:
            return str(round(v, 8))
        if abs(v) >= 1e8:
            return str(int(round(v)))
        if abs(v) >= 1:
            return str(round(v, 6))
        return str(round(v, 10))
    if isinstance(v, int):
        return str(v)
    return f"'{v}'"

lines = []
for idx, row in enumerate(all_rows, 1):
    vals = [fmt_sql(row[f], f in ('loan_term_dist', 'loan_amt_term_dist', 'loan_amt_rate')) for f in FIELDS]
    lines.append(
        f"INSERT INTO ind.ba_loan_forecast VALUES (\n"
        f"    {idx},\n"
        f"    {', '.join(vals)}\n"
        f");"
    )

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(lines))

print(f'\n已生成 {len(lines)} 条 INSERT → {OUT}')

# ============================================================
# 7. 预览打印
# ============================================================
print(f'\n{"="*120}')
print(f'{"#":<3} {"月份":<8} {"策略":<5} {"复贷":<4} {"期限":<5} {"产品":<4} {"进件量":>12} {"机审":>8} {"确认":>8} {"T30":>8} {"业绩$":>14} {"坏账$":>12} {"占比":>8}')
print('-' * 120)
for idx, row in enumerate(all_rows, 1):
    m = row['stat_month']
    gs = row['grant_strategy']
    lr = row['is_reloan2']
    lc = row['loan_cycle']
    pt = row['product_tag']
    ac = row['apply_cnt']
    bm = row['before_pass_rate']
    cr = row['confirm_rate']
    t30 = row['t30_rate']
    ca = row['contract_amt']
    ba = row['bad_amt']
    ar = row['loan_amt_rate']

    ac_s  = f'{ac:,.0f}'  if ac  else '-'
    bm_s  = f'{bm:.4f}'   if bm  else '-'
    cr_s  = f'{cr:.4f}'   if cr  else '-'
    t30_s = f'{t30:.4f}'  if t30 else '-'
    ca_s  = f'${ca:,.0f}' if ca  else '-'
    ba_s  = f'${ba:,.0f}' if ba  else '-'
    ar_s  = f'{ar:.4f}'   if ar  else '-'

    print(f'{idx:<3} {m:<8} {gs:<5} {lr:<4} {str(lc or ""):<5} {pt:<4} '
          f'{ac_s:>12} {bm_s:>8} {cr_s:>8} {t30_s:>8} {ca_s:>14} {ba_s:>12} {ar_s:>8}')

# ============================================================
# 8. 汇总验证
# ============================================================
print(f'\n{"="*80}')
print('汇总验证 (按月份×策略):')
summary = defaultdict(lambda: {'cnt':0,'apply':0,'perf':0,'bad':0})
for row in all_rows:
    k = (row['stat_month'], row['grant_strategy'], row['is_reloan2'])
    summary[k]['cnt']   += 1
    summary[k]['apply'] += row['apply_cnt'] or 0
    summary[k]['perf']  += row['contract_amt'] or 0
    summary[k]['bad']   += row['bad_amt'] or 0

for k in sorted(summary.keys()):
    m, gs, lr = k
    s = summary[k]
    t30_s = f"{s['bad']/s['perf']:.4f}" if s['perf'] else '-'
    print(f"  {m} {gs}({lr}) | {s['cnt']}行 | 进件={s['apply']:,.0f} | 业绩=${s['perf']:,.0f} | 坏账=${s['bad']:,.0f} | T30={t30_s}")
