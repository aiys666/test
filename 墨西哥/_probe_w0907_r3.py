# -*- coding: utf-8 -*-
"""第三轮: 首贷评级修正 + 产品结构分解 + A产品深查"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 420)

def q(sql, tag="", show=200):
    print("="*130); print(tag)
    r = pq.query(sql)
    if isinstance(r, str): print("[ERR]", r[:1500]); return None
    if r is None or len(r)==0: print("[空]"); return None
    print(r.to_string() if len(r)<=show else r.head(show).to_string())
    print(f"[rows={len(r)}]"); return r

WK = """case when date_trunc('week', cast(r.app_time as timestamp)) = date'2026-08-03' then 'w0803'
     when date_trunc('week', cast(r.app_time as timestamp)) = date'2026-08-10' then 'w0810'
     when date_trunc('week', cast(r.app_time as timestamp)) = date'2026-08-17' then 'w0817'
     when date_trunc('week', cast(r.app_time as timestamp)) = date'2026-08-24' then 'w0824'
     when date_trunc('week', cast(r.app_time as timestamp)) = date'2026-08-31' then 'w0831'
     else 'w0907' end"""

# Q3修正: 首贷评级×周
q(f"""
select
  {WK} as awk,
  coalesce(cast(f7.credit_level as varchar),'null') as grade,
  count(*) as app_cnt,
  count(if(r.if_issue=1,1,null)) as loan_cnt,
  round(count(if(r.if_issue=1,1,null))*100.0/count(*),2) as pass_rate,
  round(sum(if(r.if_issue=1 and r.t0_should_amt_1>0, r.t0_overdue_amount_1, null))
       /nullif(sum(if(r.if_issue=1 and r.t0_should_amt_1>0, r.t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(sum(if(r.if_issue=1 and r.t0_should_amt_1>0, r.t0_should_amt_1, null))/1000.0,0) as should_k
from mx.wxs_application_funnel r
left join mx.report_application_funnel7_table f7
  on r.camera_id = cast(f7.biz_id as bigint)
where r.tenant='yawey' and r.is_reloan='new'
  and r.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and r.app_time <  cast('2026-09-14 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "Q3修正 首贷评级×周")

# Q6: A产品(7天) 按周×评级 — 它占首贷61%, 谁在里面?
q(f"""
select
  {WK} as awk,
  coalesce(cast(f7.credit_level as varchar),'null') as grade,
  count(if(r.if_issue=1,1,null)) as loan_cnt,
  round(count(if(r.if_issue=1,1,null))*100.0/count(*),2) as pass_rate,
  round(sum(if(r.if_issue=1 and r.t0_should_amt_1>0, r.t0_overdue_amount_1, null))
       /nullif(sum(if(r.if_issue=1 and r.t0_should_amt_1>0, r.t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(avg(if(r.if_issue=1, r.issue_amount, null)),0) as loan_avg
from mx.wxs_application_funnel r
left join mx.report_application_funnel7_table f7
  on r.camera_id = cast(f7.biz_id as bigint)
where r.tenant='yawey' and r.is_reloan='new' and r.product_name='A_07_01_50_00'
  and r.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and r.app_time <  cast('2026-09-14 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "Q6 A产品(7天小额) 周×评级")

# Q7: E_07_03 大额产品 周×评级 (9/07坏账跳升10pp原因)
q(f"""
select
  {WK} as awk,
  coalesce(cast(f7.credit_level as varchar),'null') as grade,
  count(if(r.if_issue=1,1,null)) as loan_cnt,
  round(count(if(r.if_issue=1,1,null))*100.0/count(*),2) as pass_rate,
  round(sum(if(r.if_issue=1 and r.t0_should_amt_1>0, r.t0_overdue_amount_1, null))
       /nullif(sum(if(r.if_issue=1 and r.t0_should_amt_1>0, r.t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(avg(if(r.if_issue=1, r.issue_amount, null)),0) as loan_avg
from mx.wxs_application_funnel r
left join mx.report_application_funnel7_table f7
  on r.camera_id = cast(f7.biz_id as bigint)
where r.tenant='yawey' and r.is_reloan='new' and r.product_name='E_07_03_41_40X2_20'
  and r.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and r.app_time <  cast('2026-09-14 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "Q7 E_07_03大额产品 周×评级")
