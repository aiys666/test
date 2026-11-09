-- ======================================================================
-- 离线临额 对照组 vs 测试组 完整效果分析
-- 2026-11-03 | 墨西哥复贷 | 10-28(周三·有在贷) + 10-29(周四·无在贷) 两批
--
-- 【实验设计】
--   周三 10-27 晚发（batch=10-28 表）：有在贷客，临额测试 80% vs 对照 20%
--   周四 10-28 晚发（batch=10-29 表）：无在贷客，2×2 四组
--     测试组(临额) 470 / 测试组(临额+减息) 368 / 减息组(无临额) 590 / 对照组 266
--
-- 【已知污染】周三对照组里混入了 10-28 实际收到 C015 临额的人
--   → §1.2 用 C015 发放记录剔除（实测剔除 1 人）
--
-- 【口径】
--   窗口：发放日起 d0~d4（5 天）；周三 10-27~10-31、周四 10-28~11-01
--   ⚠️ v11 是 T-1 口径，11-01 的离线标记尚未落全 → 周四 d4 的临额使用率偏低，
--      进件/放款/金额不受影响（走漏斗表）
--   显著性：比例类用两比例 z 检验（SQL 内直接算）；
--           人均放款额的 Welch-t / Mann-Whitney / bootstrap 需在 Python 侧做，
--           SQL 输出每人放款额明细（§6）供外部检验
--   ⚠️ Presto 注意：中文别名必须加双引号；bigint/bigint 是整数除法要 cast double
-- ======================================================================

-- ======================================================================
-- §1 名单与污染剔除
-- ======================================================================

-- §1.1 建 6 组名单临时表
DROP TABLE IF EXISTS mx.tmp_bat_1028_1029_ys;

CREATE TABLE mx.tmp_bat_1028_1029_ys AS
WITH x28 AS (
  SELECT mid, temp_limit_tag FROM mx.darren_temp_limit_base_table_261028_1
  UNION ALL SELECT mid, temp_limit_tag FROM mx.darren_temp_limit_base_table_261028_2
  UNION ALL SELECT mid, temp_limit_tag FROM mx.darren_temp_limit_base_table_261028_3
), x29 AS (
  SELECT mid, temp_limit_tag FROM mx.yuhan_temp_disc_base_table_261029_1
  UNION ALL SELECT mid, temp_limit_tag FROM mx.yuhan_temp_disc_base_table_261029_2
  UNION ALL SELECT mid, temp_limit_tag FROM mx.yuhan_temp_disc_base_table_261029_3
)
SELECT date '2026-10-28' batch, '周三_在贷' bt, '测试组(临额)' grp, cast(mid as varchar) mid
FROM x28 WHERE temp_limit_tag LIKE '%测试组%' AND temp_limit_tag NOT LIKE '%对照%'
UNION ALL SELECT date '2026-10-28', '周三_在贷', '对照组', cast(mid as varchar)
FROM x28 WHERE temp_limit_tag LIKE '%对照组%'
UNION ALL SELECT date '2026-10-29', '周四_无在贷', '测试组(临额)', cast(mid as varchar)
FROM x29 WHERE temp_limit_tag LIKE '%临额测试组%'
UNION ALL SELECT date '2026-10-29', '周四_无在贷', '测试组(临额+减息)', cast(mid as varchar)
FROM x29 WHERE temp_limit_tag LIKE '%临额减息测试组%'
UNION ALL SELECT date '2026-10-29', '周四_无在贷', '减息组(无临额)', cast(mid as varchar)
FROM x29 WHERE temp_limit_tag LIKE '%减息测试组%' AND temp_limit_tag NOT LIKE '%临额%'
UNION ALL SELECT date '2026-10-29', '周四_无在贷', '对照组', cast(mid as varchar)
FROM x29 WHERE temp_limit_tag LIKE '%对照组%';

