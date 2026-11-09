select * from dws.dws_risk_stgy_apply_mid_tags  limit 100;


@presto
-- =============================================
-- Name: dws_cust_apply_mid_tags
-- Description:   
-- Author: chun song zheng
-- Created Date: 2025-05-20
-- Modified History: 
--   2025-12-16 [chun song zheng] [new create]
-- =============================================

DROP TABLE if EXISTS tmp.tmp_cust_apply_mid_order_tags;
create table tmp.tmp_cust_apply_mid_order_tags
as
select t.mid,
       t2.identity_number,
       app_group,
       max(if_api) if_api,
       max(case
             when order_status_code = 372 then
              1
             else
              0
           end) if_loan,
       min(date(create_time)) as first_apply_date,
       max(date(create_time)) as last_apply_date,
       max(expired_time) as prohibit_expired_time,
       localtimestamp load_time,
       max(case when now() <= expired_time then 1 else 0 end) as if_prohibit_apply
  from dwd.dwd_trans_order_info t
 inner join (select mid, identity_number
               from (select mid,
                            identity_number,
                            row_number() over(partition by mid order by create_time desc) as rn
                       from dwd.dwd_trans_order_info)  --部分MID有多个身份证号，取最新一个
              where rn = 1) t2
    on t.mid = t2.mid
  left join (select list_value credit_no,
                    split_part(type_code, '_', 1) as type,
                    max(expired_time) expired_time
               from ods.s19_sr_name_list_data
              where type_code like '%creditNo%'
              group by 1, 2) t1
    on REGEXP_extract(app_package, '[^.]+$') = t1.type
   and t.identity_number = t1.credit_no
 group by 1, 2, 3;
 
DROP TABLE if EXISTS tmp.tmp_cust_apply_mid_app_tags;
create table tmp.tmp_cust_apply_mid_app_tags
as
select cast(customer_user_id as bigint) as mid,
       max(date(event_time)) as last_login_date,
       localtimestamp load_time
  from ods.s08_appsflyer_push_data
 where event_name like ('%home%')
 group by 1;
 
DROP TABLE if EXISTS tmp.tmp_cust_apply_mid_lid_tags;
create table tmp.tmp_cust_apply_mid_lid_tags
as
select mid,
       sum(case when loan_state_code=1 then 1 else 0 end) onloan_cnt,
       min(date(loan_time)) first_loan_date,
       max(date(loan_time)) last_loan_date,
       localtimestamp load_time
  from dwd.dwd_trans_loan_info lr
 where loan_state_code in (1, 2)
 group by 1;

DROP TABLE if EXISTS tmp.tmp_cust_apply_push_token;
create table tmp.tmp_cust_apply_push_token
as
select
  cast(mid as bigint) mid,
  push_token push_token,
  localtimestamp load_time
from
  (
    select
      mid,
      push_token,
      row_number() over (
        partition by
          mid
        order by
          create_time desc
      ) rn
    from
      ods.s20_push_token
    where
      push_token is not null
      and deleted = 0
  )
where
  rn = 1;
  
DROP TABLE if EXISTS tmp.tmp_cust_apply_mid_reapyment_tags;
create table tmp.tmp_cust_apply_mid_reapyment_tags
as
select l.mid,
       max(date(fact_time)) last_repay_date,
       sum(case
             when repay_state_code in (0, 2) then
              should_capital - fact_capital
           end) onloan_bal,
       max(case
             when repay_state_code in (0, 2, 4, 7) then
              overdue_days
              when repay_state_code=1 then 0 --有表现期要给0
           end) curr_overdue_days,
       max(overdue_days) max_overdue_days,
       sum(case
             when l.app_channel in
                  ('cdf58da5-801a-4575-9af4-a56453cea6f3',
                   'cbcf1f5e-092a-44ad-abb9-7d5af8f023cb',
                   'e5a5940e-eb8e-4188-ad1a-5bdbd4580938',
                   '6d21fe7d-8344-419c-8c94-a7b5cc1c8ee8',
                   '9922eb08-b998-46d9-b81e-469ae4c2e0ec',
                   'ab9981d2-b48f-4df0-a086-ff7df6a4fa04',
                   'db0d289f-d217-49ea-a889-c191776115ef',
                   '4cc31ae6-937e-4fd3-bc98-862314e7cb68',
                   '91379659-2dc0-42d2-8205-9de6d81f7550',
                   'faa92afe-b81a-4d94-ba1a-15eb9d536833',
                   '00b3fb44-7a1a-49f3-a1a2-d81deb4026f2') then
              1
             when lr.repay_state_code in (1, 3) then
              1
           end) as repay_indexs_cnt,
       localtimestamp load_time
  from dwd.dwd_trans_loan_info l
 inner join dwd.dwd_trans_repayment_info lr
    on l.lid = lr.lid
 where loan_state_code in (1, 2)
 group by 1;
 
