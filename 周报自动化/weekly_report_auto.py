# -*- coding: utf-8 -*-
"""
印尼经分周报 — 一键数据更新脚本（精简版）
使用：python weekly_report_auto.py
输出：自动命名 印尼经分周报_YYYYMMDD_vN.xlsx
"""
import os, time
from datetime import date, datetime
import yaml, pandas as pd
from openpyxl import load_workbook
from presto_client import PrestoQuery

# ---- 加载配置 ----
CFG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')
with open(CFG_PATH, 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

TEMPLATE_DIR = cfg['template_dir']
OUTPUT_DIR   = cfg['output_dir']
FILE_PAT     = cfg['file_pattern']


# ---- 工具函数 ----
def find_latest_template():
    """找最新周报文件"""
    files = sorted(
        [f for f in os.listdir(TEMPLATE_DIR)
         if f.startswith(FILE_PAT) and f.endswith('.xlsx')],
        reverse=True
    )
    if not files:
        print("  ❌ 未找到周报模板！")
        return None
    print(f"  ✅ 模板: {files[0]}")
    return os.path.join(TEMPLATE_DIR, files[0])


def write_to_sheet(ws, df):
    """清空旧数据 → 列名映射 → 流式写入新数据"""
    # 读表头，建立映射
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
        # 未匹配的追加到末尾
        if dc not in col_map:
            next_col = ws.max_column + 1 + len([k for k in col_map if col_map[k] > ws.max_column])
            col_map[dc] = next_col
            ws.cell(1, next_col, value=dc)

    max_col = max(col_map.values())
    # 清空旧数据
    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row - 1)
    # 流式写入
    for _, row in df.iterrows():
        data = [None] * max_col
        for dc, ci in col_map.items():
            v = row[dc]
            data[ci - 1] = None if pd.isna(v) else v
        ws.append(data)
    return len(df)


# ---- 主流程 ----
def main():
    print("=" * 50)
    print("[AUTO] 印尼经分周报 - 一键数据更新")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # 1. 找模板
    tpl = find_latest_template()
    if not tpl:
        return

    # 2. 连接盘古
    print("\n>> 连接盘古")
    pq = PrestoQuery()
    try:
        pq.login()
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        return

    # 3. 跑SQL
    wb = load_workbook(tpl)
    updated = []
    for q in cfg['queries']:
        name, sheet, sql = q['name'], q['sheet'], q['sql']
        print(f"\n>> [{name}]")
        t0 = time.time()
        result = pq.query(sql)
        elapsed = time.time() - t0

        if isinstance(result, str):
            print(f"  ❌ 失败: {result} ({elapsed:.0f}s)")
            continue
        print(f"  ✅ {len(result)} 行 ({elapsed:.0f}s)")

        if sheet is None:
            # 单独保存
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            p = os.path.join(OUTPUT_DIR, f"日度放款聚合_{ts}.xlsx")
            result.to_excel(p, index=False)
            print(f"  >> 已保存: {p}")
        elif sheet in wb.sheetnames:
            rows = write_to_sheet(wb[sheet], result)
            updated.append((sheet, rows))
            print(f"  >> 写入 [{sheet}]: {rows} 行")

    # 4. 保存周报
    ds = date.today().strftime('%Y%m%d')
    v = 1
    while os.path.exists(os.path.join(OUTPUT_DIR, f"{FILE_PAT}{ds}_v{v}.xlsx")):
        v += 1
    out = os.path.join(OUTPUT_DIR, f"{FILE_PAT}{ds}_v{v}.xlsx")
    wb.save(out)
    print(f"\n✅ 周报已保存: {out}")
    for sn, rw in updated:
        print(f"   - {sn}: {rw} 行")

    # 5. 后续提示
    print("\n>> 后续手动(约5min):")
    print("  1. 打开周报 → 刷新透视表")
    print("  2. 检查数据 → 更新首贷文字")
    print("  3. 另存发送")


if __name__ == "__main__":
    main()
