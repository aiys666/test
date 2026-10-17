DROP TABLE if exists ind.ys_old_app_relate_te_all;
create table ind.ys_old_app_relate_te_all as
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
(select id,create_time,mid,is_reloan2,app_time
from dwb.dwb_risk_loan_credit_repay_overdue_info_df
where is_reloan2 in ('OLD_PLUS','OLD_SINGLE') 
and loan_type2 in ('loop') 
and create_time>=timestamp'2025-01-01') app
left join ind.ys_mor_tmp_loop_credit te 
on app.mid=te.mid 

and coalesce(app.app_time,app.create_time)>=te.endtime

)
-- where rn_te=1
;





DROP TABLE if exists ind.ys_mor_tmp_loop_credit_app;
create table ind.ys_mor_tmp_loop_credit_app as 
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
    app.if_app 
 
from ind.ctj_mor_tmp_loop_credit te 
left join ind.ys_old_app_relate_te_all relate 
    on te.externalid = relate.relate_externalid 
left join dwb.dwb_risk_loan_credit_repay_overdue_info_df app
    on relate.id = app.id
;



DROP TABLE if exists ind.ys_mor_tmp_loop_credit_trans;
create table ind.ys_mor_tmp_loop_credit_trans as 
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
 
from  ind.ys_mor_tmp_loop_credit_app
group by 1) trans on a.externalid=trans.trans_id
;




SELECT
    /* ---- time only ---- */
    date_format(createtime, '%Y-%m-01')                            AS create_month,
    to_char(date_trunc('week', createtime), 'yyyy-mm-dd')          AS create_week,
    /* ---- overall metrics ---- */
    COUNT(1)                                                        AS credit_cnt,
    SUM(if_click_T1)                                                AS click_cnt_T1,
    SUM(if_click_T7)                                                AS click_cnt_T7,
    SUM(if_click_T30)                                               AS click_cnt_T30,
    SUM(if_confirm_T1)                                              AS confirm_cnt_T1,
    SUM(if_confirm_T7)                                              AS confirm_cnt_T7,
    SUM(if_confirm_T30)                                             AS confirm_cnt_T30,
    /* ---- overall rates ---- */
    ROUND(SUM(if_confirm_T1)  * 1.0 / COUNT(1), 4)                 AS confirm_rate_T1,
    ROUND(SUM(if_confirm_T7)  * 1.0 / COUNT(1), 4)                 AS confirm_rate_T7,
    ROUND(SUM(if_confirm_T30) * 1.0 / COUNT(1), 4)                 AS confirm_rate_T30,
    ROUND(SUM(if_click_T7)   * 1.0 / COUNT(1), 4)                  AS click_rate_T7
FROM ind.ctj_mor_tmp_loop_credit_trans a
WHERE createtime >= DATE '2026-01-01'
GROUP BY
    date_format(createtime, '%Y-%m-01'),
    to_char(date_trunc('week', createtime), 'yyyy-mm-dd')
ORDER BY create_month, create_week;



SELECT
    /* ---- time only ---- */
    date_format(createtime, '%Y-%m-01')                            AS create_month,
    to_char(date_trunc('week', createtime), 'yyyy-mm-dd')          AS create_week,

    /* ---- overall metrics ---- */
    COUNT(1)                                                        AS credit_cnt,
    SUM(if_click_T1)                                                AS click_cnt_T1,
    SUM(if_click_T7)                                                AS click_cnt_T7,
    SUM(if_click_T30)                                               AS click_cnt_T30,
    SUM(if_confirm_T1)                                              AS confirm_cnt_T1,
    SUM(if_confirm_T7)                                              AS confirm_cnt_T7,
    SUM(if_confirm_T30)                                             AS confirm_cnt_T30,
    /* ---- overall rates ---- */
    ROUND(SUM(if_confirm_T1)  * 1.0 / COUNT(1), 4)                 AS confirm_rate_T1,
    ROUND(SUM(if_confirm_T7)  * 1.0 / COUNT(1), 4)                 AS confirm_rate_T7,
    ROUND(SUM(if_confirm_T30) * 1.0 / COUNT(1), 4)                 AS confirm_rate_T30,

    ROUND(SUM(if_click_T7)   * 1.0 / COUNT(1), 4)                  AS click_rate_T7

FROM ind.ys_mor_tmp_loop_credit_trans a
WHERE createtime >= DATE '2026-01-01'
GROUP BY
    date_format(createtime, '%Y-%m-01'),
    to_char(date_trunc('week', createtime), 'yyyy-mm-dd')
ORDER BY create_month, create_week;