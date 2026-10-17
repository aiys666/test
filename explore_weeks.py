import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
pd.set_option('display.width', 300)
pd.set_option('display.max_columns', None)

df = pd.read_excel(r'D:\Documents\Downloads\评级产品表现-放款月2.xlsx', sheet_name='评级产品表现-放款月2')
df = df[df['产品'].notna()].copy()  # Remove total/blank rows
df['issue_week'] = df['issue_week'].ffill()
df['week'] = pd.to_datetime(df['issue_week'], errors='coerce')
df = df[df['week'].notna()].copy()
df['week_str'] = df['week'].dt.strftime('%m-%d')

weeks = sorted(df['week_str'].unique())
print('All weeks:', weeks)
print()

for w in weeks:
    sub = df[df['week_str'] == w]
    has4t7 = sub['4t7本金逾期率'].notna()
    n_prod = sub['产品'].nunique()
    n_loans = sub['放款笔数'].sum()
    print(f'{w}: rows={len(sub)}, has4t7={has4t7.sum()}, products={n_prod}, loans={n_loans}')

print()
print('=== August weeks with 4t7 ===')
for w in weeks:
    if w < '09-01':
        sub = df[(df['week_str'] == w) & df['4t7本金逾期率'].notna() & df['产品'].notna()]
        print(f'{w}: 4t7_products={len(sub)}, loans={sub["放款笔数"].sum()}')

print()
print('=== September weeks ===')
for w in weeks:
    if w >= '09-01':
        sub = df[df['week_str'] == w]
        has4t7 = sub['4t7本金逾期率'].notna()
        print(f'{w}: rows={len(sub)}, has4t7={has4t7.sum()}, products={sub["产品"].nunique()}, loans={sub["放款笔数"].sum()}')
        # Show products
        for _, row in sub.iterrows():
            p = row['产品']
            if pd.notna(p):
                t = int(row['平均期限']) if pd.notna(row['平均期限']) else '?'
                v4t7 = 'Y' if pd.notna(row['4t7本金逾期率']) else 'N'
                print(f'  {p:>25} term={t} 4t7={v4t7} loans={int(row["放款笔数"])}')
