"""墨西哥LTV数据校验清单 - 用于手动验证"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功!")

def exec_sql(sql, desc):
    print(f"\n{'='*70}")
    print(f"【校验指标】{desc}")
    print(f"{'='*70}")
    try:
        result = pq.query(sql)
        if isinstance(result, pd.DataFrame):
            print(f"查询完成，返回 {len(result)} 行")
            print(result.to_string())
            return result
        else:
            print(f"执行完成: {result}")
            return result
    except Exception as e:
        print(f"错误: {e}")
        return None

print("="*70)
print("墨西哥LTV数据校验清单")
print("="*70)

results = {}

print("\n" + "*"*70)
print("【第一部分】首贷数据校验")
print("*"*70)

results["1.1_首贷总量"] = exec_sql("""
select '当前代码' as source, count(*) as total_cnt, sum(contract_amount) as total_amount
from mx.ys_dl_ltv_first_loan_0511
union all
select 'ods.s02_loan' as source, count(*) as total_cnt, sum(t.contract_amount) as total_amount
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
where rt.double_loan = 0 and t.state in (1,2,3)
""", "1.1 首贷总量对比")

results["1.2_首贷按月"] = exec_sql("""
select '当前代码' as source, ltv_month, count(*) as cnt, sum(contract_amount) as amount
from mx.ys_dl_ltv_first_loan_0511
group by 1, 2
order by 2 desc
limit 12
""", "1.2 首贷放款规模(按月)")

results["1.3_首贷按月_参考"] = exec_sql("""
select 'ods.s02_loan' as source, date_trunc('month', date(t.release_time)) as ltv_month, 
       count(*) as cnt, sum(t.contract_amount) as amount
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
where rt.double_loan = 0 and t.state in (1,2,3)
group by 1, 2
order by 2 desc
limit 12
""", "1.3 首贷放款规模(按月)_参考数据源")

results["1.4_首贷按渠道"] = exec_sql("""
select '当前代码' as source, ltv_month, app_channel_name, 
       sum(contract_amount) as amount, count(distinct biz_id) as cnt
from mx.ys_dl_ltv_first_loan_0511
group by 1, 2, 3
order by 2 desc, 4 desc
limit 20
""", "1.4 首贷按渠道分布")

results["1.5_首贷按渠道_参考"] = exec_sql("""
select 'ods.s02_loan' as source, date_trunc('month', date(t.release_time)) as ltv_month, 
       t.app_channel, sum(t.contract_amount) as amount, count(*) as cnt
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
where rt.double_loan = 0 and t.state in (1,2,3)
group by 1, 2, 3
order by 2 desc, 4 desc
limit 20
""", "1.5 首贷按渠道分布_参考数据源")

results["1.6_首贷按期限"] = exec_sql("""
select '当前代码' as source, ltv_month, 
       sum(case when loan_cycle = 7 then contract_amount end) as amount_7d,
       sum(case when loan_cycle = 14 then contract_amount end) as amount_14d,
       count(case when loan_cycle = 7 then biz_id end) as cnt_7d,
       count(case when loan_cycle = 14 then biz_id end) as cnt_14d
from mx.ys_dl_ltv_first_loan_0511
group by 1, 2
order by 2 desc
limit 10
""", "1.6 首贷按期限分布")

results["1.7_首贷按期限_参考"] = exec_sql("""
select 'ods.s02_loan' as source, date_trunc('month', date(t.release_time)) as ltv_month, 
       sum(case when t.loan_cycle = 7 then t.contract_amount end) as amount_7d,
       sum(case when t.loan_cycle = 14 then t.contract_amount end) as amount_14d,
       count(case when t.loan_cycle = 7 then t.camera_id end) as cnt_7d,
       count(case when t.loan_cycle = 14 then t.camera_id end) as cnt_14d
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
where rt.double_loan = 0 and t.state in (1,2,3)
group by 1, 2
order by 2 desc
limit 10
""", "1.7 首贷按期限分布_参考数据源")

results["1.8_首贷坏账率"] = exec_sql("""
select ltv_month,
       sum(should_amt_t7) as should_amt_t7,
       sum(should_amt_t7 - fact_t7) / nullif(sum(should_amt_t7), 0) as bad_t7,
       sum(should_amt_t30) as should_amt_t30,
       sum(should_amt_t30 - fact_t30) / nullif(sum(should_amt_t30), 0) as bad_t30
from mx.ys_dl_ltv_first_loan_0511
group by 1
order by 1 desc
limit 12
""", "1.8 首贷T7/T30坏账率")

print("\n" + "*"*70)
print("【第二部分】复贷数据校验")
print("*"*70)

results["2.1_复贷总量"] = exec_sql("""
select '当前代码' as source, count(*) as total_cnt, sum(contract_amount) as total_amount
from mx.ys_dl_ltv_double_loan_0511
union all
select 'ods.s02_loan' as source, count(*) as total_cnt, sum(t.contract_amount) as total_amount
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
where rt.double_loan = 1 and t.state in (1,2,3)
""", "2.1 复贷总量对比")

results["2.2_复贷按月"] = exec_sql("""
select '当前代码' as source, ltv_month, count(*) as cnt, sum(contract_amount) as amount
from mx.ys_dl_ltv_double_loan_0511
group by 1, 2
order by 2 desc
limit 12
""", "2.2 复贷放款规模(按月)")

results["2.3_复贷按月_参考"] = exec_sql("""
select 'ods.s02_loan' as source, date_trunc('month', date(t.release_time)) as ltv_month, 
       count(*) as cnt, sum(t.contract_amount) as amount
