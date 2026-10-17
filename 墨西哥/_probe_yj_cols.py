# -*- coding: utf-8 -*-
"""查 yj 表评级字段名"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

pq = PrestoQuery(); pq.login()
r = pq.query("select * from mx.yj_test_table_250225 limit 1")
if isinstance(r, str):
    print("[FAIL]", r[:500])
else:
    cols = list(r.columns)
    print("总列数", len(cols))
    for c in cols:
        if any(k in c.lower() for k in ['grade','level','risk','rating','score','index']):
            print(c)
    print("--- 全部列名 ---")
    print(cols)
