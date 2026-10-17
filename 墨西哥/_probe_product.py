# -*- coding: utf-8 -*-
"""查 product_name 明细 + loan_cycle 语义 + 产品聚类"""
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

# 1) product_name 有哪些值，loan_cycle 分布
print("="*100)
print("【1】product_name × loan_cycle 组合（8月复贷）")
sql1 = """
select coalesce(f.product_name,'空') as pname, cast(f.loan_cycle as varchar) as lc,
  sum(f.if_issue) as issue_cnt,
  sum(f.contract_amount) as amt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.release_time) between date '2026-08-01' and date '2026-08-31'
group by 1,2 order by 3 desc
"""
r = q(sql1)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["产品名x期限"] = r
    print(r.head(60).to_string(index=False))

# 2) loan_cycle 唯一值 + 是否有期数概念（app_group vs loan_cycle）
print("\n" + "="*100)
print("【2】app_group × loan_cycle 分布（8月复贷放款）")
sql2 = """
select coalesce(f.app_group,'空') as ag, cast(f.loan_cycle as varchar) as lc,
  sum(f.if_issue) as issue_cnt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.release_time) between date '2026-08-01' and date '2026-08-31'
group by 1,2 order by 3 desc
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r)
    res["app_group x 期限"] = r
    print(r.head(50).to_string(index=False))

with open(os.path.join(OUT, "_probe_product.pkl"), "wb") as f:
    pickle.dump(res, f)
print("\n\n保存完成: _probe_product.pkl")
