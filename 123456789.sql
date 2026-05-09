WITH  
reg_users AS (
    SELECT 
        mid,
        DATE_TRUNC('month', MIN(reg_dt)) AS reg_month,
        MIN(reg_dt) AS reg_date
    FROM ind.tyn_reg_install_new
    WHERE reg_dt >= DATE '2024-01-01'
    GROUP BY mid
),
 
user_behavior_d30 AS (
    SELECT 
        r.mid,
        r.reg_month,
        r.reg_date,
         
        MIN(CASE 
            WHEN date(b.app_date) >= r.reg_date 

            AND date(b.app_date) <= r.reg_date + INTERVAL '30' DAY 

            THEN b.app_date 
        END) AS d30_app_date,
        
        MIN(CASE 
            WHEN date(b.app_date) >= r.reg_date 

            AND date(b.app_date) <= r.reg_date + INTERVAL '30' DAY 

            AND b.if_in_confirm = 1
            THEN b.app_date 
        END) AS d30_if_in_confirm_date,
 
        MIN(CASE 
            WHEN date(b.confirm_time) >= r.reg_date 

            AND date(b.confirm_time) <= r.reg_date + INTERVAL '30' DAY 

            THEN b.confirm_time 
        END) AS d30_confirm_date,
          
        MIN(CASE 
            WHEN date(b.issue_date) >= r.reg_date 
            AND date(b.issue_date) <= r.reg_date + INTERVAL '30' DAY 

            THEN b.issue_date 
        END) AS d30_issue_date
        
    FROM reg_users r
    LEFT JOIN ind.ba_asset_base_info b 
        ON r.mid = b.mid 
        AND b.if_app = 1
        AND b.grant_strategy = 'NEW'
        AND b.create_time >= date'2024-01-01'
    GROUP BY r.mid, r.reg_month, r.reg_date
)


SELECT 
    reg_month,
    COUNT(DISTINCT mid) AS registered_users,
    COUNT(DISTINCT CASE WHEN d30_app_date IS NOT NULL THEN mid END) AS d30_app_users,
    COUNT(DISTINCT CASE WHEN d30_if_in_confirm_date IS NOT NULL THEN mid END) AS d30_in_confirm_users,
    COUNT(DISTINCT CASE WHEN d30_confirm_date IS NOT NULL THEN mid END) AS d30_confirm_users,
    COUNT(DISTINCT CASE WHEN d30_issue_date IS NOT NULL THEN mid END) AS d30_transaction_users 
FROM user_behavior_d30
GROUP BY 1
ORDER BY 1 DESC;
















WITH  
reg_users AS (
    SELECT 
        mid,
        DATE_TRUNC('month', MIN(reg_dt)) AS reg_month,
        MIN(reg_dt) AS reg_date
    FROM ind.tyn_reg_install_new
    WHERE reg_dt >= DATE '2024-01-01'
    GROUP BY mid
),

