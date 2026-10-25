-- ======================================================================
-- 临额分析 第一步：发放 → 覆盖 → 使用 → 未用   取数 SQL（v10 口径）
-- 2026-10-23 | 窗口 2026-09-01 ~ 2026-10-21 | 复贷老客
--
-- ══════════════════════════════════════════════════════════════════════
-- 【v10 相对 v8 改了什么】只动了 Q8，Q1~Q7 一个数都没变（见下方说明）
--
--   ① ★ Q8「沉淀的离线可用额度」加 offline_batch_seq = 1 去重
--      离线临额是**账户级(mid)**事实被扇成逐笔：同一 mid 在 5 天有效期内放多笔，
--      同一批额度在宽表每一行各记一次。v9 实测逐行 SUM 虚增 **44.7%**
--      （1,729 万 vs 去重 1,195 万）；发放额虚增 **60.8%**（1,941 万 vs 1,207 万）。
--      → 凡是回答「总共发了多少 / 总共还剩多少可用」，必须去重。
--      ✅ Q3/Q4/Q6/Q7 用的 *_used_this 是逐笔事实，**不受影响、不要去重**。
--
--   ② ★ Q8 超期判据 age > 4 → **age > 5**
--      v9 的 offline_grant_age_days 用 yuhan.data_date 算，而 data_date 相对台账实际
--      发放时刻的偏移**不统一**（实测 +1 天 11,508 笔 / +0 天 2,114 笔 / +2 天 78 笔），
--      导致该列恒偏小约 1 天、取值域被压在 [-1,4] → 「> 4」实际上永不成立（恒为 0）。
--      v10 改用台账 C015/C013 的真实发放时刻，取值域 [0,5]，5 = 到期当日**仍有效**。
--
--   ③ Q8 新增剩余有效期分档（offline_expire_days = 5 − 账龄），口径与 v3 宽表一致
--
--   ⚠️ 另需知道：v10 把离线有效期窗口从日粒度改成**时刻级**（发放必须早于用信决策），
--      holds_offline 13,620 → 11,904（剔掉 1,942 笔"放款当晚才发"的误判）。
--      所以 Q8 的「持有笔数」会比 v8 少约 1,700 笔 —— 这是修正，不是回退。
--      被剔掉的笔里只有 1 笔曾判为用了离线临额（200 元），故使用额口径几乎不变。
-- ══════════════════════════════════════════════════════════════════════
--
-- 【相对初版（v5 口径）改了什么】
--   数据源 mx.yj_asset_quota_v5 → mx.yj_asset_quota_v10，三处口径随之修正：
--     ① 离线发放加「有效期 5 天 + 只留真发放组」过滤 → Q8 的口径自动与 Q3/Q4 对齐
--        （初版 Q8 用 v5 的列、没剔减息组/对照组，和 Q3/Q4 的 14,715 vs 13,584 对不上）
--     ② 可用额度锚点改为「用信决策之前」，排除本笔自己的 C010 事件
--        → Q8 的「沉淀可用额度」显著变大（v5 少算了持有但没用的那批）
--     ③ 可用额度与「本笔用了哪种临额」解耦（holds_offline），
--        → Q8 改用 holds_offline 判「持有」，不再用 offline_grant_amount IS NOT NULL + age 条件
--   ⚠️ Q1~Q7 的数字理论上不变：它们要么不依赖 v8（Q1/Q2/Q5），
--      要么只用 *_used_this（Q3/Q4/Q6/Q7），而使用额的归属逻辑 v5→v8 一直没动。
--      跑完请对一下，若有差异说明还有没排查到的联动。
--
-- 【怎么用】每段独立可跑，输出都是「指标名 + 数值」的纵向结构，直接粘 Excel。
--          段与段之间没有依赖，想看哪块跑哪块。
--
-- 【依赖的三张现成表】
--   mx.yuhan_temp_limit_base_table_his_20260924  离线发放事实（mid 级批次表）
--   mx.wxs_application_funnel                    进件 + 放款（biz 级）
--   mx.yj_asset_quota_v10                         放款笔的额度与临额使用（biz 级）
--
-- 【★ 最关键的口径：谁算"真发放"】
--   yuhan 表里 temp_limit_issue_amount > 0 不等于真发了额度。实测 C015 事件命中率：
--     临额组     21,628 人次 → 100%      ← 真发
--     临额减息组  2,827 人次 → 100%      ← 真发
--     减息组      5,028 人次 →   2.7%    ← 圈了不发
--     对照组        275 人次 →   0.7%    ← 圈了不发（1021 批次起的灰度对照）
--   → 所以「发放」必须过滤：tag LIKE '%临额%' AND tag NOT LIKE '%对照组%'
--   → 不过滤会让发放人数虚高 2,599 人、发放额虚高 531 万，后面所有比率被稀释
--
-- 【离线有效期】yuhan.data_date = 实际发放日 + 1，有效 5 天
--   → 有效判据 age = DATE_DIFF('day', data_date, 目标日) ∈ [-1, 4]
--
-- 【在线发放】本笔自己 1386 tag=1 且 857 弹窗额 > 0
--   （在线临额按本笔主额支用算额，主额支用=0 时发放必然=0，所以这是硬门槛）
--
-- 【人次 vs 人数】同一人被多个批次反复圈中，人次 24,097 / 去重 11,201（人均 2.15 次）
--   → 漏斗主线用去重人数（否则各层分母不一致），发放规模用人次
-- ======================================================================


