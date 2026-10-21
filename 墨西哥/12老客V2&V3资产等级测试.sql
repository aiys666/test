
delete from mx.android_oldCust_mainCreditLevel_charge_V5_1_table
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');

-- 1、复贷资产等级决策流取资产等级相关
insert into mx.android_oldCust_mainCreditLevel_charge_V5_1_table
SELECT biz_id,
  CAST(JSON_EXTRACT(outputdata, '$.V5_fraud_score') AS DOUBLE) AS V5_fraud_score,
  CAST(JSON_EXTRACT(outputdata, '$.V5_behavior_score') AS DOUBLE) AS V5_behavior_score,
  CAST(JSON_EXTRACT(outputdata, '$.android_oldCust_voteScore_charge_V5_1') AS DOUBLE) AS android_oldCust_voteScore_charge_V5_1,
  CAST(JSON_EXTRACT(outputdata, '$.android_oldCust_mainCreditLevel_charge_V5_1') AS DOUBLE) AS android_oldCust_mainCreditLevel_charge_V5_1,
  CAST(JSON_EXTRACT(outputdata, '$.android_oldCust_midCreditLevel_charge_V5_1') AS DOUBLE) AS android_oldCust_midCreditLevel_charge_V5_1,
  CAST(JSON_EXTRACT(outputdata, '$.android_oldCust_ruleScore_charge_V5_1') AS DOUBLE) AS android_oldCust_ruleScore_charge_V5_1,
  CAST(JSON_EXTRACT(outputdata, '$.pvalue_mex_b321_2026v1_p1') AS DOUBLE) AS pvalue_mex_b321_2026v1_p1,
  CAST(JSON_EXTRACT(outputdata, '$.pvalue_mex_b320_2026v1_long_p1') AS DOUBLE) AS pvalue_mex_b320_2026v1_long_p1,
  CAST(JSON_EXTRACT(outputdata, '$.mex_b300_2025v2') AS DOUBLE) AS mex_b300_2025v2,
  CAST(JSON_EXTRACT(outputdata, '$.m698_old_1t3_voting_0619rh') AS DOUBLE) AS m698_old_1t3_voting_0619rh,
  CAST(JSON_EXTRACT(outputdata, '$.thirdparty_izi_whatsapp_register_status') AS DOUBLE) AS thirdparty_izi_whatsapp_register_status,
  CAST(JSON_EXTRACT(outputdata, '$.if_system_run_too_short') AS DOUBLE) AS if_system_run_too_short,
  CAST(JSON_EXTRACT(outputdata, '$.unique_email_cnt') AS DOUBLE) AS unique_email_cnt,
  CAST(JSON_EXTRACT(outputdata, '$.history_loanrec_cnt_lastprepaydays_v2') AS DOUBLE) AS history_loanrec_cnt_lastprepaydays_v2,
  CAST(JSON_EXTRACT(outputdata, '$.max_overdue_day_30d_all') AS DOUBLE) AS max_overdue_day_30d_all,
  CAST(JSON_EXTRACT(outputdata, '$.max_ovd_days_all') AS DOUBLE) AS max_ovd_days_all,
  CAST(JSON_EXTRACT(outputdata, '$.af_uninstall_cnt_30d') AS DOUBLE) AS af_uninstall_cnt_30d,
  CAST(JSON_EXTRACT(outputdata, '$.last_repay_gap_days_app_group') AS DOUBLE) AS last_repay_gap_days_app_group,
  CAST(JSON_EXTRACT(outputdata, '$.minstay_repayplan_second_30d_mid') AS DOUBLE) AS minstay_repayplan_second_30d_mid,
  CAST(JSON_EXTRACT(outputdata, '$.baseinfo_userprof_age') AS DOUBLE) AS baseinfo_userprof_age,
  CAST(JSON_EXTRACT(outputdata, '$.baseinfo_userprof_degree') AS DOUBLE) AS baseinfo_userprof_degree,
  CAST(JSON_EXTRACT(outputdata, '$.question3') AS DOUBLE) AS question3,
  CAST(JSON_EXTRACT(outputdata, '$.question6_v2') AS DOUBLE) AS question6_v2,
  CAST(JSON_EXTRACT(outputdata, '$.advance_duotou_cnt_730d') AS DOUBLE) AS advance_duotou_cnt_730d,
  CAST(JSON_EXTRACT(outputdata, '$.advance_duotou_cnt_x_19') AS DOUBLE) AS advance_duotou_cnt_x_19,
  createtime,
  etl_date
FROM (select *,
  row_number() over (partition by biz_id order by createtime desc) as rn 
  from ods.s21_risk_strategy_record
  WHERE 
  etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
  -- etl_date >= '20260101'
  AND strategytype = 'CHAMPION'
  AND strategymainid = 533) t0 
  where rn = 1 ;




delete from mx.tmp_darren_relimit_table
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');

-- 2、循环贷判断决策树取循环额度是否过期标签(复贷授信拒绝决策流)
insert into mx.tmp_darren_relimit_table
--- 条件从这里取
select biz_id,
  mid,
  date_add('hour',-6,createtime) dt,
  max(try_cast(json_extract_scalar(inputdata,'$.is_loop_limit_expired') as double)) is_loop_limit_expired,
  etl_date

from ods.s21_risk_model_record
where modelmainid = 1065
and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
and strategytype = 'CHAMPION'
group by 1,2,3,etl_date;


-- 3、取高通过组标签(租户首复贷判断决策流)\credit_amount&daily_max_available_limit复贷授信决策流
delete from mx.tmp_darren_product_table
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');

-- insert into mx.tmp_darren_product_table
-- select biz_id, 
--   max(cast(json_extract_scalar(outputdata, '$.fd_creditlevel_main_v4') as double)) as fd_creditlevel_main_v4,
--   max(cast(json_extract_scalar(outputdata, '$.fd_creditlevel_main_v4_2') as double)) as fd_creditlevel_main_v4_2,
--   max(cast(json_extract_scalar(outputdata, '$.fd_creditlevel_main_v3_3') as double)) as fd_creditlevel_main_v3_3,
--   max(cast(json_extract_scalar(outputdata, '$.mex_b300_2025v2') as double)) as mex_b300_2025v2,
--   max(cast(json_extract_scalar(outputdata, '$.m698_old_1t3_voting_0619rh') as double)) as m698_old_1t3_voting_0619rh,
--   max(cast(json_extract_scalar(outputdata, '$.fd_high_pass_label') as double)) as fd_high_pass_label,
--   max(cast(json_extract_scalar(outputdata, '$.credit_amount') as double)) as credit_amount,
--   max(cast(json_extract_scalar(outputdata, '$.fd_duotou_flag_20250724') as double)) as fd_duotou_flag_20250724,
--   max(cast(json_extract_scalar(outputdata, '$.daily_max_available_limit') as double)) as daily_max_available_limit,
--   max(etl_date) as etl_date
-- from(
--   select biz_id, outputdata,etl_date
--   from ods.s21_risk_strategy_record 
--   where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd') 
--     and productid in (432,426,464,331,196)  -- 20260916增加464
--     and strategytype = 'CHAMPION'
-- ) t0
-- group by 1 ;

 
insert into mx.tmp_darren_product_table
select
    a.biz_id,
    max(cast(json_extract_scalar(a.outputdata, '$.fd_creditlevel_main_v4') as double)) as fd_creditlevel_main_v4,
    max(cast(json_extract_scalar(a.outputdata, '$.fd_creditlevel_main_v4_2') as double)) as fd_creditlevel_main_v4_2,
    max(cast(json_extract_scalar(a.outputdata, '$.fd_creditlevel_main_v3_3') as double)) as fd_creditlevel_main_v3_3,
    max(cast(json_extract_scalar(a.outputdata, '$.mex_b300_2025v2') as double)) as mex_b300_2025v2,
    max(cast(json_extract_scalar(a.outputdata, '$.m698_old_1t3_voting_0619rh') as double)) as m698_old_1t3_voting_0619rh,
    max(cast(json_extract_scalar(a.outputdata, '$.fd_high_pass_label') as double)) as fd_high_pass_label,
    max(cast(json_extract_scalar(a.outputdata, '$.credit_amount') as double)) as credit_amount,
    max(cast(json_extract_scalar(a.outputdata, '$.fd_duotou_flag_20250724') as double)) as fd_duotou_flag_20250724,
    max(cast(json_extract_scalar(a.outputdata, '$.daily_max_available_limit') as double)) as daily_max_available_limit,
    max(a.etl_date) as etl_date
from ods.s21_risk_strategy_record a 
left join mx.tmp_darren_product_table b
    on a.biz_id = b.biz_id
where a.etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')  
  and a.productid in (432,426,464,331,196)
  and a.strategytype = 'CHAMPION'
  -- 核心条件二选一：
  -- 1. b.biz_id is null：tmp不存在，全新biz，重算新增
  -- 2. b.etl_date >= 近5天起始日期：tmp已有，并且它的最新日期在近5天内 → 需要刷新重算
  and ( b.biz_id is null OR b.etl_date >= to_char(date_add('day', -5, current_date), 'yyyymmdd') )  
group by 1;


delete from mx.tmp_darren_model_table
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');
-- 4、取一些欺诈、多头相关信息
--- 20260423改动：下线原来模型节点放松规则相关变量，该表名不变，监控弱反节点放松规则观测
insert into mx.tmp_darren_model_table
select biz_id, 
    max(cast(json_extract_scalar(inputdata, '$.emcontact_curr_ovd_cnt_all') as double)) as emcontact_curr_ovd_cnt_all,
    etl_date
from(
  select biz_id, inputdata, etl_date
  from ods.s21_risk_model_record 
  where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
    and modelmainId in (301)
    and strategytype = 'CHAMPION'
) t0
group by 1,3;


delete from mx.tmp_darren_temp_limit_table
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');

-- 5、临额发放弹窗决策流(临额发放判断标签决策树)取满额动支临额相关
insert into mx.tmp_darren_temp_limit_table
--- 条件从这里取
select biz_id,
  mid,
  date_add('hour',-6,createtime) dt,
  max(try_cast(json_extract_scalar(inputdata,'$.fd_creditlevel_main_v4_2_snapshot') as double)) fd_creditlevel_main_v4_2_snapshot,
  max(try_cast(json_extract_scalar(inputdata,'$.fd_main_creditlevel_v5_1_snapshot') as double)) fd_main_creditlevel_v5_1_snapshot,
  max(try_cast(json_extract_scalar(inputdata,'$.last_used_credit_amount') as double)) last_used_credit_amount,
  max(try_cast(json_extract_scalar(inputdata,'$.last_temp_credit_amount_issue_day_gap') as double)) last_temp_credit_amount_issue_day_gap,
  max(try_cast(json_extract_scalar(inputdata,'$.last_credit_amount') as double)) last_credit_amount,
  max(try_cast(json_extract_scalar(outputdata,'$.temp_credit_amount_issue_tag') as double)) temp_credit_amount_issue_tag,
  etl_date

from ods.s21_risk_model_record
where modelmainid = 1386
-- and etl_date >= '20260114'
and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
and strategytype = 'CHAMPION'
group by 1,2,3,etl_date;



delete from mx.tmp_darren_new_temp_limit_table
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');

-- 5、临额发放弹窗决策流(临额发放判断标签决策树)取满额动支临额相关
insert into mx.tmp_darren_new_temp_limit_table
--- 条件从这里取
select biz_id,
  mid,
  date_add('hour',-6,createtime) dt,
  max(try_cast(json_extract_scalar(inputdata,'$.fd_use_creditamount_score_v1') as double)) fd_use_creditamount_score_v1,
  max(try_cast(json_extract_scalar(outputdata,'$.fd_use_creditamount_type') as double)) fd_use_creditamount_type,
  etl_date

from ods.s21_risk_model_record
where modelmainid = 1523
-- and etl_date >= '20260501'
and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
and strategytype = 'CHAMPION'
group by 1,2,3,etl_date;


delete from mx.tmp_darren_limit_cap_table
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');
-- 6、从复贷授信拒绝决策流取全局额度超cap1.8倍则cap回1.5相关(从inputdata取)
insert into mx.tmp_darren_limit_cap_table
--- 条件从这里取
select biz_id,
  mid,
  date_add('hour',-6,createtime) dt,
  max(try_cast(json_extract_scalar(inputdata,'$.fd_global_limit_cap') as double)) fd_global_limit_cap,
  max(try_cast(json_extract_scalar(inputdata,'$.credit_amount') as double)) credit_amount,
  etl_date

from ods.s21_risk_model_record
where modelid in (4404,4596)
-- and etl_date >= '20260122'
and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
and strategytype = 'CHAMPION'
group by 1,2,3,etl_date;




-- 删除目标表中前一天及之后的分区数据
delete from mx.tmp_darren_if_product_or_maxlimit_change_tag_table
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');

-- 20260428 更新为modelmainid取
-- 7、取产品 单日可借上限  金融属性延续相关
-- 插入前一天及之后的新数据
insert into mx.tmp_darren_if_product_or_maxlimit_change_tag_table
select
  t0.biz_id,
  case when last_product_level != product_level or last_daily_max_available_limit != daily_max_available_limit then '前后不一致'
    when last_product_level = product_level and last_daily_max_available_limit = daily_max_available_limit then '前后一致'
  end as if_product_or_maxlimit_change_tag,
  createtime,
  t0.etl_date   -- 从主表获取 etl_date 作为分区字段
from (
  -- 复贷授信拒绝决策流 读取last_credit_amount决策树
  select biz_id,
    cast(json_extract_scalar(inputdata, '$.last_product_level') as varchar) as last_product_level,
    cast(json_extract_scalar(inputdata, '$.last_daily_max_available_limit') as double) as last_daily_max_available_limit,
    createtime,
    etl_date   
  from ods.s21_risk_model_record
  where modelmainid = 1067
  -- modelid in (4505,4506)
    -- and etl_date >= '20260209'
    and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
    and strategytype = 'CHAMPION'
    AND strategymainid = 472
) t0
left join (
  -- 复贷授信拒绝决策树复贷授信拒绝决策树取
  select biz_id,
    cast(json_extract_scalar(outputdata, '$.product_level') as varchar) as product_level
  from ods.s21_risk_model_record
  where modelmainid = 822
  -- modelid in (4470,4496)
    -- and etl_date >= '20260209'
    and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
    and strategytype = 'CHAMPION'
    AND strategymainid = 472
) t1 on t0.biz_id = t1.biz_id
left join (
  select biz_id,
    cast(json_extract_scalar(outputdata, '$.daily_max_available_limit') as double) as daily_max_available_limit
  from ods.s21_risk_model_record
  where modelmainid = 1077
    -- and etl_date >= '20260209'
    and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
    and strategytype = 'CHAMPION'
    AND strategymainid = 472
) t2 on t0.biz_id = t2.biz_id;



