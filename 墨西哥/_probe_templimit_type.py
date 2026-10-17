# -*- coding: utf-8 -*-
"""区分 在线临额(C010) vs 离线临额(C013/C015) 对坏账的影响
步骤1: 探查离线临额用户表结构+样本; 探查额度记录表 change_event_type 分布
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, tag=""):
    print("="*100)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:400]); return None
    print(r.to_string() if len(r) <= 60 else r.head(30).to_string())
    print(f"[rows={len(r)}]")
    return r

# 1) 离线临额用户表是否存在 + 结构
q("select * from mx.yuhan_temp_limit_base_table_his_20260924 limit 5",
  "离线临额用户表 mx.yuhan_temp_limit_base_table_his_20260924 样本")

# 2) 离线临额表行数 + 分区/日期范围
q("""select count(*) cnt, count(distinct mid) mids,
       min(data_date) mn_dd, max(data_date) mx_dd
from mx.yuhan_temp_limit_base_table_his_20260924""",
  "离线临额表行数/去重mid/日期范围")

# 3) 额度记录表 change_event_type 取值分布 (TEMP)
q("""select change_event_type, limit_type,
       count(*) cnt, count(distinct mid) mids,
       min(create_time) mn, max(create_time) mx
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type = 'TEMP'
group by 1,2 order by 3 desc""",
  "额度记录表 change_event_type 分布 (limit_type=TEMP)")

# 4) 额度记录表 C010/C013/C015 时间线 (按周)
q("""select change_event_type,
       date_format(create_time, '%Y-%u') as wk,
       count(*) cnt, count(distinct mid) mids
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type = 'TEMP' and change_event_type in ('C010','C013','C015')
  and create_time >= timestamp '2026-06-01'
group by 1,2 order by 2,1""",
  "C010/C013/C015 按周笔数/去重mid")
