# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from mexico_presto import PrestoQuery

sql = """
select count(*) rows_all,
       sum(if(is_t0_window = 1, 1, 0)) mc_t0,
       sum(if(is_t0_window = 1 and is_t0_overdue = 1, 1, 0)) oc_flag_eq1,
       round(sum(if(is_t0_window=1 and is_t0_overdue=1,1,0)) * 1.0 / nullif(sum(if(is_t0_window=1,1,0)),0), 4) rate_flag,
       round(avg(if(is_t0_window = 1, is_t0_overdue, null)), 4) avg_flag,
       min(is_t0_overdue) mn, max(is_t0_overdue) mx,
       count(distinct if(is_t0_window=1 and is_t0_overdue>=1, camera_id, null)) oc_ge1
from mx.wxs_application_funnel
where is_reloan='old' and if_issue=1 and product_name='E_07_01_80_100'
  and date(release_time)>=date '2026-07-01' and date(release_time)<date '2026-08-01'
"""
pq = PrestoQuery(); pq.login()
r = pq.query(sql)
print(r.to_string() if not isinstance(r, str) else r)
