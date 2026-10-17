"""检查 first_loan 表结构和数据"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()
print("登录成功!")

print("\n1. 查看 first_loan 表结构:")
result = pq.query("desc mx.ys_dl_ltv_first_loan_0511")
print(f"表结构: {result}")

print("\n2. 尝试不同方式查询 first_loan:")
try:
    result = pq.query("select * from mx.ys_dl_ltv_first_loan_0511 where rownum <= 1")
    print(f"rownum查询: {result}")
except Exception as e:
    print(f"rownum错误: {e}")
    
try:
    result = pq.query("select * from mx.ys_dl_ltv_first_loan_0511 limit 1")
    print(f"limit查询: {result}")
except Exception as e:
    print(f"limit错误: {e}")

print("\n3. 尝试查看表创建语句:")
result = pq.query("show create table mx.ys_dl_ltv_first_loan_0511")
print(f"创建语句: {result}")

print("\n4. 尝试创建简化版本的 first_loan:")
sql = """drop table if exists mx.ys_dl_ltv_first_loan_test;
create table mx.ys_dl_ltv_first_loan_test as
select
    l.biz_id,
    l.mid,
    l.contract_amount
from mx.ys_mx_ltv_base_loan l
where l.double_loan = 0
limit 100"""

result = pq.query(sql)
print(f"创建测试表结果: {result}")

try:
    result = pq.query("select count(1) from mx.ys_dl_ltv_first_loan_test")
    print(f"测试表行数: {result}")
except Exception as e:
    print(f"测试表查询错误: {e}")