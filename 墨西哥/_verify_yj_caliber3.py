# -*- coding: utf-8 -*-
"""确认 yj 表关键字段名 + 样本"""
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

# 找评级相关字段
r = pq.query("select * from mx.yj_test_table_250225 limit 1")
if not isinstance(r, str):
    cols = list(r.columns)
    for kw in ['creditlevel','duotou','repayment_clearing','reloan','cycle']:
        print(f"--- {kw} ---")
        for c in cols:
            if kw in c.lower():
                print("  ", c)

# 样本: 看一条记录的关键字段值
q("""
select biz_id, mid, cust_id, app_date, app_week, app_time, release_time, if_issue,
  is_t3_window_1, t0_should_amt_1, t0_overdue_amount_1, t3_should_amt_1, t3_overdue_amount_1,
  temp_grant_amount, loan_cycle, tenant, is_reloan,
  android_oldcust_maincreditlevel_charge_v5_3,
  repayment_clearing_count_tenant, advance_duotou_cnt_x_19
from mx.yj_test_table_250225
where is_t3_window_1=1
  and app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
limit 5
""", "yj 样本(8月后)")
