-- ======================================================================
-- 临额「产品封顶」与「业绩占比」· 数字验证 SQL
-- ----------------------------------------------------------------------
-- 窗口      : 2026-09-01 ~ 2026-10-15（复贷老客放款 if_issue=1）
-- 底表      : mx.tmp_online_temp_limit_wide（逐笔宽表，与 Excel 的 01_逐笔明细 同源）
-- 用法      : 逐段执行，每段输出与《临额封顶与业绩占比分析.xlsx》一一对应
-- ★重要    : 底表覆盖 2026-07-01~10-15（全量 371,925 行），
--             每段必须带窗口过滤 where app_date between date'2026-09-01' and date'2026-10-15'
--             否则会得到全表口径（371,925 行），与本文档数字不符。
-- 口径要点  :
--   · 占用主额      = main_occupy_amount_filled（恒等式补全：合同 − 临额最终使用）
--   · 盖帽点        = 风控/参数后台人工配置的「单日最大可借上限」= 10,000
--                     （= 产品路由「额度范围」上限；确认借款页三取小中「今日剩余可借额度」的基数），放款硬约束
--   · 1067 可借快照 = daily_max_amount_1067（「今日剩余」口径的展示/授信时点值，非钳制上限字段）
--   · C003 主额预授权 = authorize_main_c003（本笔真实可借上限）
--   · 在线临额使用   = online_use_amount_c010（C010 实到账）
--   · 离线临额使用   = offline_use_amount（本笔来源为离线时的实际用量）
-- 复用的窗口过滤（下文各段已内联）：
--   where app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
-- ======================================================================


-- ----------------------------------------------------------------------
-- 【0】样本核对：笔数 / 放款金额
--      预期：58,984 笔 / 86,777,763 比索
-- ----------------------------------------------------------------------
select count(1)                                  as loan_cnt,
       round(sum(contract_amount), 0)            as contract_amt_mxn
from mx.tmp_online_temp_limit_wide
where app_date >= date'2026-09-01' and app_date <= date'2026-10-15';


-- ----------------------------------------------------------------------
-- 【1】主额封顶现状：占用主额是否被 1 万卡住
--      预期：均值 1,352 / 最大 10,000 / 卡顶(=10000) 117 笔 / 超 1 万 0 笔 / 授信最大 35,000 / 授权最大 35,000
-- ----------------------------------------------------------------------
select round(avg(main_occupy_amount_filled), 0)                          as main_mean,
       max(main_occupy_amount_filled)                                    as main_max,
       sum(if(main_occupy_amount_filled >= 10000, 1, 0))                 as main_capped_cnt,   -- 正好卡顶
       sum(if(main_occupy_amount_filled >  10000, 1, 0))                 as main_over_cnt,     -- 突破1万
       max(credit_amount_1067)                                           as credit_max,        -- 授信最大(远超1万)
       sum(if(credit_amount_1067 > 10000, 1, 0))                         as credit_over_cnt,
       max(authorize_main_c003)                                          as auth_max           -- 真实可借上限
from mx.tmp_online_temp_limit_wide
where app_date >= date'2026-09-01' and app_date <= date'2026-10-15';


-- ----------------------------------------------------------------------
-- 【2】1067 可借快照现状：出口即 ≤10,000（被「单日最大可借上限」盖帽），★该快照非钳制字段
--      预期：均值 2,789 / 最大 10,000 / 超 1 万 0 笔 / =10,000 有 934 笔
--      机制：该快照是「今日剩余可借额度」口径（受当已借影响，故分布 2,000~10,000）；
--            放款校验读的是人工配置的「单日最大可借上限」=10,000，不读该快照（旁证见【2b】三条）
-- ----------------------------------------------------------------------
select round(avg(daily_max_amount_1067), 0)                               as daily_mean,
       max(daily_max_amount_1067)                                         as daily_max,
       sum(if(daily_max_amount_1067 >  10000, 1, 0))                      as daily_over_cnt,
       sum(if(daily_max_amount_1067 =  10000, 1, 0))                      as daily_eq_cnt
from mx.tmp_online_temp_limit_wide
where app_date >= date'2026-09-01' and app_date <= date'2026-10-15';


-- ----------------------------------------------------------------------
-- 【2b】★1067 可借快照「非钳制上限字段」的三条旁证
--   旁证1: 2,080 笔占用主额 > 该快照照样放款（若快照即钳制上限，这些笔应被压到快照值）
--   旁证2: 卡顶117笔中 24 笔快照仅 2,000~8,000，却冻结满 10,000（快照≠上限，决定性）
--   旁证3: 同用户同日多笔合计 max=14,589 > 1万 → 该快照非单日总量口径（仅展示/授信时点值）
--   另: 1067原始outputdata的daily_max_available_limit max=10,000、>1万 0笔、=1万 1,488笔
--       （窗口8/31~10/16, CHAMPION）→ 出口已被「单日最大可借上限」盖帽，与授信max=35,000对比鲜明
-- ----------------------------------------------------------------------
-- 旁证1 + 旁证2：超快照照放笔数 / 卡顶笔的快照分布
select sum(if(main_occupy_amount_filled > daily_max_amount_1067, 1, 0))   as over_daily_cnt,   -- 预期2,080
       sum(if(main_occupy_amount_filled >= 10000 and daily_max_amount_1067 < 10000, 1, 0)) as capped_lowdaily  -- 预期24
from mx.tmp_online_temp_limit_wide
where app_date >= date'2026-09-01' and app_date <= date'2026-10-15';

select daily_max_amount_1067 as daily_cap, count(1) as cnt
from mx.tmp_online_temp_limit_wide
where app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
  and main_occupy_amount_filled >= 10000
group by daily_max_amount_1067
order by cnt desc;
-- 预期：10000→93笔, 8000→13, 6000→3, 7000→2, 5000→2, 2000→2, 4000→1, 3500→1

-- 旁证3：同用户同日多笔合计（关联funnel7取cust_id）
select sum(if(loan_cnt >= 2 and day_sum > 10000, 1, 0))                   as multi_day_over10k,  -- 预期21
       max(case when loan_cnt >= 2 then day_sum end)                      as multi_day_sum_max   -- 预期14,589
from (
  select f7.cust_id, w.app_date,
         sum(w.main_occupy_amount_filled) as day_sum,
         count(distinct w.biz_id)         as loan_cnt
  from mx.tmp_online_temp_limit_wide w
  join mx.report_application_funnel7_table f7
    on cast(w.biz_id as bigint) = f7.camera_id
  where w.app_date >= date'2026-09-01' and w.app_date <= date'2026-10-15'
  group by f7.cust_id, w.app_date
) t;

