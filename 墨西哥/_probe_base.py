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
    print(f"\n=== {tag} ===")
    print(r.to_string(index=False) if len(r) <= 40 else r.head(40).to_string(index=False)); return r

# P1 期限×时点结构: 选一个2期产品 C_15_02_00_60(15天*2) 一个4期 B_07_04_00_60(7天*4)
# 取 2026-07-01~03 放款(已充分成熟), 看每期限 should_capit/overdue_capit 在不同时点是否一致(判断 should 是否与时点无关)
q1 = """
with s as (
 select f.biz_id, f.product_level, y.product_name_new, f.contract_amount, f.haircut_amount,
   f.t7_should_capit_1 p7c1, f.t15_should_capit_1 p15c1, f.t30_should_capit_1 p30c1,
   f.t7_should_capit_2 p7c2, f.t15_should_capit_2 p15c2, f.t30_should_capit_2 p30c2,
   f.t30_should_capit_3 p30c3, f.t30_should_capit_4 p30c4,
   f.t7_should_interest_1 p7i1, f.t15_should_interest_1 p15i1, f.t30_should_interest_1 p30i1,
   f.t7_should_interest_2 p7i2, f.t15_should_interest_2 p15i2, f.t30_should_interest_2 p30i2,
   f.t7_overdue_capit_1 o7c1, f.t30_overdue_capit_1 o30c1,
   f.t7_overdue_capit_2 o7c2, f.t30_overdue_capit_2 o30c2,
   f.is_t7_window_1 w7_1, f.is_t15_window_1 w15_1, f.is_t30_window_1 w30_1,
   f.is_t7_window_2 w7_2, f.is_t15_window_2 w15_2, f.is_t30_window_2 w30_2,
   f.is_t30_window_3 w30_3, f.is_t30_window_4 w30_4,
   f.is_t7_overdue_1 od7_1, f.is_t15_overdue_1 od15_1, f.is_t30_overdue_1 od30_1
 from mx.wxs_application_funnel f
 join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
 where f.tenant='yawey' and f.is_reloan='old' and f.if_issue=1
   and f.release_time>=date'2026-07-01' and f.release_time<date'2026-07-04'
   and f.product_level in ('C_15_02_00_60','B_07_04_00_60'))
select product_level, count(*) n,
 round(avg(contract_amount),0) ca, round(avg(haircut_amount),0) ha,
 -- 每期限应还本金是否随时点稳定(t7 vs t30)
 round(sum(case when abs(p7c1-p30c1)>0.1 then 1 else 0 end)/count(*),3) chg_c1,
 round(avg(p30c1),0) avg_c1, round(avg(p30c2),0) avg_c2, round(avg(p30c3),0) avg_c3, round(avg(p30c4),0) avg_c4,
 -- 成熟
 round(sum(w7_1)/count(*),3) mat7_1, round(sum(w15_1)/count(*),3) mat15_1, round(sum(w30_1)/count(*),3) mat30_1,
 round(sum(w7_2)/count(*),3) mat7_2, round(sum(w30_2)/count(*),3) mat30_2, round(sum(w30_3)/count(*),3) mat30_3,
 round(sum(w30_4)/count(*),3) mat30_4,
 round(avg(o30c1),0) o30c1, round(avg(o30c2),0) o30c2
from s group by 1 order by 1"""
q(q1, "P1 期限结构(应还本金随时点稳定性/每期限规模/成熟率/逾期)")

# P2 V5_3/V6_1 域值与覆盖(按月), v6_1 的 v3_flag 构成
q2 = """
with b as (select substr(cast(f.release_time as varchar),1,7) ym, f.biz_id, y.v3_flag,
  y.android_oldcust_maincreditlevel_charge_v5_3 g5, y.android_oldCust_mainCreditLevel_charge_V6_1 g6
 from mx.wxs_application_funnel f
 join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
 where f.tenant='yawey' and f.is_reloan='old' and f.if_issue=1
   and f.release_time>=date'2025-09-01' and f.release_time<date'2026-09-01')
select ym, count(*) biz,
 count(g5) g5_n, count(distinct g5) g5_d, min(g5) g5_min, max(g5) g5_max,
 count(g6) g6_n, count(distinct g6) g6_d, min(g6) g6_min, max(g6) g6_max
from b group by 1 order by 1"""
q(q2, "P2 双评级覆盖/域值 按月(2025-09~2026-08)")

q2b = """
select y.v3_flag, count(*) n,
 count(y.android_oldcust_maincreditlevel_charge_v5_3) g5_n,
 count(y.android_oldCust_mainCreditLevel_charge_V6_1) g6_n
from mx.wxs_application_funnel f
join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
where f.tenant='yawey' and f.is_reloan='old' and f.if_issue=1
  and f.release_time>=date'2026-06-01' and f.release_time<date'2026-09-01'
group by 1 order by n desc"""
q(q2b, "P2b v3_flag 构成(近期)")

# P3 yj 是否1:1 / funnel 单子是否唯一
q3 = """
select
 (select count(*) from mx.wxs_application_funnel f
   where tenant='yawey' and is_reloan='old' and if_issue=1
     and release_time>=date'2026-07-01' and release_time<date'2026-08-01') rows_n,
 (select count(distinct biz_id) from mx.wxs_application_funnel f
   where tenant='yawey' and is_reloan='old' and if_issue=1
     and release_time>=date'2026-07-01' and release_time<date'2026-08-01') biz_n,
 (select count(*) from (
    select biz_id, count(*) n from mx.yj_test_table_250225 group by 1 having count(*)>1) t) dup_yj_groups"""
q(q3, "P3 funnel行数 vs 唯一biz; yj重复组数(全表group)")

# P4 product_name_new 域(近3月老客已放款), 看是否即产品代码空间; 并与 funnel.product_level 对齐情况
q4 = """
with s as (select f.biz_id, f.product_level pl, y.product_name_new pn
 from mx.wxs_application_funnel f join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
 where f.tenant='yawey' and f.is_reloan='old' and f.if_issue=1
   and f.release_time>=date'2026-06-01' and f.release_time<date'2026-09-01')
select pn, count(*) n,
 count(distinct case when pl is not null and pl<>'' then pl end) pl_d, min(pl) pl1
from s group by 1 order by n desc"""
q(q4, "P4 yj.product_name_new 域(老客放款,近3月)")
