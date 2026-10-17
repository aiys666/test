# -*- coding: utf-8 -*-
"""聚焦 7-9月: 离线临额客群逾期天数分布 + 批次标签 判断客群放松/收紧"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, tag="", show=80):
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

# 1) 7-9月 逾期天数 0/1/2/>2/null 占比(判断放松/收紧)
q("""
select date_trunc('week', date(temp_limit_issue_date)) as issue_week,
  count(distinct mid) as total_mids,
  count(distinct case when id_30days_max_overdue_days=0 then mid end) as ovd0,
  count(distinct case when id_30days_max_overdue_days=1 then mid end) as ovd1,
  count(distinct case when id_30days_max_overdue_days=2 then mid end) as ovd2,
  count(distinct case when id_30days_max_overdue_days>2 then mid end) as ovd_gt2,
  count(distinct case when id_30days_max_overdue_days is null then mid end) as ovd_null,
  round(100.0*count(distinct case when id_30days_max_overdue_days>0 then mid end)/nullif(count(distinct mid),0),1) as pct_has_ovd
from mx.yuhan_temp_limit_base_table_his_20260924
where temp_limit_issue_date >= cast('2026-07-01' as timestamp)
group by 1 order by 1
""", "7-9月 离线临额客群逾期天数分布")

# 2) 批次标签变化(判断档位/规则调整)
q("""
select date_trunc('week', date(temp_limit_issue_date)) as issue_week,
  temp_limit_tag,
  count(distinct mid) mids, round(avg(temp_limit_issue_amount),2) amt_avg
from mx.yuhan_temp_limit_base_table_his_20260924
where temp_limit_issue_date >= cast('2026-07-01' as timestamp)
group by 1,2 order by 1,2
""", "7-9月 离线临额批次标签")
