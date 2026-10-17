import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

df_m = pd.read_excel(r"d:\Documents\Downloads\评级产品表现-放款月21.xlsx", sheet_name='评级产品表现-放款月21')
df_m['放款月份'] = df_m['放款月份'].ffill()
df_m['月份'] = df_m['放款月份'].astype(str).str[:7]
print("月度文件中所有月份:")
print(df_m['月份'].value_counts())
print("\n8月产品数:")
aug = df_m[(df_m['月份']=='2026-08') & df_m['产品'].notna()]
print(f"  {len(aug)}个产品, 放款笔数>3的有{len(aug[aug['放款笔数']>3])}个")
print("\n9月产品数:")
sep = df_m[(df_m['月份']=='2026-09') & df_m['产品'].notna()]
print(f"  {len(sep)}个产品")
print("\n9月产品列表:")
for _, r in sep.iterrows():
    term = int(r['平均期限']) if pd.notna(r['平均期限']) else '?'
    print(f"  {r['产品']:>25} {term:>3}天 loans={int(r['放款笔数']):>5}")
