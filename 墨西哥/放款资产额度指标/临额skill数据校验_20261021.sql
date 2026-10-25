-- ======================================================================
-- 临额 skill（mexico-temp-limit-analysis §1.9）数据校验
-- 执行日 2026-10-21 | 对象表 mx.yj_temp_limit_wide_table_v2 / v3
-- 引擎 Presto（盘古4.0）
--
-- 每段都标注了【实测结果】与【判定】。判定口径：
--   PASS  = skill 声明与实测一致
--   FIX   = 方向对、数字或口径需修正
--   FAIL  = 声明不成立，必须改
--
-- ⚠️ Presto 注意（本文件已规避）：
--   1) 不用 GROUPING SETS（本环境返回 data:null）
--   2) 相除必须 CAST(... AS DOUBLE)，否则整除截断
--   3) 不用中文别名（会被 SQL 检查拒绝）
--   4) 结果集 10,000 行硬顶 —— 本文件全部用聚合，不落明细
--   5) 不要并发跑，会互相饿死
--   6) ★ 校验类 sum(case when abs(x-y)>t then 1 end) 遇 NULL 会静默计 0 = 放过，
--      所以每个恒等式都必须额外单列 isnull 断言（见 B1）
-- ======================================================================


-- ──────────────────────────────────────────────────────────────────────
-- A1 行数与唯一性
-- 【实测】v2/v3 均 65,972 行，biz_id 全唯一，0 空值，窗口 2026-09-01~10-20
-- 【判定】PASS —— yj_test_table_250225 的全行重复已被 MAX() 正确去掉
-- ──────────────────────────────────────────────────────────────────────
select 'v2' as tbl, count(1) as rows_all, count(distinct biz_id) as biz_uniq,
       min(issue_date) as dmin, max(issue_date) as dmax,
       sum(case when biz_id is null then 1 else 0 end) as biz_null
from mx.yj_temp_limit_wide_table_v2
union all
select 'v3', count(1), count(distinct biz_id), min(issue_date), max(issue_date),
       sum(case when biz_id is null then 1 else 0 end)
from mx.yj_temp_limit_wide_table_v3;


-- ──────────────────────────────────────────────────────────────────────
-- A2 用 funnel 独立复算同口径笔数（不走宽表）
-- 【实测】funnel 66,407 笔 / 合同 98,943,127；宽表 65,972 → 缺 435~436 笔
-- 【判定】FAIL —— §1.9「65,972 笔 = 9/1~10/20 复贷放款 if_issue=1」不成立
-- ──────────────────────────────────────────────────────────────────────
select count(1) as rows_all, count(distinct biz_id) as biz_uniq,
       sum(cast(contract_amount as double)) as contract_sum
from mx.wxs_application_funnel
where issue_date >= date '2026-09-01' and issue_date <= date '2026-10-20'
  and if_issue = 1 and is_reloan = 'old';


-- ──────────────────────────────────────────────────────────────────────
-- A3 缺失笔落在哪天 —— 定位窗口残缺
-- 【实测】436 笔缺失中 434 笔全在 2026-10-20，另 9/17、9/28 各 1 笔
-- 【判定】FAIL —— 10/20 当日只落了约 2/3，该日一切指标不可用
-- ──────────────────────────────────────────────────────────────────────
with f as (
  select cast(biz_id as bigint) as biz_id, issue_date
  from mx.wxs_application_funnel
  where issue_date >= date '2026-09-01' and issue_date <= date '2026-10-20'
    and if_issue = 1 and is_reloan = 'old'
)
select f.issue_date, count(1) as missing_cnt
from f
left join mx.yj_temp_limit_wide_table_v3 v on v.biz_id = f.biz_id
where v.biz_id is null
group by f.issue_date
order by 2 desc
limit 25;


