# -*- coding: utf-8 -*-
"""核心：按放款周 × 期限(loan_cycle) × 产品名 拆解结构迁移与坏账"""
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
Y = """
LEFT JOIN (
  SELECT biz_id, product_name_new,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id AND y.rn = 1
"""

# 1) 放款周 × loan_cycle 放款量占比 + 1t0本金%（复贷）
print("="*110)
print("【1】复贷(old) 放款周 × 期限(loan_cycle) 放款量占比% + 1t0本金%")
sql1 = f"""
select date_trunc('week', date(f.release_time)) as w,
  cast(f.loan_cycle as varchar) as dim,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.release_time) between date '2026-07-01' and date '2026-09-30'
group by 1,2 order by 1,2
"""
r = q(sql1)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r)
    r["w"] = r["w"].astype(str).str[:10]
    r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["放款周x期限"] = r
    pct = r.pivot_table(index="dim", columns="w", values="issue_cnt", aggfunc="sum")
    pct = pct.div(pct.sum(axis=0), axis=1)*100
    print("放款量占比%:")
    print(pct.round(1).to_string())
    bad = r.pivot_table(index="dim", columns="w", values="1t0本金%", aggfunc="mean")
    print("\n1t0本金%:")
    print(bad.round(2).to_string())
    qq = r.pivot_table(index="dim", columns="w", values="issue_cnt", aggfunc="sum")
    print("\n放款笔数:")
    print(qq.to_string())

# 2) 7天1期产品 具体 product_name_new 分布（8月复贷放款）
print("\n" + "="*110)
print("【2】7天1期(loan_cycle=7) 复贷放款 按 product_name_new 分布（8月）")
sql2 = f"""
select coalesce(y.product_name_new,'空') as pname,
  sum(f.if_issue) as issue_cnt,
  sum(f.contract_amount) as amt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
{Y}
where f.is_reloan='old' and f.tenant='yawey' and f.loan_cycle=7
  and date(f.release_time) between date '2026-08-01' and date '2026-08-31'
group by 1 order by 2 desc
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["7天产品名"] = r
    print(r.head(40).to_string(index=False))

# 3) 全期限产品 按 product_name_new 分布（8月复贷放款 TOP40）
print("\n" + "="*110)
print("【3】复贷放款(8月) 按 product_name_new 分布 TOP40")
sql3 = f"""
select coalesce(y.product_name_new,'空') as pname,
  cast(f.loan_cycle as varchar) as lc,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
{Y}
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.release_time) between date '2026-08-01' and date '2026-08-31'
group by 1,2 order by 3 desc
"""
r = q(sql3)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r); r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    res["产品名x期限"] = r
    print(r.head(50).to_string(index=False))

with open(os.path.join(OUT, "_probe_structure.pkl"), "wb") as f:
    pickle.dump(res, f)
print("\n\n保存完成: _probe_structure.pkl")
