# -*- coding: utf-8 -*-
"""用户新SQL核对: ①7月覆盖/唯一性 ②案例用户 mid 下钻 ③双重临额(在线×离线/跨笔)实证"""
import sys, io, time, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 400)

def q(sql, tag):
    print("=" * 90); print(tag, flush=True)
    for i in range(6):
        try:
            r = pq.query(sql)
        except Exception as e:
            print(f"[conn retry {i+1}] {type(e).__name__}"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True)
            return r
        print(f"[retry {i+1}] {str(r)[:160]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}"); return None

for _ in range(6):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception:
        print("[login retry]"); time.sleep(8)

# Q1 月度覆盖: 7月是否有复贷老客数据
q("""
select date_format(app_date,'%Y-%m') as m,
  count(*) as rows_all, sum(if(is_reloan='old',1,0)) as old_rows,
  sum(if(is_reloan='old' and if_issue=1,1,0)) as old_issued
from mx.yj_test_table_250225
where app_date >= date'2026-06-01' and app_date < date'2026-10-06'
group by 1 order by 1
""", "Q1 月度覆盖(是否有7月数据)")

# Q2 biz_id 唯一性(C系列账户口径校验)
q("""
select count(*) as n_rows, count(distinct biz_id) as n_biz, count(distinct mid) as n_mid
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-08-19' and app_date < date'2026-10-06'
""", "Q2 biz_id唯一性(8/19-10/06, old+if_issue)")

# Q3 案例用户 调额记录
q("""
select * from ods_view_presto.s05_user_creditlimit_change_record
where mid=1040160040722566 order by create_time
""", "Q3 案例用户 mid=1040160040722566 调额记录")

# Q4 案例用户 额度冻结记录(含主额/临额)
q("""
select * from ods.s05_user_creditlimit_used_detail
where mid=1040160040722566 and change_action='FREEZE_LIMIT' and create_time>=date'2026-05-01'
order by create_time
""", "Q4 案例用户 FREEZE_LIMIT 冻结记录")

# Q5 同一mid跨笔使用临额次数分布(temp_grant_amount>0)
q("""
select uses, count(*) as mids from (
  select mid, count(*) as uses
  from mx.yj_test_table_250225
  where is_reloan='old' and if_issue=1 and temp_grant_amount>0
    and app_date >= date'2026-08-19' and app_date < date'2026-10-06'
  group by mid
) t group by uses order by uses
""", "Q5 同mid跨笔使用临额次数分布")

# Q6 在线×离线双路径重叠
q("""
select sum(if(has_on=1 and has_off=1,1,0)) as both_path,
       sum(if(has_on=1 and has_off=0,1,0)) as online_only,
       sum(if(has_on=0 and has_off=1,1,0)) as offline_only,
       sum(if(has_on=0 and has_off=0,1,0)) as neither,
       count(*) as mid_total
from (
  select mid,
    max(if(temp_credit_amount_issue_tag=1,1,0)) as has_on,
    max(if(temp_grant_amount>0 and temp_credit_amount_issue_tag<>1,1,0)) as has_off
  from mx.yj_test_table_250225
  where is_reloan='old' and if_issue=1
    and app_date >= date'2026-08-19' and app_date < date'2026-10-06'
  group by mid
) t
""", "Q6 同mid 在线×离线 双路径重叠")

print("DONE")