-- ══════════════════════════════════════════════════════════════════════
-- Q1  批次发放明细（按 批次日 × 标签）—— 这段是明细，直接粘 Excel 做透视
-- ══════════════════════════════════════════════════════════════════════
SELECT y.data_date,
       y.temp_limit_tag                                              AS tag,
       CASE WHEN y.temp_limit_tag LIKE '%对照组%'   THEN '4_对照组'
            WHEN y.temp_limit_tag LIKE '%临额减息%' THEN '3_临额减息组'
            WHEN y.temp_limit_tag LIKE '%减息%'     THEN '2_减息组'
            ELSE '1_临额组' END                                      AS grp,
       CASE WHEN y.temp_limit_tag LIKE '%临额%'
             AND y.temp_limit_tag NOT LIKE '%对照组%' THEN 1 ELSE 0 END AS is_real_grant,
       CASE WHEN STRPOS(y.temp_limit_tag, '有在贷') > 0 THEN '有在贷' ELSE '无在贷' END AS crowd,
       CASE WHEN y.temp_limit_tag LIKE '%\_1' ESCAPE '\' THEN '10%'
            WHEN y.temp_limit_tag LIKE '%\_2' ESCAPE '\' THEN '20%'
            WHEN y.temp_limit_tag LIKE '%\_3' ESCAPE '\' THEN '30%'
            WHEN STRPOS(y.temp_limit_tag, '无在贷') > 0  THEN '30%'
            ELSE '20%' END                                           AS ratio_tag,
       COUNT(DISTINCT y.mid)                                         AS mid_n,
       SUM(CAST(y.temp_limit_issue_amount AS DOUBLE))                AS grant_amt,
       AVG(CAST(y.temp_limit_issue_amount AS DOUBLE))                AS avg_amt
FROM mx.yuhan_temp_limit_base_table_his_20260924 y
WHERE y.data_date BETWEEN '20260901' AND '20261021'
  AND y.temp_limit_issue_amount IS NOT NULL
  AND CAST(y.temp_limit_issue_amount AS DOUBLE) > 0
GROUP BY 1,2,3,4,5,6
ORDER BY 1 DESC, 8 DESC;


