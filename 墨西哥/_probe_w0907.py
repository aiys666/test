# -*- coding: utf-8 -*-
"""9/07周 1t0本金坏账高企 全方位排查 - 第一轮: 口径确认+大盘定位"""
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

# Q0: funnel表 t0 本金/利息相关字段
q("""
select column_name from information_schema.columns
where table_schema='mx' and table_name='wxs_application_funnel'
  and column_name like '%t0%' and (column_name like '%principal%' or column_name like '%should%' or column_name like '%overdue%')
order by 1
""", "Q0 funnel表t0本金/应还/逾期字段")

# Q1: 大盘按进件周(7月下旬-9月下旬) 首贷vs复贷 总额口径
q("""
select
  date_format(date_trunc('week', cast(app_time as timestamp)),'%Y-%m-%d') as awk,
  is_reloan,
  count(*) as app_cnt,
  count(if(if_issue=1,1,null)) as loan_cnt,
  count(if(if_issue=1 and t0_should_amt_1>0,1,null)) as mature,
  round(sum(if(if_issue=1 and t0_should_amt_1>0,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1 and t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) as t0_rate,
  round(sum(if(if_issue=1 and t0_should_amt_1>0,t0_should_amt_1,null))/1000.0,0) as should_k,
  round(sum(if(if_issue=1 and t0_should_amt_1>0,t0_overdue_amount_1,null))/1000.0,0) as od_k
from mx.wxs_application_funnel
where tenant='yawey'
  and app_time >= cast('2026-07-20 00:00:00.000' as timestamp)
  and app_time <  cast('2026-09-22 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "Q1 大盘按进件周 首贷vs复贷 1t0总额口径(定位9/07周水平)")
