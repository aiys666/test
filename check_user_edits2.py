import sys
sys.stdout.reconfigure(encoding='utf-8')
import openpyxl
import pandas as pd

wb = openpyxl.load_workbook(r"D:\Documents\Downloads\9月每周4t7预估(覆盖率100%法).xlsx", data_only=False)
ws = wb.active

# Original weekly file
orig = pd.read_excel(r"d:\Documents\Downloads\评级产品表现-放款月2 (1).xlsx", sheet_name='评级产品表现-放款月2')
orig['issue_week'] = orig['issue_week'].ffill()
orig = orig[orig['产品'].notna()].copy()
orig['week'] = orig['issue_week'].apply(lambda x: pd.to_datetime(x, errors='coerce'))
orig = orig[orig['week'].notna()].copy()
orig['week_str'] = orig['week'].dt.strftime('%m-%d')
target = ['08-31','09-07','09-14','09-21','09-28']
orig = orig[orig['week_str'].isin(target)].sort_values(['week_str','产品']).reset_index(drop=True)

print("=== 周汇总行的S列(总收息) ===")
for wr in [23,41,61,80,99]:
    print(f"  行{wr}: A={ws.cell(wr,1).value!r} S={ws.cell(wr,19).value!r}")

print("\n=== 产品行S列是否为公式/被修改 ===")
changed = 0
for row in range(6, 101):
    a = ws.cell(row=row, column=1).value
    b = ws.cell(row=row, column=2).value
    s = ws.cell(row=row, column=19).value
    if not b or str(b).startswith('---') or '汇总' in str(a):
        continue
    if isinstance(s, str) and s.startswith('='):
        print(f"  {a} {b:>22} S{r} 是公式: {s}")
        changed += 1
        continue
    orow = orig[(orig['week_str']==a) & (orig['产品']==b)]
    if len(orow) > 0:
        o = float(orow.iloc[0]['总收息_含税'])
        sv = float(s) if s is not None else None
        if sv is None or abs(sv-o) > 1e-9:
            print(f"  {a} {b:>22} 原={o:.6f} Excel={sv} <<< 修改")
            changed += 1
if changed == 0:
    print("  (未发现产品行总收息修改)")

# Dump rows 99-110 fully for AR/AS/AT/S columns
print("\n=== 行95~110 关键列 ===")
for row in range(95, 111):
    vals = {col: ws.cell(row, col).value for col in [1,2,19,44,45,46]}
    print(f"  r{row}: {vals}")
