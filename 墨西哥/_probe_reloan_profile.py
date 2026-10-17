# -*- coding: utf-8 -*-
"""复贷为全局: 三分组(在线/离线/无临额)完整画像
+ 4t7 TR + 临额/主额使用金额(按订单精确关联 used_detail)
+ 评级6-12档份额趋势(yj表, 8/3~9/28 周, 判断扩张后是否回落)
口径: funnel 表(含首贷+复贷+完整t0/t7字段), 临额打标=放款前最近一次 TEMP 事件
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 320)

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

FW = """f.if_issue=1
  and f.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and f.app_time <  cast('2026-08-17 00:00:00.000' as timestamp)"""

# ============ Q1: 复贷三分组完整画像(人数/笔数/金额/临额主额使用/1t0双口径/4t7TR) ============
q(f"""
with use as (
  select biz_id,
    sum(case when limit_type='TEMP' then risk_credit_limit else 0 end) temp_used,
    sum(case when limit_type='MAIN' then risk_credit_limit else 0 end) main_used
  from ods_view_presto.s05_user_creditlimit_used_detail
  where change_action='FREEZE_LIMIT'
  group by biz_id
),
tmp_evt as (
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
  count(distinct f.mid) mids,
  count(*) cnt,
  round(sum(f.issue_amount),0) issue_amt,
  round(sum(u.temp_used),0) temp_used_amt,
  round(sum(u.main_used),0) main_used_amt,
  round(sum(f.is_t0_window_1),0) t0_window_cnt,
  round(sum(f.is_t0_overdue_1),0) t0_overdue_flag_cnt,
  round(sum(case when f.t0_overdue_amount_1>0 then 1 else 0 end),0) t0_overdue_amt_cnt,
  -- 1t0 笔数逾期率 (flag口径)
  round(sum(f.is_t0_overdue_1)/nullif(sum(f.is_t0_window_1),0)*100,2) as r_1t0_cnt_pct_flag,
  -- 1t0 笔数逾期率 (金额>0口径)
  round(sum(case when f.t0_overdue_amount_1>0 then 1 else 0 end)/nullif(sum(f.is_t0_window_1),0)*100,2) as r_1t0_cnt_pct,
  -- 1t0 金额逾期率
  round(sum(f.t0_overdue_amount_1)/nullif(sum(f.t0_should_amt_1),0)*100,2) as r_1t0_amt_pct,
  -- 4t7 笔数TR
  round(sum(f.is_t7_overdue_4)/nullif(sum(f.is_t7_window_4),0)*100,2) as r_4t7_cnt_pct,
  -- 4t7 金额TR
  round(sum(f.t7_overdue_amount_4)/nullif(sum(f.t7_should_amt_4),0)*100,2) as r_4t7_amt_pct
from mx.wxs_application_funnel f
left join evt_last el on f.biz_id = el.biz_id and el.rn=1
left join use u on f.biz_id = cast(u.biz_id as varchar)
where {FW} and f.is_reloan='old'
group by 1,2 order by 1,2
""", "Q1 复贷三分组完整画像(8/3 vs 8/10)")

# ============ Q2: 复贷整体(不分组) 合计 ============
q(f"""
select date_trunc('week', date(f.app_time)) as wk,
  count(distinct f.mid) mids,
  count(*) cnt,
  round(sum(f.issue_amount),0) issue_amt,
  round(sum(f.is_t0_window_1),0) t0_window_cnt,
  round(sum(f.is_t0_overdue_1),0) t0_overdue_flag_cnt,
  round(sum(case when f.t0_overdue_amount_1>0 then 1 else 0 end),0) t0_overdue_amt_cnt,
  round(sum(f.is_t0_overdue_1)/nullif(sum(f.is_t0_window_1),0)*100,2) as r_1t0_cnt_pct_flag,
  round(sum(case when f.t0_overdue_amount_1>0 then 1 else 0 end)/nullif(sum(f.is_t0_window_1),0)*100,2) as r_1t0_cnt_pct,
  round(sum(f.t0_overdue_amount_1)/nullif(sum(f.t0_should_amt_1),0)*100,2) as r_1t0_amt_pct,
  round(sum(f.is_t7_overdue_4)/nullif(sum(f.is_t7_window_4),0)*100,2) as r_4t7_cnt_pct,
  round(sum(f.t7_overdue_amount_4)/nullif(sum(f.t7_should_amt_4),0)*100,2) as r_4t7_amt_pct
from mx.wxs_application_funnel f
where {FW} and f.is_reloan='old'
group by 1 order by 1
""", "Q2 复贷整体合计")

# ============ Q3: 评级6-12档份额+率 周趋势 (yj表有评级字段, 8/3~9/28) ============
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
    select y.biz_id, e.change_event_type, e.create_time
    from mx.yj_test_table_250225 y
    join tmp_evt e on y.mid = e.mid and e.create_time <= y.release_time
    where y.is_t3_window_1=1 and y.if_issue=1 and y.is_reloan='old'
      and y.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
      and y.app_time <  cast('2026-09-28 00:00:00.000' as timestamp)
  ) x
)
select date_trunc('week', date(y.app_time)) as wk,
  case when el.change_event_type='C010' then '在线临额'
    when el.change_event_type in ('C013','C015') then '离线临额'
    else '无临额' end as tl,
  count(*) cnt,
  round(sum(y.t0_should_amt_1),0) shd,
  round(sum(y.t0_overdue_amount_1),0) ovd,
  round(sum(case when y.android_oldcust_maincreditlevel_charge_v5_3 between 6 and 12 then y.t0_should_amt_1 else 0 end),0) shd_612,
  round(sum(case when y.android_oldcust_maincreditlevel_charge_v5_3 between 6 and 12 then y.t0_overdue_amount_1 else 0 end),0) ovd_612
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
where y.is_t3_window_1=1 and y.if_issue=1 and y.is_reloan='old'
  and y.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and y.app_time <  cast('2026-09-28 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "Q3 评级6-12档份额+率 周趋势(yj表, 在线/离线/无临额, 8/3~9/21)")
