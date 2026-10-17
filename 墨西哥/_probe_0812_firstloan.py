# -*- coding: utf-8 -*-
"""用首贷表拆解 8/8~8/16 复贷客群的【首贷特征】：注册媒体来源/首贷日期分布/首贷等级
验证 8/11~8/14 脉冲是否是某一批首贷客群(投放/低等级/新客期)被集中复贷
"""
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

# 主查询：8/8~8/16 复贷进件，按天 x 首贷特征维度 聚合坏账
def run(dim_expr, dim_name, extra_join=""):
    sql = f"""
select date(f.app_time) as d, {dim_expr} as dim,
  sum(f.if_app) as app_cnt,
  sum(f.t0_overdue_capit_1) as t0_overdue_capit_1,
  sum(f.t0_should_capit_1) as t0_should_capit_1,
  sum(f.t3_overdue_capit_1) as t3_overdue_capit_1,
  sum(f.t3_should_capit_1) as t3_should_capit_1
from mx.wxs_application_funnel f
left join mx.ys_dl_ltv_first_loan_0511 fl on cast(f.cust_id as bigint) = fl.mid
{extra_join}
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.create_time) between date '2026-08-08' and date '2026-08-16'
group by 1, 2 order by 1, 2
"""
    r = q(sql)
    if isinstance(r, str):
        print(f"[FAIL] {dim_name}: {r[:300]}"); return None
    r = _num(r)
    r["1t0本金%"] = (r.t0_overdue_capit_1 / r.t0_should_capit_1 * 100).round(2)
    return r

dims = {
 "注册媒体来源": "coalesce(fl.register_media_source,'空')",
 "首贷等级": "coalesce(cast(fl.new_grade_level as varchar),'空')",
 "首贷金额档": "case when fl.contract_amount<=500 then '首贷小金额(<=500)' when fl.contract_amount>500 then '首贷非小金额(>500)' else '空' end",
 "首贷月份": "coalesce(cast(fl.ltv_month as varchar),'空')",
 "首贷期限": "coalesce(cast(fl.loan_cycle as varchar),'空')",
}

results = {}
for name, expr in dims.items():
    r = run(expr, name)
    if r is None: continue
    results[name] = r
    p = r.pivot_table(index="dim", columns="d", values="1t0本金%", aggfunc="mean")
    print("\n" + "="*110)
    print(f"【首贷·{name}】 1t0本金% 逐日")
    print(p.to_string())
    qq = r.pivot_table(index="dim", columns="d", values="app_cnt", aggfunc="sum")
    print(f"\n【首贷·{name}】 进件笔数 逐日")
    print(qq.to_string())

import pickle
with open(os.path.join(OUT, "_probe_0812_firstloan.pkl"), "wb") as f:
    pickle.dump(results, f)
print("\n\n保存完成: _probe_0812_firstloan.pkl")
