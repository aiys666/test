# -*- coding: utf-8 -*-
"""复贷坏账下降根因排查: 0920 V5_3降 / 0921 1t0降 / 0922 V6_1拒尾"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 500)

def q(sql, tag="", show=200):
    print("="*140); print(tag)
    r = pq.query(sql)
    if isinstance(r, str): print("[ERR]", r[:1800]); return None
    if r is None or len(r)==0: print("[空]"); return None
    print(r.to_string() if len(r)<=show else r.head(show).to_string())
    print(f"[rows={len(r)}]"); return r

# Q0: yj表坏账/日期/窗口字段确认
q("""
select column_name from information_schema.columns
where table_schema='mx' and table_name='yj_test_table_250225'
  and (column_name like '%t0_should%' or column_name like '%t0_overdue%'
       or column_name like '%t0_window%' or column_name like '%issue_date%'
       or column_name like '%app_date%' or column_name like '%release%')
order by 1
""", "Q0 yj表 t0/日期/窗口字段")

# Q1: 全复贷按日 1t0本金% + 成熟度(按 app_date)
q("""
select app_date,
  count(*) app_cnt,
  count(if(if_issue=1,1,null)) issue_cnt,
  count(if(if_issue=1 and t0_should_amt_1>0,1,null)) mature_cnt,
  count(if(if_issue=1 and is_t0_window_1=1,1,null)) t0_window1_cnt,
  round(sum(if(if_issue=1 and t0_should_amt_1>0,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1 and t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) t0_rate_amt,
  round(sum(if(if_issue=1 and is_t0_window_1=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1 and is_t0_window_1=1,t0_should_amt_1,null)),0)*100,2) t0_rate_window1,
  round(sum(if(if_issue=1,real_issue_amount,null))/1000.0,0) issue_amt_k,
  round(avg(if(if_issue=1,real_issue_amount,null)),0) issue_avg
from mx.yj_test_table_250225
where is_reloan='old' and app_date >= date'2026-09-14' and app_date <= date'2026-09-30'
group by 1 order by 1
""", "Q1 全复贷按日 1t0本金% + 成熟度 + 件均(9/14-9/30)")

# Q2: V5_3评级按日×评级段 1t0本金% (看0920降是率降还是结构变)
q("""
select app_date,
  case when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) <= 5 then '1-5'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 6 and 8 then '6-8'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) >= 9 then '9+'
       else 'null' end g5,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1,2 order by 1,2
""", "Q2 V5_3评级段×按日 1t0本金%(放款口径)")

# Q3: V6_1评级按日×评级段 1t0本金% (看0922拒尾后各档变化)
q("""
select app_date,
  case when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) <= 5 then '1-5'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) between 6 and 8 then '6-8'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) >= 9 then '9+'
       else 'null' end g6,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1,2 order by 1,2
""", "Q3 V6_1评级段×按日 1t0本金%(放款口径)")

# Q4: 产品×按日 1t0本金% + 占比 (看产品结构变化)
q("""
select app_date,
  case when product_name_new like '%_28_%' then '28天'
       when product_name_new like '%_14_%' then '14天'
       when product_name_new like '%_7_%' then '7天'
       else '其他' end prod,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1,2 order by 1,2
""", "Q4 产品×按日 1t0本金% + 放款笔数")

# Q5: 全复贷按日 通过率/进件(放款口径) 件均/授信 找0920前后风控动作
q("""
select app_date,
  count(*) app_cnt,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(count(if(if_issue=1,1,null))*100.0/count(*),2) pass_rate,
  round(avg(if(if_issue=1,real_issue_amount,null)),0) issue_avg,
  round(avg(if(if_issue=1,credit_amount,null)),0) credit_avg
