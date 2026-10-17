# -*- coding: utf-8 -*-
"""正式取数-阶段B：全量订单级明细分片下载 (funnel LEFT JOIN yj 去重表)
按 create_time 每7天一片，断点续传，最后 concat 存 _detail_all.pkl
"""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pd.set_option('display.width', 400)
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"

pq = PrestoQuery(); pq.login()

def q(sql, retry=4):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r.lower()):
            print(f"  [重登{i+1}]"); pq.login(); continue
        return r
    raise SystemExit(f"[失败] {r}")

# ── funnel 侧字段 ──
F = """
f.biz_id,
f.app_time, f.release_time, f.should_time, f.finish_time,
f.tenant, f.source, f.app_group, f.app, f.app_id, f.channel_category,
f.product_name, f.product_type, f.product_day, f.product_level, f.risk_level,
f.grant_score, f.grant_strategy, f.reloan_num, f.loan_cycle, f.apply_period,
f.apply_amount, f.contract_amount, f.amount, f.haircut_amount, f.should_interest,
f.should_amount, f.issue_amount, f.repay_amount,
f.if_app, f.if_issue, f.if_pass,
f.if_in_sx, f.if_sx_passed, f.if_in_sx_24h, f.if_sx_passed_24h, f.if_in_sx_120h, f.if_sx_passed_120h,
f.is_t0_window_1, f.is_t3_window_1, f.is_t7_window_1,
f.is_t0_window_2, f.is_t0_window_3, f.is_t0_window_4,
f.is_t3_window_4, f.is_t7_window_4,
f.t0_should_capit_1, f.t0_overdue_capit_1, f.t3_should_capit_1, f.t3_overdue_capit_1,
f.t7_should_capit_1, f.t7_overdue_capit_1,
f.t0_should_capit_2, f.t0_overdue_capit_2,
f.t0_should_capit_3, f.t0_overdue_capit_3,
f.t0_should_capit_4, f.t0_overdue_capit_4,
f.t3_should_capit_4, f.t3_overdue_capit_4,
f.t7_should_capit_4, f.t7_overdue_capit_4,
f.t3_overdue_interest_4, f.t7_overdue_interest_4
"""

# ── yj 侧字段 (去重后 LEFT JOIN) ──
Y = """
y.product_name_new, y.first_issue_date, y.real_issue_amount, y.loan_contract_amount,
y.android_oldcust_maincreditlevel_charge_v5_3, y.android_oldcust_maincreditlevel_charge_v6_1,
y.android_oldcust_midcreditlevel_charge_v5_3, y.android_oldcust_midcreditlevel_charge_v6_1,
y.v3_flag, y.v3_flag_huidu, y.fd_high_pass_label,
y.max_ovd_days_all, y.max_overdue_day_30d_all,
y.other_app_has_overdue_tag, y.other_app_has_overdue_interval_tag, y.emcontact_curr_ovd_cnt_all_test_flag,
y.if_reloan_24h, y.income, y.baseinfo_userprof_age, y.baseinfo_userprof_degree,
y.baseinfo_marry, y.baseinfo_employee_type, y.baseinfo_has_car, y.baseinfo_has_house,
y.v5_3_fraud_score, y.v5_3_behavior_score, y.v5_fraud_score, y.v5_behavior_score,
y.last_repay_gap_days_app_group, y.minstay_repayplan_second_30d_mid, y.history_loanrec_cnt_lastprepaydays_v2,
y.curr_ovd_cnt_all, y.curr_ovd_cnt_other_app_group, y.curr_ovd_cnt_this_app_group,
y.android_oldcust_behavior_subscore_charge_v6_1, y.android_oldcust_overdue_subscore_charge_v6_1,
y.android_oldcust_fraud_subscore_charge_v6_1, y.android_oldcust_apply_subscore_charge_v6_1,
y.android_oldcust_income_subscore_charge_v6_1
"""

