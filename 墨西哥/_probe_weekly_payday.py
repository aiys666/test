# -*- coding: utf-8 -*-
"""逐周归因(0810升/0817降/0824高位) + 发薪日周期验证"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 420)

def q(sql, tag="", show=250):
    print("="*130); print(tag)
    r = pq.query(sql)
    if isinstance(r, str): print("[ERR]", r[:1500]); return None
    if r is None or len(r)==0: print("[空]"); return None
    print(r.to_string() if len(r)<=show else r.head(show).to_string())
    print(f"[rows={len(r)}]"); return r

# R1: 复贷 进件周×临额细分(在线tag1/tag0 + 离线C013C015 + 无) — yj表+change_record打标
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
      and y.app_time >= cast('2026-07-27 00:00:00.000' as timestamp)
      and y.app_time <  cast('2026-09-15 00:00:00.000' as timestamp)
  ) x
)"""
q(f"""
with {EVT}
select
  date_format(date_trunc('week', y.app_date),'%Y-%m-%d') as awk,
  case when el.change_event_type in ('C013','C015') then 'offline'
       when el.change_event_type = 'C010' then
         case when y.temp_credit_amount_issue_tag=1 then 'online_tag1' else 'online_tag0' end
       else 'none' end as tl_grp,
  count(*) as loan_cnt,
  round(sum(if(y.t0_should_amt_1>0, y.t0_overdue_amount_1, null))
       /nullif(sum(if(y.t0_should_amt_1>0, y.t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(sum(if(y.t0_should_amt_1>0, y.t0_should_amt_1, null))/1000.0,0) as should_k,
  round(sum(if(y.t0_should_amt_1>0, y.t0_overdue_amount_1, null))/1000.0,0) as od_k
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
where y.if_issue=1 and y.is_reloan='old'
  and y.app_time >= cast('2026-07-27 00:00:00.000' as timestamp)
  and y.app_time <  cast('2026-09-15 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "R1 复贷 进件周×临额细分(在线tag/离线/无)")

# R2: 发薪日切分: 放款日issue_date按月内日段 × 首/复贷 (7-9月)
q("""
select
  date_format(issue_date,'%Y-%m') as mth,
  case when day(issue_date) between 1 and 7 then 'd01_07'
       when day(issue_date) between 8 and 14 then 'd08_14'
       when day(issue_date) between 15 and 21 then 'd15_21'
       when day(issue_date) between 22 and 28 then 'd22_28'
       else 'd29_31' end as day_seg,
  is_reloan,
  count(*) as loan_cnt,
  round(sum(if(t0_should_amt_1>0, t0_overdue_amount_1, null))
       /nullif(sum(if(t0_should_amt_1>0, t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(sum(if(t0_should_amt_1>0, t0_should_amt_1, null))/1000.0,0) as should_k
from mx.wxs_application_funnel
where tenant='yawey' and if_issue=1
  and issue_date >= date'2026-07-01' and issue_date < date'2026-09-22'
group by 1,2,3 order by 1,2,3
""", "R2 发薪日切分: 放款日×日段×首复贷 1t0%(7-9月)")

# R3: 同上但按产品期限分(看7天vs长周期产品对发薪日的敏感度)
q("""
select
  date_format(issue_date,'%Y-%m') as mth,
  case when day(issue_date) between 1 and 7 then 'd01_07'
       when day(issue_date) between 8 and 14 then 'd08_14'
       when day(issue_date) between 15 and 21 then 'd15_21'
       when day(issue_date) between 22 and 28 then 'd22_28'
       else 'd29_31' end as day_seg,
  case when product_day <= 10 then 'p_short(<=10d)' else 'p_long(>10d)' end as pterm,
  is_reloan,
  count(*) as loan_cnt,
  round(sum(if(t0_should_amt_1>0, t0_overdue_amount_1, null))
       /nullif(sum(if(t0_should_amt_1>0, t0_should_amt_1, null)),0)*100,2) as t0_rate
from mx.wxs_application_funnel
where tenant='yawey' and if_issue=1
  and issue_date >= date'2026-07-01' and issue_date < date'2026-09-22'
group by 1,2,3,4 order by 1,3,4,2
""", "R3 放款日×日段×期限×首复贷")
