-- ================================================
-- MySQL数据库查询文件
-- 数据库: YSProd
-- 主机: 47.121.121.48:3306
-- 用户: yuesong
-- 生成时间: 2026-05-03
-- ================================================

-- ================================================
-- 一、基础查询
-- ================================================

-- 1. 查看所有表
SHOW TABLES;

-- 2. 查看时间维度表数据
SELECT * FROM dim_time LIMIT 20;

-- 3. 查看产品维度表数据
SELECT * FROM dim_product;

-- 4. 查看客户维度表前20条数据
SELECT customer_id, customer_code, customer_name, age, gender, education, city, credit_score 
FROM dim_customer 
LIMIT 20;

-- 5. 查看地域维度表数据
SELECT * FROM dim_location;

-- 6. 查看机构维度表数据
SELECT * FROM dim_organization;

-- 7. 查看贷款申请事实表前10条
SELECT * FROM fct_loan_application LIMIT 10;

-- 8. 查看贷款发放事实表前10条
SELECT * FROM fct_loan_disbursement LIMIT 10;

-- 9. 查看各表结构
DESCRIBE dim_time;
DESCRIBE dim_product;
DESCRIBE dim_customer;
DESCRIBE dim_location;
DESCRIBE dim_organization;
DESCRIBE fct_loan_application;
DESCRIBE fct_loan_disbursement;

-- ================================================
-- 二、维度表查询
-- ================================================

-- 10. 按风险等级统计客户数量
SELECT 
    risk_level, 
    COUNT(*) as customer_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM dim_customer), 2) as percentage
FROM dim_customer
GROUP BY risk_level
ORDER BY customer_count DESC;

-- 11. 按客户等级统计客户分布
SELECT 
    customer_level, 
    COUNT(*) as customer_count,
    AVG(credit_score) as avg_credit_score,
    MIN(credit_score) as min_credit_score,
    MAX(credit_score) as max_credit_score
FROM dim_customer
GROUP BY customer_level
ORDER BY avg_credit_score DESC;

-- 12. 按教育程度统计客户情况
SELECT 
    education,
    COUNT(*) as customer_count,
    AVG(annual_income) as avg_annual_income,
    AVG(credit_score) as avg_credit_score
FROM dim_customer
GROUP BY education
ORDER BY customer_count DESC;

-- 13. 按城市统计客户分布（关联地域维度表）
SELECT 
    l.province,
    l.city,
    l.city_level,
    COUNT(c.customer_id) as customer_count,
    AVG(c.credit_score) as avg_credit_score,
    l.population,
    l.gdp
FROM dim_customer c
JOIN dim_location l ON c.city = l.city
GROUP BY l.province, l.city, l.city_level, l.population, l.gdp
ORDER BY customer_count DESC;

-- 14. 按年龄区间统计客户
SELECT 
    CASE 
        WHEN age < 25 THEN '20-24'
        WHEN age < 30 THEN '25-29'
        WHEN age < 35 THEN '30-34'
        WHEN age < 40 THEN '35-39'
        WHEN age < 45 THEN '40-44'
        WHEN age < 50 THEN '45-49'
        ELSE '50+' 
    END as age_group,
    COUNT(*) as customer_count,
    AVG(credit_score) as avg_credit_score,
    AVG(annual_income) as avg_annual_income
FROM dim_customer
GROUP BY age_group
ORDER BY age_group;

-- 15. 产品维度表信息汇总
SELECT 
    product_code,
    product_name,
    product_category,
    risk_level,
    interest_rate * 100 as interest_rate_pct,
    min_loan_amount,
    max_loan_amount,
    min_loan_cycle,
    max_loan_cycle,
    loan_currency,
    status
FROM dim_product
ORDER BY risk_level;

-- ================================================
-- 三、贷款申请分析查询
-- ================================================

