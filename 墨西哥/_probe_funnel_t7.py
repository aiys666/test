# -*- coding: utf-8 -*-
"""探查 funnel 表 t7 / t0 / overdue / window 字段名"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)

r = pq.query("select * from mx.wxs_application_funnel limit 1")
if isinstance(r, str):
    print("[ERR]", r[:800])
else:
    cols = list(r.columns)
    print("funnel 总列数:", len(cols))
    import re
    for c in cols:
        if re.search(r't7|t0|overdue|window|issue_amount|is_reloan|biz_id|^mid$|cust_id', c, re.I):
            print("  ", c)
