

delete from mx.tmp_darren_double_loan_tag_table
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');

insert into mx.tmp_darren_double_loan_tag_table
select cast(externalid as bigint) as externalid,
  cast(json_extract_scalar(outputdata, '$.double_loan_tenant') as double) as double_loan_tenant,
  cast(json_extract_scalar(outputdata, '$.sd_high_pass_label') as double) as sd_high_pass_label,
  cast(json_extract_scalar(outputdata, '$.fd_high_pass_label') as double) as fd_high_pass_label,
  etl_date
from ods.s21_risk_strategy_record
where productid in (310,330,331)
and strategytype = 'CHAMPION'
and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');



delete from mx.tmp_one_click_loan_tag
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');


insert into mx.tmp_one_click_loan_tag
SELECT biz_id,
  cast(json_extract_scalar(outputdata, '$.one_click_loan_tag') as varchar) as one_click_loan_tag,
  createtime,
  etl_date
FROM (select *,
  row_number() over (partition by biz_id order by createtime desc) as rn 
  from ods.s21_risk_strategy_record
  WHERE 
  etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
  -- etl_date >= '20260101'
  AND strategytype = 'CHAMPION'
  AND strategymainid = 599) t0 
  where rn = 1 ;




--实时修改
-- wxs_application_funnel建表
  drop table if exists mx.wxs_reloan; 
  create table if not exists mx.wxs_reloan as

  select distinct  t1.id
  ,case when issue_num is null then 1 else issue_num end as  reloan_num
  ,case when issue_num is null then  '首贷' ELSE '复贷' end as grant_strategy
  from 
  (select  create_time,id,mid from ods_view_presto.s09_os_credit_snapshot ) t1
  left join
  (select t1.id,count(t2.biz_id) +1 as issue_num from 
  (select  create_time,id,mid  from ods_view_presto.s09_os_credit_snapshot) t1
  left join 
  (select cast(ceil(camera_id) as varchar) as biz_id,release_time, customer_id  
  from ods_view_presto.s02_loan where state = 2) t2
  on t1.mid = t2.customer_id  
  where create_time > release_time and release_time  is not null
  group by create_time, t1.id ,t1.mid) t2
  on t1.id = t2.id
  ;
  
  


drop table if exists mx.wxs_risk_ttl;
create table if not exists mx.wxs_risk_ttl as 
--不分期贷后
select 
    t1.camera_id
    ,t1.release_time
    ,t2.should_time
    ,t2.should_capital 
    ,t2.should_interest
    ,t2.should_fine
    ,t3.fact_capital 
    ,t3.fact_interest
    ,t3.fact_fine
    ,t2.now_should_amt
    ,t2.t0_should_amt 
    ,t2.t3_should_amt
    ,t2.t7_should_amt
    ,t2.t14_should_amt
    ,t2.t30_should_amt
    ,t3.now_fact_amt 
    ,t3.t0_fact_amt 
    ,t3.t3_fact_amt
    ,t3.t7_fact_amt
    ,t3.t14_fact_amt
    ,t3.t30_fact_amt
    ,t2.t0_should_num
    ,t2.t3_should_num
    ,t2.t7_should_num
    ,t2.t14_should_num
    ,t2.t30_should_num
    ,t3.pre_p2_repay
    ,t3.p2_repay
    ,t3.p2_repaytt
    ,t3.p1_repay
    ,t3.p0_repay
    ,t4.now_overdue_days
    ,case when date_diff('day',date(should_time),CURRENT_DATE)>0 then 1 else 0 end as is_t0_window
    ,case when date_diff('day',date(should_time),CURRENT_DATE)>3 then 1 else 0 end as is_t3_window
    ,case when date_diff('day',date(should_time),CURRENT_DATE)>7 then 1 else 0 end as is_t7_window
    ,case when date_diff('day',date(should_time),CURRENT_DATE)>14 then 1 else 0 end as is_t14_window
    ,case when date_diff('day',date(should_time),CURRENT_DATE)>30 then 1 else 0 end as is_t30_window
    ,case 
    when t3.now_fact_amt >= t2.now_should_amt then 0 
    when t3.now_fact_amt < t2.now_should_amt then t2.now_should_amt - t3.now_fact_amt  
    when t3.now_fact_amt is null then now_should_amt
    end as now_OVERDUE_AMOUNT
   ,case 
    when t3.t0_fact_amt >= t2.now_should_amt then 0 
    when t3.t0_fact_amt < t2.now_should_amt then t2.now_should_amt - t3.t0_fact_amt  
    when t3.t0_fact_amt is null then t2.t0_should_amt
end as T0_OVERDUE_AMOUNT
,case 
    when t3.t3_fact_amt >= t2.now_should_amt then 0 
    when t3.t3_fact_amt < t2.now_should_amt then t2.now_should_amt - t3.t3_fact_amt  
    when t3.t3_fact_amt is null then t2.t3_should_amt
end as T3_OVERDUE_AMOUNT
,case 
    when t3.t7_fact_amt >= t2.now_should_amt then 0 
    when t3.t7_fact_amt < t2.now_should_amt then t2.now_should_amt - t3.t7_fact_amt  
    when t3.t7_fact_amt is null then t2.t7_should_amt
end as T7_OVERDUE_AMOUNT
,case 
    when t3.t14_fact_amt >= t2.now_should_amt then 0 
    when t3.t14_fact_amt < t2.now_should_amt then t2.now_should_amt - t3.t14_fact_amt  
    when t3.t14_fact_amt is null then t2.t14_should_amt
end as T14_OVERDUE_AMOUNT
,case 
    when t3.t30_fact_amt >= t2.now_should_amt then 0 
    when t3.t30_fact_amt < t2.now_should_amt then t2.now_should_amt - t3.t30_fact_amt  
    when t3.t30_fact_amt is null then t2.t30_should_amt
end as T30_OVERDUE_AMOUNT
    ,case when t3.now_fact_amt - t2.now_should_amt >= -1 then 0 else 1 end IS_now_OVERDUE
    ,case when t3.t0_fact_amt - t2.now_should_amt >= -1 then 0 else 1 end IS_T0_OVERDUE
    ,case when t3.t3_fact_amt - t2.now_should_amt >= -1 then 0 else 1 end IS_T3_OVERDUE
    ,case when t3.t7_fact_amt - t2.now_should_amt >= -1 then 0 else 1 end IS_T7_OVERDUE
    ,case when t3.t14_fact_amt - t2.now_should_amt >= -1 then 0 else 1 end IS_T14_OVERDUE
    ,case when t3.t30_fact_amt - t2.now_should_amt >= -1 then 0 else 1 end IS_T30_OVERDUE
from ods_view_presto.s02_loan t1 
left join 
(--应还-合并到订单维度
    select 
        camera_id
        ,should_time
        ,should_capital
        ,should_interest
        ,should_fine
        ,case when date(should_time) < current_date then 1 else 0 end t0_should_num
        ,case when date(should_time) + interval '3' day < current_date then 1 else 0 end t3_should_num
        ,case when date(should_time) + interval '7' day < current_date then 1 else 0 end t7_should_num
        ,case when date(should_time) + interval '14' day < current_date then 1 else 0 end t14_should_num
        ,case when date(should_time) + interval '30' day < current_date then 1 else 0 end t30_should_num
        ,should_capital+should_interest now_should_amt
        ,case when date(should_time) < current_date then should_capital+should_interest end t0_should_amt
        ,case when date(should_time) + interval '3' day < current_date then should_capital + should_interest end t3_should_amt
        ,case when date(should_time) + interval '7' day < current_date then should_capital + should_interest end t7_should_amt
        ,case when date(should_time) + interval '14' day < current_date then should_capital + should_interest end t14_should_amt
        ,case when date(should_time) + interval '30' day < current_date then should_capital + should_interest end t30_should_amt
    from    
    (
        select
            a.camera_id
            ,sum(a.should_capital) should_capital
            ,sum(a.should_interest) should_interest 
            ,sum(a.should_fine) should_fine
            ,max(a.should_time) should_time
        from ods_view_presto.s02_loan_repayment a
        left join ods_view_presto.s02_loan b on a.camera_id = b.camera_id
        where b.state in (1,2,3)
        group by 1
    )
) t2 on t1.camera_id=t2.camera_id
left join
(--实还金额-合并到订单维度
    select
        a.camera_id
        ,sum(a.fact_capital) fact_capital
        ,sum(a.fact_interest) fact_interest
        ,sum(a.fact_fine) fact_fine
        ,sum(case when date_diff('day',date(a.fact_time),date(b.should_time))>2 then a.fact_capital + a.fact_interest else 0 end) as pre_p2_repay
        ,sum(case when date_diff('day',date(a.fact_time),date(b.should_time))=2 then a.fact_capital + a.fact_interest else 0 end) as p2_repay
        ,sum(case when date_diff('day',date(a.fact_time),date(b.should_time))>=2 then a.fact_capital + a.fact_interest else 0 end) as p2_repaytt
        ,sum(case when date_diff('day',date(a.fact_time),date(b.should_time))=1 then a.fact_capital + a.fact_interest else 0 end) as p1_repay
        ,sum(case when date_diff('day',date(a.fact_time),date(b.should_time))=0 then a.fact_capital + a.fact_interest else 0 end) as p0_repay
        ,sum(a.fact_capital + a.fact_interest) now_fact_amt
        ,sum(case when date(a.fact_time) <= date(b.should_time) then a.fact_capital + a.fact_interest end) t0_fact_amt
        ,sum(case when date(a.fact_time) <= interval '3' day + date(b.should_time) then a.fact_capital + a.fact_interest end) t3_fact_amt
        ,sum(case when date(a.fact_time) <= interval '7' day + date(b.should_time) then a.fact_capital + a.fact_interest end) t7_fact_amt
        ,sum(case when date(a.fact_time) <= interval '14' day + date(b.should_time) then a.fact_capital + a.fact_interest end) t14_fact_amt
        ,sum(case when date(a.fact_time) <= interval '30' day + date(b.should_time) then a.fact_capital + a.fact_interest end) t30_fact_amt
    from ods_view_presto.s02_loan_repayment_detail a
    left join (select camera_id, max(should_time) should_time,sum(coupon_amount) coupon_amount from ods_view_presto.s02_loan_repayment group by 1) b on a.camera_id = b.camera_id 
    group by 1
) t3 on t1.camera_id=t3.camera_id
left join (
  --- 订单在逾天数：对每一期算逾期天数然后取最大值
  select 
    camera_id,
    max(now_overdue_days) as now_overdue_days
  from (
  select camera_id,indexs,greatest(overdue_days,0) as now_overdue_days
  from (
  select camera_id,indexs,
    case when (should_capital + should_interest) = (fact_capital + fact_interest + subtract_capital + subtract_interest) 
              or state in (1,3,5) then 0
          else date_diff('day', date(should_time),current_date) end overdue_days
  from ods_view_presto.s02_loan_repayment) t0 ) t1 
  group by 1
) t4 on t1.camera_id=t4.camera_id
;  


