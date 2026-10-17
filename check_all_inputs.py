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

# Map excel columns to orig columns
# F-K 出账笔数, S 总收息, T-X 9月指标, Y-Z 9月4t7, AA-AE 8月指标, AF-AG 8月4t7
col_map = {
    6: 'is_t0_window_1', 7: 'is_t3_window_1', 8: 'is_t0_window_2', 9: 'is_t0_window_3',
    10: 'is_t0_window_4', 11: 'is_t7_window_4',
    19: '总收息_含税',
    20: '1t0本金逾期率', 21: '1t3本金逾期率', 22: '2t0本金逾期率', 23: '3t0本金逾期率', 24: '4t0本金逾期率',
    25: '4t7本金逾期率', 26: '4t7息费逾期率_本金分母',
}
# 8月列需要从月度文件取，单独处理

changes = []
for row in range(6, 101):
    a = ws.cell(row=row, column=1).value
    b = ws.cell(row=row, column=2).value
    if not b or str(b).startswith('---') or '汇总' in str(a):
        continue
    o = orig[(orig['week_str']==a) & (orig['产品']==b)]
    if len(o)==0:
        continue
    o1 = o.iloc[0]
    for col, ocol in col_map.items():
        ev = ws.cell(row=row, column=col).value
        ov = o1[ocol]
        if isinstance(ev, str) and ev.startswith('='):
            continue
        ev2 = float(ev) if isinstance(ev,(int,float)) else None
        ov2 = float(ov) if pd.notna(ov) else None
        if ev2 is None and ov2 is None:
            continue
        if ev2 is None or ov2 is None or abs(ev2-ov2) > 1e-6:
            col_letter = openpyxl.utils.get_column_letter(col)
            changes.append((a, b, col_letter, ocol, ov2, ev2))

if changes:
    print(f"共发现 {len(changes)} 处输入列改动:")
    for a,b,cl,ocol,ov,ev in changes:
        print(f"  {a} {b:>22} {cl}列({ocol}): 原始={ov} Excel={ev}")
else:
    print("产品行的输入列(F-K, S, T-Z) 未发现改动(阈值1e-6)")

# 检查8月原始列 AA-AG (来自月度文件)
df_m = pd.read_excel(r"d:\Documents\Downloads\评级产品表现-放款月21.xlsx", sheet_name='评级产品表现-放款月21')
df_m['放款月份'] = df_m['放款月份'].ffill()
df_m['月份'] = df_m['放款月份'].astype(str).str[:7]
aug = df_m[(df_m['月份']=='2026-08') & df_m['产品'].notna() & (df_m['放款笔数']>3)].set_index('产品')
aug_cols = {27:'1t0本金逾期率',28:'1t3本金逾期率',29:'2t0本金逾期率',30:'3t0本金逾期率',31:'4t0本金逾期率',32:'4t7本金逾期率',33:'4t7息费逾期率_本金分母'}
aug_changes = []
for row in range(6, 101):
    a = ws.cell(row=row, column=1).value
    b = ws.cell(row=row, column=2).value
    if not b or str(b).startswith('---') or '汇总' in str(a):
        continue
    if b not in aug.index:
        continue
    augrow = aug.loc[b]
    for col, ocol in aug_cols.items():
        ev = ws.cell(row=row, column=col).value
        ov = augrow[ocol]
        if isinstance(ev, str):
            continue
        ev2 = float(ev) if isinstance(ev,(int,float)) else None
        ov2 = float(ov) if pd.notna(ov) else None
        if ev2 is None and ov2 is None: continue
        if ev2 is None or ov2 is None or abs(ev2-ov2) > 1e-6:
            aug_changes.append((a,b,openpyxl.utils.get_column_letter(col),ocol,ov2,ev2))
if aug_changes:
    print(f"\n8月原始列共发现 {len(aug_changes)} 处改动:")
    for x in aug_changes:
        print(f"  {x}")
else:
    print("\n8月原始列(AA-AG) 未发现改动")