DROP TABLE if EXISTS tmp.tmp_cust_apply_mid_id_overdue_days;
create table tmp.tmp_cust_apply_mid_id_overdue_days
as
select o.identity_number,
       max(case
             when repay_state_code in (0, 2, 4, 7) then
              overdue_days
             when repay_state_code=1 then 0 --有表现期要给0
           end) id_curr_overdue_days,
       max(
           
           case
             when date_diff('day', date(lr.create_time), date(now())) <= 30 then
              overdue_days
           end) id_30days_max_overdue_days,
       localtimestamp load_time
  from dwd.dwd_trans_order_info o
 inner join dwd.dwd_trans_loan_info l
    on o.camera_id = l.camera_id
 inner join dwd.dwd_trans_repayment_info lr
    on l.lid = lr.lid
 where loan_state_code in (1, 2)
 group by 1;

DROP TABLE if EXISTS tmp.tmp_cust_apply_mid_newcust_tags;
create table tmp.tmp_cust_apply_mid_newcust_tags
as
select mid, newcust_credit_level, newcust_credit_level_version
  from (select mid,
               cast(json_extract(outputdata, '$.newcust_creditlevel') as
                    double) as newcust_credit_level,
               cast(json_extract(outputdata, '$.newcust_creditlevel_version') as
                    varchar) as newcust_credit_level_version,
               row_number() over(partition by mid order by createtime desc) as rn
          from ods.s21_risk_strategy_record
         where productid in (188, 363, 405, 439)
           and etl_date >= '20251125' --策略20251125开始
           and strategytype = 'CHAMPION')
 where rn = 1
    or rand() < 0;

DROP TABLE if EXISTS tmp.tmp_cust_apply_mid_oldcust_tags;
create table tmp.tmp_cust_apply_mid_oldcust_tags
as
select mid, oldcust_credit_level, oldcust_credit_level_version
  from (select mid,
               cast(json_extract(outputdata, '$.oldcust_creditlevel') as
                    double) as oldcust_credit_level,
               cast(json_extract(outputdata, '$.oldcust_creditlevel_version') as
                    varchar) as oldcust_credit_level_version,
               row_number() over(partition by mid order by createtime desc) as rn
          from ods.s21_risk_strategy_record
         where productid in (432,464,428,449,450,468)
           and etl_date >= '20251125' --策略20251125开始
           and strategytype = 'CHAMPION'
           and json_extract(outputdata, '$.oldcust_creditlevel') is not null) --  结清如果走非调额分支会没有资产等级，此次新增代码 )

 where rn = 1
    or rand() < 0;


drop table if exists tmp.tmp_dwd_trans_repayment_info_curr_this;
create table tmp.tmp_dwd_trans_repayment_info_curr_this as
select
  mid,
  count(distinct case when date_diff('day',date(create_time),date(now())) <= 30 and repay_state_code = 2 then camera_id end) as curr_ovd_cnt_this_app_group_30d, --本包近30天在逾订单数
  count(distinct case when date_diff('day',date(create_time),date(now())) <= 60 and repay_state_code = 2 then camera_id end) as curr_ovd_cnt_this_app_group_60d, --本包近60天在逾订单数
  count(distinct case when date_diff('day',date(create_time),date(now())) <= 90 and repay_state_code = 2 then camera_id end) as curr_ovd_cnt_this_app_group_90d, --本包近90天在逾订单数
  count(distinct case when repay_state_code = 2 then camera_id end)                                                        as curr_ovd_cnt_this_app_group --本包在逾订单数