--- 该表是旧逻辑 没有使用
-- drop table if exists mx.wxs_risk_2stage;
-- create table if not exists mx.wxs_risk_2stage as 
-- --分期贷后
-- select distinct
--     t1.camera_id
--     ,t1.indexs
--     ,t1.should_time
--     ,t1.should_capital
--     ,t1.should_interest
--     ,t1.should_fine
--     ,t1.fact_time
--     ,t1.fact_capital
--     ,t1.fact_fine
--     ,t1.fact_interest
--     ,t2.t0_should_amt
--     ,t2.t3_should_amt
--     ,t2.t7_should_amt
--     ,t2.t14_should_amt
--     ,t2.t30_should_amt
--     ,t3.now_fact_amt
--     ,t3.t0_fact_amt
--     ,t3.t3_fact_amt
--     ,t3.t7_fact_amt
--     ,t3.t14_fact_amt
--     ,t3.t30_fact_amt
--     ,t2.t0_should_num
--     ,t2.t3_should_num
--     ,t2.t7_should_num
--     ,t2.t14_should_num
--     ,t2.t30_should_num
--     ,case when t3.t0_fact_amt - t2.t0_should_amt >= -1 then 1 else 0 end t0_fact_num
--     ,case when t3.t3_fact_amt - t2.t3_should_amt >= -1 then 1 else 0 end t3_fact_num
--     ,case when t3.t7_fact_amt - t2.t7_should_amt >= -1 then 1 else 0 end t7_fact_num
--     ,case when t3.t14_fact_amt - t2.t14_should_amt >= -1 then 1 else 0 end t14_fact_num
--     ,case when t3.t30_fact_amt - t2.t30_should_amt >= -1 then 1 else 0 end t30_fact_num
--     ,case when date_diff('day',date(t1.should_time),CURRENT_DATE)>0 then 1 else 0 end as is_t0_window
--     ,case when date_diff('day',date(t1.should_time),CURRENT_DATE)>3 then 1 else 0 end as is_t3_window
--     ,case when date_diff('day',date(t1.should_time),CURRENT_DATE)>7 then 1 else 0 end as is_t7_window
--     ,case when date_diff('day',date(t1.should_time),CURRENT_DATE)>14 then 1 else 0 end as is_t14_window
--     ,case when date_diff('day',date(t1.should_time),CURRENT_DATE)>30 then 1 else 0 end as is_t30_window
--        ,case 
--     when t3.t0_fact_amt - t2.t0_should_amt >= -1 then 0 
--     when t3.t0_fact_amt < t2.t0_should_amt then t2.t0_should_amt - t3.t0_fact_amt  
--     when t3.t0_fact_amt is null then t2.t0_should_amt
-- end as T0_OVERDUE_AMOUNT
-- ,case 
--     when t3.t3_fact_amt - t2.t3_should_amt >= -1 then 0 
--     when t3.t3_fact_amt < t2.t3_should_amt then t2.t3_should_amt - t3.t3_fact_amt  
--     when t3.t3_fact_amt is null then t2.t3_should_amt
-- end as T3_OVERDUE_AMOUNT
-- ,case 
--     when t3.t7_fact_amt - t2.t7_should_amt >= -1 then 0 
--     when t3.t7_fact_amt < t2.t7_should_amt then t2.t7_should_amt - t3.t7_fact_amt  
--     when t3.t7_fact_amt is null then t2.t7_should_amt
-- end as T7_OVERDUE_AMOUNT
-- ,case 
--     when t3.t14_fact_amt - t2.t14_should_amt >= -1 then 0 
--     when t3.t14_fact_amt < t2.t14_should_amt then t2.t14_should_amt - t3.t14_fact_amt  
--     when t3.t14_fact_amt is null then t2.t14_should_amt
-- end as T14_OVERDUE_AMOUNT
-- ,case 
--     when t3.t30_fact_amt - t2.t30_should_amt >= -1 then 0 
--     when t3.t30_fact_amt < t2.t30_should_amt then t2.t30_should_amt - t3.t30_fact_amt  
--     when t3.t30_fact_amt is null then t2.t30_should_amt
-- end as T30_OVERDUE_AMOUNT
-- ,case when t3.t0_fact_amt - t2.t0_should_amt >= -1 then 0 else 1 end IS_T0_OVERDUE
-- ,case when t3.t3_fact_amt - t2.t3_should_amt >= -1 then 0 else 1 end IS_T3_OVERDUE
-- ,case when t3.t7_fact_amt - t2.t7_should_amt >= -1 then 0 else 1 end IS_T7_OVERDUE
-- ,case when t3.t14_fact_amt - t2.t14_should_amt >= -1 then 0 else 1 end IS_T14_OVERDUE
-- ,case when t3.t30_fact_amt - t2.t30_should_amt >= -1 then 0 else 1 end IS_T30_OVERDUE
--     ,case 
--         when (t1.should_capital + t1.should_interest) = (t1.fact_capital + t1.fact_interest + t1.subtract_capital + t1.subtract_interest) 
--             or t1.state in (1,3,5) then date_diff('day', date(t1.should_time),date(t1.fact_time)) 
--         else date_diff('day', date(t1.should_time),current_date) end overdue_days
-- from ods_view_presto.s02_loan_repayment t1 
-- left join 
-- (--应还
--     select 
--         a.camera_id
--         ,a.indexs
--         -- ,case 
--         --     when a.state = 1 then day(date(a.fact_time) - date(a.should_time)) --正常还款
--         --     when a.state in (3,5) or (a.state = 6 and a.should_capital <= a.fact_fine + a.fact_capital) then day(date(a.fact_time) - date(a.should_time)) --逾期后还款/部分还款后结清/手动核销
--         --     else day(current_date-date(a.should_time)) end as ovd_days
--         -- ,day(current_date - date(c.should_time)) diff_days
--         ,case when date(a.should_time) < current_date then 1 else 0 end t0_should_num
--         ,case when date(a.should_time) + interval '3' day < current_date then 1 else 0 end t3_should_num
--         ,case when date(a.should_time) + interval '7' day < current_date then 1 else 0 end t7_should_num
--         ,case when date(a.should_time) + interval '14' day < current_date then 1 else 0 end t14_should_num
--         ,case when date(a.should_time) + interval '30' day < current_date then 1 else 0 end t30_should_num
--         ,sum(case when date(a.should_time) < current_date then a.should_capital + a.should_interest end) t0_should_amt
--         ,sum(case when date(a.should_time) + interval '3' day < current_date then a.should_capital + a.should_interest end) t3_should_amt
--         ,sum(case when date(a.should_time) + interval '7' day < current_date then a.should_capital + a.should_interest end) t7_should_amt
--         ,sum(case when date(a.should_time) + interval '14' day < current_date then a.should_capital + a.should_interest end) t14_should_amt
--         ,sum(case when date(a.should_time) + interval '30' day < current_date then a.should_capital + a.should_interest end) t30_should_amt
--     from ods_view_presto.s02_loan_repayment a
--     left join ods_view_presto.s02_loan b on a.camera_id = b.camera_id
--     where b.state in (1,2,3)     
--     group by 1,2,3,4,5,6,7
-- ) t2 on t1.camera_id = t2.camera_id and t1.indexs = t2.indexs
-- left join 
-- (--实还
--     select
--         a.camera_id
--         ,b.indexs
--         ,sum(a.fact_capital + a.fact_interest) now_fact_amt
--         ,sum(case when date(a.fact_time) <= date(b.should_time) and date(b.should_time) < current_date then a.fact_capital + a.fact_interest end) t0_fact_amt
--         ,sum(case when date(a.fact_time) <= interval '3' day + date(b.should_time) and date(b.should_time) + interval '3' day < current_date then a.fact_capital + a.fact_interest end) t3_fact_amt
--         ,sum(case when date(a.fact_time) <= interval '7' day + date(b.should_time) and date(b.should_time) + interval '7' day < current_date then a.fact_capital + a.fact_interest end) t7_fact_amt
--         ,sum(case when date(a.fact_time) <= interval '14' day + date(b.should_time) and date(b.should_time) + interval '14' day < current_date then a.fact_capital + a.fact_interest end) t14_fact_amt
--         ,sum(case when date(a.fact_time) <= interval '30' day + date(b.should_time) and date(b.should_time) + interval '30' day < current_date then a.fact_capital + a.fact_interest end) t30_fact_amt
--     from ods_view_presto.s02_loan_repayment_detail a
--     left join ods_view_presto.s02_loan_repayment b on a.camera_id = b.camera_id and a.rid = b.rid
--     group by 1,2
-- ) t3 on t1.camera_id = t3.camera_id and t1.indexs = t3.indexs
-- ;

  
  

--悲观逾期口径
drop table if exists mx.wxs_vintage_all1;
create table mx.wxs_vintage_all1 as
	select 
		ceil(lr.camera_id) camera_id
		, date(should_time) should_date 
		, date(fact_time) fact_date
		, loan_indexs
    , lr.state
	from ods_view_presto.s02_loan_repayment lr
	left join ods_view_presto.s02_loan l 
		on l.camera_id = lr.camera_id
	where lr.indexs = loan_indexs
;



drop table if exists mx.wxs_vintage_all2;
create table mx.wxs_vintage_all2 as
	select 
		ceil(camera_id) camera_id
		, indexs
		, date(should_time) should_date 
		, date(fact_time) fact_date
    , state
	from ods_view_presto.s02_loan_repayment
  union all
	select camera_id, 2 indexs , should_date, fact_date, state from mx.wxs_vintage_all1 where loan_indexs < 2
	union all
	select camera_id, 3 indexs , should_date, fact_date, state from mx.wxs_vintage_all1 where loan_indexs < 3
	union all
	select camera_id, 4 indexs , should_date, fact_date, state from mx.wxs_vintage_all1 where loan_indexs < 4
	union all
	select camera_id, 5 indexs , should_date, fact_date, state from mx.wxs_vintage_all1 where loan_indexs < 5	
	union all
	select camera_id, 6 indexs , should_date, fact_date, state from mx.wxs_vintage_all1 where loan_indexs < 6
	union all
	select camera_id, 7 indexs , should_date, fact_date, state from mx.wxs_vintage_all1 where loan_indexs < 7
	union all
	select camera_id, 8 indexs , should_date, fact_date, state from mx.wxs_vintage_all1 where loan_indexs < 8
	union all
	select camera_id, 9 indexs , should_date, fact_date, state from mx.wxs_vintage_all1 where loan_indexs < 9
	union all
	select camera_id, 10 indexs , should_date, fact_date, state from mx.wxs_vintage_all1 where loan_indexs < 10
;



drop table if exists mx.wxs_vintage_all3;
create table mx.wxs_vintage_all3 as
select 
    camera_id as id
    , r.should_date 
		, r.indexs
    , if(state in (1,3,5), 1, 0) clear_now_flag 
		, if(date_diff('day', r.should_date, current_date) > -3,1,0) duem3_flag 
		, if(date_diff('day', r.should_date, if(state in (0,2,4), current_date, r.fact_date)) > -3, 1, 0) ovdm3_flag 
		, if(date_diff('day', r.should_date, current_date) > -2,1,0) duem2_flag 
		, if(date_diff('day', r.should_date, if(state in (0,2,4), current_date, r.fact_date)) > -2, 1, 0) ovdm2_flag 
		, if(date_diff('day', r.should_date, current_date) > -1,1,0) duem1_flag 
		, if(date_diff('day', r.should_date, if(state in (0,2,4), current_date, r.fact_date)) > -1, 1, 0) ovdm1_flag 
		, if(date_diff('day', r.should_date, current_date) > 0,1,0) due0_flag 
		, if(date_diff('day', r.should_date, if(state in (0,2,4), current_date, r.fact_date)) > 0, 1, 0) ovd0_flag 
		, if(date_diff('day', r.should_date, current_date) > 1,1,0) due1_flag 
		, if(date_diff('day', r.should_date, if(state in (0,2,4), current_date, r.fact_date)) > 1, 1, 0) ovd1_flag 
		, if(date_diff('day', r.should_date, current_date) > 2,1,0) due2_flag 
		, if(date_diff('day', r.should_date, if(state in (0,2,4), current_date, r.fact_date)) > 2, 1, 0) ovd2_flag 
		, if(date_diff('day', r.should_date, current_date) > 3,1,0) due3_flag 
		, if(date_diff('day', r.should_date, if(state in (0,2,4), current_date, r.fact_date)) > 3, 1, 0) ovd3_flag 
		, if(date_diff('day', r.should_date, current_date) > 7,1,0) due7_flag 
		, if(date_diff('day', r.should_date, if(state in (0,2,4), current_date, r.fact_date)) > 7, 1, 0) ovd7_flag 
		, if(date_diff('day', r.should_date, current_date) > 30,1,0) due30_flag 
		, if(date_diff('day', r.should_date, if(state in (0,2,4), current_date, r.fact_date)) > 30, 1, 0) ovd30_flag 
    from mx.wxs_vintage_all2 r 
	  -- where if_issue = 1 
    -- and app_date > '2024-01-01'
