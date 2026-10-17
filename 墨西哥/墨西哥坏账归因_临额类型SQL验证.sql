-- =====================================================================
-- 墨西哥 0810 后坏账风险归因 —— 临额类型(在线/离线) SQL 验证脚本
-- 数据源: Presto(盘古)
--   主表:      mx.wxs_application_funnel f        (475列宽表, 关联键 = mid)
--   额度记录表: ods_view_presto.s05_user_creditlimit_change_record
--   离线临额表: mx.yuhan_temp_limit_base_table_his_20260924
--
-- 临额口径(来自 14.墨西哥离线发临额.sql):
--   在线临额: change_event_type = 'C010'  (用信时触发用信临额决策流, 用户确认使用临额后变更)
--   离线临额: change_event_type IN ('C013','C015')  (离线发放临额)
--     C015 = 离线临额发放主事件, change_total_grantamount = 临额金额
--     C013 = 10%/20%档发放临额; C015 = 30%档发放临额
--
-- 打标逻辑: 放款(release_time)之前最近一次 TEMP 事件类型, 用 biz_id 关联去重
--   (biz_id 在 if_issue=1 下唯一, 已验证 26087 行 = 26087 biz_id)
--
-- 关键结论(8/3周→8/10周, 1t0本金% 25.36%→28.63%, +3.27pp):
--   离线临额(C013/C015) 贡献 +1.32pp > 在线临额(C010) +1.04pp
--   最大单格: 非7天·老复贷·离线C013_15 (21.67%→24.04%, +1.16pp)
-- =====================================================================


-- =====================================================================
-- 【查询 A】额度记录表事件分布 —— 确认 C010 / C013 / C015 口径
-- 预期: C015 笔数最多(离线主事件), C010 次之(在线), C013 较少
-- =====================================================================
select change_event_type, limit_type,
  count(*) cnt, count(distinct mid) mids,
  min(create_time) mn, max(create_time) mx
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type = 'TEMP'
group by 1, 2
order by 3 desc;


-- =====================================================================
-- 【查询 B】离线临额用户表 样本 + 批次分布
-- 预期: temp_limit_tag 为各批次测试组(有在贷/无在贷), 约130个批次
-- =====================================================================
select mid, app_group, onloan_cnt, curr_overdue_days,
       curr_main_credit_limit, curr_temp_credit_limit,
       temp_limit_issue_date, temp_limit_tag, temp_limit_issue_amount, data_date
from mx.yuhan_temp_limit_base_table_his_20260924
limit 10;

select temp_limit_tag,
  count(*) cnt, count(distinct mid) mids,
  sum(temp_limit_issue_amount) amt,
  round(avg(temp_limit_issue_amount),2) amt_avg
from mx.yuhan_temp_limit_base_table_his_20260924
group by 1 order by 2 desc;


-- =====================================================================
-- 【查询 C】核心对比: 在线 vs 离线 vs 无临额 坏账率(放款周, 放款前最近事件打标)
-- 预期: 8/03 在线22.87% 离线23.22% 无33.38%; 8/10 在线29.00% 离线25.97% 无37.47%
-- =====================================================================
with tmp_evt as (
  select mid, change_event_type, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type = 'TEMP' and change_event_type in ('C010','C013','C015')
),
evt_last as (
  select biz_id, mid, change_event_type,
    row_number() over (partition by biz_id order by create_time desc) as rn
  from (
    select f.biz_id, f.mid, e.change_event_type, e.create_time
    from mx.wxs_application_funnel f
    join tmp_evt e on f.mid = e.mid and e.create_time <= f.release_time
    where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
      and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
  ) x
)
select date_trunc('week', date(f.release_time)) as w,
  case
    when el.change_event_type='C010' then '在线临额C010'
    when el.change_event_type in ('C013','C015') then '离线临额C013_15'
    when f.temp_grant_amount>0 then '有临额未匹配'
    else '无临额' end as tl,
  sum(f.t0_should_capit_1) as shd,
  sum(f.t0_overdue_capit_1) as ovd,
  sum(f.if_issue) as cnt,
  round(sum(f.t0_overdue_capit_1)/nullif(sum(f.t0_should_capit_1),0)*100,2) as "1t0本金%"
from mx.wxs_application_funnel f
left join evt_last el on f.biz_id = el.biz_id and el.rn=1
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
group by 1,2 order by 1,2;


