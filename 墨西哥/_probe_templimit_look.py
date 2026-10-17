# -*- coding: utf-8 -*-
"""拉离线临额用户表 mx.yuhan_temp_limit_base_table_his_20260924 的实际内容"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, tag="", n=40):
    print("="*110)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:400]); return None
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    print(r.head(n).to_string() if len(r) > n else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# 1) 样本 5 行, 看关键字段
q("""
select mid, app_group, first_loan_date, last_loan_date,
       onloan_cnt, curr_overdue_days, max_overdue_days,
       curr_main_credit_limit, curr_temp_credit_limit,
       temp_limit_issue_date, temp_limit_tag, temp_limit_issue_amount,
       total_available_limit, data_date
from mx.yuhan_temp_limit_base_table_his_20260924
limit 5""",
  "离线临额表 样本5行(关键字段)")

# 2) temp_limit_tag 分布
q("""
select temp_limit_tag, count(*) cnt, count(distinct mid) mids,
       sum(temp_limit_issue_amount) amt,
       round(avg(temp_limit_issue_amount),2) amt_avg
from mx.yuhan_temp_limit_base_table_his_20260924
group by 1 order by 2 desc""",
  "离线临额表 temp_limit_tag 分布")

# 3) 发放日期范围 + 金额区间
q("""
select min(temp_limit_issue_date) mn_issue, max(temp_limit_issue_date) mx_issue,
       min(temp_limit_issue_amount) mn_amt, max(temp_limit_issue_amount) mx_amt,
       round(avg(temp_limit_issue_amount),2) avg_amt
from mx.yuhan_temp_limit_base_table_his_20260924
where temp_limit_issue_amount is not null""",
  "离线临额表 发放日期/金额范围")
