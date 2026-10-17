"""
测试小数保留6位功能
"""
import pandas as pd

def round_numeric_cols(df, decimals=6):
    """将DataFrame中所有数值列的小数保留指定位数"""
    for col in df.columns:
        if df[col].dtype in ['float64', 'float32', 'float']:
            df[col] = df[col].round(decimals)
    return df

# 模拟数据（带有很多小数位）
data = {
    'grant_strategy': ['NEW', 'OLD'],
    '指标名称': ['bad_rate', 'TR'],
    '2025-01-01': [0.27569300000000005, 0.0021120000000000005],
    '2025-02-01': [0.11295500000000002, -0.006113000000000001],
}
df = pd.DataFrame(data)

print("原始数据（很多小数位）:")
print(df)
print("\n数据类型:")
print(df.dtypes)

# 保留6位小数
df_round = round_numeric_cols(df.copy())

print("\n保留6位小数后:")
print(df_round)
print("\n验证数值:")
print(f"bad_rate (2025-01-01): {df_round.loc[0, '2025-01-01']}")
print(f"TR (2025-01-01): {df_round.loc[1, '2025-01-01']}")
print(f"bad_rate (2025-02-01): {df_round.loc[0, '2025-02-01']}")
print(f"TR (2025-02-01): {df_round.loc[1, '2025-02-01']}")