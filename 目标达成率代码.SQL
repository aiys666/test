drop table if exists ind.cyl_user_indicator;
create table
if not exists ind.cyl_user_indicator as
select
  a.mid,
  a.is_reloan2,
  a.grant_strategy,
  a.app_month,
  a.biz_id,
  a.if_app,
  a.if_issue,
  CASE
    WHEN if_recall = 0 then if_model_passed
    when if_recall = 1
    and if_in_confirm_final = 1 then 1
    else 0
  end as if_model_passed,
  if_in_confirm_final,
  if_confirm_passed_final,
  confirm_date_final,
  CASE
    WHEN a.loan_type2 = 'loop' then if_app
    when if_recall = 0 then if_external_data_3_passed
    when grant_strategy = 'NEW'
    and if_recall = 1
    and if_in_confirm_final = 1
    and if_confirm_passed_final = 1 then 1
    when grant_strategy = 'OLD'
    and if_recall = 1
    and if_in_confirm_final = 1 then 1
    else 0
  end as if_external_data_3_passed,
  CASE
    WHEN if_recall = 0 then if_in_external_data_4
    when if_recall = 1
    and if_in_confirm_final = 1
    and if_confirm_passed_final = 1 then 1
    else 0
  end as if_in_external_data_4,
  CASE
    WHEN if_recall = 0 then if_external_data_4_passed
    when if_recall = 1
    and if_in_confirm_final = 1
    and if_confirm_passed_final = 1 then 1
    else 0
  end as if_external_data_4_passed,
  if_pass,
  a.contract_amount,
  a.contract_amount * 1.00000 / f.exchange_rate_to_dollar as contract_amount_usd,
  a.contract_amount * 1.00000 / f1.exchange_rate_to_dollar as contract_amount_usd1,
  g.sign_date as sign_date,
  (
    year (date (a.app_date)) - year (date (b.issue_date))
  ) * 12 + (
    month (date (a.app_date)) - month (date (b.issue_date))
  ) month_num,
  a.loan_cycle as loan_cycle_old,
  a.interval_start as interval_start_old,
  a.issue_month as issue_month_old,
  case
    when a.product_level like 'M%' then 'M'
    when a.product_level in (
      'A14',
      'B10',
      'B12',
      'C8',
      'A15',
      'B13',
      'B14',
      'C9',
      'A16',
      'B15',
      'B16',
      'C10',
      'G1',
      'G2',
      'H1',
      'H2',
      'H3',
      'H4',
      'I1',
      'I2',
      'I3',
      'I4',
      'I5'
    ) then 'F-NofeeNew'
    when lower(a.product_level) like '%h%' then 'F-NofeeNew'
    when lower(a.product_level) like '%g%' then 'F-NofeeNew'
    when a.product_level in ('B7', 'C7', 'A9', 'B8') then 'F-NofeeOld'
    when a.product_level like 'D%'
    or a.product_level like 'E%'
    or a.product_level like 'F%' then 'R-30'
    when a.product_level is not null then 'R-15'
    else 'other'
  end as product_level_type_1,
  case
    when a.product_level like 'M%' then 'M'
    when a.product_level in (
      'A14',
      'B10',
      'B12',
      'C8',
      'A15',
      'B13',
      'B14',
      'C9',
      'A16',
      'B15',
      'B16',
      'C10',
      'G1',
      'G2',
      'H1',
      'H2',
      'H3',
      'H4',
      'I1',
      'I2',
      'I3',
      'I4',
      'I5'
    ) then 'F-NofeeNew'
    when lower(a.product_level) like '%h%' then 'F-NofeeNew'
    when lower(a.product_level) like '%g%' then 'F-NofeeNew'
    when a.product_level in ('B7', 'C7', 'A9', 'B8') then 'F-NofeeOld'
    when a.product_level is not null then 'R'
    else 'other'
  end as product_level_type_old,
  a.new_grade_level as grade_level_old,
  a.loan_type2,
  a.loan_indexs as loan_indexs_old,
  a.reloan_num,
  b.new_grade_level as grade_level_new,
  b.product_level_type as product_level_type_new,
  b.issue_month as issue_month_new,
  b.is_reloan2 as is_reloan2_new,
  b.loan_cycle as loan_cycle_new,
  b.loan_indexs as loan_indexs_new,
  h.min_overdue7_black_date,
  (
    year (date (h.min_overdue7_black_date)) - year (a.release_time)
  ) * 12 + (
    month (date (h.min_overdue7_black_date)) - month (a.release_time)
  ) overdue7_black_month_num,
  to_char (date (h.min_overdue7_black_date), 'yyyy-mm') overdue7_black_month,
  h1.min_overdue15_black_date,
  (
    year (date (h1.min_overdue15_black_date)) - year (a.release_time)
  ) * 12 + (
    month (date (h1.min_overdue15_black_date)) - month (a.release_time)
  ) overdue15_black_month_num,
  to_char (date (h1.min_overdue15_black_date), 'yyyy-mm') overdue15_black_month,
  grantcredit_amount_final * 1.00000 / f.exchange_rate_to_dollar as grantcredit_amount,
  apply_grantcredit_amount * 1.00000 / f.exchange_rate_to_dollar as apply_grantcredit_amount,
  a.apply_amount * 1.00000 / f.exchange_rate_to_dollar as apply_amount,
  case when a.is_reloan2 in ('OLD_SINGLE') and a.if_recall = 0 and coalesce(a.grantcredit_amount_final, 0) > 0 then a.grantcredit_amount_final * 1.00000 / f.exchange_rate_to_dollar
    when a.is_reloan2 in ('OLD_PLUS') and a.if_recall = 0 and coalesce(a.grant_amount_total, 0) > 0 then grant_amount_total * 1.00000 / f.exchange_rate_to_dollar
    when a.is_reloan2 in ('OLD_PLUS') and a.if_recall = 0 and coalesce(a.grantcredit_amount_final, 0) > 0 then grantcredit_amount_final * 1.00000 / f.exchange_rate_to_dollar
    when a.is_reloan2 in ('OLD_PLUS_M') and a.app_date < '2025-01-09' and a.if_recall = 0 then (coalesce(a.grantcredit_amount_final, 0) + coalesce(try_cast (a.baseinfo_onloan_amount as bigint), 0)
    ) * 1.00000 / f.exchange_rate_to_dollar
    when a.is_reloan2 in ('OLD_PLUS_M') and a.app_date >= '2025-01-09' and a.if_recall = 0 then grant_amount_total * 1.00000 / f.exchange_rate_to_dollar
    when a.if_recall = 1 then grantcredit_amount_final * 1.00000 / f.exchange_rate_to_dollar
    when a.if_recall = 0 then grantcredit_amount_final * 1.00000 / f.exchange_rate_to_dollar
    else 0
  end as grant_amount_max,
  c.overdue_amount_1_7,
  c.should_capital_1_7,
  c.overdue_amount_2_7,
  c.should_capital_2_7,
  c.should_cnt_1_7,
  c.overdue_cnt_1_7,
  c.should_cnt_2_7,
  c.overdue_cnt_2_7,
  apply_grantcredit_amount_risk* 1.00000 / f.exchange_rate_to_dollar as apply_grantcredit_amount_risk,
  grant_amount_max_risk* 1.00000 / f.exchange_rate_to_dollar as grant_amount_max_risk