-- 1067 原始可借快照分布（证明风控出口即被『单日最大可借上限』盖帽）
select count(1)                                                           as cnt,                -- 预期99,807
       max(cast(json_extract_scalar(outputdata, '$.daily_max_available_limit') as double)) as daily_raw_max,  -- 预期10,000
       sum(if(cast(json_extract_scalar(outputdata, '$.daily_max_available_limit') as double) > 10000, 1, 0)) as daily_gt10k,  -- 预期0
       sum(if(cast(json_extract_scalar(outputdata, '$.daily_max_available_limit') as double) = 10000, 1, 0)) as daily_eq10k,  -- 预期1,488
       max(cast(json_extract_scalar(outputdata, '$.credit_amount') as double))            as credit_raw_max, -- 预期35,000
       sum(if(cast(json_extract_scalar(outputdata, '$.credit_amount') as double) > 10000, 1, 0))             as credit_gt10k   -- 预期9,876
from ods.s21_risk_model_record
where modelmainid = 1067
  and strategytype = 'CHAMPION'
  and createtime >= timestamp'2026-08-31 00:00:00'
  and createtime <  timestamp'2026-10-16 00:00:00';


-- ----------------------------------------------------------------------
-- 【3】封顶反事实：改『单日最大可借上限』10,000 → 50,000（★单点改此人工配置即可）
--      机制（2026-10-19 修正）：风控/参数后台人工配置的「单日最大可借上限」=10,000
--      （= 产品路由「额度范围」上限）是唯一放款硬盖帽点，
--      1067 可借快照不参与放款钳制（【2b】三条旁证）→ 无需"两处同步抬"
--      释放量 = Σ max(0, min(授权,5万) − 1万)
--      预期：117 笔，释放 1,731,500（卡顶笔授权均值 ≈2.5 万）
--      参考值: release_if_daily_clamps = 0（若 1067 快照参与钳制的假设情景，已被【2b】旁证证伪）
-- ----------------------------------------------------------------------
with cap as (
  select main_occupy_amount_filled                                        as main_amt,
         authorize_main_c003                                              as auth,
         daily_max_amount_1067                                            as daily,
         online_use_amount_c010                                            as online_use
  from mx.tmp_online_temp_limit_wide
  where app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
    and main_occupy_amount_filled >= 10000
)
select count(1)                                                            as affected_cnt,
       round(sum(greatest(least(auth, 50000)         - 10000, 0)), 0)       as release_new,  -- 单点改单日最大可借上限
       round(sum(greatest(least(auth, daily, 50000) - 10000, 0)), 0)       as release_if_daily_clamps, -- 假设1067快照钳制(已证伪)
       round(avg(least(auth, 50000)), 0)                                   as new_main_avg
from cap;


-- ----------------------------------------------------------------------
-- 【3b】反事实后占用主额水平变化（含未卡顶笔）
--      新占用主额 = if(卡顶, min(授权,5万), 现状占用主额)
--      预期：均值 1,352 → 1,381; 样本内最大占用主额 10,000 → 35,000
--            （35,000 是受最大 C003 授权约束的样本极值；「单日最大可借上限」人工配置本身已抬到 5 万）
-- ----------------------------------------------------------------------
select round(avg(main_now), 0)                                            as main_mean_now,
       round(avg(main_new), 0)                                            as main_mean_new,
       max(main_now)                                                      as main_max_now,
       max(main_new)                                                      as main_max_new
from (
  select main_occupy_amount_filled as main_now,
         case when main_occupy_amount_filled >= 10000
              then least(authorize_main_c003, 50000)
              else main_occupy_amount_filled end as main_new
  from mx.tmp_online_temp_limit_wide
  where app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
) t;


-- ----------------------------------------------------------------------
-- 【4】卡顶笔画像
--      预期：授权均值 ≈2.5万 / 有在线临额 44 笔 / 持有离线临额 1 笔 / 合同 max 16,000
-- ----------------------------------------------------------------------
select count(1)                                                            as cap_cnt,
       round(avg(authorize_main_c003), 0)                                  as auth_avg,
       max(authorize_main_c003)                                            as auth_max,
       sum(if(online_use_amount_c010 > 0, 1, 0))                           as has_online_cnt,
       round(sum(online_use_amount_c010), 0)                               as online_use_sum,
       sum(if(offline_use_amount > 0, 1, 0))                               as has_offline_cnt,
       max(contract_amount)                                                as contract_max
from mx.tmp_online_temp_limit_wide
where app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
  and main_occupy_amount_filled >= 10000;


-- ----------------------------------------------------------------------
-- 【5】临额业绩占比（现状）
--      预期：在线 3,190,919 = 3.68%; 离线 3,831,197 = 4.41%; 合计 7,022,116 = 8.09%
--           有临额 12,267 笔 (20.8%)：在线 6,700 / 离线 5,567
-- ----------------------------------------------------------------------
select round(sum(contract_amount), 0)                                       as loan_amt,
       round(sum(online_use_amount_c010), 0)                                as online_amt,
       round(sum(offline_use_amount), 0)                                    as offline_amt,
       round(sum(online_use_amount_c010) + sum(offline_use_amount), 0)       as temp_amt,
       round(sum(online_use_amount_c010) * 100.0 / sum(contract_amount), 2)  as online_pct,
       round(sum(offline_use_amount)     * 100.0 / sum(contract_amount), 2)  as offline_pct,
       round((sum(online_use_amount_c010) + sum(offline_use_amount)) * 100.0
             / sum(contract_amount), 2)                                     as temp_pct,
       sum(if(online_use_amount_c010 > 0, 1, 0))                             as online_cnt,
       sum(if(offline_use_amount     > 0, 1, 0))                             as offline_cnt,
       sum(if(online_use_amount_c010 > 0 or offline_use_amount > 0, 1, 0))   as any_temp_cnt
from mx.tmp_online_temp_limit_wide
where app_date >= date'2026-09-01' and app_date <= date'2026-10-15';