-- ══════════════════════════════════════════════════════════════════════
-- Q2  各组是否"真发放"验证（C015 事件命中率）
--     逻辑：yuhan 的每条圈选记录，去 change_record 找该 mid 在 ±3 天内有没有
--           C015/C013（离线发放事件）。命中率接近 100% = 真发；接近 0 = 圈了不发
-- ══════════════════════════════════════════════════════════════════════
WITH b AS (
  SELECT CAST(y.mid AS VARCHAR) AS mid,
         CAST(date_parse(y.data_date,'%Y%m%d') AS DATE) AS d,
         CAST(y.temp_limit_issue_amount AS DOUBLE) AS amt,
         y.temp_limit_tag AS tag
  FROM mx.yuhan_temp_limit_base_table_his_20260924 y
  WHERE y.data_date BETWEEN '20260901' AND '20261021'
    AND y.temp_limit_issue_amount IS NOT NULL
    AND CAST(y.temp_limit_issue_amount AS DOUBLE) > 0
),
ev AS (
  SELECT DISTINCT CAST(c.mid AS VARCHAR) AS mid, CAST(c.create_time AS DATE) AS ed
  FROM ods_view_presto.s05_user_creditlimit_change_record c
  WHERE c.limit_type = 'TEMP'
    AND c.change_event_type IN ('C015','C013')
    AND c.change_action = 'CHANGE_LIMIT'
    AND CAST(c.change_total_grantamount AS DOUBLE) > 0
    AND c.create_time >= TIMESTAMP '2026-08-28 00:00:00'
)
SELECT CASE WHEN b.tag LIKE '%对照组%'   THEN '4_对照组'
            WHEN b.tag LIKE '%临额减息%' THEN '3_临额减息组'
            WHEN b.tag LIKE '%减息%'     THEN '2_减息组'
            ELSE '1_临额组' END                          AS grp,
       COUNT(1)                                          AS person_times,
       COUNT(DISTINCT b.mid)                             AS mid_n,
       SUM(b.amt)                                        AS grant_amt,
       SUM(CASE WHEN ev.mid IS NOT NULL THEN 1 ELSE 0 END) AS n_has_c015,
       CAST(SUM(CASE WHEN ev.mid IS NOT NULL THEN 1 ELSE 0 END) AS DOUBLE)
         / NULLIF(CAST(COUNT(1) AS DOUBLE),0)            AS pct_has_c015
FROM b
LEFT JOIN ev ON ev.mid = b.mid AND DATE_DIFF('day', b.d, ev.ed) BETWEEN -3 AND 2
GROUP BY 1 ORDER BY 1;


-- ══════════════════════════════════════════════════════════════════════
-- Q3  离线供给漏斗 L1→L4（纵向，每层一行）
--     L1 发放  = 真发放批次的去重 mid
--     L2 进件  = 其中在有效期内有进件的 mid / 进件笔
--     L3 放款  = 其中在有效期内放款成功的 mid / 笔 / 放款额
--     L4 用临额 = 这些放款笔里 offline_used_this > 0 的
-- ══════════════════════════════════════════════════════════════════════
WITH b AS (
  SELECT CAST(y.mid AS VARCHAR) AS mid,
         CAST(date_parse(y.data_date,'%Y%m%d') AS DATE) AS d,
         CAST(y.temp_limit_issue_amount AS DOUBLE) AS amt
  FROM mx.yuhan_temp_limit_base_table_his_20260924 y
  WHERE y.data_date BETWEEN '20260901' AND '20261021'
    AND y.temp_limit_issue_amount IS NOT NULL
    AND CAST(y.temp_limit_issue_amount AS DOUBLE) > 0
    AND y.temp_limit_tag LIKE '%临额%'
    AND y.temp_limit_tag NOT LIKE '%对照组%'          -- ★ 只留真发放
),
app AS (
  SELECT DISTINCT b.mid, CAST(f.biz_id AS VARCHAR) AS biz_v
  FROM b JOIN mx.wxs_application_funnel f
    ON  CAST(f.mid AS VARCHAR) = b.mid
   AND  f.is_reloan = 'old'
   AND  f.app_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
   AND  DATE_DIFF('day', b.d, f.app_date) BETWEEN -1 AND 4
),
iss AS (
  SELECT DISTINCT b.mid, CAST(f.biz_id AS VARCHAR) AS biz_v,
         CAST(f.contract_amount AS DOUBLE) AS contract_amount
  FROM b JOIN mx.wxs_application_funnel f
    ON  CAST(f.mid AS VARCHAR) = b.mid
   AND  f.is_reloan = 'old' AND f.if_issue = 1
   AND  f.issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
   AND  DATE_DIFF('day', b.d, f.issue_date) BETWEEN -1 AND 4
),
used AS (
  SELECT i.mid, i.biz_v, q.offline_used_this, q.contract_amount AS q_contract
  FROM iss i JOIN mx.yj_asset_quota_v10 q ON CAST(q.biz_id AS VARCHAR) = i.biz_v
  WHERE q.offline_used_this > 0.05
)
SELECT 'L1_发放'   AS layer, CAST((SELECT COUNT(DISTINCT mid) FROM b) AS DOUBLE)    AS mid_n,
       CAST((SELECT COUNT(1) FROM b) AS DOUBLE)                                     AS biz_or_times,
       CAST((SELECT SUM(amt) FROM b) AS DOUBLE)                                     AS amt
