# -*- coding: utf-8 -*-
"""根因深挖 v3：验证'新鲜血液'假设——8/10后涌入的首复贷客户，其首贷质量是否变差"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()

def q(sql, retry=4):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r):
            print(f"  [重登{i+1}]"); pq.login(); continue
        return r
    raise SystemExit(f"[失败] {r}")

def _num(df, keep=('w','rn_g','ag')):
    for c in df.columns:
        if c not in keep: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# ===== 1. 首复贷客户(reloan_num=2)的首贷坏账质量 =====
print("="*120)
print("【1】首复贷(reloan_num=2)客群 → 其首贷(reloan_num=1)的1t0坏账率（按复贷放款周）")
sql1 = """
with first as (
  select cust_id, t0_overdue_capit_1 as fovd, t0_should_capit_1 as fshd
  from mx.wxs_application_funnel
  where tenant='yawey' and if_issue=1 and reloan_num=1
)
select date_trunc('week', date(f.release_time)) as w,
  count(*) as cnt,
  sum(f.t0_should_capit_1) as shd, sum(f.t0_overdue_capit_1) as ovd,
  sum(fl.fshd) as fshd, sum(fl.fovd) as fovd
from mx.wxs_application_funnel f
join first fl on f.cust_id=fl.cust_id
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1 and f.reloan_num=2
  and date(f.release_time) between date '2026-08-03' and date '2026-08-30'
group by 1 order by 1
"""
r = q(sql1)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["本次复贷率%"] = (r.ovd/r.shd*100).round(1)
    r["其首贷率%"] = (r.fovd/r.fshd*100).round(1)
    print(r[["w","cnt","本次复贷率%","其首贷率%"]].to_string(index=False))

# ===== 2. 首复贷客户的首贷放款时间分布（验证是否'新鲜血液'） =====
print("\n" + "="*120)
print("【2】8/10周新增首复贷(reloan_num=2)客户，其首贷(reloan_num=1)放款周分布")
sql2 = """
with first as (
  select cust_id, date_trunc('week', date(release_time)) as fw
  from mx.wxs_application_funnel
  where tenant='yawey' and if_issue=1 and reloan_num=1
)
select cast(fl.fw as varchar) as fw, count(*) as cnt
from mx.wxs_application_funnel f
join first fl on f.cust_id=fl.cust_id
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1 and f.reloan_num=2
  and date(f.release_time) between date '2026-08-10' and date '2026-08-16'
group by 1 order by 1
"""
r = q(sql2)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r)
    print(r.to_string(index=False))

# ===== 3. 首复贷客户首贷时的评级分布（6-12级占比） =====
print("\n" + "="*120)
print("【3】首复贷(reloan_num=2)客群首贷评级6-12级占比（按复贷放款周）")
sql3 = """
with first as (
  select y.biz_id, try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as integer) as gl
  from (select biz_id, android_oldcust_maincreditlevel_charge_v5_3,
          ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
        from mx.yj_test_table_250225) y
  where y.rn=1
)
select date_trunc('week', date(f.release_time)) as w,
  count(*) as cnt,
  sum(case when fl.gl>=6 and fl.gl<=12 then 1 else 0 end) as low_cnt
from mx.wxs_application_funnel f
join first fl on f.biz_id=fl.biz_id
where f.is_reloan='old' and f.tenant='yawey' and f.if_issue=1 and f.reloan_num=2
  and date(f.release_time) between date '2026-08-03' and date '2026-08-30'
group by 1 order by 1
"""
r = q(sql3)
if isinstance(r, str): print("[FAIL]", r[:400])
else:
    r = _num(r); r["w"] = r["w"].astype(str).str[:10]
    r["6-12级占比%"] = (r.low_cnt/r.cnt*100).round(1)
    print(r[["w","cnt","low_cnt","6-12级占比%"]].to_string(index=False))

print("\n\n完成")