transaction_d30 AS (
    SELECT 
        r.mid,
        r.reg_month,
         COUNT(DISTINCT b.biz_id) AS d30_transaction_count,
        
         SUM(b.contract_amount) AS d30_transaction_amount_local,
        
        -- D30应还金额（当地货币）- 需要计算应还本金+利息
        SUM(
            CASE 
                WHEN b.contract_amount > 0 
                THEN b.contract_amount * (1 + COALESCE(b.should_interest, 0) / 100.0)
                ELSE 0 
            END
        ) AS d30_should_repay_amount_local,
        
        -- D30还款金额（当地货币）- 假设有实际还款金额字段
        SUM(COALESCE(b.contract_amount - b.overdue_amount_total_30, 0)) AS d30_actual_repay_amount_local,
        
        -- D30还款笔数 - 假设有还款状态字段
        COUNT(DISTINCT CASE 
            WHEN b.should_capital_total_30 > 0 
            AND b.overdue_amount_total_30 < b.should_capital_total_30 
            THEN b.biz_id 
        END) AS d30_repayment_count,
        
        -- 逾期笔数（部分还款视为未还款）
        COUNT(DISTINCT CASE 
            WHEN b.overdue_amount_total_30 > 0 
            THEN b.biz_id 
        END) AS d30_overdue_count,
        
        -- 汇率信息（假设有汇率字段）
        AVG(COALESCE(b.exchange_rate_to_dollar, 0.36)) AS avg_exchange_rate,
        
        -- 用户层级信息用于计算定价
        AVG(CASE 
            WHEN b.product_level_type_1 = 'M' THEN 0.40
            WHEN b.product_level_type_1 = 'F-NofeeNew' THEN 0.35
            WHEN b.product_level_type_1 = 'F-NofeeOld' THEN 0.38
            WHEN b.product_level_type_1 = 'R-30' THEN 0.45
            WHEN b.product_level_type_1 = 'R-15' THEN 0.50
            ELSE 0.40 
        END) AS avg_pricing_rate
        
    FROM reg_users r
    LEFT JOIN ind.ba_asset_base_info b 
        ON r.mid = b.mid 
        AND b.if_app = 1
        AND b.grant_strategy = 'NEW'
        AND date(b.issue_date) >= r.reg_date 
        AND date(b.issue_date) <= r.reg_date + INTERVAL '30' DAY
    GROUP BY r.mid, r.reg_month
),





  
SELECT 
     DATE_FORMAT(expect_day, '%Y-%m-01') AS expect_month, -- 到期时间  
 
    SUM(should_capital) AS due_amt, 
    SUM(should_capital+should_interest+should_fine) AS due_interest, 
    sum(fact_capital) AS fact_capital, 
    sum(should_capital-fact_capital) AS onloan_amount,  
    SUM(IF(DATEDIFF(finish_day, expect_day) > 0, should_capital, 0)) AS d0_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 1, should_capital, 0)) AS d1_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 3, should_capital, 0)) AS d3_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 7, should_capital, 0)) AS d7_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 30, should_capital, 0)) AS d30_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 60, should_capital, 0)) AS d60_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 90, should_capital, 0)) AS d90_rucui,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 1,repaid_amount,0)) as  d1_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 3,repaid_amount,0)) as d3_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 7,repaid_amount,0)) as d7_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 15,repaid_amount,0)) as d15_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 30,repaid_amount,0)) as d30_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 60,repaid_amount,0))  as d60_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 90,repaid_amount,0))  as d90_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 120,repaid_amount,0))  as d120_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 150,repaid_amount,0))  as d150_huishou,
sum(if(finish_day > expect_day,repaid_amount,0))  as all_huishou
from (
    SELECT 
        customer_id,
        camera_id, 
        
        max(DATE(b.should_time)) AS expect_day,
        max(DATE(IF(b.fact_time is null,CURRENT_DATE,b.fact_time))) AS finish_day,
        sum(should_capital) AS should_capital,
        sum(fact_capital) AS fact_capital,
        sum(should_interest) AS should_interest,
        sum(fact_interest) AS fact_interest,
        sum(should_fine) AS should_fine,
        sum(fact_fine) AS fact_fine
     FROM ods.s02_loan_repayment b
    group by 1,2
) t



	drop table total_collect_due; 
	create table total_collect_due  as 
SELECT 
    DATE_FORMAT(biz_grant_time, '%Y-%m-01') AS grant_month, -- 放款时间
    DATE_FORMAT(expect_day, '%Y-%m-01') AS expect_month, -- 到期时间  
 
    SUM(should_capital) AS due_amt, -- 本金
    SUM(IF(DATEDIFF(finish_day, expect_day) > 0, should_capital, 0)) AS d0_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 1, should_capital, 0)) AS d1_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 3, should_capital, 0)) AS d3_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 7, should_capital, 0)) AS d7_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 15, should_capital, 0)) AS d15_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 30, should_capital, 0)) AS d30_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 60, should_capital, 0)) AS d60_rucui,
    SUM(IF(DATEDIFF(finish_day, expect_day) > 90, should_capital, 0)) AS d90_rucui,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 1,repaid_amount,0)) as  d1_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 3,repaid_amount,0)) as d3_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 7,repaid_amount,0)) as d7_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 15,repaid_amount,0)) as d15_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 30,repaid_amount,0)) as d30_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 60,repaid_amount,0))  as d60_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 90,repaid_amount,0))  as d90_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 120,repaid_amount,0))  as d120_huishou,
sum(if(finish_day > expect_day and DATEDIFF(finish_day, expect_day) <= 150,repaid_amount,0))  as d150_huishou,
sum(if(finish_day > expect_day,repaid_amount,0))  as all_huishou
FROM
(   SELECT  a.*, 
        b.period_seq as dtransaction_period , -- 期数 
		    DATE(b.due_time) AS expect_day, -- 到期时间 
        DATE(IF(b.finish_time is null or b.finish_time>='2024-09-01', '2024-09-01', b.finish_time)) AS finish_day,
        b.granted_principal_period_amt as should_capital, -- 本金
        b.repaid_principal_period_amt as repaid_amount -- 已还本金
    FROM ziyou_biz_grant a
    JOIN dwb.dwb_asset_period_info b ON apply_code = b.asset_item_no  AND date(b.due_time) >= '2022-01-01' AND date(b.due_time) < '2024-09-01' 
 
) d
GROUP BY 1, 2, 3, 4, 5 ,6,7,8,9,10,11,12,13,14 
ORDER BY 1, 2 ; 