Y_JOIN = f"""
LEFT JOIN (
  SELECT
    biz_id, product_name_new, first_issue_date, real_issue_amount, loan_contract_amount,
    android_oldcust_maincreditlevel_charge_v5_3, android_oldcust_maincreditlevel_charge_v6_1,
    android_oldcust_midcreditlevel_charge_v5_3, android_oldcust_midcreditlevel_charge_v6_1,
    v3_flag, v3_flag_huidu, fd_high_pass_label,
    max_ovd_days_all, max_overdue_day_30d_all,
    other_app_has_overdue_tag, other_app_has_overdue_interval_tag, emcontact_curr_ovd_cnt_all_test_flag,
    if_reloan_24h, income, baseinfo_userprof_age, baseinfo_userprof_degree,
    baseinfo_marry, baseinfo_employee_type, baseinfo_has_car, baseinfo_has_house,
    v5_3_fraud_score, v5_3_behavior_score, v5_fraud_score, v5_behavior_score,
    last_repay_gap_days_app_group, minstay_repayplan_second_30d_mid, history_loanrec_cnt_lastprepaydays_v2,
    curr_ovd_cnt_all, curr_ovd_cnt_other_app_group, curr_ovd_cnt_this_app_group,
    android_oldcust_behavior_subscore_charge_v6_1, android_oldcust_overdue_subscore_charge_v6_1,
    android_oldcust_fraud_subscore_charge_v6_1, android_oldcust_apply_subscore_charge_v6_1,
    android_oldcust_income_subscore_charge_v6_1,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id AND y.rn = 1
"""

def one_slice(d0, d1):
    fp = os.path.join(OUT, f"_detail_{d0}.pkl")
    if os.path.exists(fp):
        print(f"[skip] {d0}~{d1} 已存在")
        return
    sql = f"""
SELECT {F}, {Y}
FROM mx.wxs_application_funnel f
{Y_JOIN}
WHERE f.is_reloan='old' AND f.tenant='yawey' AND f.if_app=1
  AND date(f.create_time) >= date '{d0}' AND date(f.create_time) < date '{d1}'
"""
    t0 = time.time()
    r = q(sql)
    if isinstance(r, str):
        print(f"[FAIL] {d0}~{d1}: {r[:200]}")
        return
    if len(r) >= 9900:
        print(f"[WARN] {d0}~{d1} 接近接口1万上限 rows={len(r)} 可能截断")
    r.to_pickle(fp)
    print(f"[ok] {d0}~{d1}: rows={len(r)} cols={r.shape[1]} {time.time()-t0:.0f}s")

# 分片：6/29 起，每 3 天，到 10/04
starts = pd.date_range('2026-06-29', '2026-10-03', freq='3D')
for s in starts:
    d0 = s.strftime('%Y-%m-%d')
    d1 = (s + pd.Timedelta(days=3)).strftime('%Y-%m-%d')
    one_slice(d0, d1)

# ── concat ──
print("=" * 100)
frames, meta = [], []
for s in starts:
    fp = os.path.join(OUT, f"_detail_{s.strftime('%Y-%m-%d')}.pkl")
    if os.path.exists(fp):
        df = pd.read_pickle(fp)
        frames.append(df)
        meta.append((s.strftime('%Y-%m-%d'), len(df)))
if frames:
    allf = pd.concat(frames, ignore_index=True)
    allf.to_pickle(os.path.join(OUT, "_detail_all.pkl"))
    print("各片行数:", meta)
    print("总计 rows =", len(allf), " cols =", allf.shape[1])
    print("biz_id 总数 =", allf['biz_id'].nunique(), " 重复行数 =", len(allf) - allf['biz_id'].nunique())
    print("if_issue=1 行数 =", int((allf['if_issue']==1).sum()))
    print("保存完成: _detail_all.pkl")
else:
    print("无任何分片文件")
print("阶段B完成")
