-- ======================================================================
-- 放款资产额度指标 v11（逐笔 · 复贷老客 · 2026-09-01 起）
-- 2026-10-25。在 v10 基础上只修 3 处（见【v11 改动】），其余与 v10 完全一致。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【v11.2 改动】★★★ 在线临额占用拆分口径重构（2026-10-26，岳松二次纠错）
--
--   问题：v11.1 把 online_used_inloan_amount / online_used_noloan_amount 写成
--     「本笔 TEMP 台账残差 × 本笔当前结清状态」，加总 ≠ online_used_amount
--     （实测 1,164,884 vs 53,784，完全不闭合）。岳松原话：
--     「在贷占用和无在贷占用，不等于在线占用的金额呀」。
--
--   正确框架（岳松给出的业务语义）：
--     名义发放 online_grant_amount（4000）
--       ├─ 历史存量占用 online_used_amount（1000，C010 change_used_grantamount）
--       │    ├─ 历史未结清在贷占用 online_used_inloan_amount（主体）
--       │    └─ 历史已结清残留占用 online_used_noloan_amount（2-3 月 bug 尾巴）
--       │    闭合：used_amount ≡ inloan + noloan（断言 a12）
--       └─ 实到账可用 online_available_amount（3000 = grant − used_amount）
--            ↓ 客户领取（一次性用完）
--            本笔支用 online_used_this = available
--
--   新口径（on_src_split CTE）：
--     发放时刻(c010.grant_ts)之前，同 mid 下所有**来源笔**(ledger_biz ≠ 本笔)
--     的 TEMP 台账残差（ΣFREEZE − ΣUNFREEZE），按来源笔当前结清状态拆两组：
--       来源笔当前未结清 → online_used_inloan_amount
--       来源笔当前已结清 → online_used_noloan_amount
--
--   实测（17,326 笔持在线 / 150 笔 used_amount > 0）：
--     used_amount = 53,783.75
--       = inloan 14,614.48（45 笔，占 27%）
--       + noloan 39,169.27（106 笔，占 73%，主体是已结清残留）
--     差额 0.0，完美闭合。
--
--   ⚠️ 关键：TEMP 台账 s05_user_creditlimit_used_detail 的 biz_id 是**来源笔**
--     （造成占用的历史笔），mid 是账户 → 拆分必须按 mid join，再按 d.biz_id 拆源。
--   ⚠️ 窗口下界 2026-01-01 覆盖 2-3 月残留 bug 期。
-- ══════════════════════════════════════════════════════════════════════
--
-- ══════════════════════════════════════════════════════════════════════
-- 【v11.1 改动】★★ 在线临额三列恢复「三段式」语义 + 新增当前占用拆分（2026-10-26）
--
--   问题：v10/v11 的 online_used_amount = grant − available，而 available 恒 = grant
--     → **结构性恒 0**，与列名「历史已占用」语义冲突（岳松校验发现）。
--     且 v10 注释「857 弹窗额本身已是净可用额」**不成立**：857 是名义发放额，
--     实到账 = 名义额 − 发放前账户存量占用（SKILL §1.4 金额三段式）。
--
--   修正（与离线侧同结构的三段式）：
--     ① online_used_amount      = C010 change_used_grantamount（发放前账户存量占用
--                                 =「历史已占用」真值；实测 150 笔 >0 / 53,783.8）
--     ② online_available_amount = 名义额 − 存量占用（= 实到账可用额）
--     ③ online_used_this        = 本笔支用（不变）
--   全量验证（17,326 笔持在线 / 8,160 笔有 C010 / 9,166 笔弹窗未领取）：
--     C010 名义额 = 857 弹窗额 8,160/8,160 全中；支用 ≤ 实到账 0 笔违反；
--     支用 = 实到账 8,160 全中（领取后一次性用完）。
--   恒等式 grant − used_amount − available ≡ 0 结构性成立。
--
--   实现：新增 on_occ_led（TEMP 台账残差）、on_st（结清判定）、c010（C010 发放事件，
--         external_id = biz_id，取 change_used_grantamount）三个 CTE。
-- ══════════════════════════════════════════════════════════════════════
--
-- ══════════════════════════════════════════════════════════════════════
-- 【v11 改动】只修 3 处；恒等式、批次去重一律不动
--
--   ① ★ 离线有效期从「自然日 0~5」改为「时刻级 120 小时」
--      v10 写 DATE_DIFF('day', g_date, issue_date) BETWEEN 0 AND 5，等于第 5 个自然日
--      整日都算有效，比真实的 5×24 小时最多宽出一天。
--      实测（全量 67,980 笔 / v10 持有 11,904 笔）：
--        age=5 的 1,815 行里有 305 行落在边界，按下面的三级锚点判 → 290 行确实已过期、
--        15 行在点击用信时仍在有效期（保留）。
--        ① + ② 合计把 316 行由持有翻为不持有（290 边界过期 + 26 笔发放发生在点击之后），
--        holds_offline 11,904 → **11,588**；去重离线可用 10,889,526 → **10,705,510**
--        （−184,016，占 1.69%），逐行可用 14,589,174 → 14,230,923（−358,251）。
--        **使用额分毫未变**（offline_used_this 4,225,829.62、online 3,682,578.75 与 v10 完全一致；
--        316 行里 used_this>0 的笔数为 0）→ 只影响「持有 / 可用」，不影响业绩口径。
--      改法：新增 g.create_time + INTERVAL '5' DAY >= 用信时刻；
--            日粒度窗口保留作粗筛；账龄列仍是自然日口径（保证与 v3 宽表可比）。
--      校验：a11_expired_held = 0（实测 0；v10 自然日口径下这 305 行全部算持有）。
--
--   ② ★ 用信时刻锚点改为三级：TEMP冻结时刻 > funnel.apply_time > release_time
--      ⚠️ 原锚点是 COALESCE(limit_freeze_time, release_time)。limit_frz 只取 TEMP 的
--         FREEZE_LIMIT 行 —— 只有**本笔真的冻结了临额**时才有值，覆盖率仅 20.5%
--         （13,967/67,980）；其余 79.5% 拿 release_time（放款到账时刻）兜底，而到账比
--         冻结晚：中位 +502 秒、p99 +5,002 秒、最长 +65 小时。
--         → 「点击时额度仍在有效期、只是到账晚了几十分钟」的笔被误杀（确实不会误放，
--           但会把本来有效的持有笔判成过期）。
--      实测 mx.wxs_application_funnel.apply_time 覆盖率 **100%**，与台账首个 TEMP
--         FREEZE_LIMIT 只差 **24~33 毫秒**（n_apply_after_freeze = 0）→ 作次选锚点。
--      效果：15 笔「卡点用信」被保住（纯 release 兜底会误判过期；这 15 笔去重可用 1,700，
--            实际支用 0）；反向另有 26 笔在点击后才发放的下批额度被正确剔除（v10 多算）。
--      校验：a11_expired_held = 0、a11_rescued_by_apply_time = 15、a11_apply_time_null = 0。
--      ⚠️ 不能用 funnel.app_time（真正的申请时刻，可早 2 天）；也不能用 release_time
--         单独兜底（就是上面被否掉的旧口径）。
--
--   ③ 产品上限从写死 CASE 改为「生效区间表」
--      v10：CASE WHEN issue_date >= 2026-10-19 AND product_level='D_1_03' THEN 15000
--            ELSE 10000 —— 没有失效日期，测试回滚要改业务 SQL。
--      v11：product_cap CTE 一行一区间（product_level, start_date, end_date, cap_amount），
--            未命中一律回落 10,000。
--      实测：只有 D_1_03 的 184 笔落在 10-19 之后，avail_current_logic 因此比按 1 万算
--            高 60,532.87 比索（9,931,164.77 vs 9,870,631.90）。
--      ⚠️ 产品上限只影响 avail_current_logic（页面可见可用额度），不参与放款钳制。
--      ⚠️ 测试回滚时只改 end_date，不动计算逻辑。
-- ══════════════════════════════════════════════════════════════════════
--
-- 【命名规则】沿用原版：{主体}_{动作}_{amount | this | tag | date | flag | check}
--   _grant_amount      发放额          _used_amount   已占用（本笔之前）
--   _available_amount  当前可用        _used_this     本笔支用
--   _tag 标签   _date 日期   _flag 0/1 标志   _check 诊断列（不参与业务计算）
--   前缀：main_ 主额 / offline_ 离线临额 / online_ 在线临额 / limit_ 临额账户
--
-- ══════════════════════════════════════════════════════════════════════
-- 【v10 改动】★★ 离线/在线可用额度的时间语义分开（v9 用同一个 used_before 去减两边）
--
--   ⚠️ v9 的错：offline_available = 批次额 − used_before
--                online_available  = 弹窗额 − used_before
--      两式减的是**同一个账户级总占用** used_before，等于把同一笔占用扣了两遍。
--      恒等式照样成立（因为 _used_amount 列填的也是 used_before），但两边语义都不对。
--
--   根因：两种临额进账户的**时点不同**
--     · 离线临额：用信**前**就已进账户 → pre_total_amount 含它 → 占用要扣，但要 cap 在发放额内
--     · 在线临额：用信**决策时**才发   → pre_total_amount **不含**它 → 占用不该扣
--
--   实证（2026-10-23，全量 67,980 笔）：
--     · 16,248 笔持在线，**0 笔** online_used_this > 弹窗额，max 超出 0.0
--       → 弹窗额本身就是风控算出的「你现在能额外借多少」，即净可用额
--     · v9 的 online_available 有 124 笔为负（弹窗额 350 − 账户占用 3,793 = −3,443），
--       这 124 笔 online_used_this 全是 0，纯粹是公式造出来的负数
--
--   改法：
--     a) 离线：available = LEAST(批次发放额, acct_available)
--              used_amount = 批次发放额 − available   ← 「本批发放额中被其他在贷吃掉的部分」
--        acct_available 本身已是 GREATEST(pre_total − used_before, 0)（见下方列定义），
--        所以 available ∈ [0, 批次发放额]，恒等式恒成立。
--        （未夹 0 的原始差值仍保留在诊断列 available_amount_check，负的 15 笔在那里可查）
--     b) 在线：available = 弹窗额（持有时），used_amount = 0
--        恒等式 grant − 0 − grant = 0 恒成立
--     c) avail 三口径的离线部分改用 offline_available_amount，不再重算 GREATEST(grant−used,0)
--
--   效果（v9 → v10，★ 已实测，非模拟值）：
--     离线可用为负     48 → 0      在线可用为负 124 → 0      可用>发放额 0 → 0
--     在线用>在线可用 124 → 0
--     离线用>离线可用  74 → 31（残留见下方 OBS08，是 yuhan 批次表金额偏小，非公式问题）
--     ⚠️ 残留 31 笔而非模拟时预测的 26 笔：模拟是在 v9 的 og 输出上做的，
--        而 v10 同时改了 og（时刻级），持有集合和批次金额都变了，两者不可直接比。
--
-- 【v10 断言调整】三条原 MUST0 降级为 OBS，均已归因、非公式缺陷：
--   · 原 E22「合同额 > avail_future」**作废**（约束本身立错了）
--     avail 三口径按业务定义只含「主额 + 离线临额」，而合同额含在线临额和优惠券。
--     实测 5,629 笔违反中 5,264 笔是 online 来源、226 笔是 unknown，纯口径错位。
--     改为 A9：main_used_this + offline_used_this <= avail_future_logic（剔除在线后再比）
--     → online/unknown 来源 **0** 违反；残留 ★实测 22 笔 = OBS09(5) + OBS08(17)，
--       **0 笔未解释**（已逐笔归因核对）。
--   · OBS08 离线用 > 离线可用（★实测 31 笔）：yuhan 批次表记 333 元而账户台账实发 592 元、
--     客户用了 592（30 笔此因 + 1 笔用量 > 账户 total）。账户台账才是真实发放额。
--     offline_grant_amount 保留批次口径不动（发放侧分析框架以 yuhan 表为准）。
--   · OBS09 主额支用 > 主额可用（5 笔）：额度源快照滞后于用信时点。
--     4 笔 2026-10-22 放款，1067 授信决策在 10-17~10-19，期间提过额；
--     查 1067+1077 在 10-22 **无任何决策记录**，三源全停在授信时的 4,100，
--     而台账 MAIN 冻结是 8,000（= 合同额）。
--     第 5 笔 biz 1620000473546921：y 表记 3,000、p/s 记 3,900，3,900−2,340=1,560 = 实际冻结
--     → 兜底顺序把旧值排前面了（规模见下方 TODO-4）。
--   · E25 负金额列阈值放宽到 −1 元：14 笔全落在 [−0.9, 0)。临额使用额 13,997 笔中
--     199 笔带小数，14 笔的小数让它超过取整后的合同额，最大超 0.9 元 → 舍入噪声。
--
-- 【TODO-4（v10 新发现，未修）】credit_amount 三源兜底不一致，规模远大于以上各条：
--   mx.yj_test_table_250225(y) 与 mx.tmp_darren_product_table(p) 有 **7,697 笔不一致（11.3%）**，
--   其中 y<p 1,633 笔、y>p 6,064 笔，avg_y 4,382 vs avg_p 4,254。
--   只有 5 笔触发了 OBS09，但它直接影响 main_available_amount 和 avail 三口径。
--   需用台账 MAIN 冻结额做裁判，确定哪个源对、兜底顺序怎么排。
-- ══════════════════════════════════════════════════════════════════════
--
-- ══════════════════════════════════════════════════════════════════════
-- 【v9 改动】★★ 临额三列硬恒等式（岳松 2026-10-23 指出，v8 有 1,897 笔违反）
--     offline_grant_amount − offline_used_amount − offline_available_amount = 0
--     online_grant_amount  − online_used_amount  − online_available_amount  = 0
--
--   根因：v8 的 available 取**账户口径**（pre_total_amount − used_before），
--         而 grant 取**批次口径**（yuhan 发放额），两者锚点不同 → 相减不为 0，
--         差额恰等于 offline_grant_amount − pre_total_amount。
--
--   改法：available 改以 **grant 为基准**：available = grant − used_amount。
--         这正是岳松从一开始说的口径「批次发 4,000、其他笔占着 2,000 → 可用 2,000」。
--         ⚠️ 不夹 0 —— 占用超过本批发放额时允许为负，让问题暴露在 a0 断言里；
--            夹 0 会破坏恒等式（这是 v8 online 侧用 GREATEST 埋的雷）。
--         avail 三口径参与计算时才按 0 截断（放开上限不可能"倒扣"额度）。
--
--   ★ 这两条恒等式已作为 A0 断言放在校验段**最前面**，是任何改动后的第一道闸。
--     v5→v8 一版版漏，就是因为没把它当硬断言守。
-- ══════════════════════════════════════════════════════════════════════
--
-- ══════════════════════════════════════════════════════════════════════
-- 【v8 改动】★ 可用额度的时间锚点改为「**用信决策之前**」
--   起因：岳松指出 biz 1620000464246378 —— 用信前持有离线 5,650，v7 却填 0。
--
--   ⚠️ v7 的因果搞反了：C010 把账户 total 从 5,650 覆盖成 4,000，是「客户选了在线」的
--      **结果**，不是「离线本来就没了」的原因。客户用信前确实持有 5,650 离线可用，
--      只是**没选它**。没用 ≠ 不可用。
--
--   根因：limit_last_grant / limit_state 的窗口是 create_time <= 本笔冻结时刻，
--         **把本笔自己的 C010 也算进去了** → 用信过程中发生的事污染了用信前的状态。
--
--   改法：
--     a) 两个 CTE 都加 external_id <> 本笔 biz_id，排除本笔自己触发的事件。
--        （C015/C013 的 external_id 是 'mid_时间戳'、不是 biz_id，所以不会误剔离线批次）
--     b) 可用额度基准从 limit_frz（本笔冻结行）改为 limit_state（用信前状态），
--        新增 pre_total_amount 列；limit_total_amount 保留为诊断列。
--     c) ★ holds_offline 与 holds_online **不再互斥** —— 用信前持有离线、用信时又被
--        弹窗发了在线，两个都"持有"；互斥的只有最终"用了哪个"（used_source_tag）。
--        v7 给 holds_offline 加「账户没被 C010 覆盖」的条件，等于让本笔自己的弹窗
--        把离线持有量抹掉，是同一个因果错误。
--     d) online_available_amount = 弹窗额 − 用信前账户占用（原来取账户 total，含本笔影响）。
--
--   该笔 v8 预期：holds_offline=1、offline_available=5,650、holds_online=1、online_available=4,000，
--   avail_future = 主额可用 18,933.34 + 5,650 = 24,583.34
-- ══════════════════════════════════════════════════════════════════════
--
-- ══════════════════════════════════════════════════════════════════════
-- 【v7 改动】★ 把「持有可用额度」与「本笔用了哪种临额」彻底解耦
--   起因：岳松发现 biz 1620000464246378 —— 离线批次发了 5,650（账龄 2 天、有效期内），
--         但 offline_available_amount = 0，于是 avail 三口径里的离线部分也是 0，总可用金额不对。
--
--   根因：v6 把 _used_amount / _available_amount 也按 used_source_tag 归属了。
--         **持有 ≠ 使用** —— 客户持有多少可用额度，和他这笔用不用它是两回事。
--         影响最大的是「本笔没用临额、但账户里正躺着有效离线额度」的 **6,942 笔 / 持有 1,273.5 万**，
--         它们的可用额被填成 0 → avail 三口径系统性偏低 → 放开上限的反事实测算偏低。
--
--   改法：
--     a) 新增 limit_state CTE —— 没动用临额的笔没有 TEMP 冻结行，limit_frz 取不到账户状态，
--        退回「放款时刻账户最后一条 TEMP 事件」的 total/used。
--     b) 新增 limit_last_grant CTE —— 判断账户里的额度此刻属于谁。
--        ★ 实证：C010 发放是**整体替换**账户总额度（7,648 笔 new_total 100% = 857 弹窗额），
--          其中 1,719 笔是**调低**。反例 biz 1620000464246378：C015 发 5,650 → C010 覆盖成 4,000。
--          所以被 C010 覆盖后离线额度真的没了，offline_available = 0 是对的 ——
--          用信那一刻客户只剩「用不用这 4,000 在线」这一个选择。
--     c) 新增 holds_offline / holds_online 两个标志列，_used_amount 与 _available_amount 改看它们；
--        _used_this 仍按 used_source_tag 归属（互斥不变）。
--     d) avail 三口径的临额部分改用 holds_offline（仍只含离线，不含在线）。
--
--   岳松口径（v7 已按此实现）：批次发 4,000、该客户其他在贷笔占着 2,000
--     → 可用 2,000、本笔最多只能用 2,000。即 available = 账户总额度 − 其他笔已占用，
--       对**所有持有者**都算。
-- ══════════════════════════════════════════════════════════════════════
--
-- ══════════════════════════════════════════════════════════════════════
-- 【v6 改动】三处，都是岳松 2026-10-23 验数时发现的
--   改动A  offline_grant 加有效期窗口 age ∈ [-1, 4]
--          原因：v5 只要求 data_date <= issue_date+1，过期批次也照取 → offline_grant_amount
--          是个无意义的历史值，于是出现「offline_available_amount > offline_grant_amount」。
--          实测：账龄正常(均 1.5 天)的 6,012 笔账户 total 与批次发放额 100% 相等；
--                不等的 125 笔账龄都在 9 天左右（反例 biz 1620000476699318 账龄 46 天）。
--          → 加有效期后两个口径同源，「可用 > 发放」自然消失。
--
--   改动B  offline_grant 剔除减息组与对照组（它们「圈了不发」）
--          实测 C015/C013 命中率：临额组 100%、临额减息组 100%、减息组 2.7%、对照组 0.7%
--          → 过滤条件 tag LIKE '%临额%' AND tag NOT LIKE '%对照组%'（两个都要，
--            因为「临额对照组」同时含这两个词）
--          ⚠️ 连带影响：只在减息组出现过的 mid 若用了临额，会从 offline 改判为 unknown。
--             三笔验证单里 biz 1620000467102678 正是此例（它的批次是 0910减息测试组_无在贷、
--             本笔 1386 tag=0），v6 下会变成 unknown —— 这是对的：减息组不发额度、在线也没发，
--             来源确实判不出。详见第③段断言 a7。
--
--   改动C  avail_current/tochange/future 三口径**移除在线临额**，恢复原版「主额 + 离线临额」定义
--          原因：v5 误用池级 limit_total_amount，把在线也算进来了，污染 7,650 笔 / 373.3 万。
--          反例 biz 1620000473712741：v5 avail_tochange=14,000（含在线 4,000）、v6=10,000
--          为什么在线不该进：这三个口径用来测算「放开产品上限/单日上限能多放多少」，
--          而在线临额是池外叠加、不受这两个上限约束的，放进来会把反事实算高。
-- ══════════════════════════════════════════════════════════════════════
--
-- 【离线与在线互斥 —— 只对"用了哪种"成立，不对"持有多少"成立】
--   ✅ 互斥：offline_used_this / online_used_this / unknown_used_this 三列**最多一列非零**
--            （同一笔只会用其中一种，用 used_source_tag 一列即可判定走哪条路）
--   ❌ 不互斥：offline_available_amount / online_available_amount **可以同时 > 0**
--            （用信前持有离线 + 用信时又被弹窗发在线，实测 4,062 笔两者都持有）
--            offline_used_amount / online_used_amount 同理（都是「发放额被存量占用吃掉
--            的部分」，与本笔支用解耦，故不互斥）。
--   ⚠️【v10 删掉了 v9 这里的错误表述】v9 原文写「_used_amount 亦然、_available_amount 亦然」，
--      那是 v7 的遗留（当时 holds 靠 last_grant_type 判定、天然互斥），
--      v8 取消 holds 互斥时漏改，且与校验段 a2_both_avail_ok「允许同时 > 0」自相矛盾。
--   ⚠️ 两列可用额**不能相加**：共用一个额度账户（limit_main_id），账户 total 被最后一次
--      发放事件**覆盖**（不叠加）。相加得到的数不对应任何真实状态 ——
--      反例 biz 1620000464246378：离线可用 5,650 + 在线可用 4,000 = 9,650，而账户 total 实为 4,000。
--      要看「这个账户到底还能动用多少」，用 acct_available。
--
-- ======================================================================
-- 【相对原版改了 6 处】
--   改动1 窗口上界：DATE '2026-10-20' → DATE_ADD('day', -1, CURRENT_DATE)
--         yj_test_table_250225 每日 05:42 重跑，当日放款笔必然缺（原窗口实测缺 434 笔）。
--         建表后务必跑第③段覆盖率对账，< 99% 不要用。
--
--   改动2 ★★ 来源归属：废弃「C010 金额匹配 + else 全归离线」的排除法。新判据：
--           ① 在线 = **本笔自己** online_grant_flag=1（1386）且 online_grant_amount>0（857）
--           ② 否则查 mx.yuhan_temp_limit_base_table_his_20260924（离线发放事实表，按 mid）
--              取放款日前最近一条批次 → 离线
--           ③ 都没有 → used_source_tag='unknown'，金额落 unknown_used_this，不吞进离线
--         为什么第①条是硬门槛：在线临额按本笔主额支用算额
--           （理论额 = floor(主额冻结/20)×20 × 比例，type1 50%/60%、type2 40%、type3 20%），
--           所以**主额支用=0 时在线发放必然=0**。
--         实证反例（三笔本笔 1386 tag 全为 0、857 全输出 0 → 全是离线）：
--           biz 1620000467102678：09-11 某笔 C010 发 4800 当场用光 → 09-14 03:29 C008 解冻
--                                 → 09-14 06:47 本笔冻结 2000。那个 C010 属 biz 1620000465688819
--           biz 1620000471903111：09-22 19:23 某笔 C010 1800 → 09-22 21:00 C015 把 total 覆盖成 3600
--                                 → 09-25 11:40 本笔 total 3600 / 冻结前占用 1800 → 本笔用 1800
--                                 yuhan 批次 0923临额测试组_有在贷_2 / 发放 3600
--           biz 1620000484563011：10-06 C015 发 10500 → 10-07 某笔 C010 把 total 覆盖降到 4000
--                                 → 10-18 09:19 另一笔(1620000483123671)的 C010 → 09:23 解冻到占用 2700
--                                 → 09:59 本笔 total 4000 / 占用 2700 → 本笔用 1300
--                                 该笔 used_detail 只有 TEMP 冻结、**无 MAIN 冻结行**，主额确实 0
--         → 核心教训：**发放事件挂在【发起那笔】的 biz 上，不是本笔**。
--           既不能用「存在 C010」判，也不能用「账户最后一次发放事件类型」判（两种错法都踩过）。
--
--   改动3 ★ 「已占用 / 当前可用」改为与账户总额度**同源**：
--         三个值全部取自本笔 TEMP 冻结行（change_action='FREEZE_LIMIT'、external_id=biz_id）：
--           limit_total_amount  = change_total_grantamount  冻结时账户总额度
--           *_used_amount       = old_used_grantamount      冻结前账户已占用
--           *_available_amount  = 前者 − 后者
--         原版 grant 卡 5 天窗口、used 不卡窗口 → 36 笔出现 grant=0 而 used=7,750~10,500 的自相矛盾；
--         且「release_time − 5 天」是时刻级减法，离线批次固定 21:00~23:30 跑，实测
--         biz 1620000475860535 的批次 09-30 23:30:10.904 比窗口下界 09-30 23:30:43 早 33 秒被切掉。
--         ⚠️ change_total_grantamount 是「账户新总额度」**覆盖式**，不是本次新增额，
--            绝不可对多次发放事件 SUM（实测 C015 序列 total = 3650→1300→2500→2400→1400→1500）。
--
--   改动4 offline_grant_amount 改从 yuhan 离线发放事实表按 mid 取（原取 C015/C013 事件）。
--         ⚠️ 它是**批次口径**（这一批给了多少），可能大于 limit_total_amount（账户口径，会被后续
--            发放事件覆盖）。两者不强求相等 —— 例 biz 1620000484563011：批次发 10,500，
--            但账户 total 已被覆盖成 4,000，占用 2,700，故实际可用 1,300。
--         ⚠️【v10 更正】v9 这里写「data_date = 实际发放日 + 1 天，故窗口上界用 issue_date + 1」。
--            实测这个偏移**不统一**（2026-09-01 起，按台账 C015/C013 的 create_time 对比）：
--              +1 天 11,508 笔（发放时刻均 21.2 时，当晚跑、标次日）
--              +0 天  2,114 笔（发放时刻均 3.7 时，**凌晨 0~6 点跑、标当天**）
--              +2 天     78 笔
--            所以 data_date 只能定位批次，有效期和账龄必须用台账 create_time。
--            v10 已改成时刻级，详见 offline_grant CTE 内的【v10 改动】。
--         ⚠️ 该表是单期快照（表名带日期），换表时此处要同步改。
--
--   改动5 main_used_this 兜底补扣 voucher_limit（原注 5 已要求、原代码未实现）。
--         实测 193 笔券单都从台账取到真值、没走到兜底，故当前 0 笔差异；属潜在风险。
--
--   改动6 删掉重复的 offline_grant_tag（原版 SELECT 两次，CREATE TABLE AS 会因重复列名失败）
--         与末尾 limit 100000（网关 10,000 行硬顶突破不了，且**静默截断不报错**）。
--
-- 【新增列清单】（全部按原版命名规则）
--   offline_grant_date        批次标签日（yuhan.data_date，**只能用来定位批次**，不能算账龄）
--   offline_grant_time        【v10】台账 C015/C013 的真实发放时刻 ← 账龄与有效期的基准
--   offline_grant_age_days    【v10 改口径】真实账龄 = 放款日 − 发放日，取值域 [0,5]
--                             （v9 用 data_date 算，因 +0/+1/+2 偏移不统一而恒偏小约 1 天）
--   offline_expire_days       【v10 新增】剩余有效期 = 5 − 账龄，与 v3 宽表同口径
--   offline_batch_seq         【v10 新增】同一 (mid, 批次) 内按放款时间的序号。
--                             ⚠️ 算「总共发了多少离线临额」必须加 offline_batch_seq = 1 去重，
--                                否则同一批额度会在该 mid 的每笔订单上各记一次（实测虚增 60.8%）
--   offline_grant_ratio_tag   档位 10%/20%/30%（批次后缀 _1/_2/_3）
--   online_grant_flag         本笔是否发放了在线临额 0/1（1386 节点）
--   used_source_tag           本笔临额来源 offline/online/unknown/none
--   unknown_used_this         判不出来源的本笔临额使用额（不吞进离线）
--   limit_main_id             临额账户号（源表原名）
--   limit_freeze_time         本笔冻结临额的时刻（仅本笔真的冻结临额时有值，覆盖 20.5%）
--   apply_time                  【v11】用信确认时刻 funnel.apply_time（覆盖 100%）；有效期/冻结锚点次选
--   limit_total_amount        本笔冻结时账户总额度
--   available_amount_check    诊断：不夹 0 的剩余可用原值，< 0 = 上游总额度未同步
--   used_this_check           诊断：yj 与台账的使用额差，≠ 0 = 台账落库延迟
--
-- 【已过期的注释，原版请删掉】原版写「yj 表同一 biz_id 有 4 条完全相同的重复行」。
--   2026-10-22 实测 rows/biz_uniq 相等，**dup_ratio = 1.0，上游已修复**。
--   ROW_NUMBER() _rn=1 现在是 no-op（无害，保留作防御）。
--
-- 【结构】两段式：第①段 base 落表，第②段建宽表，第③段校验。
--   这样既绕开 Presto stage 150 上限（原版为此让 s857 不能 JOIN base、daily_max 规则不能单独建 CTE），
--   也绕开网关 10,000 行结果集硬顶（分析一律对宽表做聚合）。
-- ======================================================================


