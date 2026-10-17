# -*- coding: utf-8 -*-
"""每日放款资产状态统计（2026-05-01 起逐日）
口径对齐《01墨西哥风险宽表新口径.sql》：
  - 本金基准 = contract_amount（合同本金）；7天产品 amount+haircut=contract，应还本金=contract
  - 应还 = Σshould_capital + Σshould_interest（repayment 表聚合到订单）
  - 实还 = Σfact_capital + Σfact_interest（detail 流水聚合到订单）
  - 到期日 due_date = max(should_time)（对齐宽表 t2.max(should_time)）
  - 提前还款分箱(相对到期日 day_to_due = due_date - fact_date)：
      到期前≥3天已累计(pre3_cum: day_to_due>=3) / 到期前第3天(=3)/第2天(=2)/第1天(=1)/当天(=0)/逾期后(<0)
  - 逾期累计实还窗(相对到期日)：t0(≤due)/t1(≤due+1)/t3(≤due+3)/t7(≤due+7)
  - 逾期未还金额 = max(应还本息 - 窗内实还本息, 0)
  - 金额分箱 amount_type 同宽表：(0,200](200,500](500,1000](1000,2000](2000,3000](3000,4000](4000,5000] 5000+
  - 放款日相对还款桶 day_offset = fact_date - release_date：0=放款当日,1=次日,2=第三日,...
输出: _output/每日放款资产统计.xlsx
"""
import sys, os
import pandas as pd
import numpy as np
from datetime import date

sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_cache')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_output')
os.makedirs(OUT, exist_ok=True)

OBS = pd.Timestamp(2026, 9, 30)  # 观察日 = 今天

def read_csv(name):
    path = os.path.join(CACHE, name)
    df = pd.read_csv(path, dtype=str)
    print(f"{name}: {len(df)} 行", flush=True)
    return df

def amount_type(x):
    if x <= 200: return 1
    if x <= 500: return 2
    if x <= 1000: return 3
    if x <= 2000: return 4
    if x <= 3000: return 5
    if x <= 4000: return 6
    if x <= 5000: return 7
    return 8

