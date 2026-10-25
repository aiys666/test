-- ======================================================================
-- 临额「发放起点」漏斗取数 SQL（v11 口径 · 2026-09-01 ~ 2026-10-21）
-- 2026-10-25 | 上游额度口径 = mx.yj_asset_quota_v11（时刻级 5 天 + apply_time 锚点）
--
-- ══════════════════════════════════════════════════════════════════════
-- 【分析框架】发放 → 进件 → 用信 → 放款 → 用额，人数 / 件数 / 金额 三层展开
--
--   L1 发放     ：真的把临额发到用户/订单上（离线=C015 事件；在线=1386 tag=1 且 857 弹窗额>0）
--   L2 进件     ：发放之后该用户的进件（biz）；拆「全周期」与「有效期内」
--   L3 用信     ：进件走到确认用信（apply_time 有值，即额度冻结那一刻）；同样拆全周期/有效期内
--   L4 放款     ：if_issue=1；金额看合同额
--   L5 用临额   ：本笔真正消耗掉的临额（离线 offline_used_this / 在线 online_used_this）
--
--   每一层都出三列：**人数（去重 mid）/ 件数（biz）/ 金额**
--   核心比率：进件率、有效期内进件率、用信率、放款率、**兑现率 = 用额 / 发放额**
--
-- ── 维度 ─────────────────────────────────────────────────────────────
--   ① temp_type        ：offline / online（两条链路独立，**不可相加**，见下方 ⚠️）
--   ② grade_v5_3       ：**发放时刻**的 V5_3 主评级
--                        离线是用户级发放 → 取该 mid 在发放时刻之前最近一次快照
--                        在线是订单级发放 → 同样取发放时刻前最近一次（与订单评级一致）
--                        grade_band：1-2 高 / 3-7 中 / 8-10 低（对齐离线定档口径）
--   ③ strategy_version ：在线取 1523 落库标签（V5_2 / V5_3）；离线无版本概念 → 'NA'
--
-- ── 关键口径（务必先看）──────────────────────────────────────────────
--   ① 离线发放**只用 C015**。C013 是 9 月开发手动补单的异常事件（2,331 笔 / 193 万），
--      不是常规发放，混进来会虚增发放人数与金额 → 本表剔除，§4 有对照断言。
--   ② 有效期用系统权威字段：
--      离线 = expiring_time（= create_time + 120h，实测 27,721 条全部精确 5 天）
--      在线 = apply_time + 72h（节点 1505 参数 3 天；实测 C010 全部精确 72h）
--   ③ 事件归属：一笔进件只能挂到**一个**发放上 → 取「事件时刻之前最近一次发放」
--      事件时刻 = COALESCE(apply_time, app_time)（与 v11 的冻结锚点一致）
--      → 件数不会跨批次重复；「有效期内」再单独用时间比较打标。
--   ④ 离线是「先发后用」：发放时没有订单，靠 mid 的后续进件匹配；
--      在线是「边发边用」：发放挂在订单上，所以它的 L2 进件恒 = 1（订单本身），
--      有意义的漏斗是「发放 → C010 领取 → 放款」。两个 L2 不可直接对比。
--   ⑤ 金额单位：比索。发放额 = 台账 change_total_grantamount / 857 弹窗额；
--      使用额来自 v11（*=used_this），与业绩口径完全一致。
--   ⑥ 离线发放额是**批次级**、使用额是**逐笔累计**：同一批次被多笔复用时会累加，
--      因此「兑现率」= 该批次被用掉 / 该批次发放额，≤100%（§4 有断言）。
--
-- ── 输出 ─────────────────────────────────────────────────────────────
--   §1 明细表 mx.yj_temp_grant_funnel_v11：一行 = 一次发放
--   §2 汇总：temp_type × grade_band（含合计行）
--   §3 汇总：在线 strategy_version × grade_v5_3
--   §4 断言：发放量、金额、归属唯一性、兑现率上界、评级缺失
-- ======================================================================


