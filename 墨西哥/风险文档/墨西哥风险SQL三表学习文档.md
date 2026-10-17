# 墨西哥风险SQL三表学习文档

> 日期: 2026-08-20
> 涵盖文件:
> - `01墨西哥风险宽表.sql` (1745行) — 贷后风险宽表
> - `02墨西哥风险结清表.sql` (845行) — 结清调额与首次结清实验
> - `03墨西哥风险等级划分.sql` (668行) — 审批漏斗与风险等级

---

# 第一部分: 01墨西哥风险宽表.sql

## 1.1 这张表是做什么的？

这张表是**贷后风险的核心底表**，把每笔贷款从放款到还款到逾期的全生命周期数据整合到一起，供周报的坏账率、逾期率、LTV计算使用。

**一句话理解**: 每笔订单 → 应还多少 → 实还多少 → 逾期多少 → 分时间窗口(T0/T3/T7/T14/T30)统计

## 1.2 整体数据流向

```
s02_loan(放款表)
    ↓
s02_loan_repayment(还款计划表) ← 应还金额
    ↓
s02_loan_repayment_detail(还款明细表) ← 实还金额
    ↓
wxs_risk_ttl(订单级TTL) ← T0/T3/T7/T14/T30逾期金额
    ↓
wxs_vintage_all1~all5(Vintage链) ← 按期数×时间窗口透视
    ↓
wxs_overdue_basetable(贷后基表) ← s09授信快照 + risk_ttl + vintage_all5
    ↓
wxs_application_funnel_1(主漏斗) ← 进件 + 放款 + 贷后 + 渠道
    ↓
wxs_application_funnel_2(审批节点) ← 反欺诈/模型/人审/三方/AI/SX
    ↓
wxs_application_funnel(最终宽表) ← funnel_1 LEFT JOIN funnel_2
```

## 1.3 逐段代码逻辑

### 步骤1-2: 风险标签导入

```sql
-- 步骤1: 首复贷标签
INSERT INTO mx.tmp_darren_double_loan_tag_table
SELECT externalid, double_loan_tenant
FROM ods.s21_risk_strategy_record
WHERE productid IN (310,330,331)
  AND strategytype = 'CHAMPION'
```

**逻辑**: 从风险策略记录表(s21)中，提取产品ID为310/330/331的"首复贷租户标签"。`double_loan_tenant=0`表示首贷，`=1`表示复贷。

**为什么用s21而不是s02_loan的double_loan字段**: 因为s21是风险决策流的判定结果，更准确。s02_loan的double_loan字段可能因为渠道特殊规则而不准(见03表漏洞6的11个硬编码渠道)。

---

### 步骤3: 首复贷判断(wxs_reloan)

```sql
CREATE TABLE mx.wxs_reloan AS
SELECT DISTINCT t1.id,
  t2.issue_num,  -- 第几次放款(1=首贷, 2+=复贷)
  CASE WHEN t2.issue_num = 1 THEN 'new' ELSE 'old' END AS grant_strategy,
  t1.mid, t1.create_time
FROM ods.s09_os_credit_snapshot t1
LEFT JOIN (
  -- 统计每个用户在本次进件之前已有几笔放款
  SELECT t1.id, COUNT(t2.biz_id) + 1 AS issue_num
  FROM (...) t1
  LEFT JOIN (...) t2 ON t1.mid = t2.customer_id
  WHERE create_time > release_time  -- 之前放的款
  GROUP BY create_time, t1.id, t1.mid
) t2 ON t1.id = t2.id
```

**逻辑**:
1. 主表: s09_os_credit_snapshot(授信快照表)，每条记录是一次进件申请
2. 关联: 找到同一用户(mid)在本次进件**之前**已经放款的笔数
3. 判断: 如果之前有0笔放款 → `issue_num=1` → 首贷(new)；如果有1笔以上 → 复贷(old)

**业务含义**: 这是风险策略判断首复贷的核心逻辑。首贷用户的风险特征和复贷完全不同，后续所有审批节点都区分首贷/复贷分别处理。

---

### 步骤4: 订单级贷后TTL(wxs_risk_ttl)

这是整个风险宽表**最核心**的一张表，计算每笔订单的应还/实还/逾期金额。

