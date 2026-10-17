-- =========================================================================
-- 08_补充_主额台账与C004C008差异.sql
-- 回应2个关键问题:
--   Q1: 主额(limit_type=MAIN)是否也存在"结清后残留"?
--   Q2: C004(还款释额) vs C008(用信失败释额)的实际数据差异
--
-- 文档关键定义(来自《墨西哥循环额度》V1.5):
--   C003 用信冻结: 先主额再临时, 锁定额度 += 本次用信额度
--   C008 用信失败释额: 锁定额度 -= 本次用信额度
--   C004 还款释额: 只要应还本金有减少就触发(含催收/减免), 锁定额度 -= 本次还本金
--   C002 单期还清调额: 2025-08-27改为"每期还清都触发"
-- =========================================================================


/* =========================================================================
   SQL 8-1: 主额台账 —— 案例用户MAIN额度的FREEZE/UNFREEZE
   探查目标: 主额是否也有"冻结后没解冻"的残留？
   涉及表: ods.s05_user_creditlimit_used_detail
   过滤: mid=1040160040722566, limit_type='MAIN'
============================================================================= */
SELECT
  biz_id,
  change_action,                           -- FREEZE_LIMIT / UNFREEZE_LIMIT
  round(risk_credit_limit, 1)    AS amt,   -- 本次冻结/解冻金额（比索）
  create_time,
  update_time
FROM ods.s05_user_creditlimit_used_detail
WHERE mid = 1040160040722566
  AND limit_type = 'MAIN'
ORDER BY create_time;


/* =========================================================================
   SQL 8-2: 主额台账对账 —— 每笔biz的冻结-解冻=剩余占用
   探查目标: 主额是否存在残留？
   预期结论: 主额应该没有残留（每期还款C004都释额）
             如果有残留，说明主额也有同类bug
============================================================================= */
WITH d AS (
  SELECT
    biz_id,
    SUM(CASE WHEN change_action = 'FREEZE_LIMIT'   THEN risk_credit_limit ELSE 0 END) AS frz,
    SUM(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN risk_credit_limit ELSE 0 END) AS unfrz
  FROM ods.s05_user_creditlimit_used_detail
  WHERE mid = 1040160040722566
    AND limit_type = 'MAIN'
    AND create_time >= timestamp'2026-02-01 00:00:00'
  GROUP BY biz_id
)
SELECT
  biz_id,
  round(frz, 1)                         AS frz_sum,
  round(unfrz, 1)                       AS unfrz_sum,
  round(frz - unfrz, 1)                 AS residue
FROM d
ORDER BY residue DESC;


/* =========================================================================
   SQL 8-3: 全量主额残留统计（非案例用户，看整体）
   探查目标: 全量主额有多少biz存在残留？规模多大？
   对比临额侧: 临额残留约29笔(稳态)
   预期结论: 主额残留应为0或极少（如果系统按文档实现的话）
============================================================================= */
WITH d AS (
  SELECT
    biz_id,
    SUM(CASE WHEN change_action = 'FREEZE_LIMIT'   THEN risk_credit_limit ELSE 0 END) AS frz,
    SUM(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN risk_credit_limit ELSE 0 END) AS unfrz
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'MAIN'
    AND create_time >= timestamp'2026-07-01 00:00:00'
    AND create_time <  timestamp'2026-10-15 00:00:00'
  GROUP BY biz_id
)
SELECT
  COUNT(*)                                            AS total_biz,
  COUNT(CASE WHEN frz - unfrz > 0.01 THEN 1 END)       AS resid_biz,
  round(SUM(CASE WHEN frz - unfrz > 0.01 THEN frz - unfrz ELSE 0 END), 1) AS resid_amt,
  round(100.0 * COUNT(CASE WHEN frz - unfrz > 0.01 THEN 1 END) / NULLIF(COUNT(*), 0), 2) AS resid_pct
FROM d;


