import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter

# ============================================================
# Step 1: Load and prepare data
# ============================================================
print("Step 1: 加载数据...")
df = pd.read_excel(r"D:\Documents\Downloads\评级产品表现-放款月 (14).xlsx", sheet_name='评级产品表现-放款月')
df['放款月份'] = df['放款月份'].ffill()
df['月份'] = df['放款月份'].astype(str).str[:7]

# ============================================================
# Step 2: Extract August and September data
# ============================================================
print("Step 2: 提取8月和9月数据...")

# August data (complete - all windows reached)
aug = df[df['月份'] == '2026-08'].copy()
aug = aug[aug['产品'].notna()].copy()
# Remove products with very small sample (<=3) for ratio reliability, but keep for reference
aug['可靠'] = aug['放款笔数'] > 3

# September data
sep = df[df['月份'] == '2026-09'].copy()
sep = sep[sep['产品'].notna()].copy()

# ============================================================
# Step 3: Calculate August ratios (4t7 / early metrics)
# ============================================================
print("Step 3: 计算8月比率...")

aug_ratio = aug[['产品', '放款笔数', '放款金额', '可靠']].copy()
aug_ratio['4t7本金'] = aug['4t7本金逾期率']
aug_ratio['4t7息费'] = aug['4t7息费逾期率_本金分母']
aug_ratio['1t0'] = aug['1t0本金逾期率']
aug_ratio['1t3'] = aug['1t3本金逾期率']
aug_ratio['2t0'] = aug['2t0本金逾期率']

# Calculate ratios (handle division by zero)
for base in ['1t0', '1t3', '2t0']:
    aug_ratio[f'4t7本金/{base}'] = np.where(
        aug_ratio[base] > 0,
        aug_ratio['4t7本金'] / aug_ratio[base],
        np.nan
    )
    aug_ratio[f'4t7息费/{base}'] = np.where(
        aug_ratio[base] > 0,
        aug_ratio['4t7息费'] / aug_ratio[base],
        np.nan
    )

# Overall average ratios (for products not in August)
avg_ratio_本金 = {}
avg_ratio_息费 = {}
for base in ['1t0', '1t3', '2t0']:
    reliable = aug_ratio[aug_ratio['可靠']]
    avg_ratio_本金[base] = reliable[f'4t7本金/{base}'].mean()
    avg_ratio_息费[base] = reliable[f'4t7息费/{base}'].mean()

print(f"  8月可靠产品数: {aug_ratio['可靠'].sum()}")
print(f"  全局平均比率 (4t7本金/2t0): {avg_ratio_本金['2t0']:.4f}")
print(f"  全局平均比率 (4t7息费/2t0): {avg_ratio_息费['2t0']:.4f}")

# ============================================================
# Step 4: Estimate September 4t7 for each product
# ============================================================
print("Step 4: 预估9月4t7...")

