# -*- coding: utf-8 -*-
"""
Step 4: 预估数据入库
读取权责预估 Excel → 解析数据行 → 生成 INSERT SQL → Presto 写入 + 验证

从 ba_loan_forecast_全流程.py 提取核心逻辑
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openpyxl
from datetime import datetime
from collections import defaultdict

from core.db import PrestoQuery
from core.config import load_config


# ── 产品映射 ──
PRODUCT_MAP = {
    "常规": "R",
    "本金": "M",
    "无忧贷": "NR",
    "优享贷": "NF",
    "放心贷": "NW",
}

# ── 建表 SQL ──
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ind.ba_loan_forecast (
     id                 BIGINT,
     stat_month         VARCHAR(10),
     grant_strategy     VARCHAR(10),
     is_reloan2         VARCHAR(10),
     loan_cycle         SMALLINT,
     product_tag        VARCHAR(10),
     apply_cnt          BIGINT,
     before_pass_rate   DECIMAL(5,4),
     confirm_rate       DECIMAL(5,4),
     after_pass_rate    DECIMAL(5,4),
     pass_rate          DECIMAL(5,4),
     sign_grant_rate    DECIMAL(5,4),
     full_pass_rate     DECIMAL(18,10),
     loan_term_dist     DECIMAL(18,8),
     loan_cnt           DECIMAL(18,6),
     avg_amt_idr        DECIMAL(18,6),
     avg_amt_usd        DECIMAL(18,6),
     loan_amt_term_dist DECIMAL(18,8),
     t30_rate           DECIMAL(5,4),
     contract_amt       DECIMAL(18,6),
     bad_amt            DECIMAL(18,6),
     loan_cycle_amount  DECIMAL(18,6),
     loan_cycle_wtd     DECIMAL(18,6),
     annual_bad_rate    DECIMAL(18,10),
     loan_amt_rate      DECIMAL(18,8)
)
"""


# ═══════════════════════════════════════════════════════════════
# Excel 解析
# ═══════════════════════════════════════════════════════════════

def load_excel_records(src_path: str) -> list:
    """读取权责预估 Excel，解析数据行"""
    wb = openpyxl.load_workbook(src_path, data_only=True)
    ws = wb["Sheet1"]

    # 合并单元格填充
    merged_filled = {}
    for mr in ws.merged_cells.ranges:
        top_val = ws.cell(mr.min_row, mr.min_col).value
        for r in range(mr.min_row, mr.max_row + 1):
            for c in range(mr.min_col, mr.max_col + 1):
                merged_filled[(r, c)] = top_val

    def gv(row, col):
        if (row, col) in merged_filled:
            return merged_filled[(row, col)]
        return ws.cell(row, col).value

    def safe_val(v):
        if v is None:
            return None
        if isinstance(v, str):
            v_s = v.strip()
            if v_s in ("/", "-", "", "#DIV/0!"):
                return None
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return None
        return v

    # 动态定位表头行
    data_start_row = None
    for r in range(1, ws.max_row + 1):
        if ws.cell(r, 6).value == "月份":
            data_start_row = r + 1
            break
    if data_start_row is None:
        raise ValueError("无法找到'月份'表头")

    records = []
    for r in range(data_start_row, ws.max_row + 1):
        col_a = gv(r, 1)
        col_b = gv(r, 2)
        col_e = ws.cell(r, 5).value
        f_val = gv(r, 6)

        if not isinstance(f_val, datetime):
            continue
        if col_a not in ("首贷", "复贷"):
            continue
        if col_b == "本金加贷":
            continue
        if col_e not in PRODUCT_MAP:
            continue

        stat_month = f_val.strftime("%Y-%m")
        contract_amt_raw = safe_val(gv(r, 23))
        if contract_amt_raw == 0 or contract_amt_raw is None:
            continue

        if col_a == "首贷":
            grant_strategy = "NEW"
            is_reloan2 = "new"
        else:
            grant_strategy = "OLD"
            is_reloan2 = "loop" if col_b == "循环贷" else "normal"

        product_tag = PRODUCT_MAP[col_e]

        avg_amt_idr_wan = safe_val(gv(r, 19))
        avg_amt_idr = round(avg_amt_idr_wan * 10000, 6) if avg_amt_idr_wan else None

        records.append({
            "stat_month": stat_month,
            "grant_strategy": grant_strategy,
            "is_reloan2": is_reloan2,
            "loan_cycle": safe_val(gv(r, 26)),
            "product_tag": product_tag,
            "apply_cnt": safe_val(gv(r, 10)),
            "before_pass_rate": safe_val(gv(r, 11)),
            "confirm_rate": safe_val(gv(r, 12)),
            "after_pass_rate": safe_val(gv(r, 13)),
            "pass_rate": safe_val(gv(r, 14)),
            "sign_grant_rate": safe_val(gv(r, 15)),
            "full_pass_rate": safe_val(gv(r, 16)),
            "loan_term_dist": safe_val(gv(r, 17)),
            "loan_cnt": safe_val(gv(r, 18)),
            "avg_amt_idr": avg_amt_idr,
            "avg_amt_usd": safe_val(gv(r, 20)),
            "loan_amt_term_dist": None,
            "t30_rate": safe_val(gv(r, 22)),
            "contract_amt": contract_amt_raw,
            "bad_amt": safe_val(gv(r, 24)),
            "loan_cycle_amount": safe_val(gv(r, 25)),
            "loan_cycle_wtd": safe_val(gv(r, 25)),
            "annual_bad_rate": safe_val(gv(r, 27)),
            "loan_amt_rate": safe_val(gv(r, 28)),
        })

    # 计算 loan_amt_term_dist
    sum_map = defaultdict(float)
    for rec in records:
        key = (rec["stat_month"], rec["grant_strategy"])
        if rec["contract_amt"]:
            sum_map[key] += rec["contract_amt"]

    for rec in records:
        key = (rec["stat_month"], rec["grant_strategy"])
        s = sum_map.get(key, 0)
        rec["loan_amt_term_dist"] = round(rec["contract_amt"] / s, 8) if s else None

    return records


