with
base as (
select *
    from mx.daily_order_base
),
processor_flags as (
select
        biz_id,
        max(case when current_processor in ('复贷授信拒绝') then 1 else 0 end) as if_in_fu_sx_refuse,
        max(case when current_processor in ('首贷模型拒绝','复贷模型拒绝') then 1 else 0 end) as if_in_model,
        case
            when sum(case when current_processor in ('首贷模型拒绝','复贷模型拒绝') and approve_result = 'REFUSED' then 1 else 0 end) >= 1 then 0
            when sum(case when current_processor in ('首贷模型拒绝','复贷模型拒绝') then 1 else 0 end) >= 1 then 1
            else 0
        end as if_model_passed,
        max(case when current_processor in ('首贷授信节点','复贷授信节点') then 1 else 0 end) as if_in_confirm,
        case
            when sum(case when current_processor in ('首贷授信节点','复贷授信节点') and approve_result = 'REFUSED' then 1 else 0 end) >= 1 then 0
            when sum(case when current_processor in ('首贷授信节点','复贷授信节点') then 1 else 0 end) >= 1 then 1
            else 0
        end as if_confirm_passed,
        max(case when current_processor in ('首贷授信等待节点','复贷授信等待节点','授信等待节点') then 1 else 0 end) as if_in_ruleDetermine_data_all,
        max(case when current_processor in ('首贷授信等待节点','复贷授信等待节点','授信等待节点') then 1 else 0 end) as if_in_ruleDetermine_data,
        case
            when sum(case when current_processor in ('首贷授信等待节点','复贷授信等待节点','授信等待节点') and approve_result = 'PASSED' then 1 else 0 end) >= 1 then 1
            else 0
        end as if_normal_ruleDetermine_passed,
        max(case when current_processor in ('首贷三方节点','复贷三方节点') then 1 else 0 end) as if_in_external_data,
        case
            when sum(case when current_processor in ('首贷三方节点','复贷三方节点') and approve_result = 'REFUSED' then 1 else 0 end) >= 1 then 0
            when sum(case when current_processor in ('首贷三方节点','复贷三方节点') then 1 else 0 end) >= 1 then 1
            else 0
        end as if_external_data_passed
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
credit_snapshot as (
select
        cast(s.id as varchar) as biz_id,
        case
            when b.product_days = 14 and json_extract_scalar(s.grantcredit_info,'$.grantcredit_14d_amount') is not null then cast(json_extract_scalar(s.grantcredit_info,'$.grantcredit_14d_amount') as bigint)
            when b.product_days = 7 and json_extract_scalar(s.grantcredit_info,'$.grantcredit_7d_amount') is not null then cast(json_extract_scalar(s.grantcredit_info,'$.grantcredit_7d_amount') as bigint)
            when b.product_days = 15 and json_extract_scalar(s.grantcredit_info,'$.grantcredit_15d_amount') is not null then cast(json_extract_scalar(s.grantcredit_info,'$.grantcredit_15d_amount') as bigint)
            when b.product_days = 21 and json_extract_scalar(s.grantcredit_info,'$.grantcredit_21d_amount') is not null then cast(json_extract_scalar(s.grantcredit_info,'$.grantcredit_21d_amount') as bigint)
            when b.product_days = 28 and json_extract_scalar(s.grantcredit_info,'$.grantcredit_28d_amount') is not null then cast(json_extract_scalar(s.grantcredit_info,'$.grantcredit_28d_amount') as bigint)
            when b.product_days is not null then cast(json_extract_scalar(s.grantcredit_info,'$.grantcredit_7d_amount') as bigint)
            else 0
        end as grantcredit_amount,
        b.apply_amount / 1000 as apply_amount,
        er.exchange_rate_to_dollar
    from ods.s09_os_credit_snapshot s
    join base b
        on cast(s.id as varchar) = b.biz_id
    left join dim.dim_exchange_rate_cost er
        on to_char(date(s.create_time), 'yyyymm') = er.month_id
        and er.account_currency = 'MXN'
    where cast(json_extract(s.grantcredit_info, '$.grantcredit_7d_amount') as varchar) is not null
      and b.apply_amount / 1000 <= 100000
),
apply_metric as (
select
        b.create_date as data_date,
        b.app_channel,
        b.double_loan,
        b.double_loan_new,
        b.reloan_num,
        1 as indexs,
        b.product_name,
        b.os,
        b.new_media_source,
        count(distinct b.biz_id) as apply_cnt,
        count(distinct case when b.order_status = 372 then b.biz_id end) as pass_cnt,
        count(distinct case when pf.if_in_ruleDetermine_data_all = 1 then b.biz_id end) as if_model_passed,
        count(distinct case when pf.if_in_fu_sx_refuse = 1 then b.biz_id end) as if_in_fu_sx_refuse,
        count(distinct case when pf.if_normal_ruleDetermine_passed = 1 then b.biz_id end) as if_in_ruleDetermine_data,
        count(distinct case when pf.if_external_data_passed = 1 then b.biz_id end) as if_external_data_passed,
        count(distinct case when pf.if_in_confirm = 1 then b.biz_id end) as if_in_confirm,
        count(distinct case when b.order_status = 372 and cs.biz_id is not null then cs.biz_id end) as sx_cnt,
        sum(cs.grantcredit_amount) as sx_amt,
        sum(case when cs.exchange_rate_to_dollar is not null then cs.grantcredit_amount / cs.exchange_rate_to_dollar else cs.grantcredit_amount / 17 end) as sx_amt_usd,
        sum(cs.apply_amount) as apply_amt,
        count(distinct cs.biz_id) as you_cnt
    from base b
    left join processor_flags pf
        on b.biz_id = pf.biz_id
    left join credit_snapshot cs
        on b.biz_id = cs.biz_id
    left join global_limit_exclude ge
        on b.biz_id = ge.biz_id
    where b.create_date >= date '2023-03-01'
      and ge.biz_id is null
    group by 1,2,3,4,5,6,7,8,9
),
loan_metric as (
select
        b.release_date as data_date,
        b.app_channel,
        b.double_loan,
        b.double_loan_new,
        b.reloan_num,
        1 as indexs,
        b.product_name,
        b.os,
        b.new_media_source,
        count(distinct b.camera_id) as loan_cnt,
        sum(b.contract_amount) as loan_contract_amt,
        sum(b.contract_amount_usd) as loan_contract_amt_usd,
        sum(b.amount) as loan_amt
    from base b
    where b.release_date >= date '2023-03-01'
      and b.loan_state in (1,2,3)
    group by 1,2,3,4,5,6,7,8,9
)
select data_date, app_channel, double_loan, double_loan_new, reloan_num, indexs, product_name, os, new_media_source,
       apply_cnt, pass_cnt,
       cast(0 as double) as loan_cnt, cast(0 as double) as loan_contract_amt,
       cast(0 as double) as loan_contract_amt_usd, cast(0 as double) as loan_amt,
       if_model_passed, if_in_fu_sx_refuse, if_in_ruleDetermine_data, if_external_data_passed,
       sx_cnt, sx_amt, you_cnt, sx_amt_usd, apply_amt, if_in_confirm
from apply_metric
union all
select data_date, app_channel, double_loan, double_loan_new, reloan_num, indexs, product_name, os, new_media_source,
       cast(0 as double), cast(0 as double), loan_cnt, loan_contract_amt, loan_contract_amt_usd, loan_amt,
       cast(0 as double), cast(0 as double), cast(0 as double), cast(0 as double),
       cast(0 as double), cast(0 as double), cast(0 as double), cast(0 as double), cast(0 as double), cast(0 as double)
from loan_metric
;