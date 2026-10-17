"""执行 LTV 代码第 6b-12 段"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功!")

def exec_and_check(sql, desc):
    print(f"\n{desc}")
    try:
        result = pq.query(sql)
        if isinstance(result, pd.DataFrame):
            if len(result) > 0 and len(result.columns) <= 10:
                print(result.to_string())
            else:
                print(f"  返回 {len(result)} 行数据")
        else:
            print(f"  结果: {result}")
        return result
    except Exception as e:
        print(f"  错误: {e}")
        return None

print("===== 6b. 首贷CAC =====")
sql = """drop table if exists mx.ys_mx_ltv_first_loan_cac;
create table mx.ys_mx_ltv_first_loan_cac as
with first_loan as (
    select
        ltv_month,
        cost_app_channel as app_channel,
        register_media_source as new_media_source,
        count(distinct mid) as first_loan_mid,
        count(distinct lid) as first_loan_cnt,
        sum(contract_amount) as first_contract_amount
    from mx.ys_dl_ltv_first_loan_0511
    group by 1, 2, 3
),
cost as (
    select
        cost_month,
        app_channel,
        case
            when new_media_source in ('facebook', 'Google', 'tiktok', 'Apple Search Ads', 'organic') then new_media_source
            else 'other'
        end as new_media_source,
        sum(spend_usd) as spend_usd,
        sum(impressions) as impressions,
        sum(clicks) as clicks
    from mx.ys_mx_ltv_ads_cost
    group by 1, 2, 3
)
select
    coalesce(f.ltv_month, c.cost_month) as ltv_month,
    coalesce(f.app_channel, c.app_channel) as app_channel,
    coalesce(f.new_media_source, c.new_media_source) as new_media_source,
    coalesce(f.first_loan_mid, 0) as first_loan_mid,
    coalesce(f.first_loan_cnt, 0) as first_loan_cnt,
    coalesce(f.first_contract_amount, 0) as first_contract_amount,
    coalesce(c.spend_usd, 0) as spend_usd,
    coalesce(c.impressions, 0) as impressions,
    coalesce(c.clicks, 0) as clicks,
    coalesce(c.spend_usd, 0) / nullif(f.first_loan_mid, 0) as cac_usd_per_first_mid,
    coalesce(c.spend_usd, 0) / nullif(f.first_loan_cnt, 0) as cac_usd_per_first_order
from first_loan f
full outer join cost c
    on f.ltv_month = c.cost_month
   and f.app_channel = c.app_channel
   and f.new_media_source = c.new_media_source"""

exec_and_check(sql, "执行首贷CAC DDL...")
exec_and_check("select count(1) from mx.ys_mx_ltv_first_loan_cac", "首贷CAC行数:")
exec_and_check("select * from mx.ys_mx_ltv_first_loan_cac limit 5", "首贷CAC预览:")

print("\n===== 7. 复贷LTV明细 =====")
sql = """drop table if exists mx.ys_dl_ltv_doulbe_loan_0511;
create table mx.ys_dl_ltv_doulbe_loan_0511 as
select
    z.zr_date,
    z.zr_mid,
    z.zr_result,
    z.deal_num as zr_rank,
    z.zr_id,
    z.is_t30_zhunru,
    q.qz_date,
    q.qz_mid,
    q.pre_credit_result,
    q.deal_num as qz_rank,
    q.qz_id,
    j.mid as apply_mid,
    j.apply_date,
    j.status,
    j.deal_num as apply_rank,
    j.biz_id as apply_id,
    j.loan_period,
    date_trunc('month', date(l.release_time)) as release_month,
    date_trunc('week', date(l.release_time)) as release_week,
    d.ltv_month,
    d.cost_app_channel,
    d.register_media_source,
    coalesce(
        date_diff('week', d.ltv_week, date_trunc('week', date(l.release_time))),
        date_diff('week', d.ltv_week, date_trunc('week', date(j.apply_date))),
        date_diff('week', d.ltv_week, date_trunc('week', date(q.qz_date))),
        date_diff('week', d.ltv_week, date_trunc('week', date(z.zr_date)))
    ) as wob,
    l.mid,
    d.app_channel_name,
    d.new_grade_level,
    l.biz_id as lid,
    l.release_date as trade_start_date,
    l.trade_end_date,
    l.finish_time,
    l.loan_rank - 1 as rank,
    case when date_diff('day', l.trade_end_date, current_date) > 30 then 1 else 0 end as is_T30_wp,
    case when date_diff('day', l.trade_end_date, current_date) > 7 then 1 else 0 end as is_T7_wp,
    l.loan_cycle,
    case when coalesce(l.haircut_amount, 0) > 0 then '前置' else '后置' end as fee_type,
    (coalesce(l.fee_amount, 0) + coalesce(l.interest, 0) + coalesce(l.haircut_amount, 0))
        / nullif(l.contract_amount, 0) as fee,
    l.contract_amount as contract_amt,
    coalesce(r.should_amt, l.amount + coalesce(l.fee_amount, 0) + coalesce(l.interest, 0) + coalesce(l.haircut_amount, 0)) as should_amt,
    l.loan_state as lid_status_code,
    r.rid,
    r.fact_time,
    r.fact_capital,
    r.fact_interest,
    r.now_subtract_amt,
    r.now_coupon_amt,
    r.t7_should_amt,
    r.t30_should_amt,
    r.t7_should_capital,
    r.t30_should_capital,
    r.t7_fact_amt,
    r.t7_fact_amt_coup,
    r.t30_fact_amt,
    r.t30_fact_amt_coup,
    rz.zr_id as rz_id,
    rz.zr_time as rz_time,
    row_number() over(partition by l.mid, l.biz_id, l.release_time order by l.release_time) as l_rnk,
    row_number() over(partition by l.mid, l.biz_id, r.rid, r.fact_time order by r.fact_time) as r_rnk
