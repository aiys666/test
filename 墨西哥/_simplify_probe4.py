# -*- coding: utf-8 -*-
"""抽样贷款行, 看 期次1..4 在各窗口(t0/t3/t7)的应还本金/应还息费结构与门控, 判断期次语义."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
pq = PrestoQuery(); pq.login()

def q(sql):
    r = pq.query(sql)
    if isinstance(r, str):
        raise RuntimeError(r[:500])
    return r

def sample(prod, lim=6):
    return q(f"""
select f.biz_id, date_format(cast(f.release_time as date),'%Y-%m-%d') rel,
 f.product_name prod, f.contract_amount ca, f.loan_cycle cyc,
 f.haircut_amount ha, round(cast(f.should_interest as double),2) si,
 t0_should_capit_1 s1_0, t0_should_capit_2 s2_0, t0_should_capit_3 s3_0, t0_should_capit_4 s4_0,
 t0_should_interest_1 i1_0, t0_should_interest_2 i2_0, t0_should_interest_3 i3_0, t0_should_interest_4 i4_0,
 t0_overdue_capit_1 o1_0, t0_overdue_capit_2 o2_0,
 t3_should_capit_1 s1_3, t3_should_capit_2 s2_3, t3_should_capit_3 s3_3, t3_should_capit_4 s4_3,
 t7_should_capit_1 s1_7, t7_should_capit_2 s2_7, t7_should_capit_3 s3_7, t7_should_capit_4 s4_7,
 is_t0_window_1 w1_0, is_t0_window_2 w2_0, is_t0_window_3 w3_0, is_t0_window_4 w4_0,
 is_t3_window_1 w1_3, is_t7_window_1 w1_7
from mx.wxs_application_funnel f
where f.tenant='yawey' and f.if_issue=1 and f.is_reloan='old'
 and f.product_name='{prod}' and f.release_time>=date'2026-08-01' and f.release_time<date'2026-08-15'
order by f.biz_id limit {lim}""")

for prod in ("A_07_01_50_00", "C_07_04_00_75", "B_07_02_00_75"):
    df = sample(prod)
    print(f"\n======== 产品 {prod} ========")
    if isinstance(df, str):
        print(df); continue
    for c in df.columns:
        if c not in ("biz_id", "rel", "prod"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    print(df.to_string(index=False))