```sql
CREATE TABLE mx.wxs_risk_ttl AS
WITH
-- t2子查询: 应还金额聚合(按订单号汇总所有期)
t2 AS (
  SELECT a.camera_id,
    SUM(a.should_capital) AS should_capital,        -- 应还本金
    SUM(a.should_interest) AS should_interest,      -- 应还利息
    SUM(a.should_fine) AS should_fine,              -- 应还罚金
    MAX(a.should_time) AS should_time,              -- 最晚应还时间
    -- 按时间窗口拆分应还: T0=当天到期, T3=3天内到期...
    SUM(CASE WHEN date(should_time) < current_date THEN should_capital + should_interest ELSE 0 END) AS t0_should_amt,
    SUM(CASE WHEN date_diff('day', should_time, current_date) >= 3 THEN ... END) AS t3_should_amt,
    -- 同理 T7/T14/T30
  FROM s02_loan_repayment a
  GROUP BY a.camera_id
),
-- t3子查询: 实还金额聚合(按订单号汇总所有还款明细)
t3 AS (
  SELECT camera_id,
    SUM(fact_capital + fact_interest) AS now_fact_amt,  -- 累计实还
    -- 按时间窗口拆分实还: T0=到期前还的, T3=到期3天内还的...
    SUM(CASE WHEN date_diff('day', should_time, fact_time) <= 0 THEN fact_capital + fact_interest ELSE 0 END) AS t0_fact_amt,
    SUM(CASE WHEN date_diff('day', should_time, fact_time) <= 3 THEN ... END) AS t3_fact_amt,
    -- 同理 T7/T14/T30
  FROM s02_loan_repayment_detail
  GROUP BY camera_id
),
-- t4子查询: 在逾天数
t4 AS (
  SELECT camera_id,
    CASE WHEN (should = fact + subtract) THEN 0  -- 已还清
         ELSE date_diff('day', should_time, current_date)  -- 未还清=逾期天数
    END AS overdue_days
  FROM s02_loan_repayment
)
SELECT t1.*, t2.*, t3.*,
  -- 逾期金额 = 应还 - 实还
  CASE WHEN t3.t0_fact_amt >= t2.t0_should_amt THEN 0
       ELSE t2.t0_should_amt - t3.t0_fact_amt END AS T0_OVERDUE_AMOUNT,
  -- 同理 T3/T7/T14/T30
  t4.overdue_days
FROM s02_loan t1
LEFT JOIN t2 ON t1.camera_id = t2.camera_id
LEFT JOIN t3 ON t1.camera_id = t3.camera_id
LEFT JOIN t4 ON t1.camera_id = t4.camera_id
```

**逻辑详解**:

| 子查询 | 数据源 | 做什么 | 关键字段 |
|--------|--------|--------|---------|
| t2 | s02_loan_repayment | 按订单聚合应还金额，按时间窗口拆分 | should_capital, t0_should_amt |
| t3 | s02_loan_repayment_detail | 按订单聚合实还金额，按时间窗口拆分 | now_fact_amt, t0_fact_amt |
| t4 | s02_loan_repayment | 计算在逾天数 | overdue_days |

**时间窗口的含义**:
- T0: 到期日当天及之前 → `date_diff('day', should_time, fact_time) <= 0`
- T3: 到期后3天内 → `<= 3`
- T7: 到期后7天内 → `<= 7`
- T14: 到期后14天内 → `<= 14`
- T30: 到期后30天内 → `<= 30`

**逾期金额计算**:
```
逾期金额 = 应还金额 - 实还金额
如果实还 ≥ 应还 → 逾期金额 = 0
如果实还 < 应还 → 逾期金额 = 应还 - 实还
```

**工作中怎么用**: 这张表直接供周报的1T0/1T7逾期率计算:
```sql
-- 周报SQL中的逾期率
1T0 = (sum_t0_should - sum_has_t0) / sum_t0_should
-- sum_t0_should = t0_should_amt的总和(分母)
-- sum_has_t0 = t0_fact_amt的总和(分子中的已还部分)
```

---

### 步骤5-9: Vintage坏账分析链

Vintage分析是按**放款月+账龄(MOB)**追踪坏账的方法，用于评估不同月份放款的质量。

```
vintage_all1 (还款计划关联放款)
    ↓ 每条还款计划关联对应的放款订单
vintage_all2 (展开indexs 1-10)
    ↓ 一笔贷款只有1期?模拟展开到10期做vintage
vintage_all3 (计算due/ovd标志位)
    ↓ 每期是否到期?是否逾期?按时间窗口判断
vintage_all31 (按id+indexs聚合)
    ↓ 聚合应还/逾期金额
vintage_all4 (透视到id级)
    ↓ 行转列: indexs×时间窗口 → 一行一个订单
vintage_all5 (字段重命名)
    ↓ 统一字段命名
```

#### vintage_all1: 还款计划关联放款

```sql
CREATE TABLE mx.wxs_vintage_all1 AS
SELECT t1.camera_id, t1.loan_indexs,  -- 第几期
       t1.should_capital, t1.should_interest,
       t1.fact_capital, t1.fact_interest,
       t1.state,  -- 0=未还, 1=已还, 2=部分还, 3=已结清, 4=减免, 5=核销
       t1.should_time, t1.fact_time
FROM s02_loan_repayment t1
INNER JOIN s02_loan t2 ON t1.camera_id = t2.camera_id
WHERE t1.indexs = t1.loan_indexs  -- 只取实际存在的期数
```

**逻辑**: 把还款计划表(s02_loan_repayment)和放款表(s02_loan)关联，只取实际存在的还款期数。

#### vintage_all2: 展开indexs 1-10

```sql
-- 如果一笔贷款只有1期(indexs=1)，模拟展开到2-10期
SELECT camera_id, 2 AS indexs, should_date, fact_date, state
FROM vintage_all1 WHERE loan_indexs < 2  -- 只有1期的贷款

UNION ALL

SELECT camera_id, 3 AS indexs, should_date, fact_date, state
FROM vintage_all1 WHERE loan_indexs < 3  -- 只有1-2期的贷款
-- ...同理到10
```

**为什么展开**: Vintage分析需要统一比较不同期数的产品。一笔21天贷款只有1期，一笔90天贷款有3期，通过展开到10期，可以在同一个框架下比较。

#### vintage_all3: 计算due/ovd标志位