UNION ALL
SELECT 'L2_进件', CAST((SELECT COUNT(DISTINCT mid) FROM app) AS DOUBLE),
       CAST((SELECT COUNT(DISTINCT biz_v) FROM app) AS DOUBLE), CAST(NULL AS DOUBLE)
UNION ALL
SELECT 'L3_放款', CAST((SELECT COUNT(DISTINCT mid) FROM iss) AS DOUBLE),
       CAST((SELECT COUNT(DISTINCT biz_v) FROM iss) AS DOUBLE),
       CAST((SELECT SUM(contract_amount) FROM iss) AS DOUBLE)
UNION ALL
SELECT 'L4_用临额', CAST((SELECT COUNT(DISTINCT mid) FROM used) AS DOUBLE),
       CAST((SELECT COUNT(DISTINCT biz_v) FROM used) AS DOUBLE),
       CAST((SELECT SUM(offline_used_this) FROM used) AS DOUBLE)
UNION ALL
SELECT 'L4_覆盖合同额', CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE),
       CAST((SELECT SUM(q_contract) FROM used) AS DOUBLE)
ORDER BY 1;


-- ══════════════════════════════════════════════════════════════════════
-- Q4  未用三层拆解（人级，4 行加总 = L1 发放人数）
-- ══════════════════════════════════════════════════════════════════════
WITH b AS (
  SELECT CAST(y.mid AS VARCHAR) AS mid,
         CAST(date_parse(y.data_date,'%Y%m%d') AS DATE) AS d
  FROM mx.yuhan_temp_limit_base_table_his_20260924 y
  WHERE y.data_date BETWEEN '20260901' AND '20261021'
    AND y.temp_limit_issue_amount IS NOT NULL
    AND CAST(y.temp_limit_issue_amount AS DOUBLE) > 0
    AND y.temp_limit_tag LIKE '%临额%' AND y.temp_limit_tag NOT LIKE '%对照组%'
),
bm AS (SELECT DISTINCT mid FROM b),
app AS (
  SELECT DISTINCT b.mid FROM b JOIN mx.wxs_application_funnel f
    ON CAST(f.mid AS VARCHAR) = b.mid AND f.is_reloan='old'
   AND f.app_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
   AND DATE_DIFF('day', b.d, f.app_date) BETWEEN -1 AND 4
),
iss AS (
  SELECT DISTINCT b.mid FROM b JOIN mx.wxs_application_funnel f
    ON CAST(f.mid AS VARCHAR) = b.mid AND f.is_reloan='old' AND f.if_issue=1
   AND f.issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
   AND DATE_DIFF('day', b.d, f.issue_date) BETWEEN -1 AND 4
),
used AS (
  SELECT DISTINCT i.mid FROM (
    SELECT DISTINCT b.mid, CAST(f.biz_id AS VARCHAR) AS biz_v
    FROM b JOIN mx.wxs_application_funnel f
      ON CAST(f.mid AS VARCHAR) = b.mid AND f.is_reloan='old' AND f.if_issue=1
     AND f.issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
     AND DATE_DIFF('day', b.d, f.issue_date) BETWEEN -1 AND 4
  ) i JOIN mx.yj_asset_quota_v10 q ON CAST(q.biz_id AS VARCHAR) = i.biz_v
  WHERE q.offline_used_this > 0.05
)
SELECT '1_发了但没进件'   AS seg,
       CAST((SELECT COUNT(1) FROM bm) - (SELECT COUNT(1) FROM app) AS DOUBLE) AS mid_n
UNION ALL
SELECT '2_进件了但没放款',
       CAST((SELECT COUNT(1) FROM app) - (SELECT COUNT(1) FROM iss) AS DOUBLE)
