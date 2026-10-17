# -*- coding: utf-8 -*-
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)
sql = """
select cast(biz_id as varchar) biz, createtime, cast(outputdata as varchar) od
from ods.s21_risk_model_record
where modelmainid=1067
  and cast(biz_id as varchar) in ('1620000462179690','1620000482769098','1620000480579892')
  and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
order by biz, createtime
"""
r = None
for i in range(8):
    try:
        rr = pq.query(sql)
        if not isinstance(rr, str):
            r = rr; break
        print("retry", rr[:150]); time.sleep(8)
    except Exception as e:
        print("retry-exc", e); time.sleep(8)
for _, row in r.iterrows():
    print("="*100); print(row['biz'], row['createtime']); print(row['od'][:3000])
print("DONE")
