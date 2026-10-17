# -*- coding: utf-8 -*-
import sys, re
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from mexico_presto import PrestoQuery

txt = open(r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\墨西哥复贷产品分析_成熟窗口vintage_全SQL_v3.sql", encoding="utf-8").read()
parts = re.split(r"-- ==== Q\d+ ", txt)
# parts[1] = 月度明细 section (Q1)
q1 = parts[1].split("-- ==== Q2")[0].strip().rstrip(";")
print("Q1 len:", len(q1))

pq = PrestoQuery(); pq.login()
r = pq.query(q1)
if isinstance(r, str):
    print("STR-RESULT:", r[:500])
else:
    print("DF:", r.shape)
    print(r.head(3).to_string())
