# -*- coding: utf-8 -*-
"""校验 yj_test_table_250225 的关键字段 + 粒度"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, tag="", show=40):
    print("="*110)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:800]); return None
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 250)
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# 1) yj 表全部列名（找关键字段）
r = pq.query("select * from mx.yj_test_table_250225 limit 1")
if not isinstance(r, str):
    cols = list(r.columns)
    print("yj表总列数:", len(cols))
    keys = ['mid','biz_id','release_time','app_time','if_issue','is_t3_window','is_t0_window',
            'temp_grant','loan_cycle','reloan_num','is_reloan','tenant','cust_id','app_date',
            'contract_amount','app_week','issue','product','overdue']
    for c in cols:
        if any(k in c.lower() for k in keys):
            print("  ", c)

# 2) 粒度: is_t3_window_1=1 下 biz_id 唯一性 + 时间窗行数
q("""
select count(*) rows_cnt, count(distinct biz_id) biz_cnt, count(distinct mid) mid_cnt
from mx.yj_test_table_250225
where is_t3_window_1=1
  and app_time >= cast('2026-05-22 00:00:00.000' as timestamp)
""", "yj表 is_t3_window_1=1 + app_time 粒度")

# 3) 关键字段是否有值
q("""
select count(*) rows_cnt,
  count(release_time) release_cnt,
  count(if_issue) if_issue_cnt,
  count(temp_grant_amount) temp_grant_cnt,
  count(loan_cycle) loan_cycle_cnt,
  count(reloan_num) reloan_cnt,
  count(is_reloan) is_reloan_cnt,
  count(tenant) tenant_cnt
from mx.yj_test_table_250225
where is_t3_window_1=1
  and app_time >= cast('2026-05-22 00:00:00.000' as timestamp)
""", "yj表关键字段非空计数")
