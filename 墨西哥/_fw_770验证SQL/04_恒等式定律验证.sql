-- =========================================================================
-- 04_恒等式定律验证.sql
-- 核心数学证明：2个硬恒等式 + 账户级存量占用定律
-- 恒等式1: contract_amount = MAIN FREEZE + TEMP used（逐笔100%成立）
-- 恒等式2: C010.净可用 = used_detail TEMP FREEZE_LIMIT 该 biz 的冻结额（98.7%命中）
-- 账户级: change_used_grantamount(t) = Σ_{TEMP事件 ≤ t}(FREEZE − UNFREEZE)
-- =========================================================================


/* =========================================================================
   恒等式1 公式: contract_amount = risk_credit_limit(MAIN FREEZE) + temp_grant_amount(TEMP used)
   关联键: cast(biz_id as bigint) = used_detail.biz_id
   过滤: used_detail.change_action='FREEZE_LIMIT' AND limit_type='MAIN'（主额冻结）
   金额单位: yj.temp_grant_amount 是 bigint 分，÷1000.0 得比索
============================================================================= */

-- SQL 4-1: 案例用户逐笔验证（mid=1040160040722566）
-- 探查目标: 每笔放款都满足"合同额=主额冻结+使用临额"吗？
-- 预期结论: 所有笔 diff 列 ≈ 0（允许1比索以内舍入误差）
SELECT
  y.biz_id,
  y.app_date,
  y.contract_amount,
  round(y.temp_grant_amount / 1000.0, 1)                          AS temp_used,
  d.risk_credit_limit                                              AS main_freeze,
  round(d.risk_credit_limit + y.temp_grant_amount / 1000.0, 1)    AS main_plus_temp,
  round(y.contract_amount - d.risk_credit_limit - y.temp_grant_amount / 1000.0, 2) AS diff
FROM mx.yj_test_table_250225 y
JOIN ods.s05_user_creditlimit_used_detail d
  ON cast(y.biz_id as bigint) = d.biz_id
    AND d.change_action = 'FREEZE_LIMIT'
    AND d.limit_type = 'MAIN'
WHERE y.mid = 1040160040722566
  AND y.if_issue = 1
  AND y.temp_grant_amount > 0
ORDER BY y.app_date;


-- SQL 4-2: 全窗口恒等式命中率（复贷老客用临额放款）
-- 探查目标: 放大到全量，多少比例满足恒等式？
-- 窗口: 2026-08-19 ~ 2026-10-06
-- 预期结论: match_pct ≈ 100%（1比索内误差）
SELECT
  COUNT(*)                                                              AS used_loans,
  SUM(CASE WHEN ABS(y.contract_amount - d.risk_credit_limit
                     - y.temp_grant_amount / 1000.0) < 1
           THEN 1 ELSE 0 END)                                            AS match_cnt,
  round(100.0 * SUM(CASE WHEN ABS(y.contract_amount - d.risk_credit_limit
                              - y.temp_grant_amount / 1000.0) < 1
                         THEN 1 ELSE 0 END) / COUNT(*), 2)               AS match_pct
FROM mx.yj_test_table_250225 y
JOIN ods.s05_user_creditlimit_used_detail d
  ON cast(y.biz_id as bigint) = d.biz_id
    AND d.change_action = 'FREEZE_LIMIT'
    AND d.limit_type = 'MAIN'
WHERE y.is_reloan = 'old'
  AND y.if_issue = 1
  AND y.temp_grant_amount > 0
  AND y.app_date >= date'2026-08-19'
  AND y.app_date < date'2026-10-06';


/* =========================================================================
   恒等式2 公式: (C010.change_total_grantamount − C010.change_used_grantamount)
              = used_detail 该 biz 的 TEMP FREEZE_LIMIT 冻结额
   关联键: cast(C010.external_id as bigint) = used_detail.biz_id
   过滤: C010.limit_type='TEMP', change_event_type='C010'
         used_detail.limit_type='TEMP', change_action='FREEZE_LIMIT'
   关键窗口: 2026-07-01 ~ 2026-10-15（与台账对齐）
   预期命中率: 98.7%（失配主要来自跨月台账延迟）
============================================================================= */

-- SQL 4-3: 全量定律验证（L1）
-- 探查目标: C010净可用 是否等于 used_detail 的TEMP冻结额？
SELECT
  COUNT(*)   AS c010_with_biz,       -- 有external_id的C010总数
  COUNT(u.biz_id)                     AS matched_freeze_biz,    -- 能在台账找到冻结记录的
  SUM(CASE WHEN u.frz IS NOT NULL
            AND ABS((c.tot - c.used) - u.frz) < 0.1
           THEN 1 ELSE 0 END)         AS law_hit,               -- 定律命中
  round(100.0 * SUM(CASE WHEN u.frz IS NOT NULL
                            AND ABS((c.tot - c.used) - u.frz) < 0.1
                       THEN 1 ELSE 0 END) / COUNT(*), 2)             AS hit_pct
