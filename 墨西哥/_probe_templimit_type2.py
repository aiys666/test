# -*- coding: utf-8 -*-
"""区分 在线临额(C010) vs 离线临额(C013/C015) 对坏账的影响 — 步骤2
1) C010/C013/C015 按周时间线(修正)
2) 离线临额表 data_date / temp_limit_tag 分布
3) 复贷放款客户: temp_grant_amount>0 与额度表事件类型匹配率
4) 核心: 在线临额 vs 离线临额 vs 无临额 的坏账率(放款周)
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, tag="", show=30):
    print("="*120)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:400]); return None
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# 1) C010/C013/C015 按周笔数/去重mid (修正 %u)
q("""select change_event_type,
       date_trunc('week', create_time) as wk,
       count(*) cnt, count(distinct mid) mids
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type = 'TEMP' and change_event_type in ('C010','C013','C015')
  and create_time >= timestamp '2026-06-01'
group by 1,2 order by 2,1""",
  "C010/C013/C015 按周笔数/去重mid")

# 2) 离线临额表 data_date 分布
q("""select data_date, count(*) cnt, count(distinct mid) mids,
       count(distinct temp_limit_tag) tags
from mx.yuhan_temp_limit_base_table_his_20260924
group by 1 order by 1""",
  "离线临额表 data_date 分布")

# 2b) temp_limit_tag 分布
q("""select temp_limit_tag, count(*) cnt, count(distinct mid) mids
from mx.yuhan_temp_limit_base_table_his_20260924
group by 1 order by 2 desc limit 30""",
  "离线临额表 temp_limit_tag 分布")

# 3) 复贷放款客户: temp_grant_amount>0 与额度表事件类型匹配率
q("""with tmp_evt as (
  select mid, change_event_type, create_time,
    row_number() over (partition by mid order by create_time desc) as rn
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
),
tmp_last as (
  select mid,
    case when change_event_type='C010' then 'C010在线' else 'C013_C015离线' end as tl_type
  from tmp_evt where rn=1
)
select date_trunc('week', date(f.release_time)) as w,
  case when f.temp_grant_amount>0 then 'funnel有临额' else 'funnel无临额' end as f_tmp,
  coalesce(t.tl_type, '额度表未匹配') as tl_type,
  count(distinct f.cust_id) as custs
from mx.wxs_application_funnel f
left join tmp_last t on cast(f.cust_id as bigint) = t.mid
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
group by 1,2,3 order by 1,2,3""",
  "funnel temp_grant_amount 与 额度表事件类型 匹配率")

# 4) 核心: 在线 vs 离线 vs 无 的坏账率(放款周, 静态最近一次事件打标)
q("""with tmp_evt as (
  select mid, change_event_type, create_time,
    row_number() over (partition by mid order by create_time desc) as rn
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
),
tmp_last as (
  select mid,
    case when change_event_type='C010' then '在线临额C010' else '离线临额C013_15' end as tl_type
  from tmp_evt where rn=1
)
select date_trunc('week', date(f.release_time)) as w,
  coalesce(t.tl_type, case when f.temp_grant_amount>0 then '有临额未匹配' else '无临额' end) as tl_type,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd, sum(f.if_issue) as cnt
from mx.wxs_application_funnel f
left join tmp_last t on cast(f.cust_id as bigint) = t.mid
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-24'
group by 1,2 order by 1,2""",
  "在线 vs 离线 vs 无 坏账率(放款周 静态打标)")
