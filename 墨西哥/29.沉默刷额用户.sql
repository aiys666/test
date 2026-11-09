-- ======================================================================
-- 沉默用户固额批刷 · 圈客名单
-- 2026-11-02 | 墨西哥复贷 | 对接《墨西哥复贷离线批量跑批》PRD V0.1
--
-- 【定位】本文件只负责 PRD 职责边界里「策略 / 大数据」那一段：
--         产出跑批名单表 → 跑批系统定时取数 → 调决策流 → 回写额度
--         圈选逻辑不进跑批系统，跑批只按约定表取数（PRD 3.1）
--
-- 【★ 命名规则】
--   ① dws.dws_risk_stgy_apply_mid_tags 原有的字段 —— **一律用原名，不改**
--   ② 新增/派生的字段 —— 英文直译，不起花名
--   ③ PRD 规定的接口字段（biz_type / batch_date / decision_flow_id）—— 用 PRD 的名
--   ⚠️ 主键这里叫 `mid`（原表名），而 PRD 5.1 入参写的是 `customer_id`。
--      保留 mid 是为了和现有临额那套对得上；若跑批系统硬要求列名为 customer_id，
--      请研发侧做字段映射，不要反过来改这边（见文件末 TODO-6）。
--
-- 【与离线临额跑批的关系】骨架完全一致，沿用 27.灰度_离线临额发放.sql 的入池条件，
--   但有三处本质不同：
--     ① 改的是 **MAIN 固额**，不是 TEMP 临额 —— 不可逆，没有"到期自动失效"兜底
--     ② 多了 PRODUCT_CHANGE 业务类型（本期先只做 LIMIT_UP）
--     ③ 频率从每周两批 → 每日凌晨，且无人工导 CSV 环节
--
-- ══════════════════════════════════════════════════════════════════════
-- 【★ 跑数前必读：两个卡点，决定这个需求能不能按原计划做】
--
-- 卡点一：目标客群的主额度 **90.2% 已经过期**
--   合格池 67,140 人（已过入池条件）中：
--     未过期     3,918 人（5.8%）
--     已过期    60,591 人（90.2%）← 失效主额度合计 1.46 亿比索
--     无额度记录 2,631 人（3.9%）
--   其中最大一块「过期>180天 且 沉默>=180天」= 39,476 人，均额 2,762，平均过期 322 天。
--   ⚠️ 若照搬临额的 `curr_main_limit_expire_date > current_date` 条件，
--      67,140 会被砍到 3,918（-94.2%），而且剩下的 3,480 人沉默不足 60 天 ——
--      **这批人根本不叫沉默，需求就失去意义了**。
--   → 所以本 SQL 把"主额度是否过期"从**过滤条件**改成**分层标签**
--      (main_limit_expire_segment)，由决策流按标签走不同分支。
--      ⚠️ 待确认：PRD 的 biz_type 只有 LIMIT_UP / PRODUCT_CHANGE，
--         **"重新授信"属于哪一类、走哪条决策流，目前是空白**。
--
-- 卡点二：V6_1 评级对沉默客群的覆盖率随沉默天数急剧衰减
--   沉默 <60天 覆盖 97.0% ／ 60-179天 29.4% ／ 180-364天 3.3% ／ >=365天 3.3%
--   根因：mx.android_oldcust_maincreditlevel_charge_v6_1_table 是**按申请/用信事件打分**的
--        （312,083 行 / 48,863 mid，人均 6.4 次，2026-08-19 起），
--        **不来申请的人就没有新评级**。
--   名单池 67,140 人里实际能取到的评级：
--        V6_1 10,569 人(15.7%) ／ 旧版快照 29,874 人(44.5%) ／ 无评级 26,697 人(39.8%)
--   → 结构性矛盾：越沉默的人越需要唤醒，也越没有可用评级。
--      本 SQL 用三级兜底（V6_1 → 底表快照 → 无）并把版本落成字段，
--      但**正解是让模型侧对沉默客群离线补跑一次 V6_1 打分**（见配套需求文档）。
--   ⚠️ 绝不可把不同版本的档位混在一个阈值里比较：
--      V5_2 共16档 / V5_3 共13档 / V6_1 共13档 / V4_2 共11档，
--      同一客户三版只有 13% 给出相同档位。**版本必须随值一起透传给决策流**。
--
-- 【其他已知坑，详见 dws_risk_stgy_apply_mid_tags_字段字典.md】
--   · curr_main_credit_limit / daily_max_available_limit 有 **-999 哨兵值**，
--     做算术前必须排除（本 SQL 第②段已排）
--   · app_group 实际 13 个取值，这里只用 3 个 → 覆盖 65.6%，
--     YW(68,606) + TG(65,680) 合计 27.7% 被排除，待确认是否刻意
--   · id_30days_max_overdue_days 有 91.9% 为 NULL，该条件实际只挡掉 23,773 人
--   · load_time 是 T-1 快照（每日 07:00 刷新），非实时
--
-- 【数据源】
--   dws.dws_risk_stgy_apply_mid_tags                      客群底表（mid 级，T-1 快照）
--   mx.android_oldcust_maincreditlevel_charge_v6_1_table  V6_1 评级（事件级，取每人最新一条）
--
-- 【新增派生字段一览】（原表没有的，全部英文直译）
--   silent_days                  沉默天数   = 今天 − last_loan_date
--   silent_days_segment          沉默天数分层
--   main_limit_expired_days      主额度过期天数 = 今天 − curr_main_limit_expire_date（正数=已过期）
--   main_limit_expire_segment    主额度过期分层
--   maincreditlevel_v6_1         V6_1 主资产等级（与给 BI 的新增字段同名）
--   credit_level_final           最终采用的等级 = coalesce(V6_1, curr_credit_level)
--   credit_level_final_version   最终采用的等级对应的版本
--   credit_level_source          等级来源：V6_1 / SNAPSHOT / NONE
--   main_limit_refresh_tag       实验组 / 对照组（命名沿用临额的 temp_limit_tag 习惯）
-- ======================================================================