UNION ALL
SELECT '3_放款了但没用临额',
       CAST((SELECT COUNT(1) FROM iss) - (SELECT COUNT(1) FROM used) AS DOUBLE)
UNION ALL
SELECT '4_用上了', CAST((SELECT COUNT(1) FROM used) AS DOUBLE)
UNION ALL
SELECT '0_发放总人数', CAST((SELECT COUNT(1) FROM bm) AS DOUBLE)
ORDER BY 1;


-- ══════════════════════════════════════════════════════════════════════
-- Q5  离线业绩视角覆盖率（分母 = 全量进件 / 全量放款）
-- ══════════════════════════════════════════════════════════════════════
WITH b AS (
  SELECT CAST(y.mid AS VARCHAR) AS mid,
         CAST(date_parse(y.data_date,'%Y%m%d') AS DATE) AS d
  FROM mx.yuhan_temp_limit_base_table_his_20260924 y
  WHERE y.data_date BETWEEN '20260901' AND '20261021'
    AND y.temp_limit_issue_amount IS NOT NULL
    AND CAST(y.temp_limit_issue_amount AS DOUBLE) > 0
    AND y.temp_limit_tag LIKE '%临额%' AND y.temp_limit_tag NOT LIKE '%对照组%'
),
allapp AS (
  SELECT CAST(f.biz_id AS VARCHAR) AS biz_v, CAST(f.mid AS VARCHAR) AS mid, f.app_date
  FROM mx.wxs_application_funnel f
  WHERE f.is_reloan='old' AND f.app_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
),
cov_app AS (
  SELECT DISTINCT a.biz_v FROM allapp a
  JOIN b ON b.mid = a.mid AND DATE_DIFF('day', b.d, a.app_date) BETWEEN -1 AND 4
),
alliss AS (
  SELECT CAST(f.biz_id AS VARCHAR) AS biz_v, CAST(f.mid AS VARCHAR) AS mid, f.issue_date,
         CAST(f.contract_amount AS DOUBLE) AS contract_amount
  FROM mx.wxs_application_funnel f
  WHERE f.is_reloan='old' AND f.if_issue=1
    AND f.issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
),
cov_iss AS (
  SELECT DISTINCT a.biz_v FROM alliss a
  JOIN b ON b.mid = a.mid AND DATE_DIFF('day', b.d, a.issue_date) BETWEEN -1 AND 4
)
SELECT '1_全部进件笔'   AS metric, CAST((SELECT COUNT(DISTINCT biz_v) FROM allapp) AS DOUBLE) AS val
UNION ALL SELECT '2_覆盖进件笔', CAST((SELECT COUNT(1) FROM cov_app) AS DOUBLE)
UNION ALL SELECT '3_全部放款笔', CAST((SELECT COUNT(DISTINCT biz_v) FROM alliss) AS DOUBLE)
UNION ALL SELECT '4_覆盖放款笔', CAST((SELECT COUNT(1) FROM cov_iss) AS DOUBLE)
UNION ALL SELECT '5_全部放款额', CAST((SELECT SUM(contract_amount) FROM alliss) AS DOUBLE)
UNION ALL SELECT '6_覆盖放款额',
  CAST((SELECT SUM(a.contract_amount) FROM alliss a
        WHERE a.biz_v IN (SELECT biz_v FROM cov_iss)) AS DOUBLE)
ORDER BY 1;


-- ══════════════════════════════════════════════════════════════════════
-- Q6  在线漏斗（笔级；在线没有"人级发放"这一层，弹窗发生在用信链路里）
-- ══════════════════════════════════════════════════════════════════════
SELECT '1_全部放款笔'     AS metric, CAST(COUNT(1) AS DOUBLE) AS val FROM mx.yj_asset_quota_v10
WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '2_全部放款额', SUM(contract_amount) FROM mx.yj_asset_quota_v10
WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '3_弹窗发放笔', CAST(SUM(CASE WHEN online_grant_flag=1 AND online_grant_amount>0
                                     THEN 1 ELSE 0 END) AS DOUBLE)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '4_弹窗发放额', SUM(CASE WHEN online_grant_flag=1 AND online_grant_amount>0
                                THEN online_grant_amount ELSE 0 END)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '5_领取笔', CAST(SUM(CASE WHEN online_used_this>0.05 THEN 1 ELSE 0 END) AS DOUBLE)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '6_领取额', SUM(online_used_this) FROM mx.yj_asset_quota_v10
WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '7_未领取笔', CAST(SUM(CASE WHEN online_grant_flag=1 AND online_grant_amount>0
                                   AND online_used_this<=0.05 THEN 1 ELSE 0 END) AS DOUBLE)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '8_未领取额', SUM(CASE WHEN online_grant_flag=1 AND online_grant_amount>0
                              AND online_used_this<=0.05 THEN online_grant_amount ELSE 0 END)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '9_领取笔的合同额', SUM(CASE WHEN online_used_this>0.05 THEN contract_amount ELSE 0 END)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
ORDER BY 1;


-- ══════════════════════════════════════════════════════════════════════
-- Q7  业绩占比两口径 + 件均对照
--   口径A 直接贡献 = 临额使用额 / 全部放款额        → 回答"临额多放了多少钱"
--   口径B 覆盖业绩 = 用了临额的笔的合同额 / 全部放款额 → 回答"多大比例业绩与临额有关"
--   ⚠️ 件均差异是相关不是因果（选择效应），要量化真实增信需用 1021 对照组做 DID
-- ══════════════════════════════════════════════════════════════════════
SELECT metric, val FROM (
  SELECT '01_全部放款笔'  AS metric, CAST(COUNT(1) AS DOUBLE) AS val FROM mx.yj_asset_quota_v10
   WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
  UNION ALL SELECT '02_全部放款额', SUM(contract_amount) FROM mx.yj_asset_quota_v10
   WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
  UNION ALL SELECT '03_A_离线使用额', SUM(offline_used_this) FROM mx.yj_asset_quota_v10
   WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
  UNION ALL SELECT '04_A_在线使用额', SUM(online_used_this) FROM mx.yj_asset_quota_v10
   WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
  UNION ALL SELECT '05_A_unknown使用额', SUM(unknown_used_this) FROM mx.yj_asset_quota_v10
   WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
  UNION ALL SELECT '06_A_临额使用额合计',
            SUM(offline_used_this + online_used_this + unknown_used_this)
   FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
  UNION ALL SELECT '07_B_离线覆盖合同额',
            SUM(CASE WHEN offline_used_this>0.05 THEN contract_amount ELSE 0 END)
   FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
  UNION ALL SELECT '08_B_在线覆盖合同额',
            SUM(CASE WHEN online_used_this>0.05 THEN contract_amount ELSE 0 END)
   FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
  UNION ALL SELECT '09_B_临额覆盖合同额合计',
            SUM(CASE WHEN offline_used_this+online_used_this+unknown_used_this>0.05
                     THEN contract_amount ELSE 0 END)
   FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
  UNION ALL SELECT '10_用临额笔数',
            CAST(SUM(CASE WHEN offline_used_this+online_used_this+unknown_used_this>0.05
                          THEN 1 ELSE 0 END) AS DOUBLE)
   FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
  UNION ALL SELECT '11_件均_用临额',
            AVG(CASE WHEN offline_used_this+online_used_this+unknown_used_this>0.05
                     THEN contract_amount END)
   FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
  UNION ALL SELECT '12_件均_没用临额',
            AVG(CASE WHEN offline_used_this+online_used_this+unknown_used_this<=0.05
                     THEN contract_amount END)
   FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
) t ORDER BY metric;


