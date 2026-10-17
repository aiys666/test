# ============================================================
# 生成 ind.ba_loan_forecast INSERT SQL
# 数据来源: loan_forecast.db
# 输出: 4月 + 5月 INSERT 语句
# ============================================================

import sqlite3
from pathlib import Path

DB_PATH = Path(r'E:\岳松个人文件\嘉银工作内容的整理\code\权责自动化处理\loan_forecast.db')

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

# 读取全部数据
rows = conn.execute(
    "SELECT * FROM loan_forecast ORDER BY month DESC, loan_type, term_month, product_type"
).fetchall()
conn.close()

# 按月份分别处理，计算派生字段
for month in ('2026-05', '2026-04'):
    month_rows = [dict(r) for r in rows if r['month'] == month]

    # 计算月度 SUM（用于 loan_amt_term_dist 和 loan_amt_rate 的分母）
    sum_term_dist = sum(r['loan_term_dist'] or 0 for r in month_rows)
    sum_perf_usd  = sum(r['perf_usd']        or 0 for r in month_rows)

    print(f"\n-- {'='*60}")
    print(f"-- {month}  共 {len(month_rows)} 行")
    print(f"-- SUM(loan_term_dist)={sum_term_dist:.6f}  SUM(perf_usd)={sum_perf_usd:.2f}")
    print(f"-- {'='*60}\n")

    for i, r in enumerate(month_rows, 1):
        # 字段映射
        stat_month    = r['month']
        grant_strategy = 'NEW' if r['loan_type'] == '首贷' else 'OLD'
        is_reloan2    = 'N' if r['loan_type'] == '首贷' else 'Y'
        loan_cycle    = r['term_month'] or 0
        product_tag   = r['product_type']

        apply_cnt     = int(r['app_volume']) if r['app_volume'] else 'NULL'
        rate_mc       = f"{r['rate_mc']:.4f}" if r['rate_mc'] else 'NULL'
        rate_cf       = f"{r['rate_cf']:.4f}" if r['rate_cf'] else 'NULL'
        rate_post     = f"{r['rate_post']:.4f}" if r['rate_post'] else 'NULL'
        rate_risk     = f"{r['rate_risk']:.4f}" if r['rate_risk'] else 'NULL'
        rate_sign     = f"{r['rate_sign']:.4f}" if r['rate_sign'] else 'NULL'
        full_flow     = f"{r['full_flow_rate']:.8f}" if r['full_flow_rate'] else 'NULL'
        loan_term_dist= f"{r['loan_term_dist']:.6f}" if r['loan_term_dist'] else 'NULL'
        loan_cnt      = int(r['loan_cnt']) if r['loan_cnt'] else 'NULL'
        avg_amt_idr   = f"{r['avg_prin_wan'] * 10000:.2f}" if r['avg_prin_wan'] else 'NULL'
        avg_amt_usd   = f"{r['avg_prin_usd']:.6f}" if r['avg_prin_usd'] else 'NULL'

        # 派生字段
        if r['loan_term_dist'] and sum_term_dist > 0:
            loan_amt_term_dist = f"{r['loan_term_dist'] / sum_term_dist:.6f}"
        else:
            loan_amt_term_dist = 'NULL'

        t30_rate      = f"{r['t30_rate']:.4f}" if r['t30_rate'] else 'NULL'
        contract_amt  = f"{r['perf_usd']:.2f}" if r['perf_usd'] else 'NULL'
        bad_amt       = f"{r['bad_debt_usd']:.2f}" if r['bad_debt_usd'] else 'NULL'
        loan_cycle_amt= f"{r['perf_idr']:.2f}" if r['perf_idr'] else 'NULL'
        loan_cycle_wtd= f"{r['perf_term_wtd']:.2f}" if r['perf_term_wtd'] else 'NULL'
        annual_bad    = f"{r['annual_bad_rate']:.6f}" if r['annual_bad_rate'] and r['annual_bad_rate'] != '#DIV/0!' else 'NULL'

        if r['perf_usd'] and sum_perf_usd > 0:
            loan_amt_rate = f"{r['perf_usd'] / sum_perf_usd:.6f}"
        else:
            loan_amt_rate = 'NULL'

        sql = (
            f"INSERT INTO ind.ba_loan_forecast VALUES ("
            f"{i}, '{stat_month}', '{grant_strategy}', '{is_reloan2}', {loan_cycle}, '{product_tag}', "
            f"{apply_cnt}, {rate_mc}, {rate_cf}, {rate_post}, {rate_risk}, {rate_sign}, "
            f"{full_flow}, {loan_term_dist}, {loan_cnt}, {avg_amt_idr}, {avg_amt_usd}, "
            f"{loan_amt_term_dist}, {t30_rate}, {contract_amt}, {bad_amt}, "
            f"{loan_cycle_amt}, {loan_cycle_wtd}, {annual_bad}, {loan_amt_rate}"
            f");"
        )
        print(sql)
