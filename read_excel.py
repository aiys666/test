import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)
pd.set_option('display.max_colwidth', 30)

# Read Excel file
df = pd.read_excel(r"D:\Documents\Downloads\评级产品表现-放款月 (14).xlsx", sheet_name='评级产品表现-放款月')

# Forward fill 放款月份
df['放款月份'] = df['放款月份'].ffill()

# Print August and September data
print("="*120)
print("9月数据 (放款月份=2026-09-01):")
print("="*120)
sep = df[df['放款月份'] == '2026-09-01 00:00:00']
if sep.empty:
    sep = df[df['放款月份'].astype(str).str.startswith('2026-09')]
for _, row in sep.iterrows():
    product = str(row['产品']) if pd.notna(row['产品']) else '(无产品名)'
    print(f"产品={product:>22} | 笔数={int(row['放款笔数']):>6} | 金额={row['放款金额']:>14.2f} | "
          f"4t7TR={row['4t7TR']:.6f} | 4t7本金={row['4t7本金逾期率']:.6f} | 4t7息费={row['4t7息费逾期率_本金分母']:.6f} | "
          f"1t0={row['1t0本金逾期率']:.6f} | 1t3={row['1t3本金逾期率']:.6f} | 2t0={row['2t0本金逾期率']:.6f} | "
          f"is_t0_w4={int(row['is_t0_window_4'])} is_t3_w4={int(row['is_t3_window_4'])} is_t7_w4={int(row['is_t7_window_4'])}")

print()
print("="*120)
print("8月数据 (放款月份=2026-08-01):")
print("="*120)
aug = df[df['放款月份'].astype(str).str.startswith('2026-08')]
for _, row in aug.iterrows():
    product = str(row['产品']) if pd.notna(row['产品']) else '(无产品名)'
    print(f"产品={product:>22} | 笔数={int(row['放款笔数']):>6} | 金额={row['放款金额']:>14.2f} | "
          f"4t7TR={row['4t7TR']:.6f} | 4t7本金={row['4t7本金逾期率']:.6f} | 4t7息费={row['4t7息费逾期率_本金分母']:.6f} | "
          f"1t0={row['1t0本金逾期率']:.6f} | 1t3={row['1t3本金逾期率']:.6f} | 2t0={row['2t0本金逾期率']:.6f} | "
          f"is_t0_w4={int(row['is_t0_window_4'])} is_t3_w4={int(row['is_t3_window_4'])} is_t7_w4={int(row['is_t7_window_4'])}")