-- ──────────────────────────────────────────────────────────────────────
-- B1 ★ 核心恒等式 contract = main + offline + online + voucher
--    注意：NULL 必须单列断言，否则 abs() 判据会把 NULL 静默放过
-- 【实测】65,972 笔；五个分量 0 NULL；残差 >0.05 笔数 = 0；max|残差| = 3.6e-12
-- 【判定】PASS —— 这是 skill 最硬的结论，完全站得住
-- ──────────────────────────────────────────────────────────────────────
select count(1) as rows_all,
       sum(case when contract_amount    is null then 1 else 0 end) as n_contract_null,
       sum(case when main_used_this     is null then 1 else 0 end) as n_main_null,
       sum(case when offline_used_this  is null then 1 else 0 end) as n_offu_null,
       sum(case when online_used_this   is null then 1 else 0 end) as n_onu_null,
       sum(case when voucher_limit      is null then 1 else 0 end) as n_vou_null,
       sum(case when abs(contract_amount - (coalesce(main_used_this,0)
            + coalesce(offline_used_this,0) + coalesce(online_used_this,0)
            + coalesce(voucher_limit,0))) > 0.05 then 1 else 0 end) as n_resid_gt005,
       max(abs(contract_amount - (coalesce(main_used_this,0)
            + coalesce(offline_used_this,0) + coalesce(online_used_this,0)
            + coalesce(voucher_limit,0))))                          as max_abs_resid
from mx.yj_temp_limit_wide_table_v3;


-- ──────────────────────────────────────────────────────────────────────
-- B2 main_available_amount 是放款「前」还是「后」的可用额？
-- 【实测】主额支用 > 主额可用 仅 34 笔（其中 33 笔在 10/20）；
--        avg_credit 4,392.7 = avg_avail 2,702.2 + avg_occ 1,690.5（恒等）
-- 【判定】PASS（语义=放款前可用）；但 v2 注释 L10「放款前已占用」与
--        L69「事件发生后的账户级占用」自相矛盾，需择一删除
-- ──────────────────────────────────────────────────────────────────────
select count(1) as rows_all,
       sum(case when main_used_this > main_available_amount + 0.05 then 1 else 0 end) as n_used_gt_avail,
       sum(case when abs(main_used_this - main_available_amount) <= 0.05 then 1 else 0 end) as n_used_eq_avail,
       sum(case when main_available_amount is null then 1 else 0 end) as n_avail_null,
       avg(main_available_amount) as avg_avail, avg(main_used_this) as avg_used,
       avg(change_used_grantamount) as avg_occ, avg(credit_amount) as avg_credit
from mx.yj_temp_limit_wide_table_v3;


-- ──────────────────────────────────────────────────────────────────────
-- C1 110 笔「有离线用额、无离线发放记录」
-- 【实测】110 笔 / 离线使用 51,637 / 合同 242,633；offline_grant 与
--        offline_available 全为 0 → 破坏 used <= grant
-- 【判定】FIX —— §1.9 把它当 0.17% 小瑕疵，但它污染了按周使用率：
--        10-19 周出现 off_used_n(25) > off_grant_n(23)、使用率 86% 的荒谬值
-- ──────────────────────────────────────────────────────────────────────
select count(1) as cnt, sum(offline_used_this) as off_used,
       sum(contract_amount) as contract_sum,
       sum(case when offline_grant_amount = 0 then 1 else 0 end) as n_grant_zero,
       min(issue_date) as dmin, max(issue_date) as dmax
from mx.yj_temp_limit_wide_table_v3
where offline_used_this > 0 and offline_grant_amount = 0;


-- ──────────────────────────────────────────────────────────────────────
-- C2 1T0 的「笔数」与「比率分母」不是同一群
-- 【实测】none 52,417 笔中仅 43,473 笔 t0_should_capit_1>0（82.9%）；
--        offline 5,101/5,961（85.6%）；online 6,228/7,594（82.0%）
--        i1t0 = 28.63% / 24.87% / 26.32%（与 §1.9 一致）
-- 【判定】FIX —— 比率本身对（未成熟笔 should=0 自动不入分母），
--        但报「none 52,417 笔 + 1T0 28.6%」会被读成全量覆盖；须标注成熟笔数。
--        成熟度构成三组接近（82~86%），故组间比较是公平的。
-- ──────────────────────────────────────────────────────────────────────
select used_scenario, count(1) as n_all,
       sum(case when t0_should_capit_1 > 0 then 1 else 0 end) as n_should_pos,
       sum(case when is_t0_window_1 = 1 then 1 else 0 end) as n_window1,
       sum(t0_should_capit_1) as s1, sum(t0_overdue_capit_1) as o1,
       cast(sum(t0_overdue_capit_1) as double)
         / nullif(cast(sum(t0_should_capit_1) as double),0) as i1t0
from mx.yj_temp_limit_wide_table_v3
group by used_scenario order by 1;