;



drop table if exists mx.wxs_vintage_all31;
create table mx.wxs_vintage_all31 as
select 
  id 
  ,indexs
	-- , sum(should_capital_p1*1.0/10000) as should_capital_p1
	-- , sum(apply_amount*interval_start*1.0/10000) as app_cycle_amount 
	-- , sum(apply_amount*1.0/10000) as app_amount
  , sum(repay_tm3_amt_all) repay_tm3_amt_all 
	, sum(repay_tm2_amt_all) repay_tm2_amt_all
 	, sum(repay_tm1_amt_all) repay_tm1_amt_all 
	, sum(repay_t0_amt_all) repay_t0_amt_all 
  
  , sum(clear_now_flag) clear_now_cnt 

	, sum(duem3_flag) duem3_cnt 
	, sum(ovdm3_flag) ovdm3_cnt 
	, sum(if(duem3_flag = 1, should_capital,0)) duem3_amount 
	, sum(case when repay_tm3_coupon_all>0 then repay_tm3_coupon_all when ovdm3_flag = 1 then should_capital - repay_tm3_amt_all else 0 end) ovdm3_amount 

  , sum(duem2_flag) duem2_cnt 
	, sum(ovdm2_flag) ovdm2_cnt 
	, sum(if(duem2_flag = 1, should_capital,0)) duem2_amount 
	, sum(case when repay_tm2_coupon_all>0 then repay_tm2_coupon_all when ovdm2_flag = 1 then should_capital - repay_tm2_amt_all else 0 end) ovdm2_amount 
  
  , sum(duem1_flag) duem1_cnt 
	, sum(ovdm1_flag) ovdm1_cnt 
	, sum(if(duem1_flag = 1, should_capital,0)) duem1_amount 
	, sum(case when repay_tm1_coupon_all>0 then repay_tm1_coupon_all when ovdm1_flag = 1 then should_capital - repay_tm1_amt_all else 0 end) ovdm1_amount 
  
	, sum(due0_flag) due0_cnt 
	, sum(ovd0_flag) ovd0_cnt 
	, sum(if(due0_flag = 1, should_capital,0)) due0_amount 
	, sum(case when repay_t0_coupon_all>0 then repay_t0_coupon_all when ovd0_flag = 1 then should_capital - repay_t0_amt_all else 0 end) ovd0_amount 
	, sum(if(due0_flag = 1, should_interest,0)) due0_interest 
	, sum(case when repay_t0_coupon_all>0 then repay_t0_coupon_all when ovd0_flag = 1 then should_interest - repay_t0_amt_all_int else 0 end) ovd0_interest

	, sum(due1_flag) due1_cnt 
	, sum(ovd1_flag) ovd1_cnt 
	, sum(if(due1_flag = 1, should_capital,0)) due1_amount 
	, sum(case when repay_t1_coupon_all>0 then repay_t1_coupon_all when ovd1_flag = 1 then should_capital - repay_t1_amt_all else 0 end) ovd1_amount 
	, sum(if(due1_flag = 1, should_interest,0)) due1_interest 
	, sum(case when repay_t1_coupon_all>0 then repay_t1_coupon_all when ovd1_flag = 1 then should_interest - repay_t1_amt_all_int else 0 end) ovd1_interest
  
  , sum(due2_flag) due2_cnt 
	, sum(ovd2_flag) ovd2_cnt 
	, sum(if(due2_flag = 1, should_capital,0)) due2_amount 
	, sum(case when repay_t2_coupon_all>0 then repay_t2_coupon_all when ovd2_flag = 1 then should_capital - repay_t2_amt_all else 0 end) ovd2_amount 
	, sum(if(due2_flag = 1, should_interest,0)) due2_interest 
	, sum(case when repay_t2_coupon_all>0 then repay_t2_coupon_all when ovd2_flag = 1 then should_interest - repay_t2_amt_all_int else 0 end) ovd2_interest
  
  , sum(due3_flag) due3_cnt 
	, sum(ovd3_flag) ovd3_cnt 
	, sum(if(due3_flag = 1, should_capital,0)) due3_amount 
	, sum(case when repay_t3_coupon_all>0 then repay_t3_coupon_all when ovd3_flag = 1 then should_capital - repay_t3_amt_all else 0 end) ovd3_amount 
	, sum(if(due3_flag = 1, should_interest,0)) due3_interest 
	, sum(case when repay_t3_coupon_all>0 then repay_t3_coupon_all when ovd3_flag = 1 then should_interest - repay_t3_amt_all_int else 0 end) ovd3_interest
  
	, sum(due7_flag) due7_cnt 
	, sum(ovd7_flag) ovd7_cnt 
	, sum(if(due7_flag = 1, should_capital,0)) due7_amount 
	, sum(case when repay_t7_coupon_all>0 then repay_t7_coupon_all when ovd7_flag = 1 then should_capital - repay_t7_amt_all else 0 end) ovd7_amount 
	, sum(if(due7_flag = 1, should_interest,0)) due7_interest 
	, sum(case when repay_t7_coupon_all>0 then repay_t7_coupon_all when ovd7_flag = 1 then should_interest - repay_t7_amt_all_int else 0 end) ovd7_interest

	, sum(due30_flag) due30_cnt 
	, sum(ovd30_flag) ovd30_cnt 
	, sum(if(due30_flag = 1, should_capital,0)) due30_amount 
	, sum(case when repay_t30_coupon_all>0 then repay_t30_coupon_all when ovd30_flag = 1 then should_capital - repay_t30_amt_all else 0 end) ovd30_amount 
	, sum(if(due30_flag = 1, should_interest,0)) due30_interest 
	, sum(case when repay_t30_coupon_all>0 then repay_t30_coupon_all when ovd30_flag = 1 then should_interest - repay_t30_amt_all_int else 0 end) ovd30_interest
  
  --应还本金
  ,sum(if(due0_flag = 1, should_capit,0)) due0_capit
  ,sum(if(due1_flag = 1, should_capit,0)) due1_capit
  ,sum(if(due2_flag = 1, should_capit,0)) due2_capit
  ,sum(if(due3_flag = 1, should_capit,0)) due3_capit
  ,sum(if(due7_flag = 1, should_capit,0)) due7_capit
  ,sum(if(due30_flag = 1, should_capit,0)) due30_capit
--逾期本金
, sum(case when repay_t0_coupon_all>0 then repay_t0_coupon_all when ovd0_flag = 1 then should_capit - repay_t0_cap_all else 0 end) ovd0_capit
, sum(case when repay_t1_coupon_all>0 then repay_t1_coupon_all when ovd1_flag = 1 then should_capit - repay_t1_cap_all else 0 end) ovd1_capit
, sum(case when repay_t2_coupon_all>0 then repay_t2_coupon_all when ovd2_flag = 1 then should_capit - repay_t2_cap_all else 0 end) ovd2_capit
, sum(case when repay_t3_coupon_all>0 then repay_t3_coupon_all when ovd3_flag = 1 then should_capit - repay_t3_cap_all else 0 end) ovd3_capit
, sum(case when repay_t7_coupon_all>0 then repay_t7_coupon_all when ovd7_flag = 1 then should_capit - repay_t7_cap_all else 0 end) ovd7_capit
, sum(case when repay_t30_coupon_all>0 then repay_t30_coupon_all when ovd30_flag = 1 then should_capit - repay_t30_cap_all else 0 end) ovd30_capit

from
(
	select 
		t1.* 
    ,r.should_capital
    ,r.should_interest
    ,r.should_capit
    , sum(case when date_diff('day', should_date, date(rd.fact_time)) <= -3 then rd.fact_capital + rd.fact_interest else 0 end) repay_tm3_amt_all
    , sum(case when date_diff('day', should_date, date(rd.fact_time)) <= -2 then rd.fact_capital + rd.fact_interest else 0 end) repay_tm2_amt_all
    , sum(case when date_diff('day', should_date, date(rd.fact_time)) <= -1 then rd.fact_capital + rd.fact_interest else 0 end) repay_tm1_amt_all
		, sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 0 then rd.fact_capital + rd.fact_interest else 0 end) repay_t0_amt_all 
		, sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 1 then rd.fact_capital + rd.fact_interest else 0 end) repay_t1_amt_all 
		, sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 2 then rd.fact_capital + rd.fact_interest else 0 end) repay_t2_amt_all 
		, sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 3 then rd.fact_capital + rd.fact_interest else 0 end) repay_t3_amt_all 
		, sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 7 then rd.fact_capital + rd.fact_interest else 0 end) repay_t7_amt_all 
		, sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 30 then rd.fact_capital + rd.fact_interest else 0 end) repay_t30_amt_all 
    , max(case when date_diff('day', should_date, date(rd.fact_time)) <= -3 then r1.coupon_amount else 0 end) repay_tm3_coupon_all 
    , max(case when date_diff('day', should_date, date(rd.fact_time)) <= -2 then r1.coupon_amount else 0 end) repay_tm2_coupon_all 
    , max(case when date_diff('day', should_date, date(rd.fact_time)) <= -1 then r1.coupon_amount else 0 end) repay_tm1_coupon_all 
    , max(case when date_diff('day', should_date, date(rd.fact_time)) <= 0 then r1.coupon_amount else 0 end) repay_t0_coupon_all 
		, max(case when date_diff('day', should_date, date(rd.fact_time)) <= 1 then r1.coupon_amount else 0 end) repay_t1_coupon_all 
		, max(case when date_diff('day', should_date, date(rd.fact_time)) <= 2 then r1.coupon_amount else 0 end) repay_t2_coupon_all 
		, max(case when date_diff('day', should_date, date(rd.fact_time)) <= 3 then r1.coupon_amount else 0 end) repay_t3_coupon_all 
		, max(case when date_diff('day', should_date, date(rd.fact_time)) <= 7 then r1.coupon_amount else 0 end) repay_t7_coupon_all 
		, max(case when date_diff('day', should_date, date(rd.fact_time)) <= 30 then r1.coupon_amount else 0 end) repay_t30_coupon_all 
		, sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 0 then rd.fact_interest else 0 end) repay_t0_amt_all_int
    , sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 1 then rd.fact_interest else 0 end) repay_t1_amt_all_int
    , sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 2 then rd.fact_interest else 0 end) repay_t2_amt_all_int
    , sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 3 then rd.fact_interest else 0 end) repay_t3_amt_all_int
		, sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 7 then rd.fact_interest else 0 end) repay_t7_amt_all_int 
		, sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 30 then rd.fact_interest else 0 end) repay_t30_amt_all_int 
    --实还本金
    , sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 0 then rd.fact_capital else 0 end) repay_t0_cap_all 
    , sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 1 then rd.fact_capital else 0 end) repay_t1_cap_all 
    , sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 2 then rd.fact_capital else 0 end) repay_t2_cap_all 
    , sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 3 then rd.fact_capital else 0 end) repay_t3_cap_all 
    , sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 7 then rd.fact_capital else 0 end) repay_t7_cap_all 
    , sum(case when date_diff('day', should_date, date(rd.fact_time)) <= 30 then rd.fact_capital else 0 end) repay_t30_cap_all 
	from mx.wxs_vintage_all3 t1 
  -- left join (select camera_id,sum(should_capital) + sum(should_interest) should_capital,sum(should_interest) should_interest,sum(coupon_amount) coupon_amount from ods_view_presto.s02_loan_repayment group by 1) r on r.camera_id = t1.id 
  left join (select camera_id,sum(should_capital) + sum(should_interest) should_capital,sum(should_capital) should_capit, sum(should_interest) should_interest from ods_view_presto.s02_loan_repayment group by 1) r on r.camera_id = t1.id 
  left join (select camera_id,indexs,sum(coupon_amount) coupon_amount from ods_view_presto.s02_loan_repayment group by 1,2) r1 on r1.camera_id = t1.id and t1.indexs=r1.indexs
	left join ods_view_presto.s02_loan_repayment_detail rd on rd.camera_id = t1.id 
	group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25
) o
group by 1,2
;





