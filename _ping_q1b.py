# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from mexico_presto import PrestoQuery

txt = open(r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\墨西哥复贷产品分析_成熟窗口vintage_全SQL_v3.sql", encoding="utf-8").read()
# 取 Q1 段: 从第一个 WITH 到第一个 "\n-- ==== Q2"
s = txt.index("WITH raw AS")
e = txt.index("\n-- ==== Q2", s)
q1 = txt[s:e].strip().rstrip(";")
print("Q1 clean len:", len(q1), "| first:", q1[:20].replace("\n", "\n"))

pq = PrestoQuery(); pq.login()
r = pq.query(q1)
if isinstance(r, str):
    print("STR-RESULT:", r[:800])
else:
    print("DF:", r.shape)
    print(r.to_string())
