# -*- coding: utf-8 -*-
import sys; sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
import pandas as pd
from mexico_presto import PrestoQuery
pq = PrestoQuery(); pq.login()
def q(sql, tag):
    r = pq.query(sql)
    if isinstance(r, str):
        print(f"[{tag}] ERR:", r[:300]); return None
    print(f"\n=== {tag} ==="); print(r.to_string(index=False)); return r

# 取 2026-07-02 放款(约65天)的 C_15_03_00_85(15天*3: 期1~3各15天) 一笔, 打印关键字段
q1 = """
with one as (
 select f.biz_id,
  f.contract_amount ca, f.haircut_amount ha, f.amount amt_disp, f.should_interest si_all,
  f.t0_should_capit_1 c1_t0, f.t3_should_capit_1 c1_t3, f.t7_should_capit_1 c1_t7,
  f.t15_should_capit_1 c1_t15, f.t30_should_capit_1 c1_t30,
  f.t7_should_capit_2 c2_t7, f.t15_should_capit_2 c2_t15, f.t30_should_capit_2 c2_t30,
  f.t0_should_capit_3 c3_t0, f.t7_should_capit_3 c3_t7, f.t15_should_capit_3 c3_t15, f.t30_should_capit_3 c3_t30,
  f.t7_should_amt_1 a1_t7, f.t30_should_amt_1 a1_t30,
  f.t7_overdue_capit_1 o1_t7, f.t30_overdue_capit_1 o1_t30,
  f.t15_overdue_capit_2 o2_t15, f.t30_overdue_capit_2 o2_t30,
  f.t7_overdue_interest_1 oi1_t7, f.t30_overdue_interest_1 oi1_t30,
  f.is_t0_window_1 w0_1, f.is_t7_window_1 w7_1, f.is_t15_window_1 w15_1, f.is_t30_window_1 w30_1,
  f.is_t7_window_2 w7_2, f.is_t15_window_2 w15_2, f.is_t30_window_2 w30_2,
  f.is_t0_window_3 w0_3, f.is_t15_window_3 w15_3, f.is_t30_window_3 w30_3,
  f.is_t7_overdue_1 od7_1, f.is_t30_overdue_1 od30_1,
  date_format(date(f.release_time),'%Y-%m-%d') rd, date_format(current_date,'%Y-%m-%d') today
 from mx.wxs_application_funnel f
 where f.tenant='yawey' and f.is_reloan='old' and f.if_issue=1
  and f.product_name='C_15_03_00_85'
  and f.release_time>=date'2026-07-02' and f.release_time<date'2026-07-03'
 limit 1)
select * from one"""
q(q1, "解剖 C_15_03(15天*3) 65天龄单子")