-- ══════════════════════════════════════════════════════════════════════
-- 第①段：建名单表
--   PRD 4.1「名单字段：策略侧决定」—— 这就是策略侧的定义
--   分区键 batch_date：PRD 4.2 要求跑批等当日分区就绪后再启动
-- ══════════════════════════════════════════════════════════════════════
DROP TABLE IF EXISTS mx.yj_silent_limit_refresh_list;

CREATE TABLE mx.yj_silent_limit_refresh_list (
  -- ── 主键与 PRD 接口字段 ──
  mid                            bigint,          -- 原名（PRD 入参叫 customer_id，见 TODO-6）
  biz_type                       varchar(20),     -- PRD：LIMIT_UP / PRODUCT_CHANGE
  decision_flow_id               varchar(40),     -- PRD：由策略配置，按 biz_type 路由（待风控给值）

  -- ── 新增派生字段（英文直译）──
  silent_days                    bigint,          -- 沉默天数
  silent_days_segment            varchar(20),     -- 沉默天数分层
  main_limit_expired_days        bigint,          -- 主额度过期天数，正数=已过期
  main_limit_expire_segment      varchar(20),     -- ★ 主额度过期分层，决策流据此走提额/重新授信
  maincreditlevel_v6_1           double,          -- V6_1 主资产等级
  credit_level_final             double,          -- 最终采用的等级
  credit_level_final_version     varchar(10),     -- ★ 必须与等级同行透传，不可只传等级
  credit_level_source            varchar(10),     -- V6_1 / SNAPSHOT / NONE
  main_limit_refresh_tag         varchar(40),     -- ★ 实验组 / 对照组

  -- ── 原表字段，原名不动 ──
  identity_number                varchar,
  phone_number                   varchar,
  realname                       varchar,
  push_token                     varchar,
  app_group                      varchar,
  age                            bigint,
  is_reloan_stgy                 integer,
  onloan_cnt                     bigint,
  last_loan_date                 date,
  last_repay_date                date,
  last_login_date                date,
  curr_main_credit_limit         decimal(38,6),
  curr_main_used_credit_limit    decimal(38,6),
  curr_main_available_limit      decimal(38,6),
  curr_main_limit_expire_date    date,
  daily_max_available_limit      decimal(38,6),
  curr_credit_level              double,
  curr_credit_level_version      varchar,
  load_time                      timestamp,       -- 底表快照时间，排查时点漂移用

  batch_date                     varchar          -- 分区键
)
WITH (
  format = 'ORC',
  partitioned_by = ARRAY['batch_date']
);


