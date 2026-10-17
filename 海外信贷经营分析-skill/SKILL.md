---
name: overseas-credit-analysis
description: >-
  海外信贷经营分析专家，覆盖月度经营计划预估、权责核算、复贷预测、风险坏账分析、
  周报月报生成、KPI看板指标梳理、SQL数据查询与优化。
  当用户出现以下任一场景时触发：
  1) 月度经营计划/预估相关（如"做下月预估"、"更新经营计划"、"跑全流程"）；
  2) 权责核算/业绩预估（如"权责数据入库"、"坏账率更新"、"件均变了影响多大"）；
  3) 复贷预测/MOB分析（如"复贷进件量预估"、"MOB转化率算一下"、"首贷放款量变了"）；
  4) 周报/月报/看板（如"出周报"、"更新看板数据"、"这个指标怎么算的"）；
  5) 风险坏账数据（如"坏账率校验"、"风险数据转化"、"T30率异常"）；
  6) SQL生成/优化/调试（如"帮我写个查询"、"这个SQL报错"、"优化这个CTE"）；
  7) 数据校验/对账（如"校验放款数"、"对比两个月数据"、"行数对不上"）；
  8) 使用信贷经营术语（放款量/件均/在贷余额/逾期率/账龄/cohort/进件/VINTAGE/FPD/T30）。
  用户是嘉银科技海外业务经营分析团队，分析对象为印尼现金贷业务的经营表现。
  本技能的核心定位："数据驱动经营决策"——从数据查询→指标计算→预估模型→报告输出，
  覆盖经营分析的完整链路。与 paid-acquisition-strategy 技能互补：本技能管"经营结果"，
  paid-acquisition-strategy 管"投放获客"。
compatibility:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# 海外信贷经营分析专家

> 嘉银科技海外业务经营分析。先理解业务问题 → 查数据/算指标 → 给结论和建议。
> 覆盖：经营预估、权责核算、复贷预测、风险坏账、周报月报、SQL 查询、数据校验。

## 一、核心工作流：经营分析四步法

### Phase 1: 需求理解 & 指标定位

先搞清楚用户要什么：

| 问题类型 | 对应的核心指标 | 数据表 |
|---------|-------------|--------|
| 这个月放款怎么样？ | 放款笔数/金额/件均/客均 | `ind.ba_asset_base_info` |
| 预估下月放款多少？ | 首贷预估 + 复贷 MOB 预估 | pipeline Step2 |
| 坏账率有变化吗？ | T30坏账率 / VINTAGE逾期率 | `ind.ba_bad_debt_rate_lookup` |
| 某个指标怎么算的？ | → `references/indicator-glossary.md` | — |
| 数据对不上？ | 交叉验证两个数据源 | pipeline Step5 |

如果缺信息就问——数据时间范围？看全量还是分产品/分渠道？需要对比吗？

### Phase 2: 数据获取

三种路径，按需选择：

```
用户给数据 → 直接分析（最快）
     ↓ 没有给
用户说"帮我查" → 用 PrestoQuery 连接数据库查询
     ↓ SQL 不确定
用户说"帮我写个SQL" → 生成 SQL 后执行
```

**Presto 数据库连接**：
- 通过 `core/db.py` 的 PrestoQuery 类连接
- 核心表见 `references/data-tables.md`
- 常用查询模式见 `references/sql-patterns.md`

### Phase 3: 分析计算

根据问题类型选择分析框架：

| 场景 | 核心方法 | 工具/模板 |
|------|---------|----------|
| **经营预估** | 首贷公式推算 + 复贷 MOB 模型 | `python pipeline.py` (Step2/Step3) |
| **权责核算** | 公式链：N=K×M → P=L×N×O → R=J×P×Q → U=T×R → X=U×V | `references/forecast-methodology.md` |
| **坏账分析** | VINTAGE cohort 分析 / T30率趋势 / 产品×期限×策略交叉 | `references/sql-patterns.md` |
| **数据校验** | 行数对比 / 金额汇总 / 交叉表验证 | `python pipeline.py --step 5` |
| **指标波动** | WoW 环比 / 拆解到维度 / 区分正常波动 vs 异常 | — |

### Phase 4: 输出结论

输出格式：**数据 → 解读 → 建议**。不是 dump 数据，要说清楚"这意味着什么"。

- 周报/月报用标准模板 → `references/report-templates.md`
- 看板指标更新 → 生成 SQL 或直接写入表
- 预估结果 → Excel 文件 + 数据库表

## 二、经营预估核心框架

### 2.1 首贷预估公式

```
首贷放款笔数 = (日消耗 / CPI) × 天数 × 安装注册率 × 综合通过率 × 签名放款率
首贷放款金额 = 首贷放款笔数 × 件均
```

### 2.2 复贷 MOB 预估模型

