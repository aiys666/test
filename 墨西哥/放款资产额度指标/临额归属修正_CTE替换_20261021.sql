-- ======================================================================
-- 临额归属与剩余可用额度：口径修正补丁（替换 放款资产额度指标_20260901起.sql 的对应 CTE）
-- 修正日 2026-10-21 | 依据：本日逐笔穿透（见 临额skill数据校验_20261021.sql 的 I/J 块）
--
-- 修正 4 处：
--   ① 窗口上界：issue_date <= DATE '2026-10-20'  →  CURRENT_DATE - INTERVAL '1' DAY
--      理由：yj_test_table_250225 每日 05:42 重跑，当日放款笔必然缺。实测 10/20 缺 434 笔。
--   ② 临额来源归属：废弃「C010 金额匹配 + else 全归离线」的排除法，
--      改为「本笔 TEMP 冻结时刻之前、同 limit_main_id 账户上最后一次发放事件的类型」。
--      理由：排除法实测错判 53 笔 / 23,093 比索；新口径对 13,375 笔 100% 命中、无 no_grant_event。
--   ③ 离线/在线「剩余可用」：废弃「5 天窗口找 C015/C013 的 total − 账户占用」，
--      改为直接取本笔 TEMP C003 行自带的三个字段。
--      ⚠️ 注意：5 天有效期本身是**严格执行**的，不是窗口方向错 ——
--         实测离线额度账龄分布：0天 2,082 笔 / 1天 1,184 / 2天 1,015 / 3天 884 / 4天 699，
--         合计 0~4 天 = 5,864 笔 / 405.8 万 = **99.9%**；账龄 ≥5 天仅 20 笔 / 1.4 万（0.3%）。
--         在线同理，账龄 0 天占 98.3%（有效期 3 天）。
--      真正的问题是**实现 bug**，有三处：
--        (a) 窗口下界用「release_time − 5 天」的时刻级减法，而离线批次固定在 21:00~23:30 跑 →
--            边界批次被随机切掉。实测 biz 1620000475860535：批次 09-30 23:30:10.904，
--            窗口下界 09-30 23:30:43（release_time 10-05 23:30:43 减 5 天），**差 33 秒被切掉** → grant=0。
--            若必须用窗口，下界应取自然日 DATE_ADD('day',-5, CAST(issue_date AS TIMESTAMP))。
--        (b) 窗口只约束 grant、不约束 used_amount → 两列自相矛盾：
--            36 笔出现 offline_grant=0 而 offline_used_amount 高达 7,750~10,500（且本笔并未用临额）。
--        (c) expiring_time 过后额度账户 total 并未清零，极少数笔仍可支用（上述 20 笔），
--            所以 expiring_time 可以用来理解业务规则，但**不能当取数硬边界**。
--      → 直接取 C003 行自带字段可一次性规避 (a)(b)(c)，因为那是账户的真实状态快照。
--   ④ 兜底公式补扣 voucher_limit（原注 5 已要求，代码未实现）。
--
-- ★ 核心认识：本笔 TEMP 的 C003(FREEZE_LIMIT, external_id = biz_id) 这一行自带全部所需信息，
--   不需要去猜发放事件、不需要窗口：
--     change_total_grantamount = 冻结时刻该 TEMP 账户总额度（覆盖式，等于最后一次发放事件落的值）
--     old_used_grantamount     = 冻结前账户占用（= 该用户其他在贷笔占着的临额）
--     change_used_grantamount  = 冻结后账户占用
--   于是：
--     临额账户总额度 = change_total_grantamount
--     其他在贷占用   = old_used_grantamount
--     本笔剩余可用   = change_total_grantamount - old_used_grantamount   ← 业务定义的「剩余可用」
--     本笔实际使用   = change_used_grantamount  - old_used_grantamount
--   实测：本笔实际使用 与 宽表 (offline_used_this + online_used_this) 在 13,375 笔上 100% 相等。
--   业务对照（岳松口径）：给 3000 临额、其他在贷占 2000 → 剩余可用 1000、最终用 1000 ✓
--
-- ⚠️ change_total_grantamount 是「账户新总额度」不是「本次新增额」：
--   实测 mid 1040160056053009 的 C015 序列 total = 3650→1300→2500→2400→1400→1500，
--   每次 old_total 恰等于上次 total。故**绝不可对多次发放事件求 SUM**（会重复放大数倍）。
--   在线(C010)与离线(C013/C015)共用同一个 limit_main_id 账户池，额度互相覆盖、不叠加。
-- ======================================================================


