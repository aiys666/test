# 墨西哥经分自动化 - 系统架构文档

> 版本: v1.0 | 日期: 2026-06-30 | 作者: 岳松

## 一、背景与目标

### 1.1 背景
墨西哥业务已从印尼扩展，承接印尼经分自动化 Pipeline 的架构经验，
建立墨西哥自己的经营分析自动化体系。

### 1.2 目标
```
最终目标: 一键生成墨西哥周报 + 月度经营计划 + 权责经分模板
```

### 1.3 与印尼Pipeline的关系
| 对比项 | 印尼 Pipeline | 墨西哥 Pipeline |
|--------|--------------|----------------|
| 入口 | `pipeline.py` | `mexico_pipeline.py` |
| 配置文件 | `config.yaml` | `config.yaml` |
| 数据库 | MySQL YSProd | MySQL YSProd (共用) |
| 预测月份 | Jul-Dec 2025 | Jul-Dec 2026 |
| 数据源 | Presto DB + Excel | Excel (已整理) |
| 货币 | IDR (印尼盾) | MXN (墨西哥比索) |
| 产品数 | 5个 (K/L/M/S/V) | 5个+ (C/B类7/15天) |

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Mexico Pipeline                           │
│  python mexico_pipeline.py [--step N]                        │
└──────┬──────────────────────────────────────────────────────┘
       │
       ├─ Step 0: 数据准备
       │    输入: 墨西哥经营计划_26年6月及7月预估V4.xlsx
       │    处理: openpyxl 读取各 sheet
       │    输出: historical_data dict
       │
       ├─ Step 1: 周度指标计算
       │    输入: historical_data
       │    处理: 解析 KPI/周数据
       │    输出: weekly_data list
       │
       ├─ Step 2: 月度预测
       │    输入: weekly_data
       │    处理: 增长率模型预测 Jul-Dec 2026
       │    输出: forecast_data list
       │
       ├─ Step 3: LTV模型
       │    输入: historical_data
       │    处理: LTV = CPS / 坏账率
       │    输出: ltv_data dict
       │
       └─ Step 4: Excel模板输出
            输入: weekly_data + forecast_data + ltv_data
            处理: openpyxl 生成多 sheet Excel
            输出: 墨西哥经分报告_YYYYMMDD.xlsx
```

---

## 三、核心数据来源

### 3.1 Excel 数据文件
```
E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\墨西哥\
  墨西哥经营计划_26年6月及7月预估V4.xlsx  ← 主要数据源
  墨西哥下半年计划v7_年中版_20260617.xlsx
  海外7月权责表跟进_三国20260629_v4.xlsx
