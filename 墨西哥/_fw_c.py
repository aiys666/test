# -*- coding: utf-8 -*-
"""额度分析框架 脚本C: 模块4 离线临额(底表批次 + 8/24政策验证 + 打标周度)"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd, os

for _i in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(12)
pd.set_option('display.max_columns', None); pd.set_option('display.width', 460)
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_data"
os.makedirs(OUT, exist_ok=True)

def q(sql, name, tag="", retry=8):
    print("="*120); print(tag or name)
    for i in range(retry):
        try:
            r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(10)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r)==0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]")
            r.to_csv(os.path.join(OUT, name+".csv"), index=False, encoding='utf-8-sig')
            return r
        print(f"[retry {i+1}] {r[:150]}"); time.sleep(10)
        try: pq.login()
        except Exception: pass
    return None

# ============ C1: 离线底表 批次发放统计 ============
q("""
select temp_limit_tag,
  date_format(min(temp_limit_issue_date),'%Y-%m-%d') as issue_from,
  date_format(max(temp_limit_issue_date),'%Y-%m-%d') as issue_to,
  count(distinct mid) as people,
  count(*) as rows_cnt,
  round(avg(temp_limit_issue_amount),0) as issue_amt_avg,
  round(sum(temp_limit_issue_amount)/1000.0,0) as issue_amt_sum_k,
  round(avg(curr_credit_level),2) as grade_avg,
  round(avg(curr_main_credit_limit),0) as main_limit_avg,
  round(avg(curr_main_used_credit_limit/curr_main_credit_limit)*100,1) as main_used_rate,
  round(avg(id_30days_max_overdue_days),2) as d30_max_ovd_avg,
  round(sum(if(id_30days_max_overdue_days<=0,1,0))*100.0/count(*),1) as pct_ovd0,
  round(sum(if(id_30days_max_overdue_days between 1 and 2,1,0))*100.0/count(*),1) as pct_ovd1_2,
  round(sum(if(id_30days_max_overdue_days>=3,1,0))*100.0/count(*),1) as pct_ovd3p
from mx.yuhan_temp_limit_base_table_his_20260924
where temp_limit_tag is not null
group by 1 order by 2
""", "C1_offline_batch", "C1 离线临额批次发放(评级/主额使用率/近30天逾期)")

# ============ C2: 离线打标 逐周 × 评级档 ============
for w0, w1, wn in [('2026-07-27','2026-08-04','w0727'), ('2026-08-04','2026-08-11','w0803'),
                    ('2026-08-11','2026-08-18','w0810'), ('2026-08-18','2026-08-25','w0817'),
                    ('2026-08-25','2026-09-01','w0824'), ('2026-09-01','2026-09-08','w0831'),
                    ('2026-09-08','2026-09-15','w0907')]:
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
      and e.limit_type='TEMP' and e.change_event_type in ('C013','C015')
  ) x
)
select '{wn}' as awk,
  case when cast(y.fd_creditlevel_main_v4_2 as double) >= 9 then 'g9p'
       when cast(y.fd_creditlevel_main_v4_2 as double) >= 6 then 'g6_8'
       when cast(y.fd_creditlevel_main_v4_2 as double) >= 1 then 'g1_5' else 'g_null' end as grade_grp,
  count(*) as offline_cnt,
  round(sum(if(y.t0_should_amt_1>0,y.t0_overdue_amount_1,null))
       /nullif(sum(if(y.t0_should_amt_1>0,y.t0_should_amt_1,null)),0)*100,2) as t0_rate,
  round(avg(y.real_issue_amount),0) as issue_avg,
  round(avg(y.credit_amount),0) as credit_avg,
  round(sum(y.real_issue_amount)/nullif(sum(y.credit_amount),0)*100,2) as tr_rate,
  round(avg(cast(y.curr_ovd_cnt_all as double)),2) as ovd_cnt_avg
from mx.yj_test_table_250225 y
join evt_last el on y.biz_id = el.biz_id and el.rn=1
where y.if_issue=1 and y.is_reloan='old'
  and y.app_date >= date'{w0}' and y.app_date < date'{w1}'
group by 2 order by 2
""", f"C2_offline_{wn}", f"C2 {wn} 离线临额×评级档")
