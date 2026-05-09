WITH 
 user_statistics AS (
    SELECT 
        firstchannel,
        firstlevel,
        firstissuemonth,
        sum(mob_issue_cnt) AS mob_issue_cnt,
        sum(mob_issue_mid) AS mob_issue_mid,

        COUNT(DISTINCT mid) AS first_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob0' THEN mid END) AS mob0_reissue_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob1' THEN mid END) AS mob1_reissue_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob2' THEN mid END) AS mob2_reissue_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob3' THEN mid END) AS mob3_reissue_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob4' THEN mid END) AS mob4_reissue_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob5' THEN mid END) AS mob5_reissue_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob6' THEN mid END) AS mob6_reissue_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob7' THEN mid END) AS mob7_reissue_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob8' THEN mid END) AS mob8_reissue_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob9' THEN mid END) AS mob9_reissue_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob10' THEN mid END) AS mob10_reissue_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob11' THEN mid END) AS mob11_reissue_user_cnt,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 AND mob_tag = 'mob12' THEN mid END) AS mob12_reissue_user_cnt,
        sum(case when mob_tag = 'mob0' then mob_issue_cnt else 0 end) AS mob0_issue_cnt_total,
        sum(case when mob_tag = 'mob1' then mob_issue_cnt else 0 end) AS mob1_issue_cnt_total,
        sum(case when mob_tag = 'mob2' then mob_issue_cnt else 0 end) AS mob2_issue_cnt_total,
        sum(case when mob_tag = 'mob3' then mob_issue_cnt else 0 end) AS mob3_issue_cnt_total,
        sum(case when mob_tag = 'mob4' then mob_issue_cnt else 0 end) AS mob4_issue_cnt_total,
        sum(case when mob_tag = 'mob5' then mob_issue_cnt else 0 end) AS mob5_issue_cnt_total,
        sum(case when mob_tag = 'mob6' then mob_issue_cnt else 0 end) AS mob6_issue_cnt_total,
        sum(case when mob_tag = 'mob7' then mob_issue_cnt else 0 end) AS mob7_issue_cnt_total,
        sum(case when mob_tag = 'mob8' then mob_issue_cnt else 0 end) AS mob8_issue_cnt_total,
        sum(case when mob_tag = 'mob9' then mob_issue_cnt else 0 end) AS mob9_issue_cnt_total,
        sum(case when mob_tag = 'mob10' then mob_issue_cnt else 0 end) AS mob10_issue_cnt_total,
        sum(case when mob_tag = 'mob11' then mob_issue_cnt else 0 end) AS mob11_issue_cnt_total,
        sum(case when mob_tag = 'mob12' then mob_issue_cnt else 0 end) AS mob12_issue_cnt_total






    FROM ind.ys_finebi_table_mob_250804
    WHERE firstissuemonth >= '2025-01-01'
     GROUP BY 1, 2, 3
),

 product_issue_statistics AS (
    SELECT 
        firstchannel,
        firstlevel,
        firstissuemonth,
        product_type,
        SUM(CASE WHEN mob_tag = 'mob0' THEN mob_issue_cnt ELSE 0 END) AS mob0_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob1' THEN mob_issue_cnt ELSE 0 END) AS mob1_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob2' THEN mob_issue_cnt ELSE 0 END) AS mob2_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob3' THEN mob_issue_cnt ELSE 0 END) AS mob3_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob4' THEN mob_issue_cnt ELSE 0 END) AS mob4_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob5' THEN mob_issue_cnt ELSE 0 END) AS mob5_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob6' THEN mob_issue_cnt ELSE 0 END) AS mob6_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob7' THEN mob_issue_cnt ELSE 0 END) AS mob7_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob8' THEN mob_issue_cnt ELSE 0 END) AS mob8_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob9' THEN mob_issue_cnt ELSE 0 END) AS mob9_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob10' THEN mob_issue_cnt ELSE 0 END) AS mob10_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob11' THEN mob_issue_cnt ELSE 0 END) AS mob11_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob12' THEN mob_issue_cnt ELSE 0 END) AS mob12_issue_cnt 

    FROM ind.ys_finebi_table_mob_250804
    WHERE mob_issue_cnt >= 1 AND firstissuemonth >= '2025-01-01'

     GROUP BY 1, 2, 3, 4
),

 product_user_statistics AS (
    SELECT 
        firstchannel,
        firstlevel,
        firstissuemonth,
        product_type,
        user_level, 

        SUM(CASE WHEN mob_tag = 'mob0' THEN mob_issue_cnt ELSE 0 END) AS mob0_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob1' THEN mob_issue_cnt ELSE 0 END) AS mob1_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob2' THEN mob_issue_cnt ELSE 0 END) AS mob2_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob3' THEN mob_issue_cnt ELSE 0 END) AS mob3_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob4' THEN mob_issue_cnt ELSE 0 END) AS mob4_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob5' THEN mob_issue_cnt ELSE 0 END) AS mob5_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob6' THEN mob_issue_cnt ELSE 0 END) AS mob6_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob7' THEN mob_issue_cnt ELSE 0 END) AS mob7_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob8' THEN mob_issue_cnt ELSE 0 END) AS mob8_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob9' THEN mob_issue_cnt ELSE 0 END) AS mob9_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob10' THEN mob_issue_cnt ELSE 0 END) AS mob10_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob11' THEN mob_issue_cnt ELSE 0 END) AS mob11_issue_cnt,
        SUM(CASE WHEN mob_tag = 'mob12' THEN mob_issue_cnt ELSE 0 END) AS mob12_issue_cnt,
 

        MAX(CASE WHEN mob_tag = 'mob0' THEN mob_grant_amt_total_max ELSE 0 END) AS mob0_grant_amt_total_max,
        MAX(CASE WHEN mob_tag = 'mob1' THEN mob_grant_amt_total_max ELSE 0 END) AS mob1_grant_amt_total_max,
        MAX(CASE WHEN mob_tag = 'mob2' THEN mob_grant_amt_total_max ELSE 0 END) AS mob2_grant_amt_total_max,
        MAX(CASE WHEN mob_tag = 'mob3' THEN mob_grant_amt_total_max ELSE 0 END) AS mob3_grant_amt_total_max,
        MAX(CASE WHEN mob_tag = 'mob4' THEN mob_grant_amt_total_max ELSE 0 END) AS mob4_grant_amt_total_max,
        MAX(CASE WHEN mob_tag = 'mob5' THEN mob_grant_amt_total_max ELSE 0 END) AS mob5_grant_amt_total_max,
        MAX(CASE WHEN mob_tag = 'mob6' THEN mob_grant_amt_total_max ELSE 0 END) AS mob6_grant_amt_total_max,
        MAX(CASE WHEN mob_tag = 'mob7' THEN mob_grant_amt_total_max ELSE 0 END) AS mob7_grant_amt_total_max,
        MAX(CASE WHEN mob_tag = 'mob8' THEN mob_grant_amt_total_max ELSE 0 END) AS mob8_grant_amt_total_max,
        MAX(CASE WHEN mob_tag = 'mob9' THEN mob_grant_amt_total_max ELSE 0 END) AS mob9_grant_amt_total_max,
        MAX(CASE WHEN mob_tag = 'mob10' THEN mob_grant_amt_total_max ELSE 0 END) AS mob10_grant_amt_total_max,
        MAX(CASE WHEN mob_tag = 'mob11' THEN mob_grant_amt_total_max ELSE 0 END) AS mob11_grant_amt_total_max,
        MAX(CASE WHEN mob_tag = 'mob12' THEN mob_grant_amt_total_max ELSE 0 END) AS mob12_grant_amt_total_max

    FROM ind.ys_finebi_table_mob_250804
    WHERE mob_issue_cnt >= 1 AND firstissuemonth >= '2025-01-01'

     GROUP BY 1, 2, 3, 4,5
)

 SELECT 
    pus.firstchannel,
    pus.firstlevel,
    pus.firstissuemonth,
    
    us.first_user_cnt,
    us.mob0_reissue_user_cnt,
    us.mob1_reissue_user_cnt,
    us.mob2_reissue_user_cnt,
    us.mob3_reissue_user_cnt,
    us.mob4_reissue_user_cnt,
    us.mob5_reissue_user_cnt,
    us.mob6_reissue_user_cnt,
    us.mob7_reissue_user_cnt,
    us.mob8_reissue_user_cnt,
    us.mob9_reissue_user_cnt,
    us.mob10_reissue_user_cnt,
    us.mob11_reissue_user_cnt,
    us.mob12_reissue_user_cnt,
    us.mob0_issue_cnt_total,
    us.mob1_issue_cnt_total,
    us.mob2_issue_cnt_total,
    us.mob3_issue_cnt_total,
    us.mob4_issue_cnt_total,
    us.mob5_issue_cnt_total,
    us.mob6_issue_cnt_total,
    us.mob7_issue_cnt_total,
    us.mob8_issue_cnt_total,
    us.mob9_issue_cnt_total,
    us.mob10_issue_cnt_total,
    us.mob11_issue_cnt_total,
    us.mob12_issue_cnt_total,




    
    pis.product_type,
    pis.mob0_issue_cnt,
    pis.mob1_issue_cnt,
    pis.mob2_issue_cnt,
    pis.mob3_issue_cnt,
    pis.mob4_issue_cnt,
    pis.mob5_issue_cnt,
    pis.mob6_issue_cnt, 
    pis.mob7_issue_cnt,
    pis.mob8_issue_cnt,
    pis.mob9_issue_cnt,
    pis.mob10_issue_cnt,
    pis.mob11_issue_cnt,
    pis.mob12_issue_cnt,
    

    
    pus.user_level,
    pus.mob0_issue_cnt AS product_user_mob0_issue_cnt,
    pus.mob1_issue_cnt AS product_user_mob1_issue_cnt,
    pus.mob2_issue_cnt AS product_user_mob2_issue_cnt,
    pus.mob3_issue_cnt AS product_user_mob3_issue_cnt,
    pus.mob4_issue_cnt AS product_user_mob4_issue_cnt,
    pus.mob5_issue_cnt AS product_user_mob5_issue_cnt,
    pus.mob6_issue_cnt AS product_user_mob6_issue_cnt,
    pus.mob7_issue_cnt AS product_user_mob7_issue_cnt,
    pus.mob8_issue_cnt AS product_user_mob8_issue_cnt,
    pus.mob9_issue_cnt AS product_user_mob9_issue_cnt,
    pus.mob10_issue_cnt AS product_user_mob10_issue_cnt,
    pus.mob11_issue_cnt AS product_user_mob11_issue_cnt,
    pus.mob12_issue_cnt AS product_user_mob12_issue_cnt,

    
    pus.mob0_grant_amt_total_max,
    pus.mob1_grant_amt_total_max,
    pus.mob2_grant_amt_total_max,
    pus.mob3_grant_amt_total_max,
    pus.mob4_grant_amt_total_max,
    pus.mob5_grant_amt_total_max,
    pus.mob6_grant_amt_total_max,
    pus.mob7_grant_amt_total_max,
    pus.mob8_grant_amt_total_max,
    pus.mob9_grant_amt_total_max,
    pus.mob10_grant_amt_total_max,
    pus.mob11_grant_amt_total_max,
    pus.mob12_grant_amt_total_max, 
    case when us.mob0_issue_cnt_total > 0 then pis.mob0_issue_cnt*1.0000/us.mob0_issue_cnt_total else 0 end as prodtuct_mob0_issue_cnt_bili,
    case when us.mob1_issue_cnt_total > 0 then pis.mob1_issue_cnt*1.0000/us.mob1_issue_cnt_total else 0 end as prodtuct_mob1_issue_cnt_bili,
    case when us.mob2_issue_cnt_total > 0 then pis.mob2_issue_cnt*1.0000/us.mob2_issue_cnt_total else 0 end as prodtuct_mob2_issue_cnt_bili,
    case when us.mob3_issue_cnt_total > 0 then pis.mob3_issue_cnt*1.0000/us.mob3_issue_cnt_total else 0 end as prodtuct_mob3_issue_cnt_bili,
    case when us.mob4_issue_cnt_total > 0 then pis.mob4_issue_cnt*1.0000/us.mob4_issue_cnt_total else 0 end as prodtuct_mob4_issue_cnt_bili,
    case when us.mob5_issue_cnt_total > 0 then pis.mob5_issue_cnt*1.0000/us.mob5_issue_cnt_total else 0 end as prodtuct_mob5_issue_cnt_bili,
    case when us.mob6_issue_cnt_total > 0 then pis.mob6_issue_cnt*1.0000/us.mob6_issue_cnt_total else 0 end as prodtuct_mob6_issue_cnt_bili,
    case when us.mob7_issue_cnt_total > 0 then pis.mob7_issue_cnt*1.0000/us.mob7_issue_cnt_total else 0 end as prodtuct_mob7_issue_cnt_bili,
    case when us.mob8_issue_cnt_total > 0 then pis.mob8_issue_cnt*1.0000/us.mob8_issue_cnt_total else 0 end as prodtuct_mob8_issue_cnt_bili,
    case when us.mob9_issue_cnt_total > 0 then pis.mob9_issue_cnt*1.0000/us.mob9_issue_cnt_total else 0 end as prodtuct_mob9_issue_cnt_bili,
    case when us.mob10_issue_cnt_total > 0 then pis.mob10_issue_cnt*1.0000/us.mob10_issue_cnt_total else 0 end as prodtuct_mob10_issue_cnt_bili,
    case when us.mob11_issue_cnt_total > 0 then pis.mob11_issue_cnt*1.0000/us.mob11_issue_cnt_total else 0 end as prodtuct_mob11_issue_cnt_bili,
    case when us.mob12_issue_cnt_total > 0 then pis.mob12_issue_cnt*1.0000/us.mob12_issue_cnt_total else 0 end as prodtuct_mob12_issue_cnt_bili,

    case when us.mob0_issue_cnt_total > 0 then pus.mob0_issue_cnt*1.0000/us.mob0_issue_cnt_total else 0 end as prodtuct_user_mob0_issue_cnt_bili,
    case when us.mob1_issue_cnt_total > 0 then pus.mob1_issue_cnt*1.0000/us.mob1_issue_cnt_total else 0 end as prodtuct_user_mob1_issue_cnt_bili,
    case when us.mob2_issue_cnt_total > 0 then pus.mob2_issue_cnt*1.0000/us.mob2_issue_cnt_total else 0 end as prodtuct_user_mob2_issue_cnt_bili,
    case when us.mob3_issue_cnt_total > 0 then pus.mob3_issue_cnt*1.0000/us.mob3_issue_cnt_total else 0 end as prodtuct_user_mob3_issue_cnt_bili,
    case when us.mob4_issue_cnt_total > 0 then pus.mob4_issue_cnt*1.0000/us.mob4_issue_cnt_total else 0 end as prodtuct_user_mob4_issue_cnt_bili,
    case when us.mob5_issue_cnt_total > 0 then pus.mob5_issue_cnt*1.0000/us.mob5_issue_cnt_total else 0 end as prodtuct_user_mob5_issue_cnt_bili,
    case when us.mob6_issue_cnt_total > 0 then pus.mob6_issue_cnt*1.0000/us.mob6_issue_cnt_total else 0 end as prodtuct_user_mob6_issue_cnt_bili,
    case when us.mob7_issue_cnt_total > 0 then pus.mob7_issue_cnt*1.0000/us.mob7_issue_cnt_total else 0 end as prodtuct_user_mob7_issue_cnt_bili,
    case when us.mob8_issue_cnt_total > 0 then pus.mob8_issue_cnt*1.0000/us.mob8_issue_cnt_total else 0 end as prodtuct_user_mob8_issue_cnt_bili,
    case when us.mob9_issue_cnt_total > 0 then pus.mob9_issue_cnt*1.0000/us.mob9_issue_cnt_total else 0 end as prodtuct_user_mob9_issue_cnt_bili,
    case when us.mob10_issue_cnt_total > 0 then pus.mob10_issue_cnt*1.0000/us.mob10_issue_cnt_total else 0 end as prodtuct_user_mob10_issue_cnt_bili,
    case when us.mob11_issue_cnt_total > 0 then pus.mob11_issue_cnt*1.0000/us.mob11_issue_cnt_total else 0 end as prodtuct_user_mob11_issue_cnt_bili,
    case when us.mob12_issue_cnt_total > 0 then pus.mob12_issue_cnt*1.0000/us.mob12_issue_cnt_total else 0 end as prodtuct_user_mob12_issue_cnt_bili
 


 
FROM product_user_statistics pus 
LEFT JOIN product_issue_statistics pis 
    ON pus.firstchannel = pis.firstchannel
    AND pus.firstlevel = pis.firstlevel
    AND pus.firstissuemonth = pis.firstissuemonth
    AND pus.product_type = pis.product_type 
LEFT JOIN user_statistics us 
    ON pus.firstchannel = us.firstchannel
    AND pus.firstlevel = us.firstlevel
    AND pus.firstissuemonth = us.firstissuemonth

 ORDER BY pus.firstchannel, pus.firstlevel, pus.firstissuemonth, pis.product_type, pus.user_level;

 