-- ──────────────────────────────────────────────────────────────────────
-- 【替换 1】本笔 TEMP 冻结台账：一张 CTE 同时产出 总额度/其他占用/剩余可用/本笔使用
--   替换原来的 lz_anchor + offm 两个 CTE
-- ──────────────────────────────────────────────────────────────────────
WITH temp_frz AS (
  SELECT CAST(c.external_id AS VARCHAR)                                        AS biz_v,
         MAX(c.create_time)                                                     AS temp_freeze_time,
         MAX_BY(c.limit_main_id, c.create_time)                                 AS temp_limit_main_id,
         MAX_BY(CAST(c.change_total_grantamount AS DOUBLE), c.create_time)      AS temp_acct_total,
         MAX_BY(CAST(COALESCE(c.old_used_grantamount, 0) AS DOUBLE), c.create_time) AS temp_used_before,
         MAX_BY(CAST(c.change_used_grantamount AS DOUBLE), c.create_time)       AS temp_used_after
  FROM ods_view_presto.s05_user_creditlimit_change_record c
  WHERE c.limit_type    = 'TEMP'
    AND c.change_action = 'FREEZE_LIMIT'
    AND c.external_id IS NOT NULL
    AND c.create_time >= TIMESTAMP '2026-08-25 00:00:00'
  GROUP BY 1
),

-- ──────────────────────────────────────────────────────────────────────
-- 【替换 2】来源归属：本笔冻结时刻之前、同账户最后一次发放事件的类型
--   不看 expiring_time（额度不按它失效）；按 limit_main_id 关联（比 mid 更准，账户唯一）
--   回看下界给足 3 个月：离线额度可长期挂账，实测有跨 30 天仍被使用的
-- ──────────────────────────────────────────────────────────────────────
temp_src AS (
  SELECT f.biz_v,
         MAX_BY(g.change_event_type, g.create_time)                   AS last_grant_type,
         MAX_BY(CAST(g.change_total_grantamount AS DOUBLE), g.create_time) AS last_grant_amount,
         MAX(g.create_time)                                           AS last_grant_time
  FROM temp_frz f
  JOIN ods_view_presto.s05_user_creditlimit_change_record g
    ON  g.limit_main_id     = f.temp_limit_main_id
   AND  g.limit_type        = 'TEMP'
   AND  g.change_action     = 'CHANGE_LIMIT'
   AND  g.change_event_type IN ('C010', 'C013', 'C015')
   AND  g.create_time      <= f.temp_freeze_time
   AND  g.create_time      >= TIMESTAMP '2026-06-01 00:00:00'
  WHERE f.temp_used_after - f.temp_used_before > 0.05   -- 只对真用了临额的笔判来源
  GROUP BY 1
)

-- ──────────────────────────────────────────────────────────────────────
-- 【替换 3】主查询中临额相关的 6 列（替换原 offline_* / online_* 八列的算法）
--   注意：离线与在线共用一个额度池，所以「账户总额度/其他占用/剩余可用」是**池级**指标，
--   不再拆成 offline_xxx / online_xxx 两套（原代码拆两套本身就是口径错误的来源）。
--   要分来源看业绩，用 temp_src 判定后对 temp_used_this 分流即可。
-- ──────────────────────────────────────────────────────────────────────
SELECT
  b.biz_id,
  b.mid,
  b.issue_date,
  b.contract_amount,

  -- 临额额度池（池级，不分在线/离线）
  COALESCE(tf.temp_acct_total, 0)                                      AS temp_acct_total,
  COALESCE(tf.temp_used_before, 0)                                     AS temp_occupied_by_others,
  GREATEST(COALESCE(tf.temp_acct_total, 0)
           - COALESCE(tf.temp_used_before, 0), 0)                      AS temp_available,
  GREATEST(COALESCE(tf.temp_used_after, 0)
           - COALESCE(tf.temp_used_before, 0), 0)                      AS temp_used_this,

  -- 来源归属（C010 → 在线；C013/C015 → 离线）
  ts.last_grant_type,
  ts.last_grant_time,
  CASE WHEN ts.last_grant_type = 'C010' THEN 'online'
       WHEN ts.last_grant_type IN ('C013','C015') THEN 'offline'
       WHEN COALESCE(tf.temp_used_after,0) - COALESCE(tf.temp_used_before,0) > 0.05
         THEN 'unknown'      -- ★ 保留 unknown，不再让 else 吃掉（实测当前为 0 笔）
       ELSE 'none' END                                                 AS temp_source,
  DATE_DIFF('day', ts.last_grant_time, tf.temp_freeze_time)            AS grant_age_days,

  -- 分来源业绩（由池级使用额按来源分流，二者互斥）
  CASE WHEN ts.last_grant_type IN ('C013','C015')
       THEN GREATEST(COALESCE(tf.temp_used_after,0) - COALESCE(tf.temp_used_before,0), 0)
       ELSE 0 END                                                      AS offline_used_this,
  CASE WHEN ts.last_grant_type = 'C010'
       THEN GREATEST(COALESCE(tf.temp_used_after,0) - COALESCE(tf.temp_used_before,0), 0)
       ELSE 0 END                                                      AS online_used_this,

  -- 【替换 4】主额支用的兜底补扣 voucher_limit（原注 5 要求、原代码漏实现）
  COALESCE(c003.main_used_this,
           usedm.main_used_this,
           b.risk_credit_limit,
           b.contract_amount
             - COALESCE(tf.temp_used_after,0) + COALESCE(tf.temp_used_before,0)
             - COALESCE(vch.voucher_limit, 0))                         AS main_used_this

