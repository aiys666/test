 

drop table if exists ind.ba_asset_base_info;
create table
if not exists ind.ba_asset_base_info as
 

WITH application_data AS (
    select
      a.*, 

        CASE
            WHEN a.product_level LIKE 'M%' THEN 'M'
            WHEN a.product_level IN (
                'A14', 'B10', 'B12', 'C8', 'A15', 'B13', 'B14', 'C9',
                'A16', 'B15', 'B16', 'C10', 'G1', 'G2', 'H1', 'H2',
                'H3', 'H4', 'I1', 'I2', 'I3', 'I4', 'I5' ,'I6'
            ) THEN 'F-NofeeNew'
            WHEN LOWER(a.product_level) LIKE '%h%' THEN 'F-NofeeNew'
            WHEN LOWER(a.product_level) LIKE '%g%' THEN 'F-NofeeNew'
            WHEN a.product_level IN ('B7', 'C7', 'A9', 'B8') THEN 'F-NofeeOld'
            WHEN a.product_level LIKE 'D%' OR a.product_level LIKE 'E%' OR a.product_level LIKE 'F%' THEN 'R-30'
            WHEN a.product_level IS NOT NULL THEN 'R-15'
            ELSE 'other'
        END AS product_level_type_1, 
    
        CASE
            WHEN a.product_level LIKE 'M%' THEN 'M'
            WHEN a.product_level IN (
                'A14', 'B10', 'B12', 'C8', 'A15', 'B13', 'B14', 'C9',
                'A16', 'B15', 'B16', 'C10', 'G1', 'G2', 'H1', 'H2',
                'H3', 'H4', 'I1', 'I2', 'I3', 'I4', 'I5','I6'
            ) THEN 'F-NofeeNew'
            WHEN LOWER(a.product_level) LIKE '%h%' THEN 'F-NofeeNew'
            WHEN LOWER(a.product_level) LIKE '%g%' THEN 'F-NofeeNew'
            WHEN a.product_level IN ('B7', 'C7', 'A9', 'B8') THEN 'F-NofeeOld'
            WHEN a.product_level IS NOT NULL THEN 'R'
            ELSE 'other'
        END AS product_level_type_old,
        CASE 
            WHEN if_recall = 1  THEN 0
            WHEN source_channel2 NOT IN ('IOS') AND app_version <= '2.1.4' THEN 1
            WHEN loan_type2 = 'loop' THEN if_app
            ELSE if_in_confirm
        END AS if_in_confirm_final,
        CASE
            WHEN if_recall = 1  THEN 0
            WHEN source_channel2 NOT IN ('IOS') AND app_version <= '2.1.4' THEN 1
            WHEN loan_type2 = 'loop' THEN 1
            ELSE if_in_confirm
        END AS if_in_confirm_temp, 
        CASE
            WHEN if_recall = 1  THEN 0
            WHEN source_channel2 NOT IN ('IOS') AND app_version <= '2.1.4' THEN 1
            WHEN confirm_date IS NOT NULL THEN 1
            WHEN loan_type2 = 'loop' THEN if_app
            ELSE if_confirm_passed
        END AS if_confirm_passed_final,
        
        CASE 
            WHEN if_recall = 1  THEN null
            WHEN a.app_version <= '2.1.4' AND source_channel2 NOT IN ('IOS') THEN DATE(a.app_date)
            WHEN a.loan_type2 = 'loop' THEN DATE(a.app_date)
            ELSE a.confirm_date
        END AS confirm_date_final,
        CASE 
            WHEN if_recall = 1  THEN null
            WHEN a.app_version <= '2.1.4' AND source_channel2 NOT IN ('IOS') THEN a.app_time
            WHEN a.loan_type2 = 'loop' THEN a.app_time
            ELSE a.confirm_time
        END AS confirm_time_final,

      CASE
            WHEN a.loan_type2 = 'loop' THEN CAST(a.circular_amount AS BIGINT)
            ELSE GREATEST(
                COALESCE(grantcredit_30d_amount, 0),
                COALESCE(grantcredit_60d_amount, 0),
                COALESCE(grantcredit_90d_amount, 0),
                COALESCE(grantcredit_120d_amount, 0),
                COALESCE(grantcredit_150d_amount, 0),
                COALESCE(grantcredit_180d_amount, 0),
                COALESCE(grantcredit_210d_amount, 0)
            )
        END AS grantcredit_amount_final,
        
        -- Applied credit amount
        CASE
            WHEN a.loan_type2 = 'loop' THEN CAST(a.circular_amount AS BIGINT)
            WHEN a.loan_type2 = 'normal' AND a.interval_start = 30 AND CAST(a.grantcredit_30d_amount AS BIGINT) > 0 THEN a.grantcredit_30d_amount
            WHEN a.loan_type2 = 'normal' AND a.interval_start = 60 AND CAST(a.grantcredit_60d_amount AS BIGINT) > 0 THEN a.grantcredit_60d_amount
            WHEN a.loan_type2 = 'normal' AND a.interval_start = 90 AND CAST(a.grantcredit_90d_amount AS BIGINT) > 0 THEN a.grantcredit_90d_amount
            WHEN a.loan_type2 = 'normal' AND a.interval_start = 120 AND CAST(a.grantcredit_120d_amount AS BIGINT) > 0 THEN a.grantcredit_120d_amount
            WHEN a.loan_type2 = 'normal' AND a.interval_start = 150 AND CAST(a.grantcredit_150d_amount AS BIGINT) > 0 THEN a.grantcredit_150d_amount
            WHEN a.loan_type2 = 'normal' AND a.interval_start = 180 AND CAST(a.grantcredit_180d_amount AS BIGINT) > 0 THEN a.grantcredit_180d_amount
            WHEN a.loan_type2 = 'normal' AND a.interval_start = 210 AND CAST(a.grantcredit_210d_amount AS BIGINT) > 0 THEN a.grantcredit_210d_amount
            ELSE GREATEST(
                COALESCE(grantcredit_30d_amount, 0),
                COALESCE(grantcredit_60d_amount, 0),
                COALESCE(grantcredit_90d_amount, 0),
                COALESCE(grantcredit_120d_amount, 0),
                COALESCE(grantcredit_150d_amount, 0),
                COALESCE(grantcredit_180d_amount, 0),
                COALESCE(grantcredit_210d_amount, 0)
            )
        END AS apply_grantcredit_amount
    FROM ind.xly_application_funnel a
    WHERE 1=1
    -- and a.if_app = 1
    AND a.create_time >= date'2021-06-01'  

  ),

