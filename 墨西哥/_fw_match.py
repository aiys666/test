# -*- coding: utf-8 -*-
"""对账: 在线临额(yj tag=1 及使用) vs 额度变更记录 C010
窗口 2026-08-19 ~ 10-06 (与B/C系列一致)
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 400)

def q(sql, tag):
    print("=" * 90); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:160]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}"); return None

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: print("[login retry]"); time.sleep(8)

# A 看 C010 关键列(判定关联键)
q("""
select id, mid, external_id, risk_invoke_id, change_total_grantamount, change_used_grantamount,
  create_time, expiring_time, change_desc
from ods_view_presto.s05_user_creditlimit_change_record
where change_event_type='C010' and create_time>=date'2026-08-19'
order by create_time desc limit 5
""", "A C010 样例(找关联键)")

# B yj 在线临额侧
q("""
select
  sum(if(temp_credit_amount_issue_tag=1,1,0)) as tag1_cnt,
  sum(if(temp_credit_amount_issue_tag=1 and temp_grant_amount>0,1,0)) as tag1_used_cnt,
  count(distinct if(temp_credit_amount_issue_tag=1, mid, null)) as tag1_mid,
  count(distinct if(temp_credit_amount_issue_tag=1 and temp_grant_amount>0, mid, null)) as tag1_used_mid,
  round(sum(if(temp_credit_amount_issue_tag=1 and temp_grant_amount>0, temp_grant_amount/1000.0, 0)),1) as used_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date>=date'2026-08-19' and app_date<date'2026-10-06'
""", "B yj 在线临额侧(tag=1 / tag=1且使用)")

# C C010 侧
q("""
select count(*) as c010_cnt, count(distinct mid) as c010_mid,
  count(distinct external_id) as c010_extid,
  round(sum(change_total_grantamount),1) as c010_grant_amt,
  round(sum(change_used_grantamount),1) as c010_used_amt
from ods_view_presto.s05_user_creditlimit_change_record
where change_event_type='C010'
  and create_time>=date'2026-08-19' and create_time<date'2026-10-06'
""", "C C010 侧")

# D biz 级匹配: yj.biz_id vs C010.external_id
q("""
with y as (
  select distinct cast(biz_id as varchar) as bid from mx.yj_test_table_250225
  where is_reloan='old' and if_issue=1 and temp_credit_amount_issue_tag=1 and temp_grant_amount>0
    and app_date>=date'2026-08-19' and app_date<date'2026-10-06'
),
c as (
  select distinct cast(external_id as varchar) as bid from ods_view_presto.s05_user_creditlimit_change_record
  where change_event_type='C010' and create_time>=date'2026-08-19' and create_time<date'2026-10-06'
)
select (select count(*) from y) as y_used_biz, (select count(*) from c) as c010_biz,
  count(*) as matched_biz
from y join c on y.bid=c.bid
""", "D biz级匹配 yj(用临额的笔) vs C010.external_id")

# E mid 级匹配
q("""
with y as (select distinct mid from mx.yj_test_table_250225
  where is_reloan='old' and if_issue=1 and temp_credit_amount_issue_tag=1 and temp_grant_amount>0
    and app_date>=date'2026-08-19' and app_date<date'2026-10-06'),
c as (select distinct mid from ods_view_presto.s05_user_creditlimit_change_record
  where change_event_type='C010' and create_time>=date'2026-08-19' and create_time<date'2026-10-06')
select (select count(*) from y) as y_mid, (select count(*) from c) as c010_mid, count(*) as matched_mid
from y join c on y.mid=c.mid
""", "E mid级匹配")

print("DONE-MATCH")
