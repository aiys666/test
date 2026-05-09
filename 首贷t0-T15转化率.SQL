WITH confirm_metrics AS ( 
    SELECT  
        date_format(date(app_date),'%Y-%m-01') as app_month, 
        product_level_type_old,new_grade_level,
        SUM(if_in_confirm_final) AS apply_grantcredit_amount,
         
        SUM(if_confirm_passed_num_t0) AS confirm_passed_t0,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 1 THEN 1 ELSE 0 END) AS confirm_passed_t1,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 2 THEN 1 ELSE 0 END) AS confirm_passed_t2,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 3 THEN 1 ELSE 0 END) AS confirm_passed_t3,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 4 THEN 1 ELSE 0 END) AS confirm_passed_t4,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 5 THEN 1 ELSE 0 END) AS confirm_passed_t5,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 6 THEN 1 ELSE 0 END) AS confirm_passed_t6,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 7 THEN 1 ELSE 0 END) AS confirm_passed_t7,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 8 THEN 1 ELSE 0 END) AS confirm_passed_t8,  
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 9 THEN 1 ELSE 0 END) AS confirm_passed_t9,    
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 10 THEN 1 ELSE 0 END) AS confirm_passed_t10,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 11 THEN 1 ELSE 0 END) AS confirm_passed_t11,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 12 THEN 1 ELSE 0 END) AS confirm_passed_t12,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 13 THEN 1 ELSE 0 END) AS confirm_passed_t13,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 14 THEN 1 ELSE 0 END) AS confirm_passed_t14,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 15 THEN 1 ELSE 0 END) AS confirm_passed_t15 
    FROM ind.ba_asset_base_info
    WHERE if_in_confirm_final > 0   
    and app_date>='2025-01-01'
    and grant_strategy='NEW'
    GROUP BY 1,2,3


)

SELECT   
    app_month,  
    product_tag,product_tag_detail,new_grade_level,is_reloan2,

    ROUND(confirm_passed_t0 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t0,
    ROUND(confirm_passed_t1 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t1,
    ROUND(confirm_passed_t2 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t2,
    ROUND(confirm_passed_t3 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t3,
    ROUND(confirm_passed_t4 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t4,
    ROUND(confirm_passed_t5 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t5,
    ROUND(confirm_passed_t6 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t6,
    ROUND(confirm_passed_t7 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t7,
    ROUND(confirm_passed_t8 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t8,
    ROUND(confirm_passed_t9 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t9,
    ROUND(confirm_passed_t10 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t10,
    ROUND(confirm_passed_t11 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t11,
    ROUND(confirm_passed_t12 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t12,
    ROUND(confirm_passed_t13 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t13,
    ROUND(confirm_passed_t14 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t14,
    ROUND(confirm_passed_t15 * 1.0000 / total_if_in_confirm_final, 4) confirm_rate_t15


FROM confirm_metrics
ORDER BY  1,2,3,4,5






    SELECT  
        a.app_week,
        a.app_month,
        product_level_type_old,new_grade_level,
        SUM(apply_grantcredit_amount) AS apply_grantcredit_amount, 
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) = 0 THEN  apply_amount ELSE 0 END) AS confirm_passed_t0,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 1 THEN  apply_amount ELSE 0 END) AS confirm_passed_t1,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 2 THEN  apply_amount ELSE 0 END) AS confirm_passed_t2,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 3 THEN  apply_amount ELSE 0 END) AS confirm_passed_t3,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 4 THEN  apply_amount ELSE 0 END) AS confirm_passed_t4,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 5 THEN  apply_amount ELSE 0 END) AS confirm_passed_t5,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 6 THEN  apply_amount ELSE 0 END) AS confirm_passed_t6,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 7 THEN  apply_amount ELSE 0 END) AS confirm_passed_t7,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 8 THEN  apply_amount ELSE 0 END) AS confirm_passed_t8,  
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 9 THEN  apply_amount ELSE 0 END) AS confirm_passed_t9,    
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 10 THEN apply_amount ELSE 0 END) AS confirm_passed_t10,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 11 THEN apply_amount ELSE 0 END) AS confirm_passed_t11,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 12 THEN apply_amount ELSE 0 END) AS confirm_passed_t12,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 13 THEN apply_amount ELSE 0 END) AS confirm_passed_t13,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 14 THEN apply_amount ELSE 0 END) AS confirm_passed_t14,
        SUM(CASE WHEN date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 15 THEN apply_amount ELSE 0 END) AS confirm_passed_t15 
    FROM ind.ba_asset_base_info a
    WHERE if_in_confirm_final > 0   
    and app_date>='2025-01-01'
    and grant_strategy='NEW'
    and if_confirm_passed_final= 1 
    GROUP BY 1,2,3,4



 


 


 



 select  
