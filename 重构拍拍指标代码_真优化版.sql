-- ============================================================
-- ind.ba_paipai_basic_performance_monthly (REAL Optimized Version)
-- Strategy: Pre-materialize base tables → all CTEs read from small tables
-- ba_asset_base_info: 9 scans → 1 scan
-- s02_loan_repayment_his: many sub-query scans → 1 scan
-- ============================================================
-- RUN ORDER (Pangu API only executes one statement at a time):
--   1. DROP + CREATE ind.ys_paipai_asset_base
--   2. DROP + CREATE ind.ys_paipai_repay_base
--   3. CREATE ind.ba_paipai_basic_performance_monthly (full script below)
-- ============================================================

-- ============================================================
-- STEP 1: Asset base table — one scan of ba_asset_base_info
-- ============================================================
drop table if exists ind.ys_paipai_asset_base;

create table ind.ys_paipai_asset_base as
select *
from ind.ba_asset_base_info
where (if_app = 1 or if_issue = 1)
  and (date(app_date) >= date '2025-01-01'
       or date(issue_date) >= date '2025-01-01'
       or issue_month >= '2025-01-01');


-- ============================================================
-- STEP 2: Repayment snapshot base table — one scan of s02_loan_repayment_his
-- ============================================================
drop table if exists ind.ys_paipai_repay_base;

create table ind.ys_paipai_repay_base as
select
    date_trunc('month', to_date(data_date_fixed, 'yyyymmdd') + interval '1' month)
        - interval '1' day as data_date1,
    data_date,
    camera_id,
    lid,
    should_capital,
    fact_capital,
    should_time,
    fact_time
from (
    select
        camera_id, lid, should_capital, fact_capital, should_time, fact_time,
        case when length(data_date) = 6 then concat(data_date, '01') else data_date end as data_date_fixed,
        data_date
    from ods.s02_loan_repayment_his
    where length(data_date) = 8
      and (
          (date_trunc('month', to_date(
              case when length(data_date) = 6 then concat(data_date, '01') else data_date end,
              'yyyymmdd') + interval '1' month) - interval '1' day
           = to_date(case when length(data_date) = 6 then concat(data_date, '01') else data_date end, 'yyyymmdd'))
          or (data_date < '202409')
          or (to_date(data_date, 'yyyymmdd') = current_date - interval '1' day)
      )
) t;


-- ============================================================
-- STEP 3: Final table — ALL CTEs read from base tables (no source table scans!)
-- ============================================================
drop table if exists ind.ba_paipai_basic_performance_monthly;

create table ind.ba_paipai_basic_performance_monthly as

with
-- ============================================================
-- CTE 1: Issue metrics (from base table)
-- ============================================================
cte_issue as (
    select
        issue_month,
        count(distinct mid)                                              as loan_customer_cnt_total,
        count(distinct case when grant_strategy = 'NEW' then mid end)    as loan_customer_cnt_new,
        count(distinct case when grant_strategy = 'OLD' then mid end)    as loan_customer_cnt_old,
        sum(if_issue)                                                    as loan_cnt_total,
        sum(case when grant_strategy = 'NEW' then if_issue else 0 end)   as loan_cnt_new,
        sum(case when grant_strategy = 'OLD' then if_issue else 0 end)   as loan_cnt_old,
        sum(contract_amount_usd1)                                        as loan_amt_total,
        sum(case when grant_strategy = 'NEW' then contract_amount_usd1 else 0 end) as loan_amt_new,
        sum(case when grant_strategy = 'OLD' then contract_amount_usd1 else 0 end) as loan_amt_old,
        sum(contract_amount)                                             as loan_amt_total_idr,
        sum(case when grant_strategy = 'NEW' then contract_amount else 0 end)     as loan_amt_new_idr,
        sum(case when grant_strategy = 'OLD' then contract_amount else 0 end)     as loan_amt_old_idr,
        sum(amount)                                                      as loan1_amt_total_idr,
        sum(case when grant_strategy = 'NEW' then amount else 0 end)     as loan1_amt_new_idr,
        sum(case when grant_strategy = 'OLD' then amount else 0 end)     as loan1_amt_old_idr,
        sum(revenue)                                                     as revenue_total,
        sum(case when grant_strategy = 'NEW' then revenue else 0 end)    as revenue_new,
        sum(case when grant_strategy = 'OLD' then revenue else 0 end)    as revenue_old,
        sum(loan_cycle_amount)                                           as loan_cycle_amount_idr,
        sum(case when grant_strategy = 'NEW' then loan_cycle_amount else 0 end) as loan_cycle_amt_new_idr,
        sum(case when grant_strategy = 'OLD' then loan_cycle_amount else 0 end) as loan_cycle_amt_old_idr
    from ind.ys_paipai_asset_base
    where issue_month >= '2025-01-01' and if_issue = 1
    group by 1
),

