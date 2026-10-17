# -*- coding: utf-8 -*-
"""0903 V5_3灰度回调(70%->30%)效果评估
设计: 重算hash分3组
  A组 hash>0.7      : 0810后始终V5_2(低发放对照锚)
  B组 0.3<hash<=0.7 : 0810-0903=V5_3 -> 0903后切回V5_2 (被切换的40%)
  C组 hash<=0.3     : 始终V5_3(高发放, 剩余30%灰度)
  DID: B组切换前后变化 - A/C组同期时间趋势
口径: C010在线临额打标 / 放款周issue_week / 1t0%=t0_overdue_amount_1/t0_should_amt_1(含利息)
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 400)
pd.set_option('display.max_colwidth', 40)

def q(sql, tag="", show=100):
    print("="*130)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:1000]); return None
    if r is None or len(r) == 0:
        print("[空数据]"); return None
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# C010打标(不过滤if_issue, 进件/放款口径都能用)
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
    where y.is_reloan='old'
      and y.app_time >= cast('2026-07-01 00:00:00.000' as timestamp)
      and y.app_time <  cast('2026-10-06 00:00:00.000' as timestamp)
  ) x
),
base as (
  select
    y.biz_id, y.mid, y.if_issue, y.app_date, y.issue_date, y.release_time,
    y.temp_grant_amount, y.temp_credit_amount_issue_tag as issue_tag,
    y.temp_credit_amount_strategy_test_flag as flag_tbl,
    y.t0_should_amt_1, y.t0_overdue_amount_1,
    y.real_issue_amount, y.loan_contract_amount,
    el.change_event_type as tl_type,
    from_base(substr(to_hex(sha256(to_utf8('20260811'||y.credit_no||y.app_group_sha256))),1,4),16)/65536.0000000000000000 as h,
    case when from_base(substr(to_hex(sha256(to_utf8('20260811'||y.credit_no||y.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'A_始终V5_2'
         when from_base(substr(to_hex(sha256(to_utf8('20260811'||y.credit_no||y.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'C_始终V5_3'
         else 'B_切换组' end as hgrp
  from mx.yj_test_table_250225 y
  left join evt_last el on y.biz_id = el.biz_id and el.rn=1
  where y.is_reloan='old'
    and y.app_time >= cast('2026-07-01 00:00:00.000' as timestamp)
    and y.app_time <  cast('2026-10-06 00:00:00.000' as timestamp)
)"""

# Q0: 金额字段量级抽样(C010放款)
q(f"""
with {EVT}
select issue_date, flag_tbl, hgrp, issue_tag,
  temp_grant_amount, real_issue_amount, loan_contract_amount,
  t0_should_amt_1, t0_overdue_amount_1
from base
where if_issue=1 and tl_type='C010' and issue_date >= date'2026-08-15'
limit 10
""", "Q0 金额字段量级抽样")

# Q1: hash组分布校验(8/10后进件, C010)
q(f"""
with {EVT}
select hgrp, flag_tbl, count(*) cnt, count(if(if_issue=1,1,null)) issued
from base
where tl_type='C010' and app_date >= date'2026-08-10' and app_date < date'2026-09-03'
group by 1,2 order by 1,2
""", "Q1a hash组×落表flag (app 8/10-9/3 应: A=V5_2,B/C=V5_3)")

q(f"""
with {EVT}
select hgrp, flag_tbl, count(*) cnt, count(if(if_issue=1,1,null)) issued
from base
where tl_type='C010' and app_date >= date'2026-09-03'
group by 1,2 order by 1,2
""", "Q1b hash组×落表flag (app 9/3后 应: A/B=V5_2,C=V5_3)")
