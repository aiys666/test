import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)
pd.set_option('display.max_colwidth', 30)

# Read Excel file
df = pd.read_excel(r"D:\Documents\Downloads\评级产品表现-放款月 (14).xlsx", sheet_name='评级产品表现-放款月')

# Forward fill 放款月份
df['放款月份'] = df['放款月份'].ffill()
df['月份'] = df['放款月份'].astype(str).str[:7]

# Get product-level info (总收息_含税 is product parameter, same across months)
print("="*100)
print("各产品 总收息_含税 检查 (跨月一致性):")
print("="*100)
product_rates = df[df['产品'].notna()].groupby('产品')['总收息_含税'].nunique()
inconsistent = product_rates[product_rates > 1]
if len(inconsistent) > 0:
    print(f"警告: 以下产品的总收息_含税在不同月份不一致: {inconsistent.index.tolist()}")
else:
    print("所有产品的总收息_含税在不同月份一致 ✓")

# Verify TR formula: 4t7TR = 总收息_含税 - 4t7本金逾期率 - 4t7息费逾期率_本金分母
print("\n" + "="*100)
print("验证 TR 公式: 4t7TR = 总收息_含税 - 4t7本金 - 4t7息费")
print("="*100)
aug = df[df['月份'] == '2026-08'].copy()
aug = aug[aug['产品'].notna() & aug['4t7本金逾期率'].notna()]
aug['TR_计算'] = aug['总收息_含税'] - aug['4t7本金逾期率'] - aug['4t7息费逾期率_本金分母']
aug['TR_差异'] = aug['4t7TR'] - aug['TR_计算']
print(aug[['产品', '总收息_含税', '4t7本金逾期率', '4t7息费逾期率_本金分母', '4t7TR', 'TR_计算', 'TR_差异']].to_string(index=False))
print(f"\n最大差异: {aug['TR_差异'].abs().max():.6f}")

# Calculate ratios for August (complete data)
print("\n" + "="*100)
print("8月各产品比率分析 (4t7 / 早期指标):")
print("="*100)
aug_ratios = aug[['产品', '放款笔数', '放款金额']].copy()
aug_ratios['4t7本金/1t0'] = aug['4t7本金逾期率'] / aug['1t0本金逾期率'].replace(0, np.nan)
aug_ratios['4t7本金/1t3'] = aug['4t7本金逾期率'] / aug['1t3本金逾期率'].replace(0, np.nan)
aug_ratios['4t7本金/2t0'] = aug['4t7本金逾期率'] / aug['2t0本金逾期率'].replace(0, np.nan)
aug_ratios['4t7息费/1t0'] = aug['4t7息费逾期率_本金分母'] / aug['1t0本金逾期率'].replace(0, np.nan)
aug_ratios['4t7息费/1t3'] = aug['4t7息费逾期率_本金分母'] / aug['1t3本金逾期率'].replace(0, np.nan)
aug_ratios['4t7息费/2t0'] = aug['4t7息费逾期率_本金分母'] / aug['2t0本金逾期率'].replace(0, np.nan)
aug_ratios['4t7TR/2t0'] = aug['4t7TR'] / aug['2t0本金逾期率'].replace(0, np.nan)
print(aug_ratios.to_string(index=False))

# Also check July ratios for stability
print("\n" + "="*100)
print("7月各产品比率分析 (4t7 / 早期指标) - 验证稳定性:")
print("="*100)
jul = df[df['月份'] == '2026-07'].copy()
jul = jul[jul['产品'].notna() & jul['4t7本金逾期率'].notna()]
jul_ratios = jul[['产品', '放款笔数']].copy()
jul_ratios['4t7本金/1t0'] = jul['4t7本金逾期率'] / jul['1t0本金逾期率'].replace(0, np.nan)
jul_ratios['4t7本金/1t3'] = jul['4t7本金逾期率'] / jul['1t3本金逾期率'].replace(0, np.nan)
jul_ratios['4t7本金/2t0'] = jul['4t7本金逾期率'] / jul['2t0本金逾期率'].replace(0, np.nan)
jul_ratios['4t7息费/2t0'] = jul['4t7息费逾期率_本金分母'] / jul['2t0本金逾期率'].replace(0, np.nan)
print(jul_ratios.to_string(index=False))

# Compare August and July ratios for common products
print("\n" + "="*100)
print("8月 vs 7月 比率对比 (4t7本金/2t0):")
print("="*100)
common = set(aug_ratios['产品']) & set(jul_ratios['产品'])
for p in sorted(common):
    a_val = aug_ratios[aug_ratios['产品']==p]['4t7本金/2t0'].values[0]
    j_val = jul_ratios[jul_ratios['产品']==p]['4t7本金/2t0'].values[0]
    print(f"  {p:>22}: 8月={a_val:.4f}, 7月={j_val:.4f}, 差异={a_val-j_val:+.4f}")

# Check June ratios
print("\n" + "="*100)
print("6月各产品比率分析 (4t7本金/2t0) - 进一步验证稳定性:")
print("="*100)
jun = df[df['月份'] == '2026-06'].copy()
jun = jun[jun['产品'].notna() & jun['4t7本金逾期率'].notna()]
jun_ratios = jun[['产品', '放款笔数']].copy()
jun_ratios['4t7本金/2t0'] = jun['4t7本金逾期率'] / jun['2t0本金逾期率'].replace(0, np.nan)
jun_ratios['4t7息费/2t0'] = jun['4t7息费逾期率_本金分母'] / jun['2t0本金逾期率'].replace(0, np.nan)
print(jun_ratios.to_string(index=False))

# Three-month comparison for 4t7本金/2t0
print("\n" + "="*100)
print("6/7/8月 比率对比 (4t7本金/2t0):")
print("="*100)
all_common = set(aug_ratios['产品']) & set(jul_ratios['产品']) & set(jun_ratios['产品'])
for p in sorted(all_common):
    a_val = aug_ratios[aug_ratios['产品']==p]['4t7本金/2t0'].values[0]
    j_val = jul_ratios[jul_ratios['产品']==p]['4t7本金/2t0'].values[0]
    u_val = jun_ratios[jun_ratios['产品']==p]['4t7本金/2t0'].values[0]
    avg_val = np.mean([a_val, j_val, u_val])
    print(f"  {p:>22}: 6月={u_val:.4f}, 7月={j_val:.4f}, 8月={a_val:.4f}, 均值={avg_val:.4f}, 极差={max(a_val,j_val,u_val)-min(a_val,j_val,u_val):.4f}")

# Three-month comparison for 4t7息费/2t0
print("\n" + "="*100)
print("6/7/8月 比率对比 (4t7息费/2t0):")
print("="*100)
aug_jun_common = set(aug_ratios['产品']) & set(jun_ratios['产品'])
for p in sorted(aug_jun_common):
    a_val = aug_ratios[aug_ratios['产品']==p]['4t7息费/2t0'].values[0]
    u_val = jun_ratios[jun_ratios['产品']==p]['4t7息费/2t0'].values[0]
    j_val = jul_ratios[jul_ratios['产品']==p]['4t7息费/2t0'].values[0] if p in jul_ratios['产品'].values else np.nan
    print(f"  {p:>22}: 6月={u_val:.4f}, 7月={j_val:.4f}, 8月={a_val:.4f}")