```sql
-- duem3_flag: 应到期标志(到期日已过3天)
IF(date_diff('day', should_date, current_date) > -3, 1, 0) AS duem3_flag
-- 意思: current_date > should_date - 3，即当前日期距离到期日不到3天或已过期

-- ovdm3_flag: 逾期标志(到期3天未还清)
IF(date_diff('day', should_date, 
    IF(state IN (0,2,4), current_date, fact_date)) > -3, 1, 0) AS ovdm3_flag
-- 意思: 对未还清的订单(0,2,4)，用当前日期算逾期天数
--        对已还清的订单(1,3,5)，用实际还款日期算是否逾期过
```

**9个时间窗口**:
| 标志 | 含义 | 门槛 |
|------|------|------|
| duem3/ovdm3 | 提前3天 | 到期前3天 |
| duem2/ovdm2 | 提前2天 | 到期前2天 |
| duem1/ovdm1 | 提前1天 | 到期前1天 |
| due0/ovd0 | 到期当天 | 到期日 |
| due1/ovd1 | 逾期1天 | 到期后1天 |
| due2/ovd2 | 逾期2天 | 到期后2天 |
| due3/ovd3 | 逾期3天 | 到期后3天 |
| due7/ovd7 | 逾期7天 | 到期后7天 |
| due30/ovd30 | 逾期30天 | 到期后30天 |

#### vintage_all31: 按id+indexs聚合

```sql
-- 按订单号+期数聚合应还/逾期金额
SELECT camera_id, indexs,
  SUM(should_capital + should_interest) AS should_capital,  -- 应还总额
  -- 每个时间窗口的逾期金额 = 应还 - 对应窗口的实还
  IF(duem3_flag=1, should_capital, 0) AS duem3_amount,
  IF(ovdm3_flag=1, should_capital - repay_tm3_amt_all, 0) AS ovdm3_amount
  -- ...同理其他窗口
FROM vintage_all3
LEFT JOIN s02_loan_repayment_detail  -- 关联还款明细算repay_tN_amt
GROUP BY camera_id, indexs
```

#### vintage_all4: 透视到id级

```sql
-- 行转列: 把indexs×时间窗口的数据合并到一行
SELECT camera_id,
  -- 第1期各窗口
  SUM(IF(indexs=1, due0_cnt, 0)) AS should_cnt_1_0,      -- 第1期T0应到笔数
  SUM(IF(indexs=1, ovd0_cnt, 0)) AS overdue_cnt_1_0,      -- 第1期T0逾期笔数
  SUM(IF(indexs=1, due0_amount, 0)) AS should_capital_1_0, -- 第1期T0应到金额
  SUM(IF(indexs=1, ovd0_amount, 0)) AS overdue_amount_1_0,  -- 第1期T0逾期金额
  -- 第2期各窗口
  SUM(IF(indexs=2, due0_cnt, 0)) AS should_cnt_2_0,
  -- ...同理indexs=3,4
FROM vintage_all31
GROUP BY camera_id
```

**工作中怎么用**: 这张表供LTV计算和Vintage坏账率:
```sql
-- Vintage坏账率 = 逾期金额 / 应还金额
-- 例如: 第1期T30坏账率
overdue_amount_1_30 / should_capital_1_30
```

---

### 步骤10-11: 贷后基表(overdue_basetable)

```sql
CREATE TABLE mx.wxs_overdue_basetable AS
SELECT t1.*,  -- s09授信快照
       t2.t0_should_amt, t2.t0_fact_amt,  -- risk_ttl的应还/实还
       t3.should_cnt_1_0, t3.overdue_cnt_1_0,  -- vintage_all5的各窗口
       t3.should_capital_1_30, t3.overdue_amount_1_30
FROM s09_os_credit_snapshot t1
LEFT JOIN wxs_risk_ttl t2 ON t1.id = t2.camera_id
LEFT JOIN wxs_vintage_all5 t3 ON t1.id = t3.id
```

**逻辑**: 把授信快照表(进件层面)与贷后数据(订单层面)关联，形成完整的"进件→放款→还款→逾期"基表。

---

### 步骤12-14: 申请漏斗(application_funnel)

```sql
-- funnel_1: 主漏斗(进件→审批→放款→贷后→渠道)
CREATE TABLE mx.wxs_application_funnel_1 AS
SELECT a.*,  -- s09授信快照(进件)
       b.issue_num, b.grant_strategy,  -- 首复贷
       c.release_time, c.contract_amount,  -- 放款
       d.t0_should_amt, d.overdue_days,  -- 贷后
       e.double_loan_tenant,  -- 首复贷标签
       f.app_group, f.new_media_source  -- 渠道
FROM s09_os_credit_snapshot a
LEFT JOIN wxs_reloan b ON ...
LEFT JOIN s02_loan c ON ...
LEFT JOIN overdue_basetable d ON ...
LEFT JOIN double_loan_tag e ON ...
LEFT JOIN app_category f ON ...

-- funnel_2: 审批节点(反欺诈/模型/人审/三方/AI/SX)
CREATE TABLE mx.wxs_application_funnel_2 AS
SELECT biz_id,
  -- 每个节点的: 是否进入/是否通过/是否拒绝
  -- 例如: 首贷强反欺诈
  IF(p1.biz_id IS NOT NULL, 1, 0) AS if_in_shou_anti_fraud,
  CASE WHEN SUM(refused) IS NULL THEN 1 ELSE 0 END AS if_shou_anti_fraud_passed,
  CASE WHEN SUM(refused) >= 1 THEN 1 ELSE 0 END AS if_shou_anti_fraud_refused
FROM s05_creditx_processor_record
WHERE current_processor = '首贷强反欺诈'

-- 最终宽表: funnel_1 LEFT JOIN funnel_2
CREATE TABLE mx.wxs_application_funnel AS
SELECT a.*, b.*
FROM funnel_1 a
LEFT JOIN funnel_2 b ON a.biz_id = b.biz_id
```

