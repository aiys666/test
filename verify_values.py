import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np

# Load data
df_w = pd.read_excel(r"d:\Documents\Downloads\评级产品表现-放款月2 (1).xlsx", sheet_name='评级产品表现-放款月2')
df_w['issue_week'] = df_w['issue_week'].ffill()
df_w = df_w[df_w['产品'].notna()].copy()
df_w['week'] = df_w['issue_week'].apply(lambda x: pd.to_datetime(x, errors='coerce'))
df_w = df_w[df_w['week'].notna()].copy()
df_w['week_str'] = df_w['week'].dt.strftime('%m-%d')

target_weeks = ['08-31', '09-07', '09-14', '09-21', '09-28']
sep_weeks = df_w[df_w['week_str'].isin(target_weeks)].copy()

df_m = pd.read_excel(r"d:\Documents\Downloads\评级产品表现-放款月21.xlsx", sheet_name='评级产品表现-放款月21')
df_m['放款月份'] = df_m['放款月份'].ffill()
df_m['月份'] = df_m['放款月份'].astype(str).str[:7]
aug_m = df_m[(df_m['月份']=='2026-08') & df_m['产品'].notna() & (df_m['放款笔数']>3)].copy()
sep_m = df_m[(df_m['月份']=='2026-09') & df_m['产品'].notna()].copy()
aug_by_product = aug_m.set_index('产品')

cov_cols_map = {
    '1T0': 'is_t0_window_1', '1T3': 'is_t3_window_1', '2T0': 'is_t0_window_2',
    '3T0': 'is_t0_window_3', '4T0': 'is_t0_window_4', '4T7': 'is_t7_window_4',
}
ind_cols = ['1t0本金逾期率','1t3本金逾期率','2t0本金逾期率','3t0本金逾期率','4t0本金逾期率']

print("=== 各周预估结果验证 ===\n")
weekly_results = []

