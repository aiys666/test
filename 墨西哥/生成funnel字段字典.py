# -*- coding: utf-8 -*-
"""
生成 mx.wxs_application_funnel 全字段口径解释文档（纯中文，xlsx）。

表定位：墨西哥全链路风险宽表 = 授信快照(s09_os_credit_snapshot) × 订单(s05_creditx_order)
        × 放款(s02_loan) × 贷后基表(wxs_overdue_basetable) × 反欺诈/审批节点(funnel_2)，
        进件粒度，create_date 近720天。

字段口径来源：
  - 期次×窗口字段（tN_xxx_{期}）: 01墨西哥风险宽表新口径.sql vintage_all4/all5 别名 + 窗口判定
  - 订单级截止点字段（tN_overdue_amount 无期次）: risk_ttl 的 T{N}_OVERDUE_AMOUNT（部署表为小写）
  - 基础/订单/放款/派生/反欺诈: funnel_1/funnel_2 构建SQL + 字段字典 + 参考字典
"""
import re
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

OUT = r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\墨西哥风险宽表wxs_application_funnel字段口径.xlsx"

# ───────────────────────── 窗口口径约定 ─────────────────────────
# 期次窗口别名（vintage all4/all5）：SQL 判定 date_diff('day', 应还日, 当前) > N
_WIN_LABEL = {
    "pre3": "应还日前3天起窗口", "pre2": "应还日前2天起窗口", "pre1": "应还日当天起窗口",
    "0": "已过应还日", "1": "逾期≥2天", "2": "逾期≥3天", "3": "逾期≥4天",
    "7": "逾期≥8天", "15": "逾期≥16天", "30": "逾期≥31天",
}
_WIN_COND = {
    "pre3": "date_diff('day',应还日,当前) > -3",
    "pre2": "date_diff('day',应还日,当前) > -2",
    "pre1": "date_diff('day',应还日,当前) > -1",
    "0": "date_diff('day',应还日,当前) > 0",
    "1": "date_diff('day',应还日,当前) > 1",
    "2": "date_diff('day',应还日,当前) > 2",
    "3": "date_diff('day',应还日,当前) > 3",
    "7": "date_diff('day',应还日,当前) > 7",
    "15": "date_diff('day',应还日,当前) > 15",
    "30": "date_diff('day',应还日,当前) > 30",
}
_PRE_EXPLAIN = {
    "pre3": "从应还日前3天起进入、跨过应还日、延续到逾期之后的累计窗口，窗口内既含未到期应还、也含已逾期未结清",
    "pre2": "从应还日前2天起进入、跨过应还日、延续到逾期之后的累计窗口，窗口内既含未到期应还、也含已逾期未结清",
    "pre1": "应还日当天起进入（已到期）、延续到逾期之后的累计窗口，窗口内既含到期应还、也含已逾期未结清",
}
_WIN = "(pre3|pre2|pre1|0|1|2|3|7|15|30)"

# 期次×窗口字段 正则
_RE_overdue_amt = re.compile(rf"^t{_WIN}_overdue_amount_(\d)$")        # 逾期金额(本+息)
_RE_overdue_capit = re.compile(rf"^t{_WIN}_overdue_capit_(\d)$")       # 逾期本金
_RE_overdue_interest = re.compile(rf"^t{_WIN}_overdue_interest_(\d)$")  # 逾期利息
_RE_should_amt = re.compile(rf"^t{_WIN}_should_amt_(\d)$")             # 应还金额(本+息)
_RE_should_capit = re.compile(rf"^t{_WIN}_should_capit_(\d)$")         # 应还本金
_RE_should_interest = re.compile(rf"^t{_WIN}_should_interest_(\d)$")    # 应还利息
_RE_is_window = re.compile(rf"^is_t{_WIN}_window_(\d)$")               # 窗口标记
_RE_is_overdue_p = re.compile(rf"^is_t{_WIN}_overdue_(\d)$")           # 是否逾期标记(期次)
_RE_is_overdue_top = re.compile(rf"^is_t{_WIN}_overdue$")              # 进件级是否逾期
_RE_coupon = re.compile(rf"^t{_WIN}_coupon_substract_(\d)$")           # 减免及券成本
_RE_is_now_overdue_1 = re.compile(r"^is_now_overdue_1$")               # 第1期 当前是否逾期

def _win_logic(win):
    if win in _PRE_EXPLAIN:
        return f"{_WIN_COND[win]}；{_PRE_EXPLAIN[win]}"
    return f"{_WIN_COND[win]}（{_WIN_LABEL[win]}）"

