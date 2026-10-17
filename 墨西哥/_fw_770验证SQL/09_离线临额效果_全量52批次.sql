-- ============================================================================
-- 离线临额效果分析 校验SQL（全量52批次）
-- 数据源: mx.yuhan_temp_limit_base_table_his_20260924  (离线发临额底表)
--         mx.wxs_application_funnel                     (应用/放款漏斗表)
--
-- 【关键口径说明】
-- 1. data_date    : 数据归档分区日（yyyyMMdd字符串）
-- 2. load_time    : 批次实际执行时间，比 data_date 早1天；作为"发临额基准日"
-- 3. temp_limit_issue_date : 用户【历史首次】获得临额的时间，不是本次发放时间，勿用作基准日
-- 4. 关联窗口     : app_date ∈ [load_time, load_time+5天]
-- 5. temp_grant_amount 单位是"分"，÷1000 得比索
-- 6. 实验组识别   :
--    - 有在贷批次  : temp_limit_tag LIKE '%有在贷%'（周一/周三批，tag含 _1/_2/_3 金额档）
--    - 无在贷批次  : temp_limit_tag LIKE '%无在贷%'（周二/周四批）
--    - 组型        : '临额测试组'=临额组；'减息测试组'=减息组；'临额减息'=临额+减息组
--    - tagg        : '可用额度充足且有在贷' / '可用额度充足' / '可用额度不足'（分层标签）
-- ============================================================================


-- ============================================================================
-- Q1【底表盘点】全部发临额批次一览（截止2026-10-15共52个批次）
-- 校验点：批次是否齐全；每批人数、临额金额量级
-- ============================================================================
SELECT data_date,
       COUNT(*)                                            AS cnt,
       COUNT(DISTINCT mid)                                 AS mid_cnt,
       COUNT(DISTINCT temp_limit_tag)                      AS tag_cnt,
       SUM(CASE WHEN temp_limit_issue_amount > 0 THEN 1 ELSE 0 END) AS issue_cnt,
       round(AVG(temp_limit_issue_amount), 0)              AS avg_issue_amt
FROM mx.yuhan_temp_limit_base_table_his_20260924
GROUP BY data_date
ORDER BY data_date;


-- ============================================================================
-- Q2【底表盘点】每个批次 x 实验组 的临额金额/当前临额/主额分布
-- 校验点：实验组命名规则；有在贷批 _1/_2/_3 对应小/中/大金额档
-- ============================================================================
SELECT data_date, temp_limit_tag,
       COUNT(*)                                AS cnt,
       round(AVG(temp_limit_issue_amount), 0)  AS avg_amt,          -- 本次发放临额
       round(AVG(curr_temp_credit_limit), 0)   AS avg_curr_temp,    -- 当前生效临额
       round(AVG(curr_main_credit_limit), 0)   AS avg_main          -- 当前主额
FROM mx.yuhan_temp_limit_base_table_his_20260924
GROUP BY data_date, temp_limit_tag
ORDER BY data_date, temp_limit_tag;


-- ============================================================================
-- Q3【口径校验】data_date / load_time / temp_limit_issue_date 三者关系
-- 校验点：load_time ≈ data_date 前1天；temp_limit_issue_date 远早于批次日（历史首发时间）
-- ============================================================================
SELECT data_date,
       MIN(temp_limit_issue_date) AS min_issue_dt,
       MAX(temp_limit_issue_date) AS max_issue_dt,
       MIN(load_time)             AS min_load,
       MAX(load_time)             AS max_load
FROM mx.yuhan_temp_limit_base_table_his_20260924
WHERE temp_limit_issue_date IS NOT NULL
GROUP BY data_date
ORDER BY data_date;


-- ============================================================================
-- Q4【分层标签】tagg 分布（可用额度充足且有在贷 / 可用额度充足 / 可用额度不足）
-- 校验点：周一三批=有在贷(tagg含"有在贷")，周二四批=无在贷(tagg不含"有在贷")
-- ============================================================================
SELECT data_date, tagg, COUNT(*) AS cnt
FROM mx.yuhan_temp_limit_base_table_his_20260924
GROUP BY data_date, tagg
ORDER BY data_date, tagg;


