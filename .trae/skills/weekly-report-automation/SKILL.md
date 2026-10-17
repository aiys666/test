---
name: "weekly-report-automation"
description: "墨西哥/印尼周报自动化脚本开发与维护指南。涵盖SQL宽表设计、Sheet公式联动、8月预估逻辑、首笔版扩展、死数行处理等关键注意点。Invoke when 用户需要修改周报自动化脚本、新增指标行、调整预估逻辑、从经营计划Excel读取目标值、或排查周报产出异常时。"
---

# 周报自动化开发指南

## 1. 适用场景

本SKILL适用于以下场景：
- 修改墨西哥/印尼周报自动化脚本
- 新增周报指标行（如首贷首笔指标）
- 调整8月预估逻辑（放款量/金额/其他指标）
- 从经营计划Excel读取目标值/死数（坏账/TR/利润率/息费）
- 排查周报产出异常（数据缺失、公式错误、格式问题）
- 多国周报框架统一（墨西哥/印尼结构对齐）

---

## 2. 核心文件

| 文件 | 用途 |
|------|------|
| `墨西哥经分\墨西哥周报自动化.py` | 墨西哥周报主脚本 |
| `印尼周报自动化.py` | 印尼周报基础版 |
| `印尼周报自动化_首笔版.py` | 印尼周报首笔版（新增4行首贷首笔指标） |
| `mexico_presto.py` / `indonesia_presto.py` | Presto直连模块 |

---

## 3. 周报整体架构

### 3.1 数据流程

```
Presto查询 → Sheet3"数据源" → Sheet1 VLOOKUP公式联动 → 8月预估 → 格式化 → 保存
```

### 3.2 Sheet1 结构（行号映射）

**第一段：规模&收入（R3-R17）**
- R3-R5: 成交金额（首贷/复贷/整体）
- R6-R8: 成交标数（首贷/复贷/整体）
- R9-R11: 笔均（首贷/复贷/整体）
- R12-R14: 期限（首贷/复贷/整体）
- R15-R17: 息费（首贷/复贷/整体）— 墨西哥用，印尼保留空白

**第二段：成本（R21-R36）**
- R21: 日投放金额（死数）
- R22: 静态CPS（死数E列，VLOOKUP覆盖J列）
- R23: 静态CPD% = CPS/笔均（公式）
- R24-R26: 1T0（首贷/复贷/整体，VLOOKUP）
- R27-R29: 1T7（首贷/复贷/整体，VLOOKUP）
- R30-R32: 本金坏账Vintage%（死数）
- R33-R35: TR%（死数）
- R36: 经营利润率（死数）

### 3.3 列号映射

| 列 | 含义 |
|----|------|
| E (5) | 8月目标 |
| F (6) | 8月实际 |
| G (7) | 8月预估 |
| H (8) | 8月预估达成% |
| J (10) | 7月实际 |
| K (11) | 8月 vs 7月 环比% |

---

## 4. 关键技术注意点

### 4.1 SQL设计要点

**宽表查询（SQL_WIDE_TABLE）**
- 使用CTE聚合减少重复表扫描
- `NULLIF()` 处理除零：`ROUND(sum_contract / NULLIF(cnt_loan, 0), 1)`
- 动态日期：`release_time >= DATE '2026-01-01' AND release_time < CURRENT_DATE`
- 首贷判断：必须用 `mx.risk_double_loan_tag.double_loan=0`（非 `ods.s02_loan.double_loan`）
- new_grade_level：从 `mx.report_application_funnel7_table.credit_level` 获取，null赋值9999
- 关联条件：`on r.camera_id = cast(f7.biz_id as bigint)`
- 歧义字段必须指定表别名：`r.is_reloan`、`r.if_issue`、`att.new_media_source`

**三段式SQL结构**
- 首贷和复贷数据处理必须保留完整的三段式SQL结构
- 每段依次执行，避免Presto多语句返回 `statement_type=None`

### 4.2 Presto连接要点

- **新端点**：`https://data.tengoprestamos.com/dataworks-development/adhoc/querySql`
- **旧端点禁用**：`pangu.tengoprestamos.com`（会权限报错）
- **密码URL编码**：密码含特殊字符必须URL编码，否则登录失败
- **重试机制**：最多3次重试 + 自动重新登录
- **分页**：每页1000条循环取全部结果
- **多语句处理**：`statement_type=None` 时拆分为单语句分别执行

### 4.3 8月预估逻辑

**放款量/金额（需预估）**
```
8月预估 = 8月累计实际 + 近8天日均 × 剩余天数
```
- 近8天日均：排除不完整日期（天数<全月天数）
- 剩余天数 = 月末天数 - data_last_date.day
- 日均参数写入M/N/O列，G列用公式 `=F + 日均 × 剩余天数`