results = []
for _, sep_row in sep.iterrows():
    product = sep_row['产品']

    # Get September input metrics
    sep_1t0 = sep_row['1t0本金逾期率']
    sep_1t3 = sep_row['1t3本金逾期率']
    sep_2t0 = sep_row['2t0本金逾期率']
    sep_total_rate = sep_row['总收息_含税']

    # Find matching August product
    aug_match = aug_ratio[aug_ratio['产品'] == product]

    if len(aug_match) > 0 and aug_match.iloc[0]['可靠']:
        aug_row = aug_match.iloc[0]
        ratio_source = '8月同类产品'
        r_本金_1t0 = aug_row['4t7本金/1t0']
        r_本金_1t3 = aug_row['4t7本金/1t3']
        r_本金_2t0 = aug_row['4t7本金/2t0']
        r_息费_1t0 = aug_row['4t7息费/1t0']
        r_息费_1t3 = aug_row['4t7息费/1t3']
        r_息费_2t0 = aug_row['4t7息费/2t0']
        aug_loans = aug_row['放款笔数']
    else:
        # Use average ratio
        ratio_source = '全局平均(无8月匹配)'
        r_本金_1t0 = avg_ratio_本金['1t0']
        r_本金_1t3 = avg_ratio_本金['1t3']
        r_本金_2t0 = avg_ratio_本金['2t0']
        r_息费_1t0 = avg_ratio_息费['1t0']
        r_息费_1t3 = avg_ratio_息费['1t3']
        r_息费_2t0 = avg_ratio_息费['2t0']
        aug_loans = 0

    # Three estimates from 1t0, 1t3, 2t0
    est_本金_1t0 = sep_1t0 * r_本金_1t0 if not np.isnan(r_本金_1t0) and sep_1t0 > 0 else np.nan
    est_本金_1t3 = sep_1t3 * r_本金_1t3 if not np.isnan(r_本金_1t3) and sep_1t3 > 0 else np.nan
    est_本金_2t0 = sep_2t0 * r_本金_2t0 if not np.isnan(r_本金_2t0) and sep_2t0 > 0 else np.nan

    est_息费_1t0 = sep_1t0 * r_息费_1t0 if not np.isnan(r_息费_1t0) and sep_1t0 > 0 else np.nan
    est_息费_1t3 = sep_1t3 * r_息费_1t3 if not np.isnan(r_息费_1t3) and sep_1t3 > 0 else np.nan
    est_息费_2t0 = sep_2t0 * r_息费_2t0 if not np.isnan(r_息费_2t0) and sep_2t0 > 0 else np.nan

    # Average of available estimates
    est_本金_vals = [v for v in [est_本金_1t0, est_本金_1t3, est_本金_2t0] if not np.isnan(v)]
    est_息费_vals = [v for v in [est_息费_1t0, est_息费_1t3, est_息费_2t0] if not np.isnan(v)]

    est_本金_avg = np.mean(est_本金_vals) if est_本金_vals else np.nan
    est_息费_avg = np.mean(est_息费_vals) if est_息费_vals else np.nan

    # TR = 总收息_含税 - 本金坏账 - 息费坏账
    est_tr = sep_total_rate - est_本金_avg - est_息费_avg if not np.isnan(est_本金_avg) and not np.isnan(est_息费_avg) else np.nan

    # Also estimate TR from each method
    est_tr_1t0 = sep_total_rate - est_本金_1t0 - est_息费_1t0 if not np.isnan(est_本金_1t0) and not np.isnan(est_息费_1t0) else np.nan
    est_tr_1t3 = sep_total_rate - est_本金_1t3 - est_息费_1t3 if not np.isnan(est_本金_1t3) and not np.isnan(est_息费_1t3) else np.nan
    est_tr_2t0 = sep_total_rate - est_本金_2t0 - est_息费_2t0 if not np.isnan(est_本金_2t0) and not np.isnan(est_息费_2t0) else np.nan

    # Actual partial 4t7 (for comparison)
    actual_4t7本金 = sep_row['4t7本金逾期率']
    actual_4t7息费 = sep_row['4t7息费逾期率_本金分母']
    actual_4t7TR = sep_row['4t7TR']
    is_t7_w4 = sep_row['is_t7_window_4']
    total_loans = sep_row['放款笔数']

    results.append({
        '产品': product,
        '9月放款笔数': total_loans,
        '9月放款金额': sep_row['放款金额'],
        '9月总收息_含税': sep_total_rate,
        # Input metrics
        '9月1t0': sep_1t0,
        '9月1t3': sep_1t3,
        '9月2t0': sep_2t0,
        # August ratios
        '8月比率来源': ratio_source,
        '8月放款笔数': aug_loans,
        '8月4t7本金/1t0': r_本金_1t0,
        '8月4t7本金/1t3': r_本金_1t3,
        '8月4t7本金/2t0': r_本金_2t0,
        '8月4t7息费/1t0': r_息费_1t0,
        '8月4t7息费/1t3': r_息费_1t3,
        '8月4t7息费/2t0': r_息费_2t0,
        # Estimates from 1t0
        '预估4t7本金(基于1t0)': est_本金_1t0,
        '预估4t7息费(基于1t0)': est_息费_1t0,
        '预估4t7TR(基于1t0)': est_tr_1t0,
        # Estimates from 1t3
        '预估4t7本金(基于1t3)': est_本金_1t3,
        '预估4t7息费(基于1t3)': est_息费_1t3,
        '预估4t7TR(基于1t3)': est_tr_1t3,
        # Estimates from 2t0
        '预估4t7本金(基于2t0)': est_本金_2t0,
        '预估4t7息费(基于2t0)': est_息费_2t0,
        '预估4t7TR(基于2t0)': est_tr_2t0,
        # Average estimates
        '预估4t7本金(三法均值)': est_本金_avg,
        '预估4t7息费(三法均值)': est_息费_avg,
        '预估4t7TR(三法均值)': est_tr,
        # Actual partial
        '9月实际4t7本金(部分样本)': actual_4t7本金,
        '9月实际4t7息费(部分样本)': actual_4t7息费,
        '9月实际4t7TR(部分样本)': actual_4t7TR,
        '9月4t7已出账笔数': is_t7_w4,
        '9月4t7出账覆盖率': is_t7_w4 / total_loans if total_loans > 0 else 0,
    })

