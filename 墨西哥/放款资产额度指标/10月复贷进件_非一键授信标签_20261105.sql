-- ======================================================================
-- 2026-10 复贷总进件明细 + 标签：进件前 30 天是否有过"非一键放款且授信"
--
-- 主表：mx.wxs_application_funnel（is_reloan='old'，app_date 2026-10-01 ~ 10-31）
-- 评级：left join mx.yj_test_table_250225 取 android_oldcust_maincreditlevel_charge_v6_1
--
-- 一键放款标识：one_click_loan_tag='1' 为一键；NULL 视为非一键
--   实测 10 月复贷该字段只有 '1'(69,970 笔) 和 NULL(5,916 笔) 两类
-- 标签 prior_nononeclick_sx_30d：
--   同 mid 在本笔进件 app_date 前 1~30 天内，存在 one_click_loan_tag IS NULL 且 if_in_sx=1 的记录
--
-- 输出：每笔进件（biz_id）一行
--   笔数 = COUNT(biz_id)｜人数 = COUNT(DISTINCT mid)
--   进件率 = SUM(if_in_sx)/COUNT(biz_id)｜放款率 = SUM(if_issue)/COUNT(biz_id)
--   授信额度均值 = AVG(grantcredit_amount)｜件均 = SUM(contract_amount)/SUM(if_issue)
--   4T3 本金坏账率 = SUM(t3_overdue_capit_4)/SUM(t3_should_capit_4)
-- ======================================================================
WITH f AS (
  SELECT f.mid, f.biz_id, f.app_date, f.app_time,
         f.app_group, f.product_type, f.one_click_loan_tag,
         f.if_in_sx, f.if_sx_passed, f.if_pass, f.if_issue,
         CAST(f.grantcredit_amount AS DOUBLE)           AS grantcredit_amount,
         CAST(f.daily_max_available_limit_sx AS DOUBLE) AS daily_max_available_limit,
         CAST(f.contract_amount AS DOUBLE)              AS contract_amount,
         CAST(f.haircut_amount AS DOUBLE)               AS haircut_amount,
         CAST(f.should_interest AS DOUBLE)              AS should_interest,
         f.is_t3_window_1, f.is_t3_overdue_1,
         f.is_t3_window_4, f.is_t3_overdue_4,
         f.is_t7_window_4, f.is_t7_overdue_4,
         CAST(f.t0_should_capit_1  AS DOUBLE) AS t0_should_capit_1,
         CAST(f.t0_overdue_capit_1 AS DOUBLE) AS t0_overdue_capit_1,
         CAST(f.t3_should_capit_1  AS DOUBLE) AS t3_should_capit_1,
         CAST(f.t3_overdue_capit_1 AS DOUBLE) AS t3_overdue_capit_1,
         CAST(f.t3_should_capit_4  AS DOUBLE) AS t3_should_capit_4,
         CAST(f.t3_overdue_capit_4 AS DOUBLE) AS t3_overdue_capit_4,
         CAST(f.t7_should_capit_4  AS DOUBLE) AS t7_should_capit_4,
         CAST(f.t7_overdue_capit_4 AS DOUBLE) AS t7_overdue_capit_4,
         CAST(f.t7_overdue_interest_4 AS DOUBLE) AS t7_overdue_interest_4
  FROM mx.wxs_application_funnel f
  WHERE f.is_reloan = 'old'
    AND f.app_date >= DATE '2026-10-01'
    AND f.app_date <= DATE '2026-10-31'
),
-- 历史"非一键放款且授信"记录（9 月起，覆盖 10-01 往前 30 天）
h AS (
  SELECT mid, app_date
  FROM mx.wxs_application_funnel
  WHERE is_reloan = 'old'
    AND if_in_sx = 1
    AND one_click_loan_tag IS NULL
    AND app_date >= DATE '2026-09-01'
    AND app_date <= DATE '2026-10-31'
),
tag AS (
  SELECT f.biz_id,
         MAX(CASE WHEN h.app_date IS NOT NULL THEN 1 ELSE 0 END) AS prior_nononeclick_sx_30d
  FROM f
  LEFT JOIN h ON h.mid = f.mid
    AND h.app_date BETWEEN DATE_ADD('day', -30, f.app_date)
                       AND DATE_ADD('day', -1,  f.app_date)
  GROUP BY 1
),
y AS (
  SELECT biz_id,
         MAX(android_oldcust_maincreditlevel_charge_v6_1) AS v6_1
  FROM mx.yj_test_table_250225
  GROUP BY 1
)
SELECT f.mid, f.biz_id, f.app_date, f.app_group, f.product_type,
       f.one_click_loan_tag,
       COALESCE(t.prior_nononeclick_sx_30d, 0) AS prior_nononeclick_sx_30d,
       y.v6_1,
       f.if_in_sx, f.if_sx_passed, f.if_pass, f.if_issue,
       f.grantcredit_amount, f.daily_max_available_limit,
       f.contract_amount, f.haircut_amount, f.should_interest,
       f.is_t3_window_1, f.is_t3_overdue_1,
       f.is_t3_window_4, f.is_t3_overdue_4,
       f.is_t7_window_4, f.is_t7_overdue_4,
       f.t0_should_capit_1, f.t0_overdue_capit_1,
       f.t3_should_capit_1, f.t3_overdue_capit_1,
       f.t3_should_capit_4, f.t3_overdue_capit_4,
       f.t7_should_capit_4, f.t7_overdue_capit_4, f.t7_overdue_interest_4
FROM f
LEFT JOIN tag t ON t.biz_id = f.biz_id
LEFT JOIN y      ON y.biz_id = f.biz_id
ORDER BY f.app_date, f.mid, f.biz_id;
