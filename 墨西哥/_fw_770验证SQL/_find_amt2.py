# -*- coding: utf-8 -*-
"""排查R2: 1386决策的金额落在哪个字段"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 3000); pd.set_option('display.max_colwidth', 900)

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

BIZS = "'1620000463197032','1620000462179690'"

# Q1 两案例的全部决策节点清单(哪个节点、各字段多大)
q(f"""
select cast(biz_id as varchar) as biz_id, modelmainid, strategytype, nodeserial, createtime,
       length(inputdata) as len_in, length(outputdata) as len_out,
       length(matchedrules) as len_matched, length(weightruleresult) as len_weight
from ods.s21_risk_model_record
where cast(biz_id as varchar) in ({BIZS})
order by cast(biz_id as varchar), createtime
""", "Q1 决策节点清单(各字段长度)")

# Q2 1386节点: outputdata / matchedrules / weightruleresult 原文
q(f"""
select cast(biz_id as varchar) as biz_id, createtime, outputdata,
       substr(cast(matchedrules as varchar),1,600)  as matchedrules,
       substr(cast(weightruleresult as varchar),1,600) as weightruleresult
from ods.s21_risk_model_record
where cast(biz_id as varchar) in ({BIZS}) and modelmainid=1386
""", "Q2 1386节点 output/matched/weight")

# Q3 inputdata 里 temp_credit_amount 相关键值上下文
q(f"""
select cast(biz_id as varchar) as biz_id, modelmainid, createtime,
       regexp_extract(cast(inputdata as varchar), '.{{0,50}}temp_credit_amount[^,\\"]*\\":?\\s*[^,}}]{{0,40}}') as m1,
       regexp_extract(cast(inputdata as varchar), '.{{0,50}}temp_credit[a-z_]*type[^,}}]{{0,30}}') as m2
from ods.s21_risk_model_record
where cast(biz_id as varchar) in ({BIZS}) and modelmainid=1386
""", "Q3 inputdata中temp_credit_amount上下文")

# Q4 其他节点是否落了金额类输出
q(f"""
select cast(biz_id as varchar) as biz_id, modelmainid, nodeserial, createtime,
       substr(cast(outputdata as varchar),1,300) as outdata,
       regexp_extract(cast(matchedrules as varchar), '.{{0,60}}[Aa]mount[^,}}]{{0,40}}') as amt_in_matched
from ods.s21_risk_model_record
where cast(biz_id as varchar) in ({BIZS}) and modelmainid<>1386
  and (cast(outputdata as varchar) like '%mount%' or cast(matchedrules as varchar) like '%mount%')
""", "Q4 其他节点的金额输出")

print("DONE-FINDAMT-R2")