from
  (
    select
      a.*,
      case
        when source_channel2 not in ('IOS')
        and app_version <= '2.1.4' then 1
        when loan_type2 = 'loop' then if_app
        else if_in_confirm
      end as if_in_confirm_final,
      case
        when source_channel2 not in ('IOS')
        and app_version <= '2.1.4' then 1
        when confirm_date is not null then 1
        when loan_type2 = 'loop' then if_app
        else if_confirm_passed
      end as if_confirm_passed_final,
      case
        when a.app_version <= '2.1.4'
        and source_channel2 not in ('IOS') then date (a.app_date)
        when a.loan_type2 = 'loop' then date (a.app_date)
        else a.confirm_date
      end as confirm_date_final,
      case
        when a.loan_type2 = 'loop' then cast(a.circular_amount as bigint)
        else (
          greatest (
            coalesce(grantcredit_30d_amount, 0),
            coalesce(grantcredit_60d_amount, 0),
            coalesce(grantcredit_90d_amount, 0),
            coalesce(grantcredit_120d_amount, 0),
            coalesce(grantcredit_150d_amount, 0),
            coalesce(grantcredit_180d_amount, 0),
            coalesce(grantcredit_210d_amount, 0)
          )
        )
      end as grantcredit_amount_final,
      case
        when a.loan_type2 = 'loop' then cast(a.circular_amount as bigint)
        when a.loan_type2 = 'normal'
        and a.interval_start = 30
        and cast(a.grantcredit_30d_amount as bigint) > 0 then a.grantcredit_30d_amount
        when a.loan_type2 = 'normal'
        and a.interval_start = 60
        and cast(a.grantcredit_60d_amount as bigint) > 0 then a.grantcredit_60d_amount
        when a.loan_type2 = 'normal'
        and a.interval_start = 90
        and cast(a.grantcredit_90d_amount as bigint) > 0 then a.grantcredit_90d_amount
        when a.loan_type2 = 'normal'
        and a.interval_start = 120
        and cast(a.grantcredit_120d_amount as bigint) > 0 then a.grantcredit_120d_amount
        when a.loan_type2 = 'normal'
        and a.interval_start = 150
        and cast(a.grantcredit_150d_amount as bigint) > 0 then a.grantcredit_150d_amount
        when a.loan_type2 = 'normal'
        and a.interval_start = 180
        and cast(a.grantcredit_180d_amount as bigint) > 0 then a.grantcredit_180d_amount
        when a.loan_type2 = 'normal'
        and a.interval_start = 210
        and cast(a.grantcredit_210d_amount as bigint) > 0 then a.grantcredit_210d_amount
        else (
          greatest (
            coalesce(grantcredit_30d_amount, 0),
            coalesce(grantcredit_60d_amount, 0),
            coalesce(grantcredit_90d_amount, 0),
            coalesce(grantcredit_120d_amount, 0),
            coalesce(grantcredit_150d_amount, 0),
            coalesce(grantcredit_180d_amount, 0),
            coalesce(grantcredit_210d_amount, 0)
          )
        )
      end as apply_grantcredit_amount
    ,case when loan_type2 = 'loop' then cast(circular_amount as bigint)
            when loan_type2 = 'normal' and interval_start = 30 then grantcredit_30d_amount
            when loan_type2 = 'normal' and interval_start = 60 then grantcredit_60d_amount
            when loan_type2 = 'normal' and interval_start = 90 then grantcredit_90d_amount
            when loan_type2 = 'normal' and interval_start = 120 then grantcredit_120d_amount
            when loan_type2 = 'normal' and interval_start = 150 then grantcredit_150d_amount
            when loan_type2 = 'normal' and interval_start = 180 then grantcredit_180d_amount
        when loan_type2 = 'normal' and interval_start = 210 then grantcredit_210d_amount else 0 end as apply_grantcredit_amount_risk
        ,case when loan_type2 = 'loop' then grant_amount_total
            when loan_type2 = 'normal' and baseinfo_onloan_amount > 0 and interval_start = 30 then grantcredit_30d_amount + baseinfo_onloan_amount
            when loan_type2 = 'normal' and baseinfo_onloan_amount > 0 and interval_start = 60 then grantcredit_60d_amount + baseinfo_onloan_amount
            when loan_type2 = 'normal' and baseinfo_onloan_amount > 0 and interval_start = 90 then grantcredit_90d_amount + baseinfo_onloan_amount
            when loan_type2 = 'normal' and baseinfo_onloan_amount > 0 and interval_start = 120 then grantcredit_120d_amount + baseinfo_onloan_amount
            when loan_type2 = 'normal' and baseinfo_onloan_amount > 0 and interval_start = 150 then grantcredit_150d_amount + baseinfo_onloan_amount
            when loan_type2 = 'normal' and baseinfo_onloan_amount > 0 and interval_start = 180 then grantcredit_180d_amount + baseinfo_onloan_amount
            when loan_type2 = 'normal' and baseinfo_onloan_amount > 0 and interval_start = 210 then grantcredit_210d_amount + baseinfo_onloan_amount
            when loan_type2 = 'normal' and interval_start = 30 then grantcredit_30d_amount
            when loan_type2 = 'normal' and interval_start = 60 then grantcredit_60d_amount
            when loan_type2 = 'normal' and interval_start = 90 then grantcredit_90d_amount
            when loan_type2 = 'normal' and interval_start = 120 then grantcredit_120d_amount
            when loan_type2 = 'normal' and interval_start = 150 then grantcredit_150d_amount
            when loan_type2 = 'normal' and interval_start = 180 then grantcredit_180d_amount
            when loan_type2 = 'normal' and interval_start = 210 then grantcredit_210d_amount    
            else 0 end as grant_amount_max_risk
    from
      ind.xly_application_funnel a
    where
      a.if_app = 1
      and a.app_date >= '2021-06-01'
      --and grant_strategy = 'OLD'
      --and a.app_date <= '2025-06-30'
  ) a
  left join (
    select
      mid,
      issue_month,
      is_reloan2,
      new_grade_level,
      issue_date,
      loan_cycle,
      loan_indexs,
      case
        when a.product_level like 'M%' then 'M'
        when a.product_level in (
          'A14',
          'B10',
          'B12',
          'C8',
          'A15',
          'B13',
          'B14',
          'C9',
          'A16',
          'B15',
          'B16',
          'C10',
          'G1',
          'G2',
          'H1',
          'H2',
          'H3',
          'H4',
          'I1',
          'I2',
          'I3',
          'I4',
          'I5'
        ) then 'F-NofeeNew'
        when lower(a.product_level) like '%h%' then 'F-NofeeNew'
        when lower(a.product_level) like '%g%' then 'F-NofeeNew'
        when a.product_level in ('B7', 'C7', 'A9', 'B8') then 'F-NofeeOld'
        when a.product_level is not null then 'R'
        else 'other'
      end as product_level_type
    from
      ind.xly_application_funnel a
    where
      a.if_app = 1
      and if_issue = 1
      and grant_strategy = 'NEW'
  ) b on a.mid = b.mid
  left join dim.dim_exchange_rate_cost f on to_char (date (a.app_date), 'yyyymm') = f.month_id and f.account_currency = 'IDR'
  left join dim.dim_exchange_rate_cost f1 on to_char (date (a.issue_date), 'yyyymm') = f1.month_id and f1.account_currency = 'IDR'
  left join (
    select
      *
    from
      (
        select distinct
          biz_id,
          sign_date,
          row_number() over (
            partition by
              biz_id
            order by
              sign_date desc
          ) rn
        from
          (
            select distinct
              biz_id,
              date (create_time) sign_date
            from
              ods.s25_contract_record c
            where
              c.oper_type = 4
              and c.deleted = 0
              and date (create_time)<current_date
            union all
            select distinct
              cast(aa.camera_id as decimal(38, 6)) as biz_id,
              date (create_time) sign_date
            FROM
              ods_view_presto.s02_digisign_record aa
            WHERE
              aa.status = 1
              and aa.type = 7
              and role_type = 1
              and date (create_time)<current_date
          ) a
      ) g
    where
      rn = 1
  ) g on try_cast (a.biz_id as bigint) = try_cast (g.biz_id as bigint)
  left join (
    select
      customer_id,
      min(black_date) min_overdue7_black_date
    from
      (
        select
          customer_id,
          camera_id,
          date_add ('day', 7, date (should_time)) black_date,
          date_diff (
            'day',
            date (should_time),
            date (coalesce(fact_time, current_date))
          ) as due_day
        from
          ods.s02_loan_repayment
        where
          date_diff (
            'day',
            date (should_time),
            date (coalesce(fact_time, current_date))
          ) > 7
      ) a
    group by
      1
  ) h on cast(b.mid as bigint) = cast(h.customer_id as bigint)
  left join (
    select
      customer_id,
      min(black_date) min_overdue15_black_date
    from
      (
        select
          customer_id,
          camera_id,
          date_add ('day', 15, date (should_time)) black_date,
          date_diff (
            'day',
            date (should_time),
            date (coalesce(fact_time, current_date))
          ) as due_day
        from
          ods.s02_loan_repayment
        where
          date_diff (
            'day',
            date (should_time),
            date (coalesce(fact_time, current_date))
          ) > 15
      ) a
    group by
      1
  ) h1 on cast(b.mid as bigint) = cast(h1.customer_id as bigint)
  left join (
    select
      id,
      b.overdue_amount_1_7,
      b.should_capital_1_7,
      b.overdue_amount_2_7,
      b.should_capital_2_7,
      b.should_cnt_1_7,
      b.overdue_cnt_1_7,
      b.should_cnt_2_7,
      b.overdue_cnt_2_7
    from
      ind.whx_vintage_all4 b
  ) c on try_cast (a.biz_id as bigint) = try_cast (c.id as bigint)