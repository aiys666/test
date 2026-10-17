-- =========================================================================
-- 03_C010对账与双路径.sql
-- 探查目标: 搞清楚在线临额(C010)与yj宽表(tag=1)的对账关系
--           量化在线/离线双路径的客户重叠
-- 窗口: 2026-08-19 ~ 2026-10-06（统一窗口，所有SQL共用）
-- =========================================================================

/* =========================================================================
   公共窗口变量（SQL内直接写死）:
   yj侧:  app_date >= date'2026-08-19' AND app_date < date'2026-10-06'
   K表侧: create_time >= date'2026-08-19' AND create_time < date'2026-10-06'
============================================================================= */


/* =========================================================================
   SQL 3-1: C010 关键列样例 —— 找关联键
   探查目标: C010有哪些可用作业务单号的字段？
   预期结论: external_id 就是 biz_id（varchar类型，关联需cast）
============================================================================= */
SELECT
  id,
  mid,
  external_id,
  risk_invoke_id,
  change_total_grantamount,
  change_used_grantamount,
  create_time,
  expiring_time,
  change_desc
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE change_event_type = 'C010'
  AND create_time >= date'2026-08-19'
ORDER BY create_time DESC
LIMIT 5;


/* =========================================================================
   SQL 3-2: C010 change_desc 语义验证
   探查目标: C010是"用户点确认借款页创建"还是每次都实际使用？
   预期结论: change_desc固定值="用户点确认借款页面创建临额"
            不是每次都实际用——需要看yj的temp_grant_amount>0才是真实使用
============================================================================= */
SELECT
  change_desc,
  COUNT(*)    AS c
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE change_event_type = 'C010'
  AND create_time >= date'2026-08-19'
  AND create_time < date'2026-10-06'
GROUP BY 1
ORDER BY c DESC
LIMIT 5;


/* =========================================================================
   SQL 3-3: yj侧 —— 弹窗展示vs实际使用占比
   探查目标: tag=1的客户里，有多少真的用了临额？
   预期结论: 展示过(tag=1)的人中约70-80%实际使用(temp_grant_amount>0)
   关键: tag=1是"弹窗展示"，≠"实际使用"！
   金额单位: temp_grant_amount 是分，÷1000.0 得比索
============================================================================= */
SELECT
  SUM(CASE WHEN temp_credit_amount_issue_tag = 1 THEN 1 ELSE 0 END)            AS tag1_cnt,
  SUM(CASE WHEN temp_credit_amount_issue_tag = 1 AND temp_grant_amount > 0
           THEN 1 ELSE 0 END)                                                  AS tag1_used_cnt,
  round(100.0 * SUM(CASE WHEN temp_credit_amount_issue_tag = 1 AND temp_grant_amount > 0
                           THEN 1 ELSE 0 END)
                / NULLIF(SUM(CASE WHEN temp_credit_amount_issue_tag = 1
                                    THEN 1 ELSE 0 END), 0), 1)                 AS used_pct
FROM mx.yj_test_table_250225
WHERE is_reloan = 'old'
  AND if_issue = 1
  AND app_date >= date'2026-08-19'
  AND app_date < date'2026-10-06';


/* =========================================================================
   SQL 3-4: yj侧完整统计 —— tag/mid/金额
   探查目标: yj侧在线临额(tag=1+使用)的笔数、客户数、金额
   作为C010侧的对照组
============================================================================= */
SELECT
  SUM(CASE WHEN temp_credit_amount_issue_tag = 1 THEN 1 ELSE 0 END)            AS tag1_cnt,
  SUM(CASE WHEN temp_credit_amount_issue_tag = 1 AND temp_grant_amount > 0
           THEN 1 ELSE 0 END)                                                  AS tag1_used_cnt,
  COUNT(DISTINCT CASE WHEN temp_credit_amount_issue_tag = 1 THEN mid END)       AS tag1_mid,
  COUNT(DISTINCT CASE WHEN temp_credit_amount_issue_tag = 1 AND temp_grant_amount > 0
                      THEN mid END)                                             AS tag1_used_mid,
  round(SUM(CASE WHEN temp_credit_amount_issue_tag = 1 AND temp_grant_amount > 0
                  THEN temp_grant_amount / 1000.0 ELSE 0 END), 1)              AS used_amt
FROM mx.yj_test_table_250225
WHERE is_reloan = 'old'
  AND if_issue = 1
  AND app_date >= date'2026-08-19'
  AND app_date < date'2026-10-06';


