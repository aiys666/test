"""
测试 performance_history 转置后的格式
"""
import pandas as pd

# 模拟数据
data = {
    'month': ['2025-01-01', '2025-02-01'],
    'fl_contract_amt': [100, 200],
    'fl_issue_cnt': [10, 20],
    'rl_contract_amt': [300, 400],
    'rl_issue_cnt': [30, 40],
}
df = pd.DataFrame(data)

# 转置逻辑
month_col = 'month'
metrics = df.columns[1:]
df[month_col] = pd.to_datetime(df[month_col]).dt.strftime('%Y-%m-01')
months_q_sorted = sorted(df[month_col].unique())

transposed_rows_q = []
for metric in metrics:
    # 根据指标前缀判断grant_strategy
    if metric.startswith('rl_'):
        grant_strat = 'OLD'
    else:
        grant_strat = 'NEW'
    
    row = {'grant_strategy': grant_strat, '指标名称': metric}
    for month in months_q_sorted:
        month_data = df[df[month_col] == month]
        if len(month_data) > 0:
            row[month] = month_data[metric].values[0]
        else:
            row[month] = None
    transposed_rows_q.append(row)

df_t = pd.DataFrame(transposed_rows_q)
cols_order = ['grant_strategy', '指标名称'] + months_q_sorted
df_t = df_t[cols_order]

print("performance_history 转置后格式:")
print(df_t)
print("\n验证:")
print(f"rl_contract_amt 的 grant_strategy = {df_t[df_t['指标名称'] == 'rl_contract_amt']['grant_strategy'].values[0]}")
print(f"rl_issue_cnt 的 grant_strategy = {df_t[df_t['指标名称'] == 'rl_issue_cnt']['grant_strategy'].values[0]}")
print(f"fl_contract_amt 的 grant_strategy = {df_t[df_t['指标名称'] == 'fl_contract_amt']['grant_strategy'].values[0]}")
print(f"fl_issue_cnt 的 grant_strategy = {df_t[df_t['指标名称'] == 'fl_issue_cnt']['grant_strategy'].values[0]}")