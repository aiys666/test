drop table if exists ind.ba_apply_should_result_week_old_wdk;
create table if not exists ind.ba_apply_should_result_week_old_wdk as
WITH
  application_metrics AS (
    SELECT
      app_week,
      app_month,
      grant_strategy,
      product_tag,
      is_reloan2,
      new_grade_level,
      first_loan_grade_level,
      loan_type2,
      CASE
        WHEN TRY_CAST (SUBSTR (new_old_model_loop, 1, 1) AS INTEGER) <= 3 THEN NULL
        ELSE new_old_model_loop
      end as new_old_model_loop,
      case
        when if_regular_backup = '1' then 1
        else 0
      end as if_regular_backup,
      case
        when if_backup_switch = 1 then 1
        else 0
      end as if_backup_switch,
      sum(
        case
          when if_recall = 0 then if_app
        end
      ) if_app,
      sum(
        case
          when grant_strategy = 'OLD'
          and if_recall = 0 then if_external_data_3_passed
          when grant_strategy = 'NEW' then if_in_confirm_temp
        end
      ) if_external_3_passed,
      SUM(
        case
          when if_in_confirm_final = 1 then grant_amount_max
          else NULL
        end
      ) AS in_confirm_grantcredit_amount_total,
      SUM(
        case
          when if_in_confirm_final = 1 then grantcredit_amount
          else NULL
        end
      ) AS in_confirm_grantcredit_amount,
      SUM(
        case
          when if_confirm_passed_final = 1 then apply_grantcredit_amount
          else NULL
        end
      ) AS confirm_grantcredit_amount,
      SUM(
        case
          when if_confirm_passed_final = 1 then apply_amount
          else NULL
        end
      ) AS confirm_apply_amount,
      SUM(
        case
          when if_confirm_passed_final = 1
          and if_issue = 1 then apply_grantcredit_amount
          else NULL
        end
      ) AS issue_confirm_grantcredit_amount,
      SUM(
        case
          when if_confirm_passed_final = 1
          and if_issue = 1 then apply_amount
          else NULL
        end
      ) AS issue_confirm_apply_amount,
      sum(
        case
          when grant_strategy = 'OLD'
          and if_recall = 0 then if_in_external_data_4
          when grant_strategy = 'NEW' then if_confirm_passed_final
        end
      ) if_in_external_data_4,
      sum(if_external_data_4_passed) as pass_cnt,
      sum(if_issue) AS issue_cnt_from_app,
      sum(is_released_within_24h) AS is_released_within_24h
    FROM
      ind.ba_asset_base_info
    WHERE
      date (app_date) >= DATE ('2025-01-01')
      AND date (app_date) < CURRENT_DATE
      AND grant_strategy = 'OLD'
    GROUP BY
      1,
      2,
      3,
      4,
      5,
      6,
      7,
      8,
      9,
      10,
      11
  ),
  confirm_metrics AS (
    SELECT
      create_week,
      date_format (create_date, '%Y-%m-01') create_month,
      grant_strategy,
      product_tag,
      is_reloan2,
      new_grade_level,
      first_loan_grade_level,
      loan_type2,
      CASE
        WHEN TRY_CAST (SUBSTR (new_old_model_loop, 1, 1) AS INTEGER) <= 3 THEN NULL
        ELSE new_old_model_loop
      end as new_old_model_loop,
      case
        when if_regular_backup = '1' then 1
        else 0
      end as if_regular_backup,
      case
        when if_backup_switch = 1 then 1
        else 0
      end as if_backup_switch,
      count(
        distinct case
          when if_recall = 0 then id
          else null
        end
      ) create_app_cnt,
      sum(if_in_confirm_final) AS in_confirm_cnt_final,
      sum(if_in_confirm_temp) AS in_confirm_cnt,
      sum(
        case
          when new_grade_level IN ('1', '2') then if_in_confirm_temp
          else 0
        end
      ) AS in_confirm_cnt_1_2,
      sum(
        case
          when new_grade_level IN ('1', '2', '3', '4') then if_in_confirm_temp
          else 0
        end
      ) AS in_confirm_cnt_1_4,
      sum(
        case
          when user_level IN ('1', '2') then if_in_confirm_temp
          else 0
        end
      ) AS rl_in_confirm_cnt_1_2,
      sum(
        case
          when user_level IN ('1', '2', '3') then if_in_confirm_temp
          else 0
        end
      ) AS rl_in_confirm_cnt_1_3,
      sum(if_confirm_passed_final) AS confirm_passed_cnt,
      sum(if_confirm_passed_num_24h) AS if_confirm_passed_num_24h,
      sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
      sum(if_confirm_passed_num_t7) AS if_confirm_passed_num_t7
    FROM
      ind.ba_asset_base_info
    WHERE
      date (create_date) >= DATE ('2025-01-01')
      AND date (create_date) < CURRENT_DATE
      AND grant_strategy = 'OLD'
    GROUP BY
      1,
      2,
      3,
      4,
      5,
      6,
      7,
      8,
      9,
      10,
      11
  ),
  issue_metrics AS (
    SELECT
      issue_week,
      issue_month,
      grant_strategy,
      product_tag,
      is_reloan2,
      loan_type2,
      new_grade_level,
      first_loan_grade_level,
      CASE
        WHEN TRY_CAST (SUBSTR (new_old_model_loop, 1, 1) AS INTEGER) <= 3 THEN NULL
        ELSE new_old_model_loop
      end as new_old_model_loop,
      case
        when if_regular_backup = '1' then 1
        else 0
      end as if_regular_backup,
      case
        when if_backup_switch = 1 then 1
        else 0
      end as if_backup_switch,
      sum(if_issue) AS issue_cnt_from_issue,
      sum(
        case
          when new_grade_level IN ('1', '2') then if_issue
          else 0
        end
      ) AS issue_cnt_1_2,
      sum(
        case
          when new_grade_level IN ('1', '2', '3', '4') then if_issue
          else 0
        end
      ) AS issue_cnt_1_4,
      sum(
        case
          when user_level IN ('1', '2') then if_issue
          else 0
        end
      ) AS rl_issue_cnt_1_2,
      sum(
        case
          when user_level IN ('1', '2', '3') then if_issue
          else 0
        end
      ) AS rl_issue_cnt_1_3,
      sum(haircut_amount) as issue_haircut_amount,
      sum(interest) as issue_interest,
      sum(revenue) as issue_revenue,
      sum(contract_amount) AS issue_contract_amount,
      sum(contract_amount_usd1) AS issue_contract_amount_usd,
      sum(
        case
          when grant_strategy = 'NEW' then contract_amount_usd1
          else 0
        end
      ) AS issue_contract_amount_usd_new,
      sum(
        case
          when grant_strategy = 'OLD' then contract_amount_usd1
          else 0
        end
      ) AS issue_contract_amount_usd_old,
      SUM(
        apply_grantcredit_amount * app_exchange_rate_to_dollar
      ) AS issue_in_confirm_grantcredit_amount,
      sum(overdue_amount_1_0) AS overdue_amount_1_0,
      sum(should_capital_1_0) AS should_capital_1_0,
      sum(overdue_amount_1_7) AS overdue_amount_1_7,
      sum(should_capital_1_7) AS should_capital_1_7,
      sum(overdue_amount_1_14) AS overdue_amount_1_14,
      sum(should_capital_1_14) AS should_capital_1_14,
      sum(overdue_amount_1_30) AS overdue_amount_1_30,
      sum(should_capital_1_30) AS should_capital_1_30,
      sum(overdue_amount_2_0) AS overdue_amount_2_0,
      sum(should_capital_2_0) AS should_capital_2_0,
      sum(overdue_amount_2_7) AS overdue_amount_2_7,
      sum(should_capital_2_7) AS should_capital_2_7,
      sum(overdue_amount_2_14) AS overdue_amount_2_14,
      sum(should_capital_2_14) AS should_capital_2_14,
      sum(overdue_amount_2_30) AS overdue_amount_2_30,
      sum(should_capital_2_30) AS should_capital_2_30,
      sum(loan_cycle_amount) AS loan_cycle_amount
    FROM
      ind.ba_asset_base_info
    WHERE
      if_issue = 1
      AND grant_strategy = 'OLD'
      AND date (issue_date) >= DATE ('2025-01-01')
      AND date (issue_date) < CURRENT_DATE
    GROUP BY
      1,
      2,
      3,
      4,
      5,
      6,
      7,
      8,
      9,
      10,
      11
  ),
  should_metrics AS (
    SELECT
      to_char (date_trunc ('month', a.should_date), 'yyyy-mm-dd') as should_month,
      to_char (date_trunc ('week', a.should_date), 'yyyy-mm-dd') as should_week,
      c.grant_strategy,
      c.product_tag,
      c.is_reloan2,
      c.loan_type2,
      c.new_grade_level,
      c.first_loan_grade_level,
      CASE
        WHEN TRY_CAST (SUBSTR (new_old_model_loop, 1, 1) AS INTEGER) <= 3 THEN NULL
        ELSE new_old_model_loop
      end as new_old_model_loop,
      case
        when c.if_regular_backup = '1' then 1
        else 0
      end as if_regular_backup,
      case
        when c.if_backup_switch = 1 then 1
        else 0
      end as if_backup_switch,
      SUM(a.should_capital) AS should_capital,
      SUM(
        CASE
          WHEN DATE_DIFF ('day', should_date, CURRENT_DATE) >= 1 THEN a.should_capital
          ELSE null
        END
      ) AS should_capital_d0,
      SUM(
        CASE
          WHEN DATE_DIFF ('day', should_date, CURRENT_DATE) >= 2 THEN a.should_capital
          ELSE null
        END
      ) AS should_capital_d1,
      SUM(
        CASE
          WHEN DATE_DIFF ('day', should_date, CURRENT_DATE) >= 8 THEN a.should_capital
          ELSE null
        END
      ) AS should_capital_d7,
      SUM(
        CASE
          WHEN DATE_DIFF ('day', should_date, CURRENT_DATE) >= 16 THEN a.should_capital
          ELSE null
        END
      ) AS should_capital_d15,
      SUM(
        CASE
          WHEN DATE_DIFF ('day', should_date, CURRENT_DATE) >= 31 THEN a.should_capital
          ELSE null
        END
      ) AS should_capital_d30,
      SUM(
        CASE
          WHEN due_day <= 0
          and DATE_DIFF ('day', should_date, CURRENT_DATE) >= 1 THEN a.fact_capital
          ELSE 0
        END
      ) AS t0_capital_paid_d0,
      SUM(
        CASE
          WHEN due_day <= 1
          and DATE_DIFF ('day', should_date, CURRENT_DATE) >= 2 THEN a.fact_capital
          ELSE 0
        END
      ) AS t1_capital_paid_d1,
      SUM(
        CASE
          WHEN due_day <= 7
          and DATE_DIFF ('day', should_date, CURRENT_DATE) >= 8 THEN a.fact_capital
          ELSE 0
        END
      ) AS t7_capital_paid_d7,
      SUM(
        CASE
          WHEN due_day <= 15
          and DATE_DIFF ('day', should_date, CURRENT_DATE) >= 16 THEN a.fact_capital
          ELSE 0
        END
      ) AS t15_capital_paid_d15,
      SUM(
        CASE
          WHEN due_day <= 30
          and DATE_DIFF ('day', should_date, CURRENT_DATE) >= 31 THEN a.fact_capital
          ELSE 0
        END
      ) AS t30_capital_paid_d30,
      SUM(
        CASE
          WHEN due_day <= 0
          and DATE_DIFF ('day', should_date, CURRENT_DATE) >= 8 THEN a.fact_capital
          ELSE 0
        END
      ) AS t0_capital_paid_d7,
      SUM(
        CASE
          WHEN due_day <= 0
          and DATE_DIFF ('day', should_date, CURRENT_DATE) >= 16 THEN a.fact_capital
          ELSE 0
        END
      ) AS t0_capital_paid_d15,
      SUM(
        CASE
          WHEN due_day <= 0
          and DATE_DIFF ('day', should_date, CURRENT_DATE) >= 31 THEN a.fact_capital
          ELSE 0
        END
      ) AS t0_capital_paid_d30
    FROM
      (
        SELECT
          customer_id,
          camera_id AS biz_id,
          should_date,
          due_day,
          SUM(should_amount) AS should_amount,
          SUM(should_capital) AS should_capital,
          SUM(should_interest) AS should_interest,
          SUM(should_fine) AS should_fine,
          SUM(fact_amount) AS fact_amount,
          SUM(fact_capital) AS fact_capital,
          SUM(fact_interest) AS fact_interest,
          SUM(fact_fine) AS fact_fine
        FROM
          ind.gqy_case_info_f
        WHERE
          is_due = 0
          AND should_date >= DATE ('2025-01-01')
          AND should_date < CURRENT_DATE
        GROUP BY
          1,
          2,
          3,
          4
      ) a
      LEFT JOIN (
        SELECT
          data_date,
          customer_id,
          MAX(max_due_day) AS cus_ovd_day
        FROM
          ind.gqy_daliy_case
        GROUP BY
          1,
          2
        HAVING
          MAX(max_due_day) >= 1
      ) b ON a.customer_id = b.customer_id
      AND should_date = b.data_date
      left join ind.ba_asset_base_info c on TRY_CAST (a.biz_id AS BIGINT) = TRY_CAST (c.biz_id AS BIGINT)
    WHERE
      b.customer_id IS NULL
      AND c.grant_strategy = 'OLD'
    GROUP BY
      1,
      2,
      3,
      4,
      5,
      6,
      7,
      8,
      9,
      10,
      11
  ),
  data_date as (
    select distinct
      date_mon,
      date_format (DATE_PARSE (data_date, '%Y%m%d'), '%Y-%m-01') AS data_month,
      month_days,
      day (DATE_ADD ('day', -1, CURRENT_DATE)) as current_date_day,
      case
        when DATE_PARSE (month_end, '%Y%m%d') < DATE_TRUNC ('month', CURRENT_DATE) then day (DATE_PARSE (month_end, '%Y%m%d'))
        else day (DATE_ADD ('day', -1, CURRENT_DATE))
      end as date_month_end_actual
    from
      dim.dim_data_info
  )
