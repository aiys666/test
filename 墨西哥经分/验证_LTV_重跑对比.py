# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功")

def exe(sql, desc):
    print("\n" + "="*70)
    print(desc)
    print("="*70)
    ok, msg = pq.execute(sql)
    print(("OK: " if ok else "FAIL: ") + str(msg))
    return ok

def run(sql, desc):
    print("\n" + "-"*70)
    print(desc)
    print("-"*70)
    r = pq.query(sql)
    if isinstance(r, pd.DataFrame):
        print(r.to_string())
    else:
        print(r)
    return r

# ============ 重跑 复贷第1段：明细(加 reloan_app_channel) ============
exe("""
drop table if exists mx.ys_dl_ltv_double_loan_0511;
create table mx.ys_dl_ltv_double_loan_0511 as
select 
    d.ltv_month,
    d.ltv_week,
    date_diff('week', d.ltv_week, date_trunc('week', date(r.release_time))) as wob, 
    d.loan_cycle, 

    d.app_channel,
    d.app_channel_name,
    r.app_channel as reloan_app_channel,
    r.app_group as reloan_app_channel_name,
    d.new_grade_level,
    d.is_low_amount_flag,
    r.camera_id as biz_id,
    cast(r.cust_id as bigint) as mid,
    
    r.contract_amount,
    r.contract_amount/f.exchange_rate_to_dollar as contract_amount_usd,
    r.haircut_amount,
    r.should_interest,
    r.should_interest + r.should_capital as should_amt,
    r.t0_should_capit_4 as contract_t0,
    r.t0_should_amt_1 as should_amt_1t0,
    r.t3_should_amt_1 as should_amt_1t3,
    r.t0_should_capit_1 as contract_1t0,
    r.t3_should_capit_1 as contract_1t3,
    r.t0_should_capit_1-r.t0_overdue_capit_1 as fact_capital_1t0,
    r.t3_should_capit_1-r.t3_overdue_capit_1 as fact_capital_1t3,
    r.t0_should_amt_1-r.t0_overdue_amount_1 as fact_1t0,
    r.t3_should_amt_1-r.t3_overdue_amount_1 as fact_1t3,
    r.t7_should_amt_4 as should_amt_t7,
    r.t30_should_amt_4 as should_amt_t30,
    r.t7_should_capit_4 as contract_t7,
    r.t30_should_capit_4 as contract_t30,
    case when r.t7_should_amt_4>0 then 1 else 0 end as should_cnt_t7, 
    r.t7_should_amt_4-r.t7_overdue_amount_4 as fact_t7,
    r.t7_should_amt_4-r.t7_overdue_amount_4 as fact_t7_coup,
    r.t30_should_amt_4-r.t30_overdue_amount_4 as fact_t30,
    r.t30_should_amt_4-r.t30_overdue_amount_4 as fact_t30_coup,
    case when r.t0_should_amt_4-r.t0_overdue_amount_4>0 then 1 else 0 end as fact_cnt_t0,
    case when r.t7_should_amt_4-r.t7_overdue_amount_4>0 then 1 else 0 end as fact_cnt_t7,
    case when r.t30_should_amt_4-r.t30_overdue_amount_4>0 then 1 else 0 end as fact_cnt_t30, 
    0 fact_cnt_till_now,
    date(t.trade_start_time) as trade_start_date,
    date(t.trade_end_time) as trade_end_date,
    0 as re_zr_cnt_t30
from mx.wxs_application_funnel r
left join mx.ys_dl_ltv_first_loan_0511 d
    on cast(r.cust_id as bigint) = d.mid 
left join ods.s02_loan t
    on r.camera_id = t.camera_id
left join dim.dim_exchange_rate_cost f
    on date(DATE_PARSE(f.month_id, '%Y%m'))=date(date_format(r.release_time,'%Y-%m-01'))  
    and f.account_currency = 'MXN'
where r.is_reloan = 'old'
  and r.if_issue = 1
  and d.mid is not null;
""", "复贷第1段 重跑(加复贷渠道)")

run("""
select count(*) as row_cnt,
       count(distinct biz_id) as double_biz_cnt,
       count(distinct mid) as double_mid_cnt,
       sum(contract_amount) as double_contract_amount,
       count(distinct reloan_app_channel) as reloan_channel_cnt,
       sum(case when reloan_app_channel is null then 1 else 0 end) as null_reloan_channel
from mx.ys_dl_ltv_double_loan_0511
""", "校验1: 复贷明细总量 vs 基线(534645/534640/141930/653038101.91)")