-- ══════════════════════════════════════════════════════════════════════
-- Q8  放款笔层面：持有离线额度但没用（第③层流失的金额侧）
-- 【v8】改用 holds_offline 判「持有」：v8 的 offline_grant 已内置
--   「有效期 5 天 + 只留真发放组」过滤，所以不必再写 age 条件，口径也自动与 Q3/Q4 对齐。
--   「沉淀的离线可用额度」= 用信决策**之前**账户里真实可用的离线额度
--   （v5 口径只对「本笔用了离线」的笔算，严重低估）
-- ══════════════════════════════════════════════════════════════════════
SELECT '1_持有未过期离线额度_笔' AS metric,
       CAST(SUM(CASE WHEN holds_offline = 1 THEN 1 ELSE 0 END) AS DOUBLE) AS val
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '2_其中用了_笔', CAST(SUM(CASE WHEN holds_offline = 1 AND offline_used_this>0.05
       THEN 1 ELSE 0 END) AS DOUBLE)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '3_其中没用_笔', CAST(SUM(CASE WHEN holds_offline = 1 AND offline_used_this<=0.05
       THEN 1 ELSE 0 END) AS DOUBLE)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '4_没用的这批笔_自己的合同额', SUM(CASE WHEN holds_offline = 1 AND offline_used_this<=0.05
       THEN contract_amount ELSE 0 END)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
-- ⚠️⚠️【v10 关键修正】「沉淀的离线可用额度」必须按 (mid, 批次) 去重后再加总。
--   离线临额是**账户级(mid)**事实：同一 mid 在 5 天有效期内放多笔，
--   同一批额度会在宽表的每一行各记一次。v9 实测逐行 SUM 虚增 44.7%。
--   所以这里加 offline_batch_seq = 1 只取每个批次的第一笔作代表。
SELECT '5_沉淀的离线可用额度_去重', SUM(CASE WHEN offline_batch_seq = 1
       THEN offline_available_amount ELSE 0 END)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
-- 逐行版保留作对照：两者之差就是重复计账量，别拿这个数去汇报
SELECT '5b_沉淀的离线可用额度_逐行(勿用)', SUM(offline_available_amount)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
-- ⚠️【v10 修正】超期判据从 age > 4 改成 age > 5。
--   v9 的 offline_grant_age_days 用 yuhan.data_date 算，因 data_date 相对实际发放日
--   有 +0/+1/+2 三种偏移而恒偏小约 1 天、取值域被压在 [-1,4]，> 4 实际上永不成立。
--   v10 改用台账 C015/C013 的真实发放时刻，取值域 [0,5]，其中 5 = 到期当日**仍然有效**，
--   所以"超期"的门槛是 > 5。
SELECT '6_超期仍使用_笔', CAST(SUM(CASE WHEN offline_used_this>0.05
       AND offline_grant_age_days>5 THEN 1 ELSE 0 END) AS DOUBLE)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '7_超期仍使用_额', SUM(CASE WHEN offline_used_this>0.05
       AND offline_grant_age_days>5 THEN offline_used_this ELSE 0 END)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
-- 【v10 新增】剩余有效期分档（资金效率衰减用），口径与 v3 宽表的 offline_expire_days 一致
SELECT '8_持有分档_剩余5天_笔', CAST(SUM(CASE WHEN holds_offline=1 AND offline_expire_days=5
       THEN 1 ELSE 0 END) AS DOUBLE)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
UNION ALL
SELECT '9_持有分档_剩余0天(到期当日)_笔', CAST(SUM(CASE WHEN holds_offline=1
       AND offline_expire_days=0 THEN 1 ELSE 0 END) AS DOUBLE)
FROM mx.yj_asset_quota_v10 WHERE issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
ORDER BY 1;