**工作中怎么用**: 这张表是周报进件漏斗的数据源:
```sql
-- 周报中的通过率 = 放款量 / 进件量
if_issue / if_in_shou_anti_fraud
```

---

# 第二部分: 02墨西哥风险结清表.sql

## 2.1 这张表是做什么的？

这张表追踪**结清后调额**的全流程：用户还清贷款后，风险策略决定是否给用户提额，以及提多少。用于首次结清提额实验的AB测试分析。

**一句话理解**: 用户还清贷款 → 风险决策流判断是否提额 → AB测试分组 → 追踪提额后的进件/放款/还款表现

## 2.2 整体数据流向

```
s21_risk_strategy_record (风险决策流)
    ↓
t0~t9中间表 (提取各决策字段)
    ↓
darren_jieqing_dt_base_table (主表: 整合所有字段 + AB标签)
    ↓
darren_jieqing_dt_table (关联结清后5天内进件)
    ↓
darren_shouci_jieqing_dt_table (首次结清用户筛选)
    ↓
darren_shouci_jieqing_summary_table (多窗口汇总)
```

## 2.3 逐段代码逻辑

### 步骤1: identity↔mid映射

```sql
CREATE TABLE mx.darren_identity_mid_base_table AS
SELECT t0.identity, t1.mid
FROM s01_mem_base_info t0
LEFT JOIN s01_mem_member_account t1 ON t0.cust_id = t1.mb_cust_id
```

**逻辑**: 建立用户身份标识(identity)和会员ID(mid)的映射关系。一个identity可能对应多个mid(换设备/换账号)，后续结清次数统计需要按identity去重。

---

### 步骤2-9: 风险决策流中间表

每个中间表从s21(风险策略记录)中提取一个特定决策树的字段:

| 中间表 | 来源 | 提取字段 | 业务含义 |
|--------|------|---------|---------|
| t0 | s21 productid=428 | credit_amount, daily_max_available_limit | 结清后的授信额度和日最大可用额度 |
| t1 | s21 modelmainid=1063 | is_settle_adjust_quota_flag | 是否触发了结清调额决策树 |
| t2 | s21 modelmainid=1364 | settle_adjust_quota_cnt, last_credit_amount | 成功调额次数、上次授信额度 |
| t3 | s21 modelId=2402等 | global_limit, add_cap, uncapped | 全局额度cap相关 |
| t7 | s21 productid=196 | sx_credit_amount | 复贷授信决策流的额度 |
| t8 | s21 modelmainid=1436 | android_oldCust_mainCreditLevel_charge_V5_1 | V5_1资产等级 |
| t9 | s21 modelmainid=1063 | 10个特征字段 | 结清调额综合特征(逾期次数/天数等) |

**t9的10个关键字段**:

| 字段 | 含义 |
|------|------|
| last_credit_amount_change_day_gap | 上次额度变化距今天数 |
| curr_ovd_cnt_all | 当前总逾期次数 |
| curr_ovd_cnt_this_app_group | 当前本app_group逾期次数 |
| curr_ovd_cnt_other_app_group_90d | 90天内其他app_group逾期次数 |
| max_overdue_day_30d_all | 30天内最大逾期天数 |
| last_credit_increase_day_gap | 上次提额距今天数 |
| hist_loanrec_cnt_issue_days_last_jieqing | 上次结清到放款天数 |
| settle_adjust_quota_cnt | 成功调额次数 |
| is_settle_adjust_quota_flag | 是否触发调额 |

**工作中怎么用**: 这些字段是风险策略判断"是否给用户提额"的输入特征。例如:
- `max_overdue_day_30d_all > 2` → 最近30天逾期超过2天 → 不提额
- `curr_ovd_cnt_this_app_group > 0` → 当前有在逾 → 不提额

---

### 步骤10: 主表整合(darren_jieqing_dt_base_table)

```sql
CREATE TABLE mx.darren_jieqing_dt_base_table AS
SELECT *,  -- t0~t9所有字段
  -- 6个AB测试标签
  CASE WHEN ... THEN 'v5_3.提额组'    -- new_limit_flag
       WHEN ... THEN 'v5_3.对照组'
  END AS new_limit_flag,
  
  CASE WHEN ... THEN 'v5_3-全局额度cap测试组'  -- global_limit_cap_test_tag
       WHEN ... THEN 'v5_3-全局额度cap冠军组'
  END AS global_limit_cap_test_tag,
  
  -- 同理: single_increase_limit_cap_test_tag, daily_max_limit_tag, 
  --       limit_recommend_grp, first_settle_sha256
FROM (t0 LEFT JOIN t1 LEFT JOIN t2 ... LEFT JOIN t9)
```

**AB测试标签的生成逻辑**:

所有标签使用相同的hash算法:
```sql
from_base(substr(to_hex(sha256(to_utf8(token || key_field || app_group_sha256))),1,4),16) / 65536
```

