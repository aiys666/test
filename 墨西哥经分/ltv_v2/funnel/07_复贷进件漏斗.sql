-- ------------------------------------------------------------
-- 复贷进件漏斗（新增文档，不改动 01~06 任何既有表/文件）
--
-- 源表：mx.wxs_application_funnel  where is_reloan='old'
--   （全部旗标都在这一张表里；mx.wxs_application_funnel_2 是它的子集投影，
--     两表 if_sx_passed / if_fu_model_passed / if_in_sx / if_in_fu_model 取值
--     逐项一致、biz_id 零失配，故不 join。）
--
-- 产出：
--   mx.ys_ltv_v2_rf_base   逐单底表（按 biz_id 唯一）
--   mx.ys_ltv_v2_rf_month  月度漏斗
--   mx.ys_ltv_v2_rf_week   周度漏斗
--
-- 口径（严格嵌套链 → 恒等式天然成立）
--   进件数   N0 = 复贷进件单数
--   前置通过 N1 = if_sx_passed = 1            授信/用信决策通过
--   后置通过 N2 = N1 ∩ if_pass = 1            机审通过
--   放款     N3 = N2 ∩ if_issue = 1           放款
--   前置通过率 r1 = N1/N0   后置通过率 r2 = N2/N1   用信率 r3 = N3/N2
--   → N0 × r1 × r2 × r3 ≡ N3   连乘自动约分，逐行精确成立
--
-- 实测依据（2026-09-27，复贷进件 927,963）：
--   授信通过 610,124 ⊃ 机审通过 595,116（99.999%）⊃ 放款 589,056（99.99%）
--   复贷模型通过 564,570 与授信通过仅交集 481,699 → 模型节点是旁支不是闸口，
--   不入链，只作参考列。
--
-- 注：分母一律 nullif 防 0，比率 CAST AS DOUBLE（盘古端点陷阱）。
-- 注：盘古 Presto 不接受中文列别名，本文件列名全 ASCII；
--     中文口径名见同目录 08 号文档与 Excel「口径说明」页。
-- ------------------------------------------------------------

-- ---------- [1/3] 逐单底表 ----------
drop table if exists mx.ys_ltv_v2_rf_base;
create table mx.ys_ltv_v2_rf_base as
with dedup as (
    -- 同 biz_id 偶发多行：取最早进件时间；旗标取 max（发生过即为真）
    select
        biz_id,
        min(app_time)         as app_time,
        min(app_date)         as app_date,
        min(app_week)         as app_week,
        min(app_month)        as app_month,
        -- 复贷渠道名取自 app_group（与 墨西哥LTV代码.sql 第 11 行口径一致）；
        -- 表里的 app_channel 是 UUID，不可读，不作为维度
        max(app_group)        as app_channel_name,
        max(channel_category) as channel_category,
        max(product_name)     as product_name,
        max(app_version)      as app_version,
        max(if_app)           as if_app,
        max(if_bid)           as if_bid,
        max(if_pass)          as if_pass,
        max(if_issue)         as if_issue,
        max(if_in_sx)         as if_in_sx,
        max(if_sx_passed)     as if_sx_passed,
        max(if_in_fu_model)   as if_in_fu_model,
        max(if_fu_model_passed) as if_fu_model_passed
    from mx.wxs_application_funnel
    where is_reloan = 'old'
    group by biz_id
)
select
    biz_id, app_time, app_date, app_week, app_month,
    app_channel_name, channel_category, product_name, app_version,
    coalesce(if_app, 0)   as if_app,
    coalesce(if_bid, 0)   as if_bid,
    -- 原始旗标：供对账与旁证，不参与连乘
    coalesce(if_pass, 0)            as if_pass,
    coalesce(if_issue, 0)           as if_issue,
    coalesce(if_in_sx, 0)           as if_in_sx,
    coalesce(if_sx_passed, 0)       as if_sx_passed,
    coalesce(if_in_fu_model, 0)     as if_in_fu_model,
    coalesce(if_fu_model_passed, 0) as if_fu_model_passed,
    -- 严格嵌套链 S1 ⊇ S2 ⊇ S3，逐级取交，保证连乘不放大
    case when coalesce(if_sx_passed, 0) = 1
         then 1 else 0 end                                      as s1_pre,
    case when coalesce(if_sx_passed, 0) = 1
              and coalesce(if_pass, 0) = 1
         then 1 else 0 end                                      as s2_post,
    case when coalesce(if_sx_passed, 0) = 1
              and coalesce(if_pass, 0) = 1
              and coalesce(if_issue, 0) = 1
         then 1 else 0 end                                      as s3_issue
from dedup;

