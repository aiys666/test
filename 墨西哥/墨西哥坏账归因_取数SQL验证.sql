-- =====================================================================
-- 墨西哥 0810 后坏账风险归因 —— 取数 SQL（供验证）
-- 数据源: Presto(盘古)  |  主表: mx.wxs_application_funnel f
-- 评级表: mx.yj_test_table_250225 y  (biz_id 不唯一, 用 rn=1 去重)
--
-- 口径:
--   复贷老客  f.is_reloan = 'old'  AND  f.tenant = 'yawey'
--   起始时间  date(f.create_time) >= date '2026-06-29'
--   进件基准  f.if_app = 1   , 日期取 date(f.app_time)
--   放款基准  f.if_issue = 1 , 日期取 date(f.release_time)
--
-- 重要口径说明:
--   ① 字段映射: Excel 的 "t0_should_amt_1" 实际取的是本金字段
--      t0_should_capit_1 (宽表里 should_amt 与 should_capit 同名同值)
--   ② 指标全部由 SUM 后本地计算(与 Excel 透视表公式完全一致):
--      1t0本金 = t0_overdue_capit_1 / t0_should_capit_1
--      1t3本金 = t3_overdue_capit_1 / t3_should_capit_1
--      1t7本金 = t7_overdue_capit_1 / t7_should_capit_1
--      4t0本金 = t0_overdue_capit_4 / t0_should_capit_4
--      4t3本金 = t3_overdue_capit_4 / t3_should_capit_4
--      4t7本金 = t7_overdue_capit_4 / t7_should_capit_4
--      4t3息费 = t3_overdue_interest_4 / t3_should_capit_4
--      4t7息费 = t7_overdue_interest_4 / t7_should_capit_4
--      前砍%   = haircut_amount / contract_amount
--      后收%   = should_interest / contract_amount
--      4t3TR   = 后收% + 前砍% - 4t3息费 - 4t3本金
--      4T7TR   = 后收% + 前砍% - 4t7息费 - 4t7本金
--      件均    = contract_amount / issue_cnt   (issue_cnt=if_issue)
--      期限    = loan_cycle_amount / contract_amount
--                (loan_cycle_amount = sum(loan_cycle*contract_amount))
--      前置%   = if_in_sx / if_app
--      后置    = if_issue / if_sx_passed
--      风险通过率 = 前置% * 后置
--      24h用信率  = if_sx_passed_24h / if_in_sx_24h
--      120h用信率 = if_sx_passed_120h / if_in_sx_120h
--      出账量: is_t0_window_1 / is_t3_window_1 / is_t7_window_1 /
--              is_t0_window_4 / is_t3_window_4 / is_t7_window_4
--   ③ 评级字段为科学计数法字符串('1.0E0'/'1.0E1'/'1.1E1'=11级…),
--      用 try_cast(xxx as double) 判断区间 / try_cast(xxx as integer) 取整
-- =====================================================================