-- ══════════════════════════════════════════════════════════════════════
-- 第①段：base 落表
-- ══════════════════════════════════════════════════════════════════════
DROP TABLE IF EXISTS mx.yj_quota_base;

CREATE TABLE mx.yj_quota_base AS
WITH prod AS (
  SELECT CAST(biz_id AS VARCHAR)                        AS biz_id,
         MAX(CAST(credit_amount AS DOUBLE))             AS credit_amount,
         MAX(CAST(daily_max_available_limit AS DOUBLE)) AS daily_max_available_limit
  FROM mx.tmp_darren_product_table
  WHERE etl_date >= '20260825'
  GROUP BY 1
),
dm AS (
  SELECT CAST(biz_id AS VARCHAR)                         AS biz_id,
         MAX(TRY_CAST(risk_credit_limit AS DOUBLE))       AS risk_credit_limit,
         MAX(TRY_CAST(change_used_grantamount AS DOUBLE)) AS change_used_grantamount
  FROM mx.darren_bizid_used_grantamount
  WHERE create_time >= TIMESTAMP '2026-08-25 00:00:00'
  GROUP BY 1
),
s21auth AS (
  -- 授信决策节点 1067（CHAMPION），复贷放款笔覆盖率 100%
  SELECT CAST(biz_id AS BIGINT) AS biz_id,
         MAX(TRY_CAST(NULLIF(regexp_extract(CAST(outputdata AS VARCHAR),
             '"credit_amount":(-?[0-9.]+)', 1), '') AS DOUBLE)) AS credit_amount,
         MAX(TRY_CAST(NULLIF(regexp_extract(CAST(outputdata AS VARCHAR),
             '"daily_max_available_limit":(-?[0-9.]+)', 1), '') AS DOUBLE)) AS daily_max_available_limit
  FROM ods.s21_risk_model_record
  WHERE modelmainid = 1067 AND strategytype = 'CHAMPION' AND biz_id IS NOT NULL
    AND etl_date >= '20260820'            -- 【v9】★ 分区裁剪：不加会全分区扫描，
    AND createtime >= TIMESTAMP '2026-08-20 00:00:00'   --   既慢又会撞上无关老分区的 HDFS 坏块
  GROUP BY 1
),
usedm AS (
  SELECT CAST(biz_id AS BIGINT) AS biz_id,
         MAX(TRY_CAST(risk_credit_limit AS DOUBLE)) AS main_used_this
  FROM ods_view_presto.s05_user_creditlimit_used_detail
  WHERE limit_type = 'MAIN' AND change_action = 'FREEZE_LIMIT' AND biz_id IS NOT NULL
    AND create_time >= TIMESTAMP '2026-08-25 00:00:00'
  GROUP BY 1
)
SELECT * FROM (
  SELECT CAST(y.biz_id AS BIGINT)                                  AS biz_id,
         y.mid,
         y.issue_date,
         y.release_time,
         CAST(y.product_level AS VARCHAR)                          AS product_level,
         CAST(y.contract_amount AS DOUBLE)                         AS contract_amount,
         CAST(COALESCE(y.temp_grant_amount, 0) AS DOUBLE) / 1000.0 AS temp_used,
         COALESCE(CAST(y.credit_amount AS DOUBLE), p.credit_amount, s.credit_amount)
                                                                   AS credit_amount,
         COALESCE(CAST(y.change_used_grantamount AS DOUBLE), d.change_used_grantamount, 0)
                                                                   AS change_used_grantamount,
         COALESCE(CAST(y.daily_max_available_limit AS DOUBLE), p.daily_max_available_limit,
                  s.daily_max_available_limit)                     AS daily_max_available_limit,
         COALESCE(CAST(y.risk_credit_limit AS DOUBLE), d.risk_credit_limit, u.main_used_this)
                                                                   AS risk_credit_limit,
         CAST(y.android_oldCust_mainCreditLevel_charge_V6_1 AS DOUBLE)
                                                                   AS android_oldcust_maincreditlevel_charge_v6_1,
         ROW_NUMBER() OVER (PARTITION BY CAST(y.biz_id AS BIGINT)
                            ORDER BY y.update_time DESC)            AS _rn
  FROM mx.yj_test_table_250225 y
  LEFT JOIN prod    p ON p.biz_id = CAST(y.biz_id AS VARCHAR)
  LEFT JOIN dm      d ON d.biz_id = CAST(y.biz_id AS VARCHAR)
  LEFT JOIN s21auth s ON s.biz_id = CAST(y.biz_id AS BIGINT)
  LEFT JOIN usedm   u ON u.biz_id = CAST(y.biz_id AS BIGINT)
  WHERE y.issue_date >= DATE '2026-09-01'
    AND y.issue_date <= DATE_ADD('day', -1, CURRENT_DATE)      -- 【改动1】
    AND y.if_issue  = 1
    AND y.is_reloan = 'old'
    AND y.biz_id IS NOT NULL
) t
WHERE t._rn = 1
;