SELECT
  COALESCE(
    a.grant_strategy,
    i.grant_strategy,
    s.grant_strategy,
    c.grant_strategy
  ) AS grant_strategy,
  COALESCE(
    a.product_tag,
    i.product_tag,
    s.product_tag,
    c.product_tag
  ) AS product_tag,
  COALESCE(
    a.is_reloan2,
    i.is_reloan2,
    s.is_reloan2,
    c.is_reloan2
  ) AS is_reloan2,
  COALESCE(
    a.new_grade_level,
    i.new_grade_level,
    s.new_grade_level,
    c.new_grade_level
  ) AS new_grade_level,
  COALESCE(
    a.first_loan_grade_level,
    i.first_loan_grade_level,
    s.first_loan_grade_level,
    c.first_loan_grade_level
  ) AS first_loan_grade_level,
  COALESCE(
    a.if_regular_backup,
    i.if_regular_backup,
    s.if_regular_backup,
    c.if_regular_backup
  ) AS if_regular_backup,
  COALESCE(
    a.if_backup_switch,
    i.if_backup_switch,
    s.if_backup_switch,
    c.if_backup_switch
  ) AS if_backup_switch,
  COALESCE(
    a.new_old_model_loop,
    i.new_old_model_loop,
    s.new_old_model_loop,
    c.new_old_model_loop
  ) AS new_old_model_loop,
  COALESCE(
    date (a.app_week),
    date (i.issue_week),
    date (s.should_week),
    c.create_week
  ) AS app_week,
  COALESCE(
    a.app_month,
    i.issue_month,
    s.should_month,
    c.create_month
  ) AS app_month,
  COALESCE(a.if_app, 0) AS if_app,
  COALESCE(a.if_external_3_passed, 0) AS if_external_3_passed,
  COALESCE(c.create_app_cnt, 0) AS create_app_cnt,
  COALESCE(c.in_confirm_cnt_final, 0) AS in_confirm_cnt_final,
  COALESCE(c.in_confirm_cnt, 0) AS in_confirm_cnt,
  COALESCE(c.in_confirm_cnt_1_2, 0) AS in_confirm_cnt_1_2,
  COALESCE(c.in_confirm_cnt_1_4, 0) AS in_confirm_cnt_1_4,
  COALESCE(c.rl_in_confirm_cnt_1_2, 0) AS rl_in_confirm_cnt_1_2,
  COALESCE(c.rl_in_confirm_cnt_1_3, 0) AS rl_in_confirm_cnt_1_3,
  COALESCE(c.confirm_passed_cnt, 0) AS confirm_passed_cnt,
  COALESCE(c.if_confirm_passed_num_24h, 0) AS if_confirm_passed_num_24h,
  COALESCE(c.if_confirm_passed_num_t0, 0) AS if_confirm_passed_num_t0,
  COALESCE(c.if_confirm_passed_num_t7, 0) AS if_confirm_passed_num_t7,
  COALESCE(a.in_confirm_grantcredit_amount_total, 0) AS in_confirm_grantcredit_amount_total,
  COALESCE(a.in_confirm_grantcredit_amount, 0) AS in_confirm_grantcredit_amount,
  COALESCE(a.confirm_grantcredit_amount, 0) AS confirm_grantcredit_amount,
  COALESCE(a.confirm_apply_amount, 0) AS confirm_apply_amount,
  COALESCE(a.if_in_external_data_4, 0) AS if_in_external_data_4,
  COALESCE(a.pass_cnt, 0) AS pass_cnt,
  COALESCE(a.issue_cnt_from_app, 0) AS issue_cnt_from_app,
  COALESCE(a.is_released_within_24h, 0) AS is_released_within_24h,
  COALESCE(i.issue_cnt_from_issue, 0) AS issue_cnt_from_issue,
  COALESCE(i.issue_cnt_1_2, 0) AS issue_cnt_1_2,
  COALESCE(i.issue_cnt_1_4, 0) AS issue_cnt_1_4,
  COALESCE(i.rl_issue_cnt_1_2, 0) AS rl_issue_cnt_1_2,
  COALESCE(i.rl_issue_cnt_1_3, 0) AS rl_issue_cnt_1_3,
  COALESCE(i.issue_contract_amount, 0) AS issue_contract_amount,
  COALESCE(i.issue_contract_amount_usd, 0) AS issue_contract_amount_usd,
  COALESCE(i.issue_in_confirm_grantcredit_amount, 0) AS issue_in_confirm_grantcredit_amount,
  SUM(COALESCE(i.issue_contract_amount_usd, 0)) OVER (
    PARTITION BY
      COALESCE(a.app_month, i.issue_month, s.should_month)
  ) AS issue_contract_group,
  SUM(
    case
      when COALESCE(
        a.grant_strategy,
        i.grant_strategy,
        s.grant_strategy
      ) = 'NEW' then COALESCE(i.issue_contract_amount_usd, 0)
      else 0
    end
  ) OVER (
    PARTITION BY
      COALESCE(a.app_month, i.issue_month, s.should_month)
  ) AS issue_contract_new_group,
  SUM(
    case
      when COALESCE(
        a.grant_strategy,
        i.grant_strategy,
        s.grant_strategy
      ) = 'OLD' then COALESCE(i.issue_contract_amount_usd, 0)
      else 0
    end
  ) OVER (
    PARTITION BY
      COALESCE(a.app_month, i.issue_month, s.should_month)
  ) AS issue_contract_old_group,
  COALESCE(i.overdue_amount_1_0, 0) AS overdue_amount_1_0,
  COALESCE(i.should_capital_1_0, 0) AS should_capital_1_0,
  COALESCE(i.overdue_amount_1_7, 0) AS overdue_amount_1_7,
  COALESCE(i.should_capital_1_7, 0) AS should_capital_1_7,
  COALESCE(i.overdue_amount_1_14, 0) AS overdue_amount_1_14,
  COALESCE(i.should_capital_1_14, 0) AS should_capital_1_14,
  COALESCE(i.overdue_amount_1_30, 0) AS overdue_amount_1_30,
  COALESCE(i.should_capital_1_30, 0) AS should_capital_1_30,
  COALESCE(i.overdue_amount_2_0, 0) AS overdue_amount_2_0,
  COALESCE(i.should_capital_2_0, 0) AS should_capital_2_0,
  COALESCE(i.overdue_amount_2_7, 0) AS overdue_amount_2_7,
  COALESCE(i.should_capital_2_7, 0) AS should_capital_2_7,
  COALESCE(i.overdue_amount_2_30, 0) AS overdue_amount_2_30,
  COALESCE(i.should_capital_2_30, 0) AS should_capital_2_30,
  COALESCE(s.should_capital_d0, 0) AS should_capital_d0,
  COALESCE(s.should_capital_d1, 0) AS should_capital_d1,
  COALESCE(s.should_capital_d7, 0) AS should_capital_d7,
  COALESCE(s.should_capital_d15, 0) AS should_capital_d15,
  COALESCE(s.should_capital_d30, 0) AS should_capital_d30,
  COALESCE(s.should_capital_d0 - s.t0_capital_paid_d0, 0) AS t0_capital_due_d0,
  COALESCE(s.should_capital_d1 - s.t1_capital_paid_d1, 0) AS t1_capital_due_d1,
  COALESCE(s.should_capital_d7 - s.t7_capital_paid_d7, 0) AS t7_capital_due_d7,
  COALESCE(s.should_capital_d15 - s.t15_capital_paid_d15, 0) AS t15_capital_due_d15,
  COALESCE(s.should_capital_d30 - s.t30_capital_paid_d30, 0) AS t30_capital_due_d30,
  COALESCE(s.t0_capital_paid_d7, 0) AS t0_capital_paid_d7,
  COALESCE(s.t0_capital_paid_d15, 0) AS t0_capital_paid_d15,
  COALESCE(s.t0_capital_paid_d30, 0) AS t0_capital_paid_d30,
  COALESCE(s.t7_capital_paid_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_d7,
  COALESCE(s.t15_capital_paid_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_d15,
  COALESCE(s.t30_capital_paid_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_d30,
  COALESCE(s.should_capital_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_due_d7,
  COALESCE(s.should_capital_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_due_d15,
  COALESCE(s.should_capital_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_due_d30,
  COALESCE(loan_cycle_amount, 0) AS loan_cycle_amount,
  COALESCE(issue_haircut_amount, 0) AS issue_haircut_amount,
  COALESCE(issue_interest, 0) AS issue_interest,
  COALESCE(issue_revenue, 0) AS issue_revenue,
  total_amt * exchange_rate * 1.00000 / f1.exchange_rate_to_dollar AS ov_total_amt_usd,
  fl_contract_amt * exchange_rate * 1.00000 / f1.exchange_rate_to_dollar AS fl_total_amt_usd,
  rl_contract_amt * exchange_rate * 1.00000 / f1.exchange_rate_to_dollar AS rl_total_amt_usd,
  month_days,
  date_month_end_actual,
  COALESCE(issue_contract_amount_usd_new, 0) AS issue_contract_amount_usd_new,
  COALESCE(issue_contract_amount_usd_old, 0) AS issue_contract_amount_usd_old,
  COALESCE(a.loan_type2, i.loan_type2, s.loan_type2) AS loan_type2
FROM
  application_metrics a
  FULL JOIN issue_metrics i ON a.grant_strategy = i.grant_strategy
  AND a.product_tag = i.product_tag
  AND a.is_reloan2 = i.is_reloan2
  AND a.loan_type2 = i.loan_type2
  AND a.new_grade_level = i.new_grade_level
  AND a.app_week = i.issue_week
  AND a.app_month = i.issue_month
  AND a.new_old_model_loop = i.new_old_model_loop
  AND a.if_regular_backup = i.if_regular_backup
  AND a.if_backup_switch = i.if_backup_switch
  AND a.first_loan_grade_level = i.first_loan_grade_level
  FULL JOIN should_metrics s ON COALESCE(a.grant_strategy, i.grant_strategy) = s.grant_strategy
  AND COALESCE(a.product_tag, i.product_tag) = s.product_tag
  AND COALESCE(a.is_reloan2, i.is_reloan2) = s.is_reloan2
  AND COALESCE(a.loan_type2, i.loan_type2) = s.loan_type2
  AND COALESCE(a.new_grade_level, i.new_grade_level) = s.new_grade_level
  AND COALESCE(a.app_week, i.issue_week) = s.should_week
  AND COALESCE(a.app_month, i.issue_month) = s.should_month
  AND COALESCE(a.new_old_model_loop, i.new_old_model_loop) = s.new_old_model_loop
  AND COALESCE(a.if_regular_backup, i.if_regular_backup) = s.if_regular_backup
  AND COALESCE(a.if_backup_switch, i.if_backup_switch) = s.if_backup_switch
  AND COALESCE(
    a.first_loan_grade_level,
    i.first_loan_grade_level
  ) = s.first_loan_grade_level
  full join confirm_metrics c ON COALESCE(
    a.grant_strategy,
    i.grant_strategy,
    s.grant_strategy
  ) = c.grant_strategy
  AND COALESCE(a.product_tag, i.product_tag, s.product_tag) = c.product_tag
  AND COALESCE(a.is_reloan2, i.is_reloan2, s.is_reloan2) = c.is_reloan2
  AND COALESCE(a.loan_type2, i.loan_type2, s.loan_type2) = c.loan_type2
  AND COALESCE(
    a.new_old_model_loop,
    i.new_old_model_loop,
    s.new_old_model_loop
  ) = c.new_old_model_loop
  AND COALESCE(
    a.new_grade_level,
    i.new_grade_level,
    s.new_grade_level
  ) = c.new_grade_level
  AND COALESCE(
    date (a.app_week),
    date (i.issue_week),
    date (s.should_week)
  ) = c.create_week
  AND COALESCE(a.app_month, i.issue_month, s.should_month) = c.create_month
  AND COALESCE(
    a.if_regular_backup,
    i.if_regular_backup,
    s.if_regular_backup
  ) = c.if_regular_backup
  AND COALESCE(
    a.if_backup_switch,
    i.if_backup_switch,
    s.if_backup_switch
  ) = c.if_backup_switch
  AND COALESCE(
    a.first_loan_grade_level,
    i.first_loan_grade_level,
    s.first_loan_grade_level
  ) = c.first_loan_grade_level
  LEFT JOIN ind.ba_kpi_targets_m b ON COALESCE(a.app_month, i.issue_month, s.should_month) = b.month
  left join data_date cc ON b.month = cc.data_month
  LEFT JOIN dim.dim_exchange_rate_cost f1 ON cc.date_mon = f1.month_id
  AND f1.account_currency = 'IDR'