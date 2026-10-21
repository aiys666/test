-- ======================================================================
-- 放款资产额度指标（逐笔 · 复贷老客 · 2026-09-01 起）
-- 底表：全部基础字段取自单表 mx.yj_test_table_250225（不再关联 funnel7）
-- 列名策略：有源字段的列直接用**源表原名**；派生列用清晰英文（不再自造别名）
--
-- 列清单（24 列）与口径：
--   [标识]  biz_id / mid / issue_date / product_level / contract_amount
--           android_oldCust_mainCreditLevel_charge_V6_1                ← 源表原名（V6_1 主评级）
--   [主额]  credit_amount                授予额度（授信额度）
--           change_used_grantamount      放款前已占用
--           main_available_amount        当前可用额度 = 授予 − 已占用
--           daily_max_available_limit    单日可借上限（yj 原值优先，仅矛盾时用 1077 修正，见注 0）
--           risk_credit_limit            源表原名（上游口径的「本笔占用主额」，可能为空）
--           main_used_this               本笔支用 = COALESCE(C003台账, risk_credit_limit, 合同额 − 临额使用额)
--   [离线临额]
--           offline_grant_amount         该笔发放额（放款时刻前 5 天内最近一条 C015/C013，见注 1）
--           offline_used_amount          本笔放款时刻该账户 TEMP 的**实时占用**（见注 1）
--           offline_available_amount     当前可用额度 = MAX(授予 − 已占用, 0)
--           offline_used_this            本笔支用（本笔无 C010 时的临额使用额）
--   [在线临额]
--           product_limit_max            产品上限（见注 3）
--           online_grant_amount          本笔**弹窗发放额**（857 节点，含「已发放未领取」，见注 2）
--           online_used_amount           领取时（C010）该 TEMP 账户的既有占用
--           online_available_amount      当前可用额度 = 发放额 − 既有占用
--           online_used_this             本笔支用（本笔有 C010 时的临额使用额）
--   [三套逻辑可用额度]  分组均为「主额 + 离线临额」
--           avail_current_logic          当前逻辑 = LEAST(要改的逻辑, 产品上限)
--           avail_tochange_logic         要改的逻辑 = LEAST(主额可用, 单日可借上限) + 离线临额可用
--           avail_future_logic           未来的逻辑 = 主额可用 + 离线临额可用
--   [优惠券]
--           voucher_limit                额度立减券面值（用信确认页核销，抵减合同额，见注 5）
--           voucher_id                   券 ID（券本体 ods.s11_icpn_voucher）
--
-- 口径要点（易错处，按此理解）：
-- 注 0  yj 是每日快照（CREATE TABLE AS），credit_amount / daily_max_available_limit /
--      change_used_grantamount / risk_credit_limit 四列是同一个 LEFT JOIN 挂上来的，
--      构建时刻上游当日行未落库时会同时为空（全区间约 2,019 笔 / 3.2%）。
--      故四列统一做「上游正确口径 → yj 原值 → 上游表兜底」多重 COALESCE（按可靠性排序）：
--      ⚠️ daily_max_available_limit 的取值规则（2026-10-20 修正，勿再无条件用 1077 覆盖）：
--         **yj 原值优先**（yj 落的就是上游 1067 授信时刻的 daily_max，多数笔正确）；
--         仅当 **yj 缺失** 或 **yj < 本笔占用主额 risk_credit_limit**（逻辑不自洽，说明 yj 落的是
--         「今日剩余可借」快照）时，才用「结清授信决策流」(modelmainid=1077) 的值修正，并取两者较大值。
--         1077 取值窗口必须是 **本笔放款时刻 release_time 之前**最近一次 ——
--         用 issue_date+1 天会把**同一天放款之后**另一次申请的 1077 决策取进来（实测反例
--         biz 1620000470988726：08:20 放款，19:21 另一次申请把 daily_max 记成 8000，而放款时是 10000）。
--         1077 以 mid 为键（biz_id 通道常为空），输入含 V6_1 主评级，输出「用户单日可借金额上限」
--         （同节点另输出 fd_single_grantcredit_amount_cap = 复贷单笔授信额度cap）。
--         而 yj 原值 / mx.tmp_darren_product_table / s21(modelmainid=1067「授信-复贷风控事件」)
--         落的是**「授信时刻的今日剩余可借」快照**，故会出现 2000 / 7000 这类
--         **小于本笔占用主额**的值（如 2000 < 2940，逻辑不自洽）。
--        daily_max_available_limit → yj_test_table_250225 原值（优先）
--                                 → ods.s21_risk_model_record(1077 结清授信决策流，仅矛盾/缺失时)
--                                 → mx.tmp_darren_product_table
--                                 → ods.s21_risk_model_record(1067 授信-复贷风控事件)
--        credit_amount             → mx.tmp_darren_product_table
--                                 → ods.s21_risk_model_record(1067授信节点,覆盖率100%)
--        change_used_grantamount   → mx.darren_bizid_used_grantamount
--        risk_credit_limit         → mx.darren_bizid_used_grantamount
--                                 → ods_view_presto.s05_user_creditlimit_used_detail(MAIN冻结行)
--      本笔支用 main_used_this → C003台账增量 → used_detail MAIN冻结额 → risk_credit_limit → 恒等式
--      ⚠️ C003 是「总额度预授权」，可能与实际支用主额不等（以 used_detail MAIN 冻结额为准）。
--
-- 注 1  离线临额的「已占用」= **本笔放款时刻**该账户 TEMP 台账的实时占用，
--      不是离线批次当时记录的 curr_temp_used_credit_limit（批次快照会滞后）。
--      反例（真实案例 biz 1620000478928573）：10-07 批次发 450 时快照占用 360，
--      但占用方（原在贷笔）10-08 已结清释放，本笔 10-09 放款时占用已=0，
--      因此可用额度=450（不是 450−360=90），本笔也确实用满 450。
--      取值法：本笔 TEMP 冻结时刻之前、同 mid 最近一条 TEMP 事件的
--              change_used_grantamount（该字段即事件发生后的账户级占用）。
--      ⚠️ 发放额取 C015/C013 事件，不取 yuhan 表的 data_date（2026-10-20 修正）：
--         mx.yuhan_temp_limit_base_table_his_20260924.data_date 是**批处理标签日 = 实际发放日 + 1 天**
--         （实测 C015 09-01 20:02 发放、data_date=20260902）；按 data_date <= issue_date 会漏掉当日
--         20 点后发放的批次。该表 temp_limit_issue_date 是**首次获额时间**，也不是本批次时间。
--         改用 change_record 的 C015/C013 事件时刻 + change_total_grantamount，09-01~09-02 窗口
--         的「离线支用>0 但发放额=0」从 47 笔降到 10 笔。
--
-- 注 2  临额「实际使用额」只用 mx.yj_test_table_250225.temp_grant_amount（真值，÷1000=比索）。
--      ⚠️ 「在线临额发放额」与「在线临额使用额」是两个不同口径，务必分开（2026-10-20 修正）：
--         **发放额 online_grant_amount = 857 节点（弹窗最终额）的 temp_credit_amount**，
--         不论客户是否领取；tag=0 时 857 输出 0，故仅保留 >0 的（等价于 1386 tag=1 双保险）。
--         使用额 online_used_this 才看 temp_grant_amount / C010。
--         反例 biz 1620000470988726：1386 tag=1、1379=4000、857=4000（type2、占用主额 10000，
--         即 floor(10000/20)×20×40%），但 TEMP 台账**无 C010**、yj temp_grant_amount=0
--         —— 属「弹窗已发、客户未领取」（约占 tag=1 的 53%），此时发放额=4000、使用额=0。
--         旧逻辑把发放额也挂在 C010 上，导致这类笔发放额被算成 0。
--      归属规则：存在「本笔」C010（在线临额领取）→ 使用额全部计在线；否则全部计离线，两类不会同时使用。
--      「本笔」C010 需同时满足：① 本笔确实用了临额（temp_grant_amount>0）；
--      ② C010 净发放额（change_total_grantamount − change_used_grantamount）恰等于本笔临额使用额；
--      ③ C010 早于本笔临额冻结时刻（覆盖「跨笔领取」场景）。
--      仅按「存在 C010」判定会把跨笔/历史 C010 误挂到本笔（反例见 CTE4 注释）。
--
-- 注 3  产品上限常态 10000；product_level = 'D_1_03' 且 issue_date >= 2026-10-19 时为 15000（临时测试）。
--
-- 注 4  Presto 单次结果集上限 10000 行，本区间约 6.3 万笔会被截断，
--       请按 issue_date 拆区间执行，或用 fetch_asset_quota.py 客户端分片取全量。
--
-- 注 5  优惠券 voucher_limit 是什么、在哪出现（2026-10-20 核实）：
--       ① 是什么：**额度立减券**（额度类券），用信确认页核销后，券面值直接抵减合同额，
--          既不是授信额度、也不是临额，属于「钱」，所以不进额度池、不占临额。
--       ② 出现节点：**风控决策流不落券字段**（s21_risk_model_record 全节点无 voucher/coupon key），
--          券只在用信确认/额度冻结环节落库，唯一可取的落库点是
--          ods_view_presto.s05_user_creditlimit_used_detail 的
--          voucher_limit / voucher_id / voucher_ids（随 MAIN FREEZE 行落，与冻结同一毫秒级）。
--          券本体在 ods.s11_icpn_voucher（id=voucher_id、user_tag=mid、worth=面值、
--          status=2 已使用、use_time=核销时刻、activity_id/batch_id=活动与批次）。
--          实测：券 use_time 09-01 07:05:56.345，本笔 MAIN FREEZE 07:05:56.389，相差 44 毫秒。
--       ③ 规模：2026-09-01~10-15 复贷 58,930 笔中 193 笔（0.33%）用券，合计 38,500 比索，
--          面值几乎全为 200（少量 100/300）；主流批次 18454/活动 6281（2026-08-10 起，34,094 张）。
--       ④ 恒等式：contract_amount = MAIN冻结(risk_credit_limit) + TEMP冻结 + voucher_limit。
--          09-01~09-02 窗口有 15 笔「合同额 − 主额支用 − 临额使用」恰差 200，全部由本字段解释，
--          残差 0。故用合同额倒推临额使用额时，必须先扣 voucher_limit。
-- ======================================================================

