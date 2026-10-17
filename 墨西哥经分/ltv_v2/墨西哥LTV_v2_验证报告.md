# 墨西哥 LTV v2 跑数验证报告

生成日期：2026-09-27
底稿：`墨西哥/26.墨西哥LTV全数据.sql`（首贷侧）、`墨西哥经分/墨西哥LTV代码.sql`（月版复贷）、
`墨西哥经分/墨西哥LTV融合_首贷小金额与复贷坏账率.sql`（周版）

---

## 一、交付物

### 1. SQL（`code/墨西哥经分/ltv_v2/`）

| 文件 | 产出表 |
|---|---|
| `01_公共_首贷底表与投放成本.sql` | `mx.ys_ltv_v2_first_loan`、`mx.ys_ltv_v2_ads_cost` |
| `02_月版.sql` | `mx.ys_ltv_v2_m_first_loan_cac`、`mx.ys_ltv_v2_m_double_loan`、`mx.ys_ltv_v2_m_double_group`、`mx.ys_ltv_v2_m_final` |
| `03_周版.sql` | `mx.ys_ltv_v2_w_first_loan_cac`、`mx.ys_ltv_v2_w_double_loan`、`mx.ys_ltv_v2_w_double_group`、`mx.ys_ltv_v2_w_final` |

配套脚本：

| 脚本 | 作用 |
|---|---|
| `_runner.py <sql>` | 逐条执行建表语句 |
| `04_交付_取数写回.py [m\|w]` | 分片取数并写入 Excel 副本 |
| `05_验证报告.py` | Presto 侧跑数验证（第三节数据来源，日志 `_验证输出.log`） |
| `06_验证Excel副本.py [m\|w]` | 读回副本校验（第 5.3 节数据来源） |
| `_chunk_cache/` | 分片缓存，中断可续跑 |

### 2. Excel 副本（原文件未改动）

| 副本 | 对应原文件 |
|---|---|
| `01工作内容/墨西哥风险/墨西哥LTV更新_20260927_v2.xlsx` | `墨西哥LTV更新_20260921.xlsx` |
| `01工作内容/墨西哥风险/墨西哥LTV更新_20260927 - 小金额-周_v2.xlsx` | `墨西哥LTV更新_20260919 - 小金额-周.xlsx` |

---

## 二、两处修复（均经跑数验证生效）

### FIX-1　媒体来源关联键

```sql
-- 原写法（26.sql 第 79 行）：命中 0 行，register_media_source 全部落到 'other'
left join mx.gm_attribution_detail att on cast(r.cust_id as bigint) = att.mid
-- 修复：命中 336,843 行
left join mx.gm_attribution_detail att on r.mid = att.mid
```

验证：两种关联键的命中行数对比

| join_key | hit_rows |
|---|---|
| `cast(cust_id as bigint)` 关联（原写法） | **0** |
| `r.mid` 关联（修复后） | **336,843** |

旁证：`墨西哥/23.墨西哥yjLTV.sql` 用的就是 `a.mid = b.mid`。

修复后 `register_media_source` 分布（8 类）：

| 媒体来源 | 首贷笔数 |
|---|---|
| google | 165,259 |
| facebook | 130,477 |
| organic | 18,857 |
| tiktok | 7,596 |
| other | 7,309 |
| 探知 | 4,083 |
| bj | 2,084 |
| Apple Search Ads | 1,221 |

> 注意：`r.mid` 与 `cast(r.cust_id as bigint)` 是两个不同的 ID 空间，
> 基数相同但**零重叠**。归因走 `r.mid`，首贷↔复贷关联走 `cust_id`，两者互不替代。

### FIX-2　`new_grade_level_main` 分支顺序

```sql
-- 原写法（26.sql 第 22-26 行）：第二个分支恒不可达
when r.app_time >= date '2026-01-01' then t4.sd_creditlevel_main_v4_1
when r.app_time >= date '2026-06-02' then t4.android_newcust_maincreditlevel_charge_v5_2
-- 修复：对调
when r.app_time >= date '2026-06-02' then t4.android_newcust_maincreditlevel_charge_v5_2
when r.app_time >= date '2026-01-01' then t4.sd_creditlevel_main_v4_1
```