def make_val(v):
    """Python 值 → SQL 值字符串"""
    if v is None:
        return "NULL"
    if isinstance(v, str):
        return f"'{v}'"
    if isinstance(v, float):
        return repr(round(v, 10))
    return str(v)


def build_bulk_insert(records: list) -> str:
    """生成批量 INSERT SQL"""
    rows_sql = []
    for i, rec in enumerate(records, 1):
        vals = ", ".join([
            str(i),
            make_val(rec["stat_month"]),
            make_val(rec["grant_strategy"]),
            make_val(rec["is_reloan2"]),
            make_val(rec["loan_cycle"]),
            make_val(rec["product_tag"]),
            make_val(rec["apply_cnt"]),
            make_val(rec["before_pass_rate"]),
            make_val(rec["confirm_rate"]),
            make_val(rec["after_pass_rate"]),
            make_val(rec["pass_rate"]),
            make_val(rec["sign_grant_rate"]),
            make_val(rec["full_pass_rate"]),
            make_val(rec["loan_term_dist"]),
            make_val(rec["loan_cnt"]),
            make_val(rec["avg_amt_idr"]),
            make_val(rec["avg_amt_usd"]),
            make_val(rec["loan_amt_term_dist"]),
            make_val(rec["t30_rate"]),
            make_val(rec["contract_amt"]),
            make_val(rec["bad_amt"]),
            make_val(rec["loan_cycle_amount"]),
            make_val(rec["loan_cycle_wtd"]),
            make_val(rec["annual_bad_rate"]),
            make_val(rec["loan_amt_rate"]),
        ])
        rows_sql.append(f"  ({vals})")

    return "INSERT INTO ind.ba_loan_forecast VALUES\n" + ",\n".join(rows_sql)


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def run(cfg: dict, db: PrestoQuery = None, verbose: bool = True) -> dict:
    """
    执行 Step 4: 预估数据入库
    需要提供 Step 3 输出的 Excel 文件路径，或从配置中读取源文件
    """
    if db is None:
        return {"status": "error", "message": "此步骤需要数据库连接"}

    # 尝试从 Step 3 的输出获取 Excel 路径
    source_path = cfg.get("_step3_output_file", None)
    if not source_path:
        source_path = cfg.get("paths", {}).get("accrual_source", "")
    if not source_path or not os.path.exists(source_path):
        return {"status": "error", "message": f"预估 Excel 文件不存在: {source_path}"}

    # 1. 解析 Excel
    if verbose:
        print(f"  读取: {source_path}")
    records = load_excel_records(source_path)
    if verbose:
        print(f"  解析: {len(records)} 行数据")
        from collections import Counter
        cnt = Counter((r["stat_month"], r["grant_strategy"], r["is_reloan2"]) for r in records)
        for k, v in sorted(cnt.items()):
            print(f"    {k}: {v}行")

    if not records:
        return {"status": "error", "message": "Excel 解析结果为空"}

    # 2. 建表
    if verbose:
        print("  建表 (CREATE IF NOT EXISTS)...")
    ok = db.execute(CREATE_TABLE_SQL, verbose=False)
    if verbose:
        print(f"    → {'成功' if ok else '失败'}")

    # 3. 清空旧数据 + 插入新数据
    if verbose:
        print("  清空旧数据...")
    db.execute("DELETE FROM ind.ba_loan_forecast", verbose=False)

    if verbose:
        print(f"  批量插入 ({len(records)} 条)...")
    bulk_sql = build_bulk_insert(records)
    ok = db.execute(bulk_sql, verbose=False)
    if verbose:
        print(f"    → {'成功' if ok else '失败'}")

    # 4. 验证
    if verbose:
        print("  验证数据...")
    verify_sql = (
        "SELECT stat_month, grant_strategy, is_reloan2, COUNT(*) AS cnt "
        "FROM ind.ba_loan_forecast "
        "GROUP BY stat_month, grant_strategy, is_reloan2 "
        "ORDER BY stat_month, grant_strategy, is_reloan2"
    )
    df = db.query_df(verify_sql, verbose=False)
    if not df.empty:
        total = df["cnt"].astype(int).sum()
        if verbose:
            print(f"    数据库行数: {total}  (预期: {len(records)})")
            if total == len(records):
                print(f"    ✓ 行数校验通过")
            else:
                print(f"    ✗ 行数不一致！")

    return {
        "status": "ok",
        "records": len(records),
        "db_row_count": int(df["cnt"].astype(int).sum()) if not df.empty else 0,
    }


if __name__ == "__main__":
    cfg = load_config()
    db = PrestoQuery(cfg.get("database", {}))
    db.login()
    result = run(cfg, db, verbose=True)
    print(f"\n结果: {result.get('status')}")
