-- ======================================================================
-- 临额「发放起点」漏斗取数 SQL（v11.1 口径 · 2026-09-01 ~ 2026-10-21）
-- 2026-10-25 | 上游额度口径 = mx.yj_asset_quota_v11（时刻级 5 天 + apply_time 锚点）
--
-- ══════════════════════════════════════════════════════════════════════
-- 【v11.1 相对 v11 的改动】——「发放为起点」口径补齐
--   ① 评级拆成两套，按类型取「发放时刻」真值：
--      离线 = mx.android_oldcust_maincreditlevel_charge_v5_3_table 快照
--             （离线批处理就是读 T0 11 点这张表的 V5_3，与批次定档口径一致）
--      在线 = ods.s21_risk_model_record **本 biz 决策节点**（1500=V5_2 / 1542=V5_3）
--             → 谁进谁的决策矩阵就用谁的评级（V5_2 桶用 V5_2、V5_3 桶用 V5_3）
--      并额外保留 grade_v5_2 / grade_v5_3 两列，便于跨版本反事实与对照
--   ② 每一层都补齐「人数 / 件数 / 金额」三件套，且金额拆「全周期 / 有效期内」：
--      进件(件) → 有效期内进件(件) → 用信(件) → 有效期内用信(件)
--      → 有效期内用信用额(件) → 放款(件/合同额) → 用掉临额(件/金额)
--   ③ 修复 v11 的归属丢数：归属锚点 = COALESCE(apply_time, app_time)（跨天笔必须用
--      apply_time，见 SKILL §1.4 第 5 条），但统计 L2 进件时**不再要求 app_time>=grant_time**，
--      否则「进件早于发放、用信晚于发放」的跨天笔会被归属掉却计入 0（v11 的真实丢数）。
--      改为全部归属即计入进件，另给 app_before_grant 诊断列。
--   ④ 新增 used_win_amt / n_used_win：真正用掉临额且用信落在有效期内的笔与金额，
--      与用户口径「有效期内使用并用信」严格对齐。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【分析框架】发放 → 进件 → 用信 → 放款 → 用额，人数 / 件数 / 金额 三层展开
--
--   L1 发放     ：真的把临额发到用户/订单上（离线=C015 事件；在线=1386 tag=1 且 857 弹窗额>0）
--   L2 进件     ：发放之后该用户/该订单的进件（biz）；拆「全周期」与「有效期内」
--   L3 用信     ：进件走到确认用信（apply_time 有值，即额度冻结那一刻）；拆全周期/有效期内
--   L3+ 用信用额：用信且本笔真的消耗了临额（temp>0）；再拆有效期内
--   L4 放款     ：if_issue=1；金额看合同额
--   L5 用临额   ：本笔真正消耗掉的临额金额（离线 offline_used_this / 在线 online_used_this）
--
--   每一层都出：**人数（去重 mid）/ 件数（biz）/ 金额**
--   核心比率：进件率、有效期内进件率、用信率、有效期内用信率、放款率、
--             **兑现率 = 用额 / 发放额**（金额）、临额用额占合同比
--
-- ── 维度 ─────────────────────────────────────────────────────────────
--   ① temp_type        ：offline / online（两条链路独立，**不可相加**，见下方 ⚠️）
--   ② grade_used       ：**发放时刻**该发放"实际生效"的主评级（离线 V5_3 / 在线按版本取）
--                        grade_band：1_高(1-2) / 2_中(3-7) / 3_低(8+) / unknown
--   ③ strategy_version ：在线取 1523 落库标签（V5_2 / V5_3）；离线无版本概念 → 'NA'
--
-- ── 关键口径（务必先看）──────────────────────────────────────────────
--   ① 离线发放**只用 C015**。C013 是 9 月开发手动补单的异常事件（2,331 笔 / 193 万），
--      不是常规发放，混进来会虚增发放人数与金额 → 本表剔除。
--      连带后果：离线用额只覆盖 C015 批次（≈372.5 万），比 v11 全量 422.6 万少约 50 万
--      （差额=C013 批次消耗 + 批次金额来源差异），引用离线兑现率必须注明「仅 C015 批次」。
--   ② 有效期用系统权威字段：
--      离线 = expiring_time（= create_time + 120h，实测全部精确 5 天）
--      在线 = 发放时刻 + 72h（节点 1505 参数 3 天；实测 C010 全部精确 72h）
--   ③ 事件归属：一笔进件只能挂到**一个**发放上 → 取「事件时刻之前最近一次发放」
--      事件时刻 = COALESCE(apply_time, app_time)（与 v11 的冻结锚点一致）
--      → 件数不会跨批次重复；「有效期内」再单独用时间比较打标。
--      ⚠️ 跨天笔：进件(app_time)可能早于发放、用信(apply_time)晚于发放 → 仍归属本次发放，
--      这类「发放前进件、发放后用信」离线 2,694 笔 / 6.8%（见 n_app_before 诊断列）。
--      n_app_all 计入（确实被这笔发放接住），n_app_after 只计「发放后新进件」。
--   ④ 离线是「先发后用」：发放时没有订单，靠 mid 的后续进件匹配；
--      在线是「边发边用」：发放挂在订单上，所以它的 L2 进件恒 = 1（订单本身），
--      「有效期内进件/用信」也恒 = 1（发放就发生在确认页，天然在有效期内）。
--      两个 L2 不可直接对比，跨类型只能比比率。
--   ⑤ 金额单位：比索。发放额 = 台账 change_total_grantamount / 857 弹窗额；
--      使用额来自 v11（*_used_this），与业绩口径完全一致。
--   ⑥ 离线发放额是**批次级**、使用额是**逐笔累计**：同一批次被多笔复用时会累加，
--      因此「兑现率」= 该批次被用掉 / 该批次发放额，≤100%（§4 有断言）。
--   ⑦ 人数：分档行内按 mid 去重；跨档同人会被各档各计一次，因此**分档人数之和 ≥ 合计人数**
--      （同一 mid 在不同发放时刻可能处于不同等级）。合计行才是真正的不重复人数。
--
-- ── 输出 ─────────────────────────────────────────────────────────────
--   §1 明细表 mx.yj_temp_grant_funnel_v11：一行 = 一次发放
--   §2 汇总：temp_type × grade_band（含合计行）—— 人数/件数/金额 全层展开
--   §3 汇总：在线 strategy_version × grade_used
--   §4 断言：发放量、金额、归属唯一性、子集单调、兑现率上界、评级缺失
-- ======================================================================


