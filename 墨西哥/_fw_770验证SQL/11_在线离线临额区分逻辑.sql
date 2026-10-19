-- ============================================================================
-- 在线临额 vs 离线临额 —— 区分逻辑（唯一权威口径）
-- ============================================================================
-- 结论：区分点只有一处 —— 额度变更事件表
--        ods_view_presto.s05_user_creditlimit_change_record
--   必带 limit_type='TEMP'（区分主额 MAIN / 临额 TEMP）
--
--   ┌──────────────────┬────────────────────────────┬────────┬──────────────┐
--   │ change_event_type│ 含义                        │ 粒度   │ 触发时点      │
--   ├──────────────────┼────────────────────────────┼────────┼──────────────┤
--   │ C010             │ 在线临额(用信确认页实时发放) │ 笔级   │ 用户点"使用"  │
--   │ C015             │ 离线临额(营销系统批量圈客)   │ 名单级 │ 批量推送      │
--   │ C013             │ 离线临额(开发人工补发/修单)  │ 名单级 │ 人工          │
--   └──────────────────┴────────────────────────────┴────────┴──────────────┘
--
-- ⚠️ 两个常见错误，务必避免：
--   ① 不能用 temp_grant_amount 区分！它 = 本笔实际使用临额，已把在线+离线池
--      混合在一起（funnel 与 yj_test_table_250225 逐笔100%相等，都是这个含义）。
--   ② 不能用 temp_credit_amount_issue_tag 当"发放"！它是决策层"弹窗展示"标签，
--      展示≠使用，约一半 tag=1 并未真正产生临额（无 C010）。
--      → 要判"在线临额发放/使用"，用 C010；要判"展示"用 tag。
-- ============================================================================


-- ---------------------------------------------------------------------------
-- Step1【事件级】按事件码直接分来源（最小逻辑，一眼看懂）
-- ---------------------------------------------------------------------------
SELECT
  mid,
  external_id,                       -- 在线: C010 的 external_id = biz_id；离线: 通常为空
  change_event_type,
  CASE change_event_type
      WHEN 'C010' THEN '在线临额'
      WHEN 'C015' THEN '离线临额'
      WHEN 'C013' THEN '离线临额(人工)'
  END AS temp_source,
  change_total_grantamount,                                    -- 名义发放额
  change_used_grantamount,                                     -- 发放前存量占用
  change_total_grantamount - change_used_grantamount AS real_grant,  -- 实到账临额
  create_time,                                               -- 发放时刻(在线=用信时刻)
  expiring_time                                              -- 到期(在线=发放+3天)
FROM ods_view_presto.s05_user_creditlimit_change_record
WHERE limit_type = 'TEMP'
  AND change_event_type IN ('C010','C013','C015');


