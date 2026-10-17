# -*- coding: utf-8 -*-
"""轮询 yj_test_table_250225 是否重建完成: 逐周放款笔数稳定两轮到 READY"""
import sys, io, time, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_data"

def login():
    for _ in range(8):
        try:
            pq = PrestoQuery(); pq.login(); return pq
        except Exception:
            print("[login retry]", flush=True); time.sleep(10)
    raise RuntimeError("login fail")

pq = login()

SQL = """
select case
   when app_date >= date'2026-07-27' and app_date < date'2026-08-04' then 'w0727'
   when app_date >= date'2026-08-04' and app_date < date'2026-08-11' then 'w0803'
   when app_date >= date'2026-08-11' and app_date < date'2026-08-18' then 'w0810'
   when app_date >= date'2026-08-18' and app_date < date'2026-08-25' then 'w0817'
   when app_date >= date'2026-08-25' and app_date < date'2026-09-01' then 'w0824'
   when app_date >= date'2026-09-01' and app_date < date'2026-09-08' then 'w0831' end as awk,
 count(*) cnt
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old' and app_date >= date'2026-07-27' and app_date < date'2026-09-08'
group by 1 order by 1
"""

prev = None
stable_rounds = 0
for rnd in range(50):
    print(f"--- round {rnd} {time.strftime('%H:%M:%S')} ---", flush=True)
    df = None
    for i in range(3):
        try:
            r = pq.query(SQL)
        except Exception:
            print(f"[conn retry {i+1}]", flush=True); time.sleep(8)
            try: pq = login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            df = r; break
        print(f"[sql retry {i+1}] {r[:100]}", flush=True); time.sleep(8)
        try: pq = login()
        except Exception: pass
    if df is None:
        time.sleep(120); continue
    cur = dict(zip(df['awk'], df['cnt']))
    print(json.dumps(cur), flush=True)
    need = {'w0727':7000, 'w0803':7800, 'w0810':8000, 'w0817':8000, 'w0824':8000, 'w0831':8000}
    full = all(int(cur.get(k,0)) >= v for k,v in need.items())
    same = prev is not None and all(abs(int(cur.get(k,0))-int(prev.get(k,0))) <= 30 for k in need)
    if full and same:
        stable_rounds += 1
    else:
        stable_rounds = 0
    prev = cur
    if stable_rounds >= 2:
        with open(os.path.join(OUT, "_READY.flag"), "w") as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S') + " " + json.dumps(cur))
        print("READY", flush=True)
        break
    time.sleep(180)

print("WAIT EXIT", flush=True)
