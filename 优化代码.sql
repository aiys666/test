  
CREATE TABLE IF NOT EXISTS ind.ys_finebi_table_mob_250804 (
    mid VARCHAR,
    firstchannel VARCHAR,
    firstisreloan2 INT,
    firstlevel INT,
    firstproduct VARCHAR,
    firstcycle INT,
    firstissuedate DATE,
    firstissueweek VARCHAR,
    firstissuemonth DATE,
    firstgrantamt DOUBLE,
    firstissueamt DOUBLE,
    firstproductamt DOUBLE,
    first_1_7_capital DOUBLE,
    first_2_7_capital DOUBLE,
    first_1_7_overdue DOUBLE,
    first_2_7_overdue DOUBLE,
    
    reloan_tag INT,
    channel_tag VARCHAR,
    is_reloan2 INT,
    new_grade_level INT,
    product_type VARCHAR,
    user_level INT,
    interval_start INT,
    
    mob_tag VARCHAR,
    
    mob_issue_cnt BIGINT,
    mob_issue_mid BIGINT,
    mob_issue_amt DOUBLE,
    mob_grant_amt_total_avg DOUBLE,
    mob_grant_amt_total_max DOUBLE,
    
    limit_usage_fz DOUBLE,
    limit_usage_fm DOUBLE,
    limit_occupy_fz DOUBLE,
    limit_occupy_fm DOUBLE,
    
    ovd7_p1_p1_mob_sum BIGINT,
    due7_p1_p1_mob_sum BIGINT,
    ovd7_p2_p1_mob_sum BIGINT,
    due7_p2_p1_mob_sum BIGINT,
    
    exchange_rate_to_dollar DOUBLE,
    rn BIGINT,
    firstissuemonth_part DATE   
)
WITH (
    format = 'ORC',
    partitioned_by = ARRAY['firstissuemonth_part']   
);
 
INSERT INTO ind.ys_finebi_table_mob_250804 


-- DROP TABLE IF EXISTS ind.ys_finebi_table_mob_250804;
-- CREATE TABLE IF NOT EXISTS ind.ys_finebi_table_mob_250804 AS

WITH t1 AS (
     SELECT 
        biz_id,
        mid,
        CASE WHEN source_channel2 = 'IOS' THEN 'IOS' ELSE 'Android' END AS channel_tag,
        is_reloan2,
        new_grade_level,
        product_tag AS product_type,
        interval_start_old AS interval_start,
        issue_date,
        issue_week,
        issue_month,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '1' MONTH) - INTERVAL '1' DAY AS mob0_date,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '2' MONTH) - INTERVAL '1' DAY AS mob1_date,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '3' MONTH) - INTERVAL '1' DAY AS mob2_date,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '4' MONTH) - INTERVAL '1' DAY AS mob3_date,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '5' MONTH) - INTERVAL '1' DAY AS mob4_date,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '6' MONTH) - INTERVAL '1' DAY AS mob5_date,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '7' MONTH) - INTERVAL '1' DAY AS mob6_date,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '8' MONTH) - INTERVAL '1' DAY AS mob7_date,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '9' MONTH) - INTERVAL '1' DAY AS mob8_date,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '10' MONTH) - INTERVAL '1' DAY AS mob9_date,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '11' MONTH) - INTERVAL '1' DAY AS mob10_date,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '12' MONTH) - INTERVAL '1' DAY AS mob11_date,
        DATE_TRUNC('month', DATE(issue_month) + INTERVAL '13' MONTH) - INTERVAL '1' DAY AS mob12_date,
        apply_grantcredit_amount AS issue_grantcredit_amount,
        contract_amount_usd1 AS issue_amount,
        contract_amount_usd1 * interval_start_old AS productday_amount,
        should_capital_1_7 AS should_capital_1_7,
        should_capital_2_7 AS should_capital_2_7,
        overdue_amount_1_7 AS overdue_amount_1_7,
        overdue_amount_2_7 AS overdue_amount_2_7
    FROM ind.ba_asset_base_info
    WHERE if_issue = 1 
        AND grant_strategy = 'NEW' 
        AND issue_month >= '2024-12-01'
 ),