**算法解析**:
1. `token || key_field || app_group_sha256`: 拼接盐值+关联字段+app_group
2. `sha256(to_utf8(...))`: SHA256哈希
3. `to_hex(...)`: 转十六进制
4. `substr(...,1,4)`: 取前4位
5. `from_base(...,16)`: 十六进制转十进制
6. `/ 65536`: 归一化到0~1之间(因为4位十六进制最大=65535)

**分组规则**:
- `>= 0.5`: 提额组(50%)
- `< 0.5`: 对照组(50%)
- `>= 0.7`: 测试组(30%)
- `< 0.7`: 冠军组(70%)

**工作中怎么用**: 分析AB测试效果时，按这些标签分组对比:
```sql
-- 例如: 提额组 vs 对照组的放款金额差异
SELECT new_limit_flag, AVG(contract_amount)
FROM darren_shouci_jieqing_summary_table
GROUP BY new_limit_flag
```

---

### 步骤11: 关联结清后进件(darren_jieqing_dt_table)

```sql
CREATE TABLE mx.darren_jieqing_dt_table AS
SELECT t0.*, t1.create_time, t1.app_time, t1.biz_id
FROM darren_jieqing_dt_base_table t0
LEFT JOIN (
  SELECT mid, create_time, app_time, biz_id
  FROM wxs_application_funnel
  WHERE is_settle_adjust_quota_flag = 1  -- 触发了调额的进件
) t1
ON t0.jq_mid = t1.mid
  AND t0.settle_time < t1.create_time  -- 结清后才进件
  AND date_diff('day', t0.settle_time, t1.create_time) < 5  -- 5天内进件
```

**逻辑**: 把结清记录关联到结清后5天内的进件记录。只有触发调额的进件才关联。

---

### 步骤12: 首次结清用户筛选(darren_shouci_jieqing_dt_table)

```sql
CREATE TABLE mx.darren_shouci_jieqing_dt_table AS
SELECT *
FROM (
  SELECT *,
    ROW_NUMBER() OVER(PARTITION BY jq_mid ORDER BY settle_time) AS rn  -- 按用户取首次结清
  FROM darren_jieqing_dt_table
  WHERE date(settle_time) >= '2026-08-14'  -- ⚠️ 漏洞: 漏掉8月14日前
) t0
WHERE rn = 1  -- 只取首次
  AND max_overdue_day_30d_all <= 2  -- 30天最大逾期≤2天
  AND curr_ovd_cnt_this_app_group <= 0  -- 当前无在逾
  AND settle_adjust_quota_cnt = 0  -- 未成功调额过
  AND last_credit_amount_change_day_gap IN (3,4)  -- 上次额度变化3-4天前
```

**筛选条件解读**:
1. `rn=1`: 每个用户只取第一次结清
2. `max_overdue_day_30d_all<=2`: 近30天逾期不超过2天 → 低风险用户
3. `curr_ovd_cnt_this_app_group<=0`: 当前无在逾 → 信用良好
4. `settle_adjust_quota_cnt=0`: 之前没成功调过额 → 首次调额实验
5. `last_credit_amount_change_day_gap IN (3,4)`: 上次额度变化3-4天前 → 结清后3-4天调额

---

### 步骤13: 多窗口汇总(darren_shouci_jieqing_summary_table)

```sql
-- 7天窗口
sum(case when date_diff('day', settle_time, app_time) <= 7 
         then 1 else 0 end) as new_customer_loan_cnt_7d,
sum(case when date_diff('day', settle_time, app_time) <= 7 
         then contract_amount else 0 end) as new_customer_loan_amount_7d,
-- 同理: 14/21/28/35/42/49/56/63天 + 30/60/90/120/150/180天
```

**逻辑**: 按不同时间窗口统计结清后的进件笔数、放款金额、逾期率等指标。

**工作中怎么用**: 对比不同窗口的转化率，判断提额效果:
```sql
-- 7天转化率 vs 14天转化率
-- 如果7天→14天转化率大幅提升，说明提额刺激了用户的借贷需求
new_customer_loan_cnt_14d / new_customer_loan_cnt_7d
```

---

# 第三部分: 03墨西哥风险等级划分.sql

## 3.1 这张表是做什么的？

这张表是**审批漏斗的完整宽表**，把每笔进件从申请到放款的每个审批节点的通过/拒绝状态整合到一起。用于计算通过率、转化率、各节点的拒绝原因。

**一句话理解**: 每笔进件 → 经过22个审批节点 → 每个节点是否进入/通过/拒绝 → 最终是否放款

## 3.2 整体数据流向

```
s05_creditx_order (进件主表)
    ↓
LEFT JOIN 22个审批节点 (p1~p22)
    ↓ 每个节点: 是否进入(if_in) / 是否通过(if_passed) / 是否拒绝(if_refused)
LEFT JOIN s09_os_credit_snapshot (额度快照)
LEFT JOIN s02_loan (放款信息)
LEFT JOIN gm_attribution_detail (渠道归因)
LEFT JOIN s03_product_due (产品期限)
LEFT JOIN s02_loan_repayment (应还金额)
LEFT JOIN s08_app_category_mapping (app分组)
    ↓
darren_risk_wide_table (最终宽表)
```

## 3.3 逐段代码逻辑

### 步骤1: 高通过组标签(tmp_wenj_product_table)

```sql
INSERT INTO mx.tmp_wenj_product_table
SELECT biz_id,
  MAX(credit_amount),           -- 授信额度
  MAX(daily_max_available_limit), -- 日最大可用额度
  etl_date
FROM s21_risk_strategy_record
WHERE productid IN (195,196,217,304)  -- 复贷授信决策流的产品
  AND strategytype = 'CHAMPION'
  AND etl_date >= date_add('day',-1,current_date)  -- 只取昨天
```