-- ---------------------------------------------------------------------------
-- Step2【笔级】把每笔放款归入 在线 / 离线 / 混合 / 无
--   在线匹配: biz_id = C010.external_id           (笔级精确)
--   离线匹配: mid + 放款前7天内最近一笔 C013/C015  (名单级; 无C014过期事件, 7天近似有效期)
-- ---------------------------------------------------------------------------
WITH loan_base AS (
  SELECT mid, biz_id, app_time
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
online_grant AS (                    -- 该笔 biz 命中过 C010
  SELECT DISTINCT cast(loan_base.biz_id as bigint) AS biz_id
  FROM loan_base
  JOIN ods_view_presto.s05_user_creditlimit_change_record credit_change
    ON cast(loan_base.biz_id as varchar) = credit_change.external_id
  WHERE credit_change.limit_type='TEMP' AND credit_change.change_event_type='C010'
),
offline_grant AS (                   -- 该笔 mid 在放款前7天内被离线批量发过临额
  SELECT DISTINCT cast(loan_base.mid as bigint) AS mid
  FROM loan_base
  JOIN ods_view_presto.s05_user_creditlimit_change_record credit_change
    ON cast(loan_base.mid as bigint) = cast(credit_change.mid as bigint)
   AND credit_change.limit_type='TEMP' AND credit_change.change_event_type IN ('C013','C015')
   AND credit_change.create_time <= loan_base.app_time
   AND loan_base.app_time < credit_change.create_time + interval '7' day
)
SELECT
  CASE
    WHEN online_grant.biz_id IS NOT NULL AND offline_grant.mid IS NOT NULL THEN '混合(在线+离线)'
    WHEN online_grant.biz_id IS NOT NULL                                   THEN '在线临额'
    WHEN offline_grant.mid   IS NOT NULL                                   THEN '离线临额'
    ELSE '无临额'
  END AS temp_source_grp,
  COUNT(*) AS loan_cnt
FROM loan_base
LEFT JOIN online_grant  ON cast(loan_base.biz_id as bigint) = online_grant.biz_id
LEFT JOIN offline_grant ON cast(loan_base.mid as bigint)    = offline_grant.mid
GROUP BY 1 ORDER BY 1;


-- ---------------------------------------------------------------------------
-- Step3【金额】分别取在线发放额 / 离线发放额（两列独立，不再用单一混合字段）
--   在线发放额 = C010.change_total_grantamount
--   离线发放额 = C013/C015.change_total_grantamount
--   实际使用额 = temp_grant_amount（= FREEZE_LIMIT 的 TEMP 冻结额）—— 与来源无关，单独一列
-- ---------------------------------------------------------------------------
WITH loan_base AS (
  SELECT mid, biz_id, app_time, temp_grant_amount AS used_temp
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
online_grant AS ( -- 该笔在线发放额（C010 名义发放）
  SELECT sub.biz_id, SUM(sub.amt) AS online_grant FROM (
    SELECT DISTINCT cast(loan_base.biz_id as bigint) AS biz_id, credit_change.external_id, credit_change.change_total_grantamount AS amt
    FROM loan_base
    JOIN ods_view_presto.s05_user_creditlimit_change_record credit_change
      ON cast(loan_base.biz_id as varchar) = credit_change.external_id
    WHERE credit_change.limit_type='TEMP' AND credit_change.change_event_type='C010'
  ) sub GROUP BY sub.biz_id
),
offline_grant AS ( -- 该笔离线发放额（放款前7天内最近一笔 C013/C015）
  SELECT sub.mid, sub.amt AS offline_grant FROM (
    SELECT cast(loan_base.mid as bigint) AS mid, credit_change.change_total_grantamount AS amt,
           loan_base.biz_id, row_number() OVER (PARTITION BY loan_base.biz_id ORDER BY credit_change.create_time DESC) rn
    FROM loan_base
    JOIN ods_view_presto.s05_user_creditlimit_change_record credit_change
      ON cast(loan_base.mid as bigint) = cast(credit_change.mid as bigint)
     AND credit_change.limit_type='TEMP' AND credit_change.change_event_type IN ('C013','C015')
     AND credit_change.create_time <= loan_base.app_time
     AND loan_base.app_time < credit_change.create_time + interval '7' day
  ) sub WHERE rn=1
),
offline_grant_biz AS (
  SELECT loan_base.biz_id, offline_grant.offline_grant
  FROM offline_grant JOIN loan_base ON offline_grant.biz_id = loan_base.biz_id
)
SELECT
  loan_base.biz_id,
  online_grant.online_grant,                    -- 在线临额发放额(名义)
  offline_grant_biz.offline_grant,              -- 离线临额发放额
  loan_base.used_temp                           -- 本笔实际使用临额(=temp_grant_amount, 不分来源)
FROM loan_base
LEFT JOIN online_grant      ON cast(loan_base.biz_id as bigint) = online_grant.biz_id
LEFT JOIN offline_grant_biz ON loan_base.biz_id = offline_grant_biz.biz_id;

-- ---------------------------------------------------------------------------
-- 备选：若已有 yj_test_table_250225，判"在线"可直接用它现成字段
--   在线发放 = temp_credit_amount_issue_tag = 1
--   在线使用 = temp_credit_amount_issue_tag = 1 AND temp_grant_amount > 0
--   （离线无现成 tag，仍必须回 change_record 按 C013/C015 打标）
-- ---------------------------------------------------------------------------


-- ============================================================================
-- 【字段版】四个字段一起产出（用户要的交付形态）
--   biz_id | offline_temp_tag(离线临额标签) | online_temp_tag(在线临额标签) | temp_grp(混合/在线/离线/无)
-- ----------------------------------------------------------------------------
-- 口径说明（务必注意）：
--   两个标签都是【持有/发放】口径，不是"实际使用"口径：
--     online_temp_tag  = 该笔 biz_id 命中过 C010 事件（笔级精确，external_id=biz_id）
--     offline_temp_tag = 该笔对应 mid 在放款前7天内被 C013/C015 发放过（名单级）
--   若还要"实际使用"口径，另加一列 used_temp = (temp_grant_amount>0)，勿混进标签。
--   两个标签相互独立、可单独过滤（混合组无法从单一字段反推两边内容）。
-- ============================================================================

-- 【可直接 LEFT JOIN 到你自己的 funnel 大SQL 的 CTE】
--   用法： with ..., temp_tag as ( <下面整段> )  ...  left join temp_tag on loan_base.biz_id = temp_tag.biz_id
with
loan_base as (
  select cast(biz_id as varchar) as biz_id, mid, app_time
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
online_grant as (      -- 在线临额发放：该 biz_id 有 C010 事件
  select distinct cast(loan_base.biz_id as varchar) as biz_id
  from loan_base
  join ods_view_presto.s05_user_creditlimit_change_record credit_change
    on cast(loan_base.biz_id as varchar) = credit_change.external_id
  where credit_change.limit_type='TEMP' and credit_change.change_event_type='C010'
),
offline_grant as (     -- 离线临额发放：该笔 mid 在 app_time 前7天内有 C013/C015 发放
  select distinct cast(loan_base.biz_id as varchar) as biz_id
  from loan_base
  join ods_view_presto.s05_user_creditlimit_change_record credit_change
    on cast(loan_base.mid as bigint) = cast(credit_change.mid as bigint)
   and credit_change.limit_type='TEMP' and credit_change.change_event_type in ('C013','C015')
   and credit_change.create_time <= loan_base.app_time
   and loan_base.app_time < credit_change.create_time + interval '7' day
),
temp_tag as (
  select
    cast(loan_base.biz_id as varchar) as biz_id,
    case when offline_grant.biz_id is not null then 1 else 0 end as offline_temp_tag,  -- 离线临额标签
    case when online_grant.biz_id is not null then 1 else 0 end as online_temp_tag,    -- 在线临额标签
    case when online_grant.biz_id is not null and offline_grant.biz_id is not null then '混合'
         when online_grant.biz_id is not null then '在线'
         when offline_grant.biz_id is not null then '离线'
         else '无' end as temp_grp                                      -- 是否在线离线混合无
  from loan_base
  left join online_grant  on cast(loan_base.biz_id as varchar) = online_grant.biz_id
  left join offline_grant on cast(loan_base.biz_id as varchar) = offline_grant.biz_id
)
select biz_id, offline_temp_tag, online_temp_tag, temp_grp
from temp_tag;

-- 【验证结果】四字段(按 biz_id 逐笔)口径(9/1-10/15 复贷放款 57,497 笔):
--   在线 5,667 / 离线 12,133 / 混合 717 / 无 38,980，合计 57,497
--   两标签组合矩阵(独立不互污)：00=38980 / 01=5667 / 10=12133 / 11=717
-- ⚠️ 与 Step2 的差异说明：本表离线标签 = "该笔自身 mid 在此笔 app_time 前7天内被发放"，
--    逐笔精确；Step2 的离线用 mid 级粗匹配(只要该mid任一笔落窗就整户标记)会多算，以本表为准。


-- ============================================================================
-- 【字段版 v2】再加两个字段（区分"离线是否已过期"和"离线过期后用在线临额"）
--   biz_id | offline_temp_tag | offline_expired | online_temp_tag
--          | online_used_after_offline_expired | temp_grp2
-- ----------------------------------------------------------------------------
-- 新增口径：
--   offline_expired  = 持有离线标签(7天内) 且 该离线发放的 expiring_time <= 放款时刻
--                      → 离线临额在放款时已过期（系统无 C014，用发放记录的 expiring_time 判）
--   online_used_after_offline_expired = offline_expired=1 且 online_temp_tag=1 且 实际用了临额
--                      → 这类资产"名义有离线、实际用的是在线临额"（离线已死、online顶上）
--   temp_grp2 细化：真正混合只在"离线仍有效"时才叫混合；
--                   离线已过期 + 在线 → 归 '在线(离线已过期)'
-- ============================================================================
with
loan_base as (
  select cast(biz_id as varchar) as biz_id, mid, app_time,
         temp_grant_amount as used_temp
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
online_grant as (
  select distinct cast(loan_base.biz_id as varchar) as biz_id
  from loan_base
  join ods_view_presto.s05_user_creditlimit_change_record credit_change
    on cast(loan_base.biz_id as varchar) = credit_change.external_id
  where credit_change.limit_type='TEMP' and credit_change.change_event_type='C010'
),
offline_last_grant as (   -- 7天窗口内最近一笔离线发放(带有效期)
  select biz_id, expiring_time from (
    select cast(loan_base.biz_id as varchar) as biz_id, credit_change.expiring_time,
           row_number() over (partition by loan_base.biz_id order by credit_change.create_time desc) rn
    from loan_base
    join ods_view_presto.s05_user_creditlimit_change_record credit_change
      on cast(loan_base.mid as bigint) = cast(credit_change.mid as bigint)
     and credit_change.limit_type='TEMP' and credit_change.change_event_type in ('C013','C015')
     and credit_change.create_time <= loan_base.app_time
     and loan_base.app_time < credit_change.create_time + interval '7' day
  ) sub where rn=1
)
select
  cast(loan_base.biz_id as varchar) as biz_id,
  case when offline_last_grant.biz_id is not null then 1 else 0 end as offline_temp_tag,
  case when offline_last_grant.biz_id is not null and offline_last_grant.expiring_time <= loan_base.app_time then 1 else 0 end as offline_expired,
  case when online_grant.biz_id is not null then 1 else 0 end as online_temp_tag,
  case when offline_last_grant.biz_id is not null and offline_last_grant.expiring_time <= loan_base.app_time
        and online_grant.biz_id is not null and loan_base.used_temp>0 then 1 else 0 end as online_used_after_offline_expired,
  case
    when online_grant.biz_id is not null and offline_last_grant.biz_id is not null and offline_last_grant.expiring_time > loan_base.app_time then '真混合'
    when online_grant.biz_id is not null and offline_last_grant.biz_id is not null then '在线(离线已过期)'
    when online_grant.biz_id is not null then '在线'
    when offline_last_grant.biz_id is not null and offline_last_grant.expiring_time > loan_base.app_time then '离线(有效)'
    when offline_last_grant.biz_id is not null then '离线(已过期)'
    else '无' end as temp_grp2
from loan_base
left join online_grant       on cast(loan_base.biz_id as varchar) = online_grant.biz_id
left join offline_last_grant on cast(loan_base.biz_id as varchar) = offline_last_grant.biz_id;

-- 【验证结果】(9/1-10/15 复贷放款 57,497 笔):
--   持有离线(7天内)合计 12,850 = 有效 9,544 + 已过期 3,306
--   真混合 442 / 在线(离线已过期) 275 / 纯在线 5,667 / 离线有效 9,102 / 离线已过期 3,031 / 无 38,980
--   online_used_after_offline_expired = 275（即：离线已死后改用在线临额的资产）


-- ============================================================================
-- 【时间轴宽表 v10】每笔放款一行，把"授信→提额预授权→评级→发放→使用→放款"完整链路+策略细节摊平
--   biz_id | 进件日期 | 进件app_time | 申请apply_time | 实际放款release_time | 间隔:进件→申请/申请→放款
--   【授信底数1067】授信额度 | 单日最大可借 | 授信有效期 | 7天期支用额(实测=授信额; 无28d/30d key)
--   【评级】V5_2(1500)/V5_3(1542)/V6_1(1635) | 评级迁徙V53-V52
--   【申请时主额链(change_record MAIN)】C002申请时提额 | C003MAIN预授权(对总额度, ≠支用)
--   【离线】发放时间/金额(C015实发) | 批量算额时刻/推荐额1504 | 使用时间/金额 | 当时状态 | 在线是否覆盖离线
--   【在线决策链】发放时间1386 | 评分1522 | type1523 | 策略分桶flag | 实验hash值/ABC组 | 弹窗tag
--          | 算额底数floor20(主额补全) | 理论比例 | ★实测比例 | 理论算额1379 | 决策树标签 | 弹窗额857 | 取整调整额 | 有效期
--          | 间隔:申请→弹窗/弹窗→领取/领取→放款 | C010使用时间/金额 | 弹窗领取状态 | 是否T+1批处理重跑
--   【占用与恒等式】C003冻结时刻 | TEMP占用 | 临额最终使用(在线/离线拆分)
--          | 合同金额 | 占用主额_used_detail原始 | 占用主额_补全(合同-临额) | 恒等式差额诊断
--   【v11 历史临额占用(仅在线来源笔)】历史临额占用金额(名义-实到账) | 历史结清后临额占用 | 历史未结清临额占用
--          | 历史占用台账还原差额_诊断(≈0即互证)
-- ----------------------------------------------------------------------------
-- 字段含义：
--   app_time     = 进件/建单时刻
--   apply_time   = 客户提交申请时刻
--   release_time = 实际放款时刻
--   ★ 在线临额「发放」与「使用」是两个不同时刻（2026-10-16 实测验证）：
--     发放 = modelmainid=1386「临额发放弹窗决策」的 createtime（决定 temp_credit_amount_issue_tag）
--     使用 = change_record 的 C010 create_time（客户在确认借款页点确认才创建）
--     实证：5,652 笔中发放恒早于使用（0 笔反序），中位间隔 92 秒，59.5% 间隔 >60 秒
--     依据：SKILL §1.1 决策顺序(授信→自选主额→临额发放弹窗 1386)；§1.2 C010=实际领取/使用
--   ★ 离线临额：发放 = C015/C013 批量推送时刻，使用 = C003 冻结时刻，同样分离
--   C003 冻结紧随 C010(毫秒级)；release 在其后约10分钟
--   ★【来源判定 2026-10-16 两次修复】在线/离线不再只看"本笔 biz 有无 C010"，改为
--     "本笔 C003 冻结时刻前 最近一次的临额发放事件(C010/C013/C015)"（见 temp_source CTE），且仅在本笔
--     真的用了临额(temp_grant_amount>0)时判定：
--       修复1：解决"同日同 mid 多次申请、在线临额由前面失败笔创建、却由后面成功笔消耗"被误判为离线；
--       修复2：解决"本笔根本没消耗、却挂上同 mid 更早一笔贷款的 C010/离线"（时间锚点改用 C003，加 temp>0 门槛）。
-- ============================================================================
-- <<WIDE_TABLE_SQL_BEGIN>>
-- ============================================================================
-- 【字段与命名规则】(2026-10-18 统一; 目的: 单看一处即可读懂, 不必来回翻查)
--   1) CTE 名 = 完整英文单词/词组, 不用缩写; 引用列一律写 "CTE名.列名", 不用单字母别名。
--   2) 口径前缀一眼定来源:
--        online_*  = 在线临额(C010)          offline_* = 离线临额(C013/C015)
--        temp_*    = 不分来源的临额(综合)     main_*    = 主额
--        credit_*  = 授信                     hist_*    = 历史占用
--   3) 列名优先沿用原表字段名(如 change_total_grantamount、expiring_time), 少造缩写。
--   4) 节点号写在列名尾部(_1067 / _1379 / _1504 / _857 ...), 便于回溯决策节点。
--   5) ★ 临额来源唯一判定点 = temp_source.event_type:
--        'C010' → 在线临额 ; 'C013'/'C015' → 离线临额
--        (同表 temp_source_grp 直接给出中文值, 后续所有"在线/离线"列均按此二分)
-- ============================================================================
-- ★ 建表: 大宽表 → mx.tmp_online_temp_limit_wide (窗口 2026-07-01 ~ 2026-10-15)
--   整段直接执行即可: CTAS 只跑作业、不回拉结果集, 因此不受 ad-hoc 结果集 1 万行网关限制。
--   若想当普通查询看数, 删掉下面 CREATE TABLE 这一行(只留 with … select)即可。
CREATE TABLE mx.tmp_online_temp_limit_wide AS
with
-- ① 放款基础表(进件/申请/放款时刻 + 合同额 + 本笔实际使用临额)
loan_base as (
  select cast(biz_id as varchar) as biz_id, mid, app_time, app_date, apply_time, release_time,
         contract_amount,
         temp_grant_amount as temp_grant        -- ★ 本笔实际使用临额；=0 即"本笔不是临额笔"
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-07-01' and app_date < date'2026-10-16'
),
-- ② 本笔临额冻结时刻(C003 TEMP, 即"临额使用时刻") —— 来源判定的时间锚点
temp_freeze as (
  select cast(loan_base.biz_id as varchar) as biz_id,
         min(credit_change.create_time) as freeze_time
  from loan_base
  join ods_view_presto.s05_user_creditlimit_change_record credit_change
    on cast(loan_base.biz_id as varchar) = credit_change.external_id
  where credit_change.limit_type='TEMP' and credit_change.change_event_type='C003'
    -- ★ 补时间窗: 无窗 → change_record 全分区扫描 → Hive Metastore 元数据拉取超时(Read timed out)
    and credit_change.create_time >= timestamp '2026-06-30' and credit_change.create_time < timestamp '2026-10-17'
  group by 1
),
-- ③ 离线临额发放(C013/C015) —— 本笔申请时刻前最近一笔
offline_grant as (
  -- ★ 锚点必须用"申请时刻"apply_time，不能用"进件时刻"app_time！
  --   反例 biz 1620000463039322：app_time=09-04 09:38（进件），apply_time=09-09 08:45（申请），
  --   中间 09-09 02:30/04:16 才发了两笔离线(C015 900 / C013 600)，本笔实际用的正是它们；
  --   用 app_time 当锚点会取到 08-25 那笔已过期的 1150，把"真离线使用"误判成"离线已过期"。
  -- ★【修复 2026-10-16】增加 loan_base.temp_grant>0 门槛：本笔没用临额(temp_grant=0)时，
  --   不该再回溯"历史上某笔离线/在线"挂到本笔上（否则会出现"10/08 的笔挂着 08/18 的过期离线"）。
  select biz_id, grant_time, grant_amount, expire_time from (
    select cast(loan_base.biz_id as varchar) as biz_id,
           credit_change.create_time as grant_time,
           credit_change.change_total_grantamount as grant_amount,
           credit_change.expiring_time as expire_time,
           row_number() over (partition by loan_base.biz_id order by credit_change.create_time desc) rn
    from loan_base
    join ods_view_presto.s05_user_creditlimit_change_record credit_change
      on cast(loan_base.mid as bigint) = cast(credit_change.mid as bigint)
     and credit_change.limit_type='TEMP' and credit_change.change_event_type in ('C013','C015')
     and credit_change.create_time <= loan_base.apply_time
    where loan_base.temp_grant > 0
      -- ★ 补时间窗(同 ②): 无窗 → change_record 全分区扫描 → Metastore 超时
      and credit_change.create_time >= timestamp '2026-06-30' and credit_change.create_time < timestamp '2026-10-17'
  ) t where rn=1
),
-- ④ ★ 本笔临额实际来源 = 本笔 C003 冻结时刻前 最近一次的临额发放事件(C010/C013/C015)
--    口径区分: event_type='C010' → 在线临额 ; 'C013'/'C015' → 离线临额(见 temp_source_grp)
temp_source as (
  --   【修复1 2026-10-16】原按 biz_id=external_id 只匹配本笔 C010，会漏掉"同日同 mid 多次申请"场景：
  --   biz 1620000483074755 同日连续申请4笔，前3笔失败(C008 释额)，在线临额 C010(400) 是第1笔
  --   失败申请(biz 1620000481078667)点确认时创建、挂在同一临额账户上，最终被本笔成功放款冻结消耗；
  --   本笔自身无 C010(external_id 属前一笔)，按 biz_id 匹配会把它误判成"离线"。
  --   【修复2 2026-10-16】时间锚点由 release_time 收紧为"本笔 C003 冻结时刻(缺则回退 release_time)"，
  --   并加 temp_grant>0 门槛。原用 release_time 会把"本笔根本没消耗、只是历史上同 mid 更早的发放"
  --   （如 biz 1620000479377160：10/08 的笔、temp_grant=0，却挂上 09/30 另一笔的 C010 2000）误当成本笔来源。
  select biz_id, event_type, temp_source_grp, grant_time, grant_amount, stock_occupy_amount, limit_main_id from (
    select cast(loan_base.biz_id as varchar) as biz_id,
           credit_change.change_event_type as event_type,
           case when credit_change.change_event_type = 'C010' then '在线临额' else '离线临额' end as temp_source_grp,
           credit_change.create_time as grant_time,
           credit_change.change_total_grantamount as grant_amount,
           credit_change.change_used_grantamount as stock_occupy_amount,  -- 发放前该账户存量占用
           credit_change.limit_main_id as limit_main_id,
           row_number() over (partition by loan_base.biz_id order by credit_change.create_time desc) rn
    from loan_base
    left join temp_freeze on loan_base.biz_id = temp_freeze.biz_id
    join ods_view_presto.s05_user_creditlimit_change_record credit_change
      on cast(loan_base.mid as bigint) = cast(credit_change.mid as bigint)
     and credit_change.limit_type='TEMP' and credit_change.change_event_type in ('C010','C013','C015')
     and credit_change.create_time <= coalesce(temp_freeze.freeze_time, loan_base.release_time)
    where loan_base.temp_grant > 0
      -- ★ 补时间窗(同 ②): 无窗 → change_record 全分区扫描 → Metastore 超时
      and credit_change.create_time >= timestamp '2026-06-30' and credit_change.create_time < timestamp '2026-10-17'
  ) t where rn=1
),
-- ⑤ 在线临额"发放"时刻 = model 1386 弹窗决策 且 确实发放(issue_tag=1)
online_issue as (
  select biz_id, min(createtime) as issue_time
  from ods.s21_risk_model_record
  where modelmainid=1386 and strategytype='CHAMPION'
    -- 关键：必须过滤 issue_tag=1，否则 1386 跑过但未发放(tag=0)会被误填成"发放时间"
    and outputdata like '%"temp_credit_amount_issue_tag":1%'
    -- 补时间窗(与 ⑥⑦⑧ 同口径): 1386 与 1379 同链路, createtime≈apply 时刻, 前后各放宽即可;
    --   ★ 必须带窗: 否则按网关 1 万行切片跑全时段时, 每片都全表扫描 s21, 耗时会放大数十倍
    and createtime >= timestamp '2026-06-30' and createtime < timestamp '2026-10-17'
  group by biz_id
),
-- ⑥ ★★ 在线临额用信决策链五节点底数(CHAMPION, 一次扫描条件聚合)
online_decision as (
  --   链路: 1522(用信评分 fd_use_creditamount_score_v1, -4~5)
  --      → 1523(用信临额类型 fd_use_creditamount_type, 1优/2/3/4差)
  --      → 1386(弹窗发放 tag 0/1; outputdata 只有 tag)
  --      → 1379(理论算额: temp_credit_amount=未取整理论额, expired_day=3, decision_tree_label=1)
  --      → 857 (弹窗最终发放额 temp_credit_amount; 同一857节点还写其他变量见 credit_grant/注释)
  --   ★ 算额公式(2026-10-16 全量 14,177 笔验证, 99.87% 精确命中):
  --       theo_amount_1379 = floor(占用主额MAIN冻结 / 20) × 20 × 理论发放比例
  --     · 底数 = 占用主额向下取整到 20 比索档(MAIN 冻结常带 1~19 比索零头, 如 2179→2160)
  --     · 比例: type2=40% / type3=20% 全策略一致;
  --             type1 = V5_2 50% / V5_3 60%(★ V5_3 把最优档比例上调 10pp, yj flag 关联 100% 证实)
  --     · type4 原则不发(tag=0, 1379=null); 仅 10 笔边界(保底400/切档)有值
  --   ★ 取整规则: final_amount_857 = round(theo_amount_1379 / 50) × 50(四舍五入到 50 比索档), 14,177 笔 100% 命中
  --     例: biz 1620000462179690 type2: floor(1180/20)*20×40%=472 → round(472/50)*50=450 = C010名义额
  --   ★ final_amount_857 == C010.change_total_grantamount(名义发放额), 已领取笔 100% 相等
  --   ⚠️ tag=0 时 1379=null、857 照跑输出 temp_credit_amount=0 → 用 nullif(...,0) 剔除
  --   ⚠️ 1379 每笔算两次(一次有额/一次全 null), max() 聚合自动取有值那条
  select cast(biz_id as varchar) as biz_id,
         max(case when modelmainid=1522 then cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_score_v1":(-?[0-9.]+)',1) as double) end) as score_v1_1522,
         max(case when modelmainid=1523 then cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_type":([0-9.]+)',1) as double) end) as use_type_1523,
         max(case when modelmainid=1386 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_issue_tag":([0-9.]+)',1) as double) end) as issue_tag_1386,
         max(case when modelmainid=1379 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double) end) as theo_amount_1379,
         max(case when modelmainid=1379 then cast(regexp_extract(cast(outputdata as varchar),'"decision_tree_label":([0-9]+)',1) as integer) end) as tree_label_1379,
         max(case when modelmainid=1379 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_expired_day":([0-9]+)',1) as integer) end) as expire_day_1379,
         max(case when modelmainid=857  then nullif(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double),0) end) as final_amount_857
  from ods.s21_risk_model_record
  where strategytype='CHAMPION'
    and modelmainid in (1522,1523,1386,1379,857)
    -- 窗口比 loan_base 窗口前后各放宽1天: 10/13-15的部分申请唯一一条CHAMPION决策是 10/16凌晨 T+1批处理重跑
    -- (2026-10-16 实测11笔, createtime 00:00-02:00), 上界截到10/16会漏; 下界同理留余量
    and createtime >= timestamp '2026-06-30' and createtime < timestamp '2026-10-17'
  group by 1
),
-- ⑦ 三套主额评级(用信决策时同时落库, CHAMPION): 1500=V5_2 / 1542=V5_3 / 1635=V6_1(整数, 1优→差)
main_grade as (
  --   即 fd_use_creditamount_type 决策矩阵的行变量(见 SKILL §7); 覆盖率 57,908/57,913=99.99%
  select cast(biz_id as varchar) as biz_id,
         max(cast(regexp_extract(cast(outputdata as varchar),'"android_oldCust_mainCreditLevel_charge_V5_2":([0-9]+)',1) as integer)) as grade_v5_2_1500,
         max(cast(regexp_extract(cast(outputdata as varchar),'"android_oldCust_mainCreditLevel_charge_V5_3":([0-9]+)',1) as integer)) as grade_v5_3_1542,
         max(cast(regexp_extract(cast(outputdata as varchar),'"android_oldCust_mainCreditLevel_charge_V6_1":([0-9]+)',1) as integer)) as grade_v6_1_1635
  from ods.s21_risk_model_record
  where strategytype='CHAMPION' and modelmainid in (1500,1542,1635)
    and createtime >= timestamp '2026-06-30' and createtime < timestamp '2026-10-17' -- T+1凌晨批处理重跑, 放宽1天
  group by 1
),
-- ⑧ 授信节点 1067(覆盖率 100%)
credit_grant as (
  --   credit_amount=授信额度, daily_max=单日最大可借额度,
  --   grantcredit_7d_amount=7天期产品支用额(实测恒=credit_amount; 节点无28d/30d key, 2026-10-16 核实),
  --   credit_exp=授信有效期(天, 常见15/18/23/26/27/29/30)
  select cast(biz_id as varchar) as biz_id,
         max(cast(regexp_extract(cast(outputdata as varchar),'"credit_amount":([0-9.]+)',1) as double)) as credit_amount_1067,
         max(cast(regexp_extract(cast(outputdata as varchar),'"daily_max_available_limit":([0-9.]+)',1) as double)) as daily_max_1067,
         max(cast(regexp_extract(cast(outputdata as varchar),'"credit_amount_expired_day":([0-9]+)',1) as integer)) as credit_expire_day_1067,
         max(cast(regexp_extract(cast(outputdata as varchar),'"grantcredit_7d_amount":([0-9.]+)',1) as double)) as grant_credit_7d_1067
  from ods.s21_risk_model_record
  where modelmainid=1067
    and createtime >= timestamp '2026-06-30' and createtime < timestamp '2026-10-17' -- T+1凌晨批处理重跑, 放宽1天
  group by 1
),
-- ⑨ V5_2/V5_3 策略分桶(yj 现成 flag, 建表时按 apply_time 落; left join, yj 窗口外为 null)
strategy_bucket as (
  --   exp_hash = 实验分流 hash(口径见 SKILL §6): sha256('20260811'||credit_no||app_group_sha256) 前4位hex/65536 ∈(0,1)
  --   9/3 后阈值: hash>0.7=A组(恒V5_2)、0.3<hash<=0.7=B组、hash<=0.3=C组(恒V5_3); flag 是生产实走桶, 二者互证
  select cast(biz_id as varchar) as biz_id,
         max(temp_credit_amount_strategy_test_flag) as strategy_flag,
         max(from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16))/65536.0 as exp_hash
  from mx.yj_test_table_250225
  -- ★ 补时间窗: 无窗 → yj 全分区扫描 → Metastore 超时; yj.app_date 与本笔 app_date 同日对应
  where app_date >= date'2026-06-30' and app_date < date'2026-10-17'
  group by 1
),
-- ⑩ ★ 离线临额批量算额节点 1504/1505(2026-10-16 新发现, 与在线 1379/857 对称)
offline_recommend as (
  --   每日 20-21 点批处理圈人, biz_id 为空、只按 mid 落库; 1504=temp_credit_amount 推荐额,
  --   1505=temp_credit_amount_expired_day(恒=5天)+label。窗口 9/1-10/14 共 28,573 次/10,865 mid。
  --   全量对账: 每条(>0) 都在 ±3 天内有同 mid C015 事件且时刻差≈0; 24,748/28,573=86.6% 金额完全相等,
  --   其余差额全为 50 的倍数(+50~+1200, 旧未过期临额叠加/凑档), 即 C015 实发 = 1504 推荐额 + 叠加凑档。
  --   ★ 1504 是"推荐额(算额)", 既不是发放也不是使用: 发放看 C015/C013, 使用看 used_temp 冻结。
  --   取数: 本 mid 在本笔 apply_time 前 3 天内最近一条(同 mid 同日可能 2 条, 20/21点各一轮, 取最晚)。
  select biz_id, recommend_amount_1504, recommend_time_1504 from (
    select cast(loan_base.biz_id as varchar) as biz_id,
           risk_record.createtime as recommend_time_1504,
           cast(regexp_extract(cast(risk_record.outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double) as recommend_amount_1504,
           row_number() over (partition by loan_base.biz_id order by risk_record.createtime desc) rn
    from loan_base
    join ods.s21_risk_model_record risk_record
      on cast(loan_base.mid as bigint) = cast(risk_record.mid as bigint)
     and risk_record.modelmainid=1504
     and risk_record.createtime > loan_base.apply_time - interval '3' day
     and risk_record.createtime <= loan_base.apply_time
     -- ★ 补时间窗: 无窗 → s21 全分区扫描 → Metastore 超时
     and risk_record.createtime >= timestamp '2026-06-30' and risk_record.createtime < timestamp '2026-10-17'
  ) t where rn=1
),
-- ⑪ 本笔实际冻结占用的临额(used_detail FREEZE TEMP)
used_temp as (
  select cast(used_detail.biz_id as varchar) as biz_id, sum(used_detail.risk_credit_limit) as temp_freeze_amount
  from ods.s05_user_creditlimit_used_detail used_detail
  join loan_base on cast(used_detail.biz_id as bigint) = cast(loan_base.biz_id as bigint)
  where used_detail.change_action='FREEZE_LIMIT' and used_detail.limit_type='TEMP'
    -- ★ 补时间窗: 无窗 → used_detail 全分区扫描 → Metastore 超时
    and used_detail.create_time >= timestamp '2026-06-30' and used_detail.create_time < timestamp '2026-10-17'
  group by 1
),
-- ⑫ 本笔实际冻结占用的主额(used_detail FREEZE MAIN) = 占用主额金额(有落库延迟, 见 ④b)
used_main as (
  select cast(used_detail.biz_id as varchar) as biz_id, sum(used_detail.risk_credit_limit) as main_freeze_amount
  from ods.s05_user_creditlimit_used_detail used_detail
  join loan_base on cast(used_detail.biz_id as bigint) = cast(loan_base.biz_id as bigint)
  where used_detail.change_action='FREEZE_LIMIT' and used_detail.limit_type='MAIN'
    -- ★ 补时间窗: 无窗 → used_detail 全分区扫描 → Metastore 超时
    and used_detail.create_time >= timestamp '2026-06-30' and used_detail.create_time < timestamp '2026-10-17'
  group by 1
),
-- ⑬ ★ 申请时刻主额链条(change_record MAIN, 2026-10-16 穿透)
main_change as (
  --   经典笔 462179690: C009 授信1500(app) → C002 申请时提额到2300(synthetic external)
  --     → C003 MAIN 预授权冻结2300(apply时刻, external_id=biz, 对"总额度"授权而非支用) → TEMP C010/C003
  --   注意: C003 MAIN 预授权额 ≠ 实际支用主额(后者在 used_main.main_freeze_amount);
  --     失败重申请场景 C002/C003 会被后续失败笔改写(…2769098: 成功后 01:36 失败3笔 C004 解冻+C002 降到28000),
  --     故 C002 只取 [app_time, apply_time+1min] 窗口内最后一笔, C003 只认 external_id=本biz。
  --   ⚠️ 两个事件必须拆成两个子查询分别带分区时间过滤再 union(OR join 无法裁剪会超时)。
  select biz_id, max(raise_c002) as raise_c002, max(authorize_c003) as authorize_c003 from (
    select cast(loan_base.biz_id as varchar) as biz_id,
           cast(null as double) as raise_c002,
           credit_change.change_total_grantamount as authorize_c003
    from loan_base
    join ods_view_presto.s05_user_creditlimit_change_record credit_change
      on credit_change.external_id = cast(loan_base.biz_id as varchar)
    where credit_change.limit_type='MAIN' and credit_change.change_event_type='C003'
      and credit_change.create_time >= timestamp '2026-06-30' and credit_change.create_time < timestamp '2026-10-17'
    union all
    select cast(loan_base.biz_id as varchar) as biz_id,
           credit_change.change_total_grantamount as raise_c002,
           cast(null as double) as authorize_c003
    from loan_base
    join ods_view_presto.s05_user_creditlimit_change_record credit_change
      on cast(loan_base.mid as bigint) = cast(credit_change.mid as bigint)
     and credit_change.create_time >= loan_base.app_time and credit_change.create_time <= loan_base.apply_time + interval '1' minute
    where credit_change.limit_type='MAIN' and credit_change.change_event_type='C002'
      and credit_change.create_time >= timestamp '2026-06-30' and credit_change.create_time < timestamp '2026-10-17'
  ) t group by 1
),
-- ⑭ 【v11 历史临额占用】在线来源笔的发放锚点(仅 event_type='C010')
hist_occ_source as (
  --   历史临额占用金额 = 名义发放 - 本次实到账 = C010.change_used_grantamount(发放前该账户存量占用, 定律见 ②)
  select loan_base.biz_id, temp_source.grant_time, temp_source.limit_main_id
  from loan_base join temp_source on loan_base.biz_id = temp_source.biz_id
  where temp_source.event_type = 'C010'
),
-- ⑮ 发放时刻(grant_time)前同账户 TEMP 台账(used_detail), 按来源biz 拆 resid=Σ冻结-Σ解冻
hist_occ_ledger as (
  --   resid>0.01 才算真正的占用来源(已完全解冻的历史笔 resid≈0 不计入)。
  --   下界放到 2026-01-01: 2-3月老贷冻结残留bug期(见 SKILL §1.3)也要能还原。
  select hist_occ_source.biz_id, hist_occ_source.grant_time, used_detail.biz_id as src_biz,
         sum(case when used_detail.change_action='FREEZE_LIMIT'   then used_detail.risk_credit_limit else 0 end)
       - sum(case when used_detail.change_action='UNFREEZE_LIMIT' then used_detail.risk_credit_limit else 0 end) as resid
  from hist_occ_source
  join ods.s05_user_creditlimit_used_detail used_detail
    on used_detail.limit_main_id = hist_occ_source.limit_main_id
   and used_detail.create_time < hist_occ_source.grant_time
  where used_detail.limit_type='TEMP'
    and used_detail.create_time >= timestamp '2026-01-01' and used_detail.create_time < timestamp '2026-10-17'
  group by 1,2,3
  having sum(case when used_detail.change_action='FREEZE_LIMIT'   then used_detail.risk_credit_limit else 0 end)
       - sum(case when used_detail.change_action='UNFREEZE_LIMIT' then used_detail.risk_credit_limit else 0 end) > 0.01
),
-- ⑯ 占用来源biz 的结清状态(s02_loan_repayment, 只取涉及来源笔)
hist_occ_repayment as (
  --   any_unpaid=0 且最后一笔还款时刻 < 发放时刻 => 该来源笔在发放时刻已结清 => "结清后占用"(冻结残留未释放)
  --   否则(在途 / 发放时刻后才结清 / 无还款记录) => "未结清占用"
  select cast(repayment.camera_id as bigint) as src_biz,
         max(case when repayment.state<>1 then 1 else 0 end) as any_unpaid,
         max(repayment.fact_time) as last_pay_time
  from ods_view_presto.s02_loan_repayment repayment
  where cast(repayment.camera_id as bigint) in (select distinct cast(src_biz as bigint) from hist_occ_ledger)
  group by 1
),
-- ⑰ 汇总到本笔: 台账合计 与 结清后/未结清 二分; 台账合计应≈C010.change_used_grantamount(互证)
hist_occ_summary as (
  select hist_occ_ledger.biz_id,
         round(sum(hist_occ_ledger.resid),2) as hist_occ_ledger,
         round(sum(case when repair.any_unpaid=0 and repair.last_pay_time < hist_occ_ledger.grant_time
                        then hist_occ_ledger.resid else 0 end),2) as hist_occ_settled,
         round(sum(case when coalesce(repair.any_unpaid,1)<>0 or repair.last_pay_time >= hist_occ_ledger.grant_time
                        then hist_occ_ledger.resid else 0 end),2) as hist_occ_open
  from hist_occ_ledger
  left join hist_occ_repayment repair on repair.src_biz = cast(hist_occ_ledger.src_biz as bigint)
  group by 1
)
-- ============================================================================
-- ★ 输出: 逐笔大宽表(输出列一律用英文字段名, 各列中文含义见行内注释)
-- ============================================================================
select loan_base.biz_id,
       loan_base.app_date            as app_date,  -- 进件日期
       loan_base.app_time            as app_time,  -- 进件时刻_app_time
       loan_base.apply_time          as apply_time,  -- 申请时刻_apply_time
       loan_base.release_time        as release_time,  -- 实际放款_release_time
       date_diff('second', loan_base.app_time, loan_base.apply_time)/60.0 as interval_app_to_apply_min,  -- 间隔_进件到申请_分钟
       date_diff('second', loan_base.apply_time, loan_base.release_time)/60.0 as interval_apply_to_release_min,  -- 间隔_申请到放款_分钟
       -- ===== 授信底数(credit_grant 1067) + 三套主额评级(main_grade 1500/1542/1635) =====
       credit_grant.credit_amount_1067   as credit_amount_1067,  -- 授信额度_credit_amount_1067
       credit_grant.daily_max_1067       as daily_max_amount_1067,  -- 单日最大可借额度_1067
       credit_grant.credit_expire_day_1067 as credit_expire_day_1067,  -- 授信有效期天数_1067
       credit_grant.grant_credit_7d_1067 as grant_credit_7d_amount_1067,  -- 7天期支用额_1067
       main_grade.grade_v5_2_1500        as main_grade_v5_2_1500,  -- 主额评级_V5_2_1500
       main_grade.grade_v5_3_1542        as main_grade_v5_3_1542,  -- 主额评级_V5_3_1542
       main_grade.grade_v6_1_1635        as main_grade_v6_1_1635,  -- 主额评级_V6_1_1635
       main_grade.grade_v5_3_1542 - main_grade.grade_v5_2_1500 as grade_migration_v53_minus_v52,  -- 评级迁徙_V53减V52
       -- ===== 申请时刻主额链条(main_change: 提额C002 → 预授权C003) =====
       main_change.raise_c002        as raise_main_c002,  -- 申请时主额提额_C002
       main_change.authorize_c003    as authorize_main_c003,  -- 申请时主额预授权_C003MAIN
       -- ===== 离线临额(offline_grant 发放 / offline_recommend 1504 推荐额) =====
       offline_grant.grant_time      as offline_grant_time,  -- 离线发放时间
       offline_grant.grant_amount    as offline_grant_amount,  -- 离线发放金额
       offline_recommend.recommend_time_1504   as offline_recommend_time_1504,  -- 离线批量算额时刻_1504
       offline_recommend.recommend_amount_1504 as offline_recommend_amount_1504,  -- 离线批量推荐额_1504; C015实发=推荐额+50倍数叠加(86.6%同额), 见 offline_recommend 注释
       -- 离线临额"使用"：用 C003 冻结时刻表示(离线发放=C015/C013, 使用=C003冻结)。
       --   本笔来源为离线(temp_source.event_type 非 C010) → 该笔 C003 冻结时刻即离线使用时刻;
       --   本笔来源为在线(event_type='C010') → 实际用的是在线临额, 离线仅持有未被消耗, 记空。
       case when coalesce(temp_source.event_type,'')='C010' then null else temp_freeze.freeze_time end as offline_use_time,  -- 离线使用时间
       -- 与"临额最终使用(离线临额)"同义: 来源为离线时 = 本笔实际用临额, 否则 = 0
       case when coalesce(temp_source.event_type,'')='C010' then 0 else loan_base.temp_grant/1000.0 end as offline_use_amount,  -- 离线使用金额
       case when offline_grant.biz_id is null then '无'
            when offline_grant.expire_time > loan_base.apply_time then '仍有效' else '已过期' end as offline_status_at_apply,  -- 离线当时状态
       -- 判断离线临额的额度是否被在线临额发放额覆盖(仅金额层对比, 不代表系统实际结算路径)
       case when offline_grant.biz_id is null or coalesce(temp_source.event_type,'')<>'C010' then '不适用'
            when temp_source.grant_amount >= offline_grant.grant_amount then '是(在线>=离线)'
            else '否(在线<离线)' end as online_covers_offline,  -- 在线是否覆盖离线
       -- ===== 在线临额(online_issue 发放时刻 / online_decision 决策链) =====
       online_issue.issue_time       as online_issue_time_1386,  -- 在线临额发放时间_model1386
       online_decision.score_v1_1522 as use_credit_score_1522,  -- 用信评分_score_v1_1522
       online_decision.use_type_1523 as use_credit_amount_type_1523,  -- 用信临额类型_type_1523
       strategy_bucket.strategy_flag as strategy_bucket_v52_v53,  -- 策略分桶_V52_V53
       strategy_bucket.exp_hash      as exp_hash,  -- 实验分流hash值
       case when strategy_bucket.exp_hash is null then null
            when strategy_bucket.exp_hash > 0.7 then 'A_恒V5_2'
            when strategy_bucket.exp_hash > 0.3 then 'B_中间组'
            else 'C_恒V5_3' end     as exp_group_after_0903,  -- 实验组分桶_9月3日后口径
       online_decision.issue_tag_1386 as issue_tag_1386,  -- 弹窗发放tag_1386
       floor(coalesce(used_main.main_freeze_amount, loan_base.contract_amount - loan_base.temp_grant/1000.0)/20.0)*20
                                     as calc_base_main_floor20,  -- 算额底数_占用主额floor20; =1379公式底数; used_detail延迟时用 合同-临额 恒等式补全
       -- 理论发放比例: type2=40%/type3=20% 全策略一致; type1 V5_2=50%/V5_3=60%(见 online_decision 注释)
       -- ⚠️ 切桶边界例外: yj flag 是建表时按 apply_time 落的桶, 与生产实走策略在灰度切换日(9/3)边界可能不一致
       --    (全窗口1笔 biz 1620000462632742: flag=V5_2 但实走0.6, 1379=540=900×0.6→857=550); 以实落值为准
       case when online_decision.use_type_1523=1 then case when strategy_bucket.strategy_flag like '%V5_3%' then 0.6 else 0.5 end
            when online_decision.use_type_1523=2 then 0.4
            when online_decision.use_type_1523=3 then 0.2 end   as theoretical_ratio,  -- 理论发放比例
       -- ★ 实测比例(不依赖 flag): 1379实落 / floor20底数; type1 全量只有 0.5 与 0.6 两个值
       online_decision.theo_amount_1379
         /nullif(floor(coalesce(used_main.main_freeze_amount, loan_base.contract_amount - loan_base.temp_grant/1000.0)/20.0)*20,0)
                                     as actual_ratio_1379_over_base,  -- 实测比例_1379除底数
       online_decision.theo_amount_1379 as theoretical_amount_1379,  -- 理论算额_1379_取整前
       online_decision.tree_label_1379  as decision_tree_label_1379,  -- 决策树标签_tree_label_1379
       -- 发放金额 = 857 弹窗最终发放额(挂 tag=1 门槛)；tag=1 未领取的笔也有金额(见 ② 口径)
       case when online_issue.issue_time is not null
            then coalesce(online_decision.final_amount_857,
                          case when temp_source.event_type='C010' then temp_source.grant_amount end) end as online_issue_amount_857,  -- 在线临额发放金额_857
       online_decision.final_amount_857 - online_decision.theo_amount_1379 as popup_round_adjust_round50,  -- 弹窗取整调整额_round50; =round(1379/50)*50-1379
       online_decision.expire_day_1379 as temp_expire_day_1379,  -- 在线临额有效期天数_1379
       date_diff('second', loan_base.apply_time, online_issue.issue_time) as interval_apply_to_issue_sec,  -- 间隔_申请到弹窗决策_秒
       case when temp_source.event_type='C010' then temp_source.grant_time end as online_use_time_c010,  -- 在线临额使用时间_C010
       case when temp_source.event_type='C010' then date_diff('second', online_issue.issue_time, temp_source.grant_time) end as interval_issue_to_use_sec,  -- 间隔_弹窗到领取_秒
       case when temp_source.event_type='C010' then date_diff('second', temp_source.grant_time, loan_base.release_time) end as interval_use_to_release_sec,  -- 间隔_领取到放款_秒
       case when temp_source.event_type='C010' then temp_source.grant_amount - temp_source.stock_occupy_amount end as online_use_amount_c010,  -- 在线临额使用金额_C010; 实到账额(名义-发放前存量占用)
       -- ===== 【v11】历史临额占用拆分(仅在线来源笔, 见 hist_occ_* CTE 与 ⑦ 口径) =====
       case when temp_source.event_type='C010' then temp_source.stock_occupy_amount end as hist_occupy_amount,  -- 历史临额占用金额; =名义发放-本次实到账=发放前账户存量占用
       case when temp_source.event_type='C010' then coalesce(hist_occ_summary.hist_occ_settled,0) end as hist_occupy_settled,  -- 历史结清后临额占用; 来源贷款发放时刻前已结清但冻结未释放的残留
       case when temp_source.event_type='C010' then coalesce(hist_occ_summary.hist_occ_open,0) end as hist_occupy_open,  -- 历史未结清临额占用; 来源贷款发放时刻仍在途的占用
       case when temp_source.event_type='C010' then round(temp_source.stock_occupy_amount - coalesce(hist_occ_summary.hist_occ_ledger,0),2) end as hist_occupy_ledger_diff_diag,  -- 历史占用台账还原差额_诊断; ≈0: 台账与C010字段互证; 非0: 明细延迟/异常
       -- 弹窗状态: tag0=无弹窗; tag1且本笔C010=已弹窗在线领取; tag1但本笔走离线=弹窗未领改用离线; tag1有额无使用=弹窗未领取
       case when online_issue.issue_time is null then '无弹窗(tag0)'
            when temp_source.event_type='C010' then '已弹窗_本笔在线领取'
            when loan_base.temp_grant > 0 then '弹窗未领_本笔走离线'
            else '已弹窗_未领取' end   as popup_claim_status,  -- 弹窗领取状态
       -- T+1: 决策落库日 > "申请日"(不是进件日! 进件→申请跨天占27.6%, 不算重跑); 重跑特指申请次日凌晨补跑
       case when online_issue.issue_time is not null and cast(online_issue.issue_time as date) > cast(loan_base.apply_time as date) then '是'
            when online_issue.issue_time is null then null else '否' end as is_t1_batch_rerun,  -- 决策是否T+1批处理重跑
       -- ===== 占用与恒等式 =====
       temp_freeze.freeze_time       as temp_freeze_time_c003,  -- 临额冻结时刻_C003
       used_temp.temp_freeze_amount  as temp_occupy_amount,  -- 临额占用金额
       loan_base.temp_grant/1000.0   as temp_final_use_amount,  -- 临额最终使用金额
       -- 按来源拆分"临额最终使用金额"(来源判定 = temp_source, 见 ④):
       --   event_type='C010' → 在线; 否则(C013/C015 或无发放) → 离线。不存在同时使用两类的情况(见 SKILL §1.3)。
       case when temp_source.event_type='C010' then loan_base.temp_grant/1000.0 else 0 end as temp_final_use_online,  -- 临额最终使用(在线临额)
       case when temp_source.event_type='C010' then 0 else loan_base.temp_grant/1000.0 end as temp_final_use_offline,  -- 临额最终使用(离线临额)
       loan_base.contract_amount     as contract_amount,  -- 合同金额_放款金额
       used_main.main_freeze_amount  as main_occupy_amount_raw,  -- 占用主额_used_detail原始; 有批次落库延迟(约1-6%/日, T+1/T+2补齐)
       coalesce(used_main.main_freeze_amount, loan_base.contract_amount - loan_base.temp_grant/1000.0)
                                     as main_occupy_amount_filled,  -- 占用主额金额_补全; 恒等式补全: 合同-临额最终使用; 全额临额笔=0
       loan_base.contract_amount - coalesce(used_main.main_freeze_amount, loan_base.contract_amount - loan_base.temp_grant/1000.0)
         - loan_base.temp_grant/1000.0 as identity_diff_diag  -- 恒等式差额_诊断; 0=used_detail与恒等式一致; 非0=明细延迟
from loan_base
left join offline_grant      on loan_base.biz_id = offline_grant.biz_id
left join temp_source        on loan_base.biz_id = temp_source.biz_id
left join temp_freeze        on loan_base.biz_id = temp_freeze.biz_id
left join online_issue       on cast(loan_base.biz_id as bigint) = online_issue.biz_id
left join online_decision    on loan_base.biz_id = online_decision.biz_id
left join main_grade         on loan_base.biz_id = main_grade.biz_id
left join credit_grant       on loan_base.biz_id = credit_grant.biz_id
left join strategy_bucket    on loan_base.biz_id = strategy_bucket.biz_id
left join offline_recommend  on loan_base.biz_id = offline_recommend.biz_id
left join used_temp          on loan_base.biz_id = used_temp.biz_id
left join used_main          on loan_base.biz_id = used_main.biz_id
left join main_change        on loan_base.biz_id = main_change.biz_id
left join hist_occ_summary   on loan_base.biz_id = hist_occ_summary.biz_id
;
-- <<WIDE_TABLE_SQL_END>>

-- 单笔校验 biz=1620000482922458：1386 tag=0 → 在线发放时间应为空；
--   该笔实为"离线使用"（C015 1100 于 10-13 发放、10-18 到期，10-15 11:15:20 冻结使用，全程无 C010）。

-- ----------------------------------------------------------------------------
-- 【字段口径：三个新增字段 + 一处锚点修复】(2026-10-16)
--   ① 在线是否覆盖离线：
--      规则 = 当离线(7天内)与在线(C010)都存在时，比较 在线名义发放额(C010) vs 离线名义发放额(C015/C013)；
--             temp_source.grant_amount >= offline_grant.grant_amount → '是(在线>=离线)'，否则 '否(在线<离线)'；缺一侧 → '不适用'。
--      含义 = 该笔已发的在线额是否足以整体顶掉离线额；仅"金额层"对比，不代表系统实际结算路径
--             （实际使用额恒等于本笔冻结额，见 ③）。金额均为"名义发放额"(change_total_grantamount)。
--   ② 在线临额决策链与金额三段式(底数→理论额→弹窗额)，全部落库可逐笔还原(online_decision CTE, 2026-10-16 全量穿透)：
--      ★ 节点链(CHAMPION, 毫秒级): 1522 评分 → 1523 type → 1386 tag → 1379 理论算额 → 857 弹窗最终额
--        · 1522 outputdata = {"fd_use_creditamount_score_v1":x}（用信评分 -4~5，只落总分；
--          两个构成分量 daily_left_amount_quota_use_rate / finish_total_num 不落库, 口径见 SKILL §5）
--        · 1523 = {"fd_use_creditamount_type":1~4}（1优/4差，决策矩阵产物）
--        · 1386 = {"temp_credit_amount_issue_tag":0/1}（只落 tag，不落金额）
--        · 1379 = {"temp_credit_amount_expired_day":3,"decision_tree_label":1,"temp_credit_amount":理论额}
--        · 857  = {"temp_credit_amount":弹窗最终额}（同节点还写 last_credit_amt_float/sd_disburse_amt_temp/
--          grantcredit_7d/28d_amount 等用信页其他变量, 与临额额无关, 取数按 key 正则过滤）
--      ★ 算额公式(14,177 笔, 99.87% 精确命中, 余 0.13% 为 type4 保底/切档边界):
--          理论算额_1379 = floor(占用主额 / 20) × 20 × 理论发放比例
--        · 底数 = 占用主额(MAIN 冻结)向下取整到 20 比索档（MAIN 常带 1~19 零头, 2179→2160；864=2160×40%）
--        · 比例: type2=40%、type3=20%（V5_2/V5_3 一致）；★ type1 = V5_2 50% / V5_3 60%
--          （V5_3 除放开评级档外, 另把最优档比例上调 10pp；yj flag 关联: V5_3桶 1,641 笔全 0.6、V5_2桶 1,147 笔全 0.5）
--        · type4 原则不发(tag=0, 1379=null)；仅 10 笔有值（7笔 MAIN=300 保底400、3笔切档边界按20%）
--      ★ 取整规则: 弹窗额_857 = round(理论算额_1379 / 50) × 50（四舍五入到 50 比索档），14,177 笔 100% 命中。
--        经典案例 biz 1620000462179690: MAIN=1180 → floor20=1180 ×40% = 472 → round50 = 450 = C010名义额 = TEMP冻结
--      ★ 金额三段式语义（别混用）:
--        理论算额1379(未取整) → 弹窗额857(名义发放, 客户看到/领取的上限) → C010实到账(名义−发放前存量占用)
--          = 本笔TEMP冻结 = 临额最终使用。biz 1620000464027012: 名义1300 但发放前存量占用1217.2 → 实到账82.8，
--          只看名义高估 15 倍（存量占用机制见 SKILL §1.3）。
--      ★ 已领取(C010) 6,432 笔: 857额 == C010.change_total_grantamount 100%。
--      ★ tag=1 未领取(无C010, 约占53%): 发放时间+弹窗额有值、使用列为空——"弹窗已发客户未领"
--        （1620000463197032: 250、550全主额；1620000466574256: 300、800全主额）。
--      ⚠️ tag=0 时 1379=null、857 照跑输出 temp_credit_amount=0（43,157 笔）→ online_decision 用 nullif(...,0)、
--        列上再挂 case when online_issue.issue_time is not null 双保险。
--      ⚠️ 只取 strategytype='CHAMPION'（SHADOW 为影子链路同步重跑一份, 值相同但不应入账）。
--   ②b 授信与评级底数(2026-10-16 新增):
--      · 授信节点1067(覆盖率100%): 授信额度 credit_amount、单日最大可借 daily_max_available_limit、
--        授信有效期 credit_amount_expired_day(常见15/27/29/30天)；同节点另有 grantcredit_7d_amount(实测恒=credit_amount, 无28d/30d key)。
--        注意 credit_amount ≠ daily_max（600/1500、7500/4500 均可出现），且二者都不等于"本笔占用主额"。
--      · 评级节点 1500/1542/1635 = android_oldCust_mainCreditLevel_charge_V5_2/V5_3/V6_1
--        （整数 1优→差；V5_2 值域 1~16, V5_3/V6_1 约 1~11/10；即 type 决策矩阵行变量, 覆盖率 99.99%）。
--   ③ 临额占用金额 = sum(used_detail.risk_credit_limit) where change_action='FREEZE_LIMIT' and limit_type='TEMP'
--      临额最终使用金额 = funnel.temp_grant_amount/1000.0
--      ★ 二者同指"本笔实际用掉的临额"，两侧互证：全量 9/1-10/16 复贷放款 57,817 笔中，
--        有 TEMP 冻结明细 11,624 笔、占用额 == 最终使用额（|差|<0.01）11,555 笔 = 99.4%；
--        剩 69 笔差额仅 ±0.05/±0.04（舍入）；另 337 笔"有使用但无冻结明细"= 明细未落库的数据延迟。
--   ③b 拆成 临额最终使用(在线临额) / 临额最终使用(离线临额)：
--      ★ 来源判定（两次修复定稿）= "仅当本笔真的用了临额(temp_grant_amount>0)，才取 本笔 C003 冻结时刻
--         (缺则 release_time) 前 最近一次的临额发放事件"（temp_source CTE）：
--         temp_source.event_type='C010' → 在线 = temp_grant、离线 = 0；否则(C013/C015 或无发放) → 在线 = 0、离线 = temp_grant。
--      修订1（废弃）本笔 biz 有 C010 才算在线：它会把"同日同 mid 多次申请、在线临额由前面失败笔
--      (biz 1620000481078667)创建、却由后面成功笔(biz 1620000483074755)消耗"误判成离线 → 170 笔改判。
--      修订2（新增）时间锚点由 release_time 收紧为 C003、并加 temp>0 门槛：原写法会把"本笔根本没消耗临额、
--      只是同 mid 更早一笔贷款的发放"挂到本笔上（反例 biz 1620000479377160：10/08、temp=0、全额走主额 2185，
--      却挂上 09/30 另一笔的 C010 2000）→ 修复后 45,856 笔无临额笔中 **25,033 笔**的临额列全部清空。
--      依据 = 临额实际使用额恒等于本笔冻结额；混合场景下不存在同时使用在线+离线两类（SKILL §1.3）。
--      全量核验：原 6,422 笔有 C010 中 6,394 笔(99.56%) C010实到账 == temp_grant（差额全为 ±0.05 舍入）。
--   ②c 离线临额批量算额节点 1504/1505（2026-10-16 新发现，与在线 1379/857 对称，offline_recommend CTE）：
--      · 每日 20-21 点批处理圈人：1504 落 temp_credit_amount 推荐额、1505 落 expired_day=5；
--        biz_id 为空、只按 mid 落库；同 mid 同日可能 2 条（20/21 点各一轮，取最晚）。
--      · 窗口 9/1-10/14 共 28,573 次推荐(>0)/10,865 个 mid，金额 0~9800、均值 1301；
--        每条推荐都在 ±3 天内配对到同 mid 的 C015（无 C013）、时刻差≈0 分钟——C015 即该批处理落账事件。
--      · C015 实发 = 推荐额 + 50 倍数的叠加/凑档：86.6%（24,748/28,573）完全相等，
--        其余差额全为 50 的倍数（+50~+1200，旧未过期临额叠加），无其他尾差。
--      · 宽表取"本 mid 在本笔 apply_time 前 3 天内最近一条"，与 offline_grant CTE 的 C015 实发额并列，可直接对账。
--   ③c 离线使用时间 / 离线使用金额（紧跟"离线发放时间/金额"，与在线"发放→使用"对称）：
--      离线临额的"使用"用 C003 冻结时刻表示（SKILL：离线发放=C015/C013，使用=C003冻结）。
--      离线使用时间 = 来源为离线时的 C003 冻结时刻（来源为在线 → 离线未被消耗，记空）；
--      离线使用金额 = 来源为离线时的 temp_grant_amount（来源为在线 → 0），与"临额最终使用(离线临额)"同义。
--      注：对纯离线使用笔，离线使用时间 == "临额冻结时刻_C003"；对在线笔/无临额笔为空。
--   ③d 【来源判定取数】temp_source = mid 关联 change_record(C010/C013/C015)、create_time <= coalesce(本笔C003, release_time)、
--      且 loan_base.temp_grant>0（门槛）→ row_number() 取最近一笔 → event_type；在线列(发放金额/使用时间/使用金额)仅在 event_type='C010' 时取值。
--      离线发放(offline_grant CTE)同样加 loan_base.temp_grant>0 门槛：本笔没用临额时不再回溯历史离线，避免"10/08 的笔挂着 08/18 的过期离线"。
--   ④ 合同金额_放款金额 = funnel.contract_amount
--      占用主额金额     = sum(used_detail.risk_credit_limit) where change_action='FREEZE_LIMIT' and limit_type='MAIN'
--      ★ 硬恒等式：contract_amount = 占用主额(MAIN冻结) + 临额占用/最终使用(TEMP冻结)，逐笔成立（见 SKILL §1.1）
--   ④b ⚠️ "占用主额金额"为空 **不等于** 数据缺失：本笔全额由临额覆盖时，used_detail 里根本没有 MAIN 冻结行，
--       主额冻结=0，恒等式仍成立（反例 biz 1620000474757589：合同450 = 0(主额) + 450(临额)）。全量 9/1-10/16：
--       747 笔占用主额为空中，**722 笔是"全额走临额"**（temp占用>0），仅 25 笔是"主额、临额都空"的真延迟。
--   ⑤ 【锚点修复】离线发放 anchor 由 app_time 改为 apply_time：
--      biz 1620000463039322（app_time 09-04 → apply_time 09-09，差 5 天）本笔实际用的是 09-09 04:16 发的
--      离线(C013 600)，用 app_time 会错取 08-25 那笔已过期的 1150 → 修复后：离线发放 09-09 04:16 / 600 / 仍有效。
--   ⑥ 【v10 大宽表扩展】(2026-10-16, 由 biz …2769098"无主额"下钻带出的整条主额链+策略细节):
--      ⑥a 申请时刻主额链(change_record MAIN, main_change CTE) —— 以前宽表只有"授信1067"和"支用used_detail", 中间缺两环:
--         C009(授信落账, 金额=1067 credit_amount) → C002 CHANGE_LIMIT(申请时提额, external_id 是合成串 mid_ts)
--         → C003 FREEZE(apply 时刻对"主额总额度"预授权, external_id=本biz)。
--         经典笔 462179690: C009 1500 → C002 2300 → C003 预授权 2300(used 1370), 实际支用 MAIN used_detail=1180。
--         ⚠️ C003 预授权额 ≠ 实际支用主额! 失败重申请场景 C002/C004 会被同 mid 后续失败笔改写
--            (…2769098: 成功 apply 01:28 预授权34000, 01:36 三笔失败 C004 解冻 + C002 降到28000),
--            故 C002 只取 [app_time, apply_time+1min] 窗口, C003 只认 external_id=本biz。
--      ⑥b used_detail MAIN 延迟是"无主额"假象的唯一来源, 每日都有(9月 76~85 笔/日, 与批处理/放款时点无关,
--         T+1/T+2 补齐), 不是真没占主额。补全列 = coalesce(used_detail MAIN, 合同金额 - 临额最终使用)
--         (硬恒等式); "恒等式差额_诊断" 0=一致, 非0=明细仍延迟。…2769098: 合同450-临额0=450 即真实主额支用。
--      ⑥c 60% 比例实锤"版本效应、非时间趋势": 实测比例 = amt_1379/floor20 直接落列, 不依赖 flag;
--         type1+tag1 全量仅 0.50/0.60 两值: yj V5_2桶 1,124 笔=0.50(仅1笔切桶边界=0.60)、V5_3桶 1,568 笔=0.60,
--         两比例在同一周内并存(周交叉: 每周 0.5 有 73~202、0.6 有 85~258, 无时间漂移)。实验 hash 列+ABC 组与 flag 互证。
--         公式最终命中率 13,738/13,746=99.94%(余 8 笔=type4 保底/切档+切桶边界+3 笔 1379 落 0)。
--      ⑥d 其他策略/状态列:
--         · 1379 decision_tree_label(决策树标签, 有值笔恒=1)、1067 grantcredit_7d_amount(7天期支用额, 实测恒=credit_amount; 节点无28d/30d key)
--         · 评级迁徙 V53−V52(V5_3 放开评级档的直接体现)
--         · 弹窗领取状态(无弹窗tag0 / 已弹窗本笔在线领取 / 弹窗未领本笔走离线 / 已弹窗未领取)
--         · 决策是否T+1批处理重跑(1386 createtime::date > 申请日; 不能比进件日, 进件→申请跨天占27.6%)
--         · 间隔: 进件→申请、申请→放款(分钟); 申请→弹窗、弹窗→C010领取、领取→放款(秒)
--   ⑥e 不入宽表的探查结论(信息低或误导):
--         · 节点1553 fd_temp_limit_creditlevel_from_tag: 覆盖率98.3%但 56,947/56,948 恒=1
--         · 节点1341 oldcust_creditlevel_version: 全量恒=V5_3(平台管线版本≠实验分桶, 与 0.5/0.6 无关)
--         · 857 节点无 last_credit_amt_float / sd_disburse_amt_temp key(0 覆盖)
--   ⑦ 【v11 历史临额占用拆分】(2026-10-17, 样例笔 biz 1620000465328686: 名义400/实到账93.75/历史占用306.25):
--      ⑦a 历史临额占用金额 = 名义发放(C010.change_total_grantamount) − 本次实到账 = C010.change_used_grantamount,
--         即发放前该 TEMP 账户的存量占用(账户级恒等式, 见 ② 与 SKILL §1.3)。仅对在线来源笔(event_type='C010')取值。
--      ⑦b 台账还原(hist_occ_source→hist_occ_ledger→hist_occ_repayment→hist_occ_summary): 取发放时刻(grant_time)前同账户(limit_main_id) TEMP 台账,
--         按来源biz 拆 resid=Σ冻结−Σ解冻(>0.01 才计入), 台账合计应≈change_used_grantamount;
--         "历史占用台账还原差额_诊断"≈0 即互证, 非0 为明细延迟/异常。
--      ⑦c 结清后/未结清二分: 来源贷款在发放时刻前已结清(any_unpaid=0 且最后一笔还款 fact_time < grant_time)
--         但冻结未释放 → "历史结清后临额占用"(2-3月残留bug 即此类); 否则(在途/后才结清/无还款记录) → "历史未结清临额占用"。
--         样例笔验证: 306.25 全部来自 biz 1620000460517829(4期, 发放时刻仍在途, 9/24 才结清) → 未结清306.25/结清后0。
-- ----------------------------------------------------------------------------
-- 【抽查核对】(已在 _verify_wide7.py 跑通 9 笔，字段顺序见上面 select)
--   biz_id             | 来源event_type | 离线发放               | 合同额 | 占用主额 | 在线名义C010 | 在线实到账C010 | 冻结C003           | 占用TEMP | 最终使用
--   1620000462179690   | C010在线  | 09-01 20:02 / 250 / 有效 | 1630  | 1180    | 450          | 450           | 09-01 21:05:04.588 | 450    | 450.0
--   1620000462287861   | C010在线  | 09-01 20:30 / 2800 有效 | 2100  | 1500    | 600          | 600           | 09-02 16:49:31.104 | 600    | 600.0
--   1620000463039322   | C013离线  | 09-09 04:16 / 600  有效  | 6200  | 5905.34 | (无C010)     | (无)          | 09-09 08:45:01.224 | 294.66 | 294.7
--   1620000464027012   | C010在线  | 08-25 20:30 / 3000 过期  | 6588.8| 6506    | 1300         | 82.8          | 09-06 23:50:05.170 | 82.8   | 82.8
--   1620000482922458   | C015离线  | 10-13 21:01 / 1100 有效  | 2600  | 1500    | (无C010)     | (无)          | 10-15 11:15:20.495 | 1100   | 1100.0
--   ★1620000483074755  | C010在线  | (无)                  | 2400  | 2000    | 400          | 400           | 10-15 15:02:29.958 | 400    | 400.0   ← 修订1案例(同日失败笔创建)
--   ★1620000474757589  | C015离线  | 09-29 21:30 / 450  有效  | 450   | (空=0)  | (无C010)     | (无)          | 10-02 15:09:27.772 | 450    | 450.0   ← ④b案例(全额临额,主额=0)
--   ★1620000479377160  | (无)      | (空)                  | 2185  | 2185    | (空)         | (空)          | (空)               | (空)   | 0.0     ← 修订2案例(无临额笔,原被污染)
--   恒等式全中：1630=1180+450、2100=1500+600、6200=5905.34+294.66、6588.8=6506+82.8、2600=1500+1100、2400=2000+400、450=0+450。
--   注：used_detail 明细有落库延迟（放款当日/次日可能取不到）；1620000482922458 本次重跑已落库(1500)。
-- ----------------------------------------------------------------------------
-- 【早期结论沿用】(9/1-10/16 全量)
--   ★ 打"在线临额发放时间"必须过滤 issue_tag=1：1386 决策跑过 56,872 笔，真正发放(tag=1)仅 13,715 笔，
--     其余 43,157 笔 tag=0(未发放)；若不过滤会把"未发放"误填成"发放时间"（单笔校验发现并修复）。
--   C010(实际使用/领取) 6,422 笔 = tag=1 的 46.8%（与 SKILL §1.2 的"仅 46% 真正使用"一致）。