验证：2026-06-02 起 V5_2 / V4_1 实际启用规模

| 来源 | 行数 |
|---|---|
| `v5_2` 生效 | **68,284** |
| 两者皆空 → 兜底 9999 | 21 |
| `v5_2` 为空、回落 v4_1 | 9 |

修复前该分支恒不可达，`v5_2` 启用规模为 0。

另：`mx.wenj_sd_market` 中还带 `android_newcust_maincreditlevel_charge_v5_3 / v5_4 / v5_5`，
26.sql 只用到 v4_1 和 v5_2，未纳入。若后续要用 v5_3（2026-06-09 起干净覆盖），需另加分支。

---

## 三、跑数验证结果

### 3.1 首贷可加性检验（加维度只做拆分，不丢数不重复）

| 口径 | 行数 | 笔数 | 合同金额 |
|---|---|---|---|
| 首贷底表 `mx.ys_ltv_v2_first_loan` | 336,886 | 336,886 | 257,858,148 |
| 月版首贷 CAC（全维度）汇总 | **25,097** | **336,886** | **257,858,148** |
| 周版首贷 CAC（全维度）汇总 | **46,676** | **336,886** | **257,858,148** |

笔数与金额三个口径完全一致 → 维度拆分未产生重复计数。

### 3.2 与旧 Excel 的口径对齐

旧 Excel 月版首贷表 grid 声明到 2,433 行，实际**只有 675 行是真数据**，其余 1,758 行为全空行
（历史残留；其 `autoFilter ref="A1:AD676"` = 表头 + 675 行，正好印证）。

| 口径 | 旧 Excel | 新表收敛回该粒度 | 差异说明 |
|---|---|---|---|
| 月版首贷（月×期次×渠道×等级） | 675 | **678** | +3 为这 6 天新增数据 |
| 周版首贷（周×期次×渠道×等级） | 2,287 | **2,372** | +85 同上 |
| 周版首贷（再×小金额） | 3,883 | **4,026** | +143 同上 |

旧 Excel 首贷 `sum(frs_cnt)` = 330,983（2026-09-21 时点）vs 现在 336,886，
差额 5,903 笔即 6 天的自然增长；收敛回 4 维后 `sum(frs_cnt)` 仍是 336,886，
说明是行数增长而非口径变化。

### 3.3 复贷对账

| 环节 | 行数 | 订单数 | 合同金额 |
|---|---|---|---|
| 复贷原始口径（未关联首贷 cohort） | 589,032 | 589,030 | 703,029,513 |
| 月版复贷明细 | 544,506 | 544,501 | 667,599,770 |
| 月版复贷聚合 | 108,254 | 544,504 | 667,599,770 |
| **月版 final（进 Excel）** | **108,254** | **544,504** | **667,599,770** |
| 周版复贷明细 | 544,506 | 544,501 | 667,599,770 |
| **周版 final（进 Excel）** | **167,508** | **544,504** | **667,599,770** |

* 明细 544,506 行中 5 行的 `camera_id` 为空，故 `count(distinct)` 少 5。
* 原始口径 589,032 笔 → 明细 544,506 笔，差 44,526 笔（7.6%）是**首贷不在 cohort 内**的复贷
  （首贷 cohort 从 2024-10 起，更早的首贷无法归属），这部分天然进不了 cohort 分析。
* 聚合/ final 的订单数 544,504 比明细的 544,501 多 3，是极少数 `biz_id` 落进两个 cohort。

### 3.4 `wob` 与汇率

* `wob` 范围 0 ~ 78，月版/周版一致
* 月版首贷 CAC 中汇率缺失月份：**0 行**

---

## 四、结构变更：复贷表去掉 wob 稠密展开

### 变更原因

原设计先把首贷 cohort 键 × `wob(0..max)` 稠密展开，再左连复贷聚合，
使每个 cohort 在每个 wob 都有一行（LTV 曲线不断点）。加入 5 个新维度后：

| | cohort 组合数 | × wob(0..78) | Excel 上限 1,048,576 |
|---|---|---|---|
| 月版复贷 全维度 | 25,097 | **1,982,663** | 超限 |
| 周版复贷 全维度 | 46,676 | **3,687,404** | 超限 |

