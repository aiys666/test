"""墨西哥复贷与留存综合分析 - 支持30/60/90/180天"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功!")

def exec_sql(sql, desc):
    print(f"\n{'='*70}")
    print(f"【{desc}】")
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
print("墨西哥复贷与留存综合分析")
print("="*70)

exec_sql("""
drop table if exists mx.ys_dl_ltv_reloan_retention;
create table mx.ys_dl_ltv_reloan_retention as
with first_loans as (
    select
        date_trunc('month', date(t.release_time)) as issue_month,
        t.customer_id as mid,
        t.release_time as first_release_time,
        t.contract_amount as first_contract_amount
    from ods.s02_loan t
    inner join mx.risk_double_loan_tag rt
        on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
    where rt.double_loan = 0
      and t.release_time >= date '2025-06-01'
      and t.state in (1, 2, 3)
),
reloans as (
    select
        t.customer_id as mid,
        cast(t.camera_id as varchar) as biz_id,
        t.release_time as reloan_release_time,
        t.contract_amount as reloan_contract_amount
    from ods.s02_loan t
    inner join mx.risk_double_loan_tag rt
        on cast(t.camera_id as bigint) = cast(rt.biz_id as bigint)
    where rt.double_loan = 1