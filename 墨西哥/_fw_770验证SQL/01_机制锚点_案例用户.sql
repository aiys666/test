-- =========================================================================
-- 01_机制锚点_案例用户.sql
-- 探查链条起点：从"mid=1040160040722566每次领临额都被占770.4"这个异常锚点
-- 逐步推理→台账对账→交叉验证→定位到"两笔3月老贷解冻缺陷残留"
--
-- 案例用户: mid = 1040160040722566
-- 残留来源两笔: biz_id 1620000395926822 + 1620000396309679
-- =========================================================================

/* =========================================================================
   SQL 1-1: 异常锚点发现
   探查目标: 为什么每次在线临额发放时 used_grant 恒为 770.4?
   预期结论: 从2026-08起每次C010的change_used_grantamount都是770.4，不随发放额变化
   涉及表: ods_view_presto.s05_user_creditlimit_change_record
   关联键/过滤: mid=1040160040722566, limit_type='TEMP', change_event_type='C010'
   关键修正: 这里的 change_used_grantamount 是"发放前存量占用"，不是本次支用!
============================================================================= */
SELECT
  create_time,
  round(change_total_grantamount, 1)     AS grant,        -- 本次名义发放额
  round(change_used_grantamount, 1)      AS occupied,     -- ⚠️ 存量占用（来源）
  round(change_total_grantamount - change_used_grantamount, 1) AS net_avail,
  expiring_time
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE mid = 1040160040722566
  AND limit_type = 'TEMP'
  AND change_event_type = 'C010'
ORDER BY create_time;


/* =========================================================================
   SQL 1-2: TEMP 占用台账（逐笔 FREEZE/UNFREEZE）
   探查目标: 逐笔列出该客户所有临额冻结/解冻，看哪笔没被释放
   预期结论: 每笔biz有FREEZE就有对应的UNFREEZE，但两笔老贷只解冻了末期
   涉及表: ods.s05_user_creditlimit_used_detail（台账！不是K表）
   关联键/过滤: mid=1040160040722566, limit_type='TEMP'
   Presto陷阱: ❌ used_detail 没有 change_desc 字段！不要查！
============================================================================= */
SELECT
  biz_id,
  change_action,                           -- FREEZE_LIMIT / UNFREEZE_LIMIT
  round(risk_credit_limit, 1)    AS amt,   -- 本次冻结/解冻金额（比索）
  create_time,
  update_time
FROM ods.s05_user_creditlimit_used_detail
WHERE mid = 1040160040722566
  AND limit_type = 'TEMP'
  AND create_time >= timestamp'2026-02-01 00:00:00'
ORDER BY create_time;


/* =========================================================================
   SQL 1-3: 台账对账 —— 每笔 biz 的冻结-解冻=剩余占用
   探查目标: 定量计算哪笔biz有残留，合计是否=770.4
   预期结论: 两笔老贷（1620000395926822、1620000396309679）残留合计≈770.4
   涉及表: ods.s05_user_creditlimit_used_detail
   验证逻辑: Σ(FREEZE) - Σ(UNFREEZE) = 实际占用（应该=change_used_grantamount）
============================================================================= */
WITH d AS (
  SELECT
    biz_id,
    SUM(CASE WHEN change_action = 'FREEZE_LIMIT'   THEN risk_credit_limit ELSE 0 END) AS frz,
    SUM(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN risk_credit_limit ELSE 0 END) AS unfrz
  FROM ods.s05_user_creditlimit_used_detail
  WHERE mid = 1040160040722566
    AND limit_type = 'TEMP'
    AND create_time >= timestamp'2026-02-01 00:00:00'
  GROUP BY biz_id
)
SELECT
  biz_id,
  round(frz, 1)                         AS frz_sum,      -- 累计冻结
  round(unfrz, 1)                       AS unfrz_sum,    -- 累计解冻
  round(frz - unfrz, 1)                 AS residue       -- ⚠️ 剩余占用（>0即未释放）
FROM d
WHERE frz - unfrz > 0.01
ORDER BY residue DESC;

-- 【验证公式】上面 residue 合计 应 = SQL 1-1 的 occupied 列恒值 770.4


/* =========================================================================
   SQL 1-4: 交叉验证 —— 净可用 vs yj 实际用额
   探查目标: C010的"名义发放-存量占用"是否等于实际使用的临额？
   预期结论: 高度吻合（yj.temp_grant_amount/1000 ≈ C010净可用）
   涉及表: ods_view_presto.s05_user_creditlimit_change_record + mx.yj_test_table_250225
   关联键: cast(external_id as bigint) = cast(yj.biz_id as bigint)
   金额单位: yj.temp_grant_amount 是 bigint 分，÷1000.0 得比索
============================================================================= */
SELECT
  c.create_time,
  round(c.change_total_grantamount, 1)                          AS grant_,
  round(c.change_total_grantamount - c.change_used_grantamount, 1) AS net_avail, -- 净可用
  round(y.temp_grant_amount / 1000.0, 1)                        AS yj_used,    -- yj实际使用
  y.biz_id
FROM ods_view_presto.s05_user_creditlimit_change_record c
JOIN mx.yj_test_table_250225 y
  ON cast(c.external_id as bigint) = cast(y.biz_id as bigint)
WHERE c.mid = 1040160040722566
  AND c.limit_type = 'TEMP'
  AND c.change_event_type = 'C010'
  AND c.external_id IS NOT NULL
  AND c.external_id <> ''
  AND c.create_time >= date'2026-08-01'
ORDER BY c.create_time;


/* =========================================================================
   SQL 1-5: 来源两笔在 yj 的履约/逾期状态
   探查目标: 这两笔老贷还在逾期吗？还是已结清但没解冻？
   预期结论: 两笔均为状态正常（t0/t3逾期金额≈0），是**已结清但残留**
   涉及表: mx.yj_test_table_250225
   过滤: biz_id in 两笔来源
============================================================================= */
SELECT
  biz_id,
  app_date,
  if_issue,
  round(contract_amount, 1)               AS contract_amount,
  round(temp_grant_amount / 1000.0, 1)   AS temp_used,     -- 该笔使用的临额
  round(t0_overdue_amount_1, 1)          AS t0_od,         -- 首逾标签
  round(t3_overdue_amount_1, 1)          AS t3_od,         -- 次逾标签
  round(t0_should_amt_1, 1)              AS t0_shd_amt
FROM mx.yj_test_table_250225
WHERE biz_id IN ('1620000395926822', '1620000396309679')
  AND tenant = 'yawey'
ORDER BY biz_id;


/* =========================================================================
   SQL 1-6: TEMP 全事件流 —— 含 used_grant 找 770.4 起点
   探查目标: 追踪该客户全部临额事件，看 used_grant 从哪次开始变成 770.4
   预期结论: 两笔来源的 FREEZE 先发生，之后所有 C010 都带上了 770.4 残留
   涉及表: ods_view_presto.s05_user_creditlimit_change_record
   过滤: mid=1040160040722566, limit_type='TEMP'（**不要漏这个！**）
   额外信息: limit_main_id 可以看同一额度账户的事件归属
============================================================================= */
SELECT
  limit_main_id,
  create_time,
  change_event_type       AS evt,
  change_action,
  round(change_total_grantamount, 1)   AS total_grant,
  round(change_used_grantamount, 1)     AS used_grant,
  expiring_time
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE mid = 1040160040722566
  AND limit_type = 'TEMP'
ORDER BY create_time;


/* =========================================================================
   SQL 1-7: 还款计划对照 —— 验证 fact_capital 是否预填
   探查目标: 有些期的 fact_capital 看起来提前填了，要确认是真还了还是预填
   预期结论: fact_capital = 实际还款（state=1时有效），预填是 false positive
   涉及表: ods_view_presto.s02_loan_repayment
   Presto陷阱: camera_id 是 decimal(38,6)！关联必须 cast！
============================================================================= */
SELECT
  camera_id    AS biz,
  rid,
  indexs,
  state,
  should_time,
  fact_time,
  should_capital,
  fact_capital,
  update_time
FROM ods_view_presto.s02_loan_repayment
WHERE cast(camera_id as bigint) IN (1620000395926822, 1620000396309679)
ORDER BY cast(camera_id as bigint), indexs;


/* =========================================================================
   SQL 1-8: 订单级结清状态（s02_loan表）
   探查目标: 确认两笔来源是否真的结清（从订单表而不是还款表看）
   预期结论: finish_time 非空且早于2026-04，说明3月底前就结清了
   涉及表: ods_view_presto.s02_loan
   注意: 这里 camera_id 是 bigint，与 repayment 表不同！
============================================================================= */
SELECT
  camera_id      AS biz,
  customer_id,
  state,
  finish_time,
  create_time,
  update_time,
  contract_amount,
  issue_amount
FROM ods_view_presto.s02_loan
WHERE camera_id IN (1620000395926822, 1620000396309679);
