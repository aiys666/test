WITH confirm_metrics AS ( 
    SELECT  
        a.app_week,
        a.app_month,
        product_tag,product_tag_detail,new_grade_level,is_reloan2,
        SUM(CASE WHEN if_confirm_passed_final = 1 THEN apply_grantcredit_amount ELSE 0 END) AS apply_grantcredit_amount, 

        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) = 0 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t0,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 1 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t1,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 2 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t2,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 3 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t3,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 4 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t4,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 5 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t5,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 6 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t6,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 7 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t7,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 8 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t8,  
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 9 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t9,    
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 10 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t10,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 11 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t11,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 12 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t12,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 13 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t13,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 14 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t14,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 15 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t15 
    FROM ind.ba_asset_base_info a
    WHERE if_in_confirm_final > 0   
    and app_date>='2025-01-01'
    and grant_strategy='NEW'
    and if_confirm_passed_final= 1 
    GROUP BY 1,2,3,4,5,6
 

)

-- SELECT   
--     app_week,
--     app_month,  
--     product_tag,product_tag_detail,new_grade_level,is_reloan2,

--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t0 * 1.0000 / apply_grantcredit_amount, 4) end t0,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t1 * 1.0000 / apply_grantcredit_amount, 4) end t1,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t2 * 1.0000 / apply_grantcredit_amount, 4) end t2,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t3 * 1.0000 / apply_grantcredit_amount, 4) end t3,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t4 * 1.0000 / apply_grantcredit_amount, 4) end t4,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t5 * 1.0000 / apply_grantcredit_amount, 4) end t5,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t6 * 1.0000 / apply_grantcredit_amount, 4) end t6,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t7 * 1.0000 / apply_grantcredit_amount, 4) end t7,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t8 * 1.0000 / apply_grantcredit_amount, 4) end t8,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t9 * 1.0000 / apply_grantcredit_amount, 4) end t9,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t10 * 1.0000 / apply_grantcredit_amount, 4) end t10,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t11 * 1.0000 / apply_grantcredit_amount, 4) end t11,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t12 * 1.0000 / apply_grantcredit_amount, 4) end t12,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t13 * 1.0000 / apply_grantcredit_amount, 4) end t13,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t14 * 1.0000 / apply_grantcredit_amount, 4) end t14,
--     case when apply_grantcredit_amount=0 then 0 else ROUND(confirm_passed_t15 * 1.0000 / apply_grantcredit_amount, 4) end t15
-- FROM confirm_metrics
-- ORDER BY  1,2,3,4,5







 

drop table if exists ind.confirm_metrics_t0_t15;
create table if not exists ind.confirm_metrics_t0_t15 as 

 SELECT  
        date_format(date(app_date),'%Y-%m-01') as app_month, 
        product_level_type_old,new_grade_level,
        SUM(if_in_confirm_final) AS if_confirm_cnt,
        SUM(if_confirm_passed_num_t0) AS confirm_cnt_passed_t0,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 1 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t1,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 2 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t2,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 3 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t3,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 4 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t4,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 5 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t5,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 6 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t6,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 7 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t7,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 8 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t8,  
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 9 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t9,    
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 10 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t10,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 11 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t11,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 12 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t12,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 13 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t13,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 14 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t14,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 15 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t15,
        SUM(CASE WHEN if_confirm_passed_final = 1 THEN apply_grantcredit_amount ELSE 0 END) AS apply_grantcredit_amount, 
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) = 0 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t0,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 1 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t1,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 2 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t2,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 3 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t3,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 4 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t4,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 5 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t5,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 6 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t6,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 7 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t7,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 8 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t8,  
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 9 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t9,    
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 10 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t10,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 11 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t11,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 12 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t12,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 13 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t13,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 14 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t14,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 15 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t15 
    FROM ind.ba_asset_base_info
    WHERE if_in_confirm_final > 0   
    and app_date>='2025-01-01'
    and grant_strategy='NEW'
    GROUP BY 1,2,3










    ,
        SUM(if_confirm_passed_num_t0) AS confirm_cnt_passed_t0,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 1 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t1,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 2 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t2,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 3 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t3,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 4 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t4,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 5 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t5,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 6 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t6,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 7 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t7,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 8 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t8,  
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 9 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t9,    
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 10 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t10,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 11 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t11,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 12 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t12,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 13 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t13,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 14 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t14,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 15 THEN 1 ELSE 0 END) AS confirm_cnt_passed_t15,
        SUM(CASE WHEN if_confirm_passed_final = 1 THEN apply_grantcredit_amount ELSE 0 END) AS apply_grantcredit_amount, 
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) = 0 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t0,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 1 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t1,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 2 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t2,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 3 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t3,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 4 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t4,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 5 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t5,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 6 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t6,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 7 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t7,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 8 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t8,  
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 9 THEN  apply_amount ELSE 0 END) AS confirm_amt_passed_t9,    
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 10 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t10,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 11 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t11,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 12 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t12,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 13 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t13,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 14 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t14,
        SUM(CASE WHEN if_confirm_passed_final = 1 AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 15 THEN apply_amount ELSE 0 END) AS confirm_amt_passed_t15 
   

    SELECT  
        app_month, 
        product_level_type_old,new_grade_level, 
        'cnt' as sum_type,
        'T' as confirm_type,
        SUM(if_confirm_passed_num_t0) AS confirm_value
   FROM ind.confirm_metrics_t0_t15
    WHERE if_in_confirm_final > 0   
    and app_date>='2025-01-01'
    and grant_strategy='NEW'
    GROUP BY 1,2,3,4,5
    union all 
    SELECT  
        date_format(date(app_date),'%Y-%m-01') as app_month, 
        product_level_type_old,new_grade_level, 
        'cnt' as sum_type,
        'T0' as confirm_type,
        SUM(if_in_confirm_final) AS confirm_value
   FROM ind.ba_asset_base_info
    WHERE if_in_confirm_final > 0   
    and app_date>='2025-01-01'
    and grant_strategy='NEW'
    GROUP BY 1,2,3,4,5