def vintage_def(name):
    """期次×窗口字段 → (分组, 业务含义, 口径定义)；返回 None 表示非vintage字段。"""
    def _ovd(win, p):
        return f"第{p}期 {_WIN_LABEL[win]} 逾期金额(本+息)", f"{_win_logic(win)}；该期累计未结清金额(本+息)"
    def _cap(win, p):
        return f"第{p}期 {_WIN_LABEL[win]} 逾期本金", f"{_win_logic(win)}；该期累计未结清本金"
    def _int_ovd(win, p):
        return f"第{p}期 {_WIN_LABEL[win]} 逾期利息", f"{_win_logic(win)}；该期累计未结清利息"
    def _should(win, p):
        return f"第{p}期 {_WIN_LABEL[win]} 应还金额(本+息)", f"{_win_logic(win)}；该期应还总额(本+息)"
    def _should_cap(win, p):
        return f"第{p}期 {_WIN_LABEL[win]} 应还本金", f"{_win_logic(win)}；该期应还本金"
    def _should_int(win, p):
        return f"第{p}期 {_WIN_LABEL[win]} 应还利息", f"{_win_logic(win)}；该期应还利息"
    def _iswin(win, p):
        return f"第{p}期 {_WIN_LABEL[win]} 窗口标记(0/1)", f"{_win_logic(win)}；该期是否已进入该窗口"
    def _isovd(win, p):
        return f"第{p}期 {_WIN_LABEL[win]} 是否逾期标记(0/1)", f"{_win_logic(win)}；该期是否未结清"
    def _istop(win):
        return f"进件级是否{_WIN_LABEL[win]}未结清(取各期次最大)", f"{_win_logic(win)}；4期取最大，任一期末结清即=1"
    def _coupon(win, p):
        return f"第{p}期 {_WIN_LABEL[win]} 减免及券成本", f"{_win_logic(win)}；该期累计减免及优惠券成本"

    m = _RE_overdue_amt.match(name)
    if m: g = _ovd(*m.groups()); return ("期次×窗口：逾期金额(本+息)",) + g
    m = _RE_overdue_capit.match(name)
    if m: g = _cap(*m.groups()); return ("期次×窗口：逾期本金/利息",) + g
    m = _RE_overdue_interest.match(name)
    if m: g = _int_ovd(*m.groups()); return ("期次×窗口：逾期本金/利息",) + g
    m = _RE_should_amt.match(name)
    if m: g = _should(*m.groups()); return ("期次×窗口：应还金额(本+息)",) + g
    m = _RE_should_capit.match(name)
    if m: g = _should_cap(*m.groups()); return ("期次×窗口：应还本金/利息",) + g
    m = _RE_should_interest.match(name)
    if m: g = _should_int(*m.groups()); return ("期次×窗口：应还本金/利息",) + g
    m = _RE_is_window.match(name)
    if m: g = _iswin(*m.groups()); return ("期次×窗口：标记类",) + g
    m = _RE_is_overdue_p.match(name)
    if m: g = _isovd(*m.groups()); return ("期次×窗口：标记类",) + g
    m = _RE_is_overdue_top.match(name)
    if m: g = _istop(m.group(1)); return ("期次×窗口：标记类",) + g
    m = _RE_coupon.match(name)
    if m: g = _coupon(*m.groups()); return ("期次×窗口：减免及券成本",) + g
    if _RE_is_now_overdue_1.match(name):
        return ("期次×窗口：标记类", "第1期 当前是否逾期(未结清)", "当前时点该期是否未结清")
    return None