from dwd.dwd_trans_repayment_info
group by 1
;



--- 补充本次新提变量
drop table if exists tmp.tmp_dwd_trans_repayment_info_curr_other;
create table tmp.tmp_dwd_trans_repayment_info_curr_other as
WITH t3 AS
(
	SELECT  t0.mid
	       ,t0.identity_num as identity
	       ,t1.mid AS all_mid
	FROM dwd.dwd_mem_info t0
	LEFT JOIN dwd.dwd_mem_info t1
	ON t0.identity_num = t1.identity_num
), t4 AS
(
	--- 计算他包逾期天数
	SELECT  t3.*
	       ,create_time AS loan_time
	       ,camera_id
	       ,state
	       ,customer_id
	       ,should_time
	       ,fact_time
	       ,fact_fine
	       ,fact_capital
	       ,should_capital
	FROM t3
	LEFT JOIN
	(
		SELECT  repay_state_code as state
		       ,camera_id
		       ,mid as customer_id
		       ,should_time
		       ,fact_time
		       ,fact_fine
		       ,fact_capital
		       ,should_capital
		       ,create_time
		FROM dwd.dwd_trans_repayment_info --ods_view_presto.s02_loan_repayment
	) t4
	ON t3.all_mid = t4.customer_id AND t3.mid != t4.customer_id
)
SELECT  mid
	       ,COUNT(distinct CASE WHEN date_diff('day',date(loan_time),date(now())) <= 30 AND state = 2 THEN camera_id end) AS curr_ovd_cnt_other_app_group_30d  --他包近30天在逾订单数
	       ,COUNT(distinct CASE WHEN date_diff('day',date(loan_time),date(now())) <= 60 AND state = 2 THEN camera_id end) AS curr_ovd_cnt_other_app_group_60d  --他包近60天在逾订单数
	       ,COUNT(distinct CASE WHEN date_diff('day',date(loan_time),date(now())) <= 90 AND state = 2 THEN camera_id end) AS curr_ovd_cnt_other_app_group_90d  --他包近90天在逾订单数
	       ,COUNT(distinct CASE WHEN state = 2 THEN camera_id end)                                                        AS curr_ovd_cnt_other_app_group      --他包在逾订单数、
	FROM t4
	GROUP BY  1
;

DROP TABLE if EXISTS  tmp.tmp_cust_apply_mid_tags;
create table tmp.tmp_cust_apply_mid_tags
as
select t1.mid,
       t1.identity_number,
       t1.app_group,
       t1.first_apply_date,
       t1.last_apply_date,
       t2.onloan_cnt,
       t2.first_loan_date,
       t2.last_loan_date,
       t3.last_repay_date,
       t3.onloan_bal,
       t3.curr_overdue_days,
       t7.id_curr_overdue_days,
       t7.id_30days_max_overdue_days,
       t3.max_overdue_days,
       t4.last_login_date,
       t5.newcust_credit_level,
       t5.newcust_credit_level_version,
       t6.oldcust_credit_level curr_credit_level,
       t6.oldcust_credit_level_version curr_credit_level_version,
--       case
--         when now() <= prohibit_expired_time then
--          1
--         when id_curr_overdue_days > 0 then
--          1
--         else
--          0
--       end as if_prohibit_apply,
       if_prohibit_apply,
       t1.if_api,
       t1.if_loan,
       case when t3.repay_indexs_cnt>0 then 1 else 0 end is_reloan_stgy,
       localtimestamp load_time,
       t8.push_token

       ,t9.curr_ovd_cnt_other_app_group_30d  --  他包近30天在逾订单数
       ,t9.curr_ovd_cnt_other_app_group_60d  --他包近60天在逾订单数
       ,t9.curr_ovd_cnt_other_app_group_90d  --他包近90天在逾订单数
       ,t9.curr_ovd_cnt_other_app_group      --他包在逾订单数
       ,t10.curr_ovd_cnt_this_app_group_30d   --本包近30天在逾订单数
       ,t10.curr_ovd_cnt_this_app_group_60d  --本包近60天在逾订单数
       ,t10.curr_ovd_cnt_this_app_group_90d  --本包近90天在逾订单数
       ,t10.curr_ovd_cnt_this_app_group      --本包在逾订单数

  from tmp.tmp_cust_apply_mid_order_tags t1
  left join tmp.tmp_cust_apply_mid_lid_tags t2
    on t1.mid = t2.mid
  left join tmp.tmp_cust_apply_mid_reapyment_tags t3
    on t1.mid = t3.mid
  left join tmp.tmp_cust_apply_mid_app_tags t4
    on t1.mid = t4.mid
  left join tmp.tmp_cust_apply_mid_newcust_tags t5
    on t1.mid = t5.mid
  left join tmp.tmp_cust_apply_mid_oldcust_tags t6
    on t1.mid = t6.mid
  left join tmp.tmp_cust_apply_mid_id_overdue_days t7
    on t1.identity_number=t7.identity_number
  left join tmp.tmp_cust_apply_push_token t8
    on t1.mid=t8.mid
  left join tmp.tmp_dwd_trans_repayment_info_curr_other t9
    on t1.mid=t9.mid
  left join tmp.tmp_dwd_trans_repayment_info_curr_this t10
    on t1.mid=t10.mid
   ;
