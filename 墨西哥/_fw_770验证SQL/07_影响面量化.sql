-- =========================================================================
-- 07_影响面量化.sql
-- 核心问题: "存量占用/结清后残留"到底影响多大范围？
-- 方法: 全量C010统计 —— 被抵扣的笔数、金额、占比分布
-- 关键发现:
--   全量C010中 2.4% 被存量占用抵扣
--   总抵扣额 10.6万比索 vs 名义发放 677.1万 → 占比 1.6%
--   尾部29笔抵扣占发放额>75%（极端case）
-- 窗口: 2026-07-01 ~ 2026-10-15（同台账窗口对齐）
-- =========================================================================


/* =========================================================================
   SQL 7-1: C010 全量影响面统计
   探查目标: 在全量在线临额发放中，多少笔被存量占用"搭便车"抵扣了？
   关键字段:
     change_total_grantamount —— 名义发放额
     change_used_grantamount —— ⚠️ 发放前已有的存量占用（抵扣额）
   抵扣判定: change_used_grantamount > 0.01
   预期结论:
     c010_cnt ≈ 13701 笔
     occ_cnt ≈ 324 笔（2.4%）
     occ_amt_pos ≈ 10.6万比索（抵扣总额）
     grant_amt ≈ 677.1万比索（名义发放总额）
     抵扣率 = 10.6/677.1 ≈ 1.6%
============================================================================= */
SELECT
  COUNT(*)                                              AS c010_cnt,
  COUNT(DISTINCT mid)                                   AS mid_cnt,
  -- 被抵扣的笔数/客户数
  SUM(CASE WHEN change_used_grantamount > 0.01 THEN 1 ELSE 0 END)          AS occ_cnt,
  COUNT(DISTINCT CASE WHEN change_used_grantamount > 0.01 THEN mid END)    AS occ_mid_cnt,
  -- 金额
  round(SUM(change_total_grantamount), 1)                                   AS grant_amt,
  round(SUM(change_used_grantamount), 1)                                    AS occ_amt,
  round(SUM(CASE WHEN change_used_grantamount > 0.01
                  THEN change_used_grantamount ELSE 0 END), 1)              AS occ_amt_pos,
  round(SUM(change_total_grantamount - change_used_grantamount), 1)         AS net_amt,
  -- 占比
  round(100.0 * SUM(CASE WHEN change_used_grantamount > 0.01 THEN 1 ELSE 0 END)
                 / NULLIF(COUNT(*), 0), 2)                                  AS occ_cnt_pct,
  round(100.0 * SUM(CASE WHEN change_used_grantamount > 0.01
                          THEN change_used_grantamount ELSE 0 END)
                 / NULLIF(SUM(change_total_grantamount), 0), 2)             AS occ_amt_pct
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE limit_type = 'TEMP'
  AND change_event_type = 'C010'
  AND create_time >= timestamp'2026-07-01 00:00:00'
  AND create_time <  timestamp'2026-10-15 00:00:00';


/* =========================================================================
   SQL 7-2: 抵扣占比分布 + 极端尾部
   探查目标: 抵扣额占名义发放额的比例分布？有没有极端case？
   分桶: 0 / (0,10%] / (10%,25%] / (25%,50%] / (50%,75%] / (75%,100%) / ≈100%
   预期结论: 多数抵扣<25%，尾部有≈29笔抵扣>75%（极端case）
   Presto陷阱: 必须过滤 change_total_grantamount > 0，否则 used/tot 除零！
============================================================================= */
WITH c AS (
  SELECT
    change_total_grantamount              AS tot,
    change_used_grantamount               AS used
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE limit_type = 'TEMP'
    AND change_event_type = 'C010'
    AND create_time >= timestamp'2026-07-01 00:00:00'
    AND create_time <  timestamp'2026-10-15 00:00:00'
    AND change_total_grantamount > 0    -- ⚠️ 防除零！
)
SELECT
  CASE
    WHEN used <= 0.01    THEN '0 无抵扣'
    WHEN used / tot <= 0.10 THEN '1 (0,10%]'
    WHEN used / tot <= 0.25 THEN '2 (10%,25%]'
    WHEN used / tot <= 0.50 THEN '3 (25%,50%]'
    WHEN used / tot <= 0.75 THEN '4 (50%,75%]'
    WHEN used / tot <  0.99999 THEN '5 (75%,100%)'
    ELSE                       '6 净可用≈0(全额被占)'
  END                                                                     AS bucket,
  COUNT(*)                                                                AS cnt,
  round(SUM(used), 1)                                                     AS used_amt,
  round(SUM(tot), 1)                                                      AS grant_amt,
  round(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                     AS cnt_pct_all
FROM c
GROUP BY 1
ORDER BY 1;


/* =========================================================================
   SQL 7-3: 抵扣>75%的极端尾部明细（top20）
   探查目标: 具象看最严重的case —— 抵扣额占发放额比例
   关联键: 用external_id关联biz，看对应哪笔老贷的残留
============================================================================= */
SELECT
  cast(external_id as bigint)                                              AS biz,
  mid,
  create_time,
  round(change_total_grantamount, 1)                                       AS grant,
  round(change_used_grantamount, 1)                                        AS occupied,
  round(change_used_grantamount / NULLIF(change_total_grantamount, 0) * 100, 1) AS occ_pct,
  expiring_time
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE limit_type = 'TEMP'
  AND change_event_type = 'C010'
  AND create_time >= timestamp'2026-07-01 00:00:00'
  AND create_time <  timestamp'2026-10-15 00:00:00'
  AND change_total_grantamount > 0
  AND change_used_grantamount / change_total_grantamount > 0.75
ORDER BY change_used_grantamount / change_total_grantamount DESC
LIMIT 20;


/* =========================================================================
   SQL 7-4: 抵扣笔数按月份分布（看趋势）
   探查目标: 抵扣现象是最近才出现的还是一直都有？有无恶化？
   预期结论: 每月抵扣笔数稳定在一定水平，无明显趋势
============================================================================= */
SELECT
  date_format(create_time, '%Y-%m')                                         AS m,
  COUNT(*)                                                                  AS c010_cnt,
  SUM(CASE WHEN change_used_grantamount > 0.01 THEN 1 ELSE 0 END)           AS occ_cnt,
  round(SUM(CASE WHEN change_used_grantamount > 0.01
                  THEN change_used_grantamount ELSE 0 END), 1)              AS occ_amt,
  round(100.0 * SUM(CASE WHEN change_used_grantamount > 0.01 THEN 1 ELSE 0 END)
                 / NULLIF(COUNT(*), 0), 2)                                  AS occ_cnt_pct
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE limit_type = 'TEMP'
  AND change_event_type = 'C010'
  AND create_time >= timestamp'2026-07-01 00:00:00'
  AND create_time <  timestamp'2026-10-15 00:00:00'
GROUP BY 1
ORDER BY 1;
