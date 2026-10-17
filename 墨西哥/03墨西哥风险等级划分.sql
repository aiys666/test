
--:{author=wenjing, department=墨西哥风险策略, dagName=darren_risk_wide_table, taskName=darren_risk_wide_table}
-- 3、取高通过组标签(租户首复贷判断决策流)\credit_amount&daily_max_available_limit复贷授信决策流
delete from mx.tmp_wenj_product_table
where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
;
--:{author=wenjing, department=墨西哥风险策略, dagName=darren_risk_wide_table, taskName=darren_risk_wide_table}
insert into mx.tmp_wenj_product_table
select biz_id, 
  max(cast(json_extract_scalar(outputdata, '$.credit_amount') as double)) as credit_amount,
  max(cast(json_extract_scalar(outputdata, '$.daily_max_available_limit') as double)) as daily_max_available_limit,
  etl_date
from(
  select biz_id, outputdata,etl_date
  from ods.s21_risk_strategy_record 
  where etl_date >= to_char(date_add('day', -1, current_date), 'yyyymmdd')
    and productid in (195,196,217,304)
    and strategytype = 'CHAMPION'
) t0
group by 1,4
;
--:{author=wenjing, department=墨西哥风险策略, dagName=darren_risk_wide_table, taskName=darren_risk_wide_table}
drop table if exists mx.darren_risk_wide_table
;
--:{author=wenjing, department=墨西哥风险策略, dagName=darren_risk_wide_table, taskName=darren_risk_wide_table}
create table mx.darren_risk_wide_table as 
SELECT 
    a.*, 
    -- 第二张表宽表字段（原 b.*，直接内联其逻辑）
    b.day as b_day,
    b.create_time as b_create_time,
    b.release_day as b_release_day,
    b.t0_biz_id,  
    b.release_time as b_release_time,
    -- b.double_loan as double_loan_2,
    case when e.double_loan_tenant is not null then e.double_loan_tenant 
         when e.double_loan_tenant is null and b.double_loan is not null then b.double_loan
    else 0 end as double_loan_2,
    b.phone_num as b_phone_num,
    b.credit_no as b_credit_no,
    b.cust_name as b_cust_name,
    b.card_no as b_card_no,
    b.cust_id as b_cust_id,
    b.mid as b_mid,
    b.tenant_id as b_tenant_id,
    b.app_name as b_app_name,
    b.source as b_source,
    b.app_channel as b_app_channel,
    b.app_group,
    b.app_version as b_app_version,
    b.apply_period as b_apply_period,
    b.apply_amount as b_apply_amount,
    b.product_level as b_product_level,
    b.new_media_source,
    b.campaign_name,
    -- 反欺诈类标记（首贷/复贷/弱反欺诈）
    b.if_in_shou_anti_fraud,
    b.if_shou_anti_fraud_passed,
    b.if_shou_anti_fraud_refused,
    b.if_in_fu_anti_fraud,
    b.if_fu_anti_fraud_passed,
    b.if_fu_anti_fraud_refused,
    b.if_in_shou_anti_fraud_weak,
    b.if_shou_anti_fraud_weak_passed,
    b.if_shou_anti_fraud_weak_refused,
    b.if_in_fu_anti_fraud_weak,
    b.if_fu_anti_fraud_weak_passed,
    b.if_fu_anti_fraud_weak_refused,
    -- 模型类标记（首贷/复贷）
    b.if_in_shou_model,
    b.if_shou_model_passed,
    b.if_shou_model_refused,
    b.if_in_fu_model,
    b.if_fu_model_passed,
    b.if_fu_model_refused,
    -- 人工审核类标记（首贷/复贷）
    b.if_in_shou_normal_check,
    b.if_shou_normal_check_passed,
    b.if_shou_normal_check_refused,
    b.if_shou_normal_check_canceled,
    b.if_shou_manual_check_pending,
    b.if_in_fu_manual_check,
    b.if_fu_normal_check_passed,
    b.if_fu_normal_check_refused,
    b.if_fu_normal_check_canceled,
    b.if_fu_manual_check_pending,
    -- 三方数据类标记（首贷/复贷）
    b.if_in_shou_external_data,
    b.if_shou_external_data_passed,
    b.if_shou_external_data_refused,
    b.if_shou_external_data_review,
    b.if_in_fu_external_data,
    b.if_fu_external_data_passed,
    b.if_fu_external_data_refused,
    -- 规则类标记（首贷/复贷）
    b.if_in_shou_normal_rule_check,
    b.if_shou_normal_rule_check_passed,
    b.if_shou_normal_rule_check_canceled,
    b.if_shou_normal_rule_check_refused,
    b.if_fu_normal_rule_check_passed,
    b.if_fu_normal_rule_check_canceled,
    b.if_fu_normal_rule_check_refused,
    -- AI类标记（电核/FDAI）
    b.if_in_sd_ai,
    b.if_shou_ai_passed,
    b.if_shou_ai_pending,
    b.if_in_fd_ai,
    b.if_fu_ai_passed,
    b.if_fu_ai_refused,
    b.if_fu_ai_pending,
    -- 授信等待节点标记（首贷/复贷）
    b.if_in_sx,
    b.if_sx_passed,
    b.if_sx_waiting,
    b.if_in_post_model,
    b.if_post_model_passed,
    b.if_post_model_refused,
    -- 复贷拒绝标记
    b.if_in_fu_sx_refuse,
    b.if_fu_sx_refuse_passed,
    b.if_fu_sx_refuse_refused,
    b.if_in_shou_free_model,
    b.if_shou_free_model_passed,
    b.if_shou_free_model_refused,
    b.if_in_shou_anti_fraud_rerun,
    b.if_shou_anti_fraud_rerun_passed,
    b.if_shou_anti_fraud_rerun_refused,
    b.if_in_shou_anti_fraud_weak_rerun,
    b.if_shou_anti_fraud_weak_rerun_passed,
    b.if_shou_anti_fraud_weak_rerun_refused,
    b.if_in_shou_post_model_reject_rerun,
    b.if_shou_post_model_reject_rerun_passed,
    b.if_shou_post_model_reject_rerun_refused,

    --新增节点0512
    b.if_in_shou_loan_refuse,
    b.if_shou_loan_refuse_reject_passed,
    b.if_shou_loan_refuse_reject_refused,
    
    -- 额度/分数类字段
    b.grantcredit_7d_amount as b_grantcredit_7d_amount,
    b.grantcredit_14d_amount as b_grantcredit_14d_amount,
    b.contract_amount as b_contract_amount,
    b.should_capital as b_should_capital,
    b.should_interest as b_should_interest,
    b.camera_id,
    b.apply_phase,
    
    -- 第一张表 c 表新增字段（授信等待节点时效标记）
    c.if_sx_passed_within24h,  -- 首贷授信等待节点24小时内通过标记
    c.if_sx_passed_within48h,  -- 首贷授信等待节点48小时内通过标记
    c.if_sx_passed_within72h,  -- 首贷授信等待节点72小时内通过标记
    c.if_sx_passed_within120h,  -- 首贷授信等待节点120小时内通过标记
    c.if_sx_passed_within11h,  -- 首贷授信等待节点11小时内通过标记
    c.if_in_sx_over24h,        -- 首贷授信等待节点超过24小时标记
    c.if_in_sx_over48h,        -- 首贷授信等待节点超过48小时标记
    c.if_in_sx_over72h,        -- 首贷授信等待节点超过72小时标记
    c.if_in_sx_over120h,        -- 首贷授信等待节点超过120小时标记
    c.if_in_sx_over11h,        -- 首贷授信等待节点超过11小时标记
    c.if_in_sx_within24h,        -- 首贷授信等待节点未超过24小时标记
    c.if_in_sx_within48h,        -- 首贷授信等待节点未超过48小时标记
    c.if_in_sx_within72h,        -- 首贷授信等待节点未超过72小时标记
    c.if_in_sx_within120h,        -- 首贷授信等待节点未超过120小时标记
    c.sx_time,                 -- 授信等待节点创建时间
    
    -- 新增计算列（信用号+渠道拼接）
    CONCAT(a.credit_no, b.app_channel) AS creditno_appchan,


    f.credit_amount,
    f.daily_max_available_limit,
    substr(cast(current_timestamp as varchar),1,19) as table_update_time 