@hive     
insert overwrite table dws.dws_cust_apply_mid_tags
select * from tmp.tmp_cust_apply_mid_tags;

--alter table dws.dws_cust_apply_mid_tags add columns(
--    curr_ovd_cnt_other_app_group_30d bigint comment '他包近30天在逾订单数',
--    curr_ovd_cnt_other_app_group_60d bigint comment '他包近60天在逾订单数',
--    curr_ovd_cnt_other_app_group_90d bigint comment '他包近90天在逾订单数',
--    curr_ovd_cnt_other_app_group bigint comment '他包在逾订单数',
--    curr_ovd_cnt_this_app_group_30d bigint comment '本包近30天在逾订单数',
--    curr_ovd_cnt_this_app_group_60d bigint comment '本包近60天在逾订单数',
--    curr_ovd_cnt_this_app_group_90d bigint comment '本包近90天在逾订单数',
--    curr_ovd_cnt_this_app_group bigint comment '本包在逾订单数'
--) ;

@presto
-- =============================================
-- Name: dws_risk_stgy_apply_mid_tags
-- Description:   
-- Author: chun song zheng
-- Created Date: 2025-12-16
-- Modified History: 
--   2025-12-16 [chun song zheng] [new create]
-- =============================================
-- DROP TABLE if EXISTS tmp.tmp_risk_stgy_apply_mid_tags;
-- CREATE TABLE tmp.tmp_risk_stgy_apply_mid_tags AS
SELECT  t1.mid
       ,t1.identity_number
       ,t3.phone_number
       ,t1.app_group
       ,CASE WHEN t1.if_api is not null THEN 'API导流'
             WHEN t3.media_source LIKE '%google%' THEN 'Google'
             WHEN lower(t3.media_source) LIKE '%facebook%' or t3.media_source = 'restricted' THEN 'facebook'
             WHEN lower(t3.media_source) LIKE '%tiktok%' or lower(t3.media_source) LIKE '%cyberads%' THEN 'tiktok'
             WHEN lower(t3.media_source) LIKE '%ads%' THEN t3.media_source
             WHEN partner is not null THEN partner
             WHEN lower(t3.media_source) LIKE '%vfine_int%' THEN 'vfine_int'
             WHEN t3.media_source LIKE 'dc1' THEN 'dc1'
             WHEN t3.media_source LIKE 'tz1' THEN 'jc'
             WHEN t3.media_source = 'SMS' AND campaign LIKE '%cl%' THEN '创蓝'
             WHEN (t3.media_source = 'SMS' AND campaign LIKE '%TZ%') or lower(t3.media_source) LIKE '%tanzhi%' THEN '探知'
             WHEN t3.media_source = '11Y' THEN '11Y'
             WHEN t3.media_source = 'bj' THEN 'bj'
             WHEN lower(t3.media_source) LIKE '%outside%' THEN '短信营销'
             WHEN lower(t3.media_source) LIKE '%duobao%' or lower(t3.media_source) LIKE '%多包互导%' or lower(t3.media_source) LIKE '%yawey%' or lower(t3.media_source) LIKE '%tengo%' or lower(t3.media_source) LIKE '%hola%' or t3.media_source = 'Email' or lower(t3.media_source) LIKE '%sms%' or lower(t3.media_source) LIKE '%app%' THEN '多包互导'
             WHEN t3.media_source LIKE 'organic' THEN 'organic'
             WHEN lower(t3.media_source) LIKE '%smark%' THEN 'smark'
             WHEN t3.media_source = '其他' THEN '其他'  ELSE '其他' END AS new_media_source
       ,t1.first_apply_date
       ,t1.last_apply_date
       ,t1.first_loan_date
       ,t1.last_loan_date
       ,t1.last_repay_date
       ,t1.last_login_date
       ,t1.onloan_cnt
       ,t1.onloan_bal
       ,t1.curr_overdue_days
       ,t1.id_curr_overdue_days
       ,t1.max_overdue_days
       ,t1.id_30days_max_overdue_days
       ,t1.if_prohibit_apply
       ,t1.is_reloan_stgy
       ,t2.newcust_credit_limit
       ,t1.newcust_credit_level
       ,t1.newcust_credit_level_version
       ,t2.curr_main_credit_limit
       ,t2.curr_main_used_credit_limit
       ,t2.curr_main_available_limit
       ,t2.curr_main_limit_expire_date
       ,t1.curr_credit_level
       ,t1.curr_credit_level_version
       ,t2.curr_temp_credit_limit
       ,t2.curr_temp_used_credit_limit
       ,t2.curr_temp_limit_expired_date
       ,localtimestamp load_time
       ,t3.realname
       ,t3.sex
       ,t3.age
       ,t1.push_token
       ,t3.random_number
       ,t4.tenant_id
       ,t2.daily_max_available_limit --decimal(38,6) COMMENT '固定额度单日最大可借上限',
       ,t2.temp_limit_issue_date_newest --date COMMENT '最新的用信临额发放日期'
       ,t1.curr_ovd_cnt_other_app_group_30d  --他包近30天在逾订单数
       ,t1.curr_ovd_cnt_other_app_group_60d  --他包近60天在逾订单数
       ,t1.curr_ovd_cnt_other_app_group_90d  --他包近90天在逾订单数
       ,t1.curr_ovd_cnt_other_app_group      --他包在逾订单数
       ,t1.curr_ovd_cnt_this_app_group_30d --本包近30天在逾订单数
       ,t1.curr_ovd_cnt_this_app_group_60d --本包近60天在逾订单数
       ,t1.curr_ovd_cnt_this_app_group_90d --本包近90天在逾订单数
       ,t1.curr_ovd_cnt_this_app_group      --本包在逾订单数
       ,t2.temp_limit_use_date_newest_diff_days --最新的用信临额使用距今天数
       ,t2.temp_limit_use_date_newest --最新的用信临额使用日期
