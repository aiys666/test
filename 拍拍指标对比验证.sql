-- ============================================================
-- Validation: Original vs Optimized ba_paipai_basic_performance_monthly
-- ============================================================

-- 1. Row count comparison
select 'row_count' as check_type,
       (select count(*) from ind.ba_paipai_basic_performance_monthly_orig) as orig_rows,
       (select count(*) from ind.ba_paipai_basic_performance_monthly_opt)  as opt_rows,
       (select count(*) from ind.ba_paipai_basic_performance_monthly_orig) -
       (select count(*) from ind.ba_paipai_basic_performance_monthly_opt)  as diff;

-- 2. Month comparison: any months missing or extra?
select 'month_diff' as check_type,
       array_agg(distinct o.month) filter (where t.month is null) as only_in_orig,
       array_agg(distinct t.month) filter (where o.month is null) as only_in_opt
from ind.ba_paipai_basic_performance_monthly_orig o
full join ind.ba_paipai_basic_performance_monthly_opt t on o.month = t.month;

-- 3. Column-by-column numeric difference check
-- Find any column where the absolute difference > 0.01
with diffs as (
    select
        o.month,
        'loan_customer_cnt_total' as col, abs(o.loan_customer_cnt_total - t.loan_customer_cnt_total) as diff
    from ind.ba_paipai_basic_performance_monthly_orig o
    join ind.ba_paipai_basic_performance_monthly_opt t on o.month = t.month
    where abs(o.loan_customer_cnt_total - t.loan_customer_cnt_total) > 0.01
    union all
    select o.month, 'loan_cnt_total', abs(o.loan_cnt_total - t.loan_cnt_total)
    from ind.ba_paipai_basic_performance_monthly_orig o
    join ind.ba_paipai_basic_performance_monthly_opt t on o.month = t.month
    where abs(o.loan_cnt_total - t.loan_cnt_total) > 0.01
    union all
    select o.month, 'loan_amt_total', abs(o.loan_amt_total - t.loan_amt_total)
    from ind.ba_paipai_basic_performance_monthly_orig o
    join ind.ba_paipai_basic_performance_monthly_opt t on o.month = t.month
    where abs(o.loan_amt_total - t.loan_amt_total) > 0.01
    union all
    select o.month, 'avg_loan_amt_total', abs(o.avg_loan_amt_total - t.avg_loan_amt_total)
    from ind.ba_paipai_basic_performance_monthly_orig o
    join ind.ba_paipai_basic_performance_monthly_opt t on o.month = t.month
    where abs(o.avg_loan_amt_total - t.avg_loan_amt_total) > 0.01
    union all
    select o.month, 'new_confirm_rate', abs(o.new_confirm_rate - t.new_confirm_rate)
    from ind.ba_paipai_basic_performance_monthly_orig o
    join ind.ba_paipai_basic_performance_monthly_opt t on o.month = t.month
    where abs(o.new_confirm_rate - t.new_confirm_rate) > 0.0001
    union all
    select o.month, 'old_confirm_rate', abs(o.old_confirm_rate - t.old_confirm_rate)
    from ind.ba_paipai_basic_performance_monthly_orig o
    join ind.ba_paipai_basic_performance_monthly_opt t on o.month = t.month
    where abs(o.old_confirm_rate - t.old_confirm_rate) > 0.0001
    union all
    select o.month, 'total_confirm_rate', abs(o.total_confirm_rate - t.total_confirm_rate)
    from ind.ba_paipai_basic_performance_monthly_orig o
    join ind.ba_paipai_basic_performance_monthly_opt t on o.month = t.month
    where abs(o.total_confirm_rate - t.total_confirm_rate) > 0.0001
    union all
    select o.month, 'onloan_amount_30_m', abs(o.onloan_amount_30_m - t.onloan_amount_30_m)
    from ind.ba_paipai_basic_performance_monthly_orig o
    join ind.ba_paipai_basic_performance_monthly_opt t on o.month = t.month
    where abs(o.onloan_amount_30_m - t.onloan_amount_30_m) > 0.01
    union all
    select o.month, 'old_managed_cnt', abs(o.old_managed_cnt - t.old_managed_cnt)
    from ind.ba_paipai_basic_performance_monthly_orig o
    join ind.ba_paipai_basic_performance_monthly_opt t on o.month = t.month
    where abs(o.old_managed_cnt - t.old_managed_cnt) > 0.01
    union all
    select o.month, 'cohort_6m_cnt_rate', abs(o.cohort_6m_cnt_rate - t.cohort_6m_cnt_rate)
    from ind.ba_paipai_basic_performance_monthly_orig o
    join ind.ba_paipai_basic_performance_monthly_opt t on o.month = t.month
    where abs(o.cohort_6m_cnt_rate - t.cohort_6m_cnt_rate) > 0.0001
    union all
    select o.month, 'total_overdue_1_30', abs(o.total_overdue_1_30 - t.total_overdue_1_30)
    from ind.ba_paipai_basic_performance_monthly_orig o
    join ind.ba_paipai_basic_performance_monthly_opt t on o.month = t.month
    where abs(o.total_overdue_1_30 - t.total_overdue_1_30) > 0.0001
)
select * from diffs order by month, col
limit 200;
