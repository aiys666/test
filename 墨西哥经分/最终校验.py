"""LTV数据最终校验"""
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
            print(result.to_string())
        else:
            print(f"  结果: {result}")
        return result
    except Exception as e:
        print(f"  错误: {e}")
        return None

print("===== 1. 首贷量校验 =====")
exec_and_check("""select ltv_month, count(*) as first_loan_cnt, sum(contract_amount) as first_contract_amount
from mx.ys_dl_ltv_first_loan_0511
group by 1
order by 1 desc
limit 10""", "最近10个月首贷量:")

print("\n===== 2. 复贷量校验 =====")
exec_and_check("""select release_month, count(*) as double_loan_cnt, sum(contract_amt) as double_contract_amount
from mx.ys_dl_ltv_doulbe_loan_0511
group by 1
order by 1 desc
limit 10""", "最近10个月复贷量:")

print("\n===== 3. 首贷vs贷款宽表校验 =====")
exec_and_check("""select count(*) as loan_first_cnt from mx.ys_mx_ltv_base_loan where double_loan = 0""", "贷款宽表首贷数:")
exec_and_check("""select count(distinct mid) as first_mid_cnt from mx.ys_dl_ltv_first_loan_0511""", "首贷LTV用户数:")

print("\n===== 4. 90天复借率校验 =====")
exec_and_check("""select * from mx.ys_mx_ltv_reloan_90d_check order by issue_month desc""", "90天复借率:")

print("\n===== 5. T7/T30坏账率校验 =====")
exec_and_check("""select
    ltv_month,
    sum(should_amt_t7) as should_amt_t7,
    round(sum(should_amt_t7 - fact_t7) / nullif(sum(should_amt_t7), 0), 4) as bad_t7,
    sum(should_amt_t30) as should_amt_t30,
    round(sum(should_amt_t30 - fact_t30) / nullif(sum(should_amt_t30), 0), 4) as bad_t30
from mx.ys_dl_ltv_first_loan_0511
group by 1
order by 1 desc
limit 12""", "T7/T30坏账率(最近12个月):")

print("\n===== 6. 通过率校验 =====")
exec_and_check("""select
    date_trunc('month', data_date) as month,
    double_loan_new,
    sum(apply_cnt) as apply_cnt,
    sum(if_model_passed) as if_model_passed,
    round(sum(if_model_passed) * 1.0 / nullif(sum(apply_cnt), 0), 4) as model_pass_rate,
    sum(pass_cnt) as pass_cnt,
    sum(if_in_ruleDetermine_data) as if_in_ruleDetermine_data,
    round(sum(pass_cnt) * 1.0 / nullif(sum(if_in_ruleDetermine_data), 0), 4) as post_pass_rate
from mx.ys_mx_ltv_pass_rate_check
group by 1, 2
order by 1 desc, 2
limit 10""", "通过率(最近5个月):")

print("\n===== 7. 首贷CAC校验 =====")
exec_and_check("""select
    ltv_month,
    new_media_source,
    first_loan_mid,
    spend_usd,
    round(cac_usd_per_first_mid, 2) as cac_usd_per_first_mid
from mx.ys_mx_ltv_first_loan_cac
where ltv_month >= date '2026-01-01'
order by ltv_month desc, new_media_source""", "首贷CAC(2026年):")

print("\n===== 8. 复贷WOB校验 =====")
exec_and_check("""select
    ltv_month_d,
    case when wob_d between 0 and 13 then '0-13(90天内)'
         when wob_d between 14 and 26 then '14-26(90-180天)'
         else '>26(180天外)' end as wob_group,
    sum(double_cnt) as double_cnt,
    sum(contract_amount) as contract_amount
from mx.ys_dl_ltv_double_loan_group
group by 1, 2
order by 1 desc, wob_group
limit 15""", "复贷WOB分组:")

print("\n===== 9. 关联完整性校验 =====")
exec_and_check("""select
    count(*) as total,
    sum(case when f.biz_id is not null then 1 else 0 end) as funnel_linked,
    sum(case when r.camera_id is not null then 1 else 0 end) as repay_linked,
    sum(case when f.biz_id is not null and r.camera_id is not null then 1 else 0 end) as both_linked
from mx.ys_dl_ltv_first_loan_0511 l
left join mx.ys_mx_ltv_base_funnel f on l.lid = f.biz_id
left join mx.ys_dl_ltv_repay_order r on l.lid = r.camera_id""", "首贷LTV关联完整性:")

print("\n===== 10. 所有表数据汇总 =====")
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

print("\n表数据汇总:")
results = []
for table in tables:
    try:
        result = pq.query(f"select count(1) as cnt from {table}")
        if isinstance(result, pd.DataFrame):
            cnt = result.iloc[0]['cnt']
            print(f"  {table}: {cnt} 行")
            results.append({"表": table, "行数": cnt})
        else:
            print(f"  {table}: 查询成功")
            results.append({"表": table, "行数": "查询成功"})
    except Exception as e:
        print(f"  {table}: 错误 - {e}")
        results.append({"表": table, "行数": f"错误: {e}"})

df_results = pd.DataFrame(results)
out_path = r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥经分\墨西哥LTV最终检查结果.xlsx"
df_results.to_excel(out_path, index=False)
print(f"\n检查结果已保存到: {out_path}")