FROM base b
LEFT JOIN temp_frz tf ON tf.biz_v = CAST(b.biz_id AS VARCHAR)
LEFT JOIN temp_src ts ON ts.biz_v = CAST(b.biz_id AS VARCHAR)
LEFT JOIN c003        ON c003.biz_id  = b.biz_id
LEFT JOIN usedm       ON usedm.biz_id = b.biz_id
LEFT JOIN vch         ON vch.biz_id   = b.biz_id
;


-- ======================================================================
-- 【替换 5】base CTE 的窗口上界
-- ======================================================================
--  原：  AND y.issue_date <= DATE '2026-10-20'
--  改：  AND y.issue_date <= CURRENT_DATE - INTERVAL '1' DAY
--  并建议建表后跑一次覆盖率对账（<99% 不要用）：
/*
select
  (select count(distinct biz_id) from mx.wxs_application_funnel
    where issue_date >= date '2026-09-01'
      and issue_date <= current_date - interval '1' day
      and if_issue = 1 and is_reloan = 'old')                as funnel_cnt,
  (select count(distinct biz_id) from mx.yj_temp_limit_wide_table_v2) as wide_cnt,
  cast((select count(distinct biz_id) from mx.yj_temp_limit_wide_table_v2) as double)
    / nullif(cast((select count(distinct biz_id) from mx.wxs_application_funnel
        where issue_date >= date '2026-09-01'
          and issue_date <= current_date - interval '1' day
          and if_issue = 1 and is_reloan = 'old') as double),0)        as coverage
*/


-- ======================================================================
-- 【替换 6】删掉文件末尾的 limit 100000
-- ======================================================================
--  网关 adhoc 结果集 10,000 行硬顶，limit 100000 突破不了且**静默截断不报错**。
--  取数走「建宽表 → 对宽表做聚合」两段式；需要逐笔明细时在数据库网页端导出。


-- ======================================================================
-- 校验断言（建表后必跑；注意 NULL 必须单列断言，abs() 判据会把 NULL 静默放过）
-- ======================================================================
-- 断言 1：本笔使用额与 yj temp_grant_amount 一致
-- 断言 2：剩余可用 >= 本笔使用（当前有 21 笔不满足、6 笔剩余可用为负，需单独排查）
-- 断言 3：temp_source 无 'unknown'
-- 断言 4：恒等式 contract = main_used_this + temp_used_this + voucher_limit
/*
select count(1)                                                            as n,
       sum(case when temp_acct_total  is null then 1 else 0 end)            as n_total_null,
       sum(case when temp_used_before is null then 1 else 0 end)            as n_before_null,
       sum(case when temp_available < temp_used_this - 0.05 then 1 else 0 end) as n_avail_lt_use,
       sum(case when temp_acct_total - temp_used_before < -0.05 then 1 else 0 end) as n_avail_neg,
       sum(case when temp_source = 'unknown' then 1 else 0 end)             as n_unknown,
       sum(case when abs(contract_amount - main_used_this - temp_used_this
                         - coalesce(voucher_limit,0)) > 0.05 then 1 else 0 end) as n_identity_break
from mx.yj_temp_limit_wide_table_v2
*/