from mx.ys_dl_ltv_zr z
left join mx.ys_dl_ltv_first_loan_0511 d
    on z.zr_mid = d.mid
left join mx.ys_dl_ltv_qz_danti q
    on z.zr_mid = q.qz_mid
   and z.deal_num = q.deal_num
   and q.qz_date >= z.zr_date
left join mx.ys_dl_ltv_apply j
    on q.qz_id = j.biz_id
left join mx.ys_mx_ltv_base_loan l
    on cast(j.biz_id as varchar) = l.biz_id
left join mx.ys_dl_ltv_repay_order r
    on l.biz_id = r.camera_id
left join mx.ys_dl_ltv_zr rz
    on rz.zr_mid = l.mid
   and rz.deal_num = q.deal_num + 1
where l.loan_state in (1, 2, 3)
  and coalesce(l.double_loan, 1) = 1"""

exec_and_check(sql, "执行复贷LTV明细DDL...")
exec_and_check("select count(1) from mx.ys_dl_ltv_doulbe_loan_0511", "复贷LTV明细行数:")

print("\n===== 8. 复贷RAW聚合 =====")
sql = """drop table if exists mx.ys_dl_ltv_double_loan_group;
create table mx.ys_dl_ltv_double_loan_group as
with base as (
    select
        ltv_month,
        wob,
        app_channel_name,
        loan_period,
        new_grade_level,
        lid,
        mid,
        contract_amt,
        fee,
        trade_end_date,
        should_amt,
        fact_time,
        fact_capital,
        fact_interest,
        now_subtract_amt,
        now_coupon_amt,
        t7_should_amt,
        t30_should_amt,
        t7_should_capital,
        t30_should_capital,
        t7_fact_amt,
        t7_fact_amt_coup,
        t30_fact_amt,
        t30_fact_amt_coup,
        finish_time,
        loan_cycle,
        l_rnk,
        r_rnk,
        zr_mid,
        zr_id,
        zr_result,
        qz_mid,
        qz_id,
        pre_credit_result,
        apply_mid,
        apply_id,
        status,
        rz_time,
        (l_rnk = 1) as is_l_rnk_1,
        (r_rnk = 1) as is_r_rnk_1,
        (loan_cycle = 7) as is_7d,
        (loan_cycle = 14) as is_14d,
        (finish_time is not null) as is_finished,
        (trade_end_date < current_date) as is_trade_end_t0,
        (trade_end_date + interval '7' day < current_date) as is_trade_end_t7,
        (trade_end_date + interval '30' day < current_date) as is_trade_end_t30,
        (date(fact_time) <= trade_end_date) as is_fact_t0,
        (date(fact_time) <= trade_end_date + interval '7' day) as is_fact_t7,
        (date(fact_time) <= trade_end_date + interval '30' day) as is_fact_t30,
        (date(finish_time) + interval '7' day < current_date) as is_finish_t7,
        (date(finish_time) + interval '30' day < current_date) as is_finish_t30,
        (date(finish_time) <= trade_end_date + interval '7' day) as is_finish_before_end_plus7,
        (date(rz_time) <= date(finish_time) + interval '30' day) as is_rz_before_finish_plus30,
        (date(rz_time) <= date(finish_time) + interval '7' day) as is_rz_before_finish_plus7
    from mx.ys_dl_ltv_doulbe_loan_0511
)
select
    ltv_month as ltv_month_d,
    wob as wob_d,
    app_channel_name as app_channel_name_d,
    loan_period,
    new_grade_level as new_grade_level_d,
    count(distinct lid) as double_cnt,
    count(distinct mid) as double_mid,
    sum(case when is_l_rnk_1 then contract_amt end) as contract_amount,
    sum(case when is_l_rnk_1 then fee * contract_amt end) as fee_amount,
    sum(case when is_l_rnk_1 then contract_amt end) / nullif(count(distinct lid), 0) as avg_amount,
    sum(case when is_r_rnk_1 and is_trade_end_t0 then should_amt end) as should_amt_t0,
    sum(case when is_l_rnk_1 and is_trade_end_t7 then coalesce(t7_should_amt, should_amt) end) as should_amt_t7,
    sum(case when is_l_rnk_1 and is_trade_end_t30 then coalesce(t30_should_amt, should_amt) end) as should_amt_t30,
    sum(case when is_r_rnk_1 and is_trade_end_t0 then contract_amt end) as contract_t0,
    sum(case when is_l_rnk_1 and is_trade_end_t7 then coalesce(t7_should_capital, contract_amt) end) as contract_t7,
    sum(case when is_l_rnk_1 and is_trade_end_t30 then coalesce(t30_should_capital, contract_amt) end) as contract_t30,
    count(distinct case when is_trade_end_t0 then lid end) as should_cnt_t0,
    count(distinct case when is_trade_end_t7 then lid end) as should_cnt_t7,
    sum(case when is_r_rnk_1 and is_trade_end_t0 and is_fact_t0 then fact_capital + fact_interest end) as fact_t0,
    sum(case when is_l_rnk_1 and is_trade_end_t7 then t7_fact_amt end) as fact_t7,
    sum(case when is_l_rnk_1 and is_trade_end_t7 then coalesce(t7_fact_amt_coup, t7_fact_amt) end) as fact_t7_coup,
    sum(case when is_l_rnk_1 and is_trade_end_t30 then t30_fact_amt end) as fact_t30,
    sum(case when is_l_rnk_1 and is_trade_end_t30 then coalesce(t30_fact_amt_coup, t30_fact_amt) end) as fact_t30_coup,
    count(distinct case when is_trade_end_t0 and date(finish_time) <= trade_end_date then lid end) as fact_cnt_t0,
    count(distinct case when is_trade_end_t7 and t7_fact_amt >= t7_should_amt then lid end) as fact_cnt_t7,
    count(distinct case when is_trade_end_t30 and t30_fact_amt >= t30_should_amt then lid end) as fact_cnt_t30,
    count(distinct case when is_finished then lid end) as fact_cnt_till_now,
    sum(case when is_7d and is_l_rnk_1 then contract_amt end) as contract_amount_7d,
    sum(case when is_14d and is_l_rnk_1 then contract_amt end) as contract_amount_14d,
    sum(case when is_7d and is_l_rnk_1 and is_trade_end_t30 then coalesce(t30_should_amt, should_amt) end) as should_amt_7d,
    sum(case when is_14d and is_l_rnk_1 and is_trade_end_t30 then coalesce(t30_should_amt, should_amt) end) as should_amt_14d,
    sum(case when is_7d and is_l_rnk_1 and is_trade_end_t30 then t30_fact_amt end) as fact_t30_7d,
    sum(case when is_14d and is_l_rnk_1 and is_trade_end_t30 then t30_fact_amt end) as fact_t30_14d,
    count(distinct case when is_7d and is_l_rnk_1 then lid end) as double_cnt_7d,
    count(distinct case when is_14d and is_l_rnk_1 then lid end) as double_cnt_14d,
    sum(case when is_l_rnk_1 and is_7d then contract_amt end)
        / nullif(count(distinct case when is_7d and is_l_rnk_1 then lid end), 0) as avg_amount_7d,
    sum(case when is_l_rnk_1 and is_14d then contract_amt end)
        / nullif(count(distinct case when is_14d and is_l_rnk_1 then lid end), 0) as avg_amount_14d,
    count(distinct zr_mid) as zr_mid,
    count(distinct case when zr_result like 'PASS' then zr_mid end) as zr_pass_mid,
    count(distinct zr_id) as zr_cnt,
    count(distinct case when zr_result like 'PASS' then zr_id end) as zr_pass_cnt,
    count(distinct qz_mid) as qz_mid,
    count(distinct case when pre_credit_result like 'pass' then qz_mid end) as qz_pass_mid,
    count(distinct qz_id) as qz_cnt,
    count(distinct case when pre_credit_result like 'pass' then qz_id end) as qz_pass_cnt,
    count(distinct apply_mid) as apply_mid,
    count(distinct case when status = 372 then apply_mid end) as apply_pass_mid,
    count(distinct apply_id) as apply_cnt,
    count(distinct case when status = 372 then apply_id end) as apply_pass_cnt,
    count(distinct case when is_finish_t30 and t7_fact_amt >= t7_should_amt then lid end) as fact_cnt_t7_for_rzt30,
    count(distinct case when is_finish_t7 and t7_fact_amt >= t7_should_amt then lid end) as fact_cnt_t7_for_rzt7,
    count(distinct case when is_finish_before_end_plus7 and is_rz_before_finish_plus30 and is_finish_t30 then lid end) as re_zr_cnt_t30,
    count(distinct case when is_finish_before_end_plus7 and is_rz_before_finish_plus7 and is_finish_t7 then lid end) as re_zr_cnt_t7
