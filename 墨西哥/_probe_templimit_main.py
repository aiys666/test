# -*- coding: utf-8 -*-
"""核心: 在线临额(C010) vs 离线临额(C013/C015) 对坏账的影响
打标逻辑: 放款(release_time)之前最近一次 TEMP 事件类型
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, tag="", show=40):
    print("="*120)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:500]); return None
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# 先验证 funnel.biz_id 唯一性
q("""select count(*) rows_cnt, count(distinct biz_id) biz
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey' and if_issue=1
  and date(release_time) between date '2026-08-03' and date '2026-08-24'""",
  "funnel biz_id 唯一性(if_issue=1)")

# ===== 核心1: 时间窗打标(放款前最近一次 TEMP 事件) =====
sql_main = """
with tmp_evt as (
  select mid, change_event_type, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
),
evt_last as (
  select biz_id, mid, change_event_type,
    row_number() over (partition by biz_id order by create_time desc) as rn
  from (
    select f.biz_id, f.mid, e.change_event_type, e.create_time
    from mx.wxs_application_funnel f
    join tmp_evt e on f.mid = e.mid and e.create_time <= f.release_time
    where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
      and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
  ) x
)
select date_trunc('week', date(f.release_time)) as w,
  case
    when el.change_event_type='C010' then '在线临额C010'
    when el.change_event_type in ('C013','C015') then '离线临额C013_15'
    when f.temp_grant_amount>0 then '有临额未匹配'
    else '无临额' end as tl,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from mx.wxs_application_funnel f
left join evt_last el on f.biz_id = el.biz_id and el.rn=1
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
group by 1,2 order by 1,2
"""
q(sql_main, "【核心】在线 vs 离线 vs 无 坏账率(放款周, 放款前最近事件打标)")
