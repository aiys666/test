# -*- coding: utf-8 -*-
"""验证 ys_mx_ltv_first_loan_cac 里的 fee/houshou_fee/fee_amount/houshou_fee_amount
是否与订单粒度 ground truth 一致。"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pd.set_option("display.width", 250)

# 1) 表是否存在 + 行数
CHK = [
    ("ys_dl_ltv_first_loan_0511", "select count(*) c from mx.ys_dl_ltv_first_loan_0511"),
    ("ys_mx_ltv_ads_cost",        "select count(*) c from mx.ys_mx_ltv_ads_cost"),
    ("ys_mx_ltv_first_loan_cac",  "select count(*) c from mx.ys_mx_ltv_first_loan_cac"),
]

# 2) 边界行: contract_amount 为 0/null 的情况 (全历史 new + if_issue=1)
EDGE = """
select count(*) as total_rows,
       count(case when contract_amount=0 or contract_amount is null then 1 end) as ca_zero_or_null,
       count(case when (contract_amount=0 or contract_amount is null)
                    and (coalesce(haircut_amount,0)+coalesce(should_interest,0)<>0) then 1 end) as ca_zero_with_nums,
       count(case when haircut_amount is null or should_interest is null then 1 end) as ha_si_null
from mx.wxs_application_funnel
where is_reloan='new' and if_issue=1
"""

# 3) 订单粒度 ground truth (全历史, new): 月度 sum(ha)/sum(si)/sum(ca) + 各比例
GT = """
select date_trunc('month', date(r.release_time)) as m,
       sum(r.contract_amount) as ca,
       sum(r.haircut_amount) as ha,
       sum(r.should_interest) as si,
       sum(r.haircut_amount)+sum(r.should_interest) as ha_plus_si,
       sum(r.should_interest)*100.0/sum(r.contract_amount) as interest_rate_pct,
       sum(r.haircut_amount)*100.0/sum(r.contract_amount) as haircut_rate_pct,
       (sum(r.haircut_amount)+sum(r.should_interest))*100.0/sum(r.contract_amount) as fee_pct
from mx.wxs_application_funnel r
where r.is_reloan='new' and r.if_issue=1
group by 1 order by 1
"""

# 4) CAC 表重聚合到月: fee/houshou_fee 的 分子分母 (fee_amount/houshou_fee_amount 是 sum(fee*ca) 的产物)
CAC = """
select ltv_month,
       sum(contract_amount) as ca,
       sum(fee_amount) as fee_amount,
       sum(houshou_fee_amount) as hf_amount,
       sum(fee*contract_amount) as fee_wgt_num,
       sum(houshou_fee*contract_amount) as hf_wgt_num
from mx.ys_mx_ltv_first_loan_cac
group by 1 order by 1
"""

def run(pq, sql, tag):
    df = pq.query(sql, wait_sec=5)
    if isinstance(df, str):
        print(f"  {tag} FAILED:", df[:300]); return None
    print(f"  {tag}: {len(df)} rows")
    return df

def main():
    pq = PrestoQuery(); pq.login(); print("login ok")
    for name, sql in CHK:
        d = run(pq, sql, f"check {name}")
        if isinstance(d, pd.DataFrame):
            print(f"    -> {name} 行数 = {int(d.iloc[0]['c'])}")

    edge = run(pq, EDGE, "edge rows")
    if isinstance(edge, pd.DataFrame):
        for c in edge.columns:
            print(f"    {c} = {int(edge.iloc[0][c])}")

    gt = run(pq, GT, "ground truth")
    cac = run(pq, CAC, "cac re-agg")
    if gt is None or cac is None:
        return

    for col in gt.columns:
        if col != "m": gt[col] = pd.to_numeric(gt[col], errors="coerce")
    for col in cac.columns:
        if col != "ltv_month": cac[col] = pd.to_numeric(cac[col], errors="coerce")
    gt["m"] = pd.to_datetime(gt["m"]).dt.strftime("%Y-%m")
    cac["m"] = pd.to_datetime(cac["ltv_month"]).dt.strftime("%Y-%m")
    cac = cac.rename(columns={"ca": "cac_ca", "fee_amount": "cac_fee_amt",
                              "hf_amount": "cac_hf_amt", "fee_wgt_num": "cac_fee_wgt",
                              "hf_wgt_num": "cac_hf_wgt"})
    m = pd.merge(gt, cac, on="m", how="outer").sort_values("m")

    print("\n月份 | 后收息费率 gt% vs cac% | 砍头 gt% vs (fee%) | fee_amount/ca vs (ha+si)/ca 偏差 | 行数边缘")
    for _, r_ in m.iterrows():
        gt_si_pct = r_["interest_rate_pct"]; gt_ha_pct = r_["haircut_rate_pct"]
        ca = r_["cac_ca"] if pd.notna(r_["cac_ca"]) else r_["ca"]
        cac_hf_pct = (r_["cac_hf_amt"] / ca * 100) if ca else float("nan")
        cac_fee_pct = (r_["cac_fee_amt"] / ca * 100) if ca else float("nan")
        gt_fee_pct = r_["fee_pct"]
        print(f"{r_['m']}  si: gt={gt_si_pct:.4f} cac={cac_hf_pct:.4f} (差{cac_hf_pct-gt_si_pct:+.4f}) "
              f"| ha+si: gt={gt_fee_pct:.4f} cac_fee={cac_fee_pct:.4f} (差{cac_fee_pct-gt_fee_pct:+.4f}) "
              f"| fee_amt/ca={cac_fee_pct:.4f} | 加权round后={(r_['cac_fee_wgt']/ca*100) if ca else float('nan'):.4f}")

if __name__ == "__main__":
    main()
