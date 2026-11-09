-- ======================================================================
-- 离线临额 对照组/测试组 —— 明细数据源（每人一行，周三+周四合并）
-- 整段跑完复制到 Excel，按 batch / grp 拉透视
--
-- batch=2026-10-28  周三·有在贷（261028_{1,2,3}）｜发放 10-27｜窗口 10-27~10-31
-- batch=2026-10-29  周四·无在贷（261029_{1,2,3}）｜发放 10-28｜窗口 10-28~11-01
--
-- 字段：batch / grp / temp_limit_tag / mid / grant_date
--       main_credit_limit        ← 批次表 curr_main_credit_limit（原生）
--       total_available_limit    ← 批次表 total_available_limit（原生）
--       age                      ← 批次表 age（原生）
--       temp_limit_issue_amount  ← 批次表 temp_limit_issue_amount（原生）
--       if_app / if_pass / if_bid / if_issue / if_in_sx_24h / if_in_sx_120h
--       if_SX_passed_24h / if_SX_passed_120h      ← funnel 原生（人级取 max）
--       app_cnt / issue_cnt / contract_amount
--       offline_used_cnt / offline_used_amt        ← v11 原生 used_source_tag / offline_used_this
--       if_offline_used_24h / if_offline_used_120h ← v11 release_time 减 offline_grant_time
--
-- ⚠️ 周三对照组剔除 10-28 当天收到 C015 临额的 2 人（431 → 429）
-- ⚠️ if_in_sx_24h / if_in_sx_120h 是"进件"标记，不是临额用信
--    真临额用信看 offline_used_cnt / offline_used_amt / if_offline_used_24h / if_offline_used_120h
-- ======================================================================
WITH x AS (
  SELECT date '2026-10-28' batch, mid, temp_limit_tag, temp_limit_issue_amount,
         curr_main_credit_limit, total_available_limit, age
  FROM mx.darren_temp_limit_base_table_261028_1
  UNION ALL
  SELECT date '2026-10-28', mid, temp_limit_tag, temp_limit_issue_amount,
         curr_main_credit_limit, total_available_limit, age
  FROM mx.darren_temp_limit_base_table_261028_2
  UNION ALL
  SELECT date '2026-10-28', mid, temp_limit_tag, temp_limit_issue_amount,
         curr_main_credit_limit, total_available_limit, age
  FROM mx.darren_temp_limit_base_table_261028_3
  UNION ALL
  SELECT date '2026-10-29', mid, temp_limit_tag, temp_limit_issue_amount,
         curr_main_credit_limit, total_available_limit, age
  FROM mx.yuhan_temp_disc_base_table_261029_1
  UNION ALL
  SELECT date '2026-10-29', mid, temp_limit_tag, temp_limit_issue_amount,
         curr_main_credit_limit, total_available_limit, age
  FROM mx.yuhan_temp_disc_base_table_261029_2
  UNION ALL
  SELECT date '2026-10-29', mid, temp_limit_tag, temp_limit_issue_amount,
         curr_main_credit_limit, total_available_limit, age
  FROM mx.yuhan_temp_disc_base_table_261029_3
),
c015 AS (   -- 10-28 当天实际收到 C015 临额的人 = 周三对照组污染源
  SELECT DISTINCT cast(mid AS varchar) mid
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE limit_type='TEMP' AND change_action='CHANGE_LIMIT' AND change_event_type='C015'
    AND cast(change_total_grantamount AS double) > 0
    AND create_time >= timestamp '2026-10-28 00:00:00'
    AND create_time <  timestamp '2026-10-29 00:00:00'
),
ln0 AS (
  SELECT x.batch, cast(x.mid AS varchar) mid, x.temp_limit_tag,
         CASE WHEN x.temp_limit_tag LIKE '%对照组%'        THEN '对照组'
              WHEN x.temp_limit_tag LIKE '%临额减息测试组%' THEN '测试组(临额+减息)'
              WHEN x.temp_limit_tag LIKE '%临额测试组%'     THEN '测试组(临额)'
              WHEN x.temp_limit_tag LIKE '%减息测试组%'     THEN '减息组(无临额)' END grp,
         CASE WHEN x.batch = date '2026-10-28' THEN timestamp '2026-10-27 00:00:00'
              ELSE timestamp '2026-10-28 00:00:00' END grant_ts,
         CASE WHEN x.batch = date '2026-10-28' THEN date '2026-10-27' ELSE date '2026-10-28' END grant_date,
         CASE WHEN x.batch = date '2026-10-28' THEN date '2026-10-31' ELSE date '2026-11-01' END grant_end,
         x.curr_main_credit_limit main_credit_limit,
         x.total_available_limit  total_available_limit,
         x.age                    age,
         x.temp_limit_issue_amount temp_limit_issue_amount
  FROM x
),
ln AS (
  SELECT * FROM ln0 l
  WHERE l.grp IS NOT NULL
    AND NOT (l.batch = date '2026-10-28' AND l.grp = '对照组'
             AND l.mid IN (SELECT c.mid FROM c015 c))
),
fv AS (   -- 漏斗 + v11 额度表，按 biz_id 一一对应
  SELECT f.mid, f.biz_id, f.app_date, f.issue_date,
         f.if_app, f.if_pass, f.if_bid, f.if_issue,
         f.if_in_sx_24h, f.if_in_sx_120h, f.if_SX_passed_24h, f.if_SX_passed_120h,
         f.contract_amount,
         v.used_source_tag, v.offline_used_this,
         v.offline_grant_time, v.release_time
  FROM (
    SELECT cast(mid AS varchar) mid, biz_id, app_date, issue_date,
           cast(if_app AS integer) if_app, cast(if_pass AS integer) if_pass,
           cast(if_bid AS integer) if_bid, cast(if_issue AS integer) if_issue,
           cast(if_in_sx_24h AS integer) if_in_sx_24h,
           cast(if_in_sx_120h AS integer) if_in_sx_120h,
           cast(if_SX_passed_24h AS integer) if_SX_passed_24h,
           cast(if_SX_passed_120h AS integer) if_SX_passed_120h,
           cast(contract_amount AS double) contract_amount,
           row_number() OVER (PARTITION BY biz_id ORDER BY app_time DESC) rn
    FROM mx.wxs_application_funnel
    WHERE app_time >= timestamp '2026-10-26 00:00:00' AND app_time < timestamp '2026-11-02 00:00:00'
  ) f
  LEFT JOIN (
    SELECT biz_id,
           max_by(used_source_tag, release_time) used_source_tag,
           max_by(offline_used_this, release_time) offline_used_this,
           max_by(offline_grant_time, release_time) offline_grant_time,
           max(release_time) release_time
    FROM mx.yj_asset_quota_v11
    WHERE issue_date >= date '2026-10-26'
    GROUP BY 1
  ) v ON v.biz_id = cast(f.biz_id AS bigint)
  WHERE f.rn = 1
),
per_app AS (   -- 进件类：按进件日 app_date 落窗口
  SELECT l.batch, l.grp, l.mid,
         max(g.if_app) if_app, max(g.if_pass) if_pass, max(g.if_bid) if_bid,
         max(g.if_in_sx_24h) if_in_sx_24h, max(g.if_in_sx_120h) if_in_sx_120h,
         max(g.if_SX_passed_24h) if_SX_passed_24h, max(g.if_SX_passed_120h) if_SX_passed_120h,
         count(CASE WHEN g.if_bid = 1 THEN 1 END) app_cnt
  FROM ln l
  LEFT JOIN fv g ON g.mid = l.mid
    AND g.app_date BETWEEN l.grant_date AND l.grant_end
  GROUP BY 1,2,3
),
per_issue AS (   -- 放款类：按放款日 issue_date 落窗口
  SELECT l.batch, l.grp, l.mid,
         max(g.if_issue) if_issue,
         count(CASE WHEN g.if_issue = 1 THEN 1 END) issue_cnt,
         coalesce(sum(CASE WHEN g.if_issue = 1 THEN g.contract_amount END), 0) contract_amount,
         count(CASE WHEN g.used_source_tag = 'offline' AND g.offline_used_this > 0 THEN 1 END)
           offline_used_cnt,
         coalesce(sum(CASE WHEN g.used_source_tag = 'offline' THEN g.offline_used_this END), 0)
           offline_used_amt,
         max(CASE WHEN g.used_source_tag = 'offline' AND g.offline_used_this > 0
                   AND g.release_time >= g.offline_grant_time
                   AND g.release_time <  g.offline_grant_time + interval '1' day
              THEN 1 ELSE 0 END) if_offline_used_24h,
         max(CASE WHEN g.used_source_tag = 'offline' AND g.offline_used_this > 0
                   AND g.release_time >= g.offline_grant_time
                   AND g.release_time <  g.offline_grant_time + interval '5' day
              THEN 1 ELSE 0 END) if_offline_used_120h
  FROM ln l
  LEFT JOIN fv g ON g.mid = l.mid
    AND g.issue_date BETWEEN l.grant_date AND l.grant_end
  GROUP BY 1,2,3
)
SELECT l.batch, l.grp, l.temp_limit_tag, l.mid, l.grant_date,
       l.main_credit_limit, l.total_available_limit, l.age, l.temp_limit_issue_amount,
       coalesce(pa.if_app, 0) if_app, coalesce(pa.app_cnt, 0) app_cnt,
       coalesce(pa.if_pass, 0) if_pass,
       coalesce(pa.if_bid, 0) if_bid,
       coalesce(pi.if_issue, 0) if_issue, coalesce(pi.issue_cnt, 0) issue_cnt,
       coalesce(pi.contract_amount, 0) contract_amount,
       coalesce(pi.offline_used_cnt, 0) offline_used_cnt,
       coalesce(pi.offline_used_amt, 0) offline_used_amt,
       coalesce(pi.if_offline_used_24h, 0) if_offline_used_24h,
       coalesce(pi.if_offline_used_120h, 0) if_offline_used_120h,
       coalesce(pa.if_in_sx_24h, 0) if_in_sx_24h,
       coalesce(pa.if_in_sx_120h, 0) if_in_sx_120h,
       coalesce(pa.if_SX_passed_24h, 0) if_SX_passed_24h,
       coalesce(pa.if_SX_passed_120h, 0) if_SX_passed_120h
FROM ln l
LEFT JOIN per_app pa   ON pa.batch = l.batch AND pa.grp = l.grp AND pa.mid = l.mid
LEFT JOIN per_issue pi ON pi.batch = l.batch AND pi.grp = l.grp AND pi.mid = l.mid
ORDER BY l.batch, l.grp, l.mid;
