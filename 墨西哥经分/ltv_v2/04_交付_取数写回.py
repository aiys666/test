# -*- coding: utf-8 -*-
"""
LTV v2 交付: 从 Presto 分片取数 → 写入 Excel 副本（不覆盖原文件）。

为什么必须分片:
    adhoc 查询接口把结果集硬顶在 10,000 行, 单次 query() 拿到 1 万行就断了。
    这里按「月份/周次 → 渠道/wob」逐级下钻, 用 limit 9000 探测是否被截断,
    每片确认拿全后再拼接。

用法:
    python 04_交付_取数写回.py          # 月版 + 周版
    python 04_交付_取数写回.py m        # 只月版
    python 04_交付_取数写回.py w        # 只周版
"""
import hashlib
import os
import re
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
sys.path.insert(0, HERE)

from mexico_presto import PrestoQuery          # noqa: E402
from _xlsx import Workbook                     # noqa: E402
from _writeback import write_sheet             # noqa: E402

BASE = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险"
MAXROWS = 9000          # 低于接口 10,000 上限，留出探测余量
CACHE_DIR = os.path.join(HERE, "_chunk_cache")   # 分片缓存, 中断后可续跑

JOBS = {
    "m": dict(
        tag="月版",
        src=os.path.join(BASE, "墨西哥LTV更新_20260921.xlsx"),
        dst=os.path.join(BASE, "墨西哥LTV更新_20260927_v2.xlsx"),
        sheets={
            "数据源-首贷": ("mx.ys_ltv_v2_m_first_loan_cac", ["ltv_month", "app_channel_name"]),
            "数据源-复贷": ("mx.ys_ltv_v2_m_final", ["ltv_month", "wob"]),
        },
    ),
    "w": dict(
        tag="周版",
        src=os.path.join(BASE, "墨西哥LTV更新_20260919 - 小金额-周.xlsx"),
        dst=os.path.join(BASE, "墨西哥LTV更新_20260927 - 小金额-周_v2.xlsx"),
        sheets={
            "数据源-首贷": ("mx.ys_ltv_v2_w_first_loan_cac", ["ltv_week", "app_channel_name"]),
            "数据源-复贷": ("mx.ys_ltv_v2_w_final", ["ltv_week", "wob"]),
        },
    ),
}


def sql_lit(v):
    """把 Python 值转成 Presto 字面量。"""
    if v is None:
        return "null"
    s = str(v)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return f"date '{s}'"
    if re.match(r"^-?\d+(\.\d+)?$", s):
        return s
    return "'" + s.replace("'", "''") + "'"


def fetch_all(pq, table, keys):
    """按 keys 逐级下钻分片, 取全表。

    分片落盘缓存（CACHE_DIR）。整个表要 200+ 次请求、跑十几分钟，
    任何一次抖动都会让前功尽弃；命中缓存的分片直接复用。
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = re.sub(r"[^\w]+", "_", f"{table}__{'_'.join(keys)}")
    out, queue, nreq, ncached = [], [("", 0)], 0, 0
    t0 = time.time()

    def cpath(where):
        # 必须用稳定摘要: 内置 hash() 对字符串按进程加盐, 换个进程就换文件名, 缓存全失效
        h = hashlib.md5(where.encode("utf-8")).hexdigest()[:16]
        return os.path.join(CACHE_DIR, f"{safe}__{h}.pkl")

    def q(sql, tries=3):
        last = None
        for i in range(tries):
            r = pq.query(sql)
            if not isinstance(r, str):
                return r
            last = r
            print(f"      · 重试 {i+1}/{tries}: {r[:80]}", flush=True)
            time.sleep(3 + i * 5)
        return last

    while queue:
        where, lvl = queue.pop(0)
        f = cpath(where)
        if os.path.exists(f):
            try:
                out.append(pd.read_pickle(f))
                ncached += 1
                continue
            except Exception:
                os.remove(f)
        sql = (f"select * from {table}"
               + (f" where {where}" if where else "")
               + f" limit {MAXROWS}")
        df = q(sql)
        nreq += 1
        if isinstance(df, str):
            raise RuntimeError(f"{table} 取数失败: {df[:200]}")
        if len(df) < MAXROWS:
            df.to_pickle(f)
            out.append(df)
            print(f"    [{len(out):3d}] {table} {where or '(全表)'} → {len(df):,} 行"
                  f"  ({time.time()-t0:.0f}s)", flush=True)
            continue
        if lvl >= len(keys):
            raise RuntimeError(f"{table} 分片到底仍超限: {where}")
        col = keys[lvl]
        ks = q(f"select distinct {col} as k from {table}"
               + (f" where {where}" if where else ""))
        if isinstance(ks, str):
            raise RuntimeError(f"{table} 取分片键失败: {ks[:200]}")
        for v in ks["k"]:
            cond = f"{col} = {sql_lit(v)}"
            queue.append(((where + " and " + cond) if where else cond, lvl + 1))
    df = pd.concat(out, ignore_index=True)
    # 分片取数最危险的失败模式是"悄悄少拿"（接口 10,000 行硬顶），
    # 这里用服务端 count(*) 兜底对账，不一致直接报错而不是写进 Excel。
    chk = pq.query(f"select count(*) as n from {table}")
    if isinstance(chk, str):
        raise RuntimeError(f"{table} 行数校验失败: {chk[:200]}")
    expect = int(chk["n"].iloc[0])
    if expect != len(df):
        raise RuntimeError(
            f"{table} 行数不符: 服务端 {expect:,} vs 分片取回 {len(df):,}（差 {expect-len(df):,}）")
    print(f"  ✓ {table} 共 {len(df):,} 行 / {len(out)} 片 / {nreq} 次请求"
          f" (缓存命中 {ncached})  [已对账 count(*)] ({time.time()-t0:.0f}s)", flush=True)
    return df


def run(pq, key):
    job = JOBS[key]
    print(f"\n{'='*70}\n{job['tag']}\n  源: {os.path.basename(job['src'])}"
          f"\n  出: {os.path.basename(job['dst'])}\n{'='*70}")

    if not os.path.exists(job["src"]):
        print("  !! 源文件不存在, 跳过")
        return False

    wb = Workbook(job["src"])
    sheet_to_xml = {s: wb.sheets[s] for s in job["sheets"]}
    wb.close()

    df_map = {}
    for sheet, (table, keys) in job["sheets"].items():
        print(f"  取数 {table} ...")
        df_map[sheet] = fetch_all(pq, table, keys)

    write_sheet(job["src"], job["dst"], sheet_to_xml, df_map)
    return True


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "mw"
    keys = [k for k in ("m", "w") if k in which]
    pq = PrestoQuery()
    pq.login()
    ok = all(run(pq, k) for k in keys)
    print("\n全部完成" if ok else "\n有失败")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
