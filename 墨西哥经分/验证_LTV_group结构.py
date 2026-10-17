# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功")

r = pq.query("show create table mx.ys_dl_ltv_double_loan_group")
print(r.to_string() if hasattr(r, 'to_string') else r)