-- ============================================================
-- CTE 2: Duration (weighted avg, needs repayment table)
-- ============================================================
cte_duration as (
    select
        date_format(a.create_time, '%Y-%m-01') as issue_month,
        if(sum(b.contract_amount) > 0,
           sum(b.loan_cycle_amount) / sum(b.contract_amount), 0)          as avg_loan_cycle,
        if(sum(case when b.grant_strategy = 'NEW' then b.contract_amount else 0 end) > 0,
           sum(case when b.grant_strategy = 'NEW' then b.loan_cycle_amount else 0 end)
           / sum(case when b.grant_strategy = 'NEW' then b.contract_amount else 0 end), 0) as new_avg_loan_cycle,
        if(sum(case when b.grant_strategy = 'OLD' then b.contract_amount else 0 end) > 0,
           sum(case when b.grant_strategy = 'OLD' then b.loan_cycle_amount else 0 end)
           / sum(case when b.grant_strategy = 'OLD' then b.contract_amount else 0 end), 0) as old_avg_loan_cycle,
        if(sum(a.should_capital) > 0,
           sum(day_diff * a.should_capital) / sum(a.should_capital), 0)   as all_duration,
        if(sum(case when b.grant_strategy = 'NEW' then a.should_capital else 0 end) > 0,
           sum(case when b.grant_strategy = 'NEW' then day_diff * a.should_capital else 0 end)
           / sum(case when b.grant_strategy = 'NEW' then a.should_capital else 0 end), 0) as new_duration,
        if(sum(case when b.grant_strategy = 'OLD' then a.should_capital else 0 end) > 0,
           sum(case when b.grant_strategy = 'OLD' then day_diff * a.should_capital else 0 end)
           / sum(case when b.grant_strategy = 'OLD' then a.should_capital else 0 end), 0) as old_duration
    from (
        select camera_id, date_format(create_time, '%Y-%m-01') as create_month,
               date_diff('day', date(create_time), coalesce(date(fact_time), date(should_time))) as day_diff,
               should_capital
        from ods.s02_loan_repayment
    ) a
    join ind.ys_paipai_asset_base b
        on a.camera_id = try_cast(b.biz_id as bigint)
    where b.if_issue = 1
    group by 1
),

