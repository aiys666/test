-- =========================================================================
-- 06_结清后残留队列.sql
-- 探查目标: 按月回看，结清后临额残留是集中在哪段时间？是否已修复？
-- 方法: cohort队列 —— 取各月发起的TEMP冻结biz，看结清后还有多少残留
-- 关键月份:
--   2026-02: 缺陷高发期（队列≈22笔残留）
--   2026-03: 缺陷顶峰（队列≈112笔残留，770.4案例来源）
--   2026-06: 检查修复（残留≈0）
--   2026-07+: 确认无新增残留
-- =========================================================================


/* =========================================================================
   SQL 6-1: 3月队列 —— 结清后临额残留规模 + 公式命中
   探查目标: 包含案例用户来源两笔的月份，残留到底有多大？
   预期结论: settled_biz≈N，settled_resid_biz≈112笔，残留金额≈4.04万比索
   关键发现: 缺陷集中在2-3月，6月后消失
============================================================================= */
WITH seed AS (
  SELECT DISTINCT biz_id  AS biz
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND create_time >= timestamp'2026-03-01 00:00:00'
    AND create_time <  timestamp'2026-04-01 00:00:00'
),
led AS (
  SELECT
    biz_id  AS biz,
    SUM(CASE WHEN change_action = 'FREEZE_LIMIT'   THEN risk_credit_limit ELSE 0 END) AS frz,
    SUM(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN risk_credit_limit ELSE 0 END) AS unfr
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND biz_id IN (SELECT biz FROM seed)
  GROUP BY biz_id
),
rp0 AS (
  SELECT
    cast(camera_id as bigint) AS biz,
    indexs,
    should_capital,
    fact_time,
    state
  FROM ods_view_presto.s02_loan_repayment
  WHERE cast(camera_id as bigint) IN (SELECT biz FROM seed)
),
rp AS (
  SELECT
    biz,
    SUM(should_capital)                              AS cap_tot,
    MAX(indexs)                                       AS nper,
    SUM(CASE WHEN indexs = mx THEN should_capital ELSE 0 END) AS cap_last,
    SUM(CASE WHEN indexs <  mx THEN should_capital ELSE 0 END) AS cap_nonlast,
    MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END)       AS any_unpaid,
    MAX(fact_time)                                    AS last_pay_t
  FROM (SELECT *, MAX(indexs) OVER (PARTITION BY biz) AS mx FROM rp0) t
  GROUP BY biz
),
j AS (
  SELECT
    l.biz, l.frz, l.unfr,
    l.frz - l.unfr   AS resid,
    rp.cap_tot, rp.nper,
    rp.cap_last, rp.cap_nonlast,
    rp.any_unpaid, rp.last_pay_t
  FROM led l
  JOIN rp ON l.biz = rp.biz
)
SELECT
  COUNT(*)   AS settled_biz,
  COUNT(CASE WHEN resid > 0.01 THEN 1 END)            AS settled_resid_biz,
  round(SUM(CASE WHEN resid > 0.01 THEN resid ELSE 0 END), 1)    AS resid_amt,
  -- 残留公式命中
  COUNT(CASE WHEN resid > 0.01 AND ABS(resid - (frz - cap_last)) < 0.05 THEN 1 END)      AS f_frz_minus_last,
  COUNT(CASE WHEN resid > 0.01 AND ABS(resid - cap_nonlast) < 0.05 THEN 1 END)           AS f_frz_minus_nonlast,
  COUNT(CASE WHEN resid > 0.01 AND ABS(resid - frz) < 0.05 THEN 1 END)                   AS f_unreleased,
  COUNT(CASE WHEN resid > 0.01 AND ABS(resid - (cap_tot - cap_last)) < 0.05 THEN 1 END) AS f_tot_minus_last,
  COUNT(CASE WHEN resid > 0.01 AND nper = 2 THEN 1 END)                                  AS nper2,
  round(SUM(CASE WHEN resid > 0.01 THEN frz ELSE 0 END), 1)                              AS frz_amt
