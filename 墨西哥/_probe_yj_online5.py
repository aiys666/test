# -*- coding: utf-8 -*-
"""第三轮补充: 在线临额人群内 fd_use_creditamount_score_v1 / fd_use_creditamount_type 分布"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 400)
pd.set_option('display.max_colwidth', 50)

def q(sql, tag="", show=80):
    print("="*120)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:800]); return None
    if r is None or len(r) == 0:
        print("[空数据]"); return None
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

EVT = """tmp_evt as (
  select mid, change_event_type, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
),
evt_last as (
  select biz_id, change_event_type,
    row_number() over (partition by biz_id order by create_time desc) as rn
  from (
    select y.biz_id, e.change_event_type, e.create_time
    from mx.yj_test_table_250225 y
    join tmp_evt e on y.mid = e.mid and e.create_time <= y.release_time
    where y.if_issue=1 and y.is_reloan='old'
      and y.app_time >= cast('2026-07-01 00:00:00.000' as timestamp)
      and y.app_time <  cast('2026-10-06 00:00:00.000' as timestamp)
  ) x
)"""

# Q1: 在线临额(C010)人群内 fd_use_creditamount_score_v1 分布 (8/10后, 按周对比)
q(f"""
with {EVT}
select
  case when date(y.app_date) >= date'2026-08-10' and date(y.app_date) < date'2026-08-17' then '8/10周'
       when date(y.app_date) >= date'2026-08-03' and date(y.app_date) < date'2026-08-10' then '8/03周'
       else '其他' end as wk,
  y.fd_use_creditamount_score_v1 as score,
  count(*) cnt,
  count(distinct y.biz_id) biz_cnt
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
where y.if_issue=1 and y.is_reloan='old'
  and y.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and y.app_time <  cast('2026-08-17 00:00:00.000' as timestamp)
  and el.change_event_type='C010'
group by 1,2 order by 1,2
""", "Q1 在线临额 score_v1 分布(8/3周 vs 8/10周)")

# Q2: 在线临额(C010)人群内 fd_use_creditamount_type 分布
q(f"""
with {EVT}
select
  case when date(y.app_date) >= date'2026-08-10' and date(y.app_date) < date'2026-08-17' then '8/10周'
       when date(y.app_date) >= date'2026-08-03' and date(y.app_date) < date'2026-08-10' then '8/03周'
       else '其他' end as wk,
  y.fd_use_creditamount_type as ctype,
  count(*) cnt,
  count(distinct y.biz_id) biz_cnt
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
where y.if_issue=1 and y.is_reloan='old'
  and y.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and y.app_time <  cast('2026-08-17 00:00:00.000' as timestamp)
  and el.change_event_type='C010'
group by 1,2 order by 1,2
""", "Q2 在线临额 fd_use_creditamount_type 分布(8/3周 vs 8/10周)")

# Q3: score_v1 分子来源 daily_left_amount_quota_use_rate / finish_total_num 分布 (在线临额8/10后)
q(f"""
with {EVT}
select
  round(t.daily_left_amount_quota_use_rate, 2) as rate,
  t.finish_total_num as fin_num,
  count(*) cnt
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
left join (
  select biz_id, daily_left_amount_quota_use_rate, finish_total_num,
    row_number() over (partition by biz_id order by dt desc) rn
  from mx.tmp_darren_new_temp_limit_table
) t on y.biz_id = t.biz_id and t.rn=1
where y.if_issue=1 and y.is_reloan='old'
  and y.app_time >= cast('2026-08-10 00:00:00.000' as timestamp)
  and y.app_time <  cast('2026-08-17 00:00:00.000' as timestamp)
  and el.change_event_type='C010'
group by 1,2 order by 1,2
""", "Q3 score_v1分子(use_rate × finish_num)分布(8/10周在线临额)")