-- 名单量校验（实测：周三 测试1,702 / 对照431；周四 470 / 368 / 590 / 266）
-- ⚠️ 全表 3,827 行 / distinct mid 3,794：33 个 mid 跨批次重复（两批人群有交叠），见 §1.3
SELECT batch, bt, grp, count(*) mids FROM mx.tmp_bat_1028_1029_ys GROUP BY 1,2,3 ORDER BY 1,3;

-- §1.2 周三对照组污染剔除（10-28 当天收到 C015 临额发放的对照组成员）
--   C015 = 离线临额发放事件，change_total_grantamount>0
--   实测命中 2 人（431 → 429）
SELECT b.mid
FROM mx.tmp_bat_1028_1029_ys b
JOIN (SELECT DISTINCT cast(mid AS varchar) mid
      FROM ods_view_presto.s05_user_creditlimit_change_record
      WHERE limit_type='TEMP' AND change_action='CHANGE_LIMIT' AND change_event_type='C015'
        AND cast(change_total_grantamount AS double) > 0
        AND create_time >= timestamp '2026-10-28 00:00:00'
        AND create_time <  timestamp '2026-10-29 00:00:00') c ON c.mid = b.mid
WHERE b.batch = date '2026-10-28' AND b.grp = '对照组';

-- §1.3 跨批次重叠检查（实测 33 个 mid 同时出现在两批：周三在贷∩周四无在贷人群有交叠）
--   ★ 若"周三测试组 ∩ 周四对照组"有人，则周四对照组被临额污染，解读周四结论时注意
--   实测重叠矩阵（合计 33）：
--     周三对照组∩周四对照组 9 / 周三测试∩周四减息 8 / 周三测试∩周四临额+减息 8 /
--     周三测试∩周四测试(临额) 5 / 周三对照∩周四临额+减息 2 / 周三对照∩周四减息 1
--   → "周三测试组 ∩ 周四对照组" = 0，周四对照组干净
--   → 但周三对照组有 3 人在 10-28 晚拿到临额（2人进临额+减息组、1人进减息组），
--     对周三窗口 d1~d4 有 3/429≈0.7% 的轻微污染，量级可忽略
--   ★ 因此 §3/§4/§5 的 row_number 必须按 (batch, grp, biz_id) 分区去重：
--     同一 mid 的 funnel 行会被 join 复制到两个 batch，若只按 biz_id 分区，
--     两批复制行并列抢 rn=1，结果跨执行随机抖动（实测测试组进件人数 1291 vs 1298）
SELECT a.grp wed_grp, b.grp thu_grp, count(*) overlap_mids
FROM (SELECT grp, mid FROM mx.tmp_bat_1028_1029_ys WHERE batch = date '2026-10-28') a
JOIN (SELECT grp, mid FROM mx.tmp_bat_1028_1029_ys WHERE batch = date '2026-10-29') b
  ON b.mid = a.mid
GROUP BY 1,2 ORDER BY 3 DESC;

-- ======================================================================
-- §2 平衡性校验（分组是否随机）：当前主额度 / 可用总额 / 年龄应无系统差异
--   实测：周三 对照/测试 平均主额 16,035 vs 16,083、年龄 46.6 vs 48.8（测试组略大 2 岁）；
--         周四四组主额 13,516~14,458、年龄 46.9~48.6，整体平衡
-- ======================================================================
WITH src AS (
  SELECT date '2026-10-28' batch, cast(mid AS varchar) mid,
         cast(curr_main_credit_limit AS double) main_limit,
         cast(total_available_limit AS double) avail_limit,
         cast(age AS double) age
  FROM mx.darren_temp_limit_base_table_261028_3
  UNION ALL
  SELECT date '2026-10-29', cast(mid AS varchar),
         cast(curr_main_credit_limit AS double), cast(total_available_limit AS double), cast(age AS double)
  FROM mx.yuhan_temp_disc_base_table_261029_3
)
SELECT b.batch, b.grp, count(*) mids,
       round(avg(s.main_limit), 0) avg_main_limit,
       round(avg(s.avail_limit), 0) avg_avail_limit,
       round(avg(s.age), 1) avg_age
