-- 1业务数据尽调模板（新客报表）
-- 注意：1、D30授信审批通过用户数(这里是按照注册后30天内进件的用户数，（这批用户）的授信审批通过用户数)
-- 2、美元兑人民币汇率（按照表里的数据印尼盾兑换美金汇率/印尼盾兑换人民币汇率）
-- 3、GTV数据暂时没提供；

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
),

latest_repayments AS (
    SELECT 
        customer_id,
        camera_id, 
        
        max(DATE(b.should_time)) AS expect_day,
        max(DATE(IF(b.fact_time is null, CURRENT_DATE, b.fact_time))) AS finish_day,
        sum(should_capital) AS should_capital,
        sum(fact_capital) AS fact_capital,
        sum(should_interest) AS should_interest,
        sum(fact_interest) AS fact_interest,
        sum(should_fine) AS should_fine,
        sum(fact_fine) AS fact_fine
    FROM ods.s02_loan_repayment b
    GROUP BY 1, 2
),

issue_stats AS (
    SELECT 
        r.mid,
        r.reg_month,
        r.reg_date,
        b.biz_id,
        b.contract_amount,
        lp.expect_day,
        lp.finish_day,
        lp.should_capital,
        lp.fact_capital,
        lp.should_interest,
        lp.fact_interest,
        lp.should_fine,
        lp.fact_fine
    FROM reg_users r
    LEFT JOIN ind.ba_asset_base_info b 
        ON r.mid = b.mid 
        AND b.if_issue = 1
        AND b.grant_strategy = 'NEW'
        AND date(b.issue_date) >= r.reg_date 
        AND date(b.issue_date) <= r.reg_date + INTERVAL '30' DAY
    LEFT JOIN latest_repayments lp 
        ON lp.customer_id = r.mid 
        AND TRY_CAST(b.biz_id AS BIGINT) = TRY_CAST(lp.camera_id AS BIGINT)
),
 
user_behavior_stats AS (
    SELECT 
        reg_month,
        COUNT(DISTINCT mid) AS reg_users,
        COUNT(DISTINCT CASE WHEN d30_app_date IS NOT NULL THEN mid END) AS d30_app_users,
        COUNT(DISTINCT CASE WHEN d30_if_in_confirm_date IS NOT NULL THEN mid END) AS d30_in_confirm_users,
        COUNT(DISTINCT CASE WHEN d30_confirm_date IS NOT NULL THEN mid END) AS d30_confirm_users,
        COUNT(DISTINCT CASE WHEN d30_issue_date IS NOT NULL THEN mid END) AS d30_issue_users
    FROM user_behavior_30d
    GROUP BY reg_month
),
 
issue_repayment_stats AS (
    SELECT 
        reg_month,
        COUNT(DISTINCT biz_id) AS d30_issue_cnt,
        COUNT(DISTINCT CASE 
            WHEN finish_day <= expect_day 
            AND fact_capital >= should_capital 
            AND fact_interest >= should_interest 
            THEN biz_id 
        END) AS d30_repayment_cnt,
        SUM(contract_amount) AS d30_contract_amount,
        SUM(should_capital + should_interest) AS d30_should_repay_amount,
        SUM(fact_capital + fact_interest) AS d30_fact_repay_amount
    FROM issue_stats
    WHERE biz_id IS NOT NULL
    GROUP BY reg_month
),

spend AS (
   select 
      date(date_trunc('month', ad_date)) AS spend_month,

       sum(spend_usd_discount) as spend
       from ind.tyn_ads_cost_discount a
       where ad_date >= date'2024-01-01'
       group by 1  
) ,