drop table if exists mx.wxs_vintage_all4;
create table mx.wxs_vintage_all4 as

select 
  id 
  , max(if(indexs=1 and clear_now_cnt=0,1,0)) overdue_cnt_1_now 

  , sum(if(indexs=1, duem3_cnt, 0)) should_cnt_1_pre3 
  , sum(if(indexs=1, ovdm3_cnt, 0)) overdue_cnt_1_pre3 
  , sum(if(indexs=1, duem3_amount, 0)) should_capital_1_pre3   
  , sum(if(indexs=1, ovdm3_amount, 0)) overdue_amount_1_pre3 
  , sum(if(indexs=1, duem2_cnt, 0)) should_cnt_1_pre2
  , sum(if(indexs=1, ovdm2_cnt, 0)) overdue_cnt_1_pre2  
  , sum(if(indexs=1, duem2_amount, 0)) should_capital_1_pre2
  , sum(if(indexs=1, ovdm2_amount, 0)) overdue_amount_1_pre2
  , sum(if(indexs=1, duem1_cnt, 0)) should_cnt_1_pre1 
  , sum(if(indexs=1, ovdm1_cnt, 0)) overdue_cnt_1_pre1 
  , sum(if(indexs=1, duem1_amount, 0)) should_capital_1_pre1  
  , sum(if(indexs=1, ovdm1_amount, 0)) overdue_amount_1_pre1 

  , sum(if(indexs=1, repay_tm3_amt_all, 0)) pre_repay_tm3_amt_1
	, sum(if(indexs=1, repay_tm2_amt_all, 0)) pre_repay_tm2_amt_1
 	, sum(if(indexs=1, repay_tm1_amt_all, 0)) pre_repay_tm1_amt_1 
	, sum(if(indexs=1, repay_t0_amt_all, 0)) pre_repay_tm0_amt_1 

  , sum(if(indexs=1, due0_cnt, 0)) should_cnt_1_0 
  , sum(if(indexs=1, ovd0_cnt, 0)) overdue_cnt_1_0 
  , sum(if(indexs=1, due0_amount, 0)) should_capital_1_0 
  , sum(if(indexs=1, ovd0_amount, 0)) overdue_amount_1_0 
  , sum(if(indexs=1, due1_cnt, 0)) should_cnt_1_1 
  , sum(if(indexs=1, ovd1_cnt, 0)) overdue_cnt_1_1 
  , sum(if(indexs=1, due1_amount, 0)) should_capital_1_1 
  , sum(if(indexs=1, ovd1_amount, 0)) overdue_amount_1_1 
  , sum(if(indexs=1, due2_cnt, 0)) should_cnt_1_2 
  , sum(if(indexs=1, ovd2_cnt, 0)) overdue_cnt_1_2 
  , sum(if(indexs=1, due2_amount, 0)) should_capital_1_2 
  , sum(if(indexs=1, ovd2_amount, 0)) overdue_amount_1_2 
  , sum(if(indexs=1, due3_cnt, 0)) should_cnt_1_3 
  , sum(if(indexs=1, ovd3_cnt, 0)) overdue_cnt_1_3 
  , sum(if(indexs=1, due3_amount, 0)) should_capital_1_3 
  , sum(if(indexs=1, ovd3_amount, 0)) overdue_amount_1_3 
  , sum(if(indexs=1, due7_cnt, 0)) should_cnt_1_7 
  , sum(if(indexs=1, ovd7_cnt, 0)) overdue_cnt_1_7 
  , sum(if(indexs=1, due7_amount, 0)) should_capital_1_7 
  , sum(if(indexs=1, ovd7_amount, 0)) overdue_amount_1_7 
  , sum(if(indexs=1, due30_cnt, 0)) should_cnt_1_30
  , sum(if(indexs=1, ovd30_cnt, 0)) overdue_cnt_1_30
  , sum(if(indexs=1, due30_amount, 0)) should_capital_1_30
  , sum(if(indexs=1, ovd30_amount, 0)) overdue_amount_1_30

  , sum(if(indexs=2, due0_cnt, 0)) should_cnt_2_0 
  , sum(if(indexs=2, ovd0_cnt, 0)) overdue_cnt_2_0 
  , sum(if(indexs=2, due0_amount, 0)) should_capital_2_0 
  , sum(if(indexs=2, ovd0_amount, 0)) overdue_amount_2_0 
  , sum(if(indexs=2, due1_cnt, 0)) should_cnt_2_1 
  , sum(if(indexs=2, ovd1_cnt, 0)) overdue_cnt_2_1 
  , sum(if(indexs=2, due1_amount, 0)) should_capital_2_1 
  , sum(if(indexs=2, ovd1_amount, 0)) overdue_amount_2_1 
  , sum(if(indexs=2, due2_cnt, 0)) should_cnt_2_2
  , sum(if(indexs=2, ovd2_cnt, 0)) overdue_cnt_2_2 
  , sum(if(indexs=2, due2_amount, 0)) should_capital_2_2 
  , sum(if(indexs=2, ovd2_amount, 0)) overdue_amount_2_2 
  , sum(if(indexs=2, due3_cnt, 0)) should_cnt_2_3
  , sum(if(indexs=2, ovd3_cnt, 0)) overdue_cnt_2_3 
  , sum(if(indexs=2, due3_amount, 0)) should_capital_2_3 
  , sum(if(indexs=2, ovd3_amount, 0)) overdue_amount_2_3 
  , sum(if(indexs=2, due7_cnt, 0)) should_cnt_2_7 
  , sum(if(indexs=2, ovd7_cnt, 0)) overdue_cnt_2_7 
  , sum(if(indexs=2, due7_amount, 0)) should_capital_2_7 
  , sum(if(indexs=2, ovd7_amount, 0)) overdue_amount_2_7 
  , sum(if(indexs=2, due30_cnt, 0)) should_cnt_2_30
  , sum(if(indexs=2, ovd30_cnt, 0)) overdue_cnt_2_30
  , sum(if(indexs=2, due30_amount, 0)) should_capital_2_30
  , sum(if(indexs=2, ovd30_amount, 0)) overdue_amount_2_30

  , sum(if(indexs=3, due0_cnt, 0)) should_cnt_3_0 
  , sum(if(indexs=3, ovd0_cnt, 0)) overdue_cnt_3_0 
  , sum(if(indexs=3, due0_amount, 0)) should_capital_3_0 
  , sum(if(indexs=3, ovd0_amount, 0)) overdue_amount_3_0 
  , sum(if(indexs=3, due1_cnt, 0)) should_cnt_3_1 
  , sum(if(indexs=3, ovd1_cnt, 0)) overdue_cnt_3_1 
  , sum(if(indexs=3, due1_amount, 0)) should_capital_3_1 
  , sum(if(indexs=3, ovd1_amount, 0)) overdue_amount_3_1 
  , sum(if(indexs=3, due2_cnt, 0)) should_cnt_3_2 
  , sum(if(indexs=3, ovd2_cnt, 0)) overdue_cnt_3_2 
  , sum(if(indexs=3, due2_amount, 0)) should_capital_3_2 
  , sum(if(indexs=3, ovd2_amount, 0)) overdue_amount_3_2 
  , sum(if(indexs=3, due3_cnt, 0)) should_cnt_3_3 
  , sum(if(indexs=3, ovd3_cnt, 0)) overdue_cnt_3_3 
  , sum(if(indexs=3, due3_amount, 0)) should_capital_3_3 
  , sum(if(indexs=3, ovd3_amount, 0)) overdue_amount_3_3 
  , sum(if(indexs=3, due3_cnt, 0)) should_cnt_3_7 
  , sum(if(indexs=3, ovd7_cnt, 0)) overdue_cnt_3_7 
  , sum(if(indexs=3, due7_amount, 0)) should_capital_3_7 
  , sum(if(indexs=3, ovd7_amount, 0)) overdue_amount_3_7 
  , sum(if(indexs=3, due30_cnt, 0)) should_cnt_3_30
  , sum(if(indexs=3, ovd30_cnt, 0)) overdue_cnt_3_30
  , sum(if(indexs=3, due30_amount, 0)) should_capital_3_30
  , sum(if(indexs=3, ovd30_amount, 0)) overdue_amount_3_30

  , sum(if(indexs=4, due0_cnt, 0)) should_cnt_4_0 
  , sum(if(indexs=4, ovd0_cnt, 0)) overdue_cnt_4_0 
  , sum(if(indexs=4, due0_amount, 0)) should_capital_4_0 
  , sum(if(indexs=4, ovd0_amount, 0)) overdue_amount_4_0
  , sum(if(indexs=4, due1_cnt, 0)) should_cnt_4_1 
  , sum(if(indexs=4, ovd1_cnt, 0)) overdue_cnt_4_1 
  , sum(if(indexs=4, due1_amount, 0)) should_capital_4_1 
  , sum(if(indexs=4, ovd1_amount, 0)) overdue_amount_4_1 
  , sum(if(indexs=4, due2_cnt, 0)) should_cnt_4_2 
  , sum(if(indexs=4, ovd2_cnt, 0)) overdue_cnt_4_2 
  , sum(if(indexs=4, due2_amount, 0)) should_capital_4_2 
  , sum(if(indexs=4, ovd2_amount, 0)) overdue_amount_4_2 
  , sum(if(indexs=4, due3_cnt, 0)) should_cnt_4_3 
  , sum(if(indexs=4, ovd3_cnt, 0)) overdue_cnt_4_3 
  , sum(if(indexs=4, due3_amount, 0)) should_capital_4_3 
  , sum(if(indexs=4, ovd3_amount, 0)) overdue_amount_4_3 
  , sum(if(indexs=4, due7_cnt, 0)) should_cnt_4_7 
  , sum(if(indexs=4, ovd7_cnt, 0)) overdue_cnt_4_7 
  , sum(if(indexs=4, due7_amount, 0)) should_capital_4_7 
  , sum(if(indexs=4, ovd7_amount, 0)) overdue_amount_4_7 
  , sum(if(indexs=4, due30_cnt, 0)) should_cnt_4_30
  , sum(if(indexs=4, ovd30_cnt, 0)) overdue_cnt_4_30
  , sum(if(indexs=4, due30_amount, 0)) should_capital_4_30
  , sum(if(indexs=4, ovd30_amount, 0)) overdue_amount_4_30


  -- interest
  , sum(if(indexs=1, due0_interest, 0)) should_interest_1_0 
  , sum(if(indexs=1, ovd0_interest, 0)) overdue_interest_1_0 
  , sum(if(indexs=1, due1_interest, 0)) should_interest_1_1 
  , sum(if(indexs=1, ovd1_interest, 0)) overdue_interest_1_1 
  , sum(if(indexs=1, due2_interest, 0)) should_interest_1_2 
  , sum(if(indexs=1, ovd2_interest, 0)) overdue_interest_1_2 
  , sum(if(indexs=1, due3_interest, 0)) should_interest_1_3 
  , sum(if(indexs=1, ovd3_interest, 0)) overdue_interest_1_3 
  , sum(if(indexs=1, due7_interest, 0)) should_interest_1_7 
  , sum(if(indexs=1, ovd7_interest, 0)) overdue_interest_1_7 
  , sum(if(indexs=1, due30_interest, 0)) should_interest_1_30 
  , sum(if(indexs=1, ovd30_interest, 0)) overdue_interest_1_30 
  
  , sum(if(indexs=2, due0_interest, 0)) should_interest_2_0 
  , sum(if(indexs=2, ovd0_interest, 0)) overdue_interest_2_0 
  , sum(if(indexs=2, due1_interest, 0)) should_interest_2_1 
  , sum(if(indexs=2, ovd1_interest, 0)) overdue_interest_2_1 
  , sum(if(indexs=2, due2_interest, 0)) should_interest_2_2 
  , sum(if(indexs=2, ovd2_interest, 0)) overdue_interest_2_2 
  , sum(if(indexs=2, due3_interest, 0)) should_interest_2_3 
  , sum(if(indexs=2, ovd3_interest, 0)) overdue_interest_2_3 
  , sum(if(indexs=2, due7_interest, 0)) should_interest_2_7 
  , sum(if(indexs=2, ovd7_interest, 0)) overdue_interest_2_7 
  , sum(if(indexs=2, due30_interest, 0)) should_interest_2_30 
  , sum(if(indexs=2, ovd30_interest, 0)) overdue_interest_2_30 
  
  , sum(if(indexs=3, due0_interest, 0)) should_interest_3_0 
  , sum(if(indexs=3, ovd0_interest, 0)) overdue_interest_3_0 
  , sum(if(indexs=3, due1_interest, 0)) should_interest_3_1 
  , sum(if(indexs=3, ovd1_interest, 0)) overdue_interest_3_1 
  , sum(if(indexs=3, due2_interest, 0)) should_interest_3_2 
  , sum(if(indexs=3, ovd2_interest, 0)) overdue_interest_3_2 
  , sum(if(indexs=3, due3_interest, 0)) should_interest_3_3 
  , sum(if(indexs=3, ovd3_interest, 0)) overdue_interest_3_3 
  , sum(if(indexs=3, due7_interest, 0)) should_interest_3_7 
  , sum(if(indexs=3, ovd7_interest, 0)) overdue_interest_3_7 
  , sum(if(indexs=3, due30_interest, 0)) should_interest_3_30 
  , sum(if(indexs=3, ovd30_interest, 0)) overdue_interest_3_30 
  
  , sum(if(indexs=4, due0_interest, 0)) should_interest_4_0 
  , sum(if(indexs=4, ovd0_interest, 0)) overdue_interest_4_0 
  , sum(if(indexs=4, due1_interest, 0)) should_interest_4_1 
  , sum(if(indexs=4, ovd1_interest, 0)) overdue_interest_4_1 
  , sum(if(indexs=4, due2_interest, 0)) should_interest_4_2 
  , sum(if(indexs=4, ovd2_interest, 0)) overdue_interest_4_2 
  , sum(if(indexs=4, due3_interest, 0)) should_interest_4_3 
  , sum(if(indexs=4, ovd3_interest, 0)) overdue_interest_4_3 
  , sum(if(indexs=4, due7_interest, 0)) should_interest_4_7 
  , sum(if(indexs=4, ovd7_interest, 0)) overdue_interest_4_7 
  , sum(if(indexs=4, due30_interest, 0)) should_interest_4_30 
  , sum(if(indexs=4, ovd30_interest, 0)) overdue_interest_4_30 
