# -*- coding: utf-8 -*-
"""探针2：funnel 表列清单 + yj表与funnel关联 + 评级取值分布"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

def q(sql):
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:300])
        return None
    return r

# 1. funnel 表列清单
print("=" * 100)
print("[1] funnel 表列清单 (select * limit 1)")
d = q("select * from mx.wxs_application_funnel limit 1")
if d is not None:
    cols = list(d.columns)
    print("总列数:", len(cols))
    for c in cols:
        print(c)

print("=" * 100)
print("[2] yj_test_table_250225 列清单")
d2 = q("select * from mx.yj_test_table_250225 limit 1")
if d2 is not None:
    print("总列数:", len(d2.columns))
    for c in d2.columns:
        print(c)
