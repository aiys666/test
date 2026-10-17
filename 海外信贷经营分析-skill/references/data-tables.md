# 数据库表字典

> 印尼现金贷业务核心表结构、字段说明和关联关系。

## 一、资产底表（最核心）

### ind.ba_asset_base_info

全业务最核心的表，覆盖进件→确认→放款→还款全链路。

| 字段 | 类型 | 说明 |
|------|------|------|
| `issue_month` | VARCHAR | 放款月份 (yyyy-MM-dd) |
| `app_date` | DATE | 进件日期 |
| `app_month` | VARCHAR | 进件月份 |
| `create_date` | DATE | 创建日期 |
| `release_time` | TIMESTAMP | 放款时间 |
| `mid` | BIGINT | 用户ID |
| `biz_id` | BIGINT | 订单ID |
| `grant_strategy` | VARCHAR | 授信策略: NEW(首贷) / OLD(复贷) |
| `is_reloan2` | VARCHAR | 复贷细分: NEW_PURE / loop / normal |
| `loan_type2` | VARCHAR | 贷款类型: loop / normal |
| `loan_cycle` | INT | 期限(天): 30/60/90/120/150/180 |
| `product_tag` | VARCHAR | 产品标签: R/M/NR/NF/NW |
| `if_app` | INT | 是否进件 (0/1) |
| `if_recall` | INT | 是否召回 (0/1) |
| `if_in_confirm_temp` | INT | 是否临时确认 (0/1) |
| `if_confirm_passed_final` | INT | 是否最终确认通过 (0/1) |
| `if_issue` | INT | 是否放款 (0/1) |
| `if_external_data_3_passed` | INT | 数据3通过 (0/1) |
| `if_in_external_data_4` | INT | 进入数据4 (0/1) |
| `if_external_data_4_passed` | INT | 数据4通过 (0/1) |
| `if_confirm_passed_num_24h` | INT | 24h内确认通过 (0/1) |
| `if_confirm_passed_num_t30` | INT | 30天内确认通过 (0/1) |
| `apply_amount` | DECIMAL | 申请金额 |
| `apply_grantcredit_amount` | DECIMAL | 申请授信金额 |
| `grantcredit_amount` | DECIMAL | 授信金额 |
| `contract_amount` | DECIMAL | 合同金额(IDR) |
| `contract_amount_usd` | DECIMAL | 合同金额(USD) |
| `contract_amount_usd1` | DECIMAL | 合同金额(USD备用口径) |
| `amount` | DECIMAL | 金额(IDR) |
| `loan_cycle_amount` | DECIMAL | 期限×金额 |
| `revenue` | DECIMAL | 收入 |
| `first_loan_issue_month` | VARCHAR | 首贷放款月份 |
| `month_num_issue` | INT | 距首贷月数 |
| `issue_date` | DATE | 放款日期 |
| `confirm_date_final` | DATE | 最终确认日期 |

---

## 二、经营预估结果表

### ind.ba_loan_forecast

由 pipeline Step4 写入，存储权责预估结果。

| 字段 | 说明 |
|------|------|
| `stat_month` | 统计月份 |
| `grant_strategy` | NEW / OLD |
| `is_reloan2` | new / loop / normal |
| `loan_cycle` | 期限 |
| `product_tag` | 产品 R/M/NR/NF/NW |
| `apply_cnt` | 进件量 |
| `before_pass_rate` | 机审通过率 |
| `confirm_rate` | 确认借款率 |
| `after_pass_rate` | 后置通过率 |
| `pass_rate` | 风险通过率 |
| `sign_grant_rate` | 签名放款率 |
| `loan_cnt` | 放款笔数 |
| `avg_amt_idr` | 件均(IDR) |
| `avg_amt_usd` | 件均(USD) |
| `t30_rate` | T30坏账率 |
| `contract_amt` | 业绩(USD) |
| `bad_amt` | 坏账(USD) |
| `annual_bad_rate` | 年化坏账率 |