-- ----------------------------------------------------------------------
-- 【6】★被卡种类拆分（2026-10-19 修正：离线临额也被 1 万钳得很死）
--      「单日最大可借上限」10,000 约束的是「主额度 + 离线临额」的合计（离线与主额同池），
--      在线临额在池外叠加、不受该上限约束（因此能突破 1 万）。
--      撞顶笔（合同 >= 9999）三类互斥拆分：
--        A_主额单独顶格   : 主额顶到 1 万 → 主额维度被卡
--        B_主额+离线合计顶格: 主额<1万但主额+离线=1万 → 离线临额被卡（无法发挥）
--        C_在线突破       : 合同>1万，靠在线临额池外叠加突破 → 不受卡
--      预期：A=117笔 / B=129笔 / C=48笔（合计294笔）
-- ----------------------------------------------------------------------
with t as (
  select main_occupy_amount_filled as m, offline_use_amount as o, online_use_amount_c010 as onl,
         contract_amount as c, authorize_main_c003 as a, coalesce(offline_grant_amount, 0) as og,
         case when main_occupy_amount_filled >= 10000 then 'A_主额单独顶格'
              when offline_use_amount > 0 then 'B_主额+离线合计顶格'
              when online_use_amount_c010 > 0 then 'C_在线突破'
              else 'D_其他' end as cap_type
  from mx.tmp_online_temp_limit_wide
  where app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
    and contract_amount >= 9999
)
select cap_type,
       count(1)                                                   as cnt,
       round(sum(c), 0)                                            as contract_now,
       round(sum(m), 0)                                            as main_occupy_sum,
       round(sum(o), 0)                                            as offline_use_sum,
       round(sum(onl), 0)                                          as online_use_sum,
       -- A类主额释放 = Σ max(0, min(授权,5万) - 主额)
       round(sum(case when cap_type = 'A_主额单独顶格'
                      then greatest(least(a, 50000) - m, 0) else 0 end), 0)  as rel_A_main,
       -- B类合计释放 = Σ max(0, min(授权+离线发放,5万) - 合同)
       round(sum(case when cap_type = 'B_主额+离线合计顶格'
                      then greatest(least(a + og, 50000) - c, 0) else 0 end), 0) as rel_B_total,
       -- B类释放中的「主额部分」 = Σ max(0, min(授权,5万) - 主额)
       round(sum(case when cap_type = 'B_主额+离线合计顶格'
                      then greatest(least(a, 50000) - m, 0) else 0 end), 0)  as rel_B_main,
       -- B类释放中的「离线部分」 = 合计释放 - 主额部分（离线临额得以叠加兑现）
       round(sum(case when cap_type = 'B_主额+离线合计顶格'
                      then greatest(least(a + og, 50000) - c, 0)
                           - greatest(least(a, 50000) - m, 0) else 0 end), 0) as rel_B_offline,
       round(sum(og), 0)                                           as offline_grant_sum
from t
group by cap_type
order by cap_type;


-- ----------------------------------------------------------------------
-- 【6b】离线临额「被卡」的底数：发放 vs 实际使用（离线使用者 5,567 笔）
--      预期：发放 5,025,400 / 实际使用 3,831,197 → 约 24% 的离线发放额未兑现
--            理论可借(授信+离线发放)>1万 的有 848 笔（潜在被卡面）
--      原因：「单日最大可借上限」1 万约束「主额+离线」合计，离线临额叠加空间被吃掉
-- ----------------------------------------------------------------------
select sum(if(offline_use_amount > 0, 1, 0))                          as off_use_cnt,
       round(sum(if(offline_use_amount > 0, offline_grant_amount, 0)), 0) as off_grant_sum,
       round(sum(offline_use_amount), 0)                               as off_use_sum,
       sum(if(offline_use_amount > 0
              and credit_amount_1067 + offline_grant_amount > 10000, 1, 0)) as theory_over10k_cnt
from mx.tmp_online_temp_limit_wide
where app_date >= date'2026-09-01' and app_date <= date'2026-10-15';


-- ----------------------------------------------------------------------
-- 【6c】在线临额受主额放大的传导（A 类主额顶格且用在线临额）
--      新在线 = 新主额 × 原比例(在线/占用主额)，授权为空的行保留原值
--      预期：在线 3,190,919 → 3,363,789，增量 +172,869（影响 44 笔）
-- ----------------------------------------------------------------------
select round(sum(online_use_amount_c010), 0)                               as online_now,
       round(sum(new_online), 0)                                           as online_new,
       round(sum(new_online) - sum(online_use_amount_c010), 0)             as online_delta,
       sum(if(main_occupy_amount_filled >= 10000 and online_use_amount_c010 > 0, 1, 0)) as online_affected_cnt
from (
  select online_use_amount_c010, main_occupy_amount_filled,
         case when main_occupy_amount_filled >= 10000 and online_use_amount_c010 > 0
                   and coalesce(authorize_main_c003, 0) > 0
              then cast(least(cast(authorize_main_c003 as double), 50000e0) as double)
                   / cast(main_occupy_amount_filled as double)
                   * cast(online_use_amount_c010 as double)
              else cast(online_use_amount_c010 as double) end as new_online
  from mx.tmp_online_temp_limit_wide
  where app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
) t;


-- ----------------------------------------------------------------------
-- 【6d】离线临额「一次没用完，下次能否继续用」（跨笔复用验证）
--      规则：离线临额有效期 5 天（节点 1505），未用完的剩余额度可在有效期内被后续放款继续消耗。
--      口径：离线发放=C013/C015(mid, T0, G)；消耗=放款笔 temp_grant_amount（本笔实际用临额，不分来源），
--            按「放款时刻落在 [T0, T0+5天] 内」归属到该笔发放。
--      预期：发放级 366/6,423=5.7% 被 ≥2 笔复用；每笔发放窗口内消耗 S≈G 71.5%、S<G 24.5%、S>G 3.9%；合计 S/G=74.9%
--      结论：「24% 未兑现」以真实流失为主（客户 5 天内不再借款 → 额度到期失效），跨笔复用仅解释约 13.6%。
--      注：funnel7.temp_grant_amount 不分在线/离线来源，若窗口内同时有 C010 会少量误判（未量化）。
-- ----------------------------------------------------------------------
with offg as (
  select cast(mid as bigint) as mid, create_time as t0,
         cast(change_total_grantamount as double) as g
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type in ('C013','C015')
    and create_time >= timestamp '2026-09-01 00:00:00'
    and create_time <  timestamp '2026-10-16 00:00:00'
),
loans as (
  select cast(mid as bigint) as mid, cast(biz_id as bigint) as biz_id, apply_time as t_use,
         cast(temp_grant_amount as double) as use_amt
  from mx.report_application_funnel7_table
  where is_reloan='old' and if_issue=1 and temp_grant_amount > 0
    and apply_time >= timestamp '2026-09-01 00:00:00'
    and apply_time <  timestamp '2026-10-16 00:00:00'
),
w as (
  select g.mid, g.t0, max(g.g) as g, count(*) as cnt, sum(l.use_amt) as s
  from offg g
  join loans l on l.mid = g.mid and l.t_use >= g.t0 and l.t_use <= g.t0 + interval '5' day
  group by g.mid, g.t0
)
select count(*)                                                     as grant_cnt,
       sum(if(cnt >= 2, 1, 0))                                      as reuse_grant_cnt,
       round(sum(if(cnt >= 2, 1, 0)) * 100.0 / count(*), 1)         as reuse_pct,
       sum(if(s <  g - 0.01, 1, 0))                                 as s_lt_g,
       sum(if(s >= g - 0.01 and s <= g + 0.01, 1, 0))               as s_eq_g,
       sum(if(s >  g + 0.01, 1, 0))                                 as s_gt_g,
       round(sum(s) * 100.0 / sum(g), 1)                            as s_over_g_pct
