"""墨西哥LTV完整执行脚本 - 使用用户提供的首贷逻辑"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功!")

def exec_sql(sql, desc):
    print(f"\n{'='*60}")
    print(f"{desc}")
    print(f"{'='*60}")
    try:
        result = pq.query(sql)
        if isinstance(result, pd.DataFrame):
            print(f"  查询完成，返回 {len(result)} 行")
            if len(result) <= 5 and len(result.columns) <= 10:
                print(result.to_string())
        else:
            print(f"  DDL执行完成: {result}")
        return result
    except Exception as e:
        print(f"  错误: {e}")
        return None

def check_table(table_name):
    count_sql = f"select count(*) as cnt from {table_name}"
    try:
        result = pq.query(count_sql)
        if isinstance(result, pd.DataFrame):
            cnt = int(result.iloc[0]['cnt'])
            print(f"  {table_name}: {cnt} 行")
            return cnt
    except Exception as e:
        print(f"  {table_name}: 检查失败 - {e}")
    return -1

print("="*60)
print("开始执行墨西哥LTV完整流程")
print("="*60)

exec_sql("""
drop table if exists mx.ys_dl_ltv_first_loan_0511;
create table mx.ys_dl_ltv_first_loan_0511 as
select
    date_trunc('month', date(r.release_time)) as ltv_month, 
    date_trunc('week', date(r.release_time)) as ltv_week,
    r.loan_cycle, 
    r.app_channel,
    r.app_group as app_channel_name, 
    coalesce(f7.credit_level, 9999) as new_grade_level,
    case
        when lower(att.new_media_source) = 'facebook' then 'facebook'
        when lower(att.new_media_source) = 'google' then 'google'
        when lower(att.new_media_source) = 'tiktok' then 'tiktok'
        when lower(att.new_media_source) = 'apple search ads' then 'Apple Search Ads'
        when lower(att.new_media_source) = 'organic' then 'organic'
        else 'other'
        end as register_media_source,
    r.camera_id as biz_id, 
    cast(r.cust_id as bigint) as mid,
    
    (coalesce(r.haircut_amount, 0) + coalesce(r.should_interest, 0) ) / nullif(r.contract_amount, 0) as fee,
    r.contract_amount,
    r.haircut_amount,
    r.should_interest,
    r.should_interest+r.should_capital as should_amt,
    
    r.t7_should_amt_4 as should_amt_t7,
    r.t30_should_amt_4 as should_amt_t30,
    r.t7_should_capit_4 as contract_t7,
    r.t30_should_capit_4 as contract_t30,
    r.t7_fact_amt as fact_t7,
    r.t7_fact_amt as fact_t7_coup,
    r.t30_fact_amt as fact_t30,
    r.t30_fact_amt as fact_t30_coup,
    case when r.t0_fact_amt>0 then 1 else 0 end as fact_cnt_t0,
    case when r.t7_fact_amt>0 then 1 else 0 end as fact_cnt_t7,
    case when r.t30_fact_amt>0 then 1 else 0 end as fact_cnt_t30,
    case when r.now_fact_amt>0 then 1 else 0 end as fact_cnt_till_now,
    0 as re_zr_cnt_t30
from mx.wxs_application_funnel r 
left join ods.s02_loan t on r.camera_id=t.camera_id
left join mx.report_application_funnel7_table f7 on r.camera_id = cast(f7.biz_id as bigint)
left join mx.gm_attribution_detail att on cast(r.cust_id as bigint) = att.mid
where r.is_reloan = 'new'
  and r.if_issue=1 ; 
