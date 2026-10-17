# -*- coding: utf-8 -*-
"""诊断: 单个 cust_id 交叉验证 + 值域重叠 + 直接 bigint join"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, tag=""):
    print("="*120)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:400]); return None
    print(r.head(20).to_string())
    print(f"[rows={len(r)}]")
    return r

# 1) 单值: funnel cust_id=1040160070403283 在额度表的记录
q("""select * from ods_view_presto.s05_user_creditlimit_change_record
where mid = 1040160070403283 order by create_time desc limit 20""",
  "额度表中 mid=1040160070403283 的记录")

# 2) 单值反向: 额度表最新 C010 的 mid 在 funnel 中是否存在
q("""select * from mx.wxs_application_funnel
where cust_id = 1040160070563304 limit 20""",
  "funnel 中 cust_id=1040160070563304 的记录")

# 3) 值域重叠: 两表 mid 的交集大小 (bigint 直接 join)
q("""select count(distinct f.cust_id) as intersect_custs
from mx.wxs_application_funnel f
join ods_view_presto.s05_user_creditlimit_change_record c on f.cust_id = c.mid
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
  and c.limit_type='TEMP' and c.change_event_type in ('C010','C013','C015')""",
  "bigint直接join: funnel cust_id ∩ 额度表 mid")

# 4) funnel cust_id 值域 min/max + 与额度表 mid 值域对比
q("""select min(cust_id) mn, max(cust_id) mx, count(distinct cust_id) d
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey' and if_issue=1
  and date(release_time) between date '2026-08-03' and date '2026-08-16'""",
  "funnel cust_id 值域")

q("""select min(mid) mn, max(mid) mx, count(distinct mid) d
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
  and create_time between timestamp '2026-08-03' and timestamp '2026-08-17'""",
  "额度表 mid 值域(8/3-8/17)")