FROM j
WHERE any_unpaid = 0;


/* =========================================================================
   SQL 6-2: 2月队列 —— 同样逻辑，看更早月份的残留
   探查目标: 缺陷是从3月才开始，还是2月就有了？
   窗口: 2026-02-01 ~ 03-01
============================================================================= */
WITH seed AS (
  SELECT DISTINCT biz_id  AS biz
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND create_time >= timestamp'2026-02-01 00:00:00'
    AND create_time <  timestamp'2026-03-01 00:00:00'
),
led AS (
  SELECT
    biz_id  AS biz,
    SUM(CASE WHEN change_action = 'FREEZE_LIMIT'   THEN risk_credit_limit ELSE 0 END) AS frz,
    SUM(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN risk_credit_limit ELSE 0 END) AS unfr
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND biz_id IN (SELECT biz FROM seed)
  GROUP BY biz_id
),
rp0 AS (
  SELECT
    cast(camera_id as bigint) AS biz,
    indexs,
    should_capital,
    fact_time,
    state
  FROM ods_view_presto.s02_loan_repayment
  WHERE cast(camera_id as bigint) IN (SELECT biz FROM seed)
),
rp AS (
  SELECT
    biz,
    SUM(should_capital)                              AS cap_tot,
    MAX(indexs)                                       AS nper,
    SUM(CASE WHEN indexs = mx THEN should_capital ELSE 0 END) AS cap_last,
    SUM(CASE WHEN indexs <  mx THEN should_capital ELSE 0 END) AS cap_nonlast,
    MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END)       AS any_unpaid,
    MAX(fact_time)                                    AS last_pay_t
  FROM (SELECT *, MAX(indexs) OVER (PARTITION BY biz) AS mx FROM rp0) t
  GROUP BY biz
),
j AS (
  SELECT
    l.biz, l.frz, l.unfr,
    l.frz - l.unfr   AS resid,
    rp.cap_tot, rp.nper,
    rp.cap_last, rp.cap_nonlast,
    rp.any_unpaid, rp.last_pay_t
  FROM led l
  JOIN rp ON l.biz = rp.biz
)
SELECT
  COUNT(*)   AS settled_biz,
  COUNT(CASE WHEN resid > 0.01 THEN 1 END)            AS settled_resid_biz,
  round(SUM(CASE WHEN resid > 0.01 THEN resid ELSE 0 END), 1)    AS resid_amt,
  COUNT(CASE WHEN resid > 0.01 AND nper = 2 THEN 1 END)          AS nper2
FROM j
WHERE any_unpaid = 0;


/* =========================================================================
   SQL 6-3: 6月队列 —— 检查缺陷是否修复
   探查目标: 6月发起的临额，结清后还有残留吗？
   预期结论: 残留≈0（缺陷在3月后修复）
============================================================================= */
WITH seed AS (
  SELECT DISTINCT biz_id  AS biz
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND create_time >= timestamp'2026-06-01 00:00:00'
    AND create_time <  timestamp'2026-07-01 00:00:00'
),
led AS (
  SELECT
    biz_id  AS biz,
    SUM(CASE WHEN change_action = 'FREEZE_LIMIT'   THEN risk_credit_limit ELSE 0 END) AS frz,
    SUM(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN risk_credit_limit ELSE 0 END) AS unfr
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND biz_id IN (SELECT biz FROM seed)
  GROUP BY biz_id
),
rp0 AS (
  SELECT
    cast(camera_id as bigint) AS biz,
    indexs,
    should_capital,
    fact_time,
    state
  FROM ods_view_presto.s02_loan_repayment
  WHERE cast(camera_id as bigint) IN (SELECT biz FROM seed)
),
rp AS (
  SELECT
    biz,
    SUM(should_capital)                              AS cap_tot,
    MAX(indexs)                                       AS nper,
    SUM(CASE WHEN indexs = mx THEN should_capital ELSE 0 END) AS cap_last,
    SUM(CASE WHEN indexs <  mx THEN should_capital ELSE 0 END) AS cap_nonlast,
    MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END)       AS any_unpaid,
    MAX(fact_time)                                    AS last_pay_t
  FROM (SELECT *, MAX(indexs) OVER (PARTITION BY biz) AS mx FROM rp0) t
  GROUP BY biz
),
j AS (
  SELECT
    l.biz, l.frz, l.unfr,
    l.frz - l.unfr   AS resid,
    rp.cap_tot, rp.nper,
    rp.cap_last, rp.cap_nonlast,
    rp.any_unpaid, rp.last_pay_t
  FROM led l
  JOIN rp ON l.biz = rp.biz
)
SELECT
  COUNT(*)   AS settled_biz,
  COUNT(CASE WHEN resid > 0.01 THEN 1 END)            AS settled_resid_biz,
  round(SUM(CASE WHEN resid > 0.01 THEN resid ELSE 0 END), 1)    AS resid_amt,
  COUNT(CASE WHEN resid > 0.01 AND nper = 2 THEN 1 END)          AS nper2