--应还本金
,sum(if(indexs=1, due0_capit, 0)) should_capit_1_0
, sum(if(indexs=2, due0_capit, 0)) should_capit_2_0
, sum(if(indexs=3, due0_capit, 0)) should_capit_3_0
, sum(if(indexs=4, due0_capit, 0)) should_capit_4_0
, sum(if(indexs=1, due1_capit, 0)) should_capit_1_1
, sum(if(indexs=2, due1_capit, 0)) should_capit_2_1
, sum(if(indexs=3, due1_capit, 0)) should_capit_3_1
, sum(if(indexs=4, due1_capit, 0)) should_capit_4_1
, sum(if(indexs=1, due2_capit, 0)) should_capit_1_2
, sum(if(indexs=2, due2_capit, 0)) should_capit_2_2
, sum(if(indexs=3, due2_capit, 0)) should_capit_3_2
, sum(if(indexs=4, due2_capit, 0)) should_capit_4_2
, sum(if(indexs=1, due3_capit, 0)) should_capit_1_3
, sum(if(indexs=2, due3_capit, 0)) should_capit_2_3
, sum(if(indexs=3, due3_capit, 0)) should_capit_3_3
, sum(if(indexs=4, due3_capit, 0)) should_capit_4_3
, sum(if(indexs=1, due7_capit, 0)) should_capit_1_7
, sum(if(indexs=2, due7_capit, 0)) should_capit_2_7
, sum(if(indexs=3, due7_capit, 0)) should_capit_3_7
, sum(if(indexs=4, due7_capit, 0)) should_capit_4_7
, sum(if(indexs=1, due30_capit, 0)) should_capit_1_30
, sum(if(indexs=2, due30_capit, 0)) should_capit_2_30
, sum(if(indexs=3, due30_capit, 0)) should_capit_3_30
, sum(if(indexs=4, due30_capit, 0)) should_capit_4_30,
--逾期本金 
sum(if(indexs=1, ovd0_capit, 0)) as overdue_capit_1_0,
sum(if(indexs=2, ovd0_capit, 0)) as overdue_capit_2_0,
sum(if(indexs=3, ovd0_capit, 0)) as overdue_capit_3_0,
sum(if(indexs=4, ovd0_capit, 0)) as overdue_capit_4_0,

sum(if(indexs=1, ovd1_capit, 0)) as overdue_capit_1_1,
sum(if(indexs=2, ovd1_capit, 0)) as overdue_capit_2_1,
sum(if(indexs=3, ovd1_capit, 0)) as overdue_capit_3_1,
sum(if(indexs=4, ovd1_capit, 0)) as overdue_capit_4_1,

sum(if(indexs=1, ovd2_capit, 0)) as overdue_capit_1_2,
sum(if(indexs=2, ovd2_capit, 0)) as overdue_capit_2_2,
sum(if(indexs=3, ovd2_capit, 0)) as overdue_capit_3_2,
sum(if(indexs=4, ovd2_capit, 0)) as overdue_capit_4_2,

sum(if(indexs=1, ovd3_capit, 0)) as overdue_capit_1_3,
sum(if(indexs=2, ovd3_capit, 0)) as overdue_capit_2_3,
sum(if(indexs=3, ovd3_capit, 0)) as overdue_capit_3_3,
sum(if(indexs=4, ovd3_capit, 0)) as overdue_capit_4_3,

sum(if(indexs=1, ovd7_capit, 0)) as overdue_capit_1_7,
sum(if(indexs=2, ovd7_capit, 0)) as overdue_capit_2_7,
sum(if(indexs=3, ovd7_capit, 0)) as overdue_capit_3_7,
sum(if(indexs=4, ovd7_capit, 0)) as overdue_capit_4_7,

sum(if(indexs=1, ovd30_capit, 0)) as overdue_capit_1_30,
sum(if(indexs=2, ovd30_capit, 0)) as overdue_capit_2_30,
sum(if(indexs=3, ovd30_capit, 0)) as overdue_capit_3_30,
sum(if(indexs=4, ovd30_capit, 0)) as overdue_capit_4_30
from mx.wxs_vintage_all31
group by 1
;



drop table if exists mx.wxs_vintage_all5;
create table mx.wxs_vintage_all5 as
select
a.id  id1
,overdue_cnt_1_now is_now_overdue_1

,overdue_amount_1_pre3  tpre3_overdue_amount_1
,overdue_amount_1_pre2  tpre2_overdue_amount_1
,overdue_amount_1_pre1  tpre1_overdue_amount_1
,overdue_amount_1_0  t0_overdue_amount_1
,overdue_amount_1_1  t1_overdue_amount_1
,overdue_amount_1_2  t2_overdue_amount_1
,overdue_amount_1_3  t3_overdue_amount_1
,overdue_amount_1_30  t30_overdue_amount_1
,overdue_amount_1_7  t7_overdue_amount_1
,overdue_amount_2_0  t0_overdue_amount_2
,overdue_amount_2_1  t1_overdue_amount_2
,overdue_amount_2_2  t2_overdue_amount_2
,overdue_amount_2_3  t3_overdue_amount_2
,overdue_amount_2_30  t30_overdue_amount_2
,overdue_amount_2_7  t7_overdue_amount_2
,overdue_amount_3_0  t0_overdue_amount_3
,overdue_amount_3_1  t1_overdue_amount_3
,overdue_amount_3_2  t2_overdue_amount_3
,overdue_amount_3_3  t3_overdue_amount_3
,overdue_amount_3_30  t30_overdue_amount_3
,overdue_amount_3_7  t7_overdue_amount_3
,overdue_amount_4_0  t0_overdue_amount_4
,overdue_amount_4_1  t1_overdue_amount_4
,overdue_amount_4_2  t2_overdue_amount_4
,overdue_amount_4_3  t3_overdue_amount_4
,overdue_amount_4_30  t30_overdue_amount_4
,overdue_amount_4_7  t7_overdue_amount_4
,overdue_cnt_1_pre3  is_tpre3_overdue_1
,overdue_cnt_1_pre2  is_tpre2_overdue_1
,overdue_cnt_1_pre1  is_tpre1_overdue_1
,overdue_cnt_1_0  is_t0_overdue_1
,overdue_cnt_1_1  is_t1_overdue_1
,overdue_cnt_1_2  is_t2_overdue_1
,overdue_cnt_1_3  is_t3_overdue_1
,overdue_cnt_1_30  is_t30_overdue_1
,overdue_cnt_1_7  is_t7_overdue_1
,overdue_cnt_2_0  is_t0_overdue_2
,overdue_cnt_2_1  is_t1_overdue_2
,overdue_cnt_2_2  is_t2_overdue_2
,overdue_cnt_2_3  is_t3_overdue_2
,overdue_cnt_2_30  is_t30_overdue_2
,overdue_cnt_2_7  is_t7_overdue_2
,overdue_cnt_3_0  is_t0_overdue_3
,overdue_cnt_3_1  is_t1_overdue_3
,overdue_cnt_3_2  is_t2_overdue_3
,overdue_cnt_3_3  is_t3_overdue_3
,overdue_cnt_3_30  is_t30_overdue_3
,overdue_cnt_3_7  is_t7_overdue_3
,overdue_cnt_4_0  is_t0_overdue_4
,overdue_cnt_4_1  is_t1_overdue_4
,overdue_cnt_4_2  is_t2_overdue_4
,overdue_cnt_4_3  is_t3_overdue_4
,overdue_cnt_4_30  is_t30_overdue_4
,overdue_cnt_4_7  is_t7_overdue_4
,overdue_interest_1_0  t0_overdue_interest_1
,overdue_interest_1_1  t1_overdue_interest_1
,overdue_interest_1_2  t2_overdue_interest_1
,overdue_interest_1_3  t3_overdue_interest_1
,overdue_interest_1_30  t30_overdue_interest_1
,overdue_interest_1_7  t7_overdue_interest_1
,overdue_interest_2_0  t0_overdue_interest_2
,overdue_interest_2_1  t1_overdue_interest_2
,overdue_interest_2_2  t2_overdue_interest_2
,overdue_interest_2_3  t3_overdue_interest_2
,overdue_interest_2_30  t30_overdue_interest_2
,overdue_interest_2_7  t7_overdue_interest_2
,overdue_interest_3_0  t0_overdue_interest_3
,overdue_interest_3_1  t1_overdue_interest_3
,overdue_interest_3_2  t2_overdue_interest_3
,overdue_interest_3_3  t3_overdue_interest_3
,overdue_interest_3_30  t30_overdue_interest_3
,overdue_interest_3_7  t7_overdue_interest_3
,overdue_interest_4_0  t0_overdue_interest_4
,overdue_interest_4_1  t1_overdue_interest_4
,overdue_interest_4_2  t2_overdue_interest_4
,overdue_interest_4_3  t3_overdue_interest_4
,overdue_interest_4_30  t30_overdue_interest_4
,overdue_interest_4_7  t7_overdue_interest_4
,should_capital_1_pre3  tpre3_should_amt_1
,should_capital_1_pre2  tpre2_should_amt_1
,should_capital_1_pre1  tpre1_should_amt_1
,should_capital_1_0  t0_should_amt_1
,should_capital_1_1  t1_should_amt_1
,should_capital_1_2  t2_should_amt_1
,should_capital_1_3  t3_should_amt_1
,should_capital_1_30  t30_should_amt_1
,should_capital_1_7  t7_should_amt_1
,should_capital_2_0  t0_should_amt_2
,should_capital_2_1  t1_should_amt_2
,should_capital_2_2  t2_should_amt_2
,should_capital_2_3  t3_should_amt_2
,should_capital_2_30  t30_should_amt_2
,should_capital_2_7  t7_should_amt_2
,should_capital_3_0  t0_should_amt_3
,should_capital_3_1  t1_should_amt_3
,should_capital_3_2  t2_should_amt_3
,should_capital_3_3  t3_should_amt_3
,should_capital_3_30  t30_should_amt_3
,should_capital_3_7  t7_should_amt_3
,should_capital_4_0  t0_should_amt_4
,should_capital_4_1  t1_should_amt_4
,should_capital_4_2  t2_should_amt_4
,should_capital_4_3  t3_should_amt_4
,should_capital_4_30  t30_should_amt_4
,should_capital_4_7  t7_should_amt_4
,should_cnt_1_pre3  is_tpre3_window_1
,should_cnt_1_pre2  is_tpre2_window_1
,should_cnt_1_pre1  is_tpre1_window_1
,should_cnt_1_0  is_t0_window_1
,should_cnt_1_1  is_t1_window_1
,should_cnt_1_2  is_t2_window_1
,should_cnt_1_3  is_t3_window_1
,should_cnt_1_30  is_t30_window_1
,should_cnt_1_7  is_t7_window_1
,should_cnt_2_0  is_t0_window_2
,should_cnt_2_1  is_t1_window_2
,should_cnt_2_2  is_t2_window_2
,should_cnt_2_3  is_t3_window_2
,should_cnt_2_30  is_t30_window_2
,should_cnt_2_7  is_t7_window_2
,should_cnt_3_0  is_t0_window_3
,should_cnt_3_1  is_t1_window_3
,should_cnt_3_2  is_t2_window_3
,should_cnt_3_3  is_t3_window_3
,should_cnt_3_30  is_t30_window_3
,should_cnt_3_7  is_t7_window_3
,should_cnt_4_0  is_t0_window_4
,should_cnt_4_1  is_t1_window_4
,should_cnt_4_2  is_t2_window_4
,should_cnt_4_3  is_t3_window_4
,should_cnt_4_30  is_t30_window_4
,should_cnt_4_7  is_t7_window_4
,should_interest_1_0  t0_should_interest_1
,should_interest_1_1  t1_should_interest_1
,should_interest_1_2  t2_should_interest_1
,should_interest_1_3  t3_should_interest_1
,should_interest_1_30  t30_should_interest_1
,should_interest_1_7  t7_should_interest_1
,should_interest_2_0  t0_should_interest_2
,should_interest_2_1  t1_should_interest_2
,should_interest_2_2  t2_should_interest_2
,should_interest_2_3  t3_should_interest_2
,should_interest_2_30  t30_should_interest_2
,should_interest_2_7  t7_should_interest_2
,should_interest_3_0  t0_should_interest_3
,should_interest_3_1  t1_should_interest_3
,should_interest_3_2  t2_should_interest_3
,should_interest_3_3  t3_should_interest_3
,should_interest_3_30  t30_should_interest_3
,should_interest_3_7  t7_should_interest_3
,should_interest_4_0  t0_should_interest_4
,should_interest_4_1  t1_should_interest_4
,should_interest_4_2  t2_should_interest_4
,should_interest_4_3  t3_should_interest_4
,should_interest_4_30  t30_should_interest_4
,should_interest_4_7  t7_should_interest_4