""", "1. 首贷 LTV 明细")
check_table("mx.ys_dl_ltv_first_loan_0511")

exec_sql("""
drop table if exists mx.ys_mx_ltv_ads_cost;
create table mx.ys_mx_ltv_ads_cost as
with channel_mapping as (
    select app_key, app_channel
    from (
        values
            ('com.tiri.mx', '2930a02e-07b9-4851-aedd-200244a62b75'),
            ('com.tengoprestamos.cash.credito.mx', '2930a02e-07b9-4851-aedd-200244a62b75'),
            ('com.prestamos.credito.peso.cashvivas', '5653600e-256f-4768-8b27-8020e16c2587'),
            ('com.cash.prestamo.yaweycredito', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.cash.rapido.dinero.credito.yawey', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.cash.rapido.dinero.credito.yaweycredito', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.prestamo.credito.cash.loan.yawey', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.mx.dinero.yawey', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.cash.credito.prestamo.holapresto', 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5'),
            ('com.mxprestamo.credito.cash.rapido.holapresto', 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5'),
            ('id6504391085', 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5'),
            ('com.voltrixcredito.prestamos', '91379659-2dc0-42d2-8205-9de6d81f7550'),
            ('com.cash.prestamos.credito.prontofondo', '026f5e80-4582-4821-847a-4665660d8451'),
            ('com.holapresto.se', 'faa92afe-b81a-4d94-ba1a-15eb9d536833'),
            ('com.holapresto.pro', 'db0d289f-d217-49ea-a889-c191776115ef'),
            ('com.holapresto.max', '4cc31ae6-937e-4fd3-bc98-862314e7cb68'),
            ('com.cash.prestamo.yaweycredito.plus', 'cdf58da5-801a-4575-9af4-a56453cea6f3'),
            ('com.cash.prestamo.yaweycredito.ultra', '9922eb08-b998-46d9-b81e-469ae4c2e0ec'),
            ('com.mexcredo.loan.mx', '002e5068-2b82-443e-9447-88ddba989753'),
            ('com.efectivo.presto.credi.tuna', '38cb07f1-21ce-47ed-b552-384381fbaa92'),
            ('com.dinero.prest.balam.plata', 'f280d23f-8d33-49c8-8aff-cbbda6045c75'),
            ('id6751942954', 'a73166d6-364d-405f-bb38-a06ba2141a0f'),
            ('com.quikpeso.credito.dinerorapido', 'a73166d6-364d-405f-bb38-a06ba2141a0f'),
            ('com.rapido.credito.mikredi', '20fbd6af-b9f8-48d4-bc30-4ad3040e7205')
    ) as t(app_key, app_channel)
)
select
    date(c.ad_date) as ad_date,
    date_trunc('month', date(c.ad_date)) as ad_month,
    coalesce(cm.app_channel, 'other') as app_channel, 
    sum(c.spend_usd) as spend_usd 
from dwd.dwd_ads_cost c
left join channel_mapping cm
    on c.app_channel_name = cm.app_key
where cast(c.ad_date as date) > date '2025-01-01'
group by 1, 2, 3 ; 
""", "2. 投放花费")
check_table("mx.ys_mx_ltv_ads_cost")

exec_sql("""
drop table if exists mx.ys_mx_ltv_first_loan_cac;
create table mx.ys_mx_ltv_first_loan_cac as
with first_loan_agg as (
    select
        ltv_month,
        loan_cycle,
        app_channel,
        app_channel_name,
        new_grade_level,
        count(distinct biz_id) as frs_cnt,
        sum(contract_amount) as contract_amount,
        sum(contract_amount) / nullif(count(distinct biz_id), 0) as avg_amount,
        sum(fee * contract_amount) / nullif(sum(contract_amount), 0) as fee,
        sum(fee * contract_amount) as fee_amount,
        sum(should_amt) as should_amt,
        sum(should_amt_t7) as should_amt_t7,
        sum(should_amt_t30) as should_amt_t30,
        sum(contract_t7) as contract_t7,
        sum(contract_t30) as contract_t30,
        sum(fact_t7) as fact_t7,
        sum(fact_t7_coup) as fact_t7_coup,
        sum(fact_t30) as fact_t30,
        sum(fact_t30_coup) as fact_t30_coup,
        sum(fact_cnt_t0) as fact_cnt_t0,
        sum(fact_cnt_t7) as fact_cnt_t7,
        sum(fact_cnt_t30) as fact_cnt_t30,
        sum(fact_cnt_till_now) as fact_cnt_till_now,
        sum(re_zr_cnt_t30) as re_zr_cnt_t30 
    from mx.ys_dl_ltv_first_loan_0511
    group by 1, 2, 3, 4, 5
),
cost as (
    select
        ad_month,
        app_channel, 
        sum(spend_usd) as spend_usd
    from mx.ys_mx_ltv_ads_cost
    group by 1, 2 
),
total_cost as (
    select
        ad_month,
        sum(spend_usd) as total_spend_usd
    from mx.ys_mx_ltv_ads_cost
    group by 1
),
cost_rank as (
    select
        ltv_month,
        app_channel_name,
        new_grade_level,
        loan_cycle,
        row_number() over(partition by ltv_month,app_channel_name order by contract_amount desc) as cost_rnk
    from first_loan_agg 
)
select
    f.ltv_month,
    f.loan_cycle,
    f.app_channel_name,
    f.new_grade_level,
    f.frs_cnt,
    f.contract_amount,
    round(f.avg_amount, 2) as avg_amount,
    round(f.fee, 4) as fee,
    round(f.fee_amount, 2) as fee_amount,
    f.should_amt,
    f.should_amt_t7,
    f.should_amt_t30,
    f.contract_t7,
    f.contract_t30,
    f.fact_t7,
    f.fact_t7_coup,
    f.fact_t30,
    f.fact_t30_coup,
    f.fact_cnt_t0,
    f.fact_cnt_t7,
    f.fact_cnt_t30,
    f.fact_cnt_till_now,
    f.re_zr_cnt_t30,
    cast(0 as double) as pass_rate,
    cr.cost_rnk,
    coalesce(t.total_spend_usd/d.exchange_rate_to_dollar, 0) as total_spend_ngn,
    coalesce(t.total_spend_usd, 0) as total_spend_usd,
    coalesce(c.spend_usd/d.exchange_rate_to_dollar, 0) as spend_ngn,
    coalesce(c.spend_usd, 0) as spend_usd,
    d.exchange_rate_to_dollar
from first_loan_agg f
left join cost_rank cr
    on f.ltv_month = cr.ltv_month
   and f.app_channel_name = cr.app_channel_name
   and f.new_grade_level = cr.new_grade_level
   and f.loan_cycle = cr.loan_cycle
left join cost c
    on f.ltv_month = c.ad_month
   and f.app_channel = c.app_channel 
   and cr.cost_rnk=1
left join total_cost t
    on f.ltv_month = t.ad_month 
    and cr.cost_rnk=1
left join dim.dim_exchange_rate_cost d 
    on date(DATE_PARSE(d.month_id, '%Y%m'))=f.ltv_month
    and d.account_currency = 'MXN';
""", "3. 首贷聚合")
check_table("mx.ys_mx_ltv_first_loan_cac")

exec_sql("""
drop table if exists mx.ys_dl_ltv_double_loan_0511;
create table mx.ys_dl_ltv_double_loan_0511 as
select
    d.ltv_month,
    d.ltv_week,
    date_diff('week', d.ltv_week, date_trunc('week', date(r.release_time))) as wob, 
    d.loan_cycle, 

    d.app_channel,
    d.app_channel_name,
    d.new_grade_level,
    r.camera_id as biz_id,
    cast(r.cust_id as bigint) as mid,
    
    (coalesce(r.haircut_amount, 0) + coalesce(r.should_interest, 0)) / nullif(r.contract_amount, 0) as fee,
    r.contract_amount,
    r.haircut_amount,
    r.should_interest,
    r.should_interest + r.should_capital as should_amt,
    -- r.t7_should_amt_0 as should_amt_t0,
    r.t7_should_amt_4 as should_amt_t7,
    r.t30_should_amt_4 as should_amt_t30,
    r.t0_should_capit_4 as contract_t0,
    r.t7_should_capit_4 as contract_t7,
    r.t30_should_capit_4 as contract_t30,
    -- case when r.t0_should_amt_4>0 then 1 else 0 end as should_cnt_t0,
    case when r.t7_should_amt_4>0 then 1 else 0 end as should_cnt_t7, 
    -- r.t0_fact_amt as fact_t0,
    r.t7_fact_amt as fact_t7,
    r.t7_fact_amt as fact_t7_coup,
    r.t30_fact_amt as fact_t30,
    r.t30_fact_amt as fact_t30_coup,
    -- case when r.t0_fact_amt > 0 then 1 else 0 end as fact_cnt_t0,
    case when r.t7_fact_amt > 0 then 1 else 0 end as fact_cnt_t7,
    case when r.t30_fact_amt > 0 then 1 else 0 end as fact_cnt_t30,
    case when r.now_fact_amt > 0 then 1 else 0 end as fact_cnt_till_now,
    date(t.trade_start_time) as trade_start_date,
    date(t.trade_end_time) as trade_end_date,
    0 as re_zr_cnt_t30
from mx.wxs_application_funnel r
left join mx.ys_dl_ltv_first_loan_0511 d
    on cast(r.cust_id as bigint) = d.mid 
left join ods.s02_loan t
    on r.camera_id = t.camera_id
where r.is_reloan = 'old'
  and r.if_issue = 1
  and d.mid is not null;
""", "4. 复贷 LTV 明细")
check_table("mx.ys_dl_ltv_double_loan_0511")

exec_sql("""

    drop table if exists mx.ys_dl_ltv_double_loan_group;
    create table mx.ys_dl_ltv_double_loan_group as 
    select
        ltv_month as ltv_month_d,
        wob as wob_d,
        app_channel_name as app_channel_name_d,
        loan_cycle as loan_period, 
        new_grade_level as new_grade_level_d,
        count(distinct biz_id) as double_cnt,
        count(distinct mid) as double_mid,
        sum(contract_amount) as contract_amount,
        -- sum(fee * contract_amount) / nullif(sum(contract_amount), 0) as fee,
        sum(fee * contract_amount) as fee_amount,
        sum(contract_amount) / nullif(count(distinct biz_id), 0) as avg_amount,
        sum(should_amt) as  should_amt_t0,      -- 现在双贷表有该字段
        sum(should_amt_t7) as should_amt_t7,
        sum(should_amt_t30) as should_amt_t30,
        sum(contract_t0) as contract_t0,
        sum(contract_t7) as contract_t7,
        sum(contract_t30) as contract_t30,
        0 as should_cnt_t0, 
        sum(should_cnt_t7) as should_cnt_t7, 
        0 as fact_t0,
        sum(fact_t7) as fact_t7,
        sum(fact_t7_coup) as fact_t7_coup,
        sum(fact_t30) as fact_t30,
        sum(fact_t30_coup) as fact_t30_coup,
        0 as fact_cnt_t0,
        sum(fact_cnt_t7) as fact_cnt_t7,
        sum(fact_cnt_t30) as fact_cnt_t30,
        sum(fact_cnt_till_now) as fact_cnt_till_now,
        0 as contract_amount_7d,
        0 as contract_amount_14d,
        0 as should_amt_7d,
        0 as should_amt_14d,
        0 as fact_t30_7d,
        0 as fact_t30_14d,
        0 as double_cnt_7d,
        0 as double_cnt_14d,
        0 as avg_amount_7d,
        0 as avg_amount_14d,
        0 as zr_mid,
        0 as zr_pass_mid,
        0 as zr_cnt,
        0 as zr_pass_cnt,
        0 as qz_mid,
        0 as qz_pass_mid,
        0 as qz_cnt,
        0 as qz_pass_cnt,
        0 as apply_mid,
        0 as apply_pass_mid,
        0 as apply_cnt,
        0 as apply_pass_cnt,
        0 as fact_cnt_t7_for_rzt30,
        0 as fact_cnt_t7_for_rzt7,
        0 as re_zr_cnt_t30,
        0 as re_zr_cnt_t7
    from mx.ys_dl_ltv_double_loan_0511
    group by 1, 2, 3, 4, 5 ;

""", "5. 复贷 RAW 聚合")
check_table("mx.ys_dl_ltv_double_loan_group")

exec_sql("""
drop table if exists mx.ys_dl_ltv_double_loan_draw;
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
all_combinations as (
  select
    g.ltv_month,
    g.app_channel_name,
    g.new_grade_level,
    w.wob
  from frst_loan g
  cross join (
    select wob
    from (select max(wob_d) as max_wob from mx.ys_dl_ltv_double_loan_group)
    cross join unnest(sequence(0, max_wob)) as t(wob)
  ) w
),
  double_combinations as (
    select
      c.ltv_month,
      c.app_channel_name,
      c.new_grade_level,
      c.wob,
      a.*,
      row_number() over (
        partition by
          c.ltv_month,
          c.app_channel_name,
          c.new_grade_level,
          c.wob
      ) as double_rnk --防止首贷多匹配
    from
      all_combinations c
      left join mx.ys_dl_ltv_double_loan_group a on a.ltv_month_d = c.ltv_month
      and a.app_channel_name_d = c.app_channel_name
      and a.new_grade_level_d = c.new_grade_level
      and a.wob_d = c.wob )


select
  c.*,
  b.frs_cnt,
  b.frs_contract_amount,
  row_number() over (
    order by
      c.ltv_month,
      c.wob,
      c.app_channel_name,
      c.loan_period,
      c.new_grade_level
  ) as rnk --限制数量，根据固定顺序加序号
from
  double_combinations c
  left join frst_loan b on c.ltv_month = b.ltv_month
  and c.app_channel_name = b.app_channel_name
  and c.new_grade_level = b.new_grade_level
  and c.double_rnk = 1
where
  date(c.ltv_month) >= date '2023-02-01' --才开始有资产等级
  and c.wob <= 110;

""", "6. WOB 补全")
check_table("mx.ys_dl_ltv_double_loan_draw")

print("\n" + "="*60)
print("最终校验与结果输出")
print("="*60)

all_tables = [
    "mx.ys_dl_ltv_first_loan_0511",
    "mx.ys_mx_ltv_first_loan_cac",
    "mx.ys_dl_ltv_double_loan_0511",
    "mx.ys_dl_ltv_double_loan_group",
    "mx.ys_dl_ltv_double_loan_draw",
    "mx.ys_mx_ltv_ads_cost",
]

print("\n所有表数据汇总:")
table_results = []
for table in all_tables:
    cnt = check_table(table)
    table_results.append({"表名": table, "行数": cnt})

print("\n关键指标校验:")

check_results = {}

result = pq.query("""
select ltv_month, count(*) as first_loan_cnt, sum(contract_amount) as first_contract_amount
from mx.ys_dl_ltv_first_loan_0511
group by 1
order by 1 desc
limit 10
""")
if isinstance(result, pd.DataFrame):
    print("\n首贷量(最近10个月):")
    print(result.to_string())
    check_results["首贷量"] = result

result = pq.query("""
select ltv_month_d, wob_d, app_channel_name_d, new_grade_level_d, double_cnt, contract_amount
from mx.ys_dl_ltv_double_loan_group
limit 10
""")
if isinstance(result, pd.DataFrame):
    print("\n复贷量(前10行):")
    print(result.to_string())
    check_results["复贷量"] = result

result = pq.query("""
select
    ltv_month,
    sum(should_amt_t7) as should_amt_t7,
    sum(should_amt_t7 - fact_t7) / nullif(sum(should_amt_t7), 0) as bad_t7,
    sum(should_amt_t30) as should_amt_t30,
    sum(should_amt_t30 - fact_t30) / nullif(sum(should_amt_t30), 0) as bad_t30
from mx.ys_dl_ltv_first_loan_0511
group by 1
order by 1 desc
limit 12
""")
if isinstance(result, pd.DataFrame):
    print("\nT7_T30坏账率(最近12个月):")
    print(result.to_string())
    check_results["T7_T30坏账率"] = result

output_path = r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥经分\墨西哥LTV完整执行结果_新版.xlsx"
with pd.ExcelWriter(output_path) as writer:
    pd.DataFrame(table_results).to_excel(writer, sheet_name="表数据汇总", index=False)
    for name, df in check_results.items():
        clean_name = name.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace("[", "_").replace("]", "_")
        df.to_excel(writer, sheet_name=clean_name, index=False)

print(f"\n结果已保存到: {output_path}")
print("\n" + "="*60)
print("墨西哥LTV完整执行流程结束")
print("="*60)