install as (
    SELECT  
    date(date_trunc('month', event_time + INTERVAL '7' HOUR)) as install_month,
    COUNT(DISTINCT appsflyer_id) AS install_cnt
    FROM ods.s08_appsflyer_push_data
    WHERE  etl_date>='20240101' and event_name='install' 
    and date(event_time + INTERVAL '7' HOUR) >= date'2024-01-01'
    GROUP BY 1
),
exchange_rate_cost AS (
select date(date_format(date_parse(month_id, '%Y%m'), '%Y-%m-%d')) AS exchange_month ,

exchange_rate_to_dollar,
exchange_rate_to_cny, 
ROUND(exchange_rate_to_dollar *1.0000 / exchange_rate_to_cny, 4) AS exchange_rate_dollar_to_cny
from dim.dim_exchange_rate_cost
where account_currency='IDR'
) 

    SELECT 
        ubs.reg_month,
        i.install_cnt,
        ubs.reg_users,
        ubs.d30_app_users,
        ubs.d30_in_confirm_users,
        -- ubs.d30_confirm_users,
        ubs.d30_issue_users,
        ROUND(ubs.d30_app_users *1.0000 / ubs.reg_users, 4) AS app_to_reg_conversion_rate,
        ROUND(ubs.d30_in_confirm_users * 1.0000 / ubs.d30_app_users, 4) AS in_confirm_to_app_conversion_rate,
        ROUND(ubs.d30_issue_users * 1.0000/ ubs.d30_in_confirm_users, 4) AS issue_to_in_confirm_conversion_rate,
        ROUND(ubs.d30_issue_users * 1.0000/ ubs.d30_confirm_users, 4) AS issue_to_confirm_conversion_rate,
        ROUND(ubs.d30_issue_users * 1.0000/ ubs.reg_users, 4) AS issue_to_reg_conversion_rate,
        COALESCE(s.spend, 0) AS spend,
        COALESCE(erc.exchange_rate_dollar_to_cny, 0) AS exchange_rate_dollar_to_cny,
        '' AS spend_type,
        ROUND(s.spend * 1.0000/ ubs.d30_in_confirm_users, 4) AS cpk,
        ROUND(s.spend * 1.0000/ ubs.d30_issue_users, 4) AS cps,


        COALESCE(trs.d30_issue_cnt, 0) AS d30_issue_cnt,
        COALESCE(trs.d30_repayment_cnt, 0) AS d30_repayment_cnt,
        ROUND((trs.d30_issue_cnt- trs.d30_repayment_cnt) * 1.0000/ trs.d30_issue_cnt, 4) AS d30_due_cnt,

        COALESCE(trs.d30_contract_amount, 0) AS d30_contract_amount,
        COALESCE(trs.d30_should_repay_amount, 0) AS d30_should_repay_amount,
        COALESCE(trs.d30_fact_repay_amount, 0) AS d30_fact_repay_amount,
        ROUND((trs.d30_should_repay_amount-trs.d30_contract_amount)/trs.d30_contract_amount,4) AS d30_dingjia_rate,
        ROUND((trs.d30_should_repay_amount - trs.d30_fact_repay_amount) * 1.0000 / trs.d30_contract_amount, 4) AS d30_amount_overdue_rate,
        COALESCE(erc.exchange_rate_to_cny, 0) AS exchange_rate_to_cny,
        ROUND(trs.d30_contract_amount * 1.0000 /trs.d30_issue_cnt *erc.exchange_rate_to_cny, 4) AS d30_avg_amt_cny
 
    FROM user_behavior_stats ubs
    LEFT JOIN issue_repayment_stats trs 
        ON ubs.reg_month = trs.reg_month
    LEFT JOIN spend s 
        ON ubs.reg_month = s.spend_month
    LEFT JOIN exchange_rate_cost erc 
        ON ubs.reg_month = erc.exchange_month
    LEFT JOIN install i
        ON ubs.reg_month = i.install_month
 ;





-- 1业务数据尽调模板（放款报表）成本没提供；

WITH monthly_stats AS (
    SELECT 
        date(issue_month) as issue_month,
        COUNT(DISTINCT CASE WHEN if_issue = 1 THEN mid END) AS user_cnt,
        COUNT(DISTINCT CASE WHEN if_issue = 1 THEN biz_id END) AS issue_cnt,
        SUM(CASE WHEN if_issue = 1 THEN contract_amount ELSE 0 END) AS issue_amt
     FROM ind.ba_asset_base_info
    WHERE  if_issue = 1
    GROUP BY 1
),

exchange_rate_cost AS (
select date(date_format(date_parse(month_id, '%Y%m'), '%Y-%m-%d')) AS exchange_month ,
exchange_rate_to_dollar,
exchange_rate_to_cny, 
ROUND(exchange_rate_to_dollar *1.0000 / exchange_rate_to_cny, 4) AS exchange_rate_dollar_to_cny
from dim.dim_exchange_rate_cost
where account_currency='IDR'
) 

SELECT 
    issue_month,
    user_cnt,
    issue_cnt,
    issue_amt,
    exchange_rate_to_cny,
    issue_amt/exchange_rate_to_cny AS issue_amt_cny,
    issue_amt/(issue_cnt*exchange_rate_to_cny) AS issue_avg_amt_cny,
    issue_amt/(user_cnt*exchange_rate_to_cny) AS issue_user_avg_amt_cny 