FROM mx.tmp_bat_1028_1029_ys b
LEFT JOIN src s ON s.batch = b.batch AND s.mid = b.mid
GROUP BY 1,2 ORDER BY 1,2;
-- ⚠️ 批次表无 main_credit_limit/temp_credit_limit 字段，实测可用字段：
--    curr_main_credit_limit(当前主额) / curr_temp_credit_limit(当前临额) /
--    total_available_limit(总可用) / temp_limit_issue_amount(本批发放临额)

-- ======================================================================
-- §3 行为明细（漏斗表按 biz_id 去重）
--   ⚠️ row_number 必须按 (batch, grp, biz_id) 分区：33 个 mid 跨两批重复（§1.3），
--      只按 biz_id 分区会让两批复制行抢 rn=1，结果随机抖动
--   发放日映射：batch 10-28 → 发放日 10-27；batch 10-29 → 发放日 10-28
-- ======================================================================
WITH l AS (
  SELECT d.batch, d.bt, d.grp, d.mid, f.biz_id,
         cast(f.app_time AS date) app_date, f.issue_date,
         cast(f.if_issue AS integer) if_issue,
         cast(f.contract_amount AS double) contract_amount,
         row_number() OVER (PARTITION BY d.batch, d.grp, f.biz_id ORDER BY f.app_time DESC) rn
  FROM (SELECT batch, bt, grp, mid FROM mx.tmp_bat_1028_1029_ys
        WHERE NOT (batch = date '2026-10-28' AND grp = '对照组'
                   AND mid IN (SELECT DISTINCT cast(mid AS varchar)
                               FROM ods_view_presto.s05_user_creditlimit_change_record
                               WHERE limit_type='TEMP' AND change_action='CHANGE_LIMIT'
                                 AND change_event_type='C015'
                                 AND cast(change_total_grantamount AS double) > 0
                                 AND create_time >= timestamp '2026-10-28 00:00:00'
                                 AND create_time <  timestamp '2026-10-29 00:00:00'))
       ) d
  JOIN mx.wxs_application_funnel f ON cast(f.mid AS varchar) = d.mid
  WHERE f.app_time >= timestamp '2026-10-26 00:00:00' AND f.app_time < timestamp '2026-11-02 00:00:00'
)
SELECT * FROM l WHERE rn = 1;

