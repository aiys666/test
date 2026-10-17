# -*- coding: utf-8 -*-
"""产品名明细：funnel.product_name 分布 + 7天产品清单 + 命名解析"""
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
        if c not in ('d','dim','m','w','tag','pname','pn','lc'): df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# 1) funnel.product_name 分布（8月复贷放款 if_issue=1）
print("="*110)
print("【1】funnel.product_name 前40 + loan_cycle（8月复贷 放款口径）")
sql1 = """
select f.product_name as pn, cast(f.loan_cycle as varchar) as lc,
       sum(f.if_issue) as issue_cnt,
       sum(f.contract_amount) as amt,
       sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-08-01' and date '2026-08-31'
group by 1,2 order by issue_cnt desc
"""
r = q(sql1)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    r["件均"] = (r.amt/r.issue_cnt).round(0)
    print(r.head(40).to_string(index=False))
    pickle.dump(r, open(OUT + r"\_probe_product4.pkl","wb"))

# 2) 只保留 loan_cycle=7 的产品
print("\n" + "="*110)
print("【2】7天产品（loan_cycle=7 / loan_indexs=1）product_name 清单 全部")
sql2 = """
select f.product_name as pn,
       sum(f.if_issue) as issue_cnt,
       sum(f.contract_amount) as amt,
       sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1 and f.loan_cycle=7
  and date(f.release_time) between date '2026-08-01' and date '2026-08-31'
group by 1 order by issue_cnt desc
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    r["件均"] = (r.amt/r.issue_cnt).round(0)
    print(r.to_string(index=False))

# 3) product_name_new（yj表）7天产品清单，并解析命名 前砍/后收
print("\n" + "="*110)
print("【3】yj.product_name_new 7天产品清单 + 命名解析（前砍/后收）")
sql3 = """
select y.product_name_new as pn,
       sum(f.if_issue) as issue_cnt,
       sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
join (
  SELECT biz_id, product_name_new,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id AND y.rn = 1
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1 and f.loan_cycle=7
  and date(f.release_time) between date '2026-08-01' and date '2026-08-31'
group by 1 order by issue_cnt desc
"""
r = q(sql3)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    print(r.to_string(index=False))

# 4) 8/17、8/24 放款周 按期限结构 + 首贷占比（回答持续高坏账原因）
print("\n" + "="*110)
print("【4】放款周 × loan_cycle 结构迁移（复贷，6/29~9/28）")
sql4 = """
select date_trunc('week', date(f.release_time)) as w,
       cast(f.loan_cycle as varchar) as lc,
       sum(f.if_issue) as issue_cnt,
       sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1
  and date(f.release_time) between date '2026-06-01' and date '2026-09-30'
group by 1,2 order by 1,2
"""
r = q(sql4)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    pv = r.pivot_table(index="w", columns="lc", values="issue_cnt", fill_value=0)
    pvr = r.pivot_table(index="w", columns="lc", values="1t0本金%", fill_value=0)
    print("--- 放款量结构 ---"); print(pv.to_string())
    print("--- 1t0本金% ---"); print(pvr.round(2).to_string())

print("\n\n完成")