-- ──────────────────────────────────────────────────────────────────────
-- D1 ★★ 离线批次兑现率四口径 —— 验 §1.9「批次口径 S/G≈74.9% 才是真兑现率」
-- 【实测】发放事件 25,003 条 / 10,866 mid（含 5,041 个拿了额度但窗口内未借款的 mid）
--        G1 全量去重发放额        31,676,600  → S/G1 = 12.9%
--        G2 仅有借款 mid 的发放额  25,759,850  → S/G2 = 15.8%
--        G3 每 mid 取最大一次      10,613,250  → S/G3 = 38.3%
--        G4 笔级（宽表按笔累加）   15,990,000  → S/G4 = 25.6%
--        S  实际使用               4,088,767
-- 【判定】FAIL —— 74.9% 在任何口径下都复现不出来。
--        74.9% 出处：墨西哥/临额封顶与业绩占比_结论.md L161，population 是
--        「已被至少一笔放款消耗过的 6,423 个发放事件」= 条件在"已被使用"上的
--        存活者样本，必然偏高。skill 反而把真实值 ≈16%（=S/G2 15.8%）判成"旧口径"。
--        批次去重后发放额(3,168万) > 笔级(1,599万)，所以批次兑现率只能更低、不可能更高。
-- ──────────────────────────────────────────────────────────────────────
with ev as (
  select c.mid, c.create_time,
         max(cast(c.change_total_grantamount as double)) as gamt
  from ods_view_presto.s05_user_creditlimit_change_record c
  where c.limit_type = 'TEMP'
    and c.change_event_type in ('C015','C013')
    and c.change_action = 'CHANGE_LIMIT'
    and cast(c.change_total_grantamount as double) > 0
    and c.create_time >= timestamp '2026-09-01 00:00:00'
    and c.create_time <= timestamp '2026-10-15 23:59:59'
  group by 1,2
),
ev_mid as (select mid, sum(gamt) as gamt_sum, max(gamt) as gamt_max from ev group by 1),
use_mid as (
  select mid, sum(offline_used_this) as used_sum, sum(offline_grant_amount) as g_order
  from mx.yj_temp_limit_wide_table_v3 group by 1
)
select (select count(1) from ev)            as ev_n,
       (select count(distinct mid) from ev) as ev_mid_n,
       (select sum(gamt) from ev)           as g1_event_dedup_all,
       sum(case when u.mid is not null then e.gamt_sum else 0 end) as g2_dedup_borrow_mid,
       sum(case when u.mid is not null then e.gamt_max else 0 end) as g3_max_per_borrow_mid,
       (select sum(g_order) from use_mid)   as g4_order_level,
       (select sum(used_sum) from use_mid)  as s_used_all
from ev_mid e full outer join use_mid u on u.mid = e.mid;


-- ──────────────────────────────────────────────────────────────────────
-- D2 10/20 残缺日的污染量化
-- 【实测】before(9/1~10/19) 64,837 笔 | d1020 1,135 笔
--        occ=0 占比：before 35.4% vs d1020 98.5%（台账未落库）
--        主额越界：before 1 笔 vs d1020 33 笔
--        1T0 成熟：before 54,802 笔 vs d1020 0 笔
-- 【判定】FAIL —— 10/20 必须整日剔除。
--        顺带解释：岳松手上那份「20261020临额业绩分析V1.xlsx」数据源 64,844 笔
--        ≈ before 段 64,837 笔，即那份 Excel 其实是干净的 9/1~10/19 窗口。
-- ──────────────────────────────────────────────────────────────────────
select case when issue_date = date '2026-10-20' then 'd1020' else 'before' end as seg,
       count(1) as n, sum(contract_amount) as contract_sum,
       sum(case when main_used_this > main_available_amount + 0.05 then 1 else 0 end) as n_main_excess,
       sum(case when change_used_grantamount = 0 then 1 else 0 end) as n_occ_zero,
       sum(case when cap_type <> 'N' then 1 else 0 end) as n_capped,
       sum(add_if_cap_50000) as add_if_50000,
       sum(case when t0_should_capit_1 > 0 then 1 else 0 end) as n_t0_mature
from mx.yj_temp_limit_wide_table_v3
group by 1 order by 1;