FROM dws.dws_cust_apply_mid_tags t1
LEFT JOIN dwd.dwd_risk_stgy_credit_limit t2
ON t1.mid = t2.mid
INNER JOIN dwd.dwd_cust_base_info t3
ON t1.mid = t3.mid
left join dwd.dwd_cust_member_persons t4
on t1.mid = t4.mid
WHERE t1.if_loan = 1;

delete from dws.dws_risk_stgy_apply_mid_tags_his where data_date='$etl_date';
insert into dws.dws_risk_stgy_apply_mid_tags_his
select t.*,'$etl_date' from tmp.tmp_risk_stgy_apply_mid_tags t;
@hive     
insert overwrite table dws.dws_risk_stgy_apply_mid_tags
select * from tmp.tmp_risk_stgy_apply_mid_tags;

--alter table dws.dws_risk_stgy_apply_mid_tags  add columns (
--    temp_limit_use_date_newest_diff_days bigint COMMENT '最新的用信临额使用距今天数',
--    temp_limit_use_date_newest date COMMENT '最新的用信临额使用日期'
--);
--
--alter table dws.dws_risk_stgy_apply_mid_tags_his  add columns (
--    temp_limit_use_date_newest_diff_days bigint COMMENT '最新的用信临额使用距今天数',
--    temp_limit_use_date_newest date COMMENT '最新的用信临额使用日期'
--)cascade;