t2 AS (
    SELECT 
        biz_id,
        mid,
        reloan_num,
        CASE WHEN reloan_num = 2 THEN 2 ELSE 3 END AS reloan_tag,
        source_channel2 AS channel_tag,
        is_reloan2,
        new_grade_level,
        product_tag AS product_type,
        user_level,
        interval_start_old AS interval_start,
        issue_date,
        issue_week,
        issue_month,
        contract_amount_usd1 AS contract_amount,
        baseinfo_onloan_amount_usd AS baseinfo_onloan_amount,
        apply_grantcredit_amount AS issue_grantcredit_amount,       
        grant_amount_max AS issue_grantcredit_amount_total,         
        contract_amount_usd1 AS issue_amount,                     
        contract_amount_usd1 * interval_start_old AS productday_amount
    FROM ind.ba_asset_base_info
    WHERE if_issue = 1 
        AND grant_strategy = 'OLD' 
        AND issue_month >= '2024-12-01'
 ),

t2_agg AS (
SELECT
    *,
    issue_amount AS limit_usage_fz, 
    CASE 
        WHEN issue_amount > issue_grantcredit_amount AND issue_grantcredit_amount > 0 
            THEN issue_amount
        WHEN issue_grantcredit_amount > 0 
            THEN issue_grantcredit_amount
        ELSE issue_amount
    END AS limit_usage_fm,
    issue_amount + baseinfo_onloan_amount AS limit_occupy_fz,
    CASE 
        WHEN issue_amount + baseinfo_onloan_amount > issue_grantcredit_amount_total 
             AND issue_grantcredit_amount_total > 0 
            THEN issue_amount + baseinfo_onloan_amount
        WHEN issue_grantcredit_amount_total > 0 
            THEN issue_grantcredit_amount_total
        ELSE issue_amount
    END AS limit_occupy_fm
FROM t2
),

b1 AS ( 
    SELECT 
        l.mid,
        l.mob0_date,
        l.mob1_date,
        l.mob2_date,
        l.mob3_date,
        l.mob4_date,
        l.mob5_date,
        l.mob6_date,
        CASE WHEN lr.indexs = 1 THEN DATE_ADD('day', 7, DATE(lr.should_time)) END AS due7_p1_date,
        CASE WHEN lr.indexs = 2 THEN DATE_ADD('day', 7, DATE(lr.should_time)) END AS due7_p2_date,
        CASE WHEN lr.indexs = 1 AND lr.fact_time IS NOT NULL THEN DATE(lr.fact_time) END AS repayment_p1_date,
        CASE WHEN lr.indexs = 2 AND lr.fact_time IS NOT NULL THEN DATE(lr.fact_time) END AS repayment_p2_date
    FROM t1 l
    LEFT JOIN ods.s02_loan_repayment lr
        ON l.mid = CEIL(lr.customer_id) 
        AND l.biz_id < CAST(CEIL(lr.camera_id) AS VARCHAR) 
        AND lr.indexs <= 2
),