from w;


-- ----------------------------------------------------------------------
-- 【7】反事实后：整体放款额 + 临额占比（分母同步放大）
--      放款额增量 = 主额释放(A) + B类合计释放 + 在线临额放大
--      预期：放款额 86,777,763 → 90,588,282（+3,810,519 / +4.39%）
--            在线 3.71% / 离线 4.58%(离线额度兑现后占比反而上升) / 合计 8.29%
--      注：必须「分项求和再相加」且显式 cast(... as double)，否则 Presto 中
--          decimal(38,6)×double 混算会失真（逐行相加实测仅 15,177,090）。
-- ----------------------------------------------------------------------
with t as (
  select cast(contract_amount as double)   as contract_amt,
         cast(online_use_amount_c010 as double) as online_use,
         cast(offline_use_amount as double)     as offline_use,
         -- A类：主额单独顶格 → 主额释放
         coalesce(case when main_occupy_amount_filled >= 10000
              then cast(greatest(least(cast(authorize_main_c003 as double), 50000e0)
                   - cast(main_occupy_amount_filled as double), 0e0) as double) else 0e0 end, 0e0) as rel_A_main,
         -- B类：主额+离线合计顶格 → 拆「主额部分」与「离线部分」
         coalesce(case when main_occupy_amount_filled < 10000 and offline_use_amount > 0
                   and contract_amount >= 9999
              then cast(greatest(least(cast(authorize_main_c003 as double), 50000e0)
                   - cast(main_occupy_amount_filled as double), 0e0) as double) else 0e0 end, 0e0) as rel_B_main,
         coalesce(case when main_occupy_amount_filled < 10000 and offline_use_amount > 0
                   and contract_amount >= 9999
              then cast(greatest(least(cast(authorize_main_c003 as double)
                   + cast(coalesce(offline_grant_amount,0) as double), 50000e0)
                   - cast(contract_amount as double), 0e0) as double)
                   - cast(greatest(least(cast(authorize_main_c003 as double), 50000e0)
                       - cast(main_occupy_amount_filled as double), 0e0) as double)
              else 0e0 end, 0e0) as rel_B_off,
         -- 在线临额放大（A类主额放大后同步；授权为空的笔不放大）
         coalesce(case when main_occupy_amount_filled >= 10000 and online_use_amount_c010 > 0
                   and coalesce(authorize_main_c003, 0) > 0
              then cast(least(cast(authorize_main_c003 as double), 50000e0) as double)
                   / cast(main_occupy_amount_filled as double)
                   * cast(online_use_amount_c010 as double)
                   - cast(online_use_amount_c010 as double) else 0e0 end, 0e0) as online_delta
  from mx.tmp_online_temp_limit_wide
  where app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
)
select round(sum(contract_amt), 0)                                            as loan_now,
       round(sum(rel_A_main), 0)                                              as rel_A_main_sum,   -- 1,731,500（A类主额释放）
       round(sum(rel_B_main), 0)                                              as rel_B_main_sum,   -- 1,591,410（B类主额扩张）
       round(sum(rel_B_off), 0)                                               as rel_B_offline_sum,-- 314,740（B类离线兑现）
       round(sum(online_delta), 0)                                            as online_delta_sum, -- 172,869（在线放大）
       round(sum(contract_amt) + sum(rel_A_main) + sum(rel_B_main)
             + sum(rel_B_off) + sum(online_delta), 0)                          as loan_new,
       round((sum(contract_amt) + sum(rel_A_main) + sum(rel_B_main)
              + sum(rel_B_off) + sum(online_delta)) * 100e0
             / sum(contract_amt) - 100e0, 2)                                  as loan_growth_pct,
       round((sum(online_use) + sum(online_delta)) * 100e0
             / (sum(contract_amt) + sum(rel_A_main) + sum(rel_B_main)
                + sum(rel_B_off) + sum(online_delta)), 2)                     as online_pct_new,
       round((sum(offline_use) + sum(rel_B_off)) * 100e0
             / (sum(contract_amt) + sum(rel_A_main) + sum(rel_B_main)
                + sum(rel_B_off) + sum(online_delta)), 2)                     as offline_pct_new,
       round((sum(online_use) + sum(online_delta) + sum(offline_use) + sum(rel_B_off)) * 100e0
             / (sum(contract_amt) + sum(rel_A_main) + sum(rel_B_main)
                + sum(rel_B_off) + sum(online_delta)), 2)                     as temp_pct_new
from t;


-- ----------------------------------------------------------------------
-- 【8】结论3 · V5_3 档段下沉量化（评级 × 用信评分 单元 t0）
--      数据源：mx.yj_test_table_250225（含逾期字段），窗口 8/19~9/21
--      口径：t0 = sum(t0_overdue_amount_1)/sum(t0_should_amt_1)
--      分组：A_恒V5_2(hash>0.7) 实走V5_2 / C_恒V5_3(hash<=0.3) 实走V5_3
--      预期：V5_3 在 g8/g9/g10 低分段发放临额(type2/3)，对应 t0 33%~44% 显著高于 V5_2 同格
--      注：hash = from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536
-- ----------------------------------------------------------------------
select grp,
       grade, score_band, count(1)                                          as cnt,
       round(sum(t0_overdue_amount_1) / nullif(sum(t0_should_amt_1), 0) * 100, 2) as t0_rate,
       sum(if(temp_credit_amount_issue_tag = 1, 1, 0))                      as tag1_cnt
from (
  select case when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)
                 / 65536.0000000000000000 > 0.7 then 'A_恒V5_2_实走V5_2'
              when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)
                 / 65536.0000000000000000 <= 0.3 then 'C_恒V5_3_实走V5_3'
              else 'B_中间组' end                                          as grp,
         case when android_oldcust_maincreditlevel_charge_v5_3 is null then 'g_null'
              when android_oldcust_maincreditlevel_charge_v5_3 >= 14 then 'g14p'
              else 'g'||cast(cast(android_oldcust_maincreditlevel_charge_v5_3 as integer) as varchar) end as grade,
         case when fd_use_creditamount_score_v1 is null then 's_null'
              when fd_use_creditamount_score_v1 >= 5 then 's5p'
              when fd_use_creditamount_score_v1 >= 3 then 's3_5'
              when fd_use_creditamount_score_v1 >= 1 then 's1_3'
              when fd_use_creditamount_score_v1 >= 0 then 's0_1'
              else 'sn0' end                                                as score_band,
         t0_overdue_amount_1, t0_should_amt_1, temp_credit_amount_issue_tag
  from mx.yj_test_table_250225
  where if_issue = 1 and is_reloan = 'old'
    and app_date >= date'2026-08-19' and app_date < date'2026-09-22'
    and temp_credit_amount_strategy_test_flag is not null
) x
where grp in ('A_恒V5_2_实走V5_2', 'C_恒V5_3_实走V5_3')
group by 1,2,3
order by 1,2,3;