-- ──────────────────────────────────────────────────────────────────────
-- D3 撞顶重算（剔 10/20）—— 验 §1.9「撞顶 342 笔 / 被压 285.05 万」
-- 【实测】A 89 笔 / 799,992   （skill: 92 笔 / 85.2 万）
--        B 144 笔 / 1,408,329（skill: 144 笔 / 140.8 万）
--        C 102 笔 / 544,880  （skill: 106 笔 / 59.0 万）
--        合计 335 笔 / 2,753,200（skill: 342 笔 / 285.05 万）
-- 【判定】FIX —— 方向稳健，数字小改（-2.0% 笔数 / -3.4% 金额）。
--        但 add_if_cap_50000 的不确定性来自 occ=0：撞顶组 occ=0 占比
--        A 12.4% / B 24.3% / C 37.3%，这些笔 main_available 被按授信全额算，
--        会高估可放开空间。该 275 万应作为上界看。
-- ──────────────────────────────────────────────────────────────────────
select cap_type, count(1) as n, sum(contract_amount) as contract_sum,
       sum(add_if_cap_50000) as add_if_50000,
       avg(main_used_this) as avg_main_used, avg(main_available_amount) as avg_main_avail,
       sum(case when change_used_grantamount = 0 then 1 else 0 end) as n_occ_zero
from mx.yj_temp_limit_wide_table_v3
where issue_date < date '2026-10-20'
group by cap_type order by cap_type;


-- ──────────────────────────────────────────────────────────────────────
-- E1 ★★★ 在线临额领取率随 type 单调反向 —— skill 未发现
-- 【实测】claim_rate（领取笔/弹窗笔）与 avg_main_available：
--        V5_2 type1 13.5% (主额可用均值 11,797) / type2 25.4% (6,593)
--             type3 69.7% (3,365)             / type4 95.2% (1,717)
--        V5_3 type1 16.9% (8,760)            / type2 48.8% (3,198)
--             type3 72.9% (1,604)            / type4 100%  (1,061)
-- 【判定】新增结论 —— 机制是「主额花不完的人不需要临额」。
--        §1.9 结论②「提升领取率收益高于扩额」对 type1 是错的药：
--        type1 未领取不是转化问题，是额度冗余。
-- ──────────────────────────────────────────────────────────────────────
select strategy_version, use_type_1523, count(1) as n,
       sum(case when online_grant_amount > 0 then 1 else 0 end) as grant_n,
       sum(online_grant_amount) as grant_amt,
       sum(case when online_used_this > 0 then 1 else 0 end) as claim_n,
       sum(online_used_this) as used_amt,
       cast(sum(case when online_used_this > 0 then 1 else 0 end) as double)
         / nullif(cast(sum(case when online_grant_amount > 0 then 1 else 0 end) as double),0) as claim_rate,
       avg(main_used_this) as avg_main_used, avg(main_available_amount) as avg_main_avail
from mx.yj_temp_limit_wide_table_v3
where strategy_version is not null
group by 1,2 order by 1,2;


