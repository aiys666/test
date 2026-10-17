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
WITH app AS (
  SELECT mid, biz_id, app_time
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
online AS (                          -- 该笔 biz 命中过 C010
  SELECT DISTINCT cast(a.biz_id as bigint) AS biz_id
  FROM app a
  JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.biz_id as varchar) = e.external_id
  WHERE e.limit_type='TEMP' AND e.change_event_type='C010'
),
offline AS (                         -- 该笔 mid 在放款前7天内被离线批量发过临额
  SELECT DISTINCT cast(a.mid as bigint) AS mid
  FROM app a
  JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON cast(a.mid as bigint) = cast(e.mid as bigint)
   AND e.limit_type='TEMP' AND e.change_event_type IN ('C013','C015')
   AND e.create_time <= a.app_time
   AND a.app_time < e.create_time + interval '7' day
)
SELECT
  CASE
    WHEN o.biz_id IS NOT NULL AND f.mid IS NOT NULL THEN '混合(在线+离线)'
    WHEN o.biz_id IS NOT NULL                      THEN '在线临额'
    WHEN f.mid    IS NOT NULL                      THEN '离线临额'
    ELSE '无临额'
  END AS temp_source_grp,
  COUNT(*) AS loan_cnt
FROM app a
LEFT JOIN online  o ON cast(a.biz_id as bigint) = o.biz_id
LEFT JOIN offline f ON cast(a.mid as bigint)    = f.mid
GROUP BY 1 ORDER BY 1;


-- ---------------------------------------------------------------------------
-- Step3【金额】分别取在线发放额 / 离线发放额（两列独立，不再用单一混合字段）
--   在线发放额 = C010.change_total_grantamount
--   离线发放额 = C013/C015.change_total_grantamount
--   实际使用额 = temp_grant_amount（= FREEZE_LIMIT 的 TEMP 冻结额）—— 与来源无关，单独一列
-- ---------------------------------------------------------------------------
WITH app AS (
  SELECT mid, biz_id, app_time, temp_grant_amount AS used_temp
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
),
online AS (      -- 该笔在线发放额（C010 名义发放）
  SELECT z.biz_id, SUM(z.amt) AS online_grant FROM (
    SELECT DISTINCT cast(a.biz_id as bigint) AS biz_id, e.external_id, e.change_total_grantamount AS amt
    FROM app a
    JOIN ods_view_presto.s05_user_creditlimit_change_record e
      ON cast(a.biz_id as varchar) = e.external_id
    WHERE e.limit_type='TEMP' AND e.change_event_type='C010'
  ) z GROUP BY z.biz_id
),
offline AS (     -- 该笔离线发放额（放款前7天内最近一笔 C013/C015）
  SELECT z.mid, z.amt AS offline_grant FROM (
    SELECT cast(a.mid as bigint) AS mid, e.change_total_grantamount AS amt,
           a.biz_id, row_number() OVER (PARTITION BY a.biz_id ORDER BY e.create_time DESC) rn
    FROM app a
    JOIN ods_view_presto.s05_user_creditlimit_change_record e
      ON cast(a.mid as bigint) = cast(e.mid as bigint)
     AND e.limit_type='TEMP' AND e.change_event_type IN ('C013','C015')
     AND e.create_time <= a.app_time
     AND a.app_time < e.create_time + interval '7' day
  ) z WHERE rn=1
),
off_map AS (
  SELECT b.biz_id, o.offline_grant
  FROM offline o JOIN app b ON o.biz_id = b.biz_id
)
SELECT
  a.biz_id,
  o.online_grant,                        -- 在线临额发放额(名义)
  m.offline_grant,                       -- 离线临额发放额
  a.used_temp                            -- 本笔实际使用临额(=temp_grant_amount, 不分来源)