### 变更内容

改为只输出**真实观测到的 (cohort, wob) 组合**：

* 月版 108,254 行（原 27,732 行）
* 周版 167,508 行（原 82,457 行）

代价：某 cohort 在某 wob 周没有复贷时，不再补一行 0，改由透视表自身聚合。
`double_rnk` 沿用原口径（同一 cohort+wob 下的多个 `loan_period` 各自保留）。

---

## 五、Excel 交付说明

### 5.1 列位（新维度一律追加在末尾，未插入中间）

Excel 透视表缓存按**列顺序索引**引用字段，插入列会让现有透视表全部失效，因此：

| 表 | 原有列 | 新增列（追加） |
|---|---|---|
| 月版 数据源-首贷 | A..AD（30 列） | AE..AJ = product_name, app_version, channel_category, new_grade_level_main, register_media_source, is_low_amount_flag |
| 月版 数据源-复贷 | A..BJ（62 列） | BK..BP = product_name_d, app_version_d, channel_category_d, new_grade_level_main_d, register_media_source_d, is_low_amount_flag_d |
| 周版 数据源-首贷 | A..AE（31 列） | AF..AJ = product_name, app_version, channel_category, new_grade_level_main, register_media_source |
| 周版 数据源-复贷 | A..BL（64 列） | BM..BQ = product_name_d, app_version_d, channel_category_d, new_grade_level_main_d, register_media_source_d |

`数据源-汇率` 未改动。

### 5.2 打开后需要做的一步

副本里的 3 个透视缓存（复贷 / 汇率 / 首贷）与原文件**逐字节一致，未做任何改动**。
它们引用的是整列范围，所以**行数变化会被自动覆盖，打开后刷新即可**。
（行数校验：原 `数据源-首贷` autoFilter 只到 676 行、却声明 dimension 到 2434 行，
现在副本里 autoFilter 与实际行数一致，不再有 1,757 行空尾。）

但新增维度落在缓存范围之外，若要**在透视表里直接引用新维度**：

| 表 | 缓存当前范围 | 需要放宽到 | 新增的列 |
|---|---|---|---|
| 月版 首贷 | `A1:AC1048576` | `A1:AJ1048576` | AE..AJ |
| 月版 复贷 | `A1:BJ1048576` | `A1:BP1048576` | BK..BP |
| 周版 首贷 | `A1:AD1048576` | `A1:AJ1048576` | AF..AJ |
| 周版 复贷 | `A1:BL1048576` | `A1:BQ1048576` | BM..BQ |

> 数据透视表分析 → 更改数据源 → 按上表改范围 → 刷新

不做这一步也不影响原有分析：老维度、老指标全部照旧，只是新维度暂不参与透视。

注：周版两个 sheet 本来就没有 autoFilter（原文件即如此），副本保持一致，非遗漏。

### 5.3 Excel 副本实测校验（`06_验证Excel副本.py`）

不依赖 openpyxl（这些工作簿 openpyxl 打不开），直接按 zip+XML 读回校验：

**月版 `墨西哥LTV更新_20260927_v2.xlsx`**

| 表 | dimension | 数据行数 | 列范围 | 末列 |
|---|---|---|---|---|
| 数据源-首贷 | (25098, 36) | **25,097** | A..AJ | `AJ=is_low_amount_flag` |
| 数据源-复贷 | (108255, 68) | **108,254** | A..BP | `BP=is_low_amount_flag_d` |

日期列以序列号落盘，读回换算正确：`45566 → 2024-10-01`、`46023 → 2026-01-01`。

**周版 `墨西哥LTV更新_20260927 - 小金额-周_v2.xlsx`**

| 表 | dimension | 数据行数 | 列范围 | 末列 |
|---|---|---|---|---|
| 数据源-首贷 | (46677, 36) | **46,676** | A..AJ | `AJ=register_media_source` |
| 数据源-复贷 | (167509, 69) | **167,508** | A..BQ | `BQ=register_media_source_d` |

日期序列号读回：`46272 → 2026-09-07`、`45754 → 2025-04-07`。

