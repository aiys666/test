# -*- coding: utf-8 -*-
"""宽表v8尾巴定位: (A)iss无时间窗 vs dec有时间窗 的11笔tag1差异
   (B)tag1无857的3笔 + 公式失配4笔明细"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 4000)
pd.set_option('display.max_colwidth', 10000); pd.set_option('display.max_rows', 200)
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

# A: iss(无时间窗)有tag1 但 dec 窗口[9/1,10/16)内无1386记录的笔
q("""
with app as (
  select cast(biz_id as varchar) as biz_id, app_date
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
tag_all as (
  select cast(biz_id as varchar) as biz_id, min(createtime) as t_any
  from ods.s21_risk_model_record
  where modelmainid=1386 and strategytype='CHAMPION'
    and outputdata like '%"temp_credit_amount_issue_tag":1%'
  group by 1
),
tag_in as (
  select cast(biz_id as varchar) as biz_id
  from ods.s21_risk_model_record
  where modelmainid=1386 and strategytype='CHAMPION'
    and outputdata like '%"temp_credit_amount_issue_tag":1%'
    and createtime >= timestamp '2026-09-01' and createtime < timestamp '2026-10-16'
  group by 1
)
select a.app_date, t.t_any, count(*) n
from app a join tag_all t on a.biz_id=t.biz_id
left join tag_in i on a.biz_id=i.biz_id
where i.biz_id is null
group by 1,2 order by 1
""", "A 11笔差异: 1386 tag=1 的 createtime 落在 dec 时间窗外")

# B: tag1 中 无857 / 无比例 / 公式失配 的明细
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
  where strategytype='CHAMPION' and modelmainid in (1522,1523,1386,1379,857)
    and createtime >= timestamp '2026-09-01' and createtime < timestamp '2026-10-16'
  group by 1
),
mm as (
  select cast(u.biz_id as varchar) as biz_id, sum(u.risk_credit_limit) as main_occupy
  from ods.s05_user_creditlimit_used_detail u join app a on cast(u.biz_id as bigint)=cast(a.biz_id as bigint)
  where u.change_action='FREEZE_LIMIT' and u.limit_type='MAIN' group by 1
)
select a.biz_id, d.dtype, d.amt1379, d.amt857, m.main_occupy,
       floor(m.main_occupy/20.0)*20 as base20
from app a join dec d on a.biz_id=d.biz_id
left join mm m on a.biz_id=m.biz_id
where d.itag=1 and (
  d.amt857 is null
  or d.dtype not in (1,2,3)
  or (d.dtype in (1,2,3) and abs(d.amt1379 - floor(m.main_occupy/20.0)*20 *
        case d.dtype when 2 then 0.4 when 3 then 0.2 else null end) > 0.01
      and d.dtype in (2,3))
)
order by d.dtype, a.biz_id
""", "B 异常明细(无857/type4/null/type2-3公式失配)")
print("DONE-8B")