revenue_name AS (
    SELECT 
    a1.camera_id, 
    sum(a1.haircut_amount) haircut_amount,
    sum(a1.interest) interest,
    sum(a1.interest+a1.haircut_amount) revenue    
    FROM ods.s02_loan a1 
    WHERE release_time>=date'2021-06-01'    
    group by 1 
),
  
account_name AS (
    SELECT 
        b.camera_id,               
        b.lend_customer_id,        
        j.account_name AS original_account_name,   
        CASE 
            WHEN j.account_name = 'PT RUMAH INOVASI JET' THEN 'JET'
            WHEN j.account_name = 'PT JAYA TEKNOLOGI PRATAMA' THEN 'JAYA'
            WHEN j.account_name = 'PT TELEKOMUNIKASI ANDALAN INDONESIA' THEN 'TELKO'
            WHEN j.account_name = 'PT Bank Neo Commerce Tbk' THEN 'BNC'
            WHEN j.account_name = 'VOYAGE ONE LIMITED' THEN 'Weshare'
            WHEN j.account_name = 'weshare2_10014' THEN 'Weshare2'
            WHEN j.account_name = 'geerong_10013' THEN 'Geerong'
            WHEN j.account_name = 'Finovary Co Ltd' THEN 'Finovary'
            WHEN j.account_name = 'bss_10011' THEN 'BSS'  
        END AS account_name   
    FROM ods_view_presto.s02_lend b 
    LEFT JOIN ods.s02_lend_account j 
        ON CAST(b.lend_customer_id AS BIGINT) = CAST(j.customer_id AS BIGINT) 
    WHERE b.create_time >= date'2021-06-01'   
),





