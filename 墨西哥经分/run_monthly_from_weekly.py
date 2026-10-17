"""从周表 gm_ltv_model_camera_repurchase 拉数据，Python 聚合到月度 MOB"""
import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

print("🔗 连接墨西哥盘古...")
pq = PrestoQuery()
pq.login()
print("✅ 登录成功\n")

# 直接查已有的周表，按月聚合
sql = """
SELECT 
    dt_week
    ,app_channel
    ,product_name
    ,media_source
    ,fu_week
    ,shou_cnt
    ,shou_contract_amt
    ,camera_cnt  AS fu_camera_cnt
    ,fu_camera_amt
FROM mx.gm_ltv_model_camera_repurchase
"""

print("📊 查询周表数据...")
df = pq.query(sql, wait_sec=1)

if not isinstance(df, pd.DataFrame):
    print(f"❌ {df}")
    raise SystemExit(1)

print(f"✅ 原始数据：{df.shape[0]:,} 行\n")

# ── 转换周→月 ──
df["dt_week"] = pd.to_datetime(df["dt_week"])
df["fu_week"] = pd.to_datetime(df["fu_week"])

df["shou_month"] = df["dt_week"].dt.to_period("M").dt.to_timestamp()
df["fu_month"]   = df["fu_week"].dt.to_period("M").dt.to_timestamp()

# MOB = 复贷月 - 首贷月（精确月差）
df["mob"] = (
    (df["fu_month"].dt.year - df["shou_month"].dt.year) * 12 
    + (df["fu_month"].dt.month - df["shou_month"].dt.month)
)

# 数值列转 float
for col in ["shou_cnt", "shou_contract_amt", "fu_camera_cnt", "fu_camera_amt"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# mob/fu_month 为 NaN 的行 → mob=0, fu_month=shou_month（无复贷）
df["mob"] = df["mob"].fillna(0).astype(int)
df["fu_month"] = df["fu_month"].fillna(df["shou_month"])

# ── 月度聚合 ──
monthly = df.groupby([
    "shou_month", "mob", "fu_month", "app_channel", "product_name", "media_source"
], dropna=False).agg(
    shou_cnt=("shou_cnt", "sum"),
    shou_contract_amt=("shou_contract_amt", "sum"),
    fu_camera_cnt=("fu_camera_cnt", "sum"),
    fu_camera_amt=("fu_camera_amt", "sum"),
).reset_index()

# MOB 转 int
monthly["mob"] = monthly["mob"].astype(int)

# 排序
monthly = monthly.sort_values([
    "shou_month", "mob", "app_channel", "product_name", "media_source"
]).reset_index(drop=True)

# ── 输出 ──
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   f"墨西哥月度MOB_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
monthly.to_excel(out, index=False)
print(f"💾 已保存：{out}")
print(f"📏 {monthly.shape[0]:,} 行 × {monthly.shape[1]} 列")
try:
    print(f"   首贷月：{monthly['shou_month'].min().strftime('%Y-%m')} ~ {monthly['shou_month'].max().strftime('%Y-%m')}")
except:
    pass
print(f"   MOB：{int(monthly['mob'].min())} ~ {int(monthly['mob'].max())}")
print(f"   总首贷笔数：{monthly['shou_cnt'].sum():,.0f}")
print(f"   总复贷笔数：{monthly['fu_camera_cnt'].sum():,.0f}")
print(f"\n📋 前10行：")
print(monthly.head(10)[["shou_month","mob","fu_month","product_name","media_source","shou_cnt","fu_camera_cnt","shou_contract_amt","fu_camera_amt"]].to_string())
