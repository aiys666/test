  




 
DROP TABLE IF EXISTS ind.ba_kpi_targets_m;
 
CREATE TABLE ind.ba_kpi_targets_m (
    month VARCHAR(10),
    ba_type VARCHAR(10),   
    daily_avg_spend DECIMAL(30,10),
    cps DECIMAL(30,10),
    fl_confirm_1_2_rate DECIMAL(30,10),
    fl_issue_1_4_cnt DECIMAL(30,10),
    fl_1_4_cps_rate DECIMAL(30,10),
    fl_avg_amt DECIMAL(30,10),
    fl_issue_cnt DECIMAL(30,10),
    fl_pass_rate DECIMAL(30,10),
    fl_contract_amt DECIMAL(30,10),
    fl_loan_cycle DECIMAL(30,10),
    fl_fee_rate DECIMAL(30,10),
    fl_bad_rate DECIMAL(30,10),
    fl_cust_cost DECIMAL(30,10),
    rl_avg_amt DECIMAL(30,10),
    rl_issue_cnt DECIMAL(30,10),
    rl_pass_rate DECIMAL(30,10),
    rl_contract_amt DECIMAL(30,10),
    rl_loan_cycle DECIMAL(30,10),
    rl_fee_rate DECIMAL(30,10),
    rl_bad_rate DECIMAL(30,10),
    total_amt DECIMAL(30,10),
    rl_amt_ratio DECIMAL(30,10),
    lend_biz_ratio DECIMAL(30,10),
    lend_biz_amt DECIMAL(30,10),
    total_fee_rate DECIMAL(30,10),
    total_bad_rate DECIMAL(30,10),
    total_cust_cost DECIMAL(30,10),
    exchange_rate DECIMAL(30,10)
);
 
 
INSERT INTO ind.ba_kpi_targets_m (month,ba_type, daily_avg_spend, cps, fl_confirm_1_2_rate, fl_issue_1_4_cnt, fl_1_4_cps_rate, fl_avg_amt, fl_issue_cnt, fl_pass_rate, fl_contract_amt, fl_loan_cycle, fl_fee_rate, fl_bad_rate, fl_cust_cost, rl_avg_amt, rl_issue_cnt, rl_pass_rate, rl_contract_amt, rl_loan_cycle, rl_fee_rate, rl_bad_rate, total_amt, rl_amt_ratio, lend_biz_ratio, lend_biz_amt, total_fee_rate, total_bad_rate, total_cust_cost, exchange_rate) VALUES
('2025-01-01','kpi', 56615.0000, 28.3000, 0.0000, 0.0000, 0.0000, 51.1000, 62091.0000, 0.1350, 3175595.0000, 107.0000, 0.2560, -0.2630, -0.5530, 108.0000, 70865.0000, 0.4810, 7662436.0000, 139.0000, 0.3400, -0.2400, 10838032.0000, 0.7070, 0.1010, 1098534.0000, 0.3161, -0.2470, -0.1620, 16247.0000),
('2025-02-01','kpi', 71916.0000, 32.7000, 0.0000, 0.0000, 0.0000, 51.5000, 61602.0000, 0.1340, 3174407.0000, 85.0000, 0.2120, -0.2480, -0.6340, 105.0000, 67450.0000, 0.4420, 7103233.0000, 139.0000, 0.3440, -0.2310, 10277640.0000, 0.6910, 0.3500, 3600000.0000, 0.3043, -0.2360, -0.1960, 16335.0000),
('2025-03-01','kpi', 88000.0000, 35.7000, 0.0000, 0.0000, 0.0000, 52.2000, 76319.0000, 0.1340, 3981460.0000, 94.0000, 0.2270, -0.2630, -0.6850, 98.0000, 80752.0000, 0.4960, 7951691.0000, 141.0000, 0.3420, -0.2400, 11933151.0000, 0.6660, 0.6540, 7810045.0000, 0.3043, -0.2480, -0.2290, 16439.0000),
('2025-04-01','kpi', 89580.0000, 32.7000, 0.0000, 0.0000, 0.0000, 47.7000, 82255.0000, 0.1390, 3927552.0000, 96.0000, 0.2350, -0.2460, -0.6840, 90.0000, 98000.0000, 0.5250, 8818169.0000, 144.0000, 0.3520, -0.2310, 12745721.0000, 0.6920, 0.6960, 8869010.0000, 0.3173, -0.2360, -0.2110, 16807.0000),
('2025-05-01','kpi', 85000.0000, 36.0000, 0.0000, 0.0000, 0.0000, 40.8000, 73119.0000, 0.1230, 3036439.0000, 100.0000, 0.2450, -0.2440, -0.8840, 89.0000, 129910.0000, 0.5650, 11765743.0000, 141.0000, 0.3470, -0.2250, 14802182.0000, 0.7950, 0.8870, 13133131.0000, 0.3252, -0.2290, -0.1780, 16494.0000),
('2025-06-01','kpi', 85000.0000, 34.4000, 0.0000, 0.0000, 0.0000, 39.5000, 74168.0000, 0.1210, 2967254.0000, 93.0000, 0.2290, -0.2380, -0.8700, 87.0000, 133209.0000, 0.5200, 11716334.0000, 130.0000, 0.3250, -0.2130, 14683589.0000, 0.7980, 0.9450, 13874862.0000, 0.3071, -0.2180, -0.1760, 16301.0000),
('2025-07-01','kpi', 85000.0000, 30.9000, 0.1620, 0.0000, 0.0000, 45.0000, 85250.0000, 0.1250, 3844180.0000, 92.0000, 0.2260, -0.2390, -0.6870, 95.0000, 145436.0000, 0.5180, 13821432.0000, 132.0000, 0.3310, -0.2140, 17665613.0000, 0.7820, 0.8830, 15591871.0000, 0.3096, -0.2190, -0.1500, 16254.0000),
('2025-08-01','kpi', 75000.0000, 26.0000, 0.1690, 58444.0000, 39.8000, 45.5000, 89423.0000, 0.1230, 4057436.0000, 96.0000, 0.2390, -0.2310, -0.5710, 98.0000, 164997.0000, 0.5170, 16135903.0000, 135.0000, 0.3400, -0.2090, 20193339.0000, 0.7990, 0.8650, 17518154.0000, 0.3206, -0.2140, -0.1150, 16306.0000),
('2025-09-01','kpi', 83000.0000, 25.4000, 0.1760, 62833.0000, 39.60000, 45.4000, 98000.0000, 0.1270, 4490665.0000, 95.0000, 0.2360, -0.2300, -0.5540, 102.0000, 172798.0000, 0.5140, 17765339.0000, 135.0000, 0.3370, -0.2150, 22256004.0000, 0.7980, 0.8900, 19803235.0000, 0.3172, -0.2180, -0.1120, 16306.0000);


  
INSERT INTO ind.ba_kpi_targets_m (
    month, ba_type, daily_avg_spend, cps, fl_confirm_1_2_rate, 
    fl_issue_1_4_cnt, fl_1_4_cps_rate, fl_avg_amt, fl_issue_cnt, 
    fl_pass_rate, fl_contract_amt, fl_loan_cycle, fl_fee_rate, 
    fl_bad_rate, fl_cust_cost, rl_avg_amt, rl_issue_cnt, 
    rl_pass_rate, rl_contract_amt, rl_loan_cycle, rl_fee_rate, 
    rl_bad_rate, total_amt, rl_amt_ratio, lend_biz_ratio, 
    lend_biz_amt, total_fee_rate, total_bad_rate, total_cust_cost, 
    exchange_rate
) VALUES (
    '2025-10-01', 'kpi', 
    40000.0000000000,      
    25.6410256410,         
    0.0000000000,          
    0.0000000000,          
    0.0000000000,          
    55.8851604633,         
    48360.0000000000,      
    0.0803250000,          
    2702606.3600073500,    
    70.7743689867,         
    0.1805514236,          
    -0.2365237179,         
    -0.4588163553,         
    124.8010442723,        
    85132.1717528279,      
    0.2900975233,          
    10624583.9359176000,   
    93.3696383567,         
    0.2430306672,          
    -0.2066145700,         
    13327190.2959249000,   
    0.7972110925,          
    0.6704542091,          
    8935270.8289182300,    
    0.2313605697,          
    -0.2126798134,         
    -0.0930428674,         
    16442.0000000000       
);

