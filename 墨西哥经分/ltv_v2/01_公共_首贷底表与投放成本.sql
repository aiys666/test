-- ============================================================
-- 墨西哥 LTV v2 · 公共层
--   表1 mx.ys_ltv_v2_first_loan   首贷明细底表（月版/周版共用）
--   表2 mx.ys_ltv_v2_ads_cost     投放成本（日/月/周 × 渠道 × 媒体来源）
--
-- 底稿来源: 墨西哥/26.墨西哥LTV全数据.sql
-- 相对底稿的两处修复（已经过跑数验证）:
--   [FIX-1] 媒体来源关联键: cast(r.cust_id as bigint)=att.mid  →  r.mid=att.mid
--           原写法匹配 0/336,886 行, register_media_source 全落 'other'
--           修复后匹配 336,877/336,886 行, 21 种媒体来源
--   [FIX-2] new_grade_level_main 的 case when 分支顺序对调
--           原写法第二分支恒不可达, ≥2026-06-02 永远切不到 V5_2
-- 时间口径: issue_month / issue_week / issue_date（以 26.sql 为准）
-- ============================================================


drop table if exists mx.ys_ltv_v2_first_loan;
create table mx.ys_ltv_v2_first_loan as
select
    -- ---------- 时间维度 ----------
    r.issue_month                                   as ltv_month,
    r.issue_week                                    as ltv_week,
    r.issue_date                                    as ltv_date,

    -- ---------- 首贷分组维度 ----------
    r.loan_cycle,
    r.app_channel,
    r.app_group                                     as app_channel_name,
    r.product_name,
    r.app_version,
    r.channel_category,
    coalesce(f7.credit_level, 9999)                 as new_grade_level,
    coalesce(
        case
            when r.app_time >= date '2026-06-02' then t4.android_newcust_maincreditlevel_charge_v5_2
            when r.app_time >= date '2026-01-01' then t4.sd_creditlevel_main_v4_1
            else 9999
        end, 9999)                                  as new_grade_level_main,
    case when r.contract_amount <= 500 then '小金额(<=500)' else '非小金额(>500)' end
                                                    as is_low_amount_flag,
    case
        when lower(att.new_media_source) = 'facebook'         then 'facebook'
        when lower(att.new_media_source) = 'google'           then 'google'
        when lower(att.new_media_source) = 'tiktok'           then 'tiktok'
        when lower(att.new_media_source) = 'apple search ads' then 'Apple Search Ads'
        when lower(att.new_media_source) = 'organic'          then 'organic'
        when lower(att.new_media_source) = 'bj'               then 'bj'
        when att.new_media_source = '探知'                     then '探知'
        else 'other'
    end                                             as register_media_source,

    -- ---------- 主键 ----------
    r.camera_id                                     as biz_id,
    cast(r.cust_id as bigint)                       as mid,       -- 首贷↔复贷关联键
    r.mid                                           as att_mid,   -- 归因表关联键
    r.release_time,

    -- ---------- 息费 ----------
    (coalesce(r.haircut_amount, 0) + coalesce(r.should_interest, 0))
        / nullif(cast(r.contract_amount as double), 0)           as fee,
    r.contract_amount,
    r.haircut_amount,
    r.should_interest,
    r.should_interest + r.should_capital            as should_amt,

    -- ---------- 1期(T0/T3)口径 ----------
    r.t0_should_amt_1                               as should_amt_1t0,
    r.t3_should_amt_1                               as should_amt_1t3,
    r.t0_should_capit_1                             as contract_1t0,
    r.t3_should_capit_1                             as contract_1t3,
    r.t0_should_capit_1 - r.t0_overdue_capit_1      as fact_capital_1t0,
    r.t3_should_capit_1 - r.t3_overdue_capit_1      as fact_capital_1t3,
    r.t0_should_amt_1 - r.t0_overdue_amount_1       as fact_1t0,
    r.t3_should_amt_1 - r.t3_overdue_amount_1       as fact_1t3,

    -- ---------- 4期窗口口径(T7/T30) ----------
    r.t0_should_capit_4                             as contract_t0,
    r.t7_should_capit_4                             as contract_t7,
    r.t30_should_capit_4                            as contract_t30,
    r.t7_should_amt_4                               as should_amt_t7,
    r.t30_should_amt_4                              as should_amt_t30,
    r.t7_should_amt_4  - r.t7_overdue_amount_4      as fact_t7,
    r.t7_should_amt_4  - r.t7_overdue_amount_4      as fact_t7_coup,
    r.t30_should_amt_4 - r.t30_overdue_amount_4     as fact_t30,
    r.t30_should_amt_4 - r.t30_overdue_amount_4     as fact_t30_coup,
    case when r.t0_should_amt_4  - r.t0_overdue_amount_4  > 0 then 1 else 0 end as fact_cnt_t0,
    case when r.t7_should_amt_4  - r.t7_overdue_amount_4  > 0 then 1 else 0 end as fact_cnt_t7,
    case when r.t30_should_amt_4 - r.t30_overdue_amount_4 > 0 then 1 else 0 end as fact_cnt_t30,

    -- ---------- 占位（与历史结构保持一致） ----------
    0                                               as fact_cnt_till_now,
    0                                               as re_zr_cnt_t30
from mx.wxs_application_funnel r
left join ods.s02_loan t
    on r.camera_id = t.camera_id
left join mx.report_application_funnel7_table f7
    on r.camera_id = cast(f7.biz_id as bigint)
left join (
    select externalid7,
           sd_creditlevel_main_v4_1,
           android_newcust_maincreditlevel_charge_v5_2
    from mx.wenj_sd_market
) t4
    on r.biz_id = t4.externalid7
left join mx.gm_attribution_detail att
    on r.mid = att.mid                       -- [FIX-1]
where r.is_reloan = 'new'
  and r.if_issue = 1;


-- ============================================================
-- 投放成本（日/月/周 × 渠道 × 媒体来源）
-- ============================================================
drop table if exists mx.ys_ltv_v2_ads_cost;
create table mx.ys_ltv_v2_ads_cost as
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
    date(c.ad_date)                                 as ad_date,
    date_trunc('month', date(c.ad_date))            as ad_month,
    date_trunc('week',  date(c.ad_date))            as ad_week,
    case
        when lower(c.media_source) = 'facebook'         then 'facebook'
        when lower(c.media_source) = 'google'           then 'google'
        when lower(c.media_source) = 'tiktok'           then 'tiktok'
        when lower(c.media_source) = 'apple search ads' then 'Apple Search Ads'
        when lower(c.media_source) = 'organic'          then 'organic'
        when lower(c.media_source) = 'bj'               then 'bj'
        when c.media_source = '探知'                     then '探知'
        else 'other'
    end                                             as media_source,
    coalesce(cm.app_channel, 'other')               as app_channel,
    sum(c.spend_usd)                                as spend_usd
from dwd.dwd_ads_cost c
left join channel_mapping cm
    on c.app_channel_name = cm.app_key
where cast(c.ad_date as date) > date '2025-01-01'
group by 1, 2, 3, 4, 5;
