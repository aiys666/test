-- ============================================================
-- 墨西哥 LTV v2 · 月版
--   表1 mx.ys_ltv_v2_m_first_loan_cac   首贷 CAC 聚合（月 × 全维度）
--   表2 mx.ys_ltv_v2_m_double_loan      复贷明细（按首贷 cohort 归属）
--   表3 mx.ys_ltv_v2_m_double_group     复贷按 WOB 聚合
--   表4 mx.ys_ltv_v2_m_final             WOB 序列补全 → 最终导出（对应 数据源-复贷）
--
-- 底稿: 墨西哥经分/墨西哥LTV代码.sql
-- 新增维度: product_name / app_version / channel_category / new_grade_level_main
--           / register_media_source / is_low_amount_flag
--
-- 【列序约定】新维度一律追加在原始列之后，绝不插入列中间。
--   Excel 的透视表缓存按「列顺序索引」引用字段，插入列会让所有透视表失效。
--   月版首贷: A..AD 保持原样，AE..AJ 为新增维度
--   月版复贷: A..BJ 保持原样，BK..BP 为新增维度（*_d 后缀）
-- ============================================================


-- ------------------------------------------------------------
-- 1. 首贷 CAC 聚合（对应 Excel「数据源-首贷」）
-- ------------------------------------------------------------
drop table if exists mx.ys_ltv_v2_m_first_loan_cac;
create table mx.ys_ltv_v2_m_first_loan_cac as
with first_loan_agg as (
    select
        ltv_month,
        loan_cycle,
        app_channel,
        app_channel_name,
        new_grade_level,
        product_name,
        app_version,
        channel_category,
        new_grade_level_main,
        register_media_source,
        is_low_amount_flag,
        count(distinct biz_id)                                     as frs_cnt,
        sum(contract_amount)                                       as contract_amount,
        sum(contract_amount) / nullif(cast(count(distinct biz_id) as double), 0) as avg_amount,
        sum(fee * contract_amount) / nullif(cast(sum(contract_amount) as double), 0) as fee,
        sum(fee * contract_amount)                                 as fee_amount,
        sum(should_amt)                                            as should_amt,
        sum(should_amt_1t0)                                        as should_amt_1t0,
        sum(should_amt_1t3)                                        as should_amt_1t3,
        sum(should_amt_t7)                                         as should_amt_t7,
        sum(should_amt_t30)                                        as should_amt_t30,
        sum(contract_1t0)                                          as contract_1t0,
        sum(contract_1t3)                                          as contract_1t3,
        sum(contract_t7)                                           as contract_t7,
        sum(contract_t30)                                          as contract_t30,
        sum(fact_capital_1t0)                                      as fact_capital_1t0,
        sum(fact_capital_1t3)                                      as fact_capital_1t3,
        sum(fact_1t0)                                              as fact_1t0,
        sum(fact_1t3)                                              as fact_1t3,
        sum(fact_t7)                                               as fact_t7,
        sum(fact_t7_coup)                                          as fact_t7_coup,
        sum(fact_t30)                                              as fact_t30,
        sum(fact_t30_coup)                                         as fact_t30_coup,
        sum(fact_cnt_t0)                                           as fact_cnt_t0,
        sum(fact_cnt_t7)                                           as fact_cnt_t7,
        sum(fact_cnt_t30)                                          as fact_cnt_t30,
        sum(fact_cnt_till_now)                                     as fact_cnt_till_now,
        sum(re_zr_cnt_t30)                                         as re_zr_cnt_t30
    from mx.ys_ltv_v2_first_loan
    group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
),
cost as (
    select ad_month, app_channel, media_source, sum(spend_usd) as spend_usd
    from mx.ys_ltv_v2_ads_cost
    group by 1, 2, 3
),
total_cost as (
    select ad_month, sum(spend_usd) as total_spend_usd
    from mx.ys_ltv_v2_ads_cost
    group by 1
),
cost_rank as (
    select
        ltv_month,
        app_channel_name,
        register_media_source,
        new_grade_level,
        new_grade_level_main,
        loan_cycle,
        product_name,
        app_version,
        channel_category,
        is_low_amount_flag,
        row_number() over (
            partition by ltv_month, app_channel_name, register_media_source
            order by contract_amount desc
        ) as cost_rnk
    from first_loan_agg
)
select
    f.ltv_month,
    f.loan_cycle,
    f.app_channel_name,
    f.new_grade_level,
    f.frs_cnt,
    f.contract_amount,
    round(f.avg_amount, 2)          as avg_amount,
    round(f.fee, 4)                 as fee,
    round(f.fee_amount, 2)          as fee_amount,
    f.should_amt,
    f.should_amt_t7,
    f.should_amt_t30,
    f.contract_t7,
    f.contract_t30,
    f.fact_t7,
    f.fact_t7_coup,
    f.fact_t30,
    f.fact_t30_coup,
    f.fact_cnt_t0,
    f.fact_cnt_t7,
    f.fact_cnt_t30,
    f.fact_cnt_till_now,
    f.re_zr_cnt_t30,
    cast(0 as double)               as pass_rate,
    cr.cost_rnk,
    coalesce(t.total_spend_usd * d.exchange_rate_to_dollar, 0) as total_spend_ngn,
    coalesce(t.total_spend_usd, 0)  as total_spend_usd,
    coalesce(c.spend_usd * d.exchange_rate_to_dollar, 0)       as spend_ngn,
    coalesce(c.spend_usd, 0)        as spend_usd,
    d.exchange_rate_to_dollar,
    -- ↓↓↓ 以下为新增维度（追加在原始 30 列之后） ↓↓↓
    f.product_name,
    f.app_version,
    f.channel_category,
    f.new_grade_level_main,
    f.register_media_source,
    f.is_low_amount_flag
