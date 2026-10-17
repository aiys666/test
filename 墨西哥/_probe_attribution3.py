# -*- coding: utf-8 -*-
"""探针3：评级取值分布、v3_flag、product_name_new、放款量、if_issue"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

def q(sql):
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:400])
        return None
    return r

# 1. yj 表评级取值分布
print("=" * 100)
print("[1] yj 表 V5_3/V6_1 主评级 + v3_flag 取值分布 (7/1起)")
s1 = """
select android_oldcust_maincreditlevel_charge_v5_3 as v53,
       android_oldcust_maincreditlevel_charge_v6_1 as v61,
       v3_flag,
       count(*) as cnt
from mx.yj_test_table_250225
where date(app_time) >= date '2026-07-01'
group by 1,2,3 order by 1,2,3
"""
d1 = q(s1)
if d1 is not None:
    print(d1.to_string(index=False))

# 2. product_name_new 取值分布
print("=" * 100)
print("[2] yj 表 product_name_new 取值分布 (top 30)")
s2 = """
select product_name_new, count(*) as cnt
from mx.yj_test_table_250225
where date(app_time) >= date '2026-07-01'
group by 1 order by 2 desc limit 30
"""
d2 = q(s2)
if d2 is not None:
    print(d2.to_string(index=False))

# 3. funnel 放款量（if_issue=1）
print("=" * 100)
print("[3] funnel 复贷old 放款行数(if_issue=1) 按放款周")
s3 = """
select date_trunc('week', date(release_time)) as iwk,
       count(*) as issue_rows,
       count(distinct biz_id) as biz
from mx.wxs_application_funnel
where is_reloan = 'old'
  and date(create_time) >= date '2026-07-01'
  and if_issue = 1
group by 1 order by 1
"""
d3 = q(s3)
if d3 is not None:
    print(d3.to_string(index=False))

# 4. v3_flag_huidu 取值
print("=" * 100)
print("[4] v3_flag_huidu 取值分布")
s4 = """
select v3_flag_huidu, count(*) as cnt
from mx.yj_test_table_250225
where date(app_time) >= date '2026-07-01'
group by 1 order by 2 desc
"""
d4 = q(s4)
if d4 is not None:
    print(d4.to_string(index=False))

# 5. 首贷金额区间字段：funnel 有 contract_amount 段；确认 first_issue_date/首贷金额
print("=" * 100)
print("[5] funnel 复贷old 放款单 contract_amount 分布")
s5 = """
select case when contract_amount<500 then 'lt500' when contract_amount<1000 then '500_1k'
            when contract_amount<2000 then '1k_2k' when contract_amount<3000 then '2k_3k'
            when contract_amount<5000 then '3k_5k' else 'ge5k' end as amt,
       count(*) as cnt
from mx.wxs_application_funnel
where is_reloan = 'old'
  and date(create_time) >= date '2026-07-01'
  and if_issue = 1
group by 1 order by 1
"""
d5 = q(s5)
if d5 is not None:
    print(d5.to_string(index=False))

# 6. 评级表字段：V6_1 逾期模型子分取值范围
print("=" * 100)
print("[6] V6_1 逾期子分 / V5_3 规则分 取值范围")
s6 = """
select min(android_oldcust_overdue_subscore_charge_v6_1) as ovd_min,
       max(android_oldcust_overdue_subscore_charge_v6_1) as ovd_max,
       min(android_oldcust_rulescore_charge_v5_3) as rule53_min,
       max(android_oldcust_rulescore_charge_v5_3) as rule53_max,
       min(android_oldcust_votescore_charge_v5_3) as vote53_min,
       max(android_oldcust_votescore_charge_v5_3) as vote53_max
from mx.yj_test_table_250225
where date(app_time) >= date '2026-07-01'
"""
d6 = q(s6)
if d6 is not None:
    print(d6.to_string(index=False))

print("=" * 100)
print("DONE")
