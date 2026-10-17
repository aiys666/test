# -*- coding: utf-8 -*-
"""FINAL: (F) 残留公式终验(排除当日延迟噪声)  (I) 全量影响面量化"""
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
  select biz, sum(should_capital) as cap_tot,
    max(indexs) as nper,
    sum(case when indexs = mx then should_capital else 0 end) as cap_last,
    sum(case when indexs <  mx then should_capital else 0 end) as cap_nonlast,
    max(fact_time) as last_pay_t,
    max(case when state<>1 then 1 else 0 end) as any_unpaid
  from (select *, max(indexs) over (partition by biz) as mx from rp0) t
  group by biz
),
j as (
  select l.biz, l.frz, l.unfr, l.frz-l.unfr as resid, rp.cap_tot, rp.nper,
         rp.cap_last, rp.cap_nonlast, rp.last_pay_t, rp.any_unpaid
  from led l join rp on l.biz = rp.biz
)
"""

# F1 稳态异常集(账龄>=7天, 排除当日解冻延迟): 公式命中
q(BASE + """
select count(*) as biz_cnt, round(sum(resid),1) as resid_amt,
  sum(case when abs(resid-(frz-cap_last)) < 0.05 then 1 else 0 end) as f_frz_minus_last,
  sum(case when abs(resid-greatest(0,frz-cap_last)) < 0.05 then 1 else 0 end) as f_max0,
  sum(case when abs(resid-(cap_tot-cap_last)) < 0.05 then 1 else 0 end) as f_tot_minus_last,
  sum(case when abs(resid-cap_nonlast) < 0.05 then 1 else 0 end) as f_nonlast,
  sum(case when abs(resid-frz) < 0.05 then 1 else 0 end) as f_unreleased,
  sum(case when resid > frz+0.05 then 1 else 0 end) as f_bigger_than_frz
from j where any_unpaid = 0 and resid > 0.01
  and date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') >= 7
""", "F1 稳态异常集(结清且账龄>=7天): 残留公式命中数")

# F2 稳态异常集明细 Top20
q(BASE + """
select biz, round(frz,1) as temp_freeze, round(unfr,1) as temp_unfrz, round(resid,1) as residue,
  round(cap_tot,1) as cap_tot, round(cap_last,1) as cap_last, round(cap_nonlast,1) as cap_nonlast,
  nper, date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') as age_days
from j where any_unpaid = 0 and resid > 0.01
  and date_diff('day', last_pay_t, timestamp'2026-10-14 00:00:00') >= 7
order by resid desc limit 20
""", "F2 稳态异常集明细 Top20")

# I1 C010 全量影响面(窗口 2026-07-01~10-14)
q("""
select
  count(*) as c010_cnt,
  count(distinct mid) as mid_cnt,
  sum(case when change_used_grantamount > 0.01 then 1 else 0 end) as occ_cnt,
  count(distinct case when change_used_grantamount > 0.01 then mid end) as occ_mid_cnt,
  round(sum(change_total_grantamount),1) as grant_amt,
  round(sum(change_used_grantamount),1) as occ_amt,
  round(sum(case when change_used_grantamount > 0.01 then change_used_grantamount else 0 end),1) as occ_amt_pos,
  round(sum(change_total_grantamount - change_used_grantamount),1) as net_amt
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP' and change_event_type='C010'
  and create_time >= timestamp'2026-07-01 00:00:00' and create_time < timestamp'2026-10-15 00:00:00'
""", "I1 C010 全量: 发放笔数/被存量占用抵扣笔数/金额")

# I2 抵扣占比分布 + 极端尾部
q("""
with c as (
  select change_total_grantamount as tot, change_used_grantamount as used
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type='C010'
    and create_time >= timestamp'2026-07-01 00:00:00' and create_time < timestamp'2026-10-15 00:00:00'
    and change_total_grantamount > 0
)
select
  case when used <= 0.01 then '0 无抵扣'
       when used/tot <= 0.10 then '1 (0,10%]'
       when used/tot <= 0.25 then '2 (10%,25%]'
       when used/tot <= 0.50 then '3 (25%,50%]'
       when used/tot <= 0.75 then '4 (50%,75%]'
       when used/tot <  0.99999 then '5 (75%,100%)'
       else '6 净可用≈0(全额被占)' end as bucket,
  count(*) as cnt, round(sum(used),1) as used_amt, round(sum(tot),1) as grant_amt
from c group by 1 order by 1
""", "I2 C010 存量占用/名义发放 占比分布")

print("DONE-FINAL")