# ============ 重跑 复贷第2段：group(8位, 含复贷渠道) ============
exe("""
drop table if exists mx.ys_dl_ltv_double_loan_group;
create table mx.ys_dl_ltv_double_loan_group as 
select
    ltv_week as ltv_week_d,
    wob as wob_d,
    app_channel_name as app_channel_name_d,
    reloan_app_channel as reloan_app_channel_d,
    reloan_app_channel_name as reloan_app_channel_name_d,
    loan_cycle as loan_period, 
    new_grade_level as new_grade_level_d,
    is_low_amount_flag as is_low_amount_flag_d,
    count(distinct biz_id) as double_cnt,
    count(distinct mid) as double_mid,
    sum(contract_amount) as contract_amount,
    sum(haircut_amount+should_interest) as fee_amount,
    sum(contract_amount) / nullif(count(distinct biz_id), 0) as avg_amount,
    sum(should_amt) as  should_amt_t0,
    sum(should_amt_t7) as should_amt_t7,
    sum(should_amt_t30) as should_amt_t30,
    sum(contract_t0) as contract_t0,
    sum(contract_t7) as contract_t7,
    sum(contract_t30) as contract_t30,
    sum(should_amt_1t0) as should_amt_1t0,
    sum(should_amt_1t3) as should_amt_1t3,
    sum(contract_1t0) as contract_1t0,
    sum(contract_1t3) as contract_1t3,
    sum(fact_capital_1t0) as fact_capital_1t0,
    sum(fact_capital_1t3) as fact_capital_1t3,
    sum(fact_1t0) as fact_1t0,
    sum(fact_1t3) as fact_1t3,
    (sum(contract_1t0) - sum(fact_capital_1t0)) / nullif(sum(contract_1t0), 0) as bad_1t0_capital,
    (sum(contract_1t3) - sum(fact_capital_1t3)) / nullif(sum(contract_1t3), 0) as bad_1t3_capital,
    (sum(should_amt_1t0) - sum(fact_1t0)) / nullif(sum(should_amt_1t0), 0) as bad_1t0_amt,
    (sum(should_amt_1t3) - sum(fact_1t3)) / nullif(sum(should_amt_1t3), 0) as bad_1t3_amt,
    0 as should_cnt_t0, 
    sum(should_cnt_t7) as should_cnt_t7, 
    0 as fact_t0,
    sum(fact_t7) as fact_t7,
    sum(fact_t7_coup) as fact_t7_coup,
    sum(fact_t30) as fact_t30,
    sum(fact_t30_coup) as fact_t30_coup,
    0 as fact_cnt_t0,
    sum(fact_cnt_t7) as fact_cnt_t7,
    sum(fact_cnt_t30) as fact_cnt_t30,
    sum(fact_cnt_till_now) as fact_cnt_till_now,
    0 as contract_amount_7d,
    0 as contract_amount_14d,
    0 as should_amt_7d,
    0 as should_amt_14d,
    0 as fact_t30_7d,
    0 as fact_t30_14d,
    0 as double_cnt_7d,
    0 as double_cnt_14d,
    0 as avg_amount_7d,
    0 as avg_amount_14d,
    0 as zr_mid,
    0 as zr_pass_mid,
    0 as zr_cnt,
    0 as zr_pass_cnt,
    0 as qz_mid,
    0 as qz_pass_mid,
    0 as qz_cnt,
    0 as qz_pass_cnt,
    0 as apply_mid,
    0 as apply_pass_mid,
    0 as apply_cnt,
    0 as apply_pass_cnt,
    0 as fact_cnt_t7_for_rzt30,
    0 as fact_cnt_t7_for_rzt7,
    0 as re_zr_cnt_t30,
    0 as re_zr_cnt_t7,
    sum(contract_amount_usd) as contract_amount_usd
from mx.ys_dl_ltv_double_loan_0511
group by 1, 2, 3, 4, 5, 6, 7, 8 ;
""", "复贷第2段 重跑(8位group by含复贷渠道)")

run("""
select count(*) as group_row_cnt,
       sum(double_cnt) as sum_double_cnt,
       sum(double_mid) as sum_double_mid,
       sum(contract_amount) as sum_contract_amount
from mx.ys_dl_ltv_double_loan_group
""", "校验2: 新group表总量 vs 旧(43940/534643/409948/653038101.91)")