-- =====================================================================
-- 【通用部分 1】yj 评级表去重子查询(LEFT JOIN, rn=1)
-- =====================================================================
LEFT JOIN (
  SELECT
    biz_id, product_name_new, first_issue_date, real_issue_amount, loan_contract_amount,
    android_oldcust_maincreditlevel_charge_v5_3, android_oldcust_maincreditlevel_charge_v6_1,
    android_oldcust_midcreditlevel_charge_v5_3, android_oldcust_midcreditlevel_charge_v6_1,
    v3_flag, v3_flag_huidu, fd_high_pass_label,
    max_ovd_days_all, max_overdue_day_30d_all,
    other_app_has_overdue_tag, other_app_has_overdue_interval_tag,
    if_reloan_24h, income, baseinfo_userprof_age, baseinfo_userprof_degree,
    baseinfo_marry, baseinfo_employee_type, baseinfo_has_car, baseinfo_has_house,
    v5_3_fraud_score, v5_3_behavior_score, v5_fraud_score, v5_behavior_score,
    last_repay_gap_days_app_group, minstay_repayplan_second_30d_mid, history_loanrec_cnt_lastprepaydays_v2,
    curr_ovd_cnt_all, curr_ovd_cnt_other_app_group, curr_ovd_cnt_this_app_group,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id AND y.rn = 1


-- =====================================================================
-- 【通用部分 2】聚合字段(SUM) —— 全量版
-- =====================================================================
    sum(f.if_app)                as if_app,
    sum(f.if_issue)              as if_issue,
    sum(f.contract_amount)       as contract_amount,
    sum(f.haircut_amount)        as haircut_amount,
    sum(f.should_interest)       as should_interest,
    sum(f.if_in_sx)              as if_in_sx,
    sum(f.if_sx_passed)          as if_sx_passed,
    sum(f.if_in_sx_24h)          as if_in_sx_24h,
    sum(f.if_sx_passed_24h)      as if_sx_passed_24h,
    sum(f.if_in_sx_120h)         as if_in_sx_120h,
    sum(f.if_sx_passed_120h)     as if_sx_passed_120h,
    sum(f.is_t0_window_1)        as is_t0_window_1,
    sum(f.is_t3_window_1)        as is_t3_window_1,
    sum(f.is_t7_window_1)        as is_t7_window_1,
    sum(f.is_t0_window_2)        as is_t0_window_2,
    sum(f.is_t0_window_3)        as is_t0_window_3,
    sum(f.is_t0_window_4)        as is_t0_window_4,
    sum(f.is_t3_window_4)        as is_t3_window_4,
    sum(f.is_t7_window_4)        as is_t7_window_4,
    sum(f.t0_overdue_capit_1)    as t0_overdue_capit_1,
    sum(f.t0_should_capit_1)     as t0_should_capit_1,
    sum(f.t3_overdue_capit_1)    as t3_overdue_capit_1,
    sum(f.t3_should_capit_1)     as t3_should_capit_1,
    sum(f.t7_overdue_capit_1)    as t7_overdue_capit_1,
    sum(f.t7_should_capit_1)     as t7_should_capit_1,
    sum(f.t0_overdue_capit_2)    as t0_overdue_capit_2,
    sum(f.t0_should_capit_2)     as t0_should_capit_2,
    sum(f.t0_overdue_capit_3)    as t0_overdue_capit_3,
    sum(f.t0_should_capit_3)     as t0_should_capit_3,
    sum(f.t0_overdue_capit_4)    as t0_overdue_capit_4,
    sum(f.t0_should_capit_4)     as t0_should_capit_4,
    sum(f.t3_overdue_capit_4)    as t3_overdue_capit_4,
    sum(f.t3_should_capit_4)     as t3_should_capit_4,
    sum(f.t7_overdue_capit_4)    as t7_overdue_capit_4,
    sum(f.t7_should_capit_4)     as t7_should_capit_4,
    sum(f.t3_overdue_interest_4) as t3_overdue_interest_4,
    sum(f.t7_overdue_interest_4) as t7_overdue_interest_4,
    sum(f.is_t0_overdue_1)       as is_t0_overdue_1,
    sum(f.is_t3_overdue_1)       as is_t3_overdue_1,
    sum(f.is_t7_overdue_1)       as is_t7_overdue_1,
    sum(f.is_t0_overdue_4)       as is_t0_overdue_4,
    sum(f.is_t3_overdue_4)       as is_t3_overdue_4,
    sum(f.is_t7_overdue_4)       as is_t7_overdue_4,
    sum(f.loan_cycle*f.contract_amount) as loan_cycle_amount

-- 注: 6-12 专项版聚合字段比全量版少最后 6 个 is_t*_overdue_* 字段,
--     其余完全一致(取数脚本 _download_6_12.py 未统计 is_overdue 标签)。


-- =====================================================================
-- 【模板 A】全量(不限评级) 取数 SQL 模板
--   替换 {day_col} / {dim_expr} / {cond} 三处即可
--   base=app   : {day_col}=date(f.app_time)       {cond}=f.if_app = 1
--   base=issue : {day_col}=date(f.release_time)   {cond}=f.if_issue = 1
-- =====================================================================
select {day_col} as d, {dim_expr} as dim,
    sum(f.if_app)                as if_app,
    sum(f.if_issue)              as if_issue,
    sum(f.contract_amount)       as contract_amount,
    sum(f.haircut_amount)        as haircut_amount,
    sum(f.should_interest)       as should_interest,
    sum(f.if_in_sx)              as if_in_sx,
    sum(f.if_sx_passed)          as if_sx_passed,
    sum(f.if_in_sx_24h)          as if_in_sx_24h,
    sum(f.if_sx_passed_24h)      as if_sx_passed_24h,
    sum(f.if_in_sx_120h)         as if_in_sx_120h,
    sum(f.if_sx_passed_120h)     as if_sx_passed_120h,
    sum(f.is_t0_window_1)        as is_t0_window_1,
    sum(f.is_t3_window_1)        as is_t3_window_1,
    sum(f.is_t7_window_1)        as is_t7_window_1,
    sum(f.is_t0_window_2)        as is_t0_window_2,
    sum(f.is_t0_window_3)        as is_t0_window_3,
    sum(f.is_t0_window_4)        as is_t0_window_4,
    sum(f.is_t3_window_4)        as is_t3_window_4,
    sum(f.is_t7_window_4)        as is_t7_window_4,
    sum(f.t0_overdue_capit_1)    as t0_overdue_capit_1,
    sum(f.t0_should_capit_1)     as t0_should_capit_1,
    sum(f.t3_overdue_capit_1)    as t3_overdue_capit_1,
    sum(f.t3_should_capit_1)     as t3_should_capit_1,
    sum(f.t7_overdue_capit_1)    as t7_overdue_capit_1,
    sum(f.t7_should_capit_1)     as t7_should_capit_1,
    sum(f.t0_overdue_capit_2)    as t0_overdue_capit_2,
    sum(f.t0_should_capit_2)     as t0_should_capit_2,
    sum(f.t0_overdue_capit_3)    as t0_overdue_capit_3,
    sum(f.t0_should_capit_3)     as t0_should_capit_3,
    sum(f.t0_overdue_capit_4)    as t0_overdue_capit_4,
    sum(f.t0_should_capit_4)     as t0_should_capit_4,
    sum(f.t3_overdue_capit_4)    as t3_overdue_capit_4,
    sum(f.t3_should_capit_4)     as t3_should_capit_4,
    sum(f.t7_overdue_capit_4)    as t7_overdue_capit_4,
    sum(f.t7_should_capit_4)     as t7_should_capit_4,
    sum(f.t3_overdue_interest_4) as t3_overdue_interest_4,
    sum(f.t7_overdue_interest_4) as t7_overdue_interest_4,
    sum(f.is_t0_overdue_1)       as is_t0_overdue_1,
    sum(f.is_t3_overdue_1)       as is_t3_overdue_1,
    sum(f.is_t7_overdue_1)       as is_t7_overdue_1,
    sum(f.is_t0_overdue_4)       as is_t0_overdue_4,
    sum(f.is_t3_overdue_4)       as is_t3_overdue_4,
    sum(f.is_t7_overdue_4)       as is_t7_overdue_4,
    sum(f.loan_cycle*f.contract_amount) as loan_cycle_amount
from mx.wxs_application_funnel f
LEFT JOIN (
  SELECT
    biz_id, product_name_new, first_issue_date, real_issue_amount, loan_contract_amount,
    android_oldcust_maincreditlevel_charge_v5_3, android_oldcust_maincreditlevel_charge_v6_1,
    android_oldcust_midcreditlevel_charge_v5_3, android_oldcust_midcreditlevel_charge_v6_1,
    v3_flag, v3_flag_huidu, fd_high_pass_label,
    max_ovd_days_all, max_overdue_day_30d_all,
    other_app_has_overdue_tag, other_app_has_overdue_interval_tag,
    if_reloan_24h, income, baseinfo_userprof_age, baseinfo_userprof_degree,
    baseinfo_marry, baseinfo_employee_type, baseinfo_has_car, baseinfo_has_house,
    v5_3_fraud_score, v5_3_behavior_score, v5_fraud_score, v5_behavior_score,
    last_repay_gap_days_app_group, minstay_repayplan_second_30d_mid, history_loanrec_cnt_lastprepaydays_v2,
    curr_ovd_cnt_all, curr_ovd_cnt_other_app_group, curr_ovd_cnt_this_app_group,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id AND y.rn = 1
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.create_time) >= date '2026-06-29'
  and {cond}
group by 1, 2 order by 1, 2


-- =====================================================================
-- 【模板 B】6-12 级客群专项 取数 SQL 模板
--   与模板 A 唯一区别: where 里多加一行评级限定(主评级 6~12 级)
--   LV_FILTER = try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) between 6 and 12
--   聚合字段同模板 A(去掉最后 6 个 is_t*_overdue_*)
-- =====================================================================
select {day_col} as d, {dim_expr} as dim,
    sum(f.if_app)                as if_app,
    sum(f.if_issue)              as if_issue,
    sum(f.contract_amount)       as contract_amount,
    sum(f.haircut_amount)        as haircut_amount,
    sum(f.should_interest)       as should_interest,
    sum(f.if_in_sx)              as if_in_sx,
    sum(f.if_sx_passed)          as if_sx_passed,
    sum(f.if_in_sx_24h)          as if_in_sx_24h,
    sum(f.if_sx_passed_24h)      as if_sx_passed_24h,
    sum(f.if_in_sx_120h)         as if_in_sx_120h,
    sum(f.if_sx_passed_120h)     as if_sx_passed_120h,
    sum(f.is_t0_window_1)        as is_t0_window_1,
    sum(f.is_t3_window_1)        as is_t3_window_1,
    sum(f.is_t7_window_1)        as is_t7_window_1,
    sum(f.is_t0_window_2)        as is_t0_window_2,
    sum(f.is_t0_window_3)        as is_t0_window_3,
    sum(f.is_t0_window_4)        as is_t0_window_4,
    sum(f.is_t3_window_4)        as is_t3_window_4,
    sum(f.is_t7_window_4)        as is_t7_window_4,
    sum(f.t0_overdue_capit_1)    as t0_overdue_capit_1,
    sum(f.t0_should_capit_1)     as t0_should_capit_1,
    sum(f.t3_overdue_capit_1)    as t3_overdue_capit_1,
    sum(f.t3_should_capit_1)     as t3_should_capit_1,
    sum(f.t7_overdue_capit_1)    as t7_overdue_capit_1,
    sum(f.t7_should_capit_1)     as t7_should_capit_1,
    sum(f.t0_overdue_capit_2)    as t0_overdue_capit_2,
    sum(f.t0_should_capit_2)     as t0_should_capit_2,
    sum(f.t0_overdue_capit_3)    as t0_overdue_capit_3,
    sum(f.t0_should_capit_3)     as t0_should_capit_3,
    sum(f.t0_overdue_capit_4)    as t0_overdue_capit_4,
    sum(f.t0_should_capit_4)     as t0_should_capit_4,
    sum(f.t3_overdue_capit_4)    as t3_overdue_capit_4,
    sum(f.t3_should_capit_4)     as t3_should_capit_4,
    sum(f.t7_overdue_capit_4)    as t7_overdue_capit_4,
    sum(f.t7_should_capit_4)     as t7_should_capit_4,
    sum(f.t3_overdue_interest_4) as t3_overdue_interest_4,
    sum(f.t7_overdue_interest_4) as t7_overdue_interest_4,
    sum(f.loan_cycle*f.contract_amount) as loan_cycle_amount
