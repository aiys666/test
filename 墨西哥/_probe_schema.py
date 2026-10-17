# -*- coding: utf-8 -*-
"""查表结构 + 产品相关字段的实际取值"""
import sys, io, os, pickle
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"
pq = PrestoQuery(); pq.login()

def q(sql, retry=4):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r):
            print(f"  [重登{i+1}]"); pq.login(); continue
        return r
    raise SystemExit(f"[失败] {r}")

# 1) 表结构：找产品/期限相关字段
print("="*100)
print("【1】wxs_application_funnel 表结构（产品/期限/分组相关字段）")
r = q("describe mx.wxs_application_funnel")
if isinstance(r, str):
    print("[FAIL]", r[:300])
else:
    # describe 返回列名在 Column 字段
    col = r.columns[0]
    allcols = r[col].astype(str).tolist()
    kw = ["product", "loan", "cycle", "period", "term", "nper", "group", "install", "plan"]
    hit = [c for c in allcols if any(k in c.lower() for k in kw)]
    print("命中字段:")
    for c in hit:
        print("  ", c)
    print("\n总字段数:", len(allcols))
    # 保存全字段
    with open(os.path.join(OUT, "_funnel_cols.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(allcols))
