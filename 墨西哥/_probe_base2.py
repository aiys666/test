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

# P1b 按 yj.product_name_new 选产品(7月放款已成熟), 看每期限应还本金随时点是否恒定 & 各期规模/成熟/逾期
# 期限假设: 07_0X=7天一期, 15_0X=15天一期; 观察: 一个2期7天产品应在t7=期1到期,t15=期2到期
q1 = """
with s as (
 select f.biz_id, y.product_name_new pn, f.contract_amount ca,
   f.t0_should_capit_1 c1_t0, f.t7_should_capit_1 c1_t7, f.t15_should_capit_1 c1_t15, f.t30_should_capit_1 c1_t30,
   f.t7_should_capit_2 c2_t7, f.t15_should_capit_2 c2_t15, f.t30_should_capit_2 c2_t30,
   f.t30_should_capit_3 c3_t30, f.t30_should_capit_4 c4_t30,
   f.t0_should_interest_1 i1_t0, f.t7_should_interest_1 i1_t7, f.t30_should_interest_1 i1_t30,
   f.t15_should_interest_2 i2_t15, f.t30_should_interest_2 i2_t30,
   f.is_t0_window_1 w0_1, f.is_t7_window_1 w7_1, f.is_t15_window_1 w15_1, f.is_t30_window_1 w30_1,
   f.is_t7_window_2 w7_2, f.is_t15_window_2 w15_2, f.is_t30_window_2 w30_2,
   f.is_t30_window_3 w30_3, f.is_t30_window_4 w30_4,
   f.t7_overdue_capit_1 o7c1, f.t30_overdue_capit_1 o30c1,
   f.t15_overdue_capit_2 o15c2, f.t30_overdue_capit_2 o30c2
 from mx.wxs_application_funnel f join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
 where f.tenant='yawey' and f.is_reloan='old' and f.if_issue=1
   and f.release_time>=date'2026-07-01' and f.release_time<date'2026-07-04'
   and y.product_name_new in ('C_07_02_00_75','C_15_03_00_85','B_07_03_20_40','E_07_02_62_50X2'))
select pn,
 count(*) n, round(avg(ca),0) ca,
 -- 期1应还本金: t0/t7/t15/t30 是否一致(稳定性)
 round(sum(case when abs(c1_t0-c1_t30)>0.1 then 1 else 0 end)/count(*),3) d_c1_t0vst30,
 round(sum(case when abs(c1_t7-c1_t30)>0.1 then 1 else 0 end)/count(*),3) d_c1_t7vst30,
 round(avg(c1_t30),0) avg_c1, round(avg(c2_t30),0) avg_c2, round(avg(c3_t30),0) avg_c3, round(avg(c4_t30),0) avg_c4,
 round(avg(i1_t30),0) avg_i1, round(avg(i2_t30),0) avg_i2,
 round(sum(w0_1)/count(*),3) m0_1, round(sum(w7_1)/count(*),3) m7_1,
 round(sum(w15_1)/count(*),3) m15_1, round(sum(w30_1)/count(*),3) m30_1,
 round(sum(w15_2)/count(*),3) m15_2, round(sum(w30_2)/count(*),3) m30_2,
 round(sum(w30_3)/count(*),3) m30_3, round(sum(w30_4)/count(*),3) m30_4,
 round(sum(o30c1)/count(*),2) o30c1, round(sum(o15c2)/count(*),2) o15c2
from s group by 1 order by 1"""
q(q1, "P1b 期限×时点还款结构(7月初放款已成熟)")

# P5 funnel.product_name vs yj.product_name_new 一致性
q5 = """
with s as (select f.biz_id, f.product_name pnf, y.product_name_new pnj
 from mx.wxs_application_funnel f join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
 where f.tenant='yawey' and f.is_reloan='old' and f.if_issue=1
  and f.release_time>=date'2026-06-01' and f.release_time<date'2026-09-01')
select count(*) n,
 count(case when pnf=pnj then 1 end) same_n,
 count(case when pnf is null or pnf='' then 1 end) pnf_blank,
 count(distinct pnf) pnf_d, count(distinct pnj) pnj_d
from s"""
q(q5, "P5 funnel.product_name vs yj.product_name_new")

# P6 loan_indexs / loan_cycle 取值(7月老客放款)
q6 = """
select loan_indexs, loan_cycle, count(*) n
from mx.wxs_application_funnel f
where tenant='yawey' and is_reloan='old' and if_issue=1
 and release_time>=date'2026-07-01' and release_time<date'2026-08-01'
group by 1,2 order by n desc limit 25"""
q(q6, "P6 loan_indexs × loan_cycle 取值")
