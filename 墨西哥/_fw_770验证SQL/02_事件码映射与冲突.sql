-- =========================================================================
-- 02_事件码映射与冲突.sql
-- 探查目标: 明确各事件码(C010/C013/C015/C003/C004/C008)对应的 change_action
--           量化"未解冻即再发临额"的冲突规模
-- 关键发现: 解冻有两个事件码(C004+C008)，只识别C004会导致冲突虚高
-- =========================================================================

/* =========================================================================
   SQL 2-1: 事件码 × 动作 × 临/主额 全映射
   探查目标: 搞清楚每个事件码到底对应什么动作，主额还是临额
   预期结论:
     C010→INCREASE_LIMIT(TEMP)  在线临额发放
     C013/C015→INCREASE_LIMIT(TEMP) 离线临额发放
     C003→FREEZE_LIMIT        额度冻结
     C004/C008→UNFREEZE_LIMIT 额度解冻（⚠️ 两个事件码！）
     INCREASE/DECREASE_LIMIT → 调额
   涉及表: ods_view_presto.s05_user_creditlimit_change_record
============================================================================= */
SELECT
  change_event_type    AS evt,
  change_action,
  limit_type,
  COUNT(*)             AS c
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE create_time >= date'2026-07-01'
GROUP BY 1, 2, 3
ORDER BY c DESC
LIMIT 30;


/* =========================================================================
   SQL 2-2: 只看临额的事件码映射（去掉主额干扰）
   探查目标: 把limit_type='TEMP'过滤，单独看临额侧事件分布
   预期结论: C010/C013/C015 + FREEZE/UNFREEZE 是临额侧主要事件
============================================================================= */
SELECT
  change_event_type    AS evt,
  change_action,
  COUNT(*)             AS c
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE create_time >= date'2026-07-01'
  AND limit_type = 'TEMP'
GROUP BY 1, 2
ORDER BY c DESC;


/* =========================================================================
   SQL 2-3: 解冻覆盖验证 —— C004 vs C008 占比
   探查目标: 两个解冻事件码各占多少？只用C004会不会漏？
   预期结论: C008约占4%，只用C004会漏掉这部分，导致"未解冻"假阳性
   涉及表: ods_view_presto.s05_user_creditlimit_change_record
   关联键: 同时看 change_action='UNFREEZE_LIMIT'
============================================================================= */
SELECT
  change_event_type    AS evt,
  COUNT(*)             AS unfreeze_cnt,
  round(100.0 * COUNT(*) / (SELECT COUNT(*)
    FROM ods_view_presto.s05_user_creditlimit_change_record
    WHERE create_time >= date'2026-07-01'
      AND change_action = 'UNFREEZE_LIMIT'), 2) AS pct_of_all_unfreeze
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE create_time >= date'2026-07-01'
  AND change_action = 'UNFREEZE_LIMIT'
GROUP BY change_event_type
ORDER BY unfreeze_cnt DESC;