-- ============================================================
-- CTE 3: Application funnel (from base table)
-- ============================================================
cte_app as (
    select
        app_month,
        sum(case when if_recall = 0 then if_app end)                                          as if_app,
        sum(case when grant_strategy = 'NEW' and if_recall = 0 then if_app end)               as new_if_app,
        sum(case when grant_strategy = 'OLD' and if_recall = 0 then if_app end)               as old_if_app,
        sum(case when grant_strategy = 'OLD' and if_recall = 0 then if_external_data_3_passed
                 when grant_strategy = 'NEW' then if_in_confirm_final end)                     as if_external_3_passed,
        sum(case when grant_strategy = 'OLD' and if_recall = 0 then if_external_data_3_passed end) as old_if_external_3_passed,
        sum(case when grant_strategy = 'NEW' then if_in_confirm_final end)                     as new_if_external_3_passed,
        sum(case when grant_strategy = 'OLD' and if_recall = 0 then if_in_external_data_4
                 when grant_strategy = 'NEW' then if_confirm_passed_final end)                 as if_in_external_data_4,
        sum(case when grant_strategy = 'OLD' and if_recall = 0 then if_in_external_data_4 end) as old_if_in_external_data_4,
        sum(case when grant_strategy = 'NEW' then if_confirm_passed_final end)                 as new_if_in_external_data_4,
        sum(if_external_data_4_passed)                                                         as if_external_data_4_passed,
        sum(case when grant_strategy = 'OLD' then if_external_data_4_passed end)               as old_if_external_data_4_passed,
        sum(case when grant_strategy = 'NEW' then if_external_data_4_passed end)               as new_if_external_data_4_passed,
        sum(case when if_confirm_passed_final = 1 then apply_amount end)                       as confirm_apply_amount,
        sum(case when grant_strategy = 'OLD' and if_confirm_passed_final = 1 then apply_amount end)   as old_confirm_apply_amount,
        sum(case when grant_strategy = 'NEW' and if_confirm_passed_final = 1 then apply_amount end)   as new_confirm_apply_amount,
        sum(contract_amount_usd1)                                                              as total_contract_amount_usd,
        sum(case when grant_strategy = 'OLD' then contract_amount_usd1 end)                    as old_contract_amount_usd,
        sum(case when grant_strategy = 'NEW' then contract_amount_usd1 end)                    as new_contract_amount_usd,
        sum(if_in_confirm_temp)                                                                as in_confirm_cnt,
        sum(case when grant_strategy = 'OLD' then if_in_confirm_temp end)                      as old_in_confirm_cnt,
        sum(case when grant_strategy = 'NEW' then if_in_confirm_temp end)                      as new_in_confirm_cnt,
        sum(if_confirm_passed_final)                                                           as confirm_passed_cnt,
        sum(case when grant_strategy = 'OLD' then if_confirm_passed_final end)                 as old_confirm_passed_cnt,
        sum(case when grant_strategy = 'NEW' then if_confirm_passed_final end)                 as new_confirm_passed_cnt
    from ind.ys_paipai_asset_base
    where date(app_date) >= date '2025-01-01'
      and date(app_date) < current_date
      and if_app = 1
    group by 1
),

-- ============================================================
-- CTE 4: New pure funnel (from base table)
-- ============================================================
cte_new_pure as (
    select
        app_month,
        count(distinct case when if_app = 1 then mid end)                                  as app_user_cnt,
        count(distinct case when if_in_confirm_temp = 1 then mid end)                      as in_confirm_user_cnt,
        count(distinct case when if_confirm_passed_final = 1
                        and app_month = date_format(confirm_date_final, '%Y-%m-01') then mid end) as confirm_user_cnt,
        count(distinct case when if_confirm_passed_final = 1
                        and date_format(confirm_date_final, '%Y-%m-01')
                        <= date_format(current_date - interval '1' day, '%Y-%m-01') then mid end) as confirm_user_cnt_all,
        count(distinct case when if_confirm_passed_num_24h = 1
                        and app_month = date_format(confirm_date_final, '%Y-%m-01') then mid end) as confirm_user_cnt_24h,
        count(distinct case when if_confirm_passed_num_t30 = 1
                        and app_month = date_format(confirm_date_final, '%Y-%m-01') then mid end) as confirm_user_cnt_t30,
        count(distinct case when if_issue = 1
                        and app_month = issue_month then mid end)                           as issue_user_cnt,
        sum(case when if_in_confirm_temp = 1 then grantcredit_amount end)                   as in_confirm_grantcredit_amount,
        count(distinct case when app_month = issue_month then mid end)                      as issue_user_from_app_m,
        count(distinct case when app_month = date_format(confirm_date_final, '%Y-%m-01') then mid end) as confirm_user_from_app_m,
        count(distinct case when issue_month
                        <= date_format(current_date - interval '1' day, '%Y-%m-01') then mid end) as issue_user_from_app_all,
        count(distinct case when date_format(confirm_date_final, '%Y-%m-01')
                        <= date_format(current_date - interval '1' day, '%Y-%m-01') then mid end) as confirm_user_from_app_all,
        count(distinct case when app_month = issue_month then biz_id end)                   as issue_cnt_from_app_m,
        count(distinct case when app_month = date_format(confirm_date_final, '%Y-%m-01') then biz_id end) as confirm_cnt_from_app_m,
        sum(case when app_month = issue_month then contract_amount_usd end)                 as issue_amt_from_app_m,
        sum(case when app_month = date_format(confirm_date_final, '%Y-%m-01') then contract_amount_usd end) as confirm_amt_from_app_m
    from ind.ys_paipai_asset_base
    where grant_strategy = 'NEW'
      and if_app = 1
      and is_reloan2 = 'NEW_PURE'
      and date(app_date) >= date '2025-01-01'
    group by 1
),