b2 AS ( 
    SELECT 
        mid,
        mob0_date,
        mob1_date,
        mob2_date,
        mob3_date,
        mob4_date,
        mob5_date,
        mob6_date, 
        MAX(CASE WHEN due7_p1_date <= mob0_date THEN 1 ELSE 0 END) AS due7_p1_mob0,
        MAX(CASE WHEN due7_p1_date <= mob1_date AND due7_p1_date > mob0_date THEN 1 ELSE 0 END) AS due7_p1_mob1,
        MAX(CASE WHEN due7_p1_date <= mob2_date AND due7_p1_date > mob1_date THEN 1 ELSE 0 END) AS due7_p1_mob2,
        MAX(CASE WHEN due7_p1_date <= mob3_date AND due7_p1_date > mob2_date THEN 1 ELSE 0 END) AS due7_p1_mob3,
        MAX(CASE WHEN due7_p1_date <= mob4_date AND due7_p1_date > mob3_date THEN 1 ELSE 0 END) AS due7_p1_mob4,
        MAX(CASE WHEN due7_p1_date <= mob5_date AND due7_p1_date > mob4_date THEN 1 ELSE 0 END) AS due7_p1_mob5,
        MAX(CASE WHEN due7_p1_date <= mob6_date AND due7_p1_date > mob5_date THEN 1 ELSE 0 END) AS due7_p1_mob6,
        
        MAX(CASE WHEN (repayment_p1_date IS NULL OR repayment_p1_date > mob0_date) AND due7_p1_date <= mob0_date THEN 1 ELSE 0 END) AS ovd7_p1_mob0,
        MAX(CASE WHEN (repayment_p1_date IS NULL OR repayment_p1_date > mob1_date) AND due7_p1_date <= mob1_date THEN 1 ELSE 0 END) AS ovd7_p1_mob1,
        MAX(CASE WHEN (repayment_p1_date IS NULL OR repayment_p1_date > mob2_date) AND due7_p1_date <= mob2_date THEN 1 ELSE 0 END) AS ovd7_p1_mob2,
        MAX(CASE WHEN (repayment_p1_date IS NULL OR repayment_p1_date > mob3_date) AND due7_p1_date <= mob3_date THEN 1 ELSE 0 END) AS ovd7_p1_mob3,
        MAX(CASE WHEN (repayment_p1_date IS NULL OR repayment_p1_date > mob4_date) AND due7_p1_date <= mob4_date THEN 1 ELSE 0 END) AS ovd7_p1_mob4,
        MAX(CASE WHEN (repayment_p1_date IS NULL OR repayment_p1_date > mob5_date) AND due7_p1_date <= mob5_date THEN 1 ELSE 0 END) AS ovd7_p1_mob5,
        MAX(CASE WHEN (repayment_p1_date IS NULL OR repayment_p1_date > mob6_date) AND due7_p1_date <= mob6_date THEN 1 ELSE 0 END) AS ovd7_p1_mob6,
         
        MAX(CASE WHEN due7_p2_date <= mob0_date THEN 1 ELSE 0 END) AS due7_p2_mob0,
        MAX(CASE WHEN due7_p2_date <= mob1_date AND due7_p2_date > mob0_date THEN 1 ELSE 0 END) AS due7_p2_mob1,
        MAX(CASE WHEN due7_p2_date <= mob2_date AND due7_p2_date > mob1_date THEN 1 ELSE 0 END) AS due7_p2_mob2,
        MAX(CASE WHEN due7_p2_date <= mob3_date AND due7_p2_date > mob2_date THEN 1 ELSE 0 END) AS due7_p2_mob3,
        MAX(CASE WHEN due7_p2_date <= mob4_date AND due7_p2_date > mob3_date THEN 1 ELSE 0 END) AS due7_p2_mob4,
        MAX(CASE WHEN due7_p2_date <= mob5_date AND due7_p2_date > mob4_date THEN 1 ELSE 0 END) AS due7_p2_mob5,
        MAX(CASE WHEN due7_p2_date <= mob6_date AND due7_p2_date > mob5_date THEN 1 ELSE 0 END) AS due7_p2_mob6,
        
        MAX(CASE WHEN (repayment_p2_date IS NULL OR repayment_p2_date > mob0_date) AND due7_p2_date <= mob0_date THEN 1 ELSE 0 END) AS ovd7_p2_mob0,
        MAX(CASE WHEN (repayment_p2_date IS NULL OR repayment_p2_date > mob1_date) AND due7_p2_date <= mob1_date THEN 1 ELSE 0 END) AS ovd7_p2_mob1,
        MAX(CASE WHEN (repayment_p2_date IS NULL OR repayment_p2_date > mob2_date) AND due7_p2_date <= mob2_date THEN 1 ELSE 0 END) AS ovd7_p2_mob2,
        MAX(CASE WHEN (repayment_p2_date IS NULL OR repayment_p2_date > mob3_date) AND due7_p2_date <= mob3_date THEN 1 ELSE 0 END) AS ovd7_p2_mob3,
        MAX(CASE WHEN (repayment_p2_date IS NULL OR repayment_p2_date > mob4_date) AND due7_p2_date <= mob4_date THEN 1 ELSE 0 END) AS ovd7_p2_mob4,
        MAX(CASE WHEN (repayment_p2_date IS NULL OR repayment_p2_date > mob5_date) AND due7_p2_date <= mob5_date THEN 1 ELSE 0 END) AS ovd7_p2_mob5,
        MAX(CASE WHEN (repayment_p2_date IS NULL OR repayment_p2_date > mob6_date) AND due7_p2_date <= mob6_date THEN 1 ELSE 0 END) AS ovd7_p2_mob6
    FROM b1
    GROUP BY 1,2,3,4,5,6,7,8
),
 