-- ──────────────────────────────────────────────────────────────────────
-- F0 ★★★ 日帽 daily_max 到底约不约束？（先定这个，F1 的口径才能定）
-- 【实测】64,837 笔中 main_used_this > daily_max 的 = 0 笔（零违反）；
--        恰好顶在日帽 9,959 笔（15.4%）；主额可用 > 日帽 16,023 笔（24.7%，
--        即日帽是比主额余额更紧的那道约束）
-- 【根因已定位，见 F0b】宽表 daily_max vs 1067 节点 daily_max，64,837 笔全匹配：
--        93.7%(60,774) 相同、6.3%(4,061) 宽表更大、1 笔宽表更小；
--        用 1067 快照比 → main_used > daily 有 2,380 笔（即 §1.5 那「2,072 笔」）
--        用宽表修正值比 → 0 笔
-- 【判定】UNRESOLVED（2026-10-21 二次修订，撤回初版「FAIL / 日帽是硬约束」的结论）
--   ★ 宽表的 daily_max 不是原始观测值：v2 建表 SQL 有一条**单向上修**规则 ——
--     WHEN yj日帽 < 本笔占用主额 THEN GREATEST(COALESCE(s1077日帽, yj日帽), yj日帽)
--     即「发现不自洽就往上调」，三个源(yj / 1067 / 1077)里有一个够大就会被选中。
--     所以「宽表口径 0 笔越界」主要反映规则设计，**不能当作日帽约束力的独立证据**。
--   ★ 三个源各说一套（同一批 64,837 笔，见 F0b）：
--        1067 口径  2,380 笔越界 (3.67%)   ← §1.5 说的「2,072 笔」就是这个
--        1077 口径    327 笔越界 (0.50%)
--        宽表口径       0 笔越界           ← 被上修规则抹平
--   → 结论：日帽既不是「完全不约束」(§1.5)，也不是「0 违反的硬约束」(本校验初版)。
--     它是一道多源不一致的限制，真实约束力这份数据**判不了**，需要问产品/风控：
--     用信页「可借上限」展示的是哪个口径、是否真的拦下过放款。
--   ⚠️ 连带影响：F1 里 B 组（主额够但日帽不够，1,777 笔 / 181.8 万）算不算增量取决于本条，
--     故 F1 的真增量只能给区间，不能给单值。
-- ──────────────────────────────────────────────────────────────────────
-- F0b 宽表 daily_max 与 1067 快照的分歧（上面的根因证据）
with n1067 as (
  select biz_id,
         max(try_cast(nullif(regexp_extract(cast(outputdata as varchar),
             '"daily_max_available_limit":(-?[0-9.]+)', 1), '') as double)) as daily_1067
  from ods.s21_risk_model_record
  where modelmainid = 1067 and strategytype = 'CHAMPION'
    and createtime >= timestamp '2026-08-20 00:00:00'
    and createtime <= timestamp '2026-10-22 00:00:00'
  group by 1
)
select count(1) as n_matched,
       sum(case when abs(v.daily_max_available_limit - n.daily_1067) <= 0.05 then 1 else 0 end) as n_same,
       sum(case when v.daily_max_available_limit > n.daily_1067 + 0.05 then 1 else 0 end) as n_wide_gt,
       sum(case when v.main_used_this > n.daily_1067 + 0.05 then 1 else 0 end) as n_used_gt_1067,
       sum(case when v.main_used_this > v.daily_max_available_limit + 0.05 then 1 else 0 end) as n_used_gt_wide
from mx.yj_temp_limit_wide_table_v3 v
join n1067 n on n.biz_id = v.biz_id
where v.issue_date < date '2026-10-20';

-- F0c 顶在日帽的笔，主额是否还有余额（证明日帽是更紧的那道约束）
-- 【实测】顶日帽 9,959 笔中 8,623 笔(86.6%) 主额仍有余额，平均还剩 1,242；
--        该组临额使用 2,345,357（2,546 笔动用）→ 这些临额是「绕开日帽」的真增量
select case when abs(main_used_this - daily_max_available_limit) <= 0.05 then 'at_daily_cap'
            else 'other' end as seg,
       count(1) as n,
       sum(case when main_available_amount > main_used_this + 0.05 then 1 else 0 end) as n_main_still_left,
       avg(main_available_amount - main_used_this) as avg_main_left,
       sum(offline_used_this + online_used_this) as temp_used,
       sum(case when offline_used_this + online_used_this > 0 then 1 else 0 end) as n_temp_used
from mx.yj_temp_limit_wide_table_v3
where issue_date < date '2026-10-20'
group by 1 order by 1;
-- ──────────────────────────────────────────────────────────────────────
select count(1) as n,
       sum(case when main_used_this > daily_max_available_limit + 0.05 then 1 else 0 end) as n_used_gt_daily,
       sum(case when abs(main_used_this - daily_max_available_limit) <= 0.05 then 1 else 0 end) as n_used_eq_daily,
       sum(case when main_available_amount > daily_max_available_limit + 0.05 then 1 else 0 end) as n_avail_gt_daily,
       avg(daily_max_available_limit) as avg_daily, avg(main_used_this) as avg_main_used
from mx.yj_temp_limit_wide_table_v3
where issue_date < date '2026-10-20';


