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
    try:
        r = pq.query(sql)
    except Exception as e:
        print("EXC:", e)
        return None
    if isinstance(r, pd.DataFrame):
        print(r.to_string())
    else:
        print("RESULT:", r)
    return r

run("show create table mx.ys_dl_ltv_double_loan_group", "新group表结构")
run("select count(*) as cnt from mx.ys_dl_ltv_double_loan_group", "group表行数")