DROP TABLE IF EXISTS ind.ba_act_targets_process_m;

CREATE TABLE ind.ba_act_targets_process_m AS 

WITH overall_data AS (
    SELECT app_month as month,
           sum(issue_contract_amount_usd) as total_amt, 
           sum(case when grant_strategy='OLD' then issue_contract_amount else 0 end )/sum(issue_contract_amount) as rl_amt_ratio,
           sum(issue_haircut_amount)*1.0000/SUM(issue_contract_amount)+(SUM(issue_interest)*1.0000/SUM(issue_contract_amount))*(1-SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount)) as total_fee_rate,
           SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount) as total_bad_rate
    FROM ind.ba_apply_should_result
    GROUP BY 1
),
fl_data AS (
    SELECT app_month as month,
           sum(in_confirm_cnt_1_2)*1.0000/sum(in_confirm_cnt) as fl_confirm_1_2_rate,
           sum(issue_contract_amount_usd)*1.0000/sum(issue_cnt_from_issue) as fl_avg_amt,
           sum(issue_cnt_from_issue) as fl_issue_cnt,
           (sum(in_confirm_cnt)*1.0000/sum(if_app))*(sum(pass_cnt)*1.0000/sum(confirm_passed_cnt)) as fl_pass_rate,
           sum(issue_contract_amount_usd) as fl_contract_amt,
           sum(loan_cycle_amount)*1.0000/sum(issue_contract_amount) as fl_loan_cycle, 
           sum(issue_haircut_amount)*1.0000/SUM(issue_contract_amount)+(SUM(issue_interest)*1.0000/SUM(issue_contract_amount))*(1-SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount)) as fl_fee_rate,
           SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount) as fl_bad_rate 
    FROM ind.ba_apply_should_result
    WHERE grant_strategy='NEW' 
    GROUP BY 1
),
rl_data AS (
    SELECT app_month as month,
           sum(issue_contract_amount_usd)*1.0000/sum(issue_cnt_from_issue) as rl_avg_amt,
           sum(issue_cnt_from_issue) as rl_issue_cnt,
           (sum(in_confirm_cnt)*1.0000/sum(if_app))*(sum(pass_cnt)*1.0000/sum(confirm_passed_cnt)) as rl_pass_rate,
           sum(issue_contract_amount_usd) as rl_contract_amt,
           sum(loan_cycle_amount)*1.0000/sum(issue_contract_amount) as rl_loan_cycle, 
           sum(issue_haircut_amount)*1.0000/SUM(issue_contract_amount)+(SUM(issue_interest)*1.0000/SUM(issue_contract_amount))*(1-SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount)) as rl_fee_rate,
           SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount) as rl_bad_rate 
    FROM ind.ba_apply_should_result
    WHERE grant_strategy='OLD' 
    GROUP BY 1
),
weshare_data AS (
    SELECT issue_month as month,
           SUM(CASE WHEN account_name IN ('Weshare','Weshare2') THEN contract_amount_usd1 ELSE 0 END) AS lend_biz_amt
    FROM ind.ba_asset_base_info
    WHERE issue_month>='2025-01-01'
    GROUP BY 1
),
install_data AS (
    SELECT ad_date_month as month, 
           count(distinct ad_date) as daily_cnt,
           sum(spend)/count(distinct ad_date) as daily_avg_spend,
           sum(spend)/sum(issue_cnt) as cps,
           sum(issue_cnt_1_4) as fl_issue_1_4_cnt,
           sum(spend)/sum(issue_cnt_1_4) as fl_1_4_cps_rate,
           sum(spend)/sum(contract_amount_usd) as fl_cust_cost,
           sum(spend) as spend,
           sum(contract_amount_usd) as contract_amount_usd
    FROM ind.ba_install_apply_result
    WHERE ad_date < CURRENT_DATE
    GROUP BY 1 
)