-- ══════════════════════════════════════════════════════════════════════
-- §1 明细：一行 = 一次发放（离线 = mid×时刻；在线 = biz）
-- ══════════════════════════════════════════════════════════════════════
DROP TABLE IF EXISTS mx.yj_temp_grant_funnel_v11;

CREATE TABLE mx.yj_temp_grant_funnel_v11 AS
WITH og AS (
  -- L1 离线发放：C015 真发放
  SELECT CAST(mid AS VARCHAR)                              AS mid_v,
         create_time                                       AS grant_time,
         COALESCE(CAST(expiring_time AS TIMESTAMP),
                  create_time + INTERVAL '5' DAY)           AS expire_time,
         CAST(change_total_grantamount AS DOUBLE)          AS grant_amount
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE limit_type        = 'TEMP'
    AND change_action     = 'CHANGE_LIMIT'
    AND change_event_type = 'C015'
    AND CAST(change_total_grantamount AS DOUBLE) > 0
    AND create_time >= TIMESTAMP '2026-09-01 00:00:00'
    AND create_time <  TIMESTAMP '2026-10-22 00:00:00'
),
ong AS (
  -- L1 在线发放：本笔 1386 tag=1 且 857 弹窗额 > 0
  --   发放时刻 = 用信确认时刻 apply_time；极少数（10 笔）apply_time 为空 → 用 release_time 兜底
  SELECT CAST(biz_id AS VARCHAR)                            AS biz_v,
         mid,
         COALESCE(apply_time, release_time,
                  CAST(issue_date AS TIMESTAMP))            AS grant_time,
         COALESCE(apply_time, release_time,
                  CAST(issue_date AS TIMESTAMP)) + INTERVAL '3' DAY AS expire_time,
         online_grant_amount                               AS grant_amount
  FROM mx.yj_asset_quota_v11
  WHERE online_grant_flag = 1
    AND COALESCE(online_grant_amount, 0) > 0
    AND issue_date >= DATE '2026-09-01'
    AND issue_date <= DATE '2026-10-21'
),
g AS (
  -- 统一发放事实
  SELECT 'offline' AS temp_type,
         CONCAT('O|', mid_v, '|', CAST(grant_time AS VARCHAR)) AS grant_key,
         CAST(mid_v AS BIGINT) AS mid,
         CAST(NULL AS VARCHAR)  AS biz_v,
         grant_time, expire_time, grant_amount
  FROM og
  UNION ALL
  SELECT 'online', CONCAT('N|', biz_v), mid, biz_v, grant_time, expire_time, grant_amount
  FROM ong
),
gr_off AS (
  -- 离线评级：发放时刻的 V5_3 主评级（T0 11 点快照，与离线批处理定档口径一致）
  SELECT g.grant_key,
         MAX_BY(v.android_oldcust_maincreditlevel_charge_v5_3, v.createtime) AS grade_v5_3
  FROM g
  JOIN mx.android_oldcust_maincreditlevel_charge_v5_3_table v
    ON v.mid = g.mid
   AND v.createtime <= g.grant_time
   AND v.android_oldcust_maincreditlevel_charge_v5_3 IS NOT NULL
  WHERE g.temp_type = 'offline'
  GROUP BY 1
),
gr_on AS (
  -- 在线评级：本 biz 决策节点落库值（1500=V5_2 / 1542=V5_3），与决策矩阵行变量同源
  SELECT CAST(r.biz_id AS BIGINT) AS biz_id,
         MAX(TRY_CAST(NULLIF(regexp_extract(CAST(r.outputdata AS VARCHAR),
             '"android_oldCust_mainCreditLevel_charge_V5_2":(-?[0-9.]+)', 1), '') AS DOUBLE)) AS grade_v5_2,
         MAX(TRY_CAST(NULLIF(regexp_extract(CAST(r.outputdata AS VARCHAR),
             '"android_oldCust_mainCreditLevel_charge_V5_3":(-?[0-9.]+)', 1), '') AS DOUBLE)) AS grade_v5_3
  FROM ods.s21_risk_model_record r
  WHERE r.modelmainid IN (1500, 1542)
    AND r.strategytype = 'CHAMPION'
    AND r.biz_id IS NOT NULL
    AND r.etl_date >= '20260831'                    -- 分区裁剪（业务窗口 09-01 起，放宽 1 天）
    AND r.createtime >= TIMESTAMP '2026-08-31 00:00:00'
  GROUP BY 1
),
ver AS (
  -- 在线策略版本（1523 落库标签）；离线无版本
  SELECT CAST(biz_id AS BIGINT) AS biz_id,
         CASE WHEN MAX(CAST(temp_credit_amount_strategy_test_flag AS VARCHAR)) LIKE '%V5_3%' THEN 'V5_3'
              WHEN MAX(CAST(temp_credit_amount_strategy_test_flag AS VARCHAR)) LIKE '%V5_2%' THEN 'V5_2'
              ELSE 'unknown' END AS strategy_version
  FROM mx.yj_test_table_250225
  WHERE issue_date >= DATE '2026-09-01'
    AND issue_date <= DATE '2026-10-21'
    AND is_reloan = 'old'
  GROUP BY 1
),
fa AS (
  -- 进件事件池（funnel 去重：同一 biz 取最新一行）
  SELECT * FROM (
    SELECT CAST(f.biz_id AS BIGINT) AS biz_id,
           f.mid,
           f.app_time,
           f.apply_time,
           f.release_time,
           f.issue_date,
           CAST(COALESCE(f.if_issue, 0) AS INTEGER) AS if_issue,
           CAST(f.contract_amount AS DOUBLE)        AS contract_amount,
           ROW_NUMBER() OVER (PARTITION BY f.biz_id ORDER BY f.app_time DESC) AS rn
    FROM mx.wxs_application_funnel f
    WHERE f.is_reloan = 'old'
      AND f.app_time >= TIMESTAMP '2026-09-01 00:00:00'
      AND f.app_time <  TIMESTAMP '2026-10-22 00:00:00'
  ) t WHERE rn = 1
),
attr_off AS (
  -- 离线事件归属：每笔进件挂到「事件时刻之前最近一次离线发放」
  --   事件时刻必须用 apply_time（跨天笔 app_time 可能早好几天，见 SKILL §1.4 第 5 条）
  SELECT a.biz_id, a.mid, a.app_time, a.apply_time, a.release_time, a.issue_date,
         a.if_issue, a.contract_amount,
         g.grant_key, g.grant_time, g.expire_time, g.grant_amount,
         ROW_NUMBER() OVER (PARTITION BY a.biz_id ORDER BY g.grant_time DESC) AS rn
  FROM fa a
  JOIN g
    ON g.temp_type = 'offline'
   AND g.mid = a.mid
   AND g.grant_time <= COALESCE(a.apply_time, a.app_time)
),
ev AS (
  -- 统一事件：一行 = 一个 biz 挂到一次发放
  --   离线：归属后的进件；使用额只取 v11 的 offline_used_this（且必须与批次严格对上）
  SELECT 'offline' AS temp_type, x.grant_key, x.mid, x.biz_id,
         x.app_time, x.apply_time, x.if_issue, x.contract_amount,
         1                                                            AS is_app_all,
         CASE WHEN x.app_time >= x.grant_time THEN 1 ELSE 0 END        AS is_app_after,
         CASE WHEN x.app_time BETWEEN x.grant_time AND x.expire_time THEN 1 ELSE 0 END AS is_app_win,
         CASE WHEN x.app_time <  x.grant_time THEN 1 ELSE 0 END       AS app_before_grant,
         CASE WHEN x.apply_time IS NOT NULL THEN 1 ELSE 0 END         AS is_use_all,
         CASE WHEN x.apply_time BETWEEN x.grant_time AND x.expire_time THEN 1 ELSE 0 END AS is_use_win,
         COALESCE(v.offline_used_this, 0)                             AS used_amt,
         CASE WHEN COALESCE(v.offline_used_this, 0) > 0.05 THEN 1 ELSE 0 END AS is_used
  FROM attr_off x
  LEFT JOIN mx.yj_asset_quota_v11 v
    ON v.biz_id = x.biz_id
   AND v.offline_grant_time = x.grant_time   -- 使用额必须与该批次严格对应，避免跨批次累加
  WHERE x.rn = 1

  UNION ALL

  -- 在线：发放挂在订单上，事件恒为该 biz 本身；发放即在确认页，天然在有效期内
  SELECT 'online', h.grant_key, h.mid, CAST(h.biz_v AS BIGINT),
         f.app_time, f.apply_time, COALESCE(f.if_issue, 0), f.contract_amount,
         1, 1, 1, 0, 1, 1,
         COALESCE(v.online_used_this, 0),
         CASE WHEN COALESCE(v.online_used_this, 0) > 0.05 THEN 1 ELSE 0 END
  FROM g h
  LEFT JOIN fa f ON CAST(f.biz_id AS VARCHAR) = h.biz_v
  LEFT JOIN mx.yj_asset_quota_v11 v ON v.biz_id = CAST(h.biz_v AS BIGINT)
  WHERE h.temp_type = 'online'
),
agg AS (
  SELECT grant_key,
         COUNT(DISTINCT biz_id)                                                              AS n_app_all,
         COUNT(DISTINCT CASE WHEN is_app_after = 1 THEN biz_id END)                          AS n_app_after,
         COUNT(DISTINCT CASE WHEN is_app_win = 1 THEN biz_id END)                            AS n_app_win,
         COUNT(DISTINCT CASE WHEN app_before_grant = 1 THEN biz_id END)                      AS n_app_before,
         COUNT(DISTINCT CASE WHEN is_use_all = 1 THEN biz_id END)                            AS n_use_all,
         COUNT(DISTINCT CASE WHEN is_use_win = 1 THEN biz_id END)                            AS n_use_win,
         COUNT(DISTINCT CASE WHEN is_use_win = 1 AND is_used = 1 THEN biz_id END)            AS n_use_win_used,
         -- 严格嵌套版：只在「发放后进件」里数，用于和 n_app_after 形成单调漏斗（离线跨天笔会破嵌套）
         COUNT(DISTINCT CASE WHEN is_app_after = 1 AND is_use_all = 1 THEN biz_id END)        AS n_use_after,
         COUNT(DISTINCT CASE WHEN is_app_after = 1 AND is_use_win = 1 THEN biz_id END)        AS n_use_after_win,
         COUNT(DISTINCT CASE WHEN is_app_after = 1 AND is_use_win = 1 AND is_used = 1 THEN biz_id END)
                                                                                             AS n_use_after_win_used,
         COUNT(DISTINCT CASE WHEN is_used = 1 THEN biz_id END)                               AS n_used_all,
         COUNT(DISTINCT CASE WHEN is_used = 1 AND is_use_win = 1 THEN biz_id END)            AS n_used_win,
         COUNT(DISTINCT CASE WHEN if_issue = 1 THEN biz_id END)                              AS n_issue_all,
         COUNT(DISTINCT CASE WHEN if_issue = 1 AND is_use_win = 1 THEN biz_id END)            AS n_issue_win,
         SUM(CASE WHEN if_issue = 1 THEN contract_amount ELSE 0 END)                          AS contract_amt_all,
         SUM(CASE WHEN if_issue = 1 AND is_use_win = 1 THEN contract_amount ELSE 0 END)        AS contract_amt_win,
         SUM(used_amt)                                                                        AS used_amt_all,
         SUM(CASE WHEN is_use_win = 1 THEN used_amt ELSE 0 END)                                AS used_amt_win,
         MAX(is_used)                                                                         AS has_used
  FROM ev
  GROUP BY 1
)
SELECT g.temp_type,
       g.grant_key,
       g.mid,
       g.biz_v                                              AS biz_id,
       g.grant_time,
       g.expire_time,
       g.grant_amount,
       -- ── 发放时刻评级 ──
       CASE WHEN g.temp_type = 'offline' THEN gr_off.grade_v5_3
            ELSE gr_on.grade_v5_3 END                       AS grade_v5_3,
       CASE WHEN g.temp_type = 'online' THEN gr_on.grade_v5_2
            ELSE CAST(NULL AS DOUBLE) END                   AS grade_v5_2,
       -- 实际生效评级：在线按策略版本选（进谁家矩阵用谁家评级）
       CASE WHEN g.temp_type = 'offline' THEN gr_off.grade_v5_3
            WHEN COALESCE(ver.strategy_version, 'unknown') = 'V5_2' THEN gr_on.grade_v5_2
            WHEN COALESCE(ver.strategy_version, 'unknown') = 'V5_3' THEN gr_on.grade_v5_3
            ELSE COALESCE(gr_on.grade_v5_3, gr_on.grade_v5_2) END AS grade_used,
       CASE WHEN (CASE WHEN g.temp_type = 'offline' THEN gr_off.grade_v5_3
                       WHEN COALESCE(ver.strategy_version, 'unknown') = 'V5_2' THEN gr_on.grade_v5_2
                       ELSE COALESCE(gr_on.grade_v5_3, gr_on.grade_v5_2) END) IS NULL THEN 'unknown'
            WHEN (CASE WHEN g.temp_type = 'offline' THEN gr_off.grade_v5_3
                       WHEN COALESCE(ver.strategy_version, 'unknown') = 'V5_2' THEN gr_on.grade_v5_2
                       ELSE COALESCE(gr_on.grade_v5_3, gr_on.grade_v5_2) END) <= 2            THEN '1_高(1-2)'
            WHEN (CASE WHEN g.temp_type = 'offline' THEN gr_off.grade_v5_3
                       WHEN COALESCE(ver.strategy_version, 'unknown') = 'V5_2' THEN gr_on.grade_v5_2
                       ELSE COALESCE(gr_on.grade_v5_3, gr_on.grade_v5_2) END) <= 7            THEN '2_中(3-7)'
            ELSE '3_低(8+)' END                              AS grade_band,
       CASE WHEN g.temp_type = 'offline' THEN 'NA'
            ELSE COALESCE(ver.strategy_version, 'unknown') END AS strategy_version,
       -- ── 漏斗各层：件数 ──
       COALESCE(a.n_app_all, 0)        AS n_app_all,
       COALESCE(a.n_app_after, 0)      AS n_app_after,
       COALESCE(a.n_app_win, 0)        AS n_app_win,
       COALESCE(a.n_app_before, 0)     AS n_app_before,
       COALESCE(a.n_use_all, 0)        AS n_use_all,
       COALESCE(a.n_use_win, 0)        AS n_use_win,
       COALESCE(a.n_use_win_used, 0)   AS n_use_win_used,
       COALESCE(a.n_use_after, 0)      AS n_use_after,
       COALESCE(a.n_use_after_win, 0)  AS n_use_after_win,
       COALESCE(a.n_use_after_win_used, 0) AS n_use_after_win_used,
       COALESCE(a.n_used_all, 0)       AS n_used_all,
       COALESCE(a.n_used_win, 0)       AS n_used_win,
       COALESCE(a.n_issue_all, 0)      AS n_issue_all,
       COALESCE(a.n_issue_win, 0)      AS n_issue_win,
       -- ── 漏斗各层：金额 ──
       COALESCE(a.contract_amt_all, 0) AS contract_amt_all,
       COALESCE(a.contract_amt_win, 0) AS contract_amt_win,
       COALESCE(a.used_amt_all, 0)     AS used_amt_all,
       COALESCE(a.used_amt_win, 0)     AS used_amt_win,
       COALESCE(a.has_used, 0)         AS has_used
