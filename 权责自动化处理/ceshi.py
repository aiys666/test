from indonesia_presto import PrestoQuery
pq = PrestoQuery()
pq.login_process()
df = pq.submit_query("""SELECT
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
    ORDER BY month ASC;""")