def main():
    loan = read_csv('loan.csv')
    rep = read_csv('repayment.csv')
    det = read_csv('detail.csv')

    # ── 数值化 ──
    for c in ['contract_amount','amount','haircut_amount','interest','fee_amount']:
        loan[c] = pd.to_numeric(loan[c], errors='coerce').fillna(0.0)
    for c in ['should_capital','fact_capital','should_interest','fact_interest',
              'should_fine','fact_fine','should_overdue_fee','fact_overdue_fee',
              'subtract_capital','subtract_interest','coupon_amount']:
        rep[c] = pd.to_numeric(rep[c], errors='coerce').fillna(0.0)
    for c in ['fact_capital','fact_interest','fact_fine','fact_overdue_fee']:
        det[c] = pd.to_numeric(det[c], errors='coerce').fillna(0.0)

    loan['release_dt'] = pd.to_datetime(loan['release_time'], errors='coerce')
    loan['trade_end_dt'] = pd.to_datetime(loan['trade_end_time'], errors='coerce')
    loan['loan_cycle'] = pd.to_numeric(loan['loan_cycle'], errors='coerce').fillna(0).astype(int)
    loan['release_date'] = loan['release_dt'].dt.normalize()

    rep['should_dt'] = pd.to_datetime(rep['should_time'], errors='coerce')
    det['fact_dt'] = pd.to_datetime(det['fact_time'], errors='coerce')
    det['fact_date'] = det['fact_dt'].dt.normalize()

    # ── 订单级应还 ──
    should_ord = rep.groupby('camera_id').agg(
        should_capital=('should_capital','sum'),
        should_interest=('should_interest','sum'),
        should_fine=('should_fine','sum'),
        due_date=('should_dt','max'),  # 对齐宽表 max(should_time)
        n_inst=('indexs','count'),
    ).reset_index()
    should_ord['should_sum'] = should_ord['should_capital'] + should_ord['should_interest']

    # ── 订单级实还 ──
    det['fact_sum'] = det['fact_capital'] + det['fact_interest']
    fact_ord = det.groupby('camera_id').agg(
        fact_capital=('fact_capital','sum'),
        fact_interest=('fact_interest','sum'),
        fact_sum=('fact_sum','sum'),
    ).reset_index()

    # ── 合并订单维度 ──
    base = loan.merge(should_ord, on='camera_id', how='left')
    base = base.merge(fact_ord, on='camera_id', how='left')
    for c in ['should_capital','should_interest','should_fine','should_sum','n_inst',
              'fact_capital','fact_interest','fact_sum']:
        base[c] = base[c].fillna(0.0)

    base['unpaid_capital'] = base['should_capital'] - base['fact_capital']
    base['unpaid_sum'] = base['should_sum'] - base['fact_sum']
    # 到期状态（以 max(should_time) 为到期日）
    base['is_due'] = base['due_date'] <= OBS
    base['amount_type'] = base['contract_amount'].apply(amount_type)

    # ── 验证等式 ──
    base['check_should_cap'] = base['contract_amount'] - base['should_capital']
    base['check_bal'] = base['contract_amount'] - (base['fact_capital'] + base['unpaid_capital'])

    # ── 明细挂到期日 & 放款日，算相对天数 ──
    det = det.merge(loan[['camera_id','release_date']], on='camera_id', how='left')
    det = det.merge(should_ord[['camera_id','due_date']], on='camera_id', how='left')
    det['day_offset'] = (det['fact_date'] - det['release_date']).dt.days
    det['day_to_due'] = (det['due_date'] - det['fact_date']).dt.days
    det = det.dropna(subset=['day_offset','day_to_due'])
    det['day_offset'] = det['day_offset'].astype(int)
    det['day_to_due'] = det['day_to_due'].astype(int)

    # ── 到期日相对还款分箱 ──
    def due_bin(d):
        if d >= 3: return 'pre3_cum'  # 到期前≥3天已累计
        if d == 2: return 'd2'
        if d == 1: return 'd1'
        if d == 0: return 'd0'
        return 'after_due'
    det['due_bin'] = det['day_to_due'].apply(due_bin)
    # 单日桶（到期前第3天）
    det['d3'] = (det['day_to_due'] == 3).astype(int) * det['fact_sum']
    pivot = det.pivot_table(index='camera_id', columns='due_bin', values='fact_sum',
                            aggfunc='sum', fill_value=0.0)
    d3 = det.groupby('camera_id')['d3'].sum().rename('repay_d3')
    base = base.merge(pivot, on='camera_id', how='left')
    base = base.merge(d3, on='camera_id', how='left')
    for c in ['repay_pre3_cum','repay_d2','repay_d1','repay_d0','repay_after_due','repay_d3']:
        base[c] = base[c].fillna(0.0)

    # ── 逾期累计实还窗 t0/t1/t3/t7 ──
    for name, n in [('t0',0), ('t1',1), ('t3',3), ('t7',7)]:
        win = det[det['fact_date'] <= det['due_date'] + pd.Timedelta(days=n)]
        wg = win.groupby('camera_id')['fact_sum'].sum().rename(f'{name}_fact')
        base = base.merge(wg, on='camera_id', how='left')
        base[f'{name}_fact'] = base[f'{name}_fact'].fillna(0.0)
        base[f'{name}_overdue'] = (base['should_sum'] - base[f'{name}_fact']).clip(lower=0)

    # ── 放款日相对还款桶（day_offset 累计分布） ──
    day_pivot = det.pivot_table(index='camera_id', columns='day_offset', values='fact_sum',
                                aggfunc='sum', fill_value=0.0)
    day_pivot.columns = [f'day{int(c)}' for c in day_pivot.columns]

    # 保存订单级 & 逐日矩阵
    base.to_pickle(os.path.join(OUT, 'order_level.pkl'))
    day_pivot.to_pickle(os.path.join(OUT, 'day_pivot.pkl'))
    print("订单级:", len(base), "笔；逐日矩阵:", day_pivot.shape, flush=True)

    # ================= 汇总输出 =================
    seg_cols = ['n_loan','contract_amount','amount','haircut_amount','interest',
                'should_capital','should_sum','fact_capital','fact_interest','fact_sum',
                'unpaid_capital','unpaid_sum','n_due','n_not_due',
                'repay_pre3_cum','repay_d3','repay_d2','repay_d1','repay_d0','repay_after_due',
                't0_overdue','t1_overdue','t3_overdue','t7_overdue','check_bal']

    def seg(g):
        s = {'n_loan': len(g),
             'contract_amount': g['contract_amount'].sum(),
             'amount': g['amount'].sum(),
             'haircut_amount': g['haircut_amount'].sum(),
             'interest': g['interest'].sum(),
             'should_capital': g['should_capital'].sum(),
             'should_sum': g['should_sum'].sum(),
             'fact_capital': g['fact_capital'].sum(),
             'fact_interest': g['fact_interest'].sum(),
             'fact_sum': g['fact_sum'].sum(),
             'unpaid_capital': g['unpaid_capital'].sum(),
             'unpaid_sum': g['unpaid_sum'].sum(),
             'n_due': int(g['is_due'].sum()),
             'n_not_due': int((~g['is_due']).sum()),
             'repay_pre3_cum': g['repay_pre3_cum'].sum(),
             'repay_d3': g['repay_d3'].sum(),
             'repay_d2': g['repay_d2'].sum(),
             'repay_d1': g['repay_d1'].sum(),
             'repay_d0': g['repay_d0'].sum(),
             'repay_after_due': g['repay_after_due'].sum(),
             't0_overdue': g['t0_overdue'].sum(),
             't1_overdue': g['t1_overdue'].sum(),
             't3_overdue': g['t3_overdue'].sum(),
             't7_overdue': g['t7_overdue'].sum(),
             'check_bal': g['check_bal'].sum(),
             }
        denom = s['should_sum'] if s['should_sum'] else 0.0
        s['prepay_rate_amt'] = s['repay_pre3_cum'] / denom if denom else 0.0
        s['t0_overdue_rate'] = s['t0_overdue'] / denom if denom else 0.0
        s['t3_overdue_rate'] = s['t3_overdue'] / denom if denom else 0.0
        s['t7_overdue_rate'] = s['t7_overdue'] / denom if denom else 0.0
        return pd.Series(s)

    # 1. 每日汇总
    day_df = base.groupby('release_date').apply(seg).reset_index()
    day_df['release_date'] = day_df['release_date'].dt.strftime('%Y-%m-%d')

    # 2. 每日×金额分箱
    day_amt = base.groupby(['release_date','amount_type']).apply(seg).reset_index()
    day_amt['release_date'] = day_amt['release_date'].dt.strftime('%Y-%m-%d')

    # 3. 每日×期限
    day_cycle = base.groupby(['release_date','loan_cycle']).apply(seg).reset_index()
    day_cycle['release_date'] = day_cycle['release_date'].dt.strftime('%Y-%m-%d')

    # 4. 金额分箱汇总 / 5. 期限分箱汇总 / 6. 期限x金额
    box_amt = base.groupby('amount_type').apply(seg).reset_index()
    box_cycle = base.groupby('loan_cycle').apply(seg).reset_index()
    box_cross = base.groupby(['loan_cycle','amount_type']).apply(seg).reset_index()

    # 7. 放款日相对还款（day_offset 桶 × 放款日）
    dp = day_pivot.copy()
    dp['release_date'] = base.set_index('camera_id').loc[dp.index, 'release_date'].values
    dayoff = dp.groupby('release_date').sum().reset_index()
    dayoff['release_date'] = dayoff['release_date'].dt.strftime('%Y-%m-%d')
    # 桶归并: day0..day15, 16+
    keep = [f'day{i}' for i in range(0,16) if f'day{i}' in dayoff.columns]
    overflow = [c for c in dayoff.columns if c.startswith('day') and c not in keep]
    if overflow:
        dayoff['day16plus'] = dayoff[overflow].sum(axis=1)
    dayoff = dayoff[['release_date'] + keep + (['day16plus'] if overflow else [])]

    xlsx = os.path.join(OUT, '每日放款资产统计.xlsx')
    with pd.ExcelWriter(xlsx, engine='openpyxl') as xw:
        day_df.to_excel(xw, sheet_name='每日汇总', index=False)
        day_amt.to_excel(xw, sheet_name='每日x金额分箱', index=False)
        day_cycle.to_excel(xw, sheet_name='每日x期限', index=False)
        box_amt.to_excel(xw, sheet_name='金额分箱汇总', index=False)
        box_cycle.to_excel(xw, sheet_name='期限分箱汇总', index=False)
        box_cross.to_excel(xw, sheet_name='期限x金额汇总', index=False)
        dayoff.to_excel(xw, sheet_name='放款日相对还款', index=False)
    print("已输出:", xlsx, flush=True)

    # ── 快速验证输出 ──
    print("\n=== 全局验证 ===", flush=True)
    tot = base.agg(
        contract=('contract_amount','sum'),
        should_cap=('should_capital','sum'),
        should_sum=('should_sum','sum'),
        fact_cap=('fact_capital','sum'),
        fact_sum=('fact_sum','sum'),
        unpaid_cap=('unpaid_capital','sum'),
        unpaid_sum=('unpaid_sum','sum'),
    )
    print(tot.to_string(), flush=True)
    print("contract - should_cap 缺口:", tot['contract'] - tot['should_cap'], flush=True)
    print("contract - (fact_cap+unpaid_cap):", tot['contract'] - (tot['fact_cap']+tot['unpaid_cap']), flush=True)
    print("\n每日样例(末10行):", flush=True)
    print(day_df[['release_date','n_loan','contract_amount','fact_capital','unpaid_capital','check_bal','t7_overdue']].tail(10).to_string(index=False), flush=True)

if __name__ == '__main__':
    main()