**其余指标（不预估）**
- 8月预估 = 8月实际值（G=F）

### 4.4 汇率处理

- 按月对应汇率（从 `dim.dim_exchange_rate_cost` 读取）
- 8月强制使用固定值（墨西哥17.4827，印尼18099）
- 成交金额/笔均需按月汇率转换 MXN/IDR → USD

### 4.5 死数行处理

**死数行集合（墨西哥）**
```python
_DEAD_NUMBER_ROWS = {30, 31, 32, 33, 34, 35, 36}  # 坏账/TR/利润率
```

**死数行规则**
- E列（8月目标）+ J列（7月实际）均为手填死数
- H列 = G-E（绝对差）
- K列 = G-J（绝对差）
- J列不写VLOOKUP

**需从经营计划Excel读取的死数**
- R15-R16: 息费（首贷/复贷）
- R30-R32: 本金坏账Vintage%
- R33-R35: TR%
- R36: 经营利润率

---

## 5. 印尼周报首笔版扩展

### 5.1 新增4行指标

在R24-R27新增首贷首笔相关指标：

| 行号 | 指标 | 数据来源 |
|------|------|----------|
| R24 | 首贷笔数（首笔） | VLOOKUP（数据源） |
| R25 | 首贷金额（首笔） | VLOOKUP（数据源） |
| R26 | 静态CPS（首笔） | 计算行（投放金额/issue_cnt_1） |
| R27 | 静态CPD%（首笔） | 计算行（投放金额/contract_amount_usd_1） |

### 5.2 SQL扩展

在 `loan_agg` CTE 中新增两个字段：
```sql
SUM(CASE WHEN reloan_num = 1 THEN 1 ELSE 0 END) AS issue_cnt_1,
SUM(CASE WHEN reloan_num = 1 THEN contract_amount ELSE 0 END) AS contract_amount_usd_1
```

在 `loan_metrics` 中新增：
```sql
UNION ALL
SELECT '首贷笔数（首笔）', ..., ROUND(issue_cnt_1, 0) FROM loan_agg
UNION ALL
SELECT '首贷金额（首笔）', ..., ROUND(contract_amount_usd_1, 0) FROM loan_agg
```

新增 `first_loan_cps_rows` CTE：
```sql
SELECT '静态CPS（首笔）' AS metric, '首贷' AS loan_type, c.month,
    ROUND(c.spend / NULLIF(fl.issue_cnt_1, 0), 2) AS value
FROM cost_spend c 
LEFT JOIN first_issue_cnt fl ON c.month = fl.month
WHERE fl.issue_cnt_1 > 0

UNION ALL

SELECT '静态CPD%（首笔）' AS metric, '首贷' AS loan_type, c.month,
    ROUND(c.spend / NULLIF(fl.contract_amount_usd_1, 0), 4) AS value
FROM cost_spend c 
LEFT JOIN first_issue_cnt fl ON c.month = fl.month
WHERE fl.contract_amount_usd_1 > 0
```

### 5.3 行号映射调整（首笔版）

由于新增4行，首笔版行号整体后移：

| 指标 | 基础版行号 | 首笔版行号 |
|------|-----------|-----------|
| 首贷笔数（首笔） | - | R24 |
| 首贷金额（首笔） | - | R25 |
| 静态CPS（首笔） | - | R26 |
| 静态CPD%（首笔） | - | R27 |
| 1T0（首贷/复贷/整体） | R24-R26 | R28-R30 |
| 1T7（首贷/复贷/整体） | R27-R29 | R31-R33 |
| 本金坏账 | R30-R32 | R34-R36 |
| TR% | R33-R35 | R37-R39 |
| 经营利润率 | R36 | R40 |

### 5.4 经营利润率特殊处理

**首笔版 R40 经营利润率**：
- 清理日实际数据范围时必须跳过R40（否则会清空经营利润率值）
- 代码示例：
```python
# 清理日实际数据，但跳过R40经营利润率
for r in range(3, 41):
    if r == 40:  # 跳过经营利润率
        continue
    ws1.cell(r, F_JUN).value = None
```

---

## 6. Excel格式规范

### 6.1 字体与对齐
- 字体：微软雅黑 10pt
- 冻结窗格：A列 + 月份表头行
- 合并组标题：深蓝色背景

### 6.2 数字格式
- 金额：千分位（`#,##0`）
- 比率：百分比（`0.0%`）
- 小数：保留对应位数

### 6.3 输出要求
- 仅保留Sheet1（移除datasource sheet）
- 文件名带时间戳：`xxx_更新_YYYYMMDD_HHMMSS.xlsx`

