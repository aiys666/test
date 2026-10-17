# -*- coding: utf-8 -*-
"""
Step 1: 风险坏账数据转化
输入: 风险产品坏账.xlsx (风险团队提供的死数 Excel)
输出: CSV + INSERT SQL → ind.ba_bad_debt_rate_lookup 表

从 权责1_风险提供坏账转化脚本.py 提取核心逻辑
"""

import os
import csv
import sys

# 将父目录加入 path，支持独立运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openpyxl
from core.config import load_config
from core.db import PrestoQuery


# ── 列区段映射 ──
# (起始列, 结束列, 产品中文名, 授信策略, 期限标签)
COLUMN_RANGES = [
    (2, 7, "常规产品（等本等息+老免息）", "NEW", "15D"),
    (8, 11, "常规产品（等本等息+老免息）", "NEW", "30D"),
    (12, 14, "花式-新免息", "NEW", "F"),
    (15, 19, "本金前置", "NEW", "M"),
    (20, 22, "无忧贷", "NEW", "NR"),
    (23, 26, "优享贷", "NEW", "NF"),
    (27, 29, "放心贷", "NEW", "NW"),
    (30, 35, "常规产品（等本等息+老免息）", "OLD", "15D"),
    (36, 39, "常规产品（等本等息+老免息）", "OLD", "30D"),
    (40, 45, "花式-新免息", "OLD", "F"),
    (46, 50, "本金前置", "OLD", "M"),
    (51, 54, "无忧贷", "OLD", "NR"),
    (55, 59, "优享贷", "OLD", "NF"),
    (60, 62, "放心贷", "OLD", "NW"),
]

PRODUCT_TAG = {
    "常规产品（等本等息+老免息）": "R",
    "花式-新免息": "F",
    "本金前置": "M",
    "无忧贷": "NR",
    "优享贷": "NF",
    "放心贷": "NW",
}

HEJI_CYCLE = 9999


def parse_risk_excel(src_path: str) -> list:
    """
    解析风险产品坏账 Excel，返回 records 列表
    每条: {grant_month, product_tag, period_tag, grant_strategy,
           loan_cycle, bad_debt_rate}
    """
    wb = openpyxl.load_workbook(src_path, data_only=True)
    ws = wb["Sheet1"]

    records = []
    for data_row in range(4, ws.max_row + 1):
        month_raw = ws.cell(data_row, 1).value
        if not month_raw:
            continue
        month_str = str(month_raw).strip()[:10]

        for col_s, col_e, product_cn, grant, period in COLUMN_RANGES:
            pt = PRODUCT_TAG[product_cn]
            tenure_list = []
            for c in range(col_s, col_e + 1):
                v3 = ws.cell(3, c).value
                if v3 is None:
                    continue
                val3 = str(v3).strip()
                if val3 in ("", "合计", "总计", "合计_1", "合计_2"):
                    continue
                if val3 in ("合计", "总计"):
                    tenure_list.append((c, HEJI_CYCLE))
                else:
                    num = "".join(ch for ch in val3 if ch.isdigit())
                    if num:
                        tenure_list.append((c, int(num)))

            for t_col, t_days in tenure_list:
                cell_val = ws.cell(data_row, t_col).value
                if cell_val is None:
                    bdr = "NULL"
                elif isinstance(cell_val, (int, float)):
                    bdr = str(round(float(cell_val), 10))
                else:
                    cs = str(cell_val).strip()
                    if cs in ("/", "", "-"):
                        bdr = "NULL"
                    else:
                        try:
                            bdr = str(round(float(cs), 10))
                        except ValueError:
                            bdr = "NULL"

                records.append({
                    "grant_month": month_str,
                    "product_tag": pt,
                    "period_tag": period,
                    "grant_strategy": grant,
                    "loan_cycle": t_days,
                    "bad_debt_rate": bdr,
                })

    return records


def export_csv(records: list, output_dir: str) -> str:
    """导出 CSV 文件"""
    csv_path = os.path.join(output_dir, "risk_bad_debt.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "grant_month", "product_tag", "period_tag",
            "grant_strategy", "loan_cycle", "bad_debt_rate"
        ])
        writer.writeheader()
        writer.writerows(records)
    return csv_path


def build_insert_sql(records: list) -> str:
    """生成 INSERT SQL"""
    rows_sql = []
    for rec in records:
        lc = rec["loan_cycle"]
        bdr = rec["bad_debt_rate"]
        rows_sql.append(
            f"  ('{rec['grant_month']}','{rec['product_tag']}','{rec['period_tag']}',"
            f"'{rec['grant_strategy']}',{lc},{bdr})"
        )

    return (
        "DELETE FROM ind.ba_bad_debt_rate_lookup;\n\n"
        "INSERT INTO ind.ba_bad_debt_rate_lookup\n"
        "  (grant_month, product_tag, period_tag, grant_strategy, loan_cycle, bad_debt_rate)\n"
        "VALUES\n" + ",\n".join(rows_sql) + ";\n"
    )


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def run(cfg: dict, db: PrestoQuery = None, verbose: bool = True) -> dict:
    """
    执行 Step 1: 风险坏账数据转化
    返回: {"status": "ok", "records": N, "csv": path, "sql": path}
    """
    source_file = cfg.get("risk_bad_debt", {}).get("source_file", "")
    if not source_file or not os.path.exists(source_file):
        return {"status": "error", "message": f"风险坏账文件不存在: {source_file}"}

    output_dir = cfg.get("pipeline", {}).get("output_dir", ".")
    os.makedirs(output_dir, exist_ok=True)

    # 1. 解析 Excel
    if verbose:
        print(f"  读取: {source_file}")
    records = parse_risk_excel(source_file)
    if verbose:
        total = len(records)
        null_cnt = sum(1 for r in records if r["bad_debt_rate"] == "NULL")
        print(f"  解析: {total} 条记录  (NULL={null_cnt}, 有效={total - null_cnt})")

    # 2. 导出 CSV
    csv_path = export_csv(records, output_dir)
    if verbose:
        print(f"  CSV: {csv_path}")

    # 3. 生成 INSERT SQL
    sql = build_insert_sql(records)
    sql_path = os.path.join(output_dir, "risk_bad_debt_insert.sql")
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write(sql)
    if verbose:
        print(f"  SQL: {sql_path}")

    # 4. 写入数据库（如果提供了连接）
    db_result = None
    if db is not None:
        if verbose:
            print(f"  写入数据库...")
        ok = db.execute(sql, verbose=False)
        db_result = "成功" if ok else f"失败: {sql[:100]}"

    return {
        "status": "ok",
        "records": len(records),
        "csv": csv_path,
        "sql": sql_path,
        "db_result": db_result,
    }


# 支持独立运行
if __name__ == "__main__":
    cfg = load_config()
    result = run(cfg, verbose=True)
    print(f"\n结果: {result}")