from mx.wxs_application_funnel f
LEFT JOIN (
  SELECT
    biz_id, product_name_new,
    android_oldcust_maincreditlevel_charge_v5_3, android_oldcust_midcreditlevel_charge_v5_3,
    v3_flag, fd_high_pass_label,
    max_ovd_days_all, other_app_has_overdue_tag, if_reloan_24h,
    income, baseinfo_userprof_age, baseinfo_userprof_degree,
    baseinfo_marry, baseinfo_employee_type, baseinfo_has_car, baseinfo_has_house,
    v5_3_fraud_score, v5_3_behavior_score,
    last_repay_gap_days_app_group,
    curr_ovd_cnt_all, curr_ovd_cnt_this_app_group,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id AND y.rn = 1
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.create_time) >= date '2026-06-29'
  and {cond}
  and try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) between 6 and 12
group by 1, 2 order by 1, 2


-- =====================================================================
-- 【维度清单】dim_expr 替换表
--   —— 宽表维度 FUNNEL_DIMS ——
-- =====================================================================
-- product_name       : f.product_name
-- app_group          : f.app_group
-- channel_category   : f.channel_category
-- source             : f.source
-- product_type       : f.product_type
-- product_day        : cast(f.product_day as varchar)
-- loan_cycle         : cast(f.loan_cycle as varchar)
-- reloan_num         : case when f.reloan_num=2 then '2贷'
--                       when f.reloan_num=3 then '3贷'
--                       when f.reloan_num<=5 then '4-5贷'
--                       when f.reloan_num<=9 then '6-9贷' else '10+贷' end
-- contract_amount    : case when f.contract_amount<500 then 'L_lt500'
--                       when f.contract_amount<1000 then 'L_500_1k'
--                       when f.contract_amount<2000 then 'L_1k_2k'
--                       when f.contract_amount<5000 then 'L_2k_5k' else 'L_ge5k' end
-- t0_should_capit    : case when f.t0_should_capit_1<500 then 'T0_lt500'
--                       when f.t0_should_capit_1<1000 then 'T0_500_1k'
--                       when f.t0_should_capit_1<2000 then 'T0_1k_2k'
--                       when f.t0_should_capit_1<5000 then 'T0_2k_5k' else 'T0_ge5k' end
-- grant_score        : case when f.grant_score<50 then 'S_lt50'
--                       when f.grant_score<60 then 'S_50_60'
--                       when f.grant_score<70 then 'S_60_70'
--                       when f.grant_score<80 then 'S_70_80'
--                       when f.grant_score<90 then 'S_80_90' else 'S_ge90' end
-- grant_strategy     : f.grant_strategy
-- product_level      : f.product_level
-- risk_level         : f.risk_level