FROM j
WHERE any_unpaid = 0;


/* =========================================================================
   SQL 6-4: 3月队列明细 Top25（案例用户来源月份）
   探查目标: 看3月残留的笔具体长什么样
============================================================================= */
WITH seed AS (
  SELECT DISTINCT biz_id  AS biz
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND create_time >= timestamp'2026-03-01 00:00:00'
    AND create_time <  timestamp'2026-04-01 00:00:00'
),
led AS (
  SELECT
    biz_id  AS biz,
    SUM(CASE WHEN change_action = 'FREEZE_LIMIT'   THEN risk_credit_limit ELSE 0 END) AS frz,
    SUM(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN risk_credit_limit ELSE 0 END) AS unfr
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND biz_id IN (SELECT biz FROM seed)
  GROUP BY biz_id
),
rp0 AS (
  SELECT
    cast(camera_id as bigint) AS biz,
    indexs,
    should_capital,
    fact_time,
    state
  FROM ods_view_presto.s02_loan_repayment
  WHERE cast(camera_id as bigint) IN (SELECT biz FROM seed)
),
rp AS (
  SELECT
    biz,
    SUM(should_capital)                              AS cap_tot,
    MAX(indexs)                                       AS nper,
    SUM(CASE WHEN indexs = mx THEN should_capital ELSE 0 END) AS cap_last,
    MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END)       AS any_unpaid,
    MAX(fact_time)                                    AS last_pay_t
  FROM (SELECT *, MAX(indexs) OVER (PARTITION BY biz) AS mx FROM rp0) t
  GROUP BY biz
)
SELECT
  l.biz,
  round(l.frz, 1)      AS frz,
  round(l.unfr, 1)     AS unfr,
  round(l.frz - l.unfr, 1) AS residue,
  nper,
  round(cap_tot, 1)    AS cap_tot,
  round(cap_last, 1)   AS cap_last,
  last_pay_t,
  date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00')   AS age_days
FROM led l
JOIN rp ON l.biz = rp.biz
WHERE any_unpaid = 0
  AND l.frz - l.unfr > 0.01
ORDER BY l.frz - l.unfr DESC
LIMIT 25;