SELECT 
    o.month,
    'act' as ba_type,
    i.daily_avg_spend,
    i.cps,
    f.fl_confirm_1_2_rate,
    i.fl_issue_1_4_cnt,
    i.fl_1_4_cps_rate,
    f.fl_avg_amt,
    f.fl_issue_cnt,
    f.fl_pass_rate,
    f.fl_contract_amt,
    f.fl_loan_cycle,
    f.fl_fee_rate,
    f.fl_bad_rate,
    i.fl_cust_cost,
    r.rl_avg_amt,
    r.rl_issue_cnt,
    r.rl_pass_rate,
    r.rl_contract_amt,
    r.rl_loan_cycle,
    r.rl_fee_rate,
    r.rl_bad_rate,
    o.total_amt,
    o.rl_amt_ratio,
    w.lend_biz_amt*1.0000/o.total_amt as lend_biz_ratio,
    w.lend_biz_amt,
    o.total_fee_rate,
    o.total_bad_rate,
    i.spend/o.total_amt as total_cust_cost,
    f1.exchange_rate_to_dollar,

    i.daily_cnt 
    
FROM overall_data o
LEFT JOIN fl_data f ON o.month = f.month
LEFT JOIN rl_data r ON o.month = r.month
LEFT JOIN weshare_data w ON o.month = w.month
LEFT JOIN install_data i ON o.month = i.month
LEFT JOIN dim.dim_exchange_rate_cost f1 ON date_format(date(o.month),'%Y%m') = f1.month_id AND f1.account_currency = 'IDR'
ORDER BY o.month;



