# -*- coding: utf-8 -*-
"""复贷LTV代码诊断：验证 join 匹配、fan-out、空匹配来源、limit 截断风险。"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

def run(pq, sql, tag):
    df = pq.query(sql, wait_sec=5)
    if isinstance(df, str):
        print(f"  {tag} FAILED:", df[:300]); return None
    print(f"  {tag}: {len(df)} rows")
    return df

def main():
    pq = PrestoQuery(); pq.login(); print("login ok\n")

    # 1) 首贷表唯一性
    run(pq, """
    select count(*) as total_rows, count(distinct biz_id) as biz, count(distinct mid) as mids
    from mx.ys_dl_ltv_first_loan_0511
    """, "Q1 首贷表唯一性")

    # 2) 首贷表里 mid 重复的行数（若>0 → join 会放大）
    run(pq, """
    select count(*) as dup_mid_cnt
    from (
      select mid from mx.ys_dl_ltv_first_loan_0511 group by 1 having count(*)>1
    ) t
    """, "Q2 首贷表重复mid数")

    # 3) 复贷(老客)订单总量
    run(pq, """
    select count(*) as old_loans, count(distinct camera_id) as old_biz, count(distinct cast(cust_id as bigint)) as old_mids
    from mx.wxs_application_funnel where is_reloan='old' and if_issue=1
    """, "Q3 funnel老客订单总量")

    # 4) double_loan_0511 行数与业务数
    run(pq, """
    select count(*) as rows_, count(distinct biz_id) as biz, count(distinct mid) as mids
    from mx.ys_dl_ltv_double_loan_0511
    """, "Q4 double_loan_0511")

    # 5) 老客订单里能匹配到首贷mid的订单数（对照 double_loan 应该多少）
    run(pq, """
    select count(*) as matched_old
    from mx.wxs_application_funnel r
    where r.is_reloan='old' and r.if_issue=1
      and cast(r.cust_id as bigint) in (select distinct mid from mx.ys_dl_ltv_first_loan_0511)
    """, "Q5 能匹配到首贷的老客订单")

    # 6) double_loan_0511 里 biz_id(复贷订单) 是否重复(join放大)
    run(pq, """
    select count(*) as dup_biz_cnt
    from (select biz_id from mx.ys_dl_ltv_double_loan_0511 group by 1 having count(*)>1) t
    """, "Q6 double_loan重复biz_id数(放大检测)")

    # 7) 网格规模 vs limit 100000
    run(pq, """
    select count(*) as cohort_cnt,
           max(wob_d) as max_wob,
           count(*) * (max(wob_d)+1) as grid_est
    from (
      select ltv_month, app_channel_name, new_grade_level
      from mx.ys_dl_ltv_first_loan_0511 group by 1,2,3
    ) c
    """, "Q7 网格规模估计(月x渠道x评级 x wob)")

    # 8) double_loan_group 行数(分组粒度含loan_period)
    run(pq, """
    select count(*) as grp_rows,
           count(distinct ltv_month_d||'|'||app_channel_name_d||'|'||new_grade_level_d||'|'||wob_d) as base_combo
    from mx.ys_dl_ltv_double_loan_group
    """, "Q8 复贷分组表规模")

    # 9) 首贷表里每个mid的首贷行数分布(是否天然1:1)
    run(pq, """
    select per_mid as cnt_per_mid, count(*) as mids
    from (select mid, count(*) as per_mid from mx.ys_dl_ltv_first_loan_0511 group by 1) t
    group by 1 order by 1
    """, "Q9 首贷mid行数分布")

if __name__ == "__main__":
    main()