---

## 三、坏账率查表

### ind.ba_bad_debt_rate_lookup

由 pipeline Step1 写入，风险坏账率的维度查表。

| 字段 | 说明 |
|------|------|
| `grant_month` | 放款月份 |
| `product_tag` | 产品标签 |
| `period_tag` | 期限标签 (15D/30D/F/M/NR/NF/NW) |
| `grant_strategy` | NEW / OLD |
| `loan_cycle` | 期限天数 (15/30/60/90/120/150/180/9999合计) |
| `bad_debt_rate` | 坏账率 |

---

## 四、进件漏斗

### ind.xly_application_funnel

每条记录=一个进件订单的完整链路（注册→进件→授信→放款）。

| 关键字段 | 说明 |
|---------|------|
| `biz_id` | 订单ID |
| `mid` | 用户ID |
| `grant_strategy` | NEW/OLD |
| `app_date` / `app_time` | 进件时间 |
| `issue_date` / `issue_month` | 放款时间 |
| `contract_amount` | 合同金额 |
| `release_time` | 放款时间戳 |
| `baseinfo_onloan_amount` | 在贷余额快照 |

---

## 五、放款明细

### dwd.dwd_loan_info

| 关键字段 | 说明 |
|---------|------|
| `mid` | 用户ID |
| `order_no` | 订单号（关联进件） |
| `release_time` | 放款时间 |

---

## 六、还款计划

### ods.s02_loan_repayment / ods.s02_loan_repayment_his

| 关键字段 | 说明 |
|---------|------|
| `camera_id` | 放款ID（关联 biz_id） |
| `lid` | 还款计划ID |
| `customer_id` | 用户ID |
| `should_capital` | 应还本金 |
| `fact_capital` | 实还本金 |
| `should_time` | 应还日期 |
| `fact_time` | 实还日期 |
| `create_time` | 创建时间 |
| `data_date` | 数据日期 |

---

## 七、逾期结果

### ind.ba_apply_should_result

| 关键字段 | 说明 |
|---------|------|
| `app_month` | 进件月份 |
| `grant_strategy` | NEW/OLD |
| `overdue_amount_1_0` | FPD逾期金额 |
| `overdue_amount_1_30` | 1-30天逾期金额 |
| `overdue_amount_3_30` | 3-30天逾期金额 |
| `should_capital_1_0` | FPD应还本金 |
| `should_capital_1_30` | 1-30天应还本金 |
| `t1_capital_due_d1` | T1本金逾期 |
| `t30_capital_due_d30` | T30本金逾期 |

---

## 八、注册安装

### ind.tyn_reg_install_new

| 关键字段 | 说明 |
|---------|------|
| `mid` | 用户ID |
| `reg_dt` | 注册日期 |
| `reg_time` | 注册时间 |

---

## 九、汇率

### dim.dim_exchange_rate_cost

| 关键字段 | 说明 |
|---------|------|
| `month_id` | 月份ID (yyyymm) |
| `account_currency` | 币种 (IDR) |
| `exchange_rate_to_dollar` | 汇率 |

---

## 十、表关联速查

```
资产底表 ←→ 放款明细:     ba_asset_base_info.biz_id = dwd_loan_info.order_no
资产底表 ←→ 进件漏斗:     ba_asset_base_info.biz_id = xly_application_funnel.biz_id
资产底表 ←→ 还款计划:     ba_asset_base_info.biz_id = s02_loan_repayment.camera_id
资产底表 ←→ 逾期结果:     ba_asset_base_info.app_month = ba_apply_should_result.app_month
资产底表 ←→ 注册安装:     ba_asset_base_info.mid = tyn_reg_install_new.mid
资产底表 ←→ 汇率:         DATE_FORMAT(app_date, 'yyyymm') = dim_exchange_rate_cost.month_id
放款明细 ←→ 进件漏斗:     dwd_loan_info.order_no = xly_application_funnel.biz_id
```