-- ══════════════════════════════════════════════════════════════════════
-- 【★ 干跑已验证 2026-11-02】第②段逻辑以 SELECT 形式全量跑过，6 项校验全通过：
--   行数 67,127 = 去重 mid 数 67,127（无重复）
--   主键为空 0 · 有等级但无版本 0 · 分层字段 NULL 0 · 沉默天数负值 0 · 哨兵残留 0
--   ★ 对照组 13,570 人 = 20.22% → PASS（分流确实生效，没有重蹈临额阈值的覆辙）
--   实际推送决策流 53,557 人，涉及原主额度 1.276 亿比索
--   （-999 哨兵过滤只砍掉 13 人：curr_main_credit_limit 7 个、daily_max 6 个）
--   ⚠️ 量级随日期漂移：快照 load_time 固定在 T-1，而 current_date 每天前进，
--      所以同一份快照在不同日期跑出的分层人数会变。实测到期日=2026-11-01 的 126 人，
--      在 current_date 从 11-01 翻到 11-02 时整体从 1_valid 掉进 2_exp_le30d。
--      → 汇报量级时必须同时写明「快照日 + 跑数日」两个日期。
-- ══════════════════════════════════════════════════════════════════════
-- 第②段：圈客并落库 —— 每日凌晨跑批前执行（须早于 PRD 4.2 的跑批启动时间）
-- ══════════════════════════════════════════════════════════════════════
INSERT INTO mx.yj_silent_limit_refresh_list
WITH lv61 AS (
  -- V6_1 评级：事件级表，取每人最新一条
  SELECT mid,
         MAX_BY(android_oldcust_maincreditlevel_charge_v6_1, createtime) AS maincreditlevel_v6_1
  FROM mx.android_oldcust_maincreditlevel_charge_v6_1_table
  WHERE android_oldcust_maincreditlevel_charge_v6_1 IS NOT NULL
    AND etl_date >= '20260819'          -- ★ 分区裁剪，不加会全分区扫
  GROUP BY 1
),
base AS (
  SELECT
    t.*,
    lv61.maincreditlevel_v6_1,
    DATE_DIFF('day', t.last_loan_date, DATE(CURRENT_DATE))                AS silent_days,
    DATE_DIFF('day', t.curr_main_limit_expire_date, DATE(CURRENT_DATE))   AS main_limit_expired_days
  FROM dws.dws_risk_stgy_apply_mid_tags t
  LEFT JOIN lv61 ON lv61.mid = t.mid
  -- ── 入池条件（沿用 27.灰度_离线临额发放.sql，逐条对齐）──
  WHERE t.is_reloan_stgy = 1                                     -- 复贷老客
    AND t.app_group IN ('Balam Plata','Tuna Cash','Mexcredo')     -- 三个产品包（Mikredi 排除）
    AND t.onloan_cnt = 0                                          -- ★ 无在贷 = 沉默前提
    AND t.curr_ovd_cnt_this_app_group      <= 0                   -- 本包当前无逾期
    AND t.curr_ovd_cnt_other_app_group_90d <= 0                   -- 他包近 90 天无逾期
    AND (t.id_30days_max_overdue_days <= 0
         OR t.id_30days_max_overdue_days IS NULL)                 -- 近 30 天无逾期
    AND t.age <= 65
    AND t.if_prohibit_apply = 0                                   -- 不在禁申期
    -- ⚠️ 刻意**不加** curr_main_limit_expire_date > CURRENT_DATE
    --    原因见文件头「卡点一」：加了会砍掉 94.2%，只剩不沉默的人。
    --    改为落成 main_limit_expire_segment 字段，由决策流分支处理。
    AND t.last_loan_date IS NOT NULL                              -- 必须有过放款（否则无从谈沉默）
    -- ⚠️ -999 是上游缺失哨兵，不是真实额度，做算术前必须排掉
    AND (t.curr_main_credit_limit IS NULL OR t.curr_main_credit_limit <> -999)
    AND (t.daily_max_available_limit IS NULL OR t.daily_max_available_limit <> -999)
),
tagged AS (
  SELECT
    b.*,
    CASE WHEN b.silent_days <  30 THEN '1_lt30d'
         WHEN b.silent_days <  60 THEN '2_30to59d'
         WHEN b.silent_days < 120 THEN '3_60to119d'
         WHEN b.silent_days < 180 THEN '4_120to179d'
         WHEN b.silent_days < 365 THEN '5_180to364d'
         ELSE                          '6_ge365d' END             AS silent_days_segment,
    CASE WHEN b.curr_main_limit_expire_date IS NULL   THEN '0_no_limit'
         WHEN b.main_limit_expired_days <=   0 THEN '1_valid'
         WHEN b.main_limit_expired_days <=  30 THEN '2_exp_le30d'
         WHEN b.main_limit_expired_days <=  90 THEN '3_exp_31to90d'
         WHEN b.main_limit_expired_days <= 180 THEN '4_exp_91to180d'
         ELSE                                       '5_exp_gt180d' END AS main_limit_expire_segment,
    -- 评级三级兜底：V6_1 优先 → 底表快照 → 无
    COALESCE(b.maincreditlevel_v6_1, b.curr_credit_level)         AS credit_level_final,
    CASE WHEN b.maincreditlevel_v6_1 IS NOT NULL THEN 'V6_1'
         ELSE b.curr_credit_level_version END                     AS credit_level_final_version,
    CASE WHEN b.maincreditlevel_v6_1 IS NOT NULL THEN 'V6_1'
         WHEN b.curr_credit_level    IS NOT NULL THEN 'SNAPSHOT'
         ELSE                                         'NONE' END  AS credit_level_source,
    -- ★ 灰度分流：80% 实验组 / 20% 对照组
    --   盐固定 '20261102' → 同一客户跨批次始终落同一臂，便于累计观测
    --   ⚠️⚠️ 临额那边踩过的坑：阈值曾写成 >= 0，哈希归一化后恒成立，
    --        else 分支永不命中 → 对照组一直是空的、全量发放，直到 1021 批才发现。
    --        第③段 A3 断言专门守这条：**对照组占比必须在 18%~22% 之间**。
    CASE WHEN FROM_BASE(SUBSTR(TO_HEX(SHA256(TO_UTF8(
              '20261102' || b.identity_number || b.app_group))), 1, 4), 16)
              / 65536.0000000000000000 >= 0.2
         THEN '1102固额刷额测试组_沉默'
         ELSE '1102固额刷额对照组_沉默' END                        AS main_limit_refresh_tag
  FROM base b
)
SELECT
  mid,
  CAST('LIMIT_UP' AS VARCHAR(20))                                 AS biz_type,
  CAST(NULL AS VARCHAR(40))                                       AS decision_flow_id,
  silent_days,
  CAST(silent_days_segment AS VARCHAR(20))                        AS silent_days_segment,
  main_limit_expired_days,
  CAST(main_limit_expire_segment AS VARCHAR(20))                  AS main_limit_expire_segment,
  maincreditlevel_v6_1,
  credit_level_final,
  CAST(credit_level_final_version AS VARCHAR(10))                 AS credit_level_final_version,
  CAST(credit_level_source AS VARCHAR(10))                        AS credit_level_source,
  CAST(main_limit_refresh_tag AS VARCHAR(40))                     AS main_limit_refresh_tag,
  identity_number,
  phone_number,
  realname,
  push_token,
  app_group,
  age,
  is_reloan_stgy,
  onloan_cnt,
  last_loan_date,
  last_repay_date,
  last_login_date,
  curr_main_credit_limit,
  curr_main_used_credit_limit,
  curr_main_available_limit,
  curr_main_limit_expire_date,
  daily_max_available_limit,
  curr_credit_level,
  curr_credit_level_version,
  load_time,
  DATE_FORMAT(DATE(CURRENT_DATE), '%Y%m%d')                       AS batch_date
