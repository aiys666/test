import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

# Check weekly file columns
df_w = pd.read_excel(r"d:\Documents\Downloads\评级产品表现-放款月2 (1).xlsx", sheet_name='评级产品表现-放款月2')
print("=== 周度文件列名 ===")
for i, c in enumerate(df_w.columns):
    print(f"  [{i}] {c}")
print(f"\n行数: {len(df_w)}")

# Check monthly file
print("\n=== 月度文件列名 ===")
df_m = pd.read_excel(r"d:\Documents\Downloads\评级产品表现-放款月21.xlsx", sheet_name='评级产品表现-放款月21')
for i, c in enumerate(df_m.columns):
    print(f"  [{i}] {c}")
print(f"\n行数: {len(df_m)}")
print("\n月度文件前5行(放款月份列):")
print(df_m[['放款月份']].head(10).to_string())
