# -*- coding: utf-8 -*-
"""type1 公式失配笔定位 + 放宽窗口后 dec tag 覆盖复核"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 4000)
pd.set_option('display.max_colwidth', 10000)
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

q("""
with app as (
  select cast(biz_id as varchar) as biz_id, mid
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
dec as (
  select cast(biz_id as varchar) as biz_id,
         max(case when modelmainid=1523 then cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_type":([0-9.]+)',1) as double) end) as dtype,
         max(case when modelmainid=1386 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_issue_tag":([0-9.]+)',1) as double) end) as itag,
         max(case when modelmainid=1379 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double) end) as amt1379,
         max(case when modelmainid=857 then nullif(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double),0) end) as amt857
  from ods.s21_risk_model_record
  where strategytype='CHAMPION' and modelmainid in (1523,1386,1379,857)
    and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
  group by 1
),
yjf as (
  select cast(biz_id as varchar) as biz_id, max(temp_credit_amount_strategy_test_flag) as flag
  from mx.yj_test_table_250225 group by 1
),
mm as (
  select cast(u.biz_id as varchar) as biz_id, sum(u.risk_credit_limit) as main_occupy
  from ods.s05_user_creditlimit_used_detail u join app a on cast(u.biz_id as bigint)=cast(a.biz_id as bigint)
  where u.change_action='FREEZE_LIMIT' and u.limit_type='MAIN' group by 1
)
select a.biz_id, y.flag, d.amt1379, d.amt857, m.main_occupy,
       floor(m.main_occupy/20.0)*20 as base20,
       floor(m.main_occupy/20.0)*20*0.5 as calc50,
       floor(m.main_occupy/20.0)*20*0.6 as calc60
from app a join dec d on a.biz_id=d.biz_id
left join yjf y on a.biz_id=y.biz_id
left join mm m on a.biz_id=m.biz_id
where d.itag=1 and d.dtype=1
  and m.main_occupy is not null
  and abs(d.amt1379 - floor(m.main_occupy/20.0)*20 *
      case when y.flag like '%V5_3%' then 0.6 else 0.5 end) > 0.01
order by a.biz_id
""", "type1 公式失配笔(放宽窗口后)")

# 放宽窗口后 tag1 覆盖复核
q("""
with app as (
  select cast(biz_id as varchar) as biz_id
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
dec as (
  select cast(biz_id as varchar) as biz_id,
         max(case when modelmainid=1386 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_issue_tag":([0-9.]+)',1) as double) end) as itag
  from ods.s21_risk_model_record
  where strategytype='CHAMPION' and modelmainid in (1522,1523,1386,1379,857)
    and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
  group by 1
),
iss as (
  select biz_id from ods.s21_risk_model_record
  where modelmainid=1386 and strategytype='CHAMPION'
    and outputdata like '%"temp_credit_amount_issue_tag":1%' group by biz_id
)
select sum(case when d.itag=1 then 1 else 0 end) tag1_dec_wide,
       sum(case when s.biz_id is not null then 1 else 0 end) tag1_iss_all
from app a left join dec d on a.biz_id=d.biz_id
left join iss s on cast(a.biz_id as bigint)=s.biz_id
""", "放宽窗口后 tag1: dec vs iss 覆盖")
print("DONE-8C")
