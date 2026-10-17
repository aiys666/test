# -*- coding: utf-8 -*-
"""
Step 5: 数据校验
查询数据库表 → 对比 config.yaml 中的预期值 → 输出校验报告
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime

from core.db import PrestoQuery
from core.config import load_config


# ═══════════════════════════════════════════════════════════════
# 校验项
# ═══════════════════════════════════════════════════════════════

def check_loan_forecast_count(db: PrestoQuery) -> dict:
    """校验 ba_loan_forecast 表数据行数"""
    df = db.query_df(
        "SELECT stat_month, grant_strategy, is_reloan2, COUNT(*) AS cnt "
        "FROM ind.ba_loan_forecast "
        "GROUP BY stat_month, grant_strategy, is_reloan2 "
        "ORDER BY stat_month, grant_strategy, is_reloan2"
    )
    if df.empty:
        return {"name": "ba_loan_forecast 行数", "status": "warn", "detail": "表为空"}

    total = int(df["cnt"].astype(int).sum())
    return {
        "name": "ba_loan_forecast 行数",
        "status": "ok",
        "detail": f"共 {total} 行",
        "data": df.to_dict("records"),
    }


def check_bad_debt_coverage(db: PrestoQuery) -> dict:
    """校验坏账率数据覆盖率"""
    df = db.query_df(
        "SELECT "
        "  COUNT(*) AS total, "
        "  SUM(CASE WHEN bad_debt_rate IS NOT NULL AND bad_debt_rate > 0 THEN 1 ELSE 0 END) AS non_zero "
        "FROM ind.ba_bad_debt_rate_lookup"
    )
    if df.empty:
        return {"name": "坏账率覆盖率", "status": "warn", "detail": "表为空"}

    total = int(df["total"].iloc[0])
    non_zero = int(df["non_zero"].iloc[0])
    coverage = non_zero / total * 100 if total > 0 else 0
    status = "ok" if coverage > 50 else "warn"

    return {
        "name": "坏账率覆盖率",
        "status": status,
        "detail": f"{non_zero}/{total} 非零 ({coverage:.1f}%)",
    }


def check_monthly_contract_amt(db: PrestoQuery, months_cfg: dict) -> dict:
    """校验各月份放款金额"""
    current = months_cfg.get("current", "")
    next_m = months_cfg.get("next", "")

    df = db.query_df(
        f"SELECT stat_month, "
        f"  SUM(CASE WHEN grant_strategy='NEW' THEN contract_amt ELSE 0 END) AS new_amt, "
        f"  SUM(CASE WHEN grant_strategy='OLD' THEN contract_amt ELSE 0 END) AS old_amt, "
        f"  SUM(contract_amt) AS total_amt "
        f"FROM ind.ba_loan_forecast "
        f"WHERE stat_month IN ('{current}', '{next_m}') "
        f"GROUP BY stat_month ORDER BY stat_month"
    )
    if df.empty:
        return {"name": "月份放款金额", "status": "warn", "detail": "无数据"}

    details = []
    for _, row in df.iterrows():
        details.append(
            f"{row['stat_month']}: "
            f"首贷=${row['new_amt']:,.0f}  "
            f"复贷=${row['old_amt']:,.0f}  "
            f"合计=${row['total_amt']:,.0f}"
        )

    return {
        "name": "月份放款金额",
        "status": "ok",
        "detail": " | ".join(details),
    }


def check_asset_base_summary(db: PrestoQuery, months_cfg: dict) -> dict:
    """校验资产底表月度汇总（与预估对比）"""
    current = months_cfg.get("current", "")

    df = db.query_df(
        f"SELECT "
        f"  issue_month, "
        f"  COUNT(DISTINCT CASE WHEN grant_strategy='NEW' THEN mid END) AS new_cust, "
        f"  COUNT(DISTINCT CASE WHEN grant_strategy='OLD' THEN mid END) AS old_cust, "
        f"  SUM(if_issue) AS total_loans, "
        f"  SUM(contract_amount_usd1) AS total_amt "
        f"FROM ind.ba_asset_base_info "
        f"WHERE issue_month >= '{current}-01' AND if_issue=1 "
        f"GROUP BY issue_month ORDER BY issue_month DESC "
        f"LIMIT 3"
    )
    if df.empty:
        return {"name": "资产底表近期汇总", "status": "warn", "detail": "无近期数据"}

    details = []
    for _, row in df.iterrows():
        details.append(
            f"{row['issue_month']}: "
            f"新客={int(row['new_cust']):,}  老客={int(row['old_cust']):,}  "
            f"笔数={int(row['total_loans']):,}  金额=${row['total_amt']:,.0f}"
        )

    return {
        "name": "资产底表近期汇总",
        "status": "ok",
        "detail": " | ".join(details[:2]),
    }


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def run(cfg: dict, db: PrestoQuery = None, verbose: bool = True) -> dict:
    """
    执行 Step 5: 数据校验，输出校验报告
    """
    if db is None:
        return {"status": "error", "message": "此步骤需要数据库连接"}

    months_cfg = cfg.get("months", {})
    checks = []

    # 逐项校验
    if verbose:
        print("  校验 ba_loan_forecast 表...")
    r = check_loan_forecast_count(db)
    checks.append(r)
    if verbose:
        print(f"    [{r['status'].upper()}] {r['name']}: {r['detail']}")

    if verbose:
        print("  校验坏账率覆盖率...")
    r = check_bad_debt_coverage(db)
    checks.append(r)
    if verbose:
        print(f"    [{r['status'].upper()}] {r['name']}: {r['detail']}")

    if verbose:
        print("  校验月份放款金额...")
    r = check_monthly_contract_amt(db, months_cfg)
    checks.append(r)
    if verbose:
        print(f"    [{r['status'].upper()}] {r['name']}: {r['detail']}")

    if verbose:
        print("  校验资产底表...")
    r = check_asset_base_summary(db, months_cfg)
    checks.append(r)
    if verbose:
        print(f"    [{r['status'].upper()}] {r['name']}: {r['detail']}")

    # 汇总
    ok_count = sum(1 for c in checks if c["status"] == "ok")
    warn_count = sum(1 for c in checks if c["status"] == "warn")
    error_count = sum(1 for c in checks if c["status"] == "error")

    if verbose:
        print(f"\n  ── 校验汇总 ──")
        print(f"  ✓ 通过: {ok_count}  |  ⚠ 警告: {warn_count}  |  ✗ 错误: {error_count}")

    # 写入校验报告文件
    output_dir = cfg.get("pipeline", {}).get("output_dir", ".")
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(
        output_dir,
        f"校验报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"数据校验报告 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        for c in checks:
            icon = {"ok": "✓", "warn": "⚠", "error": "✗"}.get(c["status"], "?")
            f.write(f"  {icon} {c['name']}: {c['detail']}\n")
        f.write(f"\n通过: {ok_count}  警告: {warn_count}  错误: {error_count}\n")

    if verbose:
        print(f"  报告: {report_path}")

    return {
        "status": "ok",
        "checks": checks,
        "ok_count": ok_count,
        "warn_count": warn_count,
        "error_count": error_count,
        "report_path": report_path,
    }


if __name__ == "__main__":
    cfg = load_config()
    db = PrestoQuery(cfg.get("database", {}))
    db.login()
    result = run(cfg, db, verbose=True)
    print(f"\n结果: {result.get('status')}")
