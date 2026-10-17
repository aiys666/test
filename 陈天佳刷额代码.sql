DROP TABLE if exists ind.ctj_old_app_relate_te;
create table ind.ctj_old_app_relate_te as
select * from(
select app.id 
,app.create_time
,app.mid
,app.is_reloan2
---,te.id as relate_te_id
,te.externalid as relate_externalid
,te.createtime as te_time 
,te.endtime as te_end_time 
,row_number() over (partition by app.id order by te.createtime desc) as rn_te
from 
(select * 
from dwb.dwb_risk_loan_credit_repay_overdue_info_df
where is_reloan2 in ('OLD_PLUS','OLD_SINGLE') 
and loan_type2 in ('loop')
and create_time>=timestamp'2025-01-01') app
left join ind.ctj_mor_tmp_loop_credit te 
on app.mid=te.mid 
and coalesce(app.app_time,app.create_time)>=te.endtime

)
where rn_te=1
;





DROP TABLE if exists ind.ctj_mor_tmp_loop_credit_app;
create table ind.ctj_mor_tmp_loop_credit_app as 
select 

    te.externalid,
    --te.id,
    te.createtime as te_time,

    app.id as click_id,
    app.create_time as click_time,

    app.is_reloan2,
    app.is_reloan3,
    app.loan_type2,
    app.reloan_num,
    app.source_channel2,
    app.new_grade_level as new_grade_level_app,
    app.product_level,
    app.loan_cycle,
    app.loan_indexs,
    app.if_regular_backup,
    app.if_backup_switch,

    app.biz_id,
    app.app_time,
    app.app_date,
    app.if_app,
    app.if_pass,
    app.if_issue,

    app.grant_amount_total as grant_amount_total_app,
    app.contract_amount,
    app.circular_amount,

    should_cnt_1_0,
    should_cnt_1_3,
    should_cnt_1_7,
    overdue_cnt_1_0,
    overdue_cnt_1_3,
    overdue_cnt_1_7,
    overdue_amount_1_0,
    overdue_amount_1_3,
    overdue_amount_1_7,
    should_capital_1_0,
    should_capital_1_3,
    should_capital_1_7,

    should_cnt_2_0,
    should_cnt_2_3,
    should_cnt_2_7,
    overdue_cnt_2_0,
    overdue_cnt_2_3,
    overdue_cnt_2_7,
    overdue_amount_2_0,
    overdue_amount_2_3,
    overdue_amount_2_7,
    should_capital_2_0,
    should_capital_2_3,
    should_capital_2_7,

    should_cnt_3_0,
    should_cnt_3_3,
    should_cnt_3_7,
    overdue_cnt_3_0,
    overdue_cnt_3_3,
    overdue_cnt_3_7,
    overdue_amount_3_0,
    overdue_amount_3_3,
    overdue_amount_3_7,
    should_capital_3_0,
    should_capital_3_3,
    should_capital_3_7,

    should_cnt_4_0,
    should_cnt_4_3,
    should_cnt_4_7,
    overdue_cnt_4_0,
    overdue_cnt_4_3,
    overdue_cnt_4_7,
    overdue_amount_4_0,
    overdue_amount_4_3,
    overdue_amount_4_7,
    should_capital_4_0,
    should_capital_4_3,
    should_capital_4_7,

    should_cnt_5_0,
    should_cnt_5_3,
    should_cnt_5_7,
    overdue_cnt_5_0,
    overdue_cnt_5_3,
    overdue_cnt_5_7,
    overdue_amount_5_0,
    overdue_amount_5_3,
    overdue_amount_5_7,
    should_capital_5_0,
    should_capital_5_3,
    should_capital_5_7,

    should_cnt_6_0,
    should_cnt_6_3,
    should_cnt_6_7,
    overdue_cnt_6_0,
    overdue_cnt_6_3,
    overdue_cnt_6_7,
    overdue_amount_6_0,
    overdue_amount_6_3,
    overdue_amount_6_7,
    should_capital_6_0,
    should_capital_6_3,
    should_capital_6_7,

    should_cnt_7_0,
    should_cnt_7_3,
    should_cnt_7_7,
    overdue_cnt_7_0,
    overdue_cnt_7_3,
    overdue_cnt_7_7,
    overdue_amount_7_0,
    overdue_amount_7_3,
    overdue_amount_7_7,
    should_capital_7_0,
    should_capital_7_3,
    should_capital_7_7,

    should_cnt_8_0,
    should_cnt_8_3,
    should_cnt_8_7,
    overdue_cnt_8_0,
    overdue_cnt_8_3,
    overdue_cnt_8_7,
    overdue_amount_8_0,
    overdue_amount_8_3,
    overdue_amount_8_7,
    should_capital_8_0,
    should_capital_8_3,
    should_capital_8_7


from ind.ctj_mor_tmp_loop_credit te 
left join ind.ctj_old_app_relate_te relate 
    on te.externalid = relate.relate_externalid 
left join dwb.dwb_risk_loan_credit_repay_overdue_info_df app
    on relate.id = app.id
;