FROM monthly_stats ms
LEFT JOIN exchange_rate_cost erc 
        ON ms.issue_month = erc.exchange_month
ORDER BY issue_month DESC;







-- 1业务数据尽调模板（还款报表）
-- 注意：1、是按照每期的数据进行计算的
-- 2、如果单期中有还款实际>到期实际（即已到期还款）但是还款金额<应还金额的，视为未还清即已到期未还；为计算逾期天数，因此取当前时间作为还款时间；
 
WITH total_collect_due AS (
    SELECT 
        DATE_FORMAT(expect_day, '%Y-%m-01') AS expect_month,
        COUNT(DISTINCT customer_id) AS due_users,
        COUNT(DISTINCT camera_id) AS due_cnt,
        SUM(should_capital) AS due_amt,
        SUM(should_capital + should_interest + should_fine) AS due_amt_interest,
        SUM(fact_capital + fact_interest + fact_fine) AS fact_amt_interest,
        SUM(should_interest) AS should_interest,
        SUM(should_fine) AS should_fine,
        SUM(should_capital + should_interest + should_fine) - SUM(fact_capital + fact_interest + fact_fine) AS onloan_amount,
        SUM(CASE WHEN DATE_DIFF('day', expect_day,finish_day) > 0 THEN should_capital ELSE 0 END) AS d0_rucui,
        SUM(CASE WHEN DATE_DIFF('day', expect_day,finish_day) > 3 THEN should_capital ELSE 0 END) AS d3_rucui,
        SUM(CASE WHEN DATE_DIFF('day', expect_day,finish_day) > 7 THEN should_capital ELSE 0 END) AS d7_rucui,
        SUM(CASE WHEN DATE_DIFF('day', expect_day,finish_day) > 30 THEN should_capital ELSE 0 END) AS d30_rucui,
        SUM(CASE WHEN DATE_DIFF('day', expect_day,finish_day) > 60 THEN should_capital ELSE 0 END) AS d60_rucui,
        SUM(CASE WHEN DATE_DIFF('day', expect_day,finish_day) > 90 THEN should_capital ELSE 0 END) AS d90_rucui,
        SUM(CASE WHEN finish_day > expect_day AND DATE_DIFF('day', expect_day,finish_day) <= 0 THEN fact_capital ELSE 0 END) AS d0_huishou,
        SUM(CASE WHEN finish_day > expect_day AND DATE_DIFF('day', expect_day,finish_day) <= 3 THEN fact_capital ELSE 0 END) AS d3_huishou,
        SUM(CASE WHEN finish_day > expect_day AND DATE_DIFF('day', expect_day,finish_day) <= 7 THEN fact_capital ELSE 0 END) AS d7_huishou,
        SUM(CASE WHEN finish_day > expect_day AND DATE_DIFF('day', expect_day,finish_day) <= 30 THEN fact_capital ELSE 0 END) AS d30_huishou,
        SUM(CASE WHEN finish_day > expect_day AND DATE_DIFF('day', expect_day,finish_day) <= 60 THEN fact_capital ELSE 0 END) AS d60_huishou,
        SUM(CASE WHEN finish_day > expect_day AND DATE_DIFF('day', expect_day,finish_day) <= 90 THEN fact_capital ELSE 0 END) AS d90_huishou,
        SUM(CASE WHEN finish_day > expect_day THEN fact_capital ELSE 0 END) AS all_huishou
    FROM (
        SELECT 
             customer_id,
            camera_id,
            indexs,
            b.should_time AS expect_day,
            DATE(CASE 
                WHEN b.fact_time IS NULL 
                    OR (b.fact_time > b.should_time AND should_capital > fact_capital) 
                THEN CURRENT_DATE 
                ELSE b.fact_time 
            END) AS finish_day,
            should_capital,
            fact_capital,
            should_interest,
            fact_interest,
            should_fine,
            fact_fine
        FROM ods.s02_loan_repayment b
        -- where customer_id =1040160075870110.000000 
        -- GROUP BY 1, 2,3
    ) t
    GROUP BY 1
)

