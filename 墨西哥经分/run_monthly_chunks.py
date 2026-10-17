"""分段跑月度MOB，按年切分避免结果过期"""
import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

SQL_FILE = r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥经分\ltv_monthly_cte.sql"

with open(SQL_FILE, "r", encoding="utf-8") as f:
    sql = f.read()

# 在第一个 CTE 的 WHERE 里追加日期过滤
# 原条件：WHERE date(release_time) >= date('2023-03-01') AND state IN (1,2,3)
BASE_WHERE = "WHERE date(release_time) >= date('{start}') AND date(release_time) < date('{end}') AND state IN (1,2,3)"

print("🔗 连接墨西哥盘古...")
pq = PrestoQuery()
pq.login()
print("✅ 登录成功\n")

# 按年分段
years = [
    ("2023-03-01", "2024-01-01"),
    ("2024-01-01", "2025-01-01"),
    ("2025-01-01", "2026-01-01"),
    ("2026-01-01", "2026-08-01"),
]

all_dfs = []
for start, end in years:
    yr_filter = BASE_WHERE.format(start=start, end=end)

    # 替换两处 WHERE（shou_detail 和 fu_detail CTE）
    chunk_sql = sql.replace(
        "WHERE date(release_time) >= date('2023-03-01') AND state IN (1,2,3)",
        yr_filter
    )

    print(f"📅 {start} ~ {end} ...", end=" ", flush=True)
    df = pq.query(chunk_sql, wait_sec=0.5)

    if isinstance(df, pd.DataFrame):
        print(f"✅ {df.shape[0]:,} 行")
        all_dfs.append(df)
    else:
        print(f"❌ {df}")
        break

if all_dfs:
    result = pd.concat(all_dfs, ignore_index=True)
    result = result.drop_duplicates().sort_values(["shou_month", "mob", "app_channel", "product_name", "media_source"]).reset_index(drop=True)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       f"墨西哥月度MOB_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    result.to_excel(out, index=False)
    print(f"\n💾 已保存：{out}")
    print(f"📏 {result.shape[0]:,} 行 × {result.shape[1]} 列")
    print(f"   首贷月：{result['shou_month'].min()} ~ {result['shou_month'].max()}")
    print(f"   MOB：{result['mob'].min()} ~ {result['mob'].max()}")
    print(f"   总首贷笔数：{result['shou_cnt'].sum():,.0f}")
    print(f"   总复贷笔数：{result['fu_camera_cnt'].sum():,.0f}")
else:
    print("\n❌ 所有分段均失败")
