# 评级产品每周 4T7 坏账预估工具（覆盖率 100% 选优法）

自动生成「周 × 产品」的 **4T7 本金逾期率 / 4T7 息费逾期率 / 4T7 TR** 预估，并按时间加权聚合出整月预估。输出为**带公式的 Excel**，改输入即自动重算，方便汇报时调参。

适用于墨西哥评级产品（首贷 / 复贷），数据源为盘古 4.0 Presto 的 `mx.wxs_application_funnel`。

---

## 1. 环境准备（一次性）

- Python 3.8+（建议 3.10+）
- 安装依赖：

```powershell
pip install -r requirements.txt
```

`requirements.txt` 内容：`pandas`、`openpyxl`、`requests`。

---

## 2. 两种运行方式

| 方式 | 脚本 | 是否需要 Presto 账号 | 说明 |
|------|------|----------------------|------|
| **A. 自动取数（推荐）** | `scripts/coverage_fetch_estimate.py` | 需要 | 一条 SQL 直接从库取数，一键出结果 |
| **B. 手动上传 Excel** | `scripts/create_weekly_excel.py` | 不需要 | 你自己导出周度/月度 Excel 后喂给脚本 |

---

## 3. 方式 A：自动取数

### 3.1 配置账号（只需一次）

```powershell
cd scripts
copy config.example.py config.py
```

用编辑器打开 `config.py`，把 `PRESTO_USER` / `PRESTO_PWD` 改成你自己的盘古 4.0 账号密码。

> `config.py` 只放本地，不要提交、不要随包分享（分享包里默认只有 `config.example.py`）。
> 也可以用环境变量 `PRESTO_USER` / `PRESTO_PWD` 代替。

### 3.2 运行

```powershell
cd scripts
python coverage_fetch_estimate.py --ref-month 2026-08 --target-month 2026-09
```

输出 6 个 sheet 的 Excel：`首贷`、`复贷`、`首贷月`、`复贷月`、`首贷周`、`复贷周`
（`首贷月/复贷月/首贷周/复贷周` 为 2026-01-01 起的历史表现全量汇总）。

**常用参数**

| 参数 | 默认 | 说明 |
|------|------|------|
| `--ref-month` | `2026-08` | 参考月（算比率用，即 4t7/该指标） |
| `--target-month` | `2026-09` | 目标月（要预估的月） |
| `--out` | `当前目录/{目标月}每周4t7预估_自动取数_首贷复贷.xlsx` | 输出路径 |
| `--cache` | `当前目录/_coverage_raw_cache.csv` | 取数缓存 |
| `--no-cache` | 关 | 忽略缓存强制重新取数 |
| `--revenue-field` | `总收息_含税` | 可改 `总收息_不含税` |

> 首次运行会把取数结果缓存成 `_coverage_raw_cache.csv`；之后改预估参数会直接读缓存（快）。**改了 SQL 或要刷新数据时，加 `--no-cache`。**

---

## 4. 方式 B：手动上传 Excel

先从 Presto 导出两个文件（第一个 sheet 即可，无需手工清洗表头）：

| 文件 | 关键列 |
|------|--------|
| 周度文件 | `issue_week`、`产品`、`放款笔数`、`放款金额`、`平均期限`、`总收息_含税`、`1t0/1t3/2t0/3t0/4t0/4t7本金逾期率`、`4t7息费逾期率_本金分母`、出账笔数 `is_t0_window_1` `is_t3_window_1` `is_t0_window_2` `is_t0_window_3` `is_t0_window_4` `is_t7_window_4` |
| 月度文件 | 同上，另需 `放款月份`（含参考月 + 目标月两段） |

```powershell
cd scripts
python create_weekly_excel.py `
  --weekly "D:/xx/评级产品表现-放款月2.xlsx" `
  --monthly "D:/xx/评级产品表现-放款月21.xlsx" `
  --out "D:/xx/9月每周4t7预估.xlsx" `
  --ref-month 2026-08 --target-month 2026-09
```

`--weekly` / `--monthly` 必填；`--out` 默认输出到当前目录。

---

## 5. 换月份怎么办

**只需改 `--ref-month` 和 `--target-month` 两个参数**：

```powershell
python coverage_fetch_estimate.py --ref-month 2026-09 --target-month 2026-10
```

