# -*- coding: utf-8 -*-
"""Dry run 测试：模拟数据验证 Excel 写入逻辑（适配新模块结构）"""
import os, sys, time
from datetime import date
import pandas as pd
from openpyxl import load_workbook

# 模拟 config.yaml 的路径
TEMPLATE_DIR = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\墨西哥"
FILE_PAT = "印尼经分周报_"

# ---- 模拟数据 ----
def mock_ad(n=200):
    dates = pd.date_range('2026-01-01', periods=n, freq='D')
    return pd.DataFrame({
        'ad_date': dates,
        'ad_date_month': dates.strftime('%Y-%m-01'),
        'ad_date_week': dates.strftime('%Y-%m-%d'),
        'media_source': ['Meta'] * n,
        'spend': [10000 + i * 50 for i in range(n)],
        'install_cnt': [5000 + i * 20 for i in range(n)],
        'reg_cnt': [3000 + i * 10 for i in range(n)],
        'if_app': [2000 + i * 5 for i in range(n)],
        'issue_cnt': [500 + i * 2 for i in range(n)],
        'contract_amount_usd': [50000 + i * 100 for i in range(n)],
    })

def mock_new(n=500):
    weeks = pd.date_range('2026-01-06', periods=n, freq='W-MON').strftime('%Y-%m-%d')
    return pd.DataFrame({
        'grant_strategy': ['NEW'] * n,
        'product_tag': ['R'] * n,
        'is_reloan2': ['NEW_PURE'] * n,
        'new_grade_level': ['3'] * n,
        'user_level': ['3'] * n,
        'media_source': ['Meta'] * n,
        'source_channel2': ['Android'] * n,
        'if_regular_backup': [0] * n,
        'if_backup_switch': [0] * n,
        'app_week': weeks,
        'app_month': pd.date_range('2026-01-01', periods=n, freq='MS').strftime('%Y-%m-01')[:n],
        'if_app': [100 + i for i in range(n)],
        'if_external_3_passed': [80 + i for i in range(n)],
        'in_confirm_cnt_final': [60 + i for i in range(n)],
        'in_confirm_cnt': [70 + i for i in range(n)],
    })

def mock_old(n=500):
    weeks = pd.date_range('2026-01-06', periods=n, freq='W-MON').strftime('%Y-%m-%d')
    return pd.DataFrame({
        'grant_strategy': ['OLD'] * n,
        'product_tag': ['R'] * n,
        'is_reloan2': ['reloan'] * n,
        'new_grade_level': ['3'] * n,
        'first_loan_grade_level': ['2'] * n,
        'if_regular_backup': [0] * n,
        'if_backup_switch': [0] * n,
        'new_old_model_loop': ['4-loop'] * n,
        'app_week': weeks,
        'app_month': pd.date_range('2026-01-01', periods=n, freq='MS').strftime('%Y-%m-01')[:n],
        'if_app': [100 + i for i in range(n)],
        'if_external_3_passed': [80 + i for i in range(n)],
        'create_app_cnt': [90 + i for i in range(n)],
        'in_confirm_cnt_final': [60 + i for i in range(n)],
        'in_confirm_cnt': [70 + i for i in range(n)],
    })


# ---- 复用主脚本的 write_to_sheet ----
def write_to_sheet(ws, df):
    headers = {str(ws.cell(1, c).value or '').strip(): c
               for c in range(1, ws.max_column + 1)}
    col_map = {}
    for dc in df.columns:
        s = str(dc).strip()
        if s in headers:
            col_map[dc] = headers[s]
        elif s.lower() in {k.lower() for k in headers}:
            for h, idx in headers.items():
                if h.lower() == s.lower():
                    col_map[dc] = idx
                    break
        if dc not in col_map:
            next_col = ws.max_column + 1 + len([k for k in col_map if col_map[k] > ws.max_column])
            col_map[dc] = next_col
            ws.cell(1, next_col, value=dc)

    max_col = max(col_map.values())
    if ws.max_row > 1:
        t0 = time.time()
        ws.delete_rows(2, ws.max_row - 1)
        print(f"    清空耗时: {time.time()-t0:.1f}s")

    t0 = time.time()
    for _, row in df.iterrows():
        data = [None] * max_col
        for dc, ci in col_map.items():
            v = row[dc]
            data[ci - 1] = None if pd.isna(v) else v
        ws.append(row_data=data)
    print(f"    写入耗时: {time.time()-t0:.1f}s ({len(df)}行)")
    return len(df)


# ---- 测试主流程 ----
print("=" * 50)
print("[DRY RUN] 测试 - 模拟数据")
print("=" * 50)

# 找模板
files = sorted([f for f in os.listdir(TEMPLATE_DIR)
                if f.startswith(FILE_PAT) and f.endswith('.xlsx')], reverse=True)
if not files:
    print("❌ 没有找到周报文件")
    sys.exit(1)
tpl = os.path.join(TEMPLATE_DIR, files[0])
print(f"模板: {files[0]}")

# 加载
print("\n加载Excel...")
wb = load_workbook(tpl)

# 写入3个Sheet
mocks = {
    "投放数据源": mock_ad(200),
    "数据源（进件）": mock_new(500),
    "复贷数据源": mock_old(500),
}

for sheet, df in mocks.items():
    print(f"\n>> [{sheet}]")
    if sheet not in wb.sheetnames:
        print(f"  ⚠️ Sheet不存在，跳过")
        continue
    ws = wb[sheet]
    # 列匹配统计
    headers = {str(ws.cell(1, c).value or '').strip(): c for c in range(1, ws.max_column + 1)}
    matched = sum(1 for dc in df.columns if str(dc).strip() in headers or str(dc).strip().lower() in {k.lower() for k in headers})
    print(f"  列匹配: {matched}/{len(df.columns)}")
    rows = write_to_sheet(ws, df)
    print(f"  OK 写入 {rows} 行")

# 保存（测试版本号999）
out_name = f"{FILE_PAT}{date.today().strftime('%Y%m%d')}_v999_TEST.xlsx"
out_path = os.path.join(TEMPLATE_DIR, out_name)
print(f"\n保存: {out_path}")
t0 = time.time()
wb.save(out_path)
print(f"保存耗时: {time.time()-t0:.1f}s")
print("\n[OK] Dry Run 测试完成!")
