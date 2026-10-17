-- ============================================================
-- 墨西哥 LTV 复购分析 · 月度MOB（CTE版，不建表不删表）
-- 直接在盘古/notebook 跑这个查询即可拿到结果
-- ============================================================

WITH

-- ① 首贷用户月度明细
shou_detail AS (
    SELECT DISTINCT
        date_trunc('month', date(t1.release_time)) AS dt_month
        ,t1.app_channel
        ,ms.media_source
        ,sl.product_name
        ,t1.customer_id
        ,t1.camera_id
        ,t1.contract_amount
        ,t2.exchange_rate_to_dollar
    FROM ods.s02_loan t1
    LEFT JOIN dim.dim_exchange_rate_cost t2 
        ON to_char(date(release_time),'yyyymm') = t2.month_id 
        AND t2.account_currency = 'MXN'
    INNER JOIN (SELECT * FROM mx.risk_double_loan_tag WHERE double_loan = 0) rt 
        ON CAST(t1.camera_id AS bigint) = CAST(rt.biz_id AS bigint)
    LEFT JOIN (SELECT * FROM mx.gm_ltv_model_shou_user_layer) sl 
        ON sl.camera_id = t1.camera_id
    LEFT JOIN (SELECT * FROM mx.gm_ltv_shou_user_media_source) ms 
        ON ms.camera_id = t1.camera_id
    WHERE date(release_time) >= date('2023-03-01') 
      AND state IN (1,2,3)
),

-- ② 复贷用户月度明细
fu_detail AS (
    SELECT DISTINCT 
        date_trunc('month', date(t1.release_time)) AS dt_month
        ,t1.customer_id
        ,t1.camera_id
        ,sl.product_name
        ,t1.app_channel
        ,t1.contract_amount
    FROM ods.s02_loan t1
    INNER JOIN (SELECT * FROM mx.risk_double_loan_tag WHERE double_loan = 1) rt 
        ON CAST(t1.camera_id AS bigint) = CAST(rt.biz_id AS bigint)
    LEFT JOIN (SELECT * FROM mx.gm_ltv_model_shou_user_layer) sl 
        ON sl.camera_id = t1.camera_id
    WHERE date(release_time) >= date('2023-03-01') 
      AND state IN (1,2,3)
),

-- ③ 首复贷关联 + MOB
shou_fu AS (
    SELECT 
        a.dt_month         AS shou_month
        ,a.app_channel
        ,a.product_name    AS shou_product
        ,a.customer_id
        ,a.contract_amount
        ,a.exchange_rate_to_dollar
        ,a.media_source
        ,b.dt_month        AS fu_month
        ,b.camera_id
        ,b.product_name    AS fu_product
        ,b.contract_amount AS fu_contract_amount
        ,date_diff('month', a.dt_month, b.dt_month) AS mob
    FROM shou_detail a
    LEFT JOIN fu_detail b 
        ON a.customer_id = b.customer_id 
        AND a.app_channel = b.app_channel
),

-- ④ MOB枚举（补全首贷月没有复贷的mob行，保证分母完整）
mob_enum AS (
    SELECT DISTINCT shou_month, mob 
    FROM shou_fu
),

-- ⑤ 首贷聚合（按首贷月+MOB枚举笛卡尔积）
shou_agg AS (
    SELECT 
        a.dt_month       AS shou_month
        ,a.app_channel
        ,a.product_name
        ,a.media_source
        ,b.mob
        ,COUNT(DISTINCT a.customer_id) AS shou_cnt
        ,SUM(a.contract_amount)        AS shou_contract_amt
    FROM shou_detail a
    LEFT JOIN mob_enum b ON a.dt_month = b.shou_month
    GROUP BY 1,2,3,4,5
),

-- ⑥ 复贷聚合（按首贷月+MOB聚合）
fu_agg AS (
    SELECT 
        shou_month
        ,mob
        ,fu_month
        ,app_channel
        ,shou_product
        ,media_source
        ,COUNT(DISTINCT camera_id) AS fu_camera_cnt
        ,SUM(fu_contract_amount)    AS fu_camera_amt
    FROM shou_fu
    GROUP BY 1,2,3,4,5,6
)

-- ⑦ 最终结果：月度复借率（MOB维度）
SELECT 
    a.shou_month
    ,a.mob
    ,b.fu_month
    ,a.app_channel
    ,a.product_name
    ,a.media_source
    ,a.shou_cnt             AS shou_cnt
    ,a.shou_contract_amt    AS shou_contract_amt
    ,COALESCE(b.fu_camera_cnt, 0)  AS fu_camera_cnt
    ,COALESCE(b.fu_camera_amt, 0)  AS fu_camera_amt
FROM shou_agg a
LEFT JOIN fu_agg b 
    ON a.shou_month = b.shou_month 
    AND a.app_channel = b.app_channel 
    AND a.product_name = b.shou_product 
    AND a.media_source = b.media_source 
    AND a.mob = b.mob
ORDER BY a.shou_month, a.mob, a.app_channel, a.product_name, a.media_source
