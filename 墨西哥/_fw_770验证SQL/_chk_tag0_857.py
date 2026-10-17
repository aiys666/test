# -*- coding: utf-8 -*-
"""确认: tag=0 的笔, 857节点是否也输出金额(决定是否必须加tag=1门槛)"""
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

# tag=0 案例: 1620000474757589(1386 tag=0, 实为离线C015); 抽2笔tag=0
q("""
select cast(biz_id as varchar) as biz_id, modelmainid, nodeserial, createtime, outputdata
from ods.s21_risk_model_record
where cast(biz_id as varchar) in ('1620000474757589','1620000479377160')
  and modelmainid in (1386,1379,857)
order by cast(biz_id as varchar), createtime
""", "tag=0案例: 1386/1379/857 三节点输出对照")
print("DONE-TAG0")