-- 删除目标分区中前一天及之后的数据（保证幂等性）
DELETE FROM mx.tmp_curr_ovd_table
WHERE etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');

-- 插入当天符合条件的数据（每个 externalid 取最新一条记录）
INSERT INTO mx.tmp_curr_ovd_table
SELECT 
  t1.externalid,
  t1.mid,
  t1.createtime,
  coalesce(t1.curr_ovd_cnt_all,t2.curr_ovd_cnt_all) as curr_ovd_cnt_all,
  coalesce(t1.curr_ovd_cnt_other_app_group_30d,t2.curr_ovd_cnt_other_app_group_30d) as curr_ovd_cnt_other_app_group_30d,
  coalesce(t1.curr_ovd_cnt_other_app_group_60d,t2.curr_ovd_cnt_other_app_group_60d) as curr_ovd_cnt_other_app_group_60d,
  coalesce(t1.curr_ovd_cnt_other_app_group_90d,t2.curr_ovd_cnt_other_app_group_90d) as curr_ovd_cnt_other_app_group_90d,
  coalesce(t1.curr_ovd_cnt_this_app_group,t2.curr_ovd_cnt_this_app_group) as curr_ovd_cnt_this_app_group,
  coalesce(t1.curr_ovd_cnt_other_app_group,t2.curr_ovd_cnt_other_app_group) as curr_ovd_cnt_other_app_group,
  t1.etl_date