/* =========================================================================
   SQL 8-4: 案例用户两笔来源的解冻事件 —— 区分C004还是C008
   探查目标: 770.4案例中的解冻是"还款释额(C004)"还是"用信失败释额(C008)"？
   关键: 文档说C004每次还本金都触发，但案例中只有末期解冻
   涉及表: ods_view_presto.s05_user_creditlimit_change_record
   过滤: mid=1040160040722566, change_event_type IN ('C004','C008')
============================================================================= */
SELECT
  limit_main_id,
  create_time,
  change_event_type      AS evt,        -- C004=还款释额, C008=用信失败释额
  change_action,
  round(change_total_grantamount, 1)   AS total_grant,
  round(change_used_grantamount, 1)     AS used_grant,
  expiring_time,
  change_desc
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE mid = 1040160040722566
  AND change_event_type IN ('C004', 'C008')
ORDER BY create_time;


/* =========================================================================
   SQL 8-5: 解冻事件按C004/C008拆分（全量统计）
   探查目标: 全量解冻中C004和C008各占多少？
   预期结论: C004应该占绝大多数（还款释额是常态）
             C008应该很少（用信失败是少数）
   对比: 之前冲突扫描只看change_action='UNFREEZE_LIMIT'没区分
============================================================================= */
SELECT
  change_event_type      AS evt,
  change_action,
  limit_type,
  COUNT(*)               AS cnt,
  round(SUM(change_total_grantamount), 1)  AS total_amt,
  round(SUM(change_used_grantamount), 1)   AS used_amt
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE create_time >= date'2026-07-01'
  AND change_action = 'UNFREEZE_LIMIT'
GROUP BY 1, 2, 3
ORDER BY cnt DESC;


/* =========================================================================
   SQL 8-6: 案例用户两笔老贷的还款计划 + 解冻时间对齐
   探查目标: 验证C004是否真的只在末期触发
   方法: 把还款计划的fact_time和K表的C004时间对齐
   预期结论: 
     如果C004在每期还款后都触发 → 说明文档实现正确，770.4是其他原因
     如果C004只在末期触发 → 说明2-3月有bug，只放末期本金
   关联: cast(camera_id as bigint)
============================================================================= */
-- 还款计划
SELECT
  'repayment'       AS src,
  cast(camera_id as bigint)  AS biz,
  indexs,
  state,
  should_capital,
  fact_capital,
  should_time,
  fact_time
FROM ods_view_presto.s02_loan_repayment
WHERE cast(camera_id as bigint) IN (1620000395926822, 1620000396309679)
ORDER BY cast(camera_id as bigint), indexs;

-- 对应的C004/C008解冻事件（时间对齐）
SELECT
  'unfreeze'        AS src,
  limit_main_id,
  create_time,
  change_event_type AS evt,
  round(change_total_grantamount, 1) AS total_grant,
  round(change_used_grantamount, 1)   AS used_grant
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE mid = 1040160040722566
  AND change_event_type IN ('C004', 'C008')
  AND create_time >= timestamp'2026-03-01 00:00:00'
ORDER BY create_time;


/* =========================================================================
   SQL 8-7: 主额 vs 临额 残留对比（同窗口）
   探查目标: 主额和临额哪个残留多？
   结论: 临额残留是bug还是主额也有？
============================================================================= */
WITH all_detail AS (
  SELECT
    biz_id,
    limit_type,
    SUM(CASE WHEN change_action = 'FREEZE_LIMIT'   THEN risk_credit_limit ELSE 0 END) AS frz,
    SUM(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN risk_credit_limit ELSE 0 END) AS unfr
  FROM ods.s05_user_creditlimit_used_detail
  WHERE create_time >= timestamp'2026-07-01 00:00:00'
    AND create_time <  timestamp'2026-10-15 00:00:00'
    AND limit_type IN ('MAIN', 'TEMP')
  GROUP BY biz_id, limit_type
)
SELECT
  limit_type,
  COUNT(*)                                            AS total_biz,
  COUNT(CASE WHEN frz - unfr > 0.01 THEN 1 END)       AS resid_biz,
  round(SUM(CASE WHEN frz - unfr > 0.01 THEN frz - unfr ELSE 0 END), 1) AS resid_amt,
  round(100.0 * COUNT(CASE WHEN frz - unfr > 0.01 THEN 1 END) / NULLIF(COUNT(*), 0), 2) AS resid_pct
FROM all_detail
GROUP BY 1
ORDER BY 1;
