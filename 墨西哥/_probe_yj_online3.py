# -*- coding: utf-8 -*-
"""第三轮: 在线临额细节指标核对(yj表, 在线临额=C010口径)"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 400)
pd.set_option('display.max_colwidth', 50)

def q(sql, tag="", show=60):
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
      and y.app_time >= cast('2026-08-01 00:00:00.000' as timestamp)
      and y.app_time <  cast('2026-09-28 00:00:00.000' as timestamp)
  ) x
)"""

HASH = "from_base(substr(to_hex(sha256(to_utf8('20260811'||y.credit_no||y.app_group_sha256))),1,4),16)/65536.0000000000000000"

# Q1: 在线临额 复现 strategy_test_flag 分桶 + 使用临额均值/件数/总额/未使用件数 (app_date 7.1~8.27 窗口)
q(f"""
with {EVT}
select
  case when el.change_event_type='C010' then '在线临额'
       when el.change_event_type in ('C013','C015') then '离线临额'
       else '无临额' end as tl,
  -- 复现 strategy_test_flag (SQL用apply_time, 这里yj表只能用app_date近似)
  case when date(y.app_date) >= date'2026-09-03' then
         case when {HASH} > 0.3 then '20260518-V5_2策略' else '20260810-V5_3策略' end
       when date(y.app_date) >= date'2026-08-10' and date(y.app_date) < date'2026-09-03' then
         case when {HASH} > 0.7 then '20260518-V5_2策略' else '20260810-V5_3策略' end
       else 'null(8.10前)' end as flag,
  count(*) cnt,
  count(distinct y.biz_id) biz_cnt,
  round(avg(if(y.temp_grant_amount != 0, y.temp_grant_amount/1000.0, null)),2) as use_avg_k,
  count(distinct if(y.temp_grant_amount > 0, y.biz_id, null)) as use_biz_cnt,
  round(sum(y.temp_grant_amount/1000.0),0) as use_sum_k,
  count(distinct if(y.temp_grant_amount = 0, y.biz_id, null)) as no_use_biz_cnt
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
where y.if_issue=1 and y.is_reloan='old'
  and y.app_time >= cast('2026-07-01 00:00:00.000' as timestamp)
  and y.app_time <  cast('2026-08-28 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "Q1 在线/离线/无临额 × strategy_flag(app_date 7.1~8.27) 使用临额4指标")