FROM g
LEFT JOIN gr_off ON gr_off.grant_key = g.grant_key
LEFT JOIN gr_on  ON g.temp_type = 'online' AND gr_on.biz_id = CAST(g.biz_v AS BIGINT)
LEFT JOIN ver    ON g.temp_type = 'online' AND ver.biz_id = CAST(g.biz_v AS BIGINT)
LEFT JOIN agg a  ON a.grant_key = g.grant_key;


-- ══════════════════════════════════════════════════════════════════════
-- §2 汇总 1：临额类型 × 评级档（含合计行）—— 人数 / 件数 / 金额
--   人数 = count(distinct mid)（分档行会跨档重复，合计行才是真人数）
--   件数 = count(distinct biz)
-- ══════════════════════════════════════════════════════════════════════
SELECT COALESCE(temp_type, '0_合计')                                               AS temp_type,
       COALESCE(grade_band, '0_合计')                                              AS grade_band,
       -- L1 发放
       COUNT(1)                                                                    AS grant_times,
       COUNT(DISTINCT mid)                                                         AS grant_mid,
       SUM(grant_amount)                                                           AS grant_amt,
       -- L2 进件
       COUNT(DISTINCT CASE WHEN n_app_all > 0 THEN mid END)                        AS mid_app,
       SUM(n_app_all)                                                              AS app_cnt,
       COUNT(DISTINCT CASE WHEN n_app_after > 0 THEN mid END)                      AS mid_app_after,
       SUM(n_app_after)                                                            AS app_cnt_after,
       COUNT(DISTINCT CASE WHEN n_app_win > 0 THEN mid END)                        AS mid_app_win,
       SUM(n_app_win)                                                              AS app_cnt_win,
       -- L3 用信
       COUNT(DISTINCT CASE WHEN n_use_all > 0 THEN mid END)                        AS mid_use,
       SUM(n_use_all)                                                              AS use_cnt,
       COUNT(DISTINCT CASE WHEN n_use_win > 0 THEN mid END)                        AS mid_use_win,
       SUM(n_use_win)                                                              AS use_cnt_win,
       -- L3+ 用信且真用额（有效期内）
       COUNT(DISTINCT CASE WHEN n_use_win_used > 0 THEN mid END)                   AS mid_use_win_used,
       SUM(n_use_win_used)                                                         AS use_cnt_win_used,
       COUNT(DISTINCT CASE WHEN n_used_win > 0 THEN mid END)                       AS mid_used_win,
       SUM(n_used_win)                                                             AS used_cnt_win,
       -- L4 放款
       COUNT(DISTINCT CASE WHEN n_issue_all > 0 THEN mid END)                      AS mid_issue,
       SUM(n_issue_all)                                                            AS issue_cnt,
       COUNT(DISTINCT CASE WHEN n_issue_win > 0 THEN mid END)                      AS mid_issue_win,
       SUM(n_issue_win)                                                            AS issue_cnt_win,
       SUM(contract_amt_all)                                                       AS contract_amt_all,
       SUM(contract_amt_win)                                                       AS contract_amt_win,
       -- L5 用额
       SUM(used_amt_all)                                                           AS temp_used_amt_all,
       SUM(used_amt_win)                                                           AS temp_used_amt_win,
       -- 转化率
       CAST(SUM(n_app_win) AS DOUBLE) / NULLIF(SUM(n_app_all), 0)                  AS app_win_share,
       CAST(SUM(n_use_all) AS DOUBLE) / NULLIF(SUM(n_app_all), 0)                  AS use_rate,
       CAST(SUM(n_use_win) AS DOUBLE) / NULLIF(SUM(n_app_all), 0)                  AS use_win_rate,
       CAST(SUM(n_use_win_used) AS DOUBLE) / NULLIF(SUM(n_use_win), 0)             AS used_in_use_rate,
       CAST(SUM(n_issue_all) AS DOUBLE) / NULLIF(SUM(n_app_all), 0)                AS issue_rate,
       CAST(SUM(used_amt_all) AS DOUBLE) / NULLIF(SUM(grant_amount), 0)            AS redeem_rate,
       CAST(SUM(used_amt_win) AS DOUBLE) / NULLIF(SUM(grant_amount), 0)            AS redeem_rate_win,
       CAST(SUM(used_amt_all) AS DOUBLE) / NULLIF(SUM(contract_amt_all), 0)        AS used_share_of_contract