-- ======================================================================
-- §4 核心指标（d0~d4，5 天窗口）
--   输出：进件率 / 放款率(人数) / 放款笔数率 / 件均 / 人均放款额 / 临额使用率 / >1万笔数
-- ======================================================================
WITH l AS (
  SELECT d.batch, d.bt, d.grp, d.mid, f.biz_id,
         cast(f.app_time AS date) app_date, f.issue_date,
         cast(f.if_issue AS integer) if_issue,
         cast(f.contract_amount AS double) contract_amount,
         row_number() OVER (PARTITION BY d.batch, d.grp, f.biz_id ORDER BY f.app_time DESC) rn
  FROM (SELECT batch, bt, grp, mid FROM mx.tmp_bat_1028_1029_ys
        WHERE NOT (batch = date '2026-10-28' AND grp = '对照组'
                   AND mid IN (SELECT DISTINCT cast(mid AS varchar)
                               FROM ods_view_presto.s05_user_creditlimit_change_record
                               WHERE limit_type='TEMP' AND change_action='CHANGE_LIMIT'
                                 AND change_event_type='C015'
                                 AND cast(change_total_grantamount AS double) > 0
                                 AND create_time >= timestamp '2026-10-28 00:00:00'
                                 AND create_time <  timestamp '2026-10-29 00:00:00'))
       ) d
  JOIN mx.wxs_application_funnel f ON cast(f.mid AS varchar) = d.mid
  WHERE f.app_time >= timestamp '2026-10-26 00:00:00' AND f.app_time < timestamp '2026-11-02 00:00:00'
),
l2 AS (SELECT * FROM l WHERE rn = 1),
d AS (
  SELECT batch, bt, grp, mid,
         CASE WHEN batch = date '2026-10-28' THEN date '2026-10-27' ELSE date '2026-10-28' END grant_date
  FROM mx.tmp_bat_1028_1029_ys
),
m AS (
  -- ★ 分母同样剔除周三对照组污染，保证与 §5 口径一致
  SELECT batch, bt, grp, count(*) mids FROM mx.tmp_bat_1028_1029_ys
  WHERE NOT (batch = date '2026-10-28' AND grp = '对照组'
             AND mid IN (SELECT DISTINCT cast(mid AS varchar)
                         FROM ods_view_presto.s05_user_creditlimit_change_record
                         WHERE limit_type='TEMP' AND change_action='CHANGE_LIMIT'
                           AND change_event_type='C015'
                           AND cast(change_total_grantamount AS double) > 0
                           AND create_time >= timestamp '2026-10-28 00:00:00'
                           AND create_time <  timestamp '2026-10-29 00:00:00'))
  GROUP BY 1,2,3
),
a AS (
  SELECT l2.batch, l2.grp, count(DISTINCT l2.mid) mids_app, count(*) apps
  FROM l2 JOIN d ON d.batch = l2.batch AND d.grp = l2.grp AND d.mid = l2.mid
  WHERE app_date BETWEEN grant_date AND date_add('day', 4, grant_date)
  GROUP BY 1,2
),
lo AS (
  SELECT l2.batch, l2.grp, count(*) loans, count(DISTINCT l2.mid) mids_loan,
         sum(l2.contract_amount) loan_amt,
         count(*) FILTER (WHERE v.used_source_tag = 'offline') off_n,
         coalesce(sum(v.offline_used_this), 0) off_amt,
         count(*) FILTER (WHERE l2.contract_amount > 10000) gt1w
  FROM l2
  JOIN d ON d.batch = l2.batch AND d.grp = l2.grp AND d.mid = l2.mid
  LEFT JOIN (SELECT biz_id, used_source_tag, offline_used_this FROM mx.yj_asset_quota_v11
             WHERE issue_date >= date '2026-10-26') v
    ON v.biz_id = cast(l2.biz_id AS bigint)   -- ★ funnel 的 biz_id 是 varchar，v11 是 bigint
  WHERE l2.if_issue = 1 AND l2.issue_date BETWEEN d.grant_date AND date_add('day', 4, d.grant_date)
  GROUP BY 1,2
)
SELECT m.batch, m.bt, m.grp, m.mids,
       coalesce(a.mids_app, 0) "进件人数",
       round(coalesce(cast(a.mids_app AS double), 0) / m.mids, 4) "进件率",
       coalesce(lo.mids_loan, 0) "放款人数",
       round(coalesce(cast(lo.mids_loan AS double), 0) / m.mids, 4) "放款率",
       coalesce(lo.loans, 0) "放款笔数",
       round(coalesce(cast(lo.loans AS double), 0) / m.mids, 4) "笔数率",
       coalesce(round(lo.loan_amt, 1), 0) "放款总额",
       coalesce(round(lo.loan_amt / nullif(lo.loans, 0), 1), 0) "件均",
       coalesce(round(lo.loan_amt / m.mids, 1), 0) "人均放款额",
       coalesce(lo.off_n, 0) "临额使用笔数",
       coalesce(round(cast(lo.off_n AS double) / nullif(lo.loans, 0), 4), 0) "临额使用率",
       coalesce(round(lo.off_amt, 1), 0) "临额使用额",
       coalesce(lo.gt1w, 0) "超1万笔数"
FROM m
LEFT JOIN a ON a.batch = m.batch AND a.grp = m.grp
LEFT JOIN lo ON lo.batch = m.batch AND lo.grp = m.grp
ORDER BY m.batch, m.grp;