FROM app a
LEFT JOIN online  o ON cast(a.biz_id as bigint) = o.biz_id
LEFT JOIN off_map m ON a.biz_id = m.biz_id;

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
--   用法： with ..., temp_tag as ( <下面整段> )  ...  left join temp_tag t on a.biz_id = t.biz_id
with
app as (
  select cast(biz_id as varchar) as biz_id, mid, app_time
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
online as (      -- 在线临额发放：该 biz_id 有 C010 事件
  select distinct cast(a.biz_id as varchar) as biz_id
  from app a
  join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.biz_id as varchar) = e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C010'
),
offline as (     -- 离线临额发放：该笔 mid 在 app_time 前7天内有 C013/C015 发放
  select distinct cast(a.biz_id as varchar) as biz_id
  from app a
  join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.mid as bigint) = cast(e.mid as bigint)
   and e.limit_type='TEMP' and e.change_event_type in ('C013','C015')
   and e.create_time <= a.app_time
   and a.app_time < e.create_time + interval '7' day
),
temp_tag as (
  select
    cast(a.biz_id as varchar) as biz_id,
    case when f.biz_id is not null then 1 else 0 end as offline_temp_tag,  -- 离线临额标签
    case when o.biz_id is not null then 1 else 0 end as online_temp_tag,   -- 在线临额标签
    case when o.biz_id is not null and f.biz_id is not null then '混合'
         when o.biz_id is not null then '在线'
         when f.biz_id is not null then '离线'
         else '无' end as temp_grp                                      -- 是否在线离线混合无
  from app a
  left join online  o on cast(a.biz_id as varchar) = o.biz_id
  left join offline f on cast(a.biz_id as varchar) = f.biz_id
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
app as (
  select cast(biz_id as varchar) as biz_id, mid, app_time,
         temp_grant_amount as used_temp
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
online as (
  select distinct cast(a.biz_id as varchar) as biz_id
  from app a
  join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.biz_id as varchar) = e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C010'
),
offline_last as (   -- 7天窗口内最近一笔离线发放(带有效期)
  select biz_id, expiring_time from (
    select cast(a.biz_id as varchar) as biz_id, e.expiring_time,
           row_number() over (partition by a.biz_id order by e.create_time desc) rn
    from app a
    join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint) = cast(e.mid as bigint)
     and e.limit_type='TEMP' and e.change_event_type in ('C013','C015')
     and e.create_time <= a.app_time
     and a.app_time < e.create_time + interval '7' day
  ) t where rn=1
)
select
  cast(a.biz_id as varchar) as biz_id,
  case when l.biz_id is not null then 1 else 0 end as offline_temp_tag,
  case when l.biz_id is not null and l.expiring_time <= a.app_time then 1 else 0 end as offline_expired,
  case when o.biz_id is not null then 1 else 0 end as online_temp_tag,
  case when l.biz_id is not null and l.expiring_time <= a.app_time
        and o.biz_id is not null and a.used_temp>0 then 1 else 0 end as online_used_after_offline_expired,
  case
    when o.biz_id is not null and l.biz_id is not null and l.expiring_time > a.app_time then '真混合'
    when o.biz_id is not null and l.biz_id is not null then '在线(离线已过期)'
    when o.biz_id is not null then '在线'
    when l.biz_id is not null and l.expiring_time > a.app_time then '离线(有效)'
    when l.biz_id is not null then '离线(已过期)'
    else '无' end as temp_grp2
