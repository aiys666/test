# -*- coding: utf-8 -*-
"""正式取数-阶段B(聚合版)：SQL 内按天+维度 GROUP BY 汇总，不再拉订单级明细。
每个维度 × 每个基准(进件app_time / 放款release_time) 一条聚合SQL，SUM 全部指标字段。
输出: _aggdim_{key}_{base}.pkl  (key=维度key, base=app/issue)
本地后续滚周(app_week/issue_week) 用 calc_metrics 计算 26+1 指标。
"""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pd.set_option('display.width', 400)
pd.set_option('display.max_columns', 80)

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"
pq = PrestoQuery(); pq.login()

def q(sql, retry=4):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r):
            print(f"  [重登{i+1}]"); pq.login(); continue
        return r
    raise SystemExit(f"[失败] {r}")

def _num(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# ── 聚合字段(全部带 f. 前缀, sum) ──
AGG_COLS = [
 "if_app","if_issue","contract_amount","haircut_amount","should_interest",
 "if_in_sx","if_sx_passed","if_in_sx_24h","if_sx_passed_24h","if_in_sx_120h","if_sx_passed_120h",
 "is_t0_window_1","is_t3_window_1","is_t7_window_1",
 "is_t0_window_2","is_t0_window_3","is_t0_window_4","is_t3_window_4","is_t7_window_4",
 "t0_overdue_capit_1","t0_should_capit_1","t3_overdue_capit_1","t3_should_capit_1",
 "t7_overdue_capit_1","t7_should_capit_1",
 "t0_overdue_capit_2","t0_should_capit_2",
 "t0_overdue_capit_3","t0_should_capit_3",
 "t0_overdue_capit_4","t0_should_capit_4",
 "t3_overdue_capit_4","t3_should_capit_4",
 "t7_overdue_capit_4","t7_should_capit_4",
 "t3_overdue_interest_4","t7_overdue_interest_4",
 "is_t0_overdue_1","is_t3_overdue_1","is_t7_overdue_1",
 "is_t0_overdue_4","is_t3_overdue_4","is_t7_overdue_4",
]
AGG_F = ",\n".join([f"sum(f.{c}) as {c}" for c in AGG_COLS])
AGG_F += ",\nsum(f.loan_cycle*f.contract_amount) as loan_cycle_amount"

# ── yj 去重子查询(LEFT JOIN, rn=1) ──
Y_JOIN = """
LEFT JOIN (
  SELECT
    biz_id, product_name_new, first_issue_date, real_issue_amount, loan_contract_amount,
    android_oldcust_maincreditlevel_charge_v5_3, android_oldcust_maincreditlevel_charge_v6_1,
    android_oldcust_midcreditlevel_charge_v5_3, android_oldcust_midcreditlevel_charge_v6_1,
    v3_flag, v3_flag_huidu, fd_high_pass_label,
    max_ovd_days_all, max_overdue_day_30d_all,
    other_app_has_overdue_tag, other_app_has_overdue_interval_tag,
    if_reloan_24h, income, baseinfo_userprof_age, baseinfo_userprof_degree,
    baseinfo_marry, baseinfo_employee_type, baseinfo_has_car, baseinfo_has_house,
    v5_3_fraud_score, v5_3_behavior_score, v5_fraud_score, v5_behavior_score,
    last_repay_gap_days_app_group, minstay_repayplan_second_30d_mid, history_loanrec_cnt_lastprepaydays_v2,
    curr_ovd_cnt_all, curr_ovd_cnt_other_app_group, curr_ovd_cnt_this_app_group,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id AND y.rn = 1
"""

# ── 维度清单 ──
FUNNEL_DIMS = {
 "product_name":   "f.product_name",
 "app_group":      "f.app_group",
 "channel_category":"f.channel_category",
 "source":         "f.source",
 "product_type":   "f.product_type",
 "product_day":    "cast(f.product_day as varchar)",
 "loan_cycle":     "cast(f.loan_cycle as varchar)",
 "reloan_num":     "case when f.reloan_num=2 then '2贷' when f.reloan_num=3 then '3贷' when f.reloan_num<=5 then '4-5贷' when f.reloan_num<=9 then '6-9贷' else '10+贷' end",
 "contract_amount":"case when f.contract_amount<500 then 'L_lt500' when f.contract_amount<1000 then 'L_500_1k' when f.contract_amount<2000 then 'L_1k_2k' when f.contract_amount<5000 then 'L_2k_5k' else 'L_ge5k' end",
 "t0_should_capit":"case when f.t0_should_capit_1<500 then 'T0_lt500' when f.t0_should_capit_1<1000 then 'T0_500_1k' when f.t0_should_capit_1<2000 then 'T0_1k_2k' when f.t0_should_capit_1<5000 then 'T0_2k_5k' else 'T0_ge5k' end",
 "grant_score":    "case when f.grant_score<50 then 'S_lt50' when f.grant_score<60 then 'S_50_60' when f.grant_score<70 then 'S_60_70' when f.grant_score<80 then 'S_70_80' when f.grant_score<90 then 'S_80_90' else 'S_ge90' end",
 "grant_strategy": "f.grant_strategy",
 "product_level":  "f.product_level",
 "risk_level":     "f.risk_level",
}

YJ_DIMS = {
 "product_name_new": "coalesce(y.product_name_new,'空')",
 "v5_3主评级":       "coalesce(cast(y.android_oldcust_maincreditlevel_charge_v5_3 as varchar),'空')",
 "v6_1主评级":       "coalesce(cast(y.android_oldcust_maincreditlevel_charge_v6_1 as varchar),'空')",
 "v5_3中评级":       "coalesce(cast(y.android_oldcust_midcreditlevel_charge_v5_3 as varchar),'空')",
 "v6_1中评级":       "coalesce(cast(y.android_oldcust_midcreditlevel_charge_v6_1 as varchar),'空')",
 "v3_flag":          "coalesce(cast(y.v3_flag as varchar),'空')",
 "v3_flag_huidu":    "coalesce(cast(y.v3_flag_huidu as varchar),'空')",
 "fd_high_pass":     "coalesce(cast(y.fd_high_pass_label as varchar),'空')",
 "if_reloan_24h":    "coalesce(cast(y.if_reloan_24h as varchar),'空')",
 "学历":             "coalesce(cast(y.baseinfo_userprof_degree as varchar),'空')",
 "婚姻":             "coalesce(cast(y.baseinfo_marry as varchar),'空')",
 "职业":             "coalesce(cast(y.baseinfo_employee_type as varchar),'空')",
 "有车":             "coalesce(cast(y.baseinfo_has_car as varchar),'空')",
 "有房":             "coalesce(cast(y.baseinfo_has_house as varchar),'空')",
 "收入段":           "case when y.income<3000 then 'inc_lt3k' when y.income<5000 then 'inc_3_5k' when y.income<8000 then 'inc_5_8k' else 'inc_ge8k' end",
 "年龄段":           "case when y.baseinfo_userprof_age<25 then 'age_lt25' when y.baseinfo_userprof_age<30 then 'age_25_30' when y.baseinfo_userprof_age<35 then 'age_30_35' when y.baseinfo_userprof_age<40 then 'age_35_40' else 'age_ge40' end",
 "v5_3欺诈分":       "case when y.v5_3_fraud_score<500 then 'fx_lt500' when y.v5_3_fraud_score<600 then 'fx_500_600' when y.v5_3_fraud_score<700 then 'fx_600_700' else 'fx_ge700' end",
 "v5_3行为分":       "case when y.v5_3_behavior_score<500 then 'bh_lt500' when y.v5_3_behavior_score<600 then 'bh_500_600' when y.v5_3_behavior_score<700 then 'bh_600_700' else 'bh_ge700' end",
 "当前逾期笔数":     "case when y.curr_ovd_cnt_all=0 then 'ovd_0' when y.curr_ovd_cnt_all=1 then 'ovd_1' when y.curr_ovd_cnt_all=2 then 'ovd_2' else 'ovd_3+' end",
 "本APP逾期笔数":    "case when y.curr_ovd_cnt_this_app_group=0 then 'aovd_0' when y.curr_ovd_cnt_this_app_group=1 then 'aovd_1' when y.curr_ovd_cnt_this_app_group=2 then 'aovd_2' else 'aovd_3+' end",
 "历史最大逾期天":   "case when y.max_ovd_days_all=0 then 'mxovd_0' when y.max_ovd_days_all<=7 then 'mxovd_1_7' when y.max_ovd_days_all<=30 then 'mxovd_8_30' when y.max_ovd_days_all<=90 then 'mxovd_31_90' else 'mxovd_gt90' end",
 "他APP有逾期":      "coalesce(cast(y.other_app_has_overdue_tag as varchar),'空')",
 "最近还款间隔":      "case when y.last_repay_gap_days_app_group is null then 'gap_空' when y.last_repay_gap_days_app_group<=3 then 'gap_0_3' when y.last_repay_gap_days_app_group<=7 then 'gap_4_7' when y.last_repay_gap_days_app_group<=14 then 'gap_8_14' else 'gap_gt14' end",
}

def build_sql(base, dim_expr):
    """base: 'app'(进件基准 if_app=1) / 'issue'(放款基准 if_issue=1)"""
    if base == "app":
        day_col = "date(f.app_time)"
        cond = "f.if_app = 1"
    else:
        day_col = "date(f.release_time)"
        cond = "f.if_issue = 1"
    return f"""
select {day_col} as d, {dim_expr} as dim,
{AGG_F}
from mx.wxs_application_funnel f
{Y_JOIN}
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.create_time) >= date '2026-06-29'
  and {cond}
group by 1, 2 order by 1, 2
"""

# ── 执行 ──
TEST = False   # True=只跑产品维度issue基准验证; False=全量
if TEST:
    run = [("product_name", "issue")]
else:
    run = ([(k, "app") for k in FUNNEL_DIMS] + [(k, "issue") for k in FUNNEL_DIMS]
           + [(k, "app") for k in YJ_DIMS] + [(k, "issue") for k in YJ_DIMS])

for key, base in run:
    expr = FUNNEL_DIMS.get(key) or YJ_DIMS.get(key)
    sql = build_sql(base, expr)
    t0 = time.time()
    r = q(sql)
    if isinstance(r, str):
        print(f"[FAIL] {key}/{base}: {r[:200]}")
        continue
    r = _num(r, [c for c in r.columns if c not in ('d', 'dim')])
    if len(r) >= 9900:
        print(f"[WARN] {key}/{base} 接近接口1万上限 rows={len(r)}")
    fp = os.path.join(OUT, f"_aggdim_{key}_{base}.pkl")
    r.to_pickle(fp)
    print(f"[ok] {key}/{base}: rows={len(r)} dims={r['dim'].nunique()} days={r['d'].nunique()} {time.time()-t0:.0f}s")
    if TEST:
        print(r.head(3).to_string(index=False))

print("=" * 100)
print("聚合取数完成")
