-- ======================================================================
-- 复贷「再授信赋额」新策略灰度验证
-- 2026-11-09 | 墨西哥 | 对照 vs 测试（50/50）
--
-- 【决策流结构】
--   循环额度过期
--     → 资产等级分流：sha256_random_261030 >= 0.5 走 V6_1 决策表；< 0.5 走 V6_2
--     → 再授信赋额分流：sha256_random_261106 < 0.5 进测试组；>= 0.5 进对照组
--     → 两张再授信赋额决策表（V6_1 / V6_2）
--
-- 【重要】先跑 §0！当前数仓里 strategydefid=2326 查不到任何记录，
--   必须先确认新策略是否已落数，否则 §1~§3 全是空表。
-- ======================================================================


-- ======================================================================
-- §0 数据可用性检查（必跑）
--   1) 2326 有没有记录、从哪天开始
--   2) 2326 的输入里到底有没有 sha256_random_261106
-- ======================================================================
SELECT strategydefid, strategytype,
       count(*)                     AS cnt,
       count(DISTINCT externalid)   AS uniq_ext,
       min(endtime)                 AS min_endtime,
       max(endtime)                 AS max_endtime,
       min(etl_date)                AS min_etl_date,
       max(etl_date)                AS max_etl_date
FROM ods.s21_risk_strategy_record
WHERE strategydefid = 2326
GROUP BY 1, 2;

-- 输入里是否有新随机数（返回 0 说明灰度还没接进来，不要往下跑）
SELECT count(*) AS cnt_total,
       count(json_extract_scalar(inputdata, '$.sha256_random_261106')) AS cnt_has_261106,
       count(json_extract_scalar(inputdata, '$.sha256_random_261030')) AS cnt_has_261030
FROM ods.s21_risk_strategy_record
WHERE strategydefid = 2326
  AND etl_date >= '20261106';


-- ======================================================================
-- §1 分流比例校验（应接近 50/50；偏差大说明抽签字段取错或口径不对）
-- ======================================================================
SELECT
  CASE WHEN CAST(json_extract_scalar(inputdata, '$.sha256_random_261106') AS double) < 0.5
       THEN 'T_测试组(<0.5)' ELSE 'C_对照组(>=0.5)' END AS ab_grp,
  CASE WHEN CAST(json_extract_scalar(inputdata, '$.sha256_random_261030') AS double) < 0.5
       THEN 'V6_2' ELSE 'V6_1' END AS ver_grp,
  count(*)                   AS cnt,
  count(DISTINCT externalid) AS uniq_ext
FROM ods.s21_risk_strategy_record
WHERE strategydefid = 2326
  AND etl_date >= '20261106'
  AND json_extract_scalar(inputdata, '$.sha256_random_261106') IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2;


-- ======================================================================
-- §2 核心效果：新旧策略赋额对比（分 V6_1 / V6_2）
--   输出字段（2313 实测存在）：grantcredit_7d_amount / daily_max_available_limit
-- ======================================================================
SELECT
  CASE WHEN CAST(json_extract_scalar(inputdata, '$.sha256_random_261106') AS double) < 0.5
       THEN 'T_测试组' ELSE 'C_对照组' END AS ab_grp,
  CASE WHEN CAST(json_extract_scalar(inputdata, '$.sha256_random_261030') AS double) < 0.5
       THEN 'V6_2' ELSE 'V6_1' END AS ver_grp,
  count(*) AS cnt,
  round(avg(CAST(json_extract_scalar(outputdata, '$.grantcredit_7d_amount')  AS double)), 0) AS avg_grant_7d,
  round(avg(CAST(json_extract_scalar(outputdata, '$.grantcredit_14d_amount') AS double)), 0) AS avg_grant_14d,
  round(avg(CAST(json_extract_scalar(outputdata, '$.grantcredit_21d_amount') AS double)), 0) AS avg_grant_21d,
  round(avg(CAST(json_extract_scalar(outputdata, '$.daily_max_available_limit') AS double)), 0) AS avg_daily_max,
  round(avg(CAST(json_extract_scalar(inputdata,  '$.credit_amount') AS double)), 0) AS avg_old_credit,
  approx_percentile(CAST(json_extract_scalar(outputdata, '$.grantcredit_7d_amount') AS double), 0.5) AS med_grant_7d
FROM ods.s21_risk_strategy_record
WHERE strategydefid = 2326
  AND etl_date >= '20261106'
  AND json_extract_scalar(inputdata, '$.sha256_random_261106') IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2;


-- ======================================================================
-- §3 赋额取值分布：核对是否与「新策略额度表」的档位一致
--   新表档位集合：12000/9000/6000/4800/3500/3200/2400/2000/1600/1200/1000/700/600/500
--   若出现大量不在集合内的值，说明命中了我没覆盖到的分支或用了别的字段
-- ======================================================================
SELECT
  CASE WHEN CAST(json_extract_scalar(inputdata, '$.sha256_random_261106') AS double) < 0.5
       THEN 'T_测试组' ELSE 'C_对照组' END AS ab_grp,
  CASE WHEN CAST(json_extract_scalar(inputdata, '$.sha256_random_261030') AS double) < 0.5
       THEN 'V6_2' ELSE 'V6_1' END AS ver_grp,
  CAST(json_extract_scalar(outputdata, '$.grantcredit_7d_amount') AS bigint) AS grant_7d,
  count(*) AS cnt
FROM ods.s21_risk_strategy_record
WHERE strategydefid = 2326
  AND etl_date >= '20261106'
  AND json_extract_scalar(inputdata, '$.sha256_random_261106') IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;


-- ======================================================================
-- §4 与现有冠军策略 2313 做同口径对照（2313 目前只有 CHAMPION，无 SHADOW）
--   注意：2313 的输入里只有 sha256_random_261030，没有 261106，
--        所以它只能按 V6_1/V6_2 拆，不能按 对照/测试 拆。
-- ======================================================================
SELECT strategydefid, strategytype,
       CASE WHEN CAST(json_extract_scalar(inputdata, '$.sha256_random_261030') AS double) < 0.5
            THEN 'V6_2' ELSE 'V6_1' END AS ver_grp,
       count(*) AS cnt,
       round(avg(CAST(json_extract_scalar(outputdata, '$.grantcredit_7d_amount') AS double)), 0) AS avg_grant_7d,
       round(avg(CAST(json_extract_scalar(outputdata, '$.daily_max_available_limit') AS double)), 0) AS avg_daily_max
FROM ods.s21_risk_strategy_record
WHERE strategydefid = 2313
  AND etl_date >= '20261106'
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
