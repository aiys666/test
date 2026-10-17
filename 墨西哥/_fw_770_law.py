# -*- coding: utf-8 -*-
"""770.4 定律3: 放宽台账窗口(截断假阳性) + 候选公式 + 异常集画像"""
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
    sum(case when change_action='UNFREEZE_LIMIT' then risk_credit_limit else 0 end) as unfr,
    min(create_time) as first_t, max(create_time) as last_t
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
  select biz, sum(should_capital) as cap_tot, sum(case when state=1 then fact_capital else 0 end) as cap_paid,
    max(indexs) as nper,
    sum(case when indexs = mx then should_capital else 0 end) as cap_last,
    sum(case when indexs <  mx then should_capital else 0 end) as cap_nonlast,
    max(fact_time) as last_pay_t,
    min(case when state<>1 then 1 else 0 end) as any_unpaid
  from (select *, max(indexs) over (partition by biz) as mx from rp0) t
  group by biz
),
j as (
  select l.biz, l.frz, l.unfr, l.frz-l.unfr as resid, l.first_t, l.last_t,
    rp.cap_tot, rp.cap_paid, rp.nper, rp.cap_last, rp.cap_nonlast, rp.last_pay_t, rp.any_unpaid
  from led l join rp on l.biz = rp.biz
)
"""

# N1 全量: 残留 biz 按"是否真实结清"分类(结清=每期state=1)
q(BASE + """
select
  case when any_unpaid = 0 then 'A已全部结清' else 'B未结清' end as bucket,
  count(*) as biz_cnt, round(sum(resid),1) as resid_amt,
  round(sum(cap_tot),1) as cap_tot_amt,
  max(last_pay_t) as max_lastpay
from j
where resid > 0.01
group by 1 order by 1
""", "N1 残留 biz 按真实结清状态分类(窗口 07-01~10-14)")

# N2 已结清异常集: 候选公式命中
q(BASE + """
select count(*) as settled_resid_biz, round(sum(resid),1) as resid_amt,
  sum(case when abs(resid - (frz - cap_last)) < 0.05 then 1 else 0 end) as f_frz_minus_last,
  sum(case when abs(resid - (frz - cap_paid)) < 0.05 then 1 else 0 end) as f_frz_minus_paid,
  sum(case when abs(resid - (cap_tot - cap_last)) < 0.05 then 1 else 0 end) as f_tot_minus_last,
  sum(case when abs(resid - cap_nonlast) < 0.05 then 1 else 0 end) as f_nonlast,
  sum(case when abs(resid - frz) < 0.05 then 1 else 0 end) as f_never_released,
  sum(case when nper = 1 then 1 else 0 end) as nper1,
  sum(case when nper = 2 then 1 else 0 end) as nper2
from j where any_unpaid = 0 and resid > 0.01
""", "N2 已结清仍占用: 候选公式命中数")

# N3 已结清异常集明细 Top30
q(BASE + """
select biz, round(frz,1) as temp_freeze, round(unfr,1) as temp_unfrz, round(resid,1) as residue,
  round(cap_tot,1) as cap_tot, round(cap_last,1) as cap_last, nper,
  last_pay_t, date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') as age_days
from j where any_unpaid = 0 and resid > 0.01
order by resid desc limit 30
""", "N3 已结清仍占用 明细 Top30(含挂账天数)")

# N4 账龄分布
q(BASE + """
select case when date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') > 180 then '>180天'
             when date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') > 90 then '91-180天'
             when date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') > 30 then '31-90天'
             else '<=30天' end as age_bucket,
  count(*) as biz_cnt, round(sum(resid),1) as resid_amt
from j where any_unpaid = 0 and resid > 0.01
group by 1 order by 2 desc
""", "N4 已结清仍占用 挂账账龄分布")

print("DONE-LAW3")