SELECT 
    expect_month,
    sum(due_users) AS due_users,
    sum(due_cnt) AS due_cnt,
    SUM(due_amt) AS due_amt,
    SUM(due_amt_interest) AS due_amt_interest,
    SUM(fact_amt_interest) AS fact_amt_interest,
    SUM(due_amt_interest) - SUM(fact_amt_interest) AS due_amt_interest_diff,
    '' AS zhifu,

    
    SUM(d0_rucui)  * 1.0000 / SUM(due_amt) AS d0_rucui_rate,
    SUM(d3_rucui) * 1.0000 / SUM(due_amt) AS d3_rucui_rate,
    SUM(d7_rucui) * 1.0000 / SUM(due_amt) AS d7_rucui_rate,
    SUM(d30_rucui) * 1.0000 / SUM(due_amt) AS d30_rucui_rate,
    SUM(d60_rucui) * 1.0000 / SUM(due_amt) AS d60_rucui_rate,
    SUM(d90_rucui) * 1.0000 / SUM(due_amt) AS d90_rucui_rate,
    SUM(d0_rucui) as d0_rucui,
    sum(all_huishou-d0_huishou) as all_huishou_amt,
    SUM(d0_rucui) * 1.0000 / SUM(due_amt) AS rucui_rate,
    case when SUM(d0_rucui)=0 then 0 else  (SUM(d3_huishou - d0_huishou)) * 1.0000 / SUM(d0_rucui) end AS d3_huishou_rate,
    case when SUM(d0_rucui)=0 then 0 else  (SUM(d7_huishou - d0_huishou)) * 1.0000 / SUM(d0_rucui) end AS d7_huishou_rate,
    case when SUM(d0_rucui)=0 then 0 else  (SUM(d30_huishou - d0_huishou)) * 1.0000 / SUM(d0_rucui) end AS d30_huishou_rate,
    case when SUM(d0_rucui)=0 then 0 else  (SUM(d60_huishou - d0_huishou)) * 1.0000 / SUM(d0_rucui) end AS d60_huishou_rate,
    case when SUM(d0_rucui)=0 then 0 else  (SUM(d90_huishou - d0_huishou)) * 1.0000 / SUM(d0_rucui) end AS d90_huishou_rate,
    SUM(should_interest) AS should_interest,
    '' AS zhanqishouxufei,
    SUM(should_fine) AS should_fine,
    '' AS qitashouru,
    '' AS cuishouchengben
FROM total_collect_due

GROUP BY 1
ORDER BY 1






 














 -- 业务数据表（三、规模）
 
with issue_month as (

SELECT issue_month, 
 case when product_tag='R' then 'dengben' else 'kedou' end as product_tag,
SUM(if_issue) AS loan_cnt_all, 
SUM(contract_amount_usd1) AS loan_amt_all, 
SUM(CASE WHEN grant_strategy = 'NEW' THEN if_issue ELSE 0 END) AS loan_cnt_new, 
SUM(CASE WHEN grant_strategy = 'NEW' THEN contract_amount_usd1 ELSE 0 END) AS loan_amt_new,
SUM(CASE WHEN grant_strategy = 'OLD' THEN if_issue ELSE 0 END) AS loan_cnt_old, 
SUM(CASE WHEN grant_strategy = 'OLD' THEN contract_amount_usd1 ELSE 0 END) AS loan_amt_old 
 FROM ind.ba_asset_base_info 
 WHERE issue_month >= '2024-01-01' and if_issue = 1 
GROUP BY 1,2) 

select issue_month,
product_tag,
loan_cnt_all,
loan_amt_all,
case when loan_cnt_all>0 then loan_amt_all*1.000000/loan_cnt_all else 0 end AS avg_loan_amt_all,
loan_cnt_new,
loan_amt_new,
case when loan_cnt_new>0 then loan_amt_new*1.000000/loan_cnt_new else 0 end AS avg_loan_amt_new,
loan_cnt_old,
loan_amt_old,
case when loan_cnt_old>0 then loan_amt_old*1.000000/loan_cnt_old else 0 end AS avg_loan_amt_old
from issue_month
order by issue_month, product_tag
;















-- 业务数据表（四、用户增长）
WITH spend AS (
    SELECT 
        DATE(date_trunc('month', ad_date)) AS spend_month,
        SUM(spend_usd_discount) AS spend
    FROM ind.tyn_ads_cost_discount a
    WHERE ad_date >= DATE '2024-01-01'
    GROUP BY 1
),

app_monthly_stats AS (
    SELECT 
        DATE(b.app_month) AS app_month,
        COUNT(DISTINCT biz_id) AS app_cnt,
        COUNT(DISTINCT CASE WHEN if_in_confirm = 1 THEN biz_id END) AS app_cnt_in_confirm
    FROM ind.ba_asset_base_info b
    WHERE b.if_app = 1
        AND b.grant_strategy = 'NEW'
        AND b.app_date >= '2024-01-01'
    GROUP BY 1
),

