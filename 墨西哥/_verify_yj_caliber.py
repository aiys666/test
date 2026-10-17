# -*- coding: utf-8 -*-
"""校验: yj_test_table_250225 评级表 vs funnel 宽表 的指标字段口径"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, tag="", show=30):
    print("="*110)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:500]); return None
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 250)
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# 1) yj 表字段清单: 找 t0_ 相关指标字段
r = pq.query("select * from mx.yj_test_table_250225 limit 1")
if isinstance(r, str):
    print("[FAIL]", r[:500])
else:
    cols = list(r.columns)
    print("yj表总列数:", len(cols))
    for c in cols:
        if any(k in c.lower() for k in ['t0_', 't3_', 'should', 'overdue', 'biz_id', 'app_time', 'is_t3_window']):
            print("  ", c)
