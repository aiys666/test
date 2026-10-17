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