/* =========================================================================
   SQL 2-4: 冲突扫描 —— 未解冻即再发临额（总规模）
   探查目标: 量化"还有FREEZE没UNFREEZE就又发了C010/C013/C015"的冲突数
   关键CTE: CONFLICT_BASE —— 用窗口函数查上一个FREEZE和上一个UNFREEZE的时间
   冲突条件: 当前是发放事件(C010/13/15) 且 上一次是FREEZE 且 之后没有UNFREEZE
   预期结论: 在线侧(C010)冲突率≈0.1%，离线侧略高；跨笔冲突几乎全来自离线
============================================================================= */
WITH CONFLICT_BASE AS (
  SELECT
    mid,
    create_time,
    change_event_type    AS evt,
    change_action,
    -- 上一个 FREEZE_LIMIT 的时间（同mid）
    MAX(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN create_time END)
      OVER (PARTITION BY mid ORDER BY create_time
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)  AS last_unfz,
    -- 上一个 UNFREEZE_LIMIT 的时间（同mid）
    MAX(CASE WHEN change_action = 'FREEZE_LIMIT' THEN create_time END)
      OVER (PARTITION BY mid ORDER BY create_time
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)  AS last_frz
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE create_time >= date'2026-07-01'
    AND limit_type = 'TEMP'
    AND (change_event_type IN ('C010', 'C013', 'C015')
         OR change_action IN ('FREEZE_LIMIT', 'UNFREEZE_LIMIT'))
),
COND AS (
  evt IN ('C010', 'C013', 'C015')
  AND last_frz IS NOT NULL
  AND (last_unfz IS NULL OR last_frz > last_unfz)
)
SELECT
  COUNT(CASE WHEN evt IN ('C010', 'C013', 'C015') THEN 1 END)       AS grant_total,
  COUNT(CASE WHEN (last_frz IS NOT NULL AND (last_unfz IS NULL OR last_frz > last_unfz))
            AND evt IN ('C010', 'C013', 'C015') THEN 1 END)         AS conflict_cnt,
  round(100.0 * COUNT(CASE WHEN last_frz IS NOT NULL
                              AND (last_unfz IS NULL OR last_frz > last_unfz)
                              AND evt IN ('C010', 'C013', 'C015')
                         THEN 1 END)
       / NULLIF(COUNT(CASE WHEN evt IN ('C010', 'C013', 'C015') THEN 1 END), 0), 2)
                                                                     AS conflict_pct,
  COUNT(DISTINCT mid)                                                AS mid_total,
  COUNT(DISTINCT CASE WHEN last_frz IS NOT NULL
                          AND (last_unfz IS NULL OR last_frz > last_unfz)
                          AND evt IN ('C010', 'C013', 'C015')
                     THEN mid END)                                   AS conflict_mids
FROM CONFLICT_BASE;


/* =========================================================================
   SQL 2-5: 冲突按调额类型拆分
   探查目标: 冲突是在线(C010)还是离线(C013/15)为主？
   预期结论: C010冲突极少（系统自动控），冲突几乎全来自离线批次叠加
============================================================================= */
WITH CONFLICT_BASE AS (
  SELECT
    mid,
    create_time,
    change_event_type    AS evt,
    change_action,
    MAX(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN create_time END)
      OVER (PARTITION BY mid ORDER BY create_time
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)  AS last_unfz,
    MAX(CASE WHEN change_action = 'FREEZE_LIMIT' THEN create_time END)
      OVER (PARTITION BY mid ORDER BY create_time
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)  AS last_frz
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE create_time >= date'2026-07-01'
    AND limit_type = 'TEMP'
    AND (change_event_type IN ('C010', 'C013', 'C015')
         OR change_action IN ('FREEZE_LIMIT', 'UNFREEZE_LIMIT'))
)
SELECT
  evt                          AS grant_evt,
  COUNT(*)                     AS conflict_cnt,
  COUNT(DISTINCT mid)          AS conflict_mids
FROM CONFLICT_BASE
WHERE evt IN ('C010', 'C013', 'C015')
  AND last_frz IS NOT NULL
  AND (last_unfz IS NULL OR last_frz > last_unfz)
GROUP BY 1
ORDER BY conflict_cnt DESC;


/* =========================================================================
   SQL 2-6: 冲突样例事件流（取2个冲突mid的完整事件）
   探查目标: 具象看冲突长什么样——是替换？还是叠加？还是续期？
   预期结论: 多数冲突是"续期"（快到期再发，旧的还没解冻），非恶意叠加
============================================================================= */
-- 先取2个冲突mid（如果没有冲突则返回空）
SELECT
  e2.mid,
  e2.create_time,
  e2.change_action,
  round(e2.change_total_grantamount, 1)   AS total_grant,
  round(e2.change_used_grantamount, 1)     AS used_grant,
  e2.expiring_time,
  e2.change_event_type                     AS evt
