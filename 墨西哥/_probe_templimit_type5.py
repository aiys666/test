# -*- coding: utf-8 -*-
"""修正: 用 funnel.mid 关联额度表/离线临额表"""
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
    print(r.head(25).to_string())
    print(f"[rows={len(r)}]")
    return r

# 1) funnel.mid 类型 + 样本 + cust_id vs mid 关系
q("""select typeof(mid) mt, count(*) cnt, count(distinct mid) dmid
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey' and if_issue=1
  and date(release_time) between date '2026-08-03' and date '2026-08-16'
group by 1""", "funnel mid 类型")

q("""select cust_id, mid, temp_grant_amount, release_time
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey' and if_issue=1 and temp_grant_amount>0
  and date(release_time) between date '2026-08-03' and date '2026-08-16'
order by release_time desc limit 10""", "funnel cust_id vs mid 样本")

# 2) 单值验证: funnel.mid 在额度表
q("""select * from ods_view_presto.s05_user_creditlimit_change_record
where mid = 1040160070403283 order by create_time desc limit 10""",
  "额度表中 mid=1040160070403283")

# 3) bigint join: funnel.mid ∩ 额度表 mid
q("""select count(distinct f.mid) as intersect_mids
from mx.wxs_application_funnel f
join ods_view_presto.s05_user_creditlimit_change_record c on f.mid = c.mid
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
  and c.limit_type='TEMP' and c.change_event_type in ('C010','C013','C015')""",
  "funnel.mid ∩ 额度表 mid")

# 4) funnel.mid 命中离线临额表
q("""select count(distinct f.mid) as hit_yuhan
from mx.wxs_application_funnel f
join mx.yuhan_temp_limit_base_table_his_20260924 y on f.mid = y.mid
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16'""",
  "funnel.mid 命中离线临额表 yuhan")
