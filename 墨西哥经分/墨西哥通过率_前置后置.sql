-- 墨西哥通过率 - 前置/机审通过率 & 后置通过率
-- 按 data_date + double_loan_new 分组

with
base as (
select *
    from mx.daily_order_base
),
processor_flags as (
select
        biz_id,
        max(case when current_processor in ('首贷模型拒绝','复贷模型拒绝') then 1 else 0 end) as if_in_model,
        case
            when sum(case when current_processor in ('首贷模型拒绝','复贷模型拒绝') and approve_result = 'REFUSED' then 1 else 0 end) >= 1 then 0
            when sum(case when current_processor in ('首贷模型拒绝','复贷模型拒绝') then 1 else 0 end) >= 1 then 1
            else 0
        end as if_model_passed,
        max(case when current_processor in ('首贷授信等待节点','复贷授信等待节点','授信等待节点') then 1 else 0 end) as if_in_ruleDetermine_data,
        case
            when sum(case when current_processor in ('首贷授信等待节点','复贷授信等待节点','授信等待节点') and approve_result = 'PASSED' then 1 else 0 end) >= 1 then 1
            else 0
        end as if_normal_ruleDetermine_passed
    from ods.s05_creditx_processor_record
    group by 1
),
global_limit_exclude as (
select externalid as biz_id
    from ods.s21_risk_strategy_record
    where etl_date >= '20250226'
      and productid = 194
      and strategytype = 'CHAMPION'
      and cast(json_extract(outputdata, '$.available_limit_zero_mark') as int) = 1
      and cast(json_extract(outputdata, '$.global_limit_mark') as int) = 1
    group by 1
),
apply_metric as (
select
        b.create_date as data_date,
        b.double_loan_new,
        count(distinct b.biz_id) as apply_cnt,
        count(distinct case when b.order_status = 372 then b.biz_id end) as pass_cnt,
        count(distinct case when pf.if_model_passed = 1 then b.biz_id end) as model_pass_cnt,
        count(distinct case when pf.if_in_ruleDetermine_data = 1 then b.biz_id end) as in_rule_cnt,
        round(cast(count(distinct case when pf.if_model_passed = 1 then b.biz_id end) as double) 
            / nullif(count(distinct b.biz_id), 0), 2) as pre_approval_rate,
        round(cast(count(distinct case when b.order_status = 372 then b.biz_id end) as double) 
            / nullif(count(distinct case when pf.if_in_ruleDetermine_data = 1 then b.biz_id end), 0), 2) as post_approval_rate
    from base b
    left join processor_flags pf
        on b.biz_id = pf.biz_id
    left join global_limit_exclude ge
        on b.biz_id = ge.biz_id
    where b.create_date >= date '2023-03-01'
      and ge.biz_id is null
    group by 1,2
)
select 
    data_date, double_loan_new,
    apply_cnt, pass_cnt, model_pass_cnt, in_rule_cnt,
    pre_approval_rate, post_approval_rate
from apply_metric
order by data_date desc, double_loan_new
;