/* =========================================================================
   SQL 3-5: C010侧完整统计 —— 笔数/mid/金额
   探查目标: C010发放的笔数、客户数、发放额、存量占用
   ⚠️ 关键修正: change_used_grantamount 是发放前存量占用，不是本次支用！
============================================================================= */
SELECT
  COUNT(*)                                            AS c010_cnt,
  COUNT(DISTINCT mid)                                 AS c010_mid,
  COUNT(DISTINCT external_id)                         AS c010_extid,
  round(SUM(change_total_grantamount), 1)             AS c010_grant_amt,
  round(SUM(change_used_grantamount), 1)              AS c010_used_amt
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE change_event_type = 'C010'
  AND create_time >= date'2026-08-19'
  AND create_time < date'2026-10-06';


/* =========================================================================
   SQL 3-6: biz级对账 —— yj(用临额的笔) vs C010.external_id
   探查目标: 按业务单号对账，yj和C010的匹配率
   预期结论: 匹配率应该在97-99%（少数yj无对应C010的可能是离线临额）
   关联键: cast(biz_id as varchar) —— 两边都是字符串
============================================================================= */
WITH y AS (
  SELECT DISTINCT cast(biz_id as varchar) AS bid
  FROM mx.yj_test_table_250225
  WHERE is_reloan = 'old'
    AND if_issue = 1
    AND temp_credit_amount_issue_tag = 1
    AND temp_grant_amount > 0
    AND app_date >= date'2026-08-19'
    AND app_date < date'2026-10-06'
),
c AS (
  SELECT DISTINCT cast(external_id as varchar) AS bid
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type = 'C010'
    AND create_time >= date'2026-08-19'
    AND create_time < date'2026-10-06'
)
SELECT
  (SELECT COUNT(*) FROM y)             AS y_used_biz,
  (SELECT COUNT(*) FROM c)             AS c010_biz,
  COUNT(*)                             AS matched_biz,
  round(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM y), 0), 2) AS match_pct
FROM y JOIN c ON y.bid = c.bid;


/* =========================================================================
   SQL 3-7: mid级对账 —— yj vs C010
   探查目标: 按客户对账，多少人在yj有使用记录同时在K表有C010事件
============================================================================= */
WITH y AS (
  SELECT DISTINCT mid
  FROM mx.yj_test_table_250225
  WHERE is_reloan = 'old'
    AND if_issue = 1
    AND temp_credit_amount_issue_tag = 1
    AND temp_grant_amount > 0
    AND app_date >= date'2026-08-19'
    AND app_date < date'2026-10-06'
),
c AS (
  SELECT DISTINCT mid
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type = 'C010'
    AND create_time >= date'2026-08-19'
    AND create_time < date'2026-10-06'
)
SELECT
  (SELECT COUNT(*) FROM y)     AS y_mid,
  (SELECT COUNT(*) FROM c)     AS c010_mid,
  COUNT(*)                     AS matched_mid,
  round(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM y), 0), 2) AS match_pct
FROM y JOIN c ON y.mid = c.mid;


/* =========================================================================
   SQL 3-8: 金额三口径对比
   探查目标: 对比三个侧的金额，看差异来源
     - C010.change_total_grantamount: 发放上限
     - C003.change_total_grantamount: FREEZE事件金额
     - yj.temp_grant_amount: 实际使用额（/1000转比索）
   预期结论: yj实际使用 ≈ C003冻结额 ≈ C010净可用(total - used)
             C010发放上限 ≥ 实际使用（因为有部分没用到）
============================================================================= */
SELECT
  round(SUM(CASE WHEN c.change_event_type = 'C010'
                 THEN c.change_total_grantamount ELSE 0 END), 1)  AS c010_grant_amt,   -- 发放上限
  round(SUM(CASE WHEN c.change_event_type = 'C010'
                 THEN c.change_used_grantamount ELSE 0 END), 1)   AS c010_used_amt,    -- 存量占用
  round(SUM(CASE WHEN c.change_event_type = 'C010'
                 THEN c.change_total_grantamount - c.change_used_grantamount
                 ELSE 0 END), 1)                                  AS c010_net_amt,     -- 净可用
  round(SUM(CASE WHEN c.change_event_type = 'C003'
                 THEN c.change_total_grantamount ELSE 0 END), 1)  AS c003_freeze_amt   -- 冻结额（对照）
FROM ods_view_presto.s05_user_creditlimit_change_record c
WHERE c.limit_type = 'TEMP'
  AND c.change_event_type IN ('C010', 'C003')
  AND c.create_time >= date'2026-08-19'
  AND c.create_time < date'2026-10-06';

-- yj侧实际使用额（单独跑，对照）
SELECT
  round(SUM(temp_grant_amount / 1000.0), 1)  AS yj_used_amt
FROM mx.yj_test_table_250225
WHERE is_reloan = 'old'
  AND if_issue = 1
  AND temp_credit_amount_issue_tag = 1
  AND temp_grant_amount > 0
  AND app_date >= date'2026-08-19'
  AND app_date < date'2026-10-06';


