# -*- coding: utf-8 -*-
"""探查用信临额决策链 1522→1523→1386→1379→857 的底数落库
Q1 单笔全节点链路(biz 1620000462287861: 1180×40%=472 → 857=450)
Q2 四个节点 outputdata 结构取样
"""
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

# Q1 该笔在 s21 的全部决策节点（看完整链路有哪些节点、时间顺序）
q("""
select modelmainid, createtime, strategytype,
       length(cast(outputdata as varchar)) as od_len
from ods.s21_risk_model_record
where biz_id='1620000462287861'
order by createtime
""", "Q1 biz=1620000462287861 全部决策节点")

# Q1b 5 个关键节点的完整 outputdata
q("""
select modelmainid, createtime, cast(outputdata as varchar) as outputdata
from ods.s21_risk_model_record
where biz_id='1620000462287861'
  and modelmainid in (1522,1523,1386,1379,857)
order by createtime
""", "Q1b 5节点完整outputdata(472→450之谜)")

# Q2 四个节点各取样3条 outputdata 看字段结构
q("""
select modelmainid, biz_id, createtime, od from (
  select modelmainid, cast(biz_id as varchar) biz_id, createtime,
         cast(outputdata as varchar) od,
         row_number() over (partition by modelmainid order by createtime) rn
  from ods.s21_risk_model_record
  where modelmainid in (1522,1523,1379,857)
    and createtime >= timestamp '2026-09-20'
    and outputdata is not null
    and length(cast(outputdata as varchar)) between 20 and 3000
) t where rn<=3 order by modelmainid, createtime
""", "Q2 四节点 outputdata 结构取样")
print("DONE-PROBE1")