**逻辑**: 从风险策略记录中提取复贷授信决策流的额度和日最大可用额度。

---

### 步骤2: 主表关联(darren_risk_wide_table)

#### 主表a: darren_application_funnel_1

```sql
FROM mx.darren_application_funnel_1 a  -- 进件漏斗主表
```

这是01风险宽表生成的application_funnel_1表，包含进件、放款、贷后、渠道信息。

#### 宽表b: 22个审批节点

```sql
LEFT JOIN (
  SELECT t0.biz_id,  -- 进件ID
    -- 渠道相关
    app_channel, app_group, new_media_source, campaign_name,
    
    -- 反欺诈节点 (p1-p4)
    if_in_shou_anti_fraud,      -- 是否进入首贷强反欺诈
    if_shou_anti_fraud_passed,  -- 首贷强反欺诈是否通过
    if_shou_anti_fraud_refused, -- 首贷强反欺诈是否拒绝
    
    -- 模型节点 (p5-p6)
    if_in_shou_model,           -- 是否进入首贷模型
    if_shou_model_passed,       -- 首贷模型是否通过
    
    -- 人审节点 (p7-p8)
    if_in_shou_normal_check,    -- 是否进入首贷人审
    if_shou_normal_check_passed,
    if_shou_manual_check_pending, -- 是否在人审等待中
    
    -- 三方数据节点 (p9-p10)
    if_in_shou_external_data,   -- 是否进入首贷三方数据
    
    -- 规则节点 (p11-p12)
    if_in_shou_normal_rule_check,
    
    -- AI节点 (p13-p14)
    if_in_sd_ai,                -- 是否进入电核
    if_shou_ai_passed,
    
    -- 授信等待节点 (p15)
    if_in_sx,                   -- 是否进入授信等待
    if_sx_passed,
    
    -- 后置节点 (p16-p22)
    if_in_post_model,           -- 后置模型
    if_in_fu_sx_refuse,         -- 复贷授信拒绝
    if_in_shou_free_model,      -- 首贷免费模型
    if_in_shou_anti_fraud_rerun, -- 强反重跑
    if_in_shou_loan_refuse,     -- 放款拒绝
    
    -- 额度字段
    grantcredit_7d_amount,      -- 7天可用额度
    grantcredit_14d_amount,     -- 14天可用额度
    contract_amount,             -- 合同金额
    should_capital,              -- 应还本金
    should_interest              -- 应还利息
  FROM s05_creditx_order t0  -- 进件主表
  LEFT JOIN p1 ON ...  -- 22个审批节点
  LEFT JOIN p2 ON ...
  ...
) b ON a.biz_id = b.t0_biz_id
```

#### 22个审批节点详解

每个节点的SQL结构相似，以p1(首贷强反欺诈)为例:

```sql
LEFT JOIN (
  SELECT DISTINCT biz_id,
    1 AS if_in_shou_anti_fraud,  -- 有记录=进入了这个节点
    CASE WHEN SUM(CASE WHEN approve_result = 'REFUSED' THEN 1 END) IS NULL 
         THEN 1 ELSE 0 END AS if_shou_anti_fraud_passed,  -- 无拒绝=通过
    CASE WHEN SUM(CASE WHEN approve_result = 'REFUSED' THEN 1 END) >= 1 
         THEN 1 ELSE 0 END AS if_shou_anti_fraud_refused  -- 有拒绝=拒绝
  FROM s05_creditx_processor_record
  WHERE current_processor = '首贷强反欺诈'  -- 节点名称
  GROUP BY biz_id
) p1 ON t0.biz_id = p1.biz_id
```

**22个节点完整列表**:

| 编号 | 节点名称 | current_processor | 首贷/复贷 | 通过逻辑 |
|------|---------|-------------------|----------|---------|
| p1 | 首贷强反欺诈 | 首贷强反欺诈 | 首贷 | 无REFUSED=通过 |
| p2 | 复贷强反欺诈 | 复贷强反欺诈 | 复贷 | 无REFUSED=通过 |
| p3 | 首贷弱反欺诈 | 首贷弱反欺诈 | 首贷 | 无REFUSED=通过 |
| p4 | 复贷弱反欺诈 | 复贷弱反欺诈 | 复贷 | 无REFUSED=通过 |
| p5 | 首贷模型 | 首贷模型拒绝/首贷模型拒绝(低成本) | 首贷 | 无REFUSED=通过 |
| p6 | 复贷模型 | 复贷模型拒绝 | 复贷 | 无REFUSED=通过 |
| p7 | 首贷人审 | 首贷初审/人审节点 | 首贷 | 有PASSED=通过 |
| p8 | 复贷人审 | 复贷初审 | 复贷 | 有PASSED=通过 |
| p9 | 首贷三方 | 首贷三方节点/首贷三方测试节点 | 首贷 | 无REFUSED=通过 |
| p10 | 复贷三方 | 复贷三方节点 | 复贷 | 无REFUSED=通过 |
| p11 | 首贷规则 | 人审规则节点/人审规则节点_ios | 首贷 | myDecisionResult=Normal |
| p12 | 复贷规则 | 复贷人审规则 | 复贷 | myDecisionResult is null |
| p13 | 电核AI | 电核规则节点 | 首贷 | 有PASSED=通过 |
| p14 | FDAI | FDAI | 复贷 | 有PASSED=通过 |
| p15 | 授信等待 | 首贷授信等待节点/复贷授信等待节点 | 首贷+复贷 | 有PASSED=通过 |
| p16 | 后置模型 | 首贷后置模型拒绝节点 | 首贷 | 有PASSED=通过 |
| p17 | 复贷授信拒绝 | 复贷授信拒绝 | 复贷 | 有PASSED=通过 |
| p18 | 免费模型 | 首贷免费模型拒绝节点 | 首贷 | 有PASSED=通过 |
| p19 | 强反重跑 | 首贷后置强反重跑节点 | 首贷 | 有PASSED=通过 |
| p20 | 弱反重跑 | 首贷后置弱反重跑节点 | 首贷 | 有PASSED=通过 |
| p21 | 后置模型重跑 | 首贷后置模型拒绝重跑节点 | 首贷 | 有PASSED=通过 |
| p22 | 放款拒绝 | 放款拒绝节点 | 首贷 | 有PASSED=通过 |