WITH prod AS (
  -- CTE0a 上游复贷授信决策流落表（yj 的 credit_amount / daily_max_available_limit 本就取自这里）
  -- biz 粒度取 MAX：仅作兜底，把「yj 快照时该列还没挂上」的笔补回来
  SELECT CAST(biz_id AS VARCHAR)                        AS biz_id,
         MAX(CAST(credit_amount AS DOUBLE))              AS credit_amount,
         MAX(CAST(daily_max_available_limit AS DOUBLE))  AS daily_max_available_limit
  FROM mx.tmp_darren_product_table
  WHERE etl_date >= '20260825'
  GROUP BY 1
),
dm AS (
  -- CTE0b biz 粒度的本笔占用主额 / 已用授信（yj 的 risk_credit_limit / change_used_grantamount 取数源）
  SELECT CAST(biz_id AS VARCHAR)                          AS biz_id,
         MAX(TRY_CAST(risk_credit_limit AS DOUBLE))        AS risk_credit_limit,
         MAX(TRY_CAST(change_used_grantamount AS DOUBLE))  AS change_used_grantamount
  FROM mx.darren_bizid_used_grantamount
  WHERE create_time >= TIMESTAMP '2026-08-25 00:00:00'
  GROUP BY 1
),
s21auth AS (
  -- CTE0c 授信决策节点（modelmainid=1067, CHAMPION）：授信额度 / 单日最大可借
  -- 复贷放款笔覆盖率 100%，是 yj 四件套的最上游出处；yj 快照当日未挂上时用它兜底
  SELECT CAST(biz_id AS BIGINT) AS biz_id,
         MAX(TRY_CAST(NULLIF(regexp_extract(CAST(outputdata AS VARCHAR),
             '"credit_amount":(-?[0-9.]+)', 1), '') AS DOUBLE)) AS credit_amount,
         MAX(TRY_CAST(NULLIF(regexp_extract(CAST(outputdata AS VARCHAR),
             '"daily_max_available_limit":(-?[0-9.]+)', 1), '') AS DOUBLE)) AS daily_max_available_limit
  FROM ods.s21_risk_model_record
  WHERE modelmainid = 1067
    AND strategytype = 'CHAMPION'
    AND biz_id IS NOT NULL
    AND createtime >= TIMESTAMP '2026-08-20 00:00:00'
  GROUP BY 1
),
usedm AS (
  -- CTE0d 额度使用明细 MAIN 冻结行：本笔实际占用主额（比 C003 预授权更贴近合同口径）
  SELECT CAST(biz_id AS BIGINT) AS biz_id,
         MAX(TRY_CAST(risk_credit_limit AS DOUBLE)) AS main_used_this
  FROM ods_view_presto.s05_user_creditlimit_used_detail
  WHERE limit_type     = 'MAIN'
    AND change_action  = 'FREEZE_LIMIT'
    AND biz_id IS NOT NULL
    AND create_time >= TIMESTAMP '2026-08-25 00:00:00'
  GROUP BY 1
),
base AS (
  -- CTE1 复贷老客放款笔（单表 mx.yj_test_table_250225）+ 主额四件套上游兜底
  -- ⚠️ 去重必做：yj 表对同一 biz_id 存在 **4 条逐字段完全相同**的重复行
  --    （09-01~10-20 全区间 64,844 笔 → 259,376 行，`select distinct *` 每笔仅剩 1 行）。
  --    若不去重：① base 自身按 4 行展开；② offm 以 base 为输入也会展开 4 行；
  --    ③ 主查询 LEFT JOIN 后每笔产出 4×4=16 行（笛卡尔放大，实测 biz 1620000474029832 即 16 行）。
  --    故先按 biz_id 取 rn=1 收敛为一笔一行。
  SELECT * FROM (
    SELECT CAST(y.biz_id AS BIGINT)                                     AS biz_id,
           y.mid,
           y.issue_date,
           y.release_time,
           CAST(y.product_level AS VARCHAR)                             AS product_level,
           CAST(y.contract_amount AS DOUBLE)                            AS contract_amount,
           CAST(COALESCE(y.temp_grant_amount, 0) AS DOUBLE) / 1000.0    AS temp_used,
           COALESCE(CAST(y.credit_amount AS DOUBLE), p.credit_amount, s.credit_amount)          AS credit_amount,
           COALESCE(CAST(y.change_used_grantamount AS DOUBLE), d.change_used_grantamount, 0)     AS change_used_grantamount,
           COALESCE(CAST(y.daily_max_available_limit AS DOUBLE), p.daily_max_available_limit,
                    s.daily_max_available_limit)                                                AS daily_max_available_limit,
           COALESCE(CAST(y.risk_credit_limit AS DOUBLE), d.risk_credit_limit,
                    u.main_used_this)                                                           AS risk_credit_limit,
           CAST(y.android_oldCust_mainCreditLevel_charge_V6_1 AS DOUBLE)
                                                                      AS android_oldCust_mainCreditLevel_charge_V6_1,
           ROW_NUMBER() OVER (PARTITION BY CAST(y.biz_id AS BIGINT)
                              ORDER BY y.update_time DESC)                 AS _rn
    FROM mx.yj_test_table_250225 y
    LEFT JOIN prod    p ON p.biz_id = CAST(y.biz_id AS VARCHAR)
    LEFT JOIN dm      d ON d.biz_id = CAST(y.biz_id AS VARCHAR)
    LEFT JOIN s21auth s ON s.biz_id = CAST(y.biz_id AS BIGINT)
    LEFT JOIN usedm   u ON u.biz_id = CAST(y.biz_id AS BIGINT)
    WHERE y.issue_date >= DATE '2026-09-01'
      AND y.issue_date <= DATE '2026-10-20'
      AND y.if_issue = 1
      AND y.is_reloan = 'old'        -- 该表本身已限复贷，此条件为显式加固
      AND y.biz_id IS NOT NULL
  ) t
  WHERE t._rn = 1
),
s1077 AS (
  -- CTE1b 结清授信决策流（modelmainid=1077）：daily_max_available_limit 的**矛盾修正源**
  -- 该节点以 mid 为键（biz_id 通道常为空），输入含 V6_1 主评级，输出「用户单日可借金额上限」
  -- daily_max_available_limit（同节点另输出 fd_single_grantcredit_amount_cap = 复贷单笔授信额度cap）。
  -- ⚠️ 窗口上界必须是 **本笔放款时刻 release_time**，不能用「放款日当天及之前」：
  --    同一天放款后若客户又发起一次申请，会再跑一次 1077 并落一个不同（通常更低）的 daily_max。
  --    实测反例 biz 1620000470988726：09-26 08:20:43 放款、09-26 19:21:56 又跑 1077 记成 8000，
  --    按 issue_date+1 天取会把 8000 当成放款时的上限，而放款时真实值是 10000（yj/1067 均为 10000）。
  -- 本 CTE 只提供候选值，是否采用由 dmx 按「yj 缺失 或 yj < 占用主额」决定。
  SELECT biz_id, daily_max_available_limit
  FROM (
    SELECT b.biz_id,
           TRY_CAST(NULLIF(regexp_extract(CAST(r.outputdata AS VARCHAR),
               '"daily_max_available_limit":(-?[0-9.]+)', 1), '') AS DOUBLE) AS daily_max_available_limit,
           ROW_NUMBER() OVER (PARTITION BY b.biz_id ORDER BY r.createtime DESC) AS rn
    FROM base b
    JOIN ods.s21_risk_model_record r
      ON CAST(r.mid AS VARCHAR) = CAST(b.mid AS VARCHAR)
     AND r.modelmainid  = 1077
     AND r.strategytype = 'CHAMPION'
     AND r.etl_date    >= '20260701'
     AND r.createtime  >= TIMESTAMP '2026-07-01 00:00:00'
     AND r.createtime  <= TIMESTAMP '2026-10-22 00:00:00'
     AND r.createtime  <= COALESCE(b.release_time,
                                   CAST(DATE_ADD('day', 1, b.issue_date) AS TIMESTAMP))
    WHERE regexp_extract(CAST(r.outputdata AS VARCHAR),
            '"daily_max_available_limit":(-?[0-9.]+)', 1) <> ''
  ) t
  WHERE rn = 1
),
-- ⚠️ daily_max_available_limit 的最终取值不单独建 CTE（原 dmx）：每多引用一次 base，
--    Presto 就会把 base 的 4 个 LEFT JOIN 重新展开一遍，触发 stage 上限（150）。
--    规则已内联到主查询：yj 原值优先；仅当 yj 缺失、或 yj < 本笔占用主额时，
--    才用 s1077（结清授信决策流）修正并取两者较大值。三个真实样本：
--      biz 1620000470988726：yj=10000 = 占用主额 10000      → 保留 10000（1077 也是 10000）
--      biz 1620000483859552：yj=7000  < 占用主额 10000      → 用 1077=10000 修正
--      biz 1620000484944464：yj=2000  < 占用主额 2940       → 用 1077=3500 修正
--      biz 1620000483355776：yj=2000  < 占用主额 2650       → 用 1077=4000 修正
s857 AS (
  -- CTE1d 在线临额**弹窗发放额**（modelmainid=857 的 temp_credit_amount）
  -- 与「使用额」解耦：客户未领取（无 C010）时发放额照样有值。
  --   tag=0 → 857 输出 temp_credit_amount:0，故 HAVING >0（等价于 1386 tag=1 双保险）；
  --   857 是通用变量节点，同节点还写 last_credit_amt_float / grantcredit_7d_amount 等，
  --   必须按 key 正则取 temp_credit_amount，不能整节点取值。
  -- ⚠️ 此处不再 JOIN base：base 已被多个 CTE 引用，再加一次会触发
  --    "Number of stages (159) exceeds the allowed maximum (150)"，故独立聚合后由主查询 LEFT JOIN。
  SELECT CAST(r.biz_id AS BIGINT) AS biz_id,
         MAX(TRY_CAST(NULLIF(regexp_extract(CAST(r.outputdata AS VARCHAR),
             '"temp_credit_amount":(-?[0-9.]+)', 1), '') AS DOUBLE)) AS online_grant_amount
  FROM ods.s21_risk_model_record r
  WHERE r.modelmainid  = 857
    AND r.strategytype = 'CHAMPION'
    AND r.biz_id IS NOT NULL
    AND r.createtime >= TIMESTAMP '2026-08-25 00:00:00'
    AND r.createtime <= TIMESTAMP '2026-10-22 00:00:00'
  GROUP BY 1
  HAVING MAX(TRY_CAST(NULLIF(regexp_extract(CAST(r.outputdata AS VARCHAR),
             '"temp_credit_amount":(-?[0-9.]+)', 1), '') AS DOUBLE)) > 0
),
lz_anchor AS (
  -- CTE2a 本笔 TEMP 冻结时刻（离线临额占用的时间锚点）
  SELECT CAST(external_id AS VARCHAR) AS biz_id_v,
         MIN(create_time)             AS freeze_time
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE limit_type    = 'TEMP'
    AND change_action = 'FREEZE_LIMIT'
    AND create_time  >= TIMESTAMP '2026-08-25 00:00:00'
    AND create_time  <= TIMESTAMP '2026-10-21 23:59:59'
  GROUP BY 1
),
offm AS (
  -- CTE2 离线临额：该批次发放额 + 本笔放款时刻的账户级实时占用
  SELECT b.biz_id,
         COALESCE(g.temp_limit_issue_amount, 0) AS offline_grant_amount,
         COALESCE(u.temp_used_after, 0)         AS offline_used_amount
  FROM base b
  LEFT JOIN (
    -- 放款时刻前 5 天内最近一条离线发放（C015 标准圈选 / C013 手工补单），有效期 5 天
    -- ⚠️ 不能用 mx.yuhan_temp_limit_base_table_his_20260924 的 data_date 做批次日期：
    --    该字段是**批处理标签日 = 实际发放事件日 + 1 天**（实测：C015 09-01 20:02 发放，
    --    data_date 记 20260902）。按 data_date <= issue_date 会漏掉当日 20 点后发放的批次，
    --    09-01~09-02 两天窗口漏 47 笔（占 1.9%）。
    --    另：该表 temp_limit_issue_date 是**首次获额时间**（常为几个月前），不是本批次时间，也不可用。
    --    故直接用额度台账事件时刻，金额取 change_total_grantamount（= 账户实际到账额度）。
    SELECT b2.biz_id,
           MAX_BY(CAST(c.change_total_grantamount AS DOUBLE), c.create_time) AS temp_limit_issue_amount
    FROM base b2
    JOIN ods_view_presto.s05_user_creditlimit_change_record c
      ON c.mid = b2.mid
     AND c.limit_type        = 'TEMP'
     AND c.change_event_type IN ('C015', 'C013')
     AND c.change_action     = 'CHANGE_LIMIT'
     AND CAST(c.change_total_grantamount AS DOUBLE) > 0
     AND c.create_time >= DATE_ADD('day', -5,
           COALESCE(b2.release_time, CAST(b2.issue_date AS TIMESTAMP)))
     AND c.create_time <= COALESCE(b2.release_time, CAST(b2.issue_date AS TIMESTAMP))
    GROUP BY 1
  ) g ON g.biz_id = b.biz_id
  LEFT JOIN (
    -- 本笔 TEMP 冻结时刻之前的实时存量占用（= 该时刻前最后一条 TEMP 事件的账户级占用）
    SELECT b3.biz_id,
           MAX_BY(CAST(e.change_used_grantamount AS DOUBLE), e.create_time) AS temp_used_after
    FROM base b3
    JOIN ods_view_presto.s05_user_creditlimit_change_record e
      ON e.mid = b3.mid
     AND e.limit_type   = 'TEMP'
     AND e.create_time >= TIMESTAMP '2026-01-01 00:00:00'
     AND e.create_time <= TIMESTAMP '2026-10-21 23:59:59'
    LEFT JOIN lz_anchor a ON a.biz_id_v = CAST(b3.biz_id AS VARCHAR)
    WHERE e.create_time < COALESCE(a.freeze_time, b3.release_time)
    GROUP BY 1
  ) u ON u.biz_id = b.biz_id
),
c003 AS (
  -- CTE3 MAIN FREEZE 台账（external_id = biz_id）：本笔主额支用 = change_used_grantamount − old_used_grantamount
  -- 取最接近 release_time 的那条 C003；缺失的由主查询依次回退 risk_credit_limit → 恒等式
  SELECT biz_id, main_used_this
  FROM (
    SELECT b.biz_id,
           CAST(c.change_used_grantamount AS DOUBLE)
             - CAST(COALESCE(c.old_used_grantamount, 0) AS DOUBLE) AS main_used_this,
           ROW_NUMBER() OVER (
             PARTITION BY b.biz_id
             ORDER BY ABS(DATE_DIFF('second', c.create_time, b.release_time))
           ) AS rn
    FROM base b
    JOIN ods_view_presto.s05_user_creditlimit_change_record c
      ON CAST(c.external_id AS VARCHAR) = CAST(b.biz_id AS VARCHAR)
     AND c.limit_type    = 'MAIN'
     AND c.change_action = 'FREEZE_LIMIT'
     AND c.create_time  >= TIMESTAMP '2026-08-25 00:00:00'
     AND c.create_time  <= TIMESTAMP '2026-10-21 23:59:59'
  ) t
  WHERE rn = 1
),
c010 AS (
  -- CTE4 在线临额（C010）：锚定本笔临额冻结时刻 + 金额匹配
  -- 判定「在线」需同时满足：① 本笔确实用了临额（temp_used>0）；② 存在一条 C010，
  --   其净发放额(change_total_grantamount − change_used_grantamount)恰等于本笔临额使用额；
  --   ③ 该 C010 早于本笔临额冻结时刻（无冻结时退化为早于放款时刻）。
  -- 只按「存在 C010」判定会把跨笔/历史 C010 误挂到本笔。真实反例 biz 1620000481877146：
  --   10-18 本笔用离线临额 1000（对应 10-14 批次），账户却在 10-01 有一条无关 C010=300；
  --   按「存在即在线」会误判为在线，且 online_grant(300) < online_used_this(1000) 自相矛盾。
  SELECT biz_id, online_grant_amount, online_used_amount
  FROM (
    SELECT b.biz_id,
           CAST(c.change_total_grantamount AS DOUBLE) AS online_grant_amount,
           CAST(c.change_used_grantamount  AS DOUBLE) AS online_used_amount,
           ROW_NUMBER() OVER (
             PARTITION BY b.biz_id
             ORDER BY ABS(DATE_DIFF('second', c.create_time,
                                    COALESCE(a.freeze_time, b.release_time))),
                      c.create_time DESC
           ) AS rn
    FROM base b
    LEFT JOIN lz_anchor a ON a.biz_id_v = CAST(b.biz_id AS VARCHAR)
    JOIN ods_view_presto.s05_user_creditlimit_change_record c
      ON c.mid = b.mid
     AND c.limit_type        = 'TEMP'
     AND c.change_event_type = 'C010'
     -- ⚠️ 下界必须跟随本笔冻结时刻回看，不能用固定日期（2026-08-31）：
     --    在线临额有效期 3 天，但存在「跨笔领取」——C010 在**上一笔**放款时发放，
     --    本笔复用该额度。实测反例 biz 1620000461918805：C010 于 08-30 20:14 随
     --    biz 1620000461428809 发放（200），该笔 09-01 09:39 复用同一 200，
     --    固定下界 08-31 会把这条 C010 漏掉，导致本笔被误判为离线临额（发放额=0）。
     AND c.create_time      >= DATE_ADD('day', -7,
                                  COALESCE(a.freeze_time,
                                           b.release_time,
                                           CAST(b.issue_date AS TIMESTAMP)))
     AND c.create_time      <= COALESCE(a.freeze_time, b.release_time)
     AND ABS((CAST(c.change_total_grantamount AS DOUBLE)
              - CAST(c.change_used_grantamount  AS DOUBLE)) - b.temp_used) < 1.0
    WHERE b.temp_used > 0
  ) t
  WHERE rn = 1
),
vch AS (
  -- CTE5 优惠券（额度立减券）：与本笔额度冻结同时落库的 voucher_limit / voucher_id
  -- 含义：券在「用信确认页」核销，券面额直接抵减合同额（不是额度、不是临额）。
  --   券本体在 ods.s11_icpn_voucher（type_code='2' 额度类券、worth=面值、status=2 已使用、
  --   use_time 与本笔 MAIN FREEZE 同一秒）；风控决策流节点（s21_risk_model_record）**不落券字段**，
  --   唯一可取的落库点就是额度使用明细的 voucher_limit / voucher_id / voucher_ids。
  -- ⚠️ 只取 limit_type='MAIN' + change_action='FREEZE_LIMIT'：券随主额冻结一次性核销，
  --    TEMP 行与 UNFREEZE 行的 voucher_limit 恒为 0，多取会重复计数。
  -- 规模：2026-09-01~10-15 复贷 58,930 笔中 193 笔（0.33%）用券，合计 38,500 比索，面值几乎全为 200。
  SELECT CAST(biz_id AS BIGINT)                     AS biz_id,
         SUM(CAST(voucher_limit AS DOUBLE))         AS voucher_limit,
         MAX(CAST(voucher_id AS VARCHAR))           AS voucher_id
  FROM ods_view_presto.s05_user_creditlimit_used_detail
  WHERE limit_type    = 'MAIN'
    AND change_action = 'FREEZE_LIMIT'
    AND biz_id IS NOT NULL
    AND CAST(voucher_limit AS DOUBLE) > 0
    AND create_time  >= TIMESTAMP '2026-08-25 00:00:00'
    AND create_time  <= TIMESTAMP '2026-10-22 23:59:59'
  GROUP BY 1
)
SELECT
  -- [标识] biz_id / 客户号 / 放款日 / 产品 / 合同额 / V6_1 评级
  b.biz_id,
  b.mid,
  b.issue_date,
  b.product_level,
  b.contract_amount,
  b.android_oldCust_mainCreditLevel_charge_V6_1,

  -- [主额] 授予额度 / 放款前已占用 / 当前可用额度 / 单日可借上限 / 本笔占用主额(源口径) / 本笔支用
  b.credit_amount,
  b.change_used_grantamount,
  b.credit_amount - b.change_used_grantamount                        AS main_available_amount,
  CASE
    WHEN b.daily_max_available_limit IS NULL
      THEN COALESCE(s1077.daily_max_available_limit, b.daily_max_available_limit)
    WHEN b.daily_max_available_limit
         < COALESCE(b.risk_credit_limit, b.contract_amount - b.temp_used)
      THEN GREATEST(COALESCE(s1077.daily_max_available_limit, b.daily_max_available_limit),
                    b.daily_max_available_limit)
    ELSE b.daily_max_available_limit
  END                                                                AS daily_max_available_limit,
  COALESCE(b.risk_credit_limit,
           c003.main_used_this,
           usedm.main_used_this,
           b.contract_amount - COALESCE(b.temp_used, 0))             AS risk_credit_limit,
  COALESCE(c003.main_used_this,
           usedm.main_used_this,
           b.risk_credit_limit,
           b.contract_amount - COALESCE(b.temp_used, 0))             AS main_used_this,

  -- [离线临额] 授予额度 / 本笔放款时刻已占用 / 当前可用额度 / 本笔支用
  offm.offline_grant_amount,
  offm.offline_used_amount,
  GREATEST(offm.offline_grant_amount - offm.offline_used_amount, 0)  AS offline_available_amount,
  IF(c010.online_grant_amount IS NULL,
     COALESCE(b.temp_used, 0), 0)                                    AS offline_used_this,

  -- [在线临额] 产品上限 / 授予额度 / 已占用 / 当前可用额度 / 本笔支用
  CASE WHEN b.issue_date >= DATE '2026-10-19'
            AND b.product_level = 'D_1_03' THEN 15000 ELSE 10000 END AS product_limit_max,
  COALESCE(s857.online_grant_amount, c010.online_grant_amount, 0)     AS online_grant_amount,
  COALESCE(c010.online_used_amount, 0)                               AS online_used_amount,
  COALESCE(s857.online_grant_amount, c010.online_grant_amount, 0)
    - COALESCE(c010.online_used_amount, 0)                           AS online_available_amount,
  IF(c010.online_grant_amount IS NOT NULL,
     COALESCE(b.temp_used, 0), 0)                                    AS online_used_this,

  -- [三套逻辑可用额度] 分组：主额 + 离线临额
  -- 当前逻辑（含产品上限）
  LEAST(
    LEAST(b.credit_amount - b.change_used_grantamount,
          CASE
            WHEN b.daily_max_available_limit IS NULL
              THEN COALESCE(s1077.daily_max_available_limit, b.daily_max_available_limit)
            WHEN b.daily_max_available_limit
                 < COALESCE(b.risk_credit_limit, b.contract_amount - b.temp_used)
              THEN GREATEST(COALESCE(s1077.daily_max_available_limit, b.daily_max_available_limit),
                            b.daily_max_available_limit)
            ELSE b.daily_max_available_limit
          END)
      + GREATEST(offm.offline_grant_amount - offm.offline_used_amount, 0),
    CASE WHEN b.issue_date >= DATE '2026-10-19'
              AND b.product_level = 'D_1_03' THEN 15000 ELSE 10000 END
  )                                                                  AS avail_current_logic,
  -- 要改的逻辑（去除产品上限）
  LEAST(b.credit_amount - b.change_used_grantamount,
        CASE
          WHEN b.daily_max_available_limit IS NULL
            THEN COALESCE(s1077.daily_max_available_limit, b.daily_max_available_limit)
          WHEN b.daily_max_available_limit
               < COALESCE(b.risk_credit_limit, b.contract_amount - b.temp_used)
            THEN GREATEST(COALESCE(s1077.daily_max_available_limit, b.daily_max_available_limit),
                          b.daily_max_available_limit)
          ELSE b.daily_max_available_limit
        END)
    + GREATEST(offm.offline_grant_amount - offm.offline_used_amount, 0) AS avail_tochange_logic,
  -- 未来的逻辑（去除产品上限、去除单日可借上限）
  (b.credit_amount - b.change_used_grantamount)
    + GREATEST(offm.offline_grant_amount - offm.offline_used_amount, 0) AS avail_future_logic,

  -- [优惠券] 额度立减券（用信确认页核销，抵减合同额；见 CTE5）
  --   contract_amount = main_used_this + 临额使用额 + voucher_limit
  COALESCE(vch.voucher_limit, 0)                                     AS voucher_limit,
  vch.voucher_id                                                     AS voucher_id

FROM base b
LEFT JOIN offm  ON offm.biz_id  = b.biz_id
LEFT JOIN c003  ON c003.biz_id  = b.biz_id
LEFT JOIN c010  ON c010.biz_id  = b.biz_id
LEFT JOIN usedm ON usedm.biz_id = b.biz_id
LEFT JOIN s1077 ON s1077.biz_id = b.biz_id
LEFT JOIN s857  ON s857.biz_id  = b.biz_id
LEFT JOIN vch   ON vch.biz_id   = b.biz_id
;