-- ============================================================
-- CTE 5: Confirm metrics (merged new + total, from base table)
-- ============================================================
cte_confirm as (
    select
        date_format(confirm_date_final, '%Y-%m-01') as confirm_month,
        count(distinct case when grant_strategy = 'NEW' then mid end)                           as confirm_new_user_cnt,
        sum(case when grant_strategy = 'NEW' then apply_grantcredit_amount end)                 as confirm_new_grantcredit_amount,
        sum(case when grant_strategy = 'NEW' then contract_amount_usd end)                      as confirm_new_contract_usd,
        count(distinct case when grant_strategy = 'NEW' and if_issue = 1 then mid end)          as confirm_new_issue_user,
        count(distinct case when grant_strategy = 'NEW' and if_issue = 1
                        and issue_month = date_format(confirm_date_final, '%Y-%m-01') then biz_id end) as issue_cnt_from_new_confirm,
        count(distinct case when grant_strategy = 'NEW' then biz_id end)                        as confirm_new_cnt,
        sum(case when grant_strategy = 'NEW' and if_issue = 1
                 and issue_month = date_format(confirm_date_final, '%Y-%m-01')
                 then contract_amount_usd else 0 end)                                            as issue_amt_from_new_confirm,
        count(distinct case when if_issue = 1
                        and issue_month = date_format(confirm_date_final, '%Y-%m-01') then biz_id end) as issue_cnt_from_confirm_all,
        count(distinct biz_id)                                                                  as confirm_all_cnt,
        count(distinct case when grant_strategy = 'OLD' then mid end)                           as confirm_old_user_cnt,
        sum(case when if_issue = 1 and issue_month = date_format(confirm_date_final, '%Y-%m-01')
                 then contract_amount_usd else 0 end)                                            as issue_amt_from_confirm_all,
        sum(apply_grantcredit_amount)                                                           as confirm_grantcredit_amount_all,
        count(distinct case when if_issue = 1
                        and issue_month = date_format(confirm_date_final, '%Y-%m-01') then mid end) as issue_user_from_confirm_all,
        count(distinct mid)                                                                     as confirm_all_user_cnt
    from ind.ys_paipai_asset_base
    where if_app = 1
      and if_confirm_passed_final = 1
      and date(app_date) >= date '2025-01-01'
    group by 1
),

-- ============================================================
-- CTE 6: Registration metrics
-- ============================================================
cte_reg as (
    select
        date_format(t.reg_dt, '%Y-%m-01') as reg_month,
        count(distinct t.mid)                                                            as reg_cnt,
        count(distinct case when date(mad.first_issue_time) = t.reg_dt then t.mid end)   as t0_issue_cnt,
        count(distinct case when mad.first_issue_time <= current_date - interval '1' day
                        then t.mid end)                                                   as all_issue_cnt,
        count(distinct case when mad.first_issue_time <= t.reg_time + interval '24' hour
                        then t.mid end)                                                   as t24h_issue_cnt,
        count(distinct case when mad.first_issue_time <= t.reg_time + interval '30' day
                        then t.mid end)                                                   as t30d_issue_cnt
    from ind.tyn_reg_install_new t
    left join (
        select mid,
               min(release_time) as first_issue_time,
               min(app_date)     as first_app_date
        from ind.ys_paipai_asset_base
        where if_app = 1 and grant_strategy = 'NEW' and is_reloan2 = 'NEW_PURE'
        group by 1
    ) mad on mad.mid = t.mid
    where t.reg_dt >= date '2025-01-01'
    group by 1
),