-- ---------- [2/3] 月度漏斗 ----------
drop table if exists mx.ys_ltv_v2_rf_month;
create table mx.ys_ltv_v2_rf_month as
with agg as (
    select
        app_month        as app_month,
        app_channel_name as app_channel_name,
        channel_category as channel_category,
        product_name     as product_name,
        count(*)         as apply_cnt,
        sum(s1_pre)      as pre_pass_cnt,
        sum(s2_post)     as post_pass_cnt,
        sum(s3_issue)    as issue_cnt,
        -- 参考列：不参与恒等式
        sum(if_issue)         as ref_issue_raw_cnt,
        sum(if_in_sx)         as ref_in_sx_cnt,
        sum(if_pass)          as ref_mach_pass_cnt,
        sum(if_fu_model_passed) as ref_model_pass_cnt
    from mx.ys_ltv_v2_rf_base
    group by 1, 2, 3, 4
)
select
    app_month, app_channel_name, channel_category, product_name,
    apply_cnt, pre_pass_cnt, post_pass_cnt, issue_cnt,
    -- 三级比率：分母即上一级分子，连乘自动约分
    round(cast(pre_pass_cnt  as double) / nullif(cast(apply_cnt     as double), 0), 6) as pre_pass_rate,
    round(cast(post_pass_cnt as double) / nullif(cast(pre_pass_cnt  as double), 0), 6) as post_pass_rate,
    round(cast(issue_cnt     as double) / nullif(cast(post_pass_cnt as double), 0), 6) as use_rate,
    -- 恒等式校验列：apply_cnt × r1 × r2 × r3，应逐行等于 issue_cnt。
    -- 分母为 0 时 coalesce 归零：嵌套链下 pre=0 ⟹ post=0 ⟹ issue=0，
    -- 故这一行恒等式取 0 == 0 仍成立；若不用 coalesce，校验列会是 NULL，
    -- 而 NULL 参与 >比较< 会被判成"不违规"，形成静默盲区。
    round(cast(apply_cnt as double)
          * coalesce(cast(pre_pass_cnt  as double) / nullif(cast(apply_cnt     as double), 0), 0)
          * coalesce(cast(post_pass_cnt as double) / nullif(cast(pre_pass_cnt  as double), 0), 0)
          * coalesce(cast(issue_cnt     as double) / nullif(cast(post_pass_cnt as double), 0), 0), 6) as issue_cnt_check,
    ref_issue_raw_cnt, ref_in_sx_cnt, ref_mach_pass_cnt, ref_model_pass_cnt,
    round(cast(ref_model_pass_cnt as double) / nullif(cast(apply_cnt as double), 0), 6) as ref_model_pass_rate
from agg;

-- ---------- [3/3] 周度漏斗 ----------
drop table if exists mx.ys_ltv_v2_rf_week;
create table mx.ys_ltv_v2_rf_week as
with agg as (
    select
        app_week         as app_week,
        app_channel_name as app_channel_name,
        channel_category as channel_category,
        product_name     as product_name,
        count(*)         as apply_cnt,
        sum(s1_pre)      as pre_pass_cnt,
        sum(s2_post)     as post_pass_cnt,
        sum(s3_issue)    as issue_cnt,
        sum(if_issue)           as ref_issue_raw_cnt,
        sum(if_in_sx)           as ref_in_sx_cnt,
        sum(if_pass)            as ref_mach_pass_cnt,
        sum(if_fu_model_passed) as ref_model_pass_cnt
    from mx.ys_ltv_v2_rf_base
    group by 1, 2, 3, 4
)
select
    app_week, app_channel_name, channel_category, product_name,
    apply_cnt, pre_pass_cnt, post_pass_cnt, issue_cnt,
    round(cast(pre_pass_cnt  as double) / nullif(cast(apply_cnt     as double), 0), 6) as pre_pass_rate,
    round(cast(post_pass_cnt as double) / nullif(cast(pre_pass_cnt  as double), 0), 6) as post_pass_rate,
    round(cast(issue_cnt     as double) / nullif(cast(post_pass_cnt as double), 0), 6) as use_rate,
    -- 同月度表：分母为 0 归零，避免校验列出现 NULL 造成静默盲区
    round(cast(apply_cnt as double)
          * coalesce(cast(pre_pass_cnt  as double) / nullif(cast(apply_cnt     as double), 0), 0)
          * coalesce(cast(post_pass_cnt as double) / nullif(cast(pre_pass_cnt  as double), 0), 0)
          * coalesce(cast(issue_cnt     as double) / nullif(cast(post_pass_cnt as double), 0), 0), 6) as issue_cnt_check,
    ref_issue_raw_cnt, ref_in_sx_cnt, ref_mach_pass_cnt, ref_model_pass_cnt,
    round(cast(ref_model_pass_cnt as double) / nullif(cast(apply_cnt as double), 0), 6) as ref_model_pass_rate
from agg;
