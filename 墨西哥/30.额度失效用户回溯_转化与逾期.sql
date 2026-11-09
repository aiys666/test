-- ======================================================================
-- 额度失效用户回溯：切点客群 → 后续 120 天的进件/授信/放款 + 期次逾期
-- 2026-11-03 | 墨西哥复贷 | 为「沉默用户固额批刷」圈客提供数据依据
--
-- 【相对同事原版的简化】原版 7 个 CTE、关 4 张表（s05_creditx_order +
--   s05_creditx_processor_record×2 + s02_loan + 逾期汇总表），本版只用
--   mx.wxs_application_funnel 一张宽表，约 60 行搞定。
--
--   原版的三个问题：
--     ① 链式 JOIN：放款挂在 pr2 上、pr2 挂在 pr 上。只要 processor_record 里
--        那两个节点名没匹配上（节点改名/数据缺失），这笔放款就彻底不计数。
--        funnel 的 if_issue 是直接标志位，无链式依赖。
--     ② 只取首笔申请（apply_rn=1）：客户首次被拒、60 天后再申请并放款的，
--        完全看不见，低估转化。本版取窗口内全部申请。
--     ③ current_date - interval '120' day 写了 7 次，跨零点会不一致。
--        本版提成 ref CTE 只算一次。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【★ 期次逾期口径】源自 墨西哥/1t7_2t0_3t7_4t7_计算逻辑说明.md
--
--   指标名 {期数}t{N} = 第 N 期应还日（should_date）起算、超过 N 天的表现。
--   窗口判定是**严格大于**：date_diff('day', should_date, current_date) > N
--     t0 → 逾期 ≥1 天      t3 → 逾期 ≥4 天      t7 → 逾期 ≥8 天
--
--   ⚠️⚠️ 必须成对使用两个 flag，分母不能拿「全部放款笔」：
--     is_tN_window_{期}   = 是否已进入该窗口  → **分母**
--     is_tN_overdue_{期}  = 是否在该窗口逾期  → **分子**
--     逾期率 = overdue / window
--   没到窗口的笔（放款太新、还没走到第4期）必须排除在分母外，
--   否则新放款会把逾期率稀释，越近期的 cohort 看起来越好。
--   实测分母随窗口推后单调递减：1t0 8,552 → 4t7 7,552，说明成熟度过滤生效。
--
--   ⚠️ funnel 宽表里**两套同名前缀的字段**，别拿错：
--     tN_overdue_amount_{期}（**有**期次后缀）= vintage 窗口口径 ← 本文用这套
--     tN_overdue_amount     （**无**期次后缀）= risk_ttl 截止点口径，含义完全不同
--
--   ⚠️ 4t7 的语义：墨西哥多为 2 期产品，第 3/4 期是用「最后一期」复制补齐的。
--      所以 4t7 实际衡量「最后一期到期后 7 天还在不在逾期」，是**悲观口径**，
--      且是**笔数未结清率**，不等于最终损失率。
-- ══════════════════════════════════════════════════════════════════════
--
-- 【数据源】
--   dws.dws_risk_stgy_apply_mid_tags_his   客群历史切片（按 data_date 分区）
--   mx.wxs_application_funnel              进件→放款全链路 + 期次逾期（475 列）
-- ======================================================================

WITH ref AS (
  -- ★ 切点只算一次，避免跨零点时前后不一致
  SELECT DATE '2026-06-22' AS dt          -- 对齐同事那版的切片日
),

base AS (
  -- 切点那天的「额度失效 + 无在贷 + 无逾期」复贷客群
  SELECT
      CASE WHEN DATE_DIFF('day', a.last_login_date, r.dt) <= 7              THEN '1. 0-7天'
           WHEN DATE_DIFF('day', a.last_login_date, r.dt) BETWEEN 8  AND 15 THEN '2. 8-15天'
           WHEN DATE_DIFF('day', a.last_login_date, r.dt) BETWEEN 16 AND 30 THEN '3. 16-30天'
           WHEN DATE_DIFF('day', a.last_login_date, r.dt) BETWEEN 31 AND 60 THEN '4. 31-60天'
           ELSE '5. 60天以上' END                                            AS login_recency_group,
      CASE WHEN DATE_DIFF('day', a.last_repay_date, r.dt) <= 30             THEN '1. 0-30天'
           WHEN DATE_DIFF('day', a.last_repay_date, r.dt) BETWEEN 31 AND 90 THEN '2. 31-90天'
           WHEN DATE_DIFF('day', a.last_repay_date, r.dt) > 90              THEN '3. 90天以上'
           ELSE '4. 无还款记录' END                                          AS repay_recency_group,
      CAST(CAST(a.curr_credit_level AS INTEGER) AS VARCHAR)                  AS curr_credit_level,
      -- ★★ 版本必须跟着档位一起带：同一列里混着 V4_2(1~11)/V5_1(1~15)/
      --    V5_2(1~16)/V5_3(1~13)，档位数不同，跨版本比档号是错的
      COALESCE(a.curr_credit_level_version, 'NULL')                          AS credit_level_version,
      CAST(a.mid AS VARCHAR)                                                 AS mid,
      r.dt
  FROM dws.dws_risk_stgy_apply_mid_tags_his a
  CROSS JOIN ref r
  WHERE a.data_date = FORMAT_DATETIME(r.dt, 'yyyyMMdd')
    AND a.if_prohibit_apply = 0
    AND a.is_reloan_stgy    = 1
    AND a.curr_main_limit_expire_date <= r.dt            -- ★ 切点时主额度已失效
    AND (a.id_curr_overdue_days <= 0 OR a.id_curr_overdue_days IS NULL)
    AND a.app_group IN ('Balam Plata','Tuna Cash','Mexcredo')
    AND a.onloan_cnt = 0                                 -- 无在贷
    AND a.curr_ovd_cnt_this_app_group      <= 0
    AND a.curr_ovd_cnt_other_app_group_90d <= 0
    AND a.age <= 65
    AND (a.id_30days_max_overdue_days <= 0 OR a.id_30days_max_overdue_days IS NULL)
),

