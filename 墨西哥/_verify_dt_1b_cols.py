# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

# 完整列清单
r = pq.query("describe mx.darren_jieqing_dt_table")
cols = []
if not isinstance(r, str):
    cols = r.iloc[:, 0].tolist()
    with open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_dt_columns.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(cols))
    print("总列数:", len(cols))
    print("--- 前 180 列 ---")
    for i, c in enumerate(cols[:180], 1):
        print(f"{i:3d} {c}")
else:
    print(r)
