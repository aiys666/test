# -*- coding: utf-8 -*-
"""样例笔 1620000465328686 历史临额占用下钻:
   1) C010 事件(名义400/存量占用306.25?)
   2) 同账户 C010 前 TEMP 台账, 按来源biz拆 resid=Σ冻结-Σ解冻
   3) 各来源biz结清状态(as of C010时刻) -> 结清后占用 vs 未结清占用
"""
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

BIZ = "1620000465328686"

# 1) 本笔 C010 事件
q(f"""
select mid, limit_main_id, external_id, create_time,
       change_total_grantamount as nominal, change_used_grantamount as stock_occ,
       change_total_grantamount - change_used_grantamount as net_arrive,
       change_event_type, change_desc
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP' and change_event_type='C010' and external_id='{BIZ}'
""", "1 本笔C010事件")

# 2) 同账户 C010 时刻前的 TEMP 台账, 按来源 biz 聚合
q(f"""
with c010 as (
  select limit_main_id, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type='C010' and external_id='{BIZ}'
)
select u.biz_id as src_biz,
  sum(case when u.change_action='FREEZE_LIMIT'   then u.risk_credit_limit else 0 end) as frz,
  sum(case when u.change_action='UNFREEZE_LIMIT' then u.risk_credit_limit else 0 end) as unfr,
  sum(case when u.change_action='FREEZE_LIMIT'   then u.risk_credit_limit else 0 end)
- sum(case when u.change_action='UNFREEZE_LIMIT' then u.risk_credit_limit else 0 end) as resid,
  min(u.create_time) as first_t, max(u.create_time) as last_t, count(*) as evt_cnt
from ods.s05_user_creditlimit_used_detail u
join c010 on u.limit_main_id = c010.limit_main_id
where u.limit_type='TEMP' and u.create_time < c010.create_time
group by u.biz_id
having sum(case when u.change_action='FREEZE_LIMIT'   then u.risk_credit_limit else 0 end)
     - sum(case when u.change_action='UNFREEZE_LIMIT' then u.risk_credit_limit else 0 end) > 0.01
order by resid desc
""", "2 C010前存量占用按来源biz拆分")

# 3) 台账逐事件明细(全量看时间序)
q(f"""
with c010 as (
  select limit_main_id, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type='C010' and external_id='{BIZ}'
)
select u.biz_id as src_biz, u.change_action, u.change_event_type, u.risk_credit_limit, u.create_time
from ods.s05_user_creditlimit_used_detail u
join c010 on u.limit_main_id = c010.limit_main_id
where u.limit_type='TEMP' and u.create_time < c010.create_time
order by u.create_time
""", "3 C010前TEMP台账逐事件明细")

# 4) 各来源biz结清状态(as of C010时刻)
q(f"""
with c010 as (
  select limit_main_id, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type='C010' and external_id='{BIZ}'
),
src as (
  select distinct cast(u.biz_id as bigint) as biz
  from ods.s05_user_creditlimit_used_detail u
  join c010 on u.limit_main_id = c010.limit_main_id
  where u.limit_type='TEMP' and u.create_time < c010.create_time
)
select s.biz,
  max(r.indexs) as nper,
  max(case when r.state<>1 then 1 else 0 end) as any_unpaid_now,
  max(r.fact_time) as last_pay_t,
  case when max(case when r.state<>1 then 1 else 0 end)=0
        and max(r.fact_time) < (select create_time from c010) then '结清后占用'
       else '未结清占用' end as occ_kind
from src s left join ods_view_presto.s02_loan_repayment r
  on cast(r.camera_id as bigint) = s.biz
group by s.biz
order by s.biz
""", "4 来源biz结清状态(as of C010)")

print("DONE-PROBE")