from first_loan_agg f
left join cost_rank cr
    on  f.ltv_month              = cr.ltv_month
    and f.app_channel_name       = cr.app_channel_name
    and f.register_media_source  = cr.register_media_source
    and f.new_grade_level        = cr.new_grade_level
    and f.new_grade_level_main   = cr.new_grade_level_main
    and f.loan_cycle             = cr.loan_cycle
    and f.product_name           = cr.product_name
    and f.app_version            = cr.app_version
    and f.channel_category       = cr.channel_category
    and f.is_low_amount_flag     = cr.is_low_amount_flag
left join cost c
    on  f.ltv_month             = c.ad_month
    and f.app_channel           = c.app_channel
    and f.register_media_source = c.media_source
    and cr.cost_rnk = 1
left join total_cost t
    on  f.ltv_month = t.ad_month
    and cr.cost_rnk = 1
left join dim.dim_exchange_rate_cost d
    on  date(DATE_PARSE(d.month_id, '%Y%m')) = f.ltv_month
    and d.account_currency = 'MXN';


-- ------------------------------------------------------------
-- 2. 复贷明细
-- ------------------------------------------------------------
drop table if exists mx.ys_ltv_v2_m_double_loan;
create table mx.ys_ltv_v2_m_double_loan as
select
    d.ltv_month,
    d.ltv_week,
    d.ltv_date,
    date_diff('week', d.ltv_week, date_trunc('week', date(r.release_time))) as wob,
    d.loan_cycle,
    d.app_channel,
    d.app_channel_name,
    d.product_name,
    d.app_version,
    d.channel_category,
    d.new_grade_level,
    d.new_grade_level_main,
    d.register_media_source,
    d.is_low_amount_flag,
    r.app_channel                                   as reloan_app_channel,
    r.app_group                                     as reloan_app_channel_name,
    r.camera_id                                     as biz_id,
    cast(r.cust_id as bigint)                       as mid,
    r.contract_amount,
    r.contract_amount / f.exchange_rate_to_dollar   as contract_amount_usd,
    r.haircut_amount,
    r.should_interest,
    r.should_interest + r.should_capital            as should_amt,
    r.t0_should_capit_4                             as contract_t0,
    r.t0_should_amt_1                               as should_amt_1t0,
    r.t3_should_amt_1                               as should_amt_1t3,
    r.t0_should_capit_1                             as contract_1t0,
    r.t3_should_capit_1                             as contract_1t3,
    r.t0_should_capit_1 - r.t0_overdue_capit_1      as fact_capital_1t0,
    r.t3_should_capit_1 - r.t3_overdue_capit_1      as fact_capital_1t3,
    r.t0_should_amt_1 - r.t0_overdue_amount_1       as fact_1t0,
    r.t3_should_amt_1 - r.t3_overdue_amount_1       as fact_1t3,
    r.t7_should_amt_4                               as should_amt_t7,
    r.t30_should_amt_4                              as should_amt_t30,
    r.t7_should_capit_4                             as contract_t7,
    r.t30_should_capit_4                            as contract_t30,
    case when r.t7_should_amt_4 > 0 then 1 else 0 end as should_cnt_t7,
    r.t7_should_amt_4  - r.t7_overdue_amount_4      as fact_t7,
    r.t7_should_amt_4  - r.t7_overdue_amount_4      as fact_t7_coup,
    r.t30_should_amt_4 - r.t30_overdue_amount_4     as fact_t30,
    r.t30_should_amt_4 - r.t30_overdue_amount_4     as fact_t30_coup,
    case when r.t0_should_amt_4  - r.t0_overdue_amount_4  > 0 then 1 else 0 end as fact_cnt_t0,
    case when r.t7_should_amt_4  - r.t7_overdue_amount_4  > 0 then 1 else 0 end as fact_cnt_t7,
    case when r.t30_should_amt_4 - r.t30_overdue_amount_4 > 0 then 1 else 0 end as fact_cnt_t30,
    0                                               as fact_cnt_till_now,
    date(t.trade_start_time)                        as trade_start_date,
    date(t.trade_end_time)                          as trade_end_date,
    0                                               as re_zr_cnt_t30
