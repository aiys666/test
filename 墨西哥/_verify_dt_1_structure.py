# -*- coding: utf-8 -*-
"""验证 darren_jieqing_dt_table：结构、重复、抽样、链路"""
import sys, json
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

# 1. 表结构
print("=" * 80)
print("1) 表结构 DESCRIBE")
print("=" * 80)
r = pq.query("describe mx.darren_jieqing_dt_table")
print(r if isinstance(r, str) else r.to_string())

# 行数
print("=" * 80)
print("2) 总行数")
print("=" * 80)
r = pq.query("select count(*) as cnt from mx.darren_jieqing_dt_table")
print(r if isinstance(r, str) else r.to_string())
