-- ======================================================================
-- 临额宽表 3（分维度版 · 2026-09-01 起复贷老客放款笔）
-- 上游 = mx.yj_temp_limit_wide_table_v2（宽表2，26 列，额度口径原样沿用，不重算）
-- 本表只做两件事：① 挂分析所需**维度字段**；② 挂**风险/收息字段**
--
-- 数据源分工：
--   额度类（主额/离线临额/在线临额/券）  ← 宽表2，不重算
--   策略类（V5_2/V5_3、用信评分、临额 type、发放 tag、app_group）
--                                     ← mx.yj_test_table_250225（同 biz 4 条重复行，MAX 去重，覆盖率 100%）
--   风险类（1T0~4T0、4T7、息费、期限）  ← mx.wxs_application_funnel（**必须按 biz_id 去重**，见注释）
--   离线发放时刻                        ← 额度台账 C015/C013（5 天有效期内最近一条）
--
-- ⚠️ 两个坑（都已在本 SQL 内处理）：
--   1) yj_test_table_250225 每 biz_id 固定 4 条逐字段完全相同的行 → MAX 聚合去重；
--   2) mx.wxs_application_funnel 曾因 funnel_1 关联 ods.s08_app_category_mapping（29 个
--      app_channel 各 2 行）导致同一 biz_id 出现 2 行 → 这里先 ROW_NUMBER 取 rn=1 收敛。
--   ⚠️ yj 表**没有 t7_* 账龄列**（只有 t0_*/t3_*），4T7 必须从 funnel 取，不要写错源。
--
-- 字段说明：
--   [A 标识与时间] biz_id / mid / issue_date / release_time / issue_week / issue_month
--                  product_level / app_group / v6_1_level / v6_1_grade
--   [B 策略节点]   strategy_flag / strategy_version / use_score_1522 / use_type_1523
--                  issue_tag_1386 / temp_grant_amount_check
--   [C 场景标签]   used_scenario(none/offline/online) / grant_scenario(none/offline/online/both)
--                  has_offline_grant / has_online_grant / is_temp_used
--   [D 额度结构]   宽表2 全部额度列 + temp_used_total / temp_share_of_contract /
--                  main_share_of_contract / uplift_amount / uplift_ratio
--   [E 上限约束]   is_main_capped / is_contract_capped / cap_type(A/B/C/N) / add_if_cap_50000
--   [F 供给效率]   offline_grant_time / offline_age_days / offline_expire_days /
--                  offline_use_rate / offline_unused_amount / offline_grant_ratio
--                  online_claimed / online_use_rate
--   [G 风险收息]   loan_cycle / haircut_amount / should_interest / interest_rate
--                  t0/t3/t7 的 should & overdue 本金（1~4 期）、t7_overdue_interest_4
--                  is_t0_window_1~4 / is_t3_window_1 / is_t7_window_4 / i1t0~i4t0 / i4t7
--   [H 券]         voucher_limit / voucher_id
--
-- 口径注释：
--   1) v6_1_grade = FLOOR(v6_1_level)，V6_1 为 1~11 的连续主评级分，取整后用于分档（g8/g9/g10 即此口径）
--   2) used_scenario 只看**本笔实际用掉的临额**：online_used_this>0 → online；offline_used_this>0 → offline；
--      都为 0 → none。两类恒互斥（宽表2 已按 C010 归属拆分）。
--   3) grant_scenario 看**发放侧**：offline_grant_amount>0 为离线已发，online_grant_amount>0 为在线已发（857 弹窗额）。
--      grant_scenario='online' 但 used_scenario='none'，即「弹窗已发、客户未领取」。
--   4) is_main_capped = main_used_this >= 9999；is_contract_capped = contract_amount >= 9999
--      cap_type：A = 合同顶格且用额全部来自主额（临额未用）；B = 合同顶格且用了离线临额；
--                C = 合同顶格且用了在线临额（池外叠加突破 1 万）；N = 未撞顶
--   5) add_if_cap_50000 = 若产品上限与单日可借上限同时抬到 5 万，本笔最多可多放
--      = GREATEST(LEAST(主额可用+离线临额可用, 50000) - contract_amount, 0)，非撞顶笔为 0
--   6) offline_use_rate = offline_used_this / offline_grant_amount（仅离线已发放样本内）
--   7) 风险列为本金金额口径；i4t7 = t7_overdue_capit_4 / t7_should_capit_4
--      TR 计算请直接按期聚合 should/overdue 列，不要用比率列的简单平均（会被小额笔拉偏）
-- ======================================================================

