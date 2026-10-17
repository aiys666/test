"""检查 first_loan 表状态"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()
print("登录成功!")

print("\n1. 检查 loan 表首贷数据:")
result = pq.query("select count(1) from mx.ys_mx_ltv_base_loan where coalesce(double_loan, 0) = 0 and loan_state in (1, 2, 3)")
print(f"首贷数据量: {result}")

print("\n2. 检查 loan 与 funnel 关联:")
result = pq.query("select count(1) from mx.ys_mx_ltv_base_loan l join mx.ys_mx_ltv_base_funnel f on l.biz_id = f.biz_id where l.double_loan = 0")
print(f"关联数量: {result}")

print("\n3. 检查 loan 与 repay_order 关联:")
result = pq.query("select count(1) from mx.ys_mx_ltv_base_loan l join mx.ys_dl_ltv_repay_order r on l.biz_id = r.camera_id where l.double_loan = 0")
print(f"关联数量: {result}")

print("\n4. 尝试简单的 first_loan 查询:")
result = pq.query("show tables from mx like '%first_loan%'")
print(f"表列表: {result}")

print("\n5. 尝试带条件的 count:")
result = pq.query("select 1 as test")
print(f"测试查询: {result}")