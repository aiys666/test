# -*- coding: utf-8 -*-
"""第四轮: 首贷件均/授信按评级×周 + 通过率趋势 + 复贷平台确认"""
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

# Q8: 首贷评级×周: 授信额度/放款件均/首期应还件均 — 验证提额
q(f"""
select
  {WK} as awk,
  cast(f7.credit_level as varchar) as grade,
  count(if(r.if_issue=1,1,null)) as loan_cnt,
  round(avg(if(r.if_issue=1, r.issue_amount, null)),0) as issue_avg,
  round(avg(if(r.if_issue=1, r.credit_amount_sx, null)),0) as credit_avg,
  round(avg(if(r.if_issue=1, r.approve_amount, null)),0) as approve_avg,
  round(sum(if(r.if_issue=1 and r.t0_should_amt_1>0, r.t0_should_amt_1, null))
       /nullif(count(if(r.if_issue=1 and r.t0_should_amt_1>0,1,null)),0),0) as t0_should_avg
from mx.wxs_application_funnel r
left join mx.report_application_funnel7_table f7
  on r.camera_id = cast(f7.biz_id as bigint)
where r.tenant='yawey' and r.is_reloan='new' and f7.credit_level is not null
  and r.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and r.app_time <  cast('2026-09-14 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "Q8 首贷评级×周: 件均/授信/首期应还 (验证提额)")

# Q9: 首贷按日进件量+通过率 (看放量节奏和风控松紧的突变点)
q("""
select
  date_format(cast(app_time as timestamp),'%Y-%m-%d') as dt,
  count(*) as app_cnt,
  count(if(if_issue=1,1,null)) as loan_cnt,
  round(count(if(if_issue=1,1,null))*100.0/count(*),2) as pass_rate
from mx.wxs_application_funnel
where tenant='yawey' and is_reloan='new'
  and app_time >= cast('2026-08-25 00:00:00.000' as timestamp)
  and app_time <  cast('2026-09-14 00:00:00.000' as timestamp)
group by 1 order by 1
""", "Q9 首贷 按日进件/放款/通过率 (找放量突变点)")