FROM 
    -- 原第一张表主表 a（mx.darren_application_funnel_1）
    mx.darren_application_funnel_1 a
LEFT JOIN 
    -- 内联原第二张表的宽表逻辑（替代 b 表,即darren_wide_table）
    (
        SELECT 
            substr(cast(create_time as varchar),1,10) as day,
            create_time,
            substr(cast(release_time as varchar),1,10) as release_day,
            t0.biz_id as t0_biz_id,  -- 避免与后续 biz_id 冲突
            release_time,
            case when app_channel in ('cdf58da5-801a-4575-9af4-a56453cea6f3', 
                                        'cbcf1f5e-092a-44ad-abb9-7d5af8f023cb',
                                        'e5a5940e-eb8e-4188-ad1a-5bdbd4580938',
                                        '6d21fe7d-8344-419c-8c94-a7b5cc1c8ee8',
                                        '9922eb08-b998-46d9-b81e-469ae4c2e0ec',
                                        'ab9981d2-b48f-4df0-a086-ff7df6a4fa04',
                                        'db0d289f-d217-49ea-a889-c191776115ef',
                                        '4cc31ae6-937e-4fd3-bc98-862314e7cb68',
                                        '91379659-2dc0-42d2-8205-9de6d81f7550',
                                        'faa92afe-b81a-4d94-ba1a-15eb9d536833',
                                        '00b3fb44-7a1a-49f3-a1a2-d81deb4026f2') then 1 else double_loan end as double_loan,  
            app_group,
            -- 其他宽表字段（直接复制原第二张表的子查询逻辑）
            phone_num,
            credit_no,
            cust_name,
            card_no,
            cust_id,
            mid,
            tenant_id,
            app_name,
            source,
            app_channel,
            app_version,
            apply_period,
            apply_amount,
            product_level,
            new_media_source,
            campaign_name,
            if_in_shou_anti_fraud,
            if_shou_anti_fraud_passed,
            if_shou_anti_fraud_refused,
            if_in_fu_anti_fraud,
            if_fu_anti_fraud_passed,
            if_fu_anti_fraud_refused,
            if_in_shou_anti_fraud_weak,
            if_shou_anti_fraud_weak_passed,
            if_shou_anti_fraud_weak_refused,
            if_in_fu_anti_fraud_weak,
            if_fu_anti_fraud_weak_passed,
            if_fu_anti_fraud_weak_refused,
            if_in_shou_model,
            if_shou_model_passed,
            if_shou_model_refused,
            if_in_fu_model,
            if_fu_model_passed,
            if_fu_model_refused,
            if_in_shou_normal_check,
            if_shou_normal_check_passed,
            if_shou_normal_check_refused,
            if_shou_normal_check_canceled,
            if_shou_manual_check_pending,
             if_fu_normal_check_passed,
              if_fu_normal_check_refused,
            if_fu_normal_check_canceled,
            if_fu_manual_check_pending,
            if_in_fu_manual_check,
            if_in_shou_external_data,
            if_shou_external_data_passed,
            if_shou_external_data_refused,
            if_shou_external_data_review,
            if_in_fu_external_data,
            if_fu_external_data_passed,
            if_fu_external_data_refused,
            if_in_shou_normal_rule_check,
            if_shou_normal_rule_check_passed,
            if_shou_normal_rule_check_canceled,
            if_shou_normal_rule_check_refused,
            if_fu_normal_rule_check_passed,
            if_fu_normal_rule_check_canceled,
            if_fu_normal_rule_check_refused,
            if_in_sd_ai,
            if_shou_ai_passed,
            if_shou_ai_pending,
            if_in_fd_ai,
            if_fu_ai_passed,
            if_fu_ai_refused,
            if_fu_ai_pending,
            if_in_sx,
            if_sx_passed,
            if_sx_waiting,
            if_in_post_model,
            if_post_model_passed,
            if_post_model_refused,
            if_in_fu_sx_refuse,
            if_fu_sx_refuse_passed,
            if_fu_sx_refuse_refused,
            if_in_shou_free_model,
            if_shou_free_model_passed,
            if_shou_free_model_refused,
            if_in_shou_anti_fraud_rerun,
            if_shou_anti_fraud_rerun_passed,
            if_shou_anti_fraud_rerun_refused,
            if_in_shou_anti_fraud_weak_rerun,
            if_shou_anti_fraud_weak_rerun_passed,
            if_shou_anti_fraud_weak_rerun_refused,
            if_in_shou_post_model_reject_rerun,
            if_shou_post_model_reject_rerun_passed,
            if_shou_post_model_reject_rerun_refused,
            --新增节点0512
            if_in_shou_loan_refuse,
            if_shou_loan_refuse_reject_passed,
            if_shou_loan_refuse_reject_refused,

            grantcredit_7d_amount,
            grantcredit_14d_amount,
            contract_amount,
            should_capital,
            should_interest,
              -- should_capital + should_interest as should_amount
            t6.camera_id,
            apply_phase
        FROM (
            SELECT 
                biz_id,
                create_time,
                user_confirm_status,
                status,
                phone_num,
                cust_name,
                cust_id,
                mid,
                card_no,
                credit_no,
                tenant_id,
                double_loan,
                app_name,
                source,
                app_channel,
                apply_amount,
                app_version,
                apply_period
            FROM ods_view_presto.s05_creditx_order
            WHERE date(create_time) >= date_add('day',-720,date(now()))
        ) t0
        LEFT JOIN (
          select distinct biz_id,
				1 as if_in_shou_anti_fraud,
				case when (sum(case when approve_result = 'REFUSED' then 1 end)) is null then 1 
					else 0 end as if_shou_anti_fraud_passed,
				case when (sum(case when approve_result = 'REFUSED' then 1 end)) >= 1 then 1 
					else 0 end as if_shou_anti_fraud_refused
			from ods_view_presto.s05_creditx_processor_record 
			where current_processor in ('首贷强反欺诈')
			group by 1
        ) p1  -- 原宽表中 p1-p17 的子查询逻辑
        on t0.biz_id = p1.biz_id
        LEFT JOIN (
          select distinct biz_id, 
					1 as if_in_fu_anti_fraud,
					case when (sum(case when approve_result = 'REFUSED' then 1 end)) is null then 1 
						else 0 end as if_fu_anti_fraud_passed, 
					case when (sum(case when approve_result = 'REFUSED' then 1 end)) >= 1 then 1 
						else 0 end as if_fu_anti_fraud_refused
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('复贷强反欺诈') 
				group by 1
        ) p2
      on t0.biz_id = p2.biz_id
	left join(select distinct biz_id,
					1 as if_in_shou_anti_fraud_weak,
					case when (sum(case when approve_result = 'REFUSED' then 1 end)) is null then 1 
						else 0 end as if_shou_anti_fraud_weak_passed,
					case when (sum(case when approve_result = 'REFUSED' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_anti_fraud_weak_refused
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('首贷弱反欺诈')
				group by 1) p3
	on t0.biz_id = p3.biz_id
	left join(select distinct biz_id, 
					1 as if_in_fu_anti_fraud_weak,
					case when (sum(case when approve_result = 'REFUSED' then 1 end)) is null then 1 
						else 0 end as if_fu_anti_fraud_weak_passed, 
					case when (sum(case when approve_result = 'REFUSED' then 1 end)) >= 1 then 1 
					else 0 end as if_fu_anti_fraud_weak_refused
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('复贷弱反欺诈') 
				group by 1) p4
	on t0.biz_id = p4.biz_id
	left join(select distinct biz_id,
					1 as if_in_shou_model,
					case when (sum(case when approve_result = 'REFUSED' then 1 end)) is null then 1 
						else 0 end as if_shou_model_passed,
					case when (sum(case when approve_result = 'REFUSED' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_model_refused
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('首贷模型拒绝','首贷模型拒绝(低成本)') --- 前置的最后一个节点
				group by 1) p5 
	on t0.biz_id = p5.biz_id
	left join(select distinct biz_id, 
					1 as if_in_fu_model,
					case when (sum(case when approve_result = 'REFUSED' then 1 end)) is null then 1 
						else 0 end as if_fu_model_passed, 
					case when (sum(case when approve_result = 'REFUSED' then 1 end)) >= 1 then 1 
						else 0 end as if_fu_model_refused
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('复贷模型拒绝') 
				group by 1) p6
	on t0.biz_id = p6.biz_id
	left join(select distinct biz_id,  
					1 as if_in_shou_normal_check,
					case when (sum(case when approve_result = 'PASSED' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_normal_check_passed, 
					case when (sum(case when approve_result = 'CANCELED' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_normal_check_canceled,
					case when (sum(case when approve_result = 'REFUSED' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_normal_check_refused,
					case when (sum(case when approve_result is null then 1 end)) >= 1 then 1 
						else 0 end as if_shou_manual_check_pending
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('首贷初审','人审节点')   
				group by 1) p7
	on t0.biz_id = p7.biz_id
	left join(select distinct biz_id,  
					1 as if_in_fu_manual_check,
					case when (sum(case when approve_result='PASSED' then 1 end)) >= 1 then 1 
						else 0 end as if_fu_normal_check_passed, 
					case when (sum(case when approve_result='CANCELED' then 1 end)) >= 1 then 1 
						else 0 end as if_fu_normal_check_canceled,
					case when (sum(case when approve_result='REFUSED' then 1 end)) >=1 then 1 
						else 0 end as if_fu_normal_check_refused,
					case when (sum(case when approve_result is null then 1 end)) >=1 then 1 
						else 0 end as if_fu_manual_check_pending
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('复贷初审') 
				group by 1) p8
	on t0.biz_id = p8.biz_id
	left join(select distinct biz_id, 
					1 as if_in_shou_external_data,
					case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 
						else 0 end as if_shou_external_data_passed,
					case when (sum(case when approve_result='REFUSED' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_external_data_refused,
          case when (sum(case when json_extract_scalar(context_result, '$.myDecisionResult')='review' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_external_data_review
				from ods_view_presto.s05_creditx_processor_record
				where current_processor in ('首贷三方节点','首贷三方测试节点')  --- 后置通过
				group by 1) p9
	on t0.biz_id = p9.biz_id	
	left join(select distinct biz_id, 
					1 as if_in_fu_external_data,
					case when (sum(case when approve_result='REFUSED' then 1 end)) is null then 1 
						else 0 end as if_fu_external_data_passed,
					case when (sum(case when approve_result='REFUSED' then 1 end)) >= 1 then 1 
						else 0 end as if_fu_external_data_refused
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('复贷三方节点') 
				group by 1) p10
	on t0.biz_id = p10.biz_id	
	left join(select distinct biz_id,  
					1 as if_in_shou_normal_rule_check,
					case when (sum(case when cast(json_extract(context_result, '$.myDecisionResult') as varchar) = 'Normal' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_normal_rule_check_passed, 
					case when (sum(case when cast(json_extract(context_result, '$.myDecisionResult') as varchar)='cancel' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_normal_rule_check_canceled,
					case when (sum(case when cast(json_extract(context_result, '$.myDecisionResult') as varchar)='reject' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_normal_rule_check_refused
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('人审规则节点','人审规则节点_ios')  
				group by 1) p11
	on t0.biz_id = p11.biz_id	
	left join(select distinct biz_id,  
					1 as if_in_fu_normal_rule_check,
					case when (sum(case when cast(json_extract(context_result, '$.myDecisionResult') as varchar) is null then 1 end)) >= 1 then 1 
						else 0 end as if_fu_normal_rule_check_passed, 
					case when (sum(case when cast(json_extract(context_result, '$.myDecisionResult') as varchar)='cancel' then 1 end)) >= 1 then 1 
						else 0 end as if_fu_normal_rule_check_canceled,
					case when (sum(case when cast(json_extract(context_result, '$.myDecisionResult') as varchar)='reject' then 1 end)) >= 1 then 1 
						else 0 end as if_fu_normal_rule_check_refused
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('复贷人审规则')
				group by 1) p12
	on t0.biz_id = p12.biz_id	
	left join(select distinct biz_id,
					1 as if_in_sd_ai,
					case when (sum(case when approve_result='PASSED' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_ai_passed,
					case when (sum(case when approve_result='REFUSED' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_ai_refused,
					case when (sum(case when approve_result='WAITING' then 1 end)) >= 1 then 1 
						else 0 end as if_shou_ai_pending
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('电核规则节点')
				group by 1) p13 
	on t0.biz_id = p13.biz_id
	left join(select distinct biz_id,
					1 as if_in_fd_ai,
					case when (sum(case when approve_result='PASSED' then 1 end)) >= 1 then 1 
						else 0 end as if_fu_ai_passed,
					case when (sum(case when approve_result='REFUSED' then 1 end)) >= 1 then 1 
						else 0 end as if_fu_ai_refused,
					case when (sum(case when approve_result='WAITING' then 1 end)) >= 1 then 1 
						else 0 end as if_fu_ai_pending
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('FDAI')
				group by 1) p14 
	on t0.biz_id = p14.biz_id
  left join(select distinct biz_id,
					1 as if_in_sx,
					case when (sum(case when approve_result='PASSED' then 1 end)) >= 1 then 1 
						else 0 end as if_sx_passed,
					case when (sum(case when approve_result='WAITING' then 1 end)) >= 1 then 1 
						else 0 end as if_sx_waiting
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('首贷授信等待节点','复贷授信等待节点') --- 授信等待节点是后置的起始点
				group by 1) p15
	on t0.biz_id = p15.biz_id
left join (select distinct biz_id,
					1 as if_in_post_model,
					case when (sum(case when approve_result='PASSED' then 1 end)) >= 1 then 1 
						else 0 end as if_post_model_passed,
					case when (sum(case when approve_result='REFUSED' then 1 end)) >= 1 then 1 
						else 0 end as if_post_model_refused
				from ods_view_presto.s05_creditx_processor_record 
				where current_processor in ('首贷后置模型拒绝节点') --- 授信等待节点是后置的起始点
				group by 1) p16 
  on t0.biz_id = p16.biz_id
left join(SELECT distinct biz_id,
        1 as if_in_fu_sx_refuse,
        case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 
          else 0 end as if_fu_sx_refuse_passed,
        case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 
          else 0 end as if_fu_sx_refuse_refused
    FROM ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('复贷授信拒绝')
      group by 1) p17
  on t0.biz_id= p17.biz_id  
  left join(SELECT distinct biz_id,
        1 as if_in_shou_free_model,
        case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 
          else 0 end as if_shou_free_model_passed,
        case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 
          else 0 end as if_shou_free_model_refused
    FROM ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('首贷免费模型拒绝节点')
      group by 1) p18
  on t0.biz_id= p18.biz_id  
    left join(SELECT distinct biz_id,
        1 as if_in_shou_anti_fraud_rerun,
        case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 
          else 0 end as if_shou_anti_fraud_rerun_passed,
        case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 
          else 0 end as if_shou_anti_fraud_rerun_refused
    FROM ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('首贷后置强反重跑节点')
      group by 1) p19
  on t0.biz_id= p19.biz_id  
    left join(SELECT distinct biz_id,
        1 as if_in_shou_anti_fraud_weak_rerun,
        case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 
          else 0 end as if_shou_anti_fraud_weak_rerun_passed,
        case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 
          else 0 end as if_shou_anti_fraud_weak_rerun_refused
    FROM ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('首贷后置弱反重跑节点')
      group by 1) p20
  on t0.biz_id= p20.biz_id  
      left join(SELECT distinct biz_id,
        1 as if_in_shou_post_model_reject_rerun,
        case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 
          else 0 end as if_shou_post_model_reject_rerun_passed,
        case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 
          else 0 end as if_shou_post_model_reject_rerun_refused
    FROM ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('首贷后置模型拒绝重跑节点')
      group by 1) p21
  on t0.biz_id= p21.biz_id  
        left join(SELECT distinct biz_id,
        1 as if_in_shou_loan_refuse,
        case when (sum(case when approve_result='PASSED' then 1 end)) >=1 then 1 
          else 0 end as if_shou_loan_refuse_reject_passed,
        case when (sum(case when approve_result='REFUSED' then 1 end))>=1 then 1 
          else 0 end as if_shou_loan_refuse_reject_refused
    FROM ods_view_presto.s05_creditx_processor_record 
      where current_processor in ('放款拒绝节点')
      group by 1) p22
  on t0.biz_id= p22.biz_id 

  left join (select id,
				cast(json_extract(grantcredit_info, '$.product_level') as varchar) product_level,
				cast(json_extract(grantcredit_info, '$.grantcredit_7d_amount') as varchar) grantcredit_7d_amount,
				cast(json_extract(grantcredit_info, '$.grantcredit_14d_amount') as varchar) grantcredit_14d_amount
			from ods_view_presto.s09_os_credit_snapshot) t5  --- 快照表（实际上是授信表） 
on t0.biz_id = cast(t5.id as varchar)
left join (select camera_id,
				release_time,
				contract_amount
			from ods_view_presto.s02_loan) t6 
on t0.biz_id = cast(ceil(t6.camera_id) as varchar)
left join (SELECT mid as mid1,
case when lower(campaign) like '%cpf07%' then 'cpf07'
      when lower(campaign) like '%cpf10%' then 'cpf10' 
      when lower(campaign) like '%cpf06%' then 'cpf06' 
      when lower(campaign) like '%cpx05%'  then 'X05'
      when lower(campaign) like '%cpx07%' or lower(campaign) like '%cpx%' then 'X07'
      when lower(campaign) like '%cpv%2%' and lower(campaign) like '%bin1to8%' then 'cpv2_bin1to8'
      when lower(campaign) like '%cpv%2%' and lower(campaign) like '%weighted%' then 'cpv2_weighted'
      when lower(campaign) like '%cpv%' then 'cpv'
      else '其他' end  as campaign_name,
    CASE WHEN new_media_source IN ('vfine_int','dc1','jc','创蓝') THEN '小渠道'
		else new_media_source END AS new_media_source
FROM mx.gm_attribution_detail) t8 
on t0.mid = cast(t8.mid1 as varchar)
left join (select did,interval_start as apply_phase
from ods.s03_product_due) t9 
on cast(t0.apply_period as bigint) = t9.did
left join(select camera_id,
  sum(cast(should_capital as double)) as should_capital,
  sum(cast(should_interest as double)) as should_interest
from ods_view_presto.s02_loan_repayment
group by camera_id) t10
on cast(t0.biz_id as bigint) = cast(t10.camera_id as bigint)
left join (select app_channel as app_channel1,app_group
from ods.s08_app_category_mapping) t11 
on t0.app_channel = t11.app_channel1

    ) b 
    ON a.biz_id = b.t0_biz_id  -- 原宽表中 biz_id 可能与 a 表的 biz_id 字段名冲突，调整为 t0_biz_id 关联
LEFT JOIN (
    -- 原第一张表 c 表逻辑（授信等待节点时效标记）
    SELECT 
        biz_id as biz_id3,
        CASE WHEN approve_result='PASSED' AND date_diff('minute',create_time,update_time)<=24 * 60 
                AND date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>=24 * 60 
            THEN 1 ELSE 0 END AS if_sx_passed_within24h,
        CASE WHEN approve_result='PASSED' AND date_diff('minute',create_time,update_time)<=48 * 60 
                AND date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>=48 * 60 
            THEN 1 ELSE 0 END AS if_sx_passed_within48h,
        CASE WHEN approve_result='PASSED' AND date_diff('minute',create_time,update_time)<=120 * 60 
                AND date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>=120 * 60 
            THEN 1 ELSE 0 END AS if_sx_passed_within120h,
        CASE WHEN approve_result='PASSED' AND date_diff('minute',create_time,update_time)<=72 * 60 
                AND date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>=72 * 60 
            THEN 1 ELSE 0 END AS if_sx_passed_within72h,
        CASE WHEN approve_result='PASSED' AND date_diff('minute',create_time,update_time)<=11 * 60 
                AND date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>=11 * 60 
            THEN 1 ELSE 0 END AS if_sx_passed_within11h,
        CASE WHEN date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>=24 * 60 
            THEN 1 ELSE 0 END AS if_in_sx_over24h,
        CASE WHEN date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>=48 * 60 
            THEN 1 ELSE 0 END AS if_in_sx_over48h,
        CASE WHEN date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>=72 * 60 
            THEN 1 ELSE 0 END AS if_in_sx_over72h,
        CASE WHEN date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>=120 * 60 
            THEN 1 ELSE 0 END AS if_in_sx_over120h,
        CASE WHEN date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))>=11 * 60 
            THEN 1 ELSE 0 END AS if_in_sx_over11h,
        CASE WHEN date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))<24 * 60 
            THEN 1 ELSE 0 END AS if_in_sx_within24h,
        CASE WHEN date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))<48 * 60 
            THEN 1 ELSE 0 END AS if_in_sx_within48h,
        CASE WHEN date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))<72 * 60 
            THEN 1 ELSE 0 END AS if_in_sx_within72h,
        CASE WHEN date_diff('minute',create_time,cast(date_format(now(), '%Y-%m-%d %H:%i:%s.000') as timestamp))<120 * 60 
            THEN 1 ELSE 0 END AS if_in_sx_within120h,
        create_time as sx_time 
    FROM ods_view_presto.s05_creditx_processor_record 
    WHERE current_processor IN ('首贷授信等待节点','复贷授信等待节点')
) c 
ON a.biz_id = c.biz_id3
left join  (
  select * from
(select externalid as externalid_double,
  max(cast(json_extract_scalar(outputdata, '$.double_loan_tenant') as bigint)) as double_loan_tenant
from ods.s21_risk_strategy_record
where productid in (310,330,331)
and strategytype = 'CHAMPION'
and etl_date >= '20250101'
group by 1) mid

) e
on a.biz_id = e.externalid_double

left join (
  select biz_id as biz_idf,
    credit_amount,
    daily_max_available_limit
  from mx.tmp_wenj_product_table) f 
on a.biz_id = cast(f.biz_idf as varchar)

WHERE 
    date(a.create_time)>=date_add('day',-720,DATE(now())) 
    AND date(a.create_time)<=current_date
;