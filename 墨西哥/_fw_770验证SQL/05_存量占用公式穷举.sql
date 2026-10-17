-- =========================================================================
-- 05_存量占用公式穷举.sql
-- 核心问题: "临额冻结了，后期解冻了，还剩多少没释放？"
-- 候选公式: ① frz - cap_last   ② cap_tot - cap_last   ③ cap_nonlast
--           ④ frz - cap_paid  ⑤ frz全释放  ⑥ 舍入误差
-- 关键发现: 残留 ≈ 非末期本金（所有候选公式本质一个东西）
--           无单一闭式（各笔实际解冻期数 N 不一致）
--
-- 公共BASE CTE: 台账窗口 2026-07-01 ~ 2026-10-15
-- =========================================================================

/* =========================================================================
   ⚠️ 公共CTE（所有SQL 5-x共用）—— 直接内嵌到每条SQL里避免窗口不一致
   关键: ① 台账窗口放宽到 10-15 避免截断
         ② "已结清"判定用 max(case when state<>1 then 1 else 0 end)=0
            （比min更直观，不容易搞反）
         ③ Presto陷阱: camera_id 是 decimal！关联必须 cast！
============================================================================= */


/* =========================================================================
   SQL 5-1: 残留 biz 全分类（按真实结清状态）
   探查目标: 有残留的biz里，多少是"真已结清但没解冻"vs"真还在欠款"？
   预期结论: 多数残留来自"还在欠款"（这部分是正常占用）
            已结清仍残留的是bug（≈29笔稳态）
============================================================================= */
WITH led AS (
  SELECT
    biz_id  AS biz,
    SUM(CASE WHEN change_action = 'FREEZE_LIMIT'   THEN risk_credit_limit ELSE 0 END) AS frz,
    SUM(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN risk_credit_limit ELSE 0 END) AS unfr,
    MIN(create_time) AS first_t,
    MAX(create_time) AS last_t
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
    fact_capital,
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
    SUM(CASE WHEN indexs = mx THEN should_capital ELSE 0 END) AS cap_last,
    SUM(CASE WHEN indexs <  mx THEN should_capital ELSE 0 END) AS cap_nonlast,
    MAX(fact_time)                                    AS last_pay_t,
    MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END)       AS any_unpaid
  FROM (SELECT *, MAX(indexs) OVER (PARTITION BY biz) AS mx FROM rp0) t
  GROUP BY biz
),
j AS (
  SELECT
    l.biz, l.frz, l.unfr,
    l.frz - l.unfr   AS resid,
    l.first_t, l.last_t,
    rp.cap_tot, rp.nper, rp.cap_last, rp.cap_nonlast,
    rp.last_pay_t, rp.any_unpaid
  FROM led l
  JOIN rp ON l.biz = rp.biz
)
SELECT
  CASE
    WHEN any_unpaid = 0 THEN 'A 已全部结清'
    ELSE                    'B 未结清(正常占用)'
  END                                                       AS bucket,
  COUNT(*)                                                  AS biz_cnt,
  round(SUM(resid), 1)                                      AS resid_amt,
  round(SUM(cap_tot), 1)                                    AS cap_tot_amt,
  MAX(last_pay_t)                                           AS max_lastpay
FROM j
WHERE resid > 0.01
GROUP BY 1
ORDER BY 1;