-- ══════════════════════════════════════════════════════════════════════
-- 第②段：最终宽表
-- ══════════════════════════════════════════════════════════════════════
DROP TABLE IF EXISTS mx.yj_asset_quota_v11;

CREATE TABLE mx.yj_asset_quota_v11 AS
WITH s1077 AS (
  -- daily_max_available_limit 的矛盾修正源（口径未改）：仅当 yj 缺失或 yj < 本笔占用主额时取较大值
  -- 窗口上界必须是本笔 release_time：同日放款后若又发起申请会再跑一次 1077 并落更低的值
  -- 反例 biz 1620000470988726：09-26 08:20 放款、19:21 又跑 1077 记成 8000，放款时真实值 10000
  SELECT biz_id, daily_max_available_limit FROM (
    SELECT b.biz_id,
           TRY_CAST(NULLIF(regexp_extract(CAST(r.outputdata AS VARCHAR),
               '"daily_max_available_limit":(-?[0-9.]+)', 1), '') AS DOUBLE) AS daily_max_available_limit,
           ROW_NUMBER() OVER (PARTITION BY b.biz_id ORDER BY r.createtime DESC) AS rn
    FROM mx.yj_quota_base b
    JOIN ods.s21_risk_model_record r
      ON  CAST(r.mid AS VARCHAR) = CAST(b.mid AS VARCHAR)
     AND  r.modelmainid = 1077 AND r.strategytype = 'CHAMPION'
     AND  r.etl_date   >= '20260701'
     AND  r.createtime >= TIMESTAMP '2026-07-01 00:00:00'
     AND  r.createtime <= COALESCE(b.release_time,
                                   CAST(DATE_ADD('day', 1, b.issue_date) AS TIMESTAMP))
    WHERE regexp_extract(CAST(r.outputdata AS VARCHAR),
            '"daily_max_available_limit":(-?[0-9.]+)', 1) <> ''
  ) t WHERE rn = 1
),
online_grant AS (
  -- 在线临额**弹窗发放额**（857 节点），与使用额解耦：客户未领取时照样有值
  -- tag=0 时 857 输出 0，故 HAVING > 0；857 是通用变量节点，必须按 key 正则取
  SELECT CAST(r.biz_id AS BIGINT) AS biz_id,
         MAX(TRY_CAST(NULLIF(regexp_extract(CAST(r.outputdata AS VARCHAR),
             '"temp_credit_amount":(-?[0-9.]+)', 1), '') AS DOUBLE)) AS online_grant_amount
  FROM ods.s21_risk_model_record r
  WHERE r.modelmainid = 857 AND r.strategytype = 'CHAMPION' AND r.biz_id IS NOT NULL
    AND r.etl_date >= '20260825'          -- 【v9】★ 分区裁剪
    AND r.createtime >= TIMESTAMP '2026-08-25 00:00:00'
  GROUP BY 1
  HAVING MAX(TRY_CAST(NULLIF(regexp_extract(CAST(r.outputdata AS VARCHAR),
             '"temp_credit_amount":(-?[0-9.]+)', 1), '') AS DOUBLE)) > 0
),
online_flag AS (
  -- 【改动2】本笔是否发放了在线临额（1386 节点）—— 来源归属第一道硬门槛
  SELECT CAST(r.biz_id AS BIGINT) AS biz_id,
         MAX(TRY_CAST(NULLIF(regexp_extract(CAST(r.outputdata AS VARCHAR),
             '"temp_credit_amount_issue_tag":(-?[0-9.]+)', 1), '') AS DOUBLE)) AS online_grant_flag
  FROM ods.s21_risk_model_record r
  WHERE r.modelmainid = 1386 AND r.strategytype = 'CHAMPION' AND r.biz_id IS NOT NULL
    AND r.etl_date >= '20260820'          -- 【v9】★ 分区裁剪
    AND r.createtime >= TIMESTAMP '2026-08-20 00:00:00'
  GROUP BY 1
),
limit_frz AS (
  -- 【改动3】本笔临额冻结行：一行同时给出 账户总额度 / 冻结前占用 / 冻结后占用
  --   external_id = biz_id；三个值同源，天然自洽，不需要任何时间窗口
  SELECT CAST(c.external_id AS VARCHAR)                                           AS biz_v,
         MAX(c.create_time)                                                        AS limit_freeze_time,
         MAX_BY(c.limit_main_id, c.create_time)                                    AS limit_main_id,
         MAX_BY(CAST(c.change_total_grantamount AS DOUBLE), c.create_time)         AS limit_total_amount,
         MAX_BY(CAST(COALESCE(c.old_used_grantamount,0) AS DOUBLE), c.create_time) AS used_before,
         MAX_BY(CAST(c.change_used_grantamount AS DOUBLE), c.create_time)          AS used_after
  FROM ods_view_presto.s05_user_creditlimit_change_record c
  WHERE c.limit_type = 'TEMP' AND c.change_action = 'FREEZE_LIMIT'
    AND c.external_id IS NOT NULL
    AND c.create_time >= TIMESTAMP '2026-08-25 00:00:00'
  GROUP BY 1
),
biz_apply AS (
  -- 【v11 新增】用信时刻锚点：mx.wxs_application_funnel.apply_time
  --
  --   ⚠️ 为什么需要它：limit_frz 只取 TEMP 的 FREEZE_LIMIT 行 —— 只有**本笔真的冻结了
  --      临额**时才有值，覆盖率仅 20.5%（13,967/67,980）。其余 79.5% 的笔原先拿
  --      release_time（放款到账时刻）兜底，而到账晚于冻结：中位 +502 秒、p99 +5,002 秒、
  --      最长 +65 小时 → 「点击用信时额度仍在有效期、只是到账晚了几十分钟」的笔被误杀。
  --
  --   ★ 实测（2026-10-25 全量 67,980 笔）：
  --       apply_time 覆盖率 100%，与台账首个 TEMP FREEZE_LIMIT 只差 **24~33 毫秒**
  --       （p05 = p95 = 0 分钟，n_apply_after_freeze = 0，即 apply 从不晚于 freeze）
  --       → 用 funnel.apply_time 作**次选锚点**（limit_freeze_time > apply_time > release_time）。
  --     改判结果：305 笔 age=5 差异里 290 笔确实已过期、**15 笔在点击时仍有效**
  --       （holds_offline +15，可恢复去重可用额约 1,700 比索）。
  --   ⚠️ 用 app_time（真正的申请时刻，可早 2 天）不对，必须用 apply_time（确认用信/额度冻结）。
  SELECT CAST(f.biz_id AS VARCHAR) AS biz_v,
         MAX(f.apply_time)          AS apply_time
  FROM mx.wxs_application_funnel f
  WHERE f.issue_date >= DATE '2026-08-25'   -- 下界放宽，兜住 T+1 日期约定差异
    AND f.issue_date <= CURRENT_DATE
    AND f.apply_time IS NOT NULL
  GROUP BY 1
),
offline_grant AS (
  -- 离线发放**事实**表（按 mid），取放款日前最近一条**仍在有效期内**的批次
  --
  -- 【v6 改动A】★ 加有效期窗口 age ∈ [-1, 4]
  --   v5 只要求 data_date <= issue_date+1，哪怕那批早过期了也照取 → offline_grant_amount
  --   成了个无意义的历史值，而 offline_available_amount 是账户当前实况，两者没可比性，
  --   于是出现「可用 > 发放」这种看起来不合理的行。
  --   实测根因：账龄正常(均 1.5 天)的 6,012 笔里账户 total 与批次发放额 **100% 相等**；
  --   不等的 125 笔账龄都在 9 天左右（反例 biz 1620000476699318：批次 0819、放款 10-04，账龄 46 天）。
  --   加有效期后两个口径同源，「可用 > 发放」自然消失。
  --
  -- 【v6 改动B】★ 剔除减息组与对照组 —— 它们是「圈了不发」
  --   实测 C015/C013 事件命中率：临额组 100%、临额减息组 100%、
  --                              减息组 2.7%、对照组 0.7%（1021 批次起的灰度对照）
  --   不剔除会让发放人数虚高 2,599 人、发放额虚高 531 万，且把「只在减息组出现过」的 mid
  --   误判成 offline 来源。注意「临额对照组」同时含「临额」和「对照组」，故两个条件都要。
  -- ══════════════════════════════════════════════════════════════════
  -- 【v10 改动 ★★】有效期窗口从**日粒度**改成**时刻级**，并挂上台账拿真实发放时刻
  --
  --   ⚠️ v9 的错：窗口写 DATE_DIFF(data_date, issue_date) BETWEEN -1 AND 4。
  --      下界 -1 等价于 data_date = issue_date + 1，即这批额度的发放发生在**放款当日之后**。
  --      实测 age = -1 共 2,134 笔，其中 **1,904 笔 release_time 早于 21:00**
  --      （离线批次固定当晚 21:00~23:30 跑），这些笔在用信决策时该额度根本还不存在，
  --      却被判成「用信前持有」→ holds_offline 误置 1 → offline_available 凭空多出整批额
  --      （涉及发放额 270 万）→ avail 三口径系统性虚高。
  --      这直接违反 v8 为 limit_state / limit_last_grant 立的时间锚点：
  --      那两个 CTE 早已是时刻级（create_time <= 冻结时刻），唯独这里还是日粒度。
  --      好消息：这 1,904 笔里只有 25 笔真用了离线临额 → 业绩贡献口径几乎不受影响。
  --
  --   ⚠️ 为什么不能简单把下界改成 0、或给 data_date 减一天：
  --      data_date 相对台账实际发放时刻的偏移**不统一**（实测 2026-09-01 起）：
  --        偏移 +1 天：11,508 笔，台账发放时刻均 21.2 时（当晚跑、标次日）
  --        偏移 +0 天： 2,114 笔，台账发放时刻均 3.7 时（**凌晨 0~6 点跑、标当天**）
  --        偏移 +2 天：    78 笔
  --      （根源：14.墨西哥离线发临额.sql 里 data_date 有 +0 和 +1 两种写法并存）
  --      所以 data_date 只能用来**定位批次**，不能用来算账龄或判有效期。
  --
  --   改法：用 yuhan 定位批次（它才有 temp_limit_tag 的分组信息），
  --         用台账 C015/C013 的 create_time 作时间锚点和账龄基准。
  --         MAX_BY 的排序键一并从 data_date 换成 g.create_time —— 否则窗口内同时存在
  --         合法早期批次和放款后批次时，会用放款后那批的金额/标签覆盖真正有效的那批。
  --
  --   ★ 实测效果（v9 → v10，全量 67,980 笔）：
  --       holds_offline            13,620 → 11,904（剔掉 1,942 笔误判，1,873 笔放款早于 21:00）
  --       SUM(avail_future_logic)  1.9886 亿 → 1.9615 亿（−271 万，正是虚高那部分）
  --       批次口径≠账户口径笔数     1,885 → **274（−85%）** ← 改对了的最强证据：
  --         时刻级对齐后 yuhan 批次额与台账账户额度基本一致；
  --         v9 那 1,885 笔不符，主要是**匹配到了放款之后的那一批**。
  --       离线使用额               422.42 万 → 422.58 万（+0.04%）
  --         被剔掉的 1,942 笔里只有 1 笔曾判为用了离线临额（200 元）
  --         → **业绩贡献口径几乎不受影响，修正的纯粹是"可用额度"**。
  --   ★ 五笔标杆复核（见文件末尾）全部符合预期，含 v8 注释预言的
  --     biz 1620000464246378 → offline_available=5,650、avail_future=24,583.34。
  -- ══════════════════════════════════════════════════════════════════
  SELECT b.biz_id,
         MAX_BY(CAST(y.temp_limit_issue_amount AS DOUBLE), g.create_time) AS offline_grant_amount,
         MAX_BY(y.temp_limit_tag,                          g.create_time) AS offline_grant_tag,
         MAX_BY(y.data_date,                               g.create_time) AS offline_grant_date,
         -- 【v10 新增】台账口径的真实发放时刻 → 账龄与有效期都以它为准
         MAX(g.create_time)                                               AS offline_grant_time
  FROM mx.yj_quota_base b
  LEFT JOIN limit_frz lf ON lf.biz_v = CAST(b.biz_id AS VARCHAR)
  LEFT JOIN biz_apply ap ON ap.biz_v = CAST(b.biz_id AS VARCHAR)
  JOIN mx.yuhan_temp_limit_base_table_his_20260924 y
    ON  CAST(y.mid AS VARCHAR) = CAST(b.mid AS VARCHAR)
   AND  y.temp_limit_issue_amount IS NOT NULL
   AND  CAST(y.temp_limit_issue_amount AS DOUBLE) > 0
   AND  y.temp_limit_tag LIKE '%临额%'                                 -- 【改动B】
   AND  y.temp_limit_tag NOT LIKE '%对照组%'                           -- 【改动B】
   AND  DATE_DIFF('day', CAST(date_parse(y.data_date, '%Y%m%d') AS DATE),
                  b.issue_date) BETWEEN -2 AND 5                       -- 粗筛，放宽一天兜住 +0/+1 两种约定
  -- ★ 把 yuhan 批次与台账发放事件对齐：事件日期落在 data_date 的前两天到当天
  --   （覆盖 +0/+1/+2 三种偏移），金额不参与匹配（批次表金额与台账 13.9% 不等，见 OBS07）
  JOIN ods_view_presto.s05_user_creditlimit_change_record g
    ON  CAST(g.mid AS VARCHAR) = CAST(y.mid AS VARCHAR)
   AND  g.limit_type    = 'TEMP'
   AND  g.change_action = 'CHANGE_LIMIT'
   AND  g.change_event_type IN ('C013','C015')                         -- 离线发放事件
   AND  CAST(g.change_total_grantamount AS DOUBLE) > 0
   AND  g.create_time >= TIMESTAMP '2026-08-25 00:00:00'
   AND  CAST(g.create_time AS DATE)
          BETWEEN DATE_ADD('day', -2, CAST(date_parse(y.data_date,'%Y%m%d') AS DATE))
              AND CAST(date_parse(y.data_date,'%Y%m%d') AS DATE)
   -- ★★ 时刻级锚点：发放必须早于本笔用信决策，与 limit_state / limit_last_grant 一致
   --   【v11 修正】锚点三级：TEMP 冻结时刻 > funnel.apply_time（用信确认时刻）> release_time
   --   实测 limit_freeze_time 只覆盖 20.5%，apply_time 覆盖 100% 且与冻结时刻差 24~33 毫秒
   AND  g.create_time <= COALESCE(lf.limit_freeze_time, ap.apply_time, b.release_time)
   -- ★★【v11 修正】有效期 5 天必须按**时刻**判，不能只按自然日
   --   v10 只写了下面那条 DATE_DIFF('day', ...) BETWEEN 0 AND 5，等价于「第 5 个自然日
   --   整日都有效」，比真实的 120 小时最多宽出一天。实测 age=5 的 1,815 行里有 305 行
   --   落在边界上，按新的三级锚点判：290 行确实已过期、15 行在点击时仍有效（v11 保留）。
   --   （仅用 release_time 兜底会把那 15 行误杀 → 见 a11_rescued_by_apply_time。）
   AND  g.create_time + INTERVAL '5' DAY >= COALESCE(lf.limit_freeze_time, ap.apply_time, b.release_time)
   -- 日粒度窗口保留：只作窗口粗筛（覆盖 +0/+1/+2 三种 data_date 偏移），不承担有效期口径
   AND  DATE_DIFF('day', CAST(g.create_time AS DATE), b.issue_date) BETWEEN 0 AND 5
  GROUP BY 1
),
limit_last_grant AS (
  -- 【v8 ★ 关键修正】「**用信决策之前**」账户上最后一次发放事件
  --   v7 的窗口是 create_time <= 本笔冻结时刻，**把本笔自己的 C010 也算了进去** ——
  --   于是「用信过程中发生的事」污染了「用信前的状态」，离线被误判成已失效。
  --   ⚠️ 因果搞反了：C010 覆盖是「客户选了在线」的**结果**，不是「离线本来就没了」的原因。
  --   反例 biz 1620000464246378（岳松指出）：
  --     09-09 02:00  C015  total → 5,650          ← 用信前，离线可用 5,650
  --     09-11 11:42:05.959  C010  5,650 → 4,000   ← 用信中，客户被弹窗发了在线
  --     09-11 11:42:05.967  C003  冻结 4,000
  --   客户在用信前确实持有 5,650 离线可用，只是**没选它**。没用 ≠ 不可用。
  --   → 修法：排除本笔自己触发的事件（external_id = 本笔 biz_id）。
  --     注意 C015/C013 的 external_id 是 'mid_时间戳' 格式、不是 biz_id，
  --     所以这个排除只会剔掉本笔的 C010/C003/C004，不会误剔离线批次事件。
  SELECT b.biz_id,
         MAX_BY(g.change_event_type, g.create_time)                        AS last_grant_type,
         MAX_BY(CAST(g.change_total_grantamount AS DOUBLE), g.create_time) AS last_grant_total,
         MAX(g.create_time)                                                AS last_grant_time
  FROM mx.yj_quota_base b
  LEFT JOIN limit_frz lf ON lf.biz_v = CAST(b.biz_id AS VARCHAR)
  LEFT JOIN biz_apply ap ON ap.biz_v = CAST(b.biz_id AS VARCHAR)
  JOIN ods_view_presto.s05_user_creditlimit_change_record g
    ON  g.mid = b.mid
   AND  g.limit_type    = 'TEMP'
   AND  g.change_action = 'CHANGE_LIMIT'
   AND  g.change_event_type IN ('C010','C013','C015')
   AND  CAST(g.change_total_grantamount AS DOUBLE) > 0
   AND  COALESCE(CAST(g.external_id AS VARCHAR),'') <> CAST(b.biz_id AS VARCHAR)  -- 【v8】排除本笔
   AND  g.create_time <= COALESCE(lf.limit_freeze_time, ap.apply_time, b.release_time)  -- 【v11】三级锚点
   AND  g.create_time >= TIMESTAMP '2026-06-01 00:00:00'
  GROUP BY 1
),
limit_state AS (
  -- 【v8】账户在「**用信决策之前**」的状态（总额度 + 已被其他在贷笔占用）
  --   同样排除本笔自己的事件，口径与 limit_last_grant 对齐。
  --   ★ 为什么需要它：没动用临额的笔没有 TEMP 冻结行，limit_frz 取不到，
  --     但这些人账户里可能正躺着有效的离线额度（v6 实测 6,942 笔 / 持有 1,273.5 万被填成 0）。
  SELECT b.biz_id,
         MAX_BY(CAST(e.change_total_grantamount AS DOUBLE), e.create_time) AS state_total,
         MAX_BY(CAST(e.change_used_grantamount  AS DOUBLE), e.create_time) AS state_used
  FROM mx.yj_quota_base b
  LEFT JOIN limit_frz lf ON lf.biz_v = CAST(b.biz_id AS VARCHAR)
  LEFT JOIN biz_apply ap ON ap.biz_v = CAST(b.biz_id AS VARCHAR)
  JOIN ods_view_presto.s05_user_creditlimit_change_record e
    ON  e.mid = b.mid
   AND  e.limit_type = 'TEMP'
   AND  COALESCE(CAST(e.external_id AS VARCHAR),'') <> CAST(b.biz_id AS VARCHAR)  -- 【v8】排除本笔
   AND  e.create_time <= COALESCE(lf.limit_freeze_time, ap.apply_time, b.release_time)  -- 【v11】三级锚点
   AND  e.create_time >= TIMESTAMP '2026-06-01 00:00:00'
  GROUP BY 1
),
main_frz AS (
  -- 主额冻结台账：本笔主额支用 = change_used − old_used（取最接近 release_time 的那条）
  SELECT biz_id, main_used_this FROM (
    SELECT b.biz_id,
           CAST(c.change_used_grantamount AS DOUBLE)
             - CAST(COALESCE(c.old_used_grantamount, 0) AS DOUBLE) AS main_used_this,
           ROW_NUMBER() OVER (PARTITION BY b.biz_id
             ORDER BY ABS(DATE_DIFF('second', c.create_time, b.release_time))) AS rn
    FROM mx.yj_quota_base b
    JOIN ods_view_presto.s05_user_creditlimit_change_record c
      ON  CAST(c.external_id AS VARCHAR) = CAST(b.biz_id AS VARCHAR)
     AND  c.limit_type = 'MAIN' AND c.change_action = 'FREEZE_LIMIT'
     AND  c.create_time >= TIMESTAMP '2026-08-25 00:00:00'
  ) t WHERE rn = 1
),
main_used_detail AS (
  SELECT CAST(biz_id AS BIGINT) AS biz_id,
         MAX(TRY_CAST(risk_credit_limit AS DOUBLE)) AS main_used_this
  FROM ods_view_presto.s05_user_creditlimit_used_detail
  WHERE limit_type = 'MAIN' AND change_action = 'FREEZE_LIMIT' AND biz_id IS NOT NULL
    AND create_time >= TIMESTAMP '2026-08-25 00:00:00'
  GROUP BY 1
),
vch AS (
  -- 额度立减券：用信确认页核销、直接抵减合同额。只取 MAIN+FREEZE（TEMP 行与解冻行恒为 0）
  SELECT CAST(biz_id AS BIGINT)             AS biz_id,
         SUM(CAST(voucher_limit AS DOUBLE)) AS voucher_limit,
         MAX(CAST(voucher_id AS VARCHAR))   AS voucher_id
  FROM ods_view_presto.s05_user_creditlimit_used_detail
  WHERE limit_type = 'MAIN' AND change_action = 'FREEZE_LIMIT' AND biz_id IS NOT NULL
    AND CAST(voucher_limit AS DOUBLE) > 0
    AND create_time >= TIMESTAMP '2026-08-25 00:00:00'
  GROUP BY 1
),
product_cap AS (
  -- 【v11 改动】产品上限不再写死在 CASE 里，改为「生效区间表」：一行一个区间，未命中回落 10,000
  --   现状只有一条：2026-10-19 起 D_1_03 的 15,000 测试配置。
  --   ⚠️ 新增/回滚测试：直接改下面的日期或再加一行 UNION ALL，不要动计算逻辑。
  --   ⚠️ 产品上限只影响 avail_current_logic（页面可见可用额度），不参与放款钳制。
  SELECT 'D_1_03'        AS product_level,
         DATE '2026-10-19' AS start_date,
         DATE '2099-12-31' AS end_date,
         CAST(15000.0 AS DOUBLE) AS cap_amount
),
on_occ_led AS (
  -- 【v11.1 ★】TEMP 台账残差（按 biz）：这笔订单的在线临额「当前真实占用」= Σ冻结 − Σ解冻。
  --   占用的正确口径是台账残差，不是支用额：实测 frz 与 used_this 100% 相等（0 例外），
  --   但 2,701 笔在贷笔在还款中已发生部分/全额解冻（UNFREEZE）→ 残差 < 支用额。
  --   窗口下界 2026-08-25：早于本表 issue_date 下界（09-01）6 天，覆盖全部跨天/晚批冻结，
  --   同时满足大表 create_time 分区裁剪要求。
  --   ⚠️ 本列对离线来源笔也可能非 0（离线使用同样记 TEMP 台账），故只对在线行取用。
  SELECT CAST(biz_id AS BIGINT) AS biz_id,
         SUM(CASE WHEN change_action = 'FREEZE_LIMIT'   THEN CAST(risk_credit_limit AS DOUBLE) ELSE 0 END)
       - SUM(CASE WHEN change_action = 'UNFREEZE_LIMIT' THEN CAST(risk_credit_limit AS DOUBLE) ELSE 0 END)
                                                                        AS temp_resid
  FROM ods.s05_user_creditlimit_used_detail
  WHERE limit_type = 'TEMP' AND biz_id IS NOT NULL
    AND create_time >= TIMESTAMP '2026-08-25 00:00:00'
  GROUP BY 1
),
on_st AS (
  -- 【v11.1 ★】结清判定：state<>1 记为未还（岳松口径 MAX(state<>1)=0 才算结清）。
  --   无还款记录的 biz 默认**在贷**（COALESCE(any_unpaid,1)），不是结清。
  --   IN 半连接先裁剪到本表 biz，避免还款大表全量 GROUP BY。
  SELECT CAST(camera_id AS BIGINT) AS biz_id,
         MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END) AS any_unpaid
  FROM ods_view_presto.s02_loan_repayment
  WHERE camera_id IS NOT NULL
    AND CAST(camera_id AS BIGINT) IN (SELECT CAST(biz_id AS BIGINT) FROM mx.yj_quota_base)
  GROUP BY 1
),
c010 AS (
  -- 【v11.1 ★】本笔 C010 发放事件：在线「历史已占用」的唯一真值来源
  --   change_total_grantamount = 名义发放额（实测与 857 弹窗额 8,160/8,160 全中，仅作校验）
  --   change_used_grantamount  = 发放**前**该 TEMP 账户的存量占用（历史已占用）
  --   三段式（2026-10-26 全量验证，17,326 笔持在线 / 8,160 笔有 C010）：
  --     名义额 = 存量占用 + 实到账；支用 ≤ 实到账（0 笔违反）；支用 = 实到账（一次性用完，8,160 全中）
  --   存量占用真实存在：150 笔 / 53,783.8 比索（发放额被账户既有占用抵扣）
  --   external_id = biz_id；无 C010 的笔 = 弹窗未领取（used_before 取 0）
  -- 【v11.2】加 grant_ts：发放时刻，供 on_src_split 取「发放时刻之前」的台账残差
  SELECT CAST(c.external_id AS BIGINT) AS biz_id,
         MAX_BY(CAST(c.change_total_grantamount AS DOUBLE), c.create_time) AS c010_total,
         MAX_BY(CAST(c.change_used_grantamount  AS DOUBLE), c.create_time) AS c010_used_before,
         MAX(c.create_time)                                                AS grant_ts
  FROM ods_view_presto.s05_user_creditlimit_change_record c
  WHERE c.limit_type = 'TEMP' AND c.change_event_type = 'C010'
    AND c.external_id IS NOT NULL
    AND c.create_time >= TIMESTAMP '2026-08-25 00:00:00'
  GROUP BY 1
),
on_src_split AS (
  -- 【v11.2 ★★】online_used_amount（历史存量占用）按【来源笔当前结清状态】拆分
  --   岳松框架：名义发放 4000 = 历史存量占用 1000 + 实到账可用 3000
  --     其中历史存量占用 1000 理论上是历史笔未结清在贷占用，但可能含已结清残留（2-3 月 bug 尾巴）
  --   拆分维度：发放时刻（c010.grant_ts）之前，同 mid 下所有非本笔（ledger_biz ≠ 本笔）的
  --     TEMP 台账残差（ΣFREEZE − ΣUNFREEZE），按来源笔当前是否结清分两组：
  --       来源笔当前未结清 → online_used_inloan_amount（真"在贷占用"）
  --       来源笔当前已结清 → online_used_noloan_amount（已结清但台账未释放 = 残留）
  --   闭合断言 a12_on_used_split_identity：used_amount = inloan + noloan，期望 0
  --   实测（17,326 笔持在线 / 150 笔 used_amount>0）：
  --     53,783.75 = 14,614.48（45 笔在贷）+ 39,169.27（106 笔残留），差额 0.0
  --   ⚠️ TEMP 台账 biz_id 是来源笔（造成占用的历史笔），mid 是账户 → 必须用 mid join
  --   ⚠️ 窗口下界 2026-01-01 覆盖 2-3 月残留 bug 期（project_memory L38）
  SELECT led.cur_biz,
         SUM(CASE WHEN COALESCE(s.any_unpaid, 1) = 1 THEN led.src_resid ELSE 0 END) AS online_used_inloan_v2,
         SUM(CASE WHEN COALESCE(s.any_unpaid, 1) = 0 THEN led.src_resid ELSE 0 END) AS online_used_noloan_v2
  FROM (
    SELECT CAST(b.biz_id AS BIGINT) AS cur_biz,
           CAST(d.biz_id AS BIGINT) AS src_biz,
           SUM(CASE WHEN d.change_action = 'FREEZE_LIMIT'   THEN CAST(d.risk_credit_limit AS DOUBLE) ELSE 0 END)
         - SUM(CASE WHEN d.change_action = 'UNFREEZE_LIMIT' THEN CAST(d.risk_credit_limit AS DOUBLE) ELSE 0 END) AS src_resid
    FROM mx.yj_quota_base b
    JOIN c010 t ON t.biz_id = CAST(b.biz_id AS BIGINT)
    JOIN ods.s05_user_creditlimit_used_detail d
      ON d.mid = b.mid AND d.limit_type = 'TEMP'
     AND d.create_time <  t.grant_ts                       -- 发放时刻之前（历史存量）
     AND d.create_time >= TIMESTAMP '2026-01-01 00:00:00'  -- 覆盖 2-3 月残留 bug
     AND CAST(d.biz_id AS BIGINT) <> CAST(b.biz_id AS BIGINT)  -- 排除本笔，只看历史来源
    GROUP BY 1, 2
    HAVING SUM(CASE WHEN d.change_action = 'FREEZE_LIMIT'   THEN CAST(d.risk_credit_limit AS DOUBLE) ELSE 0 END)
         - SUM(CASE WHEN d.change_action = 'UNFREEZE_LIMIT' THEN CAST(d.risk_credit_limit AS DOUBLE) ELSE 0 END) > 0.01
  ) led
  LEFT JOIN (
    -- 来源笔当前结清状态（与 on_st 同口径：无还款记录默认在贷）
    SELECT CAST(camera_id AS BIGINT) AS src_biz,
           MAX(CASE WHEN state <> 1 THEN 1 ELSE 0 END) AS any_unpaid
    FROM ods_view_presto.s02_loan_repayment
    WHERE camera_id IS NOT NULL
    GROUP BY 1
  ) s ON s.src_biz = led.src_biz
  GROUP BY led.cur_biz
),
calc AS (
  SELECT
    b.biz_id, b.mid, b.issue_date, b.release_time, b.product_level, b.contract_amount,
    b.android_oldcust_maincreditlevel_charge_v6_1,
    b.temp_used,
    -- 【v11 新增】用信确认时刻（funnel.apply_time），有效期/冻结锚点的次选来源
    ap.apply_time,

    -- 主额（口径未改）
    b.credit_amount,
    b.change_used_grantamount,
    b.credit_amount - b.change_used_grantamount                        AS main_available_amount,
    CASE
      WHEN b.daily_max_available_limit IS NULL
        THEN COALESCE(s.daily_max_available_limit, b.daily_max_available_limit)
      WHEN b.daily_max_available_limit
           < COALESCE(b.risk_credit_limit, b.contract_amount - b.temp_used)
        THEN GREATEST(COALESCE(s.daily_max_available_limit, b.daily_max_available_limit),
                      b.daily_max_available_limit)
      ELSE b.daily_max_available_limit
    END                                                                AS daily_max_available_limit,
    b.risk_credit_limit,
    -- 【改动5】兜底补扣 voucher_limit
    COALESCE(mf.main_used_this, mud.main_used_this, b.risk_credit_limit,
             b.contract_amount - COALESCE(b.temp_used,0)
               - COALESCE(v.voucher_limit,0))                          AS main_used_this,

    -- 临额账户
    lf.limit_main_id,
    lf.limit_freeze_time,
    -- 本笔冻结行的口径（诊断用，含本笔自己的 C010 影响）
    COALESCE(lf.limit_total_amount, 0)                                 AS limit_total_amount,
    -- 【v8 ★】账户总额度/已占用改用「**用信决策之前**」的状态（ls 已排除本笔事件）
    --   这才是「这笔资产在用信时能动用多少临额」的正确锚点。
    --   v7 用本笔冻结行(lf)，但冻结发生在本笔 C010 覆盖之后 → 离线可用被抹成 0。
    COALESCE(ls.state_total, 0)                                        AS pre_total_amount,
    COALESCE(ls.state_used,  0)                                        AS used_before,
    GREATEST(COALESCE(ls.state_total,0) - COALESCE(ls.state_used,0), 0) AS acct_available,
    COALESCE(ls.state_total,0) - COALESCE(ls.state_used,0)             AS available_amount_check,
    COALESCE(b.temp_used,0)
      - GREATEST(COALESCE(lf.used_after,0) - COALESCE(lf.used_before,0), 0)
                                                                       AS used_this_check,
    -- 【v7】账户里的额度此刻属于谁：C010 = 在线已把离线覆盖掉；C013/C015 = 离线仍有效
    llg.last_grant_type,

    -- 离线临额发放侧
    og.offline_grant_amount,
    og.offline_grant_tag,
    og.offline_grant_date,
    og.offline_grant_time,
    -- 【v10 ★】账龄改用台账真实发放时刻，不再用 data_date
    --   v9 用 data_date 算 → 因 data_date 相对实际发放日有 +0/+1/+2 三种偏移（见 og CTE 注释），
    --   85% 的笔偏小整 1 天、15% 不偏，取值域被压到 [-1,4]，
    --   于是列说明「> 5 即超期」的阈值永不可达、a4_offline_overage 恒为 0，
    --   且与 yj_temp_limit_wide_table_v3 的 offline_age_days（时刻口径）整体错位一天。
    --   现在取值域是 [0,5]：0 = 当天发当天用，5 = 到期当日。
    --   【v11】有效期已在 og CTE 内按时刻（+5 天）裁剪，故本列取到 5 时，
    --     该批次在用信时刻「一定仍在有效期内」（v10 会混进已过期但同自然日的行）。
    --   本列仍是**自然日**口径，保证与 yj_temp_limit_wide_table_v3 的 offline_age_days 可比。
    CASE WHEN og.offline_grant_time IS NULL THEN NULL
         ELSE DATE_DIFF('day', CAST(og.offline_grant_time AS DATE), b.issue_date)
    END                                                                AS offline_grant_age_days,
    -- 【v10 新增】剩余有效期，与 v3 宽表的 offline_expire_days 同口径（5 − 账龄）
    CASE WHEN og.offline_grant_time IS NULL THEN NULL
         ELSE 5 - DATE_DIFF('day', CAST(og.offline_grant_time AS DATE), b.issue_date)
    END                                                                AS offline_expire_days,
    -- 批次标签格式实测 'MMDD临额测试组_有在贷_N' / '..._无在贷' / 'MMDD减息测试组_无在贷'
    -- 所有 tag 必含「有在贷」或「无在贷」，故 ELSE 分支安全
    CASE WHEN COALESCE(og.offline_grant_tag,'') = ''        THEN NULL
         WHEN STRPOS(og.offline_grant_tag, '有在贷') > 0    THEN '有在贷'
         ELSE '无在贷' END                                              AS has_outstanding_tag,
    -- ⚠️ 这列区分的是【临额实验组 vs 减息对照组】，不是「有没有临额」
    CASE WHEN COALESCE(og.offline_grant_tag,'') = ''        THEN NULL
         WHEN STRPOS(og.offline_grant_tag, '临额') > 0      THEN '临额'
         ELSE '无临额' END                                              AS has_temp_tag,
    -- 档位后缀 _1/_2/_3 = 10%/20%/30%（无后缀早期批次按 20%，_无在贷≈30%）
    -- ⚠️ LIKE 里的下划线是通配符，必须加 ESCAPE
    CASE WHEN COALESCE(og.offline_grant_tag,'') = ''              THEN NULL
         WHEN og.offline_grant_tag LIKE '%\_1' ESCAPE '\'         THEN '10%'
         WHEN og.offline_grant_tag LIKE '%\_2' ESCAPE '\'         THEN '20%'
         WHEN og.offline_grant_tag LIKE '%\_3' ESCAPE '\'         THEN '30%'
         WHEN STRPOS(og.offline_grant_tag, '无在贷') > 0          THEN '30%'
         ELSE '20%' END                                                 AS offline_grant_ratio_tag,

    -- 在线临额发放侧
    COALESCE(ofl.online_grant_flag, 0)                                 AS online_grant_flag,
    COALESCE(ong.online_grant_amount, 0)                               AS online_grant_amount,

    -- 【v7 新增 / v8 修正】★ 持有标志 —— 与「本笔用了什么」解耦
    --   持有 ≠ 使用：客户持有多少可用额度，和他这笔用不用它是两回事。
    --   ⚠️【v8】holds_offline 与 holds_online **不再互斥**：
    --     用信前持有离线 5,650、用信时又被弹窗发了在线 4,000 —— 两个都"持有"，
    --     互斥的只是最终"用了哪个"（看 used_source_tag）。
    --     v7 给 holds_offline 加了「账户额度没被 C010 覆盖」的条件，等于让本笔自己的
    --     在线弹窗把离线持有量抹掉，因果搞反了。
    --   离线持有 = 持有有效期内的离线批次（og 已按 5 天 + 真发放组过滤）
    CASE WHEN og.offline_grant_amount IS NOT NULL THEN 1 ELSE 0 END    AS holds_offline,
    --   在线持有 = 本笔弹窗发放了在线临额（1386 tag=1 且 857 弹窗额 > 0）
    CASE WHEN COALESCE(ofl.online_grant_flag,0) = 1
          AND COALESCE(ong.online_grant_amount,0) > 0
         THEN 1 ELSE 0 END                                             AS holds_online,

    -- 【改动2】来源归属：离线与在线互斥，判不出的落 unknown
    CASE WHEN COALESCE(b.temp_used,0) <= 0.05                          THEN 'none'
         WHEN COALESCE(ofl.online_grant_flag,0) = 1
          AND COALESCE(ong.online_grant_amount,0) > 0                  THEN 'online'
         WHEN og.offline_grant_amount IS NOT NULL                      THEN 'offline'
         ELSE 'unknown' END                                            AS used_source_tag,

    -- 【v11 改动】产品上限改由 product_cap 区间表决定（原为写死的 CASE，无失效日期）
    COALESCE(pc.cap_amount, 10000.0)                                   AS product_limit_max,
    COALESCE(v.voucher_limit, 0)                                       AS voucher_limit,
    v.voucher_id,
    -- 【v11.1】本笔 biz 的 TEMP 台账残差（当前真实占用）与结清标志；
    --   on_st 无记录默认在贷（无还款记录 ≠ 结清）
    COALESCE(ool.temp_resid, 0)                                        AS temp_resid,
    COALESCE(ost.any_unpaid, 1)                                        AS online_any_unpaid,
    -- 【v11.1】C010 发放前账户存量占用（在线「历史已占用」真值）；无 C010 = 未领取 → 0
    COALESCE(c10.c010_used_before, 0)                                  AS online_used_before,
    -- 【v11.2】历史存量占用按来源笔当前结清状态拆分（替换旧 inloan/noloan 错口径）
    COALESCE(osp.online_used_inloan_v2, 0)                             AS online_used_inloan_v2,
    COALESCE(osp.online_used_noloan_v2, 0)                             AS online_used_noloan_v2
  FROM mx.yj_quota_base b
  LEFT JOIN s1077            s   ON s.biz_id   = b.biz_id
  LEFT JOIN online_grant     ong ON ong.biz_id = b.biz_id
  LEFT JOIN online_flag      ofl ON ofl.biz_id = b.biz_id
  LEFT JOIN limit_frz        lf  ON lf.biz_v   = CAST(b.biz_id AS VARCHAR)
  LEFT JOIN biz_apply        ap  ON ap.biz_v   = CAST(b.biz_id AS VARCHAR)
  LEFT JOIN limit_last_grant llg ON llg.biz_id = b.biz_id
  LEFT JOIN limit_state      ls  ON ls.biz_id  = b.biz_id
  LEFT JOIN offline_grant    og  ON og.biz_id  = b.biz_id
  LEFT JOIN main_frz         mf  ON mf.biz_id  = b.biz_id
  LEFT JOIN main_used_detail mud ON mud.biz_id = b.biz_id
  LEFT JOIN vch              v   ON v.biz_id   = b.biz_id
  -- 【v11.1】在线临额占用拆分：TEMP 台账残差 + 结清判定 + C010 发放事件
  LEFT JOIN on_occ_led       ool ON ool.biz_id = b.biz_id
  LEFT JOIN on_st            ost ON ost.biz_id = b.biz_id
  LEFT JOIN c010             c10 ON c10.biz_id = b.biz_id
  -- 【v11.2】历史存量占用按来源笔当前结清状态拆分
  LEFT JOIN on_src_split     osp ON osp.cur_biz = b.biz_id
  LEFT JOIN product_cap      pc  ON pc.product_level = b.product_level
                               AND b.issue_date BETWEEN pc.start_date AND pc.end_date
)
SELECT
  -- ── [标识] ──
  biz_id, mid, issue_date, release_time, product_level, contract_amount,
  android_oldcust_maincreditlevel_charge_v6_1,

  -- ── [主额] ──
  credit_amount, change_used_grantamount, main_available_amount,
  daily_max_available_limit, risk_credit_limit, main_used_this,

  -- ── [离线临额] ──
  -- 【v7 ★】_used_amount / _available_amount 看「**持有**」(holds_offline)，
  --          _used_this 才看「**本笔用了谁**」(used_source_tag)。两者解耦。
  --   岳松口径：批次发 4,000、该客户其他在贷笔占着 2,000 → 可用 2,000、本笔最多只能用 2,000
  --   即 offline_available_amount = 账户总额度 − 其他笔已占用，对**所有持有者**都算，
  --   不是只对「本笔用了离线」的笔算（v6 的错）。
  -- ⚠️⚠️【v10 必读】offline_grant_amount **禁止跨笔直接 SUM**
  --   这是逐笔表，但离线临额是**账户级(mid)**事实：同一 mid 在 5 天有效期内放多笔，
  --   同一批额度会在每一行各记一次。实测 holds_offline=1 共 13,620 行，
  --   只对应 6,340 个 mid / 9,473 个 (mid,批次)，一个批次最多摊到 12 笔订单。
  --     SUM(offline_grant_amount)     逐行 1,941 万 vs 去重 1,207 万 → **虚增 60.8%**
  --     SUM(offline_available_amount) 逐行 1,729 万 vs 去重 1,195 万 → **虚增 44.7%**
  --   要算「总共发了多少离线临额」必须按 (mid, offline_grant_date) 去重：
  --     用下面的 offline_batch_seq = 1 过滤，或直接对 yuhan 批次表聚合。
  --   ✅ 可以直接 SUM 的是 *_used_this 三列（本笔支用，天然逐笔不重复）。
  ROW_NUMBER() OVER (PARTITION BY mid, COALESCE(offline_grant_date,'-')
                     ORDER BY release_time, biz_id)                    AS offline_batch_seq,
  offline_grant_amount, offline_grant_tag, offline_grant_date,
  offline_grant_time, offline_grant_age_days, offline_expire_days,
  offline_grant_ratio_tag, has_outstanding_tag, has_temp_tag,
  holds_offline,
  -- 【v10 ★★ 硬恒等式】offline_grant_amount − offline_used_amount − offline_available_amount = 0
  --   岳松口径：批次发 4,000、该客户其他在贷笔占着 2,000 → 可用 2,000、本笔最多只能用 2,000
  --
  --   available = LEAST(批次发放额, acct_available)
  --     · 离线临额在用信**前**就已进账户 → pre_total_amount 含它 → 账户占用要扣
  --     · cap 在批次发放额内 → 不会出现 available > grant（岳松质疑过 v5 的这个现象）
  --     · acct_available 已是 GREATEST(pre_total − used_before, 0) → available ∈ [0, 批次发放额]
  --   used_amount = 批次发放额 − available
  --     语义：「本批发放额中被其他在贷笔吃掉的部分」，非负，恒等式恒成立
  --
  --   ⚠️ v9 错在这：available = 批次额 − used_before，拿**账户级总占用**直接减批次额，
  --      且在线侧减同一个 used_before（扣两遍）。恒等式照样成立（_used_amount 也填 used_before），
  --      但造出 48 笔负的离线可用、124 笔负的在线可用。顺序必须是先 cap 再相减。
  --   ⚠️ _used_amount 一律写成 grant − available（而不是各自独立算），恒等式才是**结构性**成立：
  --      grant − (grant − avail) − avail ≡ 0，与 holds 取值、grant 是否 NULL 都无关。
  --      v9 两列各算一遍，只是**经验上**凑成 0（依赖 holds=0 ⟹ grant IS NULL），很脆。
  COALESCE(offline_grant_amount,0)
    - CASE WHEN holds_offline = 1
           THEN LEAST(COALESCE(offline_grant_amount,0), acct_available)
           ELSE 0 END                                                  AS offline_used_amount,
  CASE WHEN holds_offline = 1
       THEN LEAST(COALESCE(offline_grant_amount,0), acct_available)
       ELSE 0 END                                                      AS offline_available_amount,
  CASE WHEN used_source_tag = 'offline' THEN temp_used ELSE 0 END      AS offline_used_this,

  -- ── [在线临额] ──
  -- 【v11.1 ★★ 三段式口径】对齐离线侧结构，2026-10-26 全量验证（17,326 笔持在线）：
  --     online_grant_amount      = 857 弹窗名义发放额
  --     online_used_amount       = C010 change_used_grantamount（发放**前**账户存量占用，
  --                                即「历史已占用」；实测 150 笔 >0 / 合计 53,783.8）
  --     online_available_amount  = 名义额 − 存量占用（= 实到账可用额，本笔最多能用这么多）
  --     online_used_this         = 本笔实际支用（≤ available，0 笔违反；且实测全部 = 实到账，
  --                                印证「领取后一次性用完」）
  --   恒等式 grant − used_amount − available ≡ 0 结构性成立（与离线侧同一结构）。
  --   无 C010 的笔（9,166 笔弹窗未领取）：used_amount=0、available=grant、used_this=0。
  --   ⚠️ 校验事实：C010 名义额与 857 弹窗额 8,160/8,160 全中 → used_amount 用 C010 口径
  --      不会与 grant(857) 口径错位。
  -- 【v10 背景】C010 是**整体替换**账户总额度（实测 7,648 笔 new_total 100% = 857 弹窗额，
  --   其中 1,719 笔是调低），所以弹窗时离线额度已被抹掉 → offline_available 必为 0。
  --   反例 biz 1620000464246378：C015 发 5,650 → C010 覆盖成 4,000，
  --   用信那一刻客户只剩「用不用这 4,000 在线」这一个选择。
  online_grant_flag, online_grant_amount, holds_online,
  online_used_before                                                 AS online_used_amount,
  COALESCE(online_grant_amount,0) - online_used_before               AS online_available_amount,
  CASE WHEN used_source_tag = 'online'  THEN temp_used ELSE 0 END      AS online_used_this,
  -- 【v11.2 ★★】历史存量占用按来源笔当前结清状态拆分（替换 v11.1 错口径）：
  --   旧错口径：把 temp_resid（本笔台账残差）按本笔 online_any_unpaid 拆 → 加总 ≠ used_amount
  --   新口径：on_src_split 按「发放时刻之前、来源笔 ≠ 本笔」的 TEMP 台账残差，
  --           再按来源笔当前是否结清分两组，加总 ≡ used_amount（断言 a12 校验）
  --   实测：53,783.75 = 14,614.48（45 笔在贷）+ 39,169.27（106 笔残留），差额 0.0
  online_used_inloan_v2                                                AS online_used_inloan_amount,
  online_used_noloan_v2                                                AS online_used_noloan_amount,

  -- ── [来源与兜底] ──
  used_source_tag,
  CASE WHEN used_source_tag = 'unknown' THEN temp_used ELSE 0 END      AS unknown_used_this,

  -- ── [产品上限与三套可用额度口径] ──
  -- ★★ 分组恒为「主额 + **离线**临额」，**不含在线临额**（沿用原版定义）
  -- 【v6 改动C】修回归：v5 误用了池级 limit_total_amount，把在线临额也算了进来
  --   —— 实测污染 7,650 笔（全部 online 来源笔）/ 373.3 万。
  --   反例 biz 1620000473712741：主额可用 18,350、日帽 10,000、离线可用 0、在线用 4,000
  --     v5 错： avail_tochange = LEAST(18350,10000) + 4000 = 14,000   ← 4,000 是在线的，不该进
  --             avail_future   = 18350 + 4000 = 22,350
  --     v6 对： avail_tochange = LEAST(18350,10000) + 0 = 10,000
  --             avail_future   = 18350 + 0 = 18,350
  --   为什么在线不该进：这三个口径是用来测算「放开产品上限 / 单日上限能多放多少」，
  --   而在线临额是**池外叠加、不受这两个上限约束**的，放进来会把反事实算高。
  -- ⚠️ 单日可借上限**只压主额**，离线临额叠加在日帽之上（故 LEAST 套在内层）
  -- 【v7 改动】临额部分从「本笔用了离线」改为「**持有**可用离线额度」(holds_offline)，
  --   否则「没用临额但账户里躺着有效离线额度」的 6,942 笔 / 1,273.5 万会被漏算，
  --   放开上限的反事实测算会系统性偏低。
  -- 【v10】临额部分与 offline_available_amount **完全同源**，表达式逐字一致。
  --   v9 这里重算了一遍 GREATEST(grant − used_before, 0)，与 offline_available_amount 列
  --   （= grant − used_before，不夹 0）不是同一个值 → 负可用的 48 笔在列里是负、在 avail 里是 0，
  --   两处口径悄悄分叉。v10 的 LEAST(grant, GREATEST(acct,0)) 本身已非负且 ≤ grant，
  --   不需要再夹一层，列与 avail 三口径永远一致。
  product_limit_max,
  LEAST(LEAST(main_available_amount, daily_max_available_limit)
        + CASE WHEN holds_offline = 1
               THEN LEAST(COALESCE(offline_grant_amount,0), acct_available)
               ELSE 0 END,
        product_limit_max)                                             AS avail_current_logic,
  LEAST(main_available_amount, daily_max_available_limit)
        + CASE WHEN holds_offline = 1
               THEN LEAST(COALESCE(offline_grant_amount,0), acct_available)
               ELSE 0 END                                              AS avail_tochange_logic,
  main_available_amount
        + CASE WHEN holds_offline = 1
               THEN LEAST(COALESCE(offline_grant_amount,0), acct_available)
               ELSE 0 END                                              AS avail_future_logic,

  -- ── [优惠券] contract_amount = main_used_this + 本笔临额使用额 + voucher_limit ──
  voucher_limit, voucher_id,

  -- ── [诊断列] 不参与业务计算 ──
  limit_main_id,
  limit_freeze_time,
  -- 【v11 新增】用信确认时刻：本笔有效期/冻结锚点的次选来源（limit_freeze_time 缺失时用它）
  apply_time,
  limit_total_amount,   -- 本笔冻结行的账户总额度（已含本笔 C010 的影响，诊断用）
  pre_total_amount,     -- 【v8】用信决策**之前**的账户总额度（已排除本笔事件）← 可用额度的基准
  used_before,          -- 用信前账户已被其他在贷笔占用的临额
  acct_available,       -- = pre_total_amount − used_before（用信前账户真实可用，不分来源）
  last_grant_type,      -- 用信前最后一次发放事件：C010 在线 / C013·C015 离线
  available_amount_check,
  used_this_check,
  -- 【v11.1】在线占用拆分的中间量（诊断用，业务列在 [在线临额] 块）
  temp_resid,           -- 本笔 biz 的 TEMP 台账残差 = Σ冻结 − Σ解冻（离线来源笔也可能非 0）
  online_any_unpaid,    -- 结清标志：1=有未还期次（在贷）/ 0=全部结清；无还款记录默认 1
  -- 【v6 新增】批次口径 vs 账户口径的差：
  --   offline_grant_amount 是 yuhan 批次口径（这一批发了多少），
  --   limit_total_amount   是台账账户口径（冻结时账户里实际有多少）。
  --   加了有效期后两者应高度一致；≠ 0 的笔说明批次落账与台账不符，需单独看。
  CASE WHEN used_source_tag = 'offline'
       THEN COALESCE(offline_grant_amount,0) - limit_total_amount END   AS grant_vs_limit_check
