 

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
            WHEN source_channel2 NOT IN ('IOS') AND app_version <= '2.1.4' THEN 1
            WHEN loan_type2 = 'loop' THEN if_app
            ELSE if_in_confirm
        END AS if_in_confirm_final,
        CASE
            WHEN source_channel2 NOT IN ('IOS') AND app_version <= '2.1.4' THEN 1
            WHEN loan_type2 = 'loop' THEN 1
            ELSE if_in_confirm
        END AS if_in_confirm_temp, 
        CASE
            WHEN source_channel2 NOT IN ('IOS') AND app_version <= '2.1.4' THEN 1
            WHEN confirm_date IS NOT NULL THEN 1
            WHEN loan_type2 = 'loop' THEN if_app
            ELSE if_confirm_passed
        END AS if_confirm_passed_final,
        
        CASE
            WHEN a.app_version <= '2.1.4' AND source_channel2 NOT IN ('IOS') THEN DATE(a.app_date)
            WHEN a.loan_type2 = 'loop' THEN DATE(a.app_date)
            ELSE a.confirm_date
        END AS confirm_date_final,

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
      CASE
          WHEN product_level LIKE 'M%' THEN 'M'
          WHEN product_level IN (
              'A14', 'B10', 'B12', 'C8', 'A15', 'B13', 'B14', 'C9',
              'A16', 'B15', 'B16', 'C10', 'G1', 'G2', 'H1', 'H2',
              'H3', 'H4', 'I1', 'I2', 'I3', 'I4', 'I5','I6'
          ) THEN 'F-NofeeNew'
          WHEN LOWER(product_level) LIKE '%h%' THEN 'F-NofeeNew'
          WHEN LOWER(product_level) LIKE '%g%' THEN 'F-NofeeNew'
          WHEN product_level IN ('B7', 'C7', 'A9', 'B8') THEN 'F-NofeeOld'
          WHEN product_level IS NOT NULL THEN 'R'
          ELSE 'other'
      END AS product_level_type
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
        overdue_cnt_4_30
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
                WHEN a.product_level in ('A14','B10','B12','C8','A15','B13','B14','C9','A16','B15','B16','C10','G1','G2','H1','H2','H3','H4','I1','I2','I3','I4','I5'
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
    a.new_grade_level,
    a.user_level,
    a.if_recall,
    case 
    when t.media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then t.media_source 
    when t.media_source='ASA' or lower(t.media_source) like '%ios%' then 'IOS' 
    else 'other'
    end as media_source2,  
    case when source_channel2 = 'OTHERS' THEN 'Android' else source_channel2 end as source_channel2,
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
    a.confirm_time,
    g.sign_date as sign_date,
    a.release_time,
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
    a.should_interest,
    case when date_diff('day',date(a.app_date),date(a.confirm_date_final))=0 then 1 else 0 end as if_confirm_passed_num_t0,
    case when date_diff('day',date(a.app_date),date(a.confirm_date_final)) BETWEEN 0 and 7 then 1 else 0 end as if_confirm_passed_num_t7,
    CASE 
        WHEN a.release_time IS NOT NULL 
        AND date_diff('MINUTE',o.create_time,a.release_time)/60<=24 THEN  contract_amount* 1.00000 / f1.exchange_rate_to_dollar
        ELSE 0 
    END as is_released_within_24h, 
    a.interval_start AS interval_start_old,
    a.baseinfo_onloan_hit_mid as baseinfo_onloan_hit_mid,


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

    CASE 
        WHEN ld.lend_customer_id = 10001 THEN 'Jet'
        WHEN ld.lend_customer_id = 10002 THEN 'Jaya'
        WHEN ld.lend_customer_id = 10003 THEN 'telko'
        WHEN ld.lend_customer_id = 10010 THEN 'bnc'
        WHEN ld.lend_customer_id = 10012 THEN 'Weshare'
        WHEN ld.lend_customer_id = 10013 THEN 'Geerong'
        WHEN ld.lend_customer_id = 10014 THEN 'Weshare2' 
    END AS lender,
    
 
    CASE
        WHEN if_recall = 0 THEN if_model_passed
        WHEN if_recall = 1 AND if_in_confirm_final = 1 THEN 1
        ELSE 0
    END AS if_model_passed,
    if_in_confirm_temp,
    if_in_confirm_final,
    if_confirm_passed_final,
    confirm_date_final,

    CASE
        WHEN a.loan_type2 = 'loop' THEN if_app
        WHEN if_recall = 0 THEN if_external_data_3_passed
        WHEN grant_strategy = 'NEW' AND if_recall = 1 AND if_in_confirm_final = 1 AND if_confirm_passed_final = 1 THEN 1
        WHEN grant_strategy = 'OLD' AND if_recall = 1 AND if_in_confirm_final = 1 THEN 1
        ELSE 0
    END AS if_external_data_3_passed,

    CASE
        WHEN if_recall = 0 THEN if_in_external_data_4
        WHEN if_recall = 1 AND if_in_confirm_final = 1 AND if_confirm_passed_final = 1 THEN 1
        ELSE 0
    END AS if_in_external_data_4, 

    CASE
        WHEN if_recall = 0 THEN if_external_data_4_passed
        WHEN if_recall = 1 AND if_in_confirm_final = 1 AND if_confirm_passed_final = 1 THEN 1
        ELSE 0
    END AS if_external_data_4_passed,
 
    (YEAR(DATE(a.create_time)) - YEAR(DATE(b.issue_date))) * 12 + 
    (MONTH(DATE(a.create_time)) - MONTH(DATE(b.issue_date))) AS month_num,
    (YEAR(DATE(a.confirm_time)) - YEAR(DATE(b.issue_date))) * 12 + 
    (MONTH(DATE(a.confirm_time)) - MONTH(DATE(b.issue_date))) AS month_num_confirm,
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
    w.act_bad_debt_ratio,
    w.annual_bad_debt_ratio
 
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
LEFT JOIN ods.s05_creditx_order o ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(o.biz_id AS BIGINT)
LEFT JOIN ind.tyn_reg_install_new t ON TRY_CAST(a.mid AS BIGINT) = TRY_CAST(t.mid AS BIGINT)
LEFT JOIN asset_with_bad_debt w ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(w.biz_id AS BIGINT)
;
 

 
-- SELECT * FROM  ind.ba_apply_should_result LIMIT 100000

-- SELECT * FROM  ind.ba_apply_should_result LIMIT 100000
drop table if exists ind.ba_apply_should_result;
create table
if not exists ind.ba_apply_should_result as

WITH application_metrics AS ( 
    SELECT
        app_week,
        app_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
        media_source2,
        source_channel2,
        sum(if_app) AS if_app,
        sum(if_in_confirm_final) AS in_confirm_cnt,
        sum(case when new_grade_level IN ('1','2') then if_in_confirm_final else 0 end) AS in_confirm_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_in_confirm_final else 0 end) AS in_confirm_cnt_1_4,
        sum(case when user_level IN (1,2) then if_in_confirm_final else 0 end) AS rl_in_confirm_cnt_1_2,
        sum(case when user_level IN (1,2,3) then if_in_confirm_final else 0 end) AS rl_in_confirm_cnt_1_3,
        sum(if_confirm_passed_final) AS confirm_passed_cnt,
        sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
        sum(if_confirm_passed_num_t7) AS if_confirm_passed_num_t7,
        SUM(case when if_in_confirm_final = 1 then grant_amount_max else NULL end) AS in_confirm_grantcredit_amount_total,
        SUM(case when if_in_confirm_final = 1 then grantcredit_amount else NULL end) AS in_confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_grantcredit_amount else NULL end) AS confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_amount else NULL end) AS confirm_apply_amount,
        sum(if_pass) AS pass_cnt,
        count(distinct case when sign_date is not null then biz_id end) AS sign_cnt,
        sum(if_issue) AS issue_cnt_from_app,
        sum(is_released_within_24h) AS is_released_within_24h
    FROM ind.ba_asset_base_info
    WHERE date(app_date) >= DATE('2025-01-01')  
    AND date(app_date) < CURRENT_DATE
    AND if_app = 1
    GROUP BY 1,2,3,4,5,6,7,8,9


),
issue_metrics AS ( 
    SELECT
        issue_week,
        issue_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
        media_source2,
        source_channel2,
        sum(if_issue) AS issue_cnt_from_issue,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(case when user_level IN (1,2) then if_issue else 0 end) AS rl_issue_cnt_1_2,
        sum(case when user_level IN (1,2,3) then if_issue else 0 end) AS rl_issue_cnt_1_3,

        sum(haircut_amount) as issue_haircut_amount,
        sum(interest) as issue_interest,
        sum(revenue) as issue_revenue,
        sum(contract_amount) AS issue_contract_amount,
        sum(contract_amount_usd1) AS issue_contract_amount_usd,
     
        sum(case when grant_strategy = 'NEW' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_new,
        sum(case when grant_strategy = 'OLD' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_old,
        sum(overdue_amount_1_0) AS overdue_amount_1_0,
        sum(should_capital_1_0) AS should_capital_1_0,
        sum(overdue_amount_1_7) AS overdue_amount_1_7,
        sum(should_capital_1_7) AS should_capital_1_7,
        sum(overdue_amount_1_14) AS overdue_amount_1_14,
        sum(should_capital_1_14) AS should_capital_1_14,
        sum(overdue_amount_1_30) AS overdue_amount_1_30,
        sum(should_capital_1_30) AS should_capital_1_30,
        sum(overdue_amount_2_0) AS overdue_amount_2_0,
        sum(should_capital_2_0) AS should_capital_2_0,
        sum(overdue_amount_2_7) AS overdue_amount_2_7,
        sum(should_capital_2_7) AS should_capital_2_7,
        sum(overdue_amount_2_14) AS overdue_amount_2_14,
        sum(should_capital_2_14) AS should_capital_2_14,
        sum(overdue_amount_2_30) AS overdue_amount_2_30,
        sum(should_capital_2_30) AS should_capital_2_30,

        sum(loan_cycle_amount) AS loan_cycle_amount,
        sum(act_bad_debt_ratio*contract_amount) AS act_bad_debt_amt


    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    AND date(issue_date) >= DATE('2025-01-01') 
    AND date(issue_date) < CURRENT_DATE 
    GROUP BY 1,2,3,4,5,6,7,8,9

),



should_metrics AS (


    SELECT
    to_char(date_trunc('month',a.should_date),'yyyy-mm-dd') as should_month,
	to_char(date_trunc('week', a.should_date),'yyyy-mm-dd') as should_week,
    c.grant_strategy,
    c.product_tag,
    c.is_reloan2,
    c.new_grade_level,
    c.user_level,
    c.media_source2,
    c.source_channel2, 

    SUM(a.should_capital) AS should_capital, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.should_capital ELSE null END) AS should_capital_d0, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.should_capital ELSE null END) AS should_capital_d1,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.should_capital ELSE null END) AS should_capital_d7,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.should_capital ELSE null END) AS should_capital_d15,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.should_capital ELSE null END) AS should_capital_d30,
 
 
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d0, 
    SUM(CASE WHEN due_day <= 1  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.fact_capital ELSE 0 END) AS t1_capital_paid_d1,
    SUM(CASE WHEN due_day <= 7  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.fact_capital ELSE 0 END) AS t7_capital_paid_d7,
    SUM(CASE WHEN due_day <= 15 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t15_capital_paid_d15,
    SUM(CASE WHEN due_day <= 30 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t30_capital_paid_d30,

    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8  THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d7,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d15,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d30


 
FROM (
    SELECT  
        customer_id,
        camera_id AS biz_id, 
        should_date, 
        due_day, 
        SUM(should_amount) AS should_amount,
        SUM(should_capital) AS should_capital,
        SUM(should_interest) AS should_interest,
        SUM(should_fine) AS should_fine,
        SUM(fact_amount) AS fact_amount,
        SUM(fact_capital) AS fact_capital,
        SUM(fact_interest) AS fact_interest,
        SUM(fact_fine) AS fact_fine
    FROM ind.gqy_case_info_f
    WHERE is_due = 0
        AND should_date >= DATE('2025-01-01') 
        AND should_date < CURRENT_DATE
    GROUP BY 
        1,2,3,4

) a 
LEFT JOIN (
    SELECT 
        data_date,
        customer_id,
        MAX(max_due_day) AS cus_ovd_day
    FROM ind.gqy_daliy_case
    GROUP BY 1,2
    HAVING MAX(max_due_day) >= 1
) b ON a.customer_id = b.customer_id AND should_date = b.data_date
left join ind.ba_asset_base_info c 
on  TRY_CAST (a.biz_id AS BIGINT) = TRY_CAST (c.biz_id AS BIGINT)
WHERE b.customer_id IS NULL 
GROUP BY 1,2,3,4,5,6,7,8,9

),
data_date as (
    select distinct 
    date_mon,
    date_format(DATE_PARSE(data_date, '%Y%m%d'), '%Y-%m-01') AS data_month, 
    month_days,  
    day(DATE_ADD('day', -1, CURRENT_DATE)) as current_date_day,
    case when DATE_PARSE(month_end, '%Y%m%d')<DATE_TRUNC('month', CURRENT_DATE) 
    then day(DATE_PARSE(month_end, '%Y%m%d'))
    else day(DATE_ADD('day', -1, CURRENT_DATE))
    end as date_month_end_actual 
    from dim.dim_data_info
)

 


        SELECT 
    COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy) AS grant_strategy,
    COALESCE(a.product_tag, i.product_tag, s.product_tag) AS product_tag,
    COALESCE(a.is_reloan2, i.is_reloan2, s.is_reloan2) AS is_reloan2,
    COALESCE(a.new_grade_level, i.new_grade_level, s.new_grade_level) AS new_grade_level,
    COALESCE(a.user_level, i.user_level, s.user_level) AS user_level,
    COALESCE(a.media_source2, i.media_source2, s.media_source2) AS media_source,
    COALESCE(a.source_channel2, i.source_channel2, s.source_channel2) AS source_channel2,
    COALESCE(a.app_week, i.issue_week, s.should_week) AS app_week,
    COALESCE(a.app_month, i.issue_month, s.should_month) AS app_month,  
    COALESCE(a.if_app, 0) AS if_app,
    COALESCE(a.in_confirm_cnt, 0) AS in_confirm_cnt,
    COALESCE(a.in_confirm_cnt_1_2, 0) AS in_confirm_cnt_1_2,
    COALESCE(a.in_confirm_cnt_1_4, 0) AS in_confirm_cnt_1_4,
    COALESCE(a.rl_in_confirm_cnt_1_2, 0) AS rl_in_confirm_cnt_1_2,
    COALESCE(a.rl_in_confirm_cnt_1_3, 0) AS rl_in_confirm_cnt_1_3,

    COALESCE(a.confirm_passed_cnt, 0) AS confirm_passed_cnt,
    COALESCE(a.if_confirm_passed_num_t0, 0) AS if_confirm_passed_num_t0,
    COALESCE(a.if_confirm_passed_num_t7, 0) AS if_confirm_passed_num_t7,

    COALESCE(a.in_confirm_grantcredit_amount_total, 0) AS in_confirm_grantcredit_amount_total,
    COALESCE(a.in_confirm_grantcredit_amount, 0) AS in_confirm_grantcredit_amount,
    COALESCE(a.confirm_grantcredit_amount, 0) AS confirm_grantcredit_amount,
    COALESCE(a.confirm_apply_amount, 0) AS confirm_apply_amount,
    COALESCE(a.pass_cnt, 0) AS pass_cnt,
    COALESCE(a.sign_cnt, 0) AS sign_cnt,
    COALESCE(a.issue_cnt_from_app, 0) AS issue_cnt_from_app,
    COALESCE(a.is_released_within_24h, 0) AS is_released_within_24h, 
    COALESCE(i.issue_cnt_from_issue, 0) AS issue_cnt_from_issue,
    COALESCE(i.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(i.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(i.rl_issue_cnt_1_2, 0) AS rl_issue_cnt_1_2,
    COALESCE(i.rl_issue_cnt_1_3, 0) AS rl_issue_cnt_1_3,
    COALESCE(i.issue_contract_amount, 0) AS issue_contract_amount,
    COALESCE(i.issue_contract_amount_usd, 0) AS issue_contract_amount_usd,
    SUM(COALESCE(i.issue_contract_amount_usd, 0)) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='NEW'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_new_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='OLD'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_old_group,
    
    COALESCE(i.overdue_amount_1_0, 0) AS overdue_amount_1_0,
    COALESCE(i.should_capital_1_0, 0) AS should_capital_1_0,
    COALESCE(i.overdue_amount_1_7, 0) AS overdue_amount_1_7,
    COALESCE(i.should_capital_1_7, 0) AS should_capital_1_7,
    COALESCE(i.overdue_amount_1_14, 0) AS overdue_amount_1_14,
    COALESCE(i.should_capital_1_14, 0) AS should_capital_1_14,
    COALESCE(i.overdue_amount_1_30, 0) AS overdue_amount_1_30,
    COALESCE(i.should_capital_1_30, 0) AS should_capital_1_30, 
    COALESCE(i.overdue_amount_2_0, 0) AS overdue_amount_2_0,
    COALESCE(i.should_capital_2_0, 0) AS should_capital_2_0,
    COALESCE(i.overdue_amount_2_7, 0) AS overdue_amount_2_7,
    COALESCE(i.should_capital_2_7, 0) AS should_capital_2_7,
    COALESCE(i.overdue_amount_2_14, 0) AS overdue_amount_2_14,
    COALESCE(i.should_capital_2_14, 0) AS should_capital_2_14,
    COALESCE(i.overdue_amount_2_30, 0) AS overdue_amount_2_30,
    COALESCE(i.should_capital_2_30, 0) AS should_capital_2_30, 
    COALESCE(s.should_capital_d0, 0) AS should_capital_d0, 
    COALESCE(s.should_capital_d1, 0) AS should_capital_d1,
    COALESCE(s.should_capital_d7, 0) AS should_capital_d7,
    COALESCE(s.should_capital_d15, 0) AS should_capital_d15,
    COALESCE(s.should_capital_d30, 0) AS should_capital_d30, 
    COALESCE(s.should_capital_d0 - s.t0_capital_paid_d0, 0) AS t0_capital_due_d0,
    COALESCE(s.should_capital_d1 - s.t1_capital_paid_d1, 0) AS t1_capital_due_d1,
    COALESCE(s.should_capital_d7 - s.t7_capital_paid_d7, 0) AS t7_capital_due_d7,
    COALESCE(s.should_capital_d15 - s.t15_capital_paid_d15, 0) AS t15_capital_due_d15,
    COALESCE(s.should_capital_d30 - s.t30_capital_paid_d30, 0) AS t30_capital_due_d30,
    COALESCE(s.t0_capital_paid_d7, 0) AS t0_capital_paid_d7,
    COALESCE(s.t0_capital_paid_d15, 0) AS t0_capital_paid_d15,
    COALESCE(s.t0_capital_paid_d30, 0) AS t0_capital_paid_d30,
    COALESCE(s.t7_capital_paid_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_d7,
    COALESCE(s.t15_capital_paid_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_d15,
    COALESCE(s.t30_capital_paid_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_d30,

    COALESCE(s.should_capital_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_due_d7,
    COALESCE(s.should_capital_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_due_d15,
    COALESCE(s.should_capital_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_due_d30,
    COALESCE(loan_cycle_amount, 0) AS loan_cycle_amount,
    COALESCE(issue_haircut_amount, 0) AS issue_haircut_amount,
    COALESCE(issue_interest, 0) AS issue_interest,
    COALESCE(issue_revenue, 0) AS issue_revenue,
    COALESCE(act_bad_debt_amt, 0) AS act_bad_debt_amt,
    kpi_total_amt*kpi_exchange_rate* 1.00000 / f1.exchange_rate_to_dollar  AS ov_total_amt_usd,
    kpi_fl_contract_amt*kpi_exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS fl_total_amt_usd,
    kpi_rl_contract_amt*kpi_exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS rl_total_amt_usd,
    month_days, 
    date_month_end_actual ,
    COALESCE(issue_contract_amount_usd_new, 0) AS issue_contract_amount_usd_new,
    COALESCE(issue_contract_amount_usd_old, 0) AS issue_contract_amount_usd_old
    

FROM application_metrics a
FULL JOIN issue_metrics i 
    ON a.grant_strategy = i.grant_strategy
    AND a.product_tag = i.product_tag
    AND a.is_reloan2 = i.is_reloan2
    AND a.new_grade_level = i.new_grade_level
    AND a.media_source2 = i.media_source2
    AND a.source_channel2 = i.source_channel2
    AND a.app_week = i.issue_week
    AND a.app_month = i.issue_month
    AND a.user_level = i.user_level

FULL JOIN should_metrics s
    ON COALESCE(a.grant_strategy, i.grant_strategy) = s.grant_strategy
    AND COALESCE(a.product_tag, i.product_tag) = s.product_tag
    AND COALESCE(a.is_reloan2, i.is_reloan2) = s.is_reloan2
    AND COALESCE(a.new_grade_level, i.new_grade_level) = s.new_grade_level
    AND COALESCE(a.media_source2, i.media_source2) = s.media_source2
    AND COALESCE(a.source_channel2, i.source_channel2) = s.source_channel2
    AND COALESCE(a.app_week, i.issue_week) = s.should_week
    AND COALESCE(a.app_month, i.issue_month) = s.should_month
    AND COALESCE(a.user_level, i.user_level) = s.user_level
LEFT JOIN ind.ba_kpi_targets_m b
    ON COALESCE(a.app_month, i.issue_month, s.should_month) = b.kpi_month 
left join data_date c
    ON b.kpi_month = c.data_month 
LEFT JOIN dim.dim_exchange_rate_cost f1 ON c.date_mon = f1.month_id AND f1.account_currency = 'IDR'
;

 

    --  select  ad_date,
    -- to_char(date_trunc('month',ad_date),'yyyy-mm-dd') as ad_date_month,
    --     to_char(date_trunc('week',ad_date),'yyyy-mm-dd') as ad_date_week,
    -- case 
    -- when media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source 
    -- else 'other'
    -- end as media_source,
    -- case when media_source ='IOS' then 'IOS' 
    -- else 'Android'
    -- end as source_channel,
    -- SUM(install_cnt) AS install_cnt 
    --  FROM ind.tyn_runnning_report_bymedia_acquisitontype_del_plus
    --  WHERE ad_date>=DATE'2025-01-01'
    --  group BY 1,2,3,4,5
    --  ORDER BY 1,2,3,4,5
    

drop table if exists ind.ba_install_apply_result;
create table
if not exists ind.ba_install_apply_result as

with spend AS (
    select 
        date(ad_date) as ad_date
        ,case when lower(campaign_name) like  '%ios%' or media_source='ASA' or lower(media_source) like '%ios%' then 'IOS'
                when media_source like '%oogle%' and lower(campaign_name) not like '%ios%' then 'Google'
                when media_source like '%acebook%' and lower(campaign_name) not like '%ios%' then 'Facebook'
                when media_source='organic' then 'Organic'  
                when media_source='Tiktok' then 'Tiktok'
                when media_source='Kwai' then 'Kwai'
                else 'other'
            end as media_source
        ,sum(spend_usd_discount) as spend
        from ind.tyn_ads_cost_discount a
        where ad_date >= date'2025-01-01'
        group by 1,2  
    union all
    select
        distinct
        ad_date,
        'Organic' as media_source,
        0 as spend
        from ind.tyn_ads_cost_discount  
        where ad_date >= date'2025-01-01'
    ),
install_cnt as (
    SELECT install_date,   
    case when media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source else 'other' end as media_source,

    sum(install_cnt) as install_cnt 
    FROM (
    SELECT 
    DATE(event_time + INTERVAL '7' HOUR) AS install_date,
    case 	   		
			when platform = 'ios'  then 'IOS'	
			when media_source='googleadwords_int' then 'Google'
             when media_source='Facebook Ads' or media_source='restricted' then 'Facebook'
             when media_source='organic' then 'Organic'
             when media_source = 'shareit_int' then 'Shareit'
             when  media_source = 'kreditlist_int' or (media_source = 'vfine_int' and partner like '%redi%'  ) 
             or 
             (media_source is null and partner = 'kreditlist')
             then 'kreditlist_int'
			 when media_source = 'vfine_int' or media_source = 'adecentptuo_int' then 'Vfine'
             when media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when media_source = 'kwaiforbusiness_int' then 'Kwai'
             when media_source = 'cashcashpro' then 'cashcashpro'
			 when media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when media_source = 'kredit pintal' then 'kp'
			 when media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(campaign, '^pp') then 'Novabeyond'
			 when media_source = 'pyxis_int' then 'pyxis'
			 when media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when media_source = 'Twitter' then 'twitter'
			 when media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' or partner ='appscuckoobd650' then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(partner) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when campaign like '%CookeAds_CPI%' then 'CookeAds_CPI'
			when campaign ='CookeAds_CPS' or lower(campaign) like '%cookeads%' then 'CookeAds_CPS'
			when partner = '19mobicn' then '19mobi'
			when campaign = 'Samire_Jan2025youmi' then 'youmi'
			when media_source ='yupaamj_int' then 'yup'
			--when regexp_like(campaign, '^pp') then 'Novabeyond'
			when media_source = 'mintegral_int' then 'mintegral_int'
			when lower(media_source) like '%grab%' then 'Grab'
			when media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(campaign) like '%runto%' then 'RUNTOA'
			when lower(campaign) like '%mejoy%'  then 'mejoy'
			when lower(campaign) like '%yolo%'  then 'yolo'
			when media_source ='LinkAja_ads' then 'LinkAja_ads'
			when media_source ='easycash01' then 'easycash01'
			when media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when media_source ='tangads' then 'tangads'
			when media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when media_source ='oppoglobal_int' then 'oppoglobal_int'
            when media_source like '%_int%' then 'other'
			 else 'Organic'
        end as media_source,
    COUNT(DISTINCT appsflyer_id) AS install_cnt
    FROM ods.s08_appsflyer_push_data
    WHERE  etl_date>='20250101' and event_name='install' 
    and date(event_time + INTERVAL '7' HOUR) >= date'2025-01-01'
    GROUP BY 1,2 
    )t
    GROUP BY 1,2 
     ),

 
reg_cnt as (
    select 
    reg_dt,
    case 
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source 
    when media_source='ASA' or lower(media_source) like '%ios%' then 'IOS' 
    else 'other'
    end as media_source, 
    count(distinct mid) reg_cnt
    from ind.tyn_reg_install_new
    where reg_dt >= date'2025-01-01'
    group by 1,2 
     ),
apply_cnt AS ( 
    SELECT
        date(app_date) as app_date,  
        media_source2, 
        sum(if_app) AS if_app  
    FROM ind.ba_asset_base_info 
    WHERE grant_strategy='NEW' 
    and if_app=1
    and date(app_date) >= date'2025-01-01'
    GROUP BY 1,2 

),
issue_cnt AS ( 

    SELECT
        date(issue_date) as issue_date, 
        media_source2, 
        sum(if_issue) AS issue_cnt,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(contract_amount_usd) as contract_amount_usd
    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    and grant_strategy='NEW' 
    and date(issue_date) >= date'2025-01-01'
    GROUP BY 1,2
)
 
SELECT
    COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date) AS ad_date,
    to_char(date_trunc('month', COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date)), 'yyyy-mm-dd') AS ad_date_month,
    to_char(date_trunc('week', COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date)), 'yyyy-mm-dd') AS ad_date_week,
    COALESCE(a.media_source, b.media_source, c.media_source, d.media_source2, e.media_source2) AS media_source,
    COALESCE(a.spend, 0) AS spend,
    COALESCE(b.install_cnt, 0) AS install_cnt,
    COALESCE(c.reg_cnt, 0) AS reg_cnt,
    COALESCE(d.if_app, 0) AS if_app,
    COALESCE(e.issue_cnt, 0) AS issue_cnt,
    COALESCE(e.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(e.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(e.contract_amount_usd, 0) AS contract_amount_usd

FROM spend a
FULL OUTER JOIN install_cnt b ON a.ad_date = b.install_date AND a.media_source = b.media_source
FULL OUTER JOIN reg_cnt c ON a.ad_date = c.reg_dt AND a.media_source = c.media_source
FULL OUTER JOIN apply_cnt d ON a.ad_date = d.app_date AND a.media_source = d.media_source2
FULL OUTER JOIN issue_cnt e ON a.ad_date = e.issue_date AND a.media_source = e.media_source2;


  


  





  ---------------2025-11-03备份（更改拒绝转产的口径、通过率的口径）
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
            WHEN source_channel2 NOT IN ('IOS') AND app_version <= '2.1.4' THEN 1
            WHEN loan_type2 = 'loop' THEN if_app
            ELSE if_in_confirm
        END AS if_in_confirm_final,
        CASE
            WHEN source_channel2 NOT IN ('IOS') AND app_version <= '2.1.4' THEN 1
            WHEN loan_type2 = 'loop' THEN 1
            ELSE if_in_confirm
        END AS if_in_confirm_temp, 
        CASE
            WHEN source_channel2 NOT IN ('IOS') AND app_version <= '2.1.4' THEN 1
            WHEN confirm_date IS NOT NULL THEN 1
            WHEN loan_type2 = 'loop' THEN if_app
            ELSE if_confirm_passed
        END AS if_confirm_passed_final,
        
        CASE
            WHEN a.app_version <= '2.1.4' AND source_channel2 NOT IN ('IOS') THEN DATE(a.app_date)
            WHEN a.loan_type2 = 'loop' THEN DATE(a.app_date)
            ELSE a.confirm_date
        END AS confirm_date_final,

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
      CASE
          WHEN product_level LIKE 'M%' THEN 'M'
          WHEN product_level IN (
              'A14', 'B10', 'B12', 'C8', 'A15', 'B13', 'B14', 'C9',
              'A16', 'B15', 'B16', 'C10', 'G1', 'G2', 'H1', 'H2',
              'H3', 'H4', 'I1', 'I2', 'I3', 'I4', 'I5','I6'
          ) THEN 'F-NofeeNew'
          WHEN LOWER(product_level) LIKE '%h%' THEN 'F-NofeeNew'
          WHEN LOWER(product_level) LIKE '%g%' THEN 'F-NofeeNew'
          WHEN product_level IN ('B7', 'C7', 'A9', 'B8') THEN 'F-NofeeOld'
          WHEN product_level IS NOT NULL THEN 'R'
          ELSE 'other'
      END AS product_level_type
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
        overdue_cnt_4_30
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
    when t.media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then t.media_source 
    when t.media_source='ASA' or lower(t.media_source) like '%ios%' then 'IOS' 
    else 'other'
    end as media_source2,  
    case when source_channel2 = 'OTHERS' THEN 'Android' else source_channel2 end as source_channel2,
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
    a.should_interest,
    CASE  WHEN date_diff('day', date(a.create_time), date(confirm_date_final))=0 and if_in_confirm_temp > 0 and (a.loan_type2 = 'loop' or (a.source_channel2 NOT IN ('IOS') AND a.app_version <= '2.1.4')) THEN 1 
          when  date_diff('day', date(a.create_time), date(confirm_date_final))=0 and if_in_confirm_temp > 0 and a.biz_id is not null then 1
          else 0 END AS if_confirm_passed_num_t0, 
    CASE  WHEN date_diff('day', date(a.create_time), date(confirm_date_final))<=7 and if_in_confirm_temp > 0 and (a.loan_type2 = 'loop' or (a.source_channel2 NOT IN ('IOS') AND a.app_version <= '2.1.4')) THEN 1 
          when  date_diff('day', date(a.create_time), date(confirm_date_final))<=7 and if_in_confirm_temp > 0 and a.biz_id is not null then 1
          else 0 END AS if_confirm_passed_num_t7, 
    CASE 
        WHEN a.release_time IS NOT NULL 
        AND date_diff('MINUTE',o.create_time,a.release_time)/60<=24 THEN  contract_amount* 1.00000 / f1.exchange_rate_to_dollar
        ELSE 0 
    END as is_released_within_24h, 
    a.interval_start AS interval_start_old,
    a.baseinfo_onloan_hit_mid as baseinfo_onloan_hit_mid,


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
    -- CASE
    --     WHEN if_recall = 0 THEN if_model_passed
    --     WHEN if_recall = 1 AND if_in_confirm_final = 1 THEN 1
    --     ELSE 0
    -- END AS if_model_passed,
    if_model_passed,
    if_in_confirm,
    if_confirm_passed,
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
        WHEN if_recall = 0 THEN if_external_data_3_passed
        WHEN if_recall = 1 AND if_in_confirm_final = 1 AND if_confirm_passed_final = 1 THEN 1
        --WHEN grant_strategy = 'OLD' AND if_recall = 1 AND if_in_confirm_final = 1 THEN 1
        ELSE 0
    END AS if_external_data_3_passed,

    CASE
        WHEN if_recall = 0 THEN if_in_external_data_4
        WHEN if_recall = 1 AND if_in_confirm_final = 1 AND if_confirm_passed_final = 1 THEN 1
        ELSE 0
    END AS if_in_external_data_4, 

    CASE
        WHEN if_recall = 0 THEN if_external_data_4_passed
        WHEN if_recall = 1 AND if_in_confirm_final = 1 AND if_confirm_passed_final = 1 THEN 1
        ELSE 0
    END AS if_external_data_4_passed,
 
    (YEAR(DATE(a.create_time)) - YEAR(DATE(b.issue_date))) * 12 + 
    (MONTH(DATE(a.create_time)) - MONTH(DATE(b.issue_date))) AS month_num,
    (YEAR(DATE(a.confirm_time)) - YEAR(DATE(b.issue_date))) * 12 + 
    (MONTH(DATE(a.confirm_time)) - MONTH(DATE(b.issue_date))) AS month_num_confirm,
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
    w.act_bad_debt_ratio,
    w.annual_bad_debt_ratio
 
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
LEFT JOIN ods.s05_creditx_order o ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(o.biz_id AS BIGINT)
LEFT JOIN ind.tyn_reg_install_new t ON TRY_CAST(a.mid AS BIGINT) = TRY_CAST(t.mid AS BIGINT)
LEFT JOIN asset_with_bad_debt w ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(w.biz_id AS BIGINT)
;


-- 2025-11-03 同期调整

drop table if exists ind.ba_apply_should_result;
create table
if not exists ind.ba_apply_should_result as

WITH application_metrics AS ( 
    SELECT
        date(app_date) AS app_date,
        app_week,
        app_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
        media_source2,
        source_channel2,
        sum(if_app) AS if_app,
        sum(if_in_confirm_final) AS in_confirm_cnt,
        sum(case when new_grade_level IN ('1','2') then if_in_confirm_final else 0 end) AS in_confirm_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_in_confirm_final else 0 end) AS in_confirm_cnt_1_4,
        sum(case when user_level IN ('1','2') then if_in_confirm_final else 0 end) AS rl_in_confirm_cnt_1_2,
        sum(case when user_level IN ('1','2','3') then if_in_confirm_final else 0 end) AS rl_in_confirm_cnt_1_3,
        sum(if_confirm_passed_final) AS confirm_passed_cnt,
        sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
        sum(if_confirm_passed_num_t7) AS if_confirm_passed_num_t7,
        SUM(case when if_in_confirm_final = 1 then grant_amount_max else NULL end) AS in_confirm_grantcredit_amount_total,
        SUM(case when if_in_confirm_final = 1 then grantcredit_amount else NULL end) AS in_confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_grantcredit_amount else NULL end) AS confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_amount else NULL end) AS confirm_apply_amount,
        sum(if_pass) AS pass_cnt,
        count(distinct case when sign_date is not null then biz_id end) AS sign_cnt,
		sum(if_in_anti_fraud) AS if_in_anti_fraud,
        sum(if_anti_fraud_passed) AS if_anti_fraud_passed,
        sum(if_in_anti_fraud_weak) AS if_in_anti_fraud_weak,
        sum(if_anti_fraud_weak_passed) AS if_anti_fraud_weak_passed,
        sum(if_in_external_data_1) AS if_in_external_data_1,
        sum(if_external_data_1_passed) AS if_external_data_1_passed,
        sum(if_in_model) AS if_in_model, 
        sum(if_model_passed) AS if_model_passed, 
        sum(if_in_ai) AS if_in_ai,
        sum(if_ai_passed) AS if_ai_passed,
        sum(if_in_manual_check) AS if_in_manual_check,
        sum(if_in_manual_check_1) AS if_in_manual_check_1,
        sum(if_manual_check_1_passed) AS if_manual_check_1_passed,
        sum(if_in_manual_check_2) AS if_in_manual_check_2,
        sum(if_manual_check_2_passed) AS if_manual_check_2_passed,
        sum(if_in_external_data_pre2) AS if_in_external_data_pre2,
        sum(if_external_data_pre2_passed) AS if_external_data_pre2_passed,
        sum(if_in_external_data_2) AS if_in_external_data_2, 
        sum(if_external_data_2_passed) AS if_external_data_2_passed,
        sum(if_in_external_data_3) AS if_in_external_data_3, 
        sum(if_external_data_3_passed) AS if_external_data_3_passed,
        sum(if_in_external_data_4) AS if_in_external_data_4, 
        sum(if_external_data_4_passed) AS if_external_data_4_passed,
        sum(if_issue) AS issue_cnt_from_app,
        sum(is_released_within_24h) AS is_released_within_24h
    FROM ind.ba_asset_base_info
    WHERE date(app_date) >= DATE('2025-01-01')  
    AND date(app_date) < CURRENT_DATE
    -- AND if_app = 1
    GROUP BY 1,2,3,4,5,6,7,8,9,10



),
issue_metrics AS ( 
    SELECT
        date(issue_date) AS issue_date,
        issue_week,
        issue_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
        media_source2,
        source_channel2,
        sum(if_issue) AS issue_cnt_from_issue,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(case when user_level IN ('1','2') then if_issue else 0 end) AS rl_issue_cnt_1_2,
        sum(case when user_level IN ('1','2','3') then if_issue else 0 end) AS rl_issue_cnt_1_3,

        sum(haircut_amount) as issue_haircut_amount,
        sum(interest) as issue_interest,
        sum(revenue) as issue_revenue,
        sum(contract_amount) AS issue_contract_amount,
        sum(contract_amount_usd1) AS issue_contract_amount_usd,
     
        sum(case when grant_strategy = 'NEW' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_new,
        sum(case when grant_strategy = 'OLD' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_old,
        sum(overdue_amount_1_0) AS overdue_amount_1_0,
        sum(should_capital_1_0) AS should_capital_1_0,
        sum(overdue_amount_1_7) AS overdue_amount_1_7,
        sum(should_capital_1_7) AS should_capital_1_7,
        sum(overdue_amount_1_14) AS overdue_amount_1_14,
        sum(should_capital_1_14) AS should_capital_1_14,
        sum(overdue_amount_1_30) AS overdue_amount_1_30,
        sum(should_capital_1_30) AS should_capital_1_30,
        sum(overdue_amount_2_0) AS overdue_amount_2_0,
        sum(should_capital_2_0) AS should_capital_2_0,
        sum(overdue_amount_2_7) AS overdue_amount_2_7,
        sum(should_capital_2_7) AS should_capital_2_7,
        sum(overdue_amount_2_14) AS overdue_amount_2_14,
        sum(should_capital_2_14) AS should_capital_2_14,
        sum(overdue_amount_2_30) AS overdue_amount_2_30,
        sum(should_capital_2_30) AS should_capital_2_30,

        sum(loan_cycle_amount) AS loan_cycle_amount,
        sum(act_bad_debt_ratio*contract_amount) AS act_bad_debt_amt


    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    AND date(issue_date) >= DATE('2025-01-01') 
    AND date(issue_date) < CURRENT_DATE 
    GROUP BY 1,2,3,4,5,6,7,8,9,10


),



should_metrics AS (


    SELECT
    to_char(date_trunc('month',a.should_date),'yyyy-mm-dd') as should_month,
	to_char(date_trunc('week', a.should_date),'yyyy-mm-dd') as should_week,
    date(a.should_date) AS should_date,
    c.grant_strategy,
    c.product_tag,
    c.is_reloan2,
    c.new_grade_level,
    c.user_level,
    c.media_source2,
    c.source_channel2, 

    SUM(a.should_capital) AS should_capital, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.should_capital ELSE null END) AS should_capital_d0, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.should_capital ELSE null END) AS should_capital_d1,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.should_capital ELSE null END) AS should_capital_d7,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.should_capital ELSE null END) AS should_capital_d15,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.should_capital ELSE null END) AS should_capital_d30,
 
 
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d0, 
    SUM(CASE WHEN due_day <= 1  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.fact_capital ELSE 0 END) AS t1_capital_paid_d1,
    SUM(CASE WHEN due_day <= 7  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.fact_capital ELSE 0 END) AS t7_capital_paid_d7,
    SUM(CASE WHEN due_day <= 15 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t15_capital_paid_d15,
    SUM(CASE WHEN due_day <= 30 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t30_capital_paid_d30,

    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8  THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d7,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d15,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d30


 
FROM (
    SELECT  
        customer_id,
        camera_id AS biz_id, 
        should_date, 
        due_day, 
        SUM(should_amount) AS should_amount,
        SUM(should_capital) AS should_capital,
        SUM(should_interest) AS should_interest,
        SUM(should_fine) AS should_fine,
        SUM(fact_amount) AS fact_amount,
        SUM(fact_capital) AS fact_capital,
        SUM(fact_interest) AS fact_interest,
        SUM(fact_fine) AS fact_fine
    FROM ind.gqy_case_info_f
    WHERE is_due = 0
        AND should_date >= DATE('2025-01-01') 
        AND should_date < CURRENT_DATE
    GROUP BY 
        1,2,3,4

) a 
LEFT JOIN (
    SELECT 
        data_date,
        customer_id,
        MAX(max_due_day) AS cus_ovd_day
    FROM ind.gqy_daliy_case
    GROUP BY 1,2
    HAVING MAX(max_due_day) >= 1
) b ON a.customer_id = b.customer_id AND should_date = b.data_date
left join ind.ba_asset_base_info c 
on  TRY_CAST (a.biz_id AS BIGINT) = TRY_CAST (c.biz_id AS BIGINT)
WHERE b.customer_id IS NULL 
GROUP BY 1,2,3,4,5,6,7,8,9,10


),
data_date as (
    select distinct 
    date_mon,
    date_format(DATE_PARSE(data_date, '%Y%m%d'), '%Y-%m-01') AS data_month, 
    month_days,  
    day(DATE_ADD('day', -1, CURRENT_DATE)) as current_date_day,
    case when DATE_PARSE(month_end, '%Y%m%d')<DATE_TRUNC('month', CURRENT_DATE) 
    then day(DATE_PARSE(month_end, '%Y%m%d'))
    else day(DATE_ADD('day', -1, CURRENT_DATE))
    end as date_month_end_actual 
    from dim.dim_data_info
)

 


        SELECT 
    COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy) AS grant_strategy,
    COALESCE(a.product_tag, i.product_tag, s.product_tag) AS product_tag,
    COALESCE(a.is_reloan2, i.is_reloan2, s.is_reloan2) AS is_reloan2,
    COALESCE(a.new_grade_level, i.new_grade_level, s.new_grade_level) AS new_grade_level,
    COALESCE(a.user_level, i.user_level, s.user_level) AS user_level,
    COALESCE(a.media_source2, i.media_source2, s.media_source2) AS media_source,
    COALESCE(a.source_channel2, i.source_channel2, s.source_channel2) AS source_channel2,
    COALESCE(a.app_date, i.issue_date, s.should_date) AS app_date,
    COALESCE(a.app_week, i.issue_week, s.should_week) AS app_week,
    COALESCE(a.app_month, i.issue_month, s.should_month) AS app_month,  
    COALESCE(a.if_app, 0) AS if_app,
    COALESCE(a.in_confirm_cnt, 0) AS in_confirm_cnt,
    COALESCE(a.in_confirm_cnt_1_2, 0) AS in_confirm_cnt_1_2,
    COALESCE(a.in_confirm_cnt_1_4, 0) AS in_confirm_cnt_1_4,
    COALESCE(a.rl_in_confirm_cnt_1_2, 0) AS rl_in_confirm_cnt_1_2,
    COALESCE(a.rl_in_confirm_cnt_1_3, 0) AS rl_in_confirm_cnt_1_3,

    COALESCE(a.confirm_passed_cnt, 0) AS confirm_passed_cnt,
    COALESCE(a.if_confirm_passed_num_t0, 0) AS if_confirm_passed_num_t0,
    COALESCE(a.if_confirm_passed_num_t7, 0) AS if_confirm_passed_num_t7,

    COALESCE(a.in_confirm_grantcredit_amount_total, 0) AS in_confirm_grantcredit_amount_total,
    COALESCE(a.in_confirm_grantcredit_amount, 0) AS in_confirm_grantcredit_amount,
    COALESCE(a.confirm_grantcredit_amount, 0) AS confirm_grantcredit_amount,
    COALESCE(a.confirm_apply_amount, 0) AS confirm_apply_amount,
    COALESCE(a.pass_cnt, 0) AS pass_cnt,
    COALESCE(a.sign_cnt, 0) AS sign_cnt,
	
    COALESCE(if_in_anti_fraud, 0) AS if_in_anti_fraud,
    COALESCE(if_anti_fraud_passed, 0) AS if_anti_fraud_passed,
    COALESCE(if_in_anti_fraud_weak, 0) AS if_in_anti_fraud_weak,
    COALESCE(if_anti_fraud_weak_passed, 0) AS if_anti_fraud_weak_passed,
    COALESCE(if_in_external_data_1, 0) AS if_in_external_data_1,
    COALESCE(if_external_data_1_passed, 0) AS if_external_data_1_passed,
    COALESCE(if_in_model, 0) AS if_in_model, 
    COALESCE(if_model_passed, 0) AS if_model_passed, 
    COALESCE(if_in_ai, 0) AS if_in_ai,
    COALESCE(if_ai_passed, 0) AS if_ai_passed,
    COALESCE(if_in_manual_check, 0) AS if_in_manual_check,
    COALESCE(if_in_manual_check_1, 0) AS if_in_manual_check_1,
    COALESCE(if_manual_check_1_passed, 0) AS if_manual_check_1_passed,
    COALESCE(if_in_manual_check_2, 0) AS if_in_manual_check_2,
    COALESCE(if_manual_check_2_passed, 0) AS if_manual_check_2_passed,
    COALESCE(if_in_external_data_pre2, 0) AS if_in_external_data_pre2,
    COALESCE(if_external_data_pre2_passed, 0) AS if_external_data_pre2_passed,
    COALESCE(if_in_external_data_2, 0) AS if_in_external_data_2, 
    COALESCE(if_external_data_2_passed, 0) AS if_external_data_2_passed,
    COALESCE(if_in_external_data_3, 0) AS if_in_external_data_3, 
    COALESCE(if_external_data_3_passed, 0) AS if_external_data_3_passed,
    COALESCE(if_in_external_data_4, 0) AS if_in_external_data_4, 
    COALESCE(if_external_data_4_passed, 0) AS if_external_data_4_passed,
 
    COALESCE(a.issue_cnt_from_app, 0) AS issue_cnt_from_app,
    COALESCE(a.is_released_within_24h, 0) AS is_released_within_24h, 
    COALESCE(i.issue_cnt_from_issue, 0) AS issue_cnt_from_issue,
    COALESCE(i.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(i.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(i.rl_issue_cnt_1_2, 0) AS rl_issue_cnt_1_2,
    COALESCE(i.rl_issue_cnt_1_3, 0) AS rl_issue_cnt_1_3,
    COALESCE(i.issue_contract_amount, 0) AS issue_contract_amount,
    COALESCE(i.issue_contract_amount_usd, 0) AS issue_contract_amount_usd,
    SUM(COALESCE(i.issue_contract_amount_usd, 0)) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='NEW'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_new_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='OLD'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_old_group,
    
    COALESCE(i.overdue_amount_1_0, 0) AS overdue_amount_1_0,
    COALESCE(i.should_capital_1_0, 0) AS should_capital_1_0,
    COALESCE(i.overdue_amount_1_7, 0) AS overdue_amount_1_7,
    COALESCE(i.should_capital_1_7, 0) AS should_capital_1_7,
    COALESCE(i.overdue_amount_1_14, 0) AS overdue_amount_1_14,
    COALESCE(i.should_capital_1_14, 0) AS should_capital_1_14,
    COALESCE(i.overdue_amount_1_30, 0) AS overdue_amount_1_30,
    COALESCE(i.should_capital_1_30, 0) AS should_capital_1_30, 
    COALESCE(i.overdue_amount_2_0, 0) AS overdue_amount_2_0,
    COALESCE(i.should_capital_2_0, 0) AS should_capital_2_0,
    COALESCE(i.overdue_amount_2_7, 0) AS overdue_amount_2_7,
    COALESCE(i.should_capital_2_7, 0) AS should_capital_2_7,
    COALESCE(i.overdue_amount_2_14, 0) AS overdue_amount_2_14,
    COALESCE(i.should_capital_2_14, 0) AS should_capital_2_14,
    COALESCE(i.overdue_amount_2_30, 0) AS overdue_amount_2_30,
    COALESCE(i.should_capital_2_30, 0) AS should_capital_2_30, 
    COALESCE(s.should_capital_d0, 0) AS should_capital_d0, 
    COALESCE(s.should_capital_d1, 0) AS should_capital_d1,
    COALESCE(s.should_capital_d7, 0) AS should_capital_d7,
    COALESCE(s.should_capital_d15, 0) AS should_capital_d15,
    COALESCE(s.should_capital_d30, 0) AS should_capital_d30, 
    COALESCE(s.should_capital_d0 - s.t0_capital_paid_d0, 0) AS t0_capital_due_d0,
    COALESCE(s.should_capital_d1 - s.t1_capital_paid_d1, 0) AS t1_capital_due_d1,
    COALESCE(s.should_capital_d7 - s.t7_capital_paid_d7, 0) AS t7_capital_due_d7,
    COALESCE(s.should_capital_d15 - s.t15_capital_paid_d15, 0) AS t15_capital_due_d15,
    COALESCE(s.should_capital_d30 - s.t30_capital_paid_d30, 0) AS t30_capital_due_d30,
    COALESCE(s.t0_capital_paid_d7, 0) AS t0_capital_paid_d7,
    COALESCE(s.t0_capital_paid_d15, 0) AS t0_capital_paid_d15,
    COALESCE(s.t0_capital_paid_d30, 0) AS t0_capital_paid_d30,
    COALESCE(s.t7_capital_paid_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_d7,
    COALESCE(s.t15_capital_paid_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_d15,
    COALESCE(s.t30_capital_paid_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_d30,

    COALESCE(s.should_capital_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_due_d7,
    COALESCE(s.should_capital_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_due_d15,
    COALESCE(s.should_capital_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_due_d30,
    COALESCE(loan_cycle_amount, 0) AS loan_cycle_amount,
    COALESCE(issue_haircut_amount, 0) AS issue_haircut_amount,
    COALESCE(issue_interest, 0) AS issue_interest,
    COALESCE(issue_revenue, 0) AS issue_revenue,
    COALESCE(act_bad_debt_amt, 0) AS act_bad_debt_amt,
    total_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar  AS ov_total_amt_usd,
    fl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS fl_total_amt_usd,
    rl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS rl_total_amt_usd,
    month_days, 
    date_month_end_actual ,
    COALESCE(issue_contract_amount_usd_new, 0) AS issue_contract_amount_usd_new,
    COALESCE(issue_contract_amount_usd_old, 0) AS issue_contract_amount_usd_old
    

FROM application_metrics a
FULL JOIN issue_metrics i 
    ON a.grant_strategy = i.grant_strategy
    AND a.product_tag = i.product_tag
    AND a.is_reloan2 = i.is_reloan2
    AND a.new_grade_level = i.new_grade_level
    AND a.media_source2 = i.media_source2
    AND a.source_channel2 = i.source_channel2
    AND a.app_date = i.issue_date
    AND a.app_week = i.issue_week
    AND a.app_month = i.issue_month
    AND a.user_level = i.user_level

FULL JOIN should_metrics s
    ON COALESCE(a.grant_strategy, i.grant_strategy) = s.grant_strategy
    AND COALESCE(a.product_tag, i.product_tag) = s.product_tag
    AND COALESCE(a.is_reloan2, i.is_reloan2) = s.is_reloan2
    AND COALESCE(a.new_grade_level, i.new_grade_level) = s.new_grade_level
    AND COALESCE(a.media_source2, i.media_source2) = s.media_source2
    AND COALESCE(a.source_channel2, i.source_channel2) = s.source_channel2
    AND COALESCE(a.app_date, i.issue_date) = s.should_date
    AND COALESCE(a.app_week, i.issue_week) = s.should_week
    AND COALESCE(a.app_month, i.issue_month) = s.should_month
    AND COALESCE(a.user_level, i.user_level) = s.user_level
LEFT JOIN ind.ba_kpi_targets_m b
    ON COALESCE(a.app_month, i.issue_month, s.should_month) = b.month 
left join data_date c
    ON b.month = c.data_month 
LEFT JOIN dim.dim_exchange_rate_cost f1 ON c.date_mon = f1.month_id AND f1.account_currency = 'IDR'
;

 
 

drop table if exists ind.ba_install_apply_result;
create table
if not exists ind.ba_install_apply_result as

with spend AS (
    select 
        date(ad_date) as ad_date
        ,case when lower(campaign_name) like  '%ios%' or media_source='ASA' or lower(media_source) like '%ios%' then 'IOS'
                when media_source like '%oogle%' and lower(campaign_name) not like '%ios%' then 'Google'
                when media_source like '%acebook%' and lower(campaign_name) not like '%ios%' then 'Facebook'
                when media_source='organic' then 'Organic'  
                when media_source='Tiktok' then 'Tiktok'
                when media_source='Kwai' then 'Kwai'
                else 'other'
            end as media_source
        ,sum(spend_usd_discount) as spend
        from ind.tyn_ads_cost_discount a
        where ad_date >= date'2025-01-01'
        group by 1,2  
    union all
    select
        distinct
        ad_date,
        'Organic' as media_source,
        0 as spend
        from ind.tyn_ads_cost_discount  
        where ad_date >= date'2025-01-01'
    ),
install_cnt as (
    SELECT install_date,   
    case when media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source else 'other' end as media_source,

    sum(install_cnt) as install_cnt 
    FROM (
    SELECT 
    DATE(event_time + INTERVAL '7' HOUR) AS install_date,
    case 	   		
			when platform = 'ios'  then 'IOS'	
			when media_source='googleadwords_int' then 'Google'
             when media_source='Facebook Ads' or media_source='restricted' then 'Facebook'
             when media_source='organic' then 'Organic'
             when media_source = 'shareit_int' then 'Shareit'
             when  media_source = 'kreditlist_int' or (media_source = 'vfine_int' and partner like '%redi%'  ) 
             or 
             (media_source is null and partner = 'kreditlist')
             then 'kreditlist_int'
			 when media_source = 'vfine_int' or media_source = 'adecentptuo_int' then 'Vfine'
             when media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when media_source = 'kwaiforbusiness_int' then 'Kwai'
             when media_source = 'cashcashpro' then 'cashcashpro'
			 when media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when media_source = 'kredit pintal' then 'kp'
			 when media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(campaign, '^pp') then 'Novabeyond'
			 when media_source = 'pyxis_int' then 'pyxis'
			 when media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when media_source = 'Twitter' then 'twitter'
			 when media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' or partner ='appscuckoobd650' then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(partner) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when campaign like '%CookeAds_CPI%' then 'CookeAds_CPI'
			when campaign ='CookeAds_CPS' or lower(campaign) like '%cookeads%' then 'CookeAds_CPS'
			when partner = '19mobicn' then '19mobi'
			when campaign = 'Samire_Jan2025youmi' then 'youmi'
			when media_source ='yupaamj_int' then 'yup'
			--when regexp_like(campaign, '^pp') then 'Novabeyond'
			when media_source = 'mintegral_int' then 'mintegral_int'
			when lower(media_source) like '%grab%' then 'Grab'
			when media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(campaign) like '%runto%' then 'RUNTOA'
			when lower(campaign) like '%mejoy%'  then 'mejoy'
			when lower(campaign) like '%yolo%'  then 'yolo'
			when media_source ='LinkAja_ads' then 'LinkAja_ads'
			when media_source ='easycash01' then 'easycash01'
			when media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when media_source ='tangads' then 'tangads'
			when media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when media_source ='oppoglobal_int' then 'oppoglobal_int'
            when media_source like '%_int%' then 'other'
			 else 'Organic'
        end as media_source,
    COUNT(DISTINCT appsflyer_id) AS install_cnt
    FROM ods.s08_appsflyer_push_data
    WHERE  etl_date>='20250101' and event_name='install' 
    and date(event_time + INTERVAL '7' HOUR) >= date'2025-01-01'
    GROUP BY 1,2 
    )t
    GROUP BY 1,2 
     ),

 
reg_cnt as (
    select 
    reg_dt,
    case 
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai','IOS') then media_source 
    when media_source='ASA' or lower(media_source) like '%ios%' then 'IOS' 
    else 'other'
    end as media_source, 
    count(distinct mid) reg_cnt
    from ind.tyn_reg_install_new
    where reg_dt >= date'2025-01-01'
    group by 1,2 
     ),
apply_cnt AS ( 
    SELECT
        date(app_date) as app_date,  
        media_source2, 
        sum(if_app) AS if_app  
    FROM ind.ba_asset_base_info 
    WHERE grant_strategy='NEW' 
    and if_app=1
    and date(app_date) >= date'2025-01-01'
    GROUP BY 1,2 

),
issue_cnt AS ( 

    SELECT
        date(issue_date) as issue_date, 
        media_source2, 
        sum(if_issue) AS issue_cnt,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(contract_amount_usd) as contract_amount_usd
    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    and grant_strategy='NEW' 
    and date(issue_date) >= date'2025-01-01'
    GROUP BY 1,2
)
 
SELECT
    COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date) AS ad_date,
    to_char(date_trunc('month', COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date)), 'yyyy-mm-dd') AS ad_date_month,
    to_char(date_trunc('week', COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date)), 'yyyy-mm-dd') AS ad_date_week,
    COALESCE(a.media_source, b.media_source, c.media_source, d.media_source2, e.media_source2) AS media_source,
    COALESCE(a.spend, 0) AS spend,
    COALESCE(b.install_cnt, 0) AS install_cnt,
    COALESCE(c.reg_cnt, 0) AS reg_cnt,
    COALESCE(d.if_app, 0) AS if_app,
    COALESCE(e.issue_cnt, 0) AS issue_cnt,
    COALESCE(e.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(e.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(e.contract_amount_usd, 0) AS contract_amount_usd

FROM spend a
FULL OUTER JOIN install_cnt b ON a.ad_date = b.install_date AND a.media_source = b.media_source
FULL OUTER JOIN reg_cnt c ON a.ad_date = c.reg_dt AND a.media_source = c.media_source
FULL OUTER JOIN apply_cnt d ON a.ad_date = d.app_date AND a.media_source = d.media_source2
FULL OUTER JOIN issue_cnt e ON a.ad_date = e.issue_date AND a.media_source = e.media_source2;


  