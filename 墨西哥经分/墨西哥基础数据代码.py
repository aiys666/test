

-- 跑业绩、件均、期限、息费率、砍头比例等指标
SELECT
    DATE(release_time)                        AS data_date 
  , COUNT(1)                                  AS loan_cnt       -- 放款笔数
  , SUM(contract_amount)                       AS contract_amt    -- 合同金额
  , SUM(amount)                               AS actual_amt      -- 实放金额
  , SUM(fee_amount + interest)                 AS total_fee       -- 息费合计
  , SUM(haircut_amount)                       AS haircut_amt     -- 砍头息合计
  , SUM(contract_amount) / COUNT(1)           AS avg_contract    -- 件均合同额
  , SUM(fee_amount + interest) / SUM(contract_amount) AS take_rate   -- 息费率
  , SUM(haircut_amount) / SUM(contract_amount)       AS haircut_rate -- 砍头比例
  , SUM(loan_cycle * contract_amount) / sum(contract_amount) AS avg_term_days  -- 平均期限（天）
FROM ods.s02_loan t  
INNER JOIN mx.risk_double_loan_tag rt
       ON  CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
      AND rt.double_loan = 0  -- 首贷
WHERE release_time >= date'2026-03-01'
  AND t.state IN (1, 2, 3)
GROUP BY 1 
ORDER BY 1 DESC
;

还差一个本金坏账率和息费坏账率、投放预算表；

mx.mxepd_gyq_multyproduct_overdue_tmp_huizong_all
这个哈哈，里面有这些字段：
t0_should_sum
t7_should_sum 
hasrepayment_sum_t0
hasrepayment_sum_t7






-- 周报权责进度表 - 7月汇总（首贷/复贷/整体）-- 周报权责进度表 - 7月汇总（长格式输出）

WITH base AS (
    SELECT
        t.contract_amount,
        t.loan_cycle,
        t.fee_amount,
        t.interest,
        t.haircut_amount,
        rt.double_loan
    FROM ods.s02_loan t
    INNER JOIN mx.risk_double_loan_tag rt
        ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
    WHERE t.release_time >= DATE '2026-07-01'
      AND t.release_time < DATE '2026-08-01'
      AND t.state IN (1, 2, 3)
      AND rt.double_loan IN (0, 1)   -- 仅首贷和复贷
),
agg AS (
    -- 首贷（double_loan=0）
    SELECT 
        0 AS double_loan,
        '首贷' AS loan_type,
        SUM(contract_amount) AS contract_amt,
        COUNT(1) AS loan_cnt,
        SUM(contract_amount) / COUNT(1) AS avg_contract,
        SUM(loan_cycle * contract_amount) / SUM(contract_amount) AS avg_term,
        SUM(fee_amount + interest + haircut_amount) / SUM(contract_amount) AS fee_rate,
        1 AS type_order
    FROM base
    WHERE double_loan = 0

    UNION ALL

    -- 复贷（double_loan=1）
    SELECT 
        1,
        '复贷',
        SUM(contract_amount),
        COUNT(1),
        SUM(contract_amount) / COUNT(1),
        SUM(loan_cycle * contract_amount) / SUM(contract_amount),
        SUM(fee_amount + interest + haircut_amount) / SUM(contract_amount),
        2
    FROM base
    WHERE double_loan = 1

    UNION ALL

    -- 整体（全部）
    SELECT 
        NULL,
        '整体',
        SUM(contract_amount),
        COUNT(1),
        SUM(contract_amount) / COUNT(1),
        SUM(loan_cycle * contract_amount) / SUM(contract_amount),
        SUM(fee_amount + interest + haircut_amount) / SUM(contract_amount),
        3
    FROM base
)
-- 将每个指标拆成单独行
SELECT
    metric,
    loan_type,
    value
FROM (
    SELECT '成交金额 (USD)***' AS metric, loan_type, ROUND(contract_amt, 0) AS value, 1 AS metric_order, type_order FROM agg
    UNION ALL
    SELECT '成交标数', loan_type, ROUND(loan_cnt, 0), 2, type_order FROM agg
    UNION ALL
    SELECT '笔均 (USD)***', loan_type, ROUND(avg_contract, 0), 3, type_order FROM agg
    UNION ALL
    SELECT '期限', loan_type, ROUND(avg_term, 0), 4, type_order FROM agg
    UNION ALL
    SELECT '息费率', loan_type, ROUND(fee_rate, 4), 5, type_order FROM agg
) t
ORDER BY metric_order, type_order;















