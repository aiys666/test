import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
pd.set_option('display.width', 300)

df = pd.read_excel(r'D:\Documents\Downloads\评级产品表现-放款月2.xlsx', sheet_name='评级产品表现-放款月2')
print('All columns:')
for c in df.columns:
    print(f'  {c}')
print()

# Check for window/coverage columns
window_cols = [c for c in df.columns if 'window' in c.lower() or 'is_t' in c.lower() or '出账' in c or '笔数' in c]
print('Window/coverage columns:', window_cols)
print()

# ffill issue_week, filter
df['issue_week'] = df['issue_week'].ffill()
df = df[df['产品'].notna()].copy()
df['week'] = df['issue_week'].apply(lambda x: pd.to_datetime(x, errors='coerce'))
df = df[df['week'].notna()].copy()
df['week_str'] = df['week'].dt.strftime('%m-%d')

# Check September weeks - indicator availability
indicators = ['1t0本金逾期率', '1t3本金逾期率', '2t0本金逾期率', '3t0本金逾期率', '4t0本金逾期率']
sep = df[df['week'] >= '2026-09-01']

for w in sorted(sep['week_str'].unique()):
    sub = sep[sep['week_str'] == w]
    print(f'\n=== {w} ({len(sub)}个产品) ===')
    for ind in indicators:
        non_null = sub[ind].notna().sum()
        non_zero = (sub[ind].notna() & (sub[ind] != 0)).sum()
        print(f'  {ind}: 有值={non_null}/{len(sub)}, 非零={non_zero}')
    # Check window columns if they exist
    for wc in window_cols:
        if wc != '放款笔数':
            vals = sub[wc].dropna()
            if len(vals) > 0:
                print(f'  {wc}: 非空={len(vals)}, 样本值={vals.iloc[:3].tolist()}')