-- ============================================================================
-- Q5【核心明细】全部52批次放款率
-- 关联：offline.mid = funnel.mid 且 app_date ∈ [load_time, load_time+5天]
-- 放款率 = 5天内有放款的去重mid数 / 批次去重mid数
-- ============================================================================
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         temp_limit_issue_amount, curr_main_credit_limit, curr_temp_credit_limit,
         onloan_bal, onloan_cnt,
         date_trunc('day', load_time) AS issue_base_date
  FROM mx.yuhan_temp_limit_base_table_his_20260924
),
app AS (
  SELECT mid, app_date, if_sx_passed, if_issue, contract_amount,
         temp_grant_amount, credit_amount_sx, daily_max_available_limit_sx
  FROM mx.wxs_application_funnel
  WHERE tenant = 'yawey' AND is_reloan = 'old'
    AND app_date >= date'2026-04-21' AND app_date < date'2026-10-16'
)
SELECT
  o.data_date,
  o.issue_base_date,
  o.temp_limit_tag,
  o.tagg,
  COUNT(DISTINCT o.mid)                                              AS offline_mid_cnt,
  COUNT(DISTINCT CASE WHEN a.mid IS NOT NULL THEN o.mid END)         AS apply_mid_cnt,
  COUNT(DISTINCT CASE WHEN a.if_issue = 1 THEN o.mid END)            AS issue_mid_cnt,
  round(100.0 * COUNT(DISTINCT CASE WHEN a.if_issue = 1 THEN o.mid END)
        / NULLIF(COUNT(DISTINCT o.mid), 0), 2)                       AS issue_rate,
  round(AVG(o.temp_limit_issue_amount), 0)                           AS avg_issue_amt,
  round(AVG(o.curr_main_credit_limit), 0)                            AS avg_main_limit
FROM offline o
LEFT JOIN app a
  ON cast(o.mid as bigint) = cast(a.mid as bigint)
 AND a.app_date >= o.issue_base_date
 AND a.app_date <= date_add('day', 5, o.issue_base_date)
GROUP BY o.data_date, o.issue_base_date, o.temp_limit_tag, o.tagg
ORDER BY o.data_date, o.temp_limit_tag;


-- ============================================================================
-- Q6【汇总】人群(tagg) x 实验组型 放款率
-- 结论：有在贷+额度充足 64.4% >> 额度不足 50.1% >> 无在贷 约35%（组型间几乎无差异）
-- ============================================================================
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         temp_limit_issue_amount,
         date_trunc('day', load_time) AS issue_base_date
  FROM mx.yuhan_temp_limit_base_table_his_20260924
),
app AS (
  SELECT mid, app_date, if_sx_passed, if_issue
  FROM mx.wxs_application_funnel
  WHERE tenant = 'yawey' AND is_reloan = 'old'
    AND app_date >= date'2026-04-21' AND app_date < date'2026-10-16'
)
SELECT
  o.tagg,
  CASE
    WHEN o.temp_limit_tag LIKE '%临额减息%' THEN '临额+减息组'
    WHEN o.temp_limit_tag LIKE '%减息%'     THEN '减息组'
    WHEN o.temp_limit_tag LIKE '%临额%'     THEN '临额组'
    ELSE '其他'
  END                                                                AS exp_group,
  COUNT(DISTINCT o.mid)                                              AS mid_cnt,
  COUNT(DISTINCT CASE WHEN a.mid IS NOT NULL THEN o.mid END)         AS apply_mid_cnt,
  COUNT(DISTINCT CASE WHEN a.if_issue = 1 THEN o.mid END)            AS issue_mid_cnt,
  round(100.0 * COUNT(DISTINCT CASE WHEN a.if_issue = 1 THEN o.mid END)
        / NULLIF(COUNT(DISTINCT o.mid), 0), 2)                       AS issue_rate,
  round(AVG(o.temp_limit_issue_amount), 0)                           AS avg_issue_amt
FROM offline o
LEFT JOIN app a
  ON cast(o.mid as bigint) = cast(a.mid as bigint)
 AND a.app_date >= o.issue_base_date
 AND a.app_date <= date_add('day', 5, o.issue_base_date)
GROUP BY o.tagg,
  CASE
    WHEN o.temp_limit_tag LIKE '%临额减息%' THEN '临额+减息组'
    WHEN o.temp_limit_tag LIKE '%减息%'     THEN '减息组'
    WHEN o.temp_limit_tag LIKE '%临额%'     THEN '临额组'
    ELSE '其他'
  END
ORDER BY o.tagg, exp_group;


