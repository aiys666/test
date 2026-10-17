# -*- coding: utf-8 -*-
"""验证 _sql_agg 产出数据的口径等式。"""
import os
import pandas as pd

D = r'E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_cache\sqlagg'
total = pd.read_csv(os.path.join(D, 'total.csv')).iloc[0]

print("=== 全局 total ===")
print(total.to_dict())

print("\n=== 1. 本金等式: contract_amount = fact_capital + subtract_capital + unpaid_capital ===")
lhs = total['contract_amount']
rhs = total['fact_capital'] + total['subtract_capital'] + total['unpaid_capital']
print(f"左={lhs:.2f} 右={rhs:.2f} diff={lhs-rhs:.6f}")

print("\n=== 2. 广义等式: should_sum = fact_all + unpaid_all ===")
lhs = total['should_sum']
rhs = total['fact_all'] + total['unpaid_all']
print(f"左={lhs:.2f} 右={rhs:.2f} diff={lhs-rhs:.6f}")

print("\n=== 3. 相对到期日时点拆分: fact_cash = pre3+d3+d2+d1+d0+after ===")
lhs = total['fact_cash']
rhs = (total['repay_pre3_cum'] + total['repay_d3'] + total['repay_d2']
       + total['repay_d1'] + total['repay_d0'] + total['repay_after_due'])
print(f"左={lhs:.2f} 右={rhs:.2f} diff={lhs-rhs:.6f}")

print("\n=== 4. 相对放款日时点拆分: fact_cash = rel_d0+d1+d2+d3p ===")
rhs = (total['repay_rel_d0'] + total['repay_rel_d1']
       + total['repay_rel_d2'] + total['repay_rel_d3p'])
print(f"左={lhs:.2f} 右={rhs:.2f} diff={lhs-rhs:.6f}")

print("\n=== 5. 分箱汇总 vs total ===")
for name in ['box_amt', 'box_cycle']:
    df = pd.read_csv(os.path.join(D, f'{name}.csv'))
    for col in ['n_loan', 'contract_amount', 'should_sum', 'fact_all', 'unpaid_all']:
        s = df[col].sum()
        t = total[col]
        print(f"{name}.{col}: {s:.2f} vs {t:.2f} diff={s-t:.6f}")

print("\n=== 6. daily 汇总 vs total ===")
daily = pd.read_csv(os.path.join(D, 'daily.csv'))
for col in ['n_loan', 'contract_amount', 'should_sum', 'fact_all', 'unpaid_all']:
    s = daily[col].sum()
    t = total[col]
    print(f"daily.{col}: {s:.2f} vs {t:.2f} diff={s-t:.6f}")

print("\n=== 7. dayoff 汇总 vs fact_cash ===")
dayoff = pd.read_csv(os.path.join(D, 'dayoff.csv'))
s = dayoff['fact_amt'].sum()
print(f"dayoff.fact_amt={s:.2f} vs fact_cash={total['fact_cash']:.2f} diff={s-total['fact_cash']:.6f}")