issue_monthly_stats AS (
    SELECT 
        DATE(b.issue_month) AS issue_month,
        COUNT(DISTINCT biz_id) AS issue_cnt
    FROM ind.ba_asset_base_info b
    WHERE b.if_issue = 1
        AND b.grant_strategy = 'NEW'
        AND b.issue_date >= '2024-01-01'
    GROUP BY 1
),

install_cnt AS (
    SELECT 
        DATE(date_trunc('month', event_time + INTERVAL '7' HOUR)) AS install_month,
        COUNT(DISTINCT appsflyer_id) AS install_cnt
    FROM ods.s08_appsflyer_push_data
    WHERE etl_date >= '20240101'
        AND event_name = 'install'
        AND DATE(event_time + INTERVAL '7' HOUR) >= DATE '2024-01-01'
    GROUP BY 1
)

SELECT
    COALESCE(spend_month, install_month, app_month, issue_month) AS stata_month,
    COALESCE(a.spend, 0) AS spend,
    COALESCE(b.install_cnt, 0) AS install_cnt,
    COALESCE(c.app_cnt, 0) AS app_cnt,
    COALESCE(c.app_cnt_in_confirm, 0) AS app_cnt_in_confirm,
    COALESCE(e.issue_cnt, 0) AS issue_cnt,
    COALESCE(a.spend / e.issue_cnt, 0) AS cps
FROM spend a
FULL OUTER JOIN install_cnt b ON a.spend_month = b.install_month
FULL OUTER JOIN app_monthly_stats c ON a.spend_month = c.app_month
FULL OUTER JOIN issue_monthly_stats e ON a.spend_month = e.issue_month











-- 业务数据表（五、风险指标）
WITH total_collect_due AS (
    SELECT 
        DATE_FORMAT(expect_day, '%Y-%m-01') AS expect_month,
        product_tag,
        COUNT(DISTINCT camera_id) AS due_cnt,
        COUNT(DISTINCT CASE WHEN grant_strategy = 'NEW' THEN camera_id END) AS new_due_cnt,
        COUNT(DISTINCT CASE WHEN grant_strategy = 'OLD' THEN camera_id END) AS old_due_cnt,
        SUM(should_capital + should_interest) AS due_amt,
        SUM(CASE WHEN grant_strategy = 'NEW' THEN should_capital + should_interest ELSE 0 END) AS new_due_amt,
        SUM(CASE WHEN grant_strategy = 'OLD' THEN should_capital + should_interest ELSE 0 END) AS old_due_amt,
        COUNT(DISTINCT CASE WHEN DATE_DIFF('day', expect_day, finish_day) > 0 THEN camera_id END) AS d0_cnt,
        SUM(CASE WHEN DATE_DIFF('day', expect_day, finish_day) > 0 THEN should_capital + should_interest ELSE 0 END) AS d0_amt_rucui,
        COUNT(DISTINCT CASE WHEN grant_strategy = 'NEW' AND DATE_DIFF('day', expect_day, finish_day) > 0 THEN camera_id END) AS new_d0_cnt,
        SUM(CASE WHEN grant_strategy = 'NEW' AND DATE_DIFF('day', expect_day, finish_day) > 0 THEN should_capital + should_interest ELSE 0 END) AS new_d0_amt_rucui,
        COUNT(DISTINCT CASE WHEN grant_strategy = 'OLD' AND DATE_DIFF('day', expect_day, finish_day) > 0 THEN camera_id END) AS old_d0_cnt,
        SUM(CASE WHEN grant_strategy = 'OLD' AND DATE_DIFF('day', expect_day, finish_day) > 0 THEN should_capital + should_interest ELSE 0 END) AS old_d0_amt_rucui
    FROM (
        SELECT   
            b.camera_id,
            CASE WHEN a.product_tag = 'R' THEN 'dengben' ELSE 'kedou' END AS product_tag,
            a.grant_strategy,
            b.should_time AS expect_day,
            DATE(CASE 
                WHEN b.fact_time IS NULL 
                    OR (b.fact_time > b.should_time AND b.should_capital > b.fact_capital) 
                THEN CURRENT_DATE 
                ELSE b.fact_time 
            END) AS finish_day,
            b.should_capital,
            b.fact_capital,
            b.should_interest,
            b.fact_interest,
            b.should_fine,
            b.fact_fine
        FROM ods.s02_loan_repayment b
        LEFT JOIN ind.ba_asset_base_info a 
            ON TRY_CAST(a.biz_id AS BIGINT) = TRY_CAST(b.camera_id AS BIGINT)
    ) t
    GROUP BY 1, 2
)

