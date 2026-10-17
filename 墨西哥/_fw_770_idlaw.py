# -*- coding: utf-8 -*-
"""定律化: 对全量 C010 验证 (名义发放额 - 存量占用) = 该笔真实到账临额(used_detail TEMP冻结额)"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 620)

def q(sql, tag):
    print("=" * 116); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]\n", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:250]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}\n"); return None

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: print("[login retry]"); time.sleep(8)

# L1 全量定律: (C010.tot - C010.used) 是否 = used_detail 该 biz 的 TEMP 冻结额
q("""
with c as (
  select cast(external_id as bigint) as biz, change_total_grantamount as tot,
         change_used_grantamount as used, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type='C010'
    and create_time >= timestamp'2026-07-01 00:00:00' and create_time < timestamp'2026-10-15 00:00:00'
    and external_id is not null and external_id <> ''
),
u as (
  select biz_id, sum(risk_credit_limit) as frz
  from ods.s05_user_creditlimit_used_detail
  where limit_type='TEMP' and change_action='FREEZE_LIMIT'
    and create_time >= timestamp'2026-07-01 00:00:00' and create_time < timestamp'2026-10-15 00:00:00'
  group by biz_id
)
select count(*) as c010_with_biz,
  count(u.biz_id) as matched_freeze_biz,
  sum(case when u.frz is not null and abs((c.tot-c.used) - u.frz) < 0.1 then 1 else 0 end) as law_hit,
  round(100.0*sum(case when u.frz is not null and abs((c.tot-c.used) - u.frz) < 0.1 then 1 else 0 end)/count(*),2) as hit_pct
from c left join u on c.biz = u.biz_id
""", "L1 全量定律: 净可用(C010) = 名义发放 - 存量占用 ?= 该笔实到账临额")

# L2 命中率按"是否被抵扣"分层
q("""
with c as (
  select cast(external_id as bigint) as biz, change_total_grantamount as tot,
         change_used_grantamount as used
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type='C010'
    and create_time >= timestamp'2026-07-01 00:00:00' and create_time < timestamp'2026-10-15 00:00:00'
    and external_id is not null and external_id <> ''
),
u as (
  select biz_id, sum(risk_credit_limit) as frz
  from ods.s05_user_creditlimit_used_detail
  where limit_type='TEMP' and change_action='FREEZE_LIMIT'
    and create_time >= timestamp'2026-07-01 00:00:00' and create_time < timestamp'2026-10-15 00:00:00'
  group by biz_id
)
select case when c.used > 0.01 then 'A 有存量占用' else 'B 无存量占用' end as grp,
  count(*) as n,
  sum(case when u.frz is not null and abs((c.tot-c.used)-u.frz) < 0.1 then 1 else 0 end) as hit,
  round(100.0*sum(case when u.frz is not null and abs((c.tot-c.used)-u.frz) < 0.1 then 1 else 0 end)/count(*),2) as hit_pct
from c left join u on c.biz = u.biz_id
group by 1 order by 1
""", "L2 定律命中率 分层(A被抵扣 vs B无抵扣)")

# L3 失配样例(看原因)
q("""
with c as (
  select cast(external_id as bigint) as biz, change_total_grantamount as tot,
         change_used_grantamount as used, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type='C010'
    and create_time >= timestamp'2026-07-01 00:00:00' and create_time < timestamp'2026-10-15 00:00:00'
    and external_id is not null and external_id <> ''
),
u as (
  select biz_id, sum(risk_credit_limit) as frz
  from ods.s05_user_creditlimit_used_detail
  where limit_type='TEMP' and change_action='FREEZE_LIMIT'
    and create_time >= timestamp'2026-07-01 00:00:00' and create_time < timestamp'2026-10-15 00:00:00'
  group by biz_id
)
select c.biz, c.create_time, round(c.tot,1) as grant, round(c.used,1) as occupied,
  round(c.tot-c.used,1) as net_avail, round(u.frz,1) as real_freeze,
  round((c.tot-c.used) - coalesce(u.frz,0),1) as diff
from c left join u on c.biz=u.biz_id
where u.frz is null or abs((c.tot-c.used)-u.frz) >= 0.1
order by abs((c.tot-c.used) - coalesce(u.frz,0)) desc limit 20
""", "L3 失配样例 Top20(定位失配原因)")

print("DONE-IDLAW")
