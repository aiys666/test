#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
经营计划自动化 — 主编排器
==========================

用法:
  python pipeline.py                 # 执行 config.yaml 中启用的全部步骤
  python pipeline.py --step 2        # 只执行步骤 2
  python pipeline.py --steps 1,3,4   # 执行步骤 1,3,4
  python pipeline.py --dry-run       # 预检查（验证配置，不实际执行）
  python pipeline.py --skip-db       # 跳过所有数据库操作（只生成本地文件）

步骤说明:
  Step 1: 风险坏账数据转化 → 读取 Excel → 生成 CSV + SQL
  Step 2: 首贷+复贷进件量预估 → 查询 DB → MOB模型 → 生成预估 Excel
  Step 3: 权责月度预估 → 模板写入 → 生成预估 Excel
  Step 4: 预估数据入库 → Excel 解析 → 写入 Presto 表
  Step 5: 数据校验 → 查询 DB → 输出校验报告
"""

import os
import sys
import time
import argparse
from datetime import datetime

# Windows GBK 控制台 UTF-8 兼容
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 确保可以找到子模块
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core.config import load_config, validate_config, get_step_enabled
from core.db import PrestoQuery


# ═══════════════════════════════════════════════════════════════
# 步骤注册表
# ═══════════════════════════════════════════════════════════════

STEP_REGISTRY = {
    1: {
        "name": "风险坏账数据转化",
        "module": "steps.step1_risk_bad_debt",
        "needs_db": False,
        "description": "读取风险产品坏账.xlsx → 生成 CSV + INSERT SQL",
    },
    2: {
        "name": "首贷+复贷进件量预估",
        "module": "steps.step2_reloan_forecast",
        "needs_db": True,
        "description": "查询Presto数据库 → MOB转化率模型 → 生成预估Excel",
    },
    3: {
        "name": "权责月度预估",
        "module": "steps.step3_accrual_estimate",
        "needs_db": False,
        "description": "加载Excel模板 → 写入风险死数 → 生成预估Excel",
    },
    4: {
        "name": "预估数据入库",
        "module": "steps.step4_db_import",
        "needs_db": True,
        "description": "读取权责预估Excel → 解析数据 → 写入 ba_loan_forecast 表",
    },
    5: {
        "name": "数据校验",
        "module": "steps.step5_validation",
        "needs_db": True,
        "description": "查询数据库表 → 对比预期值 → 输出校验报告",
    },
}


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def print_banner():
    """打印横幅"""
    print()
    print("=" * 70)
    print("  经营计划自动化系统 v1.0")
    print("  印尼权责预估 · 复贷进件预估 · 坏账转化 · 数据入库")
    print("=" * 70)


def print_step_header(step_num: int, name: str):
    """打印步骤标题"""
    print()
    print("-" * 60)
    print(f"  [Step {step_num}] {name}")
    print("-" * 60)


def print_summary(results: dict):
    """打印执行摘要"""
    print()
    print("=" * 70)
    print("  执行摘要")
    print("=" * 70)

    total = len(results)
    ok = sum(1 for r in results.values() if r.get("status") == "ok")
    err = sum(1 for r in results.values() if r.get("status") == "error")
    skip = sum(1 for r in results.values() if r.get("status") == "skipped")

    for step_num, result in results.items():
        status = result.get("status", "?")
        icon = {"ok": "✓", "error": "✗", "skipped": "○"}.get(status, "?")
        name = STEP_REGISTRY.get(step_num, {}).get("name", f"Step {step_num}")
        extra = ""
        if status == "ok":
            if "records" in result:
                extra = f" ({result['records']} 条记录)"
            elif "output_file" in result:
                fname = os.path.basename(result["output_file"])
                extra = f" → {fname}"
        elif status == "error":
            extra = f" — {result.get('message', '未知错误')}"
        print(f"  {icon} Step {step_num} {name}{extra}")

    print(f"\n  总计: {total} 步 | ✓ 成功: {ok} | ✗ 失败: {err} | ○ 跳过: {skip}")
    print(f"  耗时: {results.get('_elapsed', 'N/A')}")
    print("=" * 70)
    print()


# ═══════════════════════════════════════════════════════════════
# 主逻辑
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="经营计划自动化 — 一键执行全流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python pipeline.py                  # 执行全部启用的步骤
  python pipeline.py --step 2         # 只执行步骤2
  python pipeline.py --steps 1,3,4    # 执行步骤1,3,4
  python pipeline.py --dry-run        # 只校验配置不执行
  python pipeline.py --skip-db        # 跳过数据库操作
        """,
    )
    parser.add_argument("--step", type=int, help="只执行指定步骤 (1-5)")
    parser.add_argument("--steps", type=str, help="执行指定步骤列表, 如 '1,3,4'")
    parser.add_argument("--dry-run", action="store_true", help="预检查模式，不实际执行")
    parser.add_argument("--skip-db", action="store_true", help="跳过所有数据库操作")
    parser.add_argument("--config", type=str, help="指定配置文件路径")
    args = parser.parse_args()

    print_banner()

    # ── 1. 加载配置 ────────────────────────────────────
    print("\n[初始化] 加载配置...")
    try:
        cfg = load_config(args.config)
        print(f"  配置文件: {args.config or os.path.join(BASE_DIR, 'config.yaml')}")
        print(f"  预估月份: {cfg.get('months', {}).get('current', 'N/A')}"
              f" → {cfg.get('months', {}).get('next', 'N/A')}")
    except FileNotFoundError as e:
        print(f"\n  [ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  [ERROR] 配置加载失败: {e}")
        sys.exit(1)

    # ── 2. 校验配置 ────────────────────────────────────
    print("\n[校验] 检查配置完整性...")
    errors = validate_config(cfg)
    if errors:
        print("  ⚠ 发现以下配置问题:")
        for e in errors:
            print(f"    - {e}")
        if args.dry_run:
            sys.exit(1)
        print("  将继续执行，但可能出现错误...")
    else:
        print("  ✓ 配置校验通过")

    # ── 3. 确定要执行的步骤 ──────────────────────────────
    if args.step:
        steps_to_run = [args.step]
    elif args.steps:
        steps_to_run = [int(s.strip()) for s in args.steps.split(",")]
    else:
        steps_to_run = [s for s in sorted(STEP_REGISTRY.keys())
                        if get_step_enabled(cfg, s)]

    # 验证步骤编号
    for s in steps_to_run:
        if s not in STEP_REGISTRY:
            print(f"\n  [ERROR] 无效步骤: {s} (可选: 1-5)")
            sys.exit(1)

    print(f"\n[计划] 将执行步骤: {steps_to_run}")
    if args.skip_db:
        print("  (跳过数据库操作模式)")
    if args.dry_run:
        print("  (干跑模式)\n")
        print("=" * 70)
        for s in steps_to_run:
            info = STEP_REGISTRY[s]
            db_tag = " [需DB]" if info["needs_db"] else ""
            print(f"  Step {s}: {info['name']}{db_tag}")
            print(f"         {info['description']}")
        print("=" * 70)
        print("\n干跑完成，未实际执行。")
        return

    # ── 4. 初始化数据库连接 ──────────────────────────────
    db = None
    needs_db = any(STEP_REGISTRY[s]["needs_db"] for s in steps_to_run)
    if needs_db and not args.skip_db:
        print("\n[数据库] 初始化连接...")
        db = PrestoQuery(cfg.get("database", {}))
        if db.login(verbose=True):
            print("  ✓ 数据库连接成功")
        else:
            print("  [WARN] 数据库连接失败，依赖DB的步骤将报错")
    elif args.skip_db:
        print("\n[数据库] 已跳过数据库连接 (--skip-db)")

    # ── 5. 逐步执行 ────────────────────────────────────
    results = {}
    t_start = datetime.now()

    for step_num in steps_to_run:
        info = STEP_REGISTRY[step_num]
        print_step_header(step_num, info["name"])

        # 检查是否需要数据库
        if info["needs_db"] and (db is None or args.skip_db):
            print(f"  [跳过] 此步骤需要数据库连接，但数据库不可用")
            results[step_num] = {
                "status": "skipped",
                "message": "数据库不可用",
            }
            continue

        # 动态加载并执行步骤模块
        try:
            module = __import__(info["module"], fromlist=["run"])
            t0 = time.time()
            step_result = module.run(cfg, db, verbose=True)
            elapsed = time.time() - t0

            step_result["_elapsed"] = f"{elapsed:.1f}s"
            results[step_num] = step_result

            if step_result.get("status") == "ok":
                print(f"\n  ✓ Step {step_num} 完成 (耗时 {elapsed:.1f}s)")

                # 将 Step 3 的输出传递给 Step 4
                if step_num == 3 and step_result.get("output_file"):
                    cfg["_step3_output_file"] = step_result["output_file"]

            else:
                print(f"\n  ✗ Step {step_num} 失败: {step_result.get('message', '未知错误')}")
                # 询问是否继续
                cont = input("\n  是否继续执行后续步骤? [Y/n]: ").strip().lower()
                if cont == "n":
                    print("  用户中止执行")
                    break

        except ImportError as e:
            print(f"\n  [ERROR] 模块加载失败: {e}")
            results[step_num] = {"status": "error", "message": str(e)}
        except Exception as e:
            print(f"\n  [ERROR] 步骤执行异常: {e}")
            results[step_num] = {"status": "error", "message": str(e)}
            import traceback
            traceback.print_exc()

    # ── 6. 执行摘要 ────────────────────────────────────
    t_end = datetime.now()
    results["_elapsed"] = f"{(t_end - t_start).total_seconds():.1f}s"
    print_summary(results)


if __name__ == "__main__":
    main()