-- ══════════════════════════════════════════════════════════════════════
-- Q9（可选）把 mid 级漏斗落成一张宽表，方便反复下钻
--     跑完后 SELECT * FROM mx.yj_temp_funnel_mid 即可，不用每次重算
-- ══════════════════════════════════════════════════════════════════════
/*
DROP TABLE IF EXISTS mx.yj_temp_funnel_mid;
CREATE TABLE mx.yj_temp_funnel_mid AS
WITH b AS (
  SELECT CAST(y.mid AS VARCHAR) AS mid,
         CAST(date_parse(y.data_date,'%Y%m%d') AS DATE) AS d,
         CAST(y.temp_limit_issue_amount AS DOUBLE) AS amt,
         y.temp_limit_tag AS tag
  FROM mx.yuhan_temp_limit_base_table_his_20260924 y
  WHERE y.data_date BETWEEN '20260901' AND '20261021'
    AND y.temp_limit_issue_amount IS NOT NULL
    AND CAST(y.temp_limit_issue_amount AS DOUBLE) > 0
    AND y.temp_limit_tag LIKE '%临额%' AND y.temp_limit_tag NOT LIKE '%对照组%'
),
bm AS (
  SELECT mid, COUNT(1) AS grant_times, SUM(amt) AS grant_amt,
         MAX(d) AS last_grant_date, MAX_BY(tag, d) AS last_tag
  FROM b GROUP BY 1
),
app AS (
  SELECT b.mid, COUNT(DISTINCT CAST(f.biz_id AS VARCHAR)) AS app_biz
  FROM b JOIN mx.wxs_application_funnel f
    ON CAST(f.mid AS VARCHAR) = b.mid AND f.is_reloan='old'
   AND f.app_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
   AND DATE_DIFF('day', b.d, f.app_date) BETWEEN -1 AND 4
  GROUP BY 1
),
iss AS (
  SELECT b.mid, COUNT(DISTINCT CAST(f.biz_id AS VARCHAR)) AS iss_biz,
         SUM(CAST(f.contract_amount AS DOUBLE)) AS iss_amt
  FROM b JOIN mx.wxs_application_funnel f
    ON CAST(f.mid AS VARCHAR) = b.mid AND f.is_reloan='old' AND f.if_issue=1
   AND f.issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
   AND DATE_DIFF('day', b.d, f.issue_date) BETWEEN -1 AND 4
  GROUP BY 1
),
used AS (
  SELECT i.mid, COUNT(DISTINCT i.biz_v) AS used_biz, SUM(q.offline_used_this) AS used_amt
  FROM (
    SELECT DISTINCT b.mid, CAST(f.biz_id AS VARCHAR) AS biz_v
    FROM b JOIN mx.wxs_application_funnel f
      ON CAST(f.mid AS VARCHAR) = b.mid AND f.is_reloan='old' AND f.if_issue=1
     AND f.issue_date BETWEEN DATE '2026-09-01' AND DATE '2026-10-21'
     AND DATE_DIFF('day', b.d, f.issue_date) BETWEEN -1 AND 4
  ) i JOIN mx.yj_asset_quota_v10 q ON CAST(q.biz_id AS VARCHAR) = i.biz_v
  WHERE q.offline_used_this > 0.05
  GROUP BY 1
)
SELECT bm.mid, bm.grant_times, bm.grant_amt, bm.last_grant_date, bm.last_tag,
       COALESCE(app.app_biz,0) AS app_biz,
       COALESCE(iss.iss_biz,0) AS iss_biz, COALESCE(iss.iss_amt,0) AS iss_amt,
       COALESCE(used.used_biz,0) AS used_biz, COALESCE(used.used_amt,0) AS used_amt,
       CASE WHEN COALESCE(used.used_biz,0) > 0 THEN '4_用上了'
            WHEN COALESCE(iss.iss_biz,0)  > 0 THEN '3_放款了但没用临额'
            WHEN COALESCE(app.app_biz,0)  > 0 THEN '2_进件了但没放款'
            ELSE '1_发了但没进件' END AS funnel_stage
FROM bm
LEFT JOIN app  ON app.mid  = bm.mid
LEFT JOIN iss  ON iss.mid  = bm.mid
LEFT JOIN used ON used.mid = bm.mid;
*/


-- ======================================================================
-- 【待办，等报告出完回来做】
--   TODO-1 修 v5 的 offline_grant 口径：CTE 加
--          AND y.temp_limit_tag LIKE '%临额%' AND y.temp_limit_tag NOT LIKE '%对照组%'
--          影响：只在减息组出现过的 mid 若用了临额，现在会被误判成 offline 而非 unknown
--          （当前 unknown 183 笔，修后会增加）。岳松 2026-10-23 确认影响不大、先不动
--   TODO-2 下钻第一层流失那 3,236 人（发了额度但没进件，占发放 28.9%，最大改进空间）
--          看距上次借款天数、还款表现、是否有推送触达 —— 区分"圈错人"还是"没触达到"
--   TODO-3 用 1021 批次的灰度对照组做 DID，把"用临额件均 +71.7%"里的真实增量量化出来
--          该对照组已验证是"圈了不发"（C015 命中率 0.7%），是干净的对照
-- ======================================================================