--  date_format(date(t1.app_date),'%Y-%m-01') as app_month, 
 t1.app_month,
 t1.product_level_type_old,
 t1.new_grade_level,
 t1.delay_days,
 t1.confirm_cnt,
 SUM(confirm_cnt) OVER (PARTITION BY t1.app_month, t1.product_level_type_old, t1.new_grade_level ORDER BY t1.delay_days) as cumulative_confirm_cnt,
 t2.confirm_cnt_all
FROM (
 SELECT  
        -- date(app_date) as app_date,
        date_format(date(app_date),'%Y-%m-01') as app_month, 
        product_level_type_old,
        new_grade_level,
        date_diff('day', date(app_date), date(confirm_date_final)) as delay_days,
        count(distinct biz_id) as confirm_cnt 
    FROM ind.ba_asset_base_info
    WHERE if_in_confirm_final > 0   
    and app_date>='2025-01-01'
    and grant_strategy='NEW'
    and date_diff('day', date(app_date), date(confirm_date_final)) between 0 and 15
     GROUP BY 1,2,3,4
 ) t1 
 left join (

     SELECT  
    --  date(app_date) as app_date,
     date_format(date(app_date),'%Y-%m-01') as app_month, 
        product_level_type_old,
        new_grade_level, 
        count(distinct biz_id) as confirm_cnt_all 
    FROM ind.ba_asset_base_info
    WHERE if_in_confirm_final > 0   
    and app_date>='2025-01-01'
    and grant_strategy='NEW' 
    GROUP BY 1,2,3
 ) t2 on t1.app_month=t2.app_month and t1.product_level_type_old=t2.product_level_type_old and t1.new_grade_level=t2.new_grade_level
 










 WITH confirmed_data AS (
    SELECT  
        date_format(date(app_date), '%Y-%m-01') as app_month, 
        product_level_type_old,
        new_grade_level,
        date_diff('day', date(app_date), date(confirm_date_final)) as delay_days,
        count(distinct biz_id) as confirm_cnt
    FROM ind.ba_asset_base_info
    WHERE if_in_confirm_final > 0   
    AND app_date >= '2025-01-01'
    AND grant_strategy = 'NEW'
    AND date_diff('day', date(app_date), date(confirm_date_final)) BETWEEN 0 AND 15
    GROUP BY 1, 2, 3, 4
),
total_counts AS (
    SELECT
        app_month,
        product_level_type_old,
        new_grade_level,
        SUM(confirm_cnt) as confirm_cnt_all
    FROM confirmed_data
    GROUP BY 1, 2, 3
),
distinct_groups AS (
    SELECT DISTINCT
        app_month,
        product_level_type_old,
        new_grade_level
    FROM confirmed_data
),
delay_series AS (
    SELECT * FROM (VALUES (0), (1), (2), (3), (4), (5), (6), (7), (8), (9), (10), (11), (12), (13), (14), (15)) AS t(delay_day)
)
SELECT 
    dg.app_month,
    dg.product_level_type_old,
    dg.new_grade_level,
    ds.delay_day as delay_days,
    COALESCE(cd.confirm_cnt, 0) as confirm_cnt,
    SUM(COALESCE(cd.confirm_cnt, 0)) OVER (
        PARTITION BY dg.app_month, dg.product_level_type_old, dg.new_grade_level 
        ORDER BY ds.delay_day 
        ROWS UNBOUNDED PRECEDING
    ) AS cumulative_confirm_cnt,
    tc.confirm_cnt_all
