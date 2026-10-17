# -*- coding: utf-8 -*-
"""额度框架 G: yj表重建完成后统一重跑 (A月度/A2三阶段/A3评分/D1分层/D2质量/D3-D4DID + F八周四组)
须在 _fw_wait.py 输出 READY 后运行"""
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
        print(f"[retry {i+1}] {r[:150]}", flush=True); time.sleep(10)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {name}", flush=True)
    return None

T0 = "sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100"
T0Y = "sum(if(y.t0_should_amt_1>0,y.t0_overdue_amount_1,null))/nullif(sum(if(y.t0_should_amt_1>0,y.t0_should_amt_1,null)),0)*100"
T3 = "sum(if(t3_should_amt_1>0,t3_overdue_amount_1,null))/nullif(sum(if(t3_should_amt_1>0,t3_should_amt_1,null)),0)*100"
HASH = "from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000"
GRP = f"""case when {HASH} > 0.7 then 'A_v52_always'
       when {HASH} > 0.3 then 'B_switchback'
       else 'C_v53_always' end"""
PHASE = """case when date(app_time) < date'2026-08-10' then 'P0_pre'
       when date(app_time) < date'2026-09-03' then 'P1_v53'
       when date(app_time) < date'2026-09-22' then 'P2_cutback'
       else 'P3_v61' end"""
GRADE = """case when cast(fd_creditlevel_main_v4_2 as double) >= 9 then 'g9p'
       when cast(fd_creditlevel_main_v4_2 as double) >= 6 then 'g6_8'
       when cast(fd_creditlevel_main_v4_2 as double) >= 1 then 'g1_5'
       else 'g_null' end"""

# ---------- A1 月度在线临额 ----------
q(f"""
select date_format(app_date,'%Y-%m') as mth,
  count(*) as loan_cnt,
  count(if(temp_credit_amount_issue_tag=1,1,null)) as online_tag1_cnt,
  round(count(if(temp_credit_amount_issue_tag=1,1,null))*100.0/count(*),2) as online_tag1_pct,
  count(distinct if(temp_grant_amount>0,biz_id,null)) as temp_use_cnt,
  round(sum(temp_grant_amount/1000.0),0) as temp_use_sum_k,
  round(avg(if(temp_grant_amount>0,temp_grant_amount/1000.0,null)),1) as temp_use_avg_k,
  round({T0},2) as t0_rate
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-01' and app_date < date'2026-10-01'
group by 1 order by 1
""", "A1_online_monthly", "A1 月度在线临额发放/使用")

# ---------- A2 四阶段×flag×tag ----------
q(f"""
select {PHASE} as phase,
  coalesce(temp_credit_amount_strategy_test_flag,'no_bucket') as flag,
  case when temp_credit_amount_issue_tag=1 then 'tag1' else 'tag0' end as issue_tag,
  count(*) as loan_cnt,
  round(avg(credit_amount),0) as credit_avg,
  round(avg(real_issue_amount),0) as issue_avg,
  round(sum(real_issue_amount)/nullif(sum(credit_amount),0)*100,2) as tr_rate,
  round({T0},2) as t0_rate,
  round({T3},2) as t3_rate,
  count(distinct if(temp_grant_amount>0,biz_id,null)) as temp_use_cnt,
  round(count(distinct if(temp_grant_amount>0,biz_id,null))*100.0/count(*),1) as temp_use_penetration,
  round(avg(if(temp_grant_amount>0,temp_grant_amount/1000.0,null)),1) as temp_use_avg_k,
  round(sum(temp_grant_amount/1000.0),0) as temp_use_sum_k,
  round(avg(cast(fd_creditlevel_main_v4_2 as double)),2) as grade_avg
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-15' and app_date < date'2026-10-06'
group by 1,2,3 order by 1,2,3
""", "A2_online_phase_flag", "A2 在线四阶段×flag×tag")

# ---------- A3 评分×类型 月度 ----------
q("""
select date_format(app_date,'%Y-%m') as mth,
  cast(fd_use_creditamount_score_v1 as varchar) as score_v1,
  cast(fd_use_creditamount_type as varchar) as use_type,
  count(*) as cnt,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))
       /nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) as t0_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  round(sum(temp_grant_amount/1000.0),0) as temp_sum_k
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-01' and app_date < date'2026-10-01'
group by 1,2,3 order by 1,2,3
""", "A3_score_dist", "A3 用信评分×类型 月度")