from mx.yj_test_table_250225
where is_reloan='old'
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1 order by 1
""", "Q5 全复贷按日 通过率/件均/授信(9/14-9/28)")

# Q6: 0920周日异常确认: 按日 周几 + 放款量
q("""
select app_date, day_of_week(app_date) dow,
  count(if(if_issue=1,1,null)) issue_cnt,
  count(distinct product_name_new) prod_n
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1,2 order by 1
""", "Q6 按日 周几+放款量+产品数(确认0920周日效应)")

# Q7: 两段聚合 shift-share 基础表: V5_3主评级单级
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  cast(android_oldcust_maincreditlevel_charge_v5_3 as int) g5,
  count(if(if_issue=1,1,null)) issue_cnt,
  sum(if(if_issue=1,t0_overdue_amount_1,null)) od,
  sum(if(if_issue=1,t0_should_amt_1,null)) sh
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q7 V5_3单级两段聚合(9/14-19 vs 9/21-25)")

# Q8: 两段聚合 shift-share 基础表: V6_1主评级单级
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  cast(android_oldCust_mainCreditLevel_charge_V6_1 as int) g6,
  count(if(if_issue=1,1,null)) issue_cnt,
  sum(if(if_issue=1,t0_overdue_amount_1,null)) od,
  sum(if(if_issue=1,t0_should_amt_1,null)) sh
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q8 V6_1单级两段聚合(9/14-19 vs 9/21-25)")

# Q9: 历史逾期痕迹/临额标签 两段聚合 1t0 (揪隐藏驱动维度)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when max_overdue_day_30d_all <= 0 then '0无逾期'
       when max_overdue_day_30d_all >= 7 then '7+逾期'
       else cast(cast(max_overdue_day_30d_all as int) as varchar) end ovd,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q9 历史逾期痕迹两段聚合 1t0")

# Q10: 发临额tag 两段聚合 1t0 (0921前后发临额策略是否变化)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  cast(temp_credit_amount_issue_tag as varchar) tag,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q10 发临额tag两段聚合 1t0")

# Q11: 期限(loan_cycle)×两段 1t0 + 占比 (产品期限结构变化)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  cast(loan_cycle as int) cycle,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q11 期限×两段 1t0 + 笔数")

# Q12: 灰度hash组×两段 1t0 (看V5_2/V5_3切换是否相关)
HASH = """case when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'A_V5_2'
     when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'C_V5_3'
     else 'B_切换' end"""
q(f"""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  {HASH} hgrp,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q12 灰度hash组×两段 1t0")

# Q13: 结清次数×两段 1t0 (老客质量/复借次数结构变化)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when repayment_clearing_count_tenant <= 1 then '1次'
       when repayment_clearing_count_tenant <= 3 then '2-3次'
       when repayment_clearing_count_tenant <= 6 then '4-6次'
       else '7+次' end clear,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q13 结清次数×两段 1t0")

# Q14: V5_3 9+高评级段内 0921前后 件均/授信/发临额/产品/评分 (0921高评级率骤降下钻)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(avg(if(if_issue=1,real_issue_amount,null)),0) issue_avg,
  round(avg(if(if_issue=1,credit_amount,null)),0) credit_avg,
  round(avg(if(if_issue=1,temp_grant_amount,null)),0) temp_avg,
  round(avg(if(if_issue=1,fd_use_creditamount_score_v1,null)),2) score_avg,
  round(avg(if(if_issue=1,repayment_clearing_count_tenant,null)),1) clear_avg,
  round(count(if(if_issue=1 and loan_cycle<=14,1,null))*100.0/count(if(if_issue=1,1,null)),1) short_pct
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and cast(android_oldcust_maincreditlevel_charge_v5_3 as double) >= 9
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1 order by 1
""", "Q14 V5_3 9+段 0921前后 件均/授信/评分/期限结构")

# Q15: V5_3 9+段 按日 件均/授信/短期占比 (看0921是否件均/期限突变)
q("""
select app_date,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(avg(if(if_issue=1,real_issue_amount,null)),0) issue_avg,
  round(avg(if(if_issue=1,credit_amount,null)),0) credit_avg,
  round(count(if(if_issue=1 and loan_cycle<=14,1,null))*100.0/count(if(if_issue=1,1,null)),1) short_pct
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and cast(android_oldcust_maincreditlevel_charge_v5_3 as double) >= 9
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1 order by 1
""", "Q15 V5_3 9+段 按日 件均/授信/短期占比(9/14-9/28)")

# Q16: V5_3 9+段 内部子评级(11,12,13) 0921前后 坏账 (看9+降是子结构变还是率降)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  cast(android_oldcust_maincreditlevel_charge_v5_3 as int) g5,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and cast(android_oldcust_maincreditlevel_charge_v5_3 as double) >= 9
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q16 V5_3 9+段 子评级 0921前后 坏账+笔数")

# Q17: 渠道source×两段 1t0 + 笔数 (0921渠道结构变化)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  coalesce(cast(source as varchar),'null') src,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q17 渠道source×两段 1t0 + 笔数")

# Q18: 首借距今时长×两段 (是否召回老客/新老客结构)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when first_issue_date is null then 'null'
       when date_diff('day', first_issue_date, app_date) <= 30 then '30天内首借'
       when date_diff('day', first_issue_date, app_date) <= 90 then '31-90天'
       when date_diff('day', first_issue_date, app_date) <= 180 then '91-180天'
       else '180天+' end fage,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q18 首借距今时长×两段 1t0")

# Q18b: 探测首借相关字段
q("""
select column_name, data_type from information_schema.columns
where table_schema='mx' and table_name='yj_test_table_250225'
  and (column_name like '%first%issue%' or column_name like '%first%loan%'
       or column_name like '%first_issue%' or column_name like '%issue_date%'
       or column_name like '%apply_date%' or column_name like '%reg%date%'
       or column_name like '%first%time%')