FROM tagged
;


-- ══════════════════════════════════════════════════════════════════════
-- 第③段：落库后必跑的校验
--   ⚠️ 断言写完先做一次代数化简：问自己「什么样的数据能让它非 0」，
--      答不出来就是构造恒真、没有信息量。
-- ══════════════════════════════════════════════════════════════════════
SELECT
  COUNT(1)                                                          AS n_rows,
  COUNT(DISTINCT mid)                                               AS n_mid,

  -- A1 幂等前提：同一 batch_date 内 (mid, biz_type) 必须唯一
  --    PRD 7 要求"同客同日同类型只更新一次"，名单表先天不能有重复
  COUNT(1) - COUNT(DISTINCT CAST(mid AS VARCHAR) || '|' || biz_type) AS a1_dup_rows,

  -- A2 必填入参不得为空（decision_flow_id 待风控给值前允许为空，单列观察）
  SUM(CASE WHEN mid IS NULL OR biz_type IS NULL THEN 1 ELSE 0 END)   AS a2_key_null,
  SUM(CASE WHEN decision_flow_id IS NULL THEN 1 ELSE 0 END)          AS a2_flow_null_todo,

  -- A3 ★★ 对照组必须真的分出来：占比应在 18%~22%
  --    这条就是为了守临额那个"阈值写成 >=0 导致对照组恒为空"的坑
  SUM(CASE WHEN main_limit_refresh_tag LIKE '%对照组%' THEN 1 ELSE 0 END)
                                                                    AS a3_control_n,
  CAST(SUM(CASE WHEN main_limit_refresh_tag LIKE '%对照组%' THEN 1 ELSE 0 END) AS DOUBLE)
    / NULLIF(COUNT(1), 0)                                           AS a3_control_pct,
  CASE WHEN CAST(SUM(CASE WHEN main_limit_refresh_tag LIKE '%对照组%' THEN 1 ELSE 0 END) AS DOUBLE)
            / NULLIF(COUNT(1),0) BETWEEN 0.18 AND 0.22
       THEN 'PASS' ELSE 'FAIL_分流失效' END                         AS a3_verdict,

  -- A4 评级版本不可混用：等级有值时版本必须也有值
  SUM(CASE WHEN credit_level_final IS NOT NULL
            AND credit_level_final_version IS NULL THEN 1 ELSE 0 END) AS a4_level_no_version,

  -- A5 分层字段完备性（CASE 必须覆盖全部行，不能漏到 NULL）
  SUM(CASE WHEN silent_days_segment IS NULL THEN 1 ELSE 0 END)      AS a5_silent_seg_null,
  SUM(CASE WHEN main_limit_expire_segment IS NULL THEN 1 ELSE 0 END) AS a5_expire_seg_null,

  -- A6 口径自洽：沉默天数必须 >= 0（last_loan_date 不可能在未来）
  SUM(CASE WHEN silent_days < 0 THEN 1 ELSE 0 END)                  AS a6_silent_days_neg,

  -- A7 哨兵值必须已排除
  SUM(CASE WHEN curr_main_credit_limit    = -999 THEN 1 ELSE 0 END)  AS a7_limit_sentinel,
  SUM(CASE WHEN daily_max_available_limit = -999 THEN 1 ELSE 0 END)  AS a7_daily_sentinel
