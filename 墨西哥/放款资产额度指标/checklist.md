# Checklist：放款资产额度指标逐笔表

- [x] 逐笔明细为「一行一笔放款」，`biz_id` 唯一，范围 = `issue_date>=2026-09-01 且 if_issue=1 且 is_reloan='old'` —— 63,297 行，biz_id 全部唯一
- [x] 明细行数不再被 10000 行截断（原始 63,309 行 → 去重 63,297）
- [x] 输出列数为 22，全部使用英文字段名
- [x] V6_1 评级取自 `mx.yj_test_table_250225.android_oldCust_mainCreditLevel_charge_V6_1`，覆盖率 99.69% > 95%
- [x] `main_grant_amount / main_used_amount / main_available_amount / main_daily_max` 取自 funnel7 对应字段，且 可用 = 授予 − 已占用
- [x] `main_used_this` 优先取 C003(MAIN FREEZE) 台账增量（external_id=biz_id，命中 98.78%），台账缺失时按恒等式回退（1.22%）
- [x] 主额 `支用 <= min(可用, 单日可借上限)` 越界率（1e-6 容差）0.0016%（仅 1 笔 `1620000473546921`）
- [x] 三套逻辑满足 `avail_current_logic <= avail_tochange_logic <= avail_future_logic`，单调性 100%（62,463 有效行）
- [x] 三套逻辑公式与框架截图三例回算一致（要改的逻辑 15000/16000/15000；当前逻辑 1万）
- [x] CSV 与 Excel 均产出，Excel 含「逐笔明细」+「字段字典」两个 sheet
- [x] 临时探针/日志脚本已清理，仅保留可重复执行的 `fetch_asset_quota.py`
