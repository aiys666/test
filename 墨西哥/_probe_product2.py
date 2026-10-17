# -*- coding: utf-8 -*-
"""理解产品结构：loan_cycle / apply_period / loan_indexs / product_day 语义"""
import sys, io, os, pickle
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
        if c not in ('d','dim','m','w','tag'): df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

res = {}

# 1) loan_cycle x apply_period x loan_indexs 组合分布（8月复贷放款）
print("="*100)
print("【1】loan_cycle × apply_period × loan_indexs 组合（8月复贷放款）")
sql1 = """
select cast(f.loan_cycle as varchar) as lc,
       cast(f.apply_period as varchar) as ap,
       cast(f.loan_indexs as varchar) as li,
       sum(f.if_issue) as issue_cnt,
       sum(f.t0_overdue_capit_1) as ovd1, sum(f.t0_should_capit_1) as shd1,
       sum(f.t0_overdue_capit_2) as ovd2, sum(f.t0_should_capit_2) as shd2,
       sum(f.t0_overdue_capit_3) as ovd3, sum(f.t0_should_capit_3) as shd3,
       sum(f.t0_overdue_capit_4) as ovd4, sum(f.t0_should_capit_4) as shd4
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.release_time) between date '2026-08-01' and date '2026-08-31'
group by 1,2,3 order by 4 desc
"""
r = q(sql1)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r)
    r["1t0本金%"] = (r.ovd1/r.shd1*100).round(2)
    r["2t0本金%"] = (r.ovd2/r.shd2*100).round(2)
    r["3t0本金%"] = (r.ovd3/r.shd3*100).round(2)
    r["4t0本金%"] = (r.ovd4/r.shd4*100).round(2)
    res["lc_ap_li"] = r
    print(r.head(50).to_string(index=False))

# 2) yj表 product_name_new 是否有值
print("\n" + "="*100)
print("【2】yj表 product_name_new 取值分布")
sql2 = """
select coalesce(product_name_new,'空') as pname, count(*) cnt
from mx.yj_test_table_250225
group by 1 order by 2 desc limit 30
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    print(r.to_string(index=False))

with open(os.path.join(OUT, "_probe_product2.pkl"), "wb") as f:
    pickle.dump(res, f)
print("\n\n保存完成: _probe_product2.pkl")