from base
group by 1, 2, 3, 4, 5"""

exec_and_check(sql, "执行复贷RAW聚合DDL...")
exec_and_check("select count(1) from mx.ys_dl_ltv_double_loan_group", "复贷RAW聚合行数:")

print("\n===== 9. WOB补全 =====")
sql = """drop table if exists mx.ys_dl_ltv_double_loan_draw;
create table mx.ys_dl_ltv_double_loan_draw as
with frst_loan as (
    select
        ltv_month,
        app_channel_name,
        new_grade_level,
        count(distinct mid) as frs_cnt,
        sum(contract_amount) as frs_contract_amount
    from mx.ys_dl_ltv_first_loan_0511
    group by 1, 2, 3
),
maxwob as (
    select coalesce(max(wob_d), 110) as max_wob
    from mx.ys_dl_ltv_double_loan_group
),
wob_range as (
    select wob
    from maxwob
    cross join unnest(sequence(0, least(max_wob, 110))) as t(wob)
),
all_groups as (
    select distinct
        ltv_month,
        app_channel_name,
        new_grade_level
    from frst_loan
),
all_combinations as (
    select
        g.ltv_month,
        g.app_channel_name,
        g.new_grade_level,
        w.wob
    from all_groups g
    cross join wob_range w
),
double_combinations as (
    select
        c.ltv_month,
        c.app_channel_name,
        c.new_grade_level,
        c.wob,
        a.*,
        row_number() over(
            partition by c.ltv_month, c.app_channel_name, c.new_grade_level, c.wob
        ) as double_rnk
    from all_combinations c
    left join mx.ys_dl_ltv_double_loan_group a
        on a.ltv_month_d = c.ltv_month
       and a.app_channel_name_d = c.app_channel_name
       and a.new_grade_level_d = c.new_grade_level
       and a.wob_d = c.wob
)
select
    c.*,
    b.frs_cnt,
    b.frs_contract_amount,
    row_number() over(
        order by c.ltv_month, c.wob, c.app_channel_name, c.loan_period, c.new_grade_level
    ) as rnk
