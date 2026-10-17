# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功")

def run(sql, desc):
    print("\n" + "="*70)
    print(desc)
    print("="*70)
    r = pq.query(sql)
    if isinstance(r, pd.DataFrame):
        print(r.to_string())
    else:
        print("RESULT:", r)
    return r

# ============ 1. 首贷笔数一致性 ============
run("""
select count(*) as row_cnt,
       count(distinct biz_id) as frs_biz_cnt,
       count(distinct mid) as frs_mid_cnt,
       sum(contract_amount) as frs_contract_amount
from mx.ys_dl_ltv_first_loan_0511
""", "1. 首贷明细总量 (基线: 331232 / 331232 / 331223 / 251063358)")

# ============ 2. 复贷笔数一致性 ============
run("""
select count(*) as row_cnt,
       count(distinct biz_id) as double_biz_cnt,
       count(distinct mid) as double_mid_cnt,
       sum(contract_amount) as double_contract_amount
from mx.ys_dl_ltv_double_loan_0511
""", "2. 复贷明细总量 (基线: 534645 / 534640 / 141930 / 653038101.91)")

run("""
select count(*) as group_row_cnt,
       sum(double_cnt) as sum_double_cnt,
       sum(double_mid) as sum_double_mid,
       sum(contract_amount) as sum_contract_amount
from mx.ys_dl_ltv_double_loan_group
""", "3. 新group表总量 (旧group: 43940 / 534643 / 409948 / 653038101.91)")

# ============ 3. double_rnk 删除后，同一cohort+wob多行是否保留 ============
run("""
select
    count(*) as groups_total,
    sum(case when rows_in_group > 1 then 1 else 0 end) as groups_multi_row,
    max(rows_in_group) as max_rows
from (
    select ltv_week_d, wob_d, app_channel_name_d, new_grade_level_d, is_low_amount_flag_d,
           count(*) as rows_in_group
    from mx.ys_dl_ltv_double_loan_group
    group by 1,2,3,4,5
)
""", "4. 新group表: 同一cohort+wob下多行分布 (旧: 10006组/21867行会被压掉)")

# ============ 4. 复贷渠道分布 ============
run("""
select reloan_app_channel_name_d, sum(double_cnt) as dc, sum(contract_amount) as amt
from mx.ys_dl_ltv_double_loan_group
group by 1
order by 2 desc
""", "5. 复贷渠道名分布")

# ============ 5. 明细 vs group 笔数校验(看跨cohort重复匹配放大) ============
run("""
select
    (select count(distinct biz_id) from mx.ys_dl_ltv_double_loan_0511) as detail_biz,
    (select sum(double_cnt) from mx.ys_dl_ltv_double_loan_group) as group_sum_cnt,
    (select sum(double_cnt) from mx.ys_dl_ltv_double_loan_group) - (select count(distinct biz_id) from mx.ys_dl_ltv_double_loan_0511) as diff
""", "6. 明细distinct biz vs group sum(double_cnt) 差异(跨cohort重复匹配)")