-- ──────────────────────────────────────────────────────────────────────
-- F1 ★★★ 「使用顺序先主额后临额」是否成立 —— 真增量 vs 替代
--    三分：A 主额和日帽都够(纯替代) / B 主额够但日帽不够 / C 主额确实不够
-- 【实测】(窗口 9/1~10/19，放款额 96,483,809)
--        A 纯替代        2,150 笔 / 临额 1,415,142 (占临额 18.5%，放款额 1.47%)
--        B 绕开日帽      1,777 笔 / 临额 1,817,945 (23.8%)
--        C 主额确实不够  9,476 笔 / 临额 4,411,883 (57.7%)
--        Z 未用临额     51,434 笔
--        A 组特征：主额可用均值 5,752、主额只支用 819、日帽 4,246 —— 额度绰绰有余
-- 【判定】★★ 2026-10-21 二次修订：**撤回初版「§1.1 先主额后临额 FAIL」的结论，
--        §1.1 改判 PASS。** 初版把「主额仍有余额」读成「临额替代了主额」，这是因果错误。
--   决定性反证 —— 台账时间戳（biz 1620000462179690）：
--        20:41:38  1067 授信 (credit 1500)
--        20:44:07  MAIN FREEZE 1,180   ← 用户自选主额在此锁定
--        20:46:17~19  1635→1522→1523(type2)→1386(tag1)→1379(=472)→857(=450)
--        21:05:04  TEMP FREEZE 450     ← 客户点确认才领取
--        21:15:43  放款，合同 1,630
--     主额冻结比整条临额决策链早 2 分钟，且 1379 的算额输入就是这个已冻结的 1,180
--     (floor(1180/20)*20*0.4 = 472)。另一笔 1620000483783958 时序完全相同。
--     → 临额在时间上不可能替代主额；主额先定，临额按主额支用额的比例叠加在之上。
--   → 所以「主额可用 5,752 却只支用 819」不是替代，是客户只想借那么多，
--     然后被弹窗加了一笔。临额贡献应回到归因口径 ≈7.92%。
--   ⚠️ 仍未定之处：若用信页「自选主额」那一步展示的可借上限已含预估临额，
--     则客户的主额选择不独立，归因口径会高估。需产品确认 UI 口径 +
--     用 1021 批次 20% 灰度对照组做件均 DID 才能定论。
--   【本查询仍有价值】A/B/C 三分不再读作「替代/增量」，而读作
--     「临额发放时客户的额度冗余程度」——A 组 2,150 笔（主额和日帽都绰绰有余）
--     说明这 141.5 万临额发给了根本不缺额度的人，是**发放精准度**问题（见 E1 的 type1 错配）。
-- ──────────────────────────────────────────────────────────────────────
select seg, count(1) as n, sum(temp_used) as temp_used,
       sum(contract_amount) as contract_sum,
       avg(main_available_amount) as avg_avail, avg(main_used_this) as avg_main_used,
       avg(daily_max_available_limit) as avg_daily
from (
  select contract_amount, main_available_amount, main_used_this, daily_max_available_limit,
         offline_used_this + online_used_this as temp_used,
         case
           when offline_used_this + online_used_this <= 0 then 'Z_no_temp'
           when main_available_amount - main_used_this >= offline_used_this + online_used_this - 0.05
                and daily_max_available_limit - main_used_this >= offline_used_this + online_used_this - 0.05
             then 'A_sub_both_ok'
           when main_available_amount - main_used_this >= offline_used_this + online_used_this - 0.05
             then 'B_main_ok_daily_short'
           else 'C_inc_main_short'
         end as seg
  from mx.yj_temp_limit_wide_table_v3
  where issue_date < date '2026-10-20'
) t
group by seg order by seg;


-- ──────────────────────────────────────────────────────────────────────
-- F2 「按比例混合」假说：在线临额 / 本笔主额支用 的比值是否聚在固定档
--    若聚在 {0.2,0.4,0.5,0.6} → 临额不是"补差"，而是按比例强制拆分
-- 【实测】峰值精确落在 0.20(1,905 笔)、0.40(1,022)、0.60(147)、0.50(140)，
--        ±0.01~0.03 的散开来自 857 的 round50 取整；
--        四个档正对 type3=20% / type2=40% / V5_2 type1=50% / V5_3 type1=60%
-- 【判定】假说成立 —— 在线临额用量 ≈ 本笔主额支用 × type 比例，且 100% 扣光。
--        即「按主额支用额的固定比例叠加」，不是「主额不够才补」。
--        离线侧（F3 查询）比值散在 0.1~2.0，因基准是主额度 curr_main_credit_limit
--        而非本笔支用 —— 这一条与 §1.8 一致，PASS。
-- ──────────────────────────────────────────────────────────────────────
select ratio_band, count(1) as n, sum(online_used_this) as on_used
from (
  select cast(round(online_used_this / nullif(main_used_this,0), 2) as varchar) as ratio_band,
         online_used_this
  from mx.yj_temp_limit_wide_table_v3
  where issue_date < date '2026-10-20' and online_used_this > 0
) t
group by ratio_band order by n desc limit 20;