order by 1
""", "Q18b 首借相关字段探测")

# Q20: 通过率按V5_3评级段×两段 (哪个评级段的通过率在0921后被收紧)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) <= 5 then '1-5'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 6 and 8 then '6-8'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) >= 9 then '9+'
       else 'null' end g5,
  count(*) app_cnt,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(count(if(if_issue=1,1,null))*100.0/count(*),2) pass_rate
from mx.yj_test_table_250225
where is_reloan='old'
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q20 通过率×V5_3评级段×两段")

# Q21: 全体进件(含拒绝) V5_3评级分布×两段 (看进件结构是否被拒尾改变)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) <= 5 then '1-5'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 6 and 8 then '6-8'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) >= 9 then '9+'
       else 'null' end g5,
  count(*) app_cnt
from mx.yj_test_table_250225
where is_reloan='old'
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q21 全体进件V5_3评级分布×两段")

# Q22: loan_cycle按日趋势 (期限结构偏移确认)
q("""
select app_date,
  cast(loan_cycle as int) cycle,
  count(if(if_issue=1,1,null)) issue_cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1,2 order by 1,2
""", "Q22 loan_cycle按日放款笔数")

# Q23: V6_1 10/11档(拒尾目标) 精确到0921/0922 放款笔数+率 (量化拒尾贡献)
q("""
select app_date,
  cast(android_oldCust_mainCreditLevel_charge_V6_1 as int) g6,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) >= 10
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-25'
group by 1,2 order by 2,1
""", "Q23 V6_1 10/11档按日 放款笔数+率")

# Q24: loan_cycle×两段 金额口径 shift-share 精确分解 (结构效应 vs 率效应)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  cast(loan_cycle as int) cycle,
  count(if(if_issue=1,1,null)) issue_cnt,
  sum(if(if_issue=1,t0_should_amt_1,null)) should_amt,
  sum(if(if_issue=1,t0_overdue_amount_1,null)) od_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q24 loan_cycle×两段 金额份额+率(shift-share)")

# Q25: 按日 loan_cycle 应还金额占比 (确认期限迁移时点: 0921 or 0922)
q("""
select app_date,
  cast(loan_cycle as int) cycle,
  sum(if(if_issue=1,t0_should_amt_1,null)) should_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1,2 order by 1,2