-- ----------------------------------------------------------------------
-- 【9】结论4 · 离线 0824 客群对照组（当前无对照组，本周加 20% 灰度）
--      生产圈选 SQL 见：墨西哥/14.墨西哥离线发临额.sql（第 95~116 行 准入 where + 分档）
--      灰度对照组：命中圈选但「不发临额」，用于因果评估；当前该臂尚未开跑，数据为空
-- ----------------------------------------------------------------------
select '对照组尚未开跑，本周新增 20% 灰度圈选后不发临额' as note;


-- ======================================================================
-- 第二部分：三额度「给额 / 支用 / 可用」+ 三类限制调整的额外可用
--   （2026-10-19 新增，对应 07_三额度给额支用可用 / 08_调整情景 两张 sheet）
--   口径：放款笔窗口汇总（逐笔快照累加），非账户级时点去重
--   三类限制调整点：
--     ① 产品上限调整     ：产品路由「额度范围」上限（现状 10,000）
--     ② 用信页计算逻辑调整：「临额放在里面取小」→「放到外面叠加」（需服务端发版）
--     ③ 单日上限调整     ：风控/参数后台人工配置「单日最大可借上限」（现状 10,000）
--   现状机制：合同 = min( 主额可借, 产品上限, 单日上限 ) + 在线临额(池外)
--             即「主额 + 离线临额」同池被 min(产品上限, 单日上限) 钳住；
--             在线临额在池外叠加，是唯一能突破 1 万的通道。
-- ======================================================================


-- ----------------------------------------------------------------------
-- 【10】三额度 给额 / 支用 / 可用（放款笔窗口汇总，窗口 2026-09-01~10-15）
--      预期：主额度 给 249,938,350 / 用 79,736,416 / 余 170,201,934（使用率 31.90%）
--            离线临额 给 8,132,400 / 用 3,831,196 / 余 4,301,204（使用率 47.11%）
--                     （推荐额口径 9,143,550 → 使用率 41.90%）
--            在线临额 给 7,771,650 / 用 3,190,919 / 余 4,580,731（使用率 41.06%）
--      注：给额为逐笔快照累加（同一账户多笔会重复计授信/临额发放），故为「笔窗口」口径
-- ----------------------------------------------------------------------
select count(1)                                                                  as loan_cnt,
       round(sum(contract_amount), 0)                                            as contract_amt,
       -- 主额度：给=授信(cur 额度)  支=占用主额  可用=差
       round(sum(credit_amount_1067), 0)                                         as main_give,
       round(sum(main_occupy_amount_filled), 0)                                  as main_use,
       round(sum(credit_amount_1067) - sum(main_occupy_amount_filled), 0)         as main_avail,
       round(sum(main_occupy_amount_filled) * 100e0 / sum(credit_amount_1067), 2) as main_use_pct,
       sum(if(main_occupy_amount_filled > 0, 1, 0))                               as main_use_cnt,
       -- 离线临额：给=发放额(或推荐额)  支=实际消耗  可用=差
       round(sum(coalesce(offline_grant_amount, 0)), 0)                           as off_give,
       round(sum(coalesce(offline_recommend_amount_1504, 0)), 0)                  as off_give_recommend,
       round(sum(offline_use_amount), 0)                                          as off_use,
       round(sum(coalesce(offline_grant_amount, 0)) - sum(offline_use_amount), 0)   as off_avail,
       round(sum(offline_use_amount) * 100e0
             / nullif(sum(coalesce(offline_grant_amount, 0)), 0), 2)              as off_use_pct,
       sum(if(offline_use_amount > 0, 1, 0))                                      as off_use_cnt,
       -- 在线临额：给=弹窗发放额(857)  支=C010 实领  可用=差
       round(sum(coalesce(online_issue_amount_857, 0)), 0)                        as on_give,
       round(sum(online_use_amount_c010), 0)                                      as on_use,
       round(sum(coalesce(online_issue_amount_857, 0)) - sum(online_use_amount_c010), 0) as on_avail,
       round(sum(online_use_amount_c010) * 100e0
             / nullif(sum(coalesce(online_issue_amount_857, 0)), 0), 2)           as on_use_pct,
       sum(if(online_use_amount_c010 > 0, 1, 0))                                  as on_use_cnt
from mx.tmp_online_temp_limit_wide
where app_date >= date'2026-09-01' and app_date <= date'2026-10-15';


-- ----------------------------------------------------------------------
-- 【11】被卡笔（被「主额+离线」同池钳住）规模与额外可用上限
--      被钳判据：主额 + 离线临额使用 >= 9999（撞顶）
--        A 主额单独顶格       : 主额 >= 10000
--        B 主额+离线合计顶格  : 主额 < 10000 且 离线使用 > 0 且 合同 >= 9999
--      预期：A=117 / B=129（合计 246 笔，占 0.42%）
-- ----------------------------------------------------------------------
select sum(if(main_occupy_amount_filled >= 10000
              or (main_occupy_amount_filled < 10000 and offline_use_amount > 0
                  and contract_amount >= 9999), 1, 0))                          as capped_cnt,
       sum(if(main_occupy_amount_filled >= 10000, 1, 0))                       as a_cnt,
       sum(if(main_occupy_amount_filled < 10000 and offline_use_amount > 0
              and contract_amount >= 9999, 1, 0))                              as b_cnt,
       -- 主额可释放 = Σ max(0, min(授权, 1万) - 主额)   [临额外置后主额仍受 1 万限制]
       round(sum(if(main_occupy_amount_filled >= 10000 or
                    (main_occupy_amount_filled < 10000 and offline_use_amount > 0
                     and contract_amount >= 9999),
                    greatest(least(cast(authorize_main_c003 as double), 10000e0)
                             - cast(main_occupy_amount_filled as double), 0e0), 0e0)), 0) as rel_main_10k,
       -- 离线可用空间兑现 = Σ max(0, 离线发放 - 离线使用)   [临额外置后被池挤掉的离线额度可叠加]
       round(sum(if(main_occupy_amount_filled >= 10000 or
                    (main_occupy_amount_filled < 10000 and offline_use_amount > 0
                     and contract_amount >= 9999),
                    greatest(cast(coalesce(offline_grant_amount, 0) as double)
                             - cast(offline_use_amount as double), 0e0), 0e0)), 0) as rel_off_avail
