-- 新客用户数

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
 
user_behavior_30d AS (
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
FROM user_behavior_30d
GROUP BY 1
ORDER BY 1 DESC;




-- 新客30天内交易数

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









 
transaction_30d AS (
    SELECT 
        r.mid,
        r.reg_month,
        -- D30交易笔数
        COUNT(DISTINCT b.biz_id) AS d30_transaction_count,
        
        -- D30交易金额（当地货币）
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
        AND b.issue_date >= r.reg_date 
        AND b.issue_date <= r.reg_date + INTERVAL '30' DAY
    GROUP BY r.mid, r.reg_month
),

-- GTV生命周期指标（截止到2025-08-31）
gtv_lifetime AS (
    SELECT 
        r.mid,
        r.reg_month,
        -- 生命周期交易笔数
        COUNT(DISTINCT b.biz_id) AS lifetime_transaction_count,
        
        -- 生命周期交易金额（当地货币）
        SUM(b.contract_amount) AS lifetime_transaction_amount_local,
        
        -- 生命周期应还金额（当地货币）
        SUM(
            CASE 
                WHEN b.contract_amount > 0 
                THEN b.contract_amount * (1 + COALESCE(b.should_interest, 0) / 100.0)
                ELSE 0 
            END
        ) AS lifetime_should_repay_amount_local,
        
        -- 生命周期还款金额（当地货币）
        SUM(COALESCE(b.contract_amount - b.overdue_amount_total_30, 0)) AS lifetime_actual_repay_amount_local,
        
        -- 生命周期还款笔数
        COUNT(DISTINCT CASE 
            WHEN b.should_capital_total_30 > 0 
            AND b.overdue_amount_total_30 < b.should_capital_total_30 
            THEN b.biz_id 
        END) AS lifetime_repayment_count,
        
        -- 生命周期逾期笔数
        COUNT(DISTINCT CASE 
            WHEN b.overdue_amount_total_30 > 0 
            THEN b.biz_id 
        END) AS lifetime_overdue_count,
        
        -- 最近一次交易在60天以内的用户
        MAX(CASE 
            WHEN b.issue_date >= DATE '2025-08-31' - INTERVAL '60' DAY 
            THEN 1 
            ELSE 0 
        END) AS recent_transaction_60d_flag
        
    FROM reg_users r
    LEFT JOIN ind.ba_asset_base_info b 
        ON r.mid = b.mid 
        AND b.if_app = 1
        AND b.grant_strategy = 'NEW'
        AND b.issue_date <= DATE '2025-08-31'
    GROUP BY r.mid, r.reg_month
),

-- APP下载用户数
app_download_users AS (
    SELECT 
        TO_CHAR(DATE_TRUNC('month', reg_dt), 'YYYY-MM') AS month,
        COUNT(DISTINCT mid) AS app_download_users
    FROM ind.tyn_reg_install_new
    WHERE reg_dt >= DATE '2024-01-01'
    GROUP BY TO_CHAR(DATE_TRUNC('month', reg_dt), 'YYYY-MM')
),

-- 用户留存计算（有交易的用户）
user_retention AS (
    SELECT 
        reg_month,
        COUNT(DISTINCT mid) AS total_transaction_users,
        COUNT(DISTINCT CASE 
            WHEN EXISTS (
                SELECT 1 
                FROM ind.ba_asset_base_info b2 
                WHERE b2.mid = r.mid 
                AND b2.if_app = 1 
                AND b2.grant_strategy = 'NEW'
                AND b2.issue_date >= DATE '2025-08-31' - INTERVAL '60' DAY
                AND b2.issue_date <= DATE '2025-08-31'
            ) THEN mid 
        END) AS retained_users
    FROM reg_users r
    WHERE EXISTS (
        SELECT 1 
        FROM ind.ba_asset_base_info b 
        WHERE b.mid = r.mid 
        AND b.if_app = 1 
        AND b.grant_strategy = 'NEW'
    )
    GROUP BY reg_month
),
 
monthly_stats AS (
    SELECT 
        TO_CHAR(r.reg_month, 'YYYY-MM') AS month,
        
        -- 基础用户数
        COUNT(DISTINCT r.mid) AS registered_users,
        
        -- D30申请用户数
        COUNT(DISTINCT CASE WHEN ub.d30_app_date IS NOT NULL THEN r.mid END) AS d30_app_users,
        
        -- D30授信审批通过用户数
        COUNT(DISTINCT CASE WHEN ub.d30_confirm_date IS NOT NULL THEN r.mid END) AS d30_approval_users,
        
        -- D30交易用户数
        COUNT(DISTINCT CASE WHEN ub.d30_issue_date IS NOT NULL THEN r.mid END) AS d30_transaction_users,
        
        -- D30交易笔数
        SUM(COALESCE(t.d30_transaction_count, 0)) AS d30_transaction_count,
        
        -- D30还款笔数
        SUM(COALESCE(t.d30_repayment_count, 0)) AS d30_repayment_count,
        
        -- D30交易金额（当地货币）
        SUM(COALESCE(t.d30_transaction_amount_local, 0)) AS d30_transaction_amount_local,
        
        -- D30应还金额（当地货币）
        SUM(COALESCE(t.d30_should_repay_amount_local, 0)) AS d30_should_repay_amount_local,
        
        -- D30还款金额（当地货币）
        SUM(COALESCE(t.d30_actual_repay_amount_local, 0)) AS d30_actual_repay_amount_local,
        
        -- 平均定价
        AVG(t.avg_pricing_rate) AS avg_pricing_rate_30d,
        
        -- 平均汇率
        AVG(t.avg_exchange_rate) AS avg_exchange_rate_30d,
        
        -- D30逾期笔数
        SUM(COALESCE(t.d30_overdue_count, 0)) AS d30_overdue_count,
        
        -- GTV生命周期交易笔数
        SUM(COALESCE(g.lifetime_transaction_count, 0)) AS lifetime_transaction_count,
        
        -- GTV生命周期还款笔数
        SUM(COALESCE(g.lifetime_repayment_count, 0)) AS lifetime_repayment_count,
        
        -- GTV生命周期交易金额（当地货币）
        SUM(COALESCE(g.lifetime_transaction_amount_local, 0)) AS lifetime_transaction_amount_local,
        
        -- GTV生命周期应还金额（当地货币）
        SUM(COALESCE(g.lifetime_should_repay_amount_local, 0)) AS lifetime_should_repay_amount_local,
        
        -- GTV生命周期还款金额（当地货币）
        SUM(COALESCE(g.lifetime_actual_repay_amount_local, 0)) AS lifetime_actual_repay_amount_local,
        
        -- GTV生命周期逾期笔数
        SUM(COALESCE(g.lifetime_overdue_count, 0)) AS lifetime_overdue_count,
        
        -- 最近60天内有交易的用户数
        SUM(CASE WHEN g.recent_transaction_60d_flag = 1 THEN 1 ELSE 0 END) AS recent_transaction_users_60d
        
    FROM reg_users r
    LEFT JOIN user_behavior_30d ub ON r.mid = ub.mid AND r.reg_month = ub.reg_month
    LEFT JOIN transaction_30d t ON r.mid = t.mid AND r.reg_month = t.reg_month
    LEFT JOIN gtv_lifetime g ON r.mid = g.mid AND r.reg_month = g.reg_month
    GROUP BY TO_CHAR(r.reg_month, 'YYYY-MM')
)

-- 最终结果，包含所有指标
SELECT 
    m.month,
    COALESCE(a.app_download_users, m.registered_users) AS app_download_users,
    m.registered_users,
    m.d30_app_users,
    m.d30_approval_users,
    m.d30_transaction_users,
    
    -- D30交易指标
    m.d30_transaction_count,
    m.d30_repayment_count,
    CASE 
        WHEN m.d30_transaction_count > 0 
        THEN ROUND((m.d30_transaction_count - m.d30_repayment_count) * 100.0 / m.d30_transaction_count, 2)
        ELSE 0 
    END AS d30_count_overdue_rate,
    
    m.d30_transaction_amount_local,
    m.d30_should_repay_amount_local,
    m.d30_actual_repay_amount_local,
    
    -- 定价
    CASE 
        WHEN m.d30_transaction_amount_local > 0 
        THEN ROUND((m.d30_should_repay_amount_local - m.d30_transaction_amount_local) * 100.0 / m.d30_transaction_amount_local, 2)
        ELSE 0 
    END AS pricing_30d,
    
    -- D30金额逾期率
    CASE 
        WHEN m.d30_transaction_amount_local > 0 
        THEN ROUND((m.d30_should_repay_amount_local - m.d30_actual_repay_amount_local) * 100.0 / m.d30_transaction_amount_local, 2)
        ELSE 0 
    END AS d30_amount_overdue_rate,
    
    m.avg_exchange_rate_30d AS exchange_rate_to_rmb,
    
    -- D30件均（人民币）
    CASE 
        WHEN m.d30_transaction_count > 0 
        THEN ROUND((m.d30_transaction_amount_local / m.d30_transaction_count) * m.avg_exchange_rate_30d, 0)
        ELSE 0 
    END AS d30_avg_transaction_amount_rmb,
    
    -- GTV生命周期指标
    m.lifetime_transaction_count,
    m.lifetime_repayment_count,
    CASE 
        WHEN m.lifetime_transaction_count > 0 
        THEN ROUND((m.lifetime_transaction_count - m.lifetime_repayment_count) * 100.0 / m.lifetime_transaction_count, 2)
        ELSE 0 
    END AS lifetime_count_overdue_rate,
    
    m.lifetime_transaction_amount_local,
    m.lifetime_should_repay_amount_local,
    m.lifetime_actual_repay_amount_local,
    
    -- 生命周期定价
    CASE 
        WHEN m.lifetime_transaction_amount_local > 0 
        THEN ROUND((m.lifetime_should_repay_amount_local - m.lifetime_transaction_amount_local) * 100.0 / m.lifetime_transaction_amount_local, 2)
        ELSE 0 
    END AS lifetime_pricing,
    
    -- 生命周期金额逾期率
    CASE 
        WHEN m.lifetime_transaction_amount_local > 0 
        THEN ROUND((m.lifetime_should_repay_amount_local - m.lifetime_actual_repay_amount_local) * 100.0 / m.lifetime_transaction_amount_local, 2)
        ELSE 0 
    END AS lifetime_amount_overdue_rate,
    
    -- 生命周期件均（人民币）- 使用平均汇率
    CASE 
        WHEN m.lifetime_transaction_count > 0 
        THEN ROUND((m.lifetime_transaction_amount_local / m.lifetime_transaction_count) * m.avg_exchange_rate_30d, 0)
        ELSE 0 
    END AS lifetime_avg_transaction_amount_rmb,
    
    -- 用户留存率（有交易）
    CASE 
        WHEN m.d30_transaction_users > 0 
        THEN ROUND(m.recent_transaction_users_60d * 100.0 / m.d30_transaction_users, 2)
        ELSE 0 
    END AS user_retention_rate,
    
    -- 转化率指标
    ROUND(
        CASE WHEN m.registered_users > 0 
        THEN m.d30_app_users * 100.0 / m.registered_users 
        ELSE 0 END, 2
    ) AS apply_to_reg_conversion_rate,
    
    ROUND(
        CASE WHEN m.d30_app_users > 0 
        THEN m.d30_approval_users * 100.0 / m.d30_app_users 
        ELSE 0 END, 2
    ) AS approval_to_apply_conversion_rate,
    
    ROUND(
        CASE WHEN m.d30_approval_users > 0 
        THEN m.d30_transaction_users * 100.0 / m.d30_approval_users 
        ELSE 0 END, 2
    ) AS transaction_to_approval_conversion_rate,
    
    ROUND(
        CASE WHEN m.registered_users > 0 
        THEN m.d30_transaction_users * 100.0 / m.registered_users 
        ELSE 0 END, 2
    ) AS transaction_to_reg_conversion_rate
    
FROM monthly_stats m
LEFT JOIN app_download_users a ON m.month = a.month
ORDER BY m.month DESC;