# -*- coding: utf-8 -*-
"""补: 4t7 笔数率(金额>0口径) + t7窗口笔数, 复贷三分组"""
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

FW = """f.if_issue=1
  and f.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and f.app_time <  cast('2026-08-17 00:00:00.000' as timestamp)"""

q(f"""
with tmp_evt as (
  select mid, change_event_type, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
),
evt_last as (
  select biz_id, change_event_type,
    row_number() over (partition by biz_id order by create_time desc) as rn
  from (
    select f.biz_id, e.change_event_type, e.create_time
    from mx.wxs_application_funnel f
    join tmp_evt e on f.mid = e.mid and e.create_time <= f.release_time
    where {FW} and f.is_reloan='old'
  ) x
)
select date_trunc('week', date(f.app_time)) as wk,
  case when el.change_event_type='C010' then '在线临额'
    when el.change_event_type in ('C013','C015') then '离线临额'
    else '无临额' end as tl,
  count(*) cnt,
  round(sum(f.is_t7_window_4),0) t7_window_cnt,
  round(sum(f.is_t7_overdue_4),0) t7_overdue_flag_cnt,
  round(sum(case when f.t7_overdue_amount_4>0 then 1 else 0 end),0) t7_overdue_amt_cnt,
  round(sum(f.t7_should_amt_4),0) t7_should,
  round(sum(f.t7_overdue_amount_4),0) t7_ovd
from mx.wxs_application_funnel f
left join evt_last el on f.biz_id = el.biz_id and el.rn=1
where {FW} and f.is_reloan='old'
group by 1,2 order by 1,2
""", "4t7 笔数+金额 (复贷三分组)")