DROP TABLE if exists ind.ctj_mor_tmp_loop_credit_trans;
create table ind.ctj_mor_tmp_loop_credit_trans as 
select a.*
,trans.*
from ind.ctj_mor_tmp_loop_credit a 
left join 
(select externalid  as trans_id

,max(case when click_id is not null then 1 else 0 end) as if_click
,max(case when biz_id is not null then 1 else 0 end) as if_confirm
,max(case when click_id is not null and date_diff('day',te_time,click_time)<=1 then 1 else 0 end) as if_click_T1
,max(case when biz_id is not null  and date_diff('day',te_time,app_time)<=1 then 1 else 0 end) as if_confirm_T1
,max(case when click_id is not null and date_diff('day',te_time,click_time)<=3 then 1 else 0 end) as if_click_T3
,max(case when biz_id is not null  and date_diff('day',te_time,app_time)<=3 then 1 else 0 end) as if_confirm_T3
,max(case when click_id is not null and date_diff('day',te_time,click_time)<=5 then 1 else 0 end) as if_click_T5
,max(case when biz_id is not null  and date_diff('day',te_time,app_time)<=5 then 1 else 0 end) as if_confirm_T5
,max(case when click_id is not null and date_diff('day',te_time,click_time)<=7 then 1 else 0 end) as if_click_T7
,max(case when biz_id is not null  and date_diff('day',te_time,app_time)<=7 then 1 else 0 end) as if_confirm_T7
,max(case when click_id is not null and date_diff('day',te_time,click_time)<=15 then 1 else 0 end) as if_click_T15
,max(case when biz_id is not null  and date_diff('day',te_time,app_time)<=15 then 1 else 0 end) as if_confirm_T15
,max(case when click_id is not null and date_diff('day',te_time,click_time)<=30 then 1 else 0 end) as if_click_T30
,max(case when biz_id is not null  and date_diff('day',te_time,app_time)<=30 then 1 else 0 end) as if_confirm_T30
,count(case when click_id is not null  then click_id else null end) as click_cnt
,count(case when biz_id is not null then biz_id else null end) as confrim_cnt
,count(case when click_id is not null and date_diff('day',te_time,click_time)<=30 then click_id else null end) as click_cnt_T30
,count(case when biz_id is not null  and date_diff('day',te_time,app_time)<=30 then biz_id else null end) as confrim_cnt_T30


,sum(case when biz_id is not null then cast(new_grade_level_app as int) else null end) as new_grade_level_app
,sum(case when biz_id is not null then grant_amount_total_app else null end) as grant_amount_total_app
,max(case when biz_id is not null then if_pass else null end) if_pass
,max(case when biz_id is not null then if_issue else null end) if_issue
,sum(case when biz_id is not null then if_pass else null end) pass_cnt
,sum(case when biz_id is not null then if_issue else null end) issue_cnt

,sum(case when biz_id is not null and if_issue=1 then grant_amount_total_app else null end) as grant_amount_total_issue
,sum(case when biz_id is not null and if_issue=1 then cast(circular_amount as decimal) else null end) as circular_amount
,sum(case when biz_id is not null and if_issue=1 then contract_amount else null end) as contract_amount
,sum(case when biz_id is not null and if_issue=1 then loan_indexs else null end) as loan_indexs
,sum(case when biz_id is not null and if_issue=1 then contract_amount*loan_cycle else null end) as loan_cycle


,sum(should_cnt_1_0) as should_cnt_1_0
,sum(should_cnt_1_7) as should_cnt_1_7
,sum(overdue_cnt_1_0) as overdue_cnt_1_0
,sum(overdue_cnt_1_7) as overdue_cnt_1_7
,sum(overdue_amount_1_0) as overdue_amount_1_0
,sum(overdue_amount_1_7) as overdue_amount_1_7
,sum(should_capital_1_0) as should_capital_1_0
,sum(should_capital_1_7) as should_capital_1_7

,sum(should_cnt_2_0) as should_cnt_2_0
,sum(should_cnt_2_7) as should_cnt_2_7
,sum(overdue_cnt_2_0) as overdue_cnt_2_0
,sum(overdue_cnt_2_7) as overdue_cnt_2_7
,sum(overdue_amount_2_0) as overdue_amount_2_0
,sum(overdue_amount_2_7) as overdue_amount_2_7
,sum(should_capital_2_0) as should_capital_2_0
,sum(should_capital_2_7) as should_capital_2_7

,sum(should_cnt_3_0) as should_cnt_3_0
,sum(should_cnt_3_7) as should_cnt_3_7
,sum(overdue_cnt_3_0) as overdue_cnt_3_0
,sum(overdue_cnt_3_7) as overdue_cnt_3_7
,sum(overdue_amount_3_0) as overdue_amount_3_0
,sum(overdue_amount_3_7) as overdue_amount_3_7
,sum(should_capital_3_0) as should_capital_3_0
,sum(should_capital_3_7) as should_capital_3_7

from  ind.ctj_mor_tmp_loop_credit_app
group by 1) trans on a.externalid=trans.trans_id
;