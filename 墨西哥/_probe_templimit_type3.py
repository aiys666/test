# -*- coding: utf-8 -*-
"""诊断: funnel.cust_id 与额度表 mid 关联失败原因"""
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

# 1) 额度表 mid 类型 + 样本
q("""select typeof(mid) as mid_type, count(*) cnt
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
group by 1""", "额度表 mid 类型")

q("""select mid, change_event_type, change_total_grantamount, create_time
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
order by create_time desc limit 10""", "额度表 mid 样本")

# 2) funnel cust_id 类型 + 样本
q("""select typeof(cust_id) as cust_type, count(*) cnt
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey' and if_issue=1
  and date(release_time) between date '2026-08-03' and date '2026-08-16'
group by 1""", "funnel cust_id 类型")

q("""select cust_id, temp_grant_amount, release_time
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey' and if_issue=1 and temp_grant_amount>0
  and date(release_time) between date '2026-08-03' and date '2026-08-16'
order by release_time desc limit 10""", "funnel cust_id 样本(有临额)")

# 3) 显式 cast 双向匹配测试: 取一个 funnel 有临额的 cust_id 看额度表有无
q("""select count(*) cnt
from mx.wxs_application_funnel f
join ods_view_presto.s05_user_creditlimit_change_record c
  on cast(f.cust_id as varchar) = cast(c.mid as varchar)
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1 and f.temp_grant_amount>0
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
  and c.limit_type='TEMP' and c.change_event_type in ('C010','C013','C015')""",
  "cast(varchar) 双向匹配: funnel有临额客户能命中额度表?")

# 4) 离线临额表匹配测试: funnel cust_id 能否命中 yuhan 表
q("""select count(*) cnt, count(distinct f.cust_id) custs
from mx.wxs_application_funnel f
join mx.yuhan_temp_limit_base_table_his_20260924 y
  on cast(f.cust_id as varchar) = cast(y.mid as varchar)
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16'""",
  "funnel cust_id 命中离线临额表 yuhan")
