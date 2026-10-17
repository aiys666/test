<p align="center">
  <img src="https://img.shields.io/badge/status-active-success.svg" alt="Status" />
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License" />
  <img src="https://img.shields.io/badge/platform-Meta%20%7C%20TikTok%20%7C%20Google%20%7C%20Affiliate-brightgreen" alt="Platforms" />
  <img src="https://img.shields.io/badge/focus-%E6%B5%B7%E5%A4%96%E7%8E%B0%E9%87%91%E8%B4%B7-orange" alt="Focus" />
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome" />
</p>

<h1 align="center">🚀 paid-acquisition-strategy</h1>
<p align="center">
  <b>海外现金贷投放策略专家 — 数据驱动的投放全链路决策引擎</b><br />
  <i>从数据诊断到策略输出，让每一分投放预算都花在刀刃上</i>
</p>

<p align="center">
  <a href="#-核心能力">核心能力</a> •
  <a href="#-快速上手指南">快速上手</a> •
  <a href="#-工作流概览">工作流</a> •
  <a href="#-分析脚本工具集">脚本工具</a> •
  <a href="#-自我学习系统">自我学习</a> •
  <a href="#-项目结构">项目结构</a>
</p>

---

## 📊 一句话说清楚

> **这个 skill 解决什么问题？**
>
> 投放团队每天面对海量数据——CPS 涨了、放款掉了、渠道起量失败、素材疲劳了。这个 skill 就像一个 8 年经验的海外投放总监坐在你旁边：**扔数据进去，出来诊断 + 策略 + 可执行动作**。

### 别搞错了：这不是一个知识库

市面上大部分投放资料告诉你的都是"理论"——CPM 是什么意思、Facebook 怎么投、TikTok 怎么做素材。

这个 skill 不一样。它的核心是**数据分析引擎**：

| 传统投放资料 | 这个 skill |
|------------|-----------|
| "当 CPS 上升时，考虑降低出价" | 拆解 CPS 分子分母 → 判断是成本驱动还是分母驱动 → 交叉验证业务数据 → 定位根因是投放问题/风控问题/产品问题 → 输出对应策略 |
| "素材有生命周期" | 读取素材 CTR/频次/CVR 趋势 → 逐条判断冷启/放量/衰减/淘汰阶段 → 给出具体暂停/替换/复制建议 |
| "预算要按效率分配" | 读取各渠道 CPS/Grade1-2/放量上限 → 多约束优化模型 → 给出最优分配 + 预期产出 |

---

## 💪 核心能力

