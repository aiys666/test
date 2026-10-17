# -*- coding: utf-8 -*-
"""对比两种4T7坏账率口径的偏差。

口径A(Excel本息坏账, 不含券): (should_amt_t7 - fact_t7) / contract_t7
    = t7_overdue_amount_4 / t7_should_capit_4
口径B(上午口径, 含券): (4T7逾期本金 + 4T7逾期息费) / 4T7应还本金
    = (t7_overdue_capit_4 + t7_overdue_interest_4) / t7_should_capit_4
"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 40)

SQL = """
SELECT
    date_trunc('month', date(r.release_time)) AS m,
    r.is_reloan,
    count(*)                                   AS cnt,
    sum(r.t7_should_amt_4)                     AS should_amt,       -- 本息应还
    sum(r.t7_should_capit_4)                   AS should_capit,     -- 本金应还
    sum(r.t7_should_interest_4)                AS should_interest,  -- 利息应还
    sum(r.t7_overdue_amount_4)                 AS overdue_amt,      -- 本息逾期(口径A分子)
    sum(r.t7_overdue_capit_4)                  AS overdue_capit,    -- 本金逾期
    sum(r.t7_overdue_interest_4)               AS overdue_interest, -- 利息逾期
    sum(r.t7_coupon_substract_4)               AS coupon_substract  -- 减免及券成本
FROM mx.wxs_application_funnel r
WHERE r.if_issue = 1
  AND r.release_time >= date'2025-01-01'
GROUP BY 1, 2
ORDER BY 1, 2
"""


def div(a, b):
    return (a / b) if b else float("nan")


def main():
    pq = PrestoQuery()
    pq.login()
    print("login ok")

    df = pq.query(SQL, wait_sec=5)
    if isinstance(df, str):
        print("FAILED:", df[:300])
        return

    for c in ["cnt", "should_amt", "should_capit", "should_interest",
              "overdue_amt", "overdue_capit", "overdue_interest", "coupon_substract"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["m"] = pd.to_datetime(df["m"]).dt.strftime("%Y-%m")
    df["rate_A"] = df["overdue_amt"] / df["should_capit"]
    df["rate_B"] = df["overdue_capit"] + df["overdue_interest"]
    df["rate_B"] = df["rate_B"] / df["should_capit"]
    df["diff_pp"] = (df["rate_B"] - df["rate_A"]) * 100
    df["check_eq"] = (df["overdue_amt"] - (df["overdue_capit"] + df["overdue_interest"]))

    print("\n" + "=" * 130)
    print("月份/首复贷 | 笔数 | 本金应还 | 本息逾期(A) | 本金逾期 | 利息逾期 | 本金+利息(B) | 券减免 | A坏账率 | B坏账率 | 偏差(pp) | 恒等差")
    print("=" * 130)
    for _, r in df.iterrows():
        tag = f"{r['m']}/{r['is_reloan']}"
        print(f"{tag:<14} | {r['cnt']:>7,.0f} | {r['should_capit']:>12,.0f} | "
              f"{r['overdue_amt']:>11,.0f} | {r['overdue_capit']:>10,.0f} | "
              f"{r['overdue_interest']:>9,.0f} | {r['overdue_capit']+r['overdue_interest']:>13,.0f} | "
              f"{r['coupon_substract']:>9,.0f} | {r['rate_A']*100:>7.3f}% | {r['rate_B']*100:>7.3f}% | "
              f"{r['diff_pp']:>+8.4f} | {r['check_eq']:>10,.0f}")

    # 总体(不分首复贷, 按月)
    print("\n" + "=" * 130)
    print("全量按月(合并首复贷)")
    print("=" * 130)
    g = df.groupby("m", as_index=False).agg(
        cnt=("cnt", "sum"), should_capit=("should_capit", "sum"),
        overdue_amt=("overdue_amt", "sum"), overdue_capit=("overdue_capit", "sum"),
        overdue_interest=("overdue_interest", "sum"), coupon_substract=("coupon_substract", "sum"))
    g["rate_A"] = g["overdue_amt"] / g["should_capit"]
    g["rate_B"] = (g["overdue_capit"] + g["overdue_interest"]) / g["should_capit"]
    g["diff_pp"] = (g["rate_B"] - g["rate_A"]) * 100
    for _, r in g.iterrows():
        print(f"{r['m']:<8} | {r['cnt']:>7,.0f} | {r['should_capit']:>12,.0f} | "
              f"{r['overdue_amt']:>11,.0f} | {r['overdue_capit']:>10,.0f} | "
              f"{r['overdue_interest']:>9,.0f} | {r['coupon_substract']:>9,.0f} | "
              f"A={r['rate_A']*100:.3f}% | B={r['rate_B']*100:.3f}% | 偏差={r['diff_pp']:+.4f}pp")

    # 券占比参考
    print("\n券减免/本金应还 (近似解释口径A与B的差异来源):")
    for _, r in g.iterrows():
        print(f"  {r['m']}: 券占比={r['coupon_substract']/r['should_capit']*100:.4f}%")


if __name__ == "__main__":
    main()
