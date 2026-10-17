import sys
sys.stdout.reconfigure(encoding='utf-8')
import openpyxl

wb = openpyxl.load_workbook(r"D:\Documents\Downloads\9月每周4t7预估(覆盖率100%法).xlsx")
ws = wb.active

print("=== 验证关键公式 ===\n")

# Check a product row (e.g., row 7, first product of 08-31 week)
print("--- 行7 (08-31第一个产品) ---")
for col in ['L','M','N','O','P','Q','R','AR','AS','AT']:
    cell = ws[f'{col}7']
    print(f"  {col}7: {cell.value}")

print("\n--- 行23 (08-31周汇总) ---")
for col in ['A','C','D','AR','AS','AT']:
    cell = ws[f'{col}23']
    print(f"  {col}23: {cell.value}")

print("\n--- 行102 (月聚合) ---")
for col in ['A','C','D','AR','AS','AT']:
    cell = ws[f'{col}102']
    print(f"  {col}102: {cell.value}")

print("\n--- 行105 (直接月度) ---")
for col in ['A','C','D','AR','AS','AT']:
    cell = ws[f'{col}105']
    print(f"  {col}105: {cell.value}")

print("\n--- 行106 (差额) ---")
for col in ['A','AR','AS','AT']:
    cell = ws[f'{col}106']
    print(f"  {col}106: {cell.value}")

# Check 09-28 week (推荐="无" products)
print("\n--- 行84 (09-28某产品, 应为推荐=无) ---")
for col in ['A','B','L','M','N','O','P','Q','R','AR','AS','AT']:
    cell = ws[f'{col}84']
    print(f"  {col}84: {cell.value}")