select a.*,month_days as daily_cnt from ind.ba_kpi_targets_m a
LEFT JOIN dim.dim_data_info b on  date_format(date(a.month),'%Y%m%d')=b.data_date 
union all 
select month,
    ba_type,
    daily_avg_spend,
    cps,
    fl_confirm_1_2_rate,
    fl_issue_1_4_cnt,
    fl_1_4_cps_rate,
    fl_avg_amt,
    fl_issue_cnt,
    fl_pass_rate,
    fl_contract_amt,
    fl_loan_cycle,
    fl_fee_rate,
    fl_bad_rate * (-1) AS fl_bad_rate,

    fl_cust_cost * (-1) AS fl_cust_cost,

    rl_avg_amt,
    rl_issue_cnt,
    rl_pass_rate,
    rl_contract_amt,
    rl_loan_cycle,
    rl_fee_rate,
    rl_bad_rate * (-1) AS rl_bad_rate,
    total_amt,
    rl_amt_ratio,
    lend_biz_ratio,
    lend_biz_amt,
    total_fee_rate,
    total_bad_rate * (-1) AS total_bad_rate,
    total_cust_cost * (-1) AS total_cust_cost,

    exchange_rate_to_dollar,
    daily_cnt 
     from ind.ba_act_targets_process_m 

      

      select 
    a.month,
    a.ba_type,
    a.daily_avg_spend as new_01daily_avg_spend,
    a.cps as new_02cps,
    a.fl_confirm_1_2_rate as new_03confirm_1_2_rate,
    a.fl_issue_1_4_cnt as new_04issue_1_4_cnt,
    a.fl_1_4_cps_rate as new_05_1_4_cps_rate,
    a.fl_avg_amt as new_06avg_amt,
    a.fl_issue_cnt as new_07issue_cnt,
    a.fl_pass_rate as new_08pass_rate,
    a.fl_contract_amt as new_09contract_amt,
    a.fl_loan_cycle as new_10loan_cycle,
    a.fl_fee_rate as new_11fee_rate,
    a.fl_bad_rate * (-1) AS new_12bad_rate,
    a.fl_cust_cost * (-1) AS new_13cust_cost,
    a.rl_avg_amt as old_01avg_amt,
    a.rl_issue_cnt as old_02issue_cnt,
    a.rl_pass_rate as old_03pass_rate,
    a.rl_contract_amt as old_04contract_amt,
    a.rl_loan_cycle as old_05loan_cycle,
    a.rl_fee_rate as old_06fee_rate,
    a.rl_bad_rate * (-1) AS old_07bad_rate,
    a.total_amt as total_1amt,
    a.rl_amt_ratio as total_2old_ratio,
    a.lend_biz_ratio as total_3lend_ratio,
    a.lend_biz_amt as total_4lend_amt,
    a.total_fee_rate as total_5fee_rate,
    a.total_bad_rate * (-1) AS total_6bad_rate,
    a.total_cust_cost * (-1) AS total_7cust_cost,
    a.exchange_rate,
    b.month_days as daily_cnt 
