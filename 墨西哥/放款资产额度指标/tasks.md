# Tasks：放款资产额度指标逐笔表

| # | 任务 | 产出 | 状态 |
|---|---|---|---|
| T1 | 改造取数脚本：①按 issue_date 分片循环拉取，绕过 Presto 客户端 10000 行截断；②范围收紧为复贷老客 `is_reloan='old'`；③评级改用 `mx.yj_test_table_250225.android_oldCust_mainCreditLevel_charge_V6_1`（单列）；④`main_used_this` 改为优先取 C003(MAIN FREEZE) 台账增量、恒等式回退 | `放款资产额度指标\fetch_asset_quota.py` | done |
| T2 | Presto 执行全量并落原始结果 | `_out/query_result_raw.csv` | done |
| T3 | 生成逐笔明细 CSV（22 列，英文字段名） | `放款资产额度指标_逐笔_20260901起.csv` | done |
| T4 | 生成 Excel（含字段字典 sheet） | `放款资产额度指标_逐笔_20260901起.xlsx` | done |
| T5 | 抽样验证：评级覆盖率、主额越界率（带容差）、三套逻辑单调性 | 验证输出打印 | done |
| T6 | 清理临时脚本（全部 `_probe_*.py`、`_verify_asset.py`、run 日志） | — | done |

## 验收标准

- 明细行数 ≈ funnel7 `issue_date>=2026-09-01 and if_issue=1 and is_reloan='old'` 的笔数（≈63,309，去重后 63,297），不得等于 10000 整除值。
- V6_1 评级覆盖率 > 95%。
- `main_used_this <= min(main_available_amount, main_daily_max) + 1e-6` 越界率 ≈ 0。
- `avail_current_logic <= avail_tochange_logic <= avail_future_logic`。
- 例子口径回算：当前逻辑 = min(要改的逻辑, 产品上限)。
- 输出列数 = 22。

## 实测结果（2026-10-20 最终跑）

- 明细行数 63,297（原始 63,309，12 笔 biz_id 重复去重）；列数 22。
- V6_1 评级覆盖率 99.69%；`main_used_this` 来源：C003 台账 98.78% / 恒等式回退 1.22%。
- 主额越界率（1e-6 容差）0.0016%（仅 1 笔：`1620000473546921` D_0_05，支用 1560 > 可用 660，差异 900，疑似台账与快照时点不一致）。
- 三套逻辑单调性 100%（62,463 有效行；834 行因主额授予额度缺失为空）。
- 在线临额 7,125 笔、离线临额 6,082 笔、产品上限=15000 共 2 笔。