# ───────────────────────── 基础/订单/放款/派生/贷后/反欺诈 手工定义 ─────────────────────────
# 键为小写字段名 → (业务含义, 口径定义)
MANUAL = {
    # ---- 授信快照与客户信息 (s09_os_credit_snapshot a.*) ----
    "create_time": ("授信快照创建时间", "直取 ods_view_presto.s09_os_credit_snapshot.create_time"),
    "create_date": ("授信快照日期", "直取 create_date（建表时限制 create_date>=近720天 且<=current_date）"),
    "cust_id": ("客户ID", "直取 s09_os_credit_snapshot.cust_id"),
    "identity": ("客户身份标识", "证件类型（如身份证/护照等），与 credit_no 关联"),
    "id": ("进件ID/授信快照ID", "授信快照主键，与订单 b.biz_id 关联；下游 camera_id 亦源于此"),
    "device_id": ("设备ID", "客户申请时使用的设备唯一标识"),
    "mid": ("客户号", "身份证+app 维度唯一，用于跨订单识别同一客户"),
    "tenant_id": ("租户ID", "租户唯一标识（1721000001013013=hola/…38563=yawey/…984539=tengo）"),
    "tenant": ("租户名", "CASE WHEN tenant_id→hola/yawey/tengo"),
    "app_channel": ("渠道UUID", "产品渠道唯一标识（app_channel），经映射得 app 名"),
    "risk_level": ("风险等级", "授信快照里的风险等级标记"),
    "product_day": ("产品天数", "授信产品期限天数"),
    "grant_score": ("授信评分", "客户信用评分（0-100，保留6位小数）"),
    "name": ("客户姓名", "直取 s09_os_credit_snapshot.name"),
    "longitude": ("经度", "客户申请时定位经度"),
    "latitude": ("纬度", "客户申请时定位纬度"),
    "product_level": ("产品等级", "授信产品等级（如A1），从 grantcredit_info JSON 的 product_level 解析"),
    "grantcredit_7d_amount": ("7天产品授信额度", "从 grantcredit_info JSON 的 grantcredit_7d_amount 解析（varchar）"),
    "grantcredit_14d_amount": ("14天产品授信额度", "从 grantcredit_info JSON 的 grantcredit_14d_amount 解析（varchar）"),
    "grantcredit_15d_amount": ("15天产品授信额度", "从 grantcredit_info JSON 的 grantcredit_15d_amount 解析（varchar）"),
    "grantcredit_30d_amount": ("30天产品授信额度", "从 grantcredit_info JSON 的 grantcredit_30d_amount 解析（varchar）"),
    "global_7d_limit": ("全局7天额度上限", "从 grantcredit_info JSON 的 global_7d_limit 解析（varchar）"),
    "global_limit": ("全局额度上限", "从 grantcredit_info JSON 的 global_limit 解析（varchar）"),
    "credit_amount_sx": ("授信总额", "从 grantcredit_info JSON 的 credit_amount 解析（double）"),
    "daily_max_available_limit_sx": ("每日最大可用额度", "从 grantcredit_info JSON 的 daily_max_available_limit 解析（double）"),
    "email": ("邮箱", "直取 s09_os_credit_snapshot.email"),
    "phone": ("手机号", "直取 s09_os_credit_snapshot.phone"),
    "fpid": ("设备指纹ID", "直取 s09_os_credit_snapshot.fpid"),
    # ---- 复贷标记与渠道归属 ----
    "reloan_num": ("复贷期数/第几贷", "直取 mx.wxs_reloan.reloan_num（首贷=1，复贷=历史放款次数+1）"),
    "grant_strategy": ("首贷/复贷授信策略标记", "直取 mx.wxs_reloan.grant_strategy"),
    "channel_category": ("渠道大类", "按 appsflyer media_source(register_success) 映射：facebook→FB，google→google，Apple Search Ads→apple，organic/tz*→tz，指定代理商→qudao，运营/互转/SMS→yunying，其余→organic"),
    "app": ("APP名", "按 app_channel(UUID) 映射：hola/hola se/hola max/hola pro/yawey/yawey_plus/yawey_ultra/yawey_max/tengo/voltrix/tengo_plus/tengo_ultra/tengo_max/pf，其余取 app_name"),
    "app_group": ("应用分组", "直取 ods.s08_app_category_mapping.app_group（按 app_channel）"),
    "app_group_sha256": ("应用分组(sha256编码)", "app_group 的 sha256 编码（YW→yawey 等映射）"),
    # ---- 订单信息 (s05_creditx_order b.*) ----
    "app_id": ("进件单号", "直取 b.biz_id（s05_creditx_order），与授信快照 id、funnel_2.biz_id 关联"),
    "cust_name": ("客户姓名(订单)", "直取 s05_creditx_order.cust_name"),
    "phone_num": ("手机号(订单)", "直取 s05_creditx_order.phone_num"),
    "product_type": ("产品类型", "直取 s05_creditx_order.product_type"),
    "app_time": ("申请时间", "直取 b.create_time（s05_creditx_order 创建时间）"),
    "apply_time": ("申请时间", "直取 b.apply_time"),
    "status": ("订单状态", "0=申请，1=执行中，372=已通过，425=已拒绝（order_status_code）"),
    "is_loan": ("是否放款标记", "直取 s05_creditx_order.is_loan（'1'=已放款）"),
    "product_name": ("产品名称", "直取 s05_creditx_order.product_name"),
    "double_loan": ("历史放款次数", "直取 s05_creditx_order.double_loan（0=首贷，>0=复贷次数）"),
    "source": ("来源系统", "直取 s05_creditx_order.source"),
    "is_reloan": ("是否复贷(new/old)", "double_loan_tenant=1→old，0→new；null 时按渠道/app 及 double_loan 二次判定"),
    "repayment": ("还款方式", "直取 s05_creditx_order.repayment"),
    "apply_period": ("申请期数", "直取 s05_creditx_order.apply_period"),
    "app_version": ("应用版本", "直取 s05_creditx_order.app_version"),
    "grantcredit_amount": ("授信额度", "直取 s05_creditx_order.grantcredit_amount"),
    "temp_grant_amount": ("临时授信额度", "直取 s05_creditx_order.temp_grant_amount"),
    # ---- 放款信息 (s02_loan c.*) ----
    "loan_cycle": ("产品期限(天)", "直取 s02_loan.loan_cycle 并向上取整"),
    "contract_amount": ("合同金额", "直取 s02_loan.contract_amount"),
    "amount": ("实际放款金额", "直取 s02_loan.amount"),
    "haircut_amount": ("砍头金额(前砍)", "直取 s02_loan.haircut_amount（放款时先扣除的费用）"),
    "release_time": ("放款时间", "直取 s02_loan.release_time"),
    "cancel_time": ("取消时间", "直取 s02_loan.cancel_time"),
    "finish_time": ("结清时间", "直取 s02_loan.finish_time"),
    "loan_state": ("放款状态", "0=待审核，1=已放款，2=正常结清，3=核销，4=取消，5=放款失败，6=审核拒绝，7=放款中"),
    "loan_indexs": ("贷款期数(总期数)", "直取 s02_loan.loan_indexs"),
    # ---- 进件/放款派生标志 ----
    "if_app": ("是否进件(0/1)", "b.biz_id 非空→1"),
    "if_pass": ("是否机审通过(0/1)", "status=372→1"),
    "if_bid": ("是否发标(0/1)", "is_loan='1'→1"),
    "if_cancel": ("是否取消(0/1)", "cancel_time 非空→1"),
    "if_issue": ("是否放款(0/1)", "贷后 should_time 非空→1"),
    "apply_amount": ("用户申请额度(千元)", "b.apply_amount/1000"),
    "approve_amount": ("审批额度(千元)", "b.approve_amount/1000"),
    "issue_amount": ("放款金额(实际)", "should_capital 非空时取 c.amount，否则0"),
    "should_amount": ("应还本金(全期累计)", "直取贷后 should_capital（仅本金，不含息费）"),
    "repay_amount": ("实还本金(全期累计)", "直取贷后 fact_capital（仅本金）"),
    "app_date": ("进件日", "date(b.create_time)"),
    "app_week": ("进件周", "date_trunc('week',date(b.create_time))"),
    "app_month": ("进件月", "date_trunc('month',date(b.create_time))"),
    "issue_date": ("放款日", "date(c.release_time)"),
    "issue_week": ("放款周", "date_trunc('week',date(c.release_time))"),
    "issue_month": ("放款月", "date_trunc('month',date(c.release_time))"),
    "deadline": ("到期日(应还日)", "date(d.should_time)"),
    "camera_id": ("贷款ID", "贷后基表主键（s02_loan.camera_id），按订单关联贷款"),
    # ---- 贷后订单级（截止点口径, risk_ttl） ----
    "should_time": ("应还时间(应还日)", "订单级最早/约定应还时间（贷后基表）"),
    "should_capital": ("应还本金(全期累计)", "订单所有期应还本金合计（贷后基表）"),
    "fact_capital": ("实还本金(全期累计)", "订单所有期实还本金合计"),
    "should_interest": ("应还利息(全期累计)", "订单所有期应还利息合计"),
    "fact_interest": ("实还利息(全期累计)", "订单所有期实还利息合计"),
    "should_fine": ("应还罚息(全期累计)", "订单所有期应还罚息合计"),
    "fact_fine": ("实还罚息(全期累计)", "订单所有期实还罚息合计"),
    "now_should_amt": ("当前应还总额(本+息)", "应还本金+应还利息（全期，不分期）"),
    "is_t0_window": ("是否已过应还日(0/1)", "date_diff('day',应还日,当前)>0"),
    "is_t3_window": ("是否已过应还日后3天(0/1)", "date_diff('day',应还日,当前)>3"),
    "is_t7_window": ("是否已过应还日后7天(0/1)", "date_diff('day',应还日,当前)>7"),
    "is_t14_window": ("是否已过应还日后14天(0/1)", "date_diff('day',应还日,当前)>14"),
    "is_t30_window": ("是否已过应还日后30天(0/1)", "date_diff('day',应还日,当前)>30"),
    "t0_should_amt": ("应还日已过时点应还金额(本+息)", "应还日<今天时=应还本金+应还利息，否则空"),
    "t3_should_amt": ("应还日后3天时点应还金额(本+息)", "应还日+3天<今天时=应还本金+应还利息，否则空"),
    "t7_should_amt": ("应还日后7天时点应还金额(本+息)", "应还日+7天<今天时=应还本金+应还利息，否则空"),
    "t14_should_amt": ("应还日后14天时点应还金额(本+息)", "应还日+14天<今天时=应还本金+应还利息，否则空"),
    "t30_should_amt": ("应还日后30天时点应还金额(本+息)", "应还日+30天<今天时=应还本金+应还利息，否则空"),
    "now_fact_amt": ("当前累计实还金额(本+息)", "订单累计实还本金+实还利息"),
    "t0_fact_amt": ("应还日当天及之前累计实还(本+息)", "fact_time<=应还日的累计实还"),
    "t3_fact_amt": ("应还日后3天内累计实还(本+息)", "fact_time<=应还日+3天的累计实还"),
    "t7_fact_amt": ("应还日后7天内累计实还(本+息)", "fact_time<=应还日+7天的累计实还"),
    "t14_fact_amt": ("应还日后14天内累计实还(本+息)", "fact_time<=应还日+14天的累计实还"),
    "t30_fact_amt": ("应还日后30天内累计实还(本+息)", "fact_time<=应还日+30天的累计实还"),
    "t0_should_num": ("应还日是否已过(0/1)", "date(should_time)<current_date→1"),
    "t3_should_num": ("应还日后3天是否已过(0/1)", "date(should_time)+3天<current_date→1"),
    "t7_should_num": ("应还日后7天是否已过(0/1)", "date(should_time)+7天<current_date→1"),
    "t14_should_num": ("应还日后14天是否已过(0/1)", "date(should_time)+14天<current_date→1"),
    "t30_should_num": ("应还日后30天是否已过(0/1)", "date(should_time)+30天<current_date→1"),
    "pre_p2_repay": ("提前还款金额(本+息, 应还日前>2天)", "fact_time距应还日>2天（到期前≥3天）的还款合计"),
    "p2_repay": ("应还日前第2天还款金额(本+息)", "fact_time距应还日=2天的还款合计"),
    "p2_repaytt": ("应还日前≥2天还款金额(本+息)", "fact_time距应还日>=2天的还款合计"),
    "p1_repay": ("应还日前第1天还款金额(本+息)", "fact_time距应还日=1天的还款合计"),
    "p0_repay": ("应还日当天还款金额(本+息)", "fact_time距应还日=0天的还款合计"),
    "now_overdue_amount": ("当前时点逾期金额(本+息)", "应还总额-当前累计实还（实还>=应还→0，实还空→应还总额）"),
    "t0_overdue_amount": ("应还日(T0)时点逾期金额(本+息)", "截止点口径：应还总额-应还日当天及之前累计实还（实还>=应还→0，实还空→应还总额）"),
    "t3_overdue_amount": ("应还日后3天(T3)时点逾期金额(本+息)", "截止点口径：应还总额-应还日后3天内累计实还（规则同上）"),
    "t7_overdue_amount": ("应还日后7天(T7)时点逾期金额(本+息)", "截止点口径：应还总额-应还日后7天内累计实还（规则同上）"),
    "t14_overdue_amount": ("应还日后14天(T14)时点逾期金额(本+息)", "截止点口径：应还总额-应还日后14天内累计实还（规则同上）"),
    "t30_overdue_amount": ("应还日后30天(T30)时点逾期金额(本+息)", "截止点口径：应还总额-应还日后30天内累计实还（规则同上）"),
    "is_now_overdue": ("当前是否逾期(0/1)", "当前累计实还-应还总额>=-1→0，否则1"),
    "now_overdue_days": ("当前逾期天数", "当前日期距应还日天数（已结清则取结清日）"),
    "id1": ("期次窗口关联ID", "vintage_all5 关联键（=进件id），用于期次窗口字段归属"),
    # ---- 风险标签 ----
    "credit_no": ("信用编号", "客户信用编号（与 identity 关联）"),
    "one_click_loan_tag": ("一键贷标签", "直取 mx.tmp_one_click_loan_tag"),
    "fd_high_pass_label": ("FD高分标签", "直取 double_loan_tag 表 fd_high_pass_label"),
    "sd_high_pass_label": ("SD高分标签", "直取 double_loan_tag 表 sd_high_pass_label"),
    # ---- 审批节点(反欺诈) 主键/归属 ----
    "biz_id": ("进件单号", "funnel_2 主键，与 app_id 关联；按 app_id=BIZ_ID 关联审批节点信息"),
    "if_in_shou_anti_fraud": ("是否进入首贷强反欺诈节点(0/1)", "审批流程 current_processor='首贷强反欺诈' 出现即1"),
    "if_shou_anti_fraud_passed": ("首贷强反欺诈是否通过(0/1)", "无 REFUSED 记录→1"),
    "if_shou_anti_fraud_refused": ("首贷强反欺诈是否拒绝(0/1)", "有 REFUSED 记录→1"),
    "if_in_fu_anti_fraud": ("是否进入复贷强反欺诈节点(0/1)", "current_processor='复贷强反欺诈' 出现即1"),
    "if_fu_anti_fraud_passed": ("复贷强反欺诈是否通过(0/1)", "无 REFUSED 记录→1"),
    "if_fu_anti_fraud_refused": ("复贷强反欺诈是否拒绝(0/1)", "有 REFUSED 记录→1"),
    "if_in_shou_anti_fraud_weak": ("是否进入首贷弱反欺诈节点(0/1)", "current_processor='首贷弱反欺诈' 出现即1"),
    "if_shou_anti_fraud_weak_passed": ("首贷弱反欺诈是否通过(0/1)", "无 REFUSED 记录→1"),
    "if_shou_anti_fraud_weak_refused": ("首贷弱反欺诈是否拒绝(0/1)", "有 REFUSED 记录→1"),
    "if_in_fu_anti_fraud_weak": ("是否进入复贷弱反欺诈节点(0/1)", "current_processor='复贷弱反欺诈' 出现即1"),
    "if_fu_anti_fraud_weak_passed": ("复贷弱反欺诈是否通过(0/1)", "无 REFUSED 记录→1"),
    "if_fu_anti_fraud_weak_refused": ("复贷弱反欺诈是否拒绝(0/1)", "有 REFUSED 记录→1"),
    "if_in_shou_model": ("是否进入首贷模型拒绝节点(0/1)", "current_processor='首贷模型拒绝' 出现即1"),
    "if_shou_model_passed": ("首贷模型是否通过(0/1)", "无 REFUSED 记录→1"),
    "if_shou_model_refused": ("首贷模型是否拒绝(0/1)", "有 REFUSED 记录→1"),
    "if_in_fu_model": ("是否进入复贷模型拒绝节点(0/1)", "current_processor='复贷模型拒绝' 出现即1"),
    "if_fu_model_passed": ("复贷模型是否通过(0/1)", "无 REFUSED 记录→1"),
    "if_fu_model_refused": ("复贷模型是否拒绝(0/1)", "有 REFUSED 记录→1"),
    "if_in_shou_normal_check": ("是否进入首贷人审节点(0/1)", "current_processor='首贷人审' 出现即1"),
    "if_shou_normal_check_passed": ("首贷人审是否通过(0/1)", "人审通过→1"),
    "if_shou_normal_check_refused": ("首贷人审是否拒绝(0/1)", "人审拒绝→1"),
    "if_shou_normal_check_canceled": ("首贷人审是否取消(0/1)", "人审取消→1"),
    "if_shou_manual_check_pending": ("首贷人审是否待处理(0/1)", "人审待处理→1"),
    "if_in_fu_manual_check": ("是否进入复贷人审节点(0/1)", "current_processor='复贷人审' 出现即1"),
    "if_fu_normal_check_passed": ("复贷人审是否通过(0/1)", "人审通过→1"),
    "if_fu_normal_check_refused": ("复贷人审是否拒绝(0/1)", "人审拒绝→1"),
    "if_fu_normal_check_canceled": ("复贷人审是否取消(0/1)", "人审取消→1"),
    "if_fu_manual_check_pending": ("复贷人审是否待处理(0/1)", "人审待处理→1"),
    "if_in_shou_external_data": ("是否进入首贷三方节点(0/1)", "current_processor='首贷三方' 出现即1"),
    "if_shou_external_data_passed": ("首贷三方是否通过(0/1)", "三方通过→1"),
    "if_shou_external_data_refused": ("首贷三方是否拒绝(0/1)", "三方拒绝→1"),
    "if_in_fu_external_data": ("是否进入复贷三方节点(0/1)", "current_processor='复贷三方' 出现即1"),
    "if_fu_external_data_passed": ("复贷三方是否通过(0/1)", "三方通过→1"),
    "if_fu_external_data_refused": ("复贷三方是否拒绝(0/1)", "三方拒绝→1"),
    "if_in_shou_normal_rule_check": ("是否进入首贷人审规则节点(0/1)", "current_processor='首贷人审规则' 出现即1"),
    "if_shou_normal_rule_check_passed": ("首贷人审规则是否通过(0/1)", "人审规则通过→1"),
    "if_shou_normal_rule_check_canceled": ("首贷人审规则是否取消(0/1)", "人审规则取消→1"),
    "if_shou_normal_rule_check_refused": ("首贷人审规则是否拒绝(0/1)", "人审规则拒绝→1"),
    "if_fu_normal_rule_check_passed": ("复贷人审规则是否通过(0/1)", "人审规则通过→1"),
    "if_fu_normal_rule_check_canceled": ("复贷人审规则是否取消(0/1)", "人审规则取消→1"),
    "if_fu_normal_rule_check_refused": ("复贷人审规则是否拒绝(0/1)", "人审规则拒绝→1"),
    "if_in_sd_ai": ("是否进入电核规则节点(SD AI)(0/1)", "current_processor='SD电核AI' 出现即1"),
    "if_shou_ai_passed": ("电核AI(首贷)是否通过(0/1)", "电核AI通过→1"),
    "if_shou_ai_pending": ("电核AI(首贷)是否待处理(0/1)", "电核AI待处理→1"),
    "if_shou_ai_refused": ("电核AI(首贷)是否拒绝(0/1)", "电核AI拒绝→1"),
    "if_in_fd_ai": ("是否进入FD AI节点(0/1)", "current_processor='FD AI' 出现即1"),
    "if_fu_ai_passed": ("FD AI是否通过(0/1)", "FD AI通过→1"),
    "if_fu_ai_refused": ("FD AI是否拒绝(0/1)", "FD AI拒绝→1"),
    "if_fu_ai_pending": ("FD AI是否待处理(0/1)", "FD AI待处理→1"),
    "if_in_sx": ("是否进入授信等待节点(0/1)", "current_processor='授信等待' 出现即1"),
    "if_sx_passed": ("授信等待是否通过(0/1)", "授信通过→1"),
    "if_sx_waiting": ("授信等待中(0/1)", "授信仍等待中→1"),
    "if_in_fu_normal_rule_check": ("是否进入复贷人审规则节点(0/1)", "current_processor='复贷人审规则' 出现即1"),
    "if_in_fu_sx_refuse": ("是否进入复贷授信拒绝节点(0/1)", "current_processor='复贷授信拒绝' 出现即1"),
    "if_fu_sx_refuse_passed": ("复贷授信拒绝节点是否通过(0/1)", "授信拒绝流程通过→1"),
    "if_fu_sx_refuse_waiting": ("复贷授信拒绝节点是否等待(0/1)", "授信拒绝流程等待中→1"),
    "if_in_sx_6h": ("授信等待>6小时仍无结果(0/1)", "授信等待超6小时无结果→1"),
    "if_in_sx_24h": ("授信等待>24小时仍无结果(0/1)", "授信等待超24小时无结果→1"),
    "if_in_sx_48h": ("授信等待>48小时仍无结果(0/1)", "授信等待超48小时无结果→1"),
    "if_in_sx_72h": ("授信等待>72小时仍无结果(0/1)", "授信等待超72小时无结果→1"),
    "if_in_sx_120h": ("授信等待>120小时仍无结果(0/1)", "授信等待超120小时无结果→1"),
    "if_sx_passed_6h": ("授信通过但耗时>6小时(0/1)", "授信通过但耗时超6小时→1"),
    "if_sx_passed_24h": ("授信通过但耗时>24小时(0/1)", "授信通过但耗时超24小时→1"),
    "if_sx_passed_48h": ("授信通过但耗时>48小时(0/1)", "授信通过但耗时超48小时→1"),
    "if_sx_passed_72h": ("授信通过但耗时>72小时(0/1)", "授信通过但耗时超72小时→1"),
    "if_sx_passed_120h": ("授信通过但耗时>120小时(0/1)", "授信通过但耗时超120小时→1"),
    "if_in_fu_post_anti_fraud_rerun": ("是否进入复贷后置强反重跑节点(0/1)", "current_processor='复贷后置强反重跑' 出现即1"),
    "if_fu_post_anti_fraud_rerun_passed": ("复贷后置强反重跑是否通过(0/1)", "后置强反重跑通过→1"),
    "if_fu_post_anti_fraud_rerun_refused": ("复贷后置强反重跑是否拒绝(0/1)", "后置强反重跑拒绝→1"),
    "if_in_fu_post_weak_anti_fraud_rerun": ("是否进入复贷后置弱反重跑节点(0/1)", "current_processor='复贷后置弱反重跑' 出现即1"),
    "if_fu_post_weak_anti_fraud_rerun_passed": ("复贷后置弱反重跑是否通过(0/1)", "后置弱反重跑通过→1"),
    "if_fu_post_weak_anti_fraud_rerun_refused": ("复贷后置弱反重跑是否拒绝(0/1)", "后置弱反重跑拒绝→1"),
    "if_in_fu_post_model_reject_rerun": ("是否进入复贷后置模型拒绝重跑节点(0/1)", "current_processor='复贷后置模型拒绝重跑' 出现即1"),
    "if_fu_post_model_reject_rerun_passed": ("复贷后置模型拒绝重跑是否通过(0/1)", "后置模型拒绝重跑通过→1"),
    "if_fu_post_model_reject_rerun_refused": ("复贷后置模型拒绝重跑是否拒绝(0/1)", "后置模型拒绝重跑拒绝→1"),
    "if_in_post_model": ("是否进入首贷后置模型拒绝节点(0/1)", "current_processor='首贷后置模型拒绝' 出现即1"),
}