from ind.ba_kpi_targets_m a
LEFT JOIN dim.dim_data_info b on date_format(date(a.month),'%Y%m%d')=b.data_date 
union all
select a.*,month_days as daily_cnt from ind.ba_kpi_targets_m a
LEFT JOIN dim.dim_data_info b on  date_format(date(a.month),'%Y%m%d')=b.data_date 



(IF( AND(${Column Field}=="daily_avg_spend",${ba_type}='act'),${Value Field},0)*1.0000)/IF( AND(${Column Field}='daily_avg_spend',${ba_type}='kpi'),${Value Field},0)






需要创建一个汇率表（16442）判断如果不一致，那么则使用16442的汇率；
需要更改偏移度计算逻辑；








DROP TABLE IF EXISTS ind.ba_act_targets_process_m;

CREATE TABLE ind.ba_act_targets_process_m AS 

WITH overall_data AS (
    SELECT app_month as month,
           sum(issue_contract_amount_usd) as total_amt, 
           sum(case when grant_strategy='OLD' then issue_contract_amount else 0 end )/sum(issue_contract_amount) as rl_amt_ratio,
           sum(issue_haircut_amount)*1.0000/SUM(issue_contract_amount)+(SUM(issue_interest)*1.0000/SUM(issue_contract_amount))*(1-SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount)) as total_fee_rate,
           SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount) as total_bad_rate
    FROM ind.ba_apply_should_result 

    GROUP BY 1
),
fl_data AS (
    SELECT app_month as month,
           sum(in_confirm_cnt_1_2)*1.0000/sum(in_confirm_cnt) as fl_confirm_1_2_rate,
           sum(issue_contract_amount_usd)*1.0000/sum(issue_cnt_from_issue) as fl_avg_amt,
           sum(issue_cnt_from_issue) as fl_issue_cnt,
           (sum(in_confirm_cnt)*1.0000/sum(if_app))*(sum(pass_cnt)*1.0000/sum(confirm_passed_cnt)) as fl_pass_rate,
           sum(issue_contract_amount_usd) as fl_contract_amt,
           sum(loan_cycle_amount)*1.0000/sum(issue_contract_amount) as fl_loan_cycle, 
           sum(issue_haircut_amount)*1.0000/SUM(issue_contract_amount)+(SUM(issue_interest)*1.0000/SUM(issue_contract_amount))*(1-SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount)) as fl_fee_rate,
           SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount) as fl_bad_rate 
    FROM ind.ba_apply_should_result
    WHERE grant_strategy='NEW'  
    GROUP BY 1
),
rl_data AS (
    SELECT app_month as month,
           sum(issue_contract_amount_usd)*1.0000/sum(issue_cnt_from_issue) as rl_avg_amt,
           sum(issue_cnt_from_issue) as rl_issue_cnt,
           (sum(in_confirm_cnt)*1.0000/sum(if_app))*(sum(pass_cnt)*1.0000/sum(confirm_passed_cnt)) as rl_pass_rate,
           sum(issue_contract_amount_usd) as rl_contract_amt,
           sum(loan_cycle_amount)*1.0000/sum(issue_contract_amount) as rl_loan_cycle, 
           sum(issue_haircut_amount)*1.0000/SUM(issue_contract_amount)+(SUM(issue_interest)*1.0000/SUM(issue_contract_amount))*(1-SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount)) as rl_fee_rate,
           SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount) as rl_bad_rate 
    FROM ind.ba_apply_should_result
    WHERE grant_strategy='OLD'   

    GROUP BY 1
),
weshare_data AS (
    SELECT issue_month as month,
           SUM(CASE WHEN account_name IN ('Weshare','Weshare2') THEN contract_amount_usd1 ELSE 0 END) AS lend_biz_amt
    FROM ind.ba_asset_base_info
    WHERE issue_month>='2025-01-01' 

    GROUP BY 1
),
install_data AS (
    SELECT ad_date_month as month, 
           count(distinct ad_date) as daily_cnt,
           sum(spend)/count(distinct ad_date) as daily_avg_spend,
           sum(spend)/sum(issue_cnt) as cps,
           sum(issue_cnt_1_4) as fl_issue_1_4_cnt,
           sum(spend)/sum(issue_cnt_1_4) as fl_1_4_cps_rate,
           sum(spend)/sum(contract_amount_usd) as fl_cust_cost,
           sum(spend) as spend,
           sum(contract_amount_usd) as contract_amount_usd
    FROM ind.ba_install_apply_result
    WHERE ad_date < CURRENT_DATE
    AND ad_date<DATE'2025-09-29' 
    GROUP BY 1 
)