FROM mx.yj_temp_grant_funnel_v11
GROUP BY ROLLUP (temp_type, grade_band)
ORDER BY 1, 2;


-- ══════════════════════════════════════════════════════════════════════
-- §2b 汇总 1b：离线临额「跨天笔」对照（发放前进件、发放后确认）
--   离线发放多在 20-21 点，用户先在白天进件、晚上确认 → apply_time 晚于发放，
--   但 app_time 早于发放。这批离线 2,697 件：用信真实发生，却不在「发放后进件」里。
--   → 严格嵌套漏斗用 *_after 列；业务口径（含跨天）用不带 after 的列。
-- ══════════════════════════════════════════════════════════════════════
SELECT COALESCE(grade_band, '0_合计')                                              AS grade_band,
       COUNT(1)                                                                    AS grant_times,
       COUNT(DISTINCT mid)                                                         AS grant_mid,
       SUM(grant_amount)                                                           AS grant_amt,
       SUM(n_app_all)                                                              AS app_cnt_all,
       COUNT(DISTINCT CASE WHEN n_app_all > 0 THEN mid END)                        AS mid_app_all,
       SUM(n_app_after)                                                            AS app_cnt_after,
       COUNT(DISTINCT CASE WHEN n_app_after > 0 THEN mid END)                      AS mid_app_after,
       SUM(n_app_win)                                                              AS app_cnt_win,
       COUNT(DISTINCT CASE WHEN n_app_win > 0 THEN mid END)                        AS mid_app_win,
       SUM(n_use_after_win)                                                        AS use_after_win_cnt,
       COUNT(DISTINCT CASE WHEN n_use_after_win > 0 THEN mid END)                  AS mid_use_after_win,
       SUM(n_use_win)                                                              AS use_win_cnt,
       COUNT(DISTINCT CASE WHEN n_use_win > 0 THEN mid END)                        AS mid_use_win,
       SUM(n_use_after_win_used)                                                   AS use_after_win_used_cnt,
       COUNT(DISTINCT CASE WHEN n_use_after_win_used > 0 THEN mid END)             AS mid_use_after_win_used,
       SUM(n_use_win_used)                                                         AS use_win_used_cnt,
       SUM(used_amt_all)                                                           AS used_amt