-- ============================================================================
-- Q7【趋势】有在贷人群 按月放款率
-- 结论：6-7月峰值62.3%，8-9月稳定59-60%；10月偏低是窗口未走完（1014/1015批未满5天）
-- ============================================================================
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg,
         temp_limit_issue_amount,
         date_trunc('day', load_time) AS issue_base_date,
         date_trunc('month', date_parse(data_date, '%Y%m%d')) AS batch_month
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE temp_limit_tag LIKE '%有在贷%'
),
app AS (
  SELECT mid, app_date, if_issue
  FROM mx.wxs_application_funnel
  WHERE tenant = 'yawey' AND is_reloan = 'old'
    AND app_date >= date'2026-04-21' AND app_date < date'2026-10-16'
)
SELECT
  date_format(o.batch_month, '%Y-%m')                                AS batch_month,
  o.tagg,
  COUNT(DISTINCT o.mid)                                              AS mid_cnt,
  COUNT(DISTINCT CASE WHEN a.if_issue = 1 THEN o.mid END)            AS issue_mid_cnt,
  round(100.0 * COUNT(DISTINCT CASE WHEN a.if_issue = 1 THEN o.mid END)
        / NULLIF(COUNT(DISTINCT o.mid), 0), 2)                       AS issue_rate,
  round(AVG(o.temp_limit_issue_amount), 0)                           AS avg_issue_amt
FROM offline o
LEFT JOIN app a
  ON cast(o.mid as bigint) = cast(a.mid as bigint)
 AND a.app_date >= o.issue_base_date
 AND a.app_date <= date_add('day', 5, o.issue_base_date)
GROUP BY date_format(o.batch_month, '%Y-%m'), o.tagg
ORDER BY batch_month, o.tagg;


-- ============================================================================
-- Q8【对照组】同期未进离线临额底表的用户放款率（按有无在线临额temp_grant_amount分）
-- 校验点：对照组基线。注意"有在线临额"放款率≈99.7%是因为该标记本身只在用信成功后写入，
--         存在幸存者偏差，不宜与离线组直接比。
-- ============================================================================
WITH offline_mid AS (
  SELECT DISTINCT mid FROM mx.yuhan_temp_limit_base_table_his_20260924
),
app AS (
  SELECT mid, app_date, if_sx_passed, if_issue, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant = 'yawey' AND is_reloan = 'old'
    AND app_date >= date'2026-04-21' AND app_date < date'2026-10-16'
)
SELECT
  CASE WHEN a.temp_grant_amount > 0 THEN '有临额(在线)' ELSE '无临额' END AS has_online_temp,
  COUNT(DISTINCT a.mid)                                                   AS total_mid,
  COUNT(DISTINCT CASE WHEN a.if_issue = 1 THEN a.mid END)                 AS issue_mid,
  round(100.0 * COUNT(DISTINCT CASE WHEN a.if_issue = 1 THEN a.mid END)
        / NULLIF(COUNT(DISTINCT a.mid), 0), 2)                            AS issue_rate
FROM app a
LEFT JOIN offline_mid o ON cast(a.mid as bigint) = cast(o.mid as bigint)
WHERE o.mid IS NULL
GROUP BY CASE WHEN a.temp_grant_amount > 0 THEN '有临额(在线)' ELSE '无临额' END;


-- ============================================================================
-- Q9【补充】临额金额分桶对放款率的影响（有在贷人群：金额越大放款率越高，单调递增）
-- ============================================================================
WITH offline AS (
  SELECT mid, data_date, temp_limit_tag, tagg, temp_limit_issue_amount,
         date_trunc('day', load_time) AS issue_base_date
  FROM mx.yuhan_temp_limit_base_table_his_20260924
),
app AS (
  SELECT mid, app_date, if_issue
  FROM mx.wxs_application_funnel
  WHERE tenant = 'yawey' AND is_reloan = 'old'
    AND app_date >= date'2026-04-21' AND app_date < date'2026-10-16'
)
SELECT
  CASE
    WHEN o.temp_limit_issue_amount <= 500  THEN '1_<=500'
    WHEN o.temp_limit_issue_amount <= 1000 THEN '2_500~1k'
    WHEN o.temp_limit_issue_amount <= 2000 THEN '3_1k~2k'
    WHEN o.temp_limit_issue_amount <= 3000 THEN '4_2k~3k'
    ELSE '5_>3k'
  END                                                                AS temp_amt_bucket,
  o.tagg,
  COUNT(DISTINCT o.mid)                                              AS mid_cnt,
  COUNT(DISTINCT CASE WHEN a.if_issue = 1 THEN o.mid END)            AS issue_mid,
  round(100.0 * COUNT(DISTINCT CASE WHEN a.if_issue = 1 THEN o.mid END)
        / NULLIF(COUNT(DISTINCT o.mid), 0), 2)                       AS issue_rate,
  round(AVG(o.temp_limit_issue_amount), 0)                           AS avg_temp_amt
FROM offline o
LEFT JOIN app a
  ON cast(o.mid as bigint) = cast(a.mid as bigint)
 AND a.app_date >= o.issue_base_date
 AND a.app_date <= date_add('day', 5, o.issue_base_date)
GROUP BY 1, o.tagg
ORDER BY 1, o.tagg;