SELECT 
    o.month,
    'act' as ba_type,
    i.daily_avg_spend,
    i.cps,
    f.fl_confirm_1_2_rate,
    i.fl_issue_1_4_cnt,
    i.fl_1_4_cps_rate,
    f.fl_avg_amt,
    f.fl_issue_cnt,
    f.fl_pass_rate,
    f.fl_contract_amt,
    f.fl_loan_cycle,
    f.fl_fee_rate,
    f.fl_bad_rate,
    i.fl_cust_cost,
    r.rl_avg_amt,
    r.rl_issue_cnt,
    r.rl_pass_rate,
    r.rl_contract_amt,
    r.rl_loan_cycle,
    r.rl_fee_rate,
    r.rl_bad_rate,
    o.total_amt,
    o.rl_amt_ratio,
    w.lend_biz_amt*1.0000/o.total_amt as lend_biz_ratio,
    w.lend_biz_amt,
    o.total_fee_rate,
    o.total_bad_rate,
    i.spend/o.total_amt as total_cust_cost,
    f1.exchange_rate_to_dollar,

    i.daily_cnt 
    
FROM overall_data o
LEFT JOIN fl_data f ON o.month = f.month
LEFT JOIN rl_data r ON o.month = r.month
LEFT JOIN weshare_data w ON o.month = w.month
LEFT JOIN install_data i ON o.month = i.month
LEFT JOIN dim.dim_exchange_rate_cost f1 ON date_format(date(o.month),'%Y%m') = f1.month_id AND f1.account_currency = 'IDR'
ORDER BY o.month;









