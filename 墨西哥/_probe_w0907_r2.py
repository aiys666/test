# -*- coding: utf-8 -*-
"""9/07周排查 第二轮: 首贷下钻(评级/产品/件均) + 本金口径 + 复贷临额残存"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 420)

def q(sql, tag="", show=150):
    print("="*130); print(tag)
    r = pq.query(sql)
    if isinstance(r, str): print("[ERR]", r[:1500]); return None
    if r is None or len(r)==0: print("[空]"); return None
    print(r.to_string() if len(r)<=show else r.head(show).to_string())
    print(f"[rows={len(r)}]"); return r

# Q2: 本金口径 vs 总额口径 (首贷/复贷 × 周)
q("""
select
  date_format(date_trunc('week', cast(app_time as timestamp)),'%Y-%m-%d') as awk,
  is_reloan,
  round(sum(if(if_issue=1 and t0_should_capit_1>0,t0_overdue_capit_1,null))
       /nullif(sum(if(if_issue=1 and t0_should_capit_1>0,t0_should_capit_1,null)),0)*100,2) as t0_capit_rate,
  round(sum(if(if_issue=1 and t0_should_amt_1>0,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1 and t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) as t0_amt_rate
from mx.wxs_application_funnel
where tenant='yawey'
  and app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and app_time <  cast('2026-09-22 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "Q2 本金口径 vs 总额口径对照")

# Q3: 首贷评级分布 9/07 vs 8/03 (report_application_funnel7_table credit_level)
q("""
select
  case when date_trunc('week', cast(r.app_time as timestamp)) = date'2026-08-03' then 'w0803'
       when date_trunc('week', cast(r.app_time as timestamp)) = date'2026-08-31' then 'w0831'
       else 'w0907' end as awk,
  coalesce(cast(f7.credit_level as varchar),'null') as grade,
  count(*) as app_cnt,
  count(if(r.if_issue=1,1,null)) as loan_cnt,
  round(count(if(r.if_issue=1,1,null))*100.0/count(*),2) as pass_rate,
  round(sum(if(r.if_issue=1 and r.t0_should_amt_1>0, r.t0_overdue_amount_1, null))
       /nullif(sum(if(r.if_issue=1 and r.t0_should_amt_1>0, r.t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(sum(if(r.if_issue=1 and r.t0_should_amt_1>0, r.t0_should_amt_1, null))/1000.0,0) as should_k,
  round(avg(if(r.if_issue=1, r.real_issue_amount, null)),0) as loan_avg
from mx.wxs_application_funnel r
left join mx.report_application_funnel7_table f7
  on r.camera_id = cast(f7.biz_id as bigint)
where r.tenant='yawey' and r.is_reloan='new'
  and r.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and r.app_time <  cast('2026-09-14 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "Q3 首贷 评级×周: 进件/通过率/坏账/件均")

# Q4: 首贷产品×周
q("""
select
  case when date_trunc('week', cast(app_time as timestamp)) = date'2026-08-03' then 'w0803'
       when date_trunc('week', cast(app_time as timestamp)) = date'2026-08-31' then 'w0831'
       else 'w0907' end as awk,
  product_name_new,
  count(*) as app_cnt,
  count(if(if_issue=1,1,null)) as loan_cnt,
  round(sum(if(if_issue=1 and t0_should_amt_1>0, t0_overdue_amount_1, null))
       /nullif(sum(if(if_issue=1 and t0_should_amt_1>0, t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(sum(if(if_issue=1 and t0_should_amt_1>0, t0_should_amt_1, null))/1000.0,0) as should_k,
  round(avg(if(if_issue=1, real_issue_amount, null)),0) as loan_avg
from mx.wxs_application_funnel
where tenant='yawey' and is_reloan='new'
  and app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and app_time <  cast('2026-09-14 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "Q4 首贷 产品×周")

# Q5: 复贷 9/07周 临额类型分解 (在线tag / 无临额)
q("""
select
  case when date_trunc('week', cast(app_time as timestamp)) = date'2026-08-03' then 'w0803'
       when date_trunc('week', cast(app_time as timestamp)) = date'2026-08-31' then 'w0831'
       else 'w0907' end as awk,
  case when temp_credit_amount_issue_tag=1 then 'online_tag1'
       when temp_credit_amount_issue_tag=0 then 'online_tag0'
       else 'no_tag' end as tl_grp,
  count(*) as loan_cnt,
  round(sum(if(t0_should_amt_1>0, t0_overdue_amount_1, null))
       /nullif(sum(if(t0_should_amt_1>0, t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(sum(if(t0_should_amt_1>0, t0_should_amt_1, null))/1000.0,0) as should_k,
  round(sum(if(t0_should_amt_1>0, t0_overdue_amount_1, null))/1000.0,0) as od_k
from mx.wxs_application_funnel
where tenant='yawey' and is_reloan='old' and if_issue=1
  and app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and app_time <  cast('2026-09-14 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "Q5 复贷 周×在线临额tag分解 (funnel表口径)")