FROM mx.yj_temp_grant_funnel_v11
WHERE temp_type = 'offline'
GROUP BY ROLLUP (grade_band)
ORDER BY 1;


-- ══════════════════════════════════════════════════════════════════════
-- §3 汇总 2：在线临额 策略版本 × 发放时刻评级（离线无版本，不参与）
-- ══════════════════════════════════════════════════════════════════════
-- 注：先把 null 评级映射成 'unknown'，再 ROLLUP，避免 null 评级与合计行都显示成 '0_合计'
SELECT COALESCE(strategy_version, '0_合计')                                       AS strategy_version,
       COALESCE(grade_lbl, '0_合计')                                              AS grade_used,
       COUNT(1)                                                                    AS grant_cnt,
       COUNT(DISTINCT mid)                                                         AS grant_mid,
       SUM(grant_amount)                                                           AS grant_amt,
       COUNT(DISTINCT CASE WHEN n_app_all > 0 THEN mid END)                        AS mid_app,
       SUM(n_app_all)                                                              AS app_cnt,
       COUNT(DISTINCT CASE WHEN n_use_all > 0 THEN mid END)                        AS mid_use,
       SUM(n_use_all)                                                              AS use_cnt,
       SUM(n_use_win_used)                                                         AS use_cnt_win_used,
       COUNT(DISTINCT CASE WHEN n_issue_all > 0 THEN mid END)                      AS mid_issue,
       SUM(n_issue_all)                                                            AS issue_cnt,
       SUM(contract_amt_all)                                                       AS contract_amt,
       SUM(used_amt_all)                                                           AS temp_used_amt,
       CAST(SUM(used_amt_all) AS DOUBLE) / NULLIF(SUM(grant_amount), 0)            AS redeem_rate
