# -*- coding: utf-8 -*-
"""补充探查(大宽表前置):
A 经典2笔全量change_record(MAIN+TEMP)还原事件语义
B 1553/1341 节点覆盖率与取值
C 857其他key覆盖率
D 实测比例×策略桶×周 交叉(60%是否随时间/版本)"""
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

# A 经典2笔 change_record 全量(MAIN+TEMP)
q("""
select external_id biz, limit_type, change_event_type, change_action, create_time,
       change_total_grantamount amt, change_used_grantamount used, expiring_time
from ods_view_presto.s05_user_creditlimit_change_record
where mid in (1040160058116903,1040160063333586)
  and create_time >= timestamp '2026-09-01 00:00' and create_time < timestamp '2026-09-03 00:00'
order by mid, create_time
""", "A 经典2笔 change_record 全量(MAIN+TEMP)")

# B 1553 / 1341 覆盖率+取值
q("""
with app as (
  select cast(biz_id as varchar) biz from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
s as (
  select cast(biz_id as varchar) biz,
    max(case when modelmainid=1553 then cast(regexp_extract(cast(outputdata as varchar),'"fd_temp_limit_creditlevel_from_tag":(-?[0-9.]+)',1) as double) end) tag1553,
    max(case when modelmainid=1341 then cast(regexp_extract(cast(outputdata as varchar),'"oldcust_creditlevel":(-?[0-9.]+)',1) as double) end) lvl1341,
    max(case when modelmainid=1341 then regexp_extract(cast(outputdata as varchar),'"oldcust_creditlevel_version":"([^"]+)"',1) end) ver1341
  from ods.s21_risk_model_record
  where strategytype='CHAMPION' and modelmainid in (1553,1341)
    and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
  group by 1
)
select count(*) n,
  sum(case when s.tag1553 is not null then 1 else 0 end) cov1553,
  sum(case when s.lvl1341 is not null then 1 else 0 end) cov1341,
  sum(case when s.tag1553=1 then 1 else 0 end) tag1553_1,
  sum(case when s.tag1553=0 then 1 else 0 end) tag1553_0
from app a left join s on a.biz=s.biz
""", "B1 1553/1341 覆盖率")

q("""
select ver1341, tag1553, count(*) n
from (
  select cast(r.biz_id as varchar) biz,
    max(case when modelmainid=1553 then cast(regexp_extract(cast(outputdata as varchar),'"fd_temp_limit_creditlevel_from_tag":(-?[0-9.]+)',1) as double) end) tag1553,
    max(case when modelmainid=1341 then regexp_extract(cast(outputdata as varchar),'"oldcust_creditlevel_version":"([^"]+)"',1) end) ver1341
  from ods.s21_risk_model_record r
  join mx.wxs_application_funnel f on cast(r.biz_id as varchar)=cast(f.biz_id as varchar)
    and f.tenant='yawey' and f.is_reloan='old' and f.if_issue=1
    and f.app_date >= date'2026-09-01' and f.app_date < date'2026-10-16'
  where r.strategytype='CHAMPION' and r.modelmainid in (1553,1341)
    and r.createtime >= timestamp '2026-08-31' and r.createtime < timestamp '2026-10-17'
  group by 1
) t group by 1,2 order by 1,2
""", "B2 1341版本 × 1553tag 分布")

# C 857 其他key覆盖率
q("""
with app as (
  select cast(biz_id as varchar) biz from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
s as (
  select cast(biz_id as varchar) biz,
    max(case when regexp_like(cast(outputdata as varchar),'"last_credit_amt_float":') then 1 else 0 end) k_last,
    max(case when regexp_like(cast(outputdata as varchar),'"sd_disburse_amt_temp":') then 1 else 0 end) k_sd
  from ods.s21_risk_model_record
  where strategytype='CHAMPION' and modelmainid=857
    and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
  group by 1
)
select count(*) n, sum(k_last) has_last, sum(k_sd) has_sd
from app a left join s on a.biz=s.biz
""", "C 857节点 last_credit_amt_float/sd_disburse_amt_temp 覆盖率")

