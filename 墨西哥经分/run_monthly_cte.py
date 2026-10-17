"""跑 ltv_monthly_cte.sql，导出 Excel"""
import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

SQL_FILE = r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥经分\ltv_monthly_cte.sql"

with open(SQL_FILE, "r", encoding="utf-8") as f:
    sql = f.read()

print("🔗 连接墨西哥盘古...")
pq = PrestoQuery()
pq.login()
print("✅ 登录成功\n")

print("📊 执行月度MOB查询（CTE版，不建表）...")
df = pq.query(sql, wait_sec=0.5)

if isinstance(df, pd.DataFrame):
    print(f"\n✅ 查询完成：{df.shape[0]:,} 行 × {df.shape[1]} 列")
    print(f"📊 内存：{df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       f"墨西哥月度MOB_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    df.to_excel(out, index=False)
    print(f"💾 已保存：{out}")

    print(f"\n📋 前5行预览：")
    print(df.head().to_string())
    print(f"\n📊 统计：")
    print(f"  首贷月范围：{df['shou_month'].min()} ~ {df['shou_month'].max()}")
    print(f"  MOB范围：{df['mob'].min()} ~ {df['mob'].max()}")
    print(f"  总首贷笔数：{df['shou_cnt'].sum():,.0f}")
    print(f"  总复贷笔数：{df['fu_camera_cnt'].sum():,.0f}")
else:
    print(f"❌ 查询失败：{df}")
