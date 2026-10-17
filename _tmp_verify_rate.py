# -*- coding: utf-8 -*-
"""验证两段SQL的 interest_rate / haircut_rate / T7逾期率 是否一致。

- Q1: 用户贴的第一段(权责 SQL2) 原样执行 → 订单粒度真实值(无join)
- Q2: 同一表订单粒度原始sum → 与Q1对照做ground truth
- Q3: 用户贴的第二段(LTV细粒度, 3个LEFT JOIN) 外层重聚合到月 → 检验join fan-out是否放大sum
- Q4: fan-out隔离: base vs 各join单独 vs 全join 的行数, 定位放大来源
"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)

COMMON_FILTER = "r.is_reloan = 'new' and r.if_issue=1 and r.release_time >= date'2025-01-01'"

# ── Q1: 第一段SQL(权责 SQL2) 原样 ──
Q1 = """
select
    date_trunc('month', date(r.release_time)) as qz_month,
    r.is_reloan,
    sum(loan_cycle*contract_amount)*1.0/sum(contract_amount) as avg_loan_cycle,
    max(case when r.loan_cycle <120 then r.loan_cycle else null end) as max_loan_cycle,
    sum(r.should_interest)*1.0000/sum(r.contract_amount)   as interest_rate,
    sum(r.haircut_amount)*1.0000/sum(r.contract_amount)   as haircut_rate,
    case when sum(r.t7_should_capit_4)=0 then 0 else sum(r.t7_overdue_capit_4)*1.0000/sum(r.t7_should_capit_4) end as capit_bad_rate,
    case when sum(r.t7_should_amt_4)=0 then 0 else sum(r.t7_overdue_amount_4)*1.0000/sum(r.t7_should_amt_4) end as amt_bad_rate,
    case when sum(r.t7_should_interest_4)=0 then 0 else sum(r.t7_overdue_interest_4)*1.0000/sum(r.t7_should_interest_4) end as interest_bad_rate,
    sum(r.fact_fine) as fact_fine
from mx.wxs_application_funnel r
where  r.if_issue=1
and r.release_time>=date'2025-01-01'
GROUP BY 1,2
"""

# ── Q2: 订单粒度原始sum (ground truth, 仅new) ──
Q2 = """
select date_trunc('month', date(r.release_time)) as qz_month,
       sum(r.contract_amount) as ca,
       sum(r.haircut_amount) as ha,
       sum(r.should_interest) as si,
       sum(r.t7_should_amt_4) as s7,
       sum(r.t7_overdue_amount_4) as o7,
       sum(r.t7_should_capit_4) as s7c,
       sum(r.t7_overdue_capit_4) as o7c,
       sum(r.t7_should_interest_4) as s7i,
       sum(r.t7_overdue_interest_4) as o7i,
       count(*) as base_rows,
       count(distinct r.camera_id) as base_biz
from mx.wxs_application_funnel r
where {f}
group by 1
order by 1
""".format(f=COMMON_FILTER)

# ── Q3: 第二段SQL(3 JOIN) 外层重聚合到月 ──
Q3_INNER = """
select
    date_trunc('month', date(r.release_time)) as ltv_month,
    r.contract_amount, r.haircut_amount, r.should_interest,
    r.t7_should_amt_4, r.t7_overdue_amount_4,
    r.t7_should_capit_4, r.t7_overdue_capit_4,
    r.t7_should_interest_4, r.t7_overdue_interest_4,
    r.camera_id as biz_id,
    t.camera_id as t_cam, f7.biz_id as f7_biz, att.mid as att_mid
from mx.wxs_application_funnel r
left join ods.s02_loan t on r.camera_id=t.camera_id
left join mx.report_application_funnel7_table f7 on r.camera_id = cast(f7.biz_id as bigint)
left join mx.gm_attribution_detail att on cast(r.cust_id as bigint) = att.mid
where {f}
""".format(f=COMMON_FILTER)

Q3 = """
select ltv_month,
       sum(contract_amount) as ca, sum(haircut_amount) as ha, sum(should_interest) as si,
       sum(t7_should_amt_4) as s7, sum(t7_overdue_amount_4) as o7,
       sum(t7_should_capit_4) as s7c, sum(t7_overdue_capit_4) as o7c,
       sum(t7_should_interest_4) as s7i, sum(t7_overdue_interest_4) as o7i,
       count(*) as joined_rows,
       count(distinct biz_id) as joined_biz,
       count(distinct t_cam) as t_cam_dist,
       count(distinct f7_biz) as f7_biz_dist,
       count(distinct att_mid) as att_mid_dist