```
复贷进件量(t) = Σ 首贷放款量(t-MOB) × MA转化率(MOB) × 调整系数(MOB)
```

- MOB 0: 取最近 2 期 cohort 平均转化率（跳过当月未走完的）
- MOB 1+: 取最新 1 期 cohort 转化率
- 无数据 MOB: 沿用前一个 MOB 的 MA 值（不衰减）
- 循环贷(loop) 和非循环贷(normal) 分别建模

详见 `references/forecast-methodology.md`。

### 2.3 权责公式链

`J→K→L→M→O→Q→S→V` 八个死数输入，七步公式链输出放款笔数/金额/坏账：

```
N = K × M              (机审×后置)
P = L × N × O          (确认×机审后置×签名)
R = J × P × Q          (进件×全流程率×分布 → 放款笔数)
T = S / 汇率 × 10000   (件均万IDR → 件均$)
U = T × R              (件均×笔数 → 放款金额)
W = U                  (金额权重)
X = W × V              (金额×坏账率 → 坏账$)
```

### 2.4 关键指标关系

```
CPS = 消耗 / 放款数
FPD(首期逾期率) = 首期逾期金额 / 应还本金
T30坏账率 = 逾期30天以上金额 / 应还本金
件均 = 放款金额 / 放款笔数
客均笔数 = 放款笔数 / 放款人数
Grade1-2% = 高信用等级用户占比
```

## 三、数据表速查

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| `ind.ba_asset_base_info` | 资产底表（最核心） | issue_month, grant_strategy, is_reloan2, if_issue, if_app, contract_amount_usd1, loan_cycle, revenue |
| `ind.ba_loan_forecast` | 经营预估结果表 | stat_month, grant_strategy, is_reloan2, product_tag, loan_cycle, t30_rate, contract_amt, bad_amt |
| `ind.ba_bad_debt_rate_lookup` | 坏账率查表 | grant_month, product_tag, period_tag, grant_strategy, loan_cycle, bad_debt_rate |
| `ind.xly_application_funnel` | 进件漏斗宽表 | biz_id, grant_strategy, if_issue, contract_amount |
| `dwd.dwd_loan_info` | 放款明细 | release_time, mid, order_no |
| `ods.s02_loan_repayment` | 还款计划 | camera_id, should_capital, fact_capital, should_time |
| `ind.tyn_reg_install_new` | 注册安装 | mid, reg_dt, reg_time |
| `dim.dim_exchange_rate_cost` | 汇率表 | month_id, exchange_rate_to_dollar |

完整表字典见 `references/data-tables.md`。

## 四、经营计划自动化系统

项目位置：`e:/岳松个人文件/嘉银工作内容的整理/code/权责自动化处理/`

```bash
# 一键执行全流程
python pipeline.py

# 干跑检查
python pipeline.py --dry-run

# 单步执行
python pipeline.py --step 2     # 只跑复贷预估
python pipeline.py --step 4     # 只跑数据入库

# 不写数据库
python pipeline.py --skip-db
```

**每月操作**：
1. 打开 `config.yaml` → 改参数（月份、进件量、汇率、K/L/M/S/V）
2. `python pipeline.py --dry-run` → 检查配置
3. `python pipeline.py` → 一键执行
4. 检查 Step5 校验报告

## 五、参考资源

| 文件 | 内容 | 何时读 |
|------|------|--------|
| `references/indicator-glossary.md` | 📖 全部 KPI 指标定义+计算公式+数据来源 | 问"这个指标怎么算"时 |
| `references/data-tables.md` | 🗄️ 数据库表字典（字段/分区/关联） | 写 SQL 前确认字段 |
| `references/sql-patterns.md` | 📝 高频 SQL 模式（放款/逾期/漏斗/cohort） | 需要写查询时参考 |
| `references/forecast-methodology.md` | 🧮 预估方法论详解（MOB/权责/校准） | 理解或调整预估模型时 |
| `references/report-templates.md` | 📋 周报/月报/看板标准模板 | 生成报告时 |
| `references/pipeline-guide.md` | ⚙️ pipeline 使用指南 + config.yaml 说明 | 月度执行经营计划时 |
| `references/common-issues.md` | 🚨 常见问题速查（数据对不上/预估偏差大等） | 遇到异常时 |

## 六、与 paid-acquisition-strategy 的协作

| 场景 | 用哪个 skill |
|------|-------------|
| 投放效率分析（CPS/CPI/CTR） | `paid-acquisition-strategy` |
| 经营结果分析（放款/坏账/收入） | `overseas-credit-analysis` |
| 渠道质量 vs 放款量关系 | 两个 skill 交叉验证 |
| 风控收紧导致 CPS 上升 | `paid-acquisition-strategy` 诊断 + `overseas-credit-analysis` 提供风控数据 |
| 预算分配后预估产出 | `paid-acquisition-strategy` 做分配 + `overseas-credit-analysis` 做预估 |