-- =====================================================================
-- 【查询 D】临额类型 × 期限(7天/非7天) 坏账率对比
-- 预期: 离线·非7天 是最大单格, 率 21.43%→24.39% (+2.96pp)
-- =====================================================================
with tmp_evt as (
  select mid, change_event_type, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type = 'TEMP' and change_event_type in ('C010','C013','C015')
),
evt_last as (
  select biz_id, mid, change_event_type,
    row_number() over (partition by biz_id order by create_time desc) as rn
  from (
    select f.biz_id, f.mid, e.change_event_type, e.create_time
    from mx.wxs_application_funnel f
    join tmp_evt e on f.mid = e.mid and e.create_time <= f.release_time
    where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
      and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
  ) x
)
select date_trunc('week', date(f.release_time)) as w,
  case when f.loan_cycle=7 then '7天' else '非7天' end as d7,
  case
    when el.change_event_type='C010' then '在线C010'
    when el.change_event_type in ('C013','C015') then '离线C013_15'
    else '无/未匹配' end as tl,
  sum(f.t0_should_capit_1) as shd,
  sum(f.t0_overdue_capit_1) as ovd,
  sum(f.if_issue) as cnt,
  round(sum(f.t0_overdue_capit_1)/nullif(sum(f.t0_should_capit_1),0)*100,2) as "1t0本金%"
from mx.wxs_application_funnel f
left join evt_last el on f.biz_id = el.biz_id and el.rn=1
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
group by 1,2,3 order by 1,2,3;


-- =====================================================================
-- 【查询 E】三维: 临额类型 × 期限 × 复贷(首复贷/老复贷)
-- 预期最大单格: 非7天·老复贷·离线C013_15 (贡献 +1.16pp)
-- 复贷口径: reloan_num<=2 = 首复贷; >2 = 老复贷
-- =====================================================================
with tmp_evt as (
  select mid, change_event_type, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type = 'TEMP' and change_event_type in ('C010','C013','C015')
),
evt_last as (
  select biz_id, mid, change_event_type,
    row_number() over (partition by biz_id order by create_time desc) as rn
  from (
    select f.biz_id, f.mid, e.change_event_type, e.create_time
    from mx.wxs_application_funnel f
    join tmp_evt e on f.mid = e.mid and e.create_time <= f.release_time
    where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
      and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
  ) x
)
select date_trunc('week', date(f.release_time)) as w,
  case when f.loan_cycle=7 then '7天' else '非7天' end as d7,
  case when f.reloan_num<=2 then '首复贷' else '老复贷' end as rn,
  case
    when el.change_event_type='C010' then '在线C010'
    when el.change_event_type in ('C013','C015') then '离线C013_15'
    else '无/未匹配' end as tl,
  sum(f.t0_should_capit_1) as shd,
  sum(f.t0_overdue_capit_1) as ovd,
  sum(f.if_issue) as cnt,
  round(sum(f.t0_overdue_capit_1)/nullif(sum(f.t0_should_capit_1),0)*100,2) as "1t0本金%"
from mx.wxs_application_funnel f
left join evt_last el on f.biz_id = el.biz_id and el.rn=1
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16'
group by 1,2,3,4 order by 1,2,3,4;


-- =====================================================================
-- 【查询 F】关联键校验 —— funnel.cust_id 与 funnel.mid 是两套ID
-- 必须用 f.mid 关联额度表/离线临额表, 不能用 cust_id
-- =====================================================================
select count(*) rows_cnt, count(distinct f.biz_id) biz_cnt,
  count(distinct f.mid) mid_cnt, count(distinct f.cust_id) cust_cnt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16';

-- 用 mid 关联命中(正确)
select count(distinct f.mid) hit_mid
from mx.wxs_application_funnel f
join ods_view_presto.s05_user_creditlimit_change_record e
  on f.mid = e.mid and e.limit_type='TEMP'
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16';

-- 用 cust_id 关联命中(错误, 应为 0)
select count(distinct f.cust_id) hit_cust
from mx.wxs_application_funnel f
join ods_view_presto.s05_user_creditlimit_change_record e
  on cast(f.cust_id as bigint) = e.mid and e.limit_type='TEMP'
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-03' and date '2026-08-16';
