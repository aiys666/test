import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
pd.set_option('display.width', 300)

df = pd.read_excel(r"d:\Documents\Downloads\评级产品表现-放款月2 (1).xlsx", sheet_name='评级产品表现-放款月2')
df['issue_week'] = df['issue_week'].ffill()
df = df[df['产品'].notna()].copy()
df['week'] = df['issue_week'].apply(lambda x: pd.to_datetime(x, errors='coerce'))
df = df[df['week'].notna()].copy()
df['week_str'] = df['week'].dt.strftime('%m-%d')

# Include 08-31 and all September weeks
target_weeks = ['08-31', '09-07', '09-14', '09-21', '09-28']
sep = df[df['week_str'].isin(target_weeks)]

# Coverage columns mapping (user-confirmed, corrected: 1T3 uses is_t3_window_1)
cov_cols = {
    '1T0': 'is_t0_window_1',
    '1T3': 'is_t3_window_1',
    '2T0': 'is_t0_window_2',
    '3T0': 'is_t0_window_3',
    '4T0': 'is_t0_window_4',
    '4T7': 'is_t7_window_4',
}

print("=== 各周各产品覆盖率(出账笔数/放款笔数) ===")
for w in target_weeks:
    sub = sep[sep['week_str'] == w]
    if len(sub) == 0:
        print(f"\n{w}: 无数据")
        continue
    print(f"\n=== {w} ({len(sub)}个产品) ===")
    for _, row in sub.iterrows():
        p = row['产品']
        term = int(row['平均期限']) if pd.notna(row['平均期限']) else '?'
        loans = int(row['放款笔数'])
        coverages = {}
        for label, col in cov_cols.items():
            if col in row.index and pd.notna(row[col]):
                cov = row[col] / loans if loans > 0 else 0
                coverages[label] = cov  # store numeric
            else:
                coverages[label] = None
        # Find latest indicator with 100% coverage (priority: 4T7>4T0>3T0>2T0>1T3>1T0)
        best = '无'
        for ind in ['4T7', '4T0', '3T0', '2T0', '1T3', '1T0']:
            v = coverages.get(ind)
            if v is not None and v >= 1.0:
                best = ind
                break
        fmt = lambda v: f'{v*100:.0f}%' if v is not None else 'N/A'
        print(f"  {p:>25} {term:>3}天 loans={loans:>5}  1T0={fmt(coverages['1T0']):>5} 1T3={fmt(coverages['1T3']):>5} 2T0={fmt(coverages['2T0']):>5} 3T0={fmt(coverages['3T0']):>5} 4T0={fmt(coverages['4T0']):>5} 4T7={fmt(coverages['4T7']):>5}  →推荐:{best}")
