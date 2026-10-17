-- ============================================================================
-- 离线临额效果分析（C015口径）完整校验SQL
-- ============================================================================
-- 【机制层：事件码语义】（已与业务确认）
--   C015 = 手动圈选客群的离线临额推送（主力通道）
--          - create_time 精确到秒，批次日20:00:00统一下发
--          - external_id = 'mid_时间戳'，可逐笔追踪
--          - change_total_grantamount = 本次发放临额金额（比索）
--   C013 = 开发手动调整通道：4月早期批次(0407/0414/0415/0417/0520) + 9月出错修单(0909/0917)
--          - external_id 为空
--   C010 = 在线临额（用户进件时自助领取），external_id=进件biz_id
--   C014 = 不存在（临额到期/回收无事件），故暴露窗口用"发放后7天"近似
--
-- 【底表】mx.yuhan_temp_limit_base_table_his_20260924（52个批次，4/22~10/15）
--   - load_time = 批次执行时间（比data_date早1天）= C015事件日
--   - temp_limit_issue_date = 用户【历史首次】获临额时间，非本次发放时间，勿用作基准日
--   - 批次结构：周一/周三=有在贷批（tag后缀_1/_2/_3=按主额分档的金额档，非随机）
--              周二/周四=无在贷批（临额/减息/临额减息 三臂，已验证随机平衡）
--
-- 【验证过的关键事实】
--   1. 批次mid与C015/C013事件100%匹配（减息组不发临额→0%覆盖，符合预期）
--   2. 无在贷三臂平衡：主额4084/4091/4157，前7天申请率56.4/56.2/56.4 → 随机分组成立
--   3. 有在贷_1/_2/_3档按主额分层（2104/3466/5677），非随机，臂间不可直接比
--   4. 每周重复推送 → 前后对比的pre窗口=上一批post窗口，6月起前后对比失效
--      干净设计只有：无在贷RCT臂间对比 + 首次被推送用户前后对比
-- ============================================================================


-- ============================================================================
-- Q0【机制验证】C015/C013/C010 每日事件量 + 分臂覆盖率
-- 校验点：C015日期与批次load_time对齐；减息组覆盖率=0
-- ============================================================================
SELECT date_trunc('day', create_time) AS dt, change_event_type,
       COUNT(*) AS cnt, COUNT(DISTINCT mid) AS mid_cnt
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE change_event_type IN ('C015','C013','C010')
  AND create_time >= timestamp'2026-04-01 00:00:00'
  AND create_time <  timestamp'2026-10-16 00:00:00'
GROUP BY 1, 2
ORDER BY 1, 2;

-- 分臂覆盖率（减息组应=0）
WITH grants AS (
  SELECT mid, MAX(create_time) AS grant_time, MAX(change_total_grantamount) AS grant_amt
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-04-01 00:00:00'
    AND create_time <  timestamp'2026-10-16 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
),
offline AS (
  SELECT mid, data_date, temp_limit_tag,
         date_trunc('day', load_time) AS base_dt
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260923','20260924','20260930','20261001',
                      '20261007','20261008','20261014','20261015')
)
SELECT o.data_date, o.temp_limit_tag,
       COUNT(DISTINCT o.mid) AS cnt,
       round(100.0*COUNT(DISTINCT CASE WHEN g.mid IS NOT NULL THEN o.mid END)
             /COUNT(DISTINCT o.mid),1) AS c015_cover_pct,
       round(AVG(g.grant_amt),0) AS avg_grant_amt
FROM offline o
LEFT JOIN grants g ON cast(o.mid as bigint)=cast(g.mid as bigint)
  AND g.grant_time >= o.base_dt AND g.grant_time < date_add('day',2,o.base_dt)
GROUP BY 1, 2
ORDER BY 1, 2;


