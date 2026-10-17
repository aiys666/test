# -*- coding: utf-8 -*-
"""E系列交叉表 (迭代): 评分×四组 / 评分×阶段 / type×临额使用 / 评分分布漂移
所有SQL自包含(宏展开), 便于复跑; yj窗口 8/14-10/09"""
import sys, io, time, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

for _i in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception:
        print("[login retry]", flush=True); time.sleep(12)
pd.set_option('display.max_columns', None); pd.set_option('display.width', 460)
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_data"

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
            if r is None or len(r)==0: print("[空]", flush=True); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True)
            r.to_csv(os.path.join(OUT, name+".csv"), index=False, encoding='utf-8-sig')
            return r
        print(f"[retry {i+1}] {r[:200]}", flush=True); time.sleep(10)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {name}", flush=True)
    return None

T0 = "sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100"
PHASE = """case when date(app_time) < date'2026-08-10' then 'P0_pre'
       when date(app_time) < date'2026-09-03' then 'P1_v53'
       when date(app_time) < date'2026-09-22' then 'P2_cutback'
       else 'P3_v61' end"""

# ============ E1: 评分×四组 (评分档×tl_grp, 看评分内四组坏账差异) ============
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
      and y.app_date >= date'2026-08-19' and y.app_date < date'2026-10-06'
      and e.limit_type='TEMP' and e.change_event_type in ('C010','C013','C015')
  ) x
)
select cast(y.fd_use_creditamount_score_v1 as varchar) as score_v1,
  case when el.change_event_type in ('C013','C015') then 'offline'
       when el.change_event_type = 'C010' then
         case when y.temp_credit_amount_issue_tag=1 then 'online_tag1' else 'online_tag0' end
       else 'none' end as tl_grp,
  count(*) as cnt,
  round({T0},2) as t0_rate,
  round(avg(y.real_issue_amount),0) as issue_avg,
  round(avg(cast(y.fd_creditlevel_main_v4_2 as double)),2) as grade_avg,
  round(avg(cast(y.curr_ovd_cnt_all as double)),2) as ovd_cnt_avg
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
where y.if_issue=1 and y.is_reloan='old'
  and y.app_date >= date'2026-08-19' and y.app_date < date'2026-10-06'
group by 1,2 order by 1,2
""", "E1_score_grp", "E1 评分×四组")

# ============ E2: 评分×阶段 (看评分分布在各策略阶段的漂移) ============
q(f"""
select {PHASE} as phase,
  cast(fd_use_creditamount_score_v1 as varchar) as score_v1,
  count(*) as cnt,
  round({T0},2) as t0_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  round(sum(temp_grant_amount/1000.0),0) as temp_use_k,
  count(distinct if(temp_credit_amount_issue_tag=1,biz_id,null)) as tag1_cnt
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-15' and app_date < date'2026-10-06'
group by 1,2 order by 1,2
""", "E2_score_phase", "E2 评分×阶段")

# ============ E3: type×临额使用 (type 1-4 × tag1/tag0 × 实际点用) ============
q(f"""
select cast(fd_use_creditamount_type as varchar) as use_type,
  case when temp_credit_amount_issue_tag=1 then 'tag1' else 'tag0' end as issue_tag,
  if(temp_grant_amount>0, 'used', 'not_used') as temp_used,
  count(*) as cnt,
  round({T0},2) as t0_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  round(avg(temp_grant_amount/1000.0),1) as temp_use_avg,
  round(avg(cast(fd_creditlevel_main_v4_2 as double)),2) as grade_avg
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-08-19' and app_date < date'2026-10-06'
group by 1,2,3 order by 1,2,3
""", "E3_type_tempuse", "E3 type×临额使用")

# ============ E4: 评分分布漂移 (按月, 看评分占比/件均/t0随时间变化) ============
q(f"""
select date_format(app_date,'%Y-%m') as mth,
  cast(fd_use_creditamount_score_v1 as varchar) as score_v1,
  count(*) as cnt,
  round({T0},2) as t0_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  round(sum(temp_grant_amount/1000.0),0) as temp_use_k,
  count(distinct if(temp_credit_amount_issue_tag=1,biz_id,null)) as tag1_cnt
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-01' and app_date < date'2026-10-01'
group by 1,2 order by 1,2
""", "E4_score_drift", "E4 评分分布漂移(月)")

print("E DONE", flush=True)