FROM calc
;


-- ══════════════════════════════════════════════════════════════════════
-- 第③段：建表后必跑的校验
-- ⚠️ 恒等式断言必须单列 isnull：SUM(CASE WHEN ABS(x-y)>t ...) 遇 NULL 计 0 = 静默放过
-- ══════════════════════════════════════════════════════════════════════
SELECT
  COUNT(1) AS n_rows, COUNT(DISTINCT biz_id) AS n_biz_uniq,

  -- ════════════════════════════════════════════════════════════════
  -- A0 ★★★ 临额三列硬恒等式（岳松 2026-10-23 强调：必须恒为 0，谨记）
  --     offline_grant_amount − offline_used_amount − offline_available_amount = 0
  --     online_grant_amount  − online_used_amount  − online_available_amount  = 0
  --   这两条是**任何改动后的第一道闸**。v8 曾有 1,897 笔不为 0，根因是
  --   available 取账户口径、grant 取批次口径，锚点不同。
  --   ⚠️ 必须单列 isnull：SUM(CASE WHEN ABS(x)>t ...) 遇 NULL 计 0 = 静默放过
  --   【v10】两列的 _used_amount 都已改写成 grant − available，恒等式**结构性**成立
  --   （grant − (grant−avail) − avail ≡ 0），这两条断言从此只能被"列算错/漏列"打破。
  --   【v11.1】在线侧恢复三段式：used_amount = C010 存量占用、available = grant − used_amount，
  --     恒等式仍结构性成立。
  -- ════════════════════════════════════════════════════════════════
  SUM(CASE WHEN offline_grant_amount IS NULL AND holds_offline = 1 THEN 1 ELSE 0 END)
                                                                                AS a0_off_grant_null,
  SUM(CASE WHEN offline_used_amount IS NULL OR offline_available_amount IS NULL
           THEN 1 ELSE 0 END)                                                   AS a0_off_null,
  SUM(CASE WHEN ABS(COALESCE(offline_grant_amount,0) - offline_used_amount
                    - offline_available_amount) > 0.05 THEN 1 ELSE 0 END)       AS a0_offline_identity,
  SUM(CASE WHEN online_used_amount IS NULL OR online_available_amount IS NULL
           THEN 1 ELSE 0 END)                                                   AS a0_on_null,
  SUM(CASE WHEN ABS(COALESCE(online_grant_amount,0) - online_used_amount
                    - online_available_amount) > 0.05 THEN 1 ELSE 0 END)        AS a0_online_identity,
  -- 可用额度为负的笔数
  -- 【v10】期望恒为 **0**：离线 available = LEAST(grant, acct_available) 已落在 [0, grant]，
  --   在线 available = 弹窗额。v9 这两项分别是 48 / 124，都是公式造出来的负数（见文件头）。
  --   未夹 0 的原始账户差值仍在诊断列 available_amount_check（a4_avail_negative，期望 15）。
  SUM(CASE WHEN offline_available_amount < -0.05 THEN 1 ELSE 0 END)             AS a0_off_avail_neg,
  SUM(CASE WHEN online_available_amount  < -0.05 THEN 1 ELSE 0 END)             AS a0_on_avail_neg,
  -- 【v10】可用不该超过发放额，期望恒为 0（离线被 LEAST 结构性夹住、在线恒等于发放额）
  SUM(CASE WHEN offline_available_amount > COALESCE(offline_grant_amount,0) + 0.05
           THEN 1 ELSE 0 END)                                                   AS a0_off_avail_gt_grant,
  SUM(CASE WHEN online_available_amount > COALESCE(online_grant_amount,0) + 0.05
           THEN 1 ELSE 0 END)                                                   AS a0_on_avail_gt_grant,

  -- A1 恒等式：合同额 = 主额支用 + 本笔临额使用 + 券（期望 0）
  SUM(CASE WHEN contract_amount IS NULL OR main_used_this IS NULL OR voucher_limit IS NULL
           THEN 1 ELSE 0 END)                                                   AS a1_null,
  SUM(CASE WHEN ABS(contract_amount - main_used_this
                    - (offline_used_this + online_used_this + unknown_used_this)
                    - voucher_limit) > 0.05 THEN 1 ELSE 0 END)                  AS a1_identity_break,

  -- A2 ★ 离线与在线互斥：两列同时 > 0 的笔数（期望 0）
  SUM(CASE WHEN offline_used_this > 0.05 AND online_used_this > 0.05
           THEN 1 ELSE 0 END)                                                   AS a2_both_used,
  -- ⚠️【v8】可用额度**允许**离线/在线同时 > 0（用信前持有离线 + 用信时又弹窗发在线），
  --    这列只作观察，不是违规项。互斥的只有 *_used_this。
  SUM(CASE WHEN offline_available_amount > 0.05 AND online_available_amount > 0.05
           THEN 1 ELSE 0 END)                                                   AS a2_both_avail_ok,

  -- A3 来源分布
  SUM(CASE WHEN used_source_tag = 'offline' THEN 1 ELSE 0 END)                  AS a3_offline_cnt,
  SUM(offline_used_this)                                                        AS a3_offline_amt,
  SUM(CASE WHEN used_source_tag = 'online'  THEN 1 ELSE 0 END)                  AS a3_online_cnt,
  SUM(online_used_this)                                                         AS a3_online_amt,
  SUM(CASE WHEN used_source_tag = 'unknown' THEN 1 ELSE 0 END)                  AS a3_unknown_cnt,
  SUM(unknown_used_this)                                                        AS a3_unknown_amt,

  -- A4 诊断
  SUM(CASE WHEN available_amount_check < -0.05 THEN 1 ELSE 0 END)               AS a4_avail_negative,
  SUM(CASE WHEN ABS(used_this_check) > 0.05 THEN 1 ELSE 0 END)                  AS a4_used_gap_cnt,
  -- ⚠️【v10】risk_credit_limit 为 NULL 时 ABS(NULL)>0.05 走 ELSE 0 → **静默通过**。
  --   实测 818 笔 NULL（台账落库延迟），正是 main_used_this 掉到最弱兜底的那批，
  --   恰恰最该校验却完全没查。必须单列 isnull（文件头第 660 行自己写的规则）。
  SUM(CASE WHEN risk_credit_limit IS NULL THEN 1 ELSE 0 END)                    AS a4_risk_null,
  SUM(CASE WHEN risk_credit_limit IS NOT NULL
            AND ABS(main_used_this - risk_credit_limit) > 0.05 THEN 1 ELSE 0 END) AS a4_main_vs_yj,
  -- 【v10】账龄改台账口径后，取值域应是 [0,5]，> 5 这个阈值才真正可达（v9 恒为 0）
  SUM(CASE WHEN offline_grant_age_days > 5 AND offline_used_this > 0
           THEN 1 ELSE 0 END)                                                   AS a4_offline_overage,
  -- 【v10】主额侧与 avail 三口径的 isnull 断言（v9 一条都没有，违反自己立的规则）
  --   实测 v9 这几列 NULL 全为 0，加上是防止将来兜底链断裂时静默丢行：
  --   Presto 的 LEAST 任一参数为 NULL 即返回 NULL，avail 三口径会整行消失，
  --   而 SUM() 跳过 NULL、ABS(NULL)>t 走 ELSE 0 → 既少算又不报警。
  SUM(CASE WHEN credit_amount IS NULL OR change_used_grantamount IS NULL
            OR main_available_amount IS NULL OR daily_max_available_limit IS NULL
           THEN 1 ELSE 0 END)                                                   AS a4_main_null,
  SUM(CASE WHEN avail_current_logic IS NULL OR avail_tochange_logic IS NULL
            OR avail_future_logic IS NULL THEN 1 ELSE 0 END)                    AS a4_avail_null,

  -- A5 ★【v6 改动A 验证】可用 > 发放 的笔数（期望 0）
  --   【v10】这条已被 a0_off_avail_gt_grant 全量覆盖且结构性保证，此处保留 offline 来源切片
  --   作回归对照（v5 曾在这里暴露过岳松质疑的 offline_available > offline_grant）。
  SUM(CASE WHEN used_source_tag = 'offline'
            AND offline_available_amount > COALESCE(offline_grant_amount,0) + 0.05
           THEN 1 ELSE 0 END)                                                   AS a5_avail_gt_grant,
  -- ⚠️【v10】grant_vs_limit_check 只在 used_source_tag='offline' 时非 NULL（见列定义），
  --   外面又套 COALESCE(...,0) → 其余行被当 0 静默放过。于是「持有离线但本笔没用」
  --   那批（avail 三口径的主要贡献者）对账零覆盖。保留原列作回归，另加全覆盖版本：
  SUM(CASE WHEN ABS(COALESCE(grant_vs_limit_check,0)) > 0.05 THEN 1 ELSE 0 END) AS a5_grant_ne_limit,
  --   全覆盖对账：锚点用 pre_total_amount 而非 limit_total_amount
  --   （后者是 COALESCE(lf.limit_total_amount,0)，无 TEMP 冻结行的持有笔恒为 0 → 全量假阳性）
  SUM(CASE WHEN holds_offline = 1 AND pre_total_amount IS NULL THEN 1 ELSE 0 END) AS a5_pretotal_null,
  SUM(CASE WHEN holds_offline = 1
            AND ABS(COALESCE(offline_grant_amount,0) - pre_total_amount) > 0.05
           THEN 1 ELSE 0 END)                                                   AS a5_grant_ne_pretotal,
  -- 离线可用不该超过账户真实可用（账户是唯一的池，期望恒 0）
  SUM(CASE WHEN holds_offline = 1
            AND offline_available_amount > acct_available + 0.05
           THEN 1 ELSE 0 END)                                                   AS a5_off_avail_gt_acct,

  -- A6 ★【v6 改动C 验证】三套可用额度不含在线
  --   ⚠️【v10 修正断言】v6 写的是「online 来源笔的 avail_future 应恒等于 main_available_amount」，
  --      这个前提在 v7 解耦 holds/used 之后就不成立了：一笔可以用信前持有离线、
  --      用信时又被弹窗发在线（实测 4,062 笔同时持有），此时 used_source_tag='online'
  --      但 avail_future 里的离线部分**本来就该非 0**。原断言会把正确数据判成污染。
  --   正确的判据是「avail 里不含在线」：限定 holds_offline = 0 时才要求等于主额可用。
  SUM(CASE WHEN used_source_tag = 'online' AND holds_offline = 0
            AND ABS(avail_future_logic - main_available_amount) > 0.05
           THEN 1 ELSE 0 END)                                                   AS a6_online_polluted,
  -- 等价的另一个角度：avail_future 减掉离线可用后，必须恰好是主额可用（期望恒 0）
  SUM(CASE WHEN ABS(avail_future_logic - main_available_amount
                    - offline_available_amount) > 0.05 THEN 1 ELSE 0 END)       AS a6_availf_decomp,
  SUM(avail_current_logic)                                                      AS a6_avail_cur_sum,
  SUM(avail_tochange_logic)                                                     AS a6_avail_chg_sum,
  SUM(avail_future_logic)                                                       AS a6_avail_fut_sum,

  -- A7 ★【v6 改动B 影响】离线批次全部落在有效期内、且全是真发放组
  -- ⚠️⚠️【v10 必读】下面 3 列是**构造恒真**，不是口径正确性的证据：
  --   这些谓词与 offline_grant CTE 的 JOIN 过滤条件完全重复
  --   （tag LIKE '%临额%' AND NOT LIKE '%对照组%'、账龄 BETWEEN 0 AND 5），
  --   而 MAX_BY/MAX 必定取自通过过滤的行 → 代数上永远返回 0。
  --   保留它们只作 regression guard（将来有人删掉 JOIN 里的过滤，这里会立刻报警），
  --   **不能**用「a7 全 0」来论证改动A/改动B 生效。真正的验证见下方 a7_raw_*。
  SUM(CASE WHEN offline_grant_tag IS NOT NULL
            AND offline_grant_tag NOT LIKE '%临额%' THEN 1 ELSE 0 END)          AS a7_bad_tag,
  SUM(CASE WHEN offline_grant_tag LIKE '%对照组%' THEN 1 ELSE 0 END)            AS a7_ctrl_tag,
  -- 【v10】账龄取值域随 og CTE 一起改成 [0,5]（v9 是 [-1,4]，且把坏边界 -1 固化成了"合法"）
  SUM(CASE WHEN offline_grant_amount IS NOT NULL
            AND (offline_grant_age_days < 0 OR offline_grant_age_days > 5)
           THEN 1 ELSE 0 END)                                                   AS a7_out_of_window,
  -- 【v10 新增】真正有信息量的版本：发放时刻必须早于用信决策（og 的时刻级锚点生效没有）
  SUM(CASE WHEN holds_offline = 1 AND offline_grant_time IS NULL
           THEN 1 ELSE 0 END)                                                   AS a7_grant_time_null,
  SUM(CASE WHEN offline_grant_time > COALESCE(limit_freeze_time, apply_time, release_time)
           THEN 1 ELSE 0 END)                                                   AS a7_grant_after_use,
  -- 剩余有效期应落在 [0,5]，且与账龄互补
  SUM(CASE WHEN offline_expire_days IS NOT NULL
            AND (offline_expire_days < 0 OR offline_expire_days > 5)
           THEN 1 ELSE 0 END)                                                   AS a7_expire_oob,

  -- ════════════════════════════════════════════════════════════════
  -- A11 ★【v11 新增】本次改动的回归断言
  -- ════════════════════════════════════════════════════════════════
  -- ① 时刻级有效期：持有但按时刻已过期（期望 **0**；v10 实测 305 行在 age=5 边界）
  --    锚点与 og CTE 完全一致：TEMP 冻结时刻 > funnel.apply_time > release_time
  SUM(CASE WHEN holds_offline = 1
            AND offline_grant_time + INTERVAL '5' DAY
                < COALESCE(limit_freeze_time, apply_time, release_time)
           THEN 1 ELSE 0 END)                                                   AS a11_expired_held,
  -- ①b 锚点修正的证据：limit_freeze_time 缺失（79.5% 的笔）时，若仍拿 release_time 兜底，
  --    会把这 15 笔「点击时仍在有效期、到账晚于到期」的持有笔误杀（期望 **15**）。
  --    只统计 age=5 的边界行，与上面 305 笔口径对齐。
  SUM(CASE WHEN holds_offline = 1
            AND limit_freeze_time IS NULL
            AND DATE_DIFF('day', CAST(offline_grant_time AS DATE), issue_date) = 5
            AND offline_grant_time + INTERVAL '5' DAY >= COALESCE(apply_time, release_time)
            AND offline_grant_time + INTERVAL '5' DAY <  release_time
           THEN 1 ELSE 0 END)                                                   AS a11_rescued_by_apply_time,
  -- ①c apply_time 覆盖率：持有离线的笔必须 100% 有值（funnel.apply_time 应全覆盖）
  SUM(CASE WHEN holds_offline = 1 AND apply_time IS NULL THEN 1 ELSE 0 END)        AS a11_apply_time_null,
  -- ② 产品上限区间表：命中 15,000 的笔数（期望 184，且必须全部满足 10-19 后 + D_1_03）
  SUM(CASE WHEN product_limit_max = 15000 THEN 1 ELSE 0 END)                    AS a11_cap_15000_cnt,
  SUM(CASE WHEN product_limit_max = 15000
            AND NOT (issue_date >= DATE '2026-10-19' AND product_level = 'D_1_03')
           THEN 1 ELSE 0 END)                                                   AS a11_cap_out_of_window,
  -- ③ 产品上限不应低于基准 10,000（期望 **0**，防止区间表写错把上限压到 1 万以下）
  SUM(CASE WHEN product_limit_max < 10000 THEN 1 ELSE 0 END)                    AS a11_cap_below_base,

  -- A8 ★【v7 验证】持有 vs 使用 解耦后的效果
  SUM(holds_offline)                                                            AS a8_holds_offline_cnt,
  -- ⚠️ 下面两个 SUM 跨笔重复计账（同一 mid 的同一批额度在每笔各记一次）。
  --   去重版见 a10_*。这里保留逐行版本作版本间对照。
  SUM(CASE WHEN holds_offline = 1 THEN offline_available_amount ELSE 0 END)     AS a8_holds_offline_avail,
  -- 这批正是 v6 漏算的：持有有效离线额度、但本笔没用任何临额
  SUM(CASE WHEN holds_offline = 1 AND used_source_tag = 'none' THEN 1 ELSE 0 END)
                                                                                AS a8_hold_but_unused_cnt,
  SUM(CASE WHEN holds_offline = 1 AND used_source_tag = 'none'
           THEN offline_available_amount ELSE 0 END)                            AS a8_hold_but_unused_avail,
  SUM(holds_online)                                                             AS a8_holds_online_cnt,
  -- ⚠️【v8】holds 不再互斥：用信前持有离线 + 用信时弹窗发在线，两者可同时为 1。观察用。
  SUM(CASE WHEN holds_offline = 1 AND holds_online = 1 THEN 1 ELSE 0 END)       AS a8_holds_both_ok,
  -- 用了离线却没被判定为持有离线（期望 0，否则说明 holds 判据漏了）
  SUM(CASE WHEN offline_used_this > 0.05 AND holds_offline = 0 THEN 1 ELSE 0 END)
                                                                                AS a8_used_not_held,
  -- 本笔使用额不该超过可用额
  -- 【v11.1】available 恢复为「名义额 − 存量占用」（实到账可用），实证 0 笔支用超过实到账
  --   （8,160 笔有 C010 的支用全部恰好 = 实到账；仅 1 笔跨笔领取无 C010 记录，用 grant 兜底）
  SUM(CASE WHEN online_used_this > online_available_amount + 0.05 THEN 1 ELSE 0 END)
                                                                                AS a8_on_use_gt_avail,
  -- 【v11.2 ★】历史存量占用拆分闭合：used_amount = inloan + noloan（来源笔按当前结清状态拆）
  --   期望 0。非 0 说明 on_src_split 漏了来源笔（窗口/排除条件错）或 C010 快照与台账口径错位。
  SUM(CASE WHEN ABS(online_used_amount - online_used_inloan_amount
                    - online_used_noloan_amount) > 0.05 THEN 1 ELSE 0 END)      AS a12_on_used_split_identity,
  -- 【v10】离线侧期望 **26**（OBS08，非公式问题，见下）
  SUM(CASE WHEN offline_used_this > offline_available_amount + 0.05 THEN 1 ELSE 0 END)
                                                                                AS a8_off_use_gt_avail,

  -- ════════════════════════════════════════════════════════════════
  -- A9 ★【v10 新增】替代作废的「合同额 > avail_future」
  --   avail 三口径按业务定义只含「主额 + 离线临额」，而合同额含在线临额和优惠券，
  --   直接比必然对 online 来源笔误报（v9 实测 5,629 笔违反，其中 5,264 笔 online
  --   + 226 笔 unknown 纯属口径错位）。剔除在线和券后再比才是真约束：
  --       main_used_this + offline_used_this <= avail_future_logic
  --   ★实测 22 笔 = OBS09 的 5 笔 + OBS08 的 17 笔，**0 笔未解释**；online/unknown 来源 0 笔。
  -- ════════════════════════════════════════════════════════════════
  SUM(CASE WHEN main_used_this + offline_used_this > avail_future_logic + 0.05
           THEN 1 ELSE 0 END)                                                   AS a9_main_off_gt_availf,
  SUM(CASE WHEN used_source_tag IN ('online','unknown')
            AND main_used_this + offline_used_this > avail_future_logic + 0.05
           THEN 1 ELSE 0 END)                                                   AS a9_online_src_bad,

  -- ════════════════════════════════════════════════════════════════
  -- OBS 观察项：**允许非 0**，均已归因、非公式缺陷，但要盯住规模别扩大
  -- ════════════════════════════════════════════════════════════════
  -- OBS08 离线用 > 离线可用（★实测 31）：yuhan 批次表金额偏小。
  --   30 笔形如「批次表记 333、账户台账实发 592、客户用了 592」；1 笔用量 > 账户 total 250 却用了 300。
  --   offline_grant_amount 保留批次口径不动（发放侧分析以 yuhan 表为准），
  --   账户台账才是真实发放额 → 这 26 笔的"超用"是口径差，不是客户真的超借。
  SUM(CASE WHEN offline_used_this > offline_available_amount + 0.05
            AND COALESCE(offline_grant_amount,0) < pre_total_amount - 0.05
           THEN 1 ELSE 0 END)                                                   AS obs08_batch_lt_acct,
  -- OBS09 主额支用 > 主额可用（期望 5）：额度源快照滞后于用信时点。
  --   4 笔 2026-10-22 放款但 1067 授信决策在 10-17~10-19、期间提过额（10-22 无决策记录），
  --   三源全停在授信时额度而台账 MAIN 冻结 = 合同额；
  --   1 笔(biz 1620000473546921) 是 y 表值比 p/s 旧 → 兜底顺序问题（见 TODO-4）。
  SUM(CASE WHEN main_used_this > main_available_amount + 0.05 THEN 1 ELSE 0 END) AS obs09_main_gt_avail,
  -- OBS10 main_used_this 轻微为负（期望 14，全落在 [−0.9, 0)）：合同额取整后的舍入噪声。
  --   临额使用额 13,997 笔中 199 笔带小数，14 笔的小数让它超过取整的合同额，最大超 0.9 元。
  --   阈值取 −1 元：超出 1 元才算真问题。
  SUM(CASE WHEN main_used_this < -0.0001 THEN 1 ELSE 0 END)                     AS obs10_main_neg_cnt,
  SUM(CASE WHEN main_used_this < -1.0    THEN 1 ELSE 0 END)                     AS obs10_main_neg_real,
  -- OBS07 批次口径 vs 账户口径不等（★实测 274 / holds_offline 11,904 的 2.3%）
  --   v9 是 1,885 笔（13.9%）；v10 的 og 时刻级改造把它降了 85%（见 og CTE 注释）。
  --   a5_grant_ne_limit 的 63 笔是它的 offline-来源切片（62 笔重叠），同一根因。
  SUM(CASE WHEN holds_offline = 1
            AND ABS(COALESCE(offline_grant_amount,0) - pre_total_amount) > 0.05
           THEN 1 ELSE 0 END)                                                   AS obs07_batch_ne_acct,

  -- ════════════════════════════════════════════════════════════════
  -- A10 ★【v10 新增】离线临额的 mid 级去重对照
  --   离线临额是**账户级(mid)**事实被扇成逐笔：同一 mid 在 5 天有效期内放多笔，
  --   同一批额度在每行各记一次。v9 实测逐行 SUM 虚增 60.8%（发放额）/ 44.7%（可用额）。
  --   凡是要回答「总共发了多少 / 总共还剩多少可用」，必须看 _dedup 这一列。
  -- ════════════════════════════════════════════════════════════════
  COUNT(DISTINCT CASE WHEN holds_offline = 1 THEN mid END)                      AS a10_holds_mid_uniq,
  COUNT(DISTINCT CASE WHEN holds_offline = 1
        THEN CAST(mid AS VARCHAR) || '|' || COALESCE(offline_grant_date,'-') END)
                                                                                AS a10_holds_batch_uniq,
  SUM(CASE WHEN holds_offline = 1 AND offline_batch_seq = 1
           THEN offline_grant_amount ELSE 0 END)                                AS a10_grant_dedup,
  SUM(CASE WHEN holds_offline = 1 AND offline_batch_seq = 1
           THEN offline_available_amount ELSE 0 END)                            AS a10_avail_dedup,
  -- 逐行版（= a8_holds_offline_avail），两者之差就是重复计账量
  SUM(CASE WHEN holds_offline = 1 THEN offline_grant_amount ELSE 0 END)         AS a10_grant_byrow,
  -- seq 列的完整性判据：holds_offline=1 且 seq=1 的**行数**必须等于去重后的批次组数
  --   （两列相等 ⟺ 每个 (mid,批次) 恰好有一行被选为代表）
  --   实测 8,642 = 8,642 ✓，max_seq=49、无 seq<1
  -- ⚠️ 不要拿 SUM(CASE WHEN seq=1 THEN offline_used_this) 去跟 SUM(offline_used_this) 比 ——
  --    used_this 是**逐笔**事实，按 seq=1 过滤会丢掉同批次第 2..n 笔的使用额
  --    （实测 367.2 万 vs 422.6 万）。这不是 bug，是该列本来就不该去重。
  SUM(CASE WHEN holds_offline = 1 AND offline_batch_seq = 1 THEN 1 ELSE 0 END)  AS a10_seq1_rows,
  -- 本笔支用额：逐笔事实，**全量求和才对**，不加任何 seq 过滤
  SUM(offline_used_this)                                                        AS a10_used_this_all