FROM (
  SELECT strategy_version,
         COALESCE(CAST(CAST(grade_used AS INTEGER) AS VARCHAR), 'unknown') AS grade_lbl,
         mid, grant_amount, n_app_all, n_use_all, n_use_win_used,
         n_issue_all, contract_amt_all, used_amt_all
  FROM mx.yj_temp_grant_funnel_v11
  WHERE temp_type = 'online'
) t
GROUP BY ROLLUP (strategy_version, grade_lbl)
ORDER BY 1, 2;


-- ══════════════════════════════════════════════════════════════════════
-- §4 断言
-- ══════════════════════════════════════════════════════════════════════
SELECT
  -- a0 明细行数 = 发放事件数（离线 24,454 / 在线 16,238）
  SUM(CASE WHEN temp_type = 'offline' THEN 1 ELSE 0 END)                          AS a0_off_rows,
  SUM(CASE WHEN temp_type = 'online'  THEN 1 ELSE 0 END)                          AS a0_on_rows,
  -- a1 发放金额合计（离线 32,264,550 / 在线 9,216,700）
  SUM(CASE WHEN temp_type = 'offline' THEN grant_amount ELSE 0 END)                AS a1_off_grant_amt,
  SUM(CASE WHEN temp_type = 'online'  THEN grant_amount ELSE 0 END)                AS a1_on_grant_amt,
  -- a1b 使用金额合计（离线应≈3,725,450.71 = 仅 C015 批次；在线 = 3,682,578.75）
  SUM(CASE WHEN temp_type = 'offline' THEN used_amt_all ELSE 0 END)                AS a1b_off_used_amt,
  SUM(CASE WHEN temp_type = 'online'  THEN used_amt_all ELSE 0 END)                AS a1b_on_used_amt,
  -- a2 评级缺失（离线应 0；在线应≈0.6%，仅少数节点未落）
  SUM(CASE WHEN grade_used IS NULL THEN 1 ELSE 0 END)                              AS a2_grade_null,
  SUM(CASE WHEN temp_type = 'online' AND grade_v5_2 IS NULL AND grade_v5_3 IS NULL THEN 1 ELSE 0 END)
                                                                                   AS a2_on_grade_null,
  -- a3 归属件数（离线 37,047 附近）
  SUM(CASE WHEN temp_type = 'offline' THEN n_app_all ELSE 0 END)                   AS a3_off_app_cnt,
  -- a3b 归属锚点诊断：进件早于发放但用信晚于发放的跨天笔（v11 丢的那部分，离线 2,694 笔 / 6.8%）
  SUM(n_app_before)                                                                AS a3b_app_before_grant,
  -- a4 批次复用诊断：一次发放被多笔复用且叠加了账户旧未过期余额时，累计用额可略超该批次名义额
  --    实测量级：122 笔 / 4.99 万（占离线用额 1.3%），属已知的「旧额度叠加/凑档」，非错误
  SUM(CASE WHEN used_amt_all > grant_amount + 0.5 THEN 1 ELSE 0 END)               AS a4_used_gt_grant,
  -- a5 子集单调（必须全 0）
  SUM(CASE WHEN n_app_win > n_app_all THEN 1 ELSE 0 END)                           AS a5_app_win_gt_all,
  SUM(CASE WHEN n_use_win > n_use_all THEN 1 ELSE 0 END)                           AS a5_use_win_gt_all,
  SUM(CASE WHEN n_use_win_used > n_use_win THEN 1 ELSE 0 END)                      AS a5_used_gt_use,
  SUM(CASE WHEN n_used_win > n_used_all THEN 1 ELSE 0 END)                         AS a5_usedwin_gt_used,
  SUM(CASE WHEN n_issue_win > n_issue_all THEN 1 ELSE 0 END)                       AS a5_issue_win_gt_all,
  SUM(CASE WHEN used_amt_win > used_amt_all + 0.5 THEN 1 ELSE 0 END)               AS a5_usedamt_win_gt_all,
  SUM(CASE WHEN contract_amt_win > contract_amt_all + 0.5 THEN 1 ELSE 0 END)       AS a5_contract_win_gt_all,
  -- a6 在线发放必须全部有订单（biz_id 非空）
  SUM(CASE WHEN temp_type = 'online' AND biz_id IS NULL THEN 1 ELSE 0 END)         AS a6_on_no_biz,
  -- a7 离线发放必须全部有 mid
  SUM(CASE WHEN temp_type = 'offline' AND mid IS NULL THEN 1 ELSE 0 END)           AS a7_off_mid_null,
  -- a8 在线评级两套差异（仅诊断，非错误）
  SUM(CASE WHEN temp_type = 'online' AND grade_v5_2 <> grade_v5_3 THEN 1 ELSE 0 END)
                                                                                   AS a8_on_grade_diff
FROM mx.yj_temp_grant_funnel_v11;