from mx.tmp_online_temp_limit_wide
where app_date >= date'2026-09-01' and app_date <= date'2026-10-15';


-- ----------------------------------------------------------------------
-- 【12】三类调整「单独」情景（cap 目标 = 50,000）
--      S1 只改「产品上限」1万→5万（单日上限仍1万、临额仍内嵌）
--      S2 只改「单日上限」1万→5万（产品上限仍1万、临额仍内嵌）
--      S3 只改「用信页计算逻辑」（临额外置；产品上限/单日上限仍1万）
--      预期：S1 = S2 = 0（合同 ≤ min(产品上限, 单日上限)，两者其一仍=1万 → 无释放）
--            S3 = 主额释放 321,160 + 离线可用兑现 502,540 = 823,700
-- ----------------------------------------------------------------------
with t as (
  select cast(main_occupy_amount_filled as double) as m,
         cast(offline_use_amount as double)        as o,
         cast(coalesce(offline_grant_amount,0) as double) as og,
         cast(contract_amount as double)           as c,
         cast(coalesce(authorize_main_c003,0) as double)  as a,
         case when main_occupy_amount_filled >= 10000 then 1
              when main_occupy_amount_filled < 10000 and offline_use_amount > 0
                   and contract_amount >= 9999 then 1 else 0 end as capped
  from mx.tmp_online_temp_limit_wide
  where app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
)
select
  -- S1 产品上限↑（单日上限仍1万）：合同上限仍被 1 万钳 → 0
  0e0                                                                          as s1_product_only,
  -- S2 单日上限↑（产品上限仍1万）：合同上限仍被 1 万钳 → 0
  0e0                                                                          as s2_daily_only,
  -- S3 临额外置（caps 不变）：主额释放 + 离线可用兑现
  round(sum(if(capped = 1, greatest(least(a, 10000e0) - m, 0e0), 0e0)), 0)       as s3_main,
  round(sum(if(capped = 1, greatest(og - o, 0e0), 0e0)), 0)                      as s3_offline,
  round(sum(if(capped = 1, greatest(least(a, 10000e0) - m, 0e0), 0e0))
      + sum(if(capped = 1, greatest(og - o, 0e0), 0e0)), 0)                      as s3_total
from t;


-- ----------------------------------------------------------------------
-- 【13】三类调整「组合」情景（cap 目标 = 50,000）
--      S4 = 产品上限 + 单日上限 同改 1万→5万（临额仍内嵌）
--      S5 = S4 + 临额外置（全放开）
--      预期：S4/S5 主额释放 3,322,910（A类1,731,500 + B类1,591,410）
--            离线可用兑现 502,540（本表口径：含 A类被挤掉的离线额度；原文档仅计B类=314,740）
--            在线临额联动增量 172,869（44笔主额放大后按原type比例同步放大）
--            合计额外可用 ≈ 3,998,319（+4.61%）
--      注：需「分项求和再相加」+ 显式 cast(... as double)，避免 decimal×double 混算失真
-- ----------------------------------------------------------------------
with t as (
  select cast(main_occupy_amount_filled as double) as m,
         cast(offline_use_amount as double)        as o,
         cast(coalesce(offline_grant_amount,0) as double) as og,
         cast(contract_amount as double)           as c,
         cast(online_use_amount_c010 as double)    as n,
         cast(coalesce(authorize_main_c003,0) as double)  as a,
         case when main_occupy_amount_filled >= 10000 then 1
              when main_occupy_amount_filled < 10000 and offline_use_amount > 0
                   and contract_amount >= 9999 then 1 else 0 end as capped
  from mx.tmp_online_temp_limit_wide
  where app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
)
select
  round(sum(if(capped = 1, greatest(least(a, 50000e0) - m, 0e0), 0e0)), 0)        as s4_main,
  round(sum(if(capped = 1, greatest(og - o, 0e0), 0e0)), 0)                       as s4_offline,
  round(sum(case when capped = 1 and n > 0e0 and a > 0e0
                 then least(a, 50000e0) / m * n - n else 0e0 end), 0)             as s4_online_link,
  round(sum(if(capped = 1, greatest(least(a, 50000e0) - m, 0e0), 0e0))
      + sum(if(capped = 1, greatest(og - o, 0e0), 0e0))
      + sum(case when capped = 1 and n > 0e0 and a > 0e0
                 then least(a, 50000e0) / m * n - n else 0e0 end), 0)             as s4_total,
  round((sum(if(capped = 1, greatest(least(a, 50000e0) - m, 0e0), 0e0))
       + sum(if(capped = 1, greatest(og - o, 0e0), 0e0))
       + sum(case when capped = 1 and n > 0e0 and a > 0e0
                  then least(a, 50000e0) / m * n - n else 0e0 end)) * 100e0
       / sum(c), 2)                                                               as s4_growth_pct,
       0e0                                                                        as s5_same_as_s4
from t;


-- ----------------------------------------------------------------------
-- 【14】★被卡笔客群画像（支撑「是否需要先调临额策略再放开」判断）
--      预期：A类 高授信/主额顶格；A∪B 用户用信评分偏低、type1/2/3 为主、V5_2 桶为主
--      结论指向：放开受益面窄（246笔/0.42%），但受益者集中在「低评级 + 已持有高比例临额」
--                客群 → 若这批客群坏账高（见【8】V5_3 低分段 33%~44%），应先收紧临额策略再放开
-- ----------------------------------------------------------------------
select case when main_occupy_amount_filled >= 10000 then 'A_主额单独顶格'
            else 'B_主额+离线合计顶格' end                                      as cap_type,
       count(1)                                                                 as cnt,
       round(avg(main_occupy_amount_filled), 0)                                 as main_avg,
       round(avg(cast(authorize_main_c003 as double)), 0)                        as auth_avg,
       round(avg(contract_amount), 0)                                            as contract_avg,
       round(avg(cast(use_credit_score_1522 as double)), 2)                      as score_avg,
       sum(if(use_credit_amount_type_1523 = 1, 1, 0))                           as type1_cnt,
       sum(if(use_credit_amount_type_1523 = 2, 1, 0))                           as type2_cnt,
       sum(if(use_credit_amount_type_1523 = 3, 1, 0))                           as type3_cnt,
       sum(if(strategy_bucket_v52_v53 like '%V5_3%', 1, 0))                      as v53_cnt,
       round(sum(cast(coalesce(offline_grant_amount,0) + coalesce(online_issue_amount_857,0) as double))
             * 100e0
             / nullif(sum(cast(main_occupy_amount_filled as double)), 0), 1)     as temp_give_over_main_pct
