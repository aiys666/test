
drop table if exists mx.darren_identity_mid_base_table;
create table mx.darren_identity_mid_base_table as 
select t0.identity,t1.mid
from ods.s01_mem_base_info t0 
left join ods.s01_mem_member_account t1 
on t0.cust_id = t1.mb_cust_id;


-- 保险起见更新两个分区
delete from mx.darren_jieqing_base_table_t0
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');
-- 1、结清授信决策流取更新后的credit_amount/daily_max_available_limit
insert into mx.darren_jieqing_base_table_t0
select externalid,
  mid as jq_mid,
  endtime as settle_time,
  row_number() over (partition by mid,endtime order by endtime) as rn,
  cast(json_extract_scalar(outputdata, '$.credit_amount') as double) as credit_amount,
  cast(json_extract_scalar(outputdata, '$.daily_max_available_limit') as double) as daily_max_available_limit,
  etl_date
from ods.s21_risk_strategy_record
where productid = 428
and strategytype = 'CHAMPION'
and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');

delete from mx.darren_jieqing_base_table_t1
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');
--  2、结清授信决策流中的结清决策流是否调额决策树取结清调额标签is_settle_adjust_quota_flag
insert into mx.darren_jieqing_base_table_t1
select externalid,is_settle_adjust_quota_flag,etl_date
from (
select externalid,
  cast(json_extract_scalar(outputdata, '$.is_settle_adjust_quota_flag') as double) as is_settle_adjust_quota_flag,
  row_number() over (partition by externalid order by createtime desc) as rn,
  etl_date
from ods.s21_risk_model_record
where modelmainid = 1063
  and strategytype = 'CHAMPION'
  and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
)
where rn = 1;

--- 更新t2表
delete from mx.darren_jieqing_base_table_t2
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');
-- 3、低额用户首次结清规则集打标 取小金额测试相关settle_adjust_quota_cnt(成功调额次数)、last_credit_amount、low_limit_first_settle_increase_tag(低额用户首次结清提额标签)
insert into mx.darren_jieqing_base_table_t2
select externalid,
  mid as mid_t2,
  cast(json_extract_scalar(inputdata, '$.settle_adjust_quota_cnt') as double) as settle_adjust_quota_cnt,
  cast(json_extract_scalar(inputdata, '$.last_credit_amount') as double) as last_credit_amount,
  cast(json_extract_scalar(outputdata, '$.low_limit_first_settle_increase_tag') as double) as low_limit_first_settle_increase_tag,
  createtime,
  etl_date
from ods.s21_risk_model_record
where modelmainid = 1364
  and strategytype = 'CHAMPION'
  and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
  ;




-- t3表 
-- 4、单次提幅cap_*%组/全局额度cap 取全局额度cap相关
delete from mx.darren_jieqing_base_table_t3
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');

insert into mx.darren_jieqing_base_table_t3
select externalid,
  max(cast(json_extract_scalar(inputdata, '$.fd_grantcredit_global_amount_uncapped') as double)) as champion_fd_grantcredit_global_amount_uncapped,
  max(cast(json_extract_scalar(inputdata, '$.fd_grantcredit_global_amount_add_cap') as double)) as champion_fd_grantcredit_global_amount_add_cap,
  max(cast(json_extract_scalar(outputdata, '$.global_limit') as double)) as champion_global_limit,
  etl_date
from ods.s21_risk_model_record 
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
  and modelId in (2402,3033,3114,4631)
  and strategytype = 'CHAMPION'
  and productid = 428
group by 1,5;




delete from mx.darren_jieqing_base_table_t7
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');
-- 8、复贷授信决策流取credit_amount、daily_max_available_limit
insert into mx.darren_jieqing_base_table_t7
select cast(biz_id as varchar) as biz_id4,
  cast(json_extract(outputdata, '$.credit_amount') as double) as sx_credit_amount,
  cast(json_extract(outputdata, '$.daily_max_available_limit') as double) as sx_daily_max_available_limit,
  etl_date
from ods.s21_risk_strategy_record
where productid = 196
  and strategytype = 'CHAMPION'
  and etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');


delete from mx.darren_jieqing_base_table_t8
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');
-- 9、v5_1资产等级
insert into mx.darren_jieqing_base_table_t8
select externalid,
  max(cast(json_extract_scalar(outputdata, '$.android_oldCust_mainCreditLevel_charge_V5_1') as double)) as android_oldCust_mainCreditLevel_charge_V5_1,
  etl_date
from ods.s21_risk_model_record 
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
  and modelmainId = 1436
  and strategytype = 'CHAMPION'
  and productid = 428
group by 1,3;



-- 删除目标分区中前一天及之后的数据（保证幂等性）
DELETE FROM mx.darren_jieqing_base_table_t9
WHERE etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd');
-- 插入当天符合条件的数据
INSERT INTO mx.darren_jieqing_base_table_t9
SELECT 
  externalid,
  MAX(CAST(JSON_EXTRACT_SCALAR(inputdata, '$.last_credit_amount_change_day_gap') AS DOUBLE)) AS last_credit_amount_change_day_gap,
  MAX(CAST(JSON_EXTRACT_SCALAR(inputdata, '$.curr_ovd_cnt_all') AS DOUBLE)) AS curr_ovd_cnt_all,
  MAX(CAST(JSON_EXTRACT_SCALAR(inputdata, '$.low_limit_first_settle_increase_tag') AS DOUBLE)) AS low_limit_first_settle_increase_tag,
  MAX(CAST(JSON_EXTRACT_SCALAR(inputdata, '$.curr_ovd_cnt_this_app_group') AS DOUBLE)) AS curr_ovd_cnt_this_app_group,
  MAX(CAST(JSON_EXTRACT_SCALAR(inputdata, '$.curr_ovd_cnt_other_app_group_90d') AS DOUBLE)) AS curr_ovd_cnt_other_app_group_90d,
  MAX(CAST(JSON_EXTRACT_SCALAR(inputdata, '$.max_overdue_day_30d_all') AS DOUBLE)) AS max_overdue_day_30d_all,
  MAX(CAST(JSON_EXTRACT_SCALAR(inputdata, '$.last_credit_increase_day_gap') AS DOUBLE)) AS last_credit_increase_day_gap,
  MAX(CAST(JSON_EXTRACT_SCALAR(inputdata, '$.hist_loanrec_cnt_issue_days_last_jieqing') AS DOUBLE)) AS hist_loanrec_cnt_issue_days_last_jieqing,
  MAX(CAST(JSON_EXTRACT_SCALAR(inputdata, '$.settle_adjust_quota_cnt') AS DOUBLE)) AS settle_adjust_quota_cnt,
  MAX(CAST(JSON_EXTRACT_SCALAR(outputdata, '$.is_settle_adjust_quota_flag') AS DOUBLE)) AS is_settle_adjust_quota_flag,

  etl_date
FROM ods.s21_risk_model_record
WHERE 
  -- etl_date >= to_char(date_add('day', -15, current_date), 'yyyymmdd')
  etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
  AND modelmainId = 1063         
  AND strategytype = 'CHAMPION'
  AND productid = 428        
GROUP BY externalid, etl_date;