first_loan_info AS (
    SELECT
      mid,
      biz_id as first_loan_bizid,
      issue_month,
      issue_week,
      issue_date, 
      is_reloan2,
      new_grade_level, 
      loan_cycle,
      loan_indexs,
      product_tag AS product_level_type 
    FROM ind.xly_application_funnel a
    WHERE a.if_app = 1
    AND if_issue = 1
    AND grant_strategy = 'NEW'
  ),

signature_data AS ( 
    SELECT biz_id, sign_date
    FROM (
        SELECT DISTINCT biz_id, sign_date,
          ROW_NUMBER() OVER (PARTITION BY biz_id ORDER BY sign_date DESC) rn
        FROM (
            SELECT DISTINCT biz_id, DATE(create_time) sign_date
            FROM ods.s25_contract_record c
            WHERE c.oper_type = 4
            AND c.deleted = 0
            AND DATE(create_time) < CURRENT_DATE

            UNION ALL

            SELECT DISTINCT CAST(aa.camera_id AS DECIMAL(38, 6)) AS biz_id,
                   DATE(create_time) sign_date
            FROM ods_view_presto.s02_digisign_record aa
            WHERE aa.status = 1
            AND aa.type = 7
            AND role_type = 1
            AND DATE(create_time) < CURRENT_DATE
        ) a
    ) g
    WHERE rn = 1
  ) ,

overdue_15day AS (
    SELECT customer_id, MIN(black_date) min_overdue15_black_date
    FROM (
        SELECT customer_id, 
               DATE_ADD('day', 15, DATE(should_time)) black_date,
               DATE_DIFF('day', DATE(should_time), DATE(COALESCE(fact_time, CURRENT_DATE))) AS due_day
        FROM ods.s02_loan_repayment
        WHERE DATE_DIFF('day', DATE(should_time), DATE(COALESCE(fact_time, CURRENT_DATE))) > 15
    ) a 
    GROUP BY 1
  ),