FROM (
  select *
  from (
  SELECT 
    externalid,
    mid,
    inputdata,
    etl_date,
    createtime,
    CAST(json_extract_scalar(inputdata, '$.curr_ovd_cnt_all') AS double) AS curr_ovd_cnt_all,
    CAST(json_extract_scalar(inputdata, '$.curr_ovd_cnt_other_app_group_30d') AS double) AS curr_ovd_cnt_other_app_group_30d,
    CAST(json_extract_scalar(inputdata, '$.curr_ovd_cnt_other_app_group_60d') AS double) AS curr_ovd_cnt_other_app_group_60d,
    CAST(json_extract_scalar(inputdata, '$.curr_ovd_cnt_other_app_group_90d') AS double) AS curr_ovd_cnt_other_app_group_90d,
    CAST(json_extract_scalar(inputdata, '$.curr_ovd_cnt_this_app_group') AS double) AS curr_ovd_cnt_this_app_group,
    CAST(json_extract_scalar(inputdata, '$.curr_ovd_cnt_other_app_group') AS double) AS curr_ovd_cnt_other_app_group,
    ROW_NUMBER() OVER (PARTITION BY externalid ORDER BY createtime) AS rn
  FROM ods.s21_risk_model_record
  WHERE modelmainid in (282)
    AND strategytype = 'CHAMPION'
    AND etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')) t0 
  where rn = 1
) t1 
left join (
  select *
  from (
  SELECT 
    externalid,
    mid,
    inputdata,
    etl_date,
    createtime,
    CAST(json_extract_scalar(inputdata, '$.curr_ovd_cnt_all') AS double) AS curr_ovd_cnt_all,
    CAST(json_extract_scalar(inputdata, '$.curr_ovd_cnt_other_app_group_30d') AS double) AS curr_ovd_cnt_other_app_group_30d,
    CAST(json_extract_scalar(inputdata, '$.curr_ovd_cnt_other_app_group_60d') AS double) AS curr_ovd_cnt_other_app_group_60d,
    CAST(json_extract_scalar(inputdata, '$.curr_ovd_cnt_other_app_group_90d') AS double) AS curr_ovd_cnt_other_app_group_90d,
    CAST(json_extract_scalar(inputdata, '$.curr_ovd_cnt_this_app_group') AS double) AS curr_ovd_cnt_this_app_group,
    CAST(json_extract_scalar(inputdata, '$.curr_ovd_cnt_other_app_group') AS double) AS curr_ovd_cnt_other_app_group,
    ROW_NUMBER() OVER (PARTITION BY externalid ORDER BY createtime) AS rn
  FROM ods.s21_risk_model_record
  WHERE modelmainid in (301)
    AND strategytype = 'CHAMPION'
    AND etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')) t0 
  where rn = 1) t2 
on t1.externalid = t2.externalid;





drop table if EXISTS mx.yj_test_table_250225;
CREATE table mx.yj_test_table_250225 as
select *
,case when  (max_overdue_day_30d_all >= 1 or emcontact_curr_ovd_cnt_all > 0 or
other_app_has_loan_flag >= 1 and other_app_has_overdue_interval_tag='在逾订单发生在90天外') then 1 else 0 end as release_flag-- 3个放松客群只要命中一者就算
,case when first_grantcredit_7d_amount<=500 then 1 else 0 end as low_limit_flag-- 小金额客群
,CASE WHEN mex_b300_2025v2 <= 0.163083 THEN '(-inf, 0.163083]'
  WHEN mex_b300_2025v2 > 0.163083 AND mex_b300_2025v2 <= 0.188569 THEN '(0.163083, 0.188569]'
  WHEN mex_b300_2025v2 > 0.188569 AND mex_b300_2025v2 <= 0.21973 THEN '(0.188569, 0.21973]'
  WHEN mex_b300_2025v2 > 0.21973 AND mex_b300_2025v2 <= 0.255985 THEN '(0.21973, 0.255985]'
  WHEN mex_b300_2025v2 > 0.255985 AND mex_b300_2025v2 <= 0.279371 THEN '(0.255985, 0.279371]'
  WHEN mex_b300_2025v2 > 0.279371 AND mex_b300_2025v2 <= 0.302361 THEN '(0.279371, 0.302361]'
  WHEN mex_b300_2025v2 > 0.302361 AND mex_b300_2025v2 <= 0.341002 THEN '(0.302361, 0.341002]'
  WHEN mex_b300_2025v2 > 0.341002 AND mex_b300_2025v2 <= 0.371907 THEN '(0.341002, 0.371907]'
  WHEN mex_b300_2025v2 > 0.371907 THEN '(0.371907, inf]' END AS m699_rh_new_bin,
concat(last_product_level,'-',product_level) as product_level_change,-- 转产线前后产品拼接
case when curr_biz_id is not null then '转产线' else '未转产线' end as change_product_tag,-- 是否转产线标签
from_base(substr(to_hex(sha256(to_utf8('20251106'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 as randd
  -- 进件角度看单日可借上限差异
,case when app_time >= date'2026-04-03' and v3_flag in ('V5_2') and from_base(substr(to_hex(sha256(to_utf8('20251217'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v5_2测试组'
    when app_time >= date'2026-04-03' and v3_flag in ('V5_2') and from_base(substr(to_hex(sha256(to_utf8('20251217'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v5_2冠军组'
    when app_time >= date'2026-02-09' and v3_flag in ('V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251217'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v4_2测试组'
    when app_time >= date'2026-02-09' and v3_flag in ('V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251217'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v4_2冠军组'
    when app_time >= date'2026-02-09' and v3_flag in ('V5_1') and from_base(substr(to_hex(sha256(to_utf8('20251217'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v5_1测试组'
    when app_time >= date'2026-02-09' and v3_flag in ('V5_1') and from_base(substr(to_hex(sha256(to_utf8('20251217'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v5_1冠军组'
    when app_time>= date'2025-12-16' and v3_flag in ('V4_2','原V3_3现V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251217'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v4_2测试组'
    when app_time>= date'2025-12-16' and v3_flag in ('V4_2','原V3_3现V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251217'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v4_2冠军组'
    when app_time>= date'2025-10-29' and v3_flag in ('V4_2','原V3_3现V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251010'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v4_2测试组'
    when app_time>= date'2025-10-29' and v3_flag in ('V4_2','原V3_3现V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251010'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v4_2冠军组'
    when app_time>= date'2025-10-29' and v3_flag = 'V3_3' and from_base(substr(to_hex(sha256(to_utf8('20251010'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v3_3测试组'
    when app_time>= date'2025-10-29' and v3_flag = 'V3_3' and from_base(substr(to_hex(sha256(to_utf8('20251010'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v3_3冠军组'
    when from_base(substr(to_hex(sha256(to_utf8('20251010'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.5 then '冠军组'
    when from_base(substr(to_hex(sha256(to_utf8('20251010'||phone||app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then '测试组'
      end as daily_max_limit_tag,

  CASE WHEN thirdparty_izi_whatsapp_register_status = 0 THEN '-1 [=0]'
    WHEN thirdparty_izi_whatsapp_register_status = 1 THEN '0 [=1]'
  END AS thirdparty_izi_whatsapp_register_status_score,
  CASE WHEN if_system_run_too_short = 1 THEN '0 [=1]'
    WHEN if_system_run_too_short = 0 THEN '0 [=0]'
  END AS if_system_run_too_short_score,
  CASE WHEN unique_email_cnt > 1 THEN '-1 [>1]'
    WHEN unique_email_cnt <= 1 THEN '0 [≤1]'
  END AS unique_email_cnt_score,
  CASE WHEN history_loanrec_cnt_lastprepaydays_v2 <= -30 THEN '-10 [≤ -30]'
    WHEN history_loanrec_cnt_lastprepaydays_v2 <= -2  THEN '-8 [-30 < x ≤ -2]'
    WHEN history_loanrec_cnt_lastprepaydays_v2 <= -1  THEN '-5 [-2 < x ≤ -1]'
    WHEN history_loanrec_cnt_lastprepaydays_v2 <= 0   THEN '-2 [-1 < x ≤ 0]'
    WHEN history_loanrec_cnt_lastprepaydays_v2 > 0    THEN '0 [>0]'
  END AS history_loanrec_cnt_lastprepaydays_v2_score,
  CASE WHEN max_overdue_day_30d_all < 0  THEN '-3 [<0]'
    WHEN max_overdue_day_30d_all >= 0 THEN '0 [≥0]'
  END AS max_overdue_day_30d_all_score,
  CASE WHEN max_ovd_days_all > 3  THEN '-2 [>3]'
    WHEN max_ovd_days_all > 0  THEN '-1 [0 < x ≤ 3]'
    WHEN max_ovd_days_all <= 0 THEN '0 [≤0]'
  END AS max_ovd_days_all_score,
  CASE WHEN af_uninstall_cnt_30d < 1   THEN '0 [<1]'
    WHEN af_uninstall_cnt_30d < 2   THEN '-2 [1 ≤ x < 2]'
    WHEN af_uninstall_cnt_30d >= 2  THEN '-3 [≥2]'
  END AS af_uninstall_cnt_30d_score,
  CASE WHEN last_repay_gap_days_app_group < 1   THEN '0 [<1]'
    WHEN last_repay_gap_days_app_group < 14  THEN '1 [1 ≤ x < 14]'
    WHEN last_repay_gap_days_app_group < 30  THEN '0 [14 ≤ x < 30]'
    WHEN last_repay_gap_days_app_group >= 30 THEN '-3 [≥30]'
  END AS last_repay_gap_days_app_group_score,
  CASE WHEN minstay_repayplan_second_30d_mid < 10  THEN '0 [<10]'
    WHEN minstay_repayplan_second_30d_mid >= 10 THEN '1 [≥10]'
    ELSE '0 [else]'
  END AS minstay_repayplan_second_30d_mid_score,
  CASE WHEN baseinfo_userprof_age < 35  THEN '-1 [<35]'
    WHEN baseinfo_userprof_age <= 60 THEN '0 [35 ≤ x ≤ 60]'
    WHEN baseinfo_userprof_age > 60  THEN '3 [>60]'
  END AS baseinfo_userprof_age_score,
  CASE WHEN baseinfo_userprof_degree <= 3 THEN '-1 [≤3]'
    WHEN baseinfo_userprof_degree <= 4 THEN '0 [3 < x ≤ 4]'
    WHEN baseinfo_userprof_degree <= 5 THEN '1 [4 < x ≤ 5]'
    WHEN baseinfo_userprof_degree <= 6 THEN '3 [5 < x ≤ 6]'
  END AS baseinfo_userprof_degree_score,
  CASE WHEN question3 > 5 THEN '1 [>5]'
     WHEN question3 <= 5 THEN '0 [≤5]'
  END AS question3_score,
  CASE WHEN question6_v2 >= 10 THEN '2 [≥10]'
    when question6_v2 < 10 THEN '0 [<10]'
  END AS question6_v2_score,
  CASE WHEN advance_duotou_cnt_x_19 < 2   THEN '0 [<2]'
    WHEN advance_duotou_cnt_x_19 <= 4  THEN '1 [2 ≤ x ≤ 4]'
    WHEN advance_duotou_cnt_x_19 <= 6  THEN '-2 [4 < x ≤ 6]'
    WHEN advance_duotou_cnt_x_19 > 6   THEN '-8 [>6]'
  END AS advance_duotou_cnt_x_19_score,
  CASE WHEN advance_duotou_cnt_730d <= 0   THEN '0 [≤0]'
    WHEN advance_duotou_cnt_730d <= 2   THEN '-1 [0 < x ≤ 2]'
    WHEN advance_duotou_cnt_730d <= 11  THEN '0 [2 < x ≤ 11]'
    WHEN advance_duotou_cnt_730d > 11   THEN '-1 [>11]'
  END AS advance_duotou_cnt_730d_score,
  CASE WHEN V5_3_fraud_score <= -10 THEN '-7 [≤ -10]'
    WHEN V5_3_fraud_score <= -5  THEN '-5 [-10 < x ≤ -5]'
    WHEN V5_3_fraud_score <= -2  THEN '-1 [-5 < x ≤ -2]'
    WHEN V5_3_fraud_score > -2   THEN '0 [> -2]'
  END AS V5_3_fraud_group_score,
  CASE WHEN V5_3_behavior_score >= 3   THEN '2 [≥3]'
    WHEN V5_3_behavior_score >= -1  THEN '0 [-1 ≤ x < 3]'
    WHEN V5_3_behavior_score >= -3  THEN '-2 [-3 ≤ x < -1]'
    WHEN V5_3_behavior_score >= -8  THEN '-3 [-8 ≤ x < -3]'
    WHEN V5_3_behavior_score < -8   THEN '-5 [< -8]'
  END AS V5_3_behavior_group_score,
  CASE WHEN m698_old_1t3_voting_0619rh < 0.185  THEN '2 [<0.185]'
    WHEN m698_old_1t3_voting_0619rh < 0.31   THEN '-1 [0.185 ≤ x < 0.31]'
    WHEN m698_old_1t3_voting_0619rh < 0.455  THEN '-6 [0.31 ≤ x < 0.455]'
    WHEN m698_old_1t3_voting_0619rh >= 0.455 THEN '-12 [≥0.455]'
  END AS model_698_score,
  CASE WHEN mex_b300_2025v2  < 0.18   THEN '1 [<0.18]'
    WHEN mex_b300_2025v2 < 0.39    THEN '-2 [0.18 ≤ x < 0.39]'
    WHEN mex_b300_2025v2 < 0.475   THEN '-6 [0.39 ≤ x < 0.475]'
    WHEN mex_b300_2025v2 >= 0.475  THEN '-12 [≥0.475]'
  END AS model_699_score,
  CASE WHEN pvalue_mex_b321_2026v1_p1 < 0.1762  THEN '2 [<0.1762]'
    WHEN pvalue_mex_b321_2026v1_p1 < 0.2381  THEN '-4 [0.1762 ≤ x < 0.2381]'
    WHEN pvalue_mex_b321_2026v1_p1 < 0.3287  THEN '-9 [0.2381 ≤ x < 0.3287]'
    WHEN pvalue_mex_b321_2026v1_p1 >= 0.3287 THEN '-15 [≥0.3287]'
  END AS model_p2_1t_score,
  CASE WHEN android_oldCust_voteScore_charge_V5_3 > -4  THEN '1 [>-4]'
    WHEN android_oldCust_voteScore_charge_V5_3 > -14 THEN '2 [>-14]'  
    WHEN android_oldCust_voteScore_charge_V5_3 > -27 THEN '3 [>-27]' end as android_oldCust_voteScore_charge_V5_3_bin,
  CASE WHEN android_oldCust_ruleScore_charge_V5_3 > 0 THEN '1 [>0]'   
    WHEN android_oldCust_ruleScore_charge_V5_3 > -1  THEN '2 [>-1]'    
    WHEN android_oldCust_ruleScore_charge_V5_3 > -3  THEN '3 [>-3]'  
    WHEN android_oldCust_ruleScore_charge_V5_3 > -7  THEN '4 [>-7]'  end as android_oldCust_ruleScore_charge_V5_3_bin
  ,case when app_time >= date'2026-07-01' then 
  case when last_product_level is not null and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and fd_changepro_V5_3>=1 and fd_changepro_V5_3<=7 then 'base_头部_B_07_03_00_60'
   when last_product_level is not null and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and fd_changepro_V5_3>=8 then 'base_中尾部_B_07_03_00_60'
   when last_product_level is not null and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V5_3>=1 and fd_changepro_V5_3<=7 then 'test_头部_C_15_03_00_85'
   when last_product_level is not null and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V5_3>=8  then 'test_中尾部_C_07_04_00_85'
        else '未转产' end end
 as product_level_test_260701
   ,case when app_time >= date'2026-09-20' and last_product_level is not null  then 
   case when v3_flag='V5_3'  then  
  case when from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and fd_changepro_V5_3>=1 and fd_changepro_V5_3<=2 then 'base_1档_B_07_03_00_60'
  when from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V5_3>=1 and fd_changepro_V5_3<=2 then 'test_1档_B_07_04_00_75'
   when from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and fd_changepro_V5_3>=3 and fd_changepro_V5_3<=6 then 'base_2档_B_07_03_00_60'
  when from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V5_3>=3 and fd_changepro_V5_3<=6 then 'test_2档_C_07_04_00_75'
  when from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and fd_changepro_V5_3>=7 and fd_changepro_V5_3<=10 then 'test_3档_B_07_03_00_60'
  when from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V5_3>=7 and fd_changepro_V5_3<=10 then 'base_3档_C_07_03_00_75'
  when from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and  fd_changepro_V5_3>10 then 'test_4档_C_07_03_00_85'
  when from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V5_3>10 then 'base_4档_B_07_02_00_75' else '未转产' end 
  when v3_flag='V6_1'  then 
  case when  from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and fd_changepro_V6_1>=1 and fd_changepro_V6_1<=3 then 'base_1档_B_07_03_00_60'
  when  from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V6_1>=1 and fd_changepro_V6_1<=3 then 'test_1档_B_07_04_00_75'
   when  from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and fd_changepro_V6_1>=4 and fd_changepro_V6_1<=6 then 'base_2档_B_07_03_00_60'
  when  from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V6_1>=4 and fd_changepro_V6_1<=6 then 'test_2档_C_07_04_00_75'
  when  from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and fd_changepro_V6_1>=7 and fd_changepro_V6_1<=8 then 'test_3档_B_07_03_00_60'
  when  from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V6_1>=7 and fd_changepro_V6_1<=8 then 'base_3档_C_07_03_00_75'
  when  from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and  fd_changepro_V6_1>8 then 'test_4档_C_07_03_00_85'
  when  from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V6_1>8 then 'base_4档_B_07_02_00_75' end end
   
  when app_time >= date'2026-07-22' and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 
  case when v3_flag='V5_3'  then 
  case when last_product_level is not null and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and fd_changepro_V5_3>=1 and fd_changepro_V5_3<=2 then 'base_1档_B_07_03_00_60'
  when last_product_level is not null and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V5_3>=1 and fd_changepro_V5_3<=2 then 'test_1档_B_07_04_00_75'
   when last_product_level is not null and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and fd_changepro_V5_3>=3 and fd_changepro_V5_3<=6 then 'base_2档_B_07_03_00_60'
  when last_product_level is not null and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V5_3>=3 and fd_changepro_V5_3<=6 then 'test_2档_C_07_04_00_75'
  when last_product_level is not null and fd_changepro_V5_3>=7 and fd_changepro_V5_3<=10 then 'base_3档_C_07_03_00_75'
  when last_product_level is not null and fd_changepro_V5_3>10 then 'test_4档_B_07_02_00_75'  end 
  when v3_flag='V6_1'  then 
  case when last_product_level is not null and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and fd_changepro_V6_1>=1 and fd_changepro_V6_1<=3 then 'base_1档_B_07_03_00_60'
  when last_product_level is not null and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V6_1>=1 and fd_changepro_V6_1<=3 then 'test_1档_B_07_04_00_75'
   when last_product_level is not null and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 and fd_changepro_V6_1>=4 and fd_changepro_V6_1<=6 then 'base_2档_B_07_03_00_60'
  when last_product_level is not null and from_base(substr(to_hex(sha256(to_utf8('20251107'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 and fd_changepro_V6_1>=4 and fd_changepro_V6_1<=6 then 'test_2档_C_07_04_00_75'
  when last_product_level is not null  and fd_changepro_V6_1>=7 and fd_changepro_V6_1<=8 then 'base_3档_C_07_03_00_75'
  when last_product_level is not null  and fd_changepro_V6_1>8 then 'base_4档_B_07_02_00_75' end end 
  end as product_level_change_test_260722,
 case  when if_in_sx_24h<>1 then '01.距离授信不足24h'
         when if_in_sx_24h=1 and if_SX_passed_24h=1 then '02.24h用信'
         when if_in_sx_24h=1 and change_flag='01.24H转产' and app_time< date'2026-07-16' then '03.执行24h未用信转产' 
         when if_in_sx_24h=1 and change_flag<>'01.24H转产' and app_time< date'2026-07-16' then '04.执行48h未用转产'
         when if_in_sx_24h=1 and app_time>=date'2026-07-16' then '03.执行24h未用信转产' 
   else ''
   end as change_flag1
,case when app_time >= date'2026-07-22' then 
      case when COALESCE(last_product_level, product_level)='C_07_04_00_75' and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'base_1档_C_07_04_00_75'
      when COALESCE(last_product_level, product_level)='D_1_03' and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'test_1档_D_1_03'
        when COALESCE(last_product_level, product_level)='C_07_03_00_75' and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'base_2档_C_07_03_00_75'
        when COALESCE(last_product_level, product_level)='D_1_04' and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'test_2档_D_1_04'
        when COALESCE(last_product_level, product_level)='B_07_02_00_75' and  app_time < date'2026-09-15' and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'base_3档_B_07_02_00_75'
        when COALESCE(last_product_level, product_level)='D_1_05' and  app_time < date'2026-09-15' and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'test_3档_D_1_05'
        -- 9.15灰度50%测试C_07_03_00_85
        when COALESCE(last_product_level, product_level)='B_07_02_00_75' and  app_time >= date'2026-09-15' and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 then 'base_3档_B_07_02_00_75'
        when COALESCE(last_product_level, product_level)='C_07_03_00_85' and  app_time >= date'2026-09-15' and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 then 'test_3档_C_07_03_00_85'
         when COALESCE(last_product_level, product_level)='A_07_01_50_00' and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'base_4档_A_07_01_50_00'
        when COALESCE(last_product_level, product_level)='D_1_06'  and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'test_4档_D_1_06' end end as product_test_0722
,case when app_time >= date'2026-07-22' and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7
then 'base组'
when app_time >= date'2026-07-22' and from_base(substr(to_hex(sha256(to_utf8('20260512'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7
then 'test组' end as product_random_0722,

-- 1. stgy_advance_gd_x_34_score (无重名)
CASE 
  WHEN stgy_advance_gd_x_34 >= 4 THEN '-1 [>=4]'
  WHEN stgy_advance_gd_x_34 < 4 THEN '0 [<4]'
END AS stgy_advance_gd_x_34_score,

-- 2. stgy_advance_gd_x_12_score (无重名)
CASE 
  WHEN stgy_advance_gd_x_12 < 5 THEN '0 [<5]'
  WHEN stgy_advance_gd_x_12 >= 5 THEN '-1 [>=5]'
END AS stgy_advance_gd_x_12_score,

-- 3. stgy_advance_gd_x_55_score (无重名)
CASE 
  WHEN stgy_advance_gd_x_55 <= 1 THEN '0 [≤1]'
  WHEN stgy_advance_gd_x_55 IN (2, 3) THEN '1 [2或3]'
  WHEN stgy_advance_gd_x_55 >= 4 THEN '-1 [≥4]'
END AS stgy_advance_gd_x_55_score,

-- 4. stgy_bj_apply_jgs_12m_score (无重名)
CASE 
  WHEN stgy_bj_apply_jgs_12m = -98 OR stgy_bj_apply_jgs_12m = 0 THEN '-1 [=-98或0]'
  WHEN stgy_bj_apply_jgs_12m > 0 THEN '0 [>0]'
END AS stgy_bj_apply_jgs_12m_score,

-- 5. stgy_bj_apply_jgs_1w_score (无重名)
CASE 
  WHEN stgy_bj_apply_jgs_1w = -98 THEN '0 [=-98]'
  WHEN stgy_bj_apply_jgs_1w BETWEEN 0 AND 3 THEN '1 [0≤x≤3]'
  WHEN stgy_bj_apply_jgs_1w >= 4 THEN '-2 [≥4]'
END AS stgy_bj_apply_jgs_1w_score,

-- 6. stgy_bj_apply_count_1w_score (无重名)
CASE 
  WHEN stgy_bj_apply_count_1w = -98 THEN '0 [=-98]'
  WHEN stgy_bj_apply_count_1w BETWEEN 0 AND 2 THEN '0 [0≤x≤2]'
  WHEN stgy_bj_apply_count_1w BETWEEN 3 AND 7 THEN '-1 [3≤x≤7]'
  WHEN stgy_bj_apply_count_1w >= 8 THEN '-2 [≥8]'
END AS stgy_bj_apply_count_1w_score,

-- 7. app_loan1_inst_cnt_day7_score (无重名)
CASE 
  WHEN app_loan1_inst_cnt_day7 = 0 THEN '1 [=0]'
  WHEN app_loan1_inst_cnt_day7 = 1 THEN '0 [=1]'
  WHEN app_loan1_inst_cnt_day7 = 2 THEN '-1 [=2]'
  WHEN app_loan1_inst_cnt_day7 BETWEEN 3 AND 5 THEN '-2 [3≤x≤5]'
  WHEN app_loan1_inst_cnt_day7 BETWEEN 6 AND 9 THEN '-3 [6≤x≤9]'
  WHEN app_loan1_inst_cnt_day7 >= 10 THEN '-4 [≥10]'
END AS app_loan1_inst_cnt_day7_score,

-- 8. app3_mix_loan1_cfinst_cnt_d30_score (无重名)
CASE 
  WHEN app3_mix_loan1_cfinst_cnt_d30 = 0 THEN '1 [=0]'
  WHEN app3_mix_loan1_cfinst_cnt_d30 = 1 THEN '0 [=1]'
  WHEN app3_mix_loan1_cfinst_cnt_d30 = 2 THEN '-1 [=2]'
  WHEN app3_mix_loan1_cfinst_cnt_d30 BETWEEN 3 AND 4 THEN '-2 [3≤x≤4]'
  WHEN app3_mix_loan1_cfinst_cnt_d30 BETWEEN 5 AND 9 THEN '-3 [5≤x≤9]'
  WHEN app3_mix_loan1_cfinst_cnt_d30 >= 10 THEN '-4 [≥10]'
END AS app3_mix_loan1_cfinst_cnt_d30_score,

-- 9. advance_duotou_cnt_x_19_score -> 重名，改为 _v6
CASE 
  WHEN advance_duotou_cnt_x_19 < 2 THEN '0 [<2]'
  WHEN advance_duotou_cnt_x_19 BETWEEN 2 AND 4 THEN '1 [2≤x≤4]'
  WHEN advance_duotou_cnt_x_19 > 4 AND advance_duotou_cnt_x_19 <= 6 THEN '-2 [4<x≤6]'
  WHEN advance_duotou_cnt_x_19 > 6 THEN '-8 [>6]'
END AS advance_duotou_cnt_x_19_score_v6,

-- 10. advance_duotou_cnt_730d_score -> 重名，改为 _v6
CASE 
  WHEN advance_duotou_cnt_730d <= 0 THEN '0 [≤0]'
  WHEN advance_duotou_cnt_730d > 0 AND advance_duotou_cnt_730d <= 2 THEN '-1 [0<x≤2]'
  WHEN advance_duotou_cnt_730d > 2 AND advance_duotou_cnt_730d <= 11 THEN '0 [2<x≤11]'
  WHEN advance_duotou_cnt_730d > 11 THEN '-1 [>11]'
END AS advance_duotou_cnt_730d_score_v6,

-- 11. beh2_o_create_reject_pct_d7_score (无重名)
CASE 
  WHEN beh2_o_create_reject_pct_d7 <= 0 THEN '0 [≤0]'
  WHEN beh2_o_create_reject_pct_d7 > 0 THEN '-3 [>0]'
  ELSE '0'
END AS beh2_o_create_reject_pct_d7_score,

-- 12. beh_main_reject_applypct_day60_score (无重名)
CASE 
  WHEN beh_main_reject_applypct_day60 >= 0 AND beh_main_reject_applypct_day60 < 0.3 THEN '0 [0≤x<0.3]'
  WHEN beh_main_reject_applypct_day60 >= 0.3 AND beh_main_reject_applypct_day60 < 0.6 THEN '-1 [0.3≤x<0.6]'
  WHEN beh_main_reject_applypct_day60 >= 0.6 AND beh_main_reject_applypct_day60 < 0.9 THEN '-2 [0.6≤x<0.9]'
  WHEN beh_main_reject_applypct_day60 >= 0.9 THEN '-3 [≥0.9]'
  ELSE '0'
END AS beh_main_reject_applypct_day60_score,

-- 13. stgy_dyna_amlta_d60_daydiff_median_score (无重名)
CASE 
  WHEN stgy_dyna_amlta_d60_daydiff_median < -98 THEN '-1 [<-98]'
  WHEN stgy_dyna_amlta_d60_daydiff_median < 0 AND stgy_dyna_amlta_d60_daydiff_median >= -98 THEN '-2 [-98≤x<0]'
  WHEN stgy_dyna_amlta_d60_daydiff_median >= 0 AND stgy_dyna_amlta_d60_daydiff_median <= 15 THEN '-1 [0≤x≤15]'
  WHEN stgy_dyna_amlta_d60_daydiff_median > 15 AND stgy_dyna_amlta_d60_daydiff_median <= 25 THEN '0 [15<x≤25]'
  WHEN stgy_dyna_amlta_d60_daydiff_median > 25 THEN '1 [>25]'
  ELSE '0'
END AS stgy_dyna_amlta_d60_daydiff_median_score,

-- 14. stgy_amlta_d180_record_date_unique_cnt_score (无重名)
CASE 
  WHEN stgy_amlta_d180_record_date_unique_cnt < -98 THEN '-2 [<-98]'
  WHEN stgy_amlta_d180_record_date_unique_cnt >= -98 AND stgy_amlta_d180_record_date_unique_cnt <= 0 THEN '0 [-98≤x≤0]'
  WHEN stgy_amlta_d180_record_date_unique_cnt > 0 AND stgy_amlta_d180_record_date_unique_cnt <= 20 THEN '-1 [0<x≤20]'
  WHEN stgy_amlta_d180_record_date_unique_cnt > 20 AND stgy_amlta_d180_record_date_unique_cnt <= 47 THEN '0 [20<x≤47]'
  WHEN stgy_amlta_d180_record_date_unique_cnt > 47 AND stgy_amlta_d180_record_date_unique_cnt <= 99 THEN '1 [47<x≤99]'
  WHEN stgy_amlta_d180_record_date_unique_cnt > 99 THEN '1 [>99]'
  ELSE '0'
END AS stgy_amlta_d180_record_date_unique_cnt_score,

-- 15. stgy_dyna_amlba_d30_c_cnt_score (无重名)
CASE 
  WHEN stgy_dyna_amlba_d30_c_cnt <= 0 THEN '0 [≤0]'
  WHEN stgy_dyna_amlba_d30_c_cnt > 0 THEN '-1 [>0]'
  ELSE '0'
END AS stgy_dyna_amlba_d30_c_cnt_score,

-- 16. stgy_dyna_amlba_d21_b_cnt_score (无重名)
CASE 
  WHEN stgy_dyna_amlba_d21_b_cnt < -98 THEN '-1 [<-98]'
  WHEN stgy_dyna_amlba_d21_b_cnt >= -98 AND stgy_dyna_amlba_d21_b_cnt <= 0 THEN '-2 [-98≤x≤0]'
  WHEN stgy_dyna_amlba_d21_b_cnt > 0 THEN '0 [>0]'
  ELSE '0'
END AS stgy_dyna_amlba_d21_b_cnt_score,

-- 17. stgy_advance_gd_k_104_score (无重名)
CASE 
  WHEN stgy_advance_gd_k_104 <= 3 THEN '-1 [≤3]'
  WHEN stgy_advance_gd_k_104 > 3 AND stgy_advance_gd_k_104 <= 31 THEN '0 [3<x≤31]'
  WHEN stgy_advance_gd_k_104 > 31 THEN '1 [>31]'
  ELSE '0'
END AS stgy_advance_gd_k_104_score,

-- 18. stgy_advance_gd_k_136_score (无重名)
CASE 
  WHEN stgy_advance_gd_k_136 <= -999 THEN '0 [≤-999]'
  WHEN stgy_advance_gd_k_136 > -999 AND stgy_advance_gd_k_136 <= 5 THEN '-1 [-999<x≤5]'
  WHEN stgy_advance_gd_k_136 > 5 THEN '1 [>5]'
  ELSE '0'
END AS stgy_advance_gd_k_136_score,

-- 19. stgy_advance_gd_k_292_score (无重名)
CASE 
  WHEN stgy_advance_gd_k_292 <= -999 THEN '0 [≤-999]'
  WHEN stgy_advance_gd_k_292 > -999 AND stgy_advance_gd_k_292 <= 2 THEN '-1 [-999<x≤2]'
  WHEN stgy_advance_gd_k_292 > 2 AND stgy_advance_gd_k_292 <= 7 THEN '0 [2<x≤7]'
  WHEN stgy_advance_gd_k_292 > 7 THEN '2 [>7]'
  ELSE '0'
END AS stgy_advance_gd_k_292_score,

-- 20. stgy_bj_loan_count_1w_score (无重名)
CASE 
  WHEN stgy_bj_loan_count_1w <= -98 THEN '0 [≤-98]'
  WHEN stgy_bj_loan_count_1w > -98 AND stgy_bj_loan_count_1w <= 0 THEN '-1 [-98<x≤0]'
  WHEN stgy_bj_loan_count_1w > 0 AND stgy_bj_loan_count_1w <= 9 THEN '0 [0<x≤9]'
  WHEN stgy_bj_loan_count_1w > 9 THEN '-2 [>9]'
  ELSE '0'
END AS stgy_bj_loan_count_1w_score,

-- 21. last_repay_gap_days_app_group_score -> 重名，改为 _v6
CASE 
  WHEN last_repay_gap_days_app_group <= 0 THEN '-1 [≤0]'
  WHEN last_repay_gap_days_app_group > 0 AND last_repay_gap_days_app_group < 7 THEN '0 [0<x<7]'
  WHEN last_repay_gap_days_app_group >= 7 AND last_repay_gap_days_app_group < 14 THEN '1 [7≤x<14]'
  WHEN last_repay_gap_days_app_group >= 14 AND last_repay_gap_days_app_group < 21 THEN '1 [14≤x<21]'
  WHEN last_repay_gap_days_app_group >= 21 THEN '-1 [≥21]'
  ELSE '0'
END AS last_repay_gap_days_app_group_score_v6,

-- 22. finish_issue_rate_score (无重名)
CASE 
  WHEN finish_issue_rate < 0.5 THEN '-2 [<0.5]'
  WHEN finish_issue_rate >= 0.5 AND finish_issue_rate < 0.7 THEN '-1 [0.5≤x<0.7]'
  WHEN finish_issue_rate >= 0.7 AND finish_issue_rate < 0.8 THEN '1 [0.7≤x<0.8]'
  WHEN finish_issue_rate >= 0.8 THEN '2 [≥0.8]'
  ELSE '0'
END AS finish_issue_rate_score,

-- 23. msg2_loandue_addpctall_day1_score (无重名)
CASE 
  WHEN msg2_loandue_addpctall_day1 >= 0 AND msg2_loandue_addpctall_day1 <= 0.01 THEN '0 [0≤x≤0.01]'
  WHEN msg2_loandue_addpctall_day1 > 0.01 AND msg2_loandue_addpctall_day1 <= 0.02 THEN '-1 [0.01<x≤0.02]'
  WHEN msg2_loandue_addpctall_day1 > 0.02 THEN '-2 [>0.02]'
  ELSE '0'
END AS msg2_loandue_addpctall_day1_score,

-- 24. question3_score -> 重名，改为 _v6
CASE 
  WHEN question3 <= 4 THEN '0 [≤4]'
  WHEN question3 > 4 AND question3 <= 6 THEN '1 [4<x≤6]'
  WHEN question3 > 6 THEN '2 [>6]'
  ELSE '0'
END AS question3_score_v6,

-- 25. question5_score (无重名)
CASE 
  WHEN question5 <= 3 THEN '0 [≤3]'
  WHEN question5 > 3 THEN '2 [>3]'
  ELSE '0'
END AS question5_score,

-- 26. question6_v2_score -> 重名，改为 _v6
CASE 
  WHEN question6_v2 <= 3 THEN '0 [≤3]'
  WHEN question6_v2 > 3 AND question6_v2 <= 10 THEN '1 [3<x≤10]'
  WHEN question6_v2 > 10 THEN '2 [>10]'
  ELSE '0'
END AS question6_v2_score_v6,

-- 27. stgy_dyna_amlba_d60_f3_cnt_score (无重名)
CASE 
  WHEN stgy_dyna_amlba_d60_f3_cnt <= -99 THEN '0 [≤-99]'
  WHEN stgy_dyna_amlba_d60_f3_cnt > -99 AND stgy_dyna_amlba_d60_f3_cnt <= 0 THEN '-2 [-99<x≤0]'
  WHEN stgy_dyna_amlba_d60_f3_cnt > 0 AND stgy_dyna_amlba_d60_f3_cnt <= 1 THEN '-1 [0<x≤1]'
  WHEN stgy_dyna_amlba_d60_f3_cnt > 1 THEN '-2 [>1]'
  ELSE '0'
END AS stgy_dyna_amlba_d60_f3_cnt_score,

-- 28. max_ovd_days_all_score -> 重名，改为 _v6
CASE 
  WHEN max_ovd_days_all <= 0 THEN '0 [≤0]'
  WHEN max_ovd_days_all > 0 AND max_ovd_days_all <= 3 THEN '-1 [0<x≤3]'
  WHEN max_ovd_days_all > 3 THEN '-2 [>3]'
  ELSE '0'
END AS max_ovd_days_all_score_v6,

-- 29. emcontact_curr_ovd_cnt_all_score (无重名)
CASE 
  WHEN emcontact_curr_ovd_cnt_all <= 0 THEN '0 [≤0]'
  WHEN emcontact_curr_ovd_cnt_all > 0 THEN '-2 [>0]'
  ELSE '0'
END AS emcontact_curr_ovd_cnt_all_score,

-- 30. stgy_dyna_amlba_d30_f2_daydiff_max_score (无重名)
CASE 
  WHEN stgy_dyna_amlba_d30_f2_daydiff_max <= -99 THEN '0 [≤-99]'
  WHEN stgy_dyna_amlba_d30_f2_daydiff_max > -99 AND stgy_dyna_amlba_d30_f2_daydiff_max < 1 THEN '-2 [-99<x<1]'
  WHEN stgy_dyna_amlba_d30_f2_daydiff_max >= 1 AND stgy_dyna_amlba_d30_f2_daydiff_max < 2 THEN '0 [1≤x<2]'
  WHEN stgy_dyna_amlba_d30_f2_daydiff_max >= 2 AND stgy_dyna_amlba_d30_f2_daydiff_max < 3 THEN '0 [2≤x<3]'
  WHEN stgy_dyna_amlba_d30_f2_daydiff_max >= 3 THEN '-1 [≥3]'
  ELSE '0'
END AS stgy_dyna_amlba_d30_f2_daydiff_max_score,

-- 31. max_overdue_day_30d_all_score -> 重名，改为 _v6
CASE 
  WHEN max_overdue_day_30d_all <= -999 THEN '-3 [≤-999]'
  WHEN max_overdue_day_30d_all > -999 AND max_overdue_day_30d_all <= 0 THEN '0 [-999<x≤0]'
  WHEN max_overdue_day_30d_all > 0 AND max_overdue_day_30d_all <= 1 THEN '-1 [0<x≤1]'
  WHEN max_overdue_day_30d_all > 1 THEN '-2 [>1]'
  ELSE '0'
END AS max_overdue_day_30d_all_score_v6,

-- 32. history_loanrec_cnt_lastprepaydays_v2_score -> 重名，改为 _v6
CASE 
  WHEN history_loanrec_cnt_lastprepaydays_v2 > 0 THEN '0 [>0]'
  WHEN history_loanrec_cnt_lastprepaydays_v2 > -1 AND history_loanrec_cnt_lastprepaydays_v2 <= 0 THEN '-1 [-1<x≤0]'
  WHEN history_loanrec_cnt_lastprepaydays_v2 > -2 AND history_loanrec_cnt_lastprepaydays_v2 <= -1 THEN '-2 [-2<x≤-1]'
  WHEN history_loanrec_cnt_lastprepaydays_v2 > -30 AND history_loanrec_cnt_lastprepaydays_v2 <= -2 THEN '-3 [-30<x≤-2]'
  WHEN history_loanrec_cnt_lastprepaydays_v2 <= -30 THEN '-6 [≤-30]'
  ELSE '0'
END AS history_loanrec_cnt_lastprepaydays_v2_score_v6,

-- 33. unique_email_cnt_score -> 重名，改为 _v6
CASE 
  WHEN unique_email_cnt <= 1 THEN '0 [≤1]'
  WHEN unique_email_cnt > 1 AND unique_email_cnt <= 2 THEN '-1 [1<x≤2]'
  WHEN unique_email_cnt > 2 THEN '-2 [>2]'
  ELSE '0'
END AS unique_email_cnt_score_v6,

-- 34. unique_phone_score (无重名)
CASE 
  WHEN unique_phone <= 1 THEN '0 [≤1]'
  WHEN unique_phone > 1 AND unique_phone <= 2 THEN '-2 [1<x≤2]'
  WHEN unique_phone > 2 THEN '-3 [>2]'
  ELSE '0'
END AS unique_phone_score,

-- 35. af_uninstall_cnt_30d_score -> 重名，改为 _v6
CASE 
  WHEN af_uninstall_cnt_30d < 1 THEN '0 [<1]'
  WHEN af_uninstall_cnt_30d >= 1 AND af_uninstall_cnt_30d < 2 THEN '-2 [1≤x<2]'
  WHEN af_uninstall_cnt_30d >= 2 THEN '-3 [≥2]'
  ELSE '0'
END AS af_uninstall_cnt_30d_score_v6,

-- 36. af_uninstall_cnt_lf_score (无重名)
CASE 
  WHEN af_uninstall_cnt_lf <= 0 THEN '0 [≤0]'
  WHEN af_uninstall_cnt_lf > 0 THEN '-1 [>0]'
  ELSE '0'
END AS af_uninstall_cnt_lf_score,

-- 37. minstay_repayplan_second_30d_mid_score -> 重名，改为 _v6
CASE 
  WHEN minstay_repayplan_second_30d_mid < 10 THEN '0 [<10]'
  WHEN minstay_repayplan_second_30d_mid >= 10 THEN '1 [≥10]'
  ELSE '0'
END AS minstay_repayplan_second_30d_mid_score_v6,

-- 38. app_hour_score (无重名)
CASE 
  WHEN apply_hour >= 2 AND apply_hour <= 5 THEN '-1 [2≤x≤5]'
  ELSE '0'
END AS app_hour_score,

-- 39. baseinfo_userprof_age_score -> 重名，改为 _v6
CASE 
  WHEN baseinfo_userprof_age >= 18 AND baseinfo_userprof_age <= 36 THEN '-2 [18≤x≤36]'
  WHEN baseinfo_userprof_age >= 37 AND baseinfo_userprof_age <= 55 THEN '0 [37≤x≤55]'
  WHEN baseinfo_userprof_age > 55 THEN '3 [>55]'
  ELSE '0'
END AS baseinfo_userprof_age_score_v6,

-- 40. baseinfo_userprof_degree_score -> 重名，改为 _v6
CASE 
  WHEN baseinfo_userprof_degree <= 3 THEN '-1 [≤3]'
  WHEN baseinfo_userprof_degree >= 4 AND baseinfo_userprof_degree <= 4 THEN '0 [=4]'
  WHEN baseinfo_userprof_degree >= 5 AND baseinfo_userprof_degree <= 5 THEN '1 [=5]'
  WHEN baseinfo_userprof_degree >= 6 THEN '3 [≥6]'
  ELSE '0'
END AS baseinfo_userprof_degree_score_v6,

-- 41. income_score (无重名)
CASE 
  WHEN income = -1 THEN '-2 [=-1]'
  WHEN income < 10 THEN '0 [<10]'
  WHEN income >= 10 THEN '3 [≥10]'
  ELSE '0'
END AS income_score,

-- 42. baseinfo_employee_type_score (无重名)
CASE 
  WHEN baseinfo_employee_type <= -999 THEN '0 [≤-999]'
  WHEN baseinfo_employee_type <= -1 THEN '0 [≤-1]'
  WHEN baseinfo_employee_type <= 3 THEN '-2 [≤3]'
  WHEN baseinfo_employee_type = 4 THEN '0 [=4]'
  WHEN baseinfo_employee_type IS NULL THEN '0'
  ELSE '0'
END AS baseinfo_employee_type_score,

-- 43. baseinfo_marry_score (无重名)
CASE 
  WHEN baseinfo_marry <= -999 THEN '0 [≤-999]'
  WHEN baseinfo_marry <= 0 THEN '-1 [≤0]'
  WHEN baseinfo_marry = 1 THEN '0 [=1]'
  WHEN baseinfo_marry = 2 THEN '1 [=2]'
  WHEN baseinfo_marry IN (3, 4) THEN '0 [3或4]'
  WHEN baseinfo_marry IS NULL THEN '0'
  ELSE '0'
END AS baseinfo_marry_score,

-- 44. baseinfo_has_house_score (无重名)
CASE 
  WHEN baseinfo_has_house <= -999 THEN '0 [≤-999]'
  WHEN baseinfo_has_house IN (0, 1, 2) THEN '0 [0,1,2]'
  WHEN baseinfo_has_house = 3 THEN '-1 [=3]'
  WHEN baseinfo_has_house = 4 THEN '-1 [=4]'
  WHEN baseinfo_has_house IS NULL THEN '0'
  ELSE '0'
END AS baseinfo_has_house_score,

-- 45. baseinfo_has_car_score (无重名)
CASE 
  WHEN baseinfo_has_car <= -999 THEN '0 [≤-999]'
  WHEN baseinfo_has_car = 0 THEN '1 [=0]'
  WHEN baseinfo_has_car = 1 THEN '-1 [=1]'
  WHEN baseinfo_has_car IS NULL THEN '0'
  ELSE '0'
END AS baseinfo_has_car_score,

-- 46. m687_old_1t3_ad_tengo_0709p1_score (无重名)
CASE 
  WHEN m687_old_1t3_ad_tengo_0709p1 < 0.17 THEN '1 [<0.17]'
  WHEN m687_old_1t3_ad_tengo_0709p1 >= 0.17 THEN '-1 [≥0.17]'
  ELSE '0'
END AS m687_old_1t3_ad_tengo_0709p1_score,

-- 47. m698_old_1t3_voting_0619rh_score (无重名)
CASE 
  WHEN m698_old_1t3_voting_0619rh < 0.212 THEN '1 [<0.212]'
  WHEN m698_old_1t3_voting_0619rh >= 0.212 THEN '-1 [≥0.212]'
  ELSE '0'
END AS m698_old_1t3_voting_0619rh_score,

-- 48. m696_old_1t3_bj_iz_0530_p1_score (无重名)
CASE 
  WHEN m696_old_1t3_bj_iz_0530_p1 < 0.296 THEN '1 [<0.296]'
  WHEN m696_old_1t3_bj_iz_0530_p1 >= 0.296 THEN '-1 [≥0.296]'
  ELSE '0'
END AS m696_old_1t3_bj_iz_0530_p1_score,

-- 49. pvalue_mex_b311_2025v1_p1_score (无重名)
CASE 
  WHEN pvalue_mex_b311_2025v1_p1 < 0.19 THEN '1 [<0.19]'
  WHEN pvalue_mex_b311_2025v1_p1 >= 0.19 THEN '-1 [≥0.19]'
  ELSE '0'
END AS pvalue_mex_b311_2025v1_p1_score,

-- 50. pvalue_mex_b329_2026v1_byid_p1_score (无重名)
CASE 
  WHEN pvalue_mex_b329_2026v1_byid_p1 < 0.303 THEN '1 [<0.303]'
  WHEN pvalue_mex_b329_2026v1_byid_p1 >= 0.303 AND pvalue_mex_b329_2026v1_byid_p1 < 0.457 THEN '-1 [0.303≤x<0.457]'
  WHEN pvalue_mex_b329_2026v1_byid_p1 >= 0.457 THEN '-4 [≥0.457]'
  ELSE '0'
END AS pvalue_mex_b329_2026v1_byid_p1_score,

-- 51. pvalue_mex_b320_2026v1_long_p1_score (无重名)
CASE 
  WHEN pvalue_mex_b320_2026v1_long_p1 < 0.319 THEN '1 [<0.319]'
  WHEN pvalue_mex_b320_2026v1_long_p1 >= 0.319 AND pvalue_mex_b320_2026v1_long_p1 < 0.508 THEN '-1 [0.319≤x<0.508]'
  WHEN pvalue_mex_b320_2026v1_long_p1 >= 0.508 THEN '-4 [≥0.508]'
  ELSE '0'
END AS pvalue_mex_b320_2026v1_long_p1_score,

-- 52. pvalue_mex_b321_2026v2_p1_score (无重名)
CASE 
  WHEN pvalue_mex_b321_2026v2_p1 < 0.137 THEN '3 [<0.137]'
  WHEN pvalue_mex_b321_2026v2_p1 >= 0.137 AND pvalue_mex_b321_2026v2_p1 < 0.259 THEN '-2 [0.137≤x<0.259]'
  WHEN pvalue_mex_b321_2026v2_p1 >= 0.259 AND pvalue_mex_b321_2026v2_p1 < 0.409 THEN '-5 [0.259≤x<0.409]'
  WHEN pvalue_mex_b321_2026v2_p1 >= 0.409 THEN '-10 [≥0.409]'
  ELSE '0'
END AS pvalue_mex_b321_2026v2_p1_score,

-- 53. pvalue_mex_b321_2026v1_p1_score (无重名)
CASE 
  WHEN pvalue_mex_b321_2026v1_p1 < 0.1672 THEN '1 [<0.1672]'
  WHEN pvalue_mex_b321_2026v1_p1 >= 0.1672 AND pvalue_mex_b321_2026v1_p1 < 0.2381 THEN '-2 [0.1672≤x<0.2381]'
  WHEN pvalue_mex_b321_2026v1_p1 >= 0.2381 AND pvalue_mex_b321_2026v1_p1 < 0.3287 THEN '-5 [0.2381≤x<0.3287]'
  WHEN pvalue_mex_b321_2026v1_p1 >= 0.3287 THEN '-8 [≥0.3287]'
  ELSE '0'
END AS pvalue_mex_b321_2026v1_p1_score,

-- 54. android_oldCust_behavior_subscore_charge_V6_1_score (无重名)
CASE 
  WHEN android_oldCust_behavior_subscore_charge_V6_1 < -9 THEN '-8 [<-9]'
  WHEN android_oldCust_behavior_subscore_charge_V6_1 >= -9 AND android_oldCust_behavior_subscore_charge_V6_1 < -4 THEN '-4 [-9≤x<-4]'
  WHEN android_oldCust_behavior_subscore_charge_V6_1 >= -4 AND android_oldCust_behavior_subscore_charge_V6_1 < -1 THEN '-2 [-4≤x<-1]'
  WHEN android_oldCust_behavior_subscore_charge_V6_1 >= -1 AND android_oldCust_behavior_subscore_charge_V6_1 < 3 THEN '0 [-1≤x<3]'
  WHEN android_oldCust_behavior_subscore_charge_V6_1 >= 3 THEN '3 [≥3]'
  ELSE '0'
END AS android_oldCust_behavior_subscore_charge_V6_1_score,

-- 55. android_oldCust_fraud_subscore_charge_V6_1_score (无重名)
CASE 
  WHEN android_oldCust_fraud_subscore_charge_V6_1 < -5 THEN '-5 [<-5]'
  WHEN android_oldCust_fraud_subscore_charge_V6_1 >= -5 AND android_oldCust_fraud_subscore_charge_V6_1 < -3 THEN '-3 [-5≤x<-3]'
  WHEN android_oldCust_fraud_subscore_charge_V6_1 >= -3 AND android_oldCust_fraud_subscore_charge_V6_1 < -1 THEN '-2 [-3≤x<-1]'
  WHEN android_oldCust_fraud_subscore_charge_V6_1 >= -1 THEN '0 [≥-1]'
  ELSE '0'
END AS android_oldCust_fraud_subscore_charge_V6_1_score,

-- 56. android_oldCust_overdue_subscore_charge_V6_1_score (无重名)
CASE 
  WHEN android_oldCust_overdue_subscore_charge_V6_1 < -8 THEN '-15 [<-8]'
  WHEN android_oldCust_overdue_subscore_charge_V6_1 >= -8 AND android_oldCust_overdue_subscore_charge_V6_1 < -4 THEN '-8 [-8≤x<-4]'
  WHEN android_oldCust_overdue_subscore_charge_V6_1 >= -4 AND android_oldCust_overdue_subscore_charge_V6_1 < -1 THEN '-1 [-4≤x<-1]'
  WHEN android_oldCust_overdue_subscore_charge_V6_1 >= -1 THEN '0 [≥-1]'
  ELSE '0'
END AS android_oldCust_overdue_subscore_charge_V6_1_score,

-- 57. android_oldCust_apply_subscore_charge_V6_1_score (无重名)
CASE 
  WHEN android_oldCust_apply_subscore_charge_V6_1 < -13 THEN '-10 [<-13]'
  WHEN android_oldCust_apply_subscore_charge_V6_1 >= -13 AND android_oldCust_apply_subscore_charge_V6_1 < -7 THEN '-5 [-13≤x<-7]'
  WHEN android_oldCust_apply_subscore_charge_V6_1 >= -7 AND android_oldCust_apply_subscore_charge_V6_1 < 1 THEN '-2 [-7≤x<1]'
  WHEN android_oldCust_apply_subscore_charge_V6_1 >= 1 AND android_oldCust_apply_subscore_charge_V6_1 < 4 THEN '0 [1≤x<4]'
  WHEN android_oldCust_apply_subscore_charge_V6_1 >= 4 THEN '2 [≥4]'
  ELSE '0'
END AS android_oldCust_apply_subscore_charge_V6_1_score,

-- 58. android_oldCust_income_subscore_charge_V6_1_score (无重名)
CASE 
  WHEN android_oldCust_income_subscore_charge_V6_1 < -4 THEN '-5 [<-4]'
  WHEN android_oldCust_income_subscore_charge_V6_1 >= -4 AND android_oldCust_income_subscore_charge_V6_1 < 1 THEN '-2 [-4≤x<1]'
  WHEN android_oldCust_income_subscore_charge_V6_1 >= 1 AND android_oldCust_income_subscore_charge_V6_1 < 4 THEN '0 [1≤x<4]'
  WHEN android_oldCust_income_subscore_charge_V6_1 >= 4 THEN '2 [≥4]'
  ELSE '0'
END AS android_oldCust_income_subscore_charge_V6_1_score

from
(
select 
a.biz_id
,a.cust_id
,app_group
,release_time
,app_group_sha256
,last_product_level-- 从转产线决策流取的转产前产品,如果没有转产线这个值会为空
,fd_changepro_V5_3 -- 转产线决策流的等级
,fd_changepro_V6_1 -- 转产线决策流的等级
,substr(cast(current_timestamp as varchar), 1, 24) as update_time
,cast(grantcredit_amount as decimal) as grantcredit_amount
,cast(grantcredit_7d_amount as decimal) as grantcredit_7d_amount
--7/21额度推荐
,case 
when a.app_time>=date'2026-04-29' then '延续上一笔金融属性'
when a.app_time>=date'2026-02-28' and from_base(substr(to_hex(sha256(to_utf8('20260206'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.5 then '延续上一笔金融属性'
when a.app_time>=date'2026-02-28' and from_base(substr(to_hex(sha256(to_utf8('20260206'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then '不延续上一笔金融属性'
when a.app_time<=date'2026-02-24' and a.app_time>=date'2026-02-09' and from_base(substr(to_hex(sha256(to_utf8('20260206'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.3 then '延续上一笔金融属性'
when a.app_time<=date'2026-02-24' and a.app_time>=date'2026-02-09' and from_base(substr(to_hex(sha256(to_utf8('20260206'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.3 then '不延续上一笔金融属性'
end as if_inherit_tag

-- 资产等级更新标签
,case 
when a.app_time>=date'2026-10-16' then 'V6_1' 

when a.app_time>=date'2026-09-15' and from_base(substr(to_hex(sha256(to_utf8('20260818'||a.identity||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 then 'V6_1' 
when a.app_time>=date'2026-09-15' and from_base(substr(to_hex(sha256(to_utf8('20260818'||a.identity||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then 'V5_3' 

when a.app_time>=date'2026-09-04' and from_base(substr(to_hex(sha256(to_utf8('20260818'||a.identity||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'V6_1' 
when a.app_time>=date'2026-09-04' and from_base(substr(to_hex(sha256(to_utf8('20260818'||a.identity||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'V5_3' 

when a.app_time>=date'2026-08-20' and from_base(substr(to_hex(sha256(to_utf8('20260818'||a.identity||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'V6_1' 
when a.app_time>=date'2026-08-20' and from_base(substr(to_hex(sha256(to_utf8('20260818'||a.identity||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.3 then 'V5_3' 
when a.app_time>=date'2026-06-09' then 'V5_3'
when a.app_time>=date'2026-05-22' and from_base(substr(to_hex(sha256(to_utf8('20260521'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 then 'V5_3'
when a.app_time>=date'2026-05-22' and from_base(substr(to_hex(sha256(to_utf8('20260521'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 then 'V5_2'
when a.app_time>=date'2026-04-24' then 'V5_2'
when a.app_time>=date'2026-04-03' and from_base(substr(to_hex(sha256(to_utf8('20260401'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.3 then 'V5_2'
when a.app_time>=date'2026-04-03' and from_base(substr(to_hex(sha256(to_utf8('20260401'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.3 then 'V5_1'
when a.app_time>=date'2026-03-09' then 'V5_1'
when a.app_time>=date'2026-03-04' and from_base(substr(to_hex(sha256(to_utf8('20260205'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.3 then 'V4_2'
when a.app_time>=date'2026-03-04' and from_base(substr(to_hex(sha256(to_utf8('20260205'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.3 then 'V5_1'
when a.app_time>=date'2026-02-09' and from_base(substr(to_hex(sha256(to_utf8('20260205'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'V4_2'
when a.app_time>=date'2026-02-09' and from_base(substr(to_hex(sha256(to_utf8('20260205'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'V5_1'
when a.app_time>=date'2025-11-18' then 'V4_2'
when a.app_time>=date'2025-11-03' and from_base(substr(to_hex(sha256(to_utf8('20250908'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 then 'V3_3'
when a.app_time>=date'2025-11-03' and from_base(substr(to_hex(sha256(to_utf8('20250908'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 
  and from_base(substr(to_hex(sha256(to_utf8('20250908'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then '原V3_3现V4_2'
when a.app_time>=date'2025-11-03' and from_base(substr(to_hex(sha256(to_utf8('20250908'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'V4_2'
when a.app_time>=date'2025-09-10' and from_base(substr(to_hex(sha256(to_utf8('20250908'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'V3_3'
when a.app_time>=date'2025-09-10' and from_base(substr(to_hex(sha256(to_utf8('20250908'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'V4_2'
when a.app_time>=date'2025-09-05' then 'V3_3'
when a.app_time>=date'2025-08-22' and from_base(substr(to_hex(sha256(to_utf8('20250822'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.8 then 'V3_3'
when a.app_time>=date'2025-08-22' and from_base(substr(to_hex(sha256(to_utf8('20250822'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.8 then 'V4'
when a.app_time>=date'2025-08-20' and from_base(substr(to_hex(sha256(to_utf8('20250808'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.6 then 'V3_3'
when a.app_time>=date'2025-08-20' and from_base(substr(to_hex(sha256(to_utf8('20250808'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.6 then 'V3_1'
when a.app_time>=date'2025-08-08' and from_base(substr(to_hex(sha256(to_utf8('20250808'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'V3_3'
when a.app_time>=date'2025-08-08' and from_base(substr(to_hex(sha256(to_utf8('20250808'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.3 then 'V3_1'
when a.app_time>=date'2025-07-25' then 'V3_1'
when a.app_time>=date'2025-07-11' and from_base(substr(to_hex(sha256(to_utf8('20250710'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then 'V3_2'
when (a.app_time>=date'2025-07-11' and from_base(substr(to_hex(sha256(to_utf8('20250710'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.5) then 'V3_1'
when (a.app_group='Mexcredo' and a.app_time>=date'2025-06-20' and a.app_time<=date'2025-06-23' and from_base(substr(to_hex(sha256(to_utf8('20250617'||a.phone||'other'))),1,4),16)/65536.0000000000000000 >0.5) then 'V3_1'
when (a.app_time>=date'2025-06-20' and from_base(substr(to_hex(sha256(to_utf8('20250617'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >0.5) then 'V3_1'
end as v3_flag
,  case 
    when a.app_time>=date'2026-08-20' and from_base(substr(to_hex(sha256(to_utf8('20260818'||a.identity||a.    app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'V6_1<=0.3' 
    when a.app_time>=date'2026-08-20' and from_base(substr(to_hex(sha256(to_utf8('20260818'||a.identity||a.    app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'V5_3>=0.7' 
    end as v3_flag_huidu
,fd_creditlevel_main_v3_3
,a.fd_high_pass_label
--v4资产等级
,fd_creditlevel_main_v4
,fd_creditlevel_main_v4_2,
    V5_fraud_score,
    V5_behavior_score,
    android_oldCust_voteScore_charge_V5_1,
    android_oldCust_mainCreditLevel_charge_V5_1,
    android_oldCust_midCreditLevel_charge_V5_1,
    android_oldCust_ruleScore_charge_V5_1,
    pvalue_mex_b321_2026v1_p1,
    thirdparty_izi_whatsapp_register_status,
    if_system_run_too_short,
    unique_email_cnt,
    history_loanrec_cnt_lastprepaydays_v2,
    max_overdue_day_30d_all,
    max_ovd_days_all,
    af_uninstall_cnt_30d,
    last_repay_gap_days_app_group,
    minstay_repayplan_second_30d_mid,
    baseinfo_userprof_age,
    baseinfo_userprof_degree,
    question3,
    question6_v2,
    advance_duotou_cnt_730d,
    advance_duotou_cnt_x_19
-- ,cast(chng_prdct_fd_creditlevel_main_v4_2 as double) as chng_prdct_fd_creditlevel_main_v4_2
,increase_limit_batch_id
,use_time
,coupon_use_status
,vv.mex_b300_2025v2
,vv.m698_old_1t3_voting_0619rh
--计算结清复贷率
,if_reloan_24h
,case when a.finish_time is not null  then a.biz_id end as finish_biz_id
--首贷结清人数、次数
,case when a.is_reloan='new' and a.finish_time is not null then a.credit_no end as first_loan_finish_people
,case when a.is_reloan='new' and a.finish_time is not null then a.biz_id end as first_loan_finish_biz_id
,app_version

,case when date(app_date) >= date'2026-02-09' and max_overdue_day_30d_all >= 1 then 1 else 0 end as max_overdue_day_30d_all_strategy_test
-- 对应额度不cap测试报表：选择全局额度超cap1.8倍的客群
,case when date(app_date) >= date'2026-03-09' and cap_test_fd_global_limit_cap * 1.8 < cap_test_credit_amount then 1 else 0 end as cap_1point8_strategy_test
,APP_DATE
,APP_WEEK
,APP_MONTH
,app
,tenant
,source
,apply_amount
,if_in_fu_anti_fraud
,if_fu_anti_fraud_passed
,if_in_fu_anti_fraud_weak
,if_fu_anti_fraud_weak_passed
,if_in_fu_model
,if_fu_model_passed
,if_in_fu_sx_refuse
,if_fu_sx_refuse_passed
,if_in_sx
,if_in_sx_6h
,if_in_sx_24h
,if_in_sx_48h
,if_in_sx_72h
,if_in_sx_120h
,if_sx_passed
,if_sx_passed_6h
,if_sx_passed_24h
,if_sx_passed_48h
,if_sx_passed_72h
,if_sx_passed_120h
,if_in_fu_post_anti_fraud_rerun
,if_fu_post_anti_fraud_rerun_passed
,if_in_fu_post_weak_anti_fraud_rerun
,if_fu_post_weak_anti_fraud_rerun_passed
,if_in_fu_post_model_reject_rerun
,if_fu_post_model_reject_rerun_passed
,if_in_fu_external_data
,if_fu_external_data_passed
,if_issue
,contract_amount
,loan_cycle
,a.credit_no
,is_t0_window_1
,is_t0_window_2
,is_t0_window_3
,is_t0_window_4
,is_t0_overdue_1
,is_t0_overdue_2
,is_t0_overdue_3
,is_t0_overdue_4
,t0_overdue_amount_1
,t0_overdue_amount_2
,t0_overdue_amount_3
,t0_overdue_amount_4
,t0_should_amt_1
,t0_should_amt_2
,t0_should_amt_3
,t0_should_amt_4
,is_t3_window_1
,is_t3_window_2
,is_t3_window_3
,is_t3_window_4
,is_t3_overdue_1
,is_t3_overdue_2
,is_t3_overdue_3
,is_t3_overdue_4
,t3_overdue_amount_1
,t3_overdue_amount_2
,t3_overdue_amount_3
,t3_overdue_amount_4
,t3_should_amt_1
,t3_should_amt_2
,t3_should_amt_3
,t3_should_amt_4
,change_used_grantamount
,risk_credit_limit -- 本笔占用主额
,oneday_used_grantamount
,credit_amount
,daily_max_available_limit
,a.mid
,app_time
,from_base(substr(to_hex(sha256(to_utf8(a.credit_no))),1,8),16) as credit_no_new
,issue_date
,first_issue_date
,case when is_reloan='new' then '首贷' when app='yawey' then '主贷' else '加贷' end as main_sanwich_loan_grp
,is_reloan
,product_level
,a.tenant_id
,a.phone
,a.temp_grant_amount
,product_name_new
-- ,change_product_tag
,if_product_or_maxlimit_change_tag
,case when repayment_clearing_count_tenant < 3 then cast(repayment_clearing_count_tenant as varchar)
when repayment_clearing_count_tenant < 6 then '[3,6)'
when repayment_clearing_count_tenant < 10 then '[6,10)'
when repayment_clearing_count_tenant >= 10 then '10+' end as repayment_clearing_count_tenant_flag
,case when repayment_clearing_count_index_tenant= 0 THEN '0'
when repayment_clearing_count_index_tenant = 1 THEN '1'
when repayment_clearing_count_index_tenant =2 THEN '2'
when repayment_clearing_count_index_tenant = 3 then '3'
when repayment_clearing_count_index_tenant = 4 then '4'
when repayment_clearing_count_index_tenant = 5 then '5'
when repayment_clearing_count_index_tenant <= 10 then '[5,10]'
when repayment_clearing_count_index_tenant > 10 then '10+'
else 'other' end as repayment_clearing_count_index_tenant_flag
,case when global_limit is not null then cast(global_limit as integer) else credit_amount end as global_limit
,repayment_clearing_count_index_tenant
,repayment_clearing_count_tenant
,other_app_has_loan_flag
,case when other_app_has_loan_flag >= 1 then '其他包有放款' when other_app_has_loan_flag <= 0 then '其他包无放款' end as other_app_has_loan_tag
,case when curr_ovd_cnt_other_app_group >= 1 or curr_ovd_cnt_other_app_group_90d >= 1 then '其他包有在逾' when curr_ovd_cnt_other_app_group <= 0 then '其他包无在逾' end as other_app_has_overdue_tag
,case when curr_ovd_cnt_other_app_group >= 1 and curr_ovd_cnt_other_app_group_90d <= 0 then '在逾订单发生在90天外'
      when curr_ovd_cnt_other_app_group_90d >= 1 and curr_ovd_cnt_other_app_group_60d <= 0 then '在逾订单发生在60-90天内'
      when curr_ovd_cnt_other_app_group_60d >= 1 and curr_ovd_cnt_other_app_group_30d <= 0 then '在逾订单发生在30-60天内'
      when curr_ovd_cnt_other_app_group_30d >= 1 then '在逾订单发生在30天内' end as other_app_has_overdue_interval_tag
,transfer_time
,curr_biz_id
-- 额度推荐分组标签
--更新额度推荐0721,0804
,cast(first_grantcredit_7d_amount as double) as first_grantcredit_7d_amount,
product_level_test_251205_flag,
equal_houshou_should_interest,
--- 限制新版本
case when emcontact_curr_ovd_cnt_all > 0 then 1 else 0 end as emcontact_curr_ovd_cnt_all_test_flag,

-- 对应“额度不cap测试”报表
case when date(apply_time) >= date'2026-03-09' and from_base(substr(to_hex(sha256(to_utf8('20260309'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then '1.8倍cap对照组'
  when date(apply_time) >= date'2026-03-09' and from_base(substr(to_hex(sha256(to_utf8('20260309'||a.phone||a.app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.5 then '1.8倍cap测试组' end as cap_1point8cap_strategy_test_flag,

case when date(apply_time) < date'2026-02-09' and fd_creditlevel_main_v4_2_snapshot <= 6 and last_credit_amount < last_used_credit_amount + 200 then 
  case when from_base(substr(to_hex(sha256(to_utf8('20251230'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >0.5 then '测试组-发临额'
    when from_base(substr(to_hex(sha256(to_utf8('20251230'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 then '对照组-不发临额' end end as temp_limit_test_flag,
 
case when temp_credit_amount_issue_tag = 1 and date(apply_time) >= date'2026-02-09' then 1 
when temp_credit_amount_issue_tag = 1 and date(apply_time) < date'2026-02-09' then 
  case when from_base(substr(to_hex(sha256(to_utf8('20251230'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >0.5 then 1
    when from_base(substr(to_hex(sha256(to_utf8('20251230'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 then 0 end end as strategy_temp_limit_test_flag,
case when date(apply_time) >= date'2026-09-03' then
  case when from_base(substr(to_hex(sha256(to_utf8('20260811'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.3 then '20260518-V5_2策略'
      when from_base(substr(to_hex(sha256(to_utf8('20260811'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then '20260810-V5_3策略' end 

when date(apply_time) >= date'2026-08-10' and date(apply_time) < date'2026-09-03' then
  case when from_base(substr(to_hex(sha256(to_utf8('20260811'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then '20260518-V5_2策略'
      when from_base(substr(to_hex(sha256(to_utf8('20260811'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then '20260810-V5_3策略' end 
  -- when date(apply_time) >= date'2026-07-06' then '新策略-满足条件分档发'
  -- when date(apply_time) >= date'2026-05-18' then 
  --   case when from_base(substr(to_hex(sha256(to_utf8('20260514'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.3 then '测试组-满额动支客户发'
    -- when from_base(substr(to_hex(sha256(to_utf8('20260514'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then '新策略-满足条件分档发' end
       end as temp_credit_amount_strategy_test_flag,

case when date(apply_time) >= date'2026-03-09' then '测试组-十天间隔组'
when 
-- temp_credit_amount_issue_tag = 1 and 
date(apply_time) >= date'2026-02-09' then 
    case when from_base(substr(to_hex(sha256(to_utf8('20260204'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 >0.5 then '测试组-十天间隔组'
      when from_base(substr(to_hex(sha256(to_utf8('20260204'||a.credit_no||a.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 then '对照组-五天间隔组' end end as strategy_temp_limit_interval_test_flag,
temp_credit_amount_issue_tag,
real_issue_amount,
loan_contract_amount,
CASE 
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.1977 THEN '1. <0.1977'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.2416 THEN '2. 0.1977-0.2416'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.3167 THEN '3. 0.2416-0.3167'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.3642 THEN '4. 0.3167-0.3642'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.4178 THEN '5. 0.3642-0.4178'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.4805 THEN '6. 0.4178-0.4805'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.5031 THEN '7. 0.4805-0.5031'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.5274 THEN '8. 0.5031-0.5274'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.5662 THEN '9. 0.5274-0.5662'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.5961 THEN '10. 0.5662-0.5961'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.6308 THEN '11. 0.5961-0.6308'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.6753 THEN '12. 0.6308-0.6753'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.69 THEN '13. 0.6753-0.69'
    WHEN pvalue_mex_b320_2026v1_long_p1 < 0.7050 THEN '14. 0.69-0.7050'
    WHEN pvalue_mex_b320_2026v1_long_p1 >= 0.7050 THEN '15. >=0.7050'  END as pvalue_mex_b320_2026v1_long_p1_group,
    pvalue_mex_b320_2026v1_long_p1,
    android_oldCust_midCreditLevel_charge_V5_2,
  android_oldCust_mainCreditLevel_charge_V5_2,
      V5_3_fraud_score,
    V5_3_behavior_score,
    android_oldCust_ruleScore_charge_V5_3,
    android_oldCust_voteScore_charge_V5_3,
    android_oldCust_mainCreditLevel_charge_V5_3,
    android_oldCust_midCreditLevel_charge_V5_3,
    curr_ovd_cnt_all,
    curr_ovd_cnt_other_app_group_30d,
    curr_ovd_cnt_other_app_group_60d,
    curr_ovd_cnt_other_app_group_90d,
    curr_ovd_cnt_this_app_group,
    curr_ovd_cnt_other_app_group,
    fd_use_creditamount_score_v1,
    fd_use_creditamount_type,

    stgy_advance_gd_k_136,
    stgy_advance_gd_k_292,
    stgy_advance_gd_k_104,
    beh_main_reject_applypct_day60,
    beh2_o_create_reject_pct_d7,
    stgy_amlta_d180_record_date_unique_cnt,
    stgy_dyna_amlta_d60_daydiff_median,
    stgy_dyna_amlba_d21_b_cnt,
    stgy_dyna_amlba_d30_c_cnt,
    finish_issue_rate,
    stgy_bj_loan_count_1w,
    -- question3,
    -- question6_v2,
    question5,
    msg2_loandue_addpctall_day1,
    android_oldCust_behavior_subscore_charge_V6_1,
    -- max_ovd_days_all,
    emcontact_curr_ovd_cnt_all,
    -- history_loanrec_cnt_lastprepaydays_v2,
    -- max_overdue_day_30d_all,
    stgy_dyna_amlba_d30_f2_daydiff_max,
    stgy_dyna_amlba_d60_f3_cnt,
    android_oldCust_overdue_subscore_charge_V6_1,
    apply_hour,
    history_loanrec_time_apply,
    -- minstay_repayplan_second_30d_mid,
    -- af_uninstall_cnt_30d,
    -- unique_email_cnt,
    af_uninstall_cnt_lf,
    unique_phone,
    android_oldCust_fraud_subscore_charge_V6_1,
    stgy_advance_gd_x_55,
    stgy_advance_gd_x_12,
    stgy_advance_gd_x_34,
    app_loan1_inst_cnt_day7,
    app3_mix_loan1_cfinst_cnt_d30,
    -- advance_duotou_cnt_730d,
    -- advance_duotou_cnt_x_19,
    stgy_bj_apply_count_1w,
    stgy_bj_apply_jgs_12m,
    stgy_bj_apply_jgs_1w,
    android_oldCust_apply_subscore_charge_V6_1,
    income,
    -- baseinfo_userprof_age,
    baseinfo_has_car,
    baseinfo_has_house,
    baseinfo_marry,
    baseinfo_employee_type,
    -- baseinfo_userprof_degree,
    android_oldCust_income_subscore_charge_V6_1,
    android_oldCust_rule_score_charge_V6_1,
    -- m698_old_1t3_voting_0619rh,
    pvalue_mex_b311_2025v1_p1,
    pvalue_mex_b321_2026v2_p1,
    m696_old_1t3_bj_iz_0530_p1,
    -- pvalue_mex_b320_2026v1_long_p1,
    m687_old_1t3_ad_tengo_0709p1,
    pvalue_mex_b329_2026v1_byid_p1,
    android_oldCust_voting_score_charge_V6_1,
    pvalue_mex_b320_2026v2_p1,
    android_oldCust_midCreditLevel_charge_V6_1,
    android_oldCust_mainCreditLevel_charge_V6_1,

is_loop_limit_expired,
cap_test_fd_global_limit_cap,
cap_test_credit_amount,
one_click_loan_tag,

-- 0923离线发临额  在贷人群
offline_temp.tagg_0923 as tagg_0923,
case when app_date >= date'2026-09-22' and app_date <= date_add('day', +5, date'2026-09-22') 
     then offline_temp.temp_limit_tag_0923 end as temp_limit_0923_tag,
-- 0924离线发临额  无在贷人群
offline_temp.curr_main_credit_limit_0924 as curr_main_credit_limit_0924,
case when app_date >= date'2026-09-23' and app_date <= date_add('day', +5, date'2026-09-23') 
     then offline_temp.temp_limit_tag_0924 end as temp_limit_0924_tag,
-- 0930离线发临额  在贷人群
offline_temp.tagg_0930 as tagg_0930,
case when app_date >= date'2026-09-29' and app_date <= date_add('day', +5, date'2026-09-29') 
     then offline_temp.temp_limit_tag_0930 end as temp_limit_0930_tag,
-- 1001离线发临额  无在贷人群
offline_temp.curr_main_credit_limit_1001 as curr_main_credit_limit_1001,
case when app_date >= date'2026-09-30' and app_date <= date_add('day', +5, date'2026-09-30') 
     then offline_temp.temp_limit_tag_1001 end as temp_limit_1001_tag,
-- 1007离线发临额  在贷人群
offline_temp.tagg_1007 as tagg_1007,
case when app_date >= date'2026-10-06' and app_date <= date_add('day', +5, date'2026-10-06') 
     then offline_temp.temp_limit_tag_1007 end as temp_limit_1007_tag,
-- 1008离线发临额  无在贷人群
offline_temp.curr_main_credit_limit_1008 as curr_main_credit_limit_1008,

case when app_date >= date'2026-10-07' and app_date <= date_add('day', +5, date'2026-10-07') 
     then offline_temp.temp_limit_tag_1008 end as temp_limit_1008_tag,
-- 0916离线发临额  在贷人群
offline_temp.tagg_0916 as tagg_0916,
case when app_date >= date'2026-09-15' and app_date <= date_add('day', +5, date'2026-09-15') 
     then offline_temp.temp_limit_tag_0916 end as temp_limit_0916_tag,
-- 0917离线发临额  无在贷人群
offline_temp.curr_main_credit_limit_0917 as curr_main_credit_limit_0917,
case when app_date >= date'2026-09-16' and app_date <= date_add('day', +5, date'2026-09-16') 
     then offline_temp.temp_limit_tag_0917 end as temp_limit_0917_tag,

case when change_event_type = 'C001' then '新客授信'
  when change_event_type = 'C002' then '单期结清调额'
  when change_event_type = 'C005' then '转产线'
  when change_event_type = 'C007' then '再授信'
  when change_event_type = 'C009' then '老客授信'
  when change_event_type = 'C011' then '用信页挽留弹窗'
  when change_event_type = 'C012' then '支用转产' end as last_product_origin
,case when app_time>=cast('2026-07-02 04:00:00.000' as timestamp) and cast(rand_no_72 as double)<=6 then '01.24H转产'
       when app_time>=cast('2026-07-02 04:00:00.000' as timestamp) and cast(rand_no_72 as double)>6 then '02.48H转产'
       when app_time>=cast('2026-06-30 03:00:00.000' as timestamp) and cast(rand_no_72 as double)<=8 then '01.24H转产'
       when app_time>=cast('2026-06-30 03:00:00.000' as timestamp) and cast(rand_no_72 as double)>8 then '02.48H转产'
       when tt2.mid is not null then '03.24H转产(之前)'
       else '' end as change_flag
from (select *,
case when product_name='14天产品C_07_02_00_63' then 'C_07_02_00_63'
     when product_name='15*2 后收60%' then 'C_15_02_00_60'
     when product_name='7*4 前收10 后收50' then 'B_07_04_10_50'
     when product_name='21天产品C_07_03_00_75' then 'C_07_03_00_75'
     when product_name='15*2 后收62.5' then 'C_15_02_00_63'
     when product_name='7*3 前收10 后收50' then 'B_07_03_10_50'
     when product_name='45天产品C_15_03_00_85' then 'C_15_03_00_85'
     when product_name='7*4 后收60' then 'B_07_04_00_60'
     when product_name='7*3前收20后收40' then 'B_07_03_20_40'
     when product_name='7*2 后收50' then 'B_07_02_00_50'
     when product_name='7*2 后收72' then 'C_07_02_00_72'
     when product_name='7*2 后收80' then 'C_07_02_00_80'
else product_name end as product_name_new
from mx.wxs_application_funnel
where is_reloan='old' 
and tenant = 'yawey'
and app_time>=cast('2025-09-01 00:00:00.000' as timestamp)) a
left join
(select 
biz_id
, repayment_clearing_count_index_tenant
, repayment_clearing_count_tenant
, other_app_has_loan_flag
from mx.darren_behave_var
) h
on cast(h.biz_id as bigint)=cast(a.biz_id as bigint)
left JOIN
(
select 
biz_id
,source_version
from ods.s05_loansuper_order_relation 
) l
on a.biz_id = l.biz_id
left join
(
 select 
 t2.biz_id as biz_id
,max(case when t2.finish_time is not null and t1.app_time>t2.finish_time and date_diff('hour',t2.finish_time,cast(current_time as TIMESTAMP))>=24 and date_diff('hour',t2.finish_time,t1.app_time)<=24 then 1 else 0 end) as if_reloan_24h
 from mx.wxs_application_funnel t1
 left join 
 mx.wxs_application_funnel t2
 on t1.credit_no = t2.credit_no and t1.app_group=t2.app_group
 group by 1
 ) t
 on t.biz_id=a.biz_id
left join (select biz_id,
fd_creditlevel_main_v4,
fd_creditlevel_main_v4_2,
fd_creditlevel_main_v3_3,
mex_b300_2025v2,
m698_old_1t3_voting_0619rh,
fd_high_pass_label,
-- credit_amount,
fd_duotou_flag_20250724,
-- daily_max_available_limit,
etl_date,
  row_number() over(partition by biz_id order by etl_date desc ) as rn 
  from mx.tmp_darren_product_table)vv
on cast(vv.biz_id as bigint) = cast(a.biz_id as bigint)
and rn = 1
left join (--提取新客放款时间
  select mid as mid_y,
    first_loan_date as first_issue_date,
    newcust_credit_limit as first_grantcredit_7d_amount
  from dws.dws_risk_stgy_apply_mid_tags
) y 
on a.mid=y.mid_y 
left join (
select biz_id,
  mid,
  risk_credit_limit,-- 本笔占用主额
  credit_amount, --- 本笔最新全局额度
  daily_max_available_limit,-- 本笔最新单日最大可借
  change_used_grantamount -- 总占用额度（不包括本笔）
from mx.darren_bizid_used_grantamount) z
on a.biz_id = z.biz_id 
left join (
select biz_id,
  mid,
  oneday_used_grantamount
from mx.darren_day_used_grantamount) aa 
on a.biz_id = aa.biz_id
left join (
  select *,
    row_number() over(partition by biz_id order by etl_date) as rn 
  from mx.tmp_darren_model_table) tt1 
on a.biz_id = cast(cast(tt1.biz_id as bigint) as varchar)
and tt1.rn = 1 
-- mx.change_product为转产线相关决策流数据
left join (
  select curr_biz_id,
    mid,
    transfer_time,-- 转产线时间
    last_product_level,-- 转产线前产品
    cast(fd_changepro_V5_3 as double)fd_changepro_V5_3,
    cast(fd_changepro_V6_1 as double)fd_changepro_V6_1,
    -- cast(fd_creditlevel_main_v4_2 as double) as chng_prdct_fd_creditlevel_main_v4_2,
    increase_limit_batch_id-- 提额券批次号
  from mx.change_product) tt2 
on cast(a.biz_id as bigint) = tt2.curr_biz_id 
left join (
  select biz_id as biz_idtt3,
    use_time,
    status as coupon_use_status
  from mx.darren_coupon_detail) tt3 
on cast(a.biz_id as bigint) = tt3.biz_idtt3 
left join ( --- 251205后首次进件评级<7客户标签   --- 这里改成 by 每一笔订单观察转产线前产品
select biz_id as biz_idtt4,
  mid as midtt4,
  case when fd_creditlevel_main_v4_2 < 7 then 1 else 0 end as product_level_test_251205_flag
from (
select t0.biz_id,
  t0.mid,
  t1.fd_creditlevel_main_v4_2,
  row_number() over(partition by t0.mid order by t0.create_time) as rn 
from (
select mid,biz_id,create_time
from mx.wxs_application_funnel 
where is_reloan = 'old'
and app_date >= date'2025-12-05') t0 
left join (
select biz_id,fd_creditlevel_main_v4_2
from mx.tmp_darren_product_table
where etl_date >= '20251205'
) t1 
on t0.biz_id = cast(t1.biz_id as varchar)
where fd_creditlevel_main_v4_2 is not null)
where rn = 1 ) tt4 
on cast(a.mid as bigint) = cast(tt4.midtt4 as bigint)
left join (select camera_id as biz_idtt5,
  sum(interest+contract_amount-amount) as equal_houshou_should_interest,
  sum(amount) as real_issue_amount,
  sum(contract_amount) as loan_contract_amount
from ods_view_presto.s02_loan
group by 1) tt5 
on cast(a.biz_id as bigint) = cast(tt5.biz_idtt5 as bigint)
left join (
  select biz_id as biz_idtt6,
    row_number() over(partition by biz_id order by dt) as rn,
    fd_creditlevel_main_v4_2_snapshot,
    fd_main_creditlevel_v5_1_snapshot,
    last_used_credit_amount,
    last_temp_credit_amount_issue_day_gap,
    last_credit_amount,
    temp_credit_amount_issue_tag
  from mx.tmp_darren_temp_limit_table) tt6 
on cast(a.biz_id as bigint) = cast(tt6.biz_idtt6 as bigint)
and tt6.rn = 1 
left join (
  select biz_id as biz_idtt7,
    is_loop_limit_expired
  from mx.tmp_darren_relimit_table) tt7 
on cast(a.biz_id as bigint) = cast(tt7.biz_idtt7 as bigint)
left join (
  select biz_id as biz_idtt8,  
    row_number() over(partition by biz_id order by createtime) as rn,
    V5_fraud_score,
    V5_behavior_score,
    android_oldCust_voteScore_charge_V5_1,
    android_oldCust_mainCreditLevel_charge_V5_1,
    android_oldCust_midCreditLevel_charge_V5_1,
    android_oldCust_ruleScore_charge_V5_1,
    pvalue_mex_b321_2026v1_p1,
    pvalue_mex_b320_2026v1_long_p1,
    mex_b300_2025v2,
    m698_old_1t3_voting_0619rh,
    thirdparty_izi_whatsapp_register_status,
    if_system_run_too_short,
    unique_email_cnt,
    history_loanrec_cnt_lastprepaydays_v2,
    max_overdue_day_30d_all,
    max_ovd_days_all,
    af_uninstall_cnt_30d,
    last_repay_gap_days_app_group,
    minstay_repayplan_second_30d_mid,
    baseinfo_userprof_age,
    baseinfo_userprof_degree,
    question3,
    question6_v2,
    advance_duotou_cnt_730d,
    advance_duotou_cnt_x_19
  from mx.android_oldCust_mainCreditLevel_charge_V5_1_table) tt8 
on cast(a.biz_id as bigint) = cast(tt8.biz_idtt8 as bigint)
and tt8.rn = 1 
left join (
  select biz_id as biz_idtt9,
    row_number() over (partition by biz_id order by createtime) as rn,
    if_product_or_maxlimit_change_tag
  from mx.tmp_darren_if_product_or_maxlimit_change_tag_table) tt9 
on cast(a.biz_id as bigint) = cast(tt9.biz_idtt9 as bigint)
and tt9.rn = 1
left join (
  select biz_id as biz_idtt10,
    fd_global_limit_cap as cap_test_fd_global_limit_cap,
    credit_amount as cap_test_credit_amount
  from mx.tmp_darren_limit_cap_table) tt10 
on cast(a.biz_id as bigint) = cast(tt10.biz_idtt10 as bigint)
-- 26.04.22 23之后的离线发临额
left join 
(
select 
    mid as mid_offline,

    max(case when data_date = '20260923' then tagg end) as tagg_0923,
    max(case when data_date = '20260923' then temp_limit_tag end) as temp_limit_tag_0923,
    max(case when data_date = '20260924' then curr_main_credit_limit end) as curr_main_credit_limit_0924,
    max(case when data_date = '20260924' then temp_limit_tag end) as temp_limit_tag_0924,

    max(case when data_date = '20260930' then tagg end) as tagg_0930,
    max(case when data_date = '20260930' then temp_limit_tag end) as temp_limit_tag_0930,
    max(case when data_date = '20261001' then curr_main_credit_limit end) as curr_main_credit_limit_1001,
    max(case when data_date = '20261001' then temp_limit_tag end) as temp_limit_tag_1001,

    max(case when data_date = '20261007' then tagg end) as tagg_1007,
    max(case when data_date = '20261007' then temp_limit_tag end) as temp_limit_tag_1007,
    max(case when data_date = '20261008' then curr_main_credit_limit end) as curr_main_credit_limit_1008,
    max(case when data_date = '20261008' then temp_limit_tag end) as temp_limit_tag_1008,

    max(case when data_date = '20260916' then tagg end) as tagg_0916,
    max(case when data_date = '20260916' then temp_limit_tag end) as temp_limit_tag_0916,
    max(case when data_date = '20260917' then curr_main_credit_limit end) as curr_main_credit_limit_0917,
    max(case when data_date = '20260917' then temp_limit_tag end) as temp_limit_tag_0917
  from mx.yuhan_temp_limit_base_table_his_20260924
  -- where data_date in ('20260916','20260917','20260729','20260730','20260805','20260924','20261007','20261008')
   where data_date in ('20260916','20260917','20260923','20260924','20260930','20261001','20261007','20261008')
  group by 1
)offline_temp
on cast(a.mid as bigint) = cast(offline_temp.mid_offline as bigint)
-- left join (   会有数据发散问题
--   select mid as mid_offline,temp_limit_tag,tagg as tagg_offline,curr_main_credit_limit as curr_main_credit_limit_offline,data_date
--   from mx.yuhan_temp_limit_base_table_his) offline_temp
left join (
select biz_id as biz_idtt12,
  change_event_type
from (
select *,
  row_number() over (partition by t0.biz_id order by t1.create_time desc) as rn 
from (
select *
from ods.s05_creditx_order) t0 
left join (
select *
from ods.s05_user_creditlimit_change_record
where change_event_type in ('C001','C002','C005','C007','C009','C011','C012')) t1 
on cast(t0.mid as bigint )= t1.mid 
and t0.create_time > t1.create_time) tt0 
where rn = 1) tt12 
on cast(a.biz_id as bigint) = cast(tt12.biz_idtt12 as bigint)
left join (
  select externalid as externalid13,  
    row_number() over(partition by externalid order by createtime) as rn,
    android_oldCust_mainCreditLevel_charge_V5_2,android_oldcust_midcreditlevel_charge_v5_2
  from mx.android_oldcust_main_creditlevel_charge_v5_2_param_table) tt13 
on cast(a.biz_id as varchar) = cast(tt13.externalid13 as varchar)
and tt13.rn = 1 
left join (
  select externalid as externalid14,  
    row_number() over(partition by externalid order by createtime) as rn,
    V5_3_fraud_score,
    V5_3_behavior_score,
    android_oldCust_ruleScore_charge_V5_3,
    android_oldCust_voteScore_charge_V5_3,
    android_oldCust_mainCreditLevel_charge_V5_3,
    android_oldCust_midCreditLevel_charge_V5_3
  from mx.android_oldCust_mainCreditLevel_charge_V5_3_table) tt14 
on cast(a.biz_id as varchar) = cast(tt14.externalid14 as varchar)
and tt14.rn = 1 
left join (
  select externalid as externalid15,  
    row_number() over(partition by externalid order by createtime) as rn,
    curr_ovd_cnt_all,
    curr_ovd_cnt_other_app_group_30d,
    curr_ovd_cnt_other_app_group_60d,
    curr_ovd_cnt_other_app_group_90d,
    curr_ovd_cnt_this_app_group,
    curr_ovd_cnt_other_app_group
  from mx.tmp_curr_ovd_table) tt15
on cast(a.biz_id as varchar) = cast(tt15.externalid15 as varchar) and tt15.rn = 1 
left join
(SELECT 
    a1.mid as mid_random,
    b1.random_no,
    SUBSTR(b1.random_no, 72, 1) as rand_no_72-- 48h转产线测试
FROM ods.s01_mem_member_account a1
LEFT JOIN dwd.dwd_mem_info b1
    ON a1.mid = b1.mid)  tt16
on a.mid = cast(ceil(tt16.mid_random) as bigint)

left join (
  select biz_id as biz_id17,
    row_number() over(partition by biz_id order by dt desc) as rn,
    fd_use_creditamount_score_v1,
    fd_use_creditamount_type
  from mx.tmp_darren_new_temp_limit_table) tt17 
on cast(a.biz_id as varchar) = cast(tt17.biz_id17 as varchar)
and tt17.rn = 1 
left join (
  select externalid as externalid18,
  row_number() over(partition by externalid order by createtime) as rn,
    mid,
    createtime,
    -- last_repay_gap_days_app_group,
    stgy_advance_gd_k_136,
    stgy_advance_gd_k_292,
    stgy_advance_gd_k_104,
    beh_main_reject_applypct_day60,
    beh2_o_create_reject_pct_d7,
    stgy_amlta_d180_record_date_unique_cnt,
    stgy_dyna_amlta_d60_daydiff_median,
    stgy_dyna_amlba_d21_b_cnt,
    stgy_dyna_amlba_d30_c_cnt,
    finish_issue_rate,
    stgy_bj_loan_count_1w,
    -- question3,
    -- question6_v2,
    question5,
    msg2_loandue_addpctall_day1,
    android_oldCust_behavior_subscore_charge_V6_1,
    -- max_ovd_days_all,
    -- emcontact_curr_ovd_cnt_all,
    -- history_loanrec_cnt_lastprepaydays_v2,
    -- max_overdue_day_30d_all,
    stgy_dyna_amlba_d30_f2_daydiff_max,
    stgy_dyna_amlba_d60_f3_cnt,
    android_oldCust_overdue_subscore_charge_V6_1,
    apply_hour,
    history_loanrec_time_apply,
    -- minstay_repayplan_second_30d_mid,
    -- af_uninstall_cnt_30d,
    -- unique_email_cnt,
    af_uninstall_cnt_lf,
    unique_phone,
    android_oldCust_fraud_subscore_charge_V6_1,
    stgy_advance_gd_x_55,
    stgy_advance_gd_x_12,
    stgy_advance_gd_x_34,
    app_loan1_inst_cnt_day7,
    app3_mix_loan1_cfinst_cnt_d30,
    -- advance_duotou_cnt_730d,
    -- advance_duotou_cnt_x_19,
    stgy_bj_apply_count_1w,
    stgy_bj_apply_jgs_12m,
    stgy_bj_apply_jgs_1w,
    android_oldCust_apply_subscore_charge_V6_1,
    income,
    -- baseinfo_userprof_age,
    baseinfo_has_car,
    baseinfo_has_house,
    baseinfo_marry,
    baseinfo_employee_type,
    -- baseinfo_userprof_degree,
    android_oldCust_income_subscore_charge_V6_1,
    android_oldCust_rule_score_charge_V6_1,
    -- m698_old_1t3_voting_0619rh,
    pvalue_mex_b311_2025v1_p1,
    pvalue_mex_b321_2026v2_p1,
    m696_old_1t3_bj_iz_0530_p1,
    -- pvalue_mex_b320_2026v1_long_p1,
    m687_old_1t3_ad_tengo_0709p1,
    pvalue_mex_b329_2026v1_byid_p1,
    android_oldCust_voting_score_charge_V6_1,
    pvalue_mex_b320_2026v2_p1,
    android_oldCust_midCreditLevel_charge_V6_1,
    android_oldCust_mainCreditLevel_charge_V6_1,
    etl_date
  from mx.android_oldCust_mainCreditLevel_charge_V6_1_table) tt18
on cast(a.biz_id as varchar) = cast(tt18.externalid18 as varchar)
and tt18.rn=1
);

