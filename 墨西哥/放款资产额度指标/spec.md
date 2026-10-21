# Spec：放款资产额度指标逐笔表（2026-09-01 起）

> 目标：按用户框架，产出「一行一笔放款」的额度指标明细（CSV + Excel）。
> 框架来源：用户上传截图（主额 / 离线临额 / 在线临额 三组额度列 + 「主额+离线临额」三套逻辑可用额度）。
> 状态：待用户批准后执行。

---

## 一、范围与过滤

- 主体：`mx.report_application_funnel7_table`，`issue_date >= date'2026-09-01'` 且 `if_issue = 1` 且 **`is_reloan = 'old'`（复贷老客）**。
- 粒度：一行 = 一笔放款（`biz_id` 唯一）。
- 预估规模：约 6.3 万笔。
- 兜底：`issue_date` 上界取 `current_date - 1`（批处理已落库）。
- 范围决策（用户确认）：`mx.yj_test_table_250225` 是复贷老客宽表，首贷无评级；框架中「离线临额/在线临额」本身也只适用于复贷，故本表只出复贷老客。

## 二、输出物

| 文件 | 说明 |
|---|---|
| `放款资产额度指标_逐笔_20260901起.csv` | 逐笔明细（英文字段名，UTF-8-BOM） |
| `放款资产额度指标_逐笔_20260901起.xlsx` | 同内容 Excel（含中文表头行 + 字段字典 sheet） |
| `_out/query_result_raw.csv` | 中间产物（SQL 原始结果，便于复核） |

## 三、字段字典（全部字段，共 22 列 = 5 标识评级 + 5 主额 + 4 离线临额 + 5 在线临额 + 3 三套逻辑）

### A. 标识与评级（5 列）

| 列名 | 中文 | 来源与口径 |
|---|---|---|
| `biz_id` | 业务号 | funnel7.biz_id |
| `mid` | 用户号 | funnel7.mid |
| `issue_date` | 放款日期 | funnel7.issue_date |
| `product_level` | 产品 | funnel7.product_level |
| `v6_1_credit_level` | **V6_1评级** | `mx.yj_test_table_250225.android_oldCust_mainCreditLevel_charge_V6_1`，按 `biz_id` 关联 |

> 口径变更（用户指令）：原先设计的「用信时V6_1评级（1635×pid=434）」与「放款时V6_1评级（1635×pid=464）」两列作废。
> 原因：434/464 两条流按 biz_id 对放款笔的覆盖率仅 21% / 63%，远低于 95% 的验收线，且属数据本身的覆盖缺口。
> 现改用复贷老客宽表 `mx.yj_test_table_250225` 的唯一 V6_1 主评级字段，该表每个 biz_id 一行，复贷放款笔覆盖率达 99.7%。

### B. 主额（5 列）— 全部取自 funnel7（已逐笔校验）

| 列名 | 中文 | 口径 |
|---|---|---|
| `main_grant_amount` | 主额-授予额度 | funnel7.`credit_amount`（放款时授信额度快照） |
| `main_used_amount` | 主额-历史已占用 | funnel7.`change_used_grantamount`（放款前主额存量占用） |
| `main_available_amount` | 主额-当前可用额度 | `main_grant_amount - main_used_amount` |
| `main_daily_max` | 主额-单日可借上限 | funnel7.`daily_max_available_limit` |
| `main_used_this` | 主额-当前支用额度 | 优先取 `C003 MAIN FREEZE` 台账增量（`change_used_grantamount − old_used_grantamount`，`external_id = biz_id`）；台账缺失时回退 `contract_amount − temp_grant_amount/1000`（既定口径，命中率 98%+） |

> 校验样本（mid 1040160068980096）：授予 12000、已占用 2400、可用 9600、单日上限 8000、本笔支用 8000 = `min(9600,8000)` ✓；
> 与 change_record 台账独立对账：C009 后 MAIN used=2400 → C003 MAIN FREEZE used=10400，增量 8000 ✓。
>
> 为何以 C003 台账为准：含前砍费的 A 类产品（如 `A_07_01_50_00`）合同额 > 真实主额占用（例：合同 700、到手 350、主额冻结仅 500），
> 若用「合同额 − 临额」会高估支用并出现「支用 > 主额可用」的伪越界（全量 138 笔）。C003 台账增量与合同额在无前砍费产品上完全一致。

### C. 离线临额（4 列）