FROM mx.yj_asset_quota_v11;


-- 覆盖率对账：与 funnel 同口径比笔数，< 99% 不要用这份数据
SELECT
  (SELECT COUNT(DISTINCT biz_id) FROM mx.wxs_application_funnel
    WHERE issue_date >= DATE '2026-09-01'
      AND issue_date <= DATE_ADD('day', -1, CURRENT_DATE)
      AND if_issue = 1 AND is_reloan = 'old')                     AS funnel_cnt,
  (SELECT COUNT(DISTINCT biz_id) FROM mx.yj_asset_quota_v11)       AS wide_cnt,
  CAST((SELECT COUNT(DISTINCT biz_id) FROM mx.yj_asset_quota_v11) AS DOUBLE)
    / NULLIF(CAST((SELECT COUNT(DISTINCT biz_id) FROM mx.wxs_application_funnel
        WHERE issue_date >= DATE '2026-09-01'
          AND issue_date <= DATE_ADD('day', -1, CURRENT_DATE)
          AND if_issue = 1 AND is_reloan = 'old') AS DOUBLE), 0)  AS coverage;


-- 来源分布
-- ⚠️【v10 修正】v9 这里写 AVG(offline_available_amount + online_available_amount)，
--   把两种临额的可用额**相加**了。但它们共用同一个额度账户 limit_main_id，
--   账户总额度被最后一次发放事件**覆盖**而非叠加 —— 相加后得到的数不对应任何真实状态。
--   反例 biz 1620000464246378：离线可用 5,650 + 在线可用 4,000 = 9,650，
--   而账户 total 实为 4,000。4,062 笔同时持有两种，这一列在 online / none 两组全是错的。
--   改成分开看，并给出账户唯一真实可用 acct_available 作基准。
SELECT used_source_tag,
       COUNT(1)                                                   AS n,
       SUM(offline_used_this + online_used_this + unknown_used_this) AS used_amt,
       AVG(offline_available_amount)                              AS avg_off_avail,
       AVG(online_available_amount)                               AS avg_on_avail,
       AVG(acct_available)                                        AS avg_acct_avail,
       AVG(offline_grant_age_days)                                AS avg_offline_age,
       AVG(offline_expire_days)                                   AS avg_offline_expire