-- 0904次新用户策略参数
drop table if exists mx.darren_jieqing_base_table_t10;
create table mx.darren_jieqing_base_table_t10 as 
select externalid,
  mid as mid_10,
  createtime ,
  row_number() over (partition by mid,createtime order by createtime) as rn,
  CAST(JSON_EXTRACT(outputdata, '$.sd_creditlevel_V4_3') AS DOUBLE) AS sd_creditlevel_V4_3,
  CAST(JSON_EXTRACT(outputdata, '$.android_oldCust_mainCreditLevel_charge_V5_3') AS DOUBLE) AS android_oldCust_mainCreditLevel_charge_V5_3,
  CAST(JSON_EXTRACT(outputdata, '$.android_oldCust_mainCreditLevel_charge_V6_1') AS DOUBLE) AS android_oldCust_mainCreditLevel_charge_V6_1,
  CAST(JSON_EXTRACT(outputdata, '$.sha256_random_260824') AS DOUBLE) AS sha256_random_260824,
  CAST(JSON_EXTRACT(outputdata, '$.sha256_random_260814') AS DOUBLE) AS sha256_random_260814,
  CAST(JSON_EXTRACT(outputdata, '$.first_settle_reloan_creditlvl_V5_3') AS DOUBLE) AS first_settle_reloan_creditlvl_V5_3,
  CAST(JSON_EXTRACT(outputdata, '$.first_settle_reloan_creditlvl_V6_1') AS DOUBLE) AS first_settle_reloan_creditlvl_V6_1,
  CAST(JSON_EXTRACT(outputdata, '$.new_issue_day_gap') AS bigint)new_issue_day_gap,  
  CAST(JSON_EXTRACT(outputdata, '$.repayment_clearing_count_index_tenant') AS bigint)repayment_clearing_count_index_tenant,
  CAST(JSON_EXTRACT(outputdata, '$.first_settle_reloan_tag') AS bigint)first_settle_reloan_tag,
  etl_date
