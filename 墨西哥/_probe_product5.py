# -*- coding: utf-8 -*-
"""放款周 × 结构因子：7天占比 / 首贷占比 / 高风险评级占比，解释8/3低点 vs 8/10起升"""
import sys, io, pickle
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"
pq = PrestoQuery(); pq.login()

def q(sql, retry=4):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r):
            print(f"  [重登{i+1}]"); pq.login(); continue
        return r
    raise SystemExit(f"[失败] {r}")

def _num(df):
    for c in df.columns:
        if c not in ('d','dim','m','w','tag','pn'): df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# 放款周 × (7天占比、首贷占比、6-12级占比) 整体汇总
print("="*120)
print("【综合】放款周：整体1t0本金% + 7天量占比 + 首贷占比 + 6-12级占比（复贷口径）")
sql = """
with f as (
  select f.*,
    date_trunc('week', date(f.release_time)) as w
  from mx.wxs_application_funnel f
  where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
    and date(f.release_time) between date '2026-06-01' and date '2026-09-30'
),
yj as (
  SELECT biz_id, 
    try_cast(android_oldcust_maincreditlevel_charge_v5_3 as double) as gl,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
),
fl as (
  SELECT mid as biz_id, 1 as is_first
  FROM mx.ys_dl_ltv_first_loan_0511
)
select cast(f.w as varchar) as w,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd,
  sum(f.if_issue) as issue_cnt,
  sum(case when f.loan_cycle=7 then f.if_issue else 0 end) as issue_7d,
  sum(case when fl.is_first=1 then f.if_issue else 0 end) as issue_first,
  sum(case when y.gl>=6 and y.gl<=12 then f.if_issue else 0 end) as issue_612
from f
left join yj y on f.biz_id=y.biz_id and y.rn=1
left join fl on cast(f.cust_id as bigint)=fl.biz_id
group by 1 order by 1
"""
r = q(sql)
if isinstance(r, str): print("[FAIL]", r[:500])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    r["7天量占比%"] = (r.issue_7d/r.issue_cnt*100).round(1)
    r["首贷量占比%"] = (r.issue_first/r.issue_cnt*100).round(1)
    r["6-12级占比%"] = (r.issue_612/r.issue_cnt*100).round(1)
    print(r[["w","issue_cnt","1t0本金%","7天量占比%","首贷量占比%","6-12级占比%"]].to_string(index=False))
    pickle.dump(r, open(OUT + r"\_probe_product5.pkl","wb"))

# 补充：6-12级占比本身是否稳定（全量进件口径，看评级结构是否突变）
print("\n" + "="*120)
print("【评级】放款周 评级分档占比（复贷 if_issue=1，yj.grade_level 取整）")
sql2 = """
with f as (
  select f.*, date_trunc('week', date(f.release_time)) as w
  from mx.wxs_application_funnel f
  where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
    and date(f.release_time) between date '2026-07-01' and date '2026-09-30'
),
yj as (
  SELECT biz_id, try_cast(android_oldcust_maincreditlevel_charge_v5_3 as integer) as gl,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
)
select cast(f.w as varchar) as w,
  sum(f.if_issue) as issue_cnt,
  sum(case when y.gl between 1 and 3 then f.if_issue else 0 end) as g_1_3,
  sum(case when y.gl between 4 and 5 then f.if_issue else 0 end) as g_4_5,
  sum(case when y.gl between 6 and 12 then f.if_issue else 0 end) as g_6_12
from f left join yj y on f.biz_id=y.biz_id and y.rn=1
group by 1 order by 1
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:500])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["1-3级%"] = (r.g_1_3/r.issue_cnt*100).round(1)
    r["4-5级%"] = (r.g_4_5/r.issue_cnt*100).round(1)
    r["6-12级%"] = (r.g_6_12/r.issue_cnt*100).round(1)
    print(r[["w","issue_cnt","1-3级%","4-5级%","6-12级%"]].to_string(index=False))

print("\n\n完成")
