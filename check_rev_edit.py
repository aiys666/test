import sys
sys.stdout.reconfigure(encoding='utf-8')
import openpyxl
import pandas as pd

wb = openpyxl.load_workbook(r"D:\Documents\Downloads\9月每周4t7预估(覆盖率100%法).xlsx", data_only=False)
ws = wb.active

orig = pd.read_excel(r"d:\Documents\Downloads\评级产品表现-放款月2 (1).xlsx", sheet_name='评级产品表现-放款月2')
orig['issue_week'] = orig['issue_week'].ffill()
orig = orig[orig['产品'].notna()].copy()
orig['week'] = orig['issue_week'].apply(lambda x: pd.to_datetime(x, errors='coerce'))
orig = orig[orig['week'].notna()].copy()
orig['week_str'] = orig['week'].dt.strftime('%m-%d')
target = ['08-31','09-07','09-14','09-21','09-28']
orig = orig[orig['week_str'].isin(target)]

# 原始总收息列
print("=== S列(总收息) 当前值 vs 原始'总收息_含税' ===")
print(f"{'周次':<6}{'产品':<22}{'原始总收息_含税':>16}{'原始总收息_不含税':>16}{'日息_含税':>10}{'Excel S列':>16}  改动")
for row in range(6, 101):
    a = ws.cell(row=row, column=1).value
    b = ws.cell(row=row, column=2).value
    s = ws.cell(row=row, column=19).value
    if not b or str(b).startswith('---') or '汇总' in str(a):
        continue
    o = orig[(orig['week_str']==a) & (orig['产品']==b)]
    if len(o)==0:
        continue
    o1 = o.iloc[0]
    orig_h = o1['总收息_含税']
    orig_nh = o1['总收息_不含税']
    ri = o1['日息_含税']
    sv = float(s) if isinstance(s,(int,float)) else None
    ov = float(orig_h) if pd.notna(orig_h) else None
    mark = ''
    if sv is not None and ov is not None and abs(sv-ov)>1e-9:
        mark = '<<< 改动'
    elif sv is None:
        mark = '<<< 清空'
    print(f"{a:<6}{b:<22}{ov if ov is not None else 'NaN':>16}{float(orig_nh) if pd.notna(orig_nh) else 'NaN':>16}{float(ri) if pd.notna(ri) else 'NaN':>10}{sv if sv is not None else 'None':>16}  {mark}")
