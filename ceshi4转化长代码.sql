WITH 
-- 基础数据查询，获取所有需要的原始数据
base_data AS (
    SELECT 
        firstchannel,
        firstlevel,
        firstissuemonth,
        product_type,
        user_level,
        mid,
        mob_tag,
        mob_issue_cnt,
        mob_issue_mid,
        mob_grant_amt_total_max
    FROM ind.ys_finebi_table_mob_250804
),

-- 用户统计（长表格式）
user_statistics_long AS (
    -- 基础统计
    SELECT 
        firstchannel,
        firstlevel,
        firstissuemonth,
        NULL AS product_type,
        NULL AS user_level,
        'mob_issue_cnt' AS metric_type,
        NULL AS mob_tag,
        SUM(mob_issue_cnt) AS metric_value
    FROM base_data
    GROUP BY 1, 2, 3
    
    UNION ALL
    
    SELECT 
        firstchannel,
        firstlevel,
        firstissuemonth,
        NULL AS product_type,
        NULL AS user_level,
        'mob_issue_mid' AS metric_type,
        NULL AS mob_tag,
        SUM(mob_issue_mid) AS metric_value
    FROM base_data
    GROUP BY 1, 2, 3
    
    UNION ALL
    
    SELECT 
        firstchannel,
        firstlevel,
        firstissuemonth,
        NULL AS product_type,
        NULL AS user_level,
        'first_user_cnt' AS metric_type,
        NULL AS mob_tag,
        COUNT(DISTINCT mid) AS metric_value
    FROM base_data
    GROUP BY 1, 2, 3
    
    UNION ALL
    
    -- 分mob_tag的重发用户统计
    SELECT 
        firstchannel,
        firstlevel,
        firstissuemonth,
        NULL AS product_type,
        NULL AS user_level,
        'reissue_user_cnt' AS metric_type,
        mob_tag,
        COUNT(DISTINCT CASE WHEN mob_issue_cnt >= 1 THEN mid END) AS metric_value
    FROM base_data
    GROUP BY 1, 2, 3, 6
    
    UNION ALL
    
    -- 分mob_tag的总发单量统计
    SELECT 
        firstchannel,
        firstlevel,
        firstissuemonth,
        NULL AS product_type,
        NULL AS user_level,
        'issue_cnt_total' AS metric_type,
        mob_tag,
        SUM(mob_issue_cnt) AS metric_value
    FROM base_data
    GROUP BY 1, 2, 3, 6
),

-- 产品发单统计（长表格式）
product_issue_statistics_long AS (
    SELECT 
        firstchannel,
        firstlevel,
        firstissuemonth,
        product_type,
        NULL AS user_level,
        'issue_cnt' AS metric_type,
        mob_tag,
        SUM(mob_issue_cnt) AS metric_value
    FROM base_data
    WHERE mob_issue_cnt >= 1
    GROUP BY 1, 2, 3, 4, 6
),

-- 产品用户统计（长表格式）
product_user_statistics_long AS (
    SELECT 
        firstchannel,
        firstlevel,
        firstissuemonth,
        product_type,
        user_level,
        'issue_cnt' AS metric_type,
        mob_tag,
        SUM(mob_issue_cnt) AS metric_value
    FROM base_data
    WHERE mob_issue_cnt >= 1
    GROUP BY 1, 2, 3, 4, 5, 6
    
    UNION ALL
    
    SELECT 
        firstchannel,
        firstlevel,
        firstissuemonth,
        product_type,
        user_level,
        'grant_amt_total_max' AS metric_type,
        mob_tag,
        MAX(mob_grant_amt_total_max) AS metric_value
    FROM base_data
    WHERE mob_issue_cnt >= 1
    GROUP BY 1, 2, 3, 4, 5, 6
),

-- 合并所有统计结果
combined_statistics AS (
    SELECT * FROM user_statistics_long
    UNION ALL
    SELECT * FROM product_issue_statistics_long
    UNION ALL
    SELECT * FROM product_user_statistics_long
)

-- 最终查询
SELECT 
    firstchannel,
    firstlevel,
    firstissuemonth,
    product_type,
    user_level,
    metric_type,
    mob_tag,
    metric_value
FROM combined_statistics
ORDER BY 
    firstchannel,
    firstlevel,
    firstissuemonth,
    product_type,
    user_level,
    metric_type,
    mob_tag;

 