performance_data AS (
    SELECT
        id,
        overdue_amount_1_0,
        should_capital_1_0,  
        overdue_amount_1_7,
        should_capital_1_7,  
        overdue_amount_1_14,
        should_capital_1_14, 
        overdue_amount_1_30,
        should_capital_1_30, 
        should_cnt_1_0,
        overdue_cnt_1_0,
        should_cnt_1_7,
        overdue_cnt_1_7,
        should_cnt_1_14,
        overdue_cnt_1_14, 
        should_cnt_1_30,
        overdue_cnt_1_30,
        overdue_amount_2_0,
        should_capital_2_0,  
        overdue_amount_2_7,
        should_capital_2_7,  
        overdue_amount_2_14,
        should_capital_2_14, 
        overdue_amount_2_30,
        should_capital_2_30,
        should_cnt_2_0,
        overdue_cnt_2_0,
        should_cnt_2_7,
        overdue_cnt_2_7,
        should_cnt_2_14,
        overdue_cnt_2_14, 
        should_cnt_2_30,
        overdue_cnt_2_30,
        overdue_amount_3_0,
        should_capital_3_0,  
        overdue_amount_3_7,
        should_capital_3_7,  
        overdue_amount_3_14,
        should_capital_3_14, 
        overdue_amount_3_30,
        should_capital_3_30,
        should_cnt_3_0,
        overdue_cnt_3_0,
        should_cnt_3_7,
        overdue_cnt_3_7,
        should_cnt_3_14,
        overdue_cnt_3_14, 
        should_cnt_3_30,
        overdue_cnt_3_30,
        overdue_amount_4_0,
        should_capital_4_0,  
        overdue_amount_4_7,
        should_capital_4_7,  
        overdue_amount_4_14,
        should_capital_4_14, 
        overdue_amount_4_30,
        should_capital_4_30,
        should_cnt_4_0,
        overdue_cnt_4_0,
        should_cnt_4_7,
        overdue_cnt_4_7,
        should_cnt_4_14,
        overdue_cnt_4_14, 
        should_cnt_4_30,
        overdue_cnt_4_30,
        overdue_amount_10_0,
        should_capital_10_0,  
        overdue_amount_10_7,
        should_capital_10_7,  
        overdue_amount_10_14,
        should_capital_10_14, 
        overdue_amount_10_30,
        should_capital_10_30,
        should_cnt_10_0,
        overdue_cnt_10_0,
        should_cnt_10_7,
        overdue_cnt_10_7,
        should_cnt_10_14,
        overdue_cnt_10_14, 
        should_cnt_10_30,
        overdue_cnt_10_30



        

    FROM ind.whx_vintage_all4
),

 
asset_with_bad_debt AS (
    SELECT  
        a.biz_id,
        b.annual_bad_debt_ratio,
        b.annual_bad_debt_ratio*a.interval_start/365 AS act_bad_debt_ratio
    FROM ( SELECT 
            biz_id, 
            a.new_grade_level, 
             a.interval_start, 
            issue_month,
            -- case when source_channel2 = 'OTHERS' THEN 'Android' else source_channel2 end as source_channel2,
            -- interval_start,
            -- contract_amount, 
            -- CASE 
            --     WHEN grant_strategy='NEW' THEN 'NEW'
            --     ELSE is_reloan2
            -- END AS is_reloan2,
            -- CASE WHEN product_tag = 'R_15D' THEN 'R' ELSE product_tag END AS product_tag
            CASE
                WHEN a.product_level like '%M%' THEN 'M'
                WHEN a.product_level in ('A14','B10','B12','C8','A15','B13','B14','C9','A16','B15','B16','C10','G1','G2','H1','H2','H3','H4','I1','I2','I3','I4','I5','I6'
                ) then 'F'
                WHEN a.grant_strategy = 'NEW' THEN 'NEW'
                WHEN a.grant_strategy = 'OLD'
                AND a.is_reloan2 = 'OLD_PLUS' THEN 'OLD_PLUS'
                WHEN a.is_reloan2 = 'OLD_SINGLE' THEN 'OLD_SINGLE'
                WHEN a.is_reloan2 = 'OLD_PLUS_M' THEN 'M'
                ELSE 'OTHERS'
            END AS cus_category,
            CASE
                WHEN source_channel2 = 'OTHERS' THEN 'Android'
                ELSE source_channel2
            END as source_channel2_update,
            CASE
                WHEN a.product_level in ('A14','B10','B12','C8','A15','B13','B14','C9','A16','B15','B16','C10','G1','G2','H1','H2','H3','H4','I1','I2','I3','I4','I5'
                ) then 'F'
                WHEN a.product_level like '%M%' THEN 'M'
                ELSE 'regular'
            end as product_tag,
            CASE
                WHEN a.grant_strategy = 'NEW' then 'NEW'
                ELSE a.is_reloan2
            end as cus_category_new
        FROM
            application_data a
        WHERE
            if_issue = 1
    ) a
    LEFT JOIN ind.myl_bad_debt_ratio_info_extension b 
    ON a.cus_category = b.cus_category
    AND a.new_grade_level = b.new_grade_level
    AND a.source_channel2_update = b.source_channel2
    AND a.cus_category_new = b.cus_category_new
    AND a.issue_month = b.issue_month 
)

 
 

