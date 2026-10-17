# -*- coding: utf-8 -*-
"""诊断 yj_test_table_250225: 表类型/分区/日期覆盖边界"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

for _i in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(10)

def q(sql, tag, retry=4):
    print("="*100); print(tag, flush=True)
    for i in range(retry):
        try:
            r = pq.query(sql)
        except Exception as e:
            print(f"[conn {i+1}] {type(e).__name__}", flush=True); time.sleep(8)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r)==0: print("[空]"); return
            print(r.head(80).to_string()); print(f"[rows={len(r)}]", flush=True); return
        print(f"[retry {i+1}] {r[:200]}", flush=True); time.sleep(8)
        try: pq.login()
        except Exception: pass

q("show create table mx.yj_test_table_250225", "表定义")
q("select min(app_date) mn, max(app_date) mx, count(*) cnt, count(distinct app_date) days from mx.yj_test_table_250225",
  "全表日期范围")
q("""
select app_date, count(*) cnt
from mx.yj_test_table_250225
where app_date >= date'2026-08-01' and app_date < date'2026-08-22'
group by 1 order by 1
""", "8/01-8/21 逐日笔数")
q("select * from mx.yj_test_table_250225 limit 1", "样例行(看分区字段)")
print("PROBE DONE", flush=True)
