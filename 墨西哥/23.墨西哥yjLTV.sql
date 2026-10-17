
--:{author=wangyuhan, department=墨西哥风险策略, dagName=yj_ltv_reloan_remain_create, taskName=yj_ltv_reloan_remain}
drop table if EXISTS mx.yj_LTV
;
--:{author=wangyuhan, department=墨西哥风险策略, dagName=yj_ltv_reloan_remain_create, taskName=yj_ltv_reloan_remain}
CREATE table mx.yj_LTV as
select sd_issue_week
,sd_issue_date
,app_group
,product_level
,new_media_source
,is_low_amount_flag-- 小金额标签
,max(substr(cast(current_timestamp as varchar), 1, 24)) as update_time
,sum(contract_amount_new) as contract_amount_new
,sum(sd_user_num) as sd_user_num
,sum(sd_T3_overdue_amt) as sd_T3_overdue_amt
,sum(sd_T3_should_amt) as sd_T3_should_amt
,sum(term_1_amt) as term_1_amt
,sum(term_2_amt) as term_2_amt
,sum(term_3_amt) as term_3_amt
,sum(term_4_amt) as term_4_amt
,sum(term_5_amt) as term_5_amt
,sum(term_6_amt) as term_6_amt
,sum(term_7_amt) as term_7_amt
,sum(term_8_amt) as term_8_amt
,sum(term_9_amt) as term_9_amt
,sum(term_10_amt) as term_10_amt
,sum(term_11_amt) as term_11_amt
,sum(term_12_amt) as term_12_amt
,sum(term_13_amt) as term_13_amt
-- 添加第14周到第26周放款金额
,sum(term_14_amt) as term_14_amt
,sum(term_15_amt) as term_15_amt
,sum(term_16_amt) as term_16_amt
,sum(term_17_amt) as term_17_amt
,sum(term_18_amt) as term_18_amt
,sum(term_19_amt) as term_19_amt
,sum(term_20_amt) as term_20_amt
,sum(term_21_amt) as term_21_amt
,sum(term_22_amt) as term_22_amt
,sum(term_23_amt) as term_23_amt
,sum(term_24_amt) as term_24_amt
,sum(term_25_amt) as term_25_amt
,sum(term_26_amt) as term_26_amt
-- 累加笔数
,sum(term_1_num_old) as term_1_num_old
,sum(term_2_num_old) as term_2_num_old
,sum(term_3_num_old) as term_3_num_old
,sum(term_4_num_old) as term_4_num_old
,sum(term_5_num_old) as term_5_num_old
,sum(term_6_num_old) as term_6_num_old
,sum(term_7_num_old) as term_7_num_old
,sum(term_8_num_old) as term_8_num_old
,sum(term_9_num_old) as term_9_num_old
,sum(term_10_num_old) as term_10_num_old
,sum(term_11_num_old) as term_11_num_old
,sum(term_12_num_old) as term_12_num_old
,sum(term_13_num_old) as term_13_num_old
-- 添加第14周到第26周累加笔数
,sum(term_14_num_old) as term_14_num_old
,sum(term_15_num_old) as term_15_num_old
,sum(term_16_num_old) as term_16_num_old
,sum(term_17_num_old) as term_17_num_old
,sum(term_18_num_old) as term_18_num_old
,sum(term_19_num_old) as term_19_num_old
,sum(term_20_num_old) as term_20_num_old
,sum(term_21_num_old) as term_21_num_old
,sum(term_22_num_old) as term_22_num_old
,sum(term_23_num_old) as term_23_num_old
,sum(term_24_num_old) as term_24_num_old
,sum(term_25_num_old) as term_25_num_old
,sum(term_26_num_old) as term_26_num_old
-- 增量人数
,sum(term_1_user_num_old_add) as term_1_user_num_old_add
,sum(term_2_user_num_old_add) as term_2_user_num_old_add
,sum(term_3_user_num_old_add) as term_3_user_num_old_add
,sum(term_4_user_num_old_add) as term_4_user_num_old_add
,sum(term_5_user_num_old_add) as term_5_user_num_old_add
,sum(term_6_user_num_old_add) as term_6_user_num_old_add
,sum(term_7_user_num_old_add) as term_7_user_num_old_add
,sum(term_8_user_num_old_add) as term_8_user_num_old_add
,sum(term_9_user_num_old_add) as term_9_user_num_old_add
,sum(term_10_user_num_old_add) as term_10_user_num_old_add
,sum(term_11_user_num_old_add) as term_11_user_num_old_add
,sum(term_12_user_num_old_add) as term_12_user_num_old_add
,sum(term_13_user_num_old_add) as term_13_user_num_old_add
-- 添加第14周到第26周增量人数
,sum(term_14_user_num_old_add) as term_14_user_num_old_add
,sum(term_15_user_num_old_add) as term_15_user_num_old_add
,sum(term_16_user_num_old_add) as term_16_user_num_old_add
,sum(term_17_user_num_old_add) as term_17_user_num_old_add
,sum(term_18_user_num_old_add) as term_18_user_num_old_add
,sum(term_19_user_num_old_add) as term_19_user_num_old_add
,sum(term_20_user_num_old_add) as term_20_user_num_old_add
,sum(term_21_user_num_old_add) as term_21_user_num_old_add
,sum(term_22_user_num_old_add) as term_22_user_num_old_add
,sum(term_23_user_num_old_add) as term_23_user_num_old_add
,sum(term_24_user_num_old_add) as term_24_user_num_old_add
,sum(term_25_user_num_old_add) as term_25_user_num_old_add
,sum(term_26_user_num_old_add) as term_26_user_num_old_add
--累加逾期金额
,sum(term_1_T3_overdue_amt) as term_1_T3_overdue_amt
,sum(term_2_T3_overdue_amt) as term_2_T3_overdue_amt
,sum(term_3_T3_overdue_amt) as term_3_T3_overdue_amt
,sum(term_4_T3_overdue_amt) as term_4_T3_overdue_amt
,sum(term_5_T3_overdue_amt) as term_5_T3_overdue_amt
,sum(term_6_T3_overdue_amt) as term_6_T3_overdue_amt
,sum(term_7_T3_overdue_amt) as term_7_T3_overdue_amt
,sum(term_8_T3_overdue_amt) as term_8_T3_overdue_amt
,sum(term_9_T3_overdue_amt) as term_9_T3_overdue_amt
,sum(term_10_T3_overdue_amt) as term_10_T3_overdue_amt
,sum(term_11_T3_overdue_amt) as term_11_T3_overdue_amt
,sum(term_12_T3_overdue_amt) as term_12_T3_overdue_amt
,sum(term_13_T3_overdue_amt) as term_13_T3_overdue_amt
-- 添加第14周到第26周累加逾期金额
,sum(term_14_T3_overdue_amt) as term_14_T3_overdue_amt
,sum(term_15_T3_overdue_amt) as term_15_T3_overdue_amt
,sum(term_16_T3_overdue_amt) as term_16_T3_overdue_amt
,sum(term_17_T3_overdue_amt) as term_17_T3_overdue_amt
,sum(term_18_T3_overdue_amt) as term_18_T3_overdue_amt
,sum(term_19_T3_overdue_amt) as term_19_T3_overdue_amt
,sum(term_20_T3_overdue_amt) as term_20_T3_overdue_amt
,sum(term_21_T3_overdue_amt) as term_21_T3_overdue_amt
,sum(term_22_T3_overdue_amt) as term_22_T3_overdue_amt
,sum(term_23_T3_overdue_amt) as term_23_T3_overdue_amt
,sum(term_24_T3_overdue_amt) as term_24_T3_overdue_amt
,sum(term_25_T3_overdue_amt) as term_25_T3_overdue_amt
,sum(term_26_T3_overdue_amt) as term_26_T3_overdue_amt
--老客应还金额
,sum(term_1_T3_should_amt) as term_1_T3_should_amt
,sum(term_2_T3_should_amt) as term_2_T3_should_amt
,sum(term_3_T3_should_amt) as term_3_T3_should_amt
,sum(term_4_T3_should_amt) as term_4_T3_should_amt
,sum(term_5_T3_should_amt) as term_5_T3_should_amt
,sum(term_6_T3_should_amt) as term_6_T3_should_amt
,sum(term_7_T3_should_amt) as term_7_T3_should_amt
,sum(term_8_T3_should_amt) as term_8_T3_should_amt
,sum(term_9_T3_should_amt) as term_9_T3_should_amt
,sum(term_10_T3_should_amt) as term_10_T3_should_amt
,sum(term_11_T3_should_amt) as term_11_T3_should_amt
,sum(term_12_T3_should_amt) as term_12_T3_should_amt
,sum(term_13_T3_should_amt) as term_13_T3_should_amt
-- 添加第14周到第26周老客应还金额
,sum(term_14_T3_should_amt) as term_14_T3_should_amt
,sum(term_15_T3_should_amt) as term_15_T3_should_amt
,sum(term_16_T3_should_amt) as term_16_T3_should_amt
,sum(term_17_T3_should_amt) as term_17_T3_should_amt
,sum(term_18_T3_should_amt) as term_18_T3_should_amt
,sum(term_19_T3_should_amt) as term_19_T3_should_amt
,sum(term_20_T3_should_amt) as term_20_T3_should_amt
,sum(term_21_T3_should_amt) as term_21_T3_should_amt
,sum(term_22_T3_should_amt) as term_22_T3_should_amt
,sum(term_23_T3_should_amt) as term_23_T3_should_amt
,sum(term_24_T3_should_amt) as term_24_T3_should_amt
,sum(term_25_T3_should_amt) as term_25_T3_should_amt
,sum(term_26_T3_should_amt) as term_26_T3_should_amt
from
(select t1.biz_id,t1.sd_issue_week,sd_issue_date,t1.app_group,t1.product_level,t1.new_media_source
,t1.is_low_amount_flag-- 新客小金额标签
,max(t1.contract_amount_new) as contract_amount_new
,count(distinct t1.credit_no) as sd_user_num
--新客t3金额逾期
,max(case when t1.is_t3_window_1=1 then t1.t3_overdue_amount_1 end) as sd_T3_overdue_amt
,max(case when t1.is_t3_window_1=1 then t1.t3_should_amt_1 end) as sd_T3_should_amt
-- 老客放款金额
,sum(case when term_id=1 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_1_amt
,sum(case when term_id=2 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_2_amt
,sum(case when term_id=3 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_3_amt
,sum(case when term_id=4 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_4_amt
,sum(case when term_id=5 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_5_amt
,sum(case when term_id=6 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_6_amt
,sum(case when term_id=7 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_7_amt
,sum(case when term_id=8 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_8_amt
,sum(case when term_id=9 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_9_amt
,sum(case when term_id=10 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_10_amt
,sum(case when term_id=11 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_11_amt
,sum(case when term_id=12 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_12_amt
,sum(case when term_id=13 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_13_amt
-- 添加第14周到第26周老客放款金额
,sum(case when term_id=14 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_14_amt
,sum(case when term_id=15 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_15_amt
,sum(case when term_id=16 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_16_amt
,sum(case when term_id=17 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_17_amt
,sum(case when term_id=18 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_18_amt
,sum(case when term_id=19 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_19_amt
,sum(case when term_id=20 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_20_amt
,sum(case when term_id=21 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_21_amt
,sum(case when term_id=22 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_22_amt
,sum(case when term_id=23 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_23_amt
,sum(case when term_id=24 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_24_amt
,sum(case when term_id=25 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_25_amt
,sum(case when term_id=26 and cast(obs_time as timestamp) <=now() then t2.contract_amount end) as term_26_amt
-- 老客累加放款笔数
,count(distinct case when term_id=1 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_1_num_old
,count(distinct case when term_id=2 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_2_num_old
,count(distinct case when term_id=3 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_3_num_old
,count(distinct case when term_id=4 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_4_num_old
,count(distinct case when term_id=5 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_5_num_old
,count(distinct case when term_id=6 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_6_num_old
,count(distinct case when term_id=7 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_7_num_old
,count(distinct case when term_id=8 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_8_num_old
,count(distinct case when term_id=9 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_9_num_old
,count(distinct case when term_id=10 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_10_num_old
,count(distinct case when term_id=11 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_11_num_old
,count(distinct case when term_id=12 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_12_num_old
,count(distinct case when term_id=13 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_13_num_old
-- 添加第14周到第26周老客累加放款笔数
,count(distinct case when term_id=14 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_14_num_old
,count(distinct case when term_id=15 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_15_num_old
,count(distinct case when term_id=16 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_16_num_old
,count(distinct case when term_id=17 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_17_num_old
,count(distinct case when term_id=18 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_18_num_old
,count(distinct case when term_id=19 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_19_num_old
,count(distinct case when term_id=20 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_20_num_old
,count(distinct case when term_id=21 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_21_num_old
,count(distinct case when term_id=22 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_22_num_old
,count(distinct case when term_id=23 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_23_num_old
,count(distinct case when term_id=24 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_24_num_old
,count(distinct case when term_id=25 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_25_num_old
,count(distinct case when term_id=26 and cast(obs_time as timestamp) <=now() then t2.biz_id end) as term_26_num_old
--老客增量放款人数
,count(distinct case when term_id=1 and cast(obs_time as timestamp) <=now()  then  t2.credit_no end) as term_1_user_num_old_add
,count(distinct case when term_id=2 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_2_user_num_old_add
,count(distinct case when term_id=3 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_3_user_num_old_add
,count(distinct case when term_id=4 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_4_user_num_old_add
,count(distinct case when term_id=5 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_5_user_num_old_add
,count(distinct case when term_id=6 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_6_user_num_old_add
,count(distinct case when term_id=7 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_7_user_num_old_add
,count(distinct case when term_id=8 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_8_user_num_old_add
,count(distinct case when term_id=9 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_9_user_num_old_add
,count(distinct case when term_id=10 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_10_user_num_old_add
,count(distinct case when term_id=11 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_11_user_num_old_add
,count(distinct case when term_id=12 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_12_user_num_old_add
,count(distinct case when term_id=13 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_13_user_num_old_add
-- 添加第14周到第26周老客增量放款人数
,count(distinct case when term_id=14 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_14_user_num_old_add
,count(distinct case when term_id=15 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_15_user_num_old_add
,count(distinct case when term_id=16 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_16_user_num_old_add
,count(distinct case when term_id=17 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_17_user_num_old_add
,count(distinct case when term_id=18 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_18_user_num_old_add
,count(distinct case when term_id=19 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_19_user_num_old_add
,count(distinct case when term_id=20 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_20_user_num_old_add
,count(distinct case when term_id=21 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_21_user_num_old_add
,count(distinct case when term_id=22 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_22_user_num_old_add
,count(distinct case when term_id=23 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_23_user_num_old_add
,count(distinct case when term_id=24 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_24_user_num_old_add
,count(distinct case when term_id=25 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_25_user_num_old_add
,count(distinct case when term_id=26 and cast(obs_time as timestamp) <=now() and t2.issue_date>date_add('day',-7,date(cast(obs_time as timestamp))) then  t2.credit_no end) as term_26_user_num_old_add
--老客累加逾期金额
,sum(case when term_id=1 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_1_T3_overdue_amt
,sum(case when term_id=2 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_2_T3_overdue_amt
,sum(case when term_id=3 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_3_T3_overdue_amt
,sum(case when term_id=4 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_4_T3_overdue_amt
,sum(case when term_id=5 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_5_T3_overdue_amt
,sum(case when term_id=6 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_6_T3_overdue_amt
,sum(case when term_id=7 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_7_T3_overdue_amt
,sum(case when term_id=8 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_8_T3_overdue_amt
,sum(case when term_id=9 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_9_T3_overdue_amt
,sum(case when term_id=10 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_10_T3_overdue_amt
,sum(case when term_id=11 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_11_T3_overdue_amt
,sum(case when term_id=12 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_12_T3_overdue_amt
,sum(case when term_id=13 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_13_T3_overdue_amt
-- 添加第14周到第26周老客累加逾期金额
,sum(case when term_id=14 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_14_T3_overdue_amt
,sum(case when term_id=15 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_15_T3_overdue_amt
,sum(case when term_id=16 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_16_T3_overdue_amt
,sum(case when term_id=17 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_17_T3_overdue_amt
,sum(case when term_id=18 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_18_T3_overdue_amt
,sum(case when term_id=19 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_19_T3_overdue_amt
,sum(case when term_id=20 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_20_T3_overdue_amt
,sum(case when term_id=21 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_21_T3_overdue_amt
,sum(case when term_id=22 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_22_T3_overdue_amt
,sum(case when term_id=23 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_23_T3_overdue_amt
,sum(case when term_id=24 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_24_T3_overdue_amt
,sum(case when term_id=25 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_25_T3_overdue_amt
,sum(case when term_id=26 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_overdue_amount_1 end) as term_26_T3_overdue_amt
--老客应还金额
,sum(case when term_id=1 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_1_T3_should_amt
,sum(case when term_id=2 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_2_T3_should_amt
,sum(case when term_id=3 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_3_T3_should_amt
,sum(case when term_id=4 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_4_T3_should_amt
,sum(case when term_id=5 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_5_T3_should_amt
,sum(case when term_id=6 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_6_T3_should_amt
,sum(case when term_id=7 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_7_T3_should_amt
,sum(case when term_id=8 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_8_T3_should_amt
,sum(case when term_id=9 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_9_T3_should_amt
,sum(case when term_id=10 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_10_T3_should_amt
,sum(case when term_id=11 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_11_T3_should_amt
,sum(case when term_id=12 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_12_T3_should_amt
,sum(case when term_id=13 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_13_T3_should_amt
-- 添加第14周到第26周老客应还金额
,sum(case when term_id=14 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_14_T3_should_amt
,sum(case when term_id=15 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_15_T3_should_amt
,sum(case when term_id=16 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_16_T3_should_amt
,sum(case when term_id=17 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_17_T3_should_amt
,sum(case when term_id=18 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_18_T3_should_amt
,sum(case when term_id=19 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_19_T3_should_amt
,sum(case when term_id=20 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_20_T3_should_amt
,sum(case when term_id=21 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_21_T3_should_amt
,sum(case when term_id=22 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_22_T3_should_amt
,sum(case when term_id=23 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_23_T3_should_amt
,sum(case when term_id=24 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_24_T3_should_amt
,sum(case when term_id=25 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_25_T3_should_amt
,sum(case when term_id=26 and cast(obs_time as timestamp) <=now() and t2.is_t3_window_1=1 then t2.t3_should_amt_1 end) as term_26_T3_should_amt
from --新客信息
(SELECT biz_id
,date_trunc('week',date(issue_date)) as sd_issue_week
,credit_no,app_group,product_level,new_media_source,issue_date as sd_issue_date
,is_t3_window_1
,t3_overdue_amount_1
,t3_should_amt_1
,cast(contract_amount as double) as contract_amount_new
, CASE WHEN cast(contract_amount as double) <= 500 THEN '小金额(<=500)' ELSE '非小金额(>500)'
  END AS is_low_amount_flag
,u.item AS obs_time
,row_number() over(partition by biz_id order by u.item asc) as term_id
FROM 
(select a.* ,
new_media_source
from mx.wxs_application_funnel a
left join --提取获客渠道
(SELECT
mid
,new_media_source
from mx.gm_attribution_detail
) b
on a.mid=b.mid 
where is_reloan='new' and if_issue=1 and app_time>=cast('2024-08-01 00:00:00.000' as timestamp)
) t
CROSS JOIN UNNEST(
  split(
   concat(
    cast(date_add('day', 7, date(issue_date)) as varchar), ',',
    cast(date_add('day', 14, date(issue_date)) as varchar), ',',
    cast(date_add('day', 21, date(issue_date)) as varchar), ',',
    cast(date_add('day', 28, date(issue_date)) as varchar), ',',
    cast(date_add('day', 35, date(issue_date)) as varchar), ',',
    cast(date_add('day', 42, date(issue_date)) as varchar), ',',
    cast(date_add('day', 49, date(issue_date)) as varchar), ',',
    cast(date_add('day', 56, date(issue_date)) as varchar), ',',
    cast(date_add('day', 63, date(issue_date)) as varchar), ',',
    cast(date_add('day', 70, date(issue_date)) as varchar), ',',
    cast(date_add('day', 77, date(issue_date)) as varchar), ',',
    cast(date_add('day', 84, date(issue_date)) as varchar), ',',
    cast(date_add('day', 91, date(issue_date)) as varchar), ',',
    -- 添加第14周到第26周的日期
    cast(date_add('day', 98, date(issue_date)) as varchar), ',',
    cast(date_add('day', 105, date(issue_date)) as varchar), ',',
    cast(date_add('day', 112, date(issue_date)) as varchar), ',',
    cast(date_add('day', 119, date(issue_date)) as varchar), ',',
    cast(date_add('day', 126, date(issue_date)) as varchar), ',',
    cast(date_add('day', 133, date(issue_date)) as varchar), ',',
    cast(date_add('day', 140, date(issue_date)) as varchar), ',',
    cast(date_add('day', 147, date(issue_date)) as varchar), ',',
    cast(date_add('day', 154, date(issue_date)) as varchar), ',',
    cast(date_add('day', 161, date(issue_date)) as varchar), ',',
    cast(date_add('day', 168, date(issue_date)) as varchar), ',',
    cast(date_add('day', 175, date(issue_date)) as varchar), ',',
    cast(date_add('day', 182, date(issue_date)) as varchar)
   ), ',') 
) AS u(item)
) t1
left join --老客信息
(
select * 
from mx.wxs_application_funnel 
where is_reloan='old' and if_issue=1) t2 
on t1.credit_no=t2.credit_no and t1.app_group=t2.app_group and cast(obs_time as timestamp)>=t2.issue_date
group by 1,2,3,4,5,6,7) m
group by 1,2,3,4,5,6
;