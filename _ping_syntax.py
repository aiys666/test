# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from mexico_presto import PrestoQuery

T = "mx.wxs_application_funnel"
tests = {
  "A grouping sets basic": f"select product_name, count(*) c from {T} where 1=0 group by grouping sets ((product_name), ())",
  "B two CTEs":            f"with raw as (select * from {T} where 1=0), g as (select count(*) c from raw) select * from g",
  "C gs 3combos":          f"select product_name, release_time from {T} where 1=0 group by grouping sets ((release_time, product_name), (release_time), (product_name))",
  "D count distinct gs":   f"select product_name, count(distinct camera_id) c from {T} where 1=0 group by grouping sets ((product_name), ())",
  "E gs + window":         f"select product_name, count(*) c, sum(count(*)) over (partition by 1) s from {T} where 1=0 group by grouping sets ((product_name), ())",
  "F month format":        f"select date_format(date_trunc('month', date(release_time)), '%Y-%m') g from {T} where 1=0 group by 1",
}
pq = PrestoQuery(); pq.login()
for name, sql in tests.items():
    try:
        r = pq.query(sql)
        out = f"{r.shape}" if not isinstance(r, str) else f"STR: {r[:90]}"
    except Exception as ex:
        out = f"EXC: {ex}"
    print(f"[{name}] -> {out}")
    time.sleep(1)
