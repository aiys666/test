# -*- coding: utf-8 -*-
"""查 biz_id / mid / cust_id 在 funnel 与 used_detail 的类型"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

def q(sql, tag=""):
    print("="*100)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:500]); return None
    print(r.to_string())
    return r

q("select typeof(biz_id) biz_id, typeof(mid) mid, typeof(cust_id) cust_id from mx.wxs_application_funnel limit 1",
  "funnel 类型")
q("select typeof(biz_id) biz_id, typeof(mid) mid, typeof(cust_id) cust_id from ods_view_presto.s05_user_creditlimit_used_detail limit 1",
  "used_detail 类型")
q("select typeof(biz_id) biz_id, typeof(mid) mid from ods_view_presto.s05_user_creditlimit_change_record limit 1",
  "change_record 类型")
q("select typeof(biz_id) biz_id, typeof(mid) mid from mx.yj_test_table_250225 limit 1",
  "yj 类型")