-- ══════════════════════════════════════════════════════════════════════
-- §1 明细：一行 = 一次发放（离线 = mid×时刻；在线 = biz）
-- ══════════════════════════════════════════════════════════════════════
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
gr AS (
  -- 发放时刻的 V5_3 主评级：取该 mid 在发放时刻之前最近一次快照
  SELECT g.grant_key,
         MAX_BY(v.android_oldcust_maincreditlevel_charge_v5_3, v.createtime) AS grade_v5_3
  FROM g
  JOIN mx.android_oldcust_maincreditlevel_charge_v5_3_table v
    ON v.mid = g.mid
   AND v.createtime <= g.grant_time
   AND v.android_oldcust_maincreditlevel_charge_v5_3 IS NOT NULL
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
  SELECT a.biz_id, a.mid, a.app_time, a.apply_time, a.issue_date, a.if_issue, a.contract_amount,
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
  -- 离线：归属后的进件；使用额只取 v11 的 offline_used_this（真实消耗离线临额的笔）
  SELECT 'offline' AS temp_type, x.grant_key, x.mid, x.biz_id,
         x.app_time, x.apply_time, x.if_issue, x.contract_amount,
         x.grant_time, x.expire_time,
         CASE WHEN x.app_time    >= x.grant_time THEN 1 ELSE 0 END AS is_app_after_grant,
         CASE WHEN x.app_time    BETWEEN x.grant_time AND x.expire_time THEN 1 ELSE 0 END AS is_app_in_win,
         CASE WHEN x.apply_time IS NOT NULL AND x.app_time >= x.grant_time THEN 1 ELSE 0 END AS is_use_after_grant,
         CASE WHEN x.apply_time IS NOT NULL AND x.app_time >= x.grant_time
               AND x.apply_time BETWEEN x.grant_time AND x.expire_time THEN 1 ELSE 0 END          AS is_use_in_win,
         COALESCE(v.offline_used_this, 0)                                                  AS used_amt,
         CASE WHEN COALESCE(v.offline_used_this, 0) > 0.05 THEN 1 ELSE 0 END               AS is_used
  FROM attr_off x
  LEFT JOIN mx.yj_asset_quota_v11 v
    ON v.biz_id = x.biz_id
   AND v.offline_grant_time = x.grant_time   -- 使用额必须与该批次严格对应，避免跨批次累加
  WHERE x.rn = 1

  UNION ALL

  -- 在线：发放挂在订单上，事件恒为该 biz 本身；使用额取 online_used_this
  SELECT 'online', h.grant_key, h.mid, CAST(h.biz_v AS BIGINT),
         f.app_time, f.apply_time, f.if_issue, f.contract_amount,
         h.grant_time, h.expire_time,
         1, 1, 1, 1,
         COALESCE(v.online_used_this, 0),
         CASE WHEN COALESCE(v.online_used_this, 0) > 0.05 THEN 1 ELSE 0 END
  FROM g h
  LEFT JOIN fa f ON CAST(f.biz_id AS VARCHAR) = h.biz_v
  LEFT JOIN mx.yj_asset_quota_v11 v ON v.biz_id = CAST(h.biz_v AS BIGINT)
  WHERE h.temp_type = 'online'
),
agg AS (
  SELECT grant_key,
         COUNT(DISTINCT CASE WHEN is_app_after_grant = 1 THEN biz_id END)                    AS n_app_all,
         COUNT(DISTINCT CASE WHEN is_app_in_win      = 1 THEN biz_id END)                    AS n_app_win,
         COUNT(DISTINCT CASE WHEN is_use_after_grant = 1 THEN biz_id END)                    AS n_use_all,
         COUNT(DISTINCT CASE WHEN is_use_in_win      = 1 THEN biz_id END)                    AS n_use_win,
         COUNT(DISTINCT CASE WHEN is_use_in_win = 1 AND is_used = 1 THEN biz_id END)         AS n_use_win_used,
         COUNT(DISTINCT CASE WHEN if_issue = 1 THEN biz_id END)                              AS n_issue_all,
         COUNT(DISTINCT CASE WHEN if_issue = 1 AND is_use_in_win = 1 THEN biz_id END)         AS n_issue_win,
         SUM(CASE WHEN if_issue = 1 THEN contract_amount ELSE 0 END)                         AS contract_amt,
         SUM(used_amt)                                                                       AS used_amt,
         MAX(CASE WHEN is_used = 1 THEN 1 ELSE 0 END)                                        AS has_used
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
       gr.grade_v5_3,
       CASE WHEN gr.grade_v5_3 IS NULL      THEN 'unknown'
            WHEN gr.grade_v5_3 <= 2          THEN '1_高(1-2)'
            WHEN gr.grade_v5_3 <= 7          THEN '2_中(3-7)'
            ELSE '3_低(8+)' END                        AS grade_band,
       CASE WHEN g.temp_type = 'offline' THEN 'NA'
            ELSE COALESCE(ver.strategy_version, 'unknown') END AS strategy_version,
       COALESCE(a.n_app_all, 0)        AS n_app_all,
       COALESCE(a.n_app_win, 0)        AS n_app_win,
       COALESCE(a.n_use_all, 0)        AS n_use_all,
       COALESCE(a.n_use_win, 0)        AS n_use_win,
       COALESCE(a.n_use_win_used, 0)   AS n_use_win_used,
       COALESCE(a.n_issue_all, 0)      AS n_issue_all,
       COALESCE(a.n_issue_win, 0)      AS n_issue_win,
       COALESCE(a.contract_amt, 0)     AS contract_amt,
       COALESCE(a.used_amt, 0)         AS used_amt,
       COALESCE(a.has_used, 0)         AS has_used
FROM g
LEFT JOIN gr ON gr.grant_key = g.grant_key
LEFT JOIN ver ON g.temp_type = 'online' AND ver.biz_id = CAST(g.biz_v AS BIGINT)
LEFT JOIN agg a ON a.grant_key = g.grant_key;


-- ══════════════════════════════════════════════════════════════════════
-- §2 汇总 1：临额类型 × 评级档（含合计行）—— 人数 / 件数 / 金额
-- ══════════════════════════════════════════════════════════════════════
SELECT COALESCE(temp_type, '0_合计')                                               AS temp_type,
       COALESCE(grade_band, '0_合计')                                              AS grade_band,
       COUNT(1)                                                                    AS grant_times,
       COUNT(DISTINCT mid)                                                         AS grant_mid,
       SUM(grant_amount)                                                           AS grant_amt,
       SUM(CASE WHEN n_app_all > 0     THEN 1 ELSE 0 END)                          AS n_grant_with_app,
       COUNT(DISTINCT CASE WHEN n_app_all > 0     THEN mid END)                    AS mid_app,
       SUM(n_app_all)                                                              AS app_cnt,
       COUNT(DISTINCT CASE WHEN n_app_win > 0     THEN mid END)                    AS mid_app_win,
       SUM(n_app_win)                                                              AS app_cnt_win,
       COUNT(DISTINCT CASE WHEN n_use_all > 0     THEN mid END)                    AS mid_use,
       SUM(n_use_all)                                                              AS use_cnt,
       COUNT(DISTINCT CASE WHEN n_use_win > 0     THEN mid END)                    AS mid_use_win,
       SUM(n_use_win)                                                              AS use_cnt_win,
       COUNT(DISTINCT CASE WHEN n_use_win_used > 0 THEN mid END)                   AS mid_use_win_used,
       SUM(n_use_win_used)                                                         AS use_cnt_win_used,
       COUNT(DISTINCT CASE WHEN n_issue_all > 0   THEN mid END)                    AS mid_issue,
       SUM(n_issue_all)                                                            AS issue_cnt,
       COUNT(DISTINCT CASE WHEN n_issue_win > 0   THEN mid END)                    AS mid_issue_win,
       SUM(n_issue_win)                                                            AS issue_cnt_win,
       SUM(contract_amt)                                                           AS contract_amt,
       SUM(used_amt)                                                               AS temp_used_amt,
       CAST(SUM(used_amt) AS DOUBLE) / NULLIF(SUM(grant_amount), 0)                AS redeem_rate,
       CAST(SUM(n_issue_all) AS DOUBLE) / NULLIF(SUM(n_app_all), 0)                AS issue_rate_by_cnt
FROM mx.yj_temp_grant_funnel_v11
GROUP BY ROLLUP (temp_type, grade_band)
ORDER BY 1, 2;


-- ══════════════════════════════════════════════════════════════════════
-- §3 汇总 2：在线临额 策略版本 × 评级（离线无版本，不参与）
-- ══════════════════════════════════════════════════════════════════════
-- 注：先把 null 评级映射成 'unknown'，再 ROLLUP，避免 null 评级与合计行都显示成 '0_合计'
SELECT COALESCE(strategy_version, '0_合计')                                       AS strategy_version,
       COALESCE(grade_lbl, '0_合计')                                              AS grade_v5_3,
       COUNT(1)                                                                    AS grant_cnt,
       COUNT(DISTINCT mid)                                                         AS grant_mid,
       SUM(grant_amount)                                                           AS grant_amt,
       SUM(n_issue_all)                                                            AS issue_cnt,
       SUM(contract_amt)                                                           AS contract_amt,
       SUM(used_amt)                                                               AS temp_used_amt,
       CAST(SUM(used_amt) AS DOUBLE) / NULLIF(SUM(grant_amount), 0)                AS redeem_rate
FROM (
  SELECT strategy_version,
         COALESCE(CAST(CAST(grade_v5_3 AS INTEGER) AS VARCHAR), 'unknown') AS grade_lbl,
         mid, grant_amount, n_issue_all, contract_amt, used_amt
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
  --    窗口说明：离线 C015 取到 10-21，在线 issue_date 取到 10-21（funnel app_time < 10-22）；
  --    若在线放到 10-22 则为 16,248 笔 / 9,224,900（多 10 笔 / 8,200，属 10-22 当日新发放，本窗口不纳入）
  SUM(CASE WHEN temp_type = 'offline' THEN 1 ELSE 0 END)                          AS a0_off_rows,
  SUM(CASE WHEN temp_type = 'online'  THEN 1 ELSE 0 END)                          AS a0_on_rows,
  -- a1 发放金额合计（离线 32,264,550 / 在线 9,216,700）
  SUM(CASE WHEN temp_type = 'offline' THEN grant_amount ELSE 0 END)                AS a1_off_grant_amt,
  SUM(CASE WHEN temp_type = 'online'  THEN grant_amount ELSE 0 END)                AS a1_on_grant_amt,
  -- a1b 使用金额合计（离线应为 v11 offline_used 的全量 4,225,829.62 附近；
  --     在线 = 3,682,578.75，即领取并真正用掉的部分）
  SUM(CASE WHEN temp_type = 'offline' THEN used_amt ELSE 0 END)                    AS a1b_off_used_amt,
  SUM(CASE WHEN temp_type = 'online'  THEN used_amt ELSE 0 END)                    AS a1b_on_used_amt,
  -- a2 评级缺失（允许有，但要看比例；应在 10% 以内）
  SUM(CASE WHEN grade_v5_3 IS NULL THEN 1 ELSE 0 END)                              AS a2_grade_null,
  -- a3 归属后件数不得超过事件池（离线）
  SUM(CASE WHEN temp_type = 'offline' THEN n_app_all ELSE 0 END)                   AS a3_off_app_cnt,
  -- a4 兑现率上界：任何一次发放的使用额不得超过发放额（离线批次可被复用，
  --    但累计消耗 ≤ 发放额）
  SUM(CASE WHEN used_amt > grant_amount + 0.5 THEN 1 ELSE 0 END)                   AS a4_used_gt_grant,
  -- a5 有效期内子集不得超过全周期
  SUM(CASE WHEN n_app_win > n_app_all THEN 1 ELSE 0 END)                           AS a5_app_win_gt_all,
  SUM(CASE WHEN n_use_win > n_use_all THEN 1 ELSE 0 END)                           AS a5_use_win_gt_all,
  SUM(CASE WHEN n_use_win_used > n_use_win THEN 1 ELSE 0 END)                      AS a5_used_gt_use,
  -- a6 在线发放必须全部有订单（biz_id 非空且能进 funnel）
  SUM(CASE WHEN temp_type = 'online' AND n_app_all = 0 THEN 1 ELSE 0 END)          AS a6_on_no_app,
  -- a7 离线发放必须全部有 mid
  SUM(CASE WHEN temp_type = 'offline' AND mid IS NULL THEN 1 ELSE 0 END)           AS a7_off_mid_null,
  -- a8 C013 剔除对照（仅提示，非本表口径）：不计入
  0                                                                                AS a8_c013_excluded
FROM mx.yj_temp_grant_funnel_v11;
