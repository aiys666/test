# -*- coding: utf-8 -*-
"""查首贷表 schema"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql):
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:500]); return None
    return r

print("首贷表 schema:")
r = q("describe mx.ys_dl_ltv_first_loan_0511")
if r is not None:
    print(r.to_string())