,is_t0_overdue
,is_t1_overdue
,is_t2_overdue
,is_t3_overdue
,is_t7_overdue
,is_t30_overdue
--应还本金
,should_capit_1_0 as t0_should_capit_1
,should_capit_2_0 as t0_should_capit_2
,should_capit_3_0 as t0_should_capit_3
,should_capit_4_0 as t0_should_capit_4
,should_capit_1_1 as t1_should_capit_1
,should_capit_2_1 as t1_should_capit_2
,should_capit_3_1 as t1_should_capit_3
,should_capit_4_1 as t1_should_capit_4
,should_capit_1_2 as t2_should_capit_1
,should_capit_2_2 as t2_should_capit_2
,should_capit_3_2 as t2_should_capit_3
,should_capit_4_2 as t2_should_capit_4
,should_capit_1_3 as t3_should_capit_1
,should_capit_2_3 as t3_should_capit_2
,should_capit_3_3 as t3_should_capit_3
,should_capit_4_3 as t3_should_capit_4
,should_capit_1_7 as t7_should_capit_1
,should_capit_2_7 as t7_should_capit_2
,should_capit_3_7 as t7_should_capit_3
,should_capit_4_7 as t7_should_capit_4
,should_capit_1_30 as t30_should_capit_1
,should_capit_2_30 as t30_should_capit_2
,should_capit_3_30 as t30_should_capit_3
,should_capit_4_30 as t30_should_capit_4

,overdue_capit_1_0 as t0_overdue_capit_1,
overdue_capit_2_0 as t0_overdue_capit_2,
overdue_capit_3_0 as t0_overdue_capit_3,
overdue_capit_4_0 as t0_overdue_capit_4,

overdue_capit_1_1 as t1_overdue_capit_1,
overdue_capit_2_1 as t1_overdue_capit_2,
overdue_capit_3_1 as t1_overdue_capit_3,
overdue_capit_4_1 as t1_overdue_capit_4,

overdue_capit_1_2 as t2_overdue_capit_1,
overdue_capit_2_2 as t2_overdue_capit_2,
overdue_capit_3_2 as t2_overdue_capit_3,
overdue_capit_4_2 as t2_overdue_capit_4,

overdue_capit_1_3 as t3_overdue_capit_1,
overdue_capit_2_3 as t3_overdue_capit_2,
overdue_capit_3_3 as t3_overdue_capit_3,
overdue_capit_4_3 as t3_overdue_capit_4,

overdue_capit_1_7 as t7_overdue_capit_1,
overdue_capit_2_7 as t7_overdue_capit_2,
overdue_capit_3_7 as t7_overdue_capit_3,
overdue_capit_4_7 as t7_overdue_capit_4,

overdue_capit_1_30 as t30_overdue_capit_1,
overdue_capit_2_30 as t30_overdue_capit_2,
overdue_capit_3_30 as t30_overdue_capit_3,
overdue_capit_4_30 as t30_overdue_capit_4
from mx.wxs_vintage_all4 a
left join
(SELECT 
id as id_b
,GREATEST(overdue_cnt_1_0, overdue_cnt_2_0, overdue_cnt_3_0, overdue_cnt_4_0) AS is_t0_overdue
,GREATEST(overdue_cnt_1_1, overdue_cnt_2_1, overdue_cnt_3_1, overdue_cnt_4_1) AS is_t1_overdue
,GREATEST(overdue_cnt_1_2, overdue_cnt_2_2, overdue_cnt_3_2, overdue_cnt_4_2) AS is_t2_overdue
,GREATEST(overdue_cnt_1_3, overdue_cnt_2_3, overdue_cnt_3_3, overdue_cnt_4_3) AS is_t3_overdue
,GREATEST(overdue_cnt_1_7, overdue_cnt_2_7, overdue_cnt_3_7, overdue_cnt_4_7) AS is_t7_overdue
,GREATEST(overdue_cnt_1_30, overdue_cnt_2_30, overdue_cnt_3_30, overdue_cnt_4_30) AS is_t30_overdue
from mx.wxs_vintage_all4
) b
on a.id=b.id_b
;




drop table if exists mx.wxs_overdue_basetable;
create table if not exists mx.wxs_overdue_basetable as  
select
camera_id
,should_time
,should_capital
,fact_capital
,should_interest
,fact_interest
,should_fine
,fact_fine
,now_should_amt
,is_t0_window
,is_t3_window
,is_t7_window
,is_t14_window
,is_t30_window
,t0_should_amt
,t3_should_amt
,t7_should_amt
,t14_should_amt
,t30_should_amt
,now_fact_amt
,t0_fact_amt
,t3_fact_amt
,t7_fact_amt
,t14_fact_amt
,t30_fact_amt
,t0_should_num
,t3_should_num
,t7_should_num
,t14_should_num
,t30_should_num
,pre_p2_repay
,p2_repay
,p2_repaytt
,p1_repay
,p0_repay
,now_OVERDUE_AMOUNT
,T0_OVERDUE_AMOUNT
,T3_OVERDUE_AMOUNT
,T7_OVERDUE_AMOUNT
,T14_OVERDUE_AMOUNT
,T30_OVERDUE_AMOUNT
,IS_NOW_OVERDUE
,now_overdue_days
-- ,IS_T0_OVERDUE
-- ,IS_T3_OVERDUE
-- ,IS_T7_OVERDUE
-- ,IS_T14_OVERDUE
-- ,IS_T30_OVERDUE
,tt4.*
from ods_view_presto.s09_os_credit_snapshot tt1
left join mx.wxs_risk_ttl tt3 on cast(tt1.id as varchar) = cast(ceil(tt3.camera_id) as varchar) --不分期贷后
left join mx.wxs_vintage_all5 tt4 on cast(tt1.id as varchar) = cast(tt4.id1 as varchar)
;




  drop table if exists mx.wxs_application_funnel_1;    
  create table  mx.wxs_application_funnel_1 as
  select 
  a.*
  -- ,case 
  -- when a.product_level='S2' THEN grantcredit_14d_amount
  -- when a.product_level='A1' THEN grantcredit_7d_amount ELSE grantcredit_7d_amount END AS grant_amount
  ,a1.reloan_num
  ,a1.grant_strategy
  ,CASE 
    		WHEN a2.media_source IN ( 'facebook') THEN 'FB'
    		WHEN a2.media_source IN ('google') THEN 'google'
        WHEN a2.media_source IN ( 'Apple Search Ads') THEN 'apple'
        WHEN a2.media_source IN ('organic', 'dc1', 'tz1', 'tz2', 'tz3', 'tz4', 'tz5', 'tanzhi') THEN 'tz'
        WHEN a2.media_source IN ('luxmediakx_int','vfine_int', 'Smark', 'nzxfspace_int', 'casmedia_int', 'orgnisite3n_int', 'adtiming_int', 'momentnetw8_int', 'bolinmobi0m_int', 'summads_int', 'texttmedipe_int', 'mobfire_int', '360security_int') THEN 'qudao'
        WHEN a2.media_source IN ('Tengo_to_Yawey_all', 'yawey_to_tengo_all', 'downloadNoReg_t1',  'direction_toOther', 'direction_toApp', 'api_market','94AI语音', '94ai语音','TelemarketingList_group', 'SMS', 'Diversion_reloan', 'diversion_yawey_to_tengo','hasRegNoLoan_t1_cm', 'hasRegisterNoLoan_t10', 'hasRegisterNoLoan_T15', 'finishNoLoan_T10', 'finishNoLoan_T15', 'finishNoLoan_T30') THEN 'yunying'
        ELSE 'organic'
    END AS channel_category