from ods.s21_risk_strategy_record
where productid = 428 AND strategydefid=2264  and strategytype = 'CHAMPION' 
and createtime>cast('2026-09-04 04:00' as TIMESTAMP) ;

  
drop table if exists mx.darren_jieqing_dt_base_table;
create table mx.darren_jieqing_dt_base_table as 
select *,
case when settle_time >= date'2026-06-24' and v3_flag in ('V5_3') then 'v5_3.均值组'
    when settle_time >= date'2026-05-22' and v3_flag in ('V5_3') and from_base(substr(to_hex(sha256(to_utf8('20250909'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then 'v5_3.提额组'
    when settle_time >= date'2026-05-22' and v3_flag in ('V5_3') and from_base(substr(to_hex(sha256(to_utf8('20250909'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.5 then 'v5_3.对照组'
  when settle_time >= date'2026-04-03' and v3_flag in ('V5_2') and from_base(substr(to_hex(sha256(to_utf8('20250909'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then 'v5_2.提额组'
    when settle_time >= date'2026-04-03' and v3_flag in ('V5_2') and from_base(substr(to_hex(sha256(to_utf8('20250909'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.5 then 'v5_2.对照组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V4_2') and from_base(substr(to_hex(sha256(to_utf8('20250909'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then 'v4_2.提额组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V4_2') and from_base(substr(to_hex(sha256(to_utf8('20250909'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.5 then 'v4_2.对照组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V5_1') and from_base(substr(to_hex(sha256(to_utf8('20250909'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then 'v5_1.提额组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V5_1') and from_base(substr(to_hex(sha256(to_utf8('20250909'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.5 then 'v5_1.对照组'
    when v3_flag in ('V4_2','原V3_3现V4_2') and from_base(substr(to_hex(sha256(to_utf8('20250909'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then 'v4_2.提额组'
    when v3_flag in ('V4_2','原V3_3现V4_2') and from_base(substr(to_hex(sha256(to_utf8('20250909'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.5 then 'v4_2.对照组'
    when v3_flag='V3_3' and from_base(substr(to_hex(sha256(to_utf8('20250809'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000>=0.5 then 'v3_3.提额组'
    when v3_flag='V3_3' and from_base(substr(to_hex(sha256(to_utf8('20250809'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000<0.5 then 'v3_3.对照组'
    end as new_limit_flag,
  case when settle_time >= date'2026-07-09' and v3_flag in ('V5_3') then 'v5_3-全局额度cap0709提额组'
    when settle_time >= date'2026-06-24' and v3_flag in ('V5_3') then 'v5_3-全局额度cap均值组'
    when settle_time >= date'2026-05-22' and v3_flag in ('V5_3') and from_base(substr(to_hex(sha256(to_utf8('20251215'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v5_3-全局额度cap测试组'
    when settle_time >= date'2026-05-22' and v3_flag in ('V5_3') and from_base(substr(to_hex(sha256(to_utf8('20251215'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v5_3-全局额度cap冠军组'
    when settle_time >= date'2026-04-03' and v3_flag in ('V5_2') and from_base(substr(to_hex(sha256(to_utf8('20251215'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v5_2-全局额度cap测试组'
    when settle_time >= date'2026-04-03' and v3_flag in ('V5_2') and from_base(substr(to_hex(sha256(to_utf8('20251215'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v5_2-全局额度cap冠军组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251215'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v4_2-全局额度cap测试组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251215'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v4_2-全局额度cap冠军组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V5_1') and from_base(substr(to_hex(sha256(to_utf8('20251215'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v5_1-全局额度cap测试组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V5_1') and from_base(substr(to_hex(sha256(to_utf8('20251215'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v5_1-全局额度cap冠军组'
    when settle_time >= date'2025-12-16' and from_base(substr(to_hex(sha256(to_utf8('20251215'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then '全局额度cap测试组'
    when settle_time >= date'2025-12-16' and from_base(substr(to_hex(sha256(to_utf8('20251215'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then '全局额度cap冠军组'
    when settle_time >= date'2025-11-24' and from_base(substr(to_hex(sha256(to_utf8('20251124'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then 'cap1&2测试组'
    when settle_time >= date'2025-11-24' and from_base(substr(to_hex(sha256(to_utf8('20251124'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.5 then 'cap1&2冠军组'
      end as global_limit_cap_test_tag,
case when settle_time >= date'2026-05-22' and v3_flag in ('V5_3') and from_base(substr(to_hex(sha256(to_utf8('20251216'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >=0.7 then 'v5_3-单次提幅cap测试组'
    when settle_time >= date'2026-05-22' and v3_flag in ('V5_3') and from_base(substr(to_hex(sha256(to_utf8('20251216'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <0.7 then 'v5_3-单次提幅cap冠军组'
    when settle_time >= date'2026-04-03' and v3_flag in ('V5_2') and from_base(substr(to_hex(sha256(to_utf8('20251216'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >=0.7 then 'v5_2-单次提幅cap测试组'
    when settle_time >= date'2026-04-03' and v3_flag in ('V5_2') and from_base(substr(to_hex(sha256(to_utf8('20251216'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <0.7 then 'v5_2-单次提幅cap冠军组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251216'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >=0.7 then 'v4_2-单次提幅cap测试组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251216'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <0.7 then 'v4_2-单次提幅cap冠军组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V5_1') and from_base(substr(to_hex(sha256(to_utf8('20251216'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >=0.7 then 'v5_1-单次提幅cap测试组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V5_1') and from_base(substr(to_hex(sha256(to_utf8('20251216'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <0.7 then 'v5_1-单次提幅cap冠军组'
    when settle_time >= date'2025-12-16' and from_base(substr(to_hex(sha256(to_utf8('20251216'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >=0.7 then '单次提幅cap测试组'
    when settle_time >= date'2025-12-16' and from_base(substr(to_hex(sha256(to_utf8('20251216'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <0.7 then '单次提幅cap冠军组'
    when settle_time >= date'2025-11-24' and from_base(substr(to_hex(sha256(to_utf8('20251124'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >=0.5 then 'cap1&2测试组'
    when settle_time >= date'2025-11-24' and from_base(substr(to_hex(sha256(to_utf8('20251124'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <0.5 then 'cap1&2冠军组'
      end as single_increase_limit_cap_test_tag,    
  case when settle_time >= date'2026-06-24' and v3_flag in ('V5_3') then 'v5_3均值组'
    when settle_time >= date'2026-05-22' and v3_flag in ('V5_3') and from_base(substr(to_hex(sha256(to_utf8('20251217'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v5_3测试组'
    when settle_time >= date'2026-05-22' and v3_flag in ('V5_3') and from_base(substr(to_hex(sha256(to_utf8('20251217'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v5_3冠军组'
    when settle_time >= date'2026-04-03' and v3_flag in ('V5_2') and from_base(substr(to_hex(sha256(to_utf8('20251217'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v5_2测试组'
    when settle_time >= date'2026-04-03' and v3_flag in ('V5_2') and from_base(substr(to_hex(sha256(to_utf8('20251217'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v5_2冠军组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251217'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v4_2测试组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251217'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v4_2冠军组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V5_1') and from_base(substr(to_hex(sha256(to_utf8('20251217'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v5_1测试组'
    when settle_time >= date'2026-02-09' and v3_flag in ('V5_1') and from_base(substr(to_hex(sha256(to_utf8('20251217'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v5_1冠军组'
    when settle_time>= date'2025-12-16' and v3_flag in ('V4_2','原V3_3现V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251217'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v4_2测试组'
    when settle_time>= date'2025-12-16' and v3_flag in ('V4_2','原V3_3现V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251217'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v4_2冠军组'
    when settle_time>= date'2025-10-29' and v3_flag in ('V4_2','原V3_3现V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251010'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v4_2测试组'
    when settle_time>= date'2025-10-29' and v3_flag in ('V4_2','原V3_3现V4_2') and from_base(substr(to_hex(sha256(to_utf8('20251010'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v4_2冠军组'
    when settle_time>= date'2025-10-29' and v3_flag = 'V3_3' and from_base(substr(to_hex(sha256(to_utf8('20251010'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'v3_3测试组'
    when settle_time>= date'2025-10-29' and v3_flag = 'V3_3' and from_base(substr(to_hex(sha256(to_utf8('20251010'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'v3_3冠军组'
    when from_base(substr(to_hex(sha256(to_utf8('20251010'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.5 then '冠军组'
    when from_base(substr(to_hex(sha256(to_utf8('20251010'||jq_phone||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then '测试组'
      end as daily_max_limit_tag
         ,case when settle_time >= date'2026-07-22' then 
      case when v3_flag ='V5_3' then 
      case when android_oldCust_mainCreditLevel_charge_V5_3<=2 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'base_1档_C_07_04_00_75'
      when android_oldCust_mainCreditLevel_charge_V5_3<=2 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'test_1档_D_1_03'
        when android_oldCust_mainCreditLevel_charge_V5_3<=6 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'base_2档_C_07_03_00_75'
        when android_oldCust_mainCreditLevel_charge_V5_3<=6 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'test_2档_D_1_04'
        when android_oldCust_mainCreditLevel_charge_V5_3<=10 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'base_3档_B_07_02_00_75'
        when android_oldCust_mainCreditLevel_charge_V5_3<=10 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'test_3档_D_1_05'
         when android_oldCust_mainCreditLevel_charge_V5_3>10 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'base_4档_A_07_01_50_00'
        when android_oldCust_mainCreditLevel_charge_V5_3>10  and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'test_4档_D_1_06'  end
       when v3_flag ='V6_1' then 
      case when android_oldCust_mainCreditLevel_charge_V6_1<=3 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'base_1档_C_07_04_00_75'
      when android_oldCust_mainCreditLevel_charge_V6_1<=3 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'test_1档_D_1_03'
        when android_oldCust_mainCreditLevel_charge_V6_1<=6 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'base_2档_C_07_03_00_75'
        when android_oldCust_mainCreditLevel_charge_V6_1<=6 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'test_2档_D_1_04'
        when android_oldCust_mainCreditLevel_charge_V6_1<=8 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'base_3档_B_07_02_00_75'
        when android_oldCust_mainCreditLevel_charge_V6_1<=8 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'test_3档_D_1_05'
         when android_oldCust_mainCreditLevel_charge_V6_1>8 and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'base_4档_A_07_01_50_00'
        when android_oldCust_mainCreditLevel_charge_V6_1>8  and from_base(substr(to_hex(sha256(to_utf8('20260512'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'test_4档_D_1_06' 
        end end end as product_test_0722
from(
select t0.*,
  t1.is_settle_adjust_quota_flag,
  t2.jq_phone,
  t2.jq_app_group_sha256,
  t2.jq_credit_no,
  t3.champion_fd_grantcredit_global_amount_uncapped,
  t3.champion_fd_grantcredit_global_amount_add_cap,
  t3.champion_global_limit,
  -- t4.last_credit_amount_change_day_gap,
  -- t4.hist_loanrec_cnt_issue_days_last_jieqing,
  t0.credit_amount as jq_global_limit,
  t5.last_credit_amount,
  t7.settle_adjust_quota_cnt,
  t8.android_oldCust_mainCreditLevel_charge_V5_1,
  t9.first_loan_low_limit_first_settle_increase_tag,
  t9.newcust_newest_credit_amount,
  -- t9.settle_adjust_quota_cnt,  -- t9表是在分流节点后面跑的，这里会缺少一部分数据
  t10.newcust_credit_limit,
  t11.android_oldCust_mainCreditLevel_charge_V5_2,
  t12.repayment_clearing_count_index,
  t12.repayment_clearing_count,
  t13.repayment_clearing_count_index_all,
  t13.repayment_clearing_count_all,
  t14.android_oldCust_mainCreditLevel_charge_V5_3,
  t15.last_credit_amount_change_day_gap,
  t15.curr_ovd_cnt_all,
  t15.curr_ovd_cnt_this_app_group,
  t15.curr_ovd_cnt_other_app_group_90d,
  t15.max_overdue_day_30d_all,
  t15.last_credit_increase_day_gap,
  t15.hist_loanrec_cnt_issue_days_last_jieqing,
  t16.*,  -- 15天内次新用户相关参数
  t17.android_oldCust_mainCreditLevel_charge_V6_1,
  -- t15.settle_adjust_quota_cnt, --- 这里V3版本没有添加这个变量，从t7表去取
  -- t15.is_settle_adjust_quota_flag,
  case 
    when t0.settle_time>=date'2026-09-15' and from_base(substr(to_hex(sha256(to_utf8('20260818'||t2.jq_credit_no||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 then 'V6_1' 
    when t0.settle_time>=date'2026-09-15' and from_base(substr(to_hex(sha256(to_utf8('20260818'||t2.jq_credit_no||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then 'V5_3' 

    when t0.settle_time>=date'2026-09-04' and from_base(substr(to_hex(sha256(to_utf8('20260818'||t2.jq_credit_no||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'V6_1' 
    when t0.settle_time>=date'2026-09-04' and from_base(substr(to_hex(sha256(to_utf8('20260818'||t2.jq_credit_no||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'V5_3' 

    when t0.settle_time>=date'2026-08-20' and from_base(substr(to_hex(sha256(to_utf8('20260818'||t2.jq_credit_no||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'V6_1' 
    when t0.settle_time>=date'2026-08-20' and from_base(substr(to_hex(sha256(to_utf8('20260818'||t2.jq_credit_no||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.3 then 'V5_3' 
    when t0.settle_time >= date'2026-06-09' then 'V5_3'
    when t0.settle_time >= date'2026-05-22' and from_base(substr(to_hex(sha256(to_utf8('20260521'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 then 'V5_3'
    when t0.settle_time >= date'2026-05-22' and from_base(substr(to_hex(sha256(to_utf8('20260521'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 then 'V5_2'
    when t0.settle_time >= date'2026-04-24' then 'V5_2'
    when t0.settle_time >= date'2026-04-03' and from_base(substr(to_hex(sha256(to_utf8('20260401'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.3 then 'V5_2'
    when t0.settle_time >= date'2026-04-03' and from_base(substr(to_hex(sha256(to_utf8('20260401'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.3 then 'V5_1'
    when t0.settle_time >= date'2026-03-09' then 'V5_1'
    when t0.settle_time >= date'2026-03-04' and from_base(substr(to_hex(sha256(to_utf8('20260205'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.3 then 'V4_2'
    when t0.settle_time >= date'2026-03-04' and from_base(substr(to_hex(sha256(to_utf8('20260205'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.3 then 'V5_1'
    when t0.settle_time >= date'2026-02-09' and from_base(substr(to_hex(sha256(to_utf8('20260205'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.7 then 'V4_2'
    when t0.settle_time >= date'2026-02-09' and from_base(substr(to_hex(sha256(to_utf8('20260205'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.7 then 'V5_1'
    when t0.settle_time>=date'2025-11-18' then 'V4_2'
    when t0.settle_time>=date'2025-11-03' and from_base(substr(to_hex(sha256(to_utf8('20250908'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.5 then 'V3_3'
    when t0.settle_time>=date'2025-11-03' and from_base(substr(to_hex(sha256(to_utf8('20250908'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.5 
      and from_base(substr(to_hex(sha256(to_utf8('20250908'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then '原V3_3现V4_2'
    when t0.settle_time>=date'2025-11-03' and from_base(substr(to_hex(sha256(to_utf8('20250908'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'V4_2'
    when t0.settle_time>=date'2025-09-10' and from_base(substr(to_hex(sha256(to_utf8('20250908'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.7 then 'V3_3'
    when t0.settle_time>=date'2025-09-10' and from_base(substr(to_hex(sha256(to_utf8('20250908'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'V4_2'
        end as v3_flag,

  case when t0.settle_time>=date'2026-04-07' and from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 >=0 then '对照组'
    -- when t0.settle_time>=date'2026-04-07' and from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 <0.2 then '额度推荐v2组'
    when t0.settle_time>=date'2026-03-09' and from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 >=0.2 then '对照组'
    when t0.settle_time>=date'2026-03-09' and from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 <0.2 then '额度推荐v2组'
    when t0.settle_time>=date'2026-01-26' and from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 >=0.5 then '对照组'
    when t0.settle_time>=date'2026-01-26' and from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 <0.5 then '额度推荐v2组'
    when t0.settle_time>=date'2025-12-23' and from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 >=0.8 then '对照组'
    when t0.settle_time>=date'2025-12-23' and from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 <0.8 then '额度推荐v2组'
    when t0.settle_time>=date'2025-11-24' and from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 >=0.5 then '对照组'
    when t0.settle_time>=date'2025-11-24' and from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 <0.5 then '额度推荐v2组'
    when t0.settle_time>=date'2025-11-04' and from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 >=0.3 then '对照组'
    when t0.settle_time>=date'2025-11-04' and from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 <0.3 then '额度推荐v2组'
    when from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 >=0.1 then '对照组'
    when from_base(substr(to_hex(sha256(to_utf8('20250606'||t2.jq_phone||'yawey'))),1,4),16)/65536.0000000000000000 <0.1 then '额度推荐v2组'
      end as limit_recommend_grp,
  --统计两种cap笔数
case when champion_fd_grantcredit_global_amount_uncapped > champion_fd_grantcredit_global_amount_add_cap then 1 else 0 end as if_grantcredit_global_amount_add_cap,
case when champion_fd_grantcredit_global_amount_add_cap > champion_global_limit then 1 else 0 end as if_global_limit_add_cap,
case when t5.last_credit_amount < credit_amount then '提额组'
  when t5.last_credit_amount = credit_amount then '平额组'
  when t5.last_credit_amount > credit_amount then '降额组' end as adjust_quota_tag,

case
  when t0.settle_time >= date'2026-05-22' and first_loan_low_limit_first_settle_increase_tag = 1 then '0413小金额提额测试组' 
  when t0.settle_time >= date'2026-04-13' and first_loan_low_limit_first_settle_increase_tag = 1 and from_base(substr(to_hex(sha256(to_utf8('20260409'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.3 then '0413小金额提额测试组' 
  when t0.settle_time >= date'2026-04-13' and first_loan_low_limit_first_settle_increase_tag = 1 and from_base(substr(to_hex(sha256(to_utf8('20260409'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.3 then '0413小金额提额对照组' 
  when t0.settle_time >= date'2026-04-13' and t9.settle_adjust_quota_cnt = 0 then '非小金额组' end as first_loan_low_limit_first_settle_increase_test_0413,
-- --15天内次新用户测试 0904
case
  when t0.settle_time >= date'2026-09-04' and t16.first_settle_reloan_tag = 1 and from_base(substr(to_hex(sha256(to_utf8('20260814'||t2.jq_credit_no||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.05 and from_base(substr(to_hex(sha256(to_utf8('20260824'||t2.jq_credit_no||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.3 then '0904_15天内次新用户test组' 
  when t0.settle_time >= date'2026-09-04' and t16.first_settle_reloan_tag = 1 and from_base(substr(to_hex(sha256(to_utf8('20260814'||t2.jq_credit_no||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.05 and from_base(substr(to_hex(sha256(to_utf8('20260824'||t2.jq_credit_no||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.3 then '0904_15天内次新用户base组' 
  when t0.settle_time >= date'2026-09-04' and t16.first_settle_reloan_tag != 1 then '非15天内次新用户组' end as first_settle_reloan_test_0909,
-- --降额测试
case when t0.settle_time>=date'2025-12-09' then '30%降幅组'
when t0.settle_time>=date'2025-10-29' and from_base(substr(to_hex(sha256(to_utf8('20251029'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 >= 0.5 then '30%降幅组'
when t0.settle_time>=date'2025-10-29' and from_base(substr(to_hex(sha256(to_utf8('20251029'||t2.jq_phone||t2.jq_app_group_sha256))),1,4),16)/65536.0000000000000000 < 0.5 then '20%降幅组' end as reduce_tag
from (
  select *
  from (
  select *,
    row_number() over (partition by externalid order by settle_time) as rn_outer 
  from mx.darren_jieqing_base_table_t0) tt0 
  where rn_outer = 1 ) t0--- 走结清决策流
left join mx.darren_jieqing_base_table_t1 t1 
on t0.externalid = t1.externalid
left join (
select mid,
  jq_phone,
  jq_app_group_sha256,
  jq_credit_no
from (
  select mid,
    phone as jq_phone,
    app_group_sha256 as jq_app_group_sha256,
    credit_no as jq_credit_no,
    row_number() over (partition by mid order by create_time desc) as rn 
  from mx.wxs_application_funnel) t0 
  where rn = 1 
  group by 1,2,3,4) t2 
on t0.jq_mid = t2.mid
-- 提取cap
left join mx.darren_jieqing_base_table_t3 t3 
on t0.externalid = t3.externalid
left join mx.darren_jieqing_base_table_t4 t4
on t0.externalid = t4.externalid 
left join mx.darren_jieqing_base_table_t2 t5 
on t0.externalid = t5.externalid
left join (select mid_t2,
  row_number() over (partition by mid_t2 order by createtime) as rn,
  settle_adjust_quota_cnt,
  low_limit_first_settle_increase_tag
from mx.darren_jieqing_base_table_t2) t7 
on t0.jq_mid = t7.mid_t2 and t7.rn = 1 
left join mx.darren_jieqing_base_table_t8 t8 
on t0.externalid = t8.externalid
left join (select externalid as externalid9,
  row_number() over (partition by externalid order by createtime) as rn,
  settle_adjust_quota_cnt,
  last_credit_amount as newcust_newest_credit_amount,
  low_limit_first_settle_increase_tag as first_loan_low_limit_first_settle_increase_tag
from mx.darren_jieqing_base_table_t2) t9 
on t0.externalid = t9.externalid9 and t9.rn = 1 
left join (
  select mid,
    newcust_credit_limit
  from dws.dws_risk_stgy_apply_mid_tags) t10 
on t0.jq_mid = t10.mid

left join (
  select externalid as externalid11,  
    row_number() over(partition by externalid order by createtime) as rn,
    android_oldCust_mainCreditLevel_charge_V5_2
  from mx.android_oldcust_main_creditlevel_charge_v5_2_param_table) t11
on cast(t0.externalid as varchar) = cast(t11.externalid11 as varchar)
and t11.rn = 1 
left join (
--- mid维度的结清期次数及结清订单数
select t0.externalid as externalid12
  ,count(distinct case when t1.state in (1,3,5) and fact_time < settle_time then rid end) as repayment_clearing_count_index
  ,count(distinct case when t2.state in (1,2) and finish_time < settle_time then camera_id end) as repayment_clearing_count

from mx.darren_jieqing_base_table_t0 t0
left join (select customer_id,fact_time,rid,state
  from ods_view_presto.s02_loan_repayment) t1--根据历史订单biz_id取所有放款订单
on cast(t0.jq_mid as bigint) = cast(t1.customer_id as bigint)
and t0.settle_time > t1.fact_time
left join (select customer_id,finish_time,camera_id,state
from ods_view_presto.s02_loan ) t2 --根据历史订单biz_id取所有放款订单
on cast(t0.jq_mid as bigint) = cast(t2.customer_id as bigint)
and t0.settle_time > t2.finish_time
group by 1) t12 
on cast(t0.externalid as varchar) = cast(t12.externalid12 as varchar)
left join (
--- 全局维度的结清期次数及结清订单数
select t0.externalid as externalid13
  ,count(distinct case when t1.state in (1,3,5) and fact_time < settle_time then rid end) as repayment_clearing_count_index_all
  ,count(distinct case when t2.state in (1,2) and finish_time < settle_time then camera_id end) as repayment_clearing_count_all
from 
(select t0.*,t1.identity
from 
  (select externalid,jq_mid,settle_time 
  from mx.darren_jieqing_base_table_t0) t0
left join mx.darren_identity_mid_base_table t1 
on cast(t0.jq_mid as bigint) = cast(t1.mid as bigint)) t0
left join (
  select t0.*,t1.identity
  from (select customer_id,fact_time,rid,state
  from ods_view_presto.s02_loan_repayment) t0 
  left join mx.darren_identity_mid_base_table t1 
  on cast(t0.customer_id as bigint) = cast(t1.mid as bigint)) t1
on t0.identity  = t1.identity 
and t0.settle_time > t1.fact_time
left join (
  select t0.*,t1.identity
  from (select customer_id,finish_time,camera_id,state
  from ods_view_presto.s02_loan) t0 
  left join mx.darren_identity_mid_base_table t1 
  on cast(t0.customer_id as bigint) = cast(t1.mid as bigint)) t2 
on t0.identity = t2.identity 
and t0.settle_time > t2.finish_time
group by 1) t13 
on cast(t0.externalid as varchar) = cast(t13.externalid13 as varchar)
left join (
  select externalid as externalid14,  
    row_number() over(partition by externalid order by createtime) as rn,
    android_oldCust_mainCreditLevel_charge_V5_3
  from mx.android_oldCust_mainCreditLevel_charge_V5_3_table) t14
on cast(t0.externalid as varchar) = cast(t14.externalid14 as varchar)
and t14.rn = 1 
left join (
  select externalid as externalid15,
    last_credit_amount_change_day_gap,
    curr_ovd_cnt_all,
    curr_ovd_cnt_this_app_group,
    curr_ovd_cnt_other_app_group_90d,
    max_overdue_day_30d_all,
    last_credit_increase_day_gap,
    hist_loanrec_cnt_issue_days_last_jieqing,
    settle_adjust_quota_cnt,
    is_settle_adjust_quota_flag
  from mx.darren_jieqing_base_table_t9) t15 
on cast(t0.externalid as varchar) = cast(t15.externalid15 as varchar)
left join 
(
select externalid as externalid16,first_settle_reloan_creditlvl_V5_3,first_settle_reloan_creditlvl_V6_1,first_settle_reloan_tag
from mx.darren_jieqing_base_table_t10  
where rn =1
)t16
on cast(t0.externalid as varchar) = cast(t16.externalid16 as varchar)
left join (
  select externalid as externalidt17,  
    row_number() over(partition by externalid order by createtime) as rn,
    android_oldCust_mainCreditLevel_charge_V6_1
  from mx.android_oldCust_mainCreditLevel_charge_V6_1_table) t17
on cast(t0.externalid as varchar) = cast(t17.externalidt17 as varchar)
and t17.rn = 1 
)
;




drop table if exists mx.darren_jieqing_dt_table;
create table mx.darren_jieqing_dt_table as 
select *,
  case when date_diff('minute',trigger_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp)) < 24*60 then -1 
    when apply_time is null or date_diff('minute',trigger_time,apply_time) > 24*60 then 0
    when date_diff('minute',trigger_time,apply_time) <= 24*60 then 1 end as if_sx_passed_in_24h_after_jieqing, 
  case when date_diff('minute',trigger_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp)) < 48*60 then -1 
    when apply_time is null or date_diff('minute',trigger_time,apply_time) > 48*60 then 0
    when date_diff('minute',trigger_time,apply_time) <= 48*60 then 1 end as if_sx_passed_in_48h_after_jieqing, 
  case when date_diff('minute',trigger_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp)) < 72*60 then -1 
    when apply_time is null or date_diff('minute',trigger_time,apply_time) > 72*60 then 0
    when date_diff('minute',trigger_time,apply_time) <= 72*60 then 1 end as if_sx_passed_in_72h_after_jieqing, 
  case when date_diff('minute',trigger_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp)) < 120*60 then -1 
    when apply_time is null or date_diff('minute',trigger_time,apply_time) > 120*60 then 0
    when date_diff('minute',trigger_time,apply_time) <= 120*60 then 1 end as if_sx_passed_in_120h_after_jieqing
from mx.darren_jieqing_dt_base_table t0 
left join (select *,case when product_name='14天产品C_07_02_00_63' then 'C_07_02_00_63'
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
where date(create_time) >= date'2025-10-11') t1 
on t0.jq_mid = t1.mid
and t0.settle_time < t1.create_time
and date_diff('day',date(t0.settle_time),date(t1.create_time)) < 5 
and is_settle_adjust_quota_flag = 1
left join (
select biz_id as biz_id2,
  change_used_grantamount,risk_credit_limit
from mx.darren_bizid_used_grantamount) t2 
on t1.biz_id = t2.biz_id2
left join (
select biz_id as biz_id3,
  oneday_used_grantamount
from mx.darren_day_used_grantamount) t3
on t1.biz_id = t3.biz_id3
left join (select biz_id4,
  sx_credit_amount,
  sx_daily_max_available_limit 
  from mx.darren_jieqing_base_table_t7) t4
on t1.biz_id = cast(cast(t4.biz_id4 as bigint) as varchar)
left join (
  select external_id,trigger_time
  from ods.s05_user_riskcall_time_record) t5 
on t0.externalid = t5.external_id 
left join 
 (select camera_id as camera_id6,
  sum(interest+contract_amount-amount) as equal_houshou_should_interest,
  sum(amount) as real_issue_amount,
  sum(contract_amount) as loan_contract_amount
from ods_view_presto.s02_loan
group by 1) t6
on cast(t1.biz_id as bigint) = cast(t6.camera_id6 as bigint)
;



drop table if exists mx.darren_shouci_jieqing_dt_table;
create table mx.darren_shouci_jieqing_dt_table as 
select *
from (
select *
from (
select jq_mid,
  settle_time,
  from_base(substr(to_hex(sha256(to_utf8('20260624'||jq_credit_no||jq_app_group_sha256))),1,4),16)/65536.0000000000000000 as first_settle_sha256,
  row_number() over (partition by jq_mid order by settle_time) as rn 
from mx.darren_jieqing_dt_base_table
where date(settle_time) >= date '2026-08-14'
and max_overdue_day_30d_all <= 2
and curr_ovd_cnt_this_app_group <= 0
and curr_ovd_cnt_other_app_group_90d <= 0
and settle_adjust_quota_cnt = 0
and last_credit_amount_change_day_gap in (3, 4))tt0 
where rn = 1 ) t0 
left join (select *,case when product_name='14天产品C_07_02_00_63' then 'C_07_02_00_63'
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
where date(create_time) >= date'2026-05-25') t1 
on t0.jq_mid = t1.mid
and t0.settle_time < t1.create_time
-- and date_diff('day',date(t0.settle_time),date(t1.create_time)) < 5 
-- and settle_adjust_quota_cnt = 0
left join (
select biz_id as biz_id2,
  change_used_grantamount
from mx.darren_bizid_used_grantamount) t2 
on t1.biz_id = t2.biz_id2
left join (
select biz_id as biz_id3,
  oneday_used_grantamount
from mx.darren_day_used_grantamount) t3
on t1.biz_id = t3.biz_id3
left join (select biz_id4,
  sx_credit_amount,
  sx_daily_max_available_limit 
  from mx.darren_jieqing_base_table_t7) t4
on t1.biz_id = cast(cast(t4.biz_id4 as bigint) as varchar)
where date(settle_time) >= date'2026-05-25'
;


drop table if exists mx.darren_shouci_jieqing_summary_table;
create table mx.darren_shouci_jieqing_summary_table as 
select 
--- 20260630 更换随机数token
  case when first_settle_sha256 >= 0.5 then '对照组'
    when first_settle_sha256 < 0.5 then '测试组' end as new_cust_low_limit_flag,
  count(distinct jq_mid) as new_cnt,
  
  -- ===== 7天窗口 =====
  count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then mid end) as old_customer_loan_count_7d,
  count(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then biz_id end) as old_customer_loan_num_7d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then contract_amount else 0 end) as old_customer_loan_amount_7d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then mid else null end), 0) as old_customer_loan_efficiency_7d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then biz_id else null end), 0) as old_customer_loan_avg_7d,
  (1 - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then real_issue_amount else 0 end) / 
     nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then contract_amount else 0 end), 0)) as old_customer_pre_interest_rate_7d,
  (sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then equal_houshou_should_interest else 0 end) 
    - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then contract_amount else 0 end)
    + sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then real_issue_amount else 0 end)) /
    nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then contract_amount else 0 end), 0) as old_customer_post_interest_rate_7d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then is_t3_window_1 else 0 end) as old_1t3_flag_cnt_7d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then t3_overdue_amount_1 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then t3_should_amt_1 else 0 end),0) as old_1T3_7d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then is_t3_window_3 else 0 end) as old_3t3_flag_cnt_7d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then t3_overdue_amount_3 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 7 then t3_should_amt_3 else 0 end),0) as old_3T3_7d,
  sum(case when date_diff('day', settle_time, app_time) <= 7 then contract_amount else 0 end) as t7_issue_amt,
  sum(t7_fact_amt_tot) as t7_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 7 then t7_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 7 then contract_amount else 0 end) as t7_balance_amt,

  -- ===== 14天窗口 =====
  count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then mid end) as old_customer_loan_count_14d,
  count(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then biz_id end) as old_customer_loan_num_14d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then contract_amount else 0 end) as old_customer_loan_amount_14d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then mid else null end), 0) as old_customer_loan_efficiency_14d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then biz_id else null end), 0) as old_customer_loan_avg_14d,
  (1 - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then real_issue_amount else 0 end) / 
     nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then contract_amount else 0 end), 0)) as old_customer_pre_interest_rate_14d,
  (sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then equal_houshou_should_interest else 0 end) 
    - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then contract_amount else 0 end)
    + sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then real_issue_amount else 0 end)) /
    nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then contract_amount else 0 end), 0) as old_customer_post_interest_rate_14d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then is_t3_window_1 else 0 end) as old_1t3_flag_cnt_14d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then t3_overdue_amount_1 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then t3_should_amt_1 else 0 end),0) as old_1T3_14d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then is_t3_window_3 else 0 end) as old_3t3_flag_cnt_14d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then t3_overdue_amount_3 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 14 then t3_should_amt_3 else 0 end),0) as old_3T3_14d,
  sum(case when date_diff('day', settle_time, app_time) <= 14 then contract_amount else 0 end) as t14_issue_amt,
  sum(t14_fact_amt_tot) as t14_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 14 then t14_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 14 then contract_amount else 0 end) as t14_balance_amt,

  -- ===== 21天窗口 =====
  count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then mid end) as old_customer_loan_count_21d,
  count(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then biz_id end) as old_customer_loan_num_21d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then contract_amount else 0 end) as old_customer_loan_amount_21d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then mid else null end), 0) as old_customer_loan_efficiency_21d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then biz_id else null end), 0) as old_customer_loan_avg_21d,
  (1 - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then real_issue_amount else 0 end) / 
     nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then contract_amount else 0 end), 0)) as old_customer_pre_interest_rate_21d,
  (sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then equal_houshou_should_interest else 0 end) 
    - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then contract_amount else 0 end)
    + sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then real_issue_amount else 0 end)) /
    nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then contract_amount else 0 end), 0) as old_customer_post_interest_rate_21d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then is_t3_window_1 else 0 end) as old_1t3_flag_cnt_21d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then t3_overdue_amount_1 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then t3_should_amt_1 else 0 end),0) as old_1T3_21d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then is_t3_window_3 else 0 end) as old_3t3_flag_cnt_21d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then t3_overdue_amount_3 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 21 then t3_should_amt_3 else 0 end),0) as old_3T3_21d,
  sum(case when date_diff('day', settle_time, app_time) <= 21 then contract_amount else 0 end) as t21_issue_amt,
  sum(t21_fact_amt_tot) as t21_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 21 then t21_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 21 then contract_amount else 0 end) as t21_balance_amt,

  -- ===== 28天窗口 =====
  count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then mid end) as old_customer_loan_count_28d,
  count(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then biz_id end) as old_customer_loan_num_28d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then contract_amount else 0 end) as old_customer_loan_amount_28d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then mid else null end), 0) as old_customer_loan_efficiency_28d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then biz_id else null end), 0) as old_customer_loan_avg_28d,
  (1 - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then real_issue_amount else 0 end) / 
     nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then contract_amount else 0 end), 0)) as old_customer_pre_interest_rate_28d,
  (sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then equal_houshou_should_interest else 0 end) 
    - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then contract_amount else 0 end)
    + sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then real_issue_amount else 0 end)) /
    nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then contract_amount else 0 end), 0) as old_customer_post_interest_rate_28d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then is_t3_window_1 else 0 end) as old_1t3_flag_cnt_28d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then t3_overdue_amount_1 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then t3_should_amt_1 else 0 end),0) as old_1T3_28d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then is_t3_window_3 else 0 end) as old_3t3_flag_cnt_28d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then t3_overdue_amount_3 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 28 then t3_should_amt_3 else 0 end),0) as old_3T3_28d,
  sum(case when date_diff('day', settle_time, app_time) <= 28 then contract_amount else 0 end) as t28_issue_amt,
  sum(t28_fact_amt_tot) as t28_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 28 then t28_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 28 then contract_amount else 0 end) as t28_balance_amt,

  -- ===== 35天窗口 =====
  count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then mid end) as old_customer_loan_count_35d,
  count(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then biz_id end) as old_customer_loan_num_35d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then contract_amount else 0 end) as old_customer_loan_amount_35d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then mid else null end), 0) as old_customer_loan_efficiency_35d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then biz_id else null end), 0) as old_customer_loan_avg_35d,
  (1 - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then real_issue_amount else 0 end) / 
     nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then contract_amount else 0 end), 0)) as old_customer_pre_interest_rate_35d,
  (sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then equal_houshou_should_interest else 0 end) 
    - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then contract_amount else 0 end)
    + sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then real_issue_amount else 0 end)) /
    nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then contract_amount else 0 end), 0) as old_customer_post_interest_rate_35d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then is_t3_window_1 else 0 end) as old_1t3_flag_cnt_35d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then t3_overdue_amount_1 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then t3_should_amt_1 else 0 end),0) as old_1T3_35d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then is_t3_window_3 else 0 end) as old_3t3_flag_cnt_35d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then t3_overdue_amount_3 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 35 then t3_should_amt_3 else 0 end),0) as old_3T3_35d,
  sum(case when date_diff('day', settle_time, app_time) <= 35 then contract_amount else 0 end) as t35_issue_amt,
  sum(t35_fact_amt_tot) as t35_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 35 then t35_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 35 then contract_amount else 0 end) as t35_balance_amt,

  -- ===== 42天窗口 =====
  count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then mid end) as old_customer_loan_count_42d,
  count(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then biz_id end) as old_customer_loan_num_42d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then contract_amount else 0 end) as old_customer_loan_amount_42d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then mid else null end), 0) as old_customer_loan_efficiency_42d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then biz_id else null end), 0) as old_customer_loan_avg_42d,
  (1 - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then real_issue_amount else 0 end) / 
     nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then contract_amount else 0 end), 0)) as old_customer_pre_interest_rate_42d,
  (sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then equal_houshou_should_interest else 0 end) 
    - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then contract_amount else 0 end)
    + sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then real_issue_amount else 0 end)) /
    nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then contract_amount else 0 end), 0) as old_customer_post_interest_rate_42d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then is_t3_window_1 else 0 end) as old_1t3_flag_cnt_42d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then t3_overdue_amount_1 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then t3_should_amt_1 else 0 end),0) as old_1T3_42d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then is_t3_window_3 else 0 end) as old_3t3_flag_cnt_42d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then t3_overdue_amount_3 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 42 then t3_should_amt_3 else 0 end),0) as old_3T3_42d,
  sum(case when date_diff('day', settle_time, app_time) <= 42 then contract_amount else 0 end) as t42_issue_amt,
  sum(t42_fact_amt_tot) as t42_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 42 then t42_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 42 then contract_amount else 0 end) as t42_balance_amt,

  -- ===== 49天窗口 =====
  count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then mid end) as old_customer_loan_count_49d,
  count(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then biz_id end) as old_customer_loan_num_49d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then contract_amount else 0 end) as old_customer_loan_amount_49d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then mid else null end), 0) as old_customer_loan_efficiency_49d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then biz_id else null end), 0) as old_customer_loan_avg_49d,
  (1 - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then real_issue_amount else 0 end) / 
     nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then contract_amount else 0 end), 0)) as old_customer_pre_interest_rate_49d,
  (sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then equal_houshou_should_interest else 0 end) 
    - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then contract_amount else 0 end)
    + sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then real_issue_amount else 0 end)) /
    nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then contract_amount else 0 end), 0) as old_customer_post_interest_rate_49d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then is_t3_window_1 else 0 end) as old_1t3_flag_cnt_49d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then t3_overdue_amount_1 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then t3_should_amt_1 else 0 end),0) as old_1T3_49d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then is_t3_window_3 else 0 end) as old_3t3_flag_cnt_49d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then t3_overdue_amount_3 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 49 then t3_should_amt_3 else 0 end),0) as old_3T3_49d,
  sum(case when date_diff('day', settle_time, app_time) <= 49 then contract_amount else 0 end) as t49_issue_amt,
  sum(t49_fact_amt_tot) as t49_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 49 then t49_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 49 then contract_amount else 0 end) as t49_balance_amt,

  -- ===== 56天窗口 =====
  count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then mid end) as old_customer_loan_count_56d,
  count(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then biz_id end) as old_customer_loan_num_56d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then contract_amount else 0 end) as old_customer_loan_amount_56d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then mid else null end), 0) as old_customer_loan_efficiency_56d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then biz_id else null end), 0) as old_customer_loan_avg_56d,
  (1 - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then real_issue_amount else 0 end) / 
     nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then contract_amount else 0 end), 0)) as old_customer_pre_interest_rate_56d,
  (sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then equal_houshou_should_interest else 0 end) 
    - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then contract_amount else 0 end)
    + sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then real_issue_amount else 0 end)) /
    nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then contract_amount else 0 end), 0) as old_customer_post_interest_rate_56d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then is_t3_window_1 else 0 end) as old_1t3_flag_cnt_56d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then t3_overdue_amount_1 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then t3_should_amt_1 else 0 end),0) as old_1T3_56d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then is_t3_window_3 else 0 end) as old_3t3_flag_cnt_56d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then t3_overdue_amount_3 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 56 then t3_should_amt_3 else 0 end),0) as old_3T3_56d,
  sum(case when date_diff('day', settle_time, app_time) <= 56 then contract_amount else 0 end) as t56_issue_amt,
  sum(t56_fact_amt_tot) as t56_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 56 then t56_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 56 then contract_amount else 0 end) as t56_balance_amt,

  -- ===== 63天窗口 =====
  count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then mid end) as old_customer_loan_count_63d,
  count(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then biz_id end) as old_customer_loan_num_63d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then contract_amount else 0 end) as old_customer_loan_amount_63d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then mid else null end), 0) as old_customer_loan_efficiency_63d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then biz_id else null end), 0) as old_customer_loan_avg_63d,
  (1 - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then real_issue_amount else 0 end) / 
     nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then contract_amount else 0 end), 0)) as old_customer_pre_interest_rate_63d,
  (sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then equal_houshou_should_interest else 0 end) 
    - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then contract_amount else 0 end)
    + sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then real_issue_amount else 0 end)) /
    nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then contract_amount else 0 end), 0) as old_customer_post_interest_rate_63d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then is_t3_window_1 else 0 end) as old_1t3_flag_cnt_63d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then t3_overdue_amount_1 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then t3_should_amt_1 else 0 end),0) as old_1T3_63d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then is_t3_window_3 else 0 end) as old_3t3_flag_cnt_63d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then t3_overdue_amount_3 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 63 then t3_should_amt_3 else 0 end),0) as old_3T3_63d,
  sum(case when date_diff('day', settle_time, app_time) <= 63 then contract_amount else 0 end) as t63_issue_amt,
  sum(t63_fact_amt_tot) as t63_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 63 then t63_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 63 then contract_amount else 0 end) as t63_balance_amt,

  -- ===== 原有30天窗口（保留） =====
  count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then mid end) as old_customer_loan_count_30d,
  count(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then biz_id end) as old_customer_loan_num_30d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then contract_amount else 0 end) as old_customer_loan_amount_30d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then mid else null end), 0) as old_customer_loan_efficiency_30d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then contract_amount else 0 end) / 
    nullif(count(distinct case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then biz_id else null end), 0) as old_customer_loan_avg_30d,
  (1 - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then real_issue_amount else 0 end) / 
     nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then contract_amount else 0 end), 0)) as old_customer_pre_interest_rate_30d,
  (sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then equal_houshou_should_interest else 0 end) 
    - sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then contract_amount else 0 end)
    + sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then real_issue_amount else 0 end)) /
    nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then contract_amount else 0 end), 0) as old_customer_post_interest_rate_30d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then is_t3_window_1 else 0 end) as old_1t3_flag_cnt_30d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then t3_overdue_amount_1 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then t3_should_amt_1 else 0 end),0) as old_1T3_30d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then is_t3_window_3 else 0 end) as old_3t3_flag_cnt_30d,
  sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then t3_overdue_amount_3 else 0 end)/nullif(sum(case when is_reloan = 'old' and date_diff('day', settle_time, app_time) <= 30 then t3_should_amt_3 else 0 end),0) as old_3T3_30d,
  sum(case when date_diff('day', settle_time, app_time) <= 30 then contract_amount else 0 end) as t30_issue_amt,
  sum(t30_fact_amt_tot) as t30_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 30 then t30_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 30 then contract_amount else 0 end) as t30_balance_amt,

  -- ===== 原有60天窗口（保留） =====
  sum(case when date_diff('day', settle_time, app_time) <= 60 then contract_amount else 0 end) as t60_issue_amt,
  sum(t60_fact_amt_tot) as t60_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 60 then t60_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 60 then contract_amount else 0 end) as t60_balance_amt,

  -- ===== 原有90天窗口（保留） =====
  sum(case when date_diff('day', settle_time, app_time) <= 90 then contract_amount else 0 end) as t90_issue_amt,
  sum(t90_fact_amt_tot) as t90_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 90 then t90_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 90 then contract_amount else 0 end) as t90_balance_amt,

  -- ===== 原有120天窗口（保留） =====
  sum(case when date_diff('day', settle_time, app_time) <= 120 then contract_amount else 0 end) as t120_issue_amt,
  sum(t120_fact_amt_tot) as t120_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 120 then t120_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 120 then contract_amount else 0 end) as t120_balance_amt,

  -- ===== 原有150天窗口（保留） =====
  sum(case when date_diff('day', settle_time, app_time) <= 150 then contract_amount else 0 end) as t150_issue_amt,
  sum(t150_fact_amt_tot) as t150_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 150 then t150_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 150 then contract_amount else 0 end) as t150_balance_amt,

  -- ===== 原有180天窗口（保留） =====
  sum(case when date_diff('day', settle_time, app_time) <= 180 then contract_amount else 0 end) as t180_issue_amt,
  sum(t180_fact_amt_tot) as t180_fact_amt_tot,
  sum(case when date_diff('day', settle_time, app_time) <= 180 then t180_fact_amt_tot else 0 end) - sum(case when date_diff('day', settle_time, app_time) <= 180 then contract_amount else 0 end) as t180_balance_amt

from (
  -- 主查询子查询 t：包含所有基础字段及计算 settle_time
  select 
    a.*,
    -- b.new_cust_low_limit_flag,
    c.equal_houshou_should_interest,
    c.real_issue_amount,
    c.interest
  from mx.darren_shouci_jieqing_dt_table a
  left join (
    select 
      camera_id as biz_id_tt5,
      sum(interest + contract_amount - amount) as equal_houshou_should_interest,
      sum(amount) as real_issue_amount,
      sum(interest) as interest
    from ods_view_presto.s02_loan
    group by camera_id
  ) c on cast(a.biz_id as bigint) = cast(c.biz_id_tt5 as bigint)
) t
left join 
(
  -- 子查询 t2：计算各窗口实际偿还本息（已扩展至7~63天，并保留原有30,60,90,120,150,180）
  select
    biz_id as biz_id2,
    -- 新增7~63天
    sum(case when date_diff('day', settle_time, app_time) <= 7  and date_diff('day', settle_time, fact_time) <= 7  then fact_capital+fact_interest end) as t7_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 14 and date_diff('day', settle_time, fact_time) <= 14 then fact_capital+fact_interest end) as t14_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 21 and date_diff('day', settle_time, fact_time) <= 21 then fact_capital+fact_interest end) as t21_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 28 and date_diff('day', settle_time, fact_time) <= 28 then fact_capital+fact_interest end) as t28_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 35 and date_diff('day', settle_time, fact_time) <= 35 then fact_capital+fact_interest end) as t35_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 42 and date_diff('day', settle_time, fact_time) <= 42 then fact_capital+fact_interest end) as t42_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 49 and date_diff('day', settle_time, fact_time) <= 49 then fact_capital+fact_interest end) as t49_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 56 and date_diff('day', settle_time, fact_time) <= 56 then fact_capital+fact_interest end) as t56_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 63 and date_diff('day', settle_time, fact_time) <= 63 then fact_capital+fact_interest end) as t63_fact_amt_tot,
    -- 原有30,60,90,120,150,180
    sum(case when date_diff('day', settle_time, app_time) <= 30 and date_diff('day', settle_time, fact_time) <= 30 then fact_capital+fact_interest end) as t30_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 60 and date_diff('day', settle_time, fact_time) <= 60 then fact_capital+fact_interest end) as t60_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 90 and date_diff('day', settle_time, fact_time) <= 90 then fact_capital+fact_interest end) as t90_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 120 and date_diff('day', settle_time, fact_time) <= 120 then fact_capital+fact_interest end) as t120_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 150 and date_diff('day', settle_time, fact_time) <= 150 then fact_capital+fact_interest end) as t150_fact_amt_tot,
    sum(case when date_diff('day', settle_time, app_time) <= 180 and date_diff('day', settle_time, fact_time) <= 180 then fact_capital+fact_interest end) as t180_fact_amt_tot
  from 
  (
    select 
      b1.biz_id, b1.app_time,
      b2.*,
      min(case when b1.is_reloan = 'new' then b1.app_time else null end) over (partition by b1.mid) as settle_time
    from mx.wxs_application_funnel b1 
    left join ods_view_presto.s02_loan_repayment_detail b2 
      on b1.biz_id = cast(cast(b2.camera_id as bigint) as varchar)
  ) base2
  group by 1
) t2 on t.biz_id = t2.biz_id2
group by 1;