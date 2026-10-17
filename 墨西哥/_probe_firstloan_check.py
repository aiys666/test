# -*- coding: utf-8 -*-
"""验证首贷表 + wxs_application_funnel 的 cust_id 关联"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql):
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:300]); return None
    return r

# 1) 首贷表字段 + 行数 + 日期范围
print("="*100)
print("首贷表 mx.ys_dl_ltv_first_loan_0511 探查")
r1 = q("select count(*) cnt, count(distinct biz_id) biz, count(distinct mid) mid, min(ltv_date) mn, max(ltv_date) mx from mx.ys_dl_ltv_first_loan_0511")
print(r1)

# 2) wxs_application_funnel 是否有 cust_id
print("="*100)
print("wxs_application_funnel 是否有 cust_id")
r2 = q("select count(*) cnt, count(distinct cust_id) cust from mx.wxs_application_funnel where is_reloan='old' and tenant='yawey' and date(create_time) between date '2026-08-08' and date '2026-08-16'")
print(r2)

# 3) 复贷老客 cust_id 能否命中首贷表
print("="*100)
print("8/8~8/16 复贷老客 cust_id 命中首贷表的比例")
r3 = q("""
select count(distinct f.cust_id) as reloan_cust,
       count(distinct fl.mid) as hit_cust
from mx.wxs_application_funnel f
left join mx.ys_dl_ltv_first_loan_0511 fl on cast(f.cust_id as bigint) = fl.mid
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.create_time) between date '2026-08-08' and date '2026-08-16'
""")
print(r3)