FROM (
  SELECT
    cast(external_id as bigint)   AS biz,
    change_total_grantamount     AS tot,
    change_used_grantamount      AS used,
    create_time
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE limit_type = 'TEMP'
    AND change_event_type = 'C010'
    AND create_time >= timestamp'2026-07-01 00:00:00'
    AND create_time <  timestamp'2026-10-15 00:00:00'
    AND external_id IS NOT NULL
    AND external_id <> ''
) c
LEFT JOIN (
  SELECT
    biz_id,
    SUM(risk_credit_limit)   AS frz
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND change_action = 'FREEZE_LIMIT'
    AND create_time >= timestamp'2026-07-01 00:00:00'
    AND create_time <  timestamp'2026-10-15 00:00:00'
  GROUP BY biz_id
) u
  ON c.biz = u.biz_id;


-- SQL 4-4: 定律命中率分层（L2）
-- 探查目标: "有存量占用(used>0)" vs "无存量占用(used≈0)"两组的命中率
-- 预期结论: 两组命中率都在98%以上，定律在两种场景下都成立
SELECT
  CASE
    WHEN c.used > 0.01 THEN 'A 有存量占用'
    ELSE                    'B 无存量占用'
  END                                    AS grp,
  COUNT(*)                               AS n,
  SUM(CASE WHEN u.frz IS NOT NULL
            AND ABS((c.tot - c.used) - u.frz) < 0.1
           THEN 1 ELSE 0 END)            AS hit,
  round(100.0 * SUM(CASE WHEN u.frz IS NOT NULL
                            AND ABS((c.tot - c.used) - u.frz) < 0.1
                       THEN 1 ELSE 0 END) / COUNT(*), 2)          AS hit_pct
FROM (
  SELECT
    cast(external_id as bigint)   AS biz,
    change_total_grantamount     AS tot,
    change_used_grantamount      AS used
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE limit_type = 'TEMP'
    AND change_event_type = 'C010'
    AND create_time >= timestamp'2026-07-01 00:00:00'
    AND create_time <  timestamp'2026-10-15 00:00:00'
    AND external_id IS NOT NULL
    AND external_id <> ''
) c
LEFT JOIN (
  SELECT
    biz_id,
    SUM(risk_credit_limit)   AS frz
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND change_action = 'FREEZE_LIMIT'
    AND create_time >= timestamp'2026-07-01 00:00:00'
    AND create_time <  timestamp'2026-10-15 00:00:00'
  GROUP BY biz_id
) u
  ON c.biz = u.biz_id
GROUP BY 1
ORDER BY 1;


-- SQL 4-5: 失配样例 Top20（L3）
-- 探查目标: 没命中定律的是啥情况？窗口覆盖不够？台账延迟？
-- 预期结论: 多数是台账窗口截断导致的（C010在10月中旬，但冻结记录在10月15日后）
SELECT
  c.biz,
  c.create_time,
  round(c.tot, 1)                              AS grant,
  round(c.used, 1)                             AS occupied,
  round(c.tot - c.used, 1)                     AS net_avail,
  round(u.frz, 1)                              AS real_freeze,
  round((c.tot - c.used) - COALESCE(u.frz, 0), 1) AS diff
FROM (
  SELECT
    cast(external_id as bigint)   AS biz,
    change_total_grantamount     AS tot,
    change_used_grantamount      AS used,
    create_time
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE limit_type = 'TEMP'
    AND change_event_type = 'C010'
    AND create_time >= timestamp'2026-07-01 00:00:00'
    AND create_time <  timestamp'2026-10-15 00:00:00'
    AND external_id IS NOT NULL
    AND external_id <> ''
) c
LEFT JOIN (
  SELECT
    biz_id,
    SUM(risk_credit_limit)   AS frz
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP'
    AND change_action = 'FREEZE_LIMIT'
    AND create_time >= timestamp'2026-07-01 00:00:00'
    AND create_time <  timestamp'2026-10-15 00:00:00'
  GROUP BY biz_id
) u
  ON c.biz = u.biz_id
WHERE u.frz IS NULL
   OR ABS((c.tot - c.used) - u.frz) >= 0.1
ORDER BY ABS((c.tot - c.used) - COALESCE(u.frz, 0)) DESC
LIMIT 20;
