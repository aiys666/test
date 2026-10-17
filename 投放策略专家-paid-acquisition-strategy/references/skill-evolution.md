# SKILL.md 迭代记录

> 记录投放策略技能基于用户反馈的自我迭代历史。

| 日期 | 触发分析 | 改进点 | 改进位置 | 用户确认 |
|------|---------|--------|---------|--------|
| 2026-06-02 | 测试用例#1: 印尼CPS从$18涨到$24的分析 | 见 `learned-patterns.md` #001 — CPS上升归因：区分风控与投放问题 | SKILL.md Phase3 新增关键警示段落 | ✅ 用户确认"这条分析思路很正确" |
| 2026-06-02 | 用户要求优化自我学习机制 | 设计主动型自我学习系统：自动感知用户认可→结构化记录→决策规则沉淀→后续分析自动调用 | SKILL.md 新增第七章"自我学习系统"；重构 `learned-patterns.md` 为标准格式（含决策规则、适用场景关键词）；`skill-evolution.md` 格式化 | ✅ 用户要求"当用户明确认同结论时开始自我学习" |
| 2026-06-02 | SKILL.md 过长（618行），用户要求精简 | 按 skill-creator 原则做分层：SKILL.md 精简至 ~180 行（核心工作流+框架）；新建 3 个 reference 文件（signal-strategy.md / output-templates.md / error-handling.md）按需加载 | SKILL.md 从 618 行压缩到 181 行；新增 `references/signal-strategy.md`（回传信号与客群价值）；新增 `references/output-templates.md`（输出模板）；新增 `references/error-handling.md`（异常处理速查）；README.md 更新文件树 | ✅ 用户要求精简 |
