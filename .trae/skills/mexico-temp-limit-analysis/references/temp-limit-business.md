# 临额业务逻辑参考（整理自 5 份需求文档）

来源文档：
1. 《25.11.26-新增临时额度管理体系》V1.4（2026-04-01，MK 更新）—— 在线临额/临时额度管理体系
2. 《【印尼】【墨西哥】【尼日】临时额度逻辑》V1.0（2026-03-10）—— 离线批量临额
3. 《【墨西哥】20260513 单日剩余可借额度使用率》—— daily_left_amount_quota_use_rate 口径
4. 《【墨西哥】20251209 循环贷变量改造以及临额变量提需》—— limit_type 改造 + 临额变量
5. 《【墨西哥】202511 临时额度需求相关变量开发》—— 临额变量初版

## 一、临时额度管理体系（文档1）

目标：在现有授信额度外增加独立的临时额度体系，针对授信额度已用满客户发放，预计放款规模提升 5%。

### 额度展示
- 总剩余可用额度 = 额度表剩余可用金额 + 有效期内剩余临时额度
- 今日总剩余可借 = 今日剩余可用额度 + 有效期内剩余临时额度
- 最大可借 = min(总可用额度, 今日剩余可借, 产品配置最大可借) + 有效期内剩余临额

### 用信与弹窗（在线临额核心）
- 初始用信金额 > 主额今日剩余可用 → 该笔已包含临额，不再走临额决策流；否则走临额决策流
- 用信成功后先落额度表+变更表，再调临额决策流（毫秒级）
- 临额>0 弹窗：使用 → 更新额度表+变更表（插入记录），最终用信=初始借款+临额；不使用/10秒超时/30秒-1分钟无响应 → 默认不用，不插入
- 决策流 5 秒未跑完则直接结束跳转
- 该场景临额只能全用或不用
- 先主额后临额；提额券不扣主额也不扣临额

### 还款与额度表
- 冲账顺序：先临额后主额（防风险敞口放大）
- 额度表落原三张表，用 limit_type 区分
- 风险每次输出的临额是总临额；输出非空非0时更新过期时间；输出0或空则把现有临额覆盖为0
- 主额度过期时同步使临额过期
- 新增独立的【临时额度调整决策流】，输出六要素，不放大流，必传 biz_id

## 二、离线批量临额（文档2）

背景：墨西哥风险联动运营每月两次发临额；原流程手工算额度过期/占用→Excel→技术 update，复杂不实时。墨西哥预估月增 10 万美金合同业绩。

### 链路
1. 风险提供 MID 维度名单（BI 底表字段：mid / cust_id / tenant_id）
2. 营销系统新建推送类型：临时额度 Temporary Limit（西语 Límite Temporal）；印尼另有临额百分比 Temp. Limit Pct、有效期 Temp. Limit Validity（墨西哥/尼日无）
3. 营销活动 activity_id 区分批次，(activity_id, user_id) 幂等校验（业务主键+状态机）
4. 跑批调用决策流；大流量跑批安排业务低峰/分时段
5. 落库表：
   - user_credit_limit 主表：limitType=TEMP、totalGrantamount 含临额、expiringTime 有效期、productLevel（墨西哥可能输出）
   - user_creditlimit_change_record：changeEventType、changeTotalGrantamount、changeUsedGrantamount、old* 字段、externalId 填活动ID/跑批ID

### 墨西哥离线决策流
- offline_temp_credit_amount_update_df：只更新临额，输出临额类型才更新，异常/超时/无结果不更新
- offline_credit_amount_update_df：可同时更新主额和临额，输出对应类型才更新
- 无主额记录：刷主额会创建、刷临额失败；有主额无临额：刷主额覆盖、刷临额创建；都有：更新谁覆盖谁
- 临额逻辑覆盖：用最新一条记录作为临额
- 印尼在用表 tmp_credit_valid_user（temp_credit_amount/remain_amount/start_time/end_time/status/manual_end_time）

## 三、单日剩余可借额度使用率（文档3，fd_use_creditamount_score_v1 输入）

旧版 Step：
1. 本笔占用主额 = order/snapshot 表 apply_amount - temp_grant_amount/1000；或 change_record 中 change_event_type='C003' 最近一笔 change_used_grantamount-old_used_grantamount
2. 额度表 limit_type='MAIN'：daily_max_available_limit、total_grantamount、used_grantamount
3. 单日已占用 = 当日已占用主额 - 当日释放主额（当日借款当日还款才释放）
4. 单日剩余可借 = min(total_grantamount-used_grantamount, daily_max_available_limit-单日已占用)
5. daily_left_amount_quota_use_rate = 本笔占用主额/单日剩余可借，分母0→-999

最新版：
1. 本笔占用主额 = s05_user_creditlimit_used_detail 中 biz_id=? and change_action='FREEZE_LIMIT' and limit_type='MAIN' 的 risk_credit_limit
2. 单日剩余可借同上，采用给 app 前端接口的计算值
3. 变量在用信后调用，分母需加回分子
4. daily_left_amount_quota_use_rate = 本笔占用主额/(单日剩余可借+本笔占用主额)
   - 分母0→-999；分子0→-99；接口异常→-98（不卡件）

评分为该使用率分段（4/2/0/-1/-3）+ finish_total_num 结清次数分段（>=6→1，<6→-1）之和。

## 四、2025-12-09 循环贷变量改造（文档4，关键变更）

背景：额度表引入 limit_type 后，原变量未区分主额/临额，全部加 limit_type='MAIN' 限制。

### 修改的变量（默认新增 MAIN 过滤）
- last_credit_amount：最新全局固额，limit_type='MAIN'
- last_credit_amount_change_day_gap：最近一次固额变更距今天数；变更记录表通过 limit_main_id 关联额度表 id 取 limit_type，限制 MAIN；找不到返回 -999
- last_daily_max_available_limit：最新单日可借上限（MAIN）
- last_product_level：最新产品（MAIN）
- is_loop_limit_expired：循环额度是否过期（now>有效期→1，无记录→1）（MAIN）
- loop_limit_expired_left_days：循环额度过期剩余天数，不存在返回0（MAIN）
- settle_adjust_quota_cnt：结清成功调额次数，MAIN + change_event_type='C002' 且前后额度不一致的记录数

### 新增临额变量（limit_type='TEMP'）
- last_temp_credit_amount：最新临时额度，默认0
- last_temp_credit_amount_change_day_gap：最近一次临额变更距今天数（前后临额不等的最近记录），默认 -999
- last_used_temp_credit_amount：最新占用临时额度，默认0
- temp_credit_amount_expired_left_days：临额过期剩余天数，不存在0
- last_temp_credit_amount_issue_day_gap：最近一次临额发放距今天数（变更前=0、变更后!=0 的最近记录），默认 -999
- is_temp_limit_expired：临额是否过期（无记录→1）

### 新增固额变量
- last_used_credit_amount：最新占用全局额度（MAIN），默认0
- credit_amount_use_rate：固定额度使用率 = used_credit_amount/credit_amount（MAIN），默认0

## 五、2025-11 初版变量（文档5，已被文档4命名替代）

初版命名 last_temporary_credit_amount / last_temporary_credit_amount_change_day_gap / last_used_temporary_credit_amount / temporary_credit_amount_expired_left_days / is_temporary_credit_amount_expired，口径同文档4 临额变量；2025-12-09 后统一改名为 temp_ 前缀并补齐 MAIN/TEMP 过滤。