for w in target_weeks:
    wdata = sep_weeks[sep_weeks['week_str']==w].copy().sort_values('产品').reset_index(drop=True)
    if len(wdata)==0: continue

    week_total_amt = wdata['放款金额'].sum()
    week_total_loans = wdata['放款笔数'].sum()

    # Compute estimate per product
    ar_list, as_list, at_list = [], [], []
    for _, srow in wdata.iterrows():
        product = srow['产品']
        loans = int(srow['放款笔数'])
        amt = float(srow['放款金额'])

        # Coverage
        coverages = {}
        for label, col in cov_cols_map.items():
            v = srow[col] if col in srow.index and pd.notna(srow[col]) else 0
            coverages[label] = v/loans if loans>0 else 0

        # Recommendation
        rec = '无'
        for ind in ['4T7','4T0','3T0','2T0','1T3','1T0']:
            if coverages[ind] >= 1.0:
                rec = ind; break

        # 8月比率
        has_aug = product in aug_by_product.index
        if has_aug:
            a = aug_by_product.loc[product]
            aug_4t7_ben = float(a['4t7本金逾期率']) if pd.notna(a['4t7本金逾期率']) else 0
            aug_4t7_xi = float(a['4t7息费逾期率_本金分母']) if pd.notna(a['4t7息费逾期率_本金分母']) else 0
            ratios_ben = {}
            ratios_xi = {}
            for ind in ind_cols:
                v = float(a[ind]) if pd.notna(a[ind]) else 0
                ratios_ben[ind] = aug_4t7_ben/v if v>0 else None
                ratios_xi[ind] = aug_4t7_xi/v if v>0 else None
        else:
            ratios_ben = {ind: None for ind in ind_cols}
            ratios_xi = {ind: None for ind in ind_cols}

        # Estimate
        sep_4t7_ben = float(srow['4t7本金逾期率']) if pd.notna(srow['4t7本金逾期率']) else 0
        sep_4t7_xi = float(srow['4t7息费逾期率_本金分母']) if pd.notna(srow['4t7息费逾期率_本金分母']) else 0
        total_rev = float(srow['总收息_含税']) if pd.notna(srow['总收息_含税']) else 0
        sep_inds = {ind: float(srow[ind]) if pd.notna(srow[ind]) else 0 for ind in ind_cols}

        if rec == '4T7':
            est_ben = sep_4t7_ben; est_xi = sep_4t7_xi
        elif rec == '无':
            # Fallback: 1t0 × 8月比率(本金/1t0)
            r = ratios_ben.get('1t0本金逾期率')
            r_xi = ratios_xi.get('1t0本金逾期率')
            if r is not None:
                est_ben = sep_inds['1t0本金逾期率'] * r
            else:
                est_ben = 0
            if r_xi is not None:
                est_xi = sep_inds['1t0本金逾期率'] * r_xi
            else:
                est_xi = 0
        else:
            # Map rec to indicator column
            ind_map = {'4T0':'4t0本金逾期率','3T0':'3t0本金逾期率','2T0':'2t0本金逾期率','1T3':'1t3本金逾期率','1T0':'1t0本金逾期率'}
            ind_name = ind_map[rec]
            r = ratios_ben.get(ind_name)
            r_xi = ratios_xi.get(ind_name)
            if r is not None:
                est_ben = sep_inds[ind_name] * r
            else:
                est_ben = 0
            if r_xi is not None:
                est_xi = sep_inds[ind_name] * r_xi
            else:
                est_xi = 0

        est_tr = total_rev - est_ben - est_xi
        ar_list.append((amt, est_ben, est_xi, est_tr, product, rec))

    # Weekly weighted
    wk_ar = sum(a*b for a,b,_,_,_,_ in ar_list) / week_total_amt
    wk_as = sum(a*c for a,_,c,_,_,_ in ar_list) / week_total_amt
    wk_at = sum(a*d for a,_,_,d,_,_ in ar_list) / week_total_amt

    print(f"--- {w} --- 总笔数={week_total_loans}, 总金额={week_total_amt:,.0f}")
    print(f"  加权4t7本金={wk_ar*100:.2f}%  加权4t7息费={wk_as*100:.2f}%  加权4t7TR={wk_at*100:.2f}%")
    # Show a few products
    for amt, ben, xi, tr, prod, rec in ar_list[:3]:
        print(f"    {prod:>25} 推荐={rec:>3} 本金={ben*100:.2f}% 息费={xi*100:.2f}% TR={tr*100:.2f}%")
    if len(ar_list)>3:
        print(f"    ... ({len(ar_list)-3}个更多产品)")

    weekly_results.append((w, week_total_amt, wk_ar, wk_as, wk_at))

# Monthly aggregation
print("\n=== 月度聚合 ===")
total_amt_all = sum(w[1] for w in weekly_results)
m_ar = sum(w[1]*w[2] for w in weekly_results) / total_amt_all
m_as = sum(w[1]*w[3] for w in weekly_results) / total_amt_all
m_at = sum(w[1]*w[4] for w in weekly_results) / total_amt_all
print(f"  月聚合4t7本金={m_ar*100:.2f}%  息费={m_as*100:.2f}%  TR={m_at*100:.2f}%")

# Direct monthly
print("\n=== 直接月度(9月月度文件) ===")
total_sep = sep_m['放款金额'].sum()
d_ar = (sep_m['放款金额']*sep_m['4t7本金逾期率']).sum()/total_sep
d_as = (sep_m['放款金额']*sep_m['4t7息费逾期率_本金分母']).sum()/total_sep
d_at = (sep_m['放款金额']*sep_m['4t7TR']).sum()/total_sep
print(f"  直接月度4t7本金={d_ar*100:.2f}%  息费={d_as*100:.2f}%  TR={d_at*100:.2f}%")

print(f"\n=== 差额(周聚合-月直接) ===")
print(f"  本金差额={(m_ar-d_ar)*100:.2f}pp  息费差额={(m_as-d_as)*100:.2f}pp  TR差额={(m_at-d_at)*100:.2f}pp")