-- ──────────────────────────────────────────────────────────────────────
-- G 逐笔穿透模板（把 FOCUS 换成要查的 biz_id）
--   G1 宽表声明 → G2 used_detail 冻结台账 → G3 决策链节点
--   三者对齐即可确认归属无误。已验样例：
--   · 1620000462179690：宽表 1630 = 主额 1180 + 在线 450；
--     台账 MAIN FREEZE 1180 + TEMP FREEZE 450 ✓；
--     决策链 1067 credit=1500→宽表取 C002 提额后 2300 ✓，
--     1379 = floor(1180/20)*20*0.4 = 472 ✓，857 = round(472/50)*50 = 450 ✓
--     ⚠️ 但 main_avail 2110、daily 2100 均 > 合同 1630 → 主额完全够付，
--        仍拆出 450 走在线临额 = 「先主额后临额」的反例
--   · 1620000483783958：宽表 12800 = 主额 8000 + 在线 4800；
--     台账 MAIN 8000 + TEMP 4800 ✓；1379 = 8000*0.6 = 4800 ✓（V5_3 type1）
--     ⚠️ 宽表 credit_amount=4800 < 主额支用 8000 → 1067 快照（10/16）已被
--        10/20 的 C002 提额改写，宽表 credit/main_available 失真
-- ──────────────────────────────────────────────────────────────────────
-- G1
select biz_id, mid, issue_date, release_time, contract_amount, credit_amount,
       change_used_grantamount, main_available_amount, daily_max_available_limit,
       main_used_this, offline_grant_amount, offline_used_this,
       online_grant_amount, online_used_this, voucher_limit,
       used_scenario, grant_scenario, cap_type, use_type_1523, issue_tag_1386,
       strategy_version, add_if_cap_50000
from mx.yj_temp_limit_wide_table_v3
where biz_id in (1620000462179690, 1620000483783958);

-- G2
select cast(biz_id as varchar) as biz_id, limit_type, change_action,
       sum(cast(risk_credit_limit as double)) as freeze_amt,
       sum(cast(voucher_limit as double)) as voucher_sum,
       count(1) as rows_n, min(create_time) as t_min, max(create_time) as t_max
from ods.s05_user_creditlimit_used_detail
where biz_id in (1620000462179690, 1620000483783958)
group by 1,2,3 order by 1,2,3;

-- G3（⚠️ 必须 strategytype='CHAMPION'；1379 每笔两条取非空；
--     窗口要比业务窗口前后各放宽，跨天笔的决策落在 apply 时刻）
select biz_id, modelmainid, strategytype, createtime,
       regexp_extract(cast(outputdata as varchar), '"fd_use_creditamount_score_v1":(-?[0-9.]+)', 1) as score_1522,
       regexp_extract(cast(outputdata as varchar), '"fd_use_creditamount_type":(-?[0-9.]+)', 1)     as type_1523,
       regexp_extract(cast(outputdata as varchar), '"temp_credit_amount_issue_tag":(-?[0-9.]+)', 1) as tag_1386,
       regexp_extract(cast(outputdata as varchar), '"temp_credit_amount":(-?[0-9.]+)', 1)           as temp_amt,
       regexp_extract(cast(outputdata as varchar), '"credit_amount":(-?[0-9.]+)', 1)                as credit_amt,
       regexp_extract(cast(outputdata as varchar), '"daily_max_available_limit":(-?[0-9.]+)', 1)    as daily_max
from ods.s21_risk_model_record
where biz_id in (1620000462179690, 1620000483783958)
  and strategytype = 'CHAMPION'
  and modelmainid in (1522,1523,1386,1379,857,1067,1635)
  and createtime >= timestamp '2026-08-20 00:00:00'
  and createtime <= timestamp '2026-10-22 00:00:00'
order by biz_id, createtime, modelmainid;


-- ══════════════════════════════════════════════════════════════════════
-- H 块：对 v2 建表 SQL（放款资产额度指标_20260901起.sql）本身的代码审查取证
-- ══════════════════════════════════════════════════════════════════════