from double_combinations c
left join frst_loan b
    on c.ltv_month = b.ltv_month
   and c.app_channel_name = b.app_channel_name
   and c.new_grade_level = b.new_grade_level
   and c.double_rnk = 1
where c.wob <= 110"""

exec_and_check(sql, "执行WOB补全DDL...")
exec_and_check("select count(1) from mx.ys_dl_ltv_double_loan_draw", "WOB补全行数:")

print("\n===== 10. 90天复借率校验 =====")
sql = """drop table if exists mx.ys_mx_ltv_reloan_90d_check;
create table mx.ys_mx_ltv_reloan_90d_check as
with first_loans as (
    select
        date_trunc('month', release_time) as issue_month,
        mid,
        release_time,
        contract_amount
    from mx.ys_mx_ltv_base_loan
    where double_loan = 0
      and release_time >= timestamp '2025-07-01 00:00:00'
      and loan_state in (1, 2, 3)
),
reloans as (
    select
        mid,
        biz_id,
        release_time,
        contract_amount
    from mx.ys_mx_ltv_base_loan
    where double_loan = 1
      and release_time >= timestamp '2025-07-01 00:00:00'
      and loan_state in (1, 2, 3)
)
select
    a.issue_month,
    count(distinct a.mid) as first_loan_cnt,
    count(distinct b.biz_id) as reloan_bizid_cnt_90d,
    count(distinct b.mid) as reloan_mid_cnt_90d,
    sum(b.contract_amount) as reloan_amount_90d_mxn,
    round(count(distinct b.biz_id) * 1.0 / nullif(count(distinct a.mid), 0), 4) as reloan_rate_biz,
    round(count(distinct b.mid) * 1.0 / nullif(count(distinct a.mid), 0), 4) as reloan_rate_mid
