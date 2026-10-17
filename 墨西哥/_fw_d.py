# -*- coding: utf-8 -*-
"""额度分析框架 脚本D(yj单表): 模块5-7 风险分层/客群质量/hash-DID因果"""
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

HASH = "from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000"
GRP = f"""case when {HASH} > 0.7 then 'A_v52_always'
       when {HASH} > 0.3 then 'B_switchback'
       else 'C_v53_always' end"""
PHASE = """case when date(app_time) < date'2026-08-10' then 'P0_pre'
       when date(app_time) < date'2026-09-03' then 'P1_v53'
       when date(app_time) < date'2026-09-22' then 'P2_cutback'
       else 'P3_v61' end"""

# ============ D1: 在线策略 阶段×评级×tag 反事实 ============
q(f"""
select {PHASE} as phase,
  case when cast(fd_creditlevel_main_v4_2 as double) >= 9 then 'g9p'
       when cast(fd_creditlevel_main_v4_2 as double) >= 6 then 'g6_8'
       when cast(fd_creditlevel_main_v4_2 as double) >= 1 then 'g1_5'
       else 'g_null' end as grade_grp,
  temp_credit_amount_strategy_test_flag as flag,
  case when temp_credit_amount_issue_tag=1 then 'tag1' else 'tag0' end as itag,
  count(*) as cnt,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))
       /nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) as t0_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  round(sum(real_issue_amount)/nullif(sum(credit_amount),0)*100,2) as tr_rate,
  round(sum(temp_grant_amount/1000.0),0) as temp_sum_k
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-08-03' and app_date < date'2026-09-22'
  and temp_credit_amount_strategy_test_flag is not null
group by 1,2,3,4 order by 1,2,3,4
""", "D1_grade_flag_tag", "D1 阶段×评级×策略×tag 反事实")

# ============ D2: 客群质量月度 ============
q("""
select date_format(app_date,'%Y-%m') as mth,
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
""", "D2_quality_monthly", "D2 复贷客群质量月度(评级/多头/周期/过期)")

# ============ D3: hash三组×阶段 全客户DID ============
q(f"""
select {PHASE} as phase, {GRP} as grp,
  count(*) as loan_cnt,
  round(sum(real_issue_amount)/nullif(sum(credit_amount),0)*100,2) as tr_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))
       /nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) as t0_rate,
  round(sum(if(t0_should_amt_1>0,t0_should_amt_1,null))/1000.0,0) as should_k,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/1000.0,0) as od_k,
  round(sum(equal_houshou_should_interest)/1000.0,0) as interest_k
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-07-20' and app_date < date'2026-10-06'
group by 1,2 order by 1,2
""", "D3_hash_did_all", "D3 hash三组×阶段 全客户(自然实验DID)")

# ============ D4: hash三组×阶段 tag1桶坏账(临额客群DID) ============
q(f"""
select {PHASE} as phase, {GRP} as grp,
  count(*) as tag1_cnt,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))
       /nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,2) as t0_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  round(avg(cast(fd_creditlevel_main_v4_2 as double)),2) as grade_avg,
  round(sum(temp_grant_amount/1000.0),0) as temp_sum_k
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old' and temp_credit_amount_issue_tag=1
  and app_date >= date'2026-07-20' and app_date < date'2026-10-06'
group by 1,2 order by 1,2
""", "D4_hash_did_tag1", "D4 hash三组×阶段 tag1临额客群DID")