SELECT
    a.id,
    a.mid,
    a.biz_id,
    a.is_reloan2,
    a.grant_strategy,
    a.product_level_type_1, 
    a.product_level_type_old,
    a.product_tag_detail,
    a.product_tag,
    a.product_level,
    a.new_grade_level,
    a.user_level,
    a.if_recall,
    case 
    when t.media_source in('Google','Facebook','Organic','Tiktok','Kwai') then t.media_source 
    when t.media_source='ASA' then 'IOS_ASA'
    when lower(t.media_source) like '%ios%' then 'IOS_OTHER' 
    else 'other'
    end as media_source2,  
    case when lower(t.media_source) like '%ios%' THEN 'IOS' ELSE 'Android'  end as source_channel2,
    a.loan_type2,
    a.loan_indexs,
    a.reloan_num,  
    a.create_time,
    date(a.create_time) as create_date,
    date_add('day' ,- day_of_week(date(a.create_time))+1, date(a.create_time)) as create_week,
    substr(cast(date(a.create_time) as varchar),1,7) as create_month,
    o.create_time as app_time,
    a.app_date,
    a.app_week,
    a.app_month,
    a.app_version,

    a.confirm_time,
    g.sign_date as sign_date,
    a.release_time,
    a.finish_time,
    a.issue_date,
    a.issue_week,
    a.issue_month,
    a.if_app,
    a.if_issue, 
    a.if_pass, 
    a.loan_cycle,
    a.haircut_amount,
    e.interest,
    e.revenue,
    a.contract_amount,
    a.loan_cycle*a.contract_amount as loan_cycle_amount,
    a.contract_amount * 1.00000 / f.exchange_rate_to_dollar as contract_amount_usd,
    a.contract_amount * 1.00000 / f1.exchange_rate_to_dollar as contract_amount_usd1,
    ln.amount,
    ln.amount * 1.00000 / f1.exchange_rate_to_dollar as amount_usd1,
    a.should_interest,
    CASE  WHEN date_diff('day', date(a.create_time), date(confirm_date_final))=0 and if_in_confirm_temp > 0 and (a.loan_type2 = 'loop' or (a.source_channel2 NOT IN ('IOS') AND a.app_version <= '2.1.4')) THEN 1 
          when  date_diff('day', date(a.create_time), date(confirm_date_final))=0 and if_in_confirm_temp > 0 and a.biz_id is not null then 1
          else 0 END AS if_confirm_passed_num_t0, 
    CASE  
    WHEN date_diff('hour', a.create_time, confirm_time_final) <= 24 and if_in_confirm_temp > 0 
         and (a.loan_type2 = 'loop' or (a.source_channel2 NOT IN ('IOS') AND a.app_version <= '2.1.4')) 
    THEN 1 
    WHEN date_diff('hour', a.create_time, confirm_time_final) <= 24 and if_in_confirm_temp > 0 
         and a.biz_id is not null 
    THEN 1 ELSE 0 END AS if_confirm_passed_num_24h,
    CASE  WHEN date_diff('day', date(a.create_time), date(confirm_date_final))<=7 and if_in_confirm_temp > 0 and (a.loan_type2 = 'loop' or (a.source_channel2 NOT IN ('IOS') AND a.app_version <= '2.1.4')) THEN 1 
          when  date_diff('day', date(a.create_time), date(confirm_date_final))<=7 and if_in_confirm_temp > 0 and a.biz_id is not null then 1
          else 0 END AS if_confirm_passed_num_t7, 
    CASE  WHEN date_diff('day', date(a.create_time), date(confirm_date_final))<=30 and if_in_confirm_temp > 0 and (a.loan_type2 = 'loop' or (a.source_channel2 NOT IN ('IOS') AND a.app_version <= '2.1.4')) THEN 1 
          when  date_diff('day', date(a.create_time), date(confirm_date_final))<=30 and if_in_confirm_temp > 0 and a.biz_id is not null then 1
          else 0 END AS if_confirm_passed_num_t30, 
    CASE 
        WHEN a.release_time IS NOT NULL 
        AND date_diff('MINUTE',o.create_time,a.release_time)/60<=24 THEN  a.contract_amount* 1.00000 / f1.exchange_rate_to_dollar
        ELSE 0 
    END as is_released_within_24h, 
    a.interval_start AS interval_start_old,
    a.baseinfo_onloan_hit_mid as baseinfo_onloan_hit_mid,
    a.baseinfo_onloan_amount  ,
    a.baseinfo_onloan_amount*1.0000/f.exchange_rate_to_dollar as baseinfo_onloan_amount_usd,


    b.new_grade_level AS first_loan_grade_level,
    b.product_level_type AS first_loan_product_level_type,
    b.issue_month AS first_loan_issue_month,
    b.issue_date as first_loan_issue_date,
    b.issue_week as first_loan_issue_week,
    b.is_reloan2 AS first_loan_is_reloan2,
    b.loan_cycle AS first_loan_loan_cycle,
    b.loan_indexs AS first_loan_loan_indexs,
    b.first_loan_bizid,
    d.account_name,
    a.if_regular_backup,
    a.if_backup_switch,

    CASE 
        WHEN ld.lend_customer_id = 10001 THEN 'Jet'
        WHEN ld.lend_customer_id = 10002 THEN 'Jaya'
        WHEN ld.lend_customer_id = 10003 THEN 'telko'
        WHEN ld.lend_customer_id = 10010 THEN 'bnc'
        WHEN ld.lend_customer_id = 10012 THEN 'Weshare'
        WHEN ld.lend_customer_id = 10013 THEN 'Geerong'
        WHEN ld.lend_customer_id = 10014 THEN 'Weshare2' 
    END AS lender,
    
 

    if_in_confirm_temp,
    if_in_confirm_final,
    if_confirm_passed_final,
    confirm_date_final,


    if_in_anti_fraud,
    if_anti_fraud_passed,
    if_in_anti_fraud_weak,
    if_anti_fraud_weak_passed,
    if_in_external_data_1,
    if_external_data_1_passed,
    if_in_model, 
    if_model_passed,
    a.if_in_confirm,
    a.if_confirm_passed,
    if_in_ai,
    if_ai_passed,
    if_in_manual_check,
    if_in_manual_check_1,
    if_manual_check_1_passed,
    if_in_manual_check_2,
    if_manual_check_2_passed,
    if_in_external_data_pre2,
    if_external_data_pre2_passed,
    if_in_external_data_2,
    if_external_data_2_passed,
    if_in_external_data_3, 

 