| 列名 | 中文 | 口径 |
|---|---|---|
| `offline_grant_amount` | 离线临额-授予额度 | 放款时刻该 mid **未过期**的离线临额发放额合计（TEMP 台账，来源事件 C015/C013，有效期 5 天） |
| `offline_used_amount` | 离线临额-历史已占用 | 放款时刻前 TEMP 台账的存量占用（离线来源部分） |
| `offline_available_amount` | 离线临额-当前可用额度 | `offline_grant_amount - offline_used_amount` |
| `offline_used_this` | 离线临额-当前支用额度 | 本笔临额使用且**来源为离线**时 = `temp_grant_amount/1000`，否则 0 |

> 归属规则（已有结论）：本笔若存在 C010（在线临额）事件 → 全部归在线；否则全部归离线；不存在同时使用两类的情况。

### D. 在线临额（5 列）

| 列名 | 中文 | 口径 |
|---|---|---|
| `product_limit_max` | 在线临额-产品上限 | 该笔产品 `ods.s03_product.limit_max / 1000.0`（比索） |
| `online_grant_amount` | 在线临额-授予额度 | 本笔 C010（TEMP）的 `change_total_grantamount`（无 C010 则 0/空） |
| `online_used_amount` | 在线临额-历史已占用 | 本笔 C010 的 `change_used_grantamount` |
| `online_available_amount` | 在线临额-当前可用额度 | `online_grant_amount - online_used_amount` |
| `online_used_this` | 在线临额-当前支用额度 | 本笔临额使用且**来源为在线**时 = `temp_grant_amount/1000`，否则 0 |

### E. 三套逻辑可用额度（3 列）— 分组「主额+离线临额」

设：
- `base = min(main_available_amount, main_daily_max) + offline_available_amount`
- `uncapped = main_available_amount + offline_available_amount`

| 列名 | 中文 | 公式 | 例子回算 |
|---|---|---|---|
| `avail_current_logic` | 当前逻辑（含产品上限1万）可用额度 | `min(base, product_limit_max)` | 1万 / 1万 / 1万 |
| `avail_tochange_logic` | 要改的逻辑（去除产品上限1万）可用额度 | `base` | 15000 / 16000 / 15000 |
| `avail_future_logic` | 未来的逻辑（去产品上限+去单日可借上限）可用额度 | `uncapped` | 21000 / 21000 / 21000 |

> 三例（框架截图）验证：`avail_tochange_logic` = 15000/16000/15000 与截图 col@1730 完全一致；`avail_current_logic` = 1万 与截图一致。
> 「未来」列在截图中被裁切，按逻辑外推为「去单日上限」后的主额可用 + 离线临额可用。

## 四、关联键

- funnel7 ↔ 评级：`cast(f.biz_id as bigint) = cast(y.biz_id as bigint)`（`mx.yj_test_table_250225`）
- funnel7 ↔ 产品上限：`f.product_level` → `ods.s03_product`（按 `product_name`/默认产品映射；D_1_03 默认 pid=6120001545073325）
- 临额事件：`mid` 关联 `ods_view_presto.s05_user_creditlimit_change_record`，时间窗口 = 放款时刻前 ±窗口

## 五、实现步骤（tasks）

1. 取数 SQL（Presto 直连执行）：
   - CTE1 `base`：funnel7 复贷放款笔（含主额 5 列所需字段）
   - CTE2 `yj`：`mx.yj_test_table_250225` 按 biz_id 取 V6_1 评级
   - CTE3 `c010`：TEMP 台账在线临额事件（按 mid + 放款日取最新一条）
   - CTE4 `off`：`mx.yuhan_temp_limit_base_table_his_20260924` 离线临额批次（放款日前 5 天内最近一批）
   - 主查询：join 上述，计算 22 列
2. 落 CSV → 转 Excel（含表头/字典）。
3. 抽样验证：
   - 主额：`main_used_this <= min(main_available_amount, main_daily_max)` 必须 ~100% 成立（越界即数据异常）；
     另报 `main_used_this == min(...)` 精确命中率（未满额支用的笔天然取等号不成立，属正常）
   - 三套逻辑：`avail_tochange_logic >= avail_current_logic` 恒成立
   - 评级覆盖率（V6_1 非空比例，目标 >95%）
4. 清理临时脚本（`_vprobe.py` 等）。

## 六、待确认/风险

- `offline_grant_amount` 的「有效期 5 天」截止判定按放款时刻往前 5 天取 C015/C013。
- `product_limit_max` 按产品配置层取；2026-10-19 起 D_1_03 默认产品改为 15000，故不同放款日可能取到 10000/15000。
- 评级取自 `mx.yj_test_table_250225`，该表最新数据到 2026-10-18，故 10-19 放款（154 笔）评级可能缺失。