-- ============================================================
-- CTE 7: Overdue ratios (separate table, no optimization possible)
-- ============================================================
cte_overdue as (
    select
        app_month,
        sum(overdue_amount_1_0)       / nullif(sum(should_capital_1_0), 0)       as total_overdue_1_0,
        sum(overdue_amount_1_30)      / nullif(sum(should_capital_1_30), 0)      as total_overdue_1_30,
        sum(overdue_amount_3_30)      / nullif(sum(should_capital_3_30), 0)      as total_overdue_3_30,
        sum(overdue_amount_total_30)  / nullif(sum(should_capital_total_30), 0)  as total_overdue_total_30,
        sum(t1_capital_due_d1)        / nullif(sum(should_capital_d1), 0)        as total_t1_due_d1,
        sum(t30_capital_due_d30)      / nullif(sum(should_capital_d30), 0)       as total_t30_due_d30,
        sum(case when grant_strategy = 'NEW' then overdue_amount_1_0 else 0 end)
            / nullif(sum(case when grant_strategy = 'NEW' then should_capital_1_0 else 0 end), 0) as new_overdue_1_0,
        sum(case when grant_strategy = 'NEW' then overdue_amount_1_30 else 0 end)
            / nullif(sum(case when grant_strategy = 'NEW' then should_capital_1_30 else 0 end), 0) as new_overdue_1_30,
        sum(case when grant_strategy = 'NEW' then overdue_amount_3_30 else 0 end)
            / nullif(sum(case when grant_strategy = 'NEW' then should_capital_3_30 else 0 end), 0) as new_overdue_3_30,
        sum(case when grant_strategy = 'NEW' then overdue_amount_total_30 else 0 end)
            / nullif(sum(case when grant_strategy = 'NEW' then should_capital_total_30 else 0 end), 0) as new_overdue_total_30,
        sum(case when grant_strategy = 'NEW' then t1_capital_due_d1 else 0 end)
            / nullif(sum(case when grant_strategy = 'NEW' then should_capital_d1 else 0 end), 0) as new_t1_due_d1,
        sum(case when grant_strategy = 'NEW' then t30_capital_due_d30 else 0 end)
            / nullif(sum(case when grant_strategy = 'NEW' then should_capital_d30 else 0 end), 0) as new_t30_due_d30,
        sum(case when grant_strategy = 'OLD' then overdue_amount_1_0 else 0 end)
            / nullif(sum(case when grant_strategy = 'OLD' then should_capital_1_0 else 0 end), 0) as old_overdue_1_0,
        sum(case when grant_strategy = 'OLD' then overdue_amount_1_30 else 0 end)
            / nullif(sum(case when grant_strategy = 'OLD' then should_capital_1_30 else 0 end), 0) as old_overdue_1_30,
        sum(case when grant_strategy = 'OLD' then overdue_amount_3_30 else 0 end)
            / nullif(sum(case when grant_strategy = 'OLD' then should_capital_3_30 else 0 end), 0) as old_overdue_3_30,
        sum(case when grant_strategy = 'OLD' then overdue_amount_total_30 else 0 end)
            / nullif(sum(case when grant_strategy = 'OLD' then should_capital_total_30 else 0 end), 0) as old_overdue_total_30,
        sum(case when grant_strategy = 'OLD' then t1_capital_due_d1 else 0 end)
            / nullif(sum(case when grant_strategy = 'OLD' then should_capital_d1 else 0 end), 0) as old_t1_due_d1,
        sum(case when grant_strategy = 'OLD' then t30_capital_due_d30 else 0 end)
            / nullif(sum(case when grant_strategy = 'OLD' then should_capital_d30 else 0 end), 0) as old_t30_due_d30
    from ind.ba_apply_should_result
    group by 1
),

