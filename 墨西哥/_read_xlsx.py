# -*- coding: utf-8 -*-
import pandas as pd

path = r'D:\Documents\Downloads\效应分解_2026-08-03_vs_2026-08-10 (1).xlsx'
xl = pd.ExcelFile(path)
print("Sheets:", xl.sheet_names)
for s in xl.sheet_names:
    df = pd.read_excel(path, sheet_name=s)
    print(f"\n===== Sheet: {s}  shape={df.shape} =====")
    print("Columns:", list(df.columns))
    print(df.head(15).to_string())
