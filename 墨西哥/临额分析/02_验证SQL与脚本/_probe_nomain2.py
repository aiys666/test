# -*- coding: utf-8 -*-
"""nomain修正: mid类型修正; 另查 funnel金额列 / 857节点其他key覆盖率"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 4200)
pd.set_option('display.max_colwidth', 10000); pd.set_option('display.max_rows', 400)
for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)
def q(sql, tag):
    print("=" * 170); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception as ex:
            print(f"[err] {str(ex)[:200]}"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

MID = "(select mid from mx.wxs_application_funnel where tenant='yawey' and cast(biz_id as varchar)='1620000482769098')"

# Q3 同mid跨biz节点(mid bigint)
q(f"""
select biz_id, createtime, modelmainid, substr(cast(outputdata as varchar),1,150) od
from ods.s21_risk_model_record
where cast(mid as bigint)={MID}
  and createtime >= timestamp '2026-10-15 00:00' and createtime < timestamp '2026-10-16 06:00'
  and modelmainid in (1067,661,1500,1542,1635,1522,1523,1386,1379,857)
order by createtime
""", "Q3 同mid跨biz关键节点")

# Q4 used_detail 本biz + change_record 同mid 全量(MAIN+TEMP)
q(f"""
select 'used' src, cast(biz_id as varchar) biz, limit_type, change_action,
       create_time, risk_credit_limit amt, cast(null as varchar) etype
from ods.s05_user_creditlimit_used_detail
where biz_id=1620000482769098
union all
select 'chg', external_id, limit_type, change_action, create_time,
       change_total_grantamount, change_event_type
from ods_view_presto.s05_user_creditlimit_change_record
where mid={MID}
  and create_time >= timestamp '2026-10-15 00:00' and create_time < timestamp '2026-10-17 06:00'
order by create_time
""", "Q4 used_detail+change_record(同mid, 到10/17)")

# Q5 全量: 放款笔中 used_detail 无 MAIN 冻结的有多少(数据延迟盘点)
q("""
with app as (
  select cast(biz_id as varchar) biz, app_date, release_time
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
mm as (
  select cast(biz_id as varchar) biz, sum(risk_credit_limit) m
  from ods.s05_user_creditlimit_used_detail
  where change_action='FREEZE_LIMIT' and limit_type='MAIN' group by 1
)
select a.app_date, count(*) n,
  sum(case when m.biz is null then 1 else 0 end) no_main_detail,
  sum(case when m.biz is not null and m.m=0 then 1 else 0 end) main_zero
from app a left join mm m on a.biz=m.biz
group by 1 order by 1
""", "Q5 每日放款笔中 used_detail 缺MAIN冻结的笔数")
print("DONE-NOMAIN2")