-- ──────────────────────────────────────────────────────────────────────
-- H1 ★ 三套可用额度口径能否复现
-- 【实测】64,837 笔：
--        LEAST(LEAST(主额可用, 日帽) + 离线可用, 产品上限)  → 64,837 (100%)  ← 真公式
--        LEAST(主额可用 + 离线可用, 日帽)                  → 59,567 (91.9%) ← 校验初版用错的
--        avail_tochange = LEAST(主额可用, 日帽) + 离线可用  → 64,837 (100%)
--        avail_future   = 主额可用 + 离线可用               → 64,837 (100%)
-- 【判定】PASS —— 三套口径全部 100% 可复现。**撤回初版「仅 91.9% 可复现」的指控**，
--        那是校验方套错公式。
--   ★ 机制含义（值得写进 skill）：单日可借上限**只压主额**，
--     离线临额是叠加在「日帽之后」的，不受日帽约束。
-- ──────────────────────────────────────────────────────────────────────
select count(1) as n,
       sum(case when abs(avail_current_logic
            - least(least(main_available_amount, daily_max_available_limit)
                    + offline_available_amount, product_limit_max)) <= 0.05
           then 1 else 0 end) as n_match_correct,
       sum(case when abs(avail_tochange_logic
            - (least(main_available_amount, daily_max_available_limit)
               + offline_available_amount)) <= 0.05 then 1 else 0 end) as n_match_tochange,
       sum(case when abs(avail_future_logic
            - (main_available_amount + offline_available_amount)) <= 0.05
           then 1 else 0 end) as n_match_future
from mx.yj_temp_limit_wide_table_v3
where issue_date < date '2026-10-20';


-- ──────────────────────────────────────────────────────────────────────
-- H2 risk_credit_limit 与 main_used_this 两列同候选集、反优先级，是否真分歧
--     risk_credit_limit := COALESCE(yj, c003, usedm, contract-temp)
--     main_used_this    := COALESCE(c003, usedm, yj, contract-temp)
-- 【实测】64,837 笔 0 分歧，max|差| = 4.3e-12，risk 列 0 空值
-- 【判定】FIX（冗余非 bug）—— 两列实测同义。建议合并成一列，或在注释里写明
--        「二者同义，保留 risk_credit_limit 仅为兼容源表命名」，否则下游易误以为是两个口径。
-- ──────────────────────────────────────────────────────────────────────
select count(1) as n,
       sum(case when abs(risk_credit_limit - main_used_this) > 0.05 then 1 else 0 end) as n_diff,
       sum(case when risk_credit_limit is null then 1 else 0 end) as n_risk_null,
       max(abs(risk_credit_limit - main_used_this)) as max_abs_diff
from mx.yj_temp_limit_wide_table_v3
where issue_date < date '2026-10-20';


-- ──────────────────────────────────────────────────────────────────────
-- H3 voucher 兜底隐患：注 5 要求「用合同额倒推时必须先扣 voucher_limit」，
--    但代码两处兜底 `contract_amount - COALESCE(temp_used,0)` 都没扣券
-- 【实测】193 笔券单 / 合计 38,500；恒等式破坏 0 笔；主额吃进券 0 笔
-- 【判定】LATENT（潜在未触发）—— 这 193 笔的主额都从 C003/used_detail 台账取到了真值，
--        没走到最后那级兜底，所以没踩到。但一旦某张券单同时缺 C003、used_detail、
--        yj risk_credit_limit，main_used_this 就会多算一个券面值、恒等式破。
--        建议把两处兜底改成 `contract_amount - temp_used - COALESCE(voucher_limit,0)`。
-- ──────────────────────────────────────────────────────────────────────
select count(1) as n_voucher_rows, sum(voucher_limit) as voucher_sum,
       sum(case when abs(contract_amount - main_used_this - offline_used_this
                         - online_used_this - voucher_limit) > 0.05
                then 1 else 0 end) as n_identity_break,
       sum(case when abs(main_used_this - (contract_amount - offline_used_this
                         - online_used_this)) <= 0.05 then 1 else 0 end) as n_main_includes_voucher
from mx.yj_temp_limit_wide_table_v3
where issue_date < date '2026-10-20' and voucher_limit > 0;
