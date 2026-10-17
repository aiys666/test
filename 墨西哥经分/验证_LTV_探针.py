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

# 1. 复贷明细表结构
run("show create table mx.ys_dl_ltv_double_loan_0511", "1. 复贷明细表结构")

# 2. 复贷group表结构
run("show create table mx.ys_dl_ltv_double_loan_group", "2. 复贷group表结构")

# 3. 首贷表结构
run("show create table mx.ys_dl_ltv_first_loan_0511", "3. 首贷表结构")