from ods.s02_loan t
inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
where rt.double_loan = 1 and t.state in (1,2,3)
group by 1, 2
order by 2 desc
limit 12
""", "2.3 复贷放款规模(按月)_参考数据源")

results["2.4_复贷按渠道"] = exec_sql("""
select '当前代码' as source, ltv_month, app_channel_name, 
       sum(contract_amount) as amount, count(*) as cnt
from mx.ys_dl_ltv_double_loan_0511
group by 1, 2, 3
order by 2 desc, 4 desc
limit 20
""", "2.4 复贷按渠道分布")

results["2.5_复贷按期限"] = exec_sql("""
select '当前代码' as source, ltv_month, 
       sum(case when loan_cycle = 7 then contract_amount end) as amount_7d,
       sum(case when loan_cycle = 14 then contract_amount end) as amount_14d,
       count(case when loan_cycle = 7 then biz_id end) as cnt_7d,
       count(case when loan_cycle = 14 then biz_id end) as cnt_14d
from mx.ys_dl_ltv_double_loan_0511
group by 1, 2
order by 2 desc
limit 10
""", "2.5 复贷按期限分布")

print("\n" + "*"*70)
print("【第三部分】首贷与复贷关系校验")
print("*"*70)

results["3.1_WOB复贷金额"] = exec_sql("""
select ltv_month, wob, sum(contract_amount) as double_contract_amount
from mx.ys_dl_ltv_double_loan_group
where ltv_month >= date '2025-06-01'
group by 1, 2
order by 2, 3
limit 30
""", "3.1 首贷放款月对应的WOB复贷金额(2025年6月后)")

results["3.2_WK_DIFF复贷金额_参考"] = exec_sql("""
select a.dt_week, date_diff('week', a.dt_week, b.dt_week) as wk_diff,
       sum(b.contract_amount) as fu_contract_amt
from (
    select distinct date(t.release_time) dt, 
           date_add('day',-day_of_week(date(t.release_time))+1,date(t.release_time)) as dt_week,
           t.customer_id, t.contract_amount
    from ods.s02_loan t
    inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
    where rt.double_loan = 0 and t.state in (1,2,3)
) a
left join (
    select distinct date(t.release_time) dt, 
           date_add('day',-day_of_week(date(t.release_time))+1,date(t.release_time)) as dt_week,
           t.customer_id, t.contract_amount
    from ods.s02_loan t
    inner join mx.risk_double_loan_tag rt on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
    where rt.double_loan = 1 and t.state in (1,2,3)
) b on a.customer_id = b.customer_id
where a.dt_week >= date '2025-06-01'
  and date_diff('week', a.dt_week, b.dt_week) >= 0
group by 1, 2
order by 1, 2
limit 30
""", "3.2 首贷放款周对应的WK_DIFF复贷金额(参考代码)")

results["3.3_首贷复贷按月对比"] = exec_sql("""
select f.ltv_month,
       sum(f.contract_amount) as first_amount,
       count(distinct f.biz_id) as first_cnt,
       sum(d.contract_amount) as double_amount,
       count(distinct d.biz_id) as double_cnt,
       sum(d.contract_amount) / nullif(sum(f.contract_amount), 0) as double_ratio
from mx.ys_dl_ltv_first_loan_0511 f
left join mx.ys_dl_ltv_double_loan_0511 d on f.ltv_month = d.ltv_month
group by 1
order by 1 desc
limit 10
""", "3.3 首贷与复贷放款金额对比(按月)")

results["3.4_WOB分布"] = exec_sql("""
select wob, count(*) as cnt, sum(contract_amount) as total_amount
from mx.ys_dl_ltv_double_loan_group
group by 1
order by 1
limit 15
""", "3.4 WOB分布")

print("\n" + "*"*70)
print("【第四部分】数据源明细对比")
print("*"*70)

results["4.1_数据源差异"] = exec_sql("""
select '差异数据' as source, 
       a.ltv_month,
       count(distinct a.biz_id) as first_cnt,
       count(distinct d.biz_id) as double_cnt,
       count(distinct d.biz_id) * 1.0 / nullif(count(distinct a.biz_id), 0) as reloan_rate
from mx.ys_dl_ltv_first_loan_0511 a
left join mx.ys_dl_ltv_double_loan_0511 d on a.mid = d.mid
group by 1, 2
order by 2 desc
limit 10
""", "4.1 首贷用户复贷率(按月)")

results["4.2_首贷聚合表"] = exec_sql("""
select ltv_month, app_channel_name, new_grade_level,
       frs_cnt, contract_amount, avg_amount, fee,
       should_amt_t7, should_amt_t30,
       fact_t7, fact_t30,
       bad_t7, bad_t30
from mx.ys_mx_ltv_first_loan_cac
order by ltv_month desc, contract_amount desc
limit 20
""", "4.2 首贷聚合表关键指标")

results["4.3_复贷聚合表"] = exec_sql("""
select ltv_month_d, wob_d, app_channel_name_d,
       double_cnt, contract_amount, avg_amount,
       should_amt_t7, should_amt_t30,
       fact_t7, fact_t30
from mx.ys_dl_ltv_double_loan_group
order by ltv_month_d desc, wob_d
limit 20
""", "4.3 复贷聚合表关键指标")

output_path = r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥经分\墨西哥LTV校验结果.xlsx"
with pd.ExcelWriter(output_path) as writer:
    for name, df in results.items():
        if isinstance(df, pd.DataFrame):
            clean_name = name.replace("/", "_").replace("\\", "_").replace(":", "_")
            df.to_excel(writer, sheet_name=clean_name, index=False)

print(f"\n{'='*70}")
print(f"校验结果已保存到: {output_path}")
print("墨西哥LTV数据校验完成")
print("="*70)