#### 审批流程图

```
进件申请
    ↓
[前置节点] p1-p6: 强反欺诈 → 弱反欺诈 → 模型拒绝
    ↓ 通过的
[人审节点] p7-p8: 初审(人审) → 规则节点
    ↓ 通过的
[三方数据] p9-p10: 三方数据验证
    ↓ 通过的
[AI节点] p13-p14: 电核/FDAI
    ↓ 通过的
[授信等待] p15: 授信等待节点
    ↓ 通过的
[后置节点] p16-p22: 后置模型 → 重跑节点 → 放款拒绝
    ↓ 通过的
放款
```

**工作中怎么用**: 计算各节点的通过率和漏斗转化:
```sql
-- 首贷通过率 = 放款量 / 进件量
SELECT 
  SUM(if_issue) / COUNT(*) AS approval_rate,
  -- 强反欺诈通过率
  SUM(if_shou_anti_fraud_passed) / SUM(if_in_shou_anti_fraud) AS anti_fraud_pass_rate,
  -- 模型通过率
  SUM(if_shou_model_passed) / SUM(if_in_shou_model) AS model_pass_rate
FROM darren_risk_wide_table
WHERE double_loan_2 = 0  -- 首贷
```

#### c表: 授信等待节点时效

```sql
LEFT JOIN (
  SELECT biz_id,
    -- 24小时内通过: 到现在已超24h + 在24h内通过
    CASE WHEN approve_result='PASSED' 
         AND date_diff('minute', create_time, update_time) <= 24*60  -- 24h内通过
         AND date_diff('minute', create_time, now()) >= 24*60         -- 距今已超24h
    THEN 1 ELSE 0 END AS if_sx_passed_within24h,
    -- 同理: 48h/72h/120h/11h
    -- 超过N小时未通过
    CASE WHEN date_diff('minute', create_time, now()) >= 24*60 
    THEN 1 ELSE 0 END AS if_in_sx_over24h,
    -- 未超过N小时
    CASE WHEN date_diff('minute', create_time, now()) < 24*60 
    THEN 1 ELSE 0 END AS if_in_sx_within24h
FROM s05_creditx_processor_record
WHERE current_processor IN ('首贷授信等待节点','复贷授信等待节点')
) c ON a.biz_id = c.biz_id
```

**逻辑**: 统计授信等待节点的时效——多少用户在24/48/72/120小时内通过，多少超过这些时间还未通过。

**工作中怎么用**: 监控授信等待节点的处理效率:
```sql
-- 24小时通过率 = 24h内通过 / 超过24h的总数
SUM(if_sx_passed_within24h) / SUM(if_in_sx_over24h)
```

#### e表: 首复贷标签

```sql
LEFT JOIN (
  SELECT externalid, double_loan_tenant
  FROM s21_risk_strategy_record
  WHERE productid IN (310,330,331)
    AND strategytype = 'CHAMPION'
    AND etl_date >= '20250101'
) e ON a.biz_id = e.externalid
```

**逻辑**: 从风险策略记录中提取首复贷标签，优先使用e表的，其次用b表的double_loan。

#### f表: 高通过组标签

```sql
LEFT JOIN (
  SELECT biz_id, credit_amount, daily_max_available_limit
  FROM tmp_wenj_product_table  -- 步骤1的临时表
) f ON a.biz_id = f.biz_idf
```

**逻辑**: 关联步骤1提取的复贷授信额度和日最大可用额度。

---

# 第四部分: 三表关系总结

## 4.1 数据流向关系图

```
                    s09_os_credit_snapshot (授信快照/进件)
                           ↓
    ┌──────────────────────┼──────────────────────┐
    ↓                      ↓                      ↓
01风险宽表            02风险结清表           03风险等级划分
(贷后 vintage)        (结清调额 AB测试)      (审批漏斗 22节点)
    ↓                      ↓                      ↓
wxs_application_       darren_jieqing_       darren_risk_
funnel (最终宽表)      dt_table              wide_table
    ↓                      ↓                      ↓
    └──────────→ 周报/LTV ←──────┘                      │
                       ↑                                │
                       └────────────────────────────────┘
                  03表的主表a = 01表的application_funnel_1
```

## 4.2 三表对比

