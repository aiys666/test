# -*- coding: utf-8 -*-
"""离线临额表: 按 temp_limit_issue_date 周聚合 数量/金额/客群逾期天数 变化"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, tag="", show=60):
    print("="*120)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:800]); return None
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 260)
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# 0) 表结构确认
q("select * from mx.yuhan_temp_limit_base_table_his_20260924 limit 1", "离线临额表样本")

# 1) 按周聚合: 发放数量 + 金额
q("""
select date_trunc('week', date(temp_limit_issue_date)) as issue_week,
  count(*) rows_cnt, count(distinct mid) mids,
  sum(temp_limit_issue_amount) amt_sum,
  round(avg(temp_limit_issue_amount),2) amt_avg,
  round(sum(curr_main_credit_limit)/count(distinct mid),2) main_avg,
  round(avg(temp_limit_issue_amount)/nullif(avg(curr_main_credit_limit),0)*100,1) as amt_ratio_pct
from mx.yuhan_temp_limit_base_table_his_20260924
where temp_limit_issue_date is not null
group by 1 order by 1
""", "离线临额按周: 数量/金额/占主额比例")

# 2) 客群逾期天数分布变化 (判断是否放松客群)
q("""
select date_trunc('week', date(temp_limit_issue_date)) as issue_week,
  case when id_30days_max_overdue_days is null then 'null'
       when id_30days_max_overdue_days = 0 then '0天'
       when id_30days_max_overdue_days = 1 then '1天'
       when id_30days_max_overdue_days = 2 then '2天'
       when id_30days_max_overdue_days > 2 then '>2天' end as ovd_bucket,
  count(distinct mid) mids
from mx.yuhan_temp_limit_base_table_his_20260924
where temp_limit_issue_date is not null
group by 1,2 order by 1,2
""", "离线临额客群: 近30天最大逾期天数分布(按周)")

# 3) 有在贷 vs 无在贷 (tag 判断)
q("""
select date_trunc('week', date(temp_limit_issue_date)) as issue_week,
  case when onloan_cnt > 0 then '有在贷' else '无在贷' end as onloan,
  count(distinct mid) mids, round(avg(temp_limit_issue_amount),2) amt_avg
from mx.yuhan_temp_limit_base_table_his_20260924
where temp_limit_issue_date is not null
group by 1,2 order by 1,2
""", "离线临额: 有在贷/无在贷 数量金额(按周)")