fnl AS (
  -- 切点后 120 天内的全部申请（不限首笔）
  SELECT CAST(f.mid AS VARCHAR) AS mid, f.biz_id,
         f.if_in_sx, f.if_sx_passed, f.if_pass, f.if_issue,
         CAST(f.contract_amount AS DOUBLE) AS contract_amount,
         f.is_t0_window_1, f.is_t0_overdue_1, f.is_t3_window_1, f.is_t3_overdue_1,
         f.is_t0_window_2, f.is_t0_overdue_2, f.is_t3_window_2, f.is_t3_overdue_2,
         f.is_t3_window_4, f.is_t3_overdue_4, f.is_t7_window_4, f.is_t7_overdue_4
  FROM mx.wxs_application_funnel f
  CROSS JOIN ref r
  WHERE f.is_reloan = 'old'
    AND f.app_date BETWEEN r.dt AND DATE_ADD('day', 120, r.dt)
)

SELECT
  b.login_recency_group, b.repay_recency_group,
  b.curr_credit_level, b.credit_level_version,
  COUNT(DISTINCT b.mid)                                                      AS mid_cnt,
  -- ── 漏斗 ──
  COUNT(DISTINCT CASE WHEN f.biz_id IS NOT NULL THEN b.mid END)              AS apply_mid,
  COUNT(DISTINCT f.biz_id)                                                   AS apply_biz,
  COUNT(DISTINCT CASE WHEN f.if_in_sx     = 1 THEN f.biz_id END)             AS in_sx_biz,
  COUNT(DISTINCT CASE WHEN f.if_sx_passed = 1 THEN f.biz_id END)             AS sx_pass_biz,
  COUNT(DISTINCT CASE WHEN f.if_pass      = 1 THEN f.biz_id END)             AS pass_biz,
  COUNT(DISTINCT CASE WHEN f.if_issue     = 1 THEN f.biz_id END)             AS issue_biz,
  COUNT(DISTINCT CASE WHEN f.if_issue     = 1 THEN b.mid END)                AS issue_mid,
  SUM(CASE WHEN f.if_issue = 1 THEN f.contract_amount ELSE 0 END)            AS contract_amount,
  -- ── 期次逾期：分母 window / 分子 overdue，只统计已放款笔 ──
  SUM(CASE WHEN f.if_issue=1 THEN f.is_t0_window_1  ELSE 0 END)              AS w_1t0,
  SUM(CASE WHEN f.if_issue=1 THEN f.is_t0_overdue_1 ELSE 0 END)              AS o_1t0,
  SUM(CASE WHEN f.if_issue=1 THEN f.is_t3_window_1  ELSE 0 END)              AS w_1t3,
  SUM(CASE WHEN f.if_issue=1 THEN f.is_t3_overdue_1 ELSE 0 END)              AS o_1t3,
  SUM(CASE WHEN f.if_issue=1 THEN f.is_t0_window_2  ELSE 0 END)              AS w_2t0,
  SUM(CASE WHEN f.if_issue=1 THEN f.is_t0_overdue_2 ELSE 0 END)              AS o_2t0,
  SUM(CASE WHEN f.if_issue=1 THEN f.is_t3_window_2  ELSE 0 END)              AS w_2t3,
  SUM(CASE WHEN f.if_issue=1 THEN f.is_t3_overdue_2 ELSE 0 END)              AS o_2t3,
  SUM(CASE WHEN f.if_issue=1 THEN f.is_t3_window_4  ELSE 0 END)              AS w_4t3,
  SUM(CASE WHEN f.if_issue=1 THEN f.is_t3_overdue_4 ELSE 0 END)              AS o_4t3,
  SUM(CASE WHEN f.if_issue=1 THEN f.is_t7_window_4  ELSE 0 END)              AS w_4t7,
  SUM(CASE WHEN f.if_issue=1 THEN f.is_t7_overdue_4 ELSE 0 END)              AS o_4t7
FROM base b
LEFT JOIN fnl f ON f.mid = b.mid
GROUP BY 1,2,3,4
ORDER BY 1,2,3,4;


-- ======================================================================
-- 【实测结果 2026-11-03，切点 2026-06-22，观察 120 天】
--
-- 总计对账（同事那版：37,689 人 / 进件率 12.6% / 1T0 39.3%）：
--   切片人数 36,371   进件 4,665 人（12.8%）   进件 16,100 笔
--   进入授信 13,554（/进件 84.2%）  授信通过 9,392（/进件 58.3%）
--   后置通过 8,733   放款 8,552 笔 / 1,085.8 万 / 件均 1,270
--   1t0 36.67%  1t3 28.74%  2t0 45.49%  2t3 38.64%  4t3 44.00%  4t7 42.36%
--   ※ 人数差 3.5%、1T0 差 2.6pt，来自「本版取全部申请 vs 同事只取首笔」
--
-- 候选圈选方案（详见 30.额度失效用户回溯_结论.md）：
--   方案          人数    占比   进件率  放款笔  件均   1t0    4t7   每千人放款笔
--   全量基线     36,371  100%   12.8%  8,552  1,270  36.7%  42.4%     235
--   好评级×登录≤60 1,291   3.5%   33.8%  1,239  1,990  25.7%  39.5%     960
--   好+中×登录≤60  2,767   7.6%   29.3%  2,053  1,733  29.9%  39.2%     742
-- ======================================================================