WITH base AS (
  SELECT * FROM mx.yj_temp_limit_wide_table_v2
),
yx AS (
  -- 策略维度源：yj 原表（每 biz 4 条重复行，MAX 聚合即去重）
  SELECT CAST(biz_id AS BIGINT) AS biz_id,
         MAX(app_group)                                              AS app_group,
         MAX(CAST(temp_credit_amount_strategy_test_flag AS VARCHAR)) AS strategy_flag,
         MAX(CAST(fd_use_creditamount_score_v1 AS DOUBLE))           AS use_score_1522,
         MAX(CAST(fd_use_creditamount_type AS DOUBLE))               AS use_type_1523,
         MAX(CAST(temp_credit_amount_issue_tag AS DOUBLE))           AS issue_tag_1386,
         MAX(CAST(temp_grant_amount AS DOUBLE)) / 1000.0             AS temp_grant_amount_check,
         MAX(release_time)                                           AS release_time
  FROM mx.yj_test_table_250225
  WHERE issue_date >= DATE '2026-09-01'
    AND issue_date <= DATE '2026-10-20'
    AND if_issue = 1
    AND is_reloan = 'old'
  GROUP BY 1
),
fn AS (
  -- 风险/收息源：mx.wxs_application_funnel（先按 biz_id 去重，避免历史 ×2 放大）
  SELECT * FROM (
    SELECT f.biz_id,
           f.contract_amount, f.loan_cycle, f.haircut_amount, f.should_interest,
           f.t0_should_capit_1, f.t0_overdue_capit_1,
           f.t0_should_capit_2, f.t0_overdue_capit_2,
           f.t0_should_capit_3, f.t0_overdue_capit_3,
           f.t0_should_capit_4, f.t0_overdue_capit_4,
           f.t3_should_capit_1, f.t3_overdue_capit_1,
           f.t7_should_capit_1, f.t7_overdue_capit_1,
           f.t7_should_capit_2, f.t7_overdue_capit_2,
           f.t7_should_capit_3, f.t7_overdue_capit_3,
           f.t7_should_capit_4, f.t7_overdue_capit_4, f.t7_overdue_interest_4,
           f.is_t0_window_1, f.is_t3_window_1, f.is_t0_window_2,
           f.is_t0_window_3, f.is_t0_window_4, f.is_t7_window_4,
           ROW_NUMBER() OVER (PARTITION BY f.biz_id ORDER BY f.app_time DESC) AS _rn
    FROM mx.wxs_application_funnel f
    WHERE f.issue_date >= DATE '2026-09-01'
      AND f.issue_date <= DATE '2026-10-20'
      AND f.if_issue = 1
      AND f.is_reloan = 'old'
  ) t WHERE _rn = 1
),
ogr AS (
  -- 离线临额发放时刻（5 天有效期内的最近一条 C015/C013），用于算剩余有效期
  SELECT b.biz_id, MAX(c.create_time) AS offline_grant_time
  FROM base b
  JOIN yx y ON y.biz_id = b.biz_id
  JOIN ods_view_presto.s05_user_creditlimit_change_record c
    ON c.mid = b.mid
   AND c.limit_type        = 'TEMP'
   AND c.change_event_type IN ('C015', 'C013')
   AND c.change_action     = 'CHANGE_LIMIT'
   AND CAST(c.change_total_grantamount AS DOUBLE) > 0
   AND c.create_time >= DATE_ADD('day', -5,
         COALESCE(y.release_time, CAST(b.issue_date AS TIMESTAMP)))
   AND c.create_time <= COALESCE(y.release_time, CAST(b.issue_date AS TIMESTAMP))
  GROUP BY 1
),
bd AS (
  SELECT b.*,
         y.release_time, y.app_group, y.strategy_flag, y.use_score_1522, y.use_type_1523,
         y.issue_tag_1386, y.temp_grant_amount_check,
         f.loan_cycle, f.haircut_amount, f.should_interest,
         f.t0_should_capit_1, f.t0_overdue_capit_1, f.t0_should_capit_2, f.t0_overdue_capit_2,
         f.t0_should_capit_3, f.t0_overdue_capit_3, f.t0_should_capit_4, f.t0_overdue_capit_4,
         f.t3_should_capit_1, f.t3_overdue_capit_1,
         f.t7_should_capit_1, f.t7_overdue_capit_1, f.t7_should_capit_2, f.t7_overdue_capit_2,
         f.t7_should_capit_3, f.t7_overdue_capit_3, f.t7_should_capit_4, f.t7_overdue_capit_4,
         f.t7_overdue_interest_4,
         f.is_t0_window_1, f.is_t3_window_1, f.is_t0_window_2, f.is_t0_window_3,
         f.is_t0_window_4, f.is_t7_window_4,
         COALESCE(b.offline_used_this, 0) + COALESCE(b.online_used_this, 0) AS temp_used_total,
         ogr.offline_grant_time
  FROM base b
  LEFT JOIN yx   y ON y.biz_id = b.biz_id
  LEFT JOIN fn   f ON f.biz_id = CAST(b.biz_id AS VARCHAR)
  LEFT JOIN ogr    ON ogr.biz_id = b.biz_id
)
SELECT
  -- [A 标识与时间]
  biz_id, mid, issue_date, release_time,
  CAST(date_trunc('week',  CAST(issue_date AS TIMESTAMP)) AS DATE) AS issue_week,
  CAST(date_trunc('month', CAST(issue_date AS TIMESTAMP)) AS DATE) AS issue_month,
  product_level, app_group,
  android_oldCust_mainCreditLevel_charge_V6_1                       AS v6_1_level,
  CASE WHEN android_oldCust_mainCreditLevel_charge_V6_1 IS NULL THEN NULL
       ELSE CAST(FLOOR(android_oldCust_mainCreditLevel_charge_V6_1) AS INT) END AS v6_1_grade,

  -- [B 策略节点]
  strategy_flag,
  CASE WHEN strategy_flag LIKE '%V5_3%' THEN 'V5_3'
       WHEN strategy_flag LIKE '%V5_2%' THEN 'V5_2'
       WHEN strategy_flag IS NULL      THEN NULL
       ELSE 'other' END                                             AS strategy_version,
  use_score_1522, use_type_1523, issue_tag_1386, temp_grant_amount_check,

  -- [C 场景标签]
  CASE WHEN temp_used_total > 0 AND online_used_this > 0 THEN 'online'
       WHEN temp_used_total > 0 AND offline_used_this > 0 THEN 'offline'
       ELSE 'none' END                                              AS used_scenario,
  CASE WHEN offline_grant_amount > 0 AND online_grant_amount > 0 THEN 'both'
       WHEN online_grant_amount > 0  THEN 'online'
       WHEN offline_grant_amount > 0 THEN 'offline'
       ELSE 'none' END                                              AS grant_scenario,
  CASE WHEN offline_grant_amount > 0 THEN 1 ELSE 0 END              AS has_offline_grant,
  CASE WHEN online_grant_amount  > 0 THEN 1 ELSE 0 END              AS has_online_grant,
  CASE WHEN temp_used_total > 0 THEN 1 ELSE 0 END                   AS is_temp_used,

  -- [D 额度结构]（宽表2 原列，口径不改）
  contract_amount,
  credit_amount, change_used_grantamount, main_available_amount,
  daily_max_available_limit, risk_credit_limit, main_used_this,
  offline_grant_amount, offline_used_amount, offline_available_amount, offline_used_this,
  online_grant_amount, online_used_amount, online_available_amount, online_used_this,
  product_limit_max,
  avail_current_logic, avail_tochange_logic, avail_future_logic,
  voucher_limit, voucher_id,
  temp_used_total,
  CASE WHEN contract_amount > 0 THEN temp_used_total / contract_amount ELSE 0 END     AS temp_share_of_contract,
  CASE WHEN contract_amount > 0 THEN main_used_this  / contract_amount ELSE 0 END     AS main_share_of_contract,
  contract_amount - main_used_this                                    AS uplift_amount,
  CASE WHEN main_used_this > 0 THEN contract_amount / main_used_this ELSE NULL END    AS uplift_ratio,

  -- [E 上限约束]
  CASE WHEN main_used_this  >= 9999 THEN 1 ELSE 0 END                 AS is_main_capped,
  CASE WHEN contract_amount >= 9999 THEN 1 ELSE 0 END                 AS is_contract_capped,
  CASE WHEN contract_amount >= 9999 AND online_used_this > 0 THEN 'C'
       WHEN contract_amount >= 9999 AND offline_used_this > 0 THEN 'B'
       WHEN contract_amount >= 9999 AND temp_used_total = 0 THEN 'A'
       ELSE 'N' END                                                   AS cap_type,
  CASE WHEN contract_amount >= 9999
       THEN GREATEST(LEAST(main_available_amount + offline_available_amount, 50000)
                     - contract_amount, 0)
       ELSE 0 END                                                     AS add_if_cap_50000,

  -- [F 供给效率]
  offline_grant_time,
  CASE WHEN offline_grant_time IS NULL THEN NULL
       ELSE date_diff('day', CAST(offline_grant_time AS DATE), issue_date) END AS offline_age_days,
  CASE WHEN offline_grant_time IS NULL THEN NULL
       ELSE 5 - date_diff('day', CAST(offline_grant_time AS DATE), issue_date) END AS offline_expire_days,
  CASE WHEN offline_grant_amount > 0
       THEN offline_used_this / offline_grant_amount ELSE NULL END    AS offline_use_rate,
  GREATEST(offline_grant_amount - offline_used_amount - offline_used_this, 0) AS offline_unused_amount,
  CASE WHEN credit_amount > 0
       THEN offline_grant_amount / credit_amount ELSE NULL END        AS offline_grant_ratio,
  CASE WHEN online_used_this > 0 THEN 1 ELSE 0 END                    AS online_claimed,
  CASE WHEN online_grant_amount > 0
       THEN online_used_this / online_grant_amount ELSE NULL END      AS online_use_rate,

  -- [G 风险与收息]
  loan_cycle, haircut_amount, should_interest,
  CASE WHEN contract_amount > 0
       THEN (COALESCE(haircut_amount,0) + COALESCE(should_interest,0)) / contract_amount
       ELSE NULL END                                                  AS interest_rate,
  t0_should_capit_1, t0_overdue_capit_1,
  t0_should_capit_2, t0_overdue_capit_2,
  t0_should_capit_3, t0_overdue_capit_3,
  t0_should_capit_4, t0_overdue_capit_4,
  t3_should_capit_1, t3_overdue_capit_1,
  t7_should_capit_1, t7_overdue_capit_1,
  t7_should_capit_2, t7_overdue_capit_2,
  t7_should_capit_3, t7_overdue_capit_3,
  t7_should_capit_4, t7_overdue_capit_4, t7_overdue_interest_4,
  is_t0_window_1, is_t3_window_1, is_t0_window_2, is_t0_window_3, is_t0_window_4, is_t7_window_4,
  CASE WHEN t0_should_capit_1 > 0 THEN t0_overdue_capit_1 / t0_should_capit_1 END AS i1t0,
  CASE WHEN t0_should_capit_2 > 0 THEN t0_overdue_capit_2 / t0_should_capit_2 END AS i2t0,
  CASE WHEN t0_should_capit_3 > 0 THEN t0_overdue_capit_3 / t0_should_capit_3 END AS i3t0,
  CASE WHEN t0_should_capit_4 > 0 THEN t0_overdue_capit_4 / t0_should_capit_4 END AS i4t0,
  CASE WHEN t7_should_capit_4 > 0 THEN t7_overdue_capit_4 / t7_should_capit_4 END AS i4t7

FROM bd b
;
