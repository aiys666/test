import sys
sys.stdout.reconfigure(encoding='utf-8')
import openpyxl
import pandas as pd

# Read the current Excel (user may have modified)
wb = openpyxl.load_workbook(r"D:\Documents\Downloads\9月每周4t7预估(覆盖率100%法).xlsx", data_only=False)
ws = wb.active

# Print month aggregation row (row 102) formulas
print("=== 月聚合行(102)公式 ===")
for col in ['A','C','D','AR','AS','AT']:
    print(f"  {col}102: {ws[f'{col}102'].value}")

print("\n=== 差额行(106)公式 ===")
for col in ['A','AR','AS','AT']:
    print(f"  {col}106: {ws[f'{col}106'].value}")

# Print 总收息 (S列) for all product rows, compare with original
print("\n=== 各产品行 S列(总收息) 当前值 ===")
orig = pd.read_excel(r"d:\Documents\Downloads\评级产品表现-放款月2 (1).xlsx", sheet_name='评级产品表现-放款月2')
orig['issue_week'] = orig['issue_week'].ffill()
orig = orig[orig['产品'].notna()].copy()
orig['week'] = orig['issue_week'].apply(lambda x: pd.to_datetime(x, errors='coerce'))
orig = orig[orig['week'].notna()].copy()
orig['week_str'] = orig['week'].dt.strftime('%m-%d')
target = ['08-31','09-07','09-14','09-21','09-28']
orig = orig[orig['week_str'].isin(target)].sort_values(['week_str','产品']).reset_index(drop=True)

for row in range(6, 101):
    a = ws.cell(row=row, column=1).value
    b = ws.cell(row=row, column=2).value
    s = ws.cell(row=row, column=19).value
    if b and not str(b).startswith('---') and '汇总' not in str(a):
        # find original
        orig_row = orig[(orig['week_str']==a) & (orig['产品']==b)]
        if len(orig_row)>0:
            o = float(orig_row.iloc[0]['总收息_含税'])
            if isinstance(s, str) and s.startswith('='):
                print(f"  {a} {b:>22} Excel(S{r}): {s}")
            else:
                sv = float(s) if s is not None else None
                if sv is not None and abs(sv - o) > 1e-9:
                    print(f"  {a} {b:>22} 原值={o:.6f} Excel值={sv:.6f} <<<< 已修改")
                elif sv is None:
                    print(f"  {a} {b:>22} 原值={o:.6f} Excel值=None <<<< 已清空")