FROM distinct_groups dg
CROSS JOIN delay_series ds
LEFT JOIN confirmed_data cd 
    ON dg.app_month = cd.app_month 
    AND dg.product_level_type_old = cd.product_level_type_old 
    AND dg.new_grade_level = cd.new_grade_level 
    AND ds.delay_day = cd.delay_days
LEFT JOIN total_counts tc
    ON dg.app_month = tc.app_month 
    AND dg.product_level_type_old = tc.product_level_type_old 
    AND dg.new_grade_level = tc.new_grade_level
ORDER BY dg.app_month, dg.product_level_type_old, dg.new_grade_level, ds.delay_day;



















 WITH confirmed_data AS (
    SELECT  
        date_format(date(create_time), '%Y-%m-01') as app_month, 
        product_level_type_old,
        grant_strategy,
        new_grade_level,
        case when reloan_num>=5 then '5+' else cast(reloan_num as varchar) end as reloan_num,
        date_diff('day', date(create_time), date(confirm_date_final)) as delay_days,
        count(distinct biz_id) as confirm_cnt
    FROM ind.ba_asset_base_info
    WHERE if_in_confirm_temp > 0   
    AND create_time >= date'2025-01-01'
    AND grant_strategy = 'NEW'
    AND date_diff('day', date(create_time), date(confirm_date_final)) BETWEEN 0 AND 15
    GROUP BY 1, 2, 3, 4, 5, 6

),
total_counts AS (
    SELECT
        date_format(date(create_time), '%Y-%m-01') as app_month, 
        grant_strategy,
        product_level_type_old,
        new_grade_level,
        case when reloan_num>=5 then '5+' else cast(reloan_num as varchar) end as reloan_num,
        count(distinct biz_id) as confirm_cnt_all
    FROM ind.ba_asset_base_info
    WHERE if_in_confirm_temp > 0   
    AND create_time >= date'2025-01-01' 

    GROUP BY 1, 2, 3, 4, 5


),
distinct_groups AS (
    SELECT DISTINCT
        app_month,
        product_level_type_old,
        new_grade_level,
        reloan_num,
        grant_strategy
    FROM total_counts
),
delay_series AS (
    SELECT * FROM (VALUES (0), (1), (2), (3), (4), (5), (6), (7), (8), (9), (10), (11), (12), (13), (14), (15)) AS t(delay_day)
)
SELECT 
    dg.app_month,
    dg.product_level_type_old,
    dg.new_grade_level,
    dg.reloan_num,
    dg.grant_strategy,
    ds.delay_day as delay_days,
    COALESCE(cd.confirm_cnt, 0) as confirm_cnt,
    SUM(COALESCE(cd.confirm_cnt, 0)) OVER (
        PARTITION BY dg.app_month, dg.product_level_type_old, dg.new_grade_level, dg.reloan_num, dg.grant_strategy

        ORDER BY ds.delay_day 
        ROWS UNBOUNDED PRECEDING
    ) AS cumulative_confirm_cnt,
    tc.confirm_cnt_all
FROM distinct_groups dg
CROSS JOIN delay_series ds
LEFT JOIN confirmed_data cd 
    ON dg.app_month = cd.app_month 
    AND dg.product_level_type_old = cd.product_level_type_old 
    AND dg.new_grade_level = cd.new_grade_level 
    AND ds.delay_day = cd.delay_days
    AND dg.reloan_num = cd.reloan_num
    AND dg.grant_strategy = cd.grant_strategy

LEFT JOIN total_counts tc
    ON dg.app_month = tc.app_month 
    AND dg.product_level_type_old = tc.product_level_type_old 
    AND dg.new_grade_level = tc.new_grade_level
    AND dg.reloan_num = tc.reloan_num
    AND dg.grant_strategy = tc.grant_strategy