SELECT 
    expect_month,
    product_tag,
    SUM(due_cnt) AS due_cnt,
    CASE 
        WHEN SUM(due_cnt) = 0 THEN 0 
        ELSE SUM(d0_cnt) * 1.0000 / SUM(due_cnt) 
    END AS d0_cnt_rate,
    CASE 
        WHEN SUM(new_due_cnt) = 0 THEN 0 
        ELSE SUM(new_d0_cnt) * 1.0000 / SUM(new_due_cnt) 
    END AS new_d0_cnt_rate,
    CASE 
        WHEN SUM(old_due_cnt) = 0 THEN 0 
        ELSE SUM(old_d0_cnt) * 1.0000 / SUM(old_due_cnt) 
    END AS old_d0_cnt_rate,
    CASE 
        WHEN SUM(due_amt) = 0 THEN 0 
        ELSE SUM(d0_amt_rucui) * 1.0000 / SUM(due_amt) 
    END AS d0_amt_rucui_rate,
    CASE 
        WHEN SUM(new_due_amt) = 0 THEN 0 
        ELSE SUM(new_d0_amt_rucui) * 1.0000 / SUM(new_due_amt) 
    END AS new_d0_amt_rucui_rate,
    CASE 
        WHEN SUM(old_due_amt) = 0 THEN 0 
        ELSE SUM(old_d0_amt_rucui) * 1.0000 / SUM(old_due_amt) 
    END AS old_d0_amt_rucui_rate
FROM total_collect_due
GROUP BY 1, 2
ORDER BY 1, 2
 








-- 业务数据表（六、关键效率)


WITH  
reg_users AS (
    SELECT  
        date(date_trunc('month', reg_dt)) AS reg_month,
        count(distinct mid ) as reg_user_cnt
    FROM ind.tyn_reg_install_new
    WHERE reg_dt >= DATE '2024-01-01'
    GROUP BY 1
),

app_stats AS (
    SELECT  
        date(app_month) as app_month, 
        count(distinct case when grant_strategy='NEW' and if_app=1 then  mid else null end) AS new_app_user_cnt, 
        count(distinct case when grant_strategy='OLD' and if_app=1 then  mid else null end) AS old_app_user_cnt, 

        count(distinct case when grant_strategy='NEW' and if_in_confirm_temp=1 then  mid else null end) AS new_inconfirm_user_cnt,
        count(distinct case when grant_strategy='NEW' and if_confirm_passed_final=1 then  mid else null end) AS new_confirm_user_cnt,
        count(distinct case when grant_strategy='OLD' and if_in_confirm_temp=1 then  mid else null end) AS old_inconfirm_user_cnt  
    FROM ind.ba_asset_base_info
    WHERE date(app_date) >= DATE('2024-01-01')  
    AND date(app_date) < CURRENT_DATE
    AND if_app = 1
    GROUP BY 1 
),

t0_fujie as (
  SELECT
    date(repay_month) as repay_month,
    COUNT(customer_id) AS repay_cnt,
    COUNT(mid) AS apply_cnt,
    COUNT(mid) * 1.0000 / COUNT(customer_id) AS repay_apply_rate
FROM (
    SELECT customer_id, DATE(create_time) AS repay_date, 
        DATE_TRUNC('month', create_time) AS repay_month

    FROM ods.s02_loan_repayment_detail
    GROUP BY 1, 2, 3
) a
LEFT JOIN (
    SELECT mid, create_date, create_month
    FROM ind.ba_asset_base_info
    WHERE if_recall = 0 AND grant_strategy = 'OLD'
    GROUP BY 1, 2, 3
) b ON CAST(b.mid AS BIGINT) = CAST(a.customer_id AS BIGINT) AND a.repay_date = b.create_date
WHERE repay_date >= DATE '2024-01-01'
GROUP BY 1
)


select 
new_app_user_cnt*1.0000/reg_user_cnt as app_reg_rate,
new_inconfirm_user_cnt*1.0000/new_app_user_cnt as new_inconfirm_app_rate,
new_confirm_user_cnt*1.0000/new_inconfirm_user_cnt as confirm_inconfirm_rate,
old_inconfirm_user_cnt*1.0000/old_app_user_cnt as old_inconfirm_app_rate,
repay_apply_rate
 from reg_users 
left join app_stats on reg_users.reg_month=app_stats.app_month
left join t0_fujie on reg_users.reg_month=t0_fujie.repay_month
order by 1