--   —— 评级表维度 YJ_DIMS ——
-- product_name_new   : coalesce(y.product_name_new,'空')
-- v5_3主评级          : coalesce(cast(y.android_oldcust_maincreditlevel_charge_v5_3 as varchar),'空')
-- v6_1主评级          : coalesce(cast(y.android_oldcust_maincreditlevel_charge_v6_1 as varchar),'空')
-- v5_3中评级          : coalesce(cast(y.android_oldcust_midcreditlevel_charge_v5_3 as varchar),'空')
-- v6_1中评级          : coalesce(cast(y.android_oldcust_midcreditlevel_charge_v6_1 as varchar),'空')
-- v3_flag            : coalesce(cast(y.v3_flag as varchar),'空')
-- v3_flag_huidu      : coalesce(cast(y.v3_flag_huidu as varchar),'空')
-- fd_high_pass       : coalesce(cast(y.fd_high_pass_label as varchar),'空')
-- if_reloan_24h      : coalesce(cast(y.if_reloan_24h as varchar),'空')
-- 学历               : coalesce(cast(y.baseinfo_userprof_degree as varchar),'空')
-- 婚姻               : coalesce(cast(y.baseinfo_marry as varchar),'空')
-- 职业               : coalesce(cast(y.baseinfo_employee_type as varchar),'空')
-- 有车               : coalesce(cast(y.baseinfo_has_car as varchar),'空')
-- 有房               : coalesce(cast(y.baseinfo_has_house as varchar),'空')
-- 收入段             : case when y.income<3000 then 'inc_lt3k'
--                       when y.income<5000 then 'inc_3_5k'
--                       when y.income<8000 then 'inc_5_8k' else 'inc_ge8k' end
-- 年龄段             : case when y.baseinfo_userprof_age<25 then 'age_lt25'
--                       when y.baseinfo_userprof_age<30 then 'age_25_30'
--                       when y.baseinfo_userprof_age<35 then 'age_30_35'
--                       when y.baseinfo_userprof_age<40 then 'age_35_40' else 'age_ge40' end
-- v5_3欺诈分         : case when y.v5_3_fraud_score<500 then 'fx_lt500'
--                       when y.v5_3_fraud_score<600 then 'fx_500_600'
--                       when y.v5_3_fraud_score<700 then 'fx_600_700' else 'fx_ge700' end
-- v5_3行为分         : case when y.v5_3_behavior_score<500 then 'bh_lt500'
--                       when y.v5_3_behavior_score<600 then 'bh_500_600'
--                       when y.v5_3_behavior_score<700 then 'bh_600_700' else 'bh_ge700' end
-- 当前逾期笔数       : case when y.curr_ovd_cnt_all=0 then 'ovd_0'
--                       when y.curr_ovd_cnt_all=1 then 'ovd_1'
--                       when y.curr_ovd_cnt_all=2 then 'ovd_2' else 'ovd_3+' end
-- 本APP逾期笔数      : case when y.curr_ovd_cnt_this_app_group=0 then 'aovd_0'
--                       when y.curr_ovd_cnt_this_app_group=1 then 'aovd_1'
--                       when y.curr_ovd_cnt_this_app_group=2 then 'aovd_2' else 'aovd_3+' end
-- 历史最大逾期天     : case when y.max_ovd_days_all=0 then 'mxovd_0'
--                       when y.max_ovd_days_all<=7 then 'mxovd_1_7'
--                       when y.max_ovd_days_all<=30 then 'mxovd_8_30'
--                       when y.max_ovd_days_all<=90 then 'mxovd_31_90' else 'mxovd_gt90' end
-- 他APP有逾期        : coalesce(cast(y.other_app_has_overdue_tag as varchar),'空')
-- 最近还款间隔       : case when y.last_repay_gap_days_app_group is null then 'gap_空'
--                       when y.last_repay_gap_days_app_group<=3 then 'gap_0_3'
--                       when y.last_repay_gap_days_app_group<=7 then 'gap_4_7'
--                       when y.last_repay_gap_days_app_group<=14 then 'gap_8_14' else 'gap_gt14' end