| 维度 | 01风险宽表 | 02风险结清表 | 03风险等级划分 |
|------|-----------|-------------|--------------|
| **关注阶段** | 贷后(放款后) | 结清后(还清后) | 贷前(审批中) |
| **核心数据源** | s02_loan, s02_loan_repayment | s21_risk_strategy_record | s05_creditx_order, s05_creditx_processor_record |
| **核心指标** | 逾期率, 坏账率, vintage | 提额效果, AB测试 | 通过率, 转化率, 节点时效 |
| **时间窗口** | T0/T3/T7/T14/T30 | 7/14/21...180天 | 11h/24h/48h/72h/120h |
| **产出表** | wxs_application_funnel | darren_shouci_jieqing_summary | darren_risk_wide_table |
| **周报用途** | 1T0/1T7逾期率, 坏账 | (未来)结清提额效果 | 进件漏斗, 通过率 |

## 4.3 工作中的使用场景

### 场景1: 周报数据
```sql
-- 从01表的wxs_application_funnel取
-- 进件量 = COUNT(biz_id)
-- 放款量 = SUM(if_issue)
-- 通过率 = SUM(if_issue) / COUNT(*)
-- 1T0逾期率 = (t0_should - t0_fact) / t0_should
```

### 场景2: Vintage坏账分析
```sql
-- 从01表的wxs_vintage_all4取
-- 第1期T30坏账率 = overdue_amount_1_30 / should_capital_1_30
-- 按放款月分组 = GROUP BY DATE_TRUNC('month', release_time)
```

### 场景3: AB测试效果分析
```sql
-- 从02表的darren_shouci_jieqing_summary_table取
-- 提额组 vs 对照组的放款金额
SELECT new_limit_flag, AVG(new_customer_loan_amount_7d)
GROUP BY new_limit_flag
```

### 场景4: 审批漏斗监控
```sql
-- 从03表的darren_risk_wide_table取
-- 各节点通过率
SELECT 
  SUM(if_shou_anti_fraud_passed) / NULLIF(SUM(if_in_shou_anti_fraud), 0) AS anti_fraud_rate,
  SUM(if_shou_model_passed) / NULLIF(SUM(if_in_shou_model), 0) AS model_rate,
  SUM(if_shou_normal_check_passed) / NULLIF(SUM(if_in_shou_normal_check), 0) AS manual_rate
WHERE double_loan_2 = 0  -- 首贷
```

### 场景5: 授信等待时效监控
```sql
-- 从03表的c表字段取
-- 24小时通过率
SELECT 
  SUM(if_sx_passed_within24h) / NULLIF(SUM(if_in_sx_over24h), 0) AS within24h_rate
FROM darren_risk_wide_table
```

---

# 第五部分: 关键概念解释

## 5.1 TTL(Time To Letter)

TTL是"时间到信"的缩写，在信贷领域指**从放款到出现逾期的时间**。本表中的T0/T3/T7/T14/T30表示:
- T0: 到期日当天
- T3: 到期后3天
- T7: 到期后7天
- T14: 到期后14天
- T30: 到期后30天

## 5.2 Vintage分析

Vintage分析源自葡萄酒酿造年份的概念，在信贷领域指**按放款月份追踪不同账龄(MOB)的坏账率**。

```
放款月    MOB1    MOB2    MOB3    MOB6    MOB12
2026-01   2.1%    3.5%    5.2%    8.1%    12.3%
2026-02   2.3%    3.8%    5.5%    8.5%
2026-03   1.9%    3.2%    4.8%
```

**用途**: 横向比较不同月份放款的质量，纵向观察坏账随账龄的变化趋势。

## 5.3 MOB(Month On Book)

MOB是"账龄"的概念，MOB1表示放款后第1个月，MOB3表示放款后第3个月。

## 5.4 AB测试hash分组

```sql
from_base(substr(to_hex(sha256(to_utf8('token' || key || app_group))),1,4),16) / 65536
```

**为什么用hash**: 确保同一用户每次计算结果一致(确定性)，且分布均匀(随机性)。

**为什么拼接app_group**: 确保不同app_group的用户独立分组，避免一个app的测试影响另一个app。

## 5.5 首复贷判断

| 方法 | 数据源 | 判断逻辑 | 优点 | 缺点 |
|------|--------|---------|------|------|
| s21风险策略 | s21_risk_strategy_record | double_loan_tenant字段 | 最准确(风险决策流判定) | 依赖s21更新 |
| 放款次数 | s02_loan + s09 | issue_num=1为首贷 | 历史数据完整 | 不含风险策略判断 |
| 渠道硬编码 | app_channel | 11个特定渠道=复贷 | 简单直接 | 维护成本高 |

---

# 第六部分: 已知漏洞索引

| 表 | 严重漏洞数 | 中等漏洞数 | 低风险数 | 详见 |
|----|----------|----------|---------|------|
| 01风险宽表 | 4 | 4 | 2 | 墨西哥风险宽表_漏洞清单.md |
| 02风险结清表 | 4 | 4 | 2 | 墨西哥风险结清表_漏洞清单.md |
| 03风险等级划分 | 4 | 4 | 2 | 墨西哥风险等级划分_漏洞清单.md |

**最严重的3个漏洞**:
1. **01表漏洞1**: indexs=3的7天字段用了3天的值(复制粘贴Bug)
2. **01表漏洞3**: 还款明细跨期交叉Join，金额重复计算
3. **02表漏洞1**: settle_time取首贷app_time而非结清时间，导致所有时间窗口统计错误