CASE
    WHEN bb.recall_biz_id is not null AND cc.if_in_confirm = 1 AND cc.if_confirm_passed = 1 THEN 1
    WHEN if_recall = 0 THEN if_external_data_3_passed
     ELSE 0
END AS if_external_data_3_passed,

CASE
    WHEN bb.recall_biz_id is not null AND cc.if_in_confirm = 1 AND cc.if_confirm_passed = 1 THEN 1
    WHEN if_recall = 0 THEN if_in_external_data_4
    ELSE 0
END AS if_in_external_data_4, 

CASE
    WHEN bb.recall_biz_id is not null AND cc.if_in_confirm = 1 AND cc.if_confirm_passed = 1 THEN 1
    WHEN if_recall = 0 THEN if_external_data_4_passed
    ELSE 0
END AS if_external_data_4_passed,
 
    (YEAR(DATE(a.create_time)) - YEAR(DATE(b.issue_date))) * 12 + 
    (MONTH(DATE(a.create_time)) - MONTH(DATE(b.issue_date))) AS month_num,
    (YEAR(DATE(a.confirm_date_final)) - YEAR(DATE(b.issue_date))) * 12 + 
    (MONTH(DATE(a.confirm_date_final)) - MONTH(DATE(b.issue_date))) AS month_num_confirm,
    (YEAR(DATE(a.release_time)) - YEAR(DATE(b.issue_date))) * 12 + 
    (MONTH(DATE(a.release_time)) - MONTH(DATE(b.issue_date))) AS month_num_issue,
 
    h1.min_overdue15_black_date,
    (YEAR(DATE(h1.min_overdue15_black_date)) - YEAR(a.release_time)) * 12 + 
    (MONTH(DATE(h1.min_overdue15_black_date)) - MONTH(a.release_time)) AS overdue15_black_month_num,
    TO_CHAR(DATE(h1.min_overdue15_black_date), 'yyyy-mm') AS overdue15_black_month,

    grantcredit_amount_final * 1.00000 / f.exchange_rate_to_dollar AS grantcredit_amount,
    apply_grantcredit_amount * 1.00000 / f.exchange_rate_to_dollar AS apply_grantcredit_amount,
    a.apply_amount * 1.00000 / f.exchange_rate_to_dollar AS apply_amount,
    CASE 
        WHEN a.is_reloan2 IN ('OLD_SINGLE') AND a.if_recall = 0 AND COALESCE(a.grantcredit_amount_final, 0) > 0 
            THEN a.grantcredit_amount_final * 1.00000 / f.exchange_rate_to_dollar
        WHEN a.is_reloan2 IN ('OLD_PLUS') AND a.if_recall = 0 AND COALESCE(a.grant_amount_total, 0) > 0 
            THEN grant_amount_total * 1.00000 / f.exchange_rate_to_dollar
        WHEN a.is_reloan2 IN ('OLD_PLUS') AND a.if_recall = 0 AND COALESCE(a.grantcredit_amount_final, 0) > 0 
            THEN grantcredit_amount_final * 1.00000 / f.exchange_rate_to_dollar
        WHEN a.is_reloan2 IN ('OLD_PLUS_M') 
        --AND a.app_date < '2025-01-09' 
        AND a.if_recall = 0 
        THEN (COALESCE(a.grantcredit_amount_final, 0) + COALESCE(TRY_CAST(a.baseinfo_onloan_amount AS BIGINT), 0)) * 1.00000 / f.exchange_rate_to_dollar
        --WHEN a.is_reloan2 IN ('OLD_PLUS_M') AND a.app_date >= '2025-01-09' AND a.if_recall = 0 
        --THEN grant_amount_total * 1.00000 / f.exchange_rate_to_dollar
        WHEN a.if_recall = 1 
            THEN grantcredit_amount_final * 1.00000 / f.exchange_rate_to_dollar
        WHEN a.if_recall = 0 
            THEN grantcredit_amount_final * 1.00000 / f.exchange_rate_to_dollar
        ELSE 0
    END AS grant_amount_max,

    c.overdue_amount_1_0,
    c.should_capital_1_0,  
    c.overdue_amount_1_7,
    c.should_capital_1_7,  
    c.overdue_amount_1_14,
    c.should_capital_1_14, 
    c.overdue_amount_1_30,
    c.should_capital_1_30, 
    c.should_cnt_1_0,
    c.overdue_cnt_1_0,
    c.should_cnt_1_7,
    c.overdue_cnt_1_7,
    c.should_cnt_1_14,
    c.overdue_cnt_1_14, 
    c.should_cnt_1_30,
    c.overdue_cnt_1_30,
    c.overdue_amount_2_0,
    c.should_capital_2_0,  
    c.overdue_amount_2_7,
    c.should_capital_2_7,  
    c.overdue_amount_2_14,
    c.should_capital_2_14, 
    c.overdue_amount_2_30,
    c.should_capital_2_30,
    c.should_cnt_2_0,
    c.overdue_cnt_2_0,
    c.should_cnt_2_7,
    c.overdue_cnt_2_7,
    c.should_cnt_2_14,
    c.overdue_cnt_2_14, 
    c.should_cnt_2_30,
    c.overdue_cnt_2_30,
    c.overdue_amount_3_0,
    c.should_capital_3_0,  
    c.overdue_amount_3_7,
    c.should_capital_3_7,  
    c.overdue_amount_3_14,
    c.should_capital_3_14, 
    c.overdue_amount_3_30,
    c.should_capital_3_30,
    c.should_cnt_3_0,
    c.overdue_cnt_3_0,
    c.should_cnt_3_7,
    c.overdue_cnt_3_7,
    c.should_cnt_3_14,
    c.overdue_cnt_3_14, 
    c.should_cnt_3_30,
    c.overdue_cnt_3_30,
    c.overdue_amount_4_0,
    c.should_capital_4_0,  
    c.overdue_amount_4_7,
    c.should_capital_4_7,  
    c.overdue_amount_4_14,
    c.should_capital_4_14, 
    c.overdue_amount_4_30,
    c.should_capital_4_30,
    c.should_cnt_4_0,
    c.overdue_cnt_4_0,
    c.should_cnt_4_7,
    c.overdue_cnt_4_7,
    c.should_cnt_4_14,
    c.overdue_cnt_4_14, 
    c.should_cnt_4_30,
    c.overdue_cnt_4_30,
    c.overdue_amount_10_0,
    c.should_capital_10_0,  
    c.overdue_amount_10_7,
    c.should_capital_10_7,  
    c.overdue_amount_10_14,
    c.should_capital_10_14, 
    c.overdue_amount_10_30,
    c.should_capital_10_30,
    c.should_cnt_10_0,
    c.overdue_cnt_10_0,
    c.should_cnt_10_7,
    c.overdue_cnt_10_7,
    c.should_cnt_10_14,
    c.overdue_cnt_10_14, 
    c.should_cnt_10_30,
    c.overdue_cnt_10_30,
    a.overdue_amount_total_7,
    a.should_capital_total_7,
    a.overdue_amount_total_30,
    a.should_capital_total_30,
    a.overdue_cnt_total_7,
    a.should_cnt_total_7,
    a.overdue_cnt_total_30,
    a.should_cnt_total_30,

    w.act_bad_debt_ratio,
    w.annual_bad_debt_ratio,  
    f.exchange_rate_to_dollar as app_exchange_rate_to_dollar,
    f1.exchange_rate_to_dollar

 
