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
  "G window over agg":   f"select product_name, count(*) c, sum(count(*)) over (partition by 1) s from {T} where 1=0 group by product_name",
  "H grp by product":    f"select product_name, count(distinct camera_id) loans, count(distinct mid) custs, sum(contract_amount) ca from {T} where 1=0 and product_name is not null group by product_name",
  "I grp by month col":  f"select date_format(date_trunc('month', date(release_time)), '%Y-%m') grp, count(distinct camera_id) loans from {T} where 1=0 group by 1",
  "J union all 2levels": f"select 'a' g, product_name, count(*) c from {T} where 1=0 group by 1,2 union all select 'b', null, count(*) from {T} where 1=0",
  "K case share wnd":    f"select grp, product_name, loans, round(loans*1.0/nullif(sum(case when product_name is not null then loans end) over (partition by grp),0),4) sh from (select date_format(date_trunc('month', date(release_time)), '%Y-%m') grp, product_name, count(distinct camera_id) loans from {T} where 1=0 group by 1,2) group by grp, product_name, loans",
}
pq = PrestoQuery(); pq.login()
for name, sql in tests.items():
    try:
        r = pq.query(sql)
        out = f"{r.shape}" if not isinstance(r, str) else f"STR: {r[:120]}"
    except Exception as ex:
        out = f"EXC: {ex}"
    print(f"[{name}] -> {out}")
    time.sleep(1)
