# KPI 指标词典

> 海外信贷经营分析的全部指标定义、计算公式、数据来源和业务含义。

## 一、放款类指标

| 指标 | 英文 | 计算公式 | 数据来源 | 说明 |
|------|------|---------|---------|------|
| 放款笔数 | Loan Count | `SUM(if_issue)` | `ind.ba_asset_base_info` | — |
| 放款人数 | Loan Customer Count | `COUNT(DISTINCT mid WHERE if_issue=1)` | 同上 | 去重用户数 |
| 放款金额(USD) | Loan Amount USD | `SUM(contract_amount_usd1)` | 同上 | 合同金额美金 |
| 放款金额(IDR) | Loan Amount IDR | `SUM(contract_amount)` | 同上 | 合同金额印尼盾 |
| 件均(USD) | Avg Loan Amt | `SUM(contract_amount_usd1) / SUM(if_issue)` | 同上 | 每笔平均放款额 |
| 客均笔数 | Loans per Customer | `SUM(if_issue) / COUNT(DISTINCT mid)` | 同上 | 复贷频率指标 |
| 平均期限(天) | Avg Loan Cycle | `SUM(loan_cycle_amount) / SUM(contract_amount)` | 同上+还款表 | 加权平均期限 |

### 按策略拆分

所有放款指标均按 `grant_strategy` 拆分：
- **NEW** = 首贷（新客首次放款）
- **OLD** = 复贷（老客再次借款）

### 按复贷类型拆分 (is_reloan2)

- **NEW_PURE** = 纯新客
- **loop** = 循环贷复贷
- **normal** = 非循环贷复贷

## 二、进件&转化类指标

| 指标 | 英文 | 计算公式 | 数据来源 |
|------|------|---------|---------|
| 进件量 | App Count | `SUM(if_app)` | `ind.ba_asset_base_info` |
| 进件人数 | App User Count | `COUNT(DISTINCT mid WHERE if_app=1)` | 同上 |
| 机审通过率 | Before Pass Rate | `if_external_3_passed / if_app` | 同上 |
| 确认借款率 | Confirm Rate | `if_confirm_passed_final / if_in_confirm_temp` | 同上 |
| 后置通过率 | After Pass Rate | `if_external_data_4_passed / if_in_external_data_4` | 同上 |
| 全流程通过率 | Full Pass Rate | `确认借款率 × 后置通过率` | 同上 |
| 注册→放款转化率 | Reg→Issue Rate | `all_issue_cnt / reg_cnt` | 注册表+资产表 |
| T0放款率 | T0 Issue Rate | `t0_issue_cnt / reg_cnt` | 注册当天放款 |
| T15放款率 | T15 Issue Rate | `t15_issue_cnt / reg_cnt` | 注册15天内放款 |

## 三、风险&坏账类指标

| 指标 | 英文 | 计算公式 | 数据来源 |
|------|------|---------|---------|
| T30坏账率 | T30 Bad Debt Rate | `坏账金额 / 业绩金额` | `ind.ba_loan_forecast` / 风险提供 |
| 首期逾期率(金额) | FPD Amount Rate | `SUM(overdue_amount_1_0) / SUM(should_capital_1_0)` | `ind.ba_apply_should_result` |
| 30天逾期率 | DPD30 Rate | `SUM(overdue_amount_1_30) / SUM(should_capital_1_30)` | 同上 |
| 30天逾期率(总) | Total DPD30 | `SUM(overdue_amount_3_30) / SUM(should_capital_3_30)` | 同上 |
| T1本金逾期率 | T1 Capital Due | `SUM(t1_capital_due_d1) / SUM(should_capital_d1)` | 同上 |
| T30本金逾期率 | T30 Capital Due | `SUM(t30_capital_due_d30) / SUM(should_capital_d30)` | 同上 |
| 在贷余额 | Onloan Balance | `SUM(should_capital WHERE due_days<=30)` | `ods.s02_loan_repayment_his` |
| 在贷逾期本金 | Owing Principal | `SUM(should_capital - fact_capital WHERE due_days<=30)` | 同上 |
| 年化坏账率 | Annual Bad Rate | `坏账$ / 业绩$` (年化) | `ind.ba_loan_forecast` |
| Grade1-2占比 | Grade1-2% | `高质量用户数 / 总用户数` | 风控数据 |

### VINTAGE坏账率

按放款月 cohort × 账龄月(MOB) 展开的坏账率矩阵：
```sql
SELECT issue_month, mob, SUM(bad_amt) / SUM(contract_amt) AS vintage_bad_rate
FROM (cohort展开) GROUP BY 1, 2 ORDER BY 1, 2
```

## 四、收入&利润类指标

| 指标 | 英文 | 计算公式 | 数据来源 |
|------|------|---------|---------|
| 收入 | Revenue | `SUM(revenue)` | `ind.ba_asset_base_info` |
| 业绩(合同金额) | Contract Amt | `SUM(contract_amount_usd1)` | 同上 |
| 坏账金额 | Bad Amt | `放款金额 × T30坏账率` | `ind.ba_loan_forecast` |
| 净收入 | Net Revenue | `收入 - 坏账` | 计算字段 |
| 利润率 | Profit Margin | `净收入 / 收入` | 计算字段 |
| 每进件成本(IDR) | Cost per App | `总成本 / 进件量` | 外部输入 |

## 五、cohort/复贷类指标

| 指标 | 英文 | 计算公式 | 说明 |
|------|------|---------|------|
| 6月复贷率(笔数) | Cohort 6M Cnt Rate | `首贷后6月内复贷笔数 / 首贷笔数` | — |
| 12月复贷率(笔数) | Cohort 12M Cnt Rate | `首贷后12月内复贷笔数 / 首贷笔数` | — |
| 6月复贷率(金额) | Cohort 6M Amt Rate | `首贷后6月内复贷金额 / 首贷金额` | 金额维度 |
| MOB转化率 | MOB Conversion Rate | `某MOB的复贷进件量 / 对应cohort的首贷放款量` | 复贷预估核心输入 |
| MA转化率 | MA Rate | `最近N期同MOB转化率的移动平均` | MOB0取2期，MOB1+取1期 |

## 六、运营类指标

| 指标 | 英文 | 计算公式 | 说明 |
|------|------|---------|------|
| 可运营复贷人数 | Old Managed Cnt | `COUNT(DISTINCT mid WHERE if_overdue<>1 AND if_reject<>1)` | 从运营标签表取 |
| 在贷活跃人数 | Onloan Repay Users | `COUNT(DISTINCT mid WHERE due_days<=30 AND OLD)` | 在贷老客数 |
| 平均在贷金额/人 | Avg Onloan per User | `owing_principal / repay_user_num` | 人均负债 |
| 授信额度 | Grant Amount Max | `SUM(grant_amount_max)` | 在贷用户的授信额度 |
| 人均授信 | Avg Grant per User | `grant_amount_max / repay_user_num` | — |
| 期限(加权平均) | Duration | `SUM(day_diff × should_capital) / SUM(should_capital)` | 从还款计划算 |

## 七、投放类指标（与 paid-acquisition-strategy 共享）

| 指标 | 英文 | 说明 |
|------|------|------|
| CPS | Cost per Sale | 消耗 / 放款数 |
| CPM | Cost per Mille | 千次曝光成本 |
| CTR | Click Through Rate | 点击率 |
| CPI | Cost per Install | 每安装成本 |
| CPR | Cost per Registration | 每注册成本 |
| FPD | First Payment Default | 首期逾期率 |