| 能力 | 说明 |
|------|------|
| 🧠 **数据驱动诊断** | 自动识别输入数据形态（表格/CSV/自然语言），MECE 拆解归因 |
| 📈 **CPS 异动定位** | 区分"真问题"（投放效率下降）和"假问题"（风控收紧导致分母收缩） |
| 🎯 **预算优化分配** | 基于边际效率的多约束优化，自动生成放款量最大化的预算方案 |
| 🗺️ **渠道四象限评估** | 效率×质量矩阵，一眼看清谁是明星渠道、谁是优化对象 |
| 📉 **客群质量追踪** | Grade1-2 分层 + FPD 趋势 + LTV 回收曲线，量化渠道质量 |
| 🔄 **自我学习进化** | 用户确认后自动沉淀分析模式，越用越聪明（见 [自我学习系统](#-自我学习系统)） |

### 覆盖渠道

**Meta** (Facebook/Instagram) · **TikTok** · **Google UAC** · **Audience Network** · **Affiliate** · **再营销**

---

## 🚀 快速上手指南

### 前提条件

- Claude Code 已安装
- 你手头有投放数据（有最好，没有也不影响策略输出）

### 使用方法

```bash
# 1. 在你的 Claude Code 项目中启用
claude --skill paid-acquisition-strategy

# 2. 扔数据给 skill 分析（支持各种格式）
claude "帮我看看这周印尼的数据，CPS从18涨到了24"

# 3. 或者直接给策略需求
claude "下个月预算200K，帮我出个分配方案"
```

### 输入什么数据都行

```
✅ 投放平台日报（CSV/Excel/复制的表格）
✅ BI 系统截图或粘贴数据
✅ 自然语言描述（"这周消耗了5万刀，CPS涨了20%"）
✅ 混合输入（部分数据+部分描述）
```

> **没有数据怎么办？** Skill 仍然可以给出基于目标市场和预算范围的策略方案——但会明确告诉你哪些建议是基于经验的估算，需要数据来校准。

---

## 📋 工作流概览

### 五步分析法（每次调用自动执行）

```
Phase 1 — 数据摄入
  └── 识别格式、锚定时间、评估完整性

Phase 2 — 全景诊断
  ├── 整体表现 (消耗/放款/CPS vs 目标)
  ├── 渠道结构 (各渠道占比与效率排名)
  ├── 漏斗异常 (全链路 CVR 逐个环节对比)
  └── 质量扫描 (Grade1-2/FPD 趋势)

Phase 3 — 根因下钻
  ├── CPS 上升 → MECE 拆解 + 风控验证
  ├── 放量困难 → 出价/受众/素材/回传四路排查
  ├── 量升质降 → FPD 与渠道结构分析
  └── FPD 上升 → 客群结构与外部环境分析

Phase 4 — 策略生成
  └── Why + How + What if fails 三段式输出

Phase 5 — 输出 & 追踪
  └── 诊断报告 + 策略建议 + 预期效果 + 监控指标
```

### 输出模板示例

```markdown
# 投放数据诊断报告

## 诊断摘要
- 整体：消耗 $52.8K（+16.8%），放款 2,200（-12.4%），CPS $24（+33%）
- 异常信号：消耗↑但放款↓ | Grade1-2占比反升4pp | 风险通过率骤降37%
- 核心结论：⚠️ 不是投放问题，是风控收紧导致的分母收缩

## 策略建议
1. 暂停投放端调整（根源不在出价/素材）
2. 与风控团队对齐策略调整原因
3. 重新校准目标 CPS 至 $20-22 区间
```

---

## 🛠️ 分析脚本工具集

高频分析逻辑已固化为可复用 Python 脚本，保证计算一致性和准确性。

| 脚本 | 干啥的 | 咋用 |
|------|--------|------|
| `scripts/analyze_trend.py` | 趋势检测 + 异常波动识别 + WoW 环比 | 任何时间序列数据 |
| `scripts/budget_optimizer.py` | 多约束预算最优分配 | 月度/季度预算规划 |
| `scripts/channel_matrix.py` | 渠道效率×质量四象限评估 | 渠道周度复盘 |
| `scripts/cohort_analysis.py` | Grade1-2/FPD/LTV 客群质量追踪 | 月度质量评估 |

```bash
# 示例：趋势分析
cat data.csv | python scripts/analyze_trend.py

# 示例：预算优化
python scripts/budget_optimizer.py --file budget.csv --target-cps 20

# 示例：渠道矩阵
python scripts/channel_matrix.py < channels.csv
```

---

## 🧠 自我学习系统

**这是这个 skill 区别于所有其他投放资料的核心设计。**

每次分析一旦获得你的确认，系统会自动：

```
你认可分析结论
    ↓ 自动触发（不需要你说"记下来"）
沉淀分析模式到 learned-patterns.md
    ├── #001 CPS上升归因：区分风控与投放问题 ✅ 已验证
    ↓
决策规则加入后续分析
    └── IF CPS↑ AND Grade1-2%↑ → 怀疑风控收紧
    ↓
SKILL.md 行为更新
    └── Phase 3 新增风控警示段落
```

每条经验包含完整的：**案例摘要 → 分析步骤 → 关键启示 → IFTTT 决策规则 → 适用场景关键词**。

> 你用得越多，它越懂你的业务逻辑。

---

## 📁 项目结构

```
paid-acquisition-strategy/
├── SKILL.md                          # 核心策略文件（分析工作流+框架，181行）
├── README.md                         # 就是本文件
├── scripts/                          # Python 分析脚本
│   ├── analyze_trend.py              # 趋势分析
│   ├── budget_optimizer.py           # 预算优化
│   ├── channel_matrix.py             # 渠道四象限
│   └── cohort_analysis.py            # 客群质量追踪
├── evals/                            # 测试用例
│   └── evals.json                    # 4个真实场景评估
└── references/                       # 知识库（SKILL.md 引用时自动加载）
    ├── signal-strategy.md            # 回传信号与客群价值策略
    ├── output-templates.md           # 诊断报告+策略方案模板
    ├── error-handling.md             # 异常处理速查表
    ├── learned-patterns.md           # 🧬 自我学习经验库（核心技术资产）
    ├── channel-benchmarks.md         # 各市场成本基准
    ├── ad-placement-guide.md         # 广告点位详解
    └── skill-evolution.md            # 迭代历史
```

---

## 🧪 测试用例

位于 `evals/evals.json`，覆盖四大真实场景：

| # | 场景 | 难度 |
|---|------|------|
| 1 | CPS 飙升分析（印尼 $18→$24，风控收紧干扰） | ⭐⭐⭐ |
| 2 | 月度预算分配（$200K，4个渠道多约束优化） | ⭐⭐ |
| 3 | 渠道质量评估（7个渠道四象限 + FPD 取舍） | ⭐⭐ |
| 4 | 素材疲劳诊断（Facebook 掉量 + 5条素材生命周期） | ⭐⭐⭐ |

---

## 🤝 贡献指南

发现了投放分析中的反直觉模式？想增加一个分析场景？PRs welcome！

1. Fork 本项目
2. 在 `evals/evals.json` 添加你的测试场景
3. 在 `references/learned-patterns.md` 添加你的分析模式（格式见 #005 模板）
4. 提交 PR

---

## ⚠️ 使用声明

- 本技能提供的是投放策略分析与建议，不构成投资建议
- 各渠道成本基准数据基于行业经验，实际因市场（印尼/墨西哥/尼日利亚等）、产品阶段、竞争环境而异
- 最终投放决策请结合你的实际业务数据和风控策略

---

<p align="center">
  <b>Built for 每一个海外现金贷的投放从业者</b><br />
  <sub>如果你做海外现金贷投放，这个 skill 可能比你的投放经理更早发现风控出了问题 😎</sub>
</p>