from mx.tmp_online_temp_limit_wide
where app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
  and (main_occupy_amount_filled >= 10000
       or (main_occupy_amount_filled < 10000 and offline_use_amount > 0 and contract_amount >= 9999))
group by 1
order by 1;


-- ----------------------------------------------------------------------
-- 【15】临额发放额 / 主额度 比例分布（回应「临额发这么高的人占比多少」）
--      口径：有临额发放（离线发放 + 在线发放 > 0）的放款笔，比例 = 临额发放额 / 占用主额
--      预期：约 40% 的笔临额发放 ≥ 占用主额的 40%（中位 ≈ 0.40、P75 ≈ 0.50）
-- ----------------------------------------------------------------------
with t as (
  select cast(coalesce(offline_grant_amount,0) + coalesce(online_issue_amount_857,0) as double) as g,
         cast(main_occupy_amount_filled as double) as m
  from mx.tmp_online_temp_limit_wide
  where app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
    and (coalesce(offline_grant_amount,0) + coalesce(online_issue_amount_857,0)) > 0
    and main_occupy_amount_filled > 0
)
select count(1)                                                                 as cnt,
       round(avg(g / m), 2)                                                     as ratio_avg,
       round(approx_percentile(g / m, 0.5), 2)                                  as ratio_p50,
       round(approx_percentile(g / m, 0.75), 2)                                as ratio_p75,
       round(sum(if(g / m < 0.2, 1, 0)) * 100e0 / count(1), 1)                  as pct_lt20,
       round(sum(if(g / m >= 0.2 and g / m < 0.4, 1, 0)) * 100e0 / count(1), 1) as pct_20_40,
       round(sum(if(g / m >= 0.4 and g / m < 0.6, 1, 0)) * 100e0 / count(1), 1) as pct_40_60,
       round(sum(if(g / m >= 0.6 and g / m < 0.8, 1, 0)) * 100e0 / count(1), 1) as pct_60_80,
       round(sum(if(g / m >= 0.8, 1, 0)) * 100e0 / count(1), 1)                 as pct_ge80
from t;


-- ======================================================================
-- 第三部分：进件维度 · 三额度表现 + 今日可用（三档）+ 可用受限占比 + V5_2/V5_3×评级
--   （2026-10-19 新增）
--   口径（与 Excel 09/10/11 各 sheet 一致）：
--     池理论可用 = 主额可借(authorize_main_c003) + 离线临额可用(发放 − 使用)
--     单日剩余   = max(10000 − 当日已用(oneday_used_grantamount), 0)   ← 关联 funnel7
--     今日可用额度         = min(池理论可用, 单日剩余, 产品上限=1万)
--     去产品上限后今日可用 = min(池理论可用, 单日剩余)          ← 仅放开产品上限
--     去单日上限后今日可用 = min(池理论可用, 产品上限=1万)      ← 仅放开单日上限
--     可用受限占比 = (池理论可用 − 今日可用额度) / 池理论可用
--   ★注：产品上限与单日上限现状均为 1 万，且单日剩余 ≤ 1 万 →
--        三个「今日可用」数值几乎相等 = 「单项放开无效」的进件维度呈现（呼应【12】S1=S2=0）。
-- ======================================================================

-- ----------------------------------------------------------------------
-- 【16】进件维度 · 三额度现状 + 池今日可用三档 + 可用受限占比（汇总）
--      预期：主额 给249,938,350/用79,736,416/余170,201,934
--            离线 给8,132,400/用3,831,196/余4,301,204；在线 给7,771,650/用3,190,919/余4,580,731
--            池理论可用 254,105,200 / 今日可用 201,716,900 / 受限 52,388,300 (20.62%)
--            池>1万 6,620 笔；当日已借(oneday>0) 1,743 笔
-- ----------------------------------------------------------------------
with f7o as (
  select cast(camera_id as bigint) as bk,
         max(cast(oneday_used_grantamount as double)) as oneday_used
  from mx.report_application_funnel7_table
  where if_issue = 1 and is_reloan = 'old'
    and app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
  group by 1
),
m as (
  select cast(w.credit_amount_1067 as double)                   as main_give,
         cast(w.main_occupy_amount_filled as double)            as main_use,
         cast(coalesce(w.offline_grant_amount,0) as double)     as off_give,
         cast(w.offline_use_amount as double)                   as off_use,
         cast(coalesce(w.online_issue_amount_857,0) as double)  as on_give,
         cast(w.online_use_amount_c010 as double)               as on_use,
         cast(coalesce(w.authorize_main_c003,0) as double)      as auth,
         greatest(cast(coalesce(w.offline_grant_amount,0) as double)
                  - cast(w.offline_use_amount as double), 0e0)  as off_avail,
         cast(coalesce(f.oneday_used,0) as double)              as oneday_used,
         greatest(10000e0 - cast(coalesce(f.oneday_used,0) as double), 0e0) as daily_rem
  from mx.tmp_online_temp_limit_wide w
  left join f7o f on cast(w.biz_id as bigint) = f.bk
  where w.app_date >= date'2026-09-01' and w.app_date <= date'2026-10-15'
),
p as (
  select m.*, auth + off_avail as pool from m
)
select count(1)                                                      as loan_cnt,
       round(sum(main_give), 0)                                      as main_give,
       round(sum(main_use), 0)                                       as main_use,
       round(sum(main_give) - sum(main_use), 0)                      as main_avail,
       round(sum(off_give), 0)                                       as off_give,
       round(sum(off_use), 0)                                        as off_use,
       round(sum(off_give) - sum(off_use), 0)                        as off_avail_sum,
       round(sum(on_give), 0)                                        as on_give,
       round(sum(on_use), 0)                                         as on_use,
       round(sum(on_give) - sum(on_use), 0)                          as on_avail_sum,
       round(sum(pool), 0)                                           as pool_sum,
       round(sum(least(pool, daily_rem, 10000e0)), 0)                as avail_now_sum,
       round(sum(least(pool, daily_rem)), 0)                         as avail_no_prod,
       round(sum(least(pool, 10000e0)), 0)                           as avail_no_daily,
       round(sum(greatest(pool - least(pool, daily_rem, 10000e0), 0e0)), 0) as restrict_sum,
       round(sum(greatest(pool - least(pool, daily_rem, 10000e0), 0e0)) * 100e0
             / sum(pool), 2)                                         as restrict_pct,
       sum(if(pool > 10000e0, 1, 0))                                 as pool_gt10k_cnt,
       sum(if(oneday_used > 0, 1, 0))                                as oneday_used_cnt
from p;