/* =========================================================================
   SQL 5-2: 已结清异常集 —— 7个候选公式命中数
   探查目标: 已结清但还有残留的笔，残留额符合什么公式？
   候选公式:
     f_frz_minus_last     = 冻结额 - 末期本金
     f_max0               = max(0, 冻结额-末期本金)
     f_tot_minus_last     = 合同本金 - 末期本金 = 非末期本金
     f_nonlast            = 直接取非末期本金
     f_frz_minus_paid     = 冻结额 - 已还本金
     f_unreleased         = 冻结额全没释放
   预期结论: frz-cap_last ≈ cap_tot-cap_last ≈ cap_nonlast（本质一个公式）
             命中率因各笔实际解冻期数 N 而异，无固定单一公式
   ⚠️ 旧脚本用 min(any_unpaid)，这里修正为 max 更保险
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
    fact_capital,
    state
  FROM ods_view_presto.s02_loan_repayment
  WHERE cast(camera_id as bigint) IN (SELECT biz FROM led)
),
rp AS (
  SELECT
    biz,
    SUM(should_capital)                              AS cap_tot,
    SUM(CASE WHEN state = 1 THEN fact_capital ELSE 0 END) AS cap_paid,
    MAX(indexs)                                       AS nper,
    SUM(CASE WHEN indexs = mx THEN should_capital ELSE 0 END) AS cap_last,
    SUM(CASE WHEN indexs <  mx THEN should_capital ELSE 0 END) AS cap_nonlast,
    MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END)       AS any_unpaid
  FROM (SELECT *, MAX(indexs) OVER (PARTITION BY biz) AS mx FROM rp0) t
  GROUP BY biz
),
j AS (
  SELECT
    l.biz, l.frz, l.unfr,
    l.frz - l.unfr   AS resid,
    rp.cap_tot, rp.cap_paid, rp.nper,
    rp.cap_last, rp.cap_nonlast, rp.any_unpaid
  FROM led l
  JOIN rp ON l.biz = rp.biz
)
SELECT
  COUNT(*)   AS settled_resid_biz,
  round(SUM(resid), 1)                                     AS resid_amt,
  -- 候选公式命中（|resid - 公式值| < 0.05 即命中）
  SUM(CASE WHEN ABS(resid - (frz - cap_last)) < 0.05 THEN 1 ELSE 0 END)   AS f_frz_minus_last,
  SUM(CASE WHEN ABS(resid - GREATEST(0, frz - cap_last)) < 0.05 THEN 1 ELSE 0 END) AS f_max0,
  SUM(CASE WHEN ABS(resid - (cap_tot - cap_last)) < 0.05 THEN 1 ELSE 0 END) AS f_tot_minus_last,
  SUM(CASE WHEN ABS(resid - cap_nonlast) < 0.05 THEN 1 ELSE 0 END)        AS f_nonlast,
  SUM(CASE WHEN ABS(resid - (frz - cap_paid)) < 0.05 THEN 1 ELSE 0 END)   AS f_frz_minus_paid,
  SUM(CASE WHEN ABS(resid - frz) < 0.05 THEN 1 ELSE 0 END)                AS f_unreleased,
  SUM(CASE WHEN nper = 2 THEN 1 ELSE 0 END)                                AS nper2
FROM j
WHERE any_unpaid = 0
  AND resid > 0.01;


/* =========================================================================
   SQL 5-3: 已结清异常集明细 Top30
   探查目标: 具象看已结清却残留的笔 —— 金额、期数、挂账天数
   预期结论: 两期贷为主，残留≈非末期本金，挂账>30天
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
    fact_capital,
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
    SUM(CASE WHEN indexs = mx THEN should_capital ELSE 0 END) AS cap_last,
    MAX(fact_time)                                    AS last_pay_t,
    MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END)       AS any_unpaid
  FROM (SELECT *, MAX(indexs) OVER (PARTITION BY biz) AS mx FROM rp0) t
  GROUP BY biz
),
j AS (
  SELECT
    l.biz, l.frz, l.unfr,
    l.frz - l.unfr   AS resid,
    rp.cap_tot, rp.cap_last, rp.nper,
    rp.last_pay_t, rp.any_unpaid
  FROM led l
  JOIN rp ON l.biz = rp.biz
)
SELECT
  biz,
  round(frz, 1)       AS temp_freeze,
  round(unfr, 1)      AS temp_unfrz,
  round(resid, 1)     AS residue,
  round(cap_tot, 1)   AS cap_tot,
  round(cap_last, 1)  AS cap_last,
  nper,
  last_pay_t,
  date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00')   AS age_days
FROM j
WHERE any_unpaid = 0
  AND resid > 0.01
ORDER BY resid DESC
LIMIT 30;


/* =========================================================================
   SQL 5-4: 已结清残留挂账账龄分布
   探查目标: 残留挂了多久？是近期刚结清的还是很久以前的？
   预期结论: 多数挂账>30天（是2-3月缺陷的历史残留，不是近期新增）
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
    MAX(fact_time)                                    AS last_pay_t,
    MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END)       AS any_unpaid
  FROM rp0
  GROUP BY biz
),
j AS (
  SELECT
    l.biz, l.frz, l.unfr,
    l.frz - l.unfr   AS resid,
    rp.last_pay_t, rp.any_unpaid
  FROM led l
  JOIN rp ON l.biz = rp.biz
)
SELECT
  CASE
    WHEN date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') > 180 THEN '>180天'
    WHEN date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') > 90  THEN '91-180天'
    WHEN date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') > 30  THEN '31-90天'
    ELSE                                                                       '<=30天'
  END                                                 AS age_bucket,
  COUNT(*)                                            AS biz_cnt,
  round(SUM(resid), 1)                                AS resid_amt
FROM j
WHERE any_unpaid = 0
  AND resid > 0.01
GROUP BY 1
ORDER BY 2 DESC;


/* =========================================================================
   SQL 5-5: 稳态异常集（排除当日解冻延迟噪声，账龄≥7天）
   探查目标: 用"账龄≥7天"过滤当日解冻延迟的假阳性，留下真正的bug残留
   预期结论: 异常集从≈1200笔骤降到≈29笔（其中多数是舍入误差）
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
    SUM(CASE WHEN indexs = mx THEN should_capital ELSE 0 END) AS cap_last,
    SUM(CASE WHEN indexs <  mx THEN should_capital ELSE 0 END) AS cap_nonlast,
    MAX(fact_time)                                    AS last_pay_t,
    MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END)       AS any_unpaid
  FROM (SELECT *, MAX(indexs) OVER (PARTITION BY biz) AS mx FROM rp0) t
  GROUP BY biz
),
j AS (
  SELECT
    l.biz, l.frz, l.unfr,
    l.frz - l.unfr   AS resid,
    rp.cap_tot, rp.nper,
    rp.cap_last, rp.cap_nonlast,
    rp.last_pay_t, rp.any_unpaid
  FROM led l
  JOIN rp ON l.biz = rp.biz
)
SELECT
  COUNT(*)                                            AS biz_cnt,
  round(SUM(resid), 1)                                AS resid_amt,
  -- 残留公式命中
  SUM(CASE WHEN ABS(resid - (frz - cap_last)) < 0.05 THEN 1 ELSE 0 END)    AS f_frz_minus_last,
  SUM(CASE WHEN ABS(resid - GREATEST(0, frz - cap_last)) < 0.05 THEN 1 ELSE 0 END) AS f_max0,
  SUM(CASE WHEN ABS(resid - (cap_tot - cap_last)) < 0.05 THEN 1 ELSE 0 END) AS f_tot_minus_last,
  SUM(CASE WHEN ABS(resid - cap_nonlast) < 0.05 THEN 1 ELSE 0 END)         AS f_nonlast,
  SUM(CASE WHEN ABS(resid - frz) < 0.05 THEN 1 ELSE 0 END)                 AS f_unreleased,
  SUM(CASE WHEN resid > frz + 0.05 THEN 1 ELSE 0 END)                       AS f_bigger_than_frz  -- 异常: 残留>冻结
FROM j
WHERE any_unpaid = 0
  AND resid > 0.01
  AND date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') >= 7;


/* =========================================================================
   SQL 5-6: 稳态异常集明细 Top20
   探查目标: 具象看bug残留的笔 —— 金额、期数、挂账天数
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
    SUM(CASE WHEN indexs = mx THEN should_capital ELSE 0 END) AS cap_last,
    SUM(CASE WHEN indexs <  mx THEN should_capital ELSE 0 END) AS cap_nonlast,
    MAX(fact_time)                                    AS last_pay_t,
    MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END)       AS any_unpaid
  FROM (SELECT *, MAX(indexs) OVER (PARTITION BY biz) AS mx FROM rp0) t
  GROUP BY biz
),
j AS (
  SELECT
    l.biz, l.frz, l.unfr,
    l.frz - l.unfr   AS resid,
    rp.cap_tot, rp.nper,
    rp.cap_last, rp.cap_nonlast,
    rp.last_pay_t, rp.any_unpaid
  FROM led l
  JOIN rp ON l.biz = rp.biz
)
SELECT
  biz,
  round(frz, 1)       AS temp_freeze,
  round(unfr, 1)      AS temp_unfrz,
  round(resid, 1)     AS residue,
  round(cap_tot, 1)   AS cap_tot,
  round(cap_last, 1)  AS cap_last,
  round(cap_nonlast, 1) AS cap_nonlast,
  nper,
  date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00')   AS age_days
FROM j
WHERE any_unpaid = 0
  AND resid > 0.01
  AND date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') >= 7
ORDER BY resid DESC
LIMIT 20;


/* =========================================================================
   SQL 5-7: ⚠️ C004 vs C008 解冻验证 —— 为什么前期还款没触发释额？
   探查目标: 文档说C004(还款释额)应每次还本金都触发
             但770.4案例中只有末期触发了C004
   方法: 取案例用户两笔老贷的C004/C008事件，对齐还款计划时间
   预期结论: 
     - 如果C004在每期还款后都触发 → 文档实现正确，770.4是其他原因
     - 如果C004只在末期触发 → 2-3月存在bug，只放末期本金
   文档依据: 《墨西哥循环额度》V1.5
     C004 = 还本金时触发(含前期)，锁定额度 -= 本次还本金
     C008 = 用信失败释额，与还款无关
============================================================================= */

