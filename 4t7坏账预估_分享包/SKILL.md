---
name: "rating-4t7-weekly-forecast"
description: "评级产品每周4t7坏账/息费/TR预估(覆盖率100%选优法)。支持两种模式：A) Presto自动取数一键出结果；B) 手动上传周度/月度Excel。按覆盖率=100%的最晚指标(4T7>4T0>3T0>2T0>1T3>1T0)选优，乘以参考月比率预估4t7指标，按时间加权聚合整月，输出带公式的Excel。Invoke when 用户要做任意目标月的每周4t7预估(覆盖率选优、月度时间加权聚合)、运行/修改 coverage_fetch_estimate.py 或 create_weekly_excel.py、或需要换月份重跑预估时。"
---

# 评级产品每周 4T7 预估（覆盖率 100% 选优法）

## 1. 用途

把「放款月」数据 → 生成一张**带公式的 Excel**，输出每个「周 × 产品」的 4T7 本金逾期率、4T7 息费逾期率、4T7 TR 预估值，并按时间加权聚合出整月预估。适用于墨西哥评级产品（首贷 / 复贷）。

## 2. 两种运行模式

| 模式 | 脚本（本技能目录 `scripts/`） | 是否需要 Presto 账号 |
|------|------|------|
| **A. 自动取数（推荐）** | `scripts/coverage_fetch_estimate.py` | 需要（读 `scripts/config.py`） |
| **B. 手动上传 Excel** | `scripts/create_weekly_excel.py` | 不需要 |

先安装依赖：`pip install -r requirements.txt`（pandas / openpyxl / requests）。

## 3. 模式 A：自动取数

```powershell
cd <技能目录>\scripts
copy config.example.py config.py      # 首次：填 PRESTO_USER / PRESTO_PWD
python coverage_fetch_estimate.py --ref-month 2026-08 --target-month 2026-09
```

- **凭据来源优先级**：`scripts/config.py` → 环境变量 `PRESTO_USER` / `PRESTO_PWD`。代码里不写死账号。
- 取数 SQL 打 `mx.wxs_application_funnel LEFT JOIN mx.yj_test_table_250225`，`if_issue=1`、`is_reloan IN ('new','old')`、`app_time >= 2026-01-01`。
- 输出 6 个 sheet：`首贷` / `复贷`（预估）+ `首贷月`/`复贷月`/`首贷周`/`复贷周`（2026-01-01 起历史全量汇总）。
- 参数：`--ref-month`、`--target-month`、`--out`、`--cache`、`--no-cache`、`--revenue-field`。
- 首次运行结果缓存到 `_coverage_raw_cache.csv`；**改 SQL 或要刷新数据须加 `--no-cache`**。

## 4. 模式 B：手动上传 Excel

需要 2 个文件（默认读第一个 sheet，脚本自动 `ffill` 清洗表头）：

| 文件 | 关键列 |
|------|--------|
| 周度文件 | `issue_week`、`产品`、`放款笔数`、`放款金额`、`平均期限`、`总收息_含税`、`1t0/1t3/2t0/3t0/4t0/4t7本金逾期率`、`4t7息费逾期率_本金分母`、`is_t0_window_1` `is_t3_window_1` `is_t0_window_2` `is_t0_window_3` `is_t0_window_4` `is_t7_window_4` |
| 月度文件 | 同上，另加 `放款月份`（需含参考月 + 目标月两段） |

```powershell
cd <技能目录>\scripts
python create_weekly_excel.py `
  --weekly "D:/xx/评级产品表现-放款月2.xlsx" `
  --monthly "D:/xx/评级产品表现-放款月21.xlsx" `
  --out "D:/xx/9月每周4t7预估.xlsx" `
  --ref-month 2026-08 --target-month 2026-09
```

`--weekly` / `--monthly` 必填。

## 5. 换月份

只改 `--ref-month` / `--target-month` 两个参数即可，**目标周与周权重按目标月自动推导**（覆盖该月的所有自然周；权重 = 该周落在目标月内的天数 / 7）。

```powershell
python coverage_fetch_estimate.py --ref-month 2026-09 --target-month 2026-10
```

可按需覆盖：`--target-weeks 09-28,10-05,10-12,10-19,10-26`、`--week-weights 4/7,1,1,1,6/7`。
推导函数：`create_weekly_excel.derive_target_weeks(target_month)` / `derive_week_weights(target_month, weeks)`。

