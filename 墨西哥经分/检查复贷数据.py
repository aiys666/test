"""检查复贷相关数据"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功!")

print("\n===== 检查 funnel 表中的复贷数据 =====")
sqls = [
    {"描述": "总数据量", "sql": "select count(*) as cnt from mx.ys_mx_ltv_base_funnel"},
    {"描述": "is_reloan 分布", "sql": "select is_reloan, count(*) as cnt from mx.ys_mx_ltv_base_funnel group by 1"},
    {"描述": "double_loan 分布", "sql": "select double_loan, count(*) as cnt from mx.ys_mx_ltv_base_funnel group by 1"},
    {"描述": "reloan_num 分布", "sql": "select reloan_num, count(*) as cnt from mx.ys_mx_ltv_base_funnel group by 1 having count(*) > 0"},
    {"描述": "复贷条件匹配数", "sql": "select count(*) as cnt from mx.ys_mx_ltv_base_funnel where (is_reloan = 'old' or double_loan > 0 or reloan_num > 1)"},
    {"描述": "复贷条件 + biz_id is not null", "sql": "select count(*) as cnt from mx.ys_mx_ltv_base_funnel where (is_reloan = 'old' or double_loan > 0 or reloan_num > 1) and biz_id is not null"},
    {"描述": "apply_amount > 0 的数据", "sql": "select count(*) as cnt from mx.ys_mx_ltv_base_funnel where biz_id is not null and coalesce(apply_amount, 0) > 0"},
]

for q in sqls:
    print(f"\n{q['描述']}:")
    try:
        result = pq.query(q['sql'])
        if isinstance(result, pd.DataFrame):
            print(result.to_string())
    except Exception as e:
        print(f"  查询失败: {e}")

print("\n===== 检查 repay_order 聚合逻辑 =====")
sqls2 = [
    {"描述": "repay 表 camera_id 非空数", "sql": "select count(*) as cnt from mx.ys_dl_ltv_repay where camera_id is not null"},
    {"描述": "repay 表 camera_id 去重数", "sql": "select count(distinct camera_id) as cnt from mx.ys_dl_ltv_repay"},
    {"描述": "repay_order 表数据量", "sql": "select count(*) as cnt from mx.ys_dl_ltv_repay_order"},
    {"描述": "repay 表前3行", "sql": "select camera_id, rid from mx.ys_dl_ltv_repay limit 3"},
]

for q in sqls2:
    print(f"\n{q['描述']}:")
    try:
        result = pq.query(q['sql'])
        if isinstance(result, pd.DataFrame):
            print(result.to_string())
    except Exception as e:
        print(f"  查询失败: {e}")

print("\n===== 检查 loan 表与 funnel 表关联 =====")
sqls3 = [
    {"描述": "loan 表首贷数据量", "sql": "select count(*) as cnt from mx.ys_mx_ltv_base_loan where coalesce(double_loan, 0) = 0 and loan_state in (1, 2, 3)"},
    {"描述": "loan biz_id 格式", "sql": "select biz_id, length(biz_id) as len from mx.ys_mx_ltv_base_loan limit 3"},
    {"描述": "funnel biz_id 格式", "sql": "select biz_id, length(biz_id) as len from mx.ys_mx_ltv_base_funnel limit 3"},
    {"描述": "关联匹配数", "sql": "select count(*) as cnt from mx.ys_mx_ltv_base_loan l left join mx.ys_mx_ltv_base_funnel f on l.biz_id = f.biz_id where l.double_loan = 0"},
]

for q in sqls3:
    print(f"\n{q['描述']}:")
    try:
        result = pq.query(q['sql'])
        if isinstance(result, pd.DataFrame):
            print(result.to_string())
    except Exception as e:
        print(f"  查询失败: {e}")