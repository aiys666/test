# -*- coding: utf-8 -*-
"""探查: yj表 4t7 字段 + used_detail 结构(关联键)"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)

def q(sql, tag="", show=20):
    print("="*110)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:800]); return None
    if r is None or len(r) == 0:
        print("[空数据]"); return None
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# 1) yj 表所有含 t7 / window 的列名
r = q("select * from mx.yj_test_table_250225 limit 1", "yj表样本(取列名)")
if r is not None:
    cols = list(r.columns)
    t7cols = [c for c in cols if 't7' in c.lower() or 'window' in c.lower() or '4' in c]
    print("\n>>> 含t7/window的列:")
    for c in t7cols:
        print("  ", c)

# 2) used_detail FREEZE_LIMIT 样本(看 biz_id 关联键)
q("""
select * from ods_view_presto.s05_user_creditlimit_used_detail
where change_action='FREEZE_LIMIT'
order by create_time desc limit 10
""", "used_detail FREEZE_LIMIT 样本")

# 3) used_detail 列名
r3 = q("select * from ods_view_presto.s05_user_creditlimit_used_detail limit 1", "used_detail 列名")
if r3 is not None:
    print("\n>>> used_detail 全部列:", list(r3.columns))