FROM mx.yj_silent_limit_refresh_list
WHERE batch_date = DATE_FORMAT(DATE(CURRENT_DATE), '%Y%m%d');


-- ══════════════════════════════════════════════════════════════════════
-- 第④段：量级汇总 —— 直接回答 PRD 待确认问题①
--   「墨西哥首批跑批名单量级、预计每日通过客户数，用于评估并发度与回写窗口」
-- ══════════════════════════════════════════════════════════════════════
SELECT main_limit_expire_segment,
       silent_days_segment,
       main_limit_refresh_tag,
       COUNT(1)                                                     AS n_mid,
       AVG(curr_main_credit_limit)                                  AS avg_main_credit_limit,
       SUM(curr_main_credit_limit)                                  AS sum_main_credit_limit,
       AVG(credit_level_final)                                      AS avg_credit_level_final,
       SUM(CASE WHEN credit_level_source = 'V6_1' THEN 1 ELSE 0 END) AS n_v6_1,
       CAST(SUM(CASE WHEN credit_level_source='V6_1' THEN 1 ELSE 0 END) AS DOUBLE)
         / NULLIF(COUNT(1),0)                                       AS cov_v6_1
FROM mx.yj_silent_limit_refresh_list
WHERE batch_date = DATE_FORMAT(DATE(CURRENT_DATE), '%Y%m%d')
GROUP BY 1,2,3
ORDER BY 1,2,3;