from mx.wxs_application_funnel r
left join mx.ys_ltv_v2_first_loan d
    on cast(r.cust_id as bigint) = d.mid
left join ods.s02_loan t
    on r.camera_id = t.camera_id
left join dim.dim_exchange_rate_cost f
    on  date(DATE_PARSE(f.month_id, '%Y%m')) = date(date_format(r.release_time, '%Y-%m-01'))
    and f.account_currency = 'MXN'
where r.is_reloan = 'old'
  and r.if_issue = 1
  and d.mid is not null;


-- ------------------------------------------------------------
-- 3. 复贷按 WOB 聚合
-- ------------------------------------------------------------
drop table if exists mx.ys_ltv_v2_m_double_group;
create table mx.ys_ltv_v2_m_double_group as
select
    ltv_month                                       as ltv_month_d,
    wob                                             as wob_d,
    app_channel_name                                as app_channel_name_d,
    loan_cycle                                      as loan_period,
    new_grade_level                                 as new_grade_level_d,
    product_name                                    as product_name_d,
    app_version                                     as app_version_d,
    channel_category                                as channel_category_d,
    new_grade_level_main                            as new_grade_level_main_d,
    register_media_source                           as register_media_source_d,
    is_low_amount_flag                              as is_low_amount_flag_d,
    count(distinct biz_id)                          as double_cnt,
    count(distinct mid)                             as double_mid,
    sum(contract_amount)                            as contract_amount,
    sum(haircut_amount + should_interest)           as fee_amount,
    sum(contract_amount) / nullif(cast(count(distinct biz_id) as double), 0) as avg_amount,
    sum(should_amt)                                 as should_amt_t0,
    sum(should_amt_t7)                              as should_amt_t7,
    sum(should_amt_t30)                             as should_amt_t30,
    sum(contract_t0)                                as contract_t0,
    sum(contract_t7)                                as contract_t7,
    sum(contract_t30)                               as contract_t30,
    sum(should_amt_1t0)                             as should_amt_1t0,
    sum(should_amt_1t3)                             as should_amt_1t3,
    sum(contract_1t0)                               as contract_1t0,
    sum(contract_1t3)                               as contract_1t3,
    sum(fact_capital_1t0)                           as fact_capital_1t0,
    sum(fact_capital_1t3)                           as fact_capital_1t3,
    sum(fact_1t0)                                   as fact_1t0,
    sum(fact_1t3)                                   as fact_1t3,
    (sum(contract_1t0) - sum(fact_capital_1t0)) / nullif(cast(sum(contract_1t0) as double), 0)  as bad_1t0_capital,
    (sum(contract_1t3) - sum(fact_capital_1t3)) / nullif(cast(sum(contract_1t3) as double), 0)  as bad_1t3_capital,
    (sum(should_amt_1t0) - sum(fact_1t0))       / nullif(cast(sum(should_amt_1t0) as double), 0) as bad_1t0_amt,
    (sum(should_amt_1t3) - sum(fact_1t3))       / nullif(cast(sum(should_amt_1t3) as double), 0) as bad_1t3_amt,
    0                                               as should_cnt_t0,
    sum(should_cnt_t7)                              as should_cnt_t7,
    0                                               as fact_t0,
    sum(fact_t7)                                    as fact_t7,
    sum(fact_t7_coup)                               as fact_t7_coup,
    sum(fact_t30)                                   as fact_t30,
    sum(fact_t30_coup)                              as fact_t30_coup,
    0                                               as fact_cnt_t0,
    sum(fact_cnt_t7)                                as fact_cnt_t7,
    sum(fact_cnt_t30)                               as fact_cnt_t30,
    sum(fact_cnt_till_now)                          as fact_cnt_till_now,
    0                                               as contract_amount_7d,
    0                                               as contract_amount_14d,
    0                                               as should_amt_7d,
    0                                               as should_amt_14d,
    0                                               as fact_t30_7d,
    0                                               as fact_t30_14d,
    0                                               as double_cnt_7d,
    0                                               as double_cnt_14d,
    0                                               as avg_amount_7d,
    0                                               as avg_amount_14d,
    0                                               as zr_mid,
    0                                               as zr_pass_mid,
    0                                               as zr_cnt,
    0                                               as zr_pass_cnt,
    0                                               as qz_mid,
    0                                               as qz_pass_mid,
    0                                               as qz_cnt,
    0                                               as qz_pass_cnt,
    0                                               as apply_mid,
    0                                               as apply_pass_mid,
    0                                               as apply_cnt,
    0                                               as apply_pass_cnt,
    0                                               as fact_cnt_t7_for_rzt30,
    0                                               as fact_cnt_t7_for_rzt7,
    0                                               as re_zr_cnt_t30,
    0                                               as re_zr_cnt_t7,
    sum(contract_amount_usd)                        as contract_amount_usd