-- ======================================================================
-- §5 显著性检验（比例类：两比例 z 检验，SQL 直接算）
--   z = (p2-p1) / sqrt(p*(1-p)*(1/n1+1/n2))，p 为合并比例
--   p 值 = 2*(1-Φ(|z|))，|z|>1.96 ↔ p<0.05
--   ★ 名单/窗口/去重逻辑与 §4 完全一致（同一份 l2），保证数字对得上
--   ★ Presto 坑：1.0/429 会按 decimal(2,1) 截断成 0.0 → 必须用 1e0（double 字面量）
--
--   实测结果：
--     周三 对照429 vs 测试1702：进件率 71.56%→76.26% z=2.02（显著）；
--                              放款率 37.53%→40.07% z=0.96（不显著）；
--                              笔数率 49.42%→56.11% z=2.49（显著）
--     周四 减息   z_app=1.38 z_loan=1.53 z_loans=1.49（均不显著）
--     周四 临额   z_app=1.38 z_loan=1.13 z_loans=1.29（均不显著）
--     周四 临额+减息 z_app=0.73 z_loan=0.92 z_loans=1.07（均不显著）
--   → 周三人效显著（笔数率 z=2.49），周四三组与对照均无显著差异（对照仅 266 人，功效不足）
-- ======================================================================
WITH l AS (
  SELECT d.batch, d.grp, d.mid, f.biz_id,
         cast(f.app_time AS date) app_date, f.issue_date,
         cast(f.if_issue AS integer) if_issue,
         row_number() OVER (PARTITION BY d.batch, d.grp, f.biz_id ORDER BY f.app_time DESC) rn
  FROM (SELECT batch, grp, mid FROM mx.tmp_bat_1028_1029_ys
        WHERE NOT (batch = date '2026-10-28' AND grp = '对照组'
                   AND mid IN (SELECT DISTINCT cast(mid AS varchar)
                               FROM ods_view_presto.s05_user_creditlimit_change_record
                               WHERE limit_type='TEMP' AND change_action='CHANGE_LIMIT'
                                 AND change_event_type='C015'
                                 AND cast(change_total_grantamount AS double) > 0
                                 AND create_time >= timestamp '2026-10-28 00:00:00'
                                 AND create_time <  timestamp '2026-10-29 00:00:00'))
       ) d
  JOIN mx.wxs_application_funnel f ON cast(f.mid AS varchar) = d.mid
  WHERE f.app_time >= timestamp '2026-10-26 00:00:00' AND f.app_time < timestamp '2026-11-02 00:00:00'
),
l2 AS (SELECT * FROM l WHERE rn = 1),
d AS (
  SELECT batch, grp, mid,
         CASE WHEN batch = date '2026-10-28' THEN date '2026-10-27' ELSE date '2026-10-28' END grant_date
  FROM mx.tmp_bat_1028_1029_ys
  WHERE NOT (batch = date '2026-10-28' AND grp = '对照组'
             AND mid IN (SELECT DISTINCT cast(mid AS varchar)
                         FROM ods_view_presto.s05_user_creditlimit_change_record
                         WHERE limit_type='TEMP' AND change_action='CHANGE_LIMIT'
                           AND change_event_type='C015'
                           AND cast(change_total_grantamount AS double) > 0
                           AND create_time >= timestamp '2026-10-28 00:00:00'
                           AND create_time <  timestamp '2026-10-29 00:00:00'))
),
per AS (
  -- 每人一行：d0~d4 是否进件、放款笔数
  SELECT d.batch, d.grp, d.mid,
         max(CASE WHEN l2.app_date BETWEEN d.grant_date AND date_add('day', 4, d.grant_date)
                  THEN 1 ELSE 0 END) applied,
         count(CASE WHEN l2.if_issue = 1
                     AND l2.issue_date BETWEEN d.grant_date AND date_add('day', 4, d.grant_date)
                    THEN 1 END) loans
  FROM d LEFT JOIN l2 ON l2.batch = d.batch AND l2.grp = d.grp AND l2.mid = d.mid
  GROUP BY 1,2,3
),
g AS (
  SELECT batch, grp, count(*) n,
         cast(avg(applied) AS double) p_app,
         cast(avg(CASE WHEN loans > 0 THEN 1 ELSE 0 END) AS double) p_loan,
         cast(sum(loans) AS double) / count(*) p_loans
  FROM per
  GROUP BY 1,2
),
c AS (SELECT * FROM g WHERE grp = '对照组'),
t AS (SELECT * FROM g WHERE grp <> '对照组')
SELECT t.batch, c.grp "对照", t.grp "测试",
       c.n n_ctl, t.n n_tst,
       -- 进件率 z
       round(c.p_app, 4) ctl_app, round(t.p_app, 4) tst_p_app,
       round((t.p_app - c.p_app) /
             sqrt(((c.p_app*c.n + t.p_app*t.n)/(c.n+t.n))
                  * (1 - (c.p_app*c.n + t.p_app*t.n)/(c.n+t.n))
                  * (1e0/c.n + 1e0/t.n)), 2) z_app,
       -- 放款率(人数) z
       round(c.p_loan, 4) ctl_p_loan, round(t.p_loan, 4) tst_p_loan,
       round((t.p_loan - c.p_loan) /
             sqrt(((c.p_loan*c.n + t.p_loan*t.n)/(c.n+t.n))
                  * (1 - (c.p_loan*c.n + t.p_loan*t.n)/(c.n+t.n))
                  * (1e0/c.n + 1e0/t.n)), 2) z_loan,
       -- 放款笔数率 z
       round(c.p_loans, 4) ctl_p_loans, round(t.p_loans, 4) tst_p_loans,
       round((t.p_loans - c.p_loans) /
             sqrt(((c.p_loans*c.n + t.p_loans*t.n)/(c.n+t.n))
                  * (1 - (c.p_loans*c.n + t.p_loans*t.n)/(c.n+t.n))
                  * (1e0/c.n + 1e0/t.n)), 2) z_loans
