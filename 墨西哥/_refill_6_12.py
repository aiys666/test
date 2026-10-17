# -*- coding: utf-8 -*-
import sys, io, os, time
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
sys.path.insert(0, r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥")
from mexico_presto import PrestoQuery
import pandas as pd

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"
pq = PrestoQuery(); pq.login()

# 内联需要的定义(从 _download_6_12 复制关键片段)
def myq(sql, retry=6):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r or "does not exist" in r):
            print(f"  [retry{i+1}] {r[:60]}"); pq.login(); time.sleep(6); continue
        return r
    return r

src = open(os.path.join(OUT, "_download_6_12.py"), encoding="utf-8").read()
src = src.split("run = ")[0]
src = src.replace("sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')", "")
src = src.replace("pq = PrestoQuery(); pq.login()", "")
exec(src)

need = ["app_group","channel_category","loan_cycle","reloan_num","contract_amount"]
for key in need:
    fp = os.path.join(OUT, f"_agg612_{key}_issue.pkl")
    if os.path.exists(fp):
        print(f"[exists] {key}"); continue
    expr = FUNNEL_DIMS[key]
    r = myq(build_sql("issue", expr))
    if isinstance(r, str):
        print(f"[FAIL] {key}: {r[:100]}"); continue
    for c in [x for x in r.columns if x not in ("d","dim")]:
        r[c] = pd.to_numeric(r[c], errors="coerce")
    r.to_pickle(fp)
    print(f"[ok] {key}/issue rows={len(r)}")
print("done")
