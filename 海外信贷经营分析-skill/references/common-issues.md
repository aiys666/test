# 常见问题速查

> 经营分析中常见的异常情况和排查路径。

## 一、数据校验类

### 预估 vs 实际偏差大 (>15%)

**排查路径**：
1. 检查首贷实际放款量 vs 首贷公式预估 → 调整 CPI/通过率/件均
2. 检查复贷实际 MOB 转化率 vs MA 值 → 调整窗口大小/调整系数
3. 检查权责预估 SUMIFS 输出 vs 资产底表汇总 → 定位偏差最大的产品×期限
4. 确认风险参数(K/L/M/S/V)是否已更新到最新版

### 数据行数对不上

**排查路径**：
```sql
-- 1. 检查表中总行数
SELECT COUNT(*) FROM ind.ba_loan_forecast;

-- 2. 按月份+策略分组，与 Excel 逐行对比
SELECT stat_month, grant_strategy, is_reloan2, COUNT(*) AS cnt
FROM ind.ba_loan_forecast
GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;

-- 3. 检查是否有重复或缺失的维度组合
```

### 放款金额不一致

**常见原因**：
- 口径不同：`contract_amount_usd` vs `contract_amount_usd1`
- 汇率不同：IDR→USD 的汇率来源不一样
- 时间窗口：issue_month vs app_month 的归属规则
- if_issue=1 过滤条件是否一致

---

## 二、预估模型类

### 复贷预估值偏高/偏低

**排查路径**：
1. MOB 转化率是否用了足够多的 cohort 计算？
2. MA 窗口大小是否合适？（默认 2 期）
3. 调整系数是否需要重新校准？
4. 首贷量 forecast 是否准确？（输入决定输出）
5. 是否有新产品/策略影响了复贷行为？

### 权责预估坏账率异常

**排查路径**：
1. 检查 `accrual_rates` 中各维度的 V 值是否已更新
2. 对比 V 值与实际 `ind.ba_bad_debt_rate_lookup` 中的数据
3. 确认产品×期限维度映射是否正确
4. 检查 Q 分布系数是否还适用（各期限占比是否变化）

---

## 三、数据库类

### Presto 查询超时

**原因和解决**：
- 数据量太大 → 加日期过滤 `WHERE issue_month >= 'YYYY-MM-DD'`
- CTE 嵌套太深 → 拆分为多个简单查询
- 高峰期 → 错峰执行

### 表字段不存在

**排查**：
1. `SELECT * FROM table LIMIT 1` 确认字段名
2. 检查是否是 Presto 保留字（需要双引号）
3. 大小写是否正确（Presto 对大小写敏感度取决于配置）

---

## 四、配置类

### pipeline 执行失败

**常见原因**：
1. `config.yaml` 格式错误（YAML 缩进问题）
2. 文件路径中 `{month}` 占位符未替换
3. 模板 Excel 文件不存在或结构变化
4. 数据库用户名密码过期

### 预检查报错但想强制执行

```bash
python pipeline.py  # 预检查警告不会阻止执行
```

---

## 五、SQL 类

### CASE WHEN 写得又臭又长

**优化**：
- 多次出现的 `CASE WHEN grant_strategy='NEW'` 用 CTE 先拆分
- 比率计算提取为独立 CTE，主查询只做 JOIN
- 超过 3 层的 CASE WHEN 考虑用子查询替代

### 数据突然为空

**排查**：
1. 日期过滤是否正确（`>= '2025-01-01'` 不是 `= '2025-01'`）
2. JOIN 是否因为 NULL 值丢失数据（用 LEFT JOIN 不是 INNER JOIN）
3. `if_issue=1` 等过滤条件是否遗漏
4. 分区是否最新（检查 `data_date` 或 `issue_month` 范围）
