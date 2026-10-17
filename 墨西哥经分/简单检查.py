"""简单检查表数据"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()
print("登录成功!")

tables = ["mx.ys_dl_ltv_repay_order", "mx.ys_dl_ltv_first_loan_0511"]

for table in tables:
    print(f"\n检查表: {table}")
    try:
        result = pq.query(f"select count(1) from {table}")
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  错误: {e}")
        
    try:
        result = pq.query(f"select * from {table} limit 1")
        print(f"  首行: {result}")
    except Exception as e:
        print(f"  首行错误: {e}")