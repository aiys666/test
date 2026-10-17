import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

df = pd.read_excel(r'D:\Documents\Downloads\评级产品表现-放款月2.xlsx', sheet_name='评级产品表现-放款月2')
df = df[df['产品'].notna()].copy()
df['issue_week'] = df['issue_week'].ffill()
df['week'] = df['issue_week'].apply(lambda x: pd.to_datetime(x, errors='coerce'))
df = df[df['week'].notna()].copy()
df['week_str'] = df['week'].dt.strftime('%m-%d')

print('September weeks:')
sep = df[df['week'] >= '2026-09-01']
for w in sorted(sep['week_str'].unique()):
    sub = sep[sep['week_str'] == w]
    n_prod = sub['产品'].nunique()
    has4t7 = sub['4t7本金逾期率'].notna().sum()
    n_loans = sub['放款笔数'].sum()
    print(f'  {w}: products={n_prod}, rows={len(sub)}, has4t7={has4t7}, loans={n_loans}')

print()
print('Sep weekly total loans:', sep['放款笔数'].sum())
print('Sep weekly total amount:', sep['放款金额'].sum())

# Compare with monthly
df_m = pd.read_excel(r'D:\Documents\Downloads\评级产品表现-放款月 (14).xlsx', sheet_name='评级产品表现-放款月')
df_m['放款月份'] = df_m['放款月份'].ffill()
sep_m = df_m[df_m['放款月份'].astype(str).str.startswith('2026-09') & df_m['产品'].notna()]
print('Monthly Sep total loans:', sep_m['放款笔数'].sum())
print('Monthly Sep total amount:', sep_m['放款金额'].sum())

# Check a sample product
print()
p = 'A_07_01_50_00'
print(f'Product {p}:')
print('  Monthly:', sep_m[sep_m['产品']==p][['放款笔数','放款金额','1t0本金逾期率','4t7本金逾期率']].to_dict('records'))
print('  Weekly:')
for w in sorted(sep['week_str'].unique()):
    sub = sep[(sep['week_str']==w) & (sep['产品']==p)]
    if len(sub)>0:
        row = sub.iloc[0]
        print(f'    {w}: loans={int(row["放款笔数"])}, amt={row["放款金额"]:.0f}, 1t0={row["1t0本金逾期率"]:.4f}, 4t7={row["4t7本金逾期率"] if pd.notna(row["4t7本金逾期率"]) else "NaN"}')