from (
{}
) x
group by 1
order by 1
""".format(Q3_INNER)

# ── Q4: fan-out 隔离 (行数) ──
Q4 = [
    ("base_only", """select count(*) as rows_, count(distinct r.camera_id) as biz_
                     from mx.wxs_application_funnel r where {f}""".format(f=COMMON_FILTER)),
    ("s02_loan", """select count(*) as rows_, count(distinct r.camera_id) as biz_
                    from mx.wxs_application_funnel r
                    left join ods.s02_loan t on r.camera_id=t.camera_id
                    where {f}""".format(f=COMMON_FILTER)),
    ("funnel7", """select count(*) as rows_, count(distinct r.camera_id) as biz_
                   from mx.wxs_application_funnel r
                   left join mx.report_application_funnel7_table f7 on r.camera_id = cast(f7.biz_id as bigint)
                   where {f}""".format(f=COMMON_FILTER)),
    ("attribution", """select count(*) as rows_, count(distinct r.camera_id) as biz_
                       from mx.wxs_application_funnel r
                       left join mx.gm_attribution_detail att on cast(r.cust_id as bigint) = att.mid
                       where {f}""".format(f=COMMON_FILTER)),
    ("all_3", """select count(*) as rows_, count(distinct r.camera_id) as biz_
                 from mx.wxs_application_funnel r
                 left join ods.s02_loan t on r.camera_id=t.camera_id
                 left join mx.report_application_funnel7_table f7 on r.camera_id = cast(f7.biz_id as bigint)
                 left join mx.gm_attribution_detail att on cast(r.cust_id as bigint) = att.mid
                 where {f}""".format(f=COMMON_FILTER)),
]

def run(pq, sql, tag):
    print(f"\n=== {tag} ===")
    df = pq.query(sql, wait_sec=5)
    if isinstance(df, str):
        print("  FAILED:", df[:300])
        return None
    print(f"  rows={len(df)}")
    return df

def main():
    pq = PrestoQuery()
    pq.login()
    print("login ok")

    d1 = run(pq, Q1, "Q1 第一段SQL原样")
    d2 = run(pq, Q2, "Q2 订单粒度ground truth(仅new)")
    d3 = run(pq, Q3, "Q3 第二段SQL(3JOIN)重聚合(仅new)")
    q4 = []
    for name, sql in Q4:
        df = run(pq, sql, "Q4 fan-out隔离: " + name)
        if isinstance(df, pd.DataFrame):
            q4.append((name, df))

    # ── 输出对比表 ──
    if d2 is not None and d3 is not None:
        a = d2.copy(); b = d3.copy()
        num_cols = ["ca", "ha", "si", "s7", "o7", "s7c", "o7c", "s7i", "o7i"]
        for col in num_cols:
            a[col] = pd.to_numeric(a[col], errors="coerce")
            b[col] = pd.to_numeric(b[col], errors="coerce")
        a["base_rows"] = pd.to_numeric(a.get("base_rows"), errors="coerce")
        b["joined_rows"] = pd.to_numeric(b.get("joined_rows"), errors="coerce")
        a["m"] = pd.to_datetime(a["qz_month"]).dt.strftime("%Y-%m")
        b["m"] = pd.to_datetime(b["ltv_month"]).dt.strftime("%Y-%m")
        m = pd.merge(a, b, on="m", suffixes=("_gt", "_jt"))
        print("\n" + "=" * 100)
        print("月份 | 订单粒度(gt) vs 3JOIN后(jt) 原始sum 对比")
        print("=" * 100)
        def div(a, b):
            return (a / b) if b else float("nan")

        for _, r_ in m.iterrows():
            print(f"{r_['m']}  ca  gt={r_['ca_gt']:,.0f} jt={r_['ca_jt']:,.0f} 倍={div(r_['ca_jt'],r_['ca_gt']):.3f} "
                  f"| si gt={r_['si_gt']:,.0f} jt={r_['si_jt']:,.0f} 倍={div(r_['si_jt'],r_['si_gt']):.3f} "
                  f"| rows base={r_['base_rows']:,.0f} joined={r_['joined_rows']:,.0f}")
            print(f"      interest_rate gt={div(r_['si_gt'],r_['ca_gt'])*100:.3f}%  jt={div(r_['si_jt'],r_['ca_jt'])*100:.3f}%")
            print(f"      haircut_rate  gt={div(r_['ha_gt'],r_['ca_gt'])*100:.3f}%  jt={div(r_['ha_jt'],r_['ca_jt'])*100:.3f}%")
            print(f"      amt_bad(T7)   gt={div(r_['o7_gt'],r_['s7_gt'])*100:.3f}%  jt={div(r_['o7_jt'],r_['s7_jt'])*100:.3f}%")
            print(f"      capit_bad(T7) gt={div(r_['o7c_gt'],r_['s7c_gt'])*100:.3f}%  jt={div(r_['o7c_jt'],r_['s7c_jt'])*100:.3f}%")
            print(f"      int_bad(T7)   gt={div(r_['o7i_gt'],r_['s7i_gt'])*100:.3f}%  jt={div(r_['o7i_jt'],r_['s7i_jt'])*100:.3f}%")
        print("=" * 100)

    if q4:
        print("\nfan-out 行数隔离:")
        base_rows = None
        for name, df in q4:
            if name == "base_only":
                base_rows = int(df.iloc[0]["rows_"]); base_biz = int(df.iloc[0]["biz_"])
                print(f"  base_only     : rows={base_rows:,.0f}  distinct_biz={base_biz:,.0f}")
        for name, df in q4:
            if name == "base_only":
                continue
            rows = int(df.iloc[0]["rows_"]); biz = int(df.iloc[0]["biz_"])
            mult = rows / base_rows if base_rows else 0
            print(f"  +{name:<13}: rows={rows:,.0f}  distinct_biz={biz:,.0f}  放大倍数={mult:.3f}")

if __name__ == "__main__":
    main()