mob_periods AS (
    SELECT 0 AS mob_num, 'mob0' AS mob_tag, 'mob0_date' AS mob_date_col
    UNION ALL SELECT 1, 'mob1', 'mob1_date'
    UNION ALL SELECT 2, 'mob2', 'mob2_date'
    UNION ALL SELECT 3, 'mob3', 'mob3_date'
    UNION ALL SELECT 4, 'mob4', 'mob4_date'
    UNION ALL SELECT 5, 'mob5', 'mob5_date'
    UNION ALL SELECT 6, 'mob6', 'mob6_date'
    UNION ALL SELECT 7, 'mob7', 'mob7_date'
    UNION ALL SELECT 8, 'mob8', 'mob8_date'
    UNION ALL SELECT 9, 'mob9', 'mob9_date'
    UNION ALL SELECT 10, 'mob10', 'mob10_date'
    UNION ALL SELECT 11, 'mob11', 'mob11_date'
    UNION ALL SELECT 12, 'mob12', 'mob12_date'
    UNION ALL SELECT 13, 'mob12+', 'mob12_date'
),
 
mob_data AS (
    SELECT 
        t1.mid,
        t1.channel_tag AS firstchannel,
        t1.is_reloan2 AS firstisreloan2,
        t1.new_grade_level AS firstlevel,
        t1.product_type AS firstproduct,
        t1.interval_start AS firstcycle,
        t1.issue_date AS firstissuedate,
        t1.issue_week AS firstissueweek,
        t1.issue_month AS firstissuemonth,
        t1.issue_grantcredit_amount AS firstgrantamt,
        t1.issue_amount AS firstissueamt,
        t1.productday_amount AS firstproductamt,
        t1.should_capital_1_7 AS first_1_7_capital,
        t1.should_capital_2_7 AS first_2_7_capital,
        t1.overdue_amount_1_7 AS first_1_7_overdue,
        t1.overdue_amount_2_7 AS first_2_7_overdue,
        
        mp.mob_tag,
         
        t2_agg.reloan_tag,
        t2_agg.channel_tag,
        t2_agg.is_reloan2,
        t2_agg.new_grade_level,
        t2_agg.product_type,
        t2_agg.user_level,
        t2_agg.interval_start,
         
        CASE 
            WHEN mp.mob_num = 0 THEN DATE(t2_agg.issue_date) <= t1.mob0_date
            WHEN mp.mob_num = 1 THEN DATE(t2_agg.issue_date) <= t1.mob1_date AND DATE(t2_agg.issue_date) > t1.mob0_date
            WHEN mp.mob_num = 2 THEN DATE(t2_agg.issue_date) <= t1.mob2_date AND DATE(t2_agg.issue_date) > t1.mob1_date
            WHEN mp.mob_num = 3 THEN DATE(t2_agg.issue_date) <= t1.mob3_date AND DATE(t2_agg.issue_date) > t1.mob2_date
            WHEN mp.mob_num = 4 THEN DATE(t2_agg.issue_date) <= t1.mob4_date AND DATE(t2_agg.issue_date) > t1.mob3_date
            WHEN mp.mob_num = 5 THEN DATE(t2_agg.issue_date) <= t1.mob5_date AND DATE(t2_agg.issue_date) > t1.mob4_date
            WHEN mp.mob_num = 6 THEN DATE(t2_agg.issue_date) <= t1.mob6_date AND DATE(t2_agg.issue_date) > t1.mob5_date
            WHEN mp.mob_num = 7 THEN DATE(t2_agg.issue_date) <= t1.mob7_date AND DATE(t2_agg.issue_date) > t1.mob6_date
            WHEN mp.mob_num = 8 THEN DATE(t2_agg.issue_date) <= t1.mob8_date AND DATE(t2_agg.issue_date) > t1.mob7_date
            WHEN mp.mob_num = 9 THEN DATE(t2_agg.issue_date) <= t1.mob9_date AND DATE(t2_agg.issue_date) > t1.mob8_date
            WHEN mp.mob_num = 10 THEN DATE(t2_agg.issue_date) <= t1.mob10_date AND DATE(t2_agg.issue_date) > t1.mob9_date
            WHEN mp.mob_num = 11 THEN DATE(t2_agg.issue_date) <= t1.mob11_date AND DATE(t2_agg.issue_date) > t1.mob10_date
            WHEN mp.mob_num = 12 THEN DATE(t2_agg.issue_date) <= t1.mob12_date AND DATE(t2_agg.issue_date) > t1.mob11_date
            WHEN mp.mob_num = 13 THEN DATE(t2_agg.issue_date) > t1.mob12_date
        END AS in_mob_window,
         
        t2_agg.biz_id,
        t2_agg.mid AS t2mid,
        t2_agg.issue_amount,
        t2_agg.issue_grantcredit_amount_total,
        t2_agg.limit_usage_fz,
        t2_agg.limit_usage_fm,
        t2_agg.limit_occupy_fz,
        t2_agg.limit_occupy_fm,
        t2_agg.reloan_num,
        t2_agg.issue_date AS t2_issue_date,
         
        CASE mp.mob_num
            WHEN 0 THEN b2.ovd7_p1_mob0
            WHEN 1 THEN b2.ovd7_p1_mob1
            WHEN 2 THEN b2.ovd7_p1_mob2
            WHEN 3 THEN b2.ovd7_p1_mob3
            WHEN 4 THEN b2.ovd7_p1_mob4
            WHEN 5 THEN b2.ovd7_p1_mob5
            WHEN 6 THEN b2.ovd7_p1_mob6
            ELSE 0
        END AS ovd7_p1_mob,
        
        CASE mp.mob_num
            WHEN 0 THEN b2.due7_p1_mob0
            WHEN 1 THEN b2.due7_p1_mob1
            WHEN 2 THEN b2.due7_p1_mob2
            WHEN 3 THEN b2.due7_p1_mob3
            WHEN 4 THEN b2.due7_p1_mob4
            WHEN 5 THEN b2.due7_p1_mob5
            WHEN 6 THEN b2.due7_p1_mob6
            ELSE 0
        END AS due7_p1_mob,
        
        CASE mp.mob_num
            WHEN 0 THEN b2.ovd7_p2_mob0
            WHEN 1 THEN b2.ovd7_p2_mob1
            WHEN 2 THEN b2.ovd7_p2_mob2
            WHEN 3 THEN b2.ovd7_p2_mob3
            WHEN 4 THEN b2.ovd7_p2_mob4
            WHEN 5 THEN b2.ovd7_p2_mob5
            WHEN 6 THEN b2.ovd7_p2_mob6
            ELSE 0
        END AS ovd7_p2_mob,
        
        CASE mp.mob_num
            WHEN 0 THEN b2.due7_p2_mob0
            WHEN 1 THEN b2.due7_p2_mob1
            WHEN 2 THEN b2.due7_p2_mob2
            WHEN 3 THEN b2.due7_p2_mob3
            WHEN 4 THEN b2.due7_p2_mob4
            WHEN 5 THEN b2.due7_p2_mob5
            WHEN 6 THEN b2.due7_p2_mob6
            ELSE 0
        END AS due7_p2_mob     
    FROM t1
    CROSS JOIN mob_periods mp
    LEFT JOIN t2_agg ON t1.mid = t2_agg.mid
    LEFT JOIN b2 ON t1.mid = b2.mid
    WHERE mp.mob_num < 14   
),

