# -*- coding: utf-8 -*-
"""快速复查 8/14-8/21 笔数, 判断回填是否在推进"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

for _i in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(10)

sql = """
select app_date, count(*) cnt
from mx.yj_test_table_250225
where app_date >= date'2026-08-11' and app_date < date'2026-08-22'
group by 1 order by 1
"""
for k in range(6):
    print("---", k, time.strftime('%H:%M:%S'), "---", flush=True)
    for i in range(3):
        r = None
        try:
            r = pq.query(sql)
        except Exception:
            time.sleep(5)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            print(dict(zip(r['app_date'].astype(str), r['cnt'])), flush=True); break
        print("err", r[:120], flush=True); time.sleep(5)
        try: pq.login()
        except Exception: pass
    time.sleep(120)
print("PROBE2 DONE", flush=True)
