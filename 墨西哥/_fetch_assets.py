# -*- coding: utf-8 -*-
"""按放款日分片拉取三张核心表（突破 getQueryResult 单次 10000 行上限），excel/csv 断点续传。

表结构:
  loan.csv      : lid, camera_id, customer_id, loan_cycle, loan_cycle_unit, contract_amount,
                  amount, haircut_amount, interest, fee_amount, state, release_time,
                  finish_time, trade_end_time, double_loan, paid_type
  repayment.csv : camera_id, indexs, state, should_time, fact_time, should_capital, fact_capital,
                  should_interest, fact_interest, should_fine, fact_fine, should_overdue_fee,
                  fact_overdue_fee, subtract_capital, subtract_interest, coupon_amount, is_extends
  detail.csv    : camera_id, rid, fact_time, fact_capital, fact_interest, fact_fine, fact_overdue_fee

断点: _cache/progress.json 记录每张表已完成日期，重复运行自动跳过。
"""
import sys, os, time, json, csv
from datetime import date, timedelta
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_cache')
os.makedirs(CACHE_DIR, exist_ok=True)
PROG = os.path.join(CACHE_DIR, 'progress.json')

TABLES = {
    'loan': {
        'file': 'loan.csv',
        'sql': """
select lid, camera_id, customer_id, loan_cycle, loan_cycle_unit,
       contract_amount, amount, haircut_amount, interest, fee_amount,
       state, release_time, finish_time, trade_end_time, double_loan, paid_type
from ods.s02_loan
where release_time >= timestamp '{d} 00:00:00' and release_time < timestamp '{d2} 00:00:00'
  and state in (1,2)
""",
    },
    'repayment': {
        'file': 'repayment.csv',
        'sql': """
select rp.camera_id, rp.indexs, rp.state, rp.should_time, rp.fact_time,
       rp.should_capital, rp.fact_capital, rp.should_interest, rp.fact_interest,
       rp.should_fine, rp.fact_fine, rp.should_overdue_fee, rp.fact_overdue_fee,
       rp.subtract_capital, rp.subtract_interest, rp.coupon_amount, rp.is_extends
from ods.s02_loan_repayment rp
join ods.s02_loan l on l.camera_id = rp.camera_id
where l.release_time >= timestamp '{d} 00:00:00' and l.release_time < timestamp '{d2} 00:00:00'
  and l.state in (1,2)
""",
    },
    'detail': {
        'file': 'detail.csv',
        'sql': """
select rd.camera_id, rd.rid, rd.fact_time,
       rd.fact_capital, rd.fact_interest, rd.fact_fine, rd.fact_overdue_fee
from ods.s02_loan_repayment_detail rd
join ods.s02_loan l on l.camera_id = rd.camera_id
where l.release_time >= timestamp '{d} 00:00:00' and l.release_time < timestamp '{d2} 00:00:00'
  and l.state in (1,2)
""",
    },
}

def load_prog():
    if os.path.exists(PROG):
        with open(PROG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {k: [] for k in TABLES}

def save_prog(prog):
    with open(PROG, 'w', encoding='utf-8') as f:
        json.dump(prog, f)

def date_range(d0, d1):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)

def main():
    D0 = date(2026, 5, 1)
    D1 = date(2026, 9, 29)
    days = list(date_range(D0, D1))
    prog = load_prog()
    pq = PrestoQuery()
    print("登录:", pq.login())

    for d in days:
        ds = d.isoformat()
        d2s = (d + timedelta(days=1)).isoformat()
        for tname, tcfg in TABLES.items():
            if ds in prog[tname]:
                continue
            path = os.path.join(CACHE_DIR, tcfg['file'])
            df = None
            for attempt in range(3):
                try:
                    df = pq.query(tcfg['sql'].format(d=ds, d2=d2s), wait_sec=1)
                    break
                except Exception as e:
                    print(f"[{ds}] {tname} 第{attempt+1}次网络异常: {e}", flush=True)
                    time.sleep(3 + attempt * 3)
            if isinstance(df, str) or df is None:
                print(f"[{ds}] {tname} 失败，跳过待重试", flush=True)
                continue  # 不标记完成，下次重试
            df.to_csv(path, mode='a', index=False, header=not os.path.exists(path))
            prog[tname].append(ds)
            save_prog(prog)
            print(f"[{ds}] {tname}: {len(df)} 行 累计已完成 {len(prog[tname])}/{len(days)}", flush=True)

    print("=" * 60)
    for tname, tcfg in TABLES.items():
        print(f"{tname}: 完成 {len(prog[tname])}/{len(days)} 天")
    # 输出各表已拉总行数
    for tname, tcfg in TABLES.items():
        path = os.path.join(CACHE_DIR, tcfg['file'])
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                n = sum(1 for _ in f) - 1
            print(f"{tcfg['file']}: {n} 行")

if __name__ == '__main__':
    main()