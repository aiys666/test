# -*- coding: utf-8 -*-
"""首贷逐月金额对比：逻辑1(funnel直查) vs 逻辑2(0511快照表)
指标: 后收金额=sum(should_interest), 砍头金额=sum(haircut_amount),
      后收+砍头=sum(should_interest+haircut_amount), 放款合同金额=sum(contract_amount)
"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

F_NEW = "is_reloan='new' and if_issue=1"

L1 = f"""
select date_trunc('month', date(release_time)) as m,
       sum(contract_amount) as ca,
       sum(haircut_amount) as ha,
       sum(should_interest) as si
from mx.wxs_application_funnel
where {F_NEW}
group by 1 order by 1
"""

L2 = f"""
select ltv_month as m,
       sum(contract_amount) as ca,
       sum(haircut_amount) as ha,
       sum(should_interest) as si
from mx.ys_dl_ltv_first_loan_0511
group by 1 order by 1
"""

# 顺带: CAC表里的 fee_amount / houshou_fee_amount 与 0511 原值差异(round截断)
CAC = """
select ltv_month as m,
       sum(fee_amount) as fee_amt,
       sum(houshou_fee_amount) as hf_amt
from mx.ys_mx_ltv_first_loan_cac
group by 1 order by 1
"""

def run(pq, sql, tag):
    df = pq.query(sql, wait_sec=5)
    if isinstance(df, str):
        print(f"  {tag} FAILED:", df[:300]); return None
    for col in df.columns:
        if col != "m":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["m"] = pd.to_datetime(df["m"]).dt.strftime("%Y-%m")
    print(f"  {tag}: {len(df)} rows")
    return df

def fmt(v, neg=False):
    return f"{v:,.0f}" if pd.notna(v) else "     -"

def main():
    pq = PrestoQuery(); pq.login(); print("login ok")
    d1 = run(pq, L1, "逻辑1 funnel直查")
    d2 = run(pq, L2, "逻辑2 0511快照")
    d3 = run(pq, CAC, "CAC表(round后)")
    if d1 is None or d2 is None:
        return
    m = pd.merge(d1, d2, on="m", suffixes=("_l1", "_l2"), how="outer").sort_values("m")
    cac = d3.rename(columns={"fee_amt": "cac_fee", "hf_amt": "cac_hf"})
    m = pd.merge(m, cac, on="m", how="left")

    print("\n首贷逐月金额对比 (单位: 本地币/千? 直接原值)   Δ = 逻辑2 - 逻辑1")
    hdr = f"{'月份':8} {'放款合同额 L1':>13} {'L2':>13} {'Δ':>12} | {'后收金额 L1':>12} {'L2':>12} {'Δ':>11} | {'砍头金额 L1':>12} {'L2':>12} {'Δ':>11}"
    print(hdr)
    print("-" * len(hdr))
    for _, r_ in m.iterrows():
        print(f"{r_['m']:8} {fmt(r_['ca_l1']):>13} {fmt(r_['ca_l2']):>13} {fmt(r_['ca_l2']-r_['ca_l1']):>12}"
              f" | {fmt(r_['si_l1']):>12} {fmt(r_['si_l2']):>12} {fmt(r_['si_l2']-r_['si_l1']):>11}"
              f" | {fmt(r_['ha_l1']):>12} {fmt(r_['ha_l2']):>12} {fmt(r_['ha_l2']-r_['ha_l1']):>11}")
    # 合计
    def tot(col):
        return m[col].sum()
    print("-" * len(hdr))
    print(f"{'合计':8} {fmt(tot('ca_l1')):>13} {fmt(tot('ca_l2')):>13} {fmt(tot('ca_l2')-tot('ca_l1')):>12}"
          f" | {fmt(tot('si_l1')):>12} {fmt(tot('si_l2')):>12} {fmt(tot('si_l2')-tot('si_l1')):>11}"
          f" | {fmt(tot('ha_l1')):>12} {fmt(tot('ha_l2')):>12} {fmt(tot('ha_l2')-tot('ha_l1')):>11}")

    # 后收+砍头
    print("\n后收+砍头金额 对比:")
    hdr2 = f"{'月份':8} {'后收+砍头 L1':>14} {'L2':>14} {'Δ':>13} | {'CAC.fee_amount':>15} {'CAC后收金额':>12} {'CAC砍头金额':>12}"
    print(hdr2)
    print("-" * len(hdr2))
    for _, r_ in m.iterrows():
        hs1 = r_["si_l1"] + r_["ha_l1"]; hs2 = r_["si_l2"] + r_["ha_l2"]
        cac_ha = r_["cac_fee"] - r_["cac_hf"] if pd.notna(r_["cac_fee"]) else float("nan")
        print(f"{r_['m']:8} {fmt(hs1):>14} {fmt(hs2):>14} {fmt(hs2-hs1):>13} | {fmt(r_['cac_fee']):>15} {fmt(r_['cac_hf']):>12} {fmt(cac_ha):>12}")
    hs1_t = tot("si_l1") + tot("ha_l1"); hs2_t = tot("si_l2") + tot("ha_l2")
    print("-" * len(hdr2))
    print(f"{'合计':8} {fmt(hs1_t):>14} {fmt(hs2_t):>14} {fmt(hs2_t-hs1_t):>13} | {fmt(tot('cac_fee')):>15} {fmt(tot('cac_hf')):>12} {fmt(tot('cac_fee')-tot('cac_hf')):>12}")

if __name__ == "__main__":
    main()