# ───────────────────────── 分组排序 ─────────────────────────
GROUP_ORDER = [
    "授信快照与客户信息",
    "复贷标记与渠道归属",
    "订单信息",
    "放款信息",
    "进件/放款派生标志",
    "贷后订单级（截止点口径）",
    "期次×窗口：应还金额(本+息)",
    "期次×窗口：逾期金额(本+息)",
    "期次×窗口：应还本金/利息",
    "期次×窗口：逾期本金/利息",
    "期次×窗口：标记类",
    "期次×窗口：减免及券成本",
    "风险标签",
    "审批流程节点（反欺诈/模型/人审/三方/授信）",
]

def main():
    pq = PrestoQuery(); pq.login()
    df = pq.query("show columns from mx.wxs_application_funnel", wait_sec=5)
    if isinstance(df, str):
        print("FAILED:", df); return
    rows = []
    missing = []
    for _, r_ in df.iterrows():
        name, typ = str(r_["Column"]), str(r_["Type"])
        key = name.lower()
        vd = vintage_def(key)
        if vd:
            group, desc, logic = vd
        elif key in MANUAL:
            desc, logic = MANUAL[key]
            # 反欺诈/审批节点字段不在 _manual_group 白名单里 → 归入审批节点组；
            # if_app/if_pass 等派生标志在白名单里 → 走 _manual_group 正确分组
            g = _manual_group(key)
            group = g if g != "其他" else "审批流程节点（反欺诈/模型/人审/三方/授信）"
        else:
            missing.append(name)
            group, desc, logic = "未分类", name, "（待补充）"
        rows.append((name, typ, group, desc, logic))

    # 校验缺失
    print(f"总字段数 = {len(rows)}")
    if missing:
        print("未覆盖字段:", len(missing))
        for m in missing:
            print("  -", m)

    # 输出xlsx
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    # ---- 说明 sheet ----
    ws0 = wb.active; ws0.title = "说明"
    ws0.column_dimensions["A"].width = 16
    ws0.column_dimensions["B"].width = 110
    title = Font(name="微软雅黑", size=14, bold=True, color="1F4E78")
    hf = Font(name="微软雅黑", size=11, bold=True)
    bf = Font(name="微软雅黑", size=10)
    tl = Alignment(vertical="top", wrap_text=True)

    ws0.merge_cells("A1:B1")
    ws0["A1"] = "墨西哥风险宽表 mx.wxs_application_funnel 字段口径说明"
    ws0["A1"].font = title
    intro = [
        ("表定位", "墨西哥全链路风险宽表。一行=一笔进件/贷款，由 授信快照(ods.s09_os_credit_snapshot) × 订单(ods.s05_creditx_order) × 放款(ods.s02_loan) × 贷后基表(mx.wxs_overdue_basetable) × 反欺诈/审批节点(mx.wxs_application_funnel_2) 按进件号关联拼接。"),
        ("数据范围", "create_date >= 近720天 且 <= current_date（建表时点快照，每日更新）。金额单位为墨西哥比索(MXN)。"),
        ("主键", "app_id（进件单号，= funnel_2.biz_id）；camera_id（贷款ID）。同一客户多次贷款会出现在多行，区分用 mid(客户号)。"),
        ("新老客", "is_reloan：new=首贷，old=复贷。double_loan=历史放款次数（0=首贷）。reloan_num=第几贷。"),
        ("两种窗口口径（关键区分）", "表内含两套\"T0/T3/T7\"字段，语义完全不同，使用前务必区分：\n"
            " ① 期次×窗口字段（tN_xxx_1~_4，vintage窗口口径）：累计窗口。SQL判定 date_diff('day',应还日,当前)>N。窗口0=已过应还日(逾期≥1天)，窗口N=逾期≥N+1天（如t7=逾期≥8天）。窗口随逾期天数增长只增不减，可跨期累计。\n"
            " ② 订单级截止点字段（tN_overdue_amount / tN_should_amt / tN_fact_amt，无期次后缀）：截止点快照口径。T0=应还日当天，TN=应还日后N天，取\"该时点前累计实还\"算逾期。同一笔订单 t0逾期 与 t7逾期 可因\"7天内已还清\"出现 t7=0 < t0>0。"),
        ("preN窗口", "pre3/pre2/pre1 = 从应还日前N天起进入、跨过应还日、延续到逾期之后的累计窗口（pre1=应还日当天起）。判定 SQL date_diff('day',应还日,当前)>-N。"),
        ("期次(第N期)", "一笔贷款分期还款，_1~_4 下标 = 第1~4期。第N期窗口字段只统计该期应还/逾期明细。订单级字段=全期合并。"),
        ("金额类字段组成", "本(本金 capital)、息(利息 interest)、费(前砍 haircut_amount、罚息 fine)。\n"
            "  * 应还金额 should_amt = 本金+利息；should_capit=仅本金；should_interest=仅利息。\n"
            "  * 逾期金额 overdue_amount = 本+息；overdue_capit=仅本金；overdue_interest=仅利息。\n"
            "  * 砍头金额 haircut_amount=放款时先扣的费用（无坏账、无应还，单独字段）。"),
        ("常用口径示例", "首逾T7% = SUM(第4期逾期金额 t7_overdue_amount_4)/SUM(第4期应还金额 t7_should_amt_4)。\n"
            "截止点T7逾期% = SUM(t7_overdue_amount)/SUM(now_should_amt)（订单级）。"),
        ("审批节点字段", "if_in_* = 是否进入该节点；if_*_passed/refused/canceled/pending = 该节点是否通过/拒绝/取消/待处理。均为0/1。"),
    ]
    r = 3
    for k, v in intro:
        ws0.cell(row=r, column=1, value=k).font = hf
        ws0.cell(row=r, column=1).alignment = tl
        c = ws0.cell(row=r, column=2, value=v); c.font = bf; c.alignment = tl
        ws0.row_dimensions[r].height = max(30, 16 * (v.count("\n") + 1))
        r += 1

    # ---- 字段字典 sheet ----
    ws = wb.create_sheet("字段字典")
    HEADERS = ["序号", "分组", "字段名", "类型", "业务含义", "口径定义"]
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hf2 = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    hfill = PatternFill("solid", fgColor="1F4E78")
    bf2 = Font(name="微软雅黑", size=10)
    wrap_c = Alignment(horizontal="center", vertical="center", wrap_text=True)
    wrap_l = Alignment(horizontal="left", vertical="top", wrap_text=True)

    # 按分组排序
    def gkey(x):
        return GROUP_ORDER.index(x[2]) if x[2] in GROUP_ORDER else 99
    rows_sorted = sorted(rows, key=lambda x: (gkey(x), x[0]))

    for c, h in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = hf2; cell.fill = hfill; cell.alignment = wrap_c; cell.border = border
    for i, (name, typ, group, desc, logic) in enumerate(rows_sorted, start=2):
        vals = [i - 1, group, name, typ, desc, logic]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=i, column=c, value=v)
            cell.font = bf2; cell.border = border
            cell.alignment = wrap_c if c in (1, 4) else wrap_l
    for col, w in zip("ABCDEF", [6, 26, 34, 14, 42, 62]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:F{i}"

    # 分组汇总
    ws3 = wb.create_sheet("分组汇总")
    ws3.column_dimensions["A"].width = 6
    ws3.column_dimensions["B"].width = 46
    ws3.column_dimensions["C"].width = 10
    for c, h in enumerate(["序号", "分组", "字段数"], start=1):
        cell = ws3.cell(row=1, column=c, value=h)
        cell.font = hf2; cell.fill = hfill; cell.alignment = wrap_c; cell.border = border
    from collections import Counter
    cnt = Counter(x[2] for x in rows)
    rr = 2
    for idx, g in enumerate(GROUP_ORDER, start=1):
        n = cnt.get(g, 0)
        if n == 0:
            continue
        for c, v in enumerate([idx, g, n], start=1):
            cell = ws3.cell(row=rr, column=c, value=v)
            cell.font = bf2; cell.border = border; cell.alignment = wrap_c if c in (1, 3) else wrap_l
        rr += 1

    wb.save(OUT)
    print(f"\nOK -> {OUT}")
    print(f"字段总数 = {len(rows)}，覆盖分组 = {len(set(x[2] for x in rows))}")

def _manual_group(key):
    """非反欺诈基础字段的分组映射。"""
    GRP = [
        ("授信快照与客户信息", {"create_time","create_date","cust_id","identity","id","device_id","mid",
             "tenant_id","tenant","app_channel","risk_level","product_day","grant_score","name",
             "longitude","latitude","product_level","grantcredit_7d_amount","grantcredit_14d_amount",
             "grantcredit_15d_amount","grantcredit_30d_amount","global_7d_limit","global_limit",
             "credit_amount_sx","daily_max_available_limit_sx","email","phone","fpid"}),
        ("复贷标记与渠道归属", {"reloan_num","grant_strategy","channel_category","app","app_group","app_group_sha256"}),
        ("订单信息", {"app_id","cust_name","phone_num","product_type","app_time","apply_time","status",
             "is_loan","product_name","double_loan","source","is_reloan","repayment","apply_period",
             "app_version","grantcredit_amount","temp_grant_amount"}),
        ("放款信息", {"loan_cycle","contract_amount","amount","haircut_amount","release_time",
             "cancel_time","finish_time","loan_state","loan_indexs"}),
        ("进件/放款派生标志", {"if_app","if_pass","if_bid","if_cancel","if_issue","apply_amount",
             "approve_amount","issue_amount","should_amount","repay_amount","app_date","app_week",
             "app_month","issue_date","issue_week","issue_month","deadline","camera_id"}),
        ("贷后订单级（截止点口径）", {"should_time","should_capital","fact_capital","should_interest",
             "fact_interest","should_fine","fact_fine","now_should_amt","is_t0_window","is_t3_window",
             "is_t7_window","is_t14_window","is_t30_window","t0_should_amt","t3_should_amt","t7_should_amt",
             "t14_should_amt","t30_should_amt","now_fact_amt","t0_fact_amt","t3_fact_amt","t7_fact_amt",
             "t14_fact_amt","t30_fact_amt","t0_should_num","t3_should_num","t7_should_num","t14_should_num",
             "t30_should_num","pre_p2_repay","p2_repay","p2_repaytt","p1_repay","p0_repay",
             "now_overdue_amount","t0_overdue_amount","t3_overdue_amount","t7_overdue_amount",
             "t14_overdue_amount","t30_overdue_amount","is_now_overdue","now_overdue_days","id1"}),
        ("风险标签", {"credit_no","one_click_loan_tag","fd_high_pass_label","sd_high_pass_label"}),
    ]
    for g, names in GRP:
        if key in names:
            return g
    return "其他"

if __name__ == "__main__":
    main()