ORDER BY 1,2,3,4,5,6




 




 -- 20250926 添加复贷
 
 WITH confirmed_data AS (
    SELECT  
        date_format(date(create_time), '%Y-%m-01') as app_month, 
        product_level_type_old,
        grant_strategy,
        new_grade_level,
        case when reloan_num>=5 then '5+' else cast(reloan_num as varchar) end as reloan_num,
        date_diff('day', date(create_time), date(confirm_date_final)) as delay_days,
        count(distinct biz_id) as confirm_cnt
    FROM ind.ba_asset_base_info
    WHERE if_in_confirm_temp > 0   
    AND create_time >= date'2025-01-01'
    AND grant_strategy = 'NEW'
    AND date_diff('day', date(create_time), date(confirm_date_final)) BETWEEN 0 AND 15
    GROUP BY 1, 2, 3, 4, 5, 6

),
total_counts AS (
    SELECT
        date_format(date(create_time), '%Y-%m-01') as app_month, 
        grant_strategy,
        product_level_type_old,
        new_grade_level,
        case when reloan_num>=5 then '5+' else cast(reloan_num as varchar) end as reloan_num,
        count(distinct biz_id) as confirm_cnt_all
    FROM ind.ba_asset_base_info
    WHERE if_in_confirm_temp > 0   
    AND create_time >= date'2025-01-01' 

    GROUP BY 1, 2, 3, 4, 5


),
distinct_groups AS (
    SELECT DISTINCT
        app_month,
        product_level_type_old,
        new_grade_level,
        reloan_num,
        grant_strategy
    FROM total_counts
),
delay_series AS (
    SELECT * FROM (VALUES (0), (1), (2), (3), (4), (5), (6), (7), (8), (9), (10), (11), (12), (13), (14), (15)) AS t(delay_day)
)
SELECT 
    dg.app_month,
    dg.product_level_type_old,
    dg.new_grade_level,
    dg.reloan_num,
    dg.grant_strategy,
    ds.delay_day as delay_days,
    COALESCE(cd.confirm_cnt, 0) as confirm_cnt,
    SUM(COALESCE(cd.confirm_cnt, 0)) OVER (
        PARTITION BY dg.app_month, dg.product_level_type_old, dg.new_grade_level, dg.reloan_num, dg.grant_strategy

        ORDER BY ds.delay_day 
        ROWS UNBOUNDED PRECEDING
    ) AS cumulative_confirm_cnt,
    tc.confirm_cnt_all
FROM distinct_groups dg
CROSS JOIN delay_series ds
LEFT JOIN confirmed_data cd 
    ON dg.app_month = cd.app_month 
    AND dg.product_level_type_old = cd.product_level_type_old 
    AND dg.new_grade_level = cd.new_grade_level 
    AND ds.delay_day = cd.delay_days
    AND dg.reloan_num = cd.reloan_num
    AND dg.grant_strategy = cd.grant_strategy

LEFT JOIN total_counts tc
    ON dg.app_month = tc.app_month 
    AND dg.product_level_type_old = tc.product_level_type_old 
    AND dg.new_grade_level = tc.new_grade_level
    AND dg.reloan_num = tc.reloan_num
    AND dg.grant_strategy = tc.grant_strategy

ORDER BY 1,2,3,4,5,6;




        count(distinct case when loan_type2='loop' then cast(id as varchar) else biz_id end ) as confirm_cnt,


-- 这里的一些资产，应该是IOS的，但是标签打的是OTHER
SELECT 
date_format(date(create_time), '%Y-%m-01')  AS create_week,count(1)
   FROM ind.xly_application_funnel a
    where  create_time>=date'2025-01-01' 
and  a.loan_type2 = 'normal'  
and biz_id is null
and source_channel2 NOT IN ('IOS') AND app_version <= '2.1.4'
group by 1


SELECT *
   FROM ind.xly_application_funnel a
    where  create_time>=date'2025-01-01' 
and  a.loan_type2 = 'normal'  
and biz_id is null
and source_channel2 NOT IN ('IOS') AND app_version <= '2.1.4'