# -*- coding: utf-8 -*-
"""探针：打印 funnel/yj 两表列名（按关键字过滤，用于精确取数）"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

pq = PrestoQuery(); pq.login()

def q(sql):
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:300]); return None
    return r

def dump(table, label):
    d = q(f"select * from {table} limit 1")
    if d is None: return []
    cols = list(d.columns)
    print("=" * 100)
    print(f"[{label}] {table} 总列数={len(cols)}")
    kws = ["should", "tpre", "fact", "capit", "window", "overdue", "interest",
           "if_issue", "if_app", "if_in", "if_sx", "reloan", "grant", "channel",
           "media", "source", "app_group", "product", "risk", "amount", "loan_cycle",
           "haircut", "mid", "biz", "create_time", "release_time", "app_", "issue_",
           "tenant", "v3", "credit", "level", "subscore", "score", "max_ovd", "emcontact",
           "other_app", "repay", "day"]
    for c in cols:
        low = c.lower()
        if any(k in low for k in kws):
            print(c)
    return cols

fcols = dump("mx.wxs_application_funnel", "FUNNEL")
ycols = dump("mx.yj_test_table_250225", "YJ")

# 保存全量列名到文件备查
with open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_funnel_cols.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(fcols))
with open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_yj_cols.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(ycols))
print("DONE")