-- ----------------------------------------------------------------------
-- 【17】进件维度 · 逐日趋势（按进件日 app_date）
--      预期：受限占比从 9 月初 15~18% 上行至 10 月中 21~24%（池均值同步抬升）
-- ----------------------------------------------------------------------
with f7o as (
  select cast(camera_id as bigint) as bk,
         max(cast(oneday_used_grantamount as double)) as oneday_used
  from mx.report_application_funnel7_table
  where if_issue = 1 and is_reloan = 'old'
    and app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
  group by 1
),
p as (
  select w.app_date as app_date,
         cast(coalesce(w.authorize_main_c003,0) as double)
         + greatest(cast(coalesce(w.offline_grant_amount,0) as double)
                    - cast(w.offline_use_amount as double), 0e0) as pool,
         greatest(10000e0 - cast(coalesce(f.oneday_used,0) as double), 0e0) as daily_rem
  from mx.tmp_online_temp_limit_wide w
  left join f7o f on cast(w.biz_id as bigint) = f.bk
  where w.app_date >= date'2026-09-01' and w.app_date <= date'2026-10-15'
)
select app_date,
       count(1)                                                          as cnt,
       round(sum(pool), 0)                                               as pool_sum,
       round(sum(least(pool, daily_rem, 10000e0)), 0)                    as avail_now_sum,
       round(sum(greatest(pool - least(pool, daily_rem, 10000e0), 0e0)), 0) as restrict_sum,
       round(sum(greatest(pool - least(pool, daily_rem, 10000e0), 0e0)) * 100e0
             / nullif(sum(pool), 0), 2)                                  as restrict_pct,
       round(avg(pool), 0)                                               as pool_avg
from p
group by app_date
order by app_date;


-- ----------------------------------------------------------------------
-- 【18】V5_2 策略 × 评级（按实走桶 strategy_bucket_v52_v53 过滤，评级取 main_grade_v5_2_1500）
--      预期：评级越低（g1~g3）池越大、受限占比越高（≈37%~47%）；
--            评级越高（g12~g16）池小、受限占比 <5%
-- ----------------------------------------------------------------------
with f7o as (
  select cast(camera_id as bigint) as bk,
         max(cast(oneday_used_grantamount as double)) as oneday_used
  from mx.report_application_funnel7_table
  where if_issue = 1 and is_reloan = 'old'
    and app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
  group by 1
),
p as (
  select coalesce(w.main_grade_v5_2_1500, 0)                    as grade,
         cast(w.credit_amount_1067 as double)                   as main_give,
         cast(w.main_occupy_amount_filled as double)            as main_use,
         cast(coalesce(w.offline_grant_amount,0) as double)     as off_give,
         cast(w.offline_use_amount as double)                   as off_use,
         cast(coalesce(w.online_issue_amount_857,0) as double)  as on_give,
         cast(w.online_use_amount_c010 as double)               as on_use,
         cast(coalesce(w.authorize_main_c003,0) as double)
         + greatest(cast(coalesce(w.offline_grant_amount,0) as double)
                    - cast(w.offline_use_amount as double), 0e0) as pool,
         greatest(10000e0 - cast(coalesce(f.oneday_used,0) as double), 0e0) as daily_rem
  from mx.tmp_online_temp_limit_wide w
  left join f7o f on cast(w.biz_id as bigint) = f.bk
  where w.app_date >= date'2026-09-01' and w.app_date <= date'2026-10-15'
    and w.strategy_bucket_v52_v53 like '%V5_2%'
)
select grade, count(1)                                                      as cnt,
       round(sum(main_give), 0)                                             as main_give,
       round(sum(main_use), 0)                                              as main_use,
       round(sum(off_give), 0)                                              as off_give,
       round(sum(off_use), 0)                                               as off_use,
       round(sum(on_give), 0)                                               as on_give,
       round(sum(on_use), 0)                                                as on_use,
       round(sum(pool), 0)                                                  as pool_sum,
       round(sum(least(pool, daily_rem, 10000e0)), 0)                       as avail_now_sum,
       round(sum(greatest(pool - least(pool, daily_rem, 10000e0), 0e0)), 0) as restrict_sum,
       round(sum(greatest(pool - least(pool, daily_rem, 10000e0), 0e0)) * 100e0
             / nullif(sum(pool), 0), 2)                                     as restrict_pct
from p
group by grade
order by grade;


-- ----------------------------------------------------------------------
-- 【19】V5_3 策略 × 评级（评级取 main_grade_v5_3_1542；其余口径同【18】）
--      预期：g1 池均值≈1.6万、受限占比≈51%；g12 受限占比≈0.15%
-- ----------------------------------------------------------------------
with f7o as (
  select cast(camera_id as bigint) as bk,
         max(cast(oneday_used_grantamount as double)) as oneday_used
  from mx.report_application_funnel7_table
  where if_issue = 1 and is_reloan = 'old'
    and app_date >= date'2026-09-01' and app_date <= date'2026-10-15'
  group by 1
),
p as (
  select coalesce(w.main_grade_v5_3_1542, 0)                    as grade,
         cast(w.credit_amount_1067 as double)                   as main_give,
         cast(w.main_occupy_amount_filled as double)            as main_use,
         cast(coalesce(w.offline_grant_amount,0) as double)     as off_give,
         cast(w.offline_use_amount as double)                   as off_use,
         cast(coalesce(w.online_issue_amount_857,0) as double)  as on_give,
         cast(w.online_use_amount_c010 as double)               as on_use,
         cast(coalesce(w.authorize_main_c003,0) as double)
         + greatest(cast(coalesce(w.offline_grant_amount,0) as double)
                    - cast(w.offline_use_amount as double), 0e0) as pool,
         greatest(10000e0 - cast(coalesce(f.oneday_used,0) as double), 0e0) as daily_rem
  from mx.tmp_online_temp_limit_wide w
  left join f7o f on cast(w.biz_id as bigint) = f.bk
  where w.app_date >= date'2026-09-01' and w.app_date <= date'2026-10-15'
    and w.strategy_bucket_v52_v53 like '%V5_3%'
)
select grade, count(1)                                                      as cnt,
       round(sum(main_give), 0)                                             as main_give,
       round(sum(main_use), 0)                                              as main_use,
       round(sum(off_give), 0)                                              as off_give,
       round(sum(off_use), 0)                                               as off_use,
       round(sum(on_give), 0)                                               as on_give,
       round(sum(on_use), 0)                                                as on_use,
       round(sum(pool), 0)                                                  as pool_sum,
       round(sum(least(pool, daily_rem, 10000e0)), 0)                       as avail_now_sum,
       round(sum(greatest(pool - least(pool, daily_rem, 10000e0), 0e0)), 0) as restrict_sum,
       round(sum(greatest(pool - least(pool, daily_rem, 10000e0), 0e0)) * 100e0
             / nullif(sum(pool), 0), 2)                                     as restrict_pct
from p
group by grade
order by grade;