/* =========================================================================
   SQL 3-9: 月度覆盖 —— 7月是否有复贷老客数据
   探查目标: yj宽表是否覆盖到6月？确认窗口完整性
============================================================================= */
SELECT
  date_format(app_date, '%Y-%m')         AS m,
  COUNT(*)                               AS rows_all,
  SUM(CASE WHEN is_reloan = 'old' THEN 1 ELSE 0 END)  AS old_rows,
  SUM(CASE WHEN is_reloan = 'old' AND if_issue = 1 THEN 1 ELSE 0 END)  AS old_issued
FROM mx.yj_test_table_250225
WHERE app_date >= date'2026-06-01'
  AND app_date < date'2026-10-06'
GROUP BY 1
ORDER BY 1;


/* =========================================================================
   SQL 3-10: biz_id 唯一性校验
   探查目标: yj宽表中 biz_id 是否唯一（一币一单）
   预期结论: biz_id唯一，行数=distinct biz_id
============================================================================= */
SELECT
  COUNT(*)                         AS n_rows,
  COUNT(DISTINCT biz_id)           AS n_biz,
  COUNT(DISTINCT mid)              AS n_mid
FROM mx.yj_test_table_250225
WHERE is_reloan = 'old'
  AND if_issue = 1
  AND app_date >= date'2026-08-19'
  AND app_date < date'2026-10-06';


/* =========================================================================
   SQL 3-11: 同mid跨笔使用临额次数分布
   探查目标: 一个客户会不会多次用临额？分布怎样？
============================================================================= */
SELECT
  uses,
  COUNT(*)   AS mids
FROM (
  SELECT
    mid,
    COUNT(*)   AS uses
  FROM mx.yj_test_table_250225
  WHERE is_reloan = 'old'
    AND if_issue = 1
    AND temp_grant_amount > 0
    AND app_date >= date'2026-08-19'
    AND app_date < date'2026-10-06'
  GROUP BY mid
) t
GROUP BY uses
ORDER BY uses;


/* =========================================================================
   SQL 3-12: 在线×离线双路径重叠
   探查目标: 同一客户会不会同时走在线和离线两条路？占比多少？
   判定: has_on = tag=1（有弹窗）
         has_off = 用了临额但tag≠1（推测走离线）
   预期结论: 多数客户只走一条路，双路径叠加占比低
============================================================================= */
SELECT
  SUM(CASE WHEN has_on = 1 AND has_off = 1 THEN 1 ELSE 0 END)   AS both_path,
  SUM(CASE WHEN has_on = 1 AND has_off = 0 THEN 1 ELSE 0 END)   AS online_only,
  SUM(CASE WHEN has_on = 0 AND has_off = 1 THEN 1 ELSE 0 END)   AS offline_only,
  SUM(CASE WHEN has_on = 0 AND has_off = 0 THEN 1 ELSE 0 END)   AS neither,
  COUNT(*)                                                       AS mid_total
FROM (
  SELECT
    mid,
    MAX(CASE WHEN temp_credit_amount_issue_tag = 1 THEN 1 ELSE 0 END)               AS has_on,
    MAX(CASE WHEN temp_grant_amount > 0 AND temp_credit_amount_issue_tag <> 1
            THEN 1 ELSE 0 END)                                                     AS has_off
  FROM mx.yj_test_table_250225
  WHERE is_reloan = 'old'
    AND if_issue = 1
    AND app_date >= date'2026-08-19'
    AND app_date < date'2026-10-06'
  GROUP BY mid
) t;


/* =========================================================================
   SQL 3-13: 双路径mid级交叉表
   探查目标: 另一种口径——从K表(C010/C013/C015)视角看双路径
   窗口: 2026-07-01起（K表窗口略宽）
============================================================================= */
WITH y AS (
  SELECT DISTINCT mid
  FROM mx.yj_test_table_250225
  WHERE is_reloan = 'old'
    AND if_issue = 1
    AND app_date >= date'2026-08-19'
    AND app_date < date'2026-10-06'
),
e AS (
  SELECT
    mid,
    MAX(CASE WHEN change_event_type = 'C010' THEN 1 ELSE 0 END)         AS has_online,
    MAX(CASE WHEN change_event_type IN ('C013', 'C015') THEN 1 ELSE 0 END) AS has_offline
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE limit_type = 'TEMP'
    AND create_time >= date'2026-07-01'
  GROUP BY mid
)
SELECT
  COUNT(*)                                                                 AS yj_mids,
  SUM(CASE WHEN e.has_online = 1 AND e.has_offline = 1 THEN 1 ELSE 0 END)  AS both_path_mids,
  round(100.0 * SUM(CASE WHEN e.has_online = 1 AND e.has_offline = 1
                            THEN 1 ELSE 0 END) / COUNT(*), 1)              AS both_pct
FROM y JOIN e ON y.mid = e.mid;
