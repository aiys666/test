# -*- coding: utf-8 -*-
"""额度框架 F: 修正版临额四组打标(与历史_probe_offline_weekly一致: 最后一条TEMP事件定组)
逐周 × 四组 × 评级档, 单查询/周; 另加w0810口径诊断"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd, os

for _i in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception:
        print("[login retry]", flush=True); time.sleep(12)
pd.set_option('display.max_columns', None); pd.set_option('display.width', 460)
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_data"
os.makedirs(OUT, exist_ok=True)

def q(sql, name, tag="", retry=8):
    print("="*120); print(tag or name, flush=True)
    for i in range(retry):
        try:
            r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]", flush=True); time.sleep(10)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r)==0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True)
            r.to_csv(os.path.join(OUT, name+".csv"), index=False, encoding='utf-8-sig')
            return r
        print(f"[retry {i+1}] {r[:150]}", flush=True); time.sleep(10)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {name}", flush=True)
    return None

WEEKS = [('2026-07-27','2026-08-04','w0727'), ('2026-08-04','2026-08-11','w0803'),
         ('2026-08-11','2026-08-18','w0810'), ('2026-08-18','2026-08-25','w0817'),
         ('2026-08-25','2026-09-01','w0824'), ('2026-09-01','2026-09-08','w0831'),
         ('2026-09-08','2026-09-15','w0907'), ('2026-09-15','2026-09-22','w0914')]

# F0: w0810 口径诊断 —— 总放款 / 任意C010 / 任意C013-15 / 最后事件类型
q("""
with ev as (
  select y.biz_id, e.change_event_type, e.create_time,
    row_number() over (partition by y.biz_id order by e.create_time desc) rn
  from mx.yj_test_table_250225 y
  join ods_view_presto.s05_user_creditlimit_change_record e
    on y.mid = e.mid and e.create_time <= y.release_time
  where y.if_issue=1 and y.is_reloan='old'
    and y.app_date >= date'2026-08-11' and y.app_date < date'2026-08-18'
    and e.limit_type='TEMP' and e.change_event_type in ('C010','C013','C015')
),
agg as (
  select biz_id,
    max(if(change_event_type='C010',1,0)) has_c010,
    max(if(change_event_type in ('C013','C015'),1,0)) has_off,
    max(if(rn=1, change_event_type, null)) last_evt
  from ev group by 1
)
select
  (select count(*) from mx.yj_test_table_250225
    where if_issue=1 and is_reloan='old'
      and app_date >= date'2026-08-11' and app_date < date'2026-08-18') as total_loan,
  count(*) as has_any_temp,
  sum(has_c010) as any_c010,
  sum(has_off) as any_offline,
  sum(if(last_evt='C010',1,0)) as last_c010,
  sum(if(last_evt in ('C013','C015'),1,0)) as last_offline
from agg
""", "F0_w0810_diag", "F0 w0810 打标口径诊断")

# F1-F8: 逐周 四组×评级档 (最后一条TEMP事件定组)
for w0, w1, wn in WEEKS:
    q(f"""
with evt_last as (
  select biz_id, change_event_type,
    row_number() over (partition by biz_id order by create_time desc) as rn
  from (
    select y.biz_id, e.change_event_type, e.create_time
    from mx.yj_test_table_250225 y
    join ods_view_presto.s05_user_creditlimit_change_record e
      on y.mid = e.mid and e.create_time <= y.release_time
    where y.if_issue=1 and y.is_reloan='old'
      and y.app_date >= date'{w0}' and y.app_date < date'{w1}'
      and e.limit_type='TEMP' and e.change_event_type in ('C010','C013','C015')
  ) x
)
select '{wn}' as awk,
  case when el.change_event_type in ('C013','C015') then 'offline'
       when el.change_event_type = 'C010' then
         case when y.temp_credit_amount_issue_tag=1 then 'online_tag1' else 'online_tag0' end
       else 'none' end as tl_grp,
  case when cast(y.fd_creditlevel_main_v4_2 as double) >= 9 then 'g9p'
       when cast(y.fd_creditlevel_main_v4_2 as double) >= 6 then 'g6_8'
       when cast(y.fd_creditlevel_main_v4_2 as double) >= 1 then 'g1_5'
       else 'g_null' end as grade_grp,
  count(*) as loan_cnt,
  round(sum(if(y.t0_should_amt_1>0,y.t0_overdue_amount_1,null))
       /nullif(sum(if(y.t0_should_amt_1>0,y.t0_should_amt_1,null)),0)*100,2) as t0_rate,
  round(avg(y.real_issue_amount),0) as issue_avg,
  round(sum(y.real_issue_amount)/1000.0,0) as issue_sum_k,
  round(avg(y.credit_amount),0) as credit_avg,
  round(sum(y.real_issue_amount)/nullif(sum(y.credit_amount),0)*100,2) as tr_rate,
  round(avg(cast(y.curr_ovd_cnt_all as double)),2) as ovd_cnt_avg
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
where y.if_issue=1 and y.is_reloan='old'
  and y.app_date >= date'{w0}' and y.app_date < date'{w1}'
group by 2,3 order by 2,3
""", f"F1_grp_{wn}", f"F {wn} 四组×评级档")

print("F DONE", flush=True)