# D 实测比例(1379/floor20) × yj策略桶 × 周
q("""
with app as (
  select cast(biz_id as varchar) biz, mid, app_date
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
d as (
  select cast(biz_id as varchar) biz,
    max(case when modelmainid=1523 then cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_type":([0-9.]+)',1) as double) end) dtype,
    max(case when modelmainid=1386 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_issue_tag":([0-9.]+)',1) as double) end) itag,
    max(case when modelmainid=1379 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double) end) amt1379
  from ods.s21_risk_model_record
  where strategytype='CHAMPION' and modelmainid in (1523,1386,1379)
    and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
  group by 1
),
mm as (
  select cast(u.biz_id as varchar) biz, floor(sum(u.risk_credit_limit)/20.0)*20 base20
  from ods.s05_user_creditlimit_used_detail u join app a on cast(u.biz_id as bigint)=cast(a.biz as bigint)
  where u.change_action='FREEZE_LIMIT' and u.limit_type='MAIN' group by 1
),
y as (
  select cast(biz_id as varchar) biz, max(temp_credit_amount_strategy_test_flag) flag
  from mx.yj_test_table_250225 group by 1
)
select y.flag,
  case when d.amt1379/mm.base20 between 0.59 and 0.61 then '0.60'
       when d.amt1379/mm.base20 between 0.49 and 0.51 then '0.50'
       when d.amt1379/mm.base20 between 0.39 and 0.41 then '0.40'
       when d.amt1379/mm.base20 between 0.19 and 0.21 then '0.20'
       else 'other' end ratio_real,
  count(*) n
from app a join d on a.biz=d.biz join mm on a.biz=mm.biz left join y on a.biz=y.biz
where d.itag=1 and d.dtype=1 and mm.base20>0
group by 1,2 order by 1,2
""", "D1 type1 实测比例 × yj策略桶")
# D2 type1 实测比例 × 周(看是否随时间切换)
q("""
with app as (
  select cast(biz_id as varchar) biz, mid, app_date
  from mx.wxs_application_funnel
  where tenant='yawey' and is_reloan='old' and if_issue=1
    and app_date >= date'2026-09-01' and app_date < date'2026-10-16'
),
d as (
  select cast(biz_id as varchar) biz,
    max(case when modelmainid=1523 then cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_type":([0-9.]+)',1) as double) end) dtype,
    max(case when modelmainid=1386 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_issue_tag":([0-9.]+)',1) as double) end) itag,
    max(case when modelmainid=1379 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double) end) amt1379
  from ods.s21_risk_model_record
  where strategytype='CHAMPION' and modelmainid in (1523,1386,1379)
    and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
  group by 1
),
mm as (
  select cast(u.biz_id as varchar) biz, floor(sum(u.risk_credit_limit)/20.0)*20 base20
  from ods.s05_user_creditlimit_used_detail u join app a on cast(u.biz_id as bigint)=cast(a.biz as bigint)
  where u.change_action='FREEZE_LIMIT' and u.limit_type='MAIN' group by 1
)
select date_format(date_add('day', -cast(date_format(a.app_date,'%w') as integer), a.app_date),'%Y-%m-%d') wk,
  sum(case when d.amt1379/mm.base20 between 0.59 and 0.61 then 1 else 0 end) r060,
  sum(case when d.amt1379/mm.base20 between 0.49 and 0.51 then 1 else 0 end) r050,
  sum(case when not(d.amt1379/mm.base20 between 0.49 and 0.61) then 1 else 0 end) other,
  count(*) n
from app a join d on a.biz=d.biz join mm on a.biz=mm.biz
where d.itag=1 and d.dtype=1 and mm.base20>0
group by 1 order by 1
""", "D2 type1 实测比例 × 周(时间维度)")
print("DONE-PROBE12")