FROM ods_view_presto.s05_user_creditlimit_change_record e2
WHERE e2.limit_type = 'TEMP'
  AND e2.mid IN (
    -- 子查询：取前2个有冲突的mid
    WITH cb AS (
      SELECT mid, create_time, change_event_type AS evt, change_action,
        MAX(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN create_time END)
          OVER (PARTITION BY mid ORDER BY create_time
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS last_unfz,
        MAX(CASE WHEN change_action = 'FREEZE_LIMIT' THEN create_time END)
          OVER (PARTITION BY mid ORDER BY create_time
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS last_frz
      FROM ods_view_presto.s05_user_creditlimit_change_record
      WHERE create_time >= date'2026-07-01'
        AND limit_type = 'TEMP'
        AND (change_event_type IN ('C010', 'C013', 'C015')
             OR change_action IN ('FREEZE_LIMIT', 'UNFREEZE_LIMIT'))
    )
    SELECT DISTINCT mid FROM cb
    WHERE evt IN ('C010', 'C013', 'C015')
      AND last_frz IS NOT NULL
      AND (last_unfz IS NULL OR last_frz > last_unfz)
    ORDER BY mid LIMIT 2
  )
ORDER BY e2.mid, e2.create_time;


/* =========================================================================
   SQL 2-7: 解冻事件按 C004/C008 拆分（⚠️ 关键修正！）
   探查目标: 之前只看 change_action='UNFREEZE_LIMIT' 没区分事件码
             现在搞清楚 C004(还款释额) 和 C008(用信失败释额) 各占多少
   预期结论: C004占绝大多数（每次还款都触发），C008很少（用信失败是少数）
   文档依据: 《墨西哥循环额度》V1.5
     C004 = 还本金时触发(含前期/催收/减免)，锁定额度 -= 本次还本金
     C008 = 用信审核不通过/放款失败，锁定额度 -= 本次用信额度
============================================================================= */
SELECT
  change_event_type      AS evt,
  change_action,
  limit_type,
  COUNT(*)                                                            AS cnt,
  round(SUM(change_total_grantamount), 1)                             AS total_amt,
  round(SUM(change_used_grantamount), 1)                              AS used_amt,
  round(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY change_action), 1) AS pct_in_action
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE create_time >= date'2026-07-01'
  AND change_action = 'UNFREEZE_LIMIT'
GROUP BY 1, 2, 3
ORDER BY cnt DESC;


/* =========================================================================
   SQL 2-8: 冲突扫描修正版 —— 区分 C004(还款释额) 和 C008(用信失败释额)
   探查目标: 之前把C004和C008都当作"解冻"，可能导致冲突判定不准确
             实际上C008是用信失败的回滚，不应该算作"还款解冻"
   修正点: 只把 C004 作为"还款解冻"来判断冲突（C008是用信失败回滚）
============================================================================= */
WITH CONFLICT_BASE AS (
  SELECT
    mid,
    create_time,
    change_event_type    AS evt,
    change_action,
    -- 上一个 C004 还款释额的时间（⚠️ 只看C004，不含C008）
    MAX(CASE WHEN change_event_type = 'C004' THEN create_time END)
      OVER (PARTITION BY mid ORDER BY create_time
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)  AS last_c004,
    -- 上一个 FREEZE_LIMIT 的时间
    MAX(CASE WHEN change_action = 'FREEZE_LIMIT' THEN create_time END)
      OVER (PARTITION BY mid ORDER BY create_time
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)  AS last_frz
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE create_time >= date'2026-07-01'
    AND limit_type = 'TEMP'
    AND (change_event_type IN ('C010', 'C013', 'C015', 'C004', 'C008')
         OR change_action IN ('FREEZE_LIMIT', 'UNFREEZE_LIMIT'))
)
SELECT
  COUNT(CASE WHEN evt IN ('C010', 'C013', 'C015') THEN 1 END)                       AS grant_total,
  -- 冲突判定: 上一次是FREEZE 且 之后没有C004还款释额
  COUNT(CASE WHEN evt IN ('C010', 'C013', 'C015')
              AND last_frz IS NOT NULL
              AND (last_c004 IS NULL OR last_frz > last_c004)
             THEN 1 END)                                                           AS conflict_cnt_c004,
  round(100.0 * COUNT(CASE WHEN evt IN ('C010', 'C013', 'C015')
                           AND last_frz IS NOT NULL
                           AND (last_c004 IS NULL OR last_frz > last_c004)
                          THEN 1 END)
       / NULLIF(COUNT(CASE WHEN evt IN ('C010', 'C013', 'C015') THEN 1 END), 0), 2) AS conflict_pct
FROM CONFLICT_BASE;
