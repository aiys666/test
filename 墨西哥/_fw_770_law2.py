# -*- coding: utf-8 -*-
"""770.4 定律候选公式穷举 + 异常集画像"""
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
    and create_time >= timestamp'2026-08-01 00:00:00' and create_time < timestamp'2026-10-08 00:00:00'
  group by biz_id
),
rp0 as (
  select cast(camera_id as bigint) as biz, indexs, should_capital, fact_capital, state
  from ods_view_presto.s02_loan_repayment
  where cast(camera_id as bigint) in (select biz from led)
),
rp as (
  select biz, sum(should_capital) as cap_tot, sum(fact_capital) as cap_paid,
    max(indexs) as nper,
    sum(case when indexs = mx then should_capital else 0 end) as cap_last,
    sum(case when indexs <  mx then should_capital else 0 end) as cap_nonlast
  from (select *, max(indexs) over (partition by biz) as mx from rp0) t
  group by biz
),
j as (
  select l.biz, l.frz, l.unfr, l.frz-l.unfr as resid,
    rp.cap_tot, rp.cap_paid, rp.nper, rp.cap_last, rp.cap_nonlast
  from led l join rp on l.biz = rp.biz
  where rp.cap_tot is not null
)
"""

# M1 候选公式穷举(仅已结清: 本金全还清)
q(BASE + """
select
  count(*) as settled_resid_biz,
  round(sum(resid),1) as resid_amt,
  sum(case when abs(resid - (frz - cap_last)) < 0.05 then 1 else 0 end) as f_frz_minus_last,
  sum(case when abs(resid - greatest(0, frz - cap_last)) < 0.05 then 1 else 0 end) as f_max0_frz_minus_last,
  sum(case when abs(resid - (cap_tot - cap_last)) < 0.05 then 1 else 0 end) as f_tot_minus_last,
  sum(case when abs(resid - cap_nonlast) < 0.05 then 1 else 0 end) as f_nonlast,
  sum(case when abs(resid - (frz - cap_paid)) < 0.05 then 1 else 0 end) as f_frz_minus_paid,
  sum(case when resid < 0.05 then 1 else 0 end) as f_zero,
  sum(case when nper = 2 then 1 else 0 end) as nper2
from j
where cap_paid >= cap_tot - 0.05 and resid > 0.01
""", "M1 已结清却仍占用: 7 个候选公式命中数(304 笔全集)")

# M2 已结清异常集明细(前 40 笔)
q(BASE + """
select biz, round(frz,1) as temp_freeze, round(unfr,1) as temp_unfreeze, round(resid,1) as residue,
  round(cap_tot,1) as cap_tot, round(cap_last,1) as cap_last, round(cap_paid,1) as cap_paid, nper
from j
where cap_paid >= cap_tot - 0.05 and resid > 0.01
order by resid desc limit 40
""", "M2 已结清却仍占用 明细 Top40")

# M3 对照组: 已结清且残留=0 的笔 (证明多数是正常释放的)
q(BASE + """
select
  count(*) as settled_clean_biz,
  sum(case when nper = 2 then 1 else 0 end) as nper2,
  round(sum(frz),1) as temp_freeze_amt
from j
where cap_paid >= cap_tot - 0.05 and resid <= 0.01
""", "M3 对照: 已结清且临额已完全释放的笔数")

# M4 异常集 vs 对照: 末期本金占合同比 分布(两期贷)
q(BASE + """
select
  case when resid > 0.01 then '异常(有残留)' else '正常(无残留)' end as grp,
  count(*) as biz_cnt,
  round(avg(cap_last/nullif(cap_tot,0))*100,1) as avg_last_share_pct,
  round(sum(resid),1) as resid_amt
from j
where cap_paid >= cap_tot - 0.05 and nper = 2
group by 1
""", "M4 异常 vs 正常: 末期本金占比 对比(两期贷)")

print("DONE-LAW2")
