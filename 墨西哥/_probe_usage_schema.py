# -*- coding: utf-8 -*-
"""Step A: 探查临额使用相关表字段"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, tag="", show=20):
    print("="*110)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:600]); return None
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 260)
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# 1) used_detail 字段
r = pq.query("select * from ods_view_presto.s05_user_creditlimit_used_detail limit 1")
if not isinstance(r, str):
    print("used_detail 列:", list(r.columns))

# 2) used_detail FREEZE_LIMIT TEMP 样本
q("""
select * from ods_view_presto.s05_user_creditlimit_used_detail
where limit_type='TEMP' and change_action='FREEZE_LIMIT'
order by create_time desc limit 5
""", "used_detail TEMP FREEZE 样本")

# 3) change_record C010/C013/C015 字段样本
q("""
select change_event_type, mid, change_total_grantamount, change_used_grantamount,
  create_time, limit_type
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
  and create_time >= cast('2026-08-01 00:00:00' as timestamp)
order by create_time desc limit 8
""", "change_record TEMP 事件样本(8月)")
