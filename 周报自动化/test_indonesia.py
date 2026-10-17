import sys
import pandas as pd
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from indonesia_presto import PrestoQuery

sql = """SELECT
    month,
    SUM(fl_contract_amt) AS fl_contract_amt,
    SUM(fl_issue_cnt) AS fl_issue_cnt,
    AVG(fl_avg_amt) AS fl_avg_amt,
    AVG(fl_pass_rate) AS fl_pass_rate,
    AVG(fl_loan_cycle) AS fl_loan_cycle,
    SUM(daily_avg_spend) AS daily_avg_spend,
    AVG(cps) AS cps,
    SUM(rl_contract_amt) AS rl_contract_amt,
    SUM(rl_issue_cnt) AS rl_issue_cnt,
    AVG(rl_avg_amt) AS rl_avg_amt,
    SUM(rl_pass_rate) AS rl_pass_rate,
    AVG(rl_loan_cycle) AS rl_loan_cycle
FROM ind.ba_act_targets_process_m
WHERE ba_type = 'act'
AND month >= '2025-01'
GROUP BY month
ORDER BY month ASC"""

pq = PrestoQuery()
pq.login_process()
result = pq.submit_query(sql)

if isinstance(result, tuple):
    print(f"SQL错误: {result}")
elif isinstance(result, pd.DataFrame) or result is None:
    import pandas as pd
    if isinstance(result, pd.DataFrame):
        print(f"成功，{len(result)} 行")
        print(result.head())
    else:
        print(f"结果: None")
else:
    print(f"结果: {result}")

# Also test a simple query to verify
print("\n--- 简单查询验证 ---")
pq2 = PrestoQuery()
pq2.login_process()
r2 = pq2.submit_query("select 1 as one")
print(f"select 1: {r2}")
