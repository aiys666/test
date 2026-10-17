# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功")

def run(sql, desc):
    print("\n" + "-"*70)
    print(desc)
    print("-"*70)
    r = pq.query(sql)
    if isinstance(r, pd.DataFrame):
        print(r.to_string())
    else:
        print(r)
    return r

run("select count(*) as row_cnt from mx.ys_dl_ltv_double_loan_0511", "复贷明细行数")
run("select count(distinct biz_id) as b, count(distinct mid) as m, sum(contract_amount) as amt from mx.ys_dl_ltv_double_loan_0511", "复贷明细去重")
run("select count(*) as row_cnt from mx.ys_dl_ltv_double_loan_group", "group表行数")
run("select sum(double_cnt) as dc, sum(double_mid) as dm, sum(contract_amount) as amt from mx.ys_dl_ltv_double_loan_group", "group表聚合")
