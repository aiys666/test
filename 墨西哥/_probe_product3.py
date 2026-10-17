# -*- coding: utf-8 -*-
"""最后查证：funnel表产品标识字段哪些有值 + loan_indexs语义 + 45天产品"""
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

# 1) funnel 表产品相关字段非空统计
print("="*100)
print("【1】funnel 表产品相关字段 非空/取值统计（8月复贷放款）")
sql1 = """
select
  count(*) as total,
  count(product_name) as c_product_name,
  count(product_type) as c_product_type,
  count(product_day) as c_product_day,
  count(product_level) as c_product_level,
  count(loan_indexs) as c_loan_indexs,
  count(app_group) as c_app_group,
  count(source) as c_source,
  count(apply_period) as c_apply_period,
  count(grant_strategy) as c_grant_strategy,
  count(grant_score) as c_grant_score,
  count(risk_level) as c_risk_level,
  count(reloan_num) as c_reloan_num,
  count(channel_category) as c_channel_category
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.release_time) between date '2026-08-01' and date '2026-08-31'
"""
r = q(sql1)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    print(r.to_string(index=False))

# 2) loan_indexs 与 loan_cycle / apply_period 关系
print("\n" + "="*100)
print("【2】loan_indexs 唯一值数 + 与 loan_cycle 对应")
sql2 = """
select cast(f.loan_cycle as varchar) as lc,
       cast(f.apply_period as varchar) as ap,
       count(distinct f.loan_indexs) as n_index,
       min(f.loan_indexs) as min_idx, max(f.loan_indexs) as max_idx,
       sum(f.if_issue) as issue_cnt
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.release_time) between date '2026-08-01' and date '2026-08-31'
group by 1,2 order by 5 desc
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r)
    print(r.to_string(index=False))

# 3) 45天产品 时间线（何时消失）
print("\n" + "="*100)
print("【3】loan_cycle=45 产品 放款量 按周")
sql3 = """
select date_trunc('week', date(f.release_time)) as w,
  sum(f.if_issue) as issue_cnt,
  sum(f.t0_overdue_capit_1) as ovd, sum(f.t0_should_capit_1) as shd
from mx.wxs_application_funnel f
where f.is_reloan='old' and f.tenant='yawey' and f.loan_cycle=45
  and date(f.release_time) between date '2026-06-01' and date '2026-09-30'
group by 1 order by 1
"""
r = q(sql3)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    r = _num(r)
    r["w"] = r["w"].astype(str).str[:10]
    r["1t0本金%"] = (r.ovd/r.shd*100).round(2)
    print(r.to_string(index=False))

# 4) 产品名JOIN为何NULL：funnel.biz_id 能否命中 yj 表
print("\n" + "="*100)
print("【4】funnel.biz_id 命中 yj 表 且 product_name_new 非空 的比例")
sql4 = """
select count(*) as total,
       count(y.biz_id) as joined,
       count(case when y.product_name_new is not null and y.product_name_new<>'' then 1 end) as has_pname
from mx.wxs_application_funnel f
left join (
  SELECT biz_id, product_name_new,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id AND y.rn = 1
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.release_time) between date '2026-08-01' and date '2026-08-31'
"""
r = q(sql4)
if isinstance(r, str): print("[FAIL]", r[:300])
else:
    print(r.to_string(index=False))

print("\n\n完成")