# ---------- D1 阶段×评级×flag×tag ----------
q(f"""
select {PHASE} as phase, {GRADE} as grade_grp,
  temp_credit_amount_strategy_test_flag as flag,
  case when temp_credit_amount_issue_tag=1 then 'tag1' else 'tag0' end as itag,
  count(*) as cnt,
  round({T0},2) as t0_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  round(sum(real_issue_amount)/nullif(sum(credit_amount),0)*100,2) as tr_rate,
  round(sum(temp_grant_amount/1000.0),0) as temp_sum_k
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-08-03' and app_date < date'2026-10-06'
  and temp_credit_amount_strategy_test_flag is not null
group by 1,2,3,4 order by 1,2,3,4
""", "D1_grade_flag_tag", "D1 阶段×评级×策略×tag")

# ---------- D2 客群质量月度 ----------
q("""
select date_format(app_date,'%Y-%m') as mth,
  count(*) as loan_cnt,
  round(sum(if(cast(fd_creditlevel_main_v4_2 as double) between 1 and 5,1,0))*100.0/count(*),1) as pct_g1_5,
  round(sum(if(cast(fd_creditlevel_main_v4_2 as double) between 6 and 8,1,0))*100.0/count(*),1) as pct_g6_8,
  round(sum(if(cast(fd_creditlevel_main_v4_2 as double) >= 9,1,0))*100.0/count(*),1) as pct_g9p,
  round(avg(cast(fd_creditlevel_main_v4_2 as double)),2) as grade_avg,
  round(avg(cast(curr_ovd_cnt_all as double)),3) as ovd_cnt_avg,
  round(sum(if(cast(curr_ovd_cnt_all as double)>=1,1,0))*100.0/count(*),1) as pct_ovd1p,
  round(avg(cast(loan_cycle as double)),2) as cycle_avg,
  round(sum(if(cast(is_loop_limit_expired as double)=1,1,0))*100.0/count(*),1) as pct_loop_expired,
  round(avg(cast(history_loanrec_cnt_lastprepaydays_v2 as double)),2) as hist_gap_avg
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-01' and app_date < date'2026-10-01'
group by 1 order by 1
""", "D2_quality_monthly", "D2 复贷客群质量月度")

# ---------- D3 hash三组 全客户 ----------
q(f"""
select {PHASE} as phase, {GRP} as grp,
  count(*) as loan_cnt,
  round(sum(real_issue_amount)/nullif(sum(credit_amount),0)*100,2) as tr_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  round({T0},2) as t0_rate,
  round(sum(if(t0_should_amt_1>0,t0_should_amt_1,null))/1000.0,0) as should_k,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/1000.0,0) as od_k,
  round(sum(equal_houshou_should_interest)/1000.0,0) as interest_k
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-20' and app_date < date'2026-10-06'
group by 1,2 order by 1,2
""", "D3_hash_did_all", "D3 hash三组×阶段 全客户DID")

# ---------- D4 hash三组 tag1 ----------
q(f"""
select {PHASE} as phase, {GRP} as grp,
  count(*) as tag1_cnt,
  round({T0},2) as t0_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  round(avg(cast(fd_creditlevel_main_v4_2 as double)),2) as grade_avg,
  round(sum(temp_grant_amount/1000.0),0) as temp_sum_k
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old' and temp_credit_amount_issue_tag=1
  and app_date >= date'2026-07-20' and app_date < date'2026-10-06'
group by 1,2 order by 1,2
""", "D4_hash_did_tag1", "D4 hash三组×阶段 tag1 DID")

# ---------- F 八周 四组×评级档 (重建后统一快照) ----------
WEEKS = [('2026-07-27','2026-08-04','w0727'), ('2026-08-04','2026-08-11','w0803'),
         ('2026-08-11','2026-08-18','w0810'), ('2026-08-18','2026-08-25','w0817'),
         ('2026-08-25','2026-09-01','w0824'), ('2026-09-01','2026-09-08','w0831'),
         ('2026-09-08','2026-09-15','w0907'), ('2026-09-15','2026-09-22','w0914')]
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
  {GRADE} as grade_grp,
  count(*) as loan_cnt,
  round({T0Y},2) as t0_rate,
  round(sum(if(y.t0_should_amt_1>0,y.t0_should_amt_1,null))/1000.0,0) as should_k,
  round(sum(if(y.t0_should_amt_1>0,y.t0_overdue_amount_1,null))/1000.0,0) as od_k,
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

print("G DONE", flush=True)
