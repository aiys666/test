# -*- coding: utf-8 -*-
"""定位复贷(8/10周约7000笔)逾期上升来源:
1) 复贷订单构成(在线/离线/无临额) + 笔数/放款金额/应还/逾期/坏账率
2) 8/3 vs 8/10 各组的笔数变化、业绩(放款金额)提幅、坏账贡献分解
3) 临额发放量/使用量/占主额比例
口径: funnel 表(首贷+复贷同源), 临额打标=放款前最近一次 TEMP 事件
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)

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

# ============ Q1: 复贷 8/3 vs 8/10 三分组(含放款金额) ============
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
  sum(f.if_issue) cnt,
  sum(f.issue_amount) issue_amt,
  sum(f.t0_should_amt_1) shd,
  sum(f.t0_overdue_amount_1) ovd,
  round(sum(f.t0_overdue_amount_1)/nullif(sum(f.t0_should_amt_1),0)*100,2) as rate_pct
from mx.wxs_application_funnel f
left join evt_last el on f.biz_id = el.biz_id and el.rn=1
where {FW} and f.is_reloan='old'
group by 1,2 order by 1,2
""", "Q1 复贷 8/3 vs 8/10 三分组: 笔数/放款额/应还/逾期/坏账率")

# ============ Q2: 首贷 8/3 vs 8/10 ============
q(f"""
select date_trunc('week', date(f.app_time)) as wk,
  sum(f.if_issue) cnt,
  sum(f.issue_amount) issue_amt,
  sum(f.t0_should_amt_1) shd,
  sum(f.t0_overdue_amount_1) ovd,
  round(sum(f.t0_overdue_amount_1)/nullif(sum(f.t0_should_amt_1),0)*100,2) as rate_pct
from mx.wxs_application_funnel f
where {FW} and f.is_reloan='new'
group by 1 order by 1
""", "Q2 首贷 8/3 vs 8/10")

# ============ Q3: 全局四组(首贷/在线/离线/无临额) 完整数字 ============
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
  case when f.is_reloan='new' then '首贷'
    when el.change_event_type='C010' then '在线临额'
    when el.change_event_type in ('C013','C015') then '离线临额'
    else '无临额' end as grp,
  sum(f.if_issue) cnt,
  sum(f.issue_amount) issue_amt,
  sum(f.t0_should_amt_1) shd,
  sum(f.t0_overdue_amount_1) ovd,
  round(sum(f.t0_overdue_amount_1)/nullif(sum(f.t0_should_amt_1),0)*100,2) as rate_pct
from mx.wxs_application_funnel f
left join evt_last el on f.biz_id = el.biz_id and el.rn=1
where {FW}
group by 1,2 order by 1,2
""", "Q3 全局四组: 笔数/放款额/应还/逾期/坏账率")

# ============ Q4: 临额发放量(离线) 8/3 vs 8/10 周 ============
q("""
select date_trunc('week', date(temp_limit_issue_date)) as issue_week,
  count(*) rows_cnt, count(distinct mid) mids,
  round(sum(temp_limit_issue_amount),0) amt_sum
from mx.yuhan_temp_limit_base_table_his_20260924
where temp_limit_issue_date >= cast('2026-07-27 00:00:00' as timestamp)
  and temp_limit_issue_date < cast('2026-08-17 00:00:00' as timestamp)
group by 1 order by 1
""", "Q4 离线临额发放(按周, 7/27~8/16)")

# ============ Q5: 在线临额 C010 事件 按周 ============
q("""
select date_trunc('week', date(create_time)) as wk,
  count(*) c010_cnt, count(distinct mid) mids
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP' and change_event_type='C010'
  and create_time >= cast('2026-07-27 00:00:00' as timestamp)
  and create_time < cast('2026-08-17 00:00:00' as timestamp)
group by 1 order by 1
""", "Q5 在线临额C010事件(按周, 7/27~8/16)")

# ============ Q6: 临额使用(冻结) 按周, TEMP vs MAIN ============
q("""
select date_trunc('week', date(create_time)) as wk, limit_type,
  count(*) freeze_cnt, count(distinct mid) mids,
  round(sum(risk_credit_limit),0) freeze_amt
from ods_view_presto.s05_user_creditlimit_used_detail
where change_action='FREEZE_LIMIT'
  and create_time >= cast('2026-07-27 00:00:00' as timestamp)
  and create_time < cast('2026-08-17 00:00:00' as timestamp)
group by 1,2 order by 1,2
""", "Q6 临额/主额使用(冻结)金额(按周, 7/27~8/16)")