FROM application_data a
LEFT JOIN first_loan_info b ON a.mid = b.mid
LEFT JOIN dim.dim_exchange_rate_cost f ON TO_CHAR(DATE(a.create_time), 'yyyymm') = f.month_id AND f.account_currency = 'IDR'
LEFT JOIN dim.dim_exchange_rate_cost f1 ON TO_CHAR(DATE(a.issue_date), 'yyyymm') = f1.month_id AND f1.account_currency = 'IDR'
LEFT JOIN signature_data g ON try_cast (a.biz_id as bigint) = try_cast (g.biz_id as bigint)
LEFT JOIN overdue_15day h1 ON CAST(b.mid AS BIGINT) = CAST(h1.customer_id AS BIGINT)
LEFT JOIN performance_data c ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(c.id AS BIGINT)
LEFT JOIN account_name d ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(d.camera_id AS BIGINT)
LEFT JOIN revenue_name e ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(e.camera_id AS BIGINT)
LEFT JOIN ods.s02_lend ld  ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(ld.camera_id AS BIGINT)
LEFT JOIN ods.s02_loan ln  ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(ln.camera_id AS BIGINT)
LEFT JOIN ods.s05_creditx_order o ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(o.biz_id AS BIGINT)
LEFT JOIN ind.tyn_reg_install_new t ON TRY_CAST(a.mid AS BIGINT) = TRY_CAST(t.mid AS BIGINT)
LEFT JOIN asset_with_bad_debt w ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(w.biz_id AS BIGINT)
left join
(SELECT biz_id,recall_biz_id from ods.s09_tiny_flow_record
where product_code = 'SWITCH_AFTERREJECTED_PROD' and output is not null) bb on a.biz_id=cast(bb.biz_id as varchar)
left join
(SELECT biz_id,if_in_confirm,if_confirm_passed from ind.xly_application_funnel where if_recall=1 ) cc on cast(bb.recall_biz_id as varchar)=cc.biz_id
;
 