from first_loans a
left join reloans b
    on a.mid = b.mid
   and b.release_time > a.release_time
   and date_diff('day', a.release_time, b.release_time) <= 90
group by 1"""

exec_and_check(sql, "执行90天复借率校验DDL...")
exec_and_check("select * from mx.ys_mx_ltv_reloan_90d_check", "90天复借率校验结果:")

print("\n===== 11. 通过率校验 =====")
sql = """drop table if exists mx.ys_mx_ltv_pass_rate_check;
create table mx.ys_mx_ltv_pass_rate_check as
with base as (
    select *
    from mx.daily_order_base
),
processor_flags as (
    select
        biz_id,
        max(case when current_processor in ('复贷授信拒绝') then 1 else 0 end) as if_in_fu_sx_refuse,
        case
            when sum(case when current_processor in ('首贷模型拒绝', '复贷模型拒绝') and approve_result = 'REFUSED' then 1 else 0 end) >= 1 then 0
            when sum(case when current_processor in ('首贷模型拒绝', '复贷模型拒绝') then 1 else 0 end) >= 1 then 1
            else 0
        end as if_model_passed,
        max(case when current_processor in ('首贷授信节点', '复贷授信节点') then 1 else 0 end) as if_in_confirm,
        max(case when current_processor in ('首贷授信等待节点', '复贷授信等待节点', '授信等待节点') then 1 else 0 end) as if_in_ruleDetermine_data,
        case
            when sum(case when current_processor in ('首贷授信等待节点', '复贷授信等待节点', '授信等待节点') and approve_result = 'PASSED' then 1 else 0 end) >= 1 then 1
            else 0
        end as if_normal_ruleDetermine_passed,
        case
            when sum(case when current_processor in ('首贷三方节点', '复贷三方节点') and approve_result = 'REFUSED' then 1 else 0 end) >= 1 then 0
            when sum(case when current_processor in ('首贷三方节点', '复贷三方节点') then 1 else 0 end) >= 1 then 1
            else 0
        end as if_external_data_passed
    from ods.s05_creditx_processor_record
    group by 1
),
global_limit_exclude as (
    select externalid as biz_id
    from ods.s21_risk_strategy_record
    where etl_date >= '20250226'
      and productid = 194
      and strategytype = 'CHAMPION'
      and cast(json_extract(outputdata, '$.available_limit_zero_mark') as int) = 1
      and cast(json_extract(outputdata, '$.global_limit_mark') as int) = 1
    group by 1
)
select
    b.create_date as data_date,
    b.app_channel,
    b.double_loan_new,
    b.reloan_num,
    b.product_name,
    b.os,
    b.new_media_source,
    count(distinct b.biz_id) as apply_cnt,
    count(distinct case when b.order_status = 372 then b.biz_id end) as pass_cnt,
    count(distinct case when pf.if_model_passed = 1 then b.biz_id end) as if_model_passed,
    count(distinct case when pf.if_in_ruleDetermine_data = 1 then b.biz_id end) as if_in_ruleDetermine_data,
    count(distinct case when pf.if_in_fu_sx_refuse = 1 then b.biz_id end) as if_in_fu_sx_refuse,
    count(distinct case when pf.if_normal_ruleDetermine_passed = 1 then b.biz_id end) as rule_determine_passed_cnt,
    count(distinct case when pf.if_external_data_passed = 1 then b.biz_id end) as if_external_data_passed,
    count(distinct case when pf.if_in_confirm = 1 then b.biz_id end) as if_in_confirm,
    round(count(distinct case when pf.if_model_passed = 1 then b.biz_id end) * 1.0 / nullif(count(distinct b.biz_id), 0), 4) as model_pass_rate,
    round(count(distinct case when b.order_status = 372 then b.biz_id end) * 1.0 / nullif(count(distinct case when pf.if_in_ruleDetermine_data = 1 then b.biz_id end), 0), 4) as post_pass_rate