两张副本共 4 个数据 sheet 的表头、行数、末列均与设计一致，无空行、无截断。
`is_low_amount_flag` 里的 `<` 已按 XML 规则转义（`小金额(&lt;=500)`），Excel 打开显示正常。

---

## 六、使用口径提示（会影响取数结果，务必看）

### 6.1 `frs_cnt` / `frs_contract_amount` 是 cohort 级属性，**不能 SUM**

复贷表里的这两个字段是 `left join` 首贷侧带过来的，对同一 cohort 的**每一行 wob 都重复填一遍**。

| | 行数 | `sum(frs_cnt)` | 相对首贷真值(336,886)的放大 |
|---|---|---|---|
| 旧 Excel 复贷表 | 27,732 | 26,147,025 | **×77.6** |
| 新表 复贷 final | 108,254 | 9,054,672 | **×26.9** |

放大倍数 = 该 cohort 出现的 wob 行数。**这是原有设计的口径，不是本次改动引入的**
（旧表放大更狠），但如果透视表里对这两列用了「求和」，得到的数一直是错的：

> 要么改用 `最大值`/`平均值`（同一 cohort 内取值相同，两者都正确），
> 要么首贷口径直接从「数据源-首贷」取。

复贷自身的度量（`double_cnt`、`contract_amount`、`fact_t30`、`should_amt_*` 等）
是真正可加的，求和正确。

### 6.2 `double_rnk` 当前恒等于 1

实测 `count(distinct double_rnk)=1`、`max=1`。原因是 `loan_cycle`（`loan_period`）
被其余 10 个键唯一决定，同一 (cohort, wob) 下不存在多个期次，所以排序窗口退化成 1 行。

* 拿 `double_rnk=1` 当去重条件**当前是全选**，不产生过滤效果（也不会出错）。
* 聚合无损已对账：final 的 `sum(double_cnt)` = 544,504，与明细口径一致。
* 这与你确认的「同一 cohort+wob 下的多个 loan_period 各自保留」在设计上一致——
  只是当前数据里恰好没有这种情况，行为留待将来出现时生效。

### 6.3 新增 6 个维度会把原来的 4 维单元拆细

旧表复贷的透视行键是 `ltv_month / app_channel_name / new_grade_level / wob`，
每个单元原本恰好 1 行。现在这 4 个键的一个单元最多被拆成 **171 行**
（按 product_name / app_version / channel_category / new_grade_level_main /
register_media_source / is_low_amount_flag 细分，实测单元行数分布 1～171）。

后果：
* 可加度量（`double_cnt` 等）在该单元求和**仍然正确**；
* 6.1 里那两个冗余列在 4 维单元求和会被放大；
* 若新建透视仍只用老的 4 个行键，看到的是「新维度合并后」的口径——
  这和旧表数值不直接可比。要对齐旧口径，把新维度一并拖进行/筛选区。

---

## 七、复现方式

```bash
cd code
python 墨西哥经分/ltv_v2/_runner.py 01_公共_首贷底表与投放成本.sql
python 墨西哥经分/ltv_v2/_runner.py 02_月版.sql
python 墨西哥经分/ltv_v2/_runner.py 03_周版.sql
python 墨西哥经分/ltv_v2/05_验证报告.py          # Presto 侧跑数验证
python 墨西哥经分/ltv_v2/04_交付_取数写回.py      # 生成 Excel 副本
python 墨西哥经分/ltv_v2/06_验证Excel副本.py      # 读回副本校验
```

注 1：`adhoc` 查询接口单次结果集上限 10,000 行，`04_交付_取数写回.py` 已按
「月份/周次 → 渠道/wob」逐级分片取数，月版共 183 次请求（首贷 25 + 复贷 158 片）。

注 2：每个分片落盘缓存到 `_chunk_cache/`，中断后可续跑；
取全后再用服务端 `count(*)` 对账，不一致直接报错，不会把缺行的数据写进 Excel。

注 3：两个版本**不要并发跑**。共用同一 Presto 会话时服务端串行排队，
先启动的进程会被饿死（实测月版进程 420s 墙钟只推进 17s，最终 `_poll` 超时）。
逐个跑即可。