from app a
left join online       o on cast(a.biz_id as varchar) = o.biz_id
left join offline_last l on cast(a.biz_id as varchar) = l.biz_id;

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
--     "本笔 C003 冻结时刻前 最近一次的临额发放事件(C010/C013/C015)"（见 src CTE），且仅在本笔
--     真的用了临额(temp_grant_amount>0)时判定：
--       修复1：解决"同日同 mid 多次申请、在线临额由前面失败笔创建、却由后面成功笔消耗"被误判为离线；
--       修复2：解决"本笔根本没消耗、却挂上同 mid 更早一笔贷款的 C010/离线"（时间锚点改用 C003，加 temp>0 门槛）。
-- ============================================================================
with
app as (
  select cast(biz_id as varchar) as biz_id, mid, app_time, app_date, apply_time, release_time,
         temp_grant_amount as temp_grant        -- ★ 本笔实际使用临额；=0 即"本笔不是临额笔"
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
frz as (   -- 本笔自身的冻结(C003, 即临额使用)时刻 —— 来源判定的时间锚点
  select cast(a.biz_id as varchar) as biz_id, min(e.create_time) as use_time
  from app a
  join ods_view_presto.s05_user_creditlimit_change_record e
    on cast(a.biz_id as varchar)=e.external_id
  where e.limit_type='TEMP' and e.change_event_type='C003'
  group by 1
),
off as (   -- 本笔持有/消耗的离线发放（放款前最近一笔离线）
  -- ★ 锚点必须用"申请时刻"apply_time，不能用"进件时刻"app_time！
  --   反例 biz 1620000463039322：app_time=09-04 09:38（进件），apply_time=09-09 08:45（申请），
  --   中间 09-09 02:30/04:16 才发了两笔离线(C015 900 / C013 600)，本笔实际用的正是它们；
  --   用 app_time 当锚点会取到 08-25 那笔已过期的 1150，把"真离线使用"误判成"离线已过期"。
  -- ★【修复 2026-10-16】增加 a.temp_grant>0 门槛：本笔没用临额(temp_grant=0)时，
  --   不该再回溯"历史上某笔离线/在线"挂到本笔上（否则会出现"10/08 的笔挂着 08/18 的过期离线"）。
  select biz_id, off_time, off_amt, off_exp from (
    select cast(a.biz_id as varchar) as biz_id, e.create_time as off_time,
           e.change_total_grantamount as off_amt, e.expiring_time as off_exp,
           row_number() over (partition by a.biz_id order by e.create_time desc) rn
    from app a
    join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint)=cast(e.mid as bigint)
     and e.limit_type='TEMP' and e.change_event_type in ('C013','C015')
     and e.create_time <= a.apply_time
    where a.temp_grant > 0
  ) t where rn=1
),
src as (   -- ★ 本笔临额的实际来源 = 本笔 C003 冻结时刻前 最近一次的临额发放事件(C010/C013/C015)
  --   【修复1 2026-10-16】原按 biz_id=external_id 只匹配本笔 C010，会漏掉"同日同 mid 多次申请"场景：
  --   biz 1620000483074755 同日连续申请4笔，前3笔失败(C008 释额)，在线临额 C010(400) 是第1笔
  --   失败申请(biz 1620000481078667)点确认时创建、挂在同一临额账户上，最终被本笔成功放款冻结消耗；
  --   本笔自身无 C010(external_id 属前一笔)，按 biz_id 匹配会把它误判成"离线"。故改用 mid + 时间锚点取最近一次发放。
  --   【修复2 2026-10-16】时间锚点由 release_time 收紧为"本笔 C003 冻结时刻(缺则回退 release_time)"，
  --   并加 temp_grant>0 门槛。原用 release_time 会把"本笔根本没消耗、只是历史上同 mid 更早的发放"
  --   （如 biz 1620000479377160：10/08 的笔、temp_grant=0，却挂上 09/30 另一笔的 C010 2000）误当成本笔来源。
  select biz_id, gtype, gtime, g_grant, g_used, g_lmid from (
    select cast(a.biz_id as varchar) as biz_id, e.change_event_type as gtype,
           e.create_time as gtime, e.change_total_grantamount as g_grant,
           e.change_used_grantamount as g_used, e.limit_main_id as g_lmid,
           row_number() over (partition by a.biz_id order by e.create_time desc) rn
    from app a
    left join frz z on cast(a.biz_id as varchar)=z.biz_id
    join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint)=cast(e.mid as bigint)
     and e.limit_type='TEMP' and e.change_event_type in ('C010','C013','C015')
     and e.create_time <= coalesce(z.use_time, a.release_time)
    where a.temp_grant > 0
  ) t where rn=1
),
iss as (   -- 在线临额"发放"时刻 = model1386 弹窗决策 且 确实发放(issue_tag=1)
  select biz_id, min(createtime) as issue_time
  from ods.s21_risk_model_record
  where modelmainid=1386 and strategytype='CHAMPION'
    -- 关键：必须过滤 issue_tag=1，否则 1386 跑过但未发放(tag=0)会被误填成"发放时间"
    and outputdata like '%"temp_credit_amount_issue_tag":1%'
  group by biz_id
),
dec as (   -- ★★ 在线临额用信决策链五节点底数(CHAMPION, 一次扫描条件聚合)
  --   链路: 1522(用信评分 fd_use_creditamount_score_v1, -4~5)
  --      → 1523(用信临额类型 fd_use_creditamount_type, 1优/2/3/4差)
  --      → 1386(弹窗发放 tag 0/1; outputdata 只有 tag)
  --      → 1379(理论算额: temp_credit_amount=未取整理论额, expired_day=3, decision_tree_label=1)
  --      → 857 (弹窗最终发放额 temp_credit_amount; 同一857节点还写其他变量见 crd/注释)
  --   ★ 算额公式(2026-10-16 全量 14,177 笔验证, 99.87% 精确命中):
  --       amt_1379 = floor(占用主额MAIN冻结 / 20) × 20 × 理论发放比例
  --     · 底数 = 占用主额向下取整到 20 比索档(MAIN 冻结常带 1~19 比索零头, 如 2179→2160)
  --     · 比例: type2=40% / type3=20% 全策略一致;
  --             type1 = V5_2 50% / V5_3 60%(★ V5_3 把最优档比例上调 10pp, yj flag 关联 100% 证实)
  --     · type4 原则不发(tag=0, 1379=null); 仅 10 笔边界(保底400/切档)有值
  --   ★ 取整规则: amt_857 = round(amt_1379 / 50) × 50(四舍五入到 50 比索档), 14,177 笔 100% 命中
  --     例: biz 1620000462179690 type2: floor(1180/20)*20×40%=472 → round(472/50)*50=450 = C010名义额
  --   ★ amt_857 == C010.change_total_grantamount(名义发放额), 已领取笔 100% 相等
  --   ⚠️ tag=0 时 1379=null、857 照跑输出 temp_credit_amount=0 → 用 nullif(...,0) 剔除
  --   ⚠️ 1379 每笔算两次(一次有额/一次全 null), max() 聚合自动取有值那条
  select cast(biz_id as varchar) as biz_id,
         max(case when modelmainid=1522 then cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_score_v1":(-?[0-9.]+)',1) as double) end) as dec_score,
         max(case when modelmainid=1523 then cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_type":([0-9.]+)',1) as double) end) as dec_type,
         max(case when modelmainid=1386 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_issue_tag":([0-9.]+)',1) as double) end) as dec_itag,
         max(case when modelmainid=1379 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double) end) as amt_1379,
         max(case when modelmainid=1379 then cast(regexp_extract(cast(outputdata as varchar),'"decision_tree_label":([0-9]+)',1) as integer) end) as dec_tree_label,
         max(case when modelmainid=1379 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_expired_day":([0-9]+)',1) as integer) end) as exp_days,
         max(case when modelmainid=857  then nullif(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double),0) end) as amt_857
  from ods.s21_risk_model_record
  where strategytype='CHAMPION'
    and modelmainid in (1522,1523,1386,1379,857)
    -- 窗口比 app 窗口前后各放宽1天: 10/13-15的部分申请唯一一条CHAMPION决策是 10/16凌晨 T+1批处理重跑
    -- (2026-10-16 实测11笔, createtime 00:00-02:00), 上界截到10/16会漏; 下界同理留余量
    and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
  group by 1
),
grd as (   -- 三套主额评级(用信决策时同时落库, CHAMPION): 1500=V5_2 / 1542=V5_3 / 1635=V6_1(整数, 1优→差)
  --   即 fd_use_creditamount_type 决策矩阵的行变量(见 SKILL §7); 覆盖率 57,908/57,913=99.99%
  select cast(biz_id as varchar) as biz_id,
         max(cast(regexp_extract(cast(outputdata as varchar),'"android_oldCust_mainCreditLevel_charge_V5_2":([0-9]+)',1) as integer)) as grade_v52,
         max(cast(regexp_extract(cast(outputdata as varchar),'"android_oldCust_mainCreditLevel_charge_V5_3":([0-9]+)',1) as integer)) as grade_v53,
         max(cast(regexp_extract(cast(outputdata as varchar),'"android_oldCust_mainCreditLevel_charge_V6_1":([0-9]+)',1) as integer)) as grade_v61
  from ods.s21_risk_model_record
  where strategytype='CHAMPION' and modelmainid in (1500,1542,1635)
    and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17' -- T+1凌晨批处理重跑, 放宽1天
  group by 1
),
crd as (   -- 授信节点 1067(覆盖率 100%): credit_amount=授信额度, daily_max=单日最大可借额度,
  --   grantcredit_7d_amount=7天期产品支用额(实测恒=credit_amount; 节点无28d/30d key, 2026-10-16 核实),
  --   credit_exp=授信有效期(天, 常见15/18/23/26/27/29/30)
  select cast(biz_id as varchar) as biz_id,
         max(cast(regexp_extract(cast(outputdata as varchar),'"credit_amount":([0-9.]+)',1) as double)) as credit_amt,
         max(cast(regexp_extract(cast(outputdata as varchar),'"daily_max_available_limit":([0-9.]+)',1) as double)) as daily_max,
         max(cast(regexp_extract(cast(outputdata as varchar),'"credit_amount_expired_day":([0-9]+)',1) as integer)) as credit_exp,
         max(cast(regexp_extract(cast(outputdata as varchar),'"grantcredit_7d_amount":([0-9.]+)',1) as double)) as gc7d
  from ods.s21_risk_model_record
  where modelmainid=1067
    and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17' -- T+1凌晨批处理重跑, 放宽1天
  group by 1
),
yjf as (   -- V5_2/V5_3 策略分桶(yj 现成 flag, 建表时按 apply_time 落; left join, yj 窗口外为 null)
  --   exp_hash = 实验分流 hash(口径见 SKILL §6): sha256('20260811'||credit_no||app_group_sha256) 前4位hex/65536 ∈(0,1)
  --   9/3 后阈值: hash>0.7=A组(恒V5_2)、0.3<hash<=0.7=B组、hash<=0.3=C组(恒V5_3); flag 是生产实走桶, 二者互证
  select cast(biz_id as varchar) as biz_id,
         max(temp_credit_amount_strategy_test_flag) as strat_flag,
         max(from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16))/65536.0 as exp_hash
  from mx.yj_test_table_250225
  group by 1
),
ofr as (   -- ★ 离线临额批量算额节点 1504/1505(2026-10-16 新发现, 与在线 1379/857 对称):
  --   每日 20-21 点批处理圈人, biz_id 为空、只按 mid 落库; 1504=temp_credit_amount 推荐额,
  --   1505=temp_credit_amount_expired_day(恒=5天)+label。窗口 9/1-10/14 共 28,573 次/10,865 mid。
  --   全量对账: 每条(>0) 都在 ±3 天内有同 mid C015 事件且时刻差≈0; 24,748/28,573=86.6% 金额完全相等,
  --   其余差额全为 50 的倍数(+50~+1200, 旧未过期临额叠加/凑档), 即 C015 实发 = 1504 推荐额 + 叠加凑档。
  --   取数: 本 mid 在本笔 apply_time 前 3 天内最近一条(同 mid 同日可能 2 条, 20/21点各一轮, 取最晚)。
  select biz_id, rec_amt, rec_time from (
    select cast(a.biz_id as varchar) as biz_id, r.createtime as rec_time,
           cast(regexp_extract(cast(r.outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double) as rec_amt,
           row_number() over (partition by a.biz_id order by r.createtime desc) rn
    from app a
    join ods.s21_risk_model_record r
      on cast(a.mid as bigint)=cast(r.mid as bigint)
     and r.modelmainid=1504
     and r.createtime > a.apply_time - interval '3' day
     and r.createtime <= a.apply_time
  ) t where rn=1
),
utd as (   -- 本笔实际冻结占用的临额(used_detail FREEZE TEMP)
  select cast(u.biz_id as varchar) as biz_id, sum(u.risk_credit_limit) as temp_occupy
  from ods.s05_user_creditlimit_used_detail u
  join app a on cast(u.biz_id as bigint) = cast(a.biz_id as bigint)
  where u.change_action='FREEZE_LIMIT' and u.limit_type='TEMP'
  group by 1
),
utdm as (  -- 本笔实际冻结占用的主额(used_detail FREEZE MAIN) = 占用主额金额(有落库延迟, 见 ④b)
  select cast(u.biz_id as varchar) as biz_id, sum(u.risk_credit_limit) as main_occupy
  from ods.s05_user_creditlimit_used_detail u
  join app a on cast(u.biz_id as bigint) = cast(a.biz_id as bigint)
  where u.change_action='FREEZE_LIMIT' and u.limit_type='MAIN'
  group by 1
),
mauth as ( -- ★ 申请时刻主额链条(change_record MAIN, 2026-10-16 穿透):
  --   经典笔 462179690: C009 授信1500(app) → C002 申请时提额到2300(synthetic external)
  --     → C003 MAIN 预授权冻结2300(apply时刻, external_id=biz, 对"总额度"授权而非支用) → TEMP C010/C003
  --   注意: C003 MAIN 预授权额 ≠ 实际支用主额(后者在 used_detail, 即 m.main_occupy);
  --     失败重申请场景 C002/C003 会被后续失败笔改写(…2769098: 成功后 01:36 失败3笔 C004 解冻+C002 降到28000),
  --     故 C002 只取 [app_time, apply_time+1min] 窗口内最后一笔, C003 只认 external_id=本biz。
  --   ⚠️ 两个事件必须拆成两个子查询分别带分区时间过滤再 union(OR join 无法裁剪会超时)。
  select biz_id, max(main_raise_c002) as main_raise_c002, max(main_auth_c003) as main_auth_c003 from (
    select cast(a.biz_id as varchar) as biz_id,
           cast(null as double) as main_raise_c002,
           e.change_total_grantamount as main_auth_c003
    from app a
    join ods_view_presto.s05_user_creditlimit_change_record e
      on e.external_id=cast(a.biz_id as varchar)
    where e.limit_type='MAIN' and e.change_event_type='C003'
      and e.create_time >= timestamp '2026-08-31' and e.create_time < timestamp '2026-10-17'
    union all
    select cast(a.biz_id as varchar) as biz_id,
           e.change_total_grantamount as main_raise_c002,
           cast(null as double) as main_auth_c003
    from app a
    join ods_view_presto.s05_user_creditlimit_change_record e
      on cast(a.mid as bigint)=cast(e.mid as bigint)
     and e.create_time >= a.app_time and e.create_time <= a.apply_time + interval '1' minute
    where e.limit_type='MAIN' and e.change_event_type='C002'
      and e.create_time >= timestamp '2026-08-31' and e.create_time < timestamp '2026-10-17'
  ) x group by 1
),
hsrc as ( -- 【v11 历史临额占用】在线来源笔的发放锚点(仅 gtype='C010'):
  --   历史临额占用金额 = 名义发放 - 本次实到账 = C010.change_used_grantamount(发放前该账户存量占用, 定律见 ②)
  select a.biz_id, r.gtime, r.g_lmid
  from app a join src r on a.biz_id = r.biz_id
  where r.gtype='C010'
),
hled as ( -- 发放时刻(gtime)前同账户 TEMP 台账(used_detail), 按来源biz 拆 resid=Σ冻结-Σ解冻;
  --   resid>0.01 才算真正的占用来源(已完全解冻的历史笔 resid≈0 不计入)。
  --   下界放到 2026-01-01: 2-3月老贷冻结残留bug期(见 SKILL §1.3)也要能还原。
  select h.biz_id, h.gtime, u.biz_id as src_biz,
         sum(case when u.change_action='FREEZE_LIMIT'   then u.risk_credit_limit else 0 end)
       - sum(case when u.change_action='UNFREEZE_LIMIT' then u.risk_credit_limit else 0 end) as resid
  from hsrc h
  join ods.s05_user_creditlimit_used_detail u
    on u.limit_main_id = h.g_lmid and u.create_time < h.gtime
  where u.limit_type='TEMP'
    and u.create_time >= timestamp '2026-01-01' and u.create_time < timestamp '2026-10-17'
  group by 1,2,3
  having sum(case when u.change_action='FREEZE_LIMIT'   then u.risk_credit_limit else 0 end)
       - sum(case when u.change_action='UNFREEZE_LIMIT' then u.risk_credit_limit else 0 end) > 0.01
),
hrp as (  -- 占用来源biz 的结清状态(s02_loan_repayment, 只取涉及来源笔):
  --   any_unpaid=0 且最后一笔还款时刻 < 发放时刻 => 该来源笔在发放时刻已结清 => "结清后占用"(冻结残留未释放)
  --   否则(在途 / 发放时刻后才结清 / 无还款记录) => "未结清占用"
  select cast(r.camera_id as bigint) as src_biz,
         max(case when r.state<>1 then 1 else 0 end) as any_unpaid,
         max(r.fact_time) as last_pay_t
  from ods_view_presto.s02_loan_repayment r
  where cast(r.camera_id as bigint) in (select distinct cast(src_biz as bigint) from hled)
  group by 1
),
hocc as ( -- 汇总到本笔: 台账合计 与 结清后/未结清 二分; 台账合计应≈C010.change_used_grantamount(互证)
  select l.biz_id,
         round(sum(l.resid),2) as hist_occ_ledger,
         round(sum(case when p.any_unpaid=0 and p.last_pay_t < l.gtime then l.resid else 0 end),2) as hist_occ_settled,
         round(sum(case when coalesce(p.any_unpaid,1)<>0 or p.last_pay_t >= l.gtime then l.resid else 0 end),2) as hist_occ_open
  from hled l left join hrp p on p.src_biz = cast(l.src_biz as bigint)
  group by 1
)
select a.biz_id,
       a.app_date                    as "进件日期",
       a.app_time                    as "进件时刻_app_time",
       f.apply_time                  as "申请时刻_apply_time",
       f.release_time                as "实际放款_release_time",
       date_diff('second', a.app_time, f.apply_time)/60.0 as "间隔_进件到申请_分钟",
       date_diff('second', f.apply_time, f.release_time)/60.0 as "间隔_申请到放款_分钟",
       -- ===== 授信底数(节点1067) + 三套主额评级(1500/1542/1635) =====
       c.credit_amt                  as "授信额度_credit_amount_1067",
       c.daily_max                   as "单日最大可借额度_1067",
       c.credit_exp                  as "授信有效期天数_1067",
       c.gc7d                        as "7天期支用额_1067",
       g.grade_v52                   as "主额评级_V5_2_1500",
       g.grade_v53                   as "主额评级_V5_3_1542",
       g.grade_v61                   as "主额评级_V6_1_1635",
       g.grade_v53 - g.grade_v52     as "评级迁徙_V53减V52",
       -- ===== 申请时刻主额链条(change_record MAIN): 提额C002 → 预授权C003 =====
       mh.main_raise_c002            as "申请时主额提额_C002",
       mh.main_auth_c003             as "申请时主额预授权_C003MAIN",
       o.off_time                    as "离线发放时间",
       o.off_amt                     as "离线发放金额",
       fr.rec_time                   as "离线批量算额时刻_1504",
       fr.rec_amt                   as "离线批量推荐额_1504",  -- C015实发=推荐额+50倍数叠加(86.6%同额), 见 ofr 注释
       -- 离线临额"使用"：用 C003 冻结时刻表示(SKILL: 离线发放=C015/C013, 使用=C003冻结)。
       --   本笔来源为离线(r.gtype in C013/C015 或无发放) → 该笔 C003 冻结时刻即离线使用时刻;
       --   本笔来源为在线(r.gtype='C010') → 实际用的是在线临额, 离线仅持有未被消耗, 记空。
       case when coalesce(r.gtype,'')='C010' then null else z.use_time end as "离线使用时间",
       -- 与"临额最终使用(离线临额)"同义：来源为离线时 = temp_grant_amount, 否则 = 0。
       case when coalesce(r.gtype,'')='C010' then 0 else f.temp_grant_amount/1000.0 end as "离线使用金额",
       case when o.biz_id is null then '无'
            when o.off_exp > a.apply_time then '仍有效' else '已过期' end as "离线当时状态",
       -- 判断离线临额的额度是否被在线临额的发放额度覆盖(在线名义发放额 >= 离线发放额 即覆盖)
       case when o.biz_id is null or coalesce(r.gtype,'')<>'C010' then '不适用'
            when r.g_grant >= o.off_amt then '是(在线>=离线)'
            else '否(在线<离线)' end as "在线是否覆盖离线",
       s.issue_time                  as "在线临额发放时间_model1386",
       -- ===== 在线临额用信决策链底数(dec CTE): 评分→type→策略→tag→底数→比例→理论额→弹窗额 =====
       d.dec_score                   as "用信评分_score_v1_1522",
       d.dec_type                    as "用信临额类型_type_1523",
       y.strat_flag                  as "策略分桶_V52_V53",
       y.exp_hash                    as "实验分流hash值",
       case when y.exp_hash is null then null
            when y.exp_hash > 0.7 then 'A_恒V5_2'
            when y.exp_hash > 0.3 then 'B_中间组'
            else 'C_恒V5_3' end      as "实验组分桶_9月3日后口径",
       d.dec_itag                    as "弹窗发放tag_1386",
       floor(coalesce(m.main_occupy, f.contract_amount - f.temp_grant_amount/1000.0)/20.0)*20
                                     as "算额底数_占用主额floor20",  -- =1379公式底数; used_detail延迟时用 合同-临额 恒等式补全
       -- 理论发放比例: type2=40%/type3=20% 全策略一致; type1 V5_2=50%/V5_3=60%(见 dec CTE 注释)
       -- ⚠️ 切桶边界例外: yj flag 是建表时按 apply_time 落的桶, 与生产实走策略在灰度切换日(9/3)边界可能不一致
       --    (全窗口1笔 biz 1620000462632742: flag=V5_2 但实走0.6, 1379=540=900×0.6→857=550); 以 amt_1379/amt_857 实落值为准
       case when d.dec_type=1 then case when y.strat_flag like '%V5_3%' then 0.6 else 0.5 end
            when d.dec_type=2 then 0.4
            when d.dec_type=3 then 0.2 end   as "理论发放比例",
       -- ★ 实测比例(不依赖 flag): 1379实落 / floor20底数; type1 全量只有 0.5 与 0.6 两个值
       --   (2026-10-16: V5_2桶1121笔全0.50、V5_3桶1564笔全0.60, 唯一1笔切桶边界; 两比例每日并存=版本效应非时间)
       d.amt_1379/nullif(floor(coalesce(m.main_occupy, f.contract_amount - f.temp_grant_amount/1000.0)/20.0)*20,0)
                                     as "实测比例_1379除底数",
       d.amt_1379                    as "理论算额_1379_取整前",
       d.dec_tree_label              as "决策树标签_tree_label_1379",
       -- 发放金额 = 857 弹窗最终发放额(挂 tag=1 门槛)；tag=1 未领取的笔也有金额(见 ② 口径)
       case when s.issue_time is not null
            then coalesce(d.amt_857, case when r.gtype='C010' then r.g_grant end) end as "在线临额发放金额_857",
       d.amt_857 - d.amt_1379        as "弹窗取整调整额_round50",  -- =round(1379/50)*50-1379
       d.exp_days                    as "在线临额有效期天数_1379",
       date_diff('second', f.apply_time, s.issue_time)        as "间隔_申请到弹窗决策_秒",
       case when r.gtype='C010' then r.gtime end              as "在线临额使用时间_C010",
       case when r.gtype='C010' then date_diff('second', s.issue_time, r.gtime) end as "间隔_弹窗到领取_秒",
       case when r.gtype='C010' then date_diff('second', r.gtime, f.release_time) end as "间隔_领取到放款_秒",
       case when r.gtype='C010' then r.g_grant - r.g_used end as "在线临额使用金额_C010", -- 实到账额(名义-发放前存量占用)
       -- ===== 【v11】历史临额占用拆分(仅在线来源笔, 见 hsrc/hled/hrp/hocc CTE 与 ⑦ 口径) =====
       case when r.gtype='C010' then r.g_used end as "历史临额占用金额", -- =名义发放-本次实到账=发放前账户存量占用
       case when r.gtype='C010' then coalesce(h.hist_occ_settled,0) end as "历史结清后临额占用", -- 来源贷款发放时刻前已结清但冻结未释放的残留
       case when r.gtype='C010' then coalesce(h.hist_occ_open,0) end as "历史未结清临额占用",    -- 来源贷款发放时刻仍在途的占用
       case when r.gtype='C010' then round(r.g_used - coalesce(h.hist_occ_ledger,0),2) end as "历史占用台账还原差额_诊断", -- ≈0: 台账与C010字段互证; 非0: 明细延迟/异常
       -- 弹窗状态: tag0=无弹窗; tag1且本笔C010=已弹窗在线领取; tag1但本笔走离线=弹窗未领改用离线; tag1有额无使用=弹窗未领取
       case when s.issue_time is null then '无弹窗(tag0)'
            when r.gtype='C010' then '已弹窗_本笔在线领取'
            when f.temp_grant_amount > 0 then '弹窗未领_本笔走离线'
            else '已弹窗_未领取' end   as "弹窗领取状态",
       -- T+1: 决策落库日 > "申请日"(不是进件日! 进件→申请跨天占27.6%, 不算重跑); 重跑特指申请次日凌晨补跑
       case when s.issue_time is not null and cast(s.issue_time as date) > cast(f.apply_time as date) then '是'
            when s.issue_time is null then null else '否' end as "决策是否T+1批处理重跑",
       z.use_time                    as "临额冻结时刻_C003",
       u.temp_occupy                 as "临额占用金额",
       f.temp_grant_amount/1000.0    as "临额最终使用金额",
       -- 按来源拆分"临额最终使用金额"（来源判定 = mid+放款时刻 最近一次发放事件, 见上方 src CTE）：
       --   r.gtype='C010' → 在线; 否则(C013/C015 或无发放) → 离线。不存在同时使用两类的情况(见 SKILL §1.3)。
       case when r.gtype='C010' then f.temp_grant_amount/1000.0 else 0 end as "临额最终使用(在线临额)",
       case when r.gtype='C010' then 0 else f.temp_grant_amount/1000.0 end as "临额最终使用(离线临额)",
       f.contract_amount             as "合同金额_放款金额",
       m.main_occupy                 as "占用主额_used_detail原始",  -- 有批次落库延迟(约1-6%/日, T+1/T+2补齐)
       coalesce(m.main_occupy, f.contract_amount - f.temp_grant_amount/1000.0)
                                     as "占用主额金额_补全",  -- 恒等式补全: 合同-临额最终使用; 全额临额笔=0
       f.contract_amount - coalesce(m.main_occupy, f.contract_amount - f.temp_grant_amount/1000.0)
         - f.temp_grant_amount/1000.0 as "恒等式差额_诊断"     -- 0=used_detail与恒等式一致; 非0=明细延迟
from app a
left join off  o on a.biz_id=o.biz_id
left join src  r on a.biz_id=r.biz_id
left join frz  z on a.biz_id=z.biz_id
left join iss  s on cast(a.biz_id as bigint)=s.biz_id
left join dec  d on a.biz_id=d.biz_id
left join grd  g on a.biz_id=g.biz_id
left join crd  c on a.biz_id=c.biz_id
left join yjf  y on a.biz_id=y.biz_id
left join ofr  fr on a.biz_id=fr.biz_id
left join utd  u on a.biz_id=u.biz_id
left join utdm m on a.biz_id=m.biz_id
left join mauth mh on a.biz_id=mh.biz_id
left join hocc h on a.biz_id=h.biz_id
join mx.wxs_application_funnel f on a.biz_id=cast(f.biz_id as varchar) and f.tenant='yawey';

-- 单笔校验 biz=1620000482922458：1386 tag=0 → 在线发放时间应为空；
--   该笔实为"离线使用"（C015 1100 于 10-13 发放、10-18 到期，10-15 11:15:20 冻结使用，全程无 C010）。

-- ----------------------------------------------------------------------------
-- 【字段口径：三个新增字段 + 一处锚点修复】(2026-10-16)
--   ① 在线是否覆盖离线：
--      规则 = 当离线(7天内)与在线(C010)都存在时，比较 在线名义发放额(C010) vs 离线名义发放额(C015/C013)；
--             n.on_grant >= o.off_amt → '是(在线>=离线)'，否则 '否(在线<离线)'；缺一侧 → '不适用'。
--      含义 = 该笔已发的在线额是否足以整体顶掉离线额；仅"金额层"对比，不代表系统实际结算路径
--             （实际使用额恒等于本笔冻结额，见 ③）。金额均为"名义发放额"(change_total_grantamount)。
--   ② 在线临额决策链与金额三段式(底数→理论额→弹窗额)，全部落库可逐笔还原(dec CTE, 2026-10-16 全量穿透)：
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
--      ⚠️ tag=0 时 1379=null、857 照跑输出 temp_credit_amount=0（43,157 笔）→ dec 用 nullif(...,0)、
--        列上再挂 case when s.issue_time is not null 双保险。
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
--         (缺则 release_time) 前 最近一次的临额发放事件"（src CTE）：
--         r.gtype='C010' → 在线 = temp_grant、离线 = 0；否则(C013/C015 或无发放) → 在线 = 0、离线 = temp_grant。
--      修订1（废弃）本笔 biz 有 C010 才算在线：它会把"同日同 mid 多次申请、在线临额由前面失败笔
--      (biz 1620000481078667)创建、却由后面成功笔(biz 1620000483074755)消耗"误判成离线 → 170 笔改判。
--      修订2（新增）时间锚点由 release_time 收紧为 C003、并加 temp>0 门槛：原写法会把"本笔根本没消耗临额、
--      只是同 mid 更早一笔贷款的发放"挂到本笔上（反例 biz 1620000479377160：10/08、temp=0、全额走主额 2185，
--      却挂上 09/30 另一笔的 C010 2000）→ 修复后 45,856 笔无临额笔中 **25,033 笔**的临额列全部清空。
--      依据 = 临额实际使用额恒等于本笔冻结额；混合场景下不存在同时使用在线+离线两类（SKILL §1.3）。
--      全量核验：原 6,422 笔有 C010 中 6,394 笔(99.56%) C010实到账 == temp_grant（差额全为 ±0.05 舍入）。
--   ②c 离线临额批量算额节点 1504/1505（2026-10-16 新发现，与在线 1379/857 对称，ofr CTE）：
--      · 每日 20-21 点批处理圈人：1504 落 temp_credit_amount 推荐额、1505 落 expired_day=5；
--        biz_id 为空、只按 mid 落库；同 mid 同日可能 2 条（20/21 点各一轮，取最晚）。
--      · 窗口 9/1-10/14 共 28,573 次推荐(>0)/10,865 个 mid，金额 0~9800、均值 1301；
--        每条推荐都在 ±3 天内配对到同 mid 的 C015（无 C013）、时刻差≈0 分钟——C015 即该批处理落账事件。
--      · C015 实发 = 推荐额 + 50 倍数的叠加/凑档：86.6%（24,748/28,573）完全相等，
--        其余差额全为 50 的倍数（+50~+1200，旧未过期临额叠加），无其他尾差。
--      · 宽表取"本 mid 在本笔 apply_time 前 3 天内最近一条"，与 off CTE 的 C015 实发额并列，可直接对账。
--   ③c 离线使用时间 / 离线使用金额（紧跟"离线发放时间/金额"，与在线"发放→使用"对称）：
--      离线临额的"使用"用 C003 冻结时刻表示（SKILL：离线发放=C015/C013，使用=C003冻结）。
--      离线使用时间 = 来源为离线时的 C003 冻结时刻（来源为在线 → 离线未被消耗，记空）；
--      离线使用金额 = 来源为离线时的 temp_grant_amount（来源为在线 → 0），与"临额最终使用(离线临额)"同义。
--      注：对纯离线使用笔，离线使用时间 == "临额冻结时刻_C003"；对在线笔/无临额笔为空。
--   ③d 【来源判定取数】src = mid 关联 change_record(C010/C013/C015)、create_time <= coalesce(本笔C003, release_time)、
--      且 a.temp_grant>0（门槛）→ row_number() 取最近一笔 → gtype；在线列(发放金额/使用时间/使用金额)仅在 gtype='C010' 时取值。
--      离线发放(off CTE)同样加 a.temp_grant>0 门槛：本笔没用临额时不再回溯历史离线，避免"10/08 的笔挂着 08/18 的过期离线"。
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
--      ⑥a 申请时刻主额链(change_record MAIN, mauth CTE) —— 以前宽表只有"授信1067"和"支用used_detail", 中间缺两环:
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
--         即发放前该 TEMP 账户的存量占用(账户级恒等式, 见 ② 与 SKILL §1.3)。仅对在线来源笔(gtype='C010')取值。
--      ⑦b 台账还原(hsrc→hled→hrp→hocc): 取发放时刻(gtime)前同账户(limit_main_id) TEMP 台账,
--         按来源biz 拆 resid=Σ冻结−Σ解冻(>0.01 才计入), 台账合计应≈change_used_grantamount;
--         "历史占用台账还原差额_诊断"≈0 即互证, 非0 为明细延迟/异常。
--      ⑦c 结清后/未结清二分: 来源贷款在发放时刻前已结清(any_unpaid=0 且最后一笔还款 fact_time < gtime)
--         但冻结未释放 → "历史结清后临额占用"(2-3月残留bug 即此类); 否则(在途/后才结清/无还款记录) → "历史未结清临额占用"。
--         样例笔验证: 306.25 全部来自 biz 1620000460517829(4期, 发放时刻仍在途, 9/24 才结清) → 未结清306.25/结清后0。
-- ----------------------------------------------------------------------------
-- 【抽查核对】(已在 _verify_wide7.py 跑通 9 笔，字段顺序见上面 select)
--   biz_id             | 来源gtype | 离线发放               | 合同额 | 占用主额 | 在线名义C010 | 在线实到账C010 | 冻结C003           | 占用TEMP | 最终使用
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

