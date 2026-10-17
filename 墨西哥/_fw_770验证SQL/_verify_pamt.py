# -*- coding: utf-8 -*-
"""验证: model857 的 temp_credit_amount 作为"在线临额发放金额"的正确性"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 2600)

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

# Q1 全量一致率: tag=1 的笔中 857金额覆盖率 + 与C010名义额一致率 + 反向(857有但tag=0)
q("""
with app as (
  select cast(biz_id as varchar) as biz_id
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
tag1 as (
  select cast(biz_id as varchar) as biz_id, min(createtime) as t
  from ods.s21_risk_model_record
  where modelmainid=1386 and strategytype='CHAMPION'
    and outputdata like '%"temp_credit_amount_issue_tag":1%'
  group by 1
),
p857 as (
  select biz_id, amt from (
    select cast(biz_id as varchar) as biz_id,
           cast(regexp_extract(cast(outputdata as varchar), '"temp_credit_amount":([0-9.]+)', 1) as double) as amt,
           row_number() over (partition by biz_id order by createtime) as rn
    from ods.s21_risk_model_record
    where modelmainid=857
      and regexp_extract(cast(outputdata as varchar), '"temp_credit_amount":([0-9.]+)', 1) <> ''
  ) t where rn=1
),
c010 as (
  select cast(external_id as varchar) as biz_id, max(change_total_grantamount) as g
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type='C010' and external_id is not null
  group by 1
)
select
  count(*)                                                       as "tag1笔数(窗口内)",
  sum(case when p.biz_id is not null then 1 else 0 end)          as "有857弹窗金额",
  sum(case when p.biz_id is null     then 1 else 0 end)          as "无857弹窗金额",
  sum(case when c.biz_id is not null then 1 else 0 end)          as "已领取(有C010)",
  sum(case when c.biz_id is not null and p.biz_id is not null and abs(p.amt-c.g)<0.01 then 1 else 0 end) as "857额==C010名义额",
  sum(case when c.biz_id is not null and p.biz_id is not null and abs(p.amt-c.g)>=0.01 then 1 else 0 end) as "857额<>C010名义额"
from app a join tag1 t on a.biz_id=t.biz_id
left join p857 p on a.biz_id=p.biz_id
left join c010 c on a.biz_id=c.biz_id
""", "Q1 全量: 857弹窗金额覆盖率与C010一致率")

# Q2 反向: 有857金额但1386 tag<>1 的笔(是否会被误挂)
q("""
with app as (
  select cast(biz_id as varchar) as biz_id
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
tag1 as (
  select cast(biz_id as varchar) as biz_id
  from ods.s21_risk_model_record
  where modelmainid=1386 and strategytype='CHAMPION'
    and outputdata like '%"temp_credit_amount_issue_tag":1%'
  group by 1
),
p857 as (
  select distinct cast(biz_id as varchar) as biz_id
  from ods.s21_risk_model_record
  where modelmainid=857
    and regexp_extract(cast(outputdata as varchar), '"temp_credit_amount":([0-9.]+)', 1) <> ''
)
select count(*) as "857有金额但tag1缺失"
from app a join p857 p on a.biz_id=p.biz_id
left join tag1 t on a.biz_id=t.biz_id
where t.biz_id is null
""", "Q2 反向: 857有金额但无tag1(应为0或极少)")

# Q3 案例抽查
q("""
with tag1 as (
  select cast(biz_id as varchar) as biz_id, min(createtime) as issue_time
  from ods.s21_risk_model_record
  where modelmainid=1386 and strategytype='CHAMPION'
    and outputdata like '%"temp_credit_amount_issue_tag":1%'
  group by 1
),
p857 as (
  select biz_id, amt from (
    select cast(biz_id as varchar) as biz_id,
           cast(regexp_extract(cast(outputdata as varchar), '"temp_credit_amount":([0-9.]+)', 1) as double) as amt,
           row_number() over (partition by biz_id order by createtime) as rn
    from ods.s21_risk_model_record
    where modelmainid=857
      and regexp_extract(cast(outputdata as varchar), '"temp_credit_amount":([0-9.]+)', 1) <> ''
  ) t where rn=1
),
c010 as (
  select cast(external_id as varchar) as biz_id, max(change_total_grantamount) as g, max(change_used_grantamount) as u
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type='C010' and external_id is not null
  group by 1
)
select t.biz_id, t.issue_time,
       p.amt as "857弹窗发放额",
       c.g   as "C010名义额",
       c.g - c.u as "C010实到账",
       f.temp_grant_amount/1000.0 as "实际使用临额",
       f.contract_amount
from tag1 t
left join p857 p on t.biz_id=p.biz_id
left join c010 c on t.biz_id=c.biz_id
join mx.wxs_application_funnel f on t.biz_id=cast(f.biz_id as varchar) and f.tenant='yawey'
where t.biz_id in ('1620000463197032','1620000462179690','1620000462287861','1620000464027012','1620000466574256')
order by t.biz_id
""", "Q3 案例抽查(5笔)")

print("DONE-PAMT")