/* =========================================================================
   SQL 6-5: 对账口径自检 —— 结清残留各种口径计数
   探查目标: 不同过滤条件（resid阈值、账龄阈值）下的残留规模
            解释为什么早期脚本报"304笔"而后来报"29笔"
   预期结论: 加了"账龄≥7天"且"resid>1"后，异常集从1200+缩小到29
============================================================================= */
WITH led AS (
  SELECT
    biz_id  AS biz,
    SUM(CASE WHEN change_action = 'FREEZE_LIMIT'   THEN risk_credit_limit ELSE 0 END) AS frz,
    SUM(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN risk_credit_limit ELSE 0 END) AS unfr
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND create_time >= timestamp'2026-07-01 00:00:00'
    AND create_time <  timestamp'2026-10-15 00:00:00'
  GROUP BY biz_id
),
rp0 AS (
  SELECT
    cast(camera_id as bigint) AS biz,
    indexs,
    should_capital,
    fact_time,
    state
  FROM ods_view_presto.s02_loan_repayment
  WHERE cast(camera_id as bigint) IN (SELECT biz FROM led)
),
rp AS (
  SELECT
    biz,
    SUM(should_capital)                              AS cap_tot,
    MAX(indexs)                                       AS nper,
    MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END)       AS any_unpaid,
    MAX(fact_time)                                    AS last_pay_t
  FROM rp0
  GROUP BY biz
),
j AS (
  SELECT
    l.biz, l.frz, l.unfr,
    l.frz - l.unfr   AS resid,
    rp.cap_tot, rp.nper,
    rp.any_unpaid, rp.last_pay_t
  FROM led l
  JOIN rp ON l.biz = rp.biz
)
SELECT
  -- 各种口径的结清残留计数（解释脚本间数字差异）
  SUM(CASE WHEN any_unpaid = 0 AND resid > 0.01 THEN 1 ELSE 0 END)                                                          AS settled_resid_any,
  SUM(CASE WHEN any_unpaid = 0 AND resid > 1 THEN 1 ELSE 0 END)                                                               AS settled_resid_gt1,
  SUM(CASE WHEN any_unpaid = 0 AND resid > 0.01 AND date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') >= 7 THEN 1 ELSE 0 END) AS settled_any_age7,
  SUM(CASE WHEN any_unpaid = 0 AND resid > 1 AND date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') >= 7    THEN 1 ELSE 0 END) AS settled_gt1_age7,
  SUM(CASE WHEN any_unpaid = 0 AND resid > 1 AND date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') >= 30   THEN 1 ELSE 0 END) AS settled_gt1_age30,
  round(SUM(CASE WHEN any_unpaid = 0 AND resid > 1 THEN resid ELSE 0 END), 1)                                                AS settled_gt1_amt,
  round(SUM(CASE WHEN any_unpaid = 0 AND resid > 1 AND date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') >= 7
               THEN resid ELSE 0 END), 1)                                                                                    AS settled_gt1_age7_amt
FROM j;


/* =========================================================================
   SQL 6-6: 结清残留>1的账龄分布
   探查目标: 残留主要是老的还是新的？
============================================================================= */
WITH led AS (
  SELECT
    biz_id  AS biz,
    SUM(CASE WHEN change_action = 'FREEZE_LIMIT'   THEN risk_credit_limit ELSE 0 END) AS frz,
    SUM(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN risk_credit_limit ELSE 0 END) AS unfr
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND create_time >= timestamp'2026-07-01 00:00:00'
    AND create_time <  timestamp'2026-10-15 00:00:00'
  GROUP BY biz_id
),
rp AS (
  SELECT
    cast(camera_id as bigint) AS biz,
    MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END)       AS any_unpaid,
    MAX(fact_time)                                    AS last_pay_t
  FROM ods_view_presto.s02_loan_repayment
  WHERE cast(camera_id as bigint) IN (SELECT biz FROM led)
  GROUP BY cast(camera_id as bigint)
),
j AS (
  SELECT
    l.biz,
    l.frz - l.unfr   AS resid,
    rp.any_unpaid,
    rp.last_pay_t
  FROM led l
  JOIN rp ON l.biz = rp.biz
)
SELECT
  CASE
    WHEN date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') <  0  THEN '0 负(当日)'
    WHEN date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') <= 1   THEN '1'
    WHEN date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') <= 3   THEN '2-3'
    WHEN date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') <= 7   THEN '4-7'
    WHEN date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') <= 30  THEN '8-30'
    ELSE                                                                       '>30'
  END                                                 AS age_b,
  COUNT(*)                                            AS cnt,
  round(SUM(resid), 1)                                AS resid_amt
FROM j
WHERE any_unpaid = 0
  AND resid > 1
GROUP BY 1
ORDER BY 1;