-- 周报权责进度表 - 2026年1-7月月度横向扩展（长表转宽表）
WITH
-- 1. 基础数据：筛选2026年1月至7月，并关联首复贷标签
base AS (
    SELECT
        t.contract_amount,
        t.loan_cycle,
        t.fee_amount,
        t.interest,
        t.haircut_amount,
        DATE_TRUNC('month', t.release_time) AS month,   -- 月份（每月1号）
        rt.double_loan
    FROM ods.s02_loan t
    INNER JOIN mx.risk_double_loan_tag rt
        ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
    WHERE t.release_time >= DATE '2026-01-01'
      AND t.release_time <  DATE '2026-08-01'
      AND t.state IN (1, 2, 3)
      AND rt.double_loan IN (0, 1)   -- 仅首贷和复贷
),

-- 2. 按月、按首/复贷分组汇总（首贷和复贷）
monthly_agg AS (
    SELECT
        month,
        double_loan,
        SUM(contract_amount)               AS sum_contract,
        COUNT(1)                           AS cnt_loan,
        SUM(loan_cycle * contract_amount)  AS sum_weighted_term,
        SUM(fee_amount + interest + haircut_amount) AS sum_fee
    FROM base
    GROUP BY month, double_loan
),

-- 3. 加入“整体”（即首贷+复贷的汇总），用 NULL 表示整体
all_types AS (
    SELECT month, double_loan, sum_contract, cnt_loan, sum_weighted_term, sum_fee
    FROM monthly_agg
    UNION ALL
    SELECT month, NULL AS double_loan,
           SUM(sum_contract)       AS sum_contract,
           SUM(cnt_loan)           AS cnt_loan,
           SUM(sum_weighted_term)  AS sum_weighted_term,
           SUM(sum_fee)            AS sum_fee
    FROM monthly_agg
    GROUP BY month
),

-- 4. 计算每个（月份, 类型）的最终指标值，并直接四舍五入
type_month_values AS (
    SELECT
        month,
        CASE WHEN double_loan = 0 THEN '首贷'
             WHEN double_loan = 1 THEN '复贷'
             ELSE '整体' END AS loan_type,
        -- 成交金额（整数）
        ROUND(sum_contract, 0) AS contract_amt,
        -- 成交标数（整数）
        cnt_loan AS loan_cnt,
        -- 笔均（整数）
        ROUND(sum_contract / cnt_loan, 0) AS avg_contract,
        -- 期限（按合同金额加权，整数）
        ROUND(sum_weighted_term / sum_contract, 0) AS avg_term,
        -- 息费率（保留4位小数）
        ROUND(sum_fee / sum_contract, 4) AS fee_rate
    FROM all_types
),

-- 5. 将指标“堆叠”为行（每个指标一行，带月份和值）
stacked AS (
    SELECT '成交金额 (USD)***' AS metric, loan_type, month, contract_amt AS value FROM type_month_values
    UNION ALL
    SELECT '成交标数', loan_type, month, loan_cnt FROM type_month_values
    UNION ALL
    SELECT '笔均 (USD)***', loan_type, month, avg_contract FROM type_month_values
    UNION ALL
    SELECT '期限', loan_type, month, avg_term FROM type_month_values
    UNION ALL
    SELECT '息费率', loan_type, month, fee_rate FROM type_month_values
)

-- 6. 转置为列：按 metric 和 loan_type 分组，用 CASE 提取各月值
SELECT
    metric,
    loan_type,
    MAX(CASE WHEN month = DATE '2026-01-01' THEN value END) AS "1月",
    MAX(CASE WHEN month = DATE '2026-02-01' THEN value END) AS "2月",
    MAX(CASE WHEN month = DATE '2026-03-01' THEN value END) AS "3月",
    MAX(CASE WHEN month = DATE '2026-04-01' THEN value END) AS "4月",
    MAX(CASE WHEN month = DATE '2026-05-01' THEN value END) AS "5月",
    MAX(CASE WHEN month = DATE '2026-06-01' THEN value END) AS "6月",
    MAX(CASE WHEN month = DATE '2026-07-01' THEN value END) AS "7月"
FROM stacked
GROUP BY metric, loan_type
ORDER BY
    CASE metric
        WHEN '成交金额 (USD)***' THEN 1
        WHEN '成交标数'        THEN 2
        WHEN '笔均 (USD)***'   THEN 3
        WHEN '期限'            THEN 4
        WHEN '息费率'          THEN 5
    END,
    CASE loan_type
        WHEN '首贷' THEN 1
        WHEN '复贷' THEN 2
        WHEN '整体' THEN 3
    END;