-- ============================================================================
-- Q1【分离层】全部老客申请四分类（核心CTE，后续所有分析复用）
--   1_纯离线：申请时点在C015/C013发放后7天内，且本笔未领在线临额
--   2_纯在线：本笔领了在线临额(temp_grant_amount>0)，无离线暴露
--   3_混合  ：离线暴露+本笔在线临额
--   4_无临额：两者皆无
-- 校验点：分组规模、放款率、件均的月度走势
-- ============================================================================
WITH grants AS (
  SELECT mid, MAX(create_time) AS grant_time
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-04-01 00:00:00'
    AND create_time <  timestamp'2026-10-16 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
),
app AS (
  SELECT mid, app_time, app_date, if_sx_passed, if_issue, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-01' AND app_date < date'2026-10-16'
),
off_exp AS (   -- 申请时点处于离线发放后7天暴露窗内（半连接去重防行膨胀）
  SELECT DISTINCT cast(a.mid as bigint) AS mid, a.app_time
  FROM app a
  JOIN grants g ON cast(a.mid as bigint)=cast(g.mid as bigint)
    AND g.grant_time <= a.app_time AND a.app_time < g.grant_time + interval '7' day
),
cls AS (
  SELECT a.app_date, a.if_issue, a.contract_amount,
         CASE
           WHEN o.mid IS NOT NULL AND a.temp_grant_amount > 0 THEN '3_混合(离线+在线)'
           WHEN o.mid IS NOT NULL THEN '1_纯离线'
           WHEN a.temp_grant_amount > 0 THEN '2_纯在线'
           ELSE '4_无临额'
         END AS grp
  FROM app a
  LEFT JOIN off_exp o ON cast(a.mid as bigint)=o.mid AND a.app_time=o.app_time
)
SELECT date_format(app_date,'%Y-%m') AS app_month, grp,
       COUNT(*) AS app_cnt,
       round(100.0*SUM(if_issue)/COUNT(*),2) AS issue_rate,
       round(AVG(CASE WHEN if_issue=1 THEN contract_amount END),0) AS avg_contract
FROM cls
GROUP BY 1, 2
ORDER BY 1, 2;


