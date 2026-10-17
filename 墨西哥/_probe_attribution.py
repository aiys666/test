# -*- coding: utf-8 -*-
"""探针：验证连接、funnel表7月来复贷行数、关键字段存在性"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

def q(sql):
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:300])
        return None
    return r

# 1. 复贷 old 行数规模（按 app_week）
print("=" * 100)
print("[1] funnel 表复贷(old) 7/1起 按周行数")
s1 = """
select date_trunc('week', date(create_time)) as wk,
       count(*) as rows_cnt,
       count(distinct biz_id) as biz_cnt
from mx.wxs_application_funnel
where is_reloan = 'old'
  and date(create_time) >= date '2026-07-01'
group by 1 order by 1
"""
d1 = q(s1)
if d1 is not None:
    print(d1.to_string(index=False))

# 2. tenant 分布
print("=" * 100)
print("[2] tenant 分布 (7/1起复贷old)")
s2 = """
select tenant, count(*) as cnt
from mx.wxs_application_funnel
where is_reloan = 'old'
  and date(create_time) >= date '2026-07-01'
group by 1 order by 2 desc
"""
d2 = q(s2)
if d2 is not None:
    print(d2.to_string(index=False))

# 3. 关键字段存在性检查（取1行）
print("=" * 100)
print("[3] 关键字段非空检查 (7/1起复贷old, 样本)")
s3 = """
select
  count(*) as n,
  count(if(android_oldcust_maincreditlevel_charge_v5_3 is not null,1,null)) as v53,
  count(if(android_oldCust_mainCreditLevel_charge_V6_1 is not null,1,null)) as v61,
  count(if(android_oldcust_midcreditlevel_charge_v5_3 is not null,1,null)) as v53mid,
  count(if(android_oldCust_midCreditLevel_charge_V6_1 is not null,1,null)) as v61mid,
  count(if(other_app_has_overdue_tag is not null,1,null)) as oth_tag,
  count(if(v3_flag_huidu is not null,1,null)) as huidu,
  count(if(is_t7_window_4 is not null,1,null)) as t7w4,
  count(if(t7_should_capit_4 is not null,1,null)) as t7sc4,
  count(if(t7_overdue_capit_4 is not null,1,null)) as t7oc4,
  count(if(t7_should_interest_4 is not null,1,null)) as t7si4,
  count(if(t7_overdue_interest_4 is not null,1,null)) as t7oi4,
  count(if(is_t0_window_1 is not null,1,null)) as t0w1,
  count(if(if_in_sx is not null,1,null)) as insx,
  count(if(if_sx_passed is not null,1,null)) as sxpass,
  count(if(if_sx_passed_24h is not null,1,null)) as sx24,
  count(if(reloan_num is not null,1,null)) as reloan,
  count(if(grant_score is not null,1,null)) as gscore,
  count(if(channel_category is not null,1,null)) as chcat,
  count(if(new_media_source is not null,1,null)) as media
from mx.wxs_application_funnel
where is_reloan = 'old'
  and date(create_time) >= date '2026-07-01'
"""
d3 = q(s3)
if d3 is not None:
    print(d3.to_string(index=False))

# 4. yj_test_table_250225 字段检查
print("=" * 100)
print("[4] yj_test_table_250225 7/1起 行数 + 关键字段")
s4 = """
select count(*) as n,
  count(if(android_oldcust_maincreditlevel_charge_v5_3 is not null,1,null)) as v53,
  count(if(android_oldCust_mainCreditLevel_charge_V6_1 is not null,1,null)) as v61,
  count(if(android_oldcust_overdue_subscore_charge_V6_1 is not null,1,null)) as ovdsub,
  count(if(max_ovd_days_all is not null,1,null)) as maxovd,
  count(if(max_overdue_day_30d_all is not null,1,null)) as maxovd30,
  count(if(other_app_has_overdue_tag is not null,1,null)) as oth_tag,
  count(if(other_app_has_overdue_interval_tag is not null,1,null)) as oth_interval,
  count(if(emcontact_curr_ovd_cnt_all_test_flag is not null,1,null)) as emcontact
from mx.yj_test_table_250225
where date(app_time) >= date '2026-07-01'
"""
d4 = q(s4)
if d4 is not None:
    print(d4.to_string(index=False))

# 5. 评级取值分布（确认1-10还是别的）
print("=" * 100)
print("[5] V5_3 / V6_1 主评级取值分布 (7/1起复贷old)")
s5 = """
select android_oldcust_maincreditlevel_charge_v5_3 as v53,
       android_oldCust_mainCreditLevel_charge_V6_1 as v61,
       count(*) as cnt
from mx.wxs_application_funnel
where is_reloan = 'old'
  and date(create_time) >= date '2026-07-01'
group by 1,2 order by 1,2
"""
d5 = q(s5)
if d5 is not None:
    print(d5.to_string(index=False))

print("=" * 100)
print("DONE")