from base b
left join processor_flags pf
    on b.biz_id = pf.biz_id
left join global_limit_exclude ge
    on b.biz_id = ge.biz_id
where b.create_date >= date '2025-01-01'
  and ge.biz_id is null
group by 1, 2, 3, 4, 5, 6, 7"""

exec_and_check(sql, "执行通过率校验DDL...")
exec_and_check("select count(1) from mx.ys_mx_ltv_pass_rate_check", "通过率校验行数:")

print("\n===== 12. 快速校验查询 =====")
exec_and_check("""select ltv_month, count(*) as first_loan_cnt, sum(contract_amount) as first_contract_amount
from mx.ys_dl_ltv_first_loan_0511
group by 1
order by 1 desc""", "首贷量校验:")

exec_and_check("""select ltv_month_d, wob_d, sum(double_cnt) as double_cnt, sum(contract_amount) as contract_amount
from mx.ys_dl_ltv_double_loan_group
group by 1, 2
order by 1 desc, 2
limit 20""", "复贷WOB校验:")

exec_and_check("""select
    ltv_month,
    sum(should_amt_t7) as should_amt_t7,
    sum(should_amt_t7 - fact_t7) / nullif(sum(should_amt_t7), 0) as bad_t7,
    sum(should_amt_t30) as should_amt_t30,
    sum(should_amt_t30 - fact_t30) / nullif(sum(should_amt_t30), 0) as bad_t30
from mx.ys_dl_ltv_first_loan_0511
group by 1
order by 1 desc""", "T7/T30坏账率校验:")

print("\n===== 最终所有表检查 =====")
tables = [
    "mx.ys_mx_ltv_base_funnel",
    "mx.ys_mx_ltv_base_loan",
    "mx.ys_dl_ltv_exchange_rate",
    "mx.ys_mx_ltv_ads_cost",
    "mx.ys_dl_ltv_zr",
    "mx.ys_dl_ltv_qz_danti",
    "mx.ys_dl_ltv_apply",
    "mx.ys_dl_ltv_repay",
    "mx.ys_dl_ltv_repay_order",
    "mx.ys_dl_ltv_first_loan_0511",
    "mx.ys_mx_ltv_first_loan_cac",
    "mx.ys_dl_ltv_doulbe_loan_0511",
    "mx.ys_dl_ltv_double_loan_group",
    "mx.ys_dl_ltv_double_loan_draw",
    "mx.ys_mx_ltv_reloan_90d_check",
    "mx.ys_mx_ltv_pass_rate_check",
]

print("\n表数据检查:")
for table in tables:
    try:
        result = pq.query(f"select count(1) as cnt from {table}")
        if isinstance(result, pd.DataFrame):
            cnt = result.iloc[0]['cnt']
            print(f"  {table}: {cnt} 行")
        else:
            print(f"  {table}: {result}")
    except Exception as e:
        print(f"  {table}: 错误 - {e}")