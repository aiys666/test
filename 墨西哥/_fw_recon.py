# -*- coding: utf-8 -*-
"""对账: N4(1192/591) 与 F1(29) 的矛盾排查"""
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

BASE = """
with led as (
  select biz_id as biz,
    sum(case when change_action='FREEZE_LIMIT'   then risk_credit_limit else 0 end) as frz,
    sum(case when change_action='UNFREEZE_LIMIT' then risk_credit_limit else 0 end) as unfr
  from ods.s05_user_creditlimit_used_detail
  where limit_type='TEMP'
    and create_time >= timestamp'2026-07-01 00:00:00' and create_time < timestamp'2026-10-15 00:00:00'
  group by biz_id
),
rp0 as (
  select cast(camera_id as bigint) as biz, indexs, should_capital, fact_capital, fact_time, state
  from ods_view_presto.s02_loan_repayment
  where cast(camera_id as bigint) in (select biz from led)
),
rp as (
  select biz, sum(should_capital) as cap_tot, max(indexs) as nper,
    max(case when state<>1 then 1 else 0 end) as any_unpaid,
    count(*) as nrow,
    sum(case when state<>1 then 1 else 0 end) as n_unpaid,
    sum(case when state is null then 1 else 0 end) as n_null
  from rp0 group by biz
),
j as (
  select l.biz, l.frz, l.unfr, l.frz-l.unfr as resid, rp.cap_tot, rp.nper,
         rp.any_unpaid, rp.nrow, rp.n_unpaid, rp.n_null, rp.last_pay_t
  from led l join rp on l.biz = rp.biz
)
"""
BASE = BASE.replace("rp.last_pay_t", "cast(null as timestamp) as x_last_pay_t_placeholder, rp.null")  # 占位, 下面重写

BASE = """
with led as (
  select biz_id as biz,
    sum(case when change_action='FREEZE_LIMIT'   then risk_credit_limit else 0 end) as frz,
    sum(case when change_action='UNFREEZE_LIMIT' then risk_credit_limit else 0 end) as unfr
  from ods.s05_user_creditlimit_used_detail
  where limit_type='TEMP'
    and create_time >= timestamp'2026-07-01 00:00:00' and create_time < timestamp'2026-10-15 00:00:00'
  group by biz_id
),
rp0 as (
  select cast(camera_id as bigint) as biz, indexs, should_capital, fact_capital, fact_time, state
  from ods_view_presto.s02_loan_repayment
  where cast(camera_id as bigint) in (select biz from led)
),
rp as (
  select biz, sum(should_capital) as cap_tot, max(indexs) as nper,
    max(case when state<>1 then 1 else 0 end) as any_unpaid,
    count(*) as nrow,
    max(fact_time) as last_pay_t
  from rp0 group by biz
),
j as (
  select l.biz, l.frz, l.unfr, l.frz-l.unfr as resid, rp.cap_tot, rp.nper,
         rp.any_unpaid, rp.nrow, rp.last_pay_t
  from led l join rp on l.biz = rp.biz
)
"""

q(BASE + """
select
  sum(case when any_unpaid=0 and resid>0.01 then 1 else 0 end) as settled_resid_any,
  sum(case when any_unpaid=0 and resid>1 then 1 else 0 end) as settled_resid_gt1,
  sum(case when any_unpaid=0 and resid>0.01 and date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') >= 7 then 1 else 0 end) as settled_any_age7,
  sum(case when any_unpaid=0 and resid>1 and date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') >= 7 then 1 else 0 end) as settled_gt1_age7,
  sum(case when any_unpaid=0 and resid>1 and date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') >= 30 then 1 else 0 end) as settled_gt1_age30,
  round(sum(case when any_unpaid=0 and resid>1 then resid else 0 end),1) as settled_gt1_amt,
  round(sum(case when any_unpaid=0 and resid>1 and date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') >= 7 then resid else 0 end),1) as settled_gt1_age7_amt
from j
""", "R1 对账: 结清残留 各种口径计数")

q(BASE + """
select biz, round(frz,1) as frz, round(unfr,1) as unfr, round(resid,1) as residue, nper, nrow,
  last_pay_t, date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') as age_days
from j where any_unpaid=0 and resid>1
order by residue desc limit 25
""", "R2 结清残留>1 明细 Top25")

q(BASE + """
select case when date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') < 0 then '0 负(当日)'
            when date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') <= 1 then '1'
            when date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') <= 3 then '2-3'
            when date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') <= 7 then '4-7'
            when date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') <= 30 then '8-30'
            else '>30' end as age_b,
  count(*) as cnt, round(sum(resid),1) as resid_amt
from j where any_unpaid=0 and resid>1
group by 1 order by 1
""", "R3 结清残留>1 账龄分布")

print("DONE-RECON")
