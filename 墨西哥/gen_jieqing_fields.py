# -*- coding: utf-8 -*-
"""生成《墨西哥风险结清表字段清单》Excel"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\墨西哥风险结清表字段清单.xlsx"

# 字段：名称, 中文名, 类型, 解释, 来源/计算逻辑
FIELDS = [
    ("分类", "字段名", "中文名", "类型", "字段解释", "来源/计算逻辑"),

    # ============ 主键与标识 ============
    ("主键标识", "externalid", "外部ID", "字符串", "结清决策流外部唯一标识，贯穿所有中间表的主键", "来自 ods.s21_risk_strategy_record.externalid"),
    ("主键标识", "jq_mid", "结清用户mid", "字符串", "结清用户的会员ID(mid)，用于关联申请漏斗表", "t0表 mid as jq_mid"),
    ("主键标识", "settle_time", "结清时间", "时间", "用户结清的时间点，为决策流 endtime，是实验分流的基准时间", "t0表 endtime as settle_time"),
    ("主键标识", "etl_date", "数据日期", "日期", "ETL数据日期分区", "各表 etl_date"),
    ("主键标识", "rn", "排序序号", "整数", "同mid+结清时间下的行序号(恒为1)", "row_number() over(partition by mid,endtime)"),

    # ============ 用户/申请信息 ============
    ("用户信息", "jq_phone", "用户手机号", "字符串", "用户手机号，参与随机分流哈希", "t2: wxs_application_funnel.phone"),
    ("用户信息", "jq_app_group_sha256", "应用分组sha256", "字符串", "应用分组标识的sha256值，参与随机分流哈希", "t2: app_group_sha256"),
    ("用户信息", "jq_credit_no", "借据号", "字符串", "借款合同/借据编号，参与随机分流哈希", "t2: credit_no"),
    ("用户信息", "mid", "会员ID", "字符串", "申请漏斗表的会员ID，与jq_mid关联", "t1(申请漏斗表).mid"),
    ("用户信息", "biz_id", "业务ID", "字符串", "业务/订单ID，用于关联额度使用明细", "t1(申请漏斗表).biz_id"),
    ("用户信息", "product_name", "产品名称", "字符串", "原始产品名称(如 7*2 后收50 等)", "t1(申请漏斗表).product_name"),
    ("用户信息", "product_name_new", "产品标准化名称", "字符串", "产品名称标准化编码(如 B_07_02_00_50 / C_15_02_00_60 等)", "按产品名称映射生成"),
    ("用户信息", "is_reloan", "是否复贷", "标签", "是否复贷标识 old=老客复贷, new=新客", "t1(申请漏斗表).is_reloan"),
    ("用户信息", "create_time", "创建时间", "时间", "申请记录创建时间", "t1(申请漏斗表).create_time"),
    ("用户信息", "app_time", "申请时间", "时间", "申请放款时间", "t1(申请漏斗表).app_time"),

    # ============ 授信额度相关 ============
    ("授信额度", "credit_amount", "结清后授信额度", "数值", "结清授信决策流更新后的授信额度(核心结果字段)", "t0: json_extract(outputdata,'$.credit_amount')"),
    ("授信额度", "jq_global_limit", "结清全局额度", "数值", "结清全局额度，等于credit_amount", "t0.credit_amount as jq_global_limit"),
    ("授信额度", "daily_max_available_limit", "日最大可用额度", "数值", "结清决策流更新后的日最大可用额度", "t0: json_extract(outputdata,'$.daily_max_available_limit')"),
    ("授信额度", "last_credit_amount", "上一次授信额度", "数值", "上一周期的授信额度，用于判断提额/降额", "t5(t2表): json_extract(inputdata,'$.last_credit_amount')"),
    ("授信额度", "newcust_newest_credit_amount", "新客最新授信额度", "数值", "新客最新授信额度(取t2表最近一条)", "t9: t2.last_credit_amount"),
    ("授信额度", "newcust_credit_limit", "新客授信额度", "数值", "新客授信额度", "t10: dws.dws_risk_stgy_apply_mid_tags.newcust_credit_limit"),
    ("授信额度", "champion_fd_grantcredit_global_amount_uncapped", "全局额度未封顶值", "数值", "授信决策流全局额度(未加cap)原值", "t3: inputdata.fd_grantcredit_global_amount_uncapped"),
    ("授信额度", "champion_fd_grantcredit_global_amount_add_cap", "全局额度加cap值", "数值", "授信决策流全局额度(加cap后)值", "t3: inputdata.fd_grantcredit_global_amount_add_cap"),
    ("授信额度", "champion_global_limit", "全局额度上限", "数值", "授信决策流全局额度上限(cap)", "t3: outputdata.global_limit"),
    ("授信额度", "sx_credit_amount", "复贷授信额度", "数值", "复贷授信决策流(productid=196)的授信额度", "t7(t7表): outputdata.credit_amount"),
    ("授信额度", "sx_daily_max_available_limit", "复贷日最大可用额度", "数值", "复贷授信决策流的日最大可用额度", "t7: outputdata.daily_max_available_limit"),
    ("授信额度", "change_used_grantamount", "变更已用授信金额", "数值", "额度变更后已使用的授信金额", "t2: mx.darren_bizid_used_grantamount"),
    ("授信额度", "oneday_used_grantamount", "当日已用授信金额", "数值", "当日已使用的授信金额", "t3: mx.darren_day_used_grantamount"),

    # ============ 资产等级 ============
    ("资产等级", "android_oldCust_mainCreditLevel_charge_V5_1", "老客主信用等级V5.1", "数值", "安卓老客主信用等级(V5.1版本)", "t8: outputdata.android_oldCust_mainCreditLevel_charge_V5_1"),
    ("资产等级", "android_oldCust_mainCreditLevel_charge_V5_2", "老客主信用等级V5.2", "数值", "安卓老客主信用等级(V5.2版本)", "t11: 参数表"),
    ("资产等级", "android_oldCust_mainCreditLevel_charge_V5_3", "老客主信用等级V5.3", "数值", "安卓老客主信用等级(V5.3版本)", "t14: 参数表"),

    # ============ 结清调额标签 ============
    ("调额标签", "is_settle_adjust_quota_flag", "结清调额标签", "数值", "结清决策流是否调额标签(1=调额)", "t1: outputdata.is_settle_adjust_quota_flag"),
    ("调额标签", "settle_adjust_quota_cnt", "成功调额次数", "数值", "成功调额次数(小金额测试相关)", "t7(t2表): inputdata.settle_adjust_quota_cnt"),
    ("调额标签", "low_limit_first_settle_increase_tag", "低额首次结清提额标签", "数值", "低额用户首次结清提额标签", "t2表: outputdata.low_limit_first_settle_increase_tag"),
    ("调额标签", "first_loan_low_limit_first_settle_increase_tag", "首贷低额首次结清提额标签", "数值", "首贷低额用户首次结清提额标签", "t9: t2.low_limit_first_settle_increase_tag"),

    # ============ 逾期/行为 ============
    ("逾期行为", "last_credit_amount_change_day_gap", "距上次额度变更天数", "数值", "距上一次授信额度变更的天数间隔", "t15(t9表): inputdata.last_credit_amount_change_day_gap"),
    ("逾期行为", "curr_ovd_cnt_all", "当前逾期笔数(全部)", "数值", "当前逾期订单笔数(全部维度)", "t15: inputdata.curr_ovd_cnt_all"),
    ("逾期行为", "curr_ovd_cnt_this_app_group", "当前逾期笔数(本组)", "数值", "当前逾期笔数(本应用分组)", "t15: inputdata.curr_ovd_cnt_this_app_group"),
    ("逾期行为", "curr_ovd_cnt_other_app_group_90d", "近90天他组逾期笔数", "数值", "近90天其他应用分组逾期笔数", "t15: inputdata.curr_ovd_cnt_other_app_group_90d"),
    ("逾期行为", "max_overdue_day_30d_all", "近30天最大逾期天数", "数值", "近30天最大逾期天数(全部)", "t15: inputdata.max_overdue_day_30d_all"),
    ("逾期行为", "last_credit_increase_day_gap", "距上次提额天数", "数值", "距上一次提额的天数间隔", "t15: inputdata.last_credit_increase_day_gap"),
    ("逾期行为", "hist_loanrec_cnt_issue_days_last_jieqing", "上次结清后放款单数", "数值", "自上次结清以来历史放款订单数", "t15: inputdata.hist_loanrec_cnt_issue_days_last_jieqing"),

    # ============ 结清次数/订单 ============
    ("结清次数", "repayment_clearing_count_index", "结清期次数(mid)", "整数", "mid维度结清期次数(还款订单数)", "t12: 按mid统计还款订单"),
    ("结清次数", "repayment_clearing_count", "结清订单数(mid)", "整数", "mid维度结清订单数", "t12: 按mid统计结清订单"),
    ("结清次数", "repayment_clearing_count_index_all", "结清期次数(全局)", "整数", "全局(identity维度)结清期次数", "t13: 按identity统计"),
    ("结清次数", "repayment_clearing_count_all", "结清订单数(全局)", "整数", "全局(identity维度)结清订单数", "t13: 按identity统计"),

    # ============ 实验分组/标签 ============
    ("实验分组", "v3_flag", "实验版本标识", "标签", "实验版本标识: V3_3/原V3_3现V4_2/V4_2/V5_1/V5_2/V5_3", "按结清时间+哈希分流计算"),
    ("实验分组", "new_limit_flag", "新额度提额分组", "标签", "提额实验分组(各版本提额组/对照组/均值组)", "按结清时间+v3_flag+哈希计算"),
    ("实验分组", "global_limit_cap_test_tag", "全局额度cap测试分组", "标签", "全局额度cap测试分组(测试组/冠军组/均值组)", "按结清时间+手机号哈希计算"),
    ("实验分组", "single_increase_limit_cap_test_tag", "单次提幅cap测试分组", "标签", "单次提幅cap测试分组(测试组/冠军组)", "按结清时间+手机号哈希计算"),
    ("实验分组", "daily_max_limit_tag", "日最大额度测试分组", "标签", "日最大额度测试分组(测试组/冠军组/均值组)", "按结清时间+手机号哈希计算"),
    ("实验分组", "limit_recommend_grp", "额度推荐分组", "标签", "额度推荐实验分组(额度推荐v2组/对照组)", "按结清时间+手机号哈希计算"),
    ("实验分组", "adjust_quota_tag", "调额标签", "标签", "调额结果: 提额组/平额组/降额组", "last_credit_amount 与 credit_amount 比较"),
    ("实验分组", "if_grantcredit_global_amount_add_cap", "是否命中全局额度加cap", "标签", "是否命中全局额度加cap(1=命中)", "uncapped > add_cap 判断"),
    ("实验分组", "if_global_limit_add_cap", "是否命中全局额度上限cap", "标签", "是否命中全局额度上限cap(1=命中)", "add_cap > global_limit 判断"),
    ("实验分组", "first_loan_low_limit_first_settle_increase_test_0413", "0413小金额提额测试分组", "标签", "0413小金额提额测试分组", "按首贷低额首次结清标签+哈希计算"),
    ("实验分组", "reduce_tag", "降额测试分组", "标签", "降额测试分组: 30%降幅组/20%降幅组", "按结清时间+哈希计算"),
]

# 标签取值详解
TAGS = [
    ("标签字段", "取值", "含义"),
    ("v3_flag", "V3_3", "V3.3版本实验(2025-09-10起)"),
    ("v3_flag", "原V3_3现V4_2", "原V3.3分流后转入V4.2"),
    ("v3_flag", "V4_2", "V4.2版本实验"),
    ("v3_flag", "V5_1", "V5.1版本实验(2026-02-09起)"),
    ("v3_flag", "V5_2", "V5.2版本实验(2026-04-03起)"),
    ("v3_flag", "V5_3", "V5.3版本实验(2026-05-22起)"),
    ("new_limit_flag", "vX_X.提额组", "各版本提额实验组"),
    ("new_limit_flag", "vX_X.对照组", "各版本对照组"),
    ("new_limit_flag", "v5_3.均值组", "V5.3均值组(2026-06-24起不分流)"),
    ("global_limit_cap_test_tag", "全局额度cap测试组/冠军组", "全局额度cap实验(测试vs冠军)"),
    ("single_increase_limit_cap_test_tag", "单次提幅cap测试组/冠军组", "单次提幅cap实验"),
    ("daily_max_limit_tag", "测试组/冠军组/均值组", "日最大额度实验分组"),
    ("limit_recommend_grp", "额度推荐v2组/对照组", "额度推荐v2实验"),
    ("adjust_quota_tag", "提额组/平额组/降额组", "本次结清调额方向"),
    ("reduce_tag", "30%降幅组/20%降幅组", "降额测试降幅"),
    ("first_loan_low_limit_first_settle_increase_test_0413", "0413小金额提额测试组/对照组/非小金额组", "小金额提额测试"),
]

# 表结构说明
TABLES = [
    ("表名", "说明"),
    ("mx.darren_identity_mid_base_table", "identity与mid映射基础表(用于全局维度统计)"),
    ("mx.darren_jieqing_base_table_t0", "结清授信决策流: 更新后credit_amount/daily_max_available_limit"),
    ("mx.darren_jieqing_base_table_t1", "结清调额标签 is_settle_adjust_quota_flag"),
    ("mx.darren_jieqing_base_table_t2", "低额首次结清规则集: settle_adjust_quota_cnt/last_credit_amount/low_limit_first_settle_increase_tag"),
    ("mx.darren_jieqing_base_table_t3", "全局额度cap相关: 未封顶/加cap/全局上限"),
    ("mx.darren_jieqing_base_table_t7", "复贷授信决策流(productid=196): credit_amount/daily_max_available_limit"),
    ("mx.darren_jieqing_base_table_t8", "v5_1资产等级"),
    ("mx.darren_jieqing_base_table_t9", "逾期/行为变量集合(近15天)"),
    ("mx.darren_jieqing_dt_base_table", "结清明细基础宽表(各中间表join+实验分组标签计算)"),
    ("mx.darren_jieqing_dt_table", "结清明细最终表(关联申请漏斗、额度使用明细、复贷额度)"),
    ("mx.darren_shouci_jieqing_dt_table", "首次结清明细表(满足首次结清条件的用户)"),
    ("mx.darren_shouci_jieqing_summary_table", "首次结清汇总表(按分组统计各时间窗口复贷指标)"),
]

# 样式
HEADER_FILL = PatternFill("solid", fgColor="4472C4")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
CAT_FILL = PatternFill("solid", fgColor="D9E1F2")
TITLE_FONT = Font(bold=True, size=14, color="1F4E79")
thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center")

def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER

def set_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

wb = Workbook()

# Sheet1 字段总表
ws = wb.active
ws.title = "字段总表"
ws.append(FIELDS[0])
style_header(ws, 1, len(FIELDS[0]))
prev_cat = None
for row in FIELDS[1:]:
    ws.append(row)
    r = ws.max_row
    for c in range(1, len(FIELDS[0]) + 1):
        cell = ws.cell(row=r, column=c)
        cell.border = BORDER
        cell.alignment = WRAP if c in (5, 6) else Alignment(vertical="top")
    if row[0] != prev_cat:
        ws.cell(row=r, column=1).fill = CAT_FILL
        ws.cell(row=r, column=1).font = Font(bold=True)
        prev_cat = row[0]
set_widths(ws, [16, 40, 22, 8, 46, 46])
ws.freeze_panes = "A2"

# Sheet2 标签详解
ws2 = wb.create_sheet("实验标签详解")
ws2.append(TAGS[0])
style_header(ws2, 1, len(TAGS[0]))
for row in TAGS[1:]:
    ws2.append(row)
    r = ws2.max_row
    for c in range(1, len(TAGS[0]) + 1):
        cell = ws2.cell(row=r, column=c)
        cell.border = BORDER
        cell.alignment = WRAP
set_widths(ws2, [34, 30, 40])
ws2.freeze_panes = "A2"

# Sheet3 表结构
ws3 = wb.create_sheet("表结构说明")
ws3.append(TABLES[0])
style_header(ws3, 1, len(TABLES[0]))
for row in TABLES[1:]:
    ws3.append(row)
    r = ws3.max_row
    for c in range(1, len(TABLES[0]) + 1):
        cell = ws3.cell(row=r, column=c)
        cell.border = BORDER
        cell.alignment = WRAP
set_widths(ws3, [46, 70])
ws3.freeze_panes = "A2"

wb.save(OUT)
print("saved:", OUT)
print("字段数:", len(FIELDS) - 1)