result_df = pd.DataFrame(results)

# ============================================================
# Step 5: Calculate weighted totals
# ============================================================
print("Step 5: 计算加权汇总...")

# Weight by 放款金额
total_amount = result_df['9月放款金额'].sum()

# Weighted average of estimated metrics
for col in ['预估4t7本金(三法均值)', '预估4t7息费(三法均值)', '预估4t7TR(三法均值)']:
    valid = result_df[result_df[col].notna()]
    weighted = (valid[col] * valid['9月放款金额']).sum() / valid['9月放款金额'].sum()
    print(f"  {col} (金额加权): {weighted:.6f}")

print(f"\n  9月总放款金额: {total_amount:,.2f}")

# ============================================================
# Step 6: Get July and June ratios for stability validation
# ============================================================
print("Step 6: 计算比率稳定性验证...")

# July ratios
jul = df[df['月份'] == '2026-07'].copy()
jul = jul[jul['产品'].notna() & jul['4t7本金逾期率'].notna()].copy()
jul_ratios = jul[['产品', '放款笔数']].copy()
jul_ratios['4t7本金/1t0'] = np.where(jul['1t0本金逾期率'] > 0, jul['4t7本金逾期率'] / jul['1t0本金逾期率'], np.nan)
jul_ratios['4t7本金/1t3'] = np.where(jul['1t3本金逾期率'] > 0, jul['4t7本金逾期率'] / jul['1t3本金逾期率'], np.nan)
jul_ratios['4t7本金/2t0'] = np.where(jul['2t0本金逾期率'] > 0, jul['4t7本金逾期率'] / jul['2t0本金逾期率'], np.nan)
jul_ratios['4t7息费/2t0'] = np.where(jul['2t0本金逾期率'] > 0, jul['4t7息费逾期率_本金分母'] / jul['2t0本金逾期率'], np.nan)

# June ratios
jun = df[df['月份'] == '2026-06'].copy()
jun = jun[jun['产品'].notna() & jun['4t7本金逾期率'].notna()].copy()
jun_ratios = jun[['产品', '放款笔数']].copy()
jun_ratios['4t7本金/1t0'] = np.where(jun['1t0本金逾期率'] > 0, jun['4t7本金逾期率'] / jun['1t0本金逾期率'], np.nan)
jun_ratios['4t7本金/1t3'] = np.where(jun['1t3本金逾期率'] > 0, jun['4t7本金逾期率'] / jun['1t3本金逾期率'], np.nan)
jun_ratios['4t7本金/2t0'] = np.where(jun['2t0本金逾期率'] > 0, jun['4t7本金逾期率'] / jun['2t0本金逾期率'], np.nan)
jun_ratios['4t7息费/2t0'] = np.where(jun['2t0本金逾期率'] > 0, jun['4t7息费逾期率_本金分母'] / jun['2t0本金逾期率'], np.nan)

# Save to Excel
print("\nStep 7: 保存到Excel...")
output_path = r"D:\Documents\Downloads\9月4t7预估详解.xlsx"

# Save result_df to check before Excel creation
print("\n预估结果预览:")
preview_cols = ['产品', '9月放款笔数', '9月1t0', '9月1t3', '9月2t0',
                '预估4t7本金(三法均值)', '预估4t7息费(三法均值)', '预估4t7TR(三法均值)',
                '9月实际4t7本金(部分样本)', '9月实际4t7TR(部分样本)']
print(result_df[preview_cols].to_string(index=False))

# Save the result_df and other data for Excel creation
result_df.to_pickle(r"e:\岳松个人文件\嘉银工作内容的整理\code\est_result.pkl")
aug_ratio.to_pickle(r"e:\岳松个人文件\嘉银工作内容的整理\code\aug_ratio.pkl")
jul_ratios.to_pickle(r"e:\岳松个人文件\嘉银工作内容的整理\code\jul_ratios.pkl")
jun_ratios.to_pickle(r"e:\岳松个人文件\嘉银工作内容的整理\code\jun_ratios.pkl")

print(f"\n中间数据已保存,准备创建Excel...")
