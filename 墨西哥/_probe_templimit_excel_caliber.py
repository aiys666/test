# -*- coding: utf-8 -*-
"""按 Excel 口径重跑: 在线 vs 离线临额 坏账率对比
Excel口径: base=mx.yj_test_table_250225, where is_t3_window_1=1 + app_time进件,
  指标=t0_overdue_amount_1/t0_should_amt_1 (总额口径), 分组=app_week
打标: 放款(release_time)之前最近一次 TEMP 事件类型
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, tag="", show=60):
    print("="*120)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:800]); return None
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 260)
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# ===== 核心1: 在线 vs 离线 vs 无 坏账率(进件周, Excel口径总额) =====
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
    select y.biz_id, y.mid, e.change_event_type, e.create_time
    from mx.yj_test_table_250225 y
    join tmp_evt e on y.mid = e.mid and e.create_time <= y.release_time
    where y.is_t3_window_1=1 and y.if_issue=1
      and y.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  ) x
)
select date_trunc('week', date(y.app_time)) as app_week,
  case
    when el.change_event_type='C010' then '在线临额C010'
    when el.change_event_type in ('C013','C015') then '离线临额C013_15'
    when y.temp_grant_amount>0 then '有临额未匹配'
    else '无临额' end as tl,
  sum(y.t0_should_amt_1) as shd, sum(y.t0_overdue_amount_1) as ovd, sum(y.if_issue) as cnt,
  round(sum(y.t0_overdue_amount_1)/nullif(sum(y.t0_should_amt_1),0)*100,2) as "1t0总额%"
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
where y.is_t3_window_1=1 and y.if_issue=1
  and y.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
"""
q(sql_main, "【Excel口径】在线 vs 离线 vs 无 坏账率(进件周, 总额1t0%)")