--   —— 6-12 专项额外维度(评级子段/单级, 在 6-12 客群内部再切) ——
-- 评级子段(6-12专项)  : case when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) between 6 and 9
--                         then '6-9级' else '10-12级' end
-- 评级单级(6-12专项)  : cast(try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as integer) as varchar)


-- =====================================================================
-- 【V5_3 评级自定义分档】(本地计算分档, 下为 SQL 端等价表达式, 可直接用于 dim_expr)
--   注: 全量取数时该维度原始输出为评级等级字符串, 分档在本地 Python 完成;
--       如需在 SQL 端直接验证分档结果, 用下列 case when 等价替换 dim_expr
-- =====================================================================
-- 三档(1-5 / 6-9 / 10-12 / 13参照 / 空):
--   case
--     when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) is null then '空'
--     when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) <= 5  then '1-5级'
--     when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) <= 9  then '6-9级'
--     when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) <= 12 then '10-12级'
--     else '13级(参照)' end
-- 两档(1-5 / 6-12 / 13参照 / 空):
--   case
--     when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) is null then '空'
--     when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) <= 5  then '1-5级'
--     when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) <= 12 then '6-12级'
--     else '13级(参照)' end
--   (中评级同理, 将字段换成 y.android_oldcust_midcreditlevel_charge_v5_3 即可)