""", "Q25 按日 loan_cycle 应还金额(看迁移时点)")

# Q26: V6_1评级段 两段 放款笔数占比 + 率 (拒尾对V6_1结构的影响)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) <= 5 then '1-5'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) between 6 and 8 then '6-8'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) >= 9 then '9+'
       else 'null' end g6,
  count(if(if_issue=1,1,null)) issue_cnt,
  sum(if(if_issue=1,t0_should_amt_1,null)) should_amt,
  sum(if(if_issue=1,t0_overdue_amount_1,null)) od_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q26 V6_1评级段×两段 金额份额+率")

# Q27: 21天产品(主力) × 历史逾期痕迹 × 两段 (21天率降是客群质量还是内部结构)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when max_overdue_day_30d_all <= 0 then '0无逾期'
       when max_overdue_day_30d_all >= 7 then '7+逾期'
       else cast(cast(max_overdue_day_30d_all as int) as varchar) end ovd,
  count(if(if_issue=1,1,null)) issue_cnt,
  sum(if(if_issue=1,t0_should_amt_1,null)) should_amt,
  sum(if(if_issue=1,t0_overdue_amount_1,null)) od_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1 and cast(loan_cycle as int)=21
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q27 21天×历史逾期×两段")

# Q28: 21天产品 × V5_3评级段 × 两段 (21天率降是否评级上移)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) <= 5 then '1-5'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) between 6 and 8 then '6-8'
       when cast(android_oldcust_maincreditlevel_charge_v5_3 as double) >= 9 then '9+'
       else 'null' end g5,
  count(if(if_issue=1,1,null)) issue_cnt,
  sum(if(if_issue=1,t0_should_amt_1,null)) should_amt,
  sum(if(if_issue=1,t0_overdue_amount_1,null)) od_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1 and cast(loan_cycle as int)=21
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q28 21天×V5_3评级段×两段")

# Q29: 前砍费比例按日 (haircut/contract 是否0921前后调整)
q("""
select app_date,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,haircut_amount,null))/nullif(sum(if(if_issue=1,contract_amount,null)),0)*100,2) haircut_pct
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1 order by 1
""", "Q29 前砍费比例按日(9/14-9/28)")

# Q30: product_name_new 真实产品分布×两段 (前20产品 放款笔数+率)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  product_name_new,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))
       /nullif(sum(if(if_issue=1,t0_should_amt_1,null)),0)*100,2) t0_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2
""", "Q30 产品名×两段 放款笔数+率")

# Q31: 产品首字母(A/B/C/E) × 两段 金额shift-share (揪根因: 产品结构 vs 产品率)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  substr(product_name_new,1,1) pclass,
  count(if(if_issue=1,1,null)) issue_cnt,
  sum(if(if_issue=1,t0_should_amt_1,null)) should_amt,
  sum(if(if_issue=1,t0_overdue_amount_1,null)) od_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q31 产品首字母×两段 金额份额+率(最终根因)")

# Q32: 产品首字母 × 按日 放款笔数+应还金额 (看A类压缩的精确时点)
q("""
select app_date,
  substr(product_name_new,1,1) pclass,
  count(if(if_issue=1,1,null)) issue_cnt,
  sum(if(if_issue=1,t0_should_amt_1,null)) should_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1,2 order by 1,2
""", "Q32 产品首字母×按日 放款笔数+应还金额(看压缩时点)")

# Q33: A类产品(A_07_01_50_00) × V6_1评级 × 两段 (A类压缩与V6_1拒尾的关系)
q("""
select
  case when app_date between date'2026-09-14' and date'2026-09-19' then 'before'
       else 'after' end seg,
  case when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) <= 5 then '1-5'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) between 6 and 8 then '6-8'
       when cast(android_oldCust_mainCreditLevel_charge_V6_1 as double) >= 9 then '9+'
       else 'null' end g6,
  count(if(if_issue=1,1,null)) issue_cnt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and product_name_new like 'A_%'
  and (app_date between date'2026-09-14' and date'2026-09-19'
    or app_date between date'2026-09-21' and date'2026-09-25')
group by 1,2 order by 2,1
""", "Q33 A类产品×V6_1评级×两段 放款笔数")

# Q19: 首期逾期定义验证: 按日 逾期笔数口径 vs 金额口径 (看0921是否分母跳变)
q("""
select app_date,
  count(if(if_issue=1,1,null)) issue_cnt,
  round(sum(if(if_issue=1,t0_should_amt_1,null))/count(if(if_issue=1,1,null)),0) should_avg,
  round(sum(if(if_issue=1,t0_overdue_amount_1,null))/count(if(if_issue=1,1,null)),0) od_avg,
  round(count(if(if_issue=1 and is_t0_overdue_1=1,1,null))*100.0/count(if(if_issue=1,1,null)),2) od_cnt_rate
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-09-14' and app_date <= date'2026-09-28'
group by 1 order by 1
""", "Q19 按日 首期应还件均/逾期件均/逾期笔率(看分母跳变)")