-- 总（按照月份）
	select grant_month, 
	sum(due_amt) as due_amt, 
	sum(d1_rucui) as d1,
	sum(d3_rucui) as d3,
	sum(d7_rucui) as d7,
	sum(d30_rucui) as d30,
	sum(d60_rucui) as d60,
	sum(d90_rucui) as d90,
	sum(d1_huishou) as d1_huishou,
	sum(d3_huishou) as d3_huishou,
	sum(d7_huishou) as d7_huishou,
	sum(d30_huishou) as d30_huishou,
	sum(d60_huishou) as d60_huishou,
			sum(d90_huishou) as d90_huishou,
		sum(d120_huishou) as d120_huishou,
			sum(d150_huishou) as d150_huishou,
				sum(all_huishou) as all_huishou
	 from 
	testdb.total_collect_due
	where  grant_month>='2019-01-01'
	group by 1  
	order by 1
		


        
    select customer_id,camera_id,indexs,state,
    DATE(b.should_time) AS expect_day,
    DATE(
      IF(
          b.fact_time is null,
          CURRENT_DATE,
          b.fact_time
      )
    ) AS finish_day,
    should_capital,
    fact_capital,
    should_interest,
    fact_interest,
    should_fine,
    fact_fine 
    from ods.s02_loan_repayment_his b
    where customer_id=1040160112795540.000000
    and date(should_time)=date(date_parse(data_date, '%Y%m%d'))








    WITH  
reg_users AS (
    SELECT 
        mid,
        date_trunc('month', MIN(reg_dt)) AS reg_month,
        MIN(reg_dt) AS reg_date
    FROM ind.tyn_reg_install_new
    WHERE reg_dt >= DATE '2024-01-01'
    GROUP BY mid
),
 

 
latest_repayments AS (
    SELECT 
        customer_id,
        camera_id, 
        
        max(DATE(b.should_time)) AS expect_day,
        max(DATE(IF(b.fact_time is null,CURRENT_DATE,b.fact_time))) AS finish_day,
        sum(should_capital) AS should_capital,
        sum(fact_capital) AS fact_capital,
        sum(should_interest) AS should_interest,
        sum(fact_interest) AS fact_interest,
        sum(should_fine) AS should_fine,
        sum(fact_fine) AS fact_fine
     FROM ods.s02_loan_repayment b
    group by 1,2
 
) 
    SELECT 
        r.mid,
        r.reg_month,
        r.reg_date,
        b.biz_id,
        count(distinct b.biz_id) AS d30_transaction_cnt,
        count(distinct case when lp.finish_day <= lp.expect_day   then b.biz_id else null end) AS d30_repayment_cnt,
        count(distinct case when lp.finish_day > lp.expect_day   then b.biz_id else null end) AS d30_due_cnt,
        sum(b.contract_amount) AS d30_contract_amount,
        sum(lp.should_capital+lp.should_interest) AS d30_should_repay_amount,

        sum(lp.fact_capital+lp.fact_interest) AS d30_fact_repay_amount,
        sum(lp.should_capital+lp.should_interest)/sum(b.contract_amount) AS d30_dingjia_rate,
        (sum(lp.fact_capital+lp.fact_interest)-sum(b.contract_amount))/sum(b.contract_amount) AS d30_due_amt_rate
 
    FROM reg_users r
    LEFT JOIN ind.ba_asset_base_info b  ON r.mid = b.mid  AND b.if_issue = 1  and date(b.issue_date) >= r.reg_date 
                                                          AND date(b.issue_date) <= r.reg_date + INTERVAL '30' DAY 
    left join latest_repayments lp on lp.customer_id = r.mid 
        and  TRY_CAST(b.biz_id AS BIGINT) = TRY_CAST(lp.camera_id AS BIGINT)
group by 1,2,3,4




