# -*- coding: utf-8 -*-
"""验证新增字段 + 比例正确性。"""
import os
import pandas as pd

D = r'E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_cache\sqlagg'
total = pd.read_csv(os.path.join(D, 'total.csv')).iloc[0]

print("=== 新字段口径检查 ===")
print(f"fact_cash = {total['fact_cash']:.2f}")

# 相对放款日单日拆分完整性: d0+d1+d2+d3+d7+d14+d21+d28 + 其余(>=3但非7/14/21/28) = fact_cash
rhs = (total['repay_rel_d0'] + total['repay_rel_d1'] + total['repay_rel_d2']
       + total['repay_rel_d3'] + total['repay_rel_d7'] + total['repay_rel_d14']
       + total['repay_rel_d21'] + total['repay_rel_d28'])
print(f"放款后0/1/2/3/7/14/21/28 单日实还合计 = {rhs:.2f} (占 fact_cash {rhs/total['fact_cash']:.4f})")
print(f"其余天数(≥3非7/14/21/28) = {total['fact_cash'] - rhs:.2f}")

# 到期前累计: 应单调递减 pre3>=pre4>=pre5>=pre6>=pre7
print("\n到期前累计实还（应单调递减）:")
for p in ['repay_pre3_cum', 'repay_pre4_cum', 'repay_pre5_cum', 'repay_pre6_cum', 'repay_pre7_cum']:
    print(f"  {p} = {total[p]:.2f}  (占 should_sum {total[p]/total['should_sum']:.4f})")

# 逾期未还单调递减 t0>=t1>=t3>=t7
print("\n逾期未还（应单调递减）:")
for p in ['t0_overdue', 't1_overdue', 't3_overdue', 't7_overdue']:
    print(f"  {p} = {total[p]:.2f}  (占 should_sum {total[p]/total['should_sum']:.4f})")

# dayoff 校验: 放款后 3/7/14/21/28 天 单日 应与主表一致
dayoff = pd.read_csv(os.path.join(D, 'dayoff.csv'))
for b in [3, 7, 14, 21, 28]:
    s = dayoff[dayoff['day_bucket'] == b]['fact_amt'].sum()
    col = f'repay_rel_d{b}'
    print(f"dayoff[bucket={b}]={s:.2f} vs total[{col}]={total[col]:.2f} diff={s-total[col]:.6f}")

# 到期前累计单调性
pre = [total[f'repay_pre{i}_cum'] for i in [3,4,5,6,7]]
print("\n到期前累计单调递减:", all(pre[i] >= pre[i+1] for i in range(len(pre)-1)), pre)
# 逾期单调
ovd = [total[f't{i}_overdue'] for i in [0,1,3,7]]
print("逾期未还单调递减:", all(ovd[i] >= ovd[i+1] for i in range(len(ovd)-1)), ovd)
