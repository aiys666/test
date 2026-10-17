# -*- coding: utf-8 -*-
import sys, re, time
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from mexico_presto import PrestoQuery

txt = open(r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\墨西哥复贷产品分析_成熟窗口vintage_全SQL_v3.sql", encoding="utf-8").read()
def grab(tag):
    m = re.search(r"-- ==== %s[^\n]*\n(.*?)\n-- ==== Q\d|-- ==== %s[^\n]*\n(.*)$" % (tag, tag), txt, re.S)
    body = m.group(1) if m.group(1) else m.group(2)
    return body.strip().rstrip(";")
# simpler: split by section markers
sects = re.split(r"\n-- ==== Q\d+ [^\n]*\n", txt)
q1, q3, q5 = [s.strip().rstrip(";") for s in (sects[1], sects[3], sects[5])]

def no_scan(sql):
    return sql.replace("AND date(release_time) >= date '2026-05-01' AND date(release_time) < date '2026-09-01'",
                       "AND date(release_time) >= date '2026-05-01' AND date(release_time) < date '2026-09-01' AND 1 = 0")

pq = PrestoQuery(); pq.login()
for name, sql in [("Q1 det-month", q1), ("Q3 tot-month", q3), ("Q5 prd", q5)]:
    r = pq.query(no_scan(sql))
    out = f"{r.shape}" if not isinstance(r, str) else f"STR: {r[:160]}"
    print(f"[{name}] -> {out}")
    time.sleep(1)
