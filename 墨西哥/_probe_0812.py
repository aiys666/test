# -*- coding: utf-8 -*-
"""0812 跳升定位：逐日曲线 + 产品/评级拆解"""
import sys, io, os, time
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
        if c not in ('d','dim'): df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# 1) 全量复贷老客，按进件天逐日 1t0本金% + 量
sql1 = """
select date(f.app_time) as d,
  sum(f.if_app) as app_cnt,
  sum(f.if_issue) as issue_cnt,
  sum(f.contract_amount) as contract_amount,
  sum(f.t0_overdue_capit_1) as t0_overdue_capit_1,
  sum(f.t0_should_capit_1) as t0_should_capit_1,
  sum(f.t3_overdue_capit_1) as t3_overdue_capit_1,
  sum(f.t3_should_capit_1) as t3_should_capit_1,
  sum(f.t7_overdue_capit_1) as t7_overdue_capit_1,
  sum(f.t7_should_capit_1) as t7_should_capit_1,
  sum(f.t0_overdue_capit_4) as t0_overdue_capit_4,
  sum(f.t0_should_capit_4) as t0_should_capit_4
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.create_time) >= date '2026-06-29'
group by 1 order by 1
"""
r = q(sql1)
if isinstance(r, str):
    print("[FAIL sql1]", r[:300]); 
else:
    r = _num(r)
    r["1t0本金%"] = (r.t0_overdue_capit_1 / r.t0_should_capit_1 * 100).round(2)
    r["1t3本金%"] = (r.t3_overdue_capit_1 / r.t3_should_capit_1 * 100).round(2)
    r["1t7本金%"] = (r.t7_overdue_capit_1 / r.t7_should_capit_1 * 100).round(2)
    r["4t0本金%"] = (r.t0_overdue_capit_4 / r.t0_should_capit_4 * 100).round(2)
    r.to_pickle(os.path.join(OUT, "_probe_daily_1t0.pkl"))
    print("="*100)
    print("全量复贷 · 按进件天 · 1t0本金% 曲线")
    print(r[["d","app_cnt","issue_cnt","contract_amount","1t0本金%","1t3本金%","1t7本金%","4t0本金%"]].to_string(index=False))
    print("="*100)
    # 重点看 8/8~8/16
    sub = r[(r.d >= pd.Timestamp("2026-08-08")) & (r.d <= pd.Timestamp("2026-08-16"))]
    print("8/8~8/16 放大:")
    print(sub[["d","app_cnt","issue_cnt","1t0本金%","1t3本金%","1t7本金%","4t0本金%"]].to_string(index=False))
