-- ============================================================
-- 墨西哥 Take Rate 明细底表（按 月/周/首复贷/产品/渠道 维度）
-- 表名：mx.gm_take_rate_really_detail
-- ============================================================

drop table if exists mx.gm_take_rate_really_detail;
create table mx.gm_take_rate_really_detail as

select
    -- ── 时间维度 ────────────────────────────────────
    to_char(date(t1.release_time), 'yyyymm')                                    as data_date     -- 放款月份（YYYYMM）
    ,date_add('day', -day_of_week(date(t1.release_time)) + 1, date(t1.release_time)) as date_week  -- 放款周（周一）

    -- ── 借款类型 ────────────────────────────────────
    ,case when rt.double_loan = 0 then '首贷'
          when rt.double_loan = 1 then '复贷'
     end                                                                         as order_type    -- 首贷/复贷

    -- ── 产品 & 期数 ─────────────────────────────────
    ,t1.product_name                                                             as product_level -- 产品线（优先级：cs.change_product_level > t1.product_name）
    ,t1.loan_cycle                                                               as loan_cycle    -- 借款期数

    -- ── 渠道归因 ────────────────────────────────────
    -- 按 app_channel UUID 映射为可读渠道名（TG/YW/HL/ME/TC/TL/MK/BP/QP/none）
    ,case
        when t1.app_channel in ('2930a02e-07b9-4851-aedd-200244a62b75','cbcf1f5e-092a-44ad-abb9-7d5af8f023cb','e5a5940e-eb8e-4188-ad1a-5bdbd4580938','6d21fe7d-8344-419c-8c94-a7b5cc1c8ee8') then 'TG'
        when t1.app_channel in ('56c660de-3549-4482-9ad5-0404eef0d70d','cdf58da5-801a-4575-9af4-a56453cea6f3','9922eb08-b998-46d9-b81e-469ae4c2e0ec','ab9981d2-b48f-4df0-a086-ff7df6a4fa04') then 'YW'
        when t1.app_channel in ('fe939ba4-4acb-4311-82cf-cfbbd190dfb5','faa92afe-b81a-4d94-ba1a-15eb9d536833','4cc31ae6-937e-4fd3-bc98-862314e7cb68','db0d289f-d217-49ea-a889-c191776115ef') then 'HL'
        when t1.app_channel in ('002e5068-2b82-443e-9447-88ddba989753') then 'ME'
        when t1.app_channel in ('38cb07f1-21ce-47ed-b552-384381fbaa92') then 'TC'
        when t1.app_channel in ('b0850bab-2a3b-4be2-ae70-70f6d90997d4') then 'TL'
        when t1.app_channel in ('8399a2d9-135a-46f2-bc73-be5a86662786') then 'MK'
        when t1.app_channel in ('f280d23f-8d33-49c8-8aff-cbbda6045c75') then 'BP'
        when t1.app_channel in ('a73166d6-364d-405f-bb38-a06ba2141a0f') then 'QP'
        else 'none'
    end                                                                          as app_channel   -- 渠道名称

    -- ── 操作系统 ────────────────────────────────────
    ,mos.source                                                                  as source        -- Android/iOS（来自 s05_creditx_order）

    -- ── 核心指标（金额统一换算为 USD） ──────────────
    -- 汇率逻辑：优先取 dim_exchange_rate_cost 的 exchange_rate_to_dollar，缺失时用默认 17
    ,count(distinct t1.camera_id)                                                as loan_cnt                      -- 放款笔数
    ,sum(case when exchange_rate_to_dollar is not null then t1.contract_amount / exchange_rate_to_dollar
              else t1.contract_amount / 17 end)                                  as loan_contract_amt_usd         -- 合同金额（USD）
    ,sum(case when exchange_rate_to_dollar is not null then amount / exchange_rate_to_dollar
              else amount / 17 end)                                              as amount                        -- 实放金额（USD）
    ,sum(case when exchange_rate_to_dollar is not null then interest / exchange_rate_to_dollar
              else interest / 17 end)                                            as interest                      -- 利息收入（USD）= 利息/汇率
    ,sum(case when exchange_rate_to_dollar is not null then rd.fact_amt / exchange_rate_to_dollar
              else rd.fact_amt / 17 end)                                         as fact_amt                      -- 实还金额（USD）= 本金+利息

    -- ── 结清口径 ────────────────────────────────────
    ,count(distinct case when date(t1.trade_end_time) <= date(now()) then t1.camera_id end) as finish_cnt            -- 已结清笔数
    ,sum(case when date(t1.trade_end_time) <= date(now())
                 and exchange_rate_to_dollar is not null then t1.contract_amount / exchange_rate_to_dollar
              when date(t1.trade_end_time) <= date(now())
                 and exchange_rate_to_dollar is null      then t1.contract_amount / 17
         end)                                                                     as finish_loan_contract_amt_usd  -- 已结清合同金额（USD）

