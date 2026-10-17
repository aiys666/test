# -*- coding: utf-8 -*-
"""正式取数-阶段A：聚合大数校验 + yj表唯一性检查 + 周度总览(双基准) + 逐日"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
import numpy as np

pd.set_option('display.width', 400)
pd.set_option('display.max_rows', 200)
pd.set_option('display.max_columns', 80)

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"
pq = PrestoQuery(); pq.login()

def q(sql, retry=3):
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

# ── 0. yj 表 biz_id 唯一性检查 ──
print("=" * 110)
print("[0] yj_test_table_250225 biz_id 唯一性 (7/1起)")
d0 = q("""
select count(*) as rows_cnt, count(distinct biz_id) as biz_cnt
from mx.yj_test_table_250225 where date(app_time) >= date '2026-07-01'
""")
if d0 is not None:
    print(d0.to_string(index=False))

# ── 1. 周度总览 SQL 模板 ──
BASE_AGG = """
sum(if_app) as if_app,
sum(if_issue) as issue_cnt,
sum(contract_amount) as contract_amount,
sum(loan_cycle*contract_amount) as loan_cycle_amount,
sum(haircut_amount) as haircut_amount,
sum(should_interest) as should_interest,
sum(if_in_sx) as if_in_sx,
sum(if_sx_passed) as if_sx_passed,
sum(if_in_sx_24h) as if_in_sx_24h,
sum(if_sx_passed_24h) as if_sx_passed_24h,
sum(if_in_sx_120h) as if_in_sx_120h,
sum(if_sx_passed_120h) as if_sx_passed_120h,
sum(is_t0_window_1) as is_t0_window_1,
sum(is_t3_window_1) as is_t3_window_1,
sum(is_t7_window_1) as is_t7_window_1,
sum(is_t0_window_2) as is_t0_window_2,
sum(is_t0_window_3) as is_t0_window_3,
sum(is_t0_window_4) as is_t0_window_4,
sum(is_t3_window_4) as is_t3_window_4,
sum(is_t7_window_4) as is_t7_window_4,
sum(t0_overdue_capit_1) as t0_overdue_capit_1,
sum(t0_should_capit_1) as t0_should_capit_1,
sum(t3_overdue_capit_1) as t3_overdue_capit_1,
sum(t3_should_capit_1) as t3_should_capit_1,
sum(t7_overdue_capit_1) as t7_overdue_capit_1,
sum(t7_should_capit_1) as t7_should_capit_1,
sum(t0_overdue_capit_2) as t0_overdue_capit_2,
sum(t0_should_capit_2) as t0_should_capit_2,
sum(t0_overdue_capit_3) as t0_overdue_capit_3,
sum(t0_should_capit_3) as t0_should_capit_3,
sum(t0_overdue_capit_4) as t0_overdue_capit_4,
sum(t0_should_capit_4) as t0_should_capit_4,
sum(t3_overdue_capit_4) as t3_overdue_capit_4,
sum(t3_should_capit_4) as t3_should_capit_4,
sum(t7_overdue_capit_4) as t7_overdue_capit_4,
sum(t7_should_capit_4) as t7_should_capit_4,
sum(t3_overdue_interest_4) as t3_overdue_interest_4,
sum(t7_overdue_interest_4) as t7_overdue_interest_4
"""

def calc_metrics(d):
    """按 Excel 透视表计算字段公式（SUM 后相除），返回指标 DataFrame"""
    d = d.copy()
    def pct(numer, denom):
        return (numer / denom * 100).round(2)
    d["进件数"] = d["if_app"]
    d["放款笔数"] = d["issue_cnt"]
    d["放款金额"] = d["contract_amount"].round(0)
    d["1t0本金%"] = pct(d["t0_overdue_capit_1"], d["t0_should_capit_1"])
    d["1t3本金%"] = pct(d["t3_overdue_capit_1"], d["t3_should_capit_1"])
    d["1t7本金%"] = pct(d["t7_overdue_capit_1"], d["t7_should_capit_1"])
    d["2t0本金%"] = pct(d["t0_overdue_capit_2"], d["t0_should_capit_2"])
    d["3t0本金%"] = pct(d["t0_overdue_capit_3"], d["t0_should_capit_3"])
    d["4t0本金%"] = pct(d["t0_overdue_capit_4"], d["t0_should_capit_4"])
    d["4t3本金%"] = pct(d["t3_overdue_capit_4"], d["t3_should_capit_4"])
    d["4t7本金%"] = pct(d["t7_overdue_capit_4"], d["t7_should_capit_4"])
    d["4t3息费%"] = pct(d["t3_overdue_interest_4"], d["t3_should_capit_4"])
    d["4t7息费%"] = pct(d["t7_overdue_interest_4"], d["t7_should_capit_4"])
    d["前砍%"] = pct(d["haircut_amount"], d["contract_amount"])
    d["后收%"] = pct(d["should_interest"], d["contract_amount"])
    d["4t3TR%"] = (d["后收%"] + d["前砍%"] - d["4t3息费%"] - d["4t3本金%"]).round(2)
    d["4T7TR%"] = (d["后收%"] + d["前砍%"] - d["4t7息费%"] - d["4t7本金%"]).round(2)
    d["件均"] = (d["contract_amount"] / d["issue_cnt"]).round(0)
    d["期限"] = (d["loan_cycle_amount"] / d["contract_amount"]).round(2)
    d["前置%"] = pct(d["if_in_sx"], d["if_app"])
    d["后置"] = (d["issue_cnt"] / d["if_sx_passed"]).round(3)
    d["风险通过率%"] = (d["前置%"] * d["后置"]).round(2)
    d["24h用信率%"] = pct(d["if_sx_passed_24h"], d["if_in_sx_24h"])
    d["120h用信率%"] = pct(d["if_sx_passed_120h"], d["if_in_sx_120h"])
    return d

# 简单：出账列直接改名
def add_window_cols(d):
    d = d.copy()
    d["1t0出账"] = d["is_t0_window_1"]; d["1t3出账"] = d["is_t3_window_1"]; d["1t7出账"] = d["is_t7_window_1"]
    d["2t0出账"] = d["is_t0_window_2"]; d["3t0出账"] = d["is_t0_window_3"]; d["4t0出账"] = d["is_t0_window_4"]
    d["4t3出账"] = d["is_t3_window_4"]; d["4t7出账"] = d["is_t7_window_4"]
    return d

# ── 2. 周度总览 issue_week 基准 ──
print("=" * 110)
print("[1] 周度总览 —— 放款周 issue_week 基准")
s1 = f"""
select date_trunc('week', date(release_time)) as wk, {BASE_AGG}
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey'
  and date(create_time) >= date '2026-07-01'
  and if_issue = 1
