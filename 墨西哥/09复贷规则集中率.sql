select *
from mx.fd_rule_hit_pct



--:{author=tudalun, department=墨西哥风险策略, dagName=wxs_wide_table_create, taskName=fd_rule_hit_pct}
drop table if exists mx.fd_rule_hit_pct
;
--:{author=tudalun, department=墨西哥风险策略, dagName=wxs_wide_table_create, taskName=fd_rule_hit_pct}
CREATE TABLE mx.fd_rule_hit_pct AS
SELECT 
    t0.*, 
    t2.rule_name, 
    t2.cnt,
    t3.in_cnt 
FROM (
    SELECT 
		    source,
        app_version,
        case when fd_high_pass_label = 0 then '非高通过组' 
          when fd_high_pass_label = 1 then '高通过组'
          else '高通过组上线前' end as fd_high_pass_label,
        case when one_click_loan_tag = '0' then '一键放款对照组' 
          when one_click_loan_tag = '1' then '一键放款测试组'
          else '不符合条件' end as one_click_loan_tag,
        app_group, 
        app_date, 
        app_week, 
        app_month, 
        '复贷' as double_loan, 
        SUBSTR(CAST(CURRENT_TIMESTAMP AS VARCHAR), 1, 24) AS update_time, 
        CASE 
            WHEN if_in_fu_anti_fraud = 1 AND if_fu_anti_fraud_passed = 0 THEN '强反'
            WHEN if_in_fu_anti_fraud_weak = 1 AND if_fu_anti_fraud_weak_passed = 0 THEN '弱反'
            WHEN if_in_fu_model = 1 AND if_fu_model_passed = 0 THEN '模型'
            WHEN if_in_sx = 1 AND if_sx_passed = 0 THEN '授信节点'
            WHEN if_in_fu_sx_refuse = 1 AND if_fu_sx_refuse_passed = 0 THEN '授信拒绝'
            WHEN if_in_fu_post_anti_fraud_rerun = 1 AND if_fu_post_anti_fraud_rerun_passed = 0 THEN '后置强反'
            WHEN if_in_fu_post_weak_anti_fraud_rerun = 1 AND if_fu_post_weak_anti_fraud_rerun_passed = 0 THEN '后置弱反'
            WHEN if_in_fu_post_model_reject_rerun = 1 AND if_fu_post_model_reject_rerun_passed = 0 THEN '后置模型'
            WHEN if_in_fu_external_data = 1 AND if_fu_external_data_passed = 0 THEN '三方'
        END AS rule_tag, 
        COUNT(DISTINCT biz_id) AS total_cnt
    FROM mx.wxs_application_funnel 
    WHERE is_reloan = 'old' 
        AND DATE(create_time) >= DATE '2025-02-07'
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
) t0 

-- 关联规则命中明细
LEFT JOIN (
    SELECT source,        
        app_version,
        case when fd_high_pass_label = 0 then '非高通过组' 
          when fd_high_pass_label = 1 then '高通过组'
          else '高通过组上线前' end as fd_high_pass_label,
        case when one_click_loan_tag = '0' then '一键放款对照组' 
          when one_click_loan_tag = '1' then '一键放款测试组'
          else '不符合条件' end as one_click_loan_tag,
        app_group, 
        app_date, 
        app_week, 
        app_month, 
        rule_name, 
        CASE 
            WHEN if_in_fu_anti_fraud = 1 AND if_fu_anti_fraud_passed = 0 THEN '强反'
            WHEN if_in_fu_anti_fraud_weak = 1 AND if_fu_anti_fraud_weak_passed = 0 THEN '弱反'
            WHEN if_in_fu_model = 1 AND if_fu_model_passed = 0 THEN '模型'
            WHEN if_in_sx = 1 AND if_sx_passed = 0 THEN '授信节点'
            WHEN if_in_fu_sx_refuse = 1 AND if_fu_sx_refuse_passed = 0 THEN '授信拒绝'
            WHEN if_in_fu_post_anti_fraud_rerun = 1 AND if_fu_post_anti_fraud_rerun_passed = 0 THEN '后置强反'
            WHEN if_in_fu_post_weak_anti_fraud_rerun = 1 AND if_fu_post_weak_anti_fraud_rerun_passed = 0 THEN '后置弱反'
            WHEN if_in_fu_post_model_reject_rerun = 1 AND if_fu_post_model_reject_rerun_passed = 0 THEN '后置模型'
            WHEN if_in_fu_external_data = 1 AND if_fu_external_data_passed = 0 THEN '三方'
        END AS rule_tag, 
        COUNT(DISTINCT t1.biz_id) AS cnt
    FROM (
        SELECT * 
        FROM mx.wxs_application_funnel 
        WHERE is_reloan = 'old' 
            AND DATE(create_time) >= DATE '2025-02-07'
    ) t0 
    LEFT JOIN (
        SELECT 
            biz_id, 
            rule_name 
        FROM ods.s05_creditx_anti_fraud_record 
        WHERE rule_type = 'NORMAL' 
            AND real_hint = 'true' 
            AND DATE(create_time) >= DATE '2025-02-07'
    ) t1 ON t0.biz_id = t1.biz_id 
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
) t2 ON t0.rule_tag = t2.rule_tag 
    AND t0.app_group = t2.app_group 
    AND t0.app_date = t2.app_date 
    AND t0.app_week = t2.app_week 
    AND t0.app_month = t2.app_month
    AND t0.source = t2.source
    AND t0.app_version = t2.app_version
    AND t0.fd_high_pass_label = t2.fd_high_pass_label
    AND t0.one_click_loan_tag = t2.one_click_loan_tag


