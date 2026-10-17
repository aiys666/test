# 临额相关表与字段字典

## 一、核心表

| 表 | 用途 | 关键字段/备注 |
|---|---|---|
| mx.yj_test_table_250225 | 复贷老客宽表（344列），仅 is_reloan='old' and tenant='yawey' | 无 apply_time，只有 app_time/app_date；由 12老客V2&V3资产等级测试.sql 生成 |
| mx.wxs_application_funnel | 首贷+复贷主宽表（475列） | apply_time ≥ app_time；t0/t3/t7/t14/t30 齐全 |
| mx.report_application_funnel7_table | 首复贷合并表，评级来源 | join 条件 r.camera_id = cast(f7.biz_id as bigint)；credit_level 为评级，null→9999 |
| ods_view_presto.s05_user_creditlimit_change_record | 额度变更记录 | 无 biz_id，用 mid 关联 |
| ods.s05_user_creditlimit_used_detail | 额度占用明细 | change_action='FREEZE_LIMIT' 冻结本笔占用 |
| ods.s21_risk_model_record | 风险决策流记录 | modelmainid/strategytype/inputdata/outputdata(JSON)/createtime |
| user_credit_limit | 额度主表 | limit_type=MAIN/TEMP |
| mx.tmp_darren_temp_limit_table | model 1386 落表 | 每日滚动，rn 取最早 |
| mx.tmp_darren_new_temp_limit_table | model 1523 落表 | 每日滚动，rn 取最新 |
| mx.yuhan_temp_limit_base_table_his_* | 离线临额底表 | temp_limit_tag 批次/temp_limit_issue_amount 金额/temp_limit_issue_date 时间 |

## 二、yj 表临额字段与生成逻辑

| 字段 | 类型 | 来源 | rn 排序 |
|---|---|---|---|
| temp_credit_amount_issue_tag | double(0/1) | model 1386 outputdata $.temp_credit_amount_issue_tag | order by dt（最早，rn=1） |
| fd_creditlevel_main_v4_2_snapshot | double | model 1386 inputdata（进件时评级快照） | 同上 |
| fd_main_creditlevel_v5_1_snapshot | double | model 1386 inputdata | 同上 |
| last_used_credit_amount | double | model 1386 inputdata | 同上 |
| last_temp_credit_amount_issue_day_gap | double | model 1386 inputdata | 同上 |
| last_credit_amount | double | model 1386 inputdata | 同上 |
| fd_use_creditamount_score_v1 | double(-4~5) | model 1523 inputdata $.fd_use_creditamount_score_v1 | order by dt desc（最新，rn=1） |
| fd_use_creditamount_type | double(1~4) | model 1523 outputdata $.fd_use_creditamount_type | 同上 |
| temp_grant_amount | bigint | 本笔实际使用临额（/1000=比索） | 主宽表直接取 |
| temp_credit_amount_strategy_test_flag | varchar | 建表时按 apply_time hash 落表 | 现成字段勿重算 |
| strategy_temp_limit_test_flag | int | 2/9 后老策略实验标签（tag=1 且 hash 分桶） | — |
| is_loop_limit_expired | — | 循环主额是否过期（MAIN） | — |
| loan_cycle | — | 复贷周期（第几次贷） | — |
| curr_ovd_cnt_all | — | 当前多头逾期笔数（共债预警核心变量） | — |

关联键：1386/1523 落表均为 cast(biz_id as varchar/bigint) 关联；change_record 用 mid。

## 三、change_event_type 事件码

| 事件码 | 含义 |
|---|---|
| C002 | 结清成功调额（settle_adjust_quota_cnt 计数条件，MAIN 前后额度不等） |
| C003 | 用信占用主额变更（旧版算本笔占用主额：change_used-old_used） |
| C010 | 在线临额（用信弹窗决策后发放/变更） |
| C013 | 离线临额批量更新（offline_temp_credit_amount_update_df 类） |
| C015 | 离线临额批量更新（另一类批量事件） |

## 四、决策流模型节点

| modelmainid | 决策流 | 取数字段 |
|---|---|---|
| 1386 | 临额发放弹窗决策流（满额动支在线临额判断） | outputdata: temp_credit_amount_issue_tag；inputdata: 评级快照/上次额度/发放间隔 |
| 1523 | 用信环节评分 | inputdata: fd_use_creditamount_score_v1；outputdata: fd_use_creditamount_type |
| 301 | 弱反节点放松规则观测 | emcontact_curr_ovd_cnt_all |

取数固定条件：strategytype='CHAMPION'，etl_date 按日滚动；时间字段 dt = date_add('hour',-6,createtime)。

## 五、指标口径

| 指标 | 公式 |
|---|---|
| 1t0% 坏账率（用户标准，总额含利息） | sum(t0_overdue_amount_1) / sum(t0_should_amt_1)，仅 t0_should_amt_1>0 |
| 使用临额均值 | avg(if(temp_grant_amount!=0, temp_grant_amount/1000.0, null)) |
| 使用临额件数 | count(distinct if(temp_grant_amount>0, biz_id, null)) |
| 使用临额总额 | sum(temp_grant_amount/1000.0) |
| 未使用临额件数 | count(distinct if(temp_grant_amount=0, biz_id, null)) |
| TR 动支率 | 放款金额 / 授信额度 credit_amount（约30%，非笔数通过率） |
| 审批通过率 | 放款笔数 / 进件笔数（约8-10%） |

## 六、V5_2/V5_3 hash 分桶

hash = from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16) / 65536.0

| apply_time 区间 | V5_2 | V5_3 |
|---|---|---|
| >= 2026-09-03 | hash > 0.3 | hash <= 0.3（灰度30%） |
| 2026-08-10 ~ 09-03 | hash > 0.7 | hash <= 0.7（灰度70%） |
| < 2026-08-10 | null（未分桶） | null |

自然实验三组：A=hash>0.7（始终V5_2）；B=0.3<hash<=0.7（8/10-9/3 执行V5_3后切回）；C=hash<=0.3（始终V5_3）。
