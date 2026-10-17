# -*- coding: utf-8 -*-
"""探查5: type1 0.5 vs 0.6 之谜 + 1379底数真实来源节点定位"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 4000)
pd.set_option('display.max_colwidth', 10000); pd.set_option('display.max_rows', 400)
for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)
def q(sql, tag):
    print("=" * 160); print(tag, flush=True)
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

# A 修复版全量分层: type1 同时测 0.5/0.6, type2 测0.4, type3 测0.2
q("""
with s1523 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"fd_use_creditamount_type":([0-9.]+)',1) as double)) utype
  from ods.s21_risk_model_record
  where modelmainid=1523 and strategytype='CHAMPION'
    and createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
  group by 1
),
s1379 as (
  select cast(biz_id as varchar) biz,
         max(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double)) t1379
  from ods.s21_risk_model_record
  where modelmainid=1379 and strategytype='CHAMPION'
    and createtime>=timestamp '2026-09-01' and createtime<timestamp '2026-10-16'
  group by 1
),
mm as (
  select cast(biz_id as varchar) biz, sum(risk_credit_limit) main_frz
  from ods.s05_user_creditlimit_used_detail
  where change_action='FREEZE_LIMIT' and limit_type='MAIN'
  group by 1
)
select t3.utype, count(*) n,
       sum(case when abs(t.t1379-m.main_frz*0.5)<0.01 then 1 else 0 end) hit_05,
       sum(case when abs(t.t1379-m.main_frz*0.6)<0.01 then 1 else 0 end) hit_06,
       sum(case when abs(t.t1379-m.main_frz*0.4)<0.01 then 1 else 0 end) hit_04,
       sum(case when abs(t.t1379-m.main_frz*0.2)<0.01 then 1 else 0 end) hit_02,
       sum(case when m.main_frz is null then 1 else 0 end) no_main,
       min(t.t1379/m.main_frz) min_ratio, max(t.t1379/m.main_frz) max_ratio
from s1379 t join s1523 t3 on t.biz=t3.biz left join mm m on t.biz=m.biz
where t.t1379 is not null and m.main_frz is not null
group by 1 order by 1
""", "A 全量分层: 1379/MAIN 实际比例")

# B 失配笔1620000480579892: s21 全节点中含 credit/main/amount 字样的输出
q("""
select modelmainid, createtime, cast(outputdata as varchar) od
from ods.s21_risk_model_record
where biz_id=1620000480579892
  and (cast(outputdata as varchar) like '%credit_amount%'
       or cast(outputdata as varchar) like '%main%'
       or cast(outputdata as varchar) like '%use_loop%'
       or cast(outputdata as varchar) like '%grant%')
order by createtime
""", "B 480579892 含额度字段的节点输出")

# C funnel 额度/金额相关列名
q("""
select column_name, data_type
from mx.information_schema.columns
where table_schema='mx' and table_name='wxs_application_funnel'
  and (lower(column_name) like '%credit%' or lower(column_name) like '%amount%'
       or lower(column_name) like '%main%' or lower(column_name) like '%loan%')
order by 1
""", "C funnel额度相关列")
print("DONE-PROBE5")