-- ==============================================================
-- 主表：借款数据
-- ==============================================================
from ods.s02_loan t1

-- 汇率换算：放款月 → MXN→USD
left join dim.dim_exchange_rate_cost t2
    on to_char(date(release_time), 'yyyymm') = t2.month_id
   and t2.account_currency = 'MXN'

-- 渠道归因：biz_id → source（Android/iOS）
left join (select distinct source, biz_id from ods.s05_creditx_order) mos
    on cast(mos.biz_id as bigint) = t1.camera_id

-- 新老客标签：0=首贷，1=复贷
left join (select * from mx.risk_double_loan_tag) rt
    on cast(t1.camera_id as bigint) = cast(rt.biz_id as bigint)

-- 产品线变更：2025-01-01 之后发生过 FREEZE_LIMIT 变动的，取变更后的 product_level
-- cs 逻辑：s09_os_credit_snapshot → s05_user_creditlimit_used_detail（找 limit_change_id）→ s05_user_creditlimit_change_record（取 change_product_level）
left join (
    select distinct
        case when b.biz_id is not null then change_product_level else a.product_level end as product_level
        ,id
    from ods.s09_os_credit_snapshot a
    left join (
        select biz_id, change_product_level
        from (
            select limit_change_id, biz_id
            from ods.s05_user_creditlimit_used_detail
            where change_action = 'FREEZE_LIMIT'
              and limit_type = 'MAIN'
        ) t0
        left join (
            select change_product_level, id
            from ods.s05_user_creditlimit_change_record
        ) t1 on t0.limit_change_id = t1.id
    ) b on a.id = b.biz_id
    where date(create_time) >= date('2025-01-01')
      and product_level is not null
) cs on cast(cs.id as bigint) = cast(t1.camera_id as bigint)

-- 还款明细：累计实还 = fact_capital + fact_interest
left join (
    select camera_id
          ,sum(fact_capital + fact_interest) as fact_amt
    from mx.yqw_0920_loan_repayment_detail_time_update
    group by 1
) rd on rd.camera_id = t1.camera_id

where t1.state in (1, 2, 3)    -- 有效借款状态

group by 1, 2, 3, 4, 5, 6, 7
;


-- ============================================================
-- Take Rate 计算逻辑（在这张底表基础上）
-- ============================================================
-- Gross Take Rate（毛利率）= interest（利息收入）/ amount（实放金额）
--    反映：每放出 $1，能收多少利息
--
-- 坏账估算：
--    bad_debt ≈ loan_contract_amt_usd - fact_amt
--    即 合同金额 - 累计实还 = 未收回部分
--    ⚠️ 注意：fact_amt 是累计实还（含已结清和还款中的）
--    更精确的坏账 = finish_loan_contract_amt_usd - finish实收（需另外取）
--
-- Net Take Rate（净利率）≈ (interest - 坏账) / amount
--    反映：扣除坏账后，每放出 $1 的实际利润
