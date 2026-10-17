# -*- coding: utf-8 -*-
"""严格复现Excel问题1口径: flag × issue_tag × 两窗口, 不做C010打标
窗口1: app_date 7/1-8/27 (V5_3为8/10-8/27的B+C组,70%灰度)
窗口2: app_date 9/5-10/6 (V5_3仅C组,30%灰度)
"""
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
    print(r.head(show).to_string() if len(r)>show else r.to_string())
    print(f"[rows={len(r)}]"); return r

# 精确复现Excel: flag × tag × 窗口
# T0金额逾期率 = sum(t0_overdue_amount_1)/sum(t0_should_amt_1), 分母为到期(t0_should>0)
sql_tmpl = """
select
  case when temp_credit_amount_strategy_test_flag like '%%V5_2%%' then 'V5_2'
       when temp_credit_amount_strategy_test_flag like '%%V5_3%%' then 'V5_3'
       else 'null_flag' end as flag,
  case when temp_credit_amount_issue_tag is null then 'null_tag'
       when temp_credit_amount_issue_tag = 0 then 'tag0'
       else 'tag1' end as tag,
  count(*) as app_cnt,
  count(if(if_issue=1,1,null)) as deal_cnt,
  count(if(if_issue=1 and t0_should_amt_1 > 0,1,null)) as t0_mature,
  round(sum(if(if_issue=1 and t0_should_amt_1>0,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1 and t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) as t0_amt_rate,
  round(sum(if(if_issue=1 and t0_should_amt_1>0,t0_overdue_amount_1,null))/1000.0,0) as od_k,
  round(sum(if(if_issue=1 and t0_should_amt_1>0,t0_should_amt_1,null))/1000.0,0) as should_k,
  -- T3各期金额逾期率(有t3字段的话)
  round(avg(if(if_issue=1,real_issue_amount,null)),0) loan_avg,
  count(if(if_issue=1 and temp_grant_amount>0,1,null)) temp_used,
  round(avg(if(if_issue=1,credit_amount,null)),0) credit_avg
from mx.yj_test_table_250225
where is_reloan='old'
  and app_date >= date'{d0}' and app_date < date'{d1}'
group by 1,2 order by 1,2
"""

r1 = q(sql_tmpl.format(d0='2026-07-01', d1='2026-08-28'), "复现窗口1 (app 7/1-8/27)")
r2 = q(sql_tmpl.format(d0='2026-09-05', d1='2026-10-07'), "复现窗口2 (app 9/5-10/6)")

# 进一步: V5_3 tag1 人群按周看坏账趋势(是否持续上升)
q("""
select
  date_format(date_trunc('week', app_date),'%Y-%m-%d') awk,
  case when temp_credit_amount_strategy_test_flag like '%V5_2%' then 'V5_2' else 'V5_3' end flag,
  count(if(if_issue=1,1,null)) deal,
  count(if(if_issue=1 and t0_should_amt_1>0,1,null)) mature,
  round(sum(if(if_issue=1 and t0_should_amt_1>0,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1 and t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and temp_credit_amount_issue_tag=1
  and app_date >= date'2026-08-07' and app_date < date'2026-10-06'
group by 1,2 order by 1,2
""", "tag1发临额人群 按进件周×策略 T0坏账趋势")

# 关键对比: 同窗口同tag1, V5_3 vs V5_2 客户资质差异(为什么V5_3发的临额坏账高)
q("""
select
  case when temp_credit_amount_strategy_test_flag like '%V5_2%' then 'V5_2' else 'V5_3' end flag,
  count(*) deal,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) t0_rate,
  round(avg(cast(fd_creditlevel_main_v4_2 as double)),2) grade42,
  round(count(if(cast(fd_creditlevel_main_v4_2 as double)<=5,1,null))*100.0/count(*),1) g1_5pct,
  round(count(if(cast(fd_creditlevel_main_v4_2 as double)>=9,1,null))*100.0/count(*),1) g9p_pct,
  round(avg(fd_use_creditamount_score_v1),2) score_avg,
  round(avg(real_issue_amount),0) loan_avg,
  round(avg(temp_grant_amount)/1000.0,0) temp_avg,
  round(avg(credit_amount),0) credit_avg,
  round(avg(repayment_clearing_count_tenant),1) clear_cnt
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old' and temp_credit_amount_issue_tag=1
  and app_date >= date'2026-09-05' and app_date < date'2026-10-07'
group by 1 order by 1
""", "窗口2 tag1: V5_3 vs V5_2 发临额人群资质对比(坏账差异根源)")

import pickle
pickle.dump({"w1":r1,"w2":r2}, open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_xlsx_repro.pkl","wb"))
