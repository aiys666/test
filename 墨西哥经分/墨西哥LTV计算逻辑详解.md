# 墨西哥 LTV 计算逻辑详解

> 面向小白的从头到尾完整解读。读完这篇文档，你将理解：每一行SQL在做什么、每个Excel Sheet在算什么、最终结果怎么看。

---

## 目录

1. [前置概念：什么是 LTV](#一前置概念什么是-ltv)
2. [数据来源：三张核心表](#二数据来源三张核心表)
3. [SQL 第一步：首贷数据提取](#三sql-第一步首贷数据提取)
4. [SQL 第二步：投放成本计算](#四sql-第二步投放成本计算)
5. [SQL 第三步：首贷 CAC 汇总](#五sql-第三步首贷-cac-汇总)
6. [SQL 第四步：复贷数据提取](#六sql-第四步复贷数据提取)
7. [SQL 第五步：复贷按 WOB 聚合](#七sql-第五步复贷按-wob-聚合)
8. [SQL 第六步：WOB 序列补全](#八sql-第六步wob-序列补全)
9. [Excel 处理逻辑](#九excel-处理逻辑)
10. [如何阅读结果](#十如何阅读结果)

---

## 一、前置概念：什么是 LTV

### 1.1 业务场景

墨西哥现金贷业务：用户第一次借款（**首贷**）→ 还清后再次借款（**复贷**）→ 反复循环。

**核心问题**：花 $X 广告费获取一个首贷用户，这个人一辈子能给我们赚回多少钱？

### 1.2 LTV 定义

> **LTV（Lifetime Value，用户终身价值）= 该用户带来的全部利润**

```
LTV = 首贷利润 + 第1次复贷利润 + 第2次复贷利润 + ... + 第N次复贷利润
```

如果 LTV > 获客成本，投放就是赚钱的；如果 LTV < 获客成本，投放亏损。

### 1.3 关键维度：WOB（Week on Book）

**WOB = 距离首贷过去了多少周**

- WOB 0：首贷当周
- WOB 1：首贷后第1周
- WOB 2：首贷后第2周
- ...
- WOB 110：首贷后约2年

通过 WOB，我们把复贷行为按时间线展开，看到"用户在第几周又借钱了、借了多少、产生了多少利润"。

### 1.4 分组维度

每个月放款的用户被分为不同的**群组（Cohort）**，按四个维度切分：

| 维度 | 含义 | 示例 |
|------|------|------|
| ltv_month | 首贷月份 | 2026-01 |
| app_channel | 投放渠道 | TG / YW / HL / Balam Plata ... |
| new_grade_level | 用户信用等级 | 1~6 (数字越小越好) |
| loan_cycle | 首贷期限(天) | 7 / 14 / 21 / 28 / 30 |

每个群组独立追踪其后续的复贷行为。

---

## 二、数据来源：三张核心表

### 2.1 `mx.wxs_application_funnel` — 放款主表

每一行 = 一笔放款订单。关键字段：

| 字段 | 含义 | 用途 |
|------|------|------|
| camera_id | 订单ID | 唯一标识一笔借款 |
| cust_id | 用户ID | 关联同一个人的多笔订单 |
| release_time | 放款时间 | 确定月份和周 |
| is_reloan | 是否复贷 | 'new'=首贷, 'old'=复贷 |
| if_issue | 是否放款成功 | 1=成功, 只取成功的 |
| contract_amount | 合同金额(比索) | 借款本金 |
| haircut_amount | 砍头息(比索) | 放款时先扣掉的利息 |
| should_interest | 应还利息(比索) | 借款期内产生的利息 |
| should_capital | 应还本金(比索) | = contract_amount |
| loan_cycle | 借款期限(天) | 7/14/21/28/30 |
| app_channel | 渠道标识(UUID) | 关联投放数据 |
| tN_should_amt_4 | 第N天应还总额 | N=7,30 |
| tN_overdue_amount_4 | 第N天逾期金额 | N=7,30 |
| tN_should_capit_4 | 第N天应还本金 | N=7,30 |

### 2.2 `dwd.dwd_ads_cost` — 投放成本表

每一行 = 某天某个App的投放花费(USD)。关键字段：

| 字段 | 含义 |
|------|------|
| ad_date | 投放日期 |
| app_channel_name | App包名(如 `com.tiri.mx`) |
| spend_usd | 当日花费(美元) |

### 2.3 `dim.dim_exchange_rate_cost` — 汇率表

| 字段 | 含义 |
|------|------|
| month_id | 月份(如 `202608`) |
| account_currency | 币种(`MXN`) |
| exchange_rate_to_dollar | 该币种→美元的汇率 |

---

## 三、SQL 第一步：首贷数据提取

**产出表**：`mx.ys_dl_ltv_first_loan_0511`

### 3.1 SQL 语句逐段解读

```sql
drop table if exists mx.ys_dl_ltv_first_loan_0511;
create table mx.ys_dl_ltv_first_loan_0511 as
select
    date_trunc('month', date(r.release_time)) as ltv_month,   -- 放款月份(如2026-01-01)
    date_trunc('week', date(r.release_time)) as ltv_week,     -- 放款周(用于后续WOB计算)
    r.loan_cycle,                                              -- 借款期限(天)
    r.app_channel,                                             -- 渠道UUID
    r.app_group as app_channel_name,                           -- 渠道显示名称
    coalesce(f7.credit_level, 9999) as new_grade_level,       -- 信用等级(空值→9999)
    ...
```

### 3.2 渠道归因：从归因表获取媒体来源

```sql
left join mx.gm_attribution_detail att on cast(r.cust_id as bigint) = att.mid
```

用 `att.new_media_source` 判断用户来自哪个广告平台：

```sql
case
    when lower(att.new_media_source) = 'facebook' then 'facebook'
    when lower(att.new_media_source) = 'google' then 'google'
    when lower(att.new_media_source) = 'tiktok' then 'tiktok'
    when lower(att.new_media_source) = 'apple search ads' then 'Apple Search Ads'
    when lower(att.new_media_source) = 'organic' then 'organic'
    else 'other'
end as register_media_source
```

### 3.3 核心计算字段

```sql
-- 息费率 = (砍头息 + 应还利息) / 合同金额
-- 这是这笔贷款的"收益率"
(coalesce(r.haircut_amount, 0) + coalesce(r.should_interest, 0))
    / nullif(r.contract_amount, 0) as fee

-- 应还总额 = 利息 + 本金
r.should_interest + r.should_capital as should_amt

-- T+7 应还总额
r.t7_should_amt_4 as should_amt_t7

-- T+30 应还总额
r.t30_should_amt_4 as should_amt_t30

-- T+7 实际还款金额 = 应还总额 - 逾期金额
r.t7_should_amt_4 - r.t7_overdue_amount_4 as fact_t7

-- T+30 实际还款金额
r.t30_should_amt_4 - r.t30_overdue_amount_4 as fact_t30

-- T+0 是否还款(1=还了, 0=没还)
case when r.t0_should_amt_4 - r.t0_overdue_amount_4 > 0 then 1 else 0 end as fact_cnt_t0

-- T+7 是否还款
case when r.t7_should_amt_4 - r.t7_overdue_amount_4 > 0 then 1 else 0 end as fact_cnt_t7

-- T+30 是否还款
case when r.t30_should_amt_4 - r.t30_overdue_amount_4 > 0 then 1 else 0 end as fact_cnt_t30
```

### 3.4 筛选条件

```sql
where r.is_reloan = 'new'    -- 只要首贷
  and r.if_issue = 1;        -- 只要放款成功的
```

**总结**：这一步从放款表中取出所有首贷订单，附上信用等级和媒体归因，计算每笔订单的息费率、应还金额、实际还款金额。

---

## 四、SQL 第二步：投放成本计算

**产出表**：`mx.ys_mx_ltv_ads_cost`

### 4.1 App → 渠道映射

墨西哥有21个App，但很多App属于同一个渠道品牌。例如 YW(Yawey) 旗下有6个App：

```sql
with channel_mapping as (
    select app_key, app_channel
    from (values
        ('com.tiri.mx',                                  'TG_UUID'),
        ('com.tengoprestamos.cash.credito.mx',           'TG_UUID'),
        ('com.cash.prestamo.yaweycredito',               'YW_UUID'),
        ('com.cash.rapido.dinero.credito.yawey',         'YW_UUID'),
        -- ... 共21条映射
    ) as t(app_key, app_channel)
)
```

映射结果：21个App → 9个渠道品牌。

### 4.2 按天汇总花费

```sql
select
    date(c.ad_date) as ad_date,                    -- 日期
    date_trunc('month', date(c.ad_date)) as ad_month, -- 月份
    coalesce(cm.app_channel, 'other') as app_channel, -- 渠道
    sum(c.spend_usd) as spend_usd                     -- 当日总花费(美元)
from dwd.dwd_ads_cost c
left join channel_mapping cm
    on c.app_channel_name = cm.app_key
where cast(c.ad_date as date) > date '2025-01-01'
group by 1, 2, 3
```

**总结**：把投放花费从 App 粒度汇总到渠道粒度，按天记录。

---

## 五、SQL 第三步：首贷 CAC 汇总

**产出表**：`mx.ys_mx_ltv_first_loan_cac`

这是整个计算中最核心的聚合步骤。将首贷数据和投放成本关联起来。

### 5.1 首贷聚合 (CTE: first_loan_agg)

```sql
with first_loan_agg as (
    select
        ltv_month,                                          -- 按月份
        loan_cycle,                                         -- 按期限
        app_channel,                                        -- 按渠道
        app_channel_name,                                   -- 按渠道名
        new_grade_level,                                    -- 按信用等级
        count(distinct biz_id) as frs_cnt,                 -- 首贷订单数
        sum(contract_amount) as contract_amount,            -- 总合同金额
        sum(contract_amount) / nullif(count(distinct biz_id), 0) as avg_amount,  -- 笔均金额
        sum(fee * contract_amount) / nullif(sum(contract_amount), 0) as fee,      -- 加权平均息费率
        sum(fee * contract_amount) as fee_amount,           -- 总息费金额
        sum(should_amt) as should_amt,                      -- 总应还金额
        sum(should_amt_t7) as should_amt_t7,               -- T+7 总应还
        sum(should_amt_t30) as should_amt_t30,             -- T+30 总应还
        sum(fact_t7) as fact_t7,                            -- T+7 总实还
        sum(fact_t7_coup) as fact_t7_coup,                 -- T+7 总实还(券后)
        sum(fact_t30) as fact_t30,                          -- T+30 总实还
        sum(fact_t30_coup) as fact_t30_coup,               -- T+30 总实还(券后)
        sum(fact_cnt_t0) as fact_cnt_t0,                    -- T+0 还款笔数
        sum(fact_cnt_t7) as fact_cnt_t7,                    -- T+7 还款笔数
        sum(fact_cnt_t30) as fact_cnt_t30                   -- T+30 还款笔数
    from mx.ys_dl_ltv_first_loan_0511
    group by 1, 2, 3, 4, 5
)
```

### 5.2 投放成本分配 (CTE: cost, total_cost, cost_rank)

问题：投放成本是按**月+渠道**粒度的，但首贷数据是**月+渠道+等级+期限**四维的。如何分配？

解法：**按合同金额比例分配**。

```sql
cost_rank as (
    select
        ltv_month,
        app_channel_name,
        new_grade_level,
        loan_cycle,
        row_number() over(
            partition by ltv_month, app_channel_name
            order by contract_amount desc
        ) as cost_rnk
    from first_loan_agg
)
```

`cost_rnk=1` 表示该月该渠道下合同金额最大的那个（等级×期限）组合。投放成本全部归到这个组合上（简化处理）。

### 5.3 汇率转换

```sql
left join dim.dim_exchange_rate_cost d
    on date(DATE_PARSE(d.month_id, '%Y%m')) = f.ltv_month
    and d.account_currency = 'MXN'
```

所有比索金额乘以 `exchange_rate_to_dollar` 转为美元。

**总结**：这一步产出了每个 **月份×渠道×等级×期限** 组合的关键指标：放款笔数、金额、息费率、T+7/T+30 还款情况，以及对应的投放花费。

---

## 六、SQL 第四步：复贷数据提取

**产出表**：`mx.ys_dl_ltv_double_loan_0511`

### 6.1 核心逻辑

```sql
select
    d.ltv_month,                                              -- 继承首贷的月份
    d.ltv_week,                                               -- 继承首贷的周
    date_diff('week', d.ltv_week, date_trunc('week', date(r.release_time))) as wob,
    -- ↑ 这是最关键的字段：WOB = 复贷周 - 首贷周
    -- 例如：首贷在2026年第3周，复贷在2026年第5周 → WOB = 2
    ...
from mx.wxs_application_funnel r
left join mx.ys_dl_ltv_first_loan_0511 d
    on cast(r.cust_id as bigint) = d.mid     -- 通过用户ID关联回首贷
    ...
where r.is_reloan = 'old'                    -- 只要复贷
  and r.if_issue = 1                         -- 放款成功的
  and d.mid is not null;                     -- 必须能关联回首贷
```

### 6.2 关联逻辑图解

```
首贷表 (ys_dl_ltv_first_loan_0511)
┌────────┬──────────┬──────────┬─────────┐
│ mid    │ ltv_month│ ltv_week │ channel │
├────────┼──────────┼──────────┼─────────┤
│ 用户A  │ 2026-01  │  Wk3     │ YW      │
│ 用户B  │ 2026-01  │  Wk4     │ TG      │
└────────┴──────────┴──────────┴─────────┘
         │
         │ left join on cust_id = mid
         ▼
复贷表 (wxs_application_funnel, is_reloan='old')
┌────────┬──────────┬──────────────┬───────────┐
│ cust_id│ release  │ contract_amt │ ...       │
├────────┼──────────┼──────────────┼───────────┤
│ 用户A  │ Wk5      │ 5000         │           │ ← WOB = 5-3 = 2
│ 用户A  │ Wk8      │ 3000         │           │ ← WOB = 8-3 = 5
│ 用户B  │ Wk6      │ 8000         │           │ ← WOB = 6-4 = 2
└────────┴──────────┴──────────────┴───────────┘
```

用户A的首贷在Wk3 → 后续在Wk5、Wk8各复贷一次 → WOB分别为2和5。

### 6.3 金额转美元

```sql
left join dim.dim_exchange_rate_cost f
    on date(DATE_PARSE(f.month_id, '%Y%m'))=date(date_format(r.release_time,'%Y-%m-01'))
    and f.account_currency = 'MXN'
```

```
contract_amount_usd = contract_amount(比索) / exchange_rate_to_dollar
```

---

## 七、SQL 第五步：复贷按 WOB 聚合

**产出表**：`mx.ys_dl_ltv_double_loan_group`

### 7.1 聚合维度

```sql
select
    ltv_month as ltv_month_d,         -- 首贷月份
    wob as wob_d,                     -- 第几周
    app_channel_name as app_channel_name_d,  -- 渠道
    loan_cycle as loan_period,        -- 首贷期限
    new_grade_level as new_grade_level_d,    -- 信用等级
    count(distinct biz_id) as double_cnt,    -- 复贷笔数
    count(distinct mid) as double_mid,       -- 复贷人数
    sum(contract_amount) as contract_amount, -- 复贷总金额
    sum(haircut_amount+should_interest) as fee_amount,  -- 总息费
    ...
```

### 7.2 一行数据的含义

```
ltv_month_d = 2026-01, wob_d = 3, channel = YW, grade = 2, period = 14
→ 2026年1月通过YW渠道获取的、信用等级2、首贷期限14天的用户
→ 在首贷后第3周内，共计复贷了XX笔、总金额XX、总息费XX
```

---

## 八、SQL 第六步：WOB 序列补全

**为什么需要补全？** 有些群组在某些WOB周没有复贷数据，但为了计算累计值，需要这些"空周"存在一行（数据为0）。

### 8.1 生成完整WOB序列

```sql
with frst_loan as (
    select ltv_month, app_channel_name, new_grade_level,
           count(distinct mid) as frs_cnt,
           sum(contract_amount) as frs_contract_amount
    from mx.ys_dl_ltv_first_loan_0511
    group by 1, 2, 3
),
all_combinations as (
    select g.ltv_month, g.app_channel_name, g.new_grade_level, w.wob
    from frst_loan g
    cross join (
        select wob
        from (select max(wob_d) as max_wob from mx.ys_dl_ltv_double_loan_group)
        cross join unnest(sequence(0, max_wob)) as t(wob)
    ) w
)
```

**图解**：
```
首贷群组 × WOB序列(0,1,2,...,max_wob) = 完整的 (月×渠道×等级×WOB) 矩阵

示例(仅1个月、2个渠道):
        WOB=0  WOB=1  WOB=2  ...
YW       ✓      ✓      ✓
TG       ✓      ✓      ✓
```

### 8.2 左连接补数据

```sql
double_combinations as (
    select c.*, a.*, row_number() over(...) as double_rnk
    from all_combinations c
    left join mx.ys_dl_ltv_double_loan_group a
        on a.ltv_month_d = c.ltv_month
        and a.app_channel_name_d = c.app_channel_name
        and a.new_grade_level_d = c.new_grade_level
        and a.wob_d = c.wob
)
```

有实际复贷数据的行 → 填充数值；没有的 → 字段为NULL（后续在Excel中处理为0）。

### 8.3 输出限制

```sql
where date(c.ltv_month) >= date '2023-02-01'   -- 2023年2月才开始有信用等级
  and c.wob <= 110                               -- 只看首贷后110周(约2年)
limit 100000;                                     -- 防止数据量过大
```

---

## 九、Excel 处理逻辑

### 9.1 Excel 文件结构总览

SQL跑出的数据 → 粘贴到 `数据源-首贷`、`数据源-复贷`、`数据源-汇率` 三个Sheet → 其余Sheet通过公式/透视表自动计算。

**可见Sheet（19个）按类别分层：**

```
┌──────────────────────────────────────────────┐
│              结果层（面向决策）                 │
│  等级汇总 | pivot_美金                         │
├──────────────────────────────────────────────┤
│              分析层（利润拆解）                 │
│  经营利润率 | 经营利润额 | 累计经营利润额        │
│  息费率 | 坏账T7% | 坏账T30%                   │
│  笔数复借率 | 复贷件均                          │
├──────────────────────────────────────────────┤
│              输入层（SQL原始数据）               │
│  数据源-首贷 | 数据源-复贷 | 数据源-汇率          │
└──────────────────────────────────────────────┘

隐藏Sheet（约20个）：中间计算过程，如各天数的合同金额、通过率等
```

### 9.2 数据源 Sheet

**数据源-首贷**：从 `ys_mx_ltv_first_loan_cac` 粘贴而来。

| 列 | 含义 | 示例 |
|----|------|------|
| ltv_month | 首贷月份 | 46174 (=2026-05-01) |
| loan_cycle | 期限 | 21 |
| app_channel_name | 渠道 | Tuna Cash |
| new_grade_level | 信用等级 | 1 |
| frs_cnt | 放款笔数 | 357 |
| contract_amount | 总合同金额(比索) | 1,143,000 |
| avg_amount | 件均(比索) | 3,201.68 |
| fee | 息费率 | 0.8779 |

**数据源-复贷**：从最终查询结果粘贴。

| 列 | 含义 | 示例 |
|----|------|------|
| ltv_month | 首贷月份 | 2026-01 |
| wob | 第几周 | 3 |
| app_channel_name | 渠道 | YW |
| new_grade_level | 信用等级 | 2 |
| double_cnt | 复贷笔数 | 15 |
| contract_amount | 复贷总金额 | 45,000 |
| fee_amount | 总息费 | 22,500 |

**数据源-汇率**：从 `dim_exchange_rate_cost` 粘贴。

### 9.3 等级汇总 Sheet —— 最核心的结果页

**每一行 = 一个首贷月份 × 一个期限 × 一个渠道 × 一个信用等级**

关键列解读：

| 列 | Excel公式逻辑 | 含义 |
|----|-------------|------|
| C: 首贷损益 | = 息费收入 - 坏账 - 其他成本 | 不算获客成本前，首贷本身的利润率 |
| D: 无获客成本损益 | = 首贷损益 + 获客成本 | 扣除获客成本后的利润率 |
| E: 获客成本 | = CPS / 件均 | 每美元放款对应的投放费用% |
| F: 首贷件均 | = contract_amount / frs_cnt | 笔均放款金额(美元) |
| G: 首贷人数 | = frs_cnt | 该群组的首贷人数 |
| H: 0M LTV | = 首贷利润 + WOB=0复贷利润 | 首贷当月内的LTV |
| I: 1M LTV | = 0M LTV + WOB=1~4复贷利润 | 首贷后1个月内的累计LTV |

**计算链示例**（一行数据）：
```
首贷放款: $24.22 (件均) × 3,167 人 = $76,702 合同金额

收入端: 息费率 87.7% → 息费收入 $67,257
成本端: CPS $22.47 → 获客成本 $71,120
       坏账 195% → 坏账损失 $149,761  (年化坏账率极高)
       其他成本 11% → $8,450

首贷损益 = 67,257 - 149,761 - 8,450 = -$90,954
首贷损益率 = -90,954 / 76,702 = -51.29%  ← 首贷亏51%

0M LTV = 首贷损益 + 当月复贷利润 = -$54.08
1M LTV = 0M LTV + 后续4周复贷利润 = -$55.12
```

### 9.4 经营利润率/经营利润额 Sheet

这两个Sheet展示按**WOB周**展开的利润率变化：

```
         WOB=0    WOB=1    WOB=2    WOB=3    ...
首贷     -1.82    —        —        —         
复贷     —        -0.05    -0.05    -0.05     ...
整体     -1.82    -0.05    -0.05    -0.05     ...
```

**关键发现**：复贷从 WOB=20 左右开始转正（经营利润率 > 0），之后持续贡献正利润。

### 9.5 累计经营利润额 Sheet

将每周利润累加起来：

```
WOB=0:  利润 -$12,308
WOB=1:  累计 -$12,308 + (-$81) = -$12,389
WOB=2:  累计 -$12,389 + (-$83) = -$12,472
...
WOB=82: 累计首次 > 0  → 转正！
```

**转正月数** = 转正WOB / 4.33 ≈ **19-21个月**

这是墨西哥业务最核心的指标：花$40获客，需要约20个月通过复贷利润收回。

### 9.6 息费率/坏账/复借率/件均 Sheet

这四个Sheet展示按WOB展开的各维度时间序列：

- **息费率**：WOB 0-7 用实际值，WOB 8+ 用预测值（测算系数 × 基准值）
- **坏账T7%/T30%**：T+7和T+30的坏账率（逾期/应还），随着WOB增大趋于稳定
- **笔数复借率**：每周复借人数 / 首贷总人数，WOB越大复借率衰减
- **复贷件均**：复贷的笔均金额，WOB后期明显提升（用户被"养大"）

**预测逻辑**：前7-12周用实际数据，后续用系数外推：

```
预测值 = 基准值 × (1 + 测算系数)
例如：息费率_WOB_8 = 0.6641 × (1 + 0.02) = 0.6774
```

---

## 十、如何阅读结果

### 10.1 看整体：等级汇总 Sheet

- **H列(0M LTV)**：首月LTV，判断首贷当月是否回本
- **I列(1M LTV)**：首月+后续1月LTV，判断短期是否回本
- 大多数群组的 LTV < 0（亏损），需要靠后续复贷覆盖

### 10.2 看趋势：累计经营利润额 Sheet

- 找**转正WOB**：累计利润从负变正的周数
- 越早转正 → 业务越健康
- 如果110周还没转正 → 这个渠道/等级永远亏钱

### 10.3 看结构：经营利润率 Sheet

- 复贷利润率是否在上升 → 用户质量在改善
- 首贷利润率是否在改善 → 风控/定价在优化

### 10.4 看细节：息费率/坏账/复借率

- 息费率是否稳定 → 定价策略一致性
- 坏账率是否可控 → 风控效果
- 复借率是否健康 → 用户粘性
- 件均是否增长 → 用户价值提升

---

## 附录：关键公式速查

### A.1 首贷指标

```
息费率(fee) = (砍头息 + 应还利息) / 合同金额
应还总额 = 应还利息 + 应还本金
实还金额(T+N) = 应还金额(T+N) - 逾期金额(T+N)
获客成本率 = CPS / 件均
首贷损益 = 息费收入率 - 坏账率 - 其他成本率
```

### A.2 复贷指标

```
WOB = 复贷放款周 - 首贷放款周
复借率 = 本周复借人数 / 首贷总人数
周经营利润 = 息费收入 - 坏账 - 其他成本
累计经营利润 = Σ(每周经营利润)
```

### A.3 LTV

```
LTV_nM = Σ(WOB=0 到 WOB=4n 的全部利润)
转正时间 = 累计利润首次 > 0 的WOB
```

---

> 最后更新：2026-07-31
> 数据来源：`mx.ys_dl_ltv_first_loan_0511` / `mx.ys_dl_ltv_double_loan_0511` / `mx.ys_dl_ltv_double_loan_group`