-- ══════════════════════════════════════════════════════════════════════
-- 第⑤段：给跑批系统的取数口径（跑批侧按这个取，不做任何圈选逻辑）
--   PRD 3.1：跑批只按约定表取数
-- ══════════════════════════════════════════════════════════════════════
/*
SELECT mid, biz_type, batch_date, decision_flow_id,
       silent_days, silent_days_segment,
       main_limit_expired_days, main_limit_expire_segment,
       maincreditlevel_v6_1, credit_level_final, credit_level_final_version,
       credit_level_source, main_limit_refresh_tag,
       app_group, curr_main_credit_limit, daily_max_available_limit
FROM mx.yj_silent_limit_refresh_list
WHERE batch_date = '${batch_date}'
  AND main_limit_refresh_tag LIKE '%测试组%';   -- ★ 对照组不调决策流
*/


-- ======================================================================
-- 【待办 · 需要策略/风控/模型/研发侧拍板后才能跑】
--   TODO-1 decision_flow_id：提额流的决策流 ID 还没有（PRD 待确认问题②）
--   TODO-2 「主额度已过期」那 60,591 人走哪条流？PRD 的 biz_type 只有
--          LIMIT_UP / PRODUCT_CHANGE，**没有"重新授信"这一类**，需新增或复用
--   TODO-3 模型侧对沉默客群离线补跑 V6_1 打分（需补 56,571 人）——
--          否则 >=180 天沉默段只有 3.3% 有评级
--   TODO-4 产品变更（PRODUCT_CHANGE）的圈客逻辑：
--          底表 dws_risk_stgy_apply_mid_tags **没有任何产品归属字段**，
--          要做产品变更必须先让 BI 补字段
--   TODO-5 回滚方案：固额提上去不会自动失效，PRD 没写错刷怎么退回
--   TODO-6 主键列名：本表用 `mid`（与现有临额体系一致），PRD 5.1 入参写的是
--          `customer_id`。请研发侧在跑批取数时做映射，不要改本表列名
--   TODO-7 app_group 是否纳入 YW(68,606) 与 TG(65,680)：
--          现在只圈 3 个包、覆盖 65.6%，这两个包合计 27.7% 被排除在外
--   TODO-8 ★ 调度时点冲突：PRD 4.2 要求「墨西哥时区凌晨执行」，
--          但底表 dws_risk_stgy_apply_mid_tags 每日 **07:00** 才刷新。
--          若圈客 SQL 在凌晨跑，拿到的是前一天 07:00 的快照（业务上already T-2）；
--          若等 07:00 之后跑，名单就赶不上凌晨的跑批窗口。
--          两者必须二选一：① 跑批改到 08:00 后 ② 名单用 T-2 快照并接受时效损失
--          ③ 底表刷新提前到凌晨之前。建议和研发/数仓一起定。
-- ======================================================================