,case when a.app_channel = 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5' then 'hola'
     when a.app_channel = 'faa92afe-b81a-4d94-ba1a-15eb9d536833' then 'hola se'
     when a.app_channel = '4cc31ae6-937e-4fd3-bc98-862314e7cb68' then 'hola max'
     when a.app_channel = 'db0d289f-d217-49ea-a889-c191776115ef' then 'hola pro'
     when a.app_channel = '56c660de-3549-4482-9ad5-0404eef0d70d' then 'yawey'
     when a.app_channel = 'cdf58da5-801a-4575-9af4-a56453cea6f3' then 'yawey_plus'
     when a.app_channel = '9922eb08-b998-46d9-b81e-469ae4c2e0ec' then 'yawey_ultra'
     when a.app_channel = 'ab9981d2-b48f-4df0-a086-ff7df6a4fa04' then 'yawey_max'
     when a.app_channel = '2930a02e-07b9-4851-aedd-200244a62b75' then 'tengo'
     when a.app_channel = '91379659-2dc0-42d2-8205-9de6d81f7550' then 'voltrix' 
     when a.app_channel = 'cbcf1f5e-092a-44ad-abb9-7d5af8f023cb' then 'tengo_plus' 
     when a.app_channel = 'e5a5940e-eb8e-4188-ad1a-5bdbd4580938' then 'tengo_ultra'
     when a.app_channel = '6d21fe7d-8344-419c-8c94-a7b5cc1c8ee8' then 'tengo_max'
     when a.app_channel = '026f5e80-4582-4821-847a-4665660d8451' then 'pf'
     else e.app_name
     end as app
  ,e.app_group
  ,case when e.app_group='YW' then 'yawey' else e.app_group end as app_group_sha256
  ,b.biz_id as app_id
  ,b.cust_name
  ,b.phone_num
  ,b.product_type
  ,b.create_time as app_time -- app_time就是申请时间 ,apply_time_day
  ,b.apply_time
  ,b.status --状态0：申请1:执行中372：已通过425：已拒绝 order_status_code
  ,b.is_loan
  ,b.product_name
  ,b.double_loan
  ,b.source 
  ,case when double_loan_tenant = 1 then 'old'
    when double_loan_tenant = 0 then 'new'
    when double_loan_tenant is null then 
      case when a.app_channel in ('cdf58da5-801a-4575-9af4-a56453cea6f3', 
                'cbcf1f5e-092a-44ad-abb9-7d5af8f023cb',
                'e5a5940e-eb8e-4188-ad1a-5bdbd4580938',
                '6d21fe7d-8344-419c-8c94-a7b5cc1c8ee8',
                '9922eb08-b998-46d9-b81e-469ae4c2e0ec',
                'ab9981d2-b48f-4df0-a086-ff7df6a4fa04',
                'db0d289f-d217-49ea-a889-c191776115ef',
                '4cc31ae6-937e-4fd3-bc98-862314e7cb68',
                '91379659-2dc0-42d2-8205-9de6d81f7550',
                'faa92afe-b81a-4d94-ba1a-15eb9d536833',
                '00b3fb44-7a1a-49f3-a1a2-d81deb4026f2') then 'old'
          else case when b.double_loan > 0 then 'old'
            when b.double_loan = 0 then 'new'
            else 'new' end end end as is_reloan
  ,b.repayment
  ,b.apply_period
  ,b.app_version
  ,b.grantcredit_amount
  ,b.temp_grant_amount
  ,ceil(c.loan_cycle) as loan_cycle  --产品期限
  ,c.contract_amount --合同金额
  ,c.amount --实际放款金额
  ,c.haircut_amount --砍头息
  ,c.release_time --放款时间
  ,c.cancel_time --取消时间
  ,c.finish_time --结清时间
  ,c.state as loan_state --放款状态（0：待审核；1.已放款；2.正常结清；3.核销4.取消5.放款失败6.审核拒绝7.放款中）
  ,c.loan_indexs
  -- ,d.should_time --应还时间
  -- ,d.should_capital --应还本金
  -- ,d.fact_capital --实还本金
  -- ,d.should_interest --应还利息
  -- ,d.fact_interest --实还利息
  -- ,d.should_fine --应还罚息
  -- ,d.fact_fine --实还罚息
  ,CASE WHEN b.biz_id IS NOT NULL THEN 1 ELSE 0 END AS if_app  --是否进件
  ,CASE WHEN b.status = 372 then 1 else 0 end as if_pass --是否机审通过
  ,CASE WHEN b.is_loan = '1' THEN 1 ELSE 0 END AS IF_BID --是否发标
  ,CASE WHEN c.cancel_time IS NOT NULL THEN 1 ELSE 0 END AS if_cancel  --是否取消
  ,CASE WHEN d.should_time IS NOT NULL THEN 1 ELSE 0 END AS if_issue  --是否放款
  -- ,cast(a.grantcredit_amount/1000 as decimal)  AS credit_amount --测试额度
  ,cast(b.apply_amount/1000 as decimal)  as apply_amount --用户申请额度
  ,cast(b.approve_amount/1000 as decimal)  as approve_amount --审批额度
  ,CASE WHEN d.should_capital IS NOT NULL then cast(c.amount as decimal) else 0 end as issue_amount --放款金额（实际）
  ,cast(d.should_capital as decimal) as should_amount --应还金额
  ,cast(d.fact_capital as decimal) as repay_amount --实还本金
  ,date(b.create_time) as app_date --进件日
  ,date_trunc('week',date(b.create_time)) as app_week --进件周
  ,date_trunc('month',date(b.create_time)) as app_month --进件月
  ,date(c.release_time) as issue_date --放款日
  ,date_trunc('week',date(c.release_time)) as issue_week --放款周
  ,date_trunc('month',date(c.release_time)) as issue_month --放款月
  ,date(d.should_time) as deadline --到期日
  ,d.*

  ,credit_no
  ,g.one_click_loan_tag
  ,f.fd_high_pass_label
  ,f.sd_high_pass_label
  from 
  (SELECT * FROM ods_view_presto.s05_creditx_order WHERE DATE(CREATE_TIME) >= date_add('day',-720,DATE(now()))) b 
  left join 
  (select create_time,date(create_time) as create_date,cust_id,identity,id,device_id,mid,tenant_id
,CASE WHEN tenant_id = 1721000001013013 then 'hola'
when tenant_id = 1721000001038563 then 'yawey'
when tenant_id = 1721000000984539 then 'tengo' end as tenant
,app_channel,  risk_level,product_day,grant_score,name,longitude,latitude
  ,cast(json_extract(grantcredit_info, '$.product_level') as varchar) product_level
  ,cast(json_extract(grantcredit_info, '$.grantcredit_7d_amount') as varchar) grantcredit_7d_amount
  ,cast(json_extract(grantcredit_info, '$.grantcredit_14d_amount') as varchar) grantcredit_14d_amount
  ,cast(json_extract(grantcredit_info, '$.grantcredit_15d_amount') as varchar) grantcredit_15d_amount
  ,cast(json_extract(grantcredit_info, '$.grantcredit_30d_amount') as varchar) grantcredit_30d_amount
  ,cast(json_extract(grantcredit_info, '$.global_7d_limit') as varchar) global_7d_limit
  ,cast(json_extract(grantcredit_info, '$.global_limit') as varchar) global_limit
  ,cast(json_extract(grantcredit_info, '$.credit_amount') as double) credit_amount_sx
  ,cast(json_extract(grantcredit_info, '$.daily_max_available_limit') as double) daily_max_available_limit_sx
  ,email
  ,phone
  ,fpid
      from ods_view_presto.s09_os_credit_snapshot
      group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28) a 
  on cast(a.id as varchar)= b.biz_id 
  left join mx.wxs_reloan a1
  on a.id = a1.id
  left join 
  (select cast(json_extract(event_value,'$.UserID') as varchar) mid, 
    media_source 
  from  ods.s08_appsflyer_push_data 
  where event_name='register_success'
  group by 1,2) a2 
  on cast(a.mid as varchar) = a2.mid and a2.mid <> '' and a2.mid is not null
  left join 
  ods_view_presto.s02_loan c
  on cast(a.id as varchar) = cast(ceil(c.camera_id) as varchar) 
  left join 
  mx.wxs_overdue_basetable d 
  on cast(b.biz_id as varchar)  = cast(ceil(d.camera_id) as varchar)  
  left join
  ods.s08_app_category_mapping e
  on a.app_channel=e.app_channel
  left join  (
  select *
  from mx.tmp_darren_double_loan_tag_table) f
  on cast(a.id as varchar) = cast(f.externalid as varchar)
  left join (
  select *
  from mx.tmp_one_click_loan_tag) g 
  on cast(b.biz_id as varchar) = cast(g.biz_id as varchar)
  ;
  
  
  
  
 drop table if exists mx.wxs_application_funnel_2;    
  create table  mx.wxs_application_funnel_2 as
  SELECT B.BIZ_ID
  ,if_in_shou_anti_fraud  --强反欺诈（首贷）
  ,if_shou_anti_fraud_passed
  ,if_shou_anti_fraud_refused
  ,if_in_fu_anti_fraud  --强反欺诈（复贷）
  ,if_fu_anti_fraud_passed
  ,if_fu_anti_fraud_refused
  ,if_in_shou_anti_fraud_weak  --弱反欺诈（首贷）
  ,if_shou_anti_fraud_weak_passed
  ,if_shou_anti_fraud_weak_refused
  ,if_in_fu_anti_fraud_weak  --弱反欺诈（复贷）
  ,if_fu_anti_fraud_weak_passed
  ,if_fu_anti_fraud_weak_refused
  ,if_in_shou_model  --模型（首贷）
  ,if_shou_model_passed
  ,if_shou_model_refused
  ,if_in_fu_model  --模型（复贷）
  ,if_fu_model_passed
  ,if_fu_model_refused
  ,if_in_shou_normal_check --** 正常人审（首贷）
  ,if_shou_normal_check_passed
  ,if_shou_normal_check_refused
  ,if_shou_normal_check_canceled
  ,if_shou_manual_check_pending
  ,if_in_fu_manual_check  --人审（复贷）
  ,if_fu_normal_check_passed
  ,if_fu_normal_check_refused
  ,if_fu_normal_check_canceled
  ,if_fu_manual_check_pending
  ,if_in_shou_external_data  --三方（首贷）
  ,if_shou_external_data_passed
  ,if_shou_external_data_refused
  ,if_in_fu_external_data  --三方（复贷）
  ,if_fu_external_data_passed
  ,if_fu_external_data_refused
  ,if_in_shou_normal_rule_check
  ,if_shou_normal_rule_check_passed
  ,if_shou_normal_rule_check_canceled
  ,if_shou_normal_rule_check_refused
  ,if_fu_normal_rule_check_passed
  ,if_fu_normal_rule_check_canceled
  ,if_fu_normal_rule_check_refused
  ,if_in_SD_AI
  ,if_shou_AI_passed
  ,if_shou_AI_PENDING
  ,if_in_FD_AI
  ,if_FU_AI_passed
  ,if_FU_AI_refused
  ,if_FU_AI_PENDING
  ,if_in_sx
  ,if_SX_passed
  ,if_SX_WAITING
  ,if_in_fu_normal_rule_check
  ,if_shou_ai_refused
  ,if_in_fu_sx_refuse
  ,if_fu_sx_refuse_passed
  ,if_fu_sx_refuse_WAITING
  ,if_in_sx_6h
  ,if_in_sx_24h
  ,if_in_sx_48h
  ,if_in_sx_72h
  ,if_in_sx_120h
  ,if_SX_passed_6h
  ,if_SX_passed_24h
  ,if_SX_passed_48h
  ,if_SX_passed_72h
  ,if_SX_passed_120h
  ,if_in_fu_post_anti_fraud_rerun
  ,if_fu_post_anti_fraud_rerun_passed
  ,if_fu_post_anti_fraud_rerun_refused
  ,if_in_fu_post_weak_anti_fraud_rerun
  ,if_fu_post_weak_anti_fraud_rerun_passed
  ,if_fu_post_weak_anti_fraud_rerun_refused

  ,if_in_fu_post_model_reject_rerun
  ,if_fu_post_model_reject_rerun_passed
  ,if_fu_post_model_reject_rerun_refused

  ,if_in_post_model
  
  
  FROM
  (SELECT BIZ_ID,status,double_loan FROM ods_view_presto.s05_creditx_order group by 1,2,3) b 
      left join
      (
      SELECT 
        biz_id
    ,1 as if_in_shou_anti_fraud,
      case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as if_shou_anti_fraud_passed,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_shou_anti_fraud_refused
    FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('首贷强反欺诈')
      group by 1 
      )p1 
      on b.biz_id = p1.biz_id
      left join
      (
      SELECT 
      biz_id, 1 as if_in_fu_anti_fraud,
      case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as  if_fu_anti_fraud_passed, 
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_fu_anti_fraud_refused
      FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('复贷强反欺诈') 
    group by 1     
      )p2
      on b.biz_id = p2.biz_id
      left join
      (
      SELECT 
        biz_id
    ,1 as if_in_shou_anti_fraud_weak,
      case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as if_shou_anti_fraud_weak_passed,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_shou_anti_fraud_weak_refused
    FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('首贷弱反欺诈')
      group by 1 
      )p3
      on b.biz_id = p3.biz_id
      left join
      (
      SELECT 
      biz_id, 1 as if_in_fu_anti_fraud_weak,
      case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as  if_fu_anti_fraud_weak_passed, 
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_fu_anti_fraud_weak_refused
      FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('复贷弱反欺诈') 
    group by 1     
      )p4
      on b.biz_id = p4.biz_id
      left join
      (
      SELECT 
        biz_id
    ,1 as if_in_shou_model,
      case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as if_shou_model_passed,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_shou_model_refused
    FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('首贷模型拒绝')
      group by 1 
      )p5 
      on b.biz_id = p5.biz_id
      left join
      (
      SELECT 
      biz_id, 1 as if_in_fu_model,
      case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as  if_fu_model_passed, 
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_fu_model_refused
      FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('复贷模型拒绝') 
    group by 1     
      )p6
      on b.biz_id = p6.biz_id
      left join
      (
      SELECT 
      biz_id,  1 as if_in_shou_normal_check,
      case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 else 0 end as if_shou_normal_check_passed, 
    case when (sum(case when approve_result='CANCELED' then 1 end)) >=1 then 1 else 0 end as if_shou_normal_check_canceled,
      case when (sum(case when approve_result='REFUSED' then 1 end))  >=1 then 1 else 0 end as  if_shou_normal_check_refused,
      case when (sum(case when approve_result is NULL then 1 end))  >=1  then 1 else 0 end as if_shou_manual_check_pending
    FROM  ods_view_presto.s05_creditx_processor_record where current_processor in ('首贷初审','人审节点')   
      group by 1
      )p7
      on b.biz_id = p7.biz_id
      left join
      (
      SELECT 
      biz_id,  1 as if_in_fu_manual_check,
      case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 else 0 end as if_fu_normal_check_passed, 
    case when (sum(case when approve_result='CANCELED' then 1 end)) >=1 then 1 else 0 end as if_fu_normal_check_canceled,
      case when (sum(case when approve_result='REFUSED' then 1 end))  >=1 then 1 else 0 end as  if_fu_normal_check_refused,
      case when (sum(case when approve_result is NULL then 1 end))  >=1  then 1 else 0 end as if_fu_manual_check_pending
      FROM  ods_view_presto.s05_creditx_processor_record where current_processor in ('复贷初审') 
      group by 1
      )p8
      on b.biz_id = p8.biz_id
      left join
      (
        SELECT 
      biz_id, 1 as if_in_shou_external_data
    ,case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as  if_shou_external_data_passed
    ,case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as  if_shou_external_data_refused
      FROM  ods_view_presto.s05_creditx_processor_record
    where current_processor in ('首贷三方节点') 
    group by 1 
      ) p9
      on b.biz_id = p9.biz_id	
      left join
      (
      SELECT 
      biz_id, 1 as if_in_fu_external_data
    ,case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 else 0 end as  if_fu_external_data_passed
    ,case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as  if_fu_external_data_refused
      FROM  ods_view_presto.s05_creditx_processor_record 
    where current_processor in ('复贷三方节点') 
    group by 1
      ) p10
      on b.biz_id = p10.biz_id	
      left join
      (
      SELECT 
      biz_id,  1 as if_in_shou_normal_rule_check,
      case when (sum(case when cast(json_extract(context_result, '$.myDecisionResult') as varchar) is null then 1 end)) >=1 then 1 else 0 end as if_shou_normal_rule_check_passed, 
    case when (sum(case when cast(json_extract(context_result, '$.myDecisionResult') as varchar)='cancel' then 1 end)) >=1 then 1 else 0 end as if_shou_normal_rule_check_canceled,
      case when (sum(case when cast(json_extract(context_result, '$.myDecisionResult') as varchar)='reject' then 1 end))  >=1 then 1 else 0 end as  if_shou_normal_rule_check_refused
    FROM  ods_view_presto.s05_creditx_processor_record where current_processor in ('人审规则节点')  
      group by 1
      ) p11
      on b.biz_id = p11.biz_id	
      left join
      (
      SELECT 
      biz_id,  1 as if_in_fu_normal_rule_check,
      case when (sum(case when cast(json_extract(context_result, '$.myDecisionResult') as varchar) is null then 1 end)) >=1 then 1 else 0 end as if_fu_normal_rule_check_passed, 
    case when (sum(case when cast(json_extract(context_result, '$.myDecisionResult') as varchar)='cancel' then 1 end)) >=1 then 1 else 0 end as if_fu_normal_rule_check_canceled,
      case when (sum(case when cast(json_extract(context_result, '$.myDecisionResult') as varchar)='reject' then 1 end))  >=1 then 1 else 0 end as  if_fu_normal_rule_check_refused
    FROM  ods_view_presto.s05_creditx_processor_record where current_processor in ('复贷人审规则')
      group by 1  
      ) p12
      on b.biz_id = p12.biz_id	
          left join
      (
      SELECT 
        biz_id
    ,1 as if_in_SD_AI,
      case when (sum(case when approve_result='PASSED' then 1 end))  >=1 then 1 else 0 end as if_shou_AI_passed,
      case when (sum(case when approve_result='REFUSED' then 1 end)) >=1 then 1 else 0 end as if_shou_AI_refused,
      case when (sum(case when approve_result='WAITING' then 1 end)) >=1 then 1 else 0 end as if_shou_AI_PENDING
    FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('电核规则节点')
      group by 1 
      ) p13 
      on b.biz_id = p13.biz_id
              left join
      (
      SELECT 
        biz_id
    ,1 as if_in_FD_AI,
      case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 else 0 end as if_FU_AI_passed,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_FU_AI_refused,
      case when (sum(case when approve_result='WAITING' then 1 end))>=1 then 1 else 0 end as if_FU_AI_PENDING
    FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('FDAI')
      group by 1 
      ) p14 
      on b.biz_id = p14.biz_id
              left join
      (
      SELECT 
        biz_id
    ,1 as if_in_sx,
      case when sum(case when date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp)) >= 6*60 then 1 else 0 end)>=1 then 1 else 0 end as if_in_sx_6h, 
      case when sum(case when date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp)) >= 24*60 then 1 else 0 end)>=1 then 1 else 0 end as if_in_sx_24h, 
      case when sum(case when date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp)) >= 48*60 then 1 else 0 end)>=1 then 1 else 0 end as if_in_sx_48h, 
      case when sum(case when date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp)) >= 72*60 then 1 else 0 end)>=1 then 1 else 0 end as if_in_sx_72h, 
      case when sum(case when date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp)) >= 120*60 then 1 else 0 end)>=1 then 1 else 0 end as if_in_sx_120h, 
      case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 else 0 end as if_SX_passed,
      case when (sum(case when approve_result='WAITING' then 1 end))>=1 then 1 else 0 end as if_SX_WAITING,
      case when sum(case when approve_result='PASSED' and date_diff('minute',create_time,update_time)<=6*60 AND date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>= 6 * 60 then 1 else 0 end)>=1 then 1 else 0 end as if_SX_passed_6h, 
      case when sum(case when approve_result='PASSED' and date_diff('minute',create_time,update_time)<=24*60 AND date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>= 24 * 60 then 1 else 0 end)>=1 then 1 else 0 end as if_SX_passed_24h,
      case when sum(case when approve_result='PASSED' and date_diff('minute',create_time,update_time)<=48*60 AND date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>= 48 * 60 then 1 else 0 end)>=1 then 1 else 0 end as if_SX_passed_48h,
      case when sum(case when approve_result='PASSED' and date_diff('minute',create_time,update_time)<=72*60 AND date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>= 72 * 60 then 1 else 0 end)>=1 then 1 else 0 end as if_SX_passed_72h,
      case when sum(case when approve_result='PASSED' and date_diff('minute',create_time,update_time)<=120*60 AND date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>= 120 * 60 then 1 else 0 end)>=1 then 1 else 0 end as if_SX_passed_120h
    FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('首贷授信等待节点','复贷授信等待节点')
      group by 1 
      ) p15
      on b.biz_id = p15.biz_id  
                left join
      (
      SELECT 
        biz_id
    ,1 as if_in_fu_sx_refuse,
      case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 else 0 end as if_fu_sx_refuse_passed,
      case when (sum(case when approve_result='WAITING' then 1 end))>=1 then 1 else 0 end as if_fu_sx_refuse_WAITING
    FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('复贷授信拒绝')
      group by 1 
      ) p16
      on b.biz_id = p16.biz_id  
      left join
      (
      SELECT 
        biz_id
    ,1 as if_in_fu_post_anti_fraud_rerun,
      case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 else 0 end as if_fu_post_anti_fraud_rerun_passed,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_fu_post_anti_fraud_rerun_refused
      
    FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('复贷后置强反重跑节点')
      group by 1 
      ) p17
      on b.biz_id = p17.biz_id  
      
      left join
      (
      SELECT 
        biz_id
    ,1 as if_in_fu_post_weak_anti_fraud_rerun,
      case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 else 0 end as if_fu_post_weak_anti_fraud_rerun_passed,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_fu_post_weak_anti_fraud_rerun_refused
      
    FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('复贷后置弱反重跑节点')
      group by 1 
      ) p18
      on b.biz_id = p18.biz_id  

      left join
      (
      SELECT 
        biz_id
    ,1 as if_in_fu_post_model_reject_rerun,
      case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 else 0 end as if_fu_post_model_reject_rerun_passed,
      case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 else 0 end as if_fu_post_model_reject_rerun_refused
      
    FROM  ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('复贷后置模型拒绝重跑节点')
      group by 1 
      ) p19
      on b.biz_id = p19.biz_id  

left join (select biz_id,
					1 as if_in_post_model,
					case when (sum(case when approve_result='PASSED' then 1 end)) >= 1 then 1 
						else 0 end as if_post_model_passed,
					case when (sum(case when approve_result='REFUSED' then 1 end)) >= 1 then 1 
						else 0 end as if_post_model_refused
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('首贷后置模型拒绝节点') --- 授信等待节点是后置的起始点
				group by 1) p20
  on b.biz_id = p20.biz_id


  ;
  
  
  
  drop table if exists mx.wxs_application_funnel;
  create table  mx.wxs_application_funnel as
  select a.*,b.*
  from 
  mx.wxs_application_funnel_1 a 
  left join 
  mx.wxs_application_funnel_2 b
  on a.app_id = b.BIZ_ID 
  where create_date>=date_add('day',-720,DATE(now())) and create_date<=current_date
  ;