-- ============================================================================
-- Q2【因果核心①】无在贷批次 三臂RCT（全量4-10月）
-- 逻辑：三臂已验证随机平衡 → 臂间差异=处理效应
--       临额 vs 减息 = 临额的边际效果（相对减息推送）
-- 结论：申请率+1.4pp、放款率+1.0pp、合同件均+8.5%
-- ============================================================================
WITH offline AS (
  SELECT mid, curr_main_credit_limit,
         date_trunc('day', load_time) AS base_dt,
         CASE
           WHEN temp_limit_tag LIKE '%临额减息%' THEN '3_临额+减息'
           WHEN temp_limit_tag LIKE '%减息%'     THEN '2_减息(对照:无临额)'
           ELSE '1_临额' END AS arm
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE temp_limit_tag LIKE '%无在贷%'
),
app AS (
  SELECT mid, app_date, if_sx_passed, if_issue, contract_amount, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-01' AND app_date < date'2026-10-16'
)
SELECT o.arm,
       COUNT(DISTINCT o.mid) AS mid_cnt,
       round(AVG(o.curr_main_credit_limit),0) AS avg_main_limit,
       round(100.0*COUNT(DISTINCT CASE WHEN ap.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_apply_rate,
       round(100.0*COUNT(DISTINCT CASE WHEN aq.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_apply_rate,
       round(100.0*COUNT(DISTINCT CASE WHEN aq.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_issue_rate,
       round(AVG(CASE WHEN aq.if_issue=1 THEN aq.contract_amount END),0) AS avg_contract
FROM offline o
LEFT JOIN app ap ON cast(o.mid as bigint)=cast(ap.mid as bigint)
  AND ap.app_date >= date_add('day',-7,o.base_dt) AND ap.app_date < o.base_dt
LEFT JOIN app aq ON cast(o.mid as bigint)=cast(aq.mid as bigint)
  AND aq.app_date >= o.base_dt AND aq.app_date < date_add('day',7,o.base_dt)
GROUP BY 1 ORDER BY 1;


-- ============================================================================
-- Q3【因果核心②】首次被推送用户前后对比
-- 逻辑：首次推送用户的pre窗口无历史推送污染，是最干净的前后对比
--       （注意：圈选本身偏向近期活跃户，pre绝对值偏高，臂间对比仍有效）
-- 结论(有在贷)：率持平、件均+11~13%；(无在贷RCT)：临额比减息申请+1.8pp、放款+1.5pp
-- ============================================================================
WITH first_push AS (
  SELECT mid, MIN(data_date) AS first_date
  FROM mx.yuhan_temp_limit_base_table_his_20260924 GROUP BY mid
),
offline AS (   -- 有在贷版：分档；无在贷版：改 LIKE '%无在贷%' + 分臂CASE
  SELECT o.mid, o.temp_limit_issue_amount, o.curr_main_credit_limit,
         date_trunc('day', o.load_time) AS base_dt,
         CASE substr(o.temp_limit_tag,-2)
           WHEN '_1' THEN '1_小额档(~450)'
           WHEN '_2' THEN '2_中额档(~1700)'
           WHEN '_3' THEN '3_大额档(~4800)'
           ELSE '9_其他' END AS tier
  FROM mx.yuhan_temp_limit_base_table_his_20260924 o
  JOIN first_push f ON cast(o.mid as bigint)=cast(f.mid as bigint) AND o.data_date=f.first_date
  WHERE o.temp_limit_tag LIKE '%有在贷%'
),
app AS (
  SELECT mid, app_date, if_issue, contract_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-01' AND app_date < date'2026-10-16'
)
SELECT o.tier,
       COUNT(DISTINCT o.mid) AS mid_cnt,
       round(AVG(o.curr_main_credit_limit),0) AS avg_main,
       round(AVG(o.temp_limit_issue_amount),0) AS avg_temp,
       round(100.0*COUNT(DISTINCT CASE WHEN ap.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_apply,
       round(100.0*COUNT(DISTINCT CASE WHEN ap.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS pre7d_issue,
       round(100.0*COUNT(DISTINCT CASE WHEN aq.mid IS NOT NULL THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_apply,
       round(100.0*COUNT(DISTINCT CASE WHEN aq.if_issue=1 THEN o.mid END)/COUNT(DISTINCT o.mid),2) AS post7d_issue,
       round(AVG(CASE WHEN ap.if_issue=1 THEN ap.contract_amount END),0) AS pre_contract,
       round(AVG(CASE WHEN aq.if_issue=1 THEN aq.contract_amount END),0) AS post_contract
FROM offline o
LEFT JOIN app ap ON cast(o.mid as bigint)=cast(ap.mid as bigint)
  AND ap.app_date >= date_add('day',-7,o.base_dt) AND ap.app_date < o.base_dt
LEFT JOIN app aq ON cast(o.mid as bigint)=cast(aq.mid as bigint)
  AND aq.app_date >= o.base_dt AND aq.app_date < date_add('day',7,o.base_dt)
WHERE o.tier <> '9_其他'
GROUP BY 1 ORDER BY 1;


-- ============================================================================
-- Q4【疲劳度】按被推送序号的后7天响应
-- 结论：无在贷逐次衰减(37.3→31.9→28.3%)；有在贷反升(77→86%，高频户被反复圈选的选择效应)
-- ============================================================================
WITH ranked AS (
  SELECT mid, temp_limit_tag,
         date_trunc('day', load_time) AS base_dt,
         row_number() OVER (PARTITION BY mid ORDER BY data_date) AS push_seq
  FROM mx.yuhan_temp_limit_base_table_his_20260924
),
app AS (
  SELECT mid, app_date, if_issue
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-04-01' AND app_date < date'2026-10-16'
)
SELECT
  CASE WHEN r.temp_limit_tag LIKE '%有在贷%' THEN '有在贷' ELSE '无在贷' END AS crowd,
  CASE WHEN r.push_seq >= 4 THEN '4+' ELSE cast(r.push_seq AS varchar) END AS push_seq,
  COUNT(*) AS obs_cnt,
  round(100.0*SUM(CASE WHEN aq.mid IS NOT NULL THEN 1 ELSE 0 END)/COUNT(*),2) AS post7d_apply_rate,
  round(100.0*SUM(CASE WHEN aq.if_issue=1 THEN 1 ELSE 0 END)/COUNT(*),2) AS post7d_issue_rate
FROM ranked r
LEFT JOIN app aq ON cast(r.mid as bigint)=cast(aq.mid as bigint)
  AND aq.app_date >= r.base_dt AND aq.app_date < date_add('day',7,r.base_dt)
GROUP BY 1, 2 ORDER BY 1, 2;


-- ============================================================================
-- Q5【逾期层】四分类资产质量（4-8月放款，保证2T0账龄）
-- 结论：1T0逾期率 纯离线23.4% < 纯在线29.7% < 混合32.0% < 无临额39.5%
--       混合组(双重加杠杆)逾期显著抬升；分档看临额档越高逾期越低(资质分层)
-- 注意：tr_amt_rate为多期累计口径可超100%，仅作组间相对比较
-- ============================================================================
WITH grants AS (
  SELECT mid, MAX(create_time) AS grant_time, MAX(change_total_grantamount) AS grant_amt
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-04-01 00:00:00'
    AND create_time <  timestamp'2026-09-01 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
),
off_batch AS (
  SELECT mid, temp_limit_tag, date_trunc('day', load_time) AS base_dt
  FROM mx.yuhan_temp_limit_base_table_his_20260924
),
grants2 AS (   -- 事件日期与load_time允许±1天容差（C013修单日可能晚1天）
  SELECT g.mid, g.grant_time, g.grant_amt, ob.temp_limit_tag
  FROM grants g
  LEFT JOIN off_batch ob ON cast(g.mid as bigint)=cast(ob.mid as bigint)
    AND date_trunc('day', g.grant_time) >= ob.base_dt
    AND date_trunc('day', g.grant_time) <= date_add('day',1,ob.base_dt)
),
f AS (
  SELECT mid, app_time, app_date, contract_amount, temp_grant_amount,
         is_t0_overdue_1, is_t0_overdue_2, is_t0_overdue_3, is_t0_overdue_4,
         t0_overdue_amount_1
  FROM mx.report_application_funnel7
  WHERE if_issue = 1 AND app_date >= date'2026-04-01' AND app_date <= date'2026-08-31'
),
exp AS (   -- 多笔发放取最近一笔，带出批次臂标签
  SELECT mid, app_time, temp_limit_tag FROM (
    SELECT cast(f.mid as bigint) AS mid, f.app_time, g.temp_limit_tag,
           row_number() OVER (PARTITION BY cast(f.mid as bigint), f.app_time
                              ORDER BY g.grant_time DESC) AS rn
    FROM f
    JOIN grants2 g ON cast(f.mid as bigint)=cast(g.mid as bigint)
      AND g.grant_time <= f.app_time
      AND f.app_time < g.grant_time + interval '7' day
  ) t WHERE rn = 1
),
cls AS (
  SELECT f.*,
         CASE
           WHEN e.mid IS NOT NULL AND f.temp_grant_amount > 0 THEN '3_混合'
           WHEN e.mid IS NOT NULL THEN '1_纯离线'
           WHEN f.temp_grant_amount > 0 THEN '2_纯在线'
           ELSE '4_无临额'
         END AS grp,
         e.temp_limit_tag
  FROM f LEFT JOIN exp e ON cast(f.mid as bigint)=e.mid AND f.app_time=e.app_time
)
SELECT grp,
       COUNT(*) AS issue_cnt,
       round(AVG(contract_amount),0) AS avg_contract,
       round(100.0*AVG(is_t0_overdue_1),2) AS t0_1_rate,
       round(100.0*AVG(is_t0_overdue_2),2) AS t0_2_rate,
       round(100.0*AVG(greatest(is_t0_overdue_1,is_t0_overdue_2,is_t0_overdue_3,is_t0_overdue_4)),2) AS tr_rate,
       round(100.0*SUM(t0_overdue_amount_1)/SUM(contract_amount),2) AS t0_1_amt_rate
FROM cls
GROUP BY grp
ORDER BY grp;

-- Q5b 纯离线/混合 分档分臂逾期：把上面最后一段 GROUP BY 换成：
-- GROUP BY grp, 分档CASE（见 _p3_overdue2.py / _export_c015.py S7）


-- ============================================================================
-- 【重要修正】实际临额使用量校验 + 修正后的逾期分析
-- ============================================================================
-- 之前Q5的"纯离线"标签是【持有临额】标记，经校验：持有离线临额的用户借款时
-- 84%完全不走临额（主额优先），只有16%实际消耗临额。需用实际使用量重新打标。
--
-- 【使用量来源】ods.s05_user_creditlimit_used_detail
--   change_action='FREEZE_LIMIT' 按 limit_type(MAIN/TEMP) 拆分
--   main_used + temp_used = contract_amount  （99.6~100%精确匹配，核对成立）
-- 【在线临额发放】wxs_application_funnel.temp_grant_amount > 0
-- 【离线临额持有】C015/C013事件在申请前7天内
-- ============================================================================

-- Q6【校验】main_used + temp_used 是否 = 合同额
WITH freeze AS (
  SELECT biz_id,
         SUM(CASE WHEN limit_type='MAIN' THEN risk_credit_limit ELSE 0 END) AS main_used,
         SUM(CASE WHEN limit_type='TEMP' THEN risk_credit_limit ELSE 0 END) AS temp_used
  FROM ods.s05_user_creditlimit_used_detail
  WHERE change_action='FREEZE_LIMIT'
    AND create_time >= timestamp'2026-09-01 00:00:00'
  GROUP BY biz_id
)
SELECT
  CASE
    WHEN temp_used = 0 THEN '0_未用临额'
    WHEN temp_used <= 500 THEN '1_<=500'
    WHEN temp_used <= 1000 THEN '2_500~1k'
    WHEN temp_used <= 2000 THEN '3_1k~2k'
    ELSE '4_>2k'
  END AS bucket,
  COUNT(*) AS cnt,
  round(100.0*SUM(CASE WHEN ABS(main_used + temp_used - contract_amount) < 1 THEN 1 ELSE 0 END)/COUNT(*),2) AS exact_match_pct
FROM mx.wxs_application_funnel a
JOIN freeze f ON cast(a.biz_id as bigint) = f.biz_id
WHERE a.tenant='yawey' AND a.if_issue=1
  AND a.app_date >= date'2026-09-01' AND a.app_date < date'2026-10-16'
GROUP BY 1 ORDER BY 1;

-- Q7【修正后】真实四分类逾期（按实际使用量）
-- B_纯离线使用=0笔（系统主额优先，离线临额几乎不被单独消耗）
WITH grants AS (
  SELECT mid, MAX(create_time) AS grant_time
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type IN ('C015','C013')
    AND create_time >= timestamp'2026-04-01 00:00:00'
    AND create_time <  timestamp'2026-09-01 00:00:00'
  GROUP BY mid, date_trunc('day', create_time)
),
freeze AS (
  SELECT biz_id,
         SUM(CASE WHEN limit_type='MAIN' THEN risk_credit_limit ELSE 0 END) AS main_used,
         SUM(CASE WHEN limit_type='TEMP' THEN risk_credit_limit ELSE 0 END) AS temp_used
  FROM ods.s05_user_creditlimit_used_detail
  WHERE change_action='FREEZE_LIMIT'
    AND create_time >= timestamp'2026-04-01 00:00:00'
  GROUP BY biz_id
),
app AS (
  SELECT a.mid, a.biz_id, a.app_time, a.app_date, a.contract_amount, a.temp_grant_amount,
         f.is_t0_overdue_1, f.is_t0_overdue_2, f.is_t0_overdue_3, f.is_t0_overdue_4,
         f.t0_overdue_amount_1,
         CASE WHEN g.mid IS NOT NULL THEN 1 ELSE 0 END AS has_offline
  FROM mx.wxs_application_funnel a
  JOIN mx.report_application_funnel7 f
    ON cast(a.mid as bigint)=cast(f.mid as bigint) AND a.app_time = f.app_time
  LEFT JOIN grants g ON cast(a.mid as bigint)=cast(g.mid as bigint)
    AND g.grant_time <= a.app_time AND a.app_time < g.grant_time + interval '7' day
  WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
    AND a.app_date >= date'2026-04-01' AND a.app_date <= date'2026-08-31'
),
cls AS (
  SELECT a.*, fr.temp_used, fr.main_used,
    CASE
      WHEN fr.temp_used > 0 AND a.temp_grant_amount > 0 AND a.has_offline=1 THEN 'D_混合'
      WHEN fr.temp_used > 0 AND a.temp_grant_amount > 0 THEN 'C_纯在线使用'
      WHEN fr.temp_used > 0 AND a.temp_grant_amount = 0 THEN 'B_纯离线使用'
      ELSE 'A_未使用临额'
    END AS real_grp
  FROM app a
  JOIN freeze fr ON cast(a.biz_id as bigint) = fr.biz_id
)
SELECT real_grp,
       COUNT(*) AS issue_cnt,
       round(AVG(contract_amount),0) AS avg_contract,
       round(AVG(temp_used),0) AS avg_temp_used,
       round(100.0*AVG(is_t0_overdue_1),2) AS t0_1_rate,
       round(100.0*AVG(is_t0_overdue_2),2) AS t0_2_rate,
       round(100.0*AVG(greatest(is_t0_overdue_1,is_t0_overdue_2,is_t0_overdue_3,is_t0_overdue_4)),2) AS tr_rate,
       round(100.0*SUM(t0_overdue_amount_1)/SUM(contract_amount),2) AS t0_1_amt_rate
FROM cls
GROUP BY 1 ORDER BY 1;

-- Q8【已作废】持有离线 × 是否实际使用 交叉逾期
-- Q5~Q8均建立在"temp_grant_amount>0 = 在线临额"的错误假设上。
-- Q9语义验证证明 temp_grant_amount 是【本笔实际使用的临额】(不分来源),
-- 故Q7的"C_纯在线使用"里混入了5344笔离线池使用, 结论作废, 以Q10/Q11为准。


-- ============================================================================
-- 【最终方案】双字段/三金额打标 + 与官方8批次标签交叉验证
-- ============================================================================
-- 三个金额字段(每笔放款独立给出, 不再用混合单标签):
--   online_grant  = C010事件(external_id=biz_id) change_total_grantamount
--                   进件时实时领取的在线临额(领即用, 99.7%当笔冻结)
--   offline_grant = 申请前7天内最近一笔C015/C013的 change_total_grantamount
--                   离线批量推送发放(未领取也在池中, 主额优先消耗)
--   temp_used     = used_detail FREEZE_LIMIT 中 limit_type='TEMP' 的金额
--                   = wxs_application_funnel.temp_grant_amount/1000 (100%恒等)
-- 使用来源判定: temp_used>0 且该biz有C010 -> 在线使用; 无C010 -> 离线池使用
-- ============================================================================

-- Q9【交叉验证1】我的C015精确7天暴露 vs 官方8批次窗口标签(用户SQL口径)
-- 官方口径: load自然日~+5日共6天, 含减息组; 我的口径: C015实际时刻起滚动7天
-- 对账结论(2026-08-18~09-14申请):
--   一致: 临额11193 + 临额减息616 + 双方都无40331
--   官方有/我无1278笔: 全部是申请早于同日20:00 C015实际发放(官方按0点起算)
--   官方有/我无减息1112笔: 减息组不发临额无C015(应排除, 我的口径正确)
--   我有/官方无2665笔: D+5/D+6边界2336笔(6自然日 vs 7天) + C013修单329笔
WITH base AS (
  SELECT mid,
         CASE WHEN temp_limit_tag LIKE '%临额减息%' THEN '临额减息'
              WHEN temp_limit_tag LIKE '%减息%' THEN '减息'
              ELSE '临额' END AS arm, data_date
  FROM mx.yuhan_temp_limit_base_table_his_20260924
  WHERE data_date IN ('20260819','20260820','20260826','20260827',
                      '20260902','20260903','20260909','20260910')
),
app AS (
  SELECT mid, biz_id, app_time, app_date FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old'
    AND app_date >= date'2026-08-18' AND app_date <= date'2026-09-14'
),
official AS (
  SELECT a.mid, a.biz_id, a.app_time, b.arm
  FROM app a JOIN base b ON cast(a.mid as bigint)=cast(b.mid as bigint)
  WHERE (b.data_date='20260819' AND a.app_date BETWEEN date'2026-08-18' AND date'2026-08-23')
     OR (b.data_date='20260820' AND a.app_date BETWEEN date'2026-08-19' AND date'2026-08-24')
     OR (b.data_date='20260826' AND a.app_date BETWEEN date'2026-08-25' AND date'2026-08-30')
     OR (b.data_date='20260827' AND a.app_date BETWEEN date'2026-08-26' AND date'2026-08-31')
     OR (b.data_date='20260902' AND a.app_date BETWEEN date'2026-09-01' AND date'2026-09-06')
     OR (b.data_date='20260903' AND a.app_date BETWEEN date'2026-09-02' AND date'2026-09-07')
     OR (b.data_date='20260909' AND a.app_date BETWEEN date'2026-09-08' AND date'2026-09-13')
     OR (b.data_date='20260910' AND a.app_date BETWEEN date'2026-09-09' AND date'2026-09-14')
),
mine AS (
  SELECT DISTINCT cast(a.mid as bigint) AS mid, a.app_time
  FROM app a
  JOIN ods_view_presto.s05_user_creditlimit_change_record g
    ON cast(a.mid as bigint)=cast(g.mid as bigint)
   AND g.change_event_type IN ('C015','C013')
   AND g.create_time <= a.app_time
   AND a.app_time < g.create_time + interval '7' day
  WHERE g.create_time >= timestamp'2026-08-18 00:00:00'
    AND g.create_time <  timestamp'2026-09-15 00:00:00'
)
SELECT CASE WHEN o.biz_id IS NOT NULL THEN '官方有标签' ELSE '官方无标签' END AS official_flag,
       CASE WHEN m.mid IS NOT NULL THEN '我的C015暴露' ELSE '我未标暴露' END AS mine_flag,
       o.arm, COUNT(*) AS app_cnt
FROM app a
LEFT JOIN official o ON cast(a.mid as bigint)=cast(o.mid as bigint) AND a.app_time=o.app_time
LEFT JOIN mine m ON cast(a.mid as bigint)=m.mid AND a.app_time=m.app_time
GROUP BY 1,2,o.arm ORDER BY 1,2,o.arm;

-- Q10【语义铁证】temp_grant_amount = 实际TEMP冻结额(11624笔100%相等)
--   有C010的放款: 99.7% temp_grant_amount = C010金额
--   无C010但temp_grant_amount>0的5376笔: 5344笔(99.4%)在C015发放后7天内,
--   且91.7%使用额<=离线发放额 -> 证明消耗的是离线临额池
WITH freeze AS (
  SELECT biz_id, SUM(CASE WHEN limit_type='TEMP' THEN risk_credit_limit ELSE 0 END) AS temp_used
  FROM ods.s05_user_creditlimit_used_detail
  WHERE change_action='FREEZE_LIMIT' AND create_time >= timestamp'2026-09-01 00:00:00'
  GROUP BY biz_id
)
SELECT CASE WHEN ABS(a.temp_grant_amount/1000.0 - f.temp_used) < 1 THEN '1_完全相等'
            WHEN ABS(a.temp_grant_amount/1000.0 - f.temp_used) < 50 THEN '2_差<50'
            ELSE '3_差异大' END AS match_level,
       COUNT(*) AS cnt
FROM mx.wxs_application_funnel a
JOIN freeze f ON cast(a.biz_id as bigint)=f.biz_id
WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
  AND a.app_date >= date'2026-09-01' AND a.app_date < date'2026-10-16'
  AND a.temp_grant_amount > 0
GROUP BY 1 ORDER BY 1;

-- Q11【最终口径】持有离线(2) x 使用来源(3) 六格分类: 金额 + 逾期
WITH c010 AS (
  SELECT external_id, MAX(change_total_grantamount) AS online_grant
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C010' AND create_time >= timestamp'2026-04-01 00:00:00'
  GROUP BY external_id
),
off7 AS (   -- 申请前7天内最近一笔离线发放
  SELECT mid, app_time, offline_grant FROM (
    SELECT cast(a.mid as bigint) AS mid, a.app_time,
           g.change_total_grantamount AS offline_grant,
           row_number() OVER (PARTITION BY cast(a.mid as bigint), a.app_time
                              ORDER BY g.create_time DESC) rn
    FROM mx.wxs_application_funnel a
    JOIN ods_view_presto.s05_user_creditlimit_change_record g
      ON cast(a.mid as bigint)=cast(g.mid as bigint)
     AND g.change_event_type IN ('C015','C013')
     AND g.create_time <= a.app_time
     AND a.app_time < g.create_time + interval '7' day
    WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
      AND a.app_date >= date'2026-04-01' AND a.app_date <= date'2026-08-31'
  ) t WHERE rn=1
),
app AS (
  SELECT a.mid, a.biz_id, a.app_time, a.contract_amount,
         a.temp_grant_amount/1000.0 AS temp_used,
         f.is_t0_overdue_1, f.is_t0_overdue_2, f.is_t0_overdue_3, f.is_t0_overdue_4,
         f.t0_overdue_amount_1,
         c.online_grant, o.offline_grant
  FROM mx.wxs_application_funnel a
  JOIN mx.report_application_funnel7 f
    ON cast(a.mid as bigint)=cast(f.mid as bigint) AND a.app_time=f.app_time
  LEFT JOIN c010 c ON cast(a.biz_id as varchar)=c.external_id
  LEFT JOIN off7 o ON cast(a.mid as bigint)=o.mid AND a.app_time=o.app_time
  WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
    AND a.app_date >= date'2026-04-01' AND a.app_date <= date'2026-08-31'
),
cls AS (
  SELECT *,
    CASE WHEN offline_grant IS NOT NULL THEN '持有离线(7d内)' ELSE '未持有离线' END AS hold_offline,
    CASE WHEN temp_used = 0 THEN '0_未使用临额'
         WHEN online_grant IS NOT NULL THEN '1_在线临额使用(C010)'
         ELSE '2_离线临额池使用' END AS use_source
  FROM app
)
SELECT hold_offline, use_source,
       COUNT(*) AS loan_cnt,
       round(AVG(contract_amount),0) AS avg_contract,
       round(AVG(COALESCE(offline_grant,0)),0) AS avg_offline_grant,
       round(AVG(COALESCE(online_grant,0)),0)  AS avg_online_grant,
       round(AVG(temp_used),0) AS avg_temp_used,
       round(100.0*AVG(is_t0_overdue_1),2) AS t0_1_rate,
       round(100.0*AVG(is_t0_overdue_2),2) AS t0_2_rate,
       round(100.0*AVG(greatest(is_t0_overdue_1,is_t0_overdue_2,is_t0_overdue_3,is_t0_overdue_4)),2) AS tr_rate,
       round(100.0*SUM(t0_overdue_amount_1)/SUM(contract_amount),2) AS t0_1_amt_rate
FROM cls
GROUP BY 1, 2 ORDER BY 1, 2;
-- 结果(4-8月放款):
-- 持有离线+未使用      33997笔 件均1511 1T0=23.0%  <- 圈选优质客群, 未加杠杆
-- 持有离线+在线使用     2325笔 件均2536 1T0=25.6%
-- 持有离线+离线池使用  27030笔 件均2038 1T0=32.2%  <- 真正动用离线临额, 杠杆后逾期+9.2pp
-- 未持有离线+未使用      120518笔 件均1126 1T0=33.9%  <- 大盘基线
-- 未持有离线+在线使用     21036笔 件均1832 1T0=30.5%
-- 未持有离线+离线池使用    4483笔 件均2235 1T0=27.4%  <- 7天窗口外历史离线池, 早期优质圈选客


-- ============================================================================
-- 【对账】在线临额 vs mx.yj_test_table_250225(JY-test 老客宽表)
-- ============================================================================
-- 问题: 我建立的"在线临额"口径(C010 by biz_id + funnel.temp_grant_amount)能否与
--       yj表自带字段对上?
-- 结论: ①temp_grant_amount 字段逐笔100%相等 -> 完全对得上;
--       ②但 temp_grant_amount = 实际使用临额(不分来源), 不等于"在线临额";
--       ③yj真正表示在线临额的是 temp_credit_amount_issue_tag(展示层tag);
--          C010(用信层) 与 tag 的差异全部可解释。
-- ============================================================================

-- Q12a【覆盖率】funnel(9/1-10/15复贷放款) 按 biz_id 命中 yj表
-- yj1 = biz_id 去重取最新(rn=1); yj表只有 app_time/app_date, 无 apply_time
WITH yj AS (
  SELECT biz_id, temp_grant_amount AS yj_temp, temp_credit_amount_issue_tag AS issue_tag, app_time, app_date
  FROM mx.yj_test_table_250225
  WHERE is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
yj1 AS (SELECT * FROM (SELECT *, row_number() OVER (PARTITION BY biz_id ORDER BY app_time DESC) rn FROM yj) t WHERE rn=1),
app AS (
  SELECT biz_id, temp_grant_amount AS fn_temp, contract_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
)
SELECT CASE WHEN y.biz_id IS NOT NULL THEN '命中yj表' ELSE '未命中yj表' END AS yj_match,
       COUNT(*) AS funnel_cnt,
       round(100.0*SUM(CASE WHEN a.fn_temp>0 THEN 1 ELSE 0 END)/COUNT(*),2) AS temp_gt0_pct
FROM app a LEFT JOIN yj1 y ON a.biz_id=y.biz_id
GROUP BY 1;
-- 结果: 命中56568(98.4%) / 未命中929; 命中行 temp_grant_amount>0 占20.6%

-- Q12b【字段恒等】funnel.temp_grant_amount vs yj.temp_grant_amount 逐笔
-- (同Q12a的CTE) 
SELECT CASE WHEN a.fn_temp = y.yj_temp THEN '1_完全相等' ELSE '2_不等' END AS match_level,
       COUNT(*) AS cnt, SUM(a.fn_temp/1000.0) AS sum_funnel_peso, SUM(y.yj_temp/1000.0) AS sum_yj_peso
FROM app a JOIN yj1 y ON a.biz_id=y.biz_id
GROUP BY 1;
-- 结果: 56568行 100%完全相等, 两边合计均 = 6,612,708 比索 -> 字段完全对齐

-- Q12c【在线标记对账】我的C010(biz级) × yj.temp_credit_amount_issue_tag
-- c010 = change_record 中 change_event_type='C010' 且 limit_type='TEMP' 的 external_id(=biz_id)
-- (同Q12a的CTE) + c010 CTE
SELECT CASE WHEN c.biz_str IS NOT NULL THEN '我_C010有' ELSE '我_C010无' END AS my_c010,
       CASE WHEN y.issue_tag=1 THEN 'yj_tag=1' WHEN y.issue_tag=0 THEN 'yj_tag=0' ELSE 'yj_tag=null' END AS yj_tag,
       COUNT(*) AS cnt,
       SUM(CASE WHEN a.fn_temp>0 THEN 1 ELSE 0 END) AS temp_used_cnt,
       round(AVG(a.fn_temp/1000.0),2) AS avg_temp_peso
FROM app a JOIN yj1 y ON a.biz_id=y.biz_id
LEFT JOIN c010 c ON cast(a.biz_id as varchar)=c.biz_str
GROUP BY 1,2 ORDER BY 1,2;
-- 结果:
--   我_C010有 & yj_tag=1      6292笔  全部temp_used=6292  474.6比索  <- 两边完全一致(在线临额)
--   我_C010无 & yj_tag=1      7154笔  仅3笔temp_used      0.3比索   <- 弹窗展示但未使用(展示层≠用信层)
--   我_C010无 & yj_tag=0     42199笔  5246笔temp_used      84.1比索  <- tag=0却用了临额=离线池消耗
--   我_C010无 & yj_tag=null    923笔   111笔temp_used      80.9比索
-- 结论: 有C010 <=> 一定 tag=1 且 一定真用了临额(6292/6292); tag 是"展示"层, C010 是"用信"层,
--       tag=1有46%左右未真正使用; tag=0仍用了临额的5246笔正是离线临额池消耗。

-- Q12d【金额对账】整体口径(9/1-10/15复贷放款)
-- 结果: 放款57497笔 / 合同84,221,689; 使用临额合计6,772,915比索
--       其中 我C010口径 3,026,900 / yj_tag=1口径 2,988,480 (差~1.3%, 边界+多笔)
--       使用临额笔数 11,892 -> 在线(C010)6292 + 离线池等其余

