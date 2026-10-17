# Pipeline 使用指南

> 经营计划自动化系统 (pipeline.py) 的完整使用说明。

## 系统位置

```
e:/岳松个人文件/嘉银工作内容的整理/code/权责自动化处理/
```

## 命令速查

```bash
# 全量执行
python pipeline.py

# 单步执行
python pipeline.py --step 1    # 只跑风险坏账转化
python pipeline.py --step 2    # 只跑复贷预估
python pipeline.py --step 3    # 只跑权责预估
python pipeline.py --step 4    # 只跑数据入库
python pipeline.py --step 5    # 只跑数据校验

# 多选执行
python pipeline.py --steps 1,3,4

# 预检查（不实际执行）
python pipeline.py --dry-run

# 跳过数据库（只生成本地文件）
python pipeline.py --skip-db
```

## 五步流程

```
Step 1 → 风险坏账数据转化
  输入:   风险产品坏账.xlsx (风险团队提供)
  输出:   CSV + INSERT SQL → ind.ba_bad_debt_rate_lookup

Step 2 → 首贷+复贷进件量预估
  输入:   Presto 数据库查询
  输出:   复贷进件量预估_{timestamp}.xlsx (7个Sheet)
  算法:   MOB转化率计算 → MA平滑 → 调整系数 → 未来月预估

Step 3 → 权责月度预估
  输入:   权责模板.xlsx + config.yaml 参数
  输出:   权责两个月数据预估_{月份}.xlsx
  逻辑:   死数写入→SUMIFS公式联动

Step 4 → 预估数据入库
  输入:   Step3 输出的 Excel
  输出:   ind.ba_loan_forecast 表
  逻辑:   Excel解析 → 批量INSERT → 行数验证

Step 5 → 数据校验
  输入:   Presto 数据库查询
  输出:   校验报告.txt
  校验:   行数/坏账覆盖率/放款金额/资产底表汇总
```

## config.yaml 每月修改清单

每月只需要改以下区域：

### 1. 月份配置
```yaml
months:
  current: "2026-07"       # 改这里
  next: "2026-08"          # 改这里
  label_current: "7月"     # 改这里
  label_next: "8月"        # 改这里
```

### 2. 全局参数
```yaml
global_params:
  exchange_rate: 17090     # 汇率浮动时更新
  fl_app_cost_idr:         # 首贷每进件成本
    "7月": 2011.00         # 改这里
    "8月": 2050.00         # 改这里
  rl_app_cost_idr:         # 复贷每进件成本
    "7月": 7000.00         # 改这里
    "8月": 7000.00         # 改这里
```

### 3. 进件量死数
```yaml
accrual_app_cnt:
  "首贷":
    "7月": 650000          # 改这里
    "8月": 660000          # 改这里
  "复贷-循环贷":
    "7月": 220000          # 改这里
    "8月": 225000          # 改这里
  "复贷-非循环贷":
    "7月": 165000          # 改这里
    "8月": 168000          # 改这里
```

### 4. 风险参数 (K/L/M/S/V)
```yaml
accrual_rates:
  "7月_首贷_常规_30": {K: 0.26, L: 0.81, M: 0.53, S: 60.08, V: 0.19377}
  # 风险返回后，逐行更新 V 和 S 列
```

### 5. Q分布系数 (如有变化)

## 常见问题

### Q: 数据库连接失败？
检查 Presto 服务是否可访问，用户名密码是否正确。

### Q: Excel 格式变了怎么办？
更新 `templates/` 下的模板文件，`BLOCKS_MONTH1/MONTH2` 字典中的行号。

### Q: 想在现有步骤中加入新逻辑？
在 `steps/` 目录下新建 `.py` 文件，实现 `run(cfg, db, verbose)` 函数，然后在 `pipeline.py` 的 `STEP_REGISTRY` 中注册。