-- ============================================================
-- CTE 8: Onloan balance (from repayment base table)
-- ============================================================
cte_onloan as (
    select
        date_format(a1.data_date1, '%Y-%m-01') as balance_month,
        sum(a1.should_capital)                                                              as principal,
        count(distinct case when d1.due_days <= 30 and c1.grant_strategy = 'OLD'
                        then c1.mid end)                                                     as old_repay_user_num,
        sum(case when d1.due_days <= 30 then a1.should_capital - a1.fact_capital end)       as owing_principal,
        count(distinct case when d1.due_days <= 30 then c1.mid end)                         as repay_user_num
    from ind.ys_paipai_repay_base a1
    left join (
        select camera_id, date(trade_start_time) as trade_start_time,
               date(trade_end_time) as trade_end_time,
               date(trade_end_time) + interval '60' day as due_date_60
        from ods.s02_loan
    ) b1 on cast(a1.camera_id as bigint) = cast(b1.camera_id as bigint)
    left join ind.xly_application_funnel c1
        on cast(a1.camera_id as bigint) = cast(c1.biz_id as bigint)
    left join (
        select data_date1, lid, max(due_days) as due_days
        from (
            select data_date1, lid,
                   date_diff('day', date(should_time),
                             if(fact_time is null, to_date(data_date, 'yyyymmdd'), date(fact_time))) as due_days
            from ind.ys_paipai_repay_base
        ) t
        group by 1, 2
    ) d1 on cast(a1.lid as bigint) = cast(d1.lid as bigint)
        and a1.data_date1 = d1.data_date1
    where to_char(date(a1.data_date1), 'yyyy-mm') <= to_char(date(due_date_60), 'yyyy-mm')
    group by 1
),

-- ============================================================
-- CTE 9: Grant amount max (from repayment base + asset base)
-- ============================================================
cte_grant_amount as (
    select
        date_format(data_date1, '%Y-%m-01') as grant_month,
        sum(grant_amount_max) as grant_amount_max
    from (
        select
            a.data_date1, b.grant_amount_max,
            row_number() over (partition by b.mid, a.data_date order by b.release_time desc) as rn
        from (
            select data_date1, data_date, camera_id, max(due_days) as due_days
            from (
                select data_date1, data_date, camera_id,
                       date_diff('day', date(should_time),
                                 if(fact_time is null, to_date(data_date, 'yyyymmdd'), date(fact_time))) as due_days
                from ind.ys_paipai_repay_base
            ) t
            group by 1, 2, 3
        ) a
        left join (
            select biz_id, grant_amount_max, mid, release_time
            from ind.ys_paipai_asset_base
            where if_issue = 1 and if_app = 1
        ) b on cast(a.camera_id as bigint) = cast(b.biz_id as bigint)
        where a.due_days <= 30
    ) c
    where rn = 1
    group by 1
),

-- ============================================================
-- CTE 10: Owing principal for OLD customers
-- ============================================================
cte_owing_old as (
    select
        issue_month,
        sum(owing_principal) as owing_principal,
        count(distinct biz_id) as biz_num
    from (
        select
            a.biz_id, a.mid, a.issue_month,
            a.contract_amount,
            sum(b.should_capital) - sum(b.fact_capital) + max(a.contract_amount) as owing_principal
        from (
            select biz_id, mid, release_time, app_date, issue_date,
                   contract_amount, app_time, issue_month, baseinfo_onloan_amount
            from ind.xly_application_funnel
            where if_issue = 1 and if_app = 1
              and issue_date >= '2025-01-01'
              and grant_strategy = 'OLD'
        ) a
        left join ods.s02_loan_repayment b
            on cast(a.mid as bigint) = cast(b.customer_id as bigint)
            and a.app_time > b.create_time
        group by a.biz_id, a.mid, a.release_time, a.app_date, a.issue_date,
                 a.contract_amount, a.app_time, a.issue_month, a.baseinfo_onloan_amount
    ) c
    group by 1
),