FROM mx.yj_asset_quota_v11
GROUP BY 1 ORDER BY 1;


-- 五笔标杆复核
-- ⚠️【v10 修正】v9 的标题还写着「三笔」、注释说「应全为 offline、online_grant_flag=0」，
--   但 WHERE 里早已是 5 个 biz_id，而且按 v6~v8 自己的改动，只有第 1 笔还该是 offline。
--   照旧注释复核会在 5 行里误判 4 行为错误，诱发回滚 v6~v8 的正确修正。逐笔期望：
--     1620000471903111 → offline
--     1620000467102678 → unknown（tag「0910减息测试组」过不了改动B 的 LIKE '%临额%'）
--     1620000484563011 → unknown（批次 10-07、放款 10-18，被改动A 的有效期剔除；
--                                 holds_offline=0、offline_available=0）
--     1620000473712741 → online （主额可用 18,350、日帽 10,000、在线用 4,000；
--                                 avail_tochange 应是 10,000 而非 14,000）
--     1620000464246378 → online 且 holds_offline=1、offline_available=5,650
--                                （用信前持有离线 5,650 却选了在线 4,000 —— v8 的标杆笔）
SELECT biz_id, issue_date, contract_amount, main_used_this,
       limit_total_amount, pre_total_amount, used_before, acct_available, last_grant_type,
       holds_offline, offline_batch_seq, offline_grant_amount, offline_used_amount,
       offline_available_amount, offline_used_this, offline_grant_tag,
       offline_grant_time, offline_grant_age_days, offline_expire_days,
       holds_online, online_grant_flag, online_grant_amount,
       online_used_amount, online_available_amount, online_used_this,
       used_source_tag, avail_current_logic, avail_tochange_logic, avail_future_logic
FROM mx.yj_asset_quota_v11
WHERE biz_id IN (1620000471903111, 1620000484563011, 1620000467102678,
                 1620000473712741, 1620000464246378)
ORDER BY biz_id;
