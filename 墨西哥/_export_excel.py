# -*- coding: utf-8 -*-
"""把 _cache/sqlagg 聚合 CSV 导出为 Excel 多 sheet，并为还款/逾期字段加比例列。

比例口径：金额 / should_sum(应还总额)，逐行计算。
sheet：
  每日汇总 / 每日×到期 / 每日×金额分箱 / 每日×期限 / 金额分箱汇总 / 期限分箱汇总 /
  期限×金额 / 放款日相对还款 / 总览
"""
import os
import pandas as pd

D = r'E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_cache\sqlagg'
OUT = r'E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\每日放款资产统计_20260501_20260930_v2.xlsx'

CN = {
    'release_date': '放款日', 'is_due': '是否到期(1已到期)', 'loan_cycle_bin': '期限',
    'amount_bin': '金额分箱', 'day_bucket': '放款后第N天', 'fact_amt': '当日实还',
    'n_loan': '订单数', 'contract_amount': '放款金额(合同)', 'amount': '放款金额(本金)',
    'haircut_amount': '砍头息', 'interest': '应还利息',
    'should_capital': '应还本金', 'should_interest': '应还利息(计划)', 'should_sum': '应还总额',
    'fact_capital': '实还本金', 'fact_interest': '实还利息',
    'subtract_capital': '减免本金', 'subtract_interest': '减免利息', 'coupon_amount': '优惠券',
    'fact_cash': '实还现金(本+息)', 'redu_all': '减免+优惠合计',
    'fact_all': '已还(实还+减免+优惠)', 'unpaid_all': '未还(广义)', 'unpaid_capital': '未还本金',
    'n_due': '已到期订单数', 'n_not_due': '未到期订单数',
    'repay_pre3_cum': '到期前≥3天累计实还', 'repay_pre4_cum': '到期前≥4天累计实还',
    'repay_pre5_cum': '到期前≥5天累计实还', 'repay_pre6_cum': '到期前≥6天累计实还',
    'repay_pre7_cum': '到期前≥7天累计实还',
    'repay_d3': '到期前3天实还', 'repay_d2': '到期前2天实还',
    'repay_d1': '到期前1天实还', 'repay_d0': '到期日实还', 'repay_after_due': '到期后实还',
    'repay_rel_d0': '放款当日实还', 'repay_rel_d1': '放款后1天实还', 'repay_rel_d2': '放款后2天实还',
    'repay_rel_d3': '放款后3天实还', 'repay_rel_d7': '放款后7天实还', 'repay_rel_d14': '放款后14天实还',
    'repay_rel_d21': '放款后21天实还', 'repay_rel_d28': '放款后28天实还', 'repay_rel_d3p': '放款后≥3天累计实还',
    't0_overdue': 'T0逾期未还', 't1_overdue': 'T1逾期未还',
    't3_overdue': 'T3逾期未还', 't7_overdue': 'T7逾期未还',
}

AMT_BIN_LABEL = {1: '(0,200]', 2: '(200,500]', 3: '(500,1000]', 4: '(1000,2000]',
                 5: '(2000,3000]', 6: '(3000,4000]', 7: '(4000,5000]', 8: '5000+'}

# 需要加比例列的字段（还款类 + 逾期类），分母 should_sum
RATE_COLS = [
    'fact_cash', 'fact_capital', 'fact_interest', 'redu_all', 'fact_all', 'unpaid_all', 'unpaid_capital',
    'repay_pre3_cum', 'repay_pre4_cum', 'repay_pre5_cum', 'repay_pre6_cum', 'repay_pre7_cum',
    'repay_d3', 'repay_d2', 'repay_d1', 'repay_d0', 'repay_after_due',
    'repay_rel_d0', 'repay_rel_d1', 'repay_rel_d2', 'repay_rel_d3', 'repay_rel_d7',
    'repay_rel_d14', 'repay_rel_d21', 'repay_rel_d28', 'repay_rel_d3p',
    't0_overdue', 't1_overdue', 't3_overdue', 't7_overdue',
]


def decorate(df):
    # 维度标签
    if 'amount_bin' in df.columns:
        df['金额分箱'] = df['amount_bin'].map(AMT_BIN_LABEL).fillna(df['amount_bin'].astype(str))
    if 'is_due' in df.columns:
        df['是否到期'] = df['is_due'].map({1: '已到期', 0: '未到期'})
    if 'loan_cycle_bin' in df.columns:
        df['期限'] = df['loan_cycle_bin'].map(lambda x: f"{int(x)}天" if x != 99 else "其他")
    # 重命名
    df = df.rename(columns={k: v for k, v in CN.items() if k in df.columns})

    # 比例列（成对：金额列后紧跟占比列）
    new_cols = []
    dims = ['放款日', '是否到期', '金额分箱', '期限', '放款后第N天']
    # 先排维度列
    for c in df.columns:
        if c in dims:
            new_cols.append(c)
    # 其余列：金额 + 占比成对
    has_should = '应还总额' in df.columns
    for c in df.columns:
        if c in dims:
            continue
        new_cols.append(c)
        src = c
        # 找原始英文名判断是否要加比例
        orig = [k for k, v in CN.items() if v == c]
        if orig and orig[0] in RATE_COLS and has_should:
            rate_name = c + '占比'
            df[rate_name] = df[c] / df['应还总额'].replace(0, pd.NA)
            new_cols.append(rate_name)
    df = df[new_cols]
    return df


def main():
    daily = pd.read_csv(os.path.join(D, 'daily.csv'))
    dayoff = pd.read_csv(os.path.join(D, 'dayoff.csv'))
    # dayoff 需要 join daily 拿应还总额做分母
    dayoff = dayoff.merge(daily[['release_date', 'should_sum']], on='release_date', how='left')
    dayoff['fact_amt_rate'] = dayoff['fact_amt'] / dayoff['should_sum'].replace(0, pd.NA)

    sheets = [
        ("每日汇总", daily, None),
        ("每日×到期", pd.read_csv(os.path.join(D, 'daily_due.csv')), None),
        ("每日×金额分箱", pd.read_csv(os.path.join(D, 'daily_amt.csv')), None),
        ("每日×期限", pd.read_csv(os.path.join(D, 'daily_cycle.csv')), None),
        ("金额分箱汇总", pd.read_csv(os.path.join(D, 'box_amt.csv')), None),
        ("期限分箱汇总", pd.read_csv(os.path.join(D, 'box_cycle.csv')), None),
        ("期限×金额", pd.read_csv(os.path.join(D, 'box_cross.csv')), None),
        ("放款日相对还款", dayoff, 'dayoff'),
        ("总览", pd.read_csv(os.path.join(D, 'total.csv')), None),
    ]

    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        for sheet_name, df, kind in sheets:
            if kind == 'dayoff':
                df = df.rename(columns={'release_date': '放款日', 'day_bucket': '放款后第N天',
                                        'fact_amt': '当日实还', 'fact_amt_rate': '占应还比例'})
                df = df[['放款日', '放款后第N天', '当日实还', '占应还比例']]
            else:
                df = decorate(df)
            df.to_excel(w, sheet_name=sheet_name, index=False)
    print("已导出:", OUT)


if __name__ == '__main__':
    main()
