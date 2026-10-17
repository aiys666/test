# -*- coding: utf-8 -*-
"""生成「墨西哥策略中间表梳理.xlsx」"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\墨西哥策略中间表梳理.xlsx"

HEADERS = ["表名", "中文描述", "客户范围", "数据内容", "用途", "调度时间", "当前调度人"]

ROWS = [
    ["mx.darren_jieqing_dt_table", "结清提额表",
     "所有结清提额客户（含不符合提额条件客户），以及提额后5天内放款借据",
     "额度前后标签、放款情况，还款与息费情况，Y标签等",
     "日常分析", "", "达伦"],
    ["mx.wxs_reloan", "首复贷判断表",
     "近720天所有进件（s09授信快照），按进件id粒度",
     "进件id + reloan_num（本次前已放款笔数+1）+ grant_strategy（首贷/复贷）",
     "作为funnel_1首复贷判断来源，是is_reloan的基础",
     "每日（dag: wxs_wide_table_create / task: wxs_appication_funnel）", ""],
    ["mx.wxs_risk_ttl", "订单级贷后TTL表",
     "放款订单（s02_loan），按订单(camera_id)粒度",
     "应还本金/利息/罚息、实还本金/利息/罚息、T0/T3/T7/T14/T30各窗口应还/实还/逾期金额、在逾天数",
     "1T0/1T7逾期率、逾期金额计算的订单级底表",
     "每日（dag: wxs_wide_table_create / task: wxs_appication_funnel）", ""],
    ["mx.wxs_vintage_all4/5", "Vintage坏账分析表（all4透视、all5重命名）",
     "放款订单，按期数(indexs 1-4)展开",
     "各期×各时间窗口(due/ovd m3~m30)的应还/逾期笔数与金额",
     "Vintage坏账率、LTV计算",
     "每日（dag: wxs_wide_table_create / task: wxs_appication_funnel）", ""],
    ["mx.wxs_overdue_basetable", "贷后基表",
     "近720天进件授信快照（s09），关联订单贷后",
     "授信快照字段 + risk_ttl应还/实还/逾期 + vintage各期窗口字段",
     "funnel_1的贷后数据来源",
     "每日（dag: wxs_wide_table_create / task: wxs_appication_funnel）", ""],
    ["mx.wxs_application_funnel_1", "进件申请主漏斗表（进件→审批→放款→贷后→渠道）",
     "近720天所有进件（s05_creditx_order主表），按进件(biz_id)粒度",
     "进件/授信快照、首复贷、渠道分类(channel_category/app)、放款信息、贷后还款逾期、首复贷标签、一键放款/高通过组标签",
     "03 darren_risk_wide_table的主表数据源；01最终宽表的基础",
     "每日（dag: wxs_wide_table_create / task: wxs_appication_funnel）", ""],
    ["mx.wxs_application_funnel_2", "审批节点详情表",
     "近720天所有进件（s05_creditx_order主表），按进件(biz_id)粒度",
     "各审批节点（强/弱反欺诈、模型、人审、三方、人审规则、电核AI/FDAI、授信等待、复贷后置强反/弱反/模型重跑等）是否进入/通过/拒绝/等待标志位",
     "漏斗节点转化分析、各节点通过率",
     "每日（dag: wxs_wide_table_create / task: wxs_appication_funnel）", ""],
    ["mx.wxs_application_funnel", "进件申请全流程风险宽表（最终产出）",
     "近720天所有进件申请客户（首贷+复贷、含未放款），按进件(biz_id)粒度",
     "进件/授信快照、放款信息、贷后还款逾期（T0-T30应还/实还/逾期、Vintage各期、在逾天数）、首复贷标签、审批各节点标志位、渠道分类、一键放款/高通过组标签",
     "周报/月报核心底表（进件量、放款量、通过率、1T0/1T7逾期率、坏账率、LTV）；复贷节点转化监控、老客画像、结清复借率分析的数据源",
     "每日（dag: wxs_wide_table_create / task: wxs_appication_funnel）", ""],
    ["darren_risk_wide_table", "审批漏斗风险等级宽表（进件经22个审批节点到放款）",
     "近720天所有进件申请客户（首贷+复贷），主表取自mx.darren_application_funnel_1，按进件(biz_id)粒度",
     "进件信息、22个审批节点标志位（是否进入/通过/拒绝/取消/等待）、授信等待时效（11h/24h/48h/72h/120h）、额度字段、授信快照产品等级、首复贷标签、高通过组标签、渠道归因、产品期限",
     "贷前审批漏斗分析：进件通过率、各节点转化率/拒绝原因、授信等待时效监控、风险等级划分依据",
     "每日（dag: darren_risk_wide_table / task: darren_risk_wide_table）", ""],
    ["mx.yj_reloan_prof", "老客画像表",
     "近12个月复贷进件（is_reloan='old'），按进件(biz_id)粒度",
     "基础画像（年龄/学历/收入分箱）、advance多头指标(GD_X_19/21)、通过率、授信额度、24h用信率、逾期出账、行为变量（申请/放款/结清次数、间隔天数、最大逾期天数）、新媒体来源、历史结清订单数等分箱标签",
     "老客分层画像分析、复贷策略设计",
     "每日（dag: yj_reloan_prof_create / task: yj_reloan_prof）", ""],
    ["mx.yj_clear_reloan", "老客结清复借率表",
     "2025-03-15以来所有结清订单（结清行为人群），按app_group+结清次数分组",
     "结清人数、结清次数分组、满足5天表现期的结清人数、结清后5天内复借人数/笔数/金额、复借通过率、24h用信率、T0/T3逾期金额",
     "结清复借率监控、提额/复借策略效果评估",
     "手动执行（代码未配置DAG注释）", ""],
    ["mx.wxs_aurora_za", "复贷节点转化监控汇总表",
     "近184天复贷进件（is_reloan='old'）",
     "申请量、强反/弱反/模型/三方/授信/授信拒绝/后置重跑各节点进入量与通过量、放款量/放款金额、24h/72h/120h授信通过情况",
     "复贷漏斗各节点转化监控",
     "每日（dag: wxs_wide_table_create / task: wxs_aurora_za）", ""],
    ["mx.fd_rule_hit_pct", "复贷规则集中率表",
     "2025-02-07以来复贷进件（is_reloan='old'）",
     "按source/app_version/高通过组/一键放款/app_group/日周月聚合的进件数，及命中各拒绝规则（强反/弱反/模型/授信/授信拒绝/后置强反/后置弱反/后置模型/三方）的rule_tag",
     "复贷拒绝规则集中度分析，定位主要拒绝原因",
     "每日（dag: wxs_wide_table_create / task: fd_rule_hit_pct）", ""],
    ["mx.yj_test_table_250225", "老客资产等级测试宽表（V2&V3）",
     "复贷老客（资产等级决策流进件），按进件(biz_id)粒度",
     "V3_3/V4_2/V5_1/V5_2资产等级、规则分/投票分/反欺诈分/行为分/各模型概率、特征变量分箱、AB测试分组标签（daily_max_limit_tag、v3_3/v4_2/v5_1/v5_2测试组/冠军组）、转产线标签、randd分组",
     "资产等级版本AB测试效果对比、额度/日限额策略分析",
     "每日（dag: yj_test_table_250225_create / task: yj_test_table_250225）", ""],
    ["mx.property_v5_1_feature_bin", "资产等级V5_1特征分箱表",
     "近720天资产等级相关进件，聚合到日/月粒度",
     "各特征（bj_fk_app_rate_2w/3m/all等）按阈值分箱打分、微财标签(weicai_label)、审批版本标签、新媒体来源",
     "资产等级特征WOE分箱监控、特征稳定性分析",
     "每日（dag: sd_property_level_feature / task: property_v5_1_feature_bin）", ""],
    ["mx.sd_wenj_approve_version_label", "首贷审批版本标签表",
     "productid=352的CHAMPION进件（2025-08-29以来）",
     "externalid + sd_approve_version_label（审批版本标签）",
     "给资产等级分析打审批版本标签",
     "每日（随wenj_risk_wide_table）", ""],
    ["mx.sd_lucy_property_feature_base", "首贷资产等级特征基础表",
     "productid=195的CHAMPION进件（2026-03-27以来）",
     "三方特征(gd_k_*、AdvanceCollectionType_60d/360d)、V4_2/V4_3资产等级、规则分、授信额度、产品等级等",
     "首贷资产等级V4_3特征集",
     "每日（dag: wenj_risk_wide_table / task: lucy_property_level_v4_3）", ""],
    ["mx.lucy_property_level_v4_3", "首贷资产等级V4_3宽表",
     "从sd_lucy_property_feature_base按externalid去重取最新一条",
     "资产等级V4_3相关特征与标签",
     "首贷资产等级V4_3下游分析",
     "每日（dag: wenj_risk_wide_table / task: lucy_property_level_v4_3）", ""],
]

wb = Workbook()
ws = wb.active
ws.title = "策略中间表梳理"

# 样式
thin = Side(style="thin", color="BFBFBF")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
title_font = Font(name="微软雅黑", size=14, bold=True, color="1F4E78")
sub_font = Font(name="微软雅黑", size=11, color="595959")
header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
header_fill = PatternFill("solid", fgColor="1F4E78")
body_font = Font(name="微软雅黑", size=10)
center = Alignment(horizontal="center", vertical="center")
wrap_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
wrap_left = Alignment(horizontal="left", vertical="top", wrap_text=True)

NCOL = len(HEADERS)
last_col = get_column_letter(NCOL)

# 标题/副标题
ws.merge_cells(f"A1:{last_col}1")
ws["A1"] = "墨西哥策略中间表梳理"
ws["A1"].font = title_font
ws["A1"].alignment = center
ws.merge_cells(f"A2:{last_col}2")
ws["A2"] = "决策用到的中间层梳理"
ws["A2"].font = sub_font
ws["A2"].alignment = center
ws.row_dimensions[1].height = 26
ws.row_dimensions[2].height = 20

# 表头
HEADER_ROW = 3
for c, h in enumerate(HEADERS, start=1):
    cell = ws.cell(row=HEADER_ROW, column=c, value=h)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = wrap_center
    cell.border = border
ws.row_dimensions[HEADER_ROW].height = 22

# 数据
r = HEADER_ROW + 1
for row in ROWS:
    for c, v in enumerate(row, start=1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font = body_font
        cell.border = border
        cell.alignment = wrap_center if c == 1 else wrap_left
    r += 1

# 列宽
widths = [30, 34, 42, 62, 48, 42, 10]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w

# 冻结表头 + 筛选
ws.freeze_panes = f"A{HEADER_ROW + 1}"
ws.auto_filter.ref = f"A{HEADER_ROW}:{last_col}{r - 1}"

wb.save(OUT)
print(f"OK -> {OUT}  共 {len(ROWS)} 行数据")