-- 关联进入规则节点数量
LEFT JOIN (
    -- 强反
    SELECT source, app_version,
    case when fd_high_pass_label = 0 then '非高通过组' 
          when fd_high_pass_label = 1 then '高通过组'
          else '高通过组上线前' end as fd_high_pass_label,
        case when one_click_loan_tag = '0' then '一键放款对照组' 
          when one_click_loan_tag = '1' then '一键放款测试组'
          else '不符合条件' end as one_click_loan_tag,app_group, app_date, app_week, app_month, '强反' AS rule_tag, SUM(if_in_fu_anti_fraud) AS in_cnt
    FROM mx.wxs_application_funnel 
    WHERE is_reloan = 'old' AND DATE(create_time) >= DATE '2025-02-07'
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
    
    UNION ALL
    
    -- 弱反
    SELECT source, app_version,         case when fd_high_pass_label = 0 then '非高通过组' 
          when fd_high_pass_label = 1 then '高通过组'
          else '高通过组上线前' end as fd_high_pass_label,
        case when one_click_loan_tag = '0' then '一键放款对照组' 
          when one_click_loan_tag = '1' then '一键放款测试组'
          else '不符合条件' end as one_click_loan_tag,app_group, app_date, app_week, app_month, '弱反' AS rule_tag, SUM(if_in_fu_anti_fraud_weak) AS in_cnt
    FROM mx.wxs_application_funnel 
    WHERE is_reloan = 'old' AND DATE(create_time) >= DATE '2025-02-07'
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
    
    UNION ALL
    
    -- 模型
    SELECT source, app_version,         case when fd_high_pass_label = 0 then '非高通过组' 
          when fd_high_pass_label = 1 then '高通过组'
          else '高通过组上线前' end as fd_high_pass_label,
        case when one_click_loan_tag = '0' then '一键放款对照组' 
          when one_click_loan_tag = '1' then '一键放款测试组'
          else '不符合条件' end as one_click_loan_tag,app_group, app_date, app_week, app_month, '模型' AS rule_tag, SUM(if_in_fu_model) AS in_cnt
    FROM mx.wxs_application_funnel 
    WHERE is_reloan = 'old' AND DATE(create_time) >= DATE '2025-02-07'
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
    
    UNION ALL
    
    -- 授信节点
    SELECT source, app_version,         case when fd_high_pass_label = 0 then '非高通过组' 
          when fd_high_pass_label = 1 then '高通过组'
          else '高通过组上线前' end as fd_high_pass_label,
        case when one_click_loan_tag = '0' then '一键放款对照组' 
          when one_click_loan_tag = '1' then '一键放款测试组'
          else '不符合条件' end as one_click_loan_tag,app_group, app_date, app_week, app_month, '授信节点' AS rule_tag, SUM(if_in_sx) AS in_cnt
    FROM mx.wxs_application_funnel 
    WHERE is_reloan = 'old' AND DATE(create_time) >= DATE '2025-02-07'
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
    
    UNION ALL
    
    -- 授信拒绝
    SELECT source, app_version,         case when fd_high_pass_label = 0 then '非高通过组' 
          when fd_high_pass_label = 1 then '高通过组'
          else '高通过组上线前' end as fd_high_pass_label,
        case when one_click_loan_tag = '0' then '一键放款对照组' 
          when one_click_loan_tag = '1' then '一键放款测试组'
          else '不符合条件' end as one_click_loan_tag,app_group, app_date, app_week, app_month, '授信拒绝' AS rule_tag, SUM(if_in_fu_sx_refuse) AS in_cnt
    FROM mx.wxs_application_funnel 
    WHERE is_reloan = 'old' AND DATE(create_time) >= DATE '2025-02-07'
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
    
    UNION ALL
    
    -- 三方
    SELECT source, app_version,         case when fd_high_pass_label = 0 then '非高通过组' 
          when fd_high_pass_label = 1 then '高通过组'
          else '高通过组上线前' end as fd_high_pass_label,
        case when one_click_loan_tag = '0' then '一键放款对照组' 
          when one_click_loan_tag = '1' then '一键放款测试组'
          else '不符合条件' end as one_click_loan_tag,app_group, app_date, app_week, app_month, '三方' AS rule_tag, SUM(if_in_fu_external_data) AS in_cnt
    FROM mx.wxs_application_funnel 
    WHERE is_reloan = 'old' AND DATE(create_time) >= DATE '2025-02-07'
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8

    UNION ALL
    
    -- 后置强反
    SELECT source, app_version,         case when fd_high_pass_label = 0 then '非高通过组' 
          when fd_high_pass_label = 1 then '高通过组'
          else '高通过组上线前' end as fd_high_pass_label,
        case when one_click_loan_tag = '0' then '一键放款对照组' 
          when one_click_loan_tag = '1' then '一键放款测试组'
          else '不符合条件' end as one_click_loan_tag,app_group, app_date, app_week, app_month, '后置强反' AS rule_tag, SUM(if_in_fu_post_anti_fraud_rerun) AS in_cnt
    FROM mx.wxs_application_funnel 
    WHERE is_reloan = 'old' AND DATE(create_time) >= DATE '2025-02-07'
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8

    UNION ALL
    
    -- 后置弱反
    SELECT source, app_version,         case when fd_high_pass_label = 0 then '非高通过组' 
          when fd_high_pass_label = 1 then '高通过组'
          else '高通过组上线前' end as fd_high_pass_label,
        case when one_click_loan_tag = '0' then '一键放款对照组' 
          when one_click_loan_tag = '1' then '一键放款测试组'
          else '不符合条件' end as one_click_loan_tag,app_group, app_date, app_week, app_month, '后置弱反' AS rule_tag, SUM(if_in_fu_post_weak_anti_fraud_rerun) AS in_cnt
    FROM mx.wxs_application_funnel 
    WHERE is_reloan = 'old' AND DATE(create_time) >= DATE '2025-02-07'
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8

    UNION ALL
    
    -- 后置模型
    SELECT source, app_version,         case when fd_high_pass_label = 0 then '非高通过组' 
          when fd_high_pass_label = 1 then '高通过组'
          else '高通过组上线前' end as fd_high_pass_label,
        case when one_click_loan_tag = '0' then '一键放款对照组' 
          when one_click_loan_tag = '1' then '一键放款测试组'
          else '不符合条件' end as one_click_loan_tag,app_group, app_date, app_week, app_month, '后置模型' AS rule_tag, SUM(if_in_fu_post_model_reject_rerun) AS in_cnt
    FROM mx.wxs_application_funnel 
    WHERE is_reloan = 'old' AND DATE(create_time) >= DATE '2025-02-07'
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8



) t3 ON t0.rule_tag = t3.rule_tag 
    AND t0.app_group = t3.app_group 
    AND t0.app_date = t3.app_date 
    AND t0.app_week = t3.app_week 
    AND t0.app_month = t3.app_month 
	  AND t0.source = t3.source
    AND t0.app_version = t3.app_version
    AND t0.fd_high_pass_label = t3.fd_high_pass_label
    AND t0.one_click_loan_tag = t3.one_click_loan_tag
WHERE rule_name IS NOT NULL
;