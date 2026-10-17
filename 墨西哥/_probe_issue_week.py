# -*- coding: utf-8 -*-
"""重新定位：①放款口径完整时间序列 ②7天产品的 product_name_new 明细"""
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

# 0) 确认字段存在
print("="*100)
print("【0】wxs_application_funnel 关键字段检查")
r0 = q("select count(*) c from mx.wxs_application_funnel where 1=0")
# 直接查字段
r0 = q("select release_time, issue_date, issue_week, product_name, product_name_new, loan_cycle, is_reloan from mx.wxs_application_funnel limit 2")
if isinstance(r0, str):
    print("[FAIL 字段]", r0[:300])
else:
    print(r0.to_string())

# 1) 放款口径：按放款周 issue_week 逐周坏账（复贷老客），7/1~9/30
print("\n" + "="*100)
print("【1】复贷(old) 按放款周 逐周坏账（7月~9月，全量）")
sql1 = """
select date_trunc('week', date(f.release_time)) as w,
  sum(f.if_issue) as issue_cnt,
  sum(f.contract_amount) as amt,
  sum(f.t0_overdue_capit_1) as ovd0, sum(f.t0_should_capit_1) as shd0,
  sum(f.t3_overdue_capit_1) as ovd3, sum(f.t3_should_capit_1) as shd3,
  sum(f.t7_overdue_capit_1) as ovd7, sum(f.t7_should_capit_1) as shd7,
  sum(f.t0_overdue_capit_4) as ovd40, sum(f.t0_should_capit_4) as shd40,
  sum(f.t7_overdue_capit_4) as ovd47, sum(f.t7_should_capit_4) as shd47
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.release_time) between date '2026-07-01' and date '2026-09-30'
group by 1 order by 1
"""
r = q(sql1)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r)
    r["w"] = r["w"].astype(str).str[:10]
    r["1t0本金%"] = (r.ovd0/r.shd0*100).round(2)
    r["1t3本金%"] = (r.ovd3/r.shd3*100).round(2)
    r["1t7本金%"] = (r.ovd7/r.shd7*100).round(2)
    r["4t0本金%"] = (r.ovd40/r.shd40*100).round(2)
    r["4t7本金%"] = (r.ovd47/r.shd47*100).round(2)
    res["复贷按放款周"] = r
    print(r[["w","issue_cnt","amt","1t0本金%","1t3本金%","1t7本金%","4t0本金%","4t7本金%"]].to_string(index=False))

# 2) 首贷口径：按放款周逐周坏账（对照）
print("\n" + "="*100)
print("【2】首贷(new) 按放款周 逐周坏账（7月~9月）")
sql2 = """
select date_trunc('week', date(f.release_time)) as w,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd0, sum(f.t0_should_capit_1) as shd0,
  sum(f.t3_overdue_capit_1) as ovd3, sum(f.t3_should_capit_1) as shd3,
  sum(f.t7_overdue_capit_1) as ovd7, sum(f.t7_should_capit_1) as shd7
from mx.wxs_application_funnel f
where f.is_reloan='new' and f.tenant='yawey'
  and date(f.release_time) between date '2026-07-01' and date '2026-09-30'
group by 1 order by 1
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r)
    r["w"] = r["w"].astype(str).str[:10]
    r["1t0本金%"] = (r.ovd0/r.shd0*100).round(2)
    r["1t3本金%"] = (r.ovd3/r.shd3*100).round(2)
    r["1t7本金%"] = (r.ovd7/r.shd7*100).round(2)
    res["首贷按放款周"] = r
    print(r[["w","issue_cnt","1t0本金%","1t3本金%","1t7本金%"]].to_string(index=False))

with open(os.path.join(OUT, "_probe_issue_week.pkl"), "wb") as f:
    pickle.dump(res, f)
print("\n\n保存完成: _probe_issue_week.pkl")
