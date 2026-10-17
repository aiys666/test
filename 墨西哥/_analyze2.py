# -*- coding: utf-8 -*-
"""完整分析：金额分箱 / 期限 / 放款后各天还款 / 到期前累计 / 逾期，含比例。"""
import os
import pandas as pd

D = r'E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_cache\sqlagg'
daily = pd.read_csv(os.path.join(D, 'daily.csv'))
box_amt = pd.read_csv(os.path.join(D, 'box_amt.csv'))
box_cycle = pd.read_csv(os.path.join(D, 'box_cycle.csv'))
dayoff = pd.read_csv(os.path.join(D, 'dayoff.csv'))
total = pd.read_csv(os.path.join(D, 'total.csv')).iloc[0]

AMT_LABEL = {1: '(0,200]', 2: '(200,500]', 3: '(500,1000]', 4: '(1000,2000]',
             5: '(2000,3000]', 6: '(3000,4000]', 7: '(4000,5000]', 8: '5000+'}

def pct(x):
    return f"{x*100:.2f}%"

print("=" * 78)
print("一、金额分箱（提前还款率 / 逾期率 / 回收率）")
print("=" * 78)
ba = box_amt.copy()
ba['分箱'] = ba['amount_bin'].map(AMT_LABEL)
ba['提前还款率'] = ba['repay_pre3_cum'] / ba['should_sum']
ba['T0逾期率'] = ba['t0_overdue'] / ba['should_sum']
ba['T7逾期率'] = ba['t7_overdue'] / ba['should_sum']
ba['本金回收率'] = ba['fact_capital'] / ba['contract_amount']
print(ba[['分箱', 'n_loan', 'contract_amount', '提前还款率', 'T0逾期率', 'T7逾期率', '本金回收率']].assign(
    提前还款率=lambda d: d['提前还款率'].map(pct),
    T0逾期率=lambda d: d['T0逾期率'].map(pct),
    T7逾期率=lambda d: d['T7逾期率'].map(pct),
    本金回收率=lambda d: d['本金回收率'].map(pct)).to_string(index=False))

print()
print("=" * 78)
print("二、期限（提前还款率 / 逾期率 / 回收率）")
print("=" * 78)
bc = box_cycle.copy()
bc['期限'] = bc['loan_cycle_bin'].map(lambda x: f"{int(x)}天" if x != 99 else "其他")
bc['提前还款率'] = bc['repay_pre3_cum'] / bc['should_sum']
bc['T0逾期率'] = bc['t0_overdue'] / bc['should_sum']
bc['T7逾期率'] = bc['t7_overdue'] / bc['should_sum']
bc['本金回收率'] = bc['fact_capital'] / bc['contract_amount']
print(bc[['期限', 'n_loan', 'contract_amount', '提前还款率', 'T0逾期率', 'T7逾期率', '本金回收率']].assign(
    提前还款率=lambda d: d['提前还款率'].map(pct),
    T0逾期率=lambda d: d['T0逾期率'].map(pct),
    T7逾期率=lambda d: d['T7逾期率'].map(pct),
    本金回收率=lambda d: d['本金回收率'].map(pct)).to_string(index=False))

print()
print("=" * 78)
print("三、放款后各天单日实还（全局金额 & 占应还比例）")
print("=" * 78)
rel = {0: '当日', 1: '第1天', 2: '第2天', 3: '第3天', 7: '第7天', 14: '第14天', 21: '第21天', 28: '第28天'}
for d, label in rel.items():
    amt = total[f'repay_rel_d{d}']
    print(f"  放款后{label:>5}: {amt:>15,.2f}  ({pct(amt/total['should_sum'])})")

print()
print("=" * 78)
print("四、到期前累计实还（金额 & 占应还比例）")
print("=" * 78)
for p, label in [('repay_pre3_cum', '≥3天'), ('repay_pre4_cum', '≥4天'), ('repay_pre5_cum', '≥5天'),
                 ('repay_pre6_cum', '≥6天'), ('repay_pre7_cum', '≥7天')]:
    amt = total[p]
    print(f"  到期前{label}: {amt:>15,.2f}  ({pct(amt/total['should_sum'])})")

print()
print("=" * 78)
print("五、逾期未还（金额 & 占应还比例）")
print("=" * 78)
for p, label in [('t0_overdue', 'T0'), ('t1_overdue', 'T1'), ('t3_overdue', 'T3'), ('t7_overdue', 'T7')]:
    amt = total[p]
    print(f"  {label}逾期未还: {amt:>15,.2f}  ({pct(amt/total['should_sum'])})")

print()
print("=" * 78)
print("六、逐月趋势")
print("=" * 78)
daily = daily.copy()
daily['month'] = daily['release_date'].astype(str).str[:7]
dm = daily.groupby('month').agg(n_loan=('n_loan', 'sum'), contract_amount=('contract_amount', 'sum'),
    should_sum=('should_sum', 'sum'), repay_pre3_cum=('repay_pre3_cum', 'sum'),
    t0_overdue=('t0_overdue', 'sum'), t7_overdue=('t7_overdue', 'sum')).reset_index()
dm['提前还款率'] = (dm['repay_pre3_cum'] / dm['should_sum']).map(pct)
dm['T0逾期率'] = (dm['t0_overdue'] / dm['should_sum']).map(pct)
dm['T7逾期率'] = (dm['t7_overdue'] / dm['should_sum']).map(pct)
print(dm[['month', 'n_loan', 'contract_amount', '提前还款率', 'T0逾期率', 'T7逾期率']].to_string(index=False))