---

## 7. 从经营计划Excel读取数据

### 7.1 数据源文件

**墨西哥经营计划**：`墨西哥经营计划测算_未来12个月_v4_20260809.xlsx`
- Sheet: `权责输出`、`P&L`、`首复贷假设`、`成本假设`、`历史数据`

**印尼经营计划**：`【7月】印尼经营计划测算_20260730.xlsx`
- Sheet: `P&L`、`总结`、`权责格式`

### 7.2 月份列定位

**墨西哥v4文件列号映射**
- col20: 2025年2月
- col21: 2025年3月
- ...
- col25: 2025年7月（用于7月实际J列）
- col26: 2025年8月（用于8月目标E列）

**印尼文件**：通过 `find_summary_col()` 函数按日期匹配列号

### 7.3 关键指标读取位置（墨西哥v4）

| 指标 | Sheet | 行号 | 列 |
|------|-------|------|-----|
| TR% 整体 | P&L | R15 | 8月col26 / 7月col25 |
| 经营利润率 整体 | P&L | R34 | 8月col26 / 7月col25 |
| TR% 首贷 | P&L | R56 | 8月col26 / 7月col25 |
| TR% 复贷 | P&L | R177 | 8月col26 / 7月col25 |
| 息费 首贷 | 首复贷假设 | X12+X13 | 8月col26 |
| 息费 复贷 | 首复贷假设 | X32+X33 | 8月col26 |
| 本金坏账 首贷 | 权责输出 | R13 | - |
| 本金坏账 复贷 | 权责输出 | R34 | - |
| 本金坏账 整体 | 权责输出 | R53 | - |

### 7.4 印尼 read_quanze_data 函数

```python
def read_quanze_data(file_path):
    """从印尼经营计划Excel读取 TR%、经营利润率、本金坏账%
    
    数据源:
        P&L sheet:
            row 15 = 整体-take rate
            row 56 = 首贷-take rate
            row 177 = 复贷-take rate
            row 34 = 整体-经营利润率
            row 193 = 复贷-经营利润率
        总结 sheet (场景1):
            row 12 = 首贷TR%, row 14 = 复贷TR%
            row 13 = 首贷经营利润率%, row 15 = 复贷经营利润率%, row 16 = 整体经营利润率%
        权责格式 sheet:
            row 13 = 首贷本金坏账, row 34 = 复贷本金坏账, row 53 = 整体本金坏账
    """
```

---

## 8. 常见问题与解决方案

### 8.1 Presto查询失败
- **症状**：`statement_type=None` 或返回字符串而非DataFrame
- **解决**：多语句SQL拆分为单语句分别执行

### 8.2 登录失败
- **症状**：权限错误或401
- **解决**：
  1. 检查端点是否为新端点（data.tengoprestamos.com）
  2. 密码特殊字符URL编码
  3. 加入重试机制（3次+重新登录）

### 8.3 预估数据异常
- **症状**：8月预估值偏差大
- **解决**：
  1. 检查近8天日均是否排除了不完整日期
  2. 确认剩余天数计算（月末天数 - data_last_date.day）
  3. 验证日均参数是否正确写入M/N/O列

### 8.4 Excel公式不联动
- **症状**：Sheet1数据不更新
- **解决**：
  1. 检查Sheet3数据源是否写入
  2. 确认VLOOKUP公式范围正确
  3. 整体行公式（R5/R8/R11等）是否正确

### 8.5 经营利润率被清空（首笔版）
- **症状**：R40经营利润率值为空
- **解决**：清理日实际数据范围时跳过R40

### 8.6 PowerShell输出异常
- **症状**：`System.ArgumentOutOfRangeException`
- **解决**：简化print输出内容，分步骤执行

---

## 9. 代码修改原则

1. **最小修改**：保留原始代码段，仅修改必要部分
2. **数据不变**：优化后数据结果必须与原版一致
3. **直接使用**：已修改的代码段直接使用，不再二次修改
4. **合并重复**：合并重复计算简化复杂度
5. **成功验证**：修改后必须运行成功且数据正确
6. **新增隔离**：新功能代码放入额外文档，不修改周报自动化主文件

---

## 10. 后续可自动化方向

1. **周报目标值自动读取** — 从经营计划Excel自动更新E列死数
2. **7月死数自动读取** — 坏账/TR/利润率J列从Excel读取
3. **多国周报统一框架** — 抽象为通用模板+配置驱动
4. **达成率预警** — 实际/目标 < 80% 或 > 120% 自动标红
5. **渠道维度下钻** — CPS/CPD/留存按media_source拆分
6. **Vintage cohort追踪** — 按放款月+MOB追踪坏账/复借