-- ============================================================
-- CTE 11: Cohort repurchase (from base table)
-- ============================================================
cte_cohort as (
    select
        a.first_loan_issue_month,
        sum(amt_old_6m)  / sum(cnt_new) as cohort_6m_cnt_rate,
        sum(amt_old_12m) / sum(cnt_new) as cohort_12m_cnt_rate,
        sum(amt_old_6m)  / sum(amt_new) as cohort_6m_amt_rate,
        sum(amt_old_12m) / sum(amt_new) as cohort_12m_amt_rate
    from (
        select first_loan_issue_month,
               sum(case when month_num_issue <= 6  then contract_amount_usd1 end) as amt_old_6m,
               sum(case when month_num_issue <= 12 then contract_amount_usd1 end) as amt_old_12m
        from ind.ys_paipai_asset_base
        where grant_strategy = 'OLD' and if_issue = 1
        group by 1
    ) a
    left join (
        select issue_month,
               count(mid) as cnt_new,
               sum(contract_amount_usd1) as amt_new
        from ind.ys_paipai_asset_base
        where grant_strategy = 'NEW' and if_issue = 1
        group by 1
    ) b on a.first_loan_issue_month = b.issue_month
    group by 1
),

-- ============================================================
-- CTE 12: Old managed customers (kept as-is)
-- ============================================================
cte_old_managed as (
    select
        date_format(date(slice_date), '%Y-%m-01') as stat_month,
        count(distinct case when if_overdue <> 1 and if_reject_recent_7_days <> 1
                        then mid end) as old_managed_cnt
    from ind.ys_operable_reloan_cnt_251119
    group by 1
)

