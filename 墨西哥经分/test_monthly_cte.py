"""先跑小范围验证CTE逻辑，再跑全量"""
import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

SQL_FILE = r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥经分\ltv_monthly_cte.sql"

with open(SQL_FILE, "r", encoding="utf-8") as f:
    sql = f.read()

# 加 LIMIT 验证（ORDER BY 在前，LIMIT 在后）
sql_test = sql + "\nLIMIT 1000"

print("🔗 连接墨西哥盘古...")
pq = PrestoQuery()
pq.login()
print("✅ 登录成功\n")

print("🧪 测试查询（LIMIT 1000）...")
df = pq.query(sql_test, wait_sec=1)

if isinstance(df, pd.DataFrame):
    print(f"\n✅ 测试成功：{df.shape[0]:,} 行 × {df.shape[1]} 列")
    print(f"\n📋 列名：{df.columns.tolist()}")
    print(f"\n📋 前5行：")
    print(df.head().to_string())
else:
    print(f"❌ 测试失败：{df}")