WITH overall_data AS (
    SELECT app_month as month,
           sum(issue_contract_amount_usd) as total_amt, 
           sum(case when grant_strategy='OLD' then issue_contract_amount else 0 end )/sum(issue_contract_amount) as rl_amt_ratio,
           sum(issue_haircut_amount)*1.0000/SUM(issue_contract_amount)+(SUM(issue_interest)*1.0000/SUM(issue_contract_amount))*(1-SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount)) as total_fee_rate,
           SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount) as total_bad_rate
    FROM ind.ba_apply_should_result
    WHERE date(app_date) < DATE '${end_date}'  
    GROUP BY 1
),
fl_data AS (
    SELECT app_month as month,
           sum(in_confirm_cnt_1_2)*1.0000/sum(in_confirm_cnt) as fl_confirm_1_2_rate,
           sum(issue_contract_amount_usd)*1.0000/sum(issue_cnt_from_issue) as fl_avg_amt,
           sum(issue_cnt_from_issue) as fl_issue_cnt,
           (sum(in_confirm_cnt)*1.0000/sum(if_app))*(sum(pass_cnt)*1.0000/sum(confirm_passed_cnt)) as fl_pass_rate,
           sum(issue_contract_amount_usd) as fl_contract_amt,
           sum(loan_cycle_amount)*1.0000/sum(issue_contract_amount) as fl_loan_cycle, 
           sum(issue_haircut_amount)*1.0000/SUM(issue_contract_amount)+(SUM(issue_interest)*1.0000/SUM(issue_contract_amount))*(1-SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount)) as fl_fee_rate,
           SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount) as fl_bad_rate 
    FROM ind.ba_apply_should_result
    WHERE grant_strategy='NEW' 
    AND date(app_date) < DATE '${end_date}'  
    GROUP BY 1
),
rl_data AS (
    SELECT app_month as month,
           sum(issue_contract_amount_usd)*1.0000/sum(issue_cnt_from_issue) as rl_avg_amt,
           sum(issue_cnt_from_issue) as rl_issue_cnt,
           (sum(in_confirm_cnt)*1.0000/sum(if_app))*(sum(pass_cnt)*1.0000/sum(confirm_passed_cnt)) as rl_pass_rate,
           sum(issue_contract_amount_usd) as rl_contract_amt,
           sum(loan_cycle_amount)*1.0000/sum(issue_contract_amount) as rl_loan_cycle, 
           sum(issue_haircut_amount)*1.0000/SUM(issue_contract_amount)+(SUM(issue_interest)*1.0000/SUM(issue_contract_amount))*(1-SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount)) as rl_fee_rate,
           SUM(act_bad_debt_amt)*1.0000/SUM(issue_contract_amount) as rl_bad_rate 
    FROM ind.ba_apply_should_result
    WHERE grant_strategy='OLD' 
    AND date(app_date) < DATE '${end_date}'  
    GROUP BY 1
),
weshare_data AS (
    SELECT issue_month as month,
           SUM(CASE WHEN account_name IN ('Weshare','Weshare2') THEN contract_amount_usd1 ELSE 0 END) AS lend_biz_amt
    FROM ind.ba_asset_base_info
    WHERE issue_month >= '$2025-01-01'   
    AND date(issue_date) < DATE '${end_date}'  

    GROUP BY 1
),
install_data AS (
    SELECT ad_date_month as month, 
           count(distinct ad_date) as daily_cnt,
           sum(spend)/count(distinct ad_date) as daily_avg_spend,
           sum(spend)/sum(issue_cnt) as cps,
           sum(issue_cnt_1_4) as fl_issue_1_4_cnt,
           sum(spend)/sum(issue_cnt_1_4) as fl_1_4_cps_rate,
           sum(spend)/sum(contract_amount_usd) as fl_cust_cost,
           sum(spend) as spend,
           sum(contract_amount_usd) as contract_amount_usd
    FROM ind.ba_install_apply_result
    WHERE date(ad_date) < DATE '${end_date}' 

    GROUP BY 1 
),
result as (
SELECT 
    o.month,
    'act' as ba_type,
    i.daily_avg_spend,
    i.cps,
    f.fl_confirm_1_2_rate,
    i.fl_issue_1_4_cnt,
    i.fl_1_4_cps_rate,
    f.fl_avg_amt,
    f.fl_issue_cnt,
    f.fl_pass_rate,
    f.fl_contract_amt,
    f.fl_loan_cycle,
    f.fl_fee_rate,
    f.fl_bad_rate,
    i.fl_cust_cost,
    r.rl_avg_amt,
    r.rl_issue_cnt,
    r.rl_pass_rate,
    r.rl_contract_amt,
    r.rl_loan_cycle,
    r.rl_fee_rate,
    r.rl_bad_rate,
    o.total_amt,
    o.rl_amt_ratio,
    w.lend_biz_amt*1.0000/o.total_amt as lend_biz_ratio,
    w.lend_biz_amt,
    o.total_fee_rate,
    o.total_bad_rate,
    i.spend/o.total_amt as total_cust_cost,
    f1.exchange_rate_to_dollar,
    i.daily_cnt 
FROM overall_data o
LEFT JOIN fl_data f ON o.month = f.month
LEFT JOIN rl_data r ON o.month = r.month
LEFT JOIN weshare_data w ON o.month = w.month
LEFT JOIN install_data i ON o.month = i.month
LEFT JOIN dim.dim_exchange_rate_cost f1 ON date_format(date(o.month),'%Y%m') = f1.month_id AND f1.account_currency = 'IDR'
) 
SELECT 
    a.month,
    a.ba_type,
    a.daily_avg_spend as new_01daily_avg_spend,
    a.cps as new_02cps,
    a.fl_confirm_1_2_rate as new_03confirm_1_2_rate,
    a.fl_issue_1_4_cnt as new_04issue_1_4_cnt,
    a.fl_1_4_cps_rate as new_05_1_4_cps_rate,
    a.fl_avg_amt as new_06avg_amt,
    a.fl_issue_cnt as new_07issue_cnt,
    a.fl_pass_rate as new_08pass_rate,
    a.fl_contract_amt as new_09contract_amt,
    a.fl_loan_cycle as new_10loan_cycle,
    a.fl_fee_rate as new_11fee_rate,
    a.fl_bad_rate * (-1) AS new_12bad_rate,
    a.fl_cust_cost * (-1) AS new_13cust_cost,
    a.rl_avg_amt as old_01avg_amt,
    a.rl_issue_cnt as old_02issue_cnt,
    a.rl_pass_rate as old_03pass_rate,
    a.rl_contract_amt as old_04contract_amt,
    a.rl_loan_cycle as old_05loan_cycle,
    a.rl_fee_rate as old_06fee_rate,
    a.rl_bad_rate * (-1) AS old_07bad_rate,
    a.total_amt as total_1amt,
    a.rl_amt_ratio as total_2old_ratio,
    a.lend_biz_ratio as total_3lend_ratio,
    a.lend_biz_amt as total_4lend_amt,
    a.total_fee_rate as total_5fee_rate,
    a.total_bad_rate * (-1) AS total_6bad_rate,
    a.total_cust_cost * (-1) AS total_7cust_cost,
    a.exchange_rate_to_dollar as exchange_rate,
    daily_cnt  
FROM result a 
UNION ALL
SELECT a.*, month_days as daily_cnt 
FROM ind.ba_kpi_targets_m a
LEFT JOIN dim.dim_data_info b ON date_format(date(a.month),'%Y%m%d') = b.data_date










日均投放量级
投放CPS
纯新授信1-2占比(运营口径）
1-4放款人头
授信1-4CPS
首贷-件均
首贷-笔数
首贷-通过率
首贷-合同业绩
首贷平均期限-天
预计实收息费
首贷-坏账
获客成本
复贷-件均
复贷-笔数
复贷-通过率
复贷-合同业绩
复贷平均期限-天
预计实收息费
复贷-坏账
整体业绩-美金
复贷业绩占比
助贷业绩占比
助贷业绩
预计实收息费
整体-坏账
获客成本
