import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

df = pd.read_excel(r'D:\Documents\Downloads\评级产品表现-放款月2.xlsx', sheet_name='评级产品表现-放款月2')

# Find rows where issue_week is not NaN (week header rows)
print('=== Rows with issue_week not null ===')
for i, row in df.iterrows():
    iw = row['issue_week']
    p = row['产品']
    if pd.notna(iw):
        print(f'  row{i}: issue_week={iw}, product={p}')

print()
print(f'Total rows: {len(df)}')

# Check rows 85-155 to see September structure
print()
print('=== Rows 80-155 (raw) ===')
for i in range(80, min(155, len(df))):
    iw = df.iloc[i]['issue_week']
    p = df.iloc[i]['产品']
    loans = df.iloc[i]['放款笔数']
    print(f'  row{i}: iw={iw}, prod={p}, loans={loans}')
