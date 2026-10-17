 复购表：by首贷成交月，mob，首贷level，首贷渠道，包，值：复贷成交笔数，复贷成交人数，对应首贷月总成交人数，复贷成交金额
逾期表：by首贷成交月，mob，首贷level，首贷渠道，包，值：合同金额，前砍金额，后收金额，本金坏账金额，息费坏账金额
投放表：by首贷成交月，首贷渠道，包，值：投放花费

 -- 投放表 by首贷成交月，首贷渠道，包，值：投放花费
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
    date_trunc('month', date(c.ad_date)) as ad_month,
     app_group,
    media_source,
    sum(c.spend_usd) as spend_usd 
from dwd.dwd_ads_cost c
left join channel_mapping cm
    on c.app_channel_name = cm.app_key
    left join (select app_channel,app_group from mx.wxs_application_funnel  group by 1,2) f
    on cm.app_channel = f.app_channel
where cast(c.ad_date as date) > date '2025-01-01'
group by 1, 2, 3  ; 

-- 首贷

-- 墨西哥LTV复购表: by 首贷成交月, mob, 首贷level, 首贷渠道, 包
WITH loan_base AS (
    SELECT mid,
           camera_id,
           release_time,
           is_reloan,
           'organic' as channel_category,
           app_group,
           contract_amount
    FROM mx.wxs_application_funnel
    WHERE if_issue = 1
      AND tenant = 'yawey'
      AND release_time IS NOT NULL
      AND release_time >= CAST('2025-01-01 00:00:00.000' AS TIMESTAMP)  -- 首贷判定兜底范围, 可调
),
first_loan AS ( 
    SELECT mid,
           camera_id AS first_camera_id,
           release_time AS first_release_time,
           channel_category AS first_channel_category,
           app_group AS first_app_group
    FROM (
        SELECT mid, camera_id, release_time, channel_category, app_group,
               row_number() OVER (PARTITION BY mid ORDER BY release_time, camera_id) AS rn
        FROM loan_base
        WHERE is_reloan = 'new'
    ) t
    WHERE rn = 1
),
cohort AS (
    SELECT fl.mid,
           date_trunc('month', fl.first_release_time) AS first_loan_month,
           coalesce(f7.credit_level, 9999) AS first_level,
           fl.first_channel_category,
           fl.first_app_group
    FROM first_loan fl
    LEFT JOIN mx.report_application_funnel7_table f7
        ON fl.first_camera_id = cast(f7.biz_id AS bigint)
),
agg AS (
    SELECT date_format(c.first_loan_month, '%Y-%m') AS first_loan_month,
           date_diff('month', c.first_loan_month, date_trunc('month', l.release_time)) AS mob,
           c.first_level,
           c.first_channel_category,
           c.first_app_group,
           count(DISTINCT CASE WHEN l.is_reloan = 'old' THEN l.camera_id END) AS reloan_cnt,          -- 复贷成交笔数
           count(DISTINCT CASE WHEN l.is_reloan = 'old' THEN l.mid END) AS reloan_user_cnt,           -- 复贷成交人数
           count(DISTINCT CASE WHEN l.is_reloan = 'new' THEN l.mid END) AS first_user_cnt,            -- 首贷月成交人数(仅mob=0行非0)
           sum(CASE WHEN l.is_reloan = 'old' THEN coalesce(l.contract_amount, 0) ELSE 0 END) AS reloan_amount  -- 复贷成交金额
    FROM cohort c
    JOIN loan_base l ON l.mid = c.mid
    GROUP BY 1, 2, 3, 4, 5
)
SELECT first_loan_month,
       mob,
       first_level,
       first_channel_category,
       first_app_group,
       reloan_cnt,
       reloan_user_cnt,
       max(first_user_cnt) OVER (
           PARTITION BY first_loan_month, first_level, first_channel_category, first_app_group
       ) AS cohort_first_user_cnt,   -- 对应首贷月总成交人数(分母, 每行同值)
       reloan_amount
FROM agg
ORDER BY 1,2,3,4,5




-- 墨西哥LTV逾期表: by 首贷成交月, mob, 首贷level, 首贷渠道, 包
-- 值: 合同金额 / 前砍金额 / 后收金额 / 本金坏账金额 / 息费坏账金额
-- 坏账口径: T30逾期(未到T30的期自动为0, 天然成熟门控); 息费=逾期利息(不含罚金)
WITH loan_base AS (
    SELECT mid,
           camera_id,
           release_time,
           is_reloan,
           'organic' channel_category,
           app_group,
           contract_amount,                     -- 合同金额
           haircut_amount,                      -- 前砍金额
           should_interest,                     -- 后收金额(后收利息) 
           coalesce(t7_overdue_capit_1, 0) AS t7_overdue_capit_1,   -- 逾期本金(1期)
           coalesce(t7_overdue_interest_1, 0) AS t7_overdue_interest_1, -- 逾期息费(1期)
           coalesce(t30_overdue_capit_4, 0) AS t30_overdue_capit_4,   -- 逾期本金(1~4期)
           coalesce(t30_overdue_interest_4, 0) AS t30_overdue_interest_4  -- 逾期息费(1~4期)
    FROM mx.wxs_application_funnel
    WHERE if_issue = 1
      AND tenant = 'yawey'
      AND release_time IS NOT NULL
      AND release_time >= CAST('2025-01-01 00:00:00.000' AS TIMESTAMP)
),
first_loan AS (
    SELECT mid,
           camera_id AS first_camera_id,
           release_time AS first_release_time,
           channel_category AS first_channel_category,
           app_group AS first_app_group
    FROM (
        SELECT mid, camera_id, release_time, channel_category, app_group,
               row_number() OVER (PARTITION BY mid ORDER BY release_time, camera_id) AS rn
        FROM loan_base
        WHERE is_reloan = 'new'
    ) t
    WHERE rn = 1
),
cohort AS (
    SELECT fl.mid,
           date_trunc('month', fl.first_release_time) AS first_loan_month,
           coalesce(f7.credit_level, 9999) AS first_level,
           fl.first_channel_category,
           fl.first_app_group
    FROM first_loan fl
    LEFT JOIN mx.report_application_funnel7_table f7
        ON fl.first_camera_id = cast(f7.biz_id AS bigint)
)
SELECT date_format(c.first_loan_month, '%Y-%m') AS first_loan_month,
       date_diff('month', c.first_loan_month, date_trunc('month', l.release_time)) AS mob,
       c.first_level,
       c.first_channel_category,
       c.first_app_group,
       count(DISTINCT l.camera_id) AS issue_cnt,                    -- 成交笔数(该mob全部放款)
       sum(coalesce(l.contract_amount, 0)) AS contract_amount,      -- 合同金额
       sum(coalesce(l.haircut_amount, 0)) AS haircut_amount,        -- 前砍金额
       sum(coalesce(l.should_interest, 0)) AS after_income_amount,  -- 后收金额
       sum(coalesce(l.t30_overdue_capit_4, 0)) AS principal_bad_amt,  -- 本金坏账金额
       sum(coalesce(l.t30_overdue_interest_4, 0)) AS interest_bad_amt     -- 息费坏账金额
FROM cohort c
JOIN loan_base l ON l.mid = c.mid
GROUP BY 1, 2, 3, 4, 5
ORDER BY 1, 2, 3, 4, 5