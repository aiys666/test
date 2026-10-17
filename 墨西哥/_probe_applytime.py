# -*- coding: utf-8 -*-
"""第三轮: funnel表 apply_time vs app_time 关系确认"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 400)
pd.set_option('display.max_colwidth', 50)

def q(sql, tag="", show=60):
    print("="*120)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:800]); return None
    if r is None or len(r) == 0:
        print("[空数据]"); return None
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# 1) funnel表 apply_time vs app_time 同日性
q("""
select
  count(*) cnt,
  count_if(apply_time is null) apply_null,
  count_if(app_time is null) app_null,
  count_if(date(apply_time) = date(app_time)) same_day,
  count_if(date(apply_time) != date(app_time)) diff_day,
  count_if(apply_time < app_time) apply_lt_app,
  count_if(apply_time > app_time) apply_gt_app
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey'
  and app_time >= cast('2026-08-01 00:00:00.000' as timestamp)
  and app_time <  cast('2026-09-28 00:00:00.000' as timestamp)
""", "Q1 funnel apply_time vs app_time 同日性(8/1~9/28)")

# 2) 若不同日, 看差异天数分布
q("""
select
  date_diff('day', date(apply_time), date(app_time)) as diff_days,
  count(*) cnt
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey'
  and app_time >= cast('2026-08-01 00:00:00.000' as timestamp)
  and app_time <  cast('2026-09-28 00:00:00.000' as timestamp)
  and apply_time is not null
group by 1 order by 1
""", "Q2 apply_time-app_time 差异天数分布")
