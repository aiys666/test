# -*- coding: utf-8 -*-
"""排查: 1386 决策记录里除 tag 外, 金额落在哪个字段/哪张表
案例: 1620000463197032(tag=1未领取) vs 1620000462179690(tag=1且C010=450)"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 3000); pd.set_option('display.max_rows', 500)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag, wide_transpose=True, cell_max=260):
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
            if wide_transpose and r.shape[1] > 14:
                r = r.map(lambda s: str(s)[:cell_max] if s is not None else s)
                print(r.T.to_string())
            else:
                print(r.to_string())
            print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

BIZS = "'1620000463197032','1620000462179690'"

# Q2 s21_risk_model_record: 两案例 biz 的全部决策记录(不限modelmainid)
q(f"""
select * from ods.s21_risk_model_record
where cast(biz_id as varchar) in ({BIZS})
""", "Q2 s21全字段(两案例全部决策节点)")

print("DONE-FINDAMT-R1")