-- =====================================================================
-- 【完整示例 1】全量 · 产品维度 · 放款基准(issue)
-- =====================================================================
select date(f.release_time) as d, f.product_name as dim,
    sum(f.if_app)                as if_app,
    sum(f.if_issue)              as if_issue,
    sum(f.contract_amount)       as contract_amount,
    sum(f.haircut_amount)        as haircut_amount,
    sum(f.should_interest)       as should_interest,
    sum(f.if_in_sx)              as if_in_sx,
    sum(f.if_sx_passed)          as if_sx_passed,
    sum(f.if_in_sx_24h)          as if_in_sx_24h,
    sum(f.if_sx_passed_24h)      as if_sx_passed_24h,
    sum(f.if_in_sx_120h)         as if_in_sx_120h,
    sum(f.if_sx_passed_120h)     as if_sx_passed_120h,
    sum(f.is_t0_window_1)        as is_t0_window_1,
    sum(f.is_t3_window_1)        as is_t3_window_1,
    sum(f.is_t7_window_1)        as is_t7_window_1,
    sum(f.is_t0_window_2)        as is_t0_window_2,
    sum(f.is_t0_window_3)        as is_t0_window_3,
    sum(f.is_t0_window_4)        as is_t0_window_4,
    sum(f.is_t3_window_4)        as is_t3_window_4,
    sum(f.is_t7_window_4)        as is_t7_window_4,
    sum(f.t0_overdue_capit_1)    as t0_overdue_capit_1,
    sum(f.t0_should_capit_1)     as t0_should_capit_1,
    sum(f.t3_overdue_capit_1)    as t3_overdue_capit_1,
    sum(f.t3_should_capit_1)     as t3_should_capit_1,
    sum(f.t7_overdue_capit_1)    as t7_overdue_capit_1,
    sum(f.t7_should_capit_1)     as t7_should_capit_1,
    sum(f.t0_overdue_capit_2)    as t0_overdue_capit_2,
    sum(f.t0_should_capit_2)     as t0_should_capit_2,
    sum(f.t0_overdue_capit_3)    as t0_overdue_capit_3,
    sum(f.t0_should_capit_3)     as t0_should_capit_3,
    sum(f.t0_overdue_capit_4)    as t0_overdue_capit_4,
    sum(f.t0_should_capit_4)     as t0_should_capit_4,
    sum(f.t3_overdue_capit_4)    as t3_overdue_capit_4,
    sum(f.t3_should_capit_4)     as t3_should_capit_4,
    sum(f.t7_overdue_capit_4)    as t7_overdue_capit_4,
    sum(f.t7_should_capit_4)     as t7_should_capit_4,
    sum(f.t3_overdue_interest_4) as t3_overdue_interest_4,
    sum(f.t7_overdue_interest_4) as t7_overdue_interest_4,
    sum(f.is_t0_overdue_1)       as is_t0_overdue_1,
    sum(f.is_t3_overdue_1)       as is_t3_overdue_1,
    sum(f.is_t7_overdue_1)       as is_t7_overdue_1,
    sum(f.is_t0_overdue_4)       as is_t0_overdue_4,
    sum(f.is_t3_overdue_4)       as is_t3_overdue_4,
    sum(f.is_t7_overdue_4)       as is_t7_overdue_4,
    sum(f.loan_cycle*f.contract_amount) as loan_cycle_amount
from mx.wxs_application_funnel f
LEFT JOIN (
  SELECT
    biz_id, product_name_new, first_issue_date, real_issue_amount, loan_contract_amount,
    android_oldcust_maincreditlevel_charge_v5_3, android_oldcust_maincreditlevel_charge_v6_1,
    android_oldcust_midcreditlevel_charge_v5_3, android_oldcust_midcreditlevel_charge_v6_1,
    v3_flag, v3_flag_huidu, fd_high_pass_label,
    max_ovd_days_all, max_overdue_day_30d_all,
    other_app_has_overdue_tag, other_app_has_overdue_interval_tag,
    if_reloan_24h, income, baseinfo_userprof_age, baseinfo_userprof_degree,
    baseinfo_marry, baseinfo_employee_type, baseinfo_has_car, baseinfo_has_house,
    v5_3_fraud_score, v5_3_behavior_score, v5_fraud_score, v5_behavior_score,
    last_repay_gap_days_app_group, minstay_repayplan_second_30d_mid, history_loanrec_cnt_lastprepaydays_v2,
    curr_ovd_cnt_all, curr_ovd_cnt_other_app_group, curr_ovd_cnt_this_app_group,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id AND y.rn = 1
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.create_time) >= date '2026-06-29'
  and f.if_issue = 1