## 6. 核心规则

### 6.1 覆盖率选优
覆盖率 = 该指标出账笔数 / 放款笔数（Excel `F~K` 列 / `C` 列）。对每个「周 × 产品」按优先级找**覆盖率=100%** 的最晚指标：

```
4T7 > 4T0 > 3T0 > 2T0 > 1T3 > 1T0
```

### 6.2 覆盖率列映射（重要）

```python
cnt_cols = {
    '1T0': 'is_t0_window_1',
    '1T3': 'is_t3_window_1',   # 注意是 window_1，不是 window_4
    '2T0': 'is_t0_window_2',
    '3T0': 'is_t0_window_3',
    '4T0': 'is_t0_window_4',
    '4T7': 'is_t7_window_4',
}
```

### 6.3 预估公式
- 推荐=`4T7` 且覆盖率=100%：直接用实际 `4t7本金逾期率` / `4t7息费逾期率_本金分母`。
- 推荐=`4T0/3T0/2T0/1T3/1T0`：`目标月该指标 × (参考月4t7 / 参考月该指标)`。
- 推荐=`无`：回退用 `1t0 × 参考月比率`。
- `TR = 总收息 − 4t7本金逾期率 − 4t7息费逾期率(本金分母)`。

### 6.4 周汇总与月聚合（时间加权）
- 周汇总：按 `放款金额` 加权 `SUMPRODUCT / SUM`。
- 月聚合：`Σ(D_i × 指标_i × w_i) / Σ(D_i × w_i)`，`D_i`=该周放款金额、`w_i`=该周在目标月内的天数/7。

## 7. 输出 Excel 结构（47 列 A–AU）

| 列 | 内容 | 类型 |
|----|------|------|
| A–E | 周次 / 产品 / 笔数 / 金额 / 期限 | 输入 |
| F–K | 1T0/1T3/2T0/3T0/4T0/4T7 出账笔数 | 输入 |
| L–Q | 各指标覆盖率 | 公式 |
| R | 推荐指标 | 公式(嵌套 IF) |
| S–Z | 目标月输入：总收息、1t0~4t0、4t7本、4t7息 | 输入 |
| AA–AG | 参考月原始：1t0~4t0、4t7本、4t7息 | 输入 |
| AH–AL | 参考月比率-本金（4t7本/该指标） | 公式 |
| AM–AQ | 参考月比率-息费（4t7息/该指标） | 公式 |
| AR–AT | 预估4t7本 / 预估4t7息 / 预估4t7TR | 公式 |
| AU | 标记：`无历史表现参考产品` / `无直接参考,采用:{产品}` | 输入 |

布局：每周 = 产品明细行 + 1 行金额加权汇总；最后 1 行为月度聚合。所有派生数字都是 Excel 公式，改输入后自动重算。

## 8. 关键注意点

1. **1T3 覆盖率列** 用 `is_t3_window_1`（历史曾误用 `is_t3_window_4`）。
2. **总收息口径** 默认 `总收息_含税`，可改 `总收息_不含税`（`--revenue-field` 或 `REVENUE_FIELD`）。
3. **参考月过滤**：参考月只保留 `放款笔数 > 3`（`MIN_AUG_CNT`）的产品。
4. **参考月无直接数据**：自动 fallback 到「平均期限相同 + 总收息最接近」的参考月产品，AU 列标注；若该月整体为空则 AU 标 `无历史表现参考产品`，预估仍回退 `1t0`。
5. **凭据安全**：`config.py` 只放本地，不提交、不随分享包外发。
6. **两种模式共享同一套 sheet 构建逻辑**：`create_weekly_excel.build_sheet` 被自动取数脚本复用。

## 9. 常见问题

- **跑出来是空/少周**：确认周度文件 `issue_week` 能解析成 `MM-DD`（如 `09-07`）。
- **参考月比率是 `-`**：该产品在参考月无数据或 `放款笔数 <= 3`。
- **`PermissionError`**：输出 Excel 正被打开，关闭或用 `--out` 换名。
- **数据未刷新**：加 `--no-cache`。
- **`未配置 Presto 账号密码`**：`copy config.example.py config.py` 并填账号，或设环境变量。