group by 1 order by 1
"""
d1 = q(s1)
if d1 is not None:
    d1 = _num(d1, [c for c in d1.columns if c != 'wk'])
    d1 = add_window_cols(d1)
    m1 = calc_metrics(d1)
    keep = ["wk","进件数","放款笔数","放款金额","1t0本金%","1t3本金%","1t7本金%","2t0本金%","3t0本金%",
            "4t0本金%","4t3本金%","4t7本金%","4t3息费%","4t7息费%","前砍%","后收%","4t3TR%","4T7TR%",
            "件均","期限","前置%","后置","风险通过率%","24h用信率%","120h用信率%",
            "1t0出账","1t3出账","1t7出账","2t0出账","3t0出账","4t0出账","4t3出账","4t7出账"]
    m1["wk"] = m1["wk"].astype(str).str[:10]
    print(m1[keep].to_string(index=False))
    m1.to_pickle(os.path.join(OUT, "_agg_issue_week.pkl"))
    m1[keep].to_csv(os.path.join(OUT, "_agg_issue_week.csv"), index=False, encoding="utf-8-sig")

# ── 3. 周度总览 app_week 基准 ──
print("=" * 110)
print("[2] 周度总览 —— 进件周 app_week 基准 (放款口径 if_issue=1)")
s2 = f"""
select date_trunc('week', date(app_time)) as wk, {BASE_AGG}
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey'
  and date(create_time) >= date '2026-07-01'
  and if_issue = 1
group by 1 order by 1
"""
d2 = q(s2)
if d2 is not None:
    d2 = _num(d2, [c for c in d2.columns if c != 'wk'])
    d2 = add_window_cols(d2)
    m2 = calc_metrics(d2)
    m2["wk"] = m2["wk"].astype(str).str[:10]
    print(m2[keep].to_string(index=False))
    m2.to_pickle(os.path.join(OUT, "_agg_app_week.pkl"))
    m2[keep].to_csv(os.path.join(OUT, "_agg_app_week.csv"), index=False, encoding="utf-8-sig")

# ── 4. 逐日 1t0 (issue_date) ──
print("=" * 110)
print("[3] 逐日 1t0/4t3/4t7 本金% —— 放款日 issue_date")
s3 = """
select date(release_time) as d,
       sum(if_issue) as issue_cnt,
       sum(t0_overdue_capit_1) as t0o, sum(t0_should_capit_1) as t0s,
       sum(t3_overdue_capit_4) as t3o4, sum(t3_should_capit_4) as t3s4,
       sum(t7_overdue_capit_4) as t7o4, sum(t7_should_capit_4) as t7s4
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey'
  and date(create_time) >= date '2026-07-01' and if_issue = 1
group by 1 order by 1
"""
d3 = q(s3)
if d3 is not None:
    d3 = _num(d3, ["issue_cnt","t0o","t0s","t3o4","t3s4","t7o4","t7s4"])
    d3["1t0本金%"] = (d3["t0o"]/d3["t0s"]*100).round(2)
    d3["4t3本金%"] = (d3["t3o4"]/d3["t3s4"]*100).round(2)
    d3["4t7本金%"] = (d3["t7o4"]/d3["t7s4"]*100).round(2)
    print(d3.to_string(index=False))
    d3.to_pickle(os.path.join(OUT, "_agg_daily_issue.pkl"))

# ── 5. 逐日 1t0 (app_date) ──
print("=" * 110)
print("[4] 逐日 1t0 —— 进件日 app_date")
s4 = """
select date(app_time) as d,
       sum(if_issue) as issue_cnt,
       sum(t0_overdue_capit_1) as t0o, sum(t0_should_capit_1) as t0s,
       sum(t3_overdue_capit_4) as t3o4, sum(t3_should_capit_4) as t3s4,
       sum(t7_overdue_capit_4) as t7o4, sum(t7_should_capit_4) as t7s4
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey'
  and date(create_time) >= date '2026-07-01' and if_issue = 1
group by 1 order by 1
"""
d4 = q(s4)
if d4 is not None:
    d4 = _num(d4, ["issue_cnt","t0o","t0s","t3o4","t3s4","t7o4","t7s4"])
    d4["1t0本金%"] = (d4["t0o"]/d4["t0s"]*100).round(2)
    d4["4t3本金%"] = (d4["t3o4"]/d4["t3s4"]*100).round(2)
    d4["4t7本金%"] = (d4["t7o4"]/d4["t7s4"]*100).round(2)
    print(d4.to_string(index=False))
    d4.to_pickle(os.path.join(OUT, "_agg_daily_app.pkl"))

print("=" * 110)
print("阶段A完成")