-- 16. 按产品统计贷款申请情况
SELECT 
    p.product_code,
    p.product_name,
    COUNT(*) as total_applications,
    SUM(CASE WHEN a.application_status = 'approved' THEN 1 ELSE 0 END) as approved_count,
    SUM(CASE WHEN a.application_status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
    SUM(CASE WHEN a.application_status = 'pending' THEN 1 ELSE 0 END) as pending_count,
    ROUND(SUM(CASE WHEN a.application_status = 'approved' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as approval_rate,
    AVG(a.apply_amount) as avg_apply_amount,
    AVG(a.credit_score) as avg_credit_score
FROM fct_loan_application a
JOIN dim_product p ON a.product_id = p.product_id
GROUP BY p.product_code, p.product_name
ORDER BY total_applications DESC;

-- 17. 按月份统计贷款申请趋势
SELECT 
    t.year_num,
    t.month_num,
    t.month_name,
    COUNT(*) as application_count,
    SUM(a.apply_amount) as total_apply_amount,
    AVG(a.apply_amount) as avg_apply_amount,
    ROUND(COUNT(CASE WHEN a.application_status = 'approved' THEN 1 END) * 100.0 / COUNT(*), 2) as approval_rate
FROM fct_loan_application a
JOIN dim_time t ON a.time_id = t.time_id
GROUP BY t.year_num, t.month_num, t.month_name
ORDER BY t.year_num, t.month_num;

-- 18. 按机构统计贷款申请情况
SELECT 
    o.org_code,
    o.org_name,
    o.city,
    COUNT(*) as application_count,
    SUM(a.apply_amount) as total_apply_amount,
    AVG(a.apply_amount) as avg_apply_amount,
    AVG(a.credit_score) as avg_credit_score
FROM fct_loan_application a
JOIN dim_organization o ON a.org_id = o.org_id
GROUP BY o.org_code, o.org_name, o.city
ORDER BY application_count DESC;

-- 19. 查看申请被拒原因分析
SELECT 
    reject_reason,
    COUNT(*) as reject_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fct_loan_application WHERE application_status = 'rejected'), 2) as reject_percentage,
    AVG(credit_score) as avg_credit_score_of_rejected
FROM fct_loan_application
WHERE application_status = 'rejected'
  AND reject_reason IS NOT NULL
GROUP BY reject_reason
ORDER BY reject_count DESC;

-- 20. 按信用评分区间分析申请通过率
SELECT 
    CASE 
        WHEN credit_score < 500 THEN '300-499'
        WHEN credit_score < 600 THEN '500-599'
        WHEN credit_score < 700 THEN '600-699'
        WHEN credit_score < 800 THEN '700-799'
        ELSE '800-850' 
    END as credit_score_group,
    COUNT(*) as total_applications,
    SUM(CASE WHEN application_status = 'approved' THEN 1 ELSE 0 END) as approved_count,
    ROUND(SUM(CASE WHEN application_status = 'approved' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as approval_rate,
    AVG(apply_amount) as avg_apply_amount
FROM fct_loan_application
GROUP BY credit_score_group
ORDER BY credit_score_group;

-- ================================================
-- 四、贷款发放分析查询
-- ================================================

-- 21. 按产品统计贷款发放情况
SELECT 
    p.product_code,
    p.product_name,
    p.risk_level,
    COUNT(*) as disbursement_count,
    SUM(d.loan_amount) as total_loan_amount,
    AVG(d.loan_amount) as avg_loan_amount,
    AVG(d.interest_rate * 100) as avg_interest_rate_pct,
    SUM(d.contract_amount) as total_contract_amount,
    SUM(d.haircut_amount) as total_haircut_amount,
    SUM(d.net_amount) as total_net_amount,
    SUM(d.service_fee) as total_service_fee
FROM fct_loan_disbursement d
JOIN dim_product p ON d.product_id = p.product_id
GROUP BY p.product_code, p.product_name, p.risk_level
ORDER BY total_loan_amount DESC;

-- 22. 按月份统计贷款发放趋势
SELECT 
    t.year_num,
    t.month_num,
    t.month_name,
    COUNT(*) as disbursement_count,
    SUM(d.loan_amount) as total_loan_amount,
    AVG(d.loan_amount) as avg_loan_amount,
    AVG(d.interest_rate * 100) as avg_interest_rate_pct,
    SUM(d.haircut_amount) as total_haircut_amount,
    SUM(d.net_amount) as total_net_amount
FROM fct_loan_disbursement d
JOIN dim_time t ON d.time_id = t.time_id
GROUP BY t.year_num, t.month_num, t.month_name
ORDER BY t.year_num, t.month_num;

-- 23. 按地域统计贷款发放情况
SELECT 
    l.province,
    l.city,
    l.city_level,
    COUNT(*) as disbursement_count,
    SUM(d.loan_amount) as total_loan_amount,
    AVG(d.loan_amount) as avg_loan_amount,
    AVG(d.interest_rate * 100) as avg_interest_rate_pct
FROM fct_loan_disbursement d
JOIN dim_location l ON d.location_id = l.location_id
GROUP BY l.province, l.city, l.city_level
ORDER BY total_loan_amount DESC;

-- 24. 按贷款周期统计贷款发放情况
SELECT 
    loan_cycle,
    COUNT(*) as disbursement_count,
    SUM(loan_amount) as total_loan_amount,
    AVG(loan_amount) as avg_loan_amount,
    AVG(interest_rate * 100) as avg_interest_rate_pct
FROM fct_loan_disbursement
GROUP BY loan_cycle
ORDER BY loan_cycle;

-- 25. 贷款发放金额区间分析
SELECT 
    CASE 
        WHEN loan_amount < 10000 THEN '0-10K'
        WHEN loan_amount < 20000 THEN '10K-20K'
        WHEN loan_amount < 30000 THEN '20K-30K'
        WHEN loan_amount < 50000 THEN '30K-50K'
        WHEN loan_amount < 80000 THEN '50K-80K'
        ELSE '80K-100K' 
    END as loan_amount_group,
    COUNT(*) as disbursement_count,
    SUM(loan_amount) as total_loan_amount,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fct_loan_disbursement), 2) as percentage
FROM fct_loan_disbursement
GROUP BY loan_amount_group
ORDER BY loan_amount_group;

-- ================================================
-- 五、客户综合分析查询
-- ================================================

-- 26. 客户贷款申请与发放汇总（关联申请和发放表）
SELECT 
    c.customer_id,
    c.customer_code,
    c.customer_name,
    c.credit_score,
    c.risk_level,
    c.customer_level,
    COUNT(DISTINCT a.application_id) as total_applications,
    COUNT(DISTINCT CASE WHEN a.application_status = 'approved' THEN a.application_id END) as approved_applications,
    COUNT(DISTINCT d.disbursement_id) as total_disbursements,
    SUM(DISTINCT d.loan_amount) as total_loan_amount
FROM dim_customer c
LEFT JOIN fct_loan_application a ON c.customer_id = a.customer_id
LEFT JOIN fct_loan_disbursement d ON c.customer_id = d.customer_id
GROUP BY c.customer_id, c.customer_code, c.customer_name, c.credit_score, c.risk_level, c.customer_level
ORDER BY total_loan_amount DESC
LIMIT 50;

-- 27. 按客户风险等级分析贷款发放
SELECT 
    c.risk_level,
    COUNT(DISTINCT c.customer_id) as customer_count,
    COUNT(d.disbursement_id) as disbursement_count,
    SUM(d.loan_amount) as total_loan_amount,
    AVG(d.loan_amount) as avg_loan_amount,
    AVG(d.interest_rate * 100) as avg_interest_rate_pct
FROM dim_customer c
JOIN fct_loan_disbursement d ON c.customer_id = d.customer_id
GROUP BY c.risk_level
ORDER BY total_loan_amount DESC;

-- 28. VIP客户分析
SELECT 
    'VIP客户' as customer_category,
    COUNT(*) as customer_count,
    AVG(credit_score) as avg_credit_score,
    AVG(annual_income) as avg_annual_income,
    COUNT(DISTINCT a.application_id) as total_applications,
    COUNT(DISTINCT d.disbursement_id) as total_disbursements,
    SUM(d.loan_amount) as total_loan_amount
FROM dim_customer c
LEFT JOIN fct_loan_application a ON c.customer_id = a.customer_id
LEFT JOIN fct_loan_disbursement d ON c.customer_id = d.customer_id
WHERE c.customer_level = 'VIP'

UNION ALL

SELECT 
    '普通客户' as customer_category,
    COUNT(*) as customer_count,
    AVG(credit_score) as avg_credit_score,
    AVG(annual_income) as avg_annual_income,
    COUNT(DISTINCT a.application_id) as total_applications,
    COUNT(DISTINCT d.disbursement_id) as total_disbursements,
    SUM(d.loan_amount) as total_loan_amount
FROM dim_customer c
LEFT JOIN fct_loan_application a ON c.customer_id = a.customer_id
LEFT JOIN fct_loan_disbursement d ON c.customer_id = d.customer_id
WHERE c.customer_level = 'Regular'

UNION ALL

SELECT 
    '新客户' as customer_category,
    COUNT(*) as customer_count,
    AVG(credit_score) as avg_credit_score,
    AVG(annual_income) as avg_annual_income,
    COUNT(DISTINCT a.application_id) as total_applications,
    COUNT(DISTINCT d.disbursement_id) as total_disbursements,
    SUM(d.loan_amount) as total_loan_amount
FROM dim_customer c
LEFT JOIN fct_loan_application a ON c.customer_id = a.customer_id
LEFT JOIN fct_loan_disbursement d ON c.customer_id = d.customer_id
WHERE c.customer_level = 'New';

-- ================================================
-- 六、综合分析报表查询
-- ================================================

-- 29. 按季度综合分析报表
SELECT 
    t.year_num,
    t.quarter_num,
    COUNT(DISTINCT a.application_id) as total_applications,
    COUNT(DISTINCT CASE WHEN a.application_status = 'approved' THEN a.application_id END) as approved_applications,
    ROUND(COUNT(DISTINCT CASE WHEN a.application_status = 'approved' THEN a.application_id END) * 100.0 / 
          COUNT(DISTINCT a.application_id), 2) as approval_rate,
    COUNT(DISTINCT d.disbursement_id) as total_disbursements,
    SUM(d.loan_amount) as total_loan_amount,
    SUM(d.haircut_amount) as total_haircut_amount,
    SUM(d.service_fee) as total_service_fee,
    SUM(d.net_amount) as total_net_amount
FROM dim_time t
LEFT JOIN fct_loan_application a ON t.time_id = a.time_id
LEFT JOIN fct_loan_disbursement d ON t.time_id = d.time_id
GROUP BY t.year_num, t.quarter_num
ORDER BY t.year_num, t.quarter_num;

-- 30. 产品+月份交叉分析报表
SELECT 
    p.product_name,
    t.year_num,
    t.month_num,
    t.month_name,
    COUNT(DISTINCT d.disbursement_id) as disbursement_count,
    SUM(d.loan_amount) as total_loan_amount,
    AVG(d.loan_amount) as avg_loan_amount,
    AVG(d.interest_rate * 100) as avg_interest_rate_pct
FROM fct_loan_disbursement d
JOIN dim_product p ON d.product_id = p.product_id
JOIN dim_time t ON d.time_id = t.time_id
GROUP BY p.product_name, t.year_num, t.month_num, t.month_name
ORDER BY t.year_num, t.month_num, p.product_name;

-- 31. 机构综合业绩分析
SELECT 
    o.org_code,
    o.org_name,
    o.org_level,
    o.city,
    COUNT(DISTINCT a.application_id) as total_applications,
    COUNT(DISTINCT CASE WHEN a.application_status = 'approved' THEN a.application_id END) as approved_applications,
    ROUND(COUNT(DISTINCT CASE WHEN a.application_status = 'approved' THEN a.application_id END) * 100.0 / 
          COUNT(DISTINCT a.application_id), 2) as approval_rate,
    COUNT(DISTINCT d.disbursement_id) as total_disbursements,
    SUM(d.loan_amount) as total_loan_amount,
    AVG(d.loan_amount) as avg_loan_amount
FROM dim_organization o
LEFT JOIN fct_loan_application a ON o.org_id = a.org_id
LEFT JOIN fct_loan_disbursement d ON o.org_id = d.org_id
GROUP BY o.org_code, o.org_name, o.org_level, o.city
ORDER BY total_loan_amount DESC;

-- 32. 工作日 vs 周末分析
SELECT 
    CASE WHEN t.is_weekend = 1 THEN '周末' ELSE '工作日' END as day_type,
    COUNT(DISTINCT a.application_id) as total_applications,
    COUNT(DISTINCT d.disbursement_id) as total_disbursements,
    SUM(d.loan_amount) as total_loan_amount,
    AVG(d.loan_amount) as avg_loan_amount
FROM dim_time t
LEFT JOIN fct_loan_application a ON t.time_id = a.time_id
LEFT JOIN fct_loan_disbursement d ON t.time_id = d.time_id
GROUP BY CASE WHEN t.is_weekend = 1 THEN '周末' ELSE '工作日' END;

-- 33. 月末季末分析
SELECT 
    CASE 
        WHEN t.is_month_end = 1 AND t.is_quarter_end = 1 THEN '月末+季末'
        WHEN t.is_month_end = 1 THEN '月末'
        WHEN t.is_quarter_end = 1 THEN '季末'
        ELSE '常规日' 
    END as special_day,
    COUNT(DISTINCT a.application_id) as total_applications,
    COUNT(DISTINCT d.disbursement_id) as total_disbursements,
    SUM(d.loan_amount) as total_loan_amount
FROM dim_time t
LEFT JOIN fct_loan_application a ON t.time_id = a.time_id
LEFT JOIN fct_loan_disbursement d ON t.time_id = d.time_id
GROUP BY CASE 
        WHEN t.is_month_end = 1 AND t.is_quarter_end = 1 THEN '月末+季末'
        WHEN t.is_month_end = 1 THEN '月末'
        WHEN t.is_quarter_end = 1 THEN '季末'
        ELSE '常规日' 
    END
ORDER BY special_day;

-- ================================================
-- 七、数据质量检查查询
-- ================================================

-- 34. 检查各表数据量
SELECT 
    'dim_time' as table_name, COUNT(*) as record_count FROM dim_time
UNION ALL
SELECT 'dim_product', COUNT(*) FROM dim_product
UNION ALL
SELECT 'dim_customer', COUNT(*) FROM dim_customer
UNION ALL
SELECT 'dim_location', COUNT(*) FROM dim_location
UNION ALL
SELECT 'dim_organization', COUNT(*) FROM dim_organization
UNION ALL
SELECT 'fct_loan_application', COUNT(*) FROM fct_loan_application
UNION ALL
SELECT 'fct_loan_disbursement', COUNT(*) FROM fct_loan_disbursement;

-- 35. 检查无关联的贷款申请（无客户关联）
SELECT 
    COUNT(*) as orphan_application_count
FROM fct_loan_application
WHERE customer_id NOT IN (SELECT customer_id FROM dim_customer);

-- 36. 检查无关联的贷款发放（无客户关联）
SELECT 
    COUNT(*) as orphan_disbursement_count
FROM fct_loan_disbursement
WHERE customer_id NOT IN (SELECT customer_id FROM dim_customer);

-- 37. 检查信用评分异常值
SELECT 
    customer_id,
    customer_code,
    credit_score
FROM dim_customer
WHERE credit_score < 300 OR credit_score > 850;

-- 38. 检查贷款金额异常值
SELECT 
    disbursement_id,
    disbursement_no,
    loan_amount,
    min_loan_amount,
    max_loan_amount
FROM fct_loan_disbursement d
JOIN dim_product p ON d.product_id = p.product_id
WHERE d.loan_amount < p.min_loan_amount OR d.loan_amount > p.max_loan_amount;

-- ================================================
-- 八、快速统计查询
-- ================================================

-- 39. 快速查看今日（或指定日期）的业务情况
SELECT 
    t.date_value,
    COUNT(DISTINCT a.application_id) as application_count,
    COUNT(DISTINCT CASE WHEN a.application_status = 'approved' THEN a.application_id END) as approved_count,
    COUNT(DISTINCT d.disbursement_id) as disbursement_count,
    SUM(d.loan_amount) as total_loan_amount
FROM dim_time t
LEFT JOIN fct_loan_application a ON t.time_id = a.time_id
LEFT JOIN fct_loan_disbursement d ON t.time_id = d.time_id
WHERE t.date_value = '2024-06-15' -- 可修改为任意日期
GROUP BY t.date_value;

-- 40. 最新10笔贷款发放记录
SELECT 
    d.disbursement_id,
    d.disbursement_no,
    c.customer_name,
    p.product_name,
    d.loan_amount,
    d.loan_cycle,
    d.interest_rate * 100 as interest_rate_pct,
    d.disbursement_date,
    d.disbursement_status,
    d.loan_status
FROM fct_loan_disbursement d
JOIN dim_customer c ON d.customer_id = c.customer_id
JOIN dim_product p ON d.product_id = p.product_id
ORDER BY d.create_time DESC
LIMIT 10;

-- 41. 产品贷款发放排行榜
SELECT 
    p.product_name,
    COUNT(*) as disbursement_count,
    SUM(d.loan_amount) as total_loan_amount,
    AVG(d.loan_amount) as avg_loan_amount,
    RANK() OVER (ORDER BY SUM(d.loan_amount) DESC) as rank_by_amount,
    RANK() OVER (ORDER BY COUNT(*) DESC) as rank_by_count
FROM fct_loan_disbursement d
JOIN dim_product p ON d.product_id = p.product_id
GROUP BY p.product_name
ORDER BY total_loan_amount DESC;

-- 42. 客户贷款排名
SELECT 
    c.customer_id,
    c.customer_name,
    c.credit_score,
    COUNT(d.disbursement_id) as disbursement_count,
    SUM(d.loan_amount) as total_loan_amount,
    AVG(d.loan_amount) as avg_loan_amount
FROM dim_customer c
JOIN fct_loan_disbursement d ON c.customer_id = d.customer_id
GROUP BY c.customer_id, c.customer_name, c.credit_score
ORDER BY total_loan_amount DESC
LIMIT 20;