FROM c JOIN t ON t.batch = c.batch
ORDER BY t.batch, t.grp;
-- 判读：|z| > 1.96 → p<0.05 显著；> 2.58 → p<0.01

-- ======================================================================
-- §6 每人放款额明细（供 Python 做 Welch-t / Mann-Whitney / bootstrap）
--   人均放款额 SQL 端只能给均值/方差，精确检验拉到外部做
--   实测（全员口径，未放款记 0）：周三 对照 1,054.6（n=429）vs 测试 1,098.0（n=1,702）
--     Welch-t=0.37 p=0.709 / Mann-Whitney p=0.511 / 5,000 次置换 p=0.707 → 不显著
--   周四 对照 379.9（n=266）vs 减息 253.5（p_t=0.236）/ 临额 295.7（p_t=0.452）/
--        临额+减息 302.9（p_t=0.522）→ 均不显著（对照样本小，功效不足）
-- ======================================================================
WITH d AS (
  SELECT batch, bt, grp, mid,
         CASE WHEN batch = date '2026-10-28' THEN date '2026-10-27' ELSE date '2026-10-28' END grant_date
  FROM mx.tmp_bat_1028_1029_ys
)
SELECT d.batch, d.grp, d.mid,
       coalesce(sum(CASE WHEN f.if_issue = 1
                          AND f.issue_date BETWEEN d.grant_date AND date_add('day', 4, d.grant_date)
                         THEN cast(f.contract_amount AS double) END), 0) amt