group by 1, 2 order by 1, 2


-- =====================================================================
-- 【完整示例 2】6-12 专项 · 评级子段 · 放款基准(issue)
-- =====================================================================
select date(f.release_time) as d,
    case when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) between 6 and 9
         then '6-9级' else '10-12级' end as dim,
    sum(f.if_app)                as if_app,
    sum(f.if_issue)              as if_issue,
    sum(f.contract_amount)       as contract_amount,
    sum(f.haircut_amount)        as haircut_amount,
    sum(f.should_interest)       as should_interest,
    sum(f.if_in_sx)              as if_in_sx,
    sum(f.if_sx_passed)          as if_sx_passed,
    sum(f.if_in_sx_24h)          as if_in_sx_24h,
    sum(f.if_sx_passed_24h)      as if_sx_passed_24h,
    sum(f.if_in_sx_120h)         as if_in_sx_120h,
    sum(f.if_sx_passed_120h)     as if_sx_passed_120h,
    sum(f.is_t0_window_1)        as is_t0_window_1,
    sum(f.is_t3_window_1)        as is_t3_window_1,
    sum(f.is_t7_window_1)        as is_t7_window_1,
    sum(f.is_t0_window_2)        as is_t0_window_2,
    sum(f.is_t0_window_3)        as is_t0_window_3,
    sum(f.is_t0_window_4)        as is_t0_window_4,
    sum(f.is_t3_window_4)        as is_t3_window_4,
    sum(f.is_t7_window_4)        as is_t7_window_4,
    sum(f.t0_overdue_capit_1)    as t0_overdue_capit_1,
    sum(f.t0_should_capit_1)     as t0_should_capit_1,
    sum(f.t3_overdue_capit_1)    as t3_overdue_capit_1,
    sum(f.t3_should_capit_1)     as t3_should_capit_1,
    sum(f.t7_overdue_capit_1)    as t7_overdue_capit_1,
    sum(f.t7_should_capit_1)     as t7_should_capit_1,
    sum(f.t0_overdue_capit_2)    as t0_overdue_capit_2,
    sum(f.t0_should_capit_2)     as t0_should_capit_2,
    sum(f.t0_overdue_capit_3)    as t0_overdue_capit_3,
    sum(f.t0_should_capit_3)     as t0_should_capit_3,
    sum(f.t0_overdue_capit_4)    as t0_overdue_capit_4,
    sum(f.t0_should_capit_4)     as t0_should_capit_4,
    sum(f.t3_overdue_capit_4)    as t3_overdue_capit_4,
    sum(f.t3_should_capit_4)     as t3_should_capit_4,
    sum(f.t7_overdue_capit_4)    as t7_overdue_capit_4,
    sum(f.t7_should_capit_4)     as t7_should_capit_4,
    sum(f.t3_overdue_interest_4) as t3_overdue_interest_4,
    sum(f.t7_overdue_interest_4) as t7_overdue_interest_4,
    sum(f.loan_cycle*f.contract_amount) as loan_cycle_amount
from mx.wxs_application_funnel f
LEFT JOIN (
  SELECT
    biz_id, product_name_new,
    android_oldcust_maincreditlevel_charge_v5_3, android_oldcust_midcreditlevel_charge_v5_3,
    v3_flag, fd_high_pass_label,
    max_ovd_days_all, other_app_has_overdue_tag, if_reloan_24h,
    income, baseinfo_userprof_age, baseinfo_userprof_degree,
    baseinfo_marry, baseinfo_employee_type, baseinfo_has_car, baseinfo_has_house,
    v5_3_fraud_score, v5_3_behavior_score,
    last_repay_gap_days_app_group,
    curr_ovd_cnt_all, curr_ovd_cnt_this_app_group,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id AND y.rn = 1
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.create_time) >= date '2026-06-29'
  and f.if_issue = 1
  and try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) between 6 and 12
group by 1, 2 order by 1, 2