from mx.ys_ltv_v2_m_double_loan
group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11;


-- ------------------------------------------------------------


-- ------------------------------------------------------------
-- 4. 最终导出（对应 Excel「数据源-复贷」）
--
-- 【设计变更 · 相对原文档，已与用户确认】
--   原文档先把首贷 cohort 键 × wob(0..max) 做稠密展开，再左连复贷聚合，
--   好处是每个 cohort 在每个 wob 都有行（曲线不断点）。
--   加入 5 个新维度后 cohort 键达 25,097 个，×79 周 = 1,982,663 行，
--   超过 Excel 单表 1,048,576 行上限（周版 3,687,404 行更甚）。
--   → 改为只输出「真实观测到的 (cohort, wob) 组合」= 108,230 行。
--     同一 cohort+wob 下的多个 loan_period 各自保留，double_rnk 沿用原口径。
--     无复贷的 (cohort, wob) 周次不再补 0 行，改由透视表自身聚合。
-- ------------------------------------------------------------
drop table if exists mx.ys_ltv_v2_m_final;
create table mx.ys_ltv_v2_m_final as
with frst_loan as (
    select
        ltv_month,
        app_channel_name,
        new_grade_level,
        product_name,
        app_version,
        channel_category,
        new_grade_level_main,
        register_media_source,
        is_low_amount_flag,
        count(distinct mid) as frs_cnt,
        sum(contract_amount) as frs_contract_amount
    from mx.ys_ltv_v2_first_loan
    group by 1, 2, 3, 4, 5, 6, 7, 8, 9
)
select
    -- A..D  cohort 键（与首贷侧同维度）
    g.ltv_month_d                                   as ltv_month,
    g.app_channel_name_d                            as app_channel_name,
    g.new_grade_level_d                             as new_grade_level,
    g.wob_d                                         as wob,
    -- E..BF 聚合结果（54 列，与原 Excel 位置完全一致）
    g.ltv_month_d,
    g.wob_d,
    g.app_channel_name_d,
    g.loan_period,
    g.new_grade_level_d,
    g.double_cnt,
    g.double_mid,
    g.contract_amount,
    g.fee_amount,
    g.avg_amount,
    g.should_amt_t0,
    g.should_amt_t7,
    g.should_amt_t30,
    g.contract_t0,
    g.contract_t7,
    g.contract_t30,
    g.should_cnt_t0,
    g.should_cnt_t7,
    g.fact_t0,
    g.fact_t7,
    g.fact_t7_coup,
    g.fact_t30,
    g.fact_t30_coup,
    g.fact_cnt_t0,
    g.fact_cnt_t7,
    g.fact_cnt_t30,
    g.fact_cnt_till_now,
    g.contract_amount_7d,
    g.contract_amount_14d,
    g.should_amt_7d,
    g.should_amt_14d,
    g.fact_t30_7d,
    g.fact_t30_14d,
    g.double_cnt_7d,
    g.double_cnt_14d,
    g.avg_amount_7d,
    g.avg_amount_14d,
    g.zr_mid,
    g.zr_pass_mid,
    g.zr_cnt,
    g.zr_pass_cnt,
    g.qz_mid,
    g.qz_pass_mid,
    g.qz_cnt,
    g.qz_pass_cnt,
    g.apply_mid,
    g.apply_pass_mid,
    g.apply_cnt,
    g.apply_pass_cnt,
    g.fact_cnt_t7_for_rzt30,
    g.fact_cnt_t7_for_rzt7,
    g.re_zr_cnt_t30,
    g.re_zr_cnt_t7,
    g.contract_amount_usd,
    -- BG..BJ 尾部
    row_number() over (
        partition by g.ltv_month_d, g.app_channel_name_d, g.new_grade_level_d,
                     g.product_name_d, g.app_version_d, g.channel_category_d,
                     g.new_grade_level_main_d, g.register_media_source_d,
                     g.is_low_amount_flag_d, g.wob_d
        order by g.loan_period
    ) as double_rnk,
    b.frs_cnt,
    b.frs_contract_amount,
    row_number() over (
        order by g.ltv_month_d, g.wob_d, g.app_channel_name_d, g.loan_period,
                 g.new_grade_level_d, g.product_name_d, g.app_version_d
    ) as rnk,
    -- BK..BP 新增维度（*_d 后缀，追加在原始 62 列之后）
    g.product_name_d,
    g.app_version_d,
    g.channel_category_d,
    g.new_grade_level_main_d,
    g.register_media_source_d,
    g.is_low_amount_flag_d
from mx.ys_ltv_v2_m_double_group g
left join frst_loan b
    on  g.ltv_month_d             = b.ltv_month
    and g.app_channel_name_d      = b.app_channel_name
    and g.new_grade_level_d       = b.new_grade_level
    and g.product_name_d          = b.product_name
    and g.app_version_d           = b.app_version
    and g.channel_category_d      = b.channel_category
    and g.new_grade_level_main_d  = b.new_grade_level_main
    and g.register_media_source_d = b.register_media_source
    and g.is_low_amount_flag_d    = b.is_low_amount_flag
where g.ltv_month_d >= date '2023-02-01';
