# -*- coding: utf-8 -*-
"""3月队列(含 770.4 案例): 结清后临额残留的真实规模 + 残留公式验证"""
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

def cohort(m0, m1, tag):
    return q("""
with seed as (
  select distinct biz_id as biz
  from ods.s05_user_creditlimit_used_detail
  where limit_type='TEMP'
    and create_time >= timestamp'%s' and create_time < timestamp'%s'
),
led as (
  select biz_id as biz,
    sum(case when change_action='FREEZE_LIMIT'   then risk_credit_limit else 0 end) as frz,
    sum(case when change_action='UNFREEZE_LIMIT' then risk_credit_limit else 0 end) as unfr
  from ods.s05_user_creditlimit_used_detail
  where limit_type='TEMP' and biz_id in (select biz from seed)
  group by biz_id
),
rp0 as (
  select cast(camera_id as bigint) as biz, indexs, should_capital, fact_time, state
  from ods_view_presto.s02_loan_repayment
  where cast(camera_id as bigint) in (select biz from seed)
),
rp as (
  select biz, sum(should_capital) as cap_tot, max(indexs) as nper,
    sum(case when indexs = mx then should_capital else 0 end) as cap_last,
    sum(case when indexs <  mx then should_capital else 0 end) as cap_nonlast,
    max(case when state<>1 then 1 else 0 end) as any_unpaid,
    max(fact_time) as last_pay_t
  from (select *, max(indexs) over (partition by biz) as mx from rp0) t
  group by biz
),
j as (
  select l.biz, l.frz, l.unfr, l.frz-l.unfr as resid, rp.cap_tot, rp.nper,
         rp.cap_last, rp.cap_nonlast, rp.any_unpaid, rp.last_pay_t
  from led l join rp on l.biz = rp.biz
)
select
  count(*) as settled_biz,
  count(case when resid > 0.01 then 1 end) as settled_resid_biz,
  round(sum(case when resid > 0.01 then resid else 0 end),1) as resid_amt,
  count(case when resid > 0.01 and abs(resid-(frz-cap_last)) < 0.05 then 1 end) as f_frz_minus_last,
  count(case when resid > 0.01 and abs(resid-(frz-cap_nonlast)) < 0.05 then 1 end) as f_frz_minus_nonlast,
  count(case when resid > 0.01 and abs(resid-frz) < 0.05 then 1 end) as f_unreleased,
  count(case when resid > 0.01 and abs(resid-(cap_tot-cap_last)) < 0.05 then 1 end) as f_tot_minus_last,
  count(case when resid > 0.01 and nper=2 then 1 end) as nper2,
  round(sum(case when resid > 0.01 then frz else 0 end),1) as frz_amt
from j where any_unpaid = 0
""" % (m0, m1), tag)

cohort('2026-03-01 00:00:00', '2026-04-01 00:00:00', "C-MAR 3月队列: 结清后临额残留规模 + 公式命中")
cohort('2026-02-01 00:00:00', '2026-03-01 00:00:00', "C-FEB 2月队列")
cohort('2026-06-01 00:00:00', '2026-07-01 00:00:00', "C-JUN 6月队列")

q("""
with seed as (
  select distinct biz_id as biz
  from ods.s05_user_creditlimit_used_detail
  where limit_type='TEMP' and create_time >= timestamp'2026-03-01 00:00:00' and create_time < timestamp'2026-04-01 00:00:00'
),
led as (
  select biz_id as biz,
    sum(case when change_action='FREEZE_LIMIT'   then risk_credit_limit else 0 end) as frz,
    sum(case when change_action='UNFREEZE_LIMIT' then risk_credit_limit else 0 end) as unfr
  from ods.s05_user_creditlimit_used_detail
  where limit_type='TEMP' and biz_id in (select biz from seed)
  group by biz_id
),
rp0 as (
  select cast(camera_id as bigint) as biz, indexs, should_capital, fact_time, state
  from ods_view_presto.s02_loan_repayment
  where cast(camera_id as bigint) in (select biz from seed)
),
rp as (
  select biz, sum(should_capital) as cap_tot, max(indexs) as nper,
    sum(case when indexs = mx then should_capital else 0 end) as cap_last,
    max(case when state<>1 then 1 else 0 end) as any_unpaid, max(fact_time) as last_pay_t
  from (select *, max(indexs) over (partition by biz) as mx from rp0) t
  group by biz
)
select l.biz, round(l.frz,1) as frz, round(l.unfr,1) as unfr, round(l.frz-l.unfr,1) as residue,
  nper, round(cap_tot,1) as cap_tot, round(cap_last,1) as cap_last, last_pay_t
from led l join rp on l.biz=rp.biz
where any_unpaid=0 and l.frz-l.unfr > 0.01
order by l.frz-l.unfr desc limit 25
""", "C-MAR-D 3月结清残留明细 Top25")

print("DONE-MAR")