目标周列表与各周权重会**按目标月自动推导**（覆盖该月的所有自然周，权重 = 该周落在目标月内的天数 / 7）。
例：目标月 9 月 → 周 `08-31, 09-07, 09-14, 09-21, 09-28`，权重 `6/7, 1, 1, 1, 3/7`。

如需手工指定（一般不必）：

```powershell
python coverage_fetch_estimate.py --target-month 2026-10 `
  --target-weeks 09-28,10-05,10-12,10-19,10-26
```

---

## 6. 核心规则（口径）

### 6.1 覆盖率 100% 选优

覆盖率 = 该指标出账笔数 / 放款笔数（Excel 中 `F~K` 列 / `C` 列）。
对每个「周 × 产品」，按优先级找**覆盖率 = 100%** 的最晚指标：

```
4T7 > 4T0 > 3T0 > 2T0 > 1T3 > 1T0
```

### 6.2 覆盖率列映射（易错点）

| 指标 | 覆盖率列 |
|------|----------|
| 1T0 | `is_t0_window_1` |
| **1T3** | **`is_t3_window_1`**（不是 `is_t3_window_4`） |
| 2T0 | `is_t0_window_2` |
| 3T0 | `is_t0_window_3` |
| 4T0 | `is_t0_window_4` |
| 4T7 | `is_t7_window_4` |

### 6.3 预估公式

- 推荐 = `4T7` 且覆盖率 100%：直接用实际 `4t7本金逾期率` / `4t7息费逾期率_本金分母`。
- 推荐 = `4T0/3T0/2T0/1T3/1T0`：`目标月该指标 × (参考月4t7 / 参考月该指标)`。
- 推荐 = `无`：回退用 `1t0 × 参考月比率`。
- `TR = 总收息 − 4t7本金逾期率 − 4t7息费逾期率(本金分母)`。

### 6.4 周汇总与月聚合（时间加权）

- 周汇总：按 `放款金额` 加权（`SUMPRODUCT/SUM`）。
- 月聚合：对每个周边界天数加权，`Σ(D_i × 指标_i × w_i) / Σ(D_i × w_i)`。

---

## 7. 输出 Excel 结构（47 列 A–AU）

| 列 | 内容 | 类型 |
|----|------|------|
| A–E | 周次 / 产品 / 笔数 / 金额 / 期限 | 输入 |
| F–K | 1T0/1T3/2T0/3T0/4T0/4T7 出账笔数 | 输入 |
| L–Q | 各指标覆盖率 | 公式 |
| R | 推荐指标 | 公式（嵌套 IF） |
| S–Z | 目标月输入：总收息、1t0~4t0、4t7本、4t7息 | 输入 |
| AA–AG | 参考月原始：1t0~4t0、4t7本、4t7息 | 输入 |
| AH–AL | 参考月比率-本金（4t7本/该指标） | 公式 |
| AM–AQ | 参考月比率-息费（4t7息/该指标） | 公式 |
| AR–AT | 预估 4t7本 / 4t7息 / 4t7TR | 公式 |
| AU | 标记：`无历史表现参考产品` / `无直接参考,采用:{产品}` | 输入 |

行布局：每个周有「产品明细行 + 1 行加权汇总」，最后 1 行为月度聚合。

---

## 8. 常见问题

- **跑出来是空 / 少周**：确认周度文件的 `issue_week` 能解析成 `MM-DD`（如 `09-07`）。
- **参考月比率是 `-`**：该产品在参考月无数据或 `放款笔数 <= 3`（`MIN_AUG_CNT`）。
- **提示「未配置 Presto 账号密码」**：忘了 `copy config.example.py config.py` 并填账号。
- **`PermissionError`**：输出 Excel 正被打开，关掉或换文件名。
- **数据没更新**：加 `--no-cache` 重新取数（缓存不会自动过期）。
- **产品在参考月没有直接数据**：会自动 fallback 到「平均期限相同 + 总收息最接近」的参考月产品，并在 AU 列标注。

---

## 9. 文件清单

```
4t7坏账预估_分享包/
├── README.md                       ← 本文件
├── requirements.txt
├── SKILL.md                         ← Trae 用户可直接安装的技能说明（可选）
└── scripts/
    ├── coverage_fetch_estimate.py   ← 方式A：自动取数 + 预估
    ├── create_weekly_excel.py       ← 方式B：手动上传Excel（同时被A复用）
    ├── mexico_presto.py             ← 盘古4.0 Presto 客户端
    └── config.example.py            ← 账号模板（复制为 config.py 后填自己的账号）
```
