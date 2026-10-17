# -*- coding: utf-8 -*-
"""探查2: 单笔链路 + 857/1379输出key全景 + 1379算额→857最终额调整规则"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 4000)
pd.set_option('display.max_colwidth', 10000); pd.set_option('display.max_rows', 300)
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

# Q1 biz=1620000462287861 全部决策节点(biz_id是bigint)
q("""
select modelmainid, createtime, strategytype,
       length(cast(outputdata as varchar)) as od_len,
       cast(outputdata as varchar) as od
from ods.s21_risk_model_record
where biz_id=1620000462287861
order by createtime
""", "Q1 462287861 全节点完整链路")

# Q2 857 节点 outputdata 的 key 全景(9/20-10/16 抽样10万条)
q("""
select the_key, count(*) as cnt
from (
  select regexp_extract(cast(outputdata as varchar), '"([a-z_0-9]+)"\\s*:', 1) as the_key
  from ods.s21_risk_model_record
  where modelmainid=857
    and createtime >= timestamp '2026-09-20'
    and createtime <  timestamp '2026-09-22'
) t group by 1 order by 2 desc
""", "Q2 857节点 outputdata key 分布(9/20-9/21)")

# Q3 1379 节点 outputdata 的 key 全景
q("""
select the_key, count(*) as cnt
from (
  select regexp_extract(cast(outputdata as varchar), '"([a-z_0-9]+)"\\s*:', 1) as the_key
  from ods.s21_risk_model_record
  where modelmainid=1379
    and createtime >= timestamp '2026-09-20'
    and createtime <  timestamp '2026-09-22'
) t group by 1 order by 2 desc
""", "Q3 1379节点 outputdata key 分布(9/20-9/21)")

# Q4 1379 算额非空(tag=1)样本20条: 看 expired_day / label / 金额长什么样
q("""
select cast(biz_id as varchar) biz_id, createtime, cast(outputdata as varchar) od
from ods.s21_risk_model_record
where modelmainid=1379
  and createtime >= timestamp '2026-09-20'
  and createtime <  timestamp '2026-09-21'
  and outputdata not like '%"temp_credit_amount":null%'
limit 20
""", "Q4 1379算额非空样本")
print("DONE-PROBE2")