FROM d
LEFT JOIN (
  SELECT cast(mid AS varchar) mid, biz_id, issue_date, cast(if_issue AS integer) if_issue,
         contract_amount,
         row_number() OVER (PARTITION BY biz_id ORDER BY app_time DESC) rn
  FROM mx.wxs_application_funnel
  WHERE app_time >= timestamp '2026-10-26 00:00:00' AND app_time < timestamp '2026-11-02 00:00:00'
) f ON f.mid = d.mid AND f.rn = 1
WHERE NOT (d.batch = date '2026-10-28' AND d.grp = '对照组'
           AND d.mid IN (SELECT DISTINCT cast(mid AS varchar)
                         FROM ods_view_presto.s05_user_creditlimit_change_record
                         WHERE limit_type='TEMP' AND change_action='CHANGE_LIMIT'
                           AND change_event_type='C015'
                           AND cast(change_total_grantamount AS double) > 0
                           AND create_time >= timestamp '2026-10-28 00:00:00'
                           AND create_time <  timestamp '2026-10-29 00:00:00'))
GROUP BY 1,2,3;

-- ======================================================================
-- §7 V6_1 分层效果（结论：增量集中在 1-2 档，3-7 档人均略降）
--   实测周三（对照 vs 测试）：
--     1-2 级   109人 进件68.81%/放款31.19%/人均1,350.3 → 376人 80.85%/35.11%/1,580.4（人均+17.0%，进件+12.0pp）
--     3-7 级   267人 75.66%/42.32%/1,088.3 → 1,081人 76.32%/40.43%/999.8（人均−8.1%）
--     8-10 级   46人 52.17%/28.26%/280.5 → 220人 69.09%/47.73%/796.8（人均+184%，样本小）
--     11+ 级     7人 → 25人，样本过小不作结论
--   解读：临额对中低等级（1-2）既提进件又提金额；对 3-7 档只提笔数不提金额（件均被摊薄）
-- ======================================================================
WITH lv61 AS (
  SELECT mid, createtime, android_oldcust_maincreditlevel_charge_v6_1 AS lv
  FROM mx.android_oldcust_maincreditlevel_charge_v6_1_table
  WHERE etl_date >= '20260819' AND android_oldcust_maincreditlevel_charge_v6_1 IS NOT NULL
),
bd AS (
  SELECT batch, grp, mid,
         CASE WHEN batch = date '2026-10-28' THEN timestamp '2026-10-27 00:00:00'
              ELSE timestamp '2026-10-28 00:00:00' END ts
  FROM mx.tmp_bat_1028_1029_ys
),
lvm AS (
  -- ★ max_by 必须先落成 lv 列，不能在外层 CASE 里重复调用
  SELECT bd.batch, bd.grp, bd.mid, max_by(l.lv, l.createtime) lv
  FROM bd LEFT JOIN lv61 l ON cast(l.mid AS varchar) = bd.mid AND l.createtime <= bd.ts
  GROUP BY 1,2,3
),
lvmb AS (
  SELECT batch, grp, mid,
         CASE WHEN lv IN (1,2) THEN 'V6_1_1-2'
              WHEN lv BETWEEN 3 AND 7 THEN 'V6_1_3-7'
              WHEN lv BETWEEN 8 AND 10 THEN 'V6_1_8-10'
              WHEN lv >= 11 THEN 'V6_1_11+' ELSE 'V6_1_未知' END bucket
  FROM lvm
),
d AS (
  SELECT batch, grp, mid,
         CASE WHEN batch = date '2026-10-28' THEN date '2026-10-27' ELSE date '2026-10-28' END grant_date
  FROM mx.tmp_bat_1028_1029_ys
  WHERE NOT (batch = date '2026-10-28' AND grp = '对照组'
             AND mid IN (SELECT DISTINCT cast(mid AS varchar)
                         FROM ods_view_presto.s05_user_creditlimit_change_record
                         WHERE limit_type='TEMP' AND change_action='CHANGE_LIMIT'
                           AND change_event_type='C015'
                           AND cast(change_total_grantamount AS double) > 0
                           AND create_time >= timestamp '2026-10-28 00:00:00'
                           AND create_time <  timestamp '2026-10-29 00:00:00'))
),
f AS (
  SELECT cast(mid AS varchar) mid, biz_id,
         cast(app_time AS date) app_date, issue_date,
         cast(if_issue AS integer) if_issue, cast(contract_amount AS double) contract_amount,
         row_number() OVER (PARTITION BY biz_id ORDER BY app_time DESC) rn
  FROM mx.wxs_application_funnel
  WHERE app_time >= timestamp '2026-10-26 00:00:00' AND app_time < timestamp '2026-11-02 00:00:00'
),
pm AS (
  SELECT d.batch, d.grp, d.mid,
         max(CASE WHEN f.app_date BETWEEN d.grant_date AND date_add('day', 4, d.grant_date)
                  THEN 1 ELSE 0 END) applied,
         count(CASE WHEN f.if_issue = 1
                     AND f.issue_date BETWEEN d.grant_date AND date_add('day', 4, d.grant_date)
                    THEN 1 END) loans,
         coalesce(sum(CASE WHEN f.if_issue = 1
                            AND f.issue_date BETWEEN d.grant_date AND date_add('day', 4, d.grant_date)
                           THEN f.contract_amount END), 0) amt
  FROM d LEFT JOIN f ON f.mid = d.mid AND f.rn = 1
  GROUP BY 1,2,3
)
SELECT pm.batch, pm.grp, lvmb.bucket,
       count(*) mids,
       round(avg(pm.applied), 4) "进件率",
       round(avg(CASE WHEN pm.loans > 0 THEN 1 ELSE 0 END), 4) "放款率",
       sum(pm.loans) "放款笔数",
       round(sum(pm.amt), 1) "放款总额",
       round(avg(pm.amt), 1) "人均放款额",
       round(sum(pm.amt) / nullif(sum(pm.loans), 0), 1) "件均"
