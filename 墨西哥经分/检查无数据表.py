"""检查剩余无数据表的问题"""
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

print("===== 检查复贷准入表(zr)问题 =====")
exec_and_check("select count(*) as cnt from mx.ys_dl_ltv_zr", "复贷准入表行数:")

exec_and_check("""
select count(*) as cnt from mx.ys_mx_ltv_base_funnel f
left join mx.ys_mx_ltv_base_loan p
    on f.mid = p.mid
   and p.loan_rank = coalesce(f.reloan_num - 1, f.double_loan, 1)
where (f.is_reloan = 'old' or f.double_loan > 0 or f.reloan_num > 1)
  and f.biz_id is not null
""", "复贷准入SQL直接查询:")

exec_and_check("""
select f.reloan_num, f.double_loan, coalesce(f.reloan_num - 1, f.double_loan, 1) as deal_num,
       p.loan_rank, p.trade_end_date, p.finish_time
from mx.ys_mx_ltv_base_funnel f
left join mx.ys_mx_ltv_base_loan p
    on f.mid = p.mid
   and p.loan_rank = coalesce(f.reloan_num - 1, f.double_loan, 1)
where (f.is_reloan = 'old' or f.double_loan > 0 or f.reloan_num > 1)
  and f.biz_id is not null
limit 10
""", "复贷准入数据预览:")

print("\n===== 检查首贷LTV明细表(first_loan)问题 =====")
exec_and_check("select count(*) as cnt from mx.ys_dl_ltv_first_loan_0511", "首贷LTV明细表行数:")

exec_and_check("""
select count(*) as cnt from mx.ys_mx_ltv_base_loan l
where coalesce(l.double_loan, 0) = 0
  and l.loan_state in (1, 2, 3)
""", "首贷loan数据量:")

exec_and_check("""
select count(*) as cnt from mx.ys_mx_ltv_base_loan l
left join mx.ys_mx_ltv_base_funnel f
    on l.biz_id = f.biz_id
where coalesce(l.double_loan, 0) = 0
  and l.loan_state in (1, 2, 3)
""", "首贷loan关联funnel:")

exec_and_check("""
select count(*) as cnt from mx.ys_mx_ltv_base_loan l
left join mx.ys_dl_ltv_repay_order r
    on l.biz_id = r.camera_id
where coalesce(l.double_loan, 0) = 0
  and l.loan_state in (1, 2, 3)
""", "首贷loan关联repay_order:")

exec_and_check("""
select l.biz_id as loan_biz_id, l.mid, f.biz_id as funnel_biz_id, f.mid as funnel_mid, r.camera_id as repay_camera_id
from mx.ys_mx_ltv_base_loan l
left join mx.ys_mx_ltv_base_funnel f
    on l.biz_id = f.biz_id
left join mx.ys_dl_ltv_repay_order r
    on l.biz_id = r.camera_id
where coalesce(l.double_loan, 0) = 0
  and l.loan_state in (1, 2, 3)
limit 10
""", "关联数据预览:")

exec_and_check("""
select l.biz_id, length(l.biz_id) as loan_len, r.camera_id, length(r.camera_id) as repay_len
from mx.ys_mx_ltv_base_loan l
left join mx.ys_dl_ltv_repay_order r
    on l.biz_id = cast(r.camera_id as varchar)
where coalesce(l.double_loan, 0) = 0
  and l.loan_state in (1, 2, 3)
limit 5
""", "biz_id格式对比:")