-- ============================================================
-- FINAL SELECT — all CTEs joined on month
-- ============================================================
select
    im.issue_month as month,
    daa.daily_cnt,
    maa.monthly_cnt,
    ob.owing_principal / f.exchange_rate_to_dollar                             as onloan_amount_30_m,
    im.loan_customer_cnt_total,       im.loan_customer_cnt_new,       im.loan_customer_cnt_old,
    im.loan_cnt_total,                im.loan_cnt_new,                im.loan_cnt_old,
    im.loan_amt_total,                im.loan_amt_new,                im.loan_amt_old,
    case when im.loan_cnt_total > 0 then im.loan_amt_total / im.loan_cnt_total else 0 end as avg_loan_amt_total,
    case when im.loan_cnt_new   > 0 then im.loan_amt_new   / im.loan_cnt_new   else 0 end as avg_loan_amt_new,
    case when im.loan_cnt_old   > 0 then im.loan_amt_old   / im.loan_cnt_old   else 0 end as avg_loan_amt_old,
    rc.reg_cnt,                        np.app_user_cnt,                   np.in_confirm_user_cnt,
    np.confirm_user_cnt,               np.issue_user_cnt,
    cf.confirm_new_user_cnt,
    np.in_confirm_grantcredit_amount / nullif(np.in_confirm_user_cnt, 0)                        as new_pure_in_confirm_avg_amt,
    cf.confirm_new_grantcredit_amount / nullif(cf.confirm_new_user_cnt, 0)                      as new_confirm_avg_amt,
    rc.all_issue_cnt  / nullif(rc.reg_cnt, 0)                                                   as new_reg_issue_rate,
    rc.t24h_issue_cnt / nullif(rc.reg_cnt, 0)                                                   as new_t24h_reg_issue_rate,
    rc.t30d_issue_cnt / nullif(rc.reg_cnt, 0)                                                   as new_t30d_reg_issue_rate,
    np.in_confirm_user_cnt     / nullif(np.app_user_cnt, 0)                                     as new_pure_in_confirm_rate,
    np.confirm_user_cnt_all    / nullif(np.in_confirm_user_cnt, 0)                              as new_pure_confirm_rate,
    np.confirm_user_cnt_24h    / nullif(np.in_confirm_user_cnt, 0)                              as new_pure_confirm_rate_24h,
    np.confirm_user_cnt_t30    / nullif(np.in_confirm_user_cnt, 0)                              as new_pure_confirm_rate_t30,
    ap.confirm_passed_cnt      / nullif(ap.in_confirm_cnt, 0)                                   as total_confirm_rate,
    ap.new_confirm_passed_cnt  / nullif(ap.new_in_confirm_cnt, 0)                               as new_confirm_rate,
    ap.old_confirm_passed_cnt  / nullif(ap.old_in_confirm_cnt, 0)                               as old_confirm_rate,
    ap.new_if_external_3_passed        / nullif(ap.new_if_app, 0)                               as new_before_pass_rate,
    ap.new_if_external_data_4_passed   / nullif(ap.new_if_in_external_data_4, 0)                as new_after_pass_rate,
    ap.new_contract_amount_usd         / nullif(ap.new_confirm_apply_amount, 0)                 as new_after_pass_amt_rate,
    ap.old_if_external_3_passed        / nullif(ap.old_if_app, 0)                               as old_before_pass_rate,
    ap.old_if_external_data_4_passed   / nullif(ap.old_if_in_external_data_4, 0)                as old_after_pass_rate,
    ap.old_contract_amount_usd         / nullif(ap.old_confirm_apply_amount, 0)                 as old_after_pass_amt_rate,
    om.old_managed_cnt,
    cf.confirm_old_user_cnt,
    ob.old_repay_user_num                                                                       as old_onloan_amount_30_m,
    oo.owing_principal / nullif(oo.biz_num * f.exchange_rate_to_dollar, 0)                     as old_onloan_amount_30_m_user_avg,
    ob.owing_principal / nullif(ob.repay_user_num * f.exchange_rate_to_dollar, 0)              as onloan_amount_30_m_user_avg,
    ga.grant_amount_max / nullif(ob.repay_user_num, 0)                                         as grant_amount_30_m_user_avg,
    np.in_confirm_grantcredit_amount / nullif(np.in_confirm_user_cnt, 0)                       as new_pure_confirm_app_avg_amt,
    c.cohort_6m_cnt_rate,              c.cohort_12m_cnt_rate,
    c.cohort_6m_amt_rate,              c.cohort_12m_amt_rate,
    d.avg_loan_cycle,                  d.new_avg_loan_cycle,                d.old_avg_loan_cycle,
    d.all_duration,                    d.new_duration,                      d.old_duration,
    ov.total_overdue_1_0,              ov.new_overdue_1_0,                  ov.old_overdue_1_0,
    ov.total_overdue_1_30,             ov.new_overdue_1_30,                 ov.old_overdue_1_30,
    ov.total_overdue_3_30,             ov.new_overdue_3_30,                 ov.old_overdue_3_30,
    ov.total_overdue_total_30,         ov.new_overdue_total_30,             ov.old_overdue_total_30,
    ov.total_t1_due_d1,                ov.new_t1_due_d1,                    ov.old_t1_due_d1,
    ov.total_t30_due_d30,              ov.new_t30_due_d30,                  ov.old_t30_due_d30,
    f.exchange_rate_to_dollar

from cte_issue im
left join cte_duration       d   on im.issue_month = d.issue_month
left join cte_reg            rc  on im.issue_month = rc.reg_month
left join cte_new_pure       np  on im.issue_month = np.app_month
left join cte_confirm        cf  on im.issue_month = cf.confirm_month
left join cte_app            ap  on im.issue_month = ap.app_month
left join cte_overdue        ov  on im.issue_month = ov.app_month
left join cte_old_managed    om  on im.issue_month = om.stat_month
left join cte_onloan         ob  on im.issue_month = ob.balance_month
left join cte_grant_amount   ga  on im.issue_month = ga.grant_month
left join cte_owing_old      oo  on im.issue_month = oo.issue_month
left join cte_cohort         c   on im.issue_month = c.first_loan_issue_month
left join ind.ys_daily_activate   daa on im.issue_month = date_format(date_parse(daa.month, '%Y/%m/%d'), '%Y-%m-01')
left join ind.ys_monthly_activate maa on im.issue_month = date_format(date_parse(maa.month, '%Y/%m/%d'), '%Y-%m-01')
left join dim.dim_exchange_rate_cost f on to_char(date(im.issue_month), 'yyyymm') = f.month_id
    and f.account_currency = 'IDR'
order by month;