FROM pm
LEFT JOIN lvmb ON lvmb.batch = pm.batch AND lvmb.grp = pm.grp AND lvmb.mid = pm.mid
GROUP BY 1,2,3
ORDER BY 1,2,3;

-- ======================================================================
-- §8 按日明细（看效果衰减 / 峰值日）
-- ======================================================================
WITH d AS (
  SELECT batch, bt, grp, mid,
         CASE WHEN batch = date '2026-10-28' THEN date '2026-10-27' ELSE date '2026-10-28' END grant_date
  FROM mx.tmp_bat_1028_1029_ys
  WHERE NOT (batch = date '2026-10-28' AND grp = '对照组'
             AND mid IN (SELECT DISTINCT cast(mid AS varchar)
                         FROM ods_view_presto.s05_user_creditlimit_change_record
                         WHERE limit_type='TEMP' AND change_action='CHANGE_LIMIT'
                           AND change_event_type='C015'
                           AND cast(change_total_grantamount AS double) > 0
                           AND create_time >= timestamp '2026-10-28 00:00:00'
                           AND create_time <  timestamp '2026-10-29 00:00:00'))
),
f AS (
  SELECT cast(mid AS varchar) mid, biz_id, issue_date,
         cast(if_issue AS integer) if_issue, cast(contract_amount AS double) contract_amount,
         row_number() OVER (PARTITION BY biz_id ORDER BY app_time DESC) rn
  FROM mx.wxs_application_funnel
  WHERE app_time >= timestamp '2026-10-26 00:00:00' AND app_time < timestamp '2026-11-02 00:00:00'
)
SELECT d.batch, d.grp, f.issue_date,
       count(*) loans, round(sum(f.contract_amount), 1) amt
FROM d JOIN f ON f.mid = d.mid AND f.rn = 1 AND f.if_issue = 1
WHERE f.issue_date BETWEEN d.grant_date AND date_add('day', 4, d.grant_date)
GROUP BY 1,2,3
ORDER BY 1,2,3;

-- ======================================================================
-- §9 清理
-- ======================================================================
-- DROP TABLE IF EXISTS mx.tmp_bat_1028_1029_ys;
