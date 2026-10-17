# Presto DAG 跑批任务清单

> 数据来源：Presto 调度平台 DAG 列表
> 维护人：erik
> 最后更新：2026-08-20

---

## 任务总览

| ID | DAG Name | 描述 | 调度周期 | 核心用途 |
|----|---------|------|---------|---------|
| 376 | `ba_week_report` | 周报任务 | Week | 生成印尼/周报的数据|  
 | 165 | `ba_act_targets_result` | 目标数据 | Day | **每月需手动导入目标数据**，每日刷新，用于计算本月目标偏离度 |
| 156 | `ba_install_apply_should_result` | should apply result | Day | 应放未放结果表，分析应放金额与实际放款的差异，辅助风控决策 |
| 260 | `ba_source_basic_d` | source basic | Day | 投放相关数据，主要应用在BI看版中 |
| 100 | `ba_asset_base_info` |  | Day | 资产基础信息表（放款明细、合同金额、利率等），所有经营分析的核心数据源 |
| 303 | `ba_weekly_report` | ba_weekly_report | Day | 在贷数据，驻外商务会看这个数据，在看板里用到 |
 