-- 投放花费：
with channel_mapping as (
    select app_key, app_channel
    from (
        values
            ('com.tiri.mx', '2930a02e-07b9-4851-aedd-200244a62b75'),
            ('com.tengoprestamos.cash.credito.mx', '2930a02e-07b9-4851-aedd-200244a62b75'),
            ('com.prestamos.credito.peso.cashvivas', '5653600e-256f-4768-8b27-8020e16c2587'),
            ('com.cash.prestamo.yaweycredito', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.cash.rapido.dinero.credito.yawey', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.cash.rapido.dinero.credito.yaweycredito', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.prestamo.credito.cash.loan.yawey', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.mx.dinero.yawey', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.cash.credito.prestamo.holapresto', 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5'),
            ('com.mxprestamo.credito.cash.rapido.holapresto', 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5'),
            ('id6504391085', 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5'),
            ('com.voltrixcredito.prestamos', '91379659-2dc0-42d2-8205-9de6d81f7550'),
            ('com.cash.prestamos.credito.prontofondo', '026f5e80-4582-4821-847a-4665660d8451'),
            ('com.holapresto.se', 'faa92afe-b81a-4d94-ba1a-15eb9d536833'),
            ('com.holapresto.pro', 'db0d289f-d217-49ea-a889-c191776115ef'),
            ('com.holapresto.max', '4cc31ae6-937e-4fd3-bc98-862314e7cb68'),
            ('com.cash.prestamo.yaweycredito.plus', 'cdf58da5-801a-4575-9af4-a56453cea6f3'),
            ('com.cash.prestamo.yaweycredito.ultra', '9922eb08-b998-46d9-b81e-469ae4c2e0ec'),
            ('com.mexcredo.loan.mx', '002e5068-2b82-443e-9447-88ddba989753'),
            ('com.efectivo.presto.credi.tuna', '38cb07f1-21ce-47ed-b552-384381fbaa92'),
            ('com.dinero.prest.balam.plata', 'f280d23f-8d33-49c8-8aff-cbbda6045c75'),
            ('id6751942954', 'a73166d6-364d-405f-bb38-a06ba2141a0f'),
            ('com.quikpeso.credito.dinerorapido', 'a73166d6-364d-405f-bb38-a06ba2141a0f'),
            ('com.rapido.credito.mikredi', '20fbd6af-b9f8-48d4-bc30-4ad3040e7205')
    ) as t(app_key, app_channel)
)
select
    date(c.ad_date) as ad_date,
    coalesce(cm.app_channel, 'other') as app_channel,
    case when c.campaign_name like '%IOS%' or c.app_channel_name in ('id6751942954') then 'iOS' else 'ANDROID' end as os,
    case
        when lower(c.media_source) like '%google%' then 'Google'
        when lower(c.media_source) like '%facebook%' or c.media_source = 'restricted' then 'facebook'
        when lower(c.media_source) like '%tiktok%' or lower(c.media_source) like '%cyberads%' then 'tiktok'
        when lower(c.media_source) like 'apple ads' then 'Apple Search Ads'
        when lower(c.media_source) like '%ads%' then c.media_source
        when c.agency is not null then c.agency
        when lower(c.media_source) like '%vfine_int%' then 'vfine_int'
        when c.media_source like 'dc1' then 'dc1'
        when c.media_source like 'tz1' then 'jc'
        when c.media_source = 'SMS' and c.campaign_name like '%cl%' then '创蓝'
        when (c.media_source = 'SMS' and c.campaign_name like '%TZ%') or lower(c.media_source) like '%tanzhi%' then '探知'
        when c.media_source = '11Y' then '11Y'
        when c.media_source = 'bj' then 'bj'
        when c.media_source = 'ziyouke' then 'ziyouke'
        when lower(c.media_source) like '%outside%' then '短信营销'
        when lower(c.media_source) like '%duobao%' or lower(c.media_source) like '%多包互导%' or lower(c.media_source) like '%yawey%' or lower(c.media_source) like '%tengo%' or lower(c.media_source) like '%hola%' or c.media_source = 'Email'
          or lower(c.media_source) like '%sms%' or lower(c.media_source) like '%app%' then '多包互导'
        when c.media_source like 'organic' then 'organic'
        when lower(c.media_source) like '%smark%' then 'smark'
        when c.media_source = '其他' then '其他'
        else '其他'
    end as new_media_source,
    sum(c.spend_usd) as spend,
    0 as installs,
    sum(c.impressions) as impressions,
    sum(c.clicks) as clicks
from dwd.dwd_ads_cost c
left join channel_mapping cm
    on c.app_channel_name = cm.app_key
where cast(c.ad_date as date) > date '2023-05-06'
group by 1,2,3,4
;

 

 20260702记录;年中计划已调，可以调整思路整体是：
1、先看整体的利润率是多少，然后看一下投放多少，CPS多少，复贷比例多少，调整复贷笔数；
主要是考虑复贷笔数能不能做到，这一点很重要，预估复贷笔数应该有一个比较好的方式；
2、期限息费收入和坏账统一一下，其它的成本项目基本上就不变了；