repayments_d30 AS (
    SELECT 
        r.mid,
        r.reg_month,
        r.reg_date,
        t.transaction_id,
        t.contract_amount,
        t.issue_date,
        lp.expect_day,
        lp.finish_day,
        lp.should_capital,
        lp.fact_capital,
        lp.should_interest,
        lp.fact_interest,
        lp.should_fine,
        lp.fact_fine,
        lp.state,
        -- 判断还款是否在注册后30天内（按应还日期计算）
        CASE 
            WHEN lp.expect_day >= r.reg_date 
            AND lp.expect_day <= r.reg_date + INTERVAL '30' DAY
            THEN 1 ELSE 0 
        END AS repayment_within_d30
    FROM reg_users r
    LEFT JOIN ind.ba_asset_base_info b 
        ON r.mid = b.mid 
        AND b.if_issue = 1
         AND b.issue_date >= r.reg_date 
        AND b.issue_date <= r.reg_date + INTERVAL '30' DAY
    LEFT JOIN latest_repayments lp 
        ON lp.camera_id = CAST(CEIL(b.biz_id) AS BIGINT)
        AND lp.rn = 1  -- 取最新切片
    LEFT JOIN transactions_d30 t 
        ON r.mid = t.mid AND t.transaction_id = b.biz_id
),

-- 4. 按月聚合统计交易指标
monthly_transactions AS (
    SELECT 
        date_format(reg_month, '%Y-%m') AS month,
        -- D30交易笔数
        COUNT(DISTINCT CASE 
            WHEN issue_date >= reg_date 
            AND issue_date <= reg_date + INTERVAL '30' DAY 
            THEN transaction_id 
        END) AS d30_transaction_count,
        
        -- D30交易金额（当地货币）
        SUM(CASE 
            WHEN issue_date >= reg_date 
            AND issue_date <= reg_date + INTERVAL '30' DAY 
            THEN contract_amount ELSE 0 
        END) AS d30_transaction_amount,
        
        -- D30应还金额（当地货币）包含本金+利息+罚金
        SUM(CASE 
            WHEN expect_day >= reg_date 
            AND expect_day <= reg_date + INTERVAL '30' DAY 
            THEN should_capital + should_interest + should_fine 
            ELSE 0 
        END) AS d30_should_repay_amount,
        
        -- D30还款笔数（完全还款才算，部分还款视为未还款）
        COUNT(DISTINCT CASE 
            WHEN expect_day >= reg_date 
            AND expect_day <= reg_date + INTERVAL '30' DAY 
            AND state = 1  -- 假设state=1表示已完全还款
            AND fact_capital >= should_capital 
            AND fact_interest >= should_interest 
            AND fact_fine >= should_fine
            THEN CONCAT(camera_id, '-', indexs) 
        END) AS d30_repayment_count,
        
        -- D30还款金额（当地货币）实际已还的金额
        SUM(CASE 
            WHEN expect_day >= reg_date 
            AND expect_day <= reg_date + INTERVAL '30' DAY 
            THEN fact_capital + fact_interest + fact_fine 
            ELSE 0 
        END) AS d30_actual_repay_amount
        
    FROM repayments_d30
    GROUP BY date_format(reg_month, '%Y-%m')
),

-- 5. 按月统计注册用户数
monthly_reg_users AS (
    SELECT 
        date_format(reg_month, '%Y-%m') AS month,
        COUNT(DISTINCT mid) AS registered_users
    FROM reg_users
    GROUP BY date_format(reg_month, '%Y-%m')
)

-- 6. 最终结果
SELECT 
    mr.month,
    mr.registered_users,
    mt.d30_transaction_count,
    mt.d30_repayment_count,
    -- D30笔数逾期率 = (交易笔数 - 还款笔数) / 交易笔数
    ROUND(
        CASE WHEN mt.d30_transaction_count > 0 
        THEN (mt.d30_transaction_count - mt.d30_repayment_count) * 100.0 / mt.d30_transaction_count 
        ELSE 0 END, 2
    ) AS d30_count_overdue_rate,
    
    mt.d30_transaction_amount,
    mt.d30_should_repay_amount,
    mt.d30_actual_repay_amount,
    
    -- 定价 = (应还金额 - 交易金额) / 交易金额
    ROUND(
        CASE WHEN mt.d30_transaction_amount > 0 
        THEN (mt.d30_should_repay_amount - mt.d30_transaction_amount) * 100.0 / mt.d30_transaction_amount 
        ELSE 0 END, 2
    ) AS pricing_rate,
    
    -- D30金额逾期率 = (应还金额 - 还款金额) / 交易金额
    ROUND(
        CASE WHEN mt.d30_transaction_amount > 0 
        THEN (mt.d30_should_repay_amount - mt.d30_actual_repay_amount) * 100.0 / mt.d30_transaction_amount 
        ELSE 0 END, 2
    ) AS d30_amount_overdue_rate
    
FROM monthly_reg_users mr
LEFT JOIN monthly_transactions mt ON mr.month = mt.month
ORDER BY mr.month DESC;