-- Part A: 案例用户两笔老贷的还款计划
SELECT
  'repayment'       AS src,
  cast(camera_id as bigint)  AS biz,
  indexs,
  state,
  round(should_capital, 1)  AS should_cap,
  round(fact_capital, 1)    AS fact_cap,
  should_time,
  fact_time
FROM ods_view_presto.s02_loan_repayment
WHERE cast(camera_id as bigint) IN (1620000395926822, 1620000396309679)
ORDER BY cast(camera_id as bigint), indexs;

-- Part B: 案例用户对应的 C004/C008 解冻事件（按时间对齐）
SELECT
  'unfreeze'        AS src,
  mid,
  limit_main_id,
  create_time,
  change_event_type AS evt,           -- C004=还款释额, C008=用信失败释额
  change_action,
  round(change_total_grantamount, 1)  AS unfreeze_amt,  -- 释放的额度金额
  round(change_used_grantamount, 1)    AS used_grant
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE mid = 1040160040722566
  AND change_event_type IN ('C004', 'C008')
  AND create_time >= timestamp'2026-03-01 00:00:00'
  AND create_time <  timestamp'2026-04-01 00:00:00'
ORDER BY create_time;


/* =========================================================================
   SQL 5-8: 全量解冻金额分布 —— C004 vs C008
   探查目标: 全量看C004和C008的释放金额分布，确认两者的语义差异
   预期结论: 
     C004 释放金额 ≈ 各期本金金额（还款释额）
     C008 释放金额 ≈ 用信冻结金额（用信失败回滚）
============================================================================= */
SELECT
  change_event_type      AS evt,
  limit_type,
  COUNT(*)               AS cnt,
  round(AVG(change_total_grantamount), 1)   AS avg_amt,
  round(MIN(change_total_grantamount), 1)   AS min_amt,
  round(MAX(change_total_grantamount), 1)   AS max_amt,
  round(SUM(change_total_grantamount), 1)   AS total_amt
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE create_time >= date'2026-07-01'
  AND change_action = 'UNFREEZE_LIMIT'
  AND change_event_type IN ('C004', 'C008')
GROUP BY 1, 2
ORDER BY 1, 2;