```

### 3.2 Excel Sheet 解析

| Sheet 名称 | 行x列 | 用途 | 关键字段 |
|-----------|-------|------|---------|
| 墨西哥经营计划(主) | 190x42 | 周度经营数据 | 日期/首贷/复贷 |
| 墨西哥经营计划(产品月态) | 59x25 | 产品月度态 | 产品代码/月度 |
| 墨西哥经营计划_额5期 | 129x65 | LTV预测 | 周/利息累计 |
| 墨西哥经营计划_额6期 | 132x65 | 6月预测 | 同上 |
| **Sheet3** | 19x49 | **核心KPI表** | CPI/CPR/CPA/CPS/T3转化 |
| LTV | 43x14 | LTV历史 | 新客CPS/坏账率 |
| LTV1 | 22x11 | LTV预测 | 同上 |
| 墨西哥经营计划_号7利息累计 | 34x23 | 累计报案率 | 0~19期报案率 |
| by月报案累计 | 12x10 | 月度报案 | 月度报案汇总 |

### 3.3 核心指标体系 (与印尼对应)

| 印尼指标 | 墨西哥对应 | 说明 |
|---------|-----------|------|
| K/L/M/S/V (产品) | C_07_03_00_75 等 | 7天/15天 + 2期/3期 |
| BP/HL/ME (APR类型) | BP/HL/ME/MK | 4个渠道 |
| 进件量 | APP注册量 | 首贷+复贷 |
| CPI | CPI | 每注册成本 ($) |
| CPR | CPR | 每注册率 |
| CPA | CPA | 每审批成本 |
| CPS | CPS | 每放款成本 ($) |
| T3转化率 | T3转化率 | 首贷审批通过率 |
| T10转化率 | T10转化率 | 复贷审批通过率 |
| Vintage曲线 | Vintage | 按月龄累计报案率 |
| LTV | LTV | 客户生命周期价值 ($) |

---

## 四、数据库 Schema (与印尼共用 YSProd)

### 4.1 核心表
```
dim_time       - 时间维度表
dim_product    - 产品维度表  
dim_customer   - 客户维度表
fct_loan_application  - 贷款申请事实表
fct_loan_disbursement - 贷款发放事实表
```

### 4.2 墨西哥相关 (待确认)
需要确认墨西哥数据是否已入库，表名可能包含 `mx_` 或 `mexico_` 前缀。

---

## 五、Pipeline 步骤详解

### Step 0: 数据准备
```python
# 读取 Excel 所有 sheet
python mexico_pipeline.py --step 0
```
- 使用 `openpyxl` 读取
- 自动跳过空行空列
- 识别 Sheet3 (核心KPI) 和 LTV sheet

### Step 1: 周度指标计算
```python
python mexico_pipeline.py --step 1
```
- 从 Sheet3 解析 CPI/CPR/CPA/CPS/T3转化
- 从周数据表汇总月度进件量

### Step 2: 月度预测
```python
python mexico_pipeline.py --step 2
```
- 基于最近3个月均值
- 应用月环比增长率:
  - 进件量: +5%/月
  - CPS: -2%/月 (效率提升)
  - T3转化率: +1%/月

### Step 3: LTV模型
```python
python mexico_pipeline.py --step 3
```
- LTV = 新客CPS / 坏账率
- 从 LTV1 sheet 读取预测数据
- 从 墨西哥经营计划_号7利息累计 获取各期报案率

### Step 4: Excel模板输出
```python
python mexico_pipeline.py --step 4
```
- 生成 6 个 Sheet 的 Excel 报告
- 输出到 `output/墨西哥经分报告_YYYYMMDD.xlsx`

---

## 六、下一步 (明天继续)

- [ ] **Step 0 补充**: 完善 Sheet3 KPI 解析逻辑（49列全部识别）
- [ ] **Step 1 补充**: 对接数据库，查询墨西哥实时进件数据
- [ ] **Step 2 补充**: 与墨西哥业务方确认增长率假设
- [ ] **Step 3 补充**: 完善 Vintage 曲线计算
- [ ] **Step 4 补充**: 对齐印尼的权责表模板格式
- [ ] **自动化**: 配置 Windows Task Scheduler 每周自动运行

---

## 七、文件结构

```
E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥经分\
├── mexico_pipeline.py      ← Pipeline主入口
├── config.yaml             ← 配置文件
├── ARCHITECTURE.md         ← 本文档
│
├── core/
│   ├── __init__.py
│   ├── config.py           ← 配置加载
│   └── db.py               ← 数据库连接
│
├── steps/
│   ├── __init__.py
│   ├── step0_data_prep.py         ← 数据准备
│   ├── step1_weekly_metrics.py     ← 周度指标
│   ├── step2_monthly_forecast.py   ← 月度预测
│   ├── step3_ltv_model.py          ← LTV模型
│   └── step4_template_output.py    ← Excel输出
│
├── sql/
│   └── README.md           ← SQL查询模板
│
└── output/                 ← 报告输出目录
    └── README.md           ← 输出文件说明
```

---

## 八、运行指南

### 快速开始
```bash
# 1. 检查数据库连接
python mexico_pipeline.py --check

# 2. 运行全流程
python mexico_pipeline.py

# 3. 仅运行某个 Step
python mexico_pipeline.py --step 0    # 数据准备
python mexico_pipeline.py --step 1    # 周度指标
python mexico_pipeline.py --step 4    # 输出报告

# 4. 运行多个 Steps
python mexico_pipeline.py --steps 0 1 2
```

### 依赖
```bash
pip install openpyxl pandas mysql-connector-python pyyaml
```

---

*文档创建: 2026-06-30 | 墨西哥经分自动化 v1.0*
