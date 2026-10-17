# -*- coding: utf-8 -*-
import sys, json, base64, time
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

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

import pandas as pd

run("select count(*) as row_cnt from mx.ys_dl_ltv_double_loan_group", "新group表行数")
run("""
select sum(double_cnt) as sum_double_cnt,
       sum(double_mid) as sum_double_mid,
       sum(contract_amount) as sum_contract_amount
from mx.ys_dl_ltv_double_loan_group
""", "新group表聚合 (基线: 534643 / 409948 / 653038101.91)")

run("""
select count(distinct reloan_app_channel) as channel_cnt,
       count(distinct reloan_app_channel_name) as channel_name_cnt
from mx.ys_dl_ltv_double_loan_group
""", "复贷渠道维度分布")

run("""
select reloan_app_channel_name, sum(double_cnt) as dc, sum(contract_amount) as amt
from mx.ys_dl_ltv_double_loan_group
group by 1
order by 2 desc
limit 20
""", "复贷渠道名 top20")