-- =====================================================================
-- 【完整示例 3】全量 · V5_3主评级两档(1-5 / 6-12) · 放款基准(issue)
-- =====================================================================
select date(f.release_time) as d,
    case
      when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) is null then '空'
      when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) <= 5  then '1-5级'
      when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) <= 12 then '6-12级'
      else '13级(参照)' end as dim,
    sum(f.if_app)                as if_app,
    sum(f.if_issue)              as if_issue,
    sum(f.contract_amount)       as contract_amount,
    sum(f.haircut_amount)        as haircut_amount,
    sum(f.should_interest)       as should_interest,
    sum(f.if_in_sx)              as if_in_sx,
    sum(f.if_sx_passed)          as if_sx_passed,
    sum(f.if_in_sx_24h)          as if_in_sx_24h,
    sum(f.if_sx_passed_24h)      as if_sx_passed_24h,
    sum(f.if_in_sx_120h)         as if_in_sx_120h,
    sum(f.if_sx_passed_120h)     as if_sx_passed_120h,
    sum(f.is_t0_window_1)        as is_t0_window_1,
    sum(f.is_t3_window_1)        as is_t3_window_1,
    sum(f.is_t7_window_1)        as is_t7_window_1,
    sum(f.is_t0_window_2)        as is_t0_window_2,
    sum(f.is_t0_window_3)        as is_t0_window_3,
    sum(f.is_t0_window_4)        as is_t0_window_4,
    sum(f.is_t3_window_4)        as is_t3_window_4,
    sum(f.is_t7_window_4)        as is_t7_window_4,
    sum(f.t0_overdue_capit_1)    as t0_overdue_capit_1,
    sum(f.t0_should_capit_1)     as t0_should_capit_1,
    sum(f.t3_overdue_capit_1)    as t3_overdue_capit_1,
    sum(f.t3_should_capit_1)     as t3_should_capit_1,
    sum(f.t7_overdue_capit_1)    as t7_overdue_capit_1,
    sum(f.t7_should_capit_1)     as t7_should_capit_1,
    sum(f.t0_overdue_capit_2)    as t0_overdue_capit_2,
    sum(f.t0_should_capit_2)     as t0_should_capit_2,
    sum(f.t0_overdue_capit_3)    as t0_overdue_capit_3,
    sum(f.t0_should_capit_3)     as t0_should_capit_3,
    sum(f.t0_overdue_capit_4)    as t0_overdue_capit_4,
    sum(f.t0_should_capit_4)     as t0_should_capit_4,
    sum(f.t3_overdue_capit_4)    as t3_overdue_capit_4,
    sum(f.t3_should_capit_4)     as t3_should_capit_4,
    sum(f.t7_overdue_capit_4)    as t7_overdue_capit_4,
    sum(f.t7_should_capit_4)     as t7_should_capit_4,
    sum(f.t3_overdue_interest_4) as t3_overdue_interest_4,
    sum(f.t7_overdue_interest_4) as t7_overdue_interest_4,
    sum(f.is_t0_overdue_1)       as is_t0_overdue_1,
    sum(f.is_t3_overdue_1)       as is_t3_overdue_1,
    sum(f.is_t7_overdue_1)       as is_t7_overdue_1,
    sum(f.is_t0_overdue_4)       as is_t0_overdue_4,
    sum(f.is_t3_overdue_4)       as is_t3_overdue_4,
    sum(f.is_t7_overdue_4)       as is_t7_overdue_4,
    sum(f.loan_cycle*f.contract_amount) as loan_cycle_amount
from mx.wxs_application_funnel f
LEFT JOIN (
  SELECT
    biz_id, product_name_new, first_issue_date, real_issue_amount, loan_contract_amount,
    android_oldcust_maincreditlevel_charge_v5_3, android_oldcust_maincreditlevel_charge_v6_1,
    android_oldcust_midcreditlevel_charge_v5_3, android_oldcust_midcreditlevel_charge_v6_1,
    v3_flag, v3_flag_huidu, fd_high_pass_label,
    max_ovd_days_all, max_overdue_day_30d_all,
    other_app_has_overdue_tag, other_app_has_overdue_interval_tag,
    if_reloan_24h, income, baseinfo_userprof_age, baseinfo_userprof_degree,
    baseinfo_marry, baseinfo_employee_type, baseinfo_has_car, baseinfo_has_house,
    v5_3_fraud_score, v5_3_behavior_score, v5_fraud_score, v5_behavior_score,
    last_repay_gap_days_app_group, minstay_repayplan_second_30d_mid, history_loanrec_cnt_lastprepaydays_v2,
    curr_ovd_cnt_all, curr_ovd_cnt_other_app_group, curr_ovd_cnt_this_app_group,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id AND y.rn = 1
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.create_time) >= date '2026-06-29'
  and f.if_issue = 1
group by 1, 2 order by 1, 2
