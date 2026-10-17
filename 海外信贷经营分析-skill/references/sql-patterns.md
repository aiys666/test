# 高频 SQL 模式

> 海外信贷经营分析中最常用的 SQL 查询模板。基于 `ind.ba_asset_base_info` 等核心表。

## 一、月度放款汇总

```sql
SELECT
    issue_month,
    COUNT(DISTINCT mid) AS loan_customer_cnt,
    SUM(if_issue) AS loan_cnt,
    SUM(contract_amount_usd1) AS loan_amt_usd,
    SUM(contract_amount_usd1) / NULLIF(SUM(if_issue), 0) AS avg_loan_amt
FROM ind.ba_asset_base_info
WHERE issue_month >= '2025-01-01'
  AND if_issue = 1
GROUP BY 1
ORDER BY 1
```

### 按策略拆分 (NEW/OLD)

```sql
SELECT
    issue_month,
    grant_strategy,
    COUNT(DISTINCT mid) AS cust_cnt,
    SUM(if_issue) AS loan_cnt,
    SUM(contract_amount_usd1) AS loan_amt
FROM ind.ba_asset_base_info
WHERE issue_month >= '2025-01-01' AND if_issue = 1
GROUP BY 1, 2
ORDER BY 1, 2
```

## 二、进件漏斗转化

```sql
SELECT
    app_month,
    COUNT(DISTINCT CASE WHEN if_app=1 THEN mid END) AS app_users,
    COUNT(DISTINCT CASE WHEN if_in_confirm_temp=1 THEN mid END) AS in_confirm_users,
    COUNT(DISTINCT CASE WHEN if_confirm_passed_final=1 THEN mid END) AS confirm_users,
    COUNT(DISTINCT CASE WHEN if_issue=1 THEN mid END) AS issue_users,
    -- 转化率
    COUNT(DISTINCT CASE WHEN if_in_confirm_temp=1 THEN mid END) * 1.0
        / NULLIF(COUNT(DISTINCT CASE WHEN if_app=1 THEN mid END), 0) AS in_confirm_rate,
    COUNT(DISTINCT CASE WHEN if_confirm_passed_final=1 THEN mid END) * 1.0
        / NULLIF(COUNT(DISTINCT CASE WHEN if_in_confirm_temp=1 THEN mid END), 0) AS confirm_rate,
    COUNT(DISTINCT CASE WHEN if_issue=1 THEN mid END) * 1.0
        / NULLIF(COUNT(DISTINCT CASE WHEN if_app=1 THEN mid END), 0) AS issue_rate
FROM ind.ba_asset_base_info
WHERE app_date >= DATE('2025-01-01') AND if_app = 1
GROUP BY 1 ORDER BY 1
```

## 三、逾期率查询

```sql
SELECT
    app_month,
    SUM(overdue_amount_1_0) * 1.0 / NULLIF(SUM(should_capital_1_0), 0) AS fpd_rate,
    SUM(overdue_amount_1_30) * 1.0 / NULLIF(SUM(should_capital_1_30), 0) AS dpd30_rate,
    SUM(t30_capital_due_d30) * 1.0 / NULLIF(SUM(should_capital_d30), 0) AS t30_rate
FROM ind.ba_apply_should_result
GROUP BY 1 ORDER BY 1
```

## 四、VINTAGE cohort 坏账率

```sql
WITH loan_cohort AS (
    SELECT
        issue_month,
        biz_id,
        contract_amount_usd1 AS loan_amt
    FROM ind.ba_asset_base_info
    WHERE if_issue = 1 AND issue_month >= '2025-01-01'
),
bad_debt AS (
    SELECT ...  -- 按 cohort × MOB 匹配坏账
)
SELECT
    issue_month,
    mob,
    SUM(bad_amt) / NULLIF(SUM(loan_amt), 0) AS vintage_bad_rate
FROM ... GROUP BY 1, 2 ORDER BY 1, 2
```

## 五、复贷 cohort 分析

```sql
SELECT
    first_loan_issue_month,
    SUM(CASE WHEN month_num_issue <= 6 THEN contract_amount_usd1 END) * 1.0
        / NULLIF(SUM(contract_amount_usd1_new), 0) AS cohort_6m_amt_rate,
    SUM(CASE WHEN month_num_issue <= 12 THEN contract_amount_usd1 END) * 1.0
        / NULLIF(SUM(contract_amount_usd1_new), 0) AS cohort_12m_amt_rate
FROM (
    SELECT a.first_loan_issue_month, a.month_num_issue,
           a.contract_amount_usd1,
           b.contract_amount_usd1 AS contract_amount_usd1_new
    FROM ind.ba_asset_base_info a
    LEFT JOIN (
        SELECT issue_month, SUM(contract_amount_usd1) AS contract_amount_usd1
        FROM ind.ba_asset_base_info WHERE grant_strategy='NEW' AND if_issue=1
        GROUP BY 1
    ) b ON a.first_loan_issue_month = b.issue_month
    WHERE a.grant_strategy = 'OLD' AND a.if_issue = 1
) GROUP BY 1 ORDER BY 1
```

## 六、在贷余额

```sql
SELECT
    DATE_FORMAT(data_date1, '%Y-%m-01') AS balance_month,
    SUM(should_capital) AS principal,
    SUM(CASE WHEN due_days <= 30 THEN should_capital - fact_capital END) AS owing_principal,
    COUNT(DISTINCT CASE WHEN due_days <= 30 THEN mid END) AS repay_users
FROM ...  -- 关联 s02_loan_repayment_his + xly_application_funnel
GROUP BY 1 ORDER BY 1
```

## 七、产品×期限交叉分析

```sql
SELECT
    issue_month,
    product_tag,       -- R/M/NR/NF/NW
    loan_cycle,        -- 30/60/90/120/150/180
    grant_strategy,    -- NEW/OLD
    SUM(if_issue) AS loan_cnt,
    SUM(contract_amount_usd1) AS loan_amt,
    SUM(contract_amount_usd1) / NULLIF(SUM(if_issue), 0) AS avg_amt
FROM ind.ba_asset_base_info
WHERE issue_month >= '2025-01-01' AND if_issue = 1
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2, 3, 4
```

## 八、数据校验查询

### 行数校验
```sql
SELECT stat_month, grant_strategy, is_reloan2, COUNT(*) AS cnt
FROM ind.ba_loan_forecast
GROUP BY 1, 2, 3 ORDER BY 1, 2, 3
```

### 金额校验（预估 vs 实际）
```sql
SELECT
    f.stat_month,
    f.grant_strategy,
    SUM(f.contract_amt) AS forecast_amt,
    a.actual_amt
FROM ind.ba_loan_forecast f
LEFT JOIN (
    SELECT issue_month, grant_strategy,
           SUM(contract_amount_usd1) AS actual_amt
    FROM ind.ba_asset_base_info WHERE if_issue = 1
    GROUP BY 1, 2
) a ON f.stat_month = a.issue_month AND f.grant_strategy = a.grant_strategy
GROUP BY 1, 2, 3, 4 ORDER BY 1, 2
```

## 九、注意事项

1. **日期过滤**：务必加 `>= '2025-01-01'` 限制，否则扫描全表极慢
2. **NULL 处理**：除法用 `NULLIF(分母, 0)` 避免除零
3. **去重**：人数用 `COUNT(DISTINCT mid)`，笔数用 `SUM(if_issue)`
4. **汇率**：IDR→USD 汇率从 `dim.dim_exchange_rate_cost` 取，直接算时用 `contract_amount_usd1` 字段
5. **当月预估**：当月未走完，放款量按 `已过天数 / 月总天数` 放大
