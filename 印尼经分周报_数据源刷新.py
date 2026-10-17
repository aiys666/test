# -*- coding: utf-8 -*-
"""
印尼经分周报 数据源刷新 主脚本
===============================
每周运行一次，自动完成：
  1. Presto 查询三个数据源（进件/投放/复贷）
  2. 替换周报模板中对应的三个数据源 sheet（文本自动转数值/日期转序列号）
  3. 给透视表缓存加 refreshOnLoad（Excel/WPS 打开文件时自动刷新透视表）
  4. 输出带时间戳的新周报文件，模板原文件不动

依赖:
  - indonesia_presto.py (同目录, Presto 登录+查询)
  - 印尼经分周报_数据源刷新_zip手术.py (同目录, zip 手术核心)

使用:
  python 印尼经分周报_数据源刷新.py
  可选参数:
    --template <路径>   周报模板(默认取 code 目录旁 8月预估 下的 V1)
    --outdir <目录>     输出目录(默认模板所在目录)
    --limit <N>         查询行数上限(默认 100000)
"""
import sys
import os
import time
import glob
import argparse
import shutil
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from indonesia_presto import PrestoQuery
from 印尼经分周报_数据源刷新_zip手术 import refresh_data_sources

# 默认模板目录（V1 周报所在目录）；不指定 --template 时自动取这里最新的模板
DEFAULT_TEMPLATE_DIR = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\8月预估"


def find_latest_template():
    """自动查找模板目录中最新修改的 印尼经分周报_*.xlsx（排除输出文件）。"""
    pattern = os.path.join(DEFAULT_TEMPLATE_DIR, "印尼经分周报_*.xlsx")
    candidates = []
    for f in glob.glob(pattern):
        base = os.path.basename(f)
        # 排除脚本自己生成的"数据源刷新"输出文件，避免把自己当模板
        if "数据源刷新" in base or base.startswith("~$"):
            continue
        candidates.append(f)
    if not candidates:
        return None
    # 按修改时间取最新
    latest = max(candidates, key=lambda f: os.path.getmtime(f))
    return latest

QUERIES = {
    "数据源（进件）": ("select * from ind.ba_apply_should_result_week_new_ys "
                   "where app_month>='2026-01-01' limit {limit}"),
    "投放数据源": ("select * from ind.ba_install_apply_result_ys "
              "where ad_date>=date'2026-01-01' limit {limit}"),
    "复贷数据源": ("select * from ind.ba_apply_should_result_week_old_ys "
               "where app_month>='2026-01-01' limit {limit}"),
}


def main():
    ap = argparse.ArgumentParser(description="印尼经分周报数据源刷新")
    ap.add_argument("--template", default=None, help="指定模板路径；不指定则自动选目录里最新的模板")
    ap.add_argument("--outdir", default=None, help="输出目录，默认与模板同目录")
    ap.add_argument("--limit", type=int, default=100000)
    args = ap.parse_args()

    # 模板解析：优先用户指定，否则自动找最新
    if args.template:
        template = args.template
        if not os.path.exists(template):
            print(f"[X] 模板不存在: {template}")
            sys.exit(1)
    else:
        template = find_latest_template()
        if template is None:
            print(f"[X] 在 {DEFAULT_TEMPLATE_DIR} 下未找到 印尼经分周报_*.xlsx 模板")
            print("    请用 --template 指定模板路径")
            sys.exit(1)
        print(f"[i] 自动选用最新模板: {os.path.basename(template)}")
    outdir = args.outdir or os.path.dirname(template)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(outdir, f"印尼经分周报_{ts}_数据源刷新.xlsx")

    t_all = time.time()
    print("== 1/4 Presto 登录 ==")
    pq = PrestoQuery()
    pq.login_process()

    print("== 2/4 查询三个数据源 ==")
    data_map = {}
    for name, sql_tpl in QUERIES.items():
        sql = sql_tpl.format(limit=args.limit)
        # 重试机制：Presto 偶发"查询结果过期"，最多重试3次（含重新登录）
        df = None
        for attempt in range(1, 4):
            try:
                t0 = time.time()
                df = pq.submit_query(sql, wait_sec=2)
            except Exception as e:
                df = None
                print(f"  [!] {name} 第{attempt}次异常: {e}")
            if df is not None and not isinstance(df, str):
                break
            if attempt < 3:
                print(f"  [!] {name} 第{attempt}次失败({str(df)[:60]})，重新登录重试...")
                time.sleep(3)
                pq.login_process()
        if df is None or isinstance(df, str):
            print(f"  [X] {name} 查询失败(重试3次后): {df}")
            sys.exit(1)
        print(f"  [OK] {name}: {df.shape} 耗时 {time.time()-t0:.1f}s")
        data_map[name] = df

    print(f"== 3/4 复制模板并做 zip 手术 (总查询耗时 {time.time()-t_all:.1f}s) ==")
    shutil.copy2(template, out_path)
    refresh_data_sources(out_path, out_path, data_map, log=print)

    print(f"== 4/4 完成 ==")
    print(f"输出文件: {out_path} ({os.path.getsize(out_path)/1024/1024:.1f} MB)")
    print("提示: 用 Excel/WPS 打开文件，透视表将自动刷新；若未自动刷新，"
          "右键透视表 -> 刷新，或按 Ctrl+Alt+F5 全部刷新后另存。")


if __name__ == "__main__":
    main()
