-- ============================================================
-- 墨西哥 LTV 复购分析 · 月度版（MOB维度）
-- 不动原周表，新建 _m 后缀的月度表
-- ============================================================

-- ① 首贷用户月度明细表
drop table if exists mx.gm_ltv_model_shou_user_detail_m;
create table mx.gm_ltv_model_shou_user_detail_m as

select distinct 
    date_trunc('month', date(t1.release_time)) as dt_month
    ,t1.double_loan
    ,t1.app_channel
    ,ms.media_source
    ,sl.product_name
    ,mos.source as os
    ,t1.customer_id
    ,t1.camera_id
    ,t1.contract_amount
    ,t1.amount
    ,t2.exchange_rate_to_dollar
from ods.s02_loan t1
left join dim.dim_exchange_rate_cost t2 
    on to_char(date(release_time),'yyyymm') = t2.month_id 
    and t2.account_currency = 'MXN'
left join (select distinct source,biz_id from ods.s05_creditx_order) mos 
    on cast(mos.biz_id as bigint) = t1.camera_id
inner join (select * from mx.risk_double_loan_tag where double_loan = 0) rt 
    on cast(t1.camera_id as bigint) = cast(rt.biz_id as bigint)
left join (select * from mx.gm_ltv_model_shou_user_layer) sl 
    on sl.camera_id = t1.camera_id
left join (select * from mx.gm_ltv_shou_user_media_source) ms 
    on ms.camera_id = t1.camera_id
where date(release_time) >= date('2023-03-01') 
  and state in (1,2,3)
;


-- ② 首复贷用户月度明细表（含MOB）
drop table if exists mx.gm_ltv_model_shou_fu_user_detail_m;
create table mx.gm_ltv_model_shou_fu_user_detail_m as

select 
    a.dt_month         as shou_month
    ,a.app_channel
    ,a.product_name    as shou_product
    ,a.customer_id
    ,a.contract_amount
    ,a.exchange_rate_to_dollar
    ,a.amount          as shou_amount
    ,a.media_source
    ,b.customer_id     as fu_customer_id
    ,b.dt_month        as fu_month
    ,b.camera_id
    ,b.product_name    as fu_product
    ,b.contract_amount as fu_contract_amount
    ,b.amount          as fu_amount
    ,date_diff('month', a.dt_month, b.dt_month) as mob
from mx.gm_ltv_model_shou_user_detail_m a
left join (
    select distinct 
        date_trunc('month', date(t1.release_time)) as dt_month
        ,t1.customer_id
        ,t1.camera_id
        ,sl.product_name
        ,t1.app_channel
        ,t1.contract_amount
        ,t1.amount
    from ods.s02_loan t1
    inner join (select * from mx.risk_double_loan_tag where double_loan = 1) rt 
        on cast(t1.camera_id as bigint) = cast(rt.biz_id as bigint)
    left join (select * from mx.gm_ltv_model_shou_user_layer) sl 
        on sl.camera_id = t1.camera_id
    where date(release_time) >= date('2023-03-01') 
      and state in (1,2,3)
) b on a.customer_id = b.customer_id 
   and a.app_channel = b.app_channel
;


-- ③ 月度复借率（按笔数，MOB维度）
drop table if exists mx.gm_ltv_model_camera_repurchase_m;
create table mx.gm_ltv_model_camera_repurchase_m as

select 
    a.*
    ,b.fu_month
    ,b.fu_camera_cnt
    ,b.fu_camera_amt
from (
    -- 首贷月度 + MOB补全
    select 
        a.dt_month       as shou_month
        ,a.app_channel
        ,a.product_name
        ,a.media_source
        ,b.mob
        ,count(distinct a.customer_id) as shou_cnt
        ,sum(a.contract_amount)        as shou_contract_amt
    from mx.gm_ltv_model_shou_user_detail_m a
    left join (
        -- MOB枚举：补足首贷月份没有对应复贷的mob行，保证分母完整
        select distinct shou_month, mob 
        from mx.gm_ltv_model_shou_fu_user_detail_m
    ) b on a.dt_month = b.shou_month
    group by 1,2,3,4,5
) a
left join (
    -- 复贷月度（按首贷月+MOB聚合）
    select 
        shou_month
        ,mob
        ,fu_month
        ,app_channel
        ,shou_product
        ,media_source
        ,count(distinct camera_id) as fu_camera_cnt
        ,sum(fu_contract_amount)    as fu_camera_amt
    from mx.gm_ltv_model_shou_fu_user_detail_m
    group by 1,2,3,4,5,6
) b on a.shou_month = b.shou_month 
   and a.app_channel = b.app_channel 
   and a.product_name = b.shou_product 
   and a.media_source = b.media_source 
   and a.mob = b.mob
;


-- ============================================================
-- 查询示例
-- ============================================================

-- 示例1：首贷月度汇总
-- select shou_month, product_name, media_source, app_channel,
--        sum(shou_cnt) shou_笔数, sum(shou_contract_amt) shou_金额
-- from mx.gm_ltv_model_camera_repurchase_m
-- where mob = 0
-- group by 1,2,3,4 order by 1;

-- 示例2：MOB 0-12 复贷笔数/金额矩阵
-- select shou_month, mob,
--        sum(shou_cnt) 首贷笔数, sum(fu_camera_cnt) 复贷笔数,
--        sum(shou_contract_amt) 首贷金额, sum(fu_camera_amt) 复贷金额
-- from mx.gm_ltv_model_camera_repurchase_m
-- group by 1,2 order by 1,2;
