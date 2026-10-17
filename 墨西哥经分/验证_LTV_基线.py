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
        print(r)
    return r

# ============ A. 基线：现有旧表口径 ============

# A1 首贷明细总量
run("""
select count(*) as row_cnt,
       count(distinct biz_id) as frs_biz_cnt,
       count(distinct mid) as frs_mid_cnt,
       sum(contract_amount) as frs_contract_amount
from mx.ys_dl_ltv_first_loan_0511
""", "A1 首贷明细总量(旧)")

# A2 复贷明细总量
run("""
select count(*) as row_cnt,
       count(distinct biz_id) as double_biz_cnt,
       count(distinct mid) as double_mid_cnt,
       sum(contract_amount) as double_contract_amount
from mx.ys_dl_ltv_double_loan_0511
""", "A2 复贷明细总量(旧)")

# A3 复贷 group 表总量（旧：6位 group by）
run("""
select count(*) as group_row_cnt,
       sum(double_cnt) as sum_double_cnt,
       sum(double_mid) as sum_double_mid,
       sum(contract_amount) as sum_contract_amount
from mx.ys_dl_ltv_double_loan_group
""", "A3 复贷group表总量(旧)")

# A4 复贷 group 表是否被 double_rnk 压行：统计每个 cohort+wob 下有多行的组
run("""
select count(*) as groups_with_multi_row,
       sum(row_in_group) as rows_in_multi_groups,
       max(row_in_group) as max_rows_in_one_group
from (
    select ltv_week_d, wob_d, app_channel_name_d, new_grade_level_d, is_low_amount_flag_d,
           count(*) as row_in_group
    from mx.ys_dl_ltv_double_loan_group
    group by 1,2,3,4,5
    having count(*) > 1
)
""", "A4 旧group表:同一cohort+wob多行(会被double_rnk压掉)的情况")

# A5 首贷最终select口径 frs_cnt 总量(按 ltv_week+渠道+评级+金额flag 分组)
run("""
select count(*) as frs_group_cnt,
       sum(frs_cnt) as sum_frs_cnt,
       sum(frs_contract_amount) as sum_frs_amt
from (
    select ltv_week, app_channel_name, new_grade_level, is_low_amount_flag,
           count(distinct mid) as frs_cnt,
           sum(contract_amount) as frs_contract_amount
    from mx.ys_dl_ltv_first_loan_0511
    group by 1,2,3,4
)
""", "A5 首贷最终口径(ltv_week维度)frst_loan总量")