mob_data1 as (
select *,ROW_NUMBER() OVER (PARTITION BY mid,mob_tag,in_mob_window ORDER BY t2_issue_date DESC) AS rn
 from mob_data 
 ),


 aggregated_data AS (
    SELECT 
        mid,
        firstchannel,
        firstisreloan2,
        firstlevel,
        firstproduct,
        firstcycle,
        firstissuedate,
        firstissueweek,
        firstissuemonth,
        firstgrantamt,
        firstissueamt,
        firstproductamt,
        first_1_7_capital,
        first_2_7_capital,
        first_1_7_overdue,
        first_2_7_overdue,
        
        reloan_tag,
        channel_tag,
        is_reloan2,
        new_grade_level,
        product_type,
        user_level,
        interval_start,
        
        mob_tag,
        
        COUNT(CASE WHEN in_mob_window THEN biz_id END) AS mob_issue_cnt,
        COUNT(DISTINCT CASE WHEN in_mob_window THEN t2mid END) AS mob_issue_mid,
        SUM(CASE WHEN in_mob_window THEN issue_amount ELSE 0 END) AS mob_issue_amt,
        AVG(CASE WHEN in_mob_window THEN issue_grantcredit_amount_total END) AS mob_grant_amt_total_avg,
        MAX(CASE WHEN in_mob_window THEN issue_grantcredit_amount_total ELSE 0 END) AS mob_grant_amt_total_max,
        
        SUM(CASE WHEN in_mob_window THEN limit_usage_fz ELSE 0 END) AS limit_usage_fz,
        SUM(CASE WHEN in_mob_window THEN limit_usage_fm ELSE 0 END) AS limit_usage_fm,
        SUM(CASE WHEN in_mob_window AND rn = 1 THEN limit_occupy_fz ELSE 0 END) AS limit_occupy_fz,
        SUM(CASE WHEN in_mob_window AND rn = 1 THEN limit_occupy_fm ELSE 0 END) AS limit_occupy_fm,
        
        SUM(ovd7_p1_mob) AS ovd7_p1_mob_sum,
        SUM(due7_p1_mob) AS due7_p1_mob_sum,
        SUM(ovd7_p2_mob) AS ovd7_p2_mob_sum,
        SUM(due7_p2_mob) AS due7_p2_mob_sum
        
    FROM mob_data1
    GROUP BY 
        mid, firstchannel, firstisreloan2, firstlevel, firstproduct, firstcycle,
        firstissuedate, firstissueweek, firstissuemonth, firstgrantamt, firstissueamt,
        firstproductamt, first_1_7_capital, first_2_7_capital, first_1_7_overdue, first_2_7_overdue,
        reloan_tag, channel_tag, is_reloan2, new_grade_level, product_type, user_level,
        interval_start, mob_tag
)
 
SELECT
    a.*,
    b.exchange_rate_to_dollar,
    ROW_NUMBER() OVER (PARTITION BY mid ORDER BY 
        CASE mob_tag
            WHEN 'mob0' THEN 1
            WHEN 'mob1' THEN 2
            WHEN 'mob2' THEN 3
            WHEN 'mob3' THEN 4
            WHEN 'mob4' THEN 5
            WHEN 'mob5' THEN 6
            WHEN 'mob6' THEN 7
            WHEN 'mob7' THEN 8
            WHEN 'mob8' THEN 9
            WHEN 'mob9' THEN 10
            WHEN 'mob10' THEN 11
            WHEN 'mob11' THEN 12
            WHEN 'mob12' THEN 13
            WHEN 'mob12+' THEN 14
        END, is_reloan2) AS rn,
    a.firstissuemonth AS firstissuemonth_part  -- 添加分区列
FROM aggregated_data a
LEFT JOIN dim.dim_exchange_rate_cost b
    ON TO_CHAR(DATE(a.firstissuemonth), 'yyyymm') = b.month_id 
    AND b.account_currency = 'IDR'
-- WHERE mob_issue_cnt > 0   
